#!/usr/bin/env python3
"""Local pilot server. Bind to loopback by default; not an Internet deployment."""
from __future__ import annotations
import argparse
import getpass
import hmac
import json
import mimetypes
import os
import runpy
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from backend import Database, Problem, SESSION_TTL
from geocoding_service import geocode

ROOT=Path(__file__).resolve().parent
MAX_JSON=2*1024*1024
STATIC={'index.html','loader.js','connected.js','connected.css','app.js','domain.js','delivery.js','delivery-ui.js','order-flow.js','styles.css','delivery.css','icon.svg','manifest.webmanifest','service-worker.js'}
LIMITS=defaultdict(deque); LIMIT_LOCK=threading.Lock()

class Handler(BaseHTTPRequestHandler):
    server_version='PedePilot/0.4'
    protocol_version='HTTP/1.1'

    def log_message(self,fmt,*args):
        # Never log request bodies, credentials, cookies, addresses or query strings.
        print(f'{self.command} {urlsplit(self.path).path}',file=sys.stderr)

    def reply(self,status,data,content_type='application/json; charset=utf-8',cookie=None,head=False):
        if not isinstance(data,bytes): data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(data)))
        if self.command=='POST':
            self.send_header('Connection','close'); self.close_connection=True
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer'); self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; worker-src 'self'")
        if cookie is not None:
            secure='; Secure' if self.server.secure_cookie else ''
            age=SESSION_TTL if cookie else 0
            self.send_header('Set-Cookie',f'pede_session={cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age={age}{secure}')
        self.end_headers()
        if not head:
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError): pass

    def host_ok(self):
        host=self.headers.get('Host','').lower()
        if host not in self.server.allowed_hosts: raise Problem('Host n\u00e3o autorizado.',403)

    def token(self):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception:return ''
        value=cookie.get('pede_session')
        return value.value if value else ''

    def session(self,required=False):
        s=self.server.db.session(self.token())
        if required and not s: raise Problem('Entre na sua conta para continuar.',401)
        return s

    def limit(self,key,max_count,window=900):
        now=time.monotonic(); ident=(self.client_address[0],key)
        with LIMIT_LOCK:
            q=LIMITS[ident]
            while q and q[0]<now-window:q.popleft()
            if len(q)>=max_count:raise Problem('Muitas tentativas. Aguarde antes de tentar novamente.',429)
            q.append(now)
            if len(LIMITS)>10000:
                for k in list(LIMITS):
                    if not LIMITS[k] or LIMITS[k][-1]<now-window:del LIMITS[k]

    def body(self,maximum,content_type):
        if self.headers.get('Transfer-Encoding'):raise Problem('Envio n\u00e3o suportado.',400)
        if self.headers.get('Content-Type','').split(';')[0]!=content_type:raise Problem('Formato de envio incorreto.',415)
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:raise Problem('Tamanho inv\u00e1lido.')
        if not 0<size<=maximum:raise Problem('Envio vazio ou acima do limite.',413)
        self.connection.settimeout(25); raw=self.rfile.read(size)
        if len(raw)!=size:raise Problem('Envio incompleto.')
        return raw

    def do_HEAD(self):self.do_GET(head=True)

    def do_GET(self,head=False):
        try:
            self.host_ok(); path=unquote(urlsplit(self.path).path)
            if path=='/api/health':
                try:import pypdf; pdf=True
                except ImportError:pdf=False
                return self.reply(200,{'ok':True,'version':'0.4','mode':'piloto-local','pdf':pdf,'geocoding':bool(os.environ.get('GEOAPIFY_API_KEY')),'demoAddresses':self.server.db.allow_samples},head=head)
            if path=='/api/bootstrap':return self.reply(200,self.server.db.bootstrap(self.session()),head=head)
            name='index.html' if path=='/' else path.lstrip('/')
            if name not in STATIC or path.startswith('//'):raise Problem('Recurso n\u00e3o encontrado.',404)
            target=ROOT/name
            if not target.is_file():raise Problem('Recurso n\u00e3o encontrado.',404)
            mime={'.js':'text/javascript','.css':'text/css','.webmanifest':'application/manifest+json'}.get(target.suffix,mimetypes.guess_type(name)[0] or 'application/octet-stream')
            return self.reply(200,target.read_bytes(),mime+'; charset=utf-8',head=head)
        except Problem as e:return self.reply(e.status,{'error':str(e)},head=head)
        except Exception:return self.reply(500,{'error':'Erro interno. Nada foi confirmado.'},head=head)

    def do_POST(self):
        try:
            self.host_ok(); path=urlsplit(self.path).path
            origin=self.headers.get('Origin')
            expected=self.server.public_origin or 'http://'+self.headers.get('Host','')
            if origin and origin!=expected:raise Problem('Origem n\u00e3o autorizada.',403)
            if self.headers.get('X-Pede-Request')!='1':raise Problem('Requisi\u00e7\u00e3o inv\u00e1lida.',403)
            self.limit('all-writes',400,60)
            auth_path=path in ('/api/login','/api/register')
            s=self.session(required=not auth_path)
            if not auth_path and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):raise Problem('Sess\u00e3o alterada. Atualize a p\u00e1gina.',403)
            if path=='/api/import-pdf':
                self.limit('pdf',12,900)
                if not self.server.db.bootstrap(s)['managedStores']:raise Problem('Recurso exclusivo do lojista.',403)
                raw=self.body(10*1024*1024,'application/pdf')
                try:
                    proc=subprocess.run([sys.executable,str(ROOT/'pdf_service.py')],input=raw,capture_output=True,timeout=25,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT)})
                    data=json.loads(proc.stdout) if proc.returncode==0 else {'error':'Falha ao ler o PDF.'}
                except (subprocess.TimeoutExpired,ValueError):data={'error':'O PDF excedeu os limites de leitura.'}
                return self.reply(422 if 'error' in data else 200,data)
            raw=self.body(MAX_JSON,'application/json')
            try:p=json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
            except (ValueError,UnicodeDecodeError):raise Problem('JSON inv\u00e1lido.')
            if not isinstance(p,dict):raise Problem('JSON inv\u00e1lido.')
            db=self.server.db
            if path=='/api/register':
                self.limit('register',10); token=db.register(p,self.token());return self.reply(201,{'ok':True},cookie=token)
            if path=='/api/login':
                self.limit('login',20); token=db.login(p,self.token());return self.reply(200,{'ok':True},cookie=token)
            uid=s['user']['id']
            if path=='/api/logout':db.logout(self.token());return self.reply(200,{'ok':True},cookie='')
            if path=='/api/favorites':return self.reply(200,db.favorites(uid,p))
            if path=='/api/catalog':return self.reply(200,db.catalog(uid,p))
            if path=='/api/quote':self.limit('quote',120);return self.reply(200,db.quote(uid,p))
            if path=='/api/orders':self.limit('order',100);return self.reply(201,db.create_order(uid,p))
            if path=='/api/order-action':return self.reply(200,db.action(uid,p))
            if path=='/api/geocode':
                self.limit('geocode',30)
                code,data=geocode(p.get('address'))
                if code==200:data['results']=db.add_geocodes(uid,data['results'])
                return self.reply(code,data)
            raise Problem('Recurso n\u00e3o encontrado.',404)
        except Problem as e:return self.reply(e.status,{'error':str(e)})
        except (TimeoutError,ConnectionError,OSError):self.close_connection=True;return self.reply(408,{'error':'Falha de conex\u00e3o. Consulte seus pedidos antes de reenviar.'})
        except Exception:
            # Deliberately avoid printing sensitive exception values.
            print('Internal request error; inspect local tests.',file=sys.stderr)
            return self.reply(500,{'error':'N\u00e3o foi poss\u00edvel concluir. Atualize antes de reenviar.'})


