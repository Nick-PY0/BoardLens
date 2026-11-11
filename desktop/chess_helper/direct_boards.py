"""Exact board reads supplied by opt-in connectors; no input injection."""
from __future__ import annotations
import json,threading,time,secrets,hmac
from .core import data_dir
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import chess,numpy as np
from .core import ordered_symbols
from .recognition import Read
from .vision import Detection


def exact_read(fen,bottom,identity,points=None,desktop_rect=None):
    board=chess.Board(fen)
    if not board.is_valid():raise ValueError('The connector sent an invalid position.')
    read=Read(ordered_symbols(board,bottom),np.ones(64),np.zeros((64,13)),bottom,board.turn,
              np.full((256,256,3),32,dtype=np.uint8),Detection(0,0,256,1))
    read.exact_fen=board.fen();read.source_id=identity;read.points=points;read.desktop_rect=desktop_rect
    return read


class BrowserReader:
    """Separate loopback service: reads and hints only, never settings or moves."""
    def __init__(self,port=8788):
        self.lock=threading.Lock();self.frames={};self.hints={};self.rejected_at=0.;self.token=secrets.token_urlsafe(32)
        secret=data_dir()/'browser-reader-key'
        if secret.is_file() and len(secret.read_text().strip())>=40:self.token=secret.read_text().strip()
        else:secret.write_text(self.token);secret.chmod(0o600)
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status,data):
                raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def authorized(self):
                accepted=hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+owner.token)
                if not accepted:owner.rejected_at=time.monotonic()
                return accepted
            def do_GET(self):
                if not self.authorized():return self.reply(401,{'error':'Pair the browser reader with its desktop key.'})
                with owner.lock:data=dict(owner.hints)
                self.reply(200,data)
            def do_POST(self):
                if not self.authorized():return self.reply(401,{'error':'Pair the browser reader first.'})
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<100_000:raise ValueError('Invalid board message size.')
                    payload=json.loads(self.rfile.read(length));owner.accept(payload);self.reply(200,{'ok':True})
                except (ValueError,TypeError,KeyError) as exc:self.reply(400,{'error':str(exc)})
        self.http=ThreadingHTTPServer(('127.0.0.1',port),Handler);self.http.daemon_threads=True;self.port=self.http.server_port
        self.thread=threading.Thread(target=lambda:self.http.serve_forever(poll_interval=.1),daemon=True);self.thread.start()
    def accept(self,payload):
        source=payload['source'];boards=payload['boards']
        if not isinstance(source,str) or len(source)>100 or not isinstance(boards,list) or len(boards)>3:raise ValueError('Expected at most three visible boards.')
        frames=[]
        for index,item in enumerate(boards):
            if not isinstance(item.get('white_bottom'),bool):raise ValueError('Missing orientation.')
            identity=f'browser:{source}:{index}'
            read=exact_read(item['fen'],item['white_bottom'],identity)
            read.visible_fen=item['fen']
            if item.get('exact') is False:read.exact_fen=None;read.turn_hint=item.get('turn_hint') if isinstance(item.get('turn_hint'),bool) else None
            frames.append((identity,'Browser reader',read,256,256))
        with self.lock:self.frames[source]=(time.monotonic(),frames)
    def reads(self):
        with self.lock:return [frame for at,frames in self.frames.values() if time.monotonic()-at<1.5 for frame in frames][:3]
    def connection_status(self):
        now=time.monotonic()
        with self.lock:
            latest=max((at for at,_ in self.frames.values()),default=0.)
            count=sum(len(frames) for at,frames in self.frames.values() if now-at<2)
        if self.rejected_at>latest and now-self.rejected_at<10:return 'Needs pairing · reconnect with the desktop key'
        if latest and now-latest<2:return f'Connected · {count} visible board'+('s' if count!=1 else '')
        return 'Disconnected · reader retries automatically' if latest else 'Waiting for the browser reader'

    def publish(self,hints):
        with self.lock:self.hints=hints
    def close(self):self.http.shutdown();self.http.server_close()
