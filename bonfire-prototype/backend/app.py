"""The Bonfire API: persistent, faction-scoped backend for the Bonfire UI.

This service never sends Torn money. Torn API access is read-only; payment records
are posted only from verified faction giveFunds news or explicit treasurer evidence.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, sqlite3, time, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv('BONFIRE_DB_PATH', os.path.join(APP_DIR, 'bonfire.sqlite3'))
TOKEN_SECRET = os.getenv('BONFIRE_TOKEN_SECRET', '')
FERNET_KEY = os.getenv('BONFIRE_FERNET_KEY', '')
FACTION_ID = os.getenv('TORN_FACTION_ID', '')
TOKEN_TTL = int(os.getenv('BONFIRE_TOKEN_TTL', '43200'))

app = FastAPI(title='The Bonfire API', version='1.0.0')
origins = [x.strip() for x in os.getenv('BONFIRE_CORS_ORIGINS', '').split(',') if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=['GET','POST','PUT','PATCH','DELETE'], allow_headers=['Authorization','Content-Type','Idempotency-Key'])

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_roles(user_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL, PRIMARY KEY(user_id,role));
CREATE TABLE IF NOT EXISTS members(player_id INTEGER PRIMARY KEY, name TEXT NOT NULL, current INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wars(id TEXT PRIMARY KEY, external_id TEXT, opponent TEXT NOT NULL DEFAULT '', start_at TEXT, end_at TEXT, status TEXT NOT NULL DEFAULT 'collecting', income INTEGER NOT NULL DEFAULT 0, source_state TEXT NOT NULL DEFAULT 'not_synced', raw_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settlements(id TEXT PRIMARY KEY, war_id TEXT NOT NULL REFERENCES wars(id), revision INTEGER NOT NULL, state TEXT NOT NULL, rules_json TEXT NOT NULL, calculation_json TEXT NOT NULL, source_hash TEXT NOT NULL, approved_by TEXT REFERENCES users(id), approved_at TEXT, created_at TEXT NOT NULL, UNIQUE(war_id,revision));
CREATE TABLE IF NOT EXISTS obligations(id TEXT PRIMARY KEY, settlement_id TEXT NOT NULL REFERENCES settlements(id), war_id TEXT NOT NULL REFERENCES wars(id), player_id INTEGER NOT NULL REFERENCES members(player_id), approved_amount INTEGER NOT NULL CHECK(approved_amount>=0), created_at TEXT NOT NULL, UNIQUE(settlement_id,player_id));
CREATE TABLE IF NOT EXISTS payment_intents(id TEXT PRIMARY KEY, war_id TEXT NOT NULL REFERENCES wars(id), settlement_id TEXT NOT NULL REFERENCES settlements(id), player_id INTEGER NOT NULL REFERENCES members(player_id), amount INTEGER NOT NULL CHECK(amount>0), method TEXT NOT NULL CHECK(method IN ('give','payday')), status TEXT NOT NULL, expires_at TEXT NOT NULL, idempotency_key TEXT UNIQUE NOT NULL, created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_intent_per_player ON payment_intents(player_id) WHERE status='pending';
CREATE TABLE IF NOT EXISTS source_events(id TEXT PRIMARY KEY, kind TEXT NOT NULL, player_id INTEGER, amount INTEGER, occurred_at TEXT, raw_json TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY, intent_id TEXT REFERENCES payment_intents(id), war_id TEXT NOT NULL REFERENCES wars(id), settlement_id TEXT NOT NULL REFERENCES settlements(id), player_id INTEGER NOT NULL REFERENCES members(player_id), amount INTEGER NOT NULL CHECK(amount>0), source_event_id TEXT UNIQUE REFERENCES source_events(id), evidence TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'posted', created_by TEXT REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reversals(id TEXT PRIMARY KEY, payment_id TEXT NOT NULL REFERENCES payments(id), reason TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, actor_id TEXT, action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, detail_json TEXT NOT NULL, request_id TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS payments_war_player ON payments(war_id,player_id);
CREATE INDEX IF NOT EXISTS audit_created ON audit(created_at);
'''

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA journal_mode=WAL')
    try:
        yield con
        if con.in_transaction: con.commit()
    except Exception:
        if con.in_transaction: con.rollback()
        raise
    finally: con.close()

@app.on_event('startup')
def startup():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    with db() as c: c.executescript(SCHEMA)
    if not TOKEN_SECRET or len(TOKEN_SECRET) < 32: print('WARNING: set BONFIRE_TOKEN_SECRET to a random 32+ character secret')
    if not FERNET_KEY: print('WARNING: set BONFIRE_FERNET_KEY; Torn key storage is disabled')


def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def password_hash(password: str) -> str:
    salt=secrets.token_bytes(16); digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1)
    return 'scrypt$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(digest).decode()
def verify_password(password: str, stored: str) -> bool:
    try:
        alg,salt,digest=stored.split('$'); got=hashlib.scrypt(password.encode(),salt=base64.urlsafe_b64decode(salt),n=2**14,r=8,p=1)
        return alg=='scrypt' and hmac.compare_digest(got,base64.urlsafe_b64decode(digest))
    except Exception: return False

def token_for(user_id: str):
    if len(TOKEN_SECRET)<32: raise HTTPException(503,'Authentication secret is not configured.')
    payload={'sub':user_id,'exp':int(time.time())+TOKEN_TTL,'jti':uid()}
    raw=base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).decode().rstrip('=')
    sig=base64.urlsafe_b64encode(hmac.new(TOKEN_SECRET.encode(),raw.encode(),hashlib.sha256).digest()).decode().rstrip('=')
    return raw+'.'+sig

def current_user(authorization: str|None=Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Sign in required.')
    try:
        raw,sig=authorization[7:].split('.',1); expected=base64.urlsafe_b64encode(hmac.new(TOKEN_SECRET.encode(),raw.encode(),hashlib.sha256).digest()).decode().rstrip('=')
        if not hmac.compare_digest(sig,expected): raise ValueError()
        payload=json.loads(base64.urlsafe_b64decode(raw+'='*((4-len(raw)%4)%4)))
        if payload['exp']<time.time(): raise ValueError()
        with db() as c: user=c.execute('SELECT id,username,active FROM users WHERE id=?',(payload['sub'],)).fetchone(); roles=[r['role'] for r in c.execute('SELECT role FROM user_roles WHERE user_id=?',(payload['sub'],))]
        if not user or not user['active']: raise ValueError()
        return {'id':user['id'],'username':user['username'],'roles':roles}
    except Exception: raise HTTPException(401,'Invalid or expired session.')

def require(*roles):
    def dep(user=Depends(current_user)):
        if not set(roles).intersection(user['roles']): raise HTTPException(403,'Your leadership role cannot perform this action.')
        return user
    return dep

def audit(c, actor, action, entity_type, entity_id, detail=None, request_id=None):
    c.execute('INSERT INTO audit VALUES(?,?,?,?,?,?,?,?)',(uid(),actor,action,entity_type,str(entity_id),json.dumps(detail or {},separators=(',',':')),request_id,now()))

def encryptor():
    if not FERNET_KEY: raise HTTPException(503,'Credential encryption is not configured.')
    try: return Fernet(FERNET_KEY.encode())
    except Exception: raise HTTPException(503,'BONFIRE_FERNET_KEY is invalid.')

def posted_paid(c,war_id,player_id):
    row=c.execute('''SELECT COALESCE(SUM(p.amount),0) n FROM payments p LEFT JOIN reversals r ON r.payment_id=p.id WHERE p.war_id=? AND p.player_id=? AND p.status='posted' AND r.id IS NULL''',(war_id,player_id)).fetchone()
    return int(row['n'])

class Login(BaseModel): username:str; password:str
class Bootstrap(BaseModel): username:str; password:str
class UserCreate(BaseModel): username:str; password:str=Field(min_length=12); roles:list[str]
class TornKey(BaseModel): key:str=Field(min_length=16,max_length=256)
class WarIn(BaseModel): id:str; external_id:str|None=None; opponent:str=''; start_at:str|None=None; end_at:str|None=None; status:str='collecting'; income:int=Field(default=0,ge=0); source_state:str='not_synced'; raw:dict=Field(default_factory=dict)
class SettlementIn(BaseModel): war_id:str; rules:dict; calculation:dict; source_hash:str
class IntentIn(BaseModel): war_id:str; player_id:int; amount:int=Field(gt=0); method:str='give'; settlement_id:str; idempotency_key:str=Field(min_length=8,max_length=128)
class EvidenceIn(BaseModel): player_id:int; amount:int=Field(gt=0); occurred_at:str; reference:str=Field(min_length=3); source_event_id:str|None=None
class ClassifyEvent(BaseModel): player_id:int=Field(gt=0); amount:int=Field(gt=0)
class ReverseIn(BaseModel): reason:str=Field(min_length=5,max_length=500)

@app.get('/health')
def health(): return {'ok':True,'service':'bonfire-api','time':now()}

@app.post('/api/bootstrap')
def bootstrap(body:Bootstrap):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']:
            raise HTTPException(409,'Bootstrap is already complete.')
        user=uid(); c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(user,body.username,password_hash(body.password),1,now()))
        for role in ['admin','leader','officer','treasurer','viewer']: c.execute('INSERT INTO user_roles VALUES(?,?)',(user,role))
        audit(c,user,'bootstrap','user',user,{'username':body.username})
    return {'user_id':user,'token':token_for(user),'username':body.username,'roles':['admin','leader','officer','treasurer','viewer']}

@app.post('/api/auth/login')
def login(body:Login):
    with db() as c: row=c.execute('SELECT * FROM users WHERE username=?',(body.username,)).fetchone()
    if not row or not row['active'] or not verify_password(body.password,row['password_hash']): raise HTTPException(401,'Invalid username or password.')
    user=current_user_from_id(row['id'])
    return {'token':token_for(row['id']),'user':user}

def current_user_from_id(user_id):
    with db() as c:
        u=c.execute('SELECT id,username FROM users WHERE id=?',(user_id,)).fetchone(); roles=[r['role'] for r in c.execute('SELECT role FROM user_roles WHERE user_id=?',(user_id,))]
    return {'id':u['id'],'username':u['username'],'roles':roles}

@app.get('/api/auth/me')
def me(user=Depends(current_user)): return user

@app.post('/api/users',status_code=201)
def create_user(body:UserCreate,user=Depends(require('admin','leader'))):
    allowed={'admin','leader','officer','treasurer','viewer'}
    if not body.roles or not set(body.roles)<=allowed: raise HTTPException(400,'Invalid role assignment.')
    if 'admin' in body.roles and 'admin' not in user['roles']: raise HTTPException(403,'Only an administrator can grant administrator access.')
    with db() as c:
        if c.execute('SELECT 1 FROM users WHERE username=?',(body.username,)).fetchone(): raise HTTPException(409,'Username already exists.')
        ident=uid(); c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(ident,body.username,password_hash(body.password),1,now()))
        c.executemany('INSERT INTO user_roles VALUES(?,?)',[(ident,r) for r in sorted(set(body.roles))]); audit(c,user['id'],'user.created','user',ident,{'roles':body.roles})
    return {'id':ident,'username':body.username,'roles':body.roles}

@app.put('/api/settings/torn-key')
def set_torn_key(body:TornKey,user=Depends(require('admin','leader'))):
    token=encryptor().encrypt(body.key.encode()).decode()
    with db() as c:
        c.execute("INSERT INTO settings(key,value) VALUES('torn_key_enc',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(token,))
        c.execute("INSERT INTO settings(key,value) VALUES('torn_key_verified','0') ON CONFLICT(key) DO UPDATE SET value='0'")
        audit(c,user['id'],'torn_key.updated','settings','torn_key',{'masked':'********'})
    return {'configured':True,'masked':'••••••••','note':'Stored encrypted on the server; never returned.'}

@app.get('/api/settings/torn-key')
def torn_key_status(user=Depends(require('admin','leader'))):
    with db() as c: row=c.execute("SELECT 1 FROM settings WHERE key='torn_key_enc'").fetchone()
    with db() as c: verified=c.execute("SELECT value FROM settings WHERE key='torn_key_verified'").fetchone()
    return {'configured':bool(row),'verified':bool(verified and verified['value']=='1'),'faction_id_configured':bool(FACTION_ID)}

@app.post('/api/settings/torn-key/verify')
async def verify_torn_key(user=Depends(require('admin','leader'))):
    if not FACTION_ID: raise HTTPException(503,'Set TORN_FACTION_ID before verifying faction ownership.')
    info=await torn_get('key/info')
    key_info=info.get('info') or {}; owner=key_info.get('user') or {}; access=key_info.get('access') or {}; selections=(key_info.get('selections') or {}).get('faction') or []
    actual=str(owner.get('faction_id') or '')
    if actual!=str(FACTION_ID):
        raise HTTPException(409,'The stored API key does not belong to the configured faction. No sync was started.')
    if not access.get('faction') or 'members' not in selections or 'news' not in selections:
        raise HTTPException(409,'The Torn key is missing faction access, members or news selections. Use a Limited/Custom key with faction permissions and the giveFunds news category.')
    with db() as c:
        c.execute("INSERT INTO settings(key,value) VALUES('torn_key_verified','1') ON CONFLICT(key) DO UPDATE SET value='1'")
        audit(c,user['id'],'torn_key.verified','settings','torn_key',{'faction_id':actual})
    return {'verified':True,'faction_id':actual,'owner_id':owner.get('id'),'faction_access':True,'selections':selections}

async def torn_get(path, params=None):
    with db() as c: row=c.execute("SELECT value FROM settings WHERE key='torn_key_enc'").fetchone()
    if not row: raise HTTPException(409,'Torn API key is not configured.')
    try: key=encryptor().decrypt(row['value'].encode()).decode()
    except (InvalidToken,ValueError): raise HTTPException(500,'Stored Torn credential cannot be decrypted.')
    query={'comment':'Bonfire'}
    if params: query.update(params)
    async with httpx.AsyncClient(timeout=20,headers={'User-Agent':'TheBonfireFactionManagement/1.0','Authorization':f'ApiKey {key}'}) as client:
        response=await client.get('https://api.torn.com/v2/'+path.lstrip('/'),params=query)
    if response.status_code==429: raise HTTPException(503,'Torn API rate limit reached; retry later.')
    if response.status_code>=400: raise HTTPException(502,'Torn API request failed; credential or permissions may be invalid.')
    data=response.json()
    if data.get('error'): raise HTTPException(502,'Torn API returned an error: '+str(data['error'].get('error','unknown')))
    return data

def require_verified_torn_key():
    with db() as c: row=c.execute("SELECT value FROM settings WHERE key='torn_key_verified'").fetchone()
    if not row or row['value']!='1': raise HTTPException(409,'Verify the stored Torn key belongs to this faction before syncing.')

@app.post('/api/sync/roster')
async def sync_roster(user=Depends(require('admin','leader','officer'))):
    require_verified_torn_key()
    data=await torn_get('faction/members')
    members=data.get('members',[])
    with db() as c:
        for m in members:
            pid=int(m.get('id') or m.get('player_id') or 0); name=str(m.get('name') or '').strip()
            if pid>0 and name: c.execute('INSERT INTO members(player_id,name,current,updated_at) VALUES(?,?,1,?) ON CONFLICT(player_id) DO UPDATE SET name=excluded.name,current=1,updated_at=excluded.updated_at',(pid,name,now()))
        ids=[int(m.get('id') or m.get('player_id') or 0) for m in members]
        if ids: c.execute('UPDATE members SET current=0 WHERE player_id NOT IN ('+','.join('?' for _ in ids)+')',ids)
        audit(c,user['id'],'sync.roster','members','faction',{'received':len(members)})
    return {'synced':len(members),'fetched_at':now()}

@app.get('/api/members')
def get_members(user=Depends(current_user)):
    with db() as c: rows=c.execute('SELECT player_id,name,current,updated_at FROM members ORDER BY name COLLATE NOCASE').fetchall()
    return [dict(r) for r in rows]

@app.post('/api/wars')
def upsert_war(body:WarIn,user=Depends(require('admin','leader','officer'))):
    if body.status not in {'collecting','draft','in_review','approved','partially_paid','paid','archived'}: raise HTTPException(400,'Invalid settlement state.')
    with db() as c:
        c.execute('''INSERT INTO wars VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET external_id=excluded.external_id,opponent=excluded.opponent,start_at=excluded.start_at,end_at=excluded.end_at,status=excluded.status,income=excluded.income,source_state=excluded.source_state,raw_json=excluded.raw_json,updated_at=excluded.updated_at''',(body.id,body.external_id,body.opponent,body.start_at,body.end_at,body.status,body.income,body.source_state,json.dumps(body.raw),now()))
        audit(c,user['id'],'war.upserted','war',body.id,{'source_state':body.source_state})
    return {'id':body.id,'saved':True}

@app.get('/api/wars')
def list_wars(user=Depends(current_user)):
    with db() as c: rows=c.execute('SELECT * FROM wars ORDER BY COALESCE(start_at,updated_at) DESC').fetchall()
    return [{**dict(r),'raw':json.loads(r['raw_json'])} for r in rows]

@app.post('/api/settlements')
def save_settlement(body:SettlementIn,user=Depends(require('admin','leader','officer'))):
    if not body.calculation.get('valid',False): raise HTTPException(400,'Only a valid calculation can be saved.')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        war=c.execute('SELECT * FROM wars WHERE id=?',(body.war_id,)).fetchone()
        if not war: raise HTTPException(404,'War not found.')
        if war['status'] in ('approved','archived'): raise HTTPException(409,'Approved or archived war is immutable; create a new revision.')
        rev=c.execute('SELECT COALESCE(MAX(revision),0)+1 n FROM settlements WHERE war_id=?',(body.war_id,)).fetchone()['n']
        sid=uid(); c.execute('INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,body.war_id,rev,'draft',json.dumps(body.rules),json.dumps(body.calculation),body.source_hash,None,None,now()))
        audit(c,user['id'],'settlement.draft_saved','settlement',sid,{'war_id':body.war_id,'revision':rev})
    return {'id':sid,'revision':rev,'state':'draft'}

@app.post('/api/settlements/{settlement_id}/approve')
def approve(settlement_id:str,user=Depends(require('admin','leader'))):
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); s=c.execute('SELECT * FROM settlements WHERE id=?',(settlement_id,)).fetchone()
        if not s: raise HTTPException(404,'Settlement not found.')
        w=c.execute('SELECT * FROM wars WHERE id=?',(s['war_id'],)).fetchone()
        if w['end_at'] is None or w['source_state']!='complete': raise HTTPException(409,'Approval blocked: war must be finished and source coverage complete.')
        existing=c.execute("SELECT 1 FROM settlements WHERE war_id=? AND state='approved'",(s['war_id'],)).fetchone()
        if existing: raise HTTPException(409,'An approved revision already exists. Withdraw or revise it first.')
        calc=json.loads(s['calculation_json']); lines=calc.get('lines',[])
        if not lines or calc.get('deficit',0)>0: raise HTTPException(409,'Settlement has no payable lines or is underfunded.')
        for line in lines:
            pid=int(line['id']); amount=int(Decimal(str(line['amount'])).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
            if amount<0 or not c.execute('SELECT 1 FROM members WHERE player_id=?',(pid,)).fetchone(): raise HTTPException(409,'Unknown payout recipient; import roster before approval.')
            c.execute('INSERT INTO obligations VALUES(?,?,?,?,?,?)',(uid(),s['id'],s['war_id'],pid,amount,now()))
        c.execute("UPDATE settlements SET state='approved',approved_by=?,approved_at=? WHERE id=?",(user['id'],now(),settlement_id))
        c.execute("UPDATE wars SET status='approved',updated_at=? WHERE id=?",(now(),s['war_id']))
        audit(c,user['id'],'settlement.approved','settlement',settlement_id,{'revision':s['revision'],'total':int(calc.get('total',0))})
    return {'approved':True,'settlement_id':settlement_id,'revision':s['revision'],'transfer_sent':False}

@app.get('/api/settlements/{settlement_id}')
def settlement_detail(settlement_id:str,user=Depends(current_user)):
    with db() as c:
        s=c.execute('SELECT * FROM settlements WHERE id=?',(settlement_id,)).fetchone()
        if not s: raise HTTPException(404,'Settlement not found.')
        obligations=c.execute('SELECT o.*,m.name,m.current FROM obligations o JOIN members m USING(player_id) WHERE settlement_id=? ORDER BY m.name',(settlement_id,)).fetchall()
        payments=c.execute("SELECT p.*,r.reason reversal_reason FROM payments p LEFT JOIN reversals r ON r.payment_id=p.id WHERE p.settlement_id=? ORDER BY p.created_at",(settlement_id,)).fetchall()
    return {**dict(s),'rules':json.loads(s['rules_json']),'calculation':json.loads(s['calculation_json']),'obligations':[dict(o) for o in obligations],'payments':[dict(p) for p in payments]}

@app.post('/api/payment-intents',status_code=201)
def create_intent(body:IntentIn,user=Depends(require('admin','leader','treasurer')),idem: str|None=Header(default=None,alias='Idempotency-Key')):
    if body.method not in ('give','payday'): raise HTTPException(400,'Invalid payment method.')
    key=idem or body.idempotency_key
    with db() as c:
        prior=c.execute('SELECT * FROM payment_intents WHERE idempotency_key=?',(key,)).fetchone()
        if prior: return dict(prior)
        c.execute('BEGIN IMMEDIATE')
        c.execute("UPDATE payment_intents SET status='expired' WHERE status='pending' AND expires_at<=?",(now(),))
        s=c.execute("SELECT * FROM settlements WHERE id=? AND state='approved'",(body.settlement_id,)).fetchone()
        if not s or s['war_id']!=body.war_id: raise HTTPException(409,'An approved settlement is required.')
        m=c.execute('SELECT * FROM members WHERE player_id=?',(body.player_id,)).fetchone()
        if not m or not m['current']: raise HTTPException(409,'Former or unknown members require manual evidence.')
        o=c.execute('SELECT approved_amount FROM obligations WHERE settlement_id=? AND player_id=?',(body.settlement_id,body.player_id)).fetchone()
        if not o: raise HTTPException(404,'No approved obligation for this player.')
        due=int(o['approved_amount'])-posted_paid(c,body.war_id,body.player_id)
        if body.amount>due: raise HTTPException(409,f'Amount exceeds outstanding obligation ({max(due,0)}).')
        existing=c.execute("SELECT id FROM payment_intents WHERE player_id=? AND status='pending' AND expires_at>?",(body.player_id,now())).fetchone()
        if existing: raise HTTPException(409,'A payment is already pending for this player.')
        iid=uid(); expiry=datetime.fromtimestamp(time.time()+600,timezone.utc).isoformat()
        c.execute('INSERT INTO payment_intents VALUES(?,?,?,?,?,?,?,?,?,?,?)',(iid,body.war_id,body.settlement_id,body.player_id,body.amount,body.method,'pending',expiry,key,user['id'],now()))
        audit(c,user['id'],'payment.intent_created','payment_intent',iid,{'player_id':body.player_id,'amount':body.amount,'method':body.method})
    link=(f'https://www.torn.com/factions.php?step=your#/tab=controls&giveMoneyTo={body.player_id}&money={body.amount}' if body.method=='give' else 'https://www.torn.com/factions.php?step=your&type=3#/tab=controls&option=pay-day')
    return {'id':iid,'status':'pending','expires_at':expiry,'link':link,'amount':body.amount,'player_id':body.player_id,'method':body.method,'note':'Opening this link does not record a payment.'}

@app.post('/api/sync/give-funds')
async def sync_give_funds(user=Depends(require('admin','leader','officer','treasurer'))):
    require_verified_torn_key()
    # Torn v2 News objects contain only id, text and timestamp. Persist the raw
    # source first; never invent a player/amount by guessing the news wording.
    data=await torn_get('faction/news',{'cat':'giveFunds','limit':100,'sort':'DESC','striptags':'false'})
    items=data.get('news',[]); inserted=0
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        for item in items:
            raw=json.dumps(item,separators=(',',':')); event_id=str(item.get('id') or hashlib.sha256(raw.encode()).hexdigest())
            occurred=item.get('timestamp')
            if not occurred: continue
            occurred_at=datetime.fromtimestamp(int(occurred),timezone.utc).isoformat()
            cur=c.execute('INSERT OR IGNORE INTO source_events VALUES(?,?,?,?,?,?,0,?)',(event_id,'giveFunds_unclassified',None,None,occurred_at,raw,now()))
            inserted+=cur.rowcount
        audit(c,user['id'],'sync.give_funds','source_events','faction',{'received':len(items),'new_candidates':inserted})
    return {'received':len(items),'new_candidates':inserted,'needs_review':True,'note':'Torn v2 news exposes raw text only. Classify the recipient and amount from the original event before it can match a payment intent.'}

@app.get('/api/reconciliation/candidates')
def reconciliation_candidates(user=Depends(require('admin','leader','treasurer'))):
    with db() as c: rows=c.execute("SELECT * FROM source_events WHERE consumed=0 ORDER BY occurred_at DESC LIMIT 300").fetchall()
    return [{**dict(r),'raw':json.loads(r['raw_json'])} for r in rows]

@app.post('/api/reconciliation/{event_id}/classify')
def classify_event(event_id:str,body:ClassifyEvent,user=Depends(require('admin','leader','treasurer'))):
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); ev=c.execute('SELECT * FROM source_events WHERE id=?',(event_id,)).fetchone()
        if not ev: raise HTTPException(404,'Source event not found.')
        if ev['consumed']: raise HTTPException(409,'Source event has already been allocated.')
        if ev['player_id'] is not None or ev['amount'] is not None: raise HTTPException(409,'Source event has already been classified.')
        c.execute("UPDATE source_events SET player_id=?,amount=?,kind='giveFunds_classified' WHERE id=?",(body.player_id,body.amount,event_id))
        audit(c,user['id'],'reconciliation.classified','source_event',event_id,{'player_id':body.player_id,'amount':body.amount})
    confirmed=match_events()
    with db() as c: updated=c.execute('SELECT * FROM source_events WHERE id=?',(event_id,)).fetchone()
    return {'event_id':event_id,'classified':True,'consumed':bool(updated['consumed']),'confirmed_count':confirmed,'note':'Classification is an officer-reviewed interpretation of Torn news text.'}

def match_events():
    confirmed=0
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        events=c.execute('SELECT * FROM source_events WHERE consumed=0 ORDER BY occurred_at').fetchall()
        for ev in events:
            try: at=datetime.fromisoformat(ev['occurred_at'].replace('Z','+00:00')).timestamp()
            except Exception: continue
            intents=c.execute("SELECT * FROM payment_intents WHERE status IN ('pending','expired') AND player_id=? AND amount=?",(ev['player_id'],ev['amount'])).fetchall()
            matches=[]
            for it in intents:
                try: created=datetime.fromisoformat(it['created_at']).timestamp()
                except Exception: continue
                if at>=created: matches.append(it)
            if len(matches)!=1: continue
            it=matches[0]; obligation=c.execute('SELECT approved_amount FROM obligations WHERE settlement_id=? AND player_id=?',(it['settlement_id'],it['player_id'])).fetchone()
            if not obligation: continue
            due=int(obligation['approved_amount'])-posted_paid(c,it['war_id'],it['player_id'])
            if int(ev['amount'])>due: continue
            pid=uid(); c.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?,?)',(pid,it['id'],it['war_id'],it['settlement_id'],it['player_id'],it['amount'],ev['id'],ev['raw_json'],'posted',it['created_by'],now()))
            c.execute("UPDATE payment_intents SET status='confirmed' WHERE id=?",(it['id'],)); c.execute('UPDATE source_events SET consumed=1 WHERE id=?',(ev['id'],))
            audit(c,it['created_by'],'payment.confirmed_from_api','payment',pid,{'source_event_id':ev['id']}); confirmed+=1
    return confirmed

@app.post('/api/payments/manual',status_code=201)
def manual_payment(body:EvidenceIn,user=Depends(require('admin','leader','treasurer')),idem: str|None=Header(default=None,alias='Idempotency-Key')):
    if not idem: raise HTTPException(400,'Idempotency-Key header is required.')
    with db() as c:
        if len(idem)>128: raise HTTPException(400,'Idempotency-Key must be at most 128 characters.')
        prior=c.execute('SELECT * FROM payments WHERE id=?',(idem,)).fetchone()
        if prior: return dict(prior)
        c.execute('BEGIN IMMEDIATE')
        intent=c.execute("SELECT * FROM payment_intents WHERE player_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1",(body.player_id,)).fetchone()
        if not intent: raise HTTPException(409,'No active payment intent for this member. Create one first.')
        if body.amount>intent['amount']: raise HTTPException(409,'Evidence amount exceeds prepared intent.')
        due=c.execute('SELECT approved_amount FROM obligations WHERE settlement_id=? AND player_id=?',(intent['settlement_id'],body.player_id)).fetchone()['approved_amount']-posted_paid(c,intent['war_id'],body.player_id)
        if body.amount>due: raise HTTPException(409,'Payment exceeds outstanding obligation.')
        if body.source_event_id:
            source=c.execute('SELECT * FROM source_events WHERE id=?',(body.source_event_id,)).fetchone()
            if not source or source['consumed']: raise HTTPException(409,'Source evidence is missing or already allocated.')
            if source['player_id'] is not None and (source['player_id']!=body.player_id or source['amount']!=body.amount): raise HTTPException(409,'Source evidence does not match the payment details.')
            c.execute('UPDATE source_events SET consumed=1 WHERE id=?',(body.source_event_id,))
        pid=idem; c.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?,?)',(pid,intent['id'],intent['war_id'],intent['settlement_id'],body.player_id,body.amount,body.source_event_id,body.reference,'posted',user['id'],now()))
        if body.amount==intent['amount']: c.execute("UPDATE payment_intents SET status='confirmed' WHERE id=?",(intent['id'],))
        audit(c,user['id'],'payment.manually_recorded','payment',pid,{'amount':body.amount,'reference':body.reference})
    return {'id':pid,'status':'posted','amount':body.amount}

@app.post('/api/payments/{payment_id}/reverse')
def reverse_payment(payment_id:str,body:ReverseIn,user=Depends(require('admin','leader','treasurer'))):
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); p=c.execute('SELECT * FROM payments WHERE id=?',(payment_id,)).fetchone()
        if not p: raise HTTPException(404,'Payment not found.')
        if c.execute('SELECT 1 FROM reversals WHERE payment_id=?',(payment_id,)).fetchone(): raise HTTPException(409,'Payment is already reversed.')
        rid=uid(); c.execute('INSERT INTO reversals VALUES(?,?,?,?,?)',(rid,payment_id,body.reason,user['id'],now()))
        audit(c,user['id'],'payment.reversed','payment',payment_id,{'reason':body.reason,'reversal_id':rid})
    return {'reversed':True,'payment_id':payment_id,'note':'This reverses only the local ledger record, not a Torn transfer.'}

@app.get('/api/payments')
def payments(war_id:str|None=None,user=Depends(current_user)):
    with db() as c:
        q='''SELECT p.*,m.name,r.reason reversal_reason FROM payments p JOIN members m USING(player_id) LEFT JOIN reversals r ON r.payment_id=p.id'''; args=()
        if war_id: q+=' WHERE p.war_id=?'; args=(war_id,)
        rows=c.execute(q+' ORDER BY p.created_at DESC',args).fetchall()
    return [dict(r) for r in rows]

@app.get('/api/audit')
def audit_log(limit:int=100,user=Depends(require('admin','leader'))):
    limit=max(1,min(limit,500))
    with db() as c: rows=c.execute('SELECT a.*,u.username actor FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.created_at DESC LIMIT ?',(limit,)).fetchall()
    return [{**dict(r),'detail':json.loads(r['detail_json'])} for r in rows]

@app.get('/api/export/settlement/{settlement_id}.csv')
def export_settlement(settlement_id:str,user=Depends(current_user)):
    import csv,io
    with db() as c:
        s=c.execute('SELECT * FROM settlements WHERE id=?',(settlement_id,)).fetchone()
        if not s: raise HTTPException(404,'Settlement not found.')
        rows=c.execute('''SELECT o.player_id,m.name,o.approved_amount,COALESCE((SELECT SUM(p.amount) FROM payments p LEFT JOIN reversals r ON r.payment_id=p.id WHERE p.settlement_id=o.settlement_id AND p.player_id=o.player_id AND r.id IS NULL),0) paid FROM obligations o JOIN members m USING(player_id) WHERE o.settlement_id=?''',(settlement_id,)).fetchall()
    out=__import__('io').StringIO(); w=csv.writer(out); w.writerow(['Settlement','Revision','Player ID','Player','Approved','Paid','Due','Currency'])
    for r in rows:
        # Formula injection protection for text fields.
        name=str(r['name']); name="'"+name if name.startswith(('=','+','-','@','\t','\r')) else name
        w.writerow([settlement_id,s['revision'],r['player_id'],name,r['approved_amount'],r['paid'],max(0,r['approved_amount']-r['paid']),'Torn dollars'])
    from fastapi.responses import Response
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="bonfire-{settlement_id}.csv"'})
