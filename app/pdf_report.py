"""Local PDF export from immutable analysis/review snapshots; no external calls."""
from io import BytesIO
from pathlib import Path
import os
from threading import Lock
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, KeepTogether, Image
from app.congress_policy import policy_definitions

_FONT_LOCK=Lock()

def register_fonts():
    with _FONT_LOCK:
        if 'Congress' in pdfmetrics.getRegisteredFontNames():return
        candidates=[('/System/Library/Fonts/Supplemental/Arial.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
                    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                    (str(Path(os.getenv('WINDIR', 'C:/Windows'))/'Fonts/arial.ttf'),
                     str(Path(os.getenv('WINDIR', 'C:/Windows'))/'Fonts/arialbd.ttf'))]
        for regular,bold in candidates:
            if Path(regular).is_file() and Path(bold).is_file():
                pdfmetrics.registerFont(TTFont('Congress',regular))
                pdfmetrics.registerFont(TTFont('CongressBold',bold))
                pdfmetrics.registerFontFamily('Congress',normal='Congress',bold='CongressBold',italic='Congress',boldItalic='CongressBold')
                return
        raise ValueError('PDF için Türkçe karakter destekli Arial veya DejaVu Sans yazı tipi bulunamadı.')

def analysis_pdf(report, *, logo=None):
    register_fonts()
    analysis=report['analysis'];review=report.get('review');model=report['model']
    result=review['saved']['result'] if review else analysis['result']
    metadata=review['metadata'] if review else analysis['metadata']
    criteria={c['code']:c for c in policy_definitions()}
    ink=colors.HexColor('#13264c');blue=colors.HexColor('#234ccc');muted=colors.HexColor('#536683')
    styles={
        'body':ParagraphStyle('body',fontName='Congress',fontSize=9,leading=13,textColor=ink,spaceAfter=7,splitLongWords=True),
        'title':ParagraphStyle('title',fontName='CongressBold',fontSize=23,leading=28,textColor=ink,spaceAfter=12),
        'h2':ParagraphStyle('h2',fontName='CongressBold',fontSize=13,leading=17,textColor=blue,spaceBefore=14,spaceAfter=8,keepWithNext=True),
        'small':ParagraphStyle('small',fontName='Congress',fontSize=8,leading=11,textColor=muted,spaceAfter=5,splitLongWords=True),
    }
    def p(text,kind='body'):
        text=str(text or '').replace('\x00','').replace('\u2011','-')
        return Paragraph(escape(text).replace('\n','<br/>'),styles[kind])
    def number(value):return 'Bilinmiyor' if value is None else f'{value:.2f}'.replace('.',',')
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=44,leftMargin=44,topMargin=48,bottomMargin=44,
                          title=str(metadata.get('name') or 'Kongre analizi'),author='Kongre Pusulası')
    story=[p('KONGRE PUSULASI / AHP ANALİZ RAPORU','small'),p(metadata.get('name') or 'Kongre analizi','title'),
           p(f"Analiz: {report['created_at'][:10]} | {report.get('provider_name','AI')} / {report['provider_model']} | AHP v{model['version']}",'small')]
    if report.get('providers_used'):
        story.append(p('Analize katkı veren AI servisleri: '+'; '.join(
            f"{item['provider_name']} / {item['provider_model']} ({item['batches']} parça)"
            for item in report['providers_used']),'small'))
    if report.get('provider_failures'):
        story.append(p('Otomatik geçişte tamamlanamayan servisler: '+'; '.join(
            f"{item['provider_name']} ({item['code']})" for item in report['provider_failures']),'small'))
    if report.get('resumed_batches'):
        story.append(p(f"Önceki denemeden korunan tamamlanmış parça: {report['resumed_batches']}",'small'))
    if logo:
        from app.logo_service import logo_surface
        emblem = Image(BytesIO(logo))
        ratio = min(110/emblem.imageWidth, 55/emblem.imageHeight)
        emblem.drawWidth, emblem.drawHeight = emblem.imageWidth*ratio, emblem.imageHeight*ratio
        emblem.hAlign = 'LEFT'
        if logo_surface(logo) == 'dark':
            emblem = Table([[emblem]], colWidths=[122], hAlign='LEFT')
            emblem.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0b1945')),
                                       ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.insert(1, emblem)
    names={'edition':'Edisyon / yıl','start_date':'Başlangıç','end_date':'Bitiş','location':'Konum','organizer':'Düzenleyen','format':'Katılım biçimi'}
    story.append(p(' | '.join(names[k]+': '+str(metadata[k]) for k in names if metadata.get(k)),'small'))
    if review:story.append(p('Kaydedilmiş inceleme sonucu. İnceleyen: '+review.get('evaluator',''),'small'))
    else:story.append(p('AI analiz sonucu; kullanıcı incelemesi henüz kaydedilmedi.','small'))
    if report.get('deleted'):story.append(p('Bu analiz silinen analizler arasında korunuyor.','small'))
    raw=review['saved'].get('raw_score') if review else analysis.get('raw_score')
    score=number(result.get('total')) if result.get('total') is not None else number(result['lower'])+' - '+number(result['upper'])
    story += [p('Sonuç','h2'),p(('Ham puan: '+str(raw)+' / 10 | ' if raw is not None else '')+'AHP puanı: '+score+' / 100 | '+result['status']),
              p('Kanıt kapsamı: %'+str(round(analysis['completeness']*100))+' | AI güven tahmini: '+('Belirtilmedi' if analysis.get('confidence') is None else '%'+str(round(analysis['confidence']*100))))]
    story.append(p(analysis.get('general_explanation') or 'AHP puanı kriter değerleri ile model ağırlıklarının çarpımlarından hesaplanmıştır.'))
    story.append(p('Politika: '+analysis.get('policy_version','Eski kayıt')+' | Ağırlıklı kanıt kapsamı: '+str(round(100*analysis.get('evidence_coverage',0)))+'% | Sayı atanmış ağırlık: '+str(round(100*analysis.get('assigned_coverage',analysis['result']['coverage'])))+'%', 'small'))
    story.append(p('Ağırlık kaynağı ve sınıflandırma eşikleri deneysel kalibrasyon gerektirir. AI güveni doğruluk garantisi değildir. Kanıt bulunmayan varsayılanlar gözlemlenmiş gerçek anlamına gelmez. Görsel alıntıları OCR metniyle eşleştirilir; okuma hatalarını asıl görselle kontrol edin.','small'))
    for conflict in analysis.get('conflicts',[]):story.append(p('Kaynak çelişkisi: '+str(conflict.get('field',''))+' - '+' / '.join(conflict.get('values',[]))))
    story.append(p('AHP hesabı ve kriter katkıları','h2'))
    table_rows=[[p(x,'small') for x in ['Kriter','Ağırlık','Değer','Katkı','Karar / güven']]]
    for finding in analysis['findings']:
        code=finding['criterion'];decision=review['decisions'][code] if review else None
        value=decision['final_value'] if decision else finding['value']
        confidence='Kullanıcı kararı' if decision and decision['action']!='approve' else finding.get('confidence_label') or '%'+str(round(finding['confidence']*100))
        if finding.get('basis')=='project_default' and (not decision or decision['action']=='approve'):confidence+=' / Proje kuralı'
        table_rows.append([p(code+' - '+criteria[code]['name'],'small'),p('%'+number(model['weights'][code]*100),'small'),
                           p('?' if value is None else str(int(value)),'small'),p(number(result['contributions'][code]),'small'),p(confidence,'small')])
    table=Table(table_rows,colWidths=[184,57,38,53,doc.width-332],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0ff')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d8e1f2')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story+=[table,p('Katkı = kriter değeri x global AHP ağırlığı x 100. Mevcut Excel ağırlıkları korunmuştur.','small'),p('Kriter gerekçeleri ve kanıtlar','h2')]
    for finding in analysis['findings']:
        code=finding['criterion'];decision=review['decisions'][code] if review else None
        block=[p(code+' - '+criteria[code]['name'],'h2')]
        corrected=decision and decision['action']!='approve'
        block.append(p((decision.get('note') or 'Kullanıcı bilinmiyor olarak kaydetti.') if corrected else finding['explanation']))
        if corrected:block.append(p('Aşağıdaki alıntılar ilk AI bulgusuna aittir; nihai değer yukarıdaki kullanıcı kararıdır.','small'))
        if not finding['evidence']:block.append(p('Bu kriter için kullanılabilir kaynak alıntısı yok.','small'))
        for evidence in finding['evidence']:
            source=next((s for s in report['sources'] if s['id']==evidence['source_id']),{})
            segment=next((s for s in source.get('segments',[]) if s['id']==evidence['segment_id']),{})
            block.append(p('“'+evidence['quote']+'”'))
            ref=source.get('id','')+'/'+segment.get('id','')+' | '+str(segment.get('label') or source.get('label') or '')
            if segment.get('page'):ref+=' | Sayfa '+str(segment['page'])
            block.append(p(ref,'small'))
        story.append(KeepTogether(block))
    story.append(p('Kaynak künyeleri','h2'))
    for source in report['sources']:
        story.append(p(source['id']+' - '+source['label']))
        story.append(p('Tür: '+source['kind']+' | Erişim: '+source.get('retrieved_at','')[:10],'small'))
        for segment in source['segments']:
            url=segment.get('url') or source.get('url')
            if url:story.append(p(source['id']+'/'+segment['id']+' - '+url,'small'))
        for warning in source.get('warnings',[]):story.append(p(warning,'small'))
    story.append(p('Analiz kimliği: '+report['id']+' | Politika: '+analysis.get('policy_version','Önceki sürüm'),'small'))
    def footer(canvas,document):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d8e1f2'));canvas.line(44,32,A4[0]-44,32)
        canvas.setFont('Congress',8);canvas.setFillColor(muted)
        canvas.drawString(44,20,'Kongre Pusulası - Kaynaklara dayalı AHP değerlendirmesi')
        canvas.drawRightString(A4[0]-44,20,str(document.page));canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
