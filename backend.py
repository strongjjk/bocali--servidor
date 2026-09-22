"""Bocali v1.0 core database.
Money is integer cents. SQLite is authoritative; client totals are never trusted.
Payments are confirmed by the server/provider before a paid order becomes actionable.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

PH = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1, type=Type.ID)
DUMMY_HASH = PH.hash(secrets.token_urlsafe(24))
SESSION_TTL = 12 * 3600
SESSION_IDLE = 2 * 3600
QUOTE_TTL = 600
FIELDS = ('street','number','neighborhood','city','state','postcode','complement')
TRANSITIONS = {'awaiting_payment':['cancelled'],'new':['accepted','cancelled'],'accepted':['preparing','cancelled'],
 'preparing':['ready','cancelled'],'ready':['dispatched','completed','cancelled'],
 'dispatched':['completed','cancelled'],'completed':[],'cancelled':[]}

class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(value or '')) if not unicodedata.combining(c)).lower().split())


def text(value, label, maximum=120, required=True):
    if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()):
        raise Problem('Confira '+label+'.')
    return value.strip()


def identifier(value, label):
    value=text(value,label,100)
    if not re.fullmatch(r"[A-Za-z0-9_-]+",value): raise Problem("Identificador inv\u00e1lido: "+label+".")
    return value


def integer(value, label, lo=0, hi=10000000):
    if type(value) is not int or not lo <= value <= hi:
        raise Problem('Valor inv\u00e1lido: '+label+'.')
    return value


def point_valid(p):
    return isinstance(p,dict) and all(type(p.get(k)) in (int,float) and math.isfinite(p[k]) and abs(p[k])<=lim for k,lim in [('lng',180),('lat',85)])


def on_segment(p,a,b):
    cross=(p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0])
    return abs(cross)<1e-12 and min(a[0],b[0])-1e-10<=p[0]<=max(a[0],b[0])+1e-10 and min(a[1],b[1])-1e-10<=p[1]<=max(a[1],b[1])+1e-10


def in_ring(point,ring):
    p=[point['lng'],point['lat']]; inside=False
    for i,a in enumerate(ring):
        b=ring[i-1]
        if on_segment(p,a,b): return True
        if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
            inside=not inside
    return inside


def orient(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def intersects(a,b,c,d):
    u,v,w,x=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    return (u*v<0 and w*x<0) or (abs(u)<1e-12 and on_segment(c,a,b)) or (abs(v)<1e-12 and on_segment(d,a,b)) or (abs(w)<1e-12 and on_segment(a,c,d)) or (abs(x)<1e-12 and on_segment(b,c,d))


def clean_zone(z,store_id):
    if not isinstance(z,dict) or z.get('storeId')!=store_id: raise Problem('\u00c1rea de outra loja.')
    if z.get('kind') not in ('delivery','blocked') or type(z.get('active')) is not bool: raise Problem('Tipo de \u00e1rea inv\u00e1lido.')
    ring=z.get('ring')
    if not isinstance(ring,list) or not 3<=len(ring)<=100 or not all(isinstance(p,list) and len(p)==2 and point_valid({'lng':p[0],'lat':p[1]}) for p in ring): raise Problem('Desenhe de 3 a 100 pontos v\u00e1lidos.')
    area=0; n=len(ring)
    for i,a in enumerate(ring):
        j=(i+1)%n; b=ring[j]; area+=a[0]*b[1]-b[0]*a[1]
        if a==b: raise Problem('Remova pontos repetidos da \u00e1rea.')
        for k in range(i+1,n):
            l=(k+1)%n
            if i==k or j==k or l==i: continue
            if intersects(a,b,ring[k],ring[l]): raise Problem('O contorno cruza a si mesmo.')
    if abs(area)<1e-10: raise Problem('O contorno precisa ter superf\u00edcie.')
    return {'id':identifier(z.get('id'),'identificador da \u00e1rea'),'storeId':store_id,'name':text(z.get('name'),'nome da \u00e1rea',60),
     'kind':z['kind'],'active':z['active'],'fee':integer(z.get('fee'),'taxa',0,100000),
     'priority':integer(z.get('priority'),'prioridade',0,999),'ring':ring}


def area_quote(store,point):
    cfg=store.get('deliveryConfig')
    if not cfg or not point_valid(point): raise Problem('Endere\u00e7o ou cobertura n\u00e3o configurados.',422)
    active=[clean_zone(z,store['id']) for z in cfg['zones'] if z['active']]
    matches=[z for z in active if in_ring(point,z['ring'])]
    if any(z['kind']=='blocked' for z in matches): raise Problem('Esta \u00e1rea est\u00e1 bloqueada para entrega.',422)
    if not matches: raise Problem('Fora da cobertura. Escolha retirada ou outro endere\u00e7o.',422)
    matches.sort(key=lambda z:(-z['priority'],z['id']))
    if len(matches)>1 and matches[0]['priority']==matches[1]['priority']: raise Problem('Conflito entre \u00e1reas. A loja precisa ajustar as prioridades.',422)
    z=matches[0]
    return {'ok':True,'storeId':store['id'],'zoneId':z['id'],'zoneName':z['name'],'fee':z['fee'],'revision':cfg['revision'],'priority':z['priority'],'overlap':len(matches)>1}


def clean_neighborhood_rate(rate):
    if not isinstance(rate,dict) or type(rate.get('active')) is not bool:
        raise Problem('Taxa por bairro invalida.')
    aliases=rate.get('aliases',[])
    if not isinstance(aliases,list) or len(aliases)>20:
        raise Problem('Apelidos do bairro invalidos.')
    clean_aliases=[]
    for alias in aliases:
        value=text(alias,'apelido do bairro',80)
        if norm(value) not in {norm(x) for x in clean_aliases}: clean_aliases.append(value)
    return {'id':identifier(rate.get('id'),'identificador do bairro'),
            'name':text(rate.get('name'),'bairro',80),'aliases':clean_aliases,
            'fee':integer(rate.get('fee'),'taxa do bairro',0,100000),'active':rate['active']}


def neighborhood_quote(store,address):
    cfg=store.get('deliveryConfig') or {}
    rates=[clean_neighborhood_rate(r) for r in cfg.get('neighborhoodRates',[]) if r.get('active')]
    if not rates: raise Problem('A loja ainda nao cadastrou as taxas por bairro.',422)
    configured_city=norm(cfg.get('city'))
    configured_state=norm(cfg.get('state'))
    if configured_city and norm(address.get('city'))!=configured_city:
        raise Problem('Esta loja entrega somente em '+str(cfg.get('city'))+'. Confira a cidade.',422)
    if configured_state and norm(address.get('state'))!=configured_state:
        raise Problem('Confira a UF do endereco de entrega.',422)
    wanted=norm(address.get('neighborhood'))
    matches=[]
    for rate in rates:
        names=[rate['name'],*rate.get('aliases',[])]
        if wanted and any(wanted==norm(x) for x in names): matches.append(rate)
    if not matches:
        raise Problem('Este bairro ainda nao esta na area de entrega da loja. Confira o bairro ou escolha retirada.',422)
    if len(matches)>1:
        raise Problem('O bairro esta duplicado na tabela de entrega. A loja precisa corrigir a configuracao.',422)
    rate=matches[0]
    return {'ok':True,'storeId':store['id'],'zoneId':rate['id'],'zoneName':rate['name'],
            'neighborhood':rate['name'],'fee':rate['fee'],'revision':cfg.get('revision',1),
            'mode':'neighborhood','priority':0,'overlap':False}


class Database:
    def __init__(self,path,seed_path,allow_samples=True,seed_catalog=True):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.seed=json.loads(Path(seed_path).read_text(encoding='utf-8')); self.allow_samples=allow_samples; self.seed_catalog=seed_catalog
        self.init()

    @contextmanager
    def connect(self,write=False):
        c=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=10000')
        try:
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield c
            c.commit()
        except Exception:
            c.rollback(); raise
        finally: c.close()

    def init(self):
        with sqlite3.connect(self.path) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript('''
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,name TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires REAL NOT NULL,last_seen REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stores(id TEXT PRIMARY KEY,data TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS members(user_id TEXT NOT NULL REFERENCES users(id),store_id TEXT NOT NULL REFERENCES stores(id),PRIMARY KEY(user_id,store_id));
CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,store_id TEXT NOT NULL REFERENCES stores(id),data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS favorites(user_id TEXT NOT NULL REFERENCES users(id),store_id TEXT NOT NULL REFERENCES stores(id),PRIMARY KEY(user_id,store_id));
CREATE TABLE IF NOT EXISTS addresses(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),data TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),data TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS orders(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE,user_id TEXT NOT NULL REFERENCES users(id),store_id TEXT NOT NULL REFERENCES stores(id),idem TEXT NOT NULL,quote_id TEXT NOT NULL UNIQUE,data TEXT NOT NULL,UNIQUE(user_id,idem));
CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id,seq DESC);
CREATE INDEX IF NOT EXISTS orders_store ON orders(store_id,seq DESC);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,user_id TEXT NOT NULL,store_id TEXT,action TEXT NOT NULL,resource TEXT);
PRAGMA user_version=4;
''')
            # Official production starts empty; stores are created by merchant registration.
            # Local/LAN development may still seed the bundled Cantinho fixture.
            if self.seed_catalog:
                for s in self.seed['stores']:
                    c.execute('INSERT OR IGNORE INTO stores(id,data) VALUES(?,?)',(s['id'],dump(s)))
                # Demo products are seeded once only in local/LAN development.
                if not c.execute('SELECT 1 FROM audit WHERE action=?',('seed',)).fetchone():
                    for p in self.seed['products']: c.execute('INSERT OR IGNORE INTO products VALUES(?,?,?)',(p['id'],p['storeId'],dump(p)))
                    c.execute('INSERT INTO audit(at,user_id,action) VALUES(?,?,?)',(utc(),'system','seed'))
            # RC5 production cleanup. These IDs/names belonged only to bundled fixtures.
            # User-created stores use loja_* IDs and are never deleted by this migration.
            legacy_ids={'forno','acai'}
            legacy_names={'Forno da Vila','Açaí da Praça'}
            for row in c.execute('SELECT id,data FROM stores').fetchall():
                sid=row[0]
                try: store_data=json.loads(row[1])
                except Exception: store_data={}
                if sid in legacy_ids or (store_data.get('name') in legacy_names and store_data.get('tag')=='Estabelecimento fictício'):
                    c.execute('DELETE FROM orders WHERE store_id=?',(sid,))
                    c.execute('DELETE FROM favorites WHERE store_id=?',(sid,))
                    c.execute('DELETE FROM products WHERE store_id=?',(sid,))
                    c.execute('DELETE FROM members WHERE store_id=?',(sid,))
                    c.execute('DELETE FROM stores WHERE id=?',(sid,))
            if not c.execute('SELECT 1 FROM audit WHERE action=?',('production_cleanup_rc5',)).fetchone():
                c.execute('INSERT INTO audit(at,user_id,action,resource) VALUES(?,?,?,?)',
                          (utc(),'system','production_cleanup_rc5','legacy-fixtures'))
            # Remove old pilot wording from Cantinho only when it still has the exact legacy value.
            row=c.execute('SELECT data FROM stores WHERE id=?',('cantinho',)).fetchone()
            if row:
                store=json.loads(row[0]); changed=False
                if store.get('tag')=='Seu estabelecimento piloto': store['tag']='Pastelaria'; changed=True
                if store.get('description')=='Escolha seu sabor, personalize e acompanhe seu pedido.':
                    store['description']='Escolha seu sabor, personalize e acompanhe seu pedido.'
                if changed: c.execute('UPDATE stores SET data=?,version=version+1 WHERE id=?',(dump(store),'cantinho'))
        try: self.path.chmod(0o600)
        except OSError: pass

    def legacy_fixture_count(self):
        with self.connect() as c:
            row=c.execute("SELECT COUNT(*) AS n FROM stores WHERE id IN ('forno','acai')").fetchone()
            return int(row['n'])

    def audit(self,c,uid,store_id,action,resource=None):
        c.execute('INSERT INTO audit(at,user_id,store_id,action,resource) VALUES(?,?,?,?,?)',(utc(),uid,store_id,action,resource))

    def owns(self,c,uid,sid):
        if not c.execute('SELECT 1 FROM members WHERE user_id=? AND store_id=?',(uid,sid)).fetchone(): raise Problem('Voc\u00ea n\u00e3o tem acesso a esta loja.',403)

    def user(self,c,uid):
        r=c.execute('SELECT id,email,name FROM users WHERE id=?',(uid,)).fetchone()
        if not r: raise Problem('Entre na sua conta.',401)
        return dict(r)

    def store(self,c,sid):
        r=c.execute('SELECT data,version FROM stores WHERE id=?',(sid,)).fetchone()
        if not r: raise Problem('Loja n\u00e3o encontrada.',404)
        s=json.loads(r['data']); s['version']=r['version']; return s

    def session(self,token):
        if not token: return None
        now=time.time()
        with self.connect(True) as c:
            r=c.execute('SELECT * FROM sessions WHERE token_hash=?',(digest(token),)).fetchone()
            if not r or r['expires']<=now or r['last_seen']<now-SESSION_IDLE: return None
            c.execute('UPDATE sessions SET last_seen=? WHERE token_hash=?',(now,digest(token)))
            return {'user':self.user(c,r['user_id']),'csrf':r['csrf']}

    def new_session(self,c,uid,old_token=None):
        if old_token: c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(old_token),))
        c.execute('DELETE FROM sessions WHERE expires<? OR last_seen<?',(time.time(),time.time()-SESSION_IDLE))
        token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
        c.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(digest(token),uid,csrf,time.time()+SESSION_TTL,time.time()))
        return token

    def register(self,payload,old_token=None):
        email=text(payload.get('email'),'e-mail',254).casefold()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise Problem('E-mail inv\u00e1lido.')
        name=text(payload.get('name'),'nome',80); password=payload.get('password')
        if not isinstance(password,str) or not 12<=len(password)<=128: raise Problem('Use uma senha de 12 a 128 caracteres.')
        mode=payload.get('mode','customer')
        if mode not in ('customer','merchant'): raise Problem('Tipo de conta inv\u00e1lido.')
        store_name=text(payload.get('storeName'),'nome da loja',80) if mode=='merchant' else None
        hashed=PH.hash(password); uid='usr_'+secrets.token_hex(12)
        with self.connect(True) as c:
            if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): raise Problem('N\u00e3o foi poss\u00edvel criar a conta com estes dados.',409)
            c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,email,name,hashed,utc()))
            if store_name:
                sid='loja_'+secrets.token_hex(8)
                cfg=copy.deepcopy(self.seed['stores'][0]['deliveryConfig']); cfg['zones']=[]; cfg['neighborhoodRates']=[]; cfg['schema']=2; cfg['revision']=1
                s={'id':sid,'name':store_name,'initials':''.join(x[0] for x in store_name.split()[:2]).upper(),'type':'Alimenta\u00e7\u00e3o','tag':'Loja no Bocali','description':'Card\u00e1pio em configura\u00e7\u00e3o.','tone':'sage','open':False,'fee':0,'eta':'A confirmar','minimum':0,'deliveryConfig':cfg}
                c.execute('INSERT INTO stores(id,data) VALUES(?,?)',(sid,dump(s)))
                c.execute('INSERT INTO members VALUES(?,?)',(uid,sid))
            self.audit(c,uid,None,'register')
            return self.new_session(c,uid,old_token)

    def login(self,payload,old_token=None):
        email=text(payload.get('email'),'e-mail',254).casefold(); password=payload.get('password')
        if not isinstance(password,str) or len(password)>128: raise Problem('E-mail ou senha inv\u00e1lidos.',401)
        with self.connect() as c: row=c.execute('SELECT id,password_hash FROM users WHERE email=?',(email,)).fetchone()
        try: PH.verify(row['password_hash'] if row else DUMMY_HASH,password)
        except (VerifyMismatchError,InvalidHashError,VerificationError): raise Problem('E-mail ou senha inv\u00e1lidos.',401)
        if not row: raise Problem('E-mail ou senha inv\u00e1lidos.',401)
        with self.connect(True) as c:
            if PH.check_needs_rehash(row['password_hash']): c.execute('UPDATE users SET password_hash=? WHERE id=?',(PH.hash(password),row['id']))
            return self.new_session(c,row['id'],old_token)

    def logout(self,token):
        with self.connect(True) as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(token),))

    def bootstrap(self,session):
        uid=session['user']['id'] if session else None
        with self.connect() as c:
            stores=[self.store(c,r['id']) for r in c.execute('SELECT id FROM stores ORDER BY rowid')]
            products=[json.loads(r['data']) for r in c.execute('SELECT data FROM products ORDER BY rowid')]
            owned=[r['store_id'] for r in c.execute('SELECT store_id FROM members WHERE user_id=?',(uid,))] if uid else []
            favorites=[r['store_id'] for r in c.execute('SELECT store_id FROM favorites WHERE user_id=?',(uid,))] if uid else []
            mine=[json.loads(r['data']) for r in c.execute('SELECT data FROM orders WHERE user_id=? ORDER BY seq DESC LIMIT 200',(uid,))] if uid else []
            managed=[json.loads(r['data']) for r in c.execute('SELECT o.data FROM orders o JOIN members m ON m.store_id=o.store_id WHERE m.user_id=? ORDER BY seq DESC LIMIT 300',(uid,))] if uid else []
            managed=[o for o in managed if o.get('status')!='awaiting_payment']
        return {'user':session['user'] if session else None,'csrf':session['csrf'] if session else None,'managedStores':owned,'stores':stores,'products':products,'favorites':favorites,'customerOrders':mine,'merchantOrders':managed,'mode':'server','version':'1.0-rc4','demoAddresses':self.allow_samples}

    def favorites(self,uid,payload):
        sid=text(payload.get('storeId'),'loja',100)
        if type(payload.get('saved')) is not bool: raise Problem('Favorito inv\u00e1lido.')
        with self.connect(True) as c:
            self.store(c,sid)
            if payload['saved']: c.execute('INSERT OR IGNORE INTO favorites VALUES(?,?)',(uid,sid))
            else: c.execute('DELETE FROM favorites WHERE user_id=? AND store_id=?',(uid,sid))
        return {'ok':True}

    def clean_product(self,p,sid):
        if not isinstance(p,dict) or p.get('storeId')!=sid: raise Problem('Produto de outra loja.')
        extras=p.get('extras',[])
        if not isinstance(extras,list) or len(extras)>50: raise Problem('Adicionais inv\u00e1lidos.')
        clean=[]
        for e in extras:
            if not isinstance(e,dict): raise Problem('Adicional inv\u00e1lido.')
            clean.append({'id':identifier(e.get('id'),'ID do adicional'),'name':text(e.get('name'),'adicional',100),'price':integer(e.get('price'),'pre\u00e7o do adicional',0,100000)})
        if len({e['id'] for e in clean})!=len(clean): raise Problem('Adicionais repetidos.')
        if type(p.get('available')) is not bool: raise Problem('Disponibilidade inv\u00e1lida.')
        art=p.get('art','pastel')
        if art not in ('pastel','pizza','sweet','drink','acai','bag','menu'): art='pastel'
        return {'id':identifier(p.get('id'),'ID do produto'),'storeId':sid,'name':text(p.get('name'),'produto',100),'description':text(p.get('description',''),'descri\u00e7\u00e3o',240,False),'category':text(p.get('category'),'categoria',50),'price':integer(p.get('price'),'pre\u00e7o',1,10000000),'available':p['available'],'art':art,'extras':clean}

    def catalog(self,uid,payload):
        sid=text(payload.get('storeId'),'loja',100); version=integer(payload.get('expectedVersion'),'vers\u00e3o',1)
        incoming=payload.get('store'); products=payload.get('products')
        if not isinstance(incoming,dict) or incoming.get('id')!=sid or not isinstance(products,list) or len(products)>1000: raise Problem('Cat\u00e1logo inv\u00e1lido.')
        clean=[self.clean_product(p,sid) for p in products]
        if len({p['id'] for p in clean})!=len(clean): raise Problem('IDs de produtos repetidos.')
        cfg=incoming.get('deliveryConfig')
        if not isinstance(cfg,dict) or not point_valid(cfg.get('reference')) or not isinstance(cfg.get('zones',[]),list) or len(cfg.get('zones',[]))>60: raise Problem('Configura\u00e7\u00e3o de entrega inv\u00e1lida.')
        zones=[clean_zone(z,sid) for z in cfg.get('zones',[])]
        if len({z['id'] for z in zones})!=len(zones): raise Problem('IDs de \u00e1reas repetidos.')
        raw_rates=cfg.get('neighborhoodRates',[])
        if not isinstance(raw_rates,list) or len(raw_rates)>300: raise Problem('Tabela de bairros invalida.')
        rates=[clean_neighborhood_rate(r) for r in raw_rates]
        keys=[]
        for rate in rates:
            keys.extend([norm(rate['name']),*[norm(x) for x in rate.get('aliases',[])]])
        keys=[x for x in keys if x]
        if len(set(keys))!=len(keys): raise Problem('Ha bairros ou apelidos repetidos na tabela de entrega.')
        with self.connect(True) as c:
            self.owns(c,uid,sid); current=self.store(c,sid)
            if current['version']!=version: raise Problem('A loja mudou em outro aparelho. Atualize e tente novamente.',409)
            for key,maximum in [('name',80),('description',240),('type',80),('eta',60)]: current[key]=text(incoming.get(key,current[key]),key,maximum)
            if type(incoming.get('open')) is not bool: raise Problem('Estado da loja inv\u00e1lido.')
            current['open']=incoming['open']; current['minimum']=integer(incoming.get('minimum'),'pedido m\u00ednimo',0,1000000)
            current['deliveryConfig']={'schema':2,'revision':current['deliveryConfig']['revision']+1,'city':text(cfg.get('city'),'cidade',120),'state':text(cfg.get('state'),'UF',2),'reference':cfg['reference'],'zones':zones,'neighborhoodRates':rates}
            printer=incoming.get('printer',{'paper':80,'autoPrint':False})
            if not isinstance(printer,dict) or type(printer.get('paper')) is not int or printer['paper'] not in (58,80) or type(printer.get('autoPrint')) is not bool: raise Problem('Impressora inv\u00e1lida.')
            current['printer']={'paper':printer['paper'],'autoPrint':printer['autoPrint']}
            for p in clean:
                other=c.execute('SELECT store_id FROM products WHERE id=?',(p['id'],)).fetchone()
                if other and other['store_id']!=sid: raise Problem('Produto pertence a outra loja.',403)
            current.pop('version',None)
            c.execute('UPDATE stores SET data=?,version=version+1 WHERE id=?',(dump(current),sid))
            c.execute('DELETE FROM products WHERE store_id=?',(sid,))
            for p in clean: c.execute('INSERT INTO products VALUES(?,?,?)',(p['id'],sid,dump(p)))
            self.audit(c,uid,sid,'catalog.update')
        return {'ok':True}

    def add_geocodes(self,uid,results):
        out=[]
        with self.connect(True) as c:
            c.execute('DELETE FROM addresses WHERE expires<?',(time.time(),))
            for r in results:
                token=secrets.token_urlsafe(24)
                c.execute('INSERT INTO addresses VALUES(?,?,?,?)',(token,uid,dump(r),time.time()+900))
                out.append({**r,'addressToken':token})
        return out

    def selected_address(self,c,uid,payload):
        address=payload.get('address')
        if not isinstance(address,dict): raise Problem('Confirme o endere\u00e7o.')
        a={k:text(address.get(k,''),k,120,k in ('street','number','neighborhood','city','state')) for k in FIELDS}
        if not re.fullmatch('[A-Za-z]{2}',a['state']): raise Problem('UF inv\u00e1lida.')
        if a['postcode'] and not re.fullmatch(r'\d{5}-?\d{3}',a['postcode']): raise Problem('CEP inv\u00e1lido.')
        idx=payload.get('sampleIndex')
        if idx is not None:
            if not self.allow_samples: raise Problem('Endere\u00e7os fict\u00edcios desativados.',403)
            integer(idx,'exemplo',0,3); row=copy.deepcopy(self.seed['samples'][idx])
        else:
            token=text(payload.get('addressToken'),'localiza\u00e7\u00e3o',100)
            saved=c.execute('SELECT data,expires FROM addresses WHERE token=? AND user_id=?',(token,uid)).fetchone()
            if not saved or saved['expires']<time.time(): raise Problem('Localiza\u00e7\u00e3o expirada. Consulte novamente.',409)
            row=json.loads(saved['data'])
        if not row.get('precise') or not point_valid(row.get('point')): raise Problem('Localiza\u00e7\u00e3o imprecisa. Confira rua e n\u00famero.',422)
        if any(norm(a[k])!=norm(row['address'].get(k,'')) for k in FIELDS if k!='complement'): raise Problem('O endere\u00e7o mudou. Localize novamente.',409)
        row['address']=a
        return row

    def price_order(self,c,uid,payload,selection=None):
        sid=text(payload.get('storeId'),'loja',100); store=self.store(c,sid)
        if not store['open']: raise Problem('A loja est\u00e1 pausada.',409)
        fulfillment=payload.get('fulfillment'); payment=payload.get('payment')
        if fulfillment not in ('delivery','pickup') or payment not in ('cash','card_machine','card','pix'): raise Problem('Modalidade ou pagamento invalido.')
        request_items=payload.get('items')
        if not isinstance(request_items,list) or not 1<=len(request_items)<=50: raise Problem('Confira sua sacola.')
        items=[]; subtotal=0; quantity=0
        for i in request_items:
            if not isinstance(i,dict): raise Problem('Item inv\u00e1lido.')
            pid=text(i.get('productId'),'produto',100)
            row=c.execute('SELECT data FROM products WHERE id=? AND store_id=?',(pid,sid)).fetchone()
            if not row: raise Problem('Produto n\u00e3o pertence a esta loja.',422)
            p=json.loads(row['data'])
            if not p['available']: raise Problem(p['name']+' est\u00e1 indispon\u00edvel.',409)
            qty=integer(i.get('quantity'),'quantidade',1,20); extras=i.get('extraIds',[])
            if not isinstance(extras,list) or len(extras)>50 or any(not isinstance(x,str) for x in extras) or len(set(extras))!=len(extras): raise Problem('Adicionais inv\u00e1lidos ou repetidos.')
            choices={e['id']:e for e in p['extras']}
            if any(x not in choices for x in extras): raise Problem('Adicional indispon\u00edvel.',409)
            selected=[choices[x] for x in extras]
            item={'id':'item_'+secrets.token_hex(8),'productId':pid,'name':p['name'],'unitPrice':p['price'],'quantity':qty,'extras':selected,'note':text(i.get('note',''),'observa\u00e7\u00e3o do item',200,False)}
            subtotal+=(p['price']+sum(e['price'] for e in selected))*qty; quantity+=qty; items.append(item)
        if subtotal<store['minimum']: raise Problem('O pedido est\u00e1 abaixo do m\u00ednimo da loja.',422)
        if subtotal>10000000: raise Problem('Valor acima do limite permitido.',422)
        payment_details={}
        if payment=='cash':
            details=payload.get('paymentDetails') or {}
            if not isinstance(details,dict): raise Problem('Dados do pagamento invalidos.')
            needs=details.get('changeNeeded',False)
            if type(needs) is not bool: raise Problem('Opcao de troco invalida.')
            change_for=details.get('changeFor')
            if needs:
                change_for=integer(change_for,'troco para',subtotal,20000000)
            else: change_for=None
            payment_details={'changeNeeded':needs,'changeFor':change_for}
        elif payment=='card_machine':
            payment_details={'machineAt':fulfillment}
        delivery=None; fee=0
        if fulfillment=='delivery':
            cfg=store.get('deliveryConfig') or {}
            if cfg.get('neighborhoodRates'):
                source=(selection or {}).get('address') if isinstance(selection,dict) else payload.get('address')
                if not isinstance(source,dict): raise Problem('Preencha o endereco de entrega.',422)
                address={k:text(source.get(k,''),k,120,k in ('street','number','neighborhood','city','state')) for k in FIELDS}
                if not re.fullmatch('[A-Za-z]{2}',address['state']): raise Problem('UF invalida.')
                if address['postcode'] and not re.fullmatch(r'\d{5}-?\d{3}',address['postcode']): raise Problem('CEP invalido.')
                q=neighborhood_quote(store,address); fee=q['fee']
                delivery={'address':address,'source':'neighborhood','quote':q,'confirmed':True,'confirmedAt':utc(),
                          'addressKey':'|'.join(norm(address.get(k,'')) for k in FIELDS)}
            else:
                selection=selection or self.selected_address(c,uid,payload)
                q=area_quote(store,selection['point']); fee=q['fee']
                delivery={**selection,'quote':q,'confirmed':True,'confirmedAt':utc(),'addressKey':'|'.join(norm(selection['address'].get(k,'')) for k in FIELDS)}
        if payment=='cash' and payment_details.get('changeNeeded') and payment_details.get('changeFor',0)<subtotal+fee:
            raise Problem('O valor para troco precisa ser igual ou maior que o total do pedido.',422)
        return {'storeId':sid,'storeName':store['name'],'items':items,'subtotal':subtotal,'fee':fee,'total':subtotal+fee,'quantity':quantity,'delivery':delivery,'fulfillment':fulfillment,'payment':payment,'paymentDetails':payment_details,'paymentStatus':('cash_pending' if payment in ('cash','card_machine') else 'pending'),'note':text(payload.get('note',''),'observa\u00e7\u00e3o',200,False),'demo':False}

    @staticmethod
    def fingerprint(order):
        # Ignore generated timestamps/IDs; compare prices, product descriptions,
        # extras, address, coverage revision and customer-visible snapshot.
        d=copy.deepcopy(order)
        for i in d['items']: i.pop('id',None)
        if d.get('delivery'):
            for k in ('confirmedAt','addressToken'): d['delivery'].pop(k,None)
        return digest(dump(d))

    def quote(self,uid,payload):
        with self.connect(True) as c:
            order=self.price_order(c,uid,payload); qid=secrets.token_urlsafe(24)
            clean_request={k:order[k] for k in ('storeId','fulfillment','payment','paymentDetails','note')}
            clean_request['items']=[{'productId':i['productId'],'quantity':i['quantity'],'extraIds':[e['id'] for e in i['extras']],'note':i['note']} for i in order['items']]
            if order.get('delivery') and order['delivery'].get('source')=='neighborhood': clean_request['address']=order['delivery']['address']
            stored={'order':order,'request':clean_request,'fingerprint':self.fingerprint(order)}
            c.execute('DELETE FROM quotes WHERE expires<? AND id NOT IN (SELECT quote_id FROM orders)',(time.time(),))
            c.execute('INSERT INTO quotes VALUES(?,?,?,?)',(qid,uid,dump(stored),time.time()+QUOTE_TTL))
        return {'quoteId':qid,'expiresIn':QUOTE_TTL,'order':order}

    def create_order(self,uid,payload):
        qid=text(payload.get('quoteId'),'resumo do pedido',100); idem=text(payload.get('idempotencyKey'),'identificador de envio',100)
        if len(idem)<16: raise Problem('Identificador de envio inv\u00e1lido.')
        with self.connect(True) as c:
            previous=c.execute('SELECT data,quote_id FROM orders WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
            if previous:
                if previous['quote_id']!=qid: raise Problem('Identificador j\u00e1 usado em outro pedido.',409)
                return {'order':json.loads(previous['data']),'reused':True}
            previous=c.execute('SELECT data FROM orders WHERE user_id=? AND quote_id=?',(uid,qid)).fetchone()
            if previous: return {'order':json.loads(previous['data']),'reused':True}
            row=c.execute('SELECT data,expires FROM quotes WHERE id=? AND user_id=?',(qid,uid)).fetchone()
            if not row or row['expires']<time.time(): raise Problem('Resumo expirado. Recalcule e confirme novamente.',409)
            saved=json.loads(row['data']); selection=saved['order'].get('delivery')
            now_order=self.price_order(c,uid,saved['request'],selection)
            if self.fingerprint(now_order)!=saved['fingerprint']: raise Problem('Pre\u00e7o, produto ou taxa mudou. Recalcule e confirme o novo total.',409)
            now=utc(); order=saved['order']; initial='new' if order['payment'] in ('cash','card_machine') else 'awaiting_payment'
            order.update({'status':initial,'createdAt':now,'events':[{'status':initial,'at':now}],'revision':1,'customerName':self.user(c,uid)['name'],'payments':[]})
            cur=c.execute('INSERT INTO orders(user_id,store_id,idem,quote_id,data) VALUES(?,?,?,?,?)',(uid,order['storeId'],idem,qid,'{}'))
            order['id']='PED-'+str(cur.lastrowid).zfill(6)
            c.execute('UPDATE orders SET id=?,data=? WHERE seq=?',(order['id'],dump(order),cur.lastrowid))
            self.audit(c,uid,order['storeId'],'order.create',order['id'])
            return {'order':order,'reused':False}

    def payment_target(self,uid,order_id):
        order_id=text(order_id,'pedido',100)
        with self.connect() as c:
            r=c.execute('SELECT data,user_id FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r: raise Problem('Pedido não encontrado.',404)
            if r['user_id']!=uid: raise Problem('Este pedido pertence a outra conta.',403)
            o=json.loads(r['data'])
            if o.get('payment') not in ('card','pix'): raise Problem('Este pedido não usa pagamento online.',409)
            if o.get('paymentStatus')=='approved': raise Problem('Este pedido já está pago.',409)
            if o.get('status') not in ('awaiting_payment','new'): raise Problem('Pagamento indisponível nesta etapa.',409)
            return o

    def save_checkout_preference(self,uid,order_id,preference,checkout_url):
        order_id=text(order_id,'pedido',100)
        pref_id=text(preference.get('id'),'preferência de pagamento',120)
        checkout_url=text(checkout_url,'endereço do pagamento',2048)
        if not checkout_url.startswith('https://'): raise Problem('Endereço do checkout inválido.',502)
        with self.connect(True) as c:
            r=c.execute('SELECT data,user_id,store_id FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r: raise Problem('Pedido não encontrado.',404)
            if r['user_id']!=uid: raise Problem('Este pedido pertence a outra conta.',403)
            o=json.loads(r['data'])
            if o.get('payment')!='card': raise Problem('Este pedido não usa checkout de cartão.',409)
            if o.get('paymentStatus')=='approved': raise Problem('Este pedido já está pago.',409)
            if o.get('status') not in ('awaiting_payment','new'): raise Problem('Pagamento indisponível nesta etapa.',409)
            # Once a checkout URL is attached to an unpaid order, always reuse it. This prevents
            # repeated taps from creating multiple payable preferences for the same Bocali order.
            if o.get('checkoutPreferenceUrl'):
                return {'order':o,'preferenceId':o.get('checkoutPreferenceId',''),'checkoutUrl':o['checkoutPreferenceUrl'],'reused':True}
            o['checkoutPreferenceId']=pref_id
            o['checkoutPreferenceUrl']=checkout_url
            o['checkoutPreferenceCreatedAt']=utc()
            o['revision']=int(o.get('revision',0))+1
            c.execute('UPDATE orders SET data=? WHERE id=?',(dump(o),order_id))
            self.audit(c,uid,r['store_id'],'payment.preference',order_id)
            return {'order':o,'preferenceId':pref_id,'checkoutUrl':checkout_url,'reused':False}

    def refund_target(self,uid,payload):
        oid=text(payload.get('orderId'),'pedido',100)
        expected=integer(payload.get('expectedRevision'),'versão do pedido',1)
        reason=text(payload.get('reason'),'motivo do cancelamento',200)
        with self.connect() as c:
            r=c.execute('SELECT data,store_id FROM orders WHERE id=?',(oid,)).fetchone()
            if not r: raise Problem('Pedido não encontrado.',404)
            self.owns(c,uid,r['store_id']); o=json.loads(r['data'])
            if expected!=o['revision']: raise Problem('Pedido atualizado por outro atendente. Confira a fila.',409)
            if o.get('paymentStatus')!='approved' or o.get('payment') not in ('card','pix'):
                return None
            provider_id=str(o.get('paymentProviderId') or '')
            if not provider_id: raise Problem('Pagamento aprovado sem identificador do provedor. Não cancele até conferir o Mercado Pago.',409)
            if o.get('status') not in ('new','accepted','preparing','ready'):
                raise Problem('Este pedido não pode ser estornado nesta etapa automaticamente.',409)
            return {'order':o,'providerId':provider_id,'reason':reason}

    def apply_payment(self,order_id,provider_payment,actor='mercadopago',cancellation_reason=None):
        order_id=text(order_id,'pedido',100)
        provider_id=str(provider_payment.get('id') or '')
        status=str(provider_payment.get('status') or '').lower()
        if not provider_id or status not in ('approved','pending','in_process','rejected','cancelled','refunded','charged_back'):
            raise Problem('Resposta de pagamento inválida.',502)
        with self.connect(True) as c:
            r=c.execute('SELECT data,user_id,store_id FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r: raise Problem('Pedido de pagamento não encontrado.',404)
            o=json.loads(r['data'])
            if o.get('payment') not in ('card','pix'): raise Problem('Pedido não usa pagamento online.',409)
            payments=o.setdefault('payments',[])
            attempt={'provider':'mercadopago','id':provider_id,'status':status,'statusDetail':str(provider_payment.get('status_detail') or '')[:120],
                     'method':str(provider_payment.get('payment_method_id') or o.get('payment',''))[:80],'updatedAt':utc()}
            previous=next((x for x in payments if x.get('id')==provider_id),None)
            if previous: previous.update(attempt)
            else: payments.append(attempt)
            old=o.get('paymentStatus')
            mapped='approved' if status=='approved' else ('rejected' if status in ('rejected','cancelled') else ('refunded' if status in ('refunded','charged_back') else 'pending'))
            provider_method=str(provider_payment.get('payment_method_id') or '')[:80]
            o['paymentStatus']=mapped; o['paymentProvider']='mercadopago'; o['paymentProviderId']=provider_id; o['paymentProviderMethod']=provider_method
            if mapped=='approved' and o.get('status')=='awaiting_payment':
                o['status']='new'; o['events'].append({'status':'payment_approved','at':utc(),'provider':'mercadopago'}); o['events'].append({'status':'new','at':utc()})
            elif mapped=='refunded' and o.get('status') not in ('completed','cancelled'):
                o['status']='cancelled'; o['cancellationReason']=cancellation_reason or 'Pagamento estornado/cancelado pelo provedor.'; o['events'].append({'status':'cancelled','at':utc(),'reason':'payment_refunded'})
            elif mapped!=old:
                o['events'].append({'status':'payment_'+mapped,'at':utc(),'provider':'mercadopago'})
            o['revision']=int(o.get('revision',0))+1
            c.execute('UPDATE orders SET data=? WHERE id=?',(dump(o),order_id))
            self.audit(c,actor,r['store_id'],'payment.'+mapped,order_id)
            return o

    def action(self,uid,payload):
        oid=text(payload.get('orderId'),'pedido',100); act=payload.get('action')
        with self.connect(True) as c:
            r=c.execute('SELECT data,store_id FROM orders WHERE id=?',(oid,)).fetchone()
            if not r: raise Problem('Pedido n\u00e3o encontrado.',404)
            self.owns(c,uid,r['store_id']); o=json.loads(r['data'])
            expected=integer(payload.get('expectedRevision'),'vers\u00e3o do pedido',1)
            if expected!=o['revision']:
                if act=='print-result' and type(payload.get('success')) is bool:
                    j=next((j for j in o.get('printJobs',[]) if j['id']==payload.get('jobId')),None)
                    wanted='confirmed_by_operator' if payload['success'] else 'failed_by_operator'
                    if j and j.get('status')==wanted:
                        return {'order':o}
                raise Problem('Pedido atualizado por outro atendente. Confira a fila.',409)
            now=utc()
            if act=='accept':
                if o['status']!='new': raise Problem('Este pedido j\u00e1 foi atendido.',409)
                lo=integer(payload.get('min'),'prazo m\u00ednimo',1,240); hi=integer(payload.get('max'),'prazo m\u00e1ximo',lo,240)
                at=datetime.now(timezone.utc)
                iso=lambda v:v.isoformat(timespec='milliseconds').replace('+00:00','Z')
                o['eta']={'minMinutes':lo,'maxMinutes':hi,'from':iso(at+timedelta(minutes=lo)),'to':iso(at+timedelta(minutes=hi)),'basis':now,'fulfillment':o['fulfillment']}
                o['acceptedAt']=now; o['status']='accepted'; o['events'].append({'status':'accepted','at':now,'eta':o['eta']})
            elif act=='status':
                to=payload.get('to')
                if to not in TRANSITIONS[o['status']] or to=='accepted': raise Problem('Mudanc\u0327a de etapa inv\u00e1lida.',409)
                if (to=='dispatched' and o['fulfillment']!='delivery') or (o['status']=='ready' and to=='completed' and o['fulfillment']=='delivery'): raise Problem('Etapa incompat\u00edvel com a entrega/retirada.',409)
                if to=='cancelled': o['cancellationReason']=text(payload.get('reason'),'motivo do cancelamento',200)
                o['status']=to; o['events'].append({'status':to,'at':now})
            elif act=='print':
                kind=payload.get('kind'); paper=payload.get('paper')
                allowed=(kind=='cancellation' and o['status']=='cancelled' and bool(o.get('acceptedAt'))) or (kind in ('kitchen','counter') and o['status'] in ('accepted','preparing','ready','dispatched','completed'))
                if not allowed or type(paper) is not int or paper not in (58,80): raise Problem('Via indispon\u00edvel nesta etapa.',409)
                jobs=o.setdefault('printJobs',[]); same=[j for j in jobs if j['kind']==kind]
                if any(j['status']=='requested' for j in same): raise Problem('Confira a tentativa anterior antes de imprimir novamente.',409)
                jobs.append({'id':'print_'+secrets.token_hex(12),'kind':kind,'paper':paper,'sequence':len(same)+1,'status':'requested','requestedAt':now})
            elif act=='print-result':
                j=next((j for j in o.get('printJobs',[]) if j['id']==payload.get('jobId')),None)
                if not j or type(payload.get('success')) is not bool:
                    raise Problem('Tentativa de impressao invalida.',409)
                wanted='confirmed_by_operator' if payload['success'] else 'failed_by_operator'
                if j['status'] == 'requested':
                    j['status']=wanted; j['resolvedAt']=now
                elif j['status'] != wanted:
                    raise Problem('Esta tentativa ja foi resolvida de outra forma.',409)
            else: raise Problem('A\u00e7\u00e3o desconhecida.')
            o['revision']+=1; c.execute('UPDATE orders SET data=? WHERE id=?',(dump(o),oid)); self.audit(c,uid,r['store_id'],'order.'+act,oid)
            return {'order':o}

    def setup_owner(self,email,password,name='Responsável da loja'):
        # One transaction: never leave an orphan user if setup is already complete.
        email=text(email,'e-mail',254).casefold()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise Problem('E-mail inv\u00e1lido.')
        name=text(name,'nome',80)
        if not isinstance(password,str) or not 12<=len(password)<=128: raise Problem('Use uma senha de 12 a 128 caracteres.')
        hashed=PH.hash(password); uid='usr_'+secrets.token_hex(12)
        with self.connect(True) as c:
            if c.execute('SELECT 1 FROM members WHERE store_id=?',('cantinho',)).fetchone(): raise Problem('O Cantinho j\u00e1 tem respons\u00e1vel.',409)
            if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): raise Problem('N\u00e3o foi poss\u00edvel criar a conta com estes dados.',409)
            c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,email,name,hashed,utc()))
            c.execute('INSERT INTO members VALUES(?,?)',(uid,'cantinho'))
            self.audit(c,uid,'cantinho','owner.setup')
