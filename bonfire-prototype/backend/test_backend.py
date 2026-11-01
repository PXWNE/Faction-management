import os, tempfile, unittest
from cryptography.fernet import Fernet

TMP=tempfile.NamedTemporaryFile(delete=False); TMP.close()
os.environ['BONFIRE_DB_PATH']=TMP.name
os.environ['BONFIRE_TOKEN_SECRET']='test-secret-'+'x'*48
os.environ['BONFIRE_FERNET_KEY']=Fernet.generate_key().decode()
os.environ['TORN_FACTION_ID']='12345'
from fastapi.testclient import TestClient
import app

class BackendTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.client=TestClient(app.app); cls.client.__enter__()
 @classmethod
 def tearDownClass(cls): cls.client.__exit__(None,None,None)
 def test_full_leadership_workflow(self):
  c=self.client
  r=c.post('/api/bootstrap',json={'username':'admin','password':'Long-enough-test-password-123'}); self.assertEqual(r.status_code,200,r.text)
  token=r.json()['token']; h={'Authorization':'Bearer '+token}
  self.assertEqual(c.post('/api/bootstrap',json={'username':'other','password':'Long-enough-test-password-123'}).status_code,409)
  r=c.post('/api/users',headers=h,json={'username':'treasurer','password':'Another-long-password-123','roles':['treasurer']}); self.assertEqual(r.status_code,201,r.text)
  login=c.post('/api/auth/login',json={'username':'treasurer','password':'Another-long-password-123'}).json(); th={'Authorization':'Bearer '+login['token']}
  with app.db() as con:
   con.execute('INSERT INTO members VALUES(?,?,?,?)',(777,'Test Player',1,app.now()))
  r=c.post('/api/wars',headers=h,json={'id':'war-1','opponent':'Test opponent','start_at':'2026-10-01T00:00:00Z','end_at':'2026-10-02T00:00:00Z','status':'draft','income':10000,'source_state':'complete'}); self.assertEqual(r.status_code,200,r.text)
  calc={'valid':True,'lines':[{'id':777,'name':'Test Player','amount':8000}],'total':8000,'deficit':0}
  r=c.post('/api/settlements',headers=h,json={'war_id':'war-1','rules':{'supply':10,'reserve':10},'calculation':calc,'source_hash':'hash-v1'}); self.assertEqual(r.status_code,200,r.text); sid=r.json()['id']
  r=c.post(f'/api/settlements/{sid}/approve',headers=h); self.assertEqual(r.status_code,200,r.text)
  r=c.post('/api/payment-intents',headers=th,json={'war_id':'war-1','settlement_id':sid,'player_id':777,'amount':3000,'method':'give','idempotency_key':'intent-key-0001'}); self.assertEqual(r.status_code,201,r.text)
  self.assertIn('giveMoneyTo=777',r.json()['link'])
  with app.db() as con:
   event_time=int(__import__('time').time()+2); con.execute('INSERT INTO source_events VALUES(?,?,?,?,?,?,0,?)',('torn-news-1','giveFunds_unclassified',None,None,app.datetime.fromtimestamp(event_time,app.timezone.utc).isoformat(),'{"id":"torn-news-1","text":"review fixture","timestamp":'+str(event_time)+'}',app.now()))
  r=c.post('/api/reconciliation/torn-news-1/classify',headers=th,json={'player_id':777,'amount':3000}); self.assertEqual(r.status_code,200,r.text); self.assertTrue(r.json()['consumed'])
  r=c.post('/api/payment-intents',headers=th,json={'war_id':'war-1','settlement_id':sid,'player_id':777,'amount':3000,'method':'payday','idempotency_key':'intent-key-0002'}); self.assertEqual(r.status_code,201,r.text)
  r=c.post('/api/payments/manual',headers={**th,'Idempotency-Key':'manual-payment-0001'},json={'player_id':777,'amount':3000,'occurred_at':app.now(),'reference':'Treasurer confirmed Torn transfer'}); self.assertEqual(r.status_code,201,r.text)
  r2=c.post('/api/payments/manual',headers={**th,'Idempotency-Key':'manual-payment-0001'},json={'player_id':777,'amount':3000,'occurred_at':app.now(),'reference':'Treasurer confirmed Torn transfer'}); self.assertEqual(r2.status_code,201,r2.text); self.assertEqual(r2.json()['id'],r.json()['id'])
  pid=r.json()['id']; r=c.post(f'/api/payments/{pid}/reverse',headers=th,json={'reason':'Incorrect local reconciliation record'}); self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(c.get('/api/payments?war_id=war-1',headers=th).status_code,200)
 def test_auth_required(self): self.assertEqual(self.client.get('/api/members').status_code,401)

if __name__=='__main__': unittest.main()
