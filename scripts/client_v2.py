"""Authenticated no-UI integration client; never silently retries a mutation."""
import argparse,json,os,urllib.request,uuid

def main():
    p=argparse.ArgumentParser(); p.add_argument('--url',default='http://127.0.0.1:8005'); p.add_argument('--username',default='operator'); args=p.parse_args()
    token=None
    def request(path,body=None):
        headers={'Content-Type':'application/json'}
        if token: headers['Authorization']='Bearer '+token
        req=urllib.request.Request(args.url+'/api/v2/'+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
    login=request('auth/login',{'username':args.username,'password':os.environ['TRAFFIX_PASSWORD']}); token=login['token']
    print(json.dumps(request('locations'),indent=2))
    request('lease',{'action':'acquire'})
    state=request('state')
    result=request('commands',{'api_version':'2.0','command_id':str(uuid.uuid4()),'run_id':state['run']['run_id'],
        'expected_revision':state['revision'],'payload':{'action':'pause'}})
    print(json.dumps({k:v for k,v in result.items() if k!='state'},indent=2))
    request('lease',{'action':'release'}); request('auth/revoke',{})
if __name__=='__main__': main()
