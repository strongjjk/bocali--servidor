"""Bocali v1.0 WSGI application.

Transport-neutral HTTP adapter. Production runs behind HTTPS with Waitress.
Local/LAN modes remain available for development and Epson testing.
"""
from __future__ import annotations
import hashlib
import hmac
import ipaddress
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from backend import Database, Problem, SESSION_TTL
from geocoding_service import geocode
from cep_service import lookup_cep
from mercadopago_service import MercadoPagoService, MercadoPagoError

ROOT = Path(__file__).resolve().parent
APP_NAME = 'Bocali'
APP_VERSION = '1.0-rc4'
GATE_TTL = 8 * 60 * 60
MAX_JSON = 2 * 1024 * 1024
STATIC = frozenset({
    'index.html', 'loader.js', 'connected.js', 'connected.css', 'app.js',
    'domain.js', 'delivery.js', 'delivery-ui.js', 'order-flow.js', 'styles.css',
    'delivery.css', 'icon.svg', 'manifest.webmanifest', 'service-worker.js', 'native-print.js',
    'pilot.js', 'pilot.css', 'setup.js', 'operations.js', 'operations.css', 'neighborhood-delivery.js', 'neighborhood-delivery.css',
})
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; "
       "frame-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
       "form-action 'self'; worker-src 'self'")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def load_environment(path: Path | None = None) -> None:
    """Optional local file. Values are literal, never executed or interpolated."""
    path = path or ROOT / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not (key.startswith('PEDE_') or key.startswith('BOCALI_') or key in ('PORT', 'GEOAPIFY_API_KEY')):
            continue
        os.environ.setdefault(key, value.strip())


@dataclass(frozen=True)
class Settings:
    origin: str
    data_dir: Path
    mode: str = 'local'
    pilot_code: str = ''
    secret_key: str = ''
    setup_token: str = ''
    demo_addresses: bool = True
    enable_pdf: bool = False
    mp_access_token: str = ''
    mp_public_key: str = ''
    mp_webhook_secret: str = ''
    mp_environment: str = 'test'

    @classmethod
    def from_env(cls):
        def env(primary, legacy=None, default=''):
            value=os.environ.get(primary)
            if value is None and legacy: value=os.environ.get(legacy)
            return default if value is None else value
        mode=env('BOCALI_MODE','PEDE_MODE','local')
        origin=env('BOCALI_PUBLIC_ORIGIN','PEDE_PUBLIC_ORIGIN','http://127.0.0.1:8000').rstrip('/')
        root=Path(env('BOCALI_DATA_DIR','PEDE_DATA_DIR',str(ROOT/'data'))).resolve()
        # Production is public: legacy pilot codes are ignored. The protected mode
        # remains available for staging/internal previews.
        pilot_code = '' if mode == 'production' else env('BOCALI_PILOT_CODE','PEDE_PILOT_CODE','')
        settings=cls(origin,root,mode,
            pilot_code,
            env('BOCALI_SECRET_KEY','PEDE_SECRET_KEY',''),
            env('BOCALI_SETUP_TOKEN','PEDE_SETUP_TOKEN',''),
            env('BOCALI_DEMO_ADDRESSES','PEDE_DEMO_ADDRESSES','1')=='1',
            env('BOCALI_ENABLE_PDF','PEDE_ENABLE_PDF','0')=='1',
            env('BOCALI_MP_ACCESS_TOKEN',None,''),
            env('BOCALI_MP_PUBLIC_KEY',None,''),
            env('BOCALI_MP_WEBHOOK_SECRET',None,''),
            env('BOCALI_MP_ENVIRONMENT',None,'test').strip().lower())
        settings.validate()
        volume=os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
        if mode in ('production','protected') and os.environ.get('RAILWAY_ENVIRONMENT_ID'):
            if not volume or not root.is_relative_to(Path(volume).resolve()):
                raise ValueError('Configure um volume Railway no diretorio de dados antes de iniciar.')
        return settings

    def validate(self):
        p=urlsplit(self.origin)
        if (self.mode not in ('local','lan','production','protected') or p.scheme not in ('http','https')
                or not p.hostname or p.username or p.password or p.path or p.query or p.fragment):
            raise ValueError('BOCALI_PUBLIC_ORIGIN deve ser uma origem valida, sem caminho.')
        if self.mode=='local' and p.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Modo local limitado ao computador. Use lan ou production.')
        if self.mode=='lan':
            if p.scheme!='http': raise ValueError('O teste LAN usa HTTP apenas na rede interna.')
            try: addr=ipaddress.ip_address(p.hostname)
            except ValueError: raise ValueError('No modo lan, use o IPv4 privado do computador.')
            if addr.version!=4 or not addr.is_private: raise ValueError('No modo lan, use somente um IPv4 privado.')
        if self.mode in ('production','protected') and p.scheme!='https':
            raise ValueError('O Bocali publicado exige HTTPS.')
        if self.mode in ('production','protected') and len(self.secret_key)<32:
            raise ValueError('BOCALI_SECRET_KEY deve ter pelo menos 32 caracteres.')
        if self.pilot_code and (len(self.pilot_code)<24 or len(self.secret_key)<32):
            raise ValueError('Gere BOCALI_PILOT_CODE (24+) e BOCALI_SECRET_KEY (32+).')
        if self.setup_token and len(self.setup_token)<32:
            raise ValueError('BOCALI_SETUP_TOKEN deve ter pelo menos 32 caracteres.')
        if not self.data_dir.is_absolute(): raise ValueError('O diretorio de dados deve ser absoluto.')
        # Checkout Pro + Pix server-side require the Access Token. Public Key is kept
        # as an optional deployment field for future native/tokenized card flows.
        if self.mp_environment not in ('test','production'): raise ValueError('BOCALI_MP_ENVIRONMENT deve ser test ou production.')

    @property
    def secure(self): return self.origin.startswith('https://')

    @property
    def production(self): return self.mode in ('production','protected')

    @property
    def db_path(self): return self.data_dir/'bocali.sqlite3'


