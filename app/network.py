"""Use approved system proxies and certificate roots; never disable TLS validation."""
import os
import ssl
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass
import httpx

OFFLINE_MESSAGE = 'Çevrimdışı mod etkin. Yerel AHP hesapları ve kayıtlar kullanılabilir; bu işlem internet gerektirir.'

class NetworkPolicyError(ValueError): pass

def require_online():
    if os.getenv('KONGRE_OFFLINE') == '1': raise NetworkPolicyError(OFFLINE_MESSAGE)

def proxy_for(url):
    require_online()
    scheme, host = urlsplit(url).scheme, urlsplit(url).hostname
    proxies = getproxies()
    proxy = proxies.get(scheme) or proxies.get('all')
    # getproxies reads actual environment/static OS proxies. Windows AutoDetect
    # and a PAC URL are settings, not proof that this request requires a proxy.
    # Never block a real API request merely because those flags are enabled.
    # Explicit proxies remain authoritative; failed requests do not retry direct.
    if proxy and proxy_bypass(host): return None
    if proxy and '://' not in proxy: proxy = 'http://' + proxy
    if proxy:
        try:
            parsed = urlsplit(proxy)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.port == 0: raise ValueError()
            httpx.URL(proxy)
        except (ValueError,httpx.InvalidURL):
            raise NetworkPolicyError('Proxy adresi desteklenmiyor. BT biriminiz HTTP/HTTPS proxy ayarını kontrol etmelidir.') from None
    return proxy

def tls_context():
    # Includes Windows system ROOT certificates, and SSL_CERT_FILE / SSL_CERT_DIR.
    try: return ssl.create_default_context()
    except (OSError,ssl.SSLError) as error:
        raise ssl.SSLError('Güvenilen sertifikalar yüklenemedi.') from error

def client_options(url):
    return {'proxy':proxy_for(url), 'verify':tls_context(), 'trust_env':False}

class ProxyConnection:
    """Streaming http.client-shaped adapter; existing source byte limits still apply."""
    def __init__(self, host, port, secure, proxy):
        self.base = ('https' if secure else 'http') + '://' + host + ':' + str(port)
        self.client = httpx.Client(proxy=proxy, verify=tls_context(), trust_env=False,
                                   timeout=10, follow_redirects=False)
        self.response = None
        self.buffer = bytearray()

    def request(self, method, path, headers):
        try:
            request = self.client.build_request(method, self.base+path, headers=headers)
            self.response = self.client.send(request, stream=True)
            self.status = self.response.status_code
            self.chunks = self.response.iter_raw(chunk_size=16384)
        except httpx.HTTPError as error:
            from app.connection_errors import transport_failure
            raise transport_failure('Web kaynağı',error) from None

    def getresponse(self): return self
    def getheader(self, key, default=None): return self.response.headers.get(key, default)
    def read(self, size):
        try:
            while len(self.buffer) < size:
                chunk = next(self.chunks, None)
                if chunk is None: break
                self.buffer.extend(chunk)
            data = bytes(self.buffer[:size]); del self.buffer[:size]
            return data
        except httpx.HTTPError as error:
            from app.connection_errors import transport_failure
            raise transport_failure('Web kaynağı',error) from None

    def close(self):
        if self.response is not None: self.response.close()
        self.client.close()
