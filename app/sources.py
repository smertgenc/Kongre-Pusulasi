"""Bounded extraction. URLs connect only to validated public IPs, including redirects."""
import base64
import hashlib
import http.client
import io
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin, urldefrag
from bs4 import BeautifulSoup
from pypdf import PdfReader
from app.services import now

MAX_PDF = 4_000_000
MAX_TEXT = 60_000

def clean(text):
    return ' '.join(text.replace('\x00',' ').split())

def public_target(url):
    from app.network import require_online
    require_online()
    try:
        u = urlsplit(url)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.port not in (None,80,443):
            raise ValueError()
        host = u.hostname.encode('idna').decode('ascii')
        addresses = socket.getaddrinfo(host, u.port or (443 if u.scheme=='https' else 80), type=socket.SOCK_STREAM)
        ips = [ipaddress.ip_address(x[4][0]) for x in addresses]
        if not ips or any(not ip.is_global or ip.is_multicast or ip.is_reserved for ip in ips):
            raise ValueError()
        return u, host, addresses[0][4][0]
    except (ValueError, OSError, UnicodeError):
        raise ValueError('Web adresi erişilebilir, genel bir http/https adresi olmalıdır. Yerel ağ adresleri alınamaz.') from None

class PinnedConnection(http.client.HTTPConnection):
    def __new__(cls, host, port, ip, secure):
        from app.network import proxy_for, ProxyConnection
        proxy = proxy_for(('https' if secure else 'http')+'://'+host)
        if proxy: return ProxyConnection(host, port, secure, proxy)
        return super().__new__(cls)

    def __init__(self, host, port, ip, secure):
        super().__init__(host, port, timeout=10)
        self.ip, self.secure = ip, secure

    def connect(self):
        self.sock = socket.create_connection((self.ip,self.port),self.timeout)
        if self.secure:
            from app.network import tls_context
            self.sock = tls_context().wrap_socket(self.sock,server_hostname=self.host)

def related_links(soup, url):
    """Only links present on the page, in the same event path and origin."""
    root=urlsplit(url)
    path=root.path.rstrip('/')
    if path.lower().endswith(('.html','.htm','.php','.asp','.aspx')):
        path=path.rsplit('/',1)[0]
    keywords=('hakkında','hakkinda','about','bilim','scientific','committee','kurul','program','programme','konu','topic','ücret','ucret','fee','registration','kayıt','kayit','geçmiş','gecmis','history')
    links=[];seen={urldefrag(url)[0]}
    for a in soup.find_all('a',href=True):
        label=clean(a.get_text(' '));href=a['href'].strip()
        if not href or href.startswith('#') or not any(k in label.casefold() for k in keywords):continue
        try:
            target=urldefrag(urljoin(url,href))[0];u=urlsplit(target)
        except ValueError:continue
        if (u.scheme,u.netloc)!=(root.scheme,root.netloc) or u.username or u.password:continue
        if path and not u.path.startswith(path+'/'):continue
        if u.path.lower().endswith(('.pdf','.jpg','.png','.zip','.docx')) or target in seen:continue
        seen.add(target);links.append({'url':target,'label':label[:200]})
    return links[:4]

def fetch_page(url, *, with_links=False, allowed_origin=None):
    for _ in range(4):
        if allowed_origin is not None and (urlsplit(url).scheme,urlsplit(url).netloc)!=allowed_origin:
            raise ValueError('İlgili sayfa başka bir siteye yönlendi; alınmadı.')
        u, host, ip = public_target(url)
        if host == 'instagram.com' or host.endswith('.instagram.com'):
            raise ValueError('Instagram içeriğini Instagram seçeneğinde metin olarak yapıştırın; oturum gerektiren sayfalar alınamaz.')
        conn = PinnedConnection(host,u.port or (443 if u.scheme=='https' else 80),ip,u.scheme=='https')
        try:
            conn.request('GET',(u.path or '/')+('?' + u.query if u.query else ''),headers={'User-Agent':'KongrePusulasi/1.2','Accept':'text/html,text/plain','Accept-Encoding':'identity'})
            r = conn.getresponse()
            if r.status in (301,302,303,307,308):
                if not r.getheader('Location'): raise ValueError('Web yönlendirmesi geçersiz.')
                url = urljoin(url,r.getheader('Location')); continue
            if r.status != 200: raise ValueError('Web sayfası alınamadı. İçeriği metin olarak ekleyebilirsiniz.')
            if r.getheader('Content-Encoding','identity') != 'identity': raise ValueError('Sıkıştırılmış web yanıtı desteklenmiyor; metni yapıştırın.')
            mime = r.getheader('Content-Type','').lower()
            if not any(t in mime for t in ('text/html','text/plain','application/xhtml')):
                raise ValueError('Adres HTML/metin döndürmedi. PDF dosyasını indirip PDF alanından yükleyin.')
            raw=bytearray(); deadline=time.monotonic()+20
            while len(raw)<=1_000_000:
                if time.monotonic()>deadline: raise ValueError('Web sayfası zaman aşımına uğradı.')
                chunk=r.read(16384)
                if not chunk: break
                raw.extend(chunk)
            if len(raw)>1_000_000: raise ValueError('Web sayfası 1 MB sınırını aşıyor; ilgili metni yapıştırın.')
            soup=BeautifulSoup(bytes(raw),'html.parser')
            title=clean(soup.title.get_text())[:200] if soup.title else host
            links=related_links(soup,url) if with_links else []
            for tag in soup(['script','style','noscript','nav','footer','form','svg']): tag.decompose()
            if with_links:return title, clean(soup.get_text(' ')), url, links
            return title, clean(soup.get_text(' ')), url
        except (OSError, http.client.HTTPException):
            raise ValueError('Web sayfasına bağlanılamadı. Metni yapıştırarak devam edebilirsiniz.') from None
        finally: conn.close()
    raise ValueError('Web sayfasında çok fazla yönlendirme var.')

