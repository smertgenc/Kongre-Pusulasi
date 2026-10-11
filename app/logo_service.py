"""Bounded public-site logo discovery and local raster storage; never changes AHP."""
import base64
import hashlib
import http.client
import io
import json
import re
import time
import warnings
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urljoin, urlsplit, unquote

from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, StrictBool
from sqlalchemy import select
from app.input_model import InputModel
from app.models import Congress, CongressLogo, CongressDeletion
from app.services import now, require_active, ConflictError, NotFoundError
from app.sources import public_target, PinnedConnection

MAX_IMAGE = 3_000_000

class LogoUpload(InputModel):
    content: str = Field(min_length=1, max_length=4_000_000)

class LogoDiscovery(InputModel):
    force: StrictBool = False

def raster_logo(raw):
    """Decode and re-encode images, dropping metadata, active formats and animation."""
    if not raw or len(raw) > MAX_IMAGE:
        raise ValueError('Logo en fazla 3 MB olabilir.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP', 'ICO'):
                    raise ValueError('PNG, JPG, WebP veya ICO biçiminde bir logo seçin.')
                if image.width * image.height > 16_000_000 or min(image.size) < 8:
                    raise ValueError('Logo en az 8 piksel ve en fazla 16 megapiksel olmalıdır.')
                image = ImageOps.exif_transpose(image).convert('RGBA')
                image.thumbnail((512, 512))
                output = io.BytesIO()
                image.save(output, format='PNG', optimize=True)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Logo dosyası okunamadı. PNG, JPG veya WebP görseli seçin.') from None

