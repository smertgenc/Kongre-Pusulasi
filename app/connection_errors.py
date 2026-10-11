"""Classify actual HTTP/transport failures without exposing credentials or bodies."""
import socket
import ssl
import httpx
from desktop.logging_setup import event

MESSAGES = {
    'AUTH_ERROR':'API anahtarı geçersiz veya yetkilendirme başarısız.',
    'ACCESS_DENIED':'API erişimi reddedildi. API anahtarının yetkilerini kontrol edin.',
    'RATE_LIMIT':'API kota/rate limit sınırına ulaşıldı.',
    'TIMEOUT':'API bağlantısı zaman aşımına uğradı.',
    'SSL_ERROR':'SSL sertifika doğrulama hatası.',
    'DNS_ERROR':'Servis adresi çözümlenemedi.',
    'CONNECTION_ERROR':'API sunucusuna bağlantı kurulamadı.',
    'PROXY_ERROR':'Proxy üzerinden API bağlantısı kurulamadı.',
    'SERVICE_UNAVAILABLE':'API hizmeti şu anda kullanılamıyor. Daha sonra tekrar deneyin.',
    'HTTP_ERROR':'API isteği kabul edilmedi.',
    'UNKNOWN_ERROR':'Genel bir bağlantı hatası oluştu. Teknik ayrıntılar log dosyasına kaydedildi.',
}

class ConnectionFailure(ValueError):
    def __init__(self, service, code, *, status=None, message=None):
        self.service=service; self.code=code; self.http_status=status
        super().__init__(service+': '+(message or MESSAGES[code]))

def exception_chain(error):
    seen=set(); pending=[error]
    while pending and len(seen)<12:
        current=pending.pop(0)
        if id(current) in seen: continue
        seen.add(id(current)); yield current
        # HTTPX/httpcore wrap socket and SSL errors; inspect the actual cause first.
        nested=current.__cause__ or current.__context__
        if nested is not None: pending.append(nested)

def transport_code(error):
    chain=list(exception_chain(error))
    if any(isinstance(e,httpx.ProxyError) for e in chain): return 'PROXY_ERROR'
    if any(isinstance(e,(httpx.TimeoutException,TimeoutError)) for e in chain): return 'TIMEOUT'
    if any(isinstance(e,ssl.SSLError) for e in chain): return 'SSL_ERROR'
    if any(isinstance(e,socket.gaierror) for e in chain): return 'DNS_ERROR'
    # Some transports preserve only the OpenSSL reason, without the SSL cause.
    if any(isinstance(e,httpx.ConnectError) and 'CERTIFICATE_VERIFY_FAILED' in str(e) for e in chain): return 'SSL_ERROR'
    if any(isinstance(e,(httpx.NetworkError,ConnectionError)) for e in chain): return 'CONNECTION_ERROR'
    return 'UNKNOWN_ERROR'

def transport_failure(service, error):
    code=transport_code(error)
    event('api_transport_failed',error,code=code,service=service)
    return ConnectionFailure(service,code)

def status_code(status):
    if status==401: return 'AUTH_ERROR'
    if status==403: return 'ACCESS_DENIED'
    if status in (402,429,432,433): return 'RATE_LIMIT'
    if status==407: return 'PROXY_ERROR'
    if status in (408,504): return 'TIMEOUT'
    if status>=500: return 'SERVICE_UNAVAILABLE'
    return 'HTTP_ERROR'

def status_failure(service, status):
    code=status_code(status)
    event('api_http_failed',code=code,http_status=status,service=service)
    return ConnectionFailure(service,code,status=status)