def fetch_site(url):
    title,text,final_url,links=fetch_page(url,with_links=True)
    origin=(urlsplit(final_url).scheme,urlsplit(final_url).netloc)
    segments=[];warnings=[];seen={final_url};total=0
    def append(label,content,address):
        nonlocal total
        if len(content)<80:return False
        if total+len(content)>MAX_TEXT:
            warnings.append('İlgili sayfanın metni toplam sınırı aşıyor; bu sayfa analize alınmadı.');return False
        segments.append({'id':str(len(segments)+1),'page':None,'label':label,'url':address,'text':content})
        total+=len(content);return True
    if not append(title,text,final_url):warnings.append('Ana sayfada yeterli açıklama bulunamadı; aynı kongrenin ilgili sayfaları incelendi.')
    for link in links:
        try:
            label,content,address,_=fetch_page(link['url'],with_links=True,allowed_origin=origin)
            if address in seen:continue
            seen.add(address)
            if not append(label,content,address):warnings.append(link['label']+': yeterli okunabilir metin yok veya boyut sınırı aşıldı.')
        except ValueError as exc:warnings.append(link['label']+': '+str(exc))
    if not segments:
        raise ValueError('Kongre sayfasından yalnızca başlık/menü alınabildi. Program veya açıklama sayfasını, PDF dosyasını ya da kongre metnini ekleyin. AI isteği gönderilmedi.')
    return title,segments,final_url,warnings

def extract_sources(inputs, *, search=None):
    sources=[]; total=0
    for i, source in enumerate(inputs,1):
        sid=f'S{i}'; url=source.url; warnings=[]; extra={}
        if source.kind=='url':
            label, segments, url, warnings = fetch_site(source.content)
        elif source.kind=='search':
            if search is None: raise ValueError('Web arama bağlantısı kurulmamış.')
            from app.search import SEARCH_PROVIDERS
            results=search(source.content,source.search_provider)
            label=SEARCH_PROVIDERS[source.search_provider]+' · '+source.content
            segments=[{**r,'id':str(n),'page':None,'text':clean(r['text'])} for n,r in enumerate(results,1)]
            url=''
            extra={'search_provider':source.search_provider,'query':source.content}
            warnings.append('Arama servisi tarafından getirilen kaynak metinleri kullanıldı; sonuçların kongre adı ve edisyonuyla eşleştiğini kontrol edin.')
            if any(r.get('excerpt_only') for r in results):warnings.append('Bazı sonuçlarda yalnızca arama özeti mevcut; tam sayfa doğrulaması yapılmadı.')
            if any(r.get('truncated') for r in results):warnings.append('Uzun arama sonuçlarının ilk 12.000 karakteri analize alındı.')
        elif source.kind=='image':
            from app.image_ocr import extract_image
            ocr,image=extract_image(source.content)
            label=source.label or 'Kongre görseli';url=''
            segments=[{'id':'1','page':None,'text':clean(ocr['text']),'label':'Görselden okunan metin'}]
            extra={'image':image,'ocr':{'engine':ocr['engine'],'lines':ocr['lines']}}
            warnings.append('Görseldeki metin bu bilgisayarda OCR ile okundu. Yazım ve rakam hataları olabilir; alıntıları görselle karşılaştırın. Yalnızca okunan metin AI sağlayıcısına gönderildi.')
        elif source.kind=='pdf':
            try:
                raw=base64.b64decode(source.content,validate=True)
                if len(raw)>MAX_PDF or not raw.startswith(b'%PDF-'): raise ValueError()
                reader=PdfReader(io.BytesIO(raw))
                if reader.is_encrypted: raise ValueError('Şifreli PDF desteklenmiyor.')
                if len(reader.pages)>30: raise ValueError('PDF en fazla 30 sayfa olabilir.')
                segments=[]
                for n,p in enumerate(reader.pages,1):
                    text=clean(p.extract_text() or '')
                    if not text: warnings.append(f'{n}. sayfada metin yok; OCR gerekli olabilir.')
                    segments.append({'id':str(n),'page':n,'text':text})
                    if sum(len(s['text']) for s in segments)>MAX_TEXT: raise ValueError('PDF metni 60.000 karakteri aşıyor; ilgili sayfaları yükleyin.')
                label=source.label or 'PDF dosyası'
            except ValueError as e:
                raise ValueError(str(e) or 'Geçerli, en fazla 4 MB boyutunda bir PDF seçin.') from None
            except Exception:
                raise ValueError('PDF okunamadı. Metin içeren, şifresiz bir PDF yükleyin.') from None
        else:
            label=source.label or ('Instagram gönderisi' if source.kind=='instagram' else 'Kongre metni')
            segments=[{'id':'1','page':None,'text':clean(source.content)}]
            if url:
                u=urlsplit(url)
                if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:
                    raise ValueError('Kaynak bağlantısı geçersiz.')
        text='\n'.join(s['text'] for s in segments)
        if len(text)<20: raise ValueError(label+': yeterli metin bulunamadı. Taranmış PDF için OCR henüz desteklenmiyor.')
        total+=len(text)
        if total>MAX_TEXT: raise ValueError('Kaynakların toplam metni 60.000 karakteri aşıyor; ilgili bölümleri seçin.')
        sources.append({'id':sid,'kind':source.kind,'label':source.label or label,'url':url,'segments':segments,
                        'retrieved_at':now(),'content_hash':hashlib.sha256(text.encode()).hexdigest(),'warnings':warnings,**extra})
    return sources
