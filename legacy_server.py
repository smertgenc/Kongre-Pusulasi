#!/usr/bin/env python3
"""Local congress decision support server. Python 3.9+, standard library only."""
import argparse
import csv
import io
import json
import os
import sqlite3
import threading
import uuid
import webbrowser
from datetime import datetime, timezone, date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from engine import CRITERIA, DEFAULT_MATRICES, calculate_model, score, scenario_weights, number

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT/'data'/'kongre.db'
LOCK = threading.RLock()

def now(): return datetime.now(timezone.utc).isoformat()
def encode(x): return json.dumps(x,ensure_ascii=False,allow_nan=False)
def connect():
    con = sqlite3.connect(str(DB_PATH),timeout=10)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def initialize():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY,version INTEGER UNIQUE NOT NULL,name TEXT NOT NULL,data TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS congresses(id TEXT PRIMARY KEY,identity_key TEXT UNIQUE NOT NULL,metadata TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evaluations(id TEXT PRIMARY KEY,congress_id TEXT NOT NULL REFERENCES congresses(id),model_id TEXT NOT NULL REFERENCES models(id),data TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS evaluations_congress ON evaluations(congress_id,created_at);
        ''')
        if not con.execute('SELECT 1 FROM models LIMIT 1').fetchone():
            mid=str(uuid.uuid4())
            con.execute('INSERT INTO models VALUES(?,?,?,?,?)',(mid,1,'Excel başlangıç modeli',encode(calculate_model(DEFAULT_MATRICES)),now()))
            fixtures=json.loads((ROOT/'analiz'/'hesaplama_sonuclari.json').read_text())
            for f in fixtures['congresses']:
                cid=str(uuid.uuid4())
                meta={'name':f['name'],'edition':'Excel örneği','start_date':'','end_date':'','location':'','organizer':'','website':'','format':'Belirtilmedi','context':'Excel referans verisi','sample':True}
                values={c[0]:v for c,v in zip(CRITERIA,f['inputs'])}
                payload={'metadata':meta,'utilities':values,'notes':{c[0]:'Excel’den aktarılmış örnek; kaynak kanıtı yok.' for c in CRITERIA},'scale':1,'evaluator':'Excel aktarımı','result':score(calculate_model(DEFAULT_MATRICES)['weights'],values,{'average':70,'valid':90})}
                con.execute('INSERT INTO congresses VALUES(?,?,?,?)',(cid,identity(meta),encode(meta),now()))
                con.execute('INSERT INTO evaluations VALUES(?,?,?,?,?)',(str(uuid.uuid4()),cid,mid,encode(payload),now()))

def identity(m):
    return ' '.join((m['name']+'|'+m['edition']).casefold().split())

def model_row(r):
    return {'id':r['id'],'version':r['version'],'name':r['name'],'created_at':r['created_at'],**json.loads(r['data'])}

def state():
    with connect() as con:
        models=[model_row(r) for r in con.execute('SELECT * FROM models ORDER BY version DESC')]
        congresses=[]
        for c in con.execute('SELECT * FROM congresses ORDER BY created_at DESC'):
            evaluations=[{'id':e['id'],'model_id':e['model_id'],'created_at':e['created_at'],**json.loads(e['data'])} for e in con.execute('SELECT * FROM evaluations WHERE congress_id=? ORDER BY created_at DESC',(c['id'],))]
            congresses.append({'id':c['id'],'metadata':json.loads(c['metadata']),'evaluations':evaluations})
    return {'models':models,'congresses':congresses,'criteria':[{'code':c,'name':n,'group':g,'description':d} for c,n,g,d in CRITERIA]}

def textfield(data,key,limit=200,required=False):
    val=data.get(key,'')
    if not isinstance(val,str) or len(val)>limit: raise ValueError(key+': metin çok uzun veya geçersiz.')
    val=val.strip()
    if required and not val: raise ValueError('Lütfen '+key+' alanını doldurun.')
    return val

def save_evaluation(p):
    meta=p.get('metadata')
    if not isinstance(meta,dict): raise ValueError('Kongre bilgileri eksik.')
    meta={k:textfield(meta,k,2000 if k=='context' else 500,k in ('name','edition')) for k in ['name','edition','start_date','end_date','location','organizer','website','format','context']}
    for k in ('start_date','end_date'):
        if meta[k]:
            try: date.fromisoformat(meta[k])
            except ValueError: raise ValueError('Tarih YYYY-AA-GG biçiminde olmalıdır.')
    if meta['start_date'] and meta['end_date'] and meta['end_date']<meta['start_date']: raise ValueError('Bitiş tarihi başlangıçtan önce olamaz.')
    if meta['website'] and (urlsplit(meta['website']).scheme not in ('http','https') or not urlsplit(meta['website']).netloc): raise ValueError('Web adresi http:// veya https:// ile başlamalıdır.')
    if not meta['context']: raise ValueError('Değerlendirme profilini / koşullarını belirtin.')
    scale=p.get('scale',1)
    if type(scale) is not int or scale not in (1,5,10): raise ValueError('Puan ölçeği 1, 5 veya 10 olmalıdır.')
    raw=p.get('scores')
    if not isinstance(raw,dict) or set(raw)!={c[0] for c in CRITERIA}: raise ValueError('On kriterin tamamı gereklidir.')
    if any(v is not None and (not number(v) or not 0<=v<=scale or int(v)!=v) for v in raw.values()): raise ValueError('Puan, seçilen ölçekte bir tam sayı olmalıdır.')
    utilities={k:None if v is None else v/scale for k,v in raw.items()}
    notes=p.get('notes',{})
    if not isinstance(notes,dict): raise ValueError('Kriter notları geçersiz.')
    notes={c[0]:textfield(notes,c[0],3000) for c in CRITERIA}
    for c in utilities:
        if utilities[c] is not None and not notes[c]: raise ValueError(c+' için karar gerekçesi veya kaynak ekleyin.')
    evaluator=textfield(p,'evaluator',120,True)
    with LOCK, connect() as con:
        m=con.execute('SELECT * FROM models WHERE id=?',(p.get('model_id'),)).fetchone()
        if not m: raise ValueError('Model bulunamadı.')
        model=model_row(m)
        result=score(model['weights'],utilities,model['thresholds'])
        cid=p.get('congress_id')
        if cid:
            c=con.execute('SELECT * FROM congresses WHERE id=?',(cid,)).fetchone()
            if not c: raise ValueError('Kongre bulunamadı.')
            latest=con.execute('SELECT id FROM evaluations WHERE congress_id=? ORDER BY created_at DESC LIMIT 1',(cid,)).fetchone()
            if p.get('previous_id')!=latest['id']: raise ValueError('Bu kayıt değişmiş. Sayfayı yenileyip tekrar deneyin.')
            meta['sample']=json.loads(c['metadata']).get('sample',False)
            con.execute('UPDATE congresses SET identity_key=?,metadata=? WHERE id=?',(identity(meta),encode(meta),cid))
        else:
            cid=str(uuid.uuid4()); meta['sample']=False
            con.execute('INSERT INTO congresses VALUES(?,?,?,?)',(cid,identity(meta),encode(meta),now()))
        eid=str(uuid.uuid4())
        payload={'metadata':meta,'utilities':utilities,'notes':notes,'scale':scale,'evaluator':evaluator,'result':result}
        con.execute('INSERT INTO evaluations VALUES(?,?,?,?,?)',(eid,cid,model['id'],encode(payload),now()))
    return {'id':cid,'evaluation_id':eid,'result':result}

class Handler(BaseHTTPRequestHandler):
    def send(self,status,content,ctype='application/json; charset=utf-8',headers=None):
        body=content if isinstance(content,bytes) else content.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        try:
            path=urlsplit(self.path).path
            if path=='/api/state': return self.send(200,encode(state()))
            if path=='/api/backup':
                with LOCK,connect() as con:
                    dump='\n'.join(con.iterdump())
                return self.send(200,dump,'application/sql; charset=utf-8',{'Content-Disposition':'attachment; filename="kongre-yedek.sql"'})
            if path=='/api/export':
                out=io.StringIO(); writer=csv.writer(out,delimiter=';')
                writer.writerow(['Kongre','Edisyon','Model','Tarih','Değerlendiren','Puan','Durum','Kapsam']+[c[0] for c in CRITERIA])
                data=state(); models={m['id']:m['version'] for m in data['models']}
                def safe(v):
                    v=str(v)
                    return "'"+v if v.startswith(('=','+','-','@','\t','\r')) else v
                for c in data['congresses']:
                    for e in c['evaluations']:
                        r=e['result']; meta=e['metadata']
                        writer.writerow([safe(meta['name']),safe(meta['edition']),models[e['model_id']],e['created_at'],safe(e['evaluator']),r['total'] if r['total'] is not None else '',r['status'],r['coverage']]+[e['utilities'][k[0]] for k in CRITERIA])
                return self.send(200,('\ufeff'+out.getvalue()).encode(),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="kongre-degerlendirmeleri.csv"'})
            files={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
            if path not in files: return self.send(404,encode({'error':'Sayfa bulunamadı.'}))
            ctype={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/styles.css':'text/css; charset=utf-8'}[path]
            self.send(200,(ROOT/'static'/files[path]).read_bytes(),ctype)
        except Exception:
            self.send(500,encode({'error':'İstek tamamlanamadı.'}))

    def do_POST(self):
        try:
            host=self.headers.get('Host','')
            if host not in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)):
                return self.send(403,encode({'error':'Yalnızca yerel erişime izin verilir.'}))
            origin=self.headers.get('Origin')
            if origin and origin not in ('http://'+host,): return self.send(403,encode({'error':'Kaynak doğrulanamadı.'}))
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('JSON içerik gereklidir.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<200000: raise ValueError('İstek boyutu geçersiz.')
            p=json.loads(self.rfile.read(length))
            if not isinstance(p,dict): raise ValueError('İstek nesne olmalıdır.')
            path=urlsplit(self.path).path
            if path=='/api/evaluations': return self.send(201,encode(save_evaluation(p)))
            if path in ('/api/models/preview','/api/models'):
                model=calculate_model(p.get('matrices'),p.get('thresholds'))
                if path.endswith('preview'): return self.send(200,encode(model))
                if not model['consistent']: raise ValueError('CR > 0,10 olan matris var. Karşılaştırmaları gözden geçirin.')
                name=textfield(p,'name',120,True)
                with LOCK,connect() as con:
                    latest=con.execute('SELECT id,version FROM models ORDER BY version DESC LIMIT 1').fetchone()
                    if p.get('base_id')!=latest['id']: raise ValueError('Yeni bir model sürümü var. Sayfayı yenileyin.')
                    mid=str(uuid.uuid4()); version=latest['version']+1
                    con.execute('INSERT INTO models VALUES(?,?,?,?,?)',(mid,version,name,encode(model),now()))
                return self.send(201,encode({'id':mid,'version':version}))
            if path=='/api/scenario':
                data=state(); model=next((m for m in data['models'] if m['id']==p.get('model_id')),None)
                if not model: raise ValueError('Model bulunamadı.')
                weights=scenario_weights(model['weights'],p.get('criterion'),p.get('target'))
                results=[]
                for c in data['congresses']:
                    e=next((e for e in c['evaluations'] if e['model_id']==model['id']),None)
                    if e: results.append({'id':c['id'],'name':e['metadata']['name'],'context':e['metadata']['context'],'scale':e['scale'],'before':e['result'],'after':score(weights,e['utilities'],model['thresholds'])})
                return self.send(200,encode({'weights':weights,'results':results}))
            self.send(404,encode({'error':'İşlem bulunamadı.'}))
        except sqlite3.IntegrityError:
            self.send(409,encode({'error':'Aynı ad ve edisyonla bir kongre zaten var. Mevcut kaydı düzenleyin.'}))
        except (ValueError,TypeError,KeyError) as e:
            self.send(422,encode({'error':str(e)}))
        except Exception as e:
            print('Server error:',repr(e))
            self.send(500,encode({'error':'İşlem kaydedilemedi. Lütfen tekrar deneyin.'}))

def main():
    global DB_PATH
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--db',type=Path,default=DB_PATH)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args(); DB_PATH=args.db
    initialize()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url='http://127.0.0.1:'+str(args.port)
    print('Kongre Pusulası hazır: '+url,flush=True)
    if args.open: threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nUygulama durduruldu.')
    finally: server.server_close()

if __name__=='__main__': main()
