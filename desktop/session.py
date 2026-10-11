"""Per-launch WebView session; loopback alone is not authentication."""
import secrets
from http.cookies import SimpleCookie, CookieError
from urllib.parse import parse_qs
from starlette.responses import JSONResponse, RedirectResponse

def matches(supplied, expected):
    try: return secrets.compare_digest(supplied.encode('ascii'), expected.encode('ascii'))
    except UnicodeEncodeError: return False

class DesktopSession:
    def __init__(self, app, *, token, host):
        self.app, self.token, self.host = app, token, host
        self.cookie = secrets.token_urlsafe(32)
        self.used = False

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan': return await self.app(scope, receive, send)
        if scope['type'] != 'http':
            await send({'type':'websocket.close','code':1008}); return
        headers = dict(scope['headers'])
        host = headers.get(b'host', b'').decode('latin1')
        origin = headers.get(b'origin', b'').decode('latin1')
        async def reject():
            await JSONResponse({'error':'Masaüstü oturumu doğrulanamadı.'}, status_code=403,
                               headers={'Cache-Control':'no-store'})(scope, receive, send)
        if host != self.host or (origin and origin != 'http://'+self.host): return await reject()
        if scope['path'] == '/_desktop/start' and scope['method'] == 'GET':
            supplied = parse_qs(scope.get('query_string',b'').decode('ascii',errors='ignore')).get('token',[''])[0]
            if self.used or not matches(supplied, self.token): return await reject()
            self.used = True
            response = RedirectResponse('/', status_code=303, headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
            # HTTP only ever traverses this process's 127.0.0.1 socket.
            response.set_cookie('ahp_session', self.cookie, httponly=True, samesite='strict', path='/')
            return await response(scope, receive, send)
        try:
            cookies = SimpleCookie(); cookies.load(headers.get(b'cookie',b'').decode('latin1'))
            supplied = cookies['ahp_session'].value if 'ahp_session' in cookies else ''
        except CookieError: return await reject()
        if not matches(supplied, self.cookie): return await reject()
        return await self.app(scope, receive, send)