class RateLimiter:
    """Single-process limiter. Never trust forwarded client addresses by default."""
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = threading.Lock()

    def hit(self, identity, key, maximum, window=900):
        now = time.monotonic()
        with self.lock:
            q = self.entries[(identity, key)]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= maximum:
                raise Problem('Muitas tentativas. Aguarde antes de tentar novamente.', 429)
            q.append(now)
            if len(self.entries) > 10000:
                for k in list(self.entries):
                    if not self.entries[k] or self.entries[k][-1] <= now - 3600:
                        del self.entries[k]


class Request:
    def __init__(self, environ):
        self.env = environ
        self.path = environ.get('PATH_INFO', '/')
        self.method = environ.get('REQUEST_METHOD', 'GET').upper()
        self.cookies = SimpleCookie()
        try:
            self.cookies.load(environ.get('HTTP_COOKIE', ''))
        except Exception:
            self.cookies = SimpleCookie()

    def header(self, name):
        key = name.upper().replace('-', '_')
        return self.env.get(key if key in ('CONTENT_TYPE', 'CONTENT_LENGTH') else 'HTTP_' + key, '')

    def cookie(self, name):
        item = self.cookies.get(name)
        return item.value if item else ''

    def query(self, name):
        values=parse_qs(self.env.get('QUERY_STRING',''),keep_blank_values=True).get(name,[])
        return values[0] if values else ''

    def body(self, content_type='application/json', maximum=MAX_JSON):
        if self.header('Content-Type').split(';')[0].strip() != content_type:
            raise Problem('Formato de envio incorreto.', 415)
        try:
            length = int(self.header('Content-Length') or 0)
        except ValueError:
            raise Problem('Tamanho invalido.')
        if length <= 0 or length > maximum:
            raise Problem('Envio vazio ou acima do limite.', 413)
        raw = self.env['wsgi.input'].read(length)
        if len(raw) != length:
            raise Problem('Envio incompleto.')
        return raw

    def json(self):
        try:
            data = json.loads(self.body(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (UnicodeDecodeError, ValueError):
            raise Problem('JSON invalido.')
        if not isinstance(data, dict):
            raise Problem('JSON invalido.')
        return data


class PilotApp:
    def __init__(self, settings: Settings, db: Database | None = None):
        settings.validate()
        self.settings = settings
        self.db = db or Database(settings.db_path, ROOT/'seed.json', settings.demo_addresses, seed_catalog=(settings.mode!='production'))
        self.mp = MercadoPagoService(settings.mp_access_token, settings.mp_public_key, settings.mp_webhook_secret)
        self.limiter = RateLimiter()
        self.setup_lock = threading.Lock()
        self.started = time.time()
        self.gate_key = hmac.new(settings.secret_key.encode(),
            ('pede-gate-v05:' + digest(settings.pilot_code)).encode(), hashlib.sha256).digest()

    def gate_value(self):
        value = f'{int(time.time())}.{secrets.token_urlsafe(24)}'
        return value + '.' + hmac.new(self.gate_key, value.encode(), hashlib.sha256).hexdigest()

    def gate_valid(self, value):
        if not self.settings.pilot_code:
            return True
        try:
            stamp, nonce, signature = value.split('.')
            age = time.time() - int(stamp)
            expected = hmac.new(self.gate_key, (stamp + '.' + nonce).encode(), hashlib.sha256).hexdigest()
            return 0 <= age < GATE_TTL and hmac.compare_digest(signature, expected)
        except (ValueError, TypeError):
            return False

    def cookie(self, name, value, ttl):
        c = SimpleCookie()
        c[name] = value
        c[name]['path'] = '/'
        c[name]['httponly'] = True
        c[name]['samesite'] = 'Lax'
        c[name]['max-age'] = ttl if value else 0
        if self.settings.secure:
            c[name]['secure'] = True
        return ('Set-Cookie', c.output(header='').strip())

    def owner_missing(self):
        # The one-time Cantinho setup is a legacy/local migration path. Official
        # production uses normal merchant registration and must never block the homepage.
        if self.settings.mode == 'production':
            return False
        with self.db.connect() as c:
            return not bool(c.execute('SELECT 1 FROM members WHERE store_id=?', ('cantinho',)).fetchone())

    def session(self, req, required=False):
        result = self.db.session(req.cookie('pede_session'))
        if required and not result:
            raise Problem('Entre na sua conta para continuar.', 401)
        return result

    def limit(self, req, key, maximum, window=900):
        self.limiter.hit(req.env.get('REMOTE_ADDR', 'unknown'), key, maximum, window)

    def asset(self, name):
        if name not in STATIC | {'pilot.html', 'setup.html'}:
            raise Problem('Recurso nao encontrado.', 404)
        mime = {'.js':'text/javascript', '.css':'text/css', '.webmanifest':'application/manifest+json'}.get(
            Path(name).suffix, mimetypes.guess_type(name)[0] or 'application/octet-stream')
        return 200, (ROOT / name).read_bytes(), [('Content-Type', mime + '; charset=utf-8')]

    def bootstrap(self, session):
        data = self.db.bootstrap(session)
        mode='producao' if self.settings.production else ('desenvolvimento-rede-local' if self.settings.mode=='lan' else 'desenvolvimento-local')
        data.update(version=APP_VERSION,appName=APP_NAME,mode=mode,pilotGate=bool(self.settings.pilot_code),publicOrigin=self.settings.origin,
            setupRequired=self.owner_missing() and bool(self.settings.setup_token),
            payments={'provider':'mercadopago','enabled':self.mp.enabled,'publicKey':self.settings.mp_public_key if self.mp.enabled else '',
                      'webhookReady':bool(self.settings.mp_webhook_secret),'environment':self.settings.mp_environment,
                      'cardFlow':'custom-tab','pixFlow':'server-qr'})
        return data

    def operations(self, session):
        boot = self.bootstrap(session)
        if not boot['managedStores']:
            raise Problem('Recurso exclusivo do lojista.', 403)
        return {
            'version':APP_VERSION, 'appName':APP_NAME, 'mode':boot['mode'], 'gateEnabled':boot['pilotGate'],
            'httpsConfigured':self.settings.secure, 'origin':self.settings.origin,
            'databaseConnected':True, 'payments':('mercadopago' if self.mp.enabled else 'not-configured'), 'printing':'android-bridge-or-browser',
            'geocodingConfigured':bool(os.environ.get('GEOAPIFY_API_KEY')),
            'geocodingValidated':False, 'demoAddresses':self.db.allow_samples,
            'pdfEnabled':self.settings.enable_pdf, 'emailRecovery':False,
            'backupToolAvailable':True, 'automaticBackupConfigured':False,
            'stores':[{'id':s['id'], 'name':s['name'], 'open':s['open'],
                'products':sum(p['storeId']==s['id'] for p in boot['products']),
                'deliveryAreas':sum(r.get('active',True) for r in s.get('deliveryConfig',{}).get('neighborhoodRates',[])) or sum(z['active'] and z['kind']=='delivery' for z in s.get('deliveryConfig',{}).get('zones',[]))}
                for s in boot['stores'] if s['id'] in boot['managedStores']],
            'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }

    def validate_mp_webhook(self, req, data_id):
        secret=self.settings.mp_webhook_secret
        if not secret: raise Problem('Webhook do Mercado Pago ainda não configurado.',503)
        signature=req.header('X-Signature'); request_id=req.header('X-Request-Id')
        parts={}
        for piece in signature.split(',') if signature else []:
            key,sep,value=piece.strip().partition('=')
            if sep: parts[key]=value
        ts=parts.get('ts',''); received=parts.get('v1','')
        if not ts or not received or not request_id or not data_id: raise Problem('Assinatura de webhook ausente.',401)
        manifest=f'id:{data_id};request-id:{request_id};ts:{ts};'
        expected=hmac.new(secret.encode('utf-8'),manifest.encode('utf-8'),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received,expected): raise Problem('Assinatura de webhook inválida.',401)

    def dispatch(self, req):
        cfg = self.settings
        expected_host=urlsplit(cfg.origin).netloc.lower()
        host = req.header('Host').lower()
        # Hosting health checks may use an internal Host header. /healthz exposes only
        # a boolean readiness signal, so allow that path before strict public-Host checks.
        health_check = req.path == '/healthz'
        if host != expected_host and not health_check:
            raise Problem('Host nao autorizado.', 403)
        if req.method not in ('GET','HEAD','POST'):
            raise Problem('Metodo nao permitido.',405)
        if req.method=='POST' and req.path=='/api/webhooks/mercadopago':
            if not self.mp.enabled: raise Problem('Pagamentos ainda não configurados.',503)
            data_id=req.query('data.id')
            self.validate_mp_webhook(req,data_id)
            payment=self.mp.get_payment(data_id)
            order_id=payment.get('external_reference','')
            if order_id: self.db.apply_payment(order_id,payment,'mercadopago:webhook')
            return 200,{'ok':True},[]
        if req.method in ('GET','HEAD') and req.path == '/healthz':
            with self.db.connect() as c:
                c.execute('SELECT 1 FROM stores LIMIT 1').fetchone()
            return 200, {'ok':True}, []
        if req.method == 'POST':
            if req.header('Origin') != cfg.origin or (req.header('X-Bocali-Request')!='1' and req.header('X-Pede-Request')!='1'):
                raise Problem('Origem ou requisicao nao autorizada.', 403)
            self.limit(req, 'all-writes', 400, 60)
            if req.path == '/api/pilot-unlock':
                self.limit(req, 'gate', 15)
                p = req.json()
                value = p.get('code', '')
                if not isinstance(value, str) or not cfg.pilot_code or not hmac.compare_digest(digest(value), digest(cfg.pilot_code)):
                    raise Problem('Codigo de acesso invalido.', 401)
                return 200, {'ok':True}, [self.cookie('pede_pilot', self.gate_value(), GATE_TTL)]
        gate_ok = self.gate_valid(req.cookie('pede_pilot'))
        if not gate_ok:
            if req.method in ('GET', 'HEAD') and req.path in ('/', '/index.html', '/pilot', '/setup'):
                return self.asset('pilot.html')
            if req.method in ('GET', 'HEAD') and req.path in ('/pilot.js', '/pilot.css', '/icon.svg'):
                return self.asset(req.path[1:])
            return 403, {'error':'Acesso ao piloto bloqueado ou expirado.', 'gateRequired':True}, []
        if req.method in ('GET', 'HEAD'):
            if req.path == '/api/bootstrap':
                return 200, self.bootstrap(self.session(req)), []
            if req.path == '/api/pilot-status':
                return 200, self.operations(self.session(req, True)), []
            if req.path == '/api/health':
                return 200, {'ok':True, 'version':APP_VERSION, 'appName':APP_NAME, 'mode':('production' if cfg.production else 'development'), 'pdf':cfg.enable_pdf, 'payments':self.mp.enabled,
                    'geocoding':bool(os.environ.get('GEOAPIFY_API_KEY')), 'demoAddresses':self.db.allow_samples}, []
            if req.path == '/payment-return':
                # Browser checkout return. Payment status is never trusted from this URL; the
                # customer order screen reads the server state updated by signed webhooks/polling.
                return 303, b'', [('Location','/#/pedidos')]
            if req.path == '/setup':
                if not cfg.setup_token or not self.owner_missing():
                    return 303, b'', [('Location','/#/conta')]
                return self.asset('setup.html')
            if req.path in ('/', '/index.html') and self.owner_missing() and cfg.setup_token:
                return 303, b'', [('Location','/setup')]
            if req.path == '/pilot':
                if cfg.mode == 'production':
                    return 303, b'', [('Location','/')]
                return self.asset('pilot.html')
            name = 'index.html' if req.path == '/' else req.path[1:]
            if name not in STATIC:
                raise Problem('Recurso nao encontrado.', 404)
            return self.asset(name)
        auth = req.path in ('/api/register','/api/login','/api/setup-owner')
        session = self.session(req, required=not auth)
        if not auth and not hmac.compare_digest(req.header('X-CSRF-Token'), session['csrf']):
            raise Problem('Sessao alterada. Atualize a pagina.', 403)
        if req.path == '/api/import-pdf':
            if not cfg.enable_pdf:
                raise Problem('Leitura de PDF desativada neste ambiente. Use texto colado enquanto validamos o importador.', 503)
            self.limit(req, 'pdf', 12)
            if not self.db.bootstrap(session)['managedStores']:
                raise Problem('Recurso exclusivo do lojista.', 403)
            raw = req.body('application/pdf', 10 * 1024 * 1024)
            # Do not pass hosting secrets to the PDF subprocess.
            safe_env = {k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP')}
            try:
                proc = subprocess.run([sys.executable, str(ROOT/'pdf_service.py')], input=raw,
                    capture_output=True, timeout=25, cwd=ROOT, env=safe_env)
                data = json.loads(proc.stdout) if proc.returncode == 0 else {'error':'Falha ao ler o PDF.'}
            except (subprocess.TimeoutExpired, ValueError):
                data = {'error':'O PDF excedeu os limites de leitura.'}
            return (422 if 'error' in data else 200), data, []
        p=req.json()
        token=req.cookie('pede_session')
        if req.path=='/api/payment':
            if not self.mp.enabled: raise Problem('Pix/cartão ainda não foram configurados neste servidor.',503)
            self.limit(req,'payment',30,60)
            order_id=p.get('orderId'); idem=p.get('idempotencyKey'); form=p.get('formData')
            if not isinstance(idem,str) or len(idem)<16 or len(idem)>100: raise Problem('Identificador do pagamento inválido.')
            order=self.db.payment_target(session['user']['id'],order_id)
            if order.get('payment')!='pix':
                raise Problem('Pagamento com cartão usa o checkout seguro externo do Mercado Pago.',409)
            method=form.get('payment_method_id') if isinstance(form,dict) else None
            if method!='pix': raise Problem('Este pedido foi criado para pagamento Pix.',409)
            # If a Pix attempt is still active, return the same provider payment instead of
            # creating another charge/QR code. This reduces accidental double payment.
            existing=str(order.get('paymentProviderId') or '')
            if order.get('paymentStatus')=='pending' and existing:
                current=self.mp.get_payment(existing)
                if current.get('external_reference') and current['external_reference']!=order['id']:
                    raise Problem('Referência de pagamento divergente.',502)
                updated=self.db.apply_payment(order['id'],current,'mercadopago:refresh')
                if current.get('status') in ('approved','pending','in_process'):
                    return 200,{'order':updated,'payment':current,'reused':True},[]
                order=self.db.payment_target(session['user']['id'],order_id)
            payment=self.mp.create_payment(order,form,idem,cfg.origin+'/api/webhooks/mercadopago')
            if payment.get('external_reference') and payment['external_reference']!=order['id']:
                raise Problem('Referência de pagamento divergente.',502)
            updated=self.db.apply_payment(order['id'],payment,'mercadopago:api')
            return 200,{'order':updated,'payment':payment,'reused':False},[]
        if req.path=='/api/card-checkout':
            if not self.mp.enabled: raise Problem('Mercado Pago ainda não foi configurado neste servidor.',503)
            self.limit(req,'card-checkout',20,60)
            order=self.db.payment_target(session['user']['id'],p.get('orderId'))
            if order.get('payment')!='card': raise Problem('Este pedido não foi criado para pagamento com cartão.',409)
            if order.get('checkoutPreferenceUrl'):
                return 200,{'order':order,'checkoutUrl':order['checkoutPreferenceUrl'],'preferenceId':order.get('checkoutPreferenceId',''),'reused':True},[]
            return_mode=p.get('returnMode')
            if return_mode not in ('android','web'): raise Problem('Modo de retorno do pagamento inválido.')
            oid=order['id']
            if return_mode=='android':
                back={k:f'bocali://payment/{k}?orderId={oid}' for k in ('success','pending','failure')}
            else:
                back={k:f'{cfg.origin}/payment-return?result={k}&orderId={oid}' for k in ('success','pending','failure')}
            idem=hashlib.sha256(f'checkout-pro:{oid}'.encode('utf-8')).hexdigest()
            pref=self.mp.create_checkout_preference(order,idem,cfg.origin+'/api/webhooks/mercadopago',back)
            if pref.get('external_reference') and pref['external_reference']!=oid: raise Problem('Referência do checkout divergente.',502)
            checkout=(pref.get('sandbox_init_point') if cfg.mp_environment=='test' else pref.get('init_point')) or pref.get('init_point') or pref.get('sandbox_init_point')
            if not checkout or not checkout.startswith('https://'): raise Problem('Mercado Pago não retornou um checkout seguro.',502)
            saved=self.db.save_checkout_preference(session['user']['id'],oid,pref,checkout)
            return 200,saved,[]
        if req.path == '/api/setup-owner':
            self.limit(req, 'setup', 8)
            value = p.get('setupToken','')
            if not cfg.setup_token or not isinstance(value,str) or not hmac.compare_digest(digest(value), digest(cfg.setup_token)):
                raise Problem('Chave de configuracao invalida.', 403)
            with self.setup_lock:
                if not self.owner_missing():
                    raise Problem('O responsavel ja foi configurado.', 409)
                self.db.setup_owner(p.get('email'), p.get('password'), p.get('name'))
            token = self.db.login(p, token)
            return 201, {'ok':True}, [self.cookie('pede_session', token, SESSION_TTL)]
        if req.path == '/api/register':
            self.limit(req, 'register', 10)
            token = self.db.register(p, token)
            return 201, {'ok':True}, [self.cookie('pede_session', token, SESSION_TTL)]
        if req.path == '/api/login':
            self.limit(req, 'login', 20)
            token = self.db.login(p, token)
            return 200, {'ok':True}, [self.cookie('pede_session', token, SESSION_TTL)]
        uid = session['user']['id']
        if req.path in ('/api/logout','/api/pilot-lock'):
            self.db.logout(token)
            headers = [self.cookie('pede_session','',0)]
            if req.path.endswith('pilot-lock'):
                headers.append(self.cookie('pede_pilot','',0))
            return 200, {'ok':True}, headers
        if req.path=='/api/order-action' and p.get('action')=='status' and p.get('to')=='cancelled':
            target=self.db.refund_target(uid,p)
            if target:
                if not self.mp.enabled: raise Problem('O pedido está pago. Configure o Mercado Pago para estornar antes de cancelar.',503)
                key=hashlib.sha256(f"refund:{target['order']['id']}:{target['order']['revision']}".encode()).hexdigest()
                self.mp.refund_payment(target['providerId'],key)
                current=self.mp.get_payment(target['providerId'])
                if current.get('status') not in ('refunded','charged_back'):
                    # The provider accepted the refund request but has not reflected the final state yet.
                    # Keep the order visible until the webhook/refresh confirms the money movement.
                    raise Problem('Estorno solicitado. Aguarde a confirmação do Mercado Pago antes de cancelar novamente.',409)
                updated=self.db.apply_payment(target['order']['id'],current,'mercadopago:refund',target['reason'])
                return 200,{'order':updated,'refunded':True},[]
        actions = {'/api/favorites':self.db.favorites, '/api/catalog':self.db.catalog,
            '/api/quote':self.db.quote, '/api/orders':self.db.create_order, '/api/order-action':self.db.action}
        if req.path in actions:
            if req.path in ('/api/quote','/api/orders'):
                self.limit(req, req.path, 120)
            result = actions[req.path](uid,p)
            return (201 if req.path == '/api/orders' else 200), result, []
        if req.path == '/api/cep':
            self.limit(req, 'cep', 60, 60)
            code, data = lookup_cep(p.get('postcode'))
            return code, data, []
        if req.path == '/api/geocode':
            self.limit(req, 'geocode', 30)
            code, data = geocode(p.get('address'))
            if code == 200:
                data['results'] = self.db.add_geocodes(uid, data['results'])
            return code, data, []
        raise Problem('Recurso nao encontrado.', 404)

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            status, data, headers = self.dispatch(req)
        except (Problem,MercadoPagoError) as exc:
            status,data,headers=getattr(exc,'status',400),{'error':str(exc)},[]
        except Exception:
            # No request bodies, addresses, credentials, query strings or exception details in logs.
            print('Bocali request failed; check tests and storage health.', file=sys.stderr)
            status, data, headers = 500, {'error':'Nao foi possivel concluir. Confira seus pedidos antes de reenviar.'}, []
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        headers += [('Content-Length', str(len(data))), ('Cache-Control','no-store'),
            ('X-Content-Type-Options','nosniff'), ('X-Frame-Options','DENY'),
            ('Referrer-Policy','no-referrer'), ('Content-Security-Policy',CSP),
            ('X-Robots-Tag','noindex, nofollow, noarchive'),
            ('Permissions-Policy','camera=(), microphone=(), payment=()')]
        if not any(k.lower() == 'content-type' for k,v in headers):
            headers.append(('Content-Type','application/json; charset=utf-8'))
        if self.settings.secure:
            headers.append(('Strict-Transport-Security','max-age=86400'))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [b'' if req.method == 'HEAD' else data]


def create_app():
    load_environment()
    app = PilotApp(Settings.from_env())
    if app.settings.mode == 'protected' and app.owner_missing() and not app.settings.setup_token:
        raise ValueError('Configure PEDE_SETUP_TOKEN para criar o primeiro responsavel.')
    return app