def make_server(host,port,db,allowed_hosts=None,public_origin=''):
    srv=ThreadingHTTPServer((host,port),Handler);srv.daemon_threads=True
    actual=srv.server_address[1]
    srv.allowed_hosts=set(allowed_hosts or [f'127.0.0.1:{actual}',f'localhost:{actual}'])
    srv.public_origin=public_origin.rstrip('/');srv.secure_cookie=public_origin.startswith('https://');srv.db=db
    return srv


def main():
    parser=argparse.ArgumentParser(description='Bocali v0.4 - piloto local; nao publicar diretamente na internet.')
    parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000')))
    parser.add_argument('--db',default=os.environ.get('PEDE_DB',str(ROOT/'data/pede.sqlite3')))
    parser.add_argument('--allow-host',action='append');parser.add_argument('--setup-owner',action='store_true')
    args=parser.parse_args()
    db=Database(args.db,ROOT/'seed.json',os.environ.get('PEDE_DEMO_ADDRESSES','1')=='1')
    if args.setup_owner:
        email=input('E-mail de TESTE do responsavel pelo Cantinho: ').strip()
        name=input('Nome de teste: ').strip() or 'Responsavel do piloto'
        pw=getpass.getpass('Crie uma senha de teste (12+ caracteres): ')
        if pw!=getpass.getpass('Repita a senha: '):raise SystemExit('As senhas nao conferem.')
        try:db.setup_owner(email,pw,name)
        except Problem as e:raise SystemExit(str(e))
        print('Responsavel criado. Nenhuma conta de outro sistema foi alterada.')
    if args.host not in ('127.0.0.1','localhost') and not args.allow_host:
        raise SystemExit('Para rede local, informe --allow-host IP:PORTA. HTTP nao deve transportar dados reais.')
    srv=make_server(args.host,args.port,db,args.allow_host,os.environ.get('PEDE_PUBLIC_ORIGIN',''))
    print(f'Bocali v0.4 em http://{args.host}:{args.port} - use apenas dados ficticios.')
    print('Pedidos persistem no banco local. Pagamentos continuam simulados.')
    try:srv.serve_forever()
    except KeyboardInterrupt:print('\nServidor encerrado.')
    finally:srv.server_close()

if __name__=='__main__':main()