def fetch_asset(url, *, html=False, deadline=None):
    """Pin DNS on every redirect. No browser cookies, private addresses or remote SVG."""
    deadline = deadline or time.monotonic() + 25
    maximum = 1_000_000 if html else MAX_IMAGE
    for _ in range(4):
        if time.monotonic() >= deadline:
            raise ValueError('Logo bağlantısı zaman aşımına uğradı.')
        u, host, ip = public_target(url)
        conn = PinnedConnection(host, u.port or (443 if u.scheme == 'https' else 80), ip, u.scheme == 'https')
        conn.timeout = min(8, max(1, deadline-time.monotonic()))
        try:
            conn.request('GET', (u.path or '/') + ('?' + u.query if u.query else ''), headers={
                'User-Agent': 'KongrePusulasi/1.7.1', 'Accept': 'text/html' if html else 'image/png,image/jpeg,image/webp,image/x-icon',
                'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                target = response.getheader('Location')
                if not target: raise ValueError('Logo yönlendirmesi geçersiz.')
                url = urljoin(url, target)
                continue
            if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                raise ValueError('Kongre sitesindeki görsel alınamadı.')
            mime = response.getheader('Content-Type', '').split(';')[0].lower()
            if html and mime not in ('text/html', 'application/xhtml+xml'):
                raise ValueError('Kongre sitesi HTML sayfası döndürmedi.')
            raw = bytearray()
            while len(raw) <= maximum:
                if time.monotonic() >= deadline: raise ValueError('Logo bağlantısı zaman aşımına uğradı.')
                chunk = response.read(min(32768, maximum + 1 - len(raw)))
                if not chunk: break
                raw.extend(chunk)
            if len(raw) > maximum: raise ValueError('Logo kaynağı boyut sınırını aşıyor.')
            return bytes(raw), url
        except (OSError, http.client.HTTPException):
            raise ValueError('Kongrenin web sitesine şu anda ulaşılamadı. Logo dosyası yükleyebilirsiniz.') from None
        finally:
            conn.close()
    raise ValueError('Logo için çok fazla yönlendirme var.')

def logo_candidates(html, page_url):
    """Prefer header branding; never mistake sponsor/indexing or arbitrary OG photos for logos."""
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []
    for image in soup.find_all('img'):
        src = image.get('src') or image.get('data-src') or ''
        description = ' '.join([src, image.get('alt', ''), image.get('id', ''), ' '.join(image.get('class', []))]).lower()
        parent = image.find_parent(['header', 'nav'])
        brand_parent = image.find_parent(class_=re.compile(r'logo|brand', re.I))
        logo_filename = re.search(r'/(?:logo|logo2|logo-dark|logo-light)(?:[._-]|$)', unquote(src), re.I)
        if not (logo_filename or brand_parent or (parent and ('logo' in description or 'brand' in description))):
            continue
        if any(word in description for word in ('sponsor', 'supporter', 'scopus', 'ieee', 'index', 'thomson')):
            continue
        # A university portal's global logo is its site identity, not the event emblem.
        kind = 'site_icon' if 'logo_tr' in description or 'logo_en' in description else 'website'
        priority = (80 if brand_parent else 60 if parent else 40) + (20 if logo_filename else 0)
        candidates.append((priority, urljoin(page_url, src), kind))
    for link in soup.find_all('link', href=True):
        rel = ' '.join(link.get('rel', [])).lower()
        if 'icon' in rel:
            candidates.append((20 if 'apple-touch' in rel else 10, urljoin(page_url, link['href']), 'site_icon'))
    seen = set(); result = []
    for _, url, kind in sorted(candidates, key=lambda x: -x[0]):
        if urlsplit(url).scheme not in ('http', 'https') or url in seen: continue
        if urlsplit(url).path.lower().endswith('.svg'): continue
        seen.add(url); result.append((url, kind))
    return result[:5]

def discover_logo(website):
    deadline = time.monotonic() + 30
    html, final_url = fetch_asset(website, html=True, deadline=deadline)
    for url, kind in logo_candidates(html, final_url):
        try:
            raw, source_url = fetch_asset(url, deadline=deadline)
            return raster_logo(raw), source_url, kind
        except ValueError:
            if time.monotonic() >= deadline: break
    raise ValueError('Sitede kullanılabilir bir logo bulunamadı. Logo dosyasını yükleyebilirsiniz.')

@lru_cache(maxsize=128)
def logo_surface(image):
    """Light artwork with transparency needs a navy surface, without altering the logo."""
    if not image: return 'light'
    with Image.open(io.BytesIO(image)) as bitmap:
        bitmap.thumbnail((64, 64))
        pixels = list(bitmap.convert('RGBA').get_flattened_data())
    visible = [p for p in pixels if p[3] > 64]
    if visible and len(visible) < len(pixels)*.92:
        brightness = sum(.2126*p[0]+.7152*p[1]+.0722*p[2] for p in visible)/len(visible)
        if brightness > 160: return 'dark'
    return 'light'

class LogoService:
    def __init__(self, db): self.db = db

    @staticmethod
    def public(row):
        if not row: return None
        return {'status': row.status, 'source': row.source, 'source_url': row.source_url,
                'website': row.website, 'updated_at': row.updated_at, 'surface': logo_surface(row.image),
                'url': '/api/congresses/' + row.congress_id + '/logo?v=' + hashlib.sha256(row.image).hexdigest()[:16] if row.status == 'ready' else None}

    def all(self):
        with self.db.session() as session:
            # Logo bytes are fetched only by the image endpoint, not placed in /state JSON.
            return {row.congress_id: self.public(row) for row in session.scalars(select(CongressLogo))}

    def image(self, cid):
        with self.db.session() as session:
            row = session.get(CongressLogo, cid)
            if not row or row.status != 'ready': raise NotFoundError('Bu kongre için logo yok.')
            return row.image

    def report_image(self, report):
        review = report.get('review')
        if review:
            try: return self.image(review['saved']['id'])
            except NotFoundError: return None
        website = report.get('analysis', {}).get('metadata', {}).get('website') or next(
            (s.get('url') for s in report.get('sources', []) if s.get('kind') == 'url'), '')
        if not website: return None
        # Unreviewed reports reuse branding only for exactly the same event URL.
        with self.db.session() as session:
            for congress, logo in session.execute(select(Congress,CongressLogo).join(CongressLogo,Congress.id==CongressLogo.congress_id).where(CongressLogo.status=='ready',~Congress.id.in_(select(CongressDeletion.congress_id)))):
                if json.loads(congress.metadata_json).get('website','').rstrip('/') == website.rstrip('/'):
                    return logo.image
        return None

    def upload(self, cid, content):
        try: raw = base64.b64decode(content, validate=True)
        except ValueError: raise ValueError('Logo dosyasının kodlaması okunamadı.') from None
        image = raster_logo(raw)
        with self.db.session(write=True) as session:
            congress = require_active(session, cid)
            row = session.get(CongressLogo, cid) or CongressLogo(congress_id=cid)
            row.image, row.status, row.source, row.source_url = image, 'ready', 'upload', ''
            row.website, row.updated_at = json.loads(congress.metadata_json).get('website', ''), now()
            session.add(row);session.flush()
            return {'logo': self.public(row)}

    def hide(self, cid, restore=False):
        with self.db.session(write=True) as session:
            require_active(session, cid)
            row = session.get(CongressLogo, cid) or CongressLogo(congress_id=cid, image=b'', source='', source_url='', website='')
            if restore and not row.image: raise ValueError('Geri getirilecek logo yok.')
            row.status, row.updated_at = ('ready' if restore else 'hidden'), now()
            session.add(row);session.flush()
            return {'logo': self.public(row)}

    def discover(self, cid, force=False):
        with self.db.session() as session:
            congress = require_active(session, cid)
            metadata = json.loads(congress.metadata_json);website = metadata.get('website', '')
            row = session.get(CongressLogo, cid)
            stamp = row.updated_at if row else None
            if not force and row:
                cached = row.website == website and (datetime.now(timezone.utc)-datetime.fromisoformat(row.updated_at)).total_seconds() < 86400
                if row.status == 'hidden' or row.source == 'upload' or cached:
                    return {'logo': self.public(row)}
            if not website: raise ValueError('Önce kongrenin web adresini kaydedin veya bir logo dosyası yükleyin.')
        message = ''
        try: image, source_url, kind = discover_logo(website)
        except ValueError as error: image, source_url, kind, message = b'', '', '', str(error)
        with self.db.session(write=True) as session:
            congress = require_active(session, cid)
            current = session.get(CongressLogo, cid)
            # An upload/hide/website edit made during retrieval always wins.
            if (current.updated_at if current else None) != stamp or json.loads(congress.metadata_json).get('website', '') != website:
                raise ConflictError('Logo veya web adresi değişti; sayfayı yenileyin.')
            if not image and current and current.image:
                return {'logo': self.public(current), 'message': message}
            row = current or CongressLogo(congress_id=cid)
            row.image, row.source_url, row.source = image, source_url, kind
            row.status, row.website, row.updated_at = ('ready' if image else 'missing'), website, now()
            session.add(row);session.flush()
            return {'logo': self.public(row), 'message': message}
