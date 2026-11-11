"""Opt-in local companion server. HTTP threads never access Qt widgets."""
from __future__ import annotations
import hmac,json,secrets,socket,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class PhoneServer:
    def __init__(self,command,port=8789,host='0.0.0.0'):
        self.command=command
        self.token=secrets.token_urlsafe(32)
        self.code=f'{secrets.randbelow(1000000):06d}'
        self.lock=threading.Lock();self.snapshot={'boards':[],'status':'Starting companion…'}
        self.attempts={};self.clients={}
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send_json(self,status,value):
                self.send_bytes(status,json.dumps(value,allow_nan=False).encode(),'application/json')
            def send_bytes(self,status,data,mime):
                self.send_response(status);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers();self.wfile.write(data)
            def authorized(self):
                header=self.headers.get('Authorization','')
                good=hmac.compare_digest(header,'Bearer '+owner.token)
                if good:
                    with owner.lock:owner.clients[self.client_address[0]]=time.monotonic()
                return good
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/api/health':return self.send_json(200,{'app':'BoardLens','version':'2.13.0','pairing':True})
                if path in ('/api/state','/api/phone-position'):
                    if not self.authorized():return self.send_json(401,{'error':'Pair with the code shown on your computer.'})
                    with owner.lock:state=owner.snapshot
                    if path=='/api/phone-position':state={'phone_analysis':state.get('phone_analysis',{})}
                    return self.send_json(200,state)
                logos={'/branding/banner.png':'boardlens-banner.png','/branding/icon.png':'boardlens-icon.png'}
                if path in logos:
                    target=Path(__file__).parent/'assets/ui'/logos[path]
                    return self.send_bytes(200,target.read_bytes(),'image/png')
                names={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
                if path not in names:return self.send_json(404,{'error':'Not found'})
                target=Path(__file__).parent/'assets/phone'/names[path]
                mime={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[target.suffix[1:]]
                return self.send_bytes(200,target.read_bytes(),mime)
            def do_POST(self):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if length<=0 or length>8*1024*1024:raise ValueError('Request is too large or empty.')
                    if self.headers.get_content_type()!='application/json':raise ValueError('Use a JSON request.')
                    data=json.loads(self.rfile.read(length))
                    if not isinstance(data,dict):raise ValueError('Expected a JSON object.')
                    path=urlsplit(self.path).path
                    if path=='/api/pair':
                        ip=self.client_address[0];now=time.monotonic()
                        with owner.lock:
                            tries=[t for t in owner.attempts.get(ip,[]) if now-t<60]
                            if len(tries)>=8:return self.send_json(429,{'error':'Too many attempts. Wait a minute and try again.'})
                            tries.append(now);owner.attempts[ip]=tries
                        if not hmac.compare_digest(str(data.get('code','')),owner.code):return self.send_json(403,{'error':'That code does not match. Check the Phone section on your computer.'})
                        return self.send_json(200,{'token':owner.token})
                    if not self.authorized():return self.send_json(401,{'error':'Pair with this computer first.'})
                    if path!='/api/command':return self.send_json(404,{'error':'Not found'})
                    result=owner.command(data)
                    return self.send_json(200,{'ok':True,'result':result})
                except (ValueError,TypeError,json.JSONDecodeError) as exc:self.send_json(400,{'error':str(exc)})
                except TimeoutError:self.send_json(503,{'error':'The desktop is busy. Try again.'})
                except Exception as exc:self.send_json(409,{'error':str(exc)})
        class Server(ThreadingHTTPServer):
            daemon_threads=True
            allow_reuse_address=True
        self.http=Server((host,port),Handler)
        self.port=self.http.server_address[1]
        self.thread=threading.Thread(target=lambda:self.http.serve_forever(poll_interval=.1),daemon=True,name='BoardLens-phone')
        self.thread.start()

    def publish(self,state):
        with self.lock:self.snapshot=state

    def client_count(self):
        now=time.monotonic()
        with self.lock:return sum(now-t<8 for t in self.clients.values())

    def close(self):
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=1)
        self.token=secrets.token_urlsafe(32)


def local_addresses(port):
    addresses=[]
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1',80));addresses.append(sock.getsockname()[0])
    except OSError:pass
    try:addresses.extend(item[4][0] for item in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET,socket.SOCK_STREAM))
    except OSError:pass
    addresses=list(dict.fromkeys(ip for ip in addresses if not ip.startswith('127.') and ip!='0.0.0.0'))
    return [f'http://{ip}:{port}' for ip in addresses] or [f'http://127.0.0.1:{port}']
