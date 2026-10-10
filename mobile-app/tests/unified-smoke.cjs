// Real local SUMO host + actual TypeScript adapter over HTTP/WebSocket.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {TrafficClient} = require('./load-client.cjs');
const host = process.env.TRAFFIX_TEST_HOST || 'http://127.0.0.1:8013';
const accounts = JSON.parse(fs.readFileSync(process.env.TRAFFIX_TEST_ACCOUNTS,'utf8').replace(/^\uFEFF/,''));
async function waitFor(predicate,label){const end=Date.now()+15000;while(!predicate()){assert.ok(Date.now()<end,'Timed out: '+label);await new Promise(r=>setTimeout(r,100));}}
(async()=>{
 const username=Object.keys(accounts)[0];
 const login=await fetch(host+'/api/v2/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password:accounts[username].password})});
 assert.equal(login.status,200);
 const token=(await login.json()).token;
 const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
 const get=async path=>{const r=await fetch(host+path,{headers});assert.ok(r.ok,path+' '+r.status);return r.json();};
 const post=async(path,body)=>{const r=await fetch(host+path,{method:'POST',headers,body:JSON.stringify(body)});assert.ok(r.ok,path+' '+r.status+' '+await r.clone().text());return r.json();};
 const command=async payload=>{await post('/api/v2/lease',{action:'acquire'});const s=await get('/api/v2/state');return post('/api/v2/commands',{api_version:'2.0',command_id:crypto.randomUUID(),run_id:s.run.run_id,expected_revision:s.revision,payload});};
 const client=new TrafficClient(()=>{},()=>{});
 try{
  await command({action:'reset',settings:{mode:'explore',demand_per_hour:1400,duration_s:180,drain_s:900},seed:42});
  let state=await get('/api/v2/state');
  for(let i=0;!state.run.vehicles.length&&i<80;i++){await command({action:'step'});state=await get('/api/v2/state');}
  await client.configure(host);assert.equal(client.apiVersion,'2.0');
  const invite=await post('/api/v2/phones/invites',{});await client.join(invite.join_code);
  await waitFor(()=>client.state.connection==='connected'&&client.state.fresh&&client.state.own,'bound trip and frame');
  assert.ok(client.world.roads.length);assert.ok(client.state.own.route_path.length);
  assert.equal(client.state.sharing,false);
  const before=await get('/api/v2/observations');assert.equal(before.accepted_uplinks,0);
  const raw=await fetch(host+`/api/v2/phones/state?session_id=${client.state.claim.session_id}&run_id=${client.state.claim.run_id}`,{headers:{Authorization:'Bearer '+client.state.claim.token}}).then(r=>r.json());
  const edge=raw.route_path[0];state=await get('/api/v2/state');
  const event={kind:'blockage',edge_id:edge,start_s:state.run.sim_time_s,duration_s:180,severity:.85};
  await command({action:'event_preview',event});await client.pollOwn();assert.equal(client.state.own.events.filter(e=>e.status==='active').length,0);
  await command({action:'event_apply',event});await client.pollOwn();
  const alert=client.state.own.events.find(e=>e.edge_id===edge&&e.status==='active');assert.ok(alert,'operator restriction reaches bound native adapter');
  assert.match(alert.effect,/speed restriction/i);
  assert.equal(client.state.sharing,false,'operator alerts do not imply probe consent');
  client.toggle(true);await waitFor(()=>client.state.sharing&&client.state.samples>0,'confirmed consent and exact probe');
  client.toggle(false);await waitFor(()=>!client.state.sharing&&!client.state.pending,'confirmed withdrawal');
  await command({action:'event_end',event_id:alert.event_id});await client.pollOwn();
  assert.equal(client.state.own.events.filter(e=>e.status==='active').length,0);
  client.suspend();client.connect();await waitFor(()=>client.state.connection==='connected','reconnect');assert.equal(client.state.sharing,false);
  await command({action:'reset',settings:{mode:'explore'},seed:42});await waitFor(()=>client.state.connection==='rejoin','run reset invalidation');
  console.log(JSON.stringify({passed:true,host,actualNativeAdapter:true,transport:'real HTTP/WebSocket',traffic:'real SUMO synthetic demand',checks:['scoped map and route geometry','admin preview has no driver effect','admin apply alerts only bound route','consent stays explicit','validated probe and withdrawal','event end clears alert','reconnect clears consent','reset requires rejoin'],physicalHandset:false},null,2));
 }finally{client.suspend();}
})().catch(error=>{console.error(error);process.exitCode=1;});
