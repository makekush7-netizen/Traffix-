import test from 'node:test';

import assert from 'node:assert/strict';

import {commandEnvelope,commandId,previewEvent,observationRows,scenarioSettings,registrationPayload,prepareAndStart,accessReason,eventRoads,comparisonPair} from './protocol.mjs';

test('LAN command identities and revision use authoritative run',()=>{

 const id=commandId();assert.match(id,/^[a-f0-9-]{36}$/);

 assert.equal(commandEnvelope({revision:3,run:{run_id:'r'}},{action:'pause'},id).expected_revision,3);

 assert.throws(()=>commandEnvelope(null,{action:'pause'}));

});

test('preview preserves worker event identity and normalized schedule',()=>{

 const e=previewEvent({status:'applied',state:{event_preview:{event_id:'event.1',start_s:50,end_s:80,kind:'rain'}}});

 assert.equal(e.duration_s,30);assert.equal(e.event_id,'event.1');

 assert.throws(()=>previewEvent({status:'applied',state:{}}));

});

test('unknown sensor rows never become clear; no source stays zero',()=>{

 assert.deepEqual(observationRows({}),[]);

 const rows=observationRows({simulated_sensors:[{movements:[{incoming_lane:'edge_1_0',queue:1,upstream_capacity:5,fresh:false}]}]});

 assert.equal(rows[0].edge_id,'edge_1');assert.equal(rows[0].slowdown,null);assert.equal(rows[0].coverage,'stale');

});

test('finite settings reject invalid input',()=>{

 assert.equal(scenarioSettings('explore',180,180).mode,'explore');

 for(const args of [['invalid',1,1],['experiment',0,1],['experiment',NaN,1],['experiment',1,3601]])assert.throws(()=>scenarioSettings(...args));

});


test('registration cannot select admin role and validates identity and confirmation',()=>{
 assert.deepEqual(registrationPayload(' team.user ','longpassword','longpassword'),{username:'team.user',password:'longpassword',request_operator:true});
 for(const args of [['Admin','longpassword','longpassword'],['a','longpassword','longpassword'],['team','short','short'],['team','longpassword','mismatch']])assert.throws(()=>registrationPayload(...args));
});

test('guided preparation waits for acknowledged reset before resume',async()=>{
 const actions=[];const result=await prepareAndStart(async p=>{actions.push(p.action);return {status:'applied'};},{action:'reset'});
 assert.deepEqual(actions,['reset','resume']);assert.equal(result.status,'applied');
 const failed=[];assert.equal(await prepareAndStart(async p=>{failed.push(p.action);return undefined;},{action:'reset'}),undefined);assert.deepEqual(failed,['reset']);
});
test('viewer and conflicting lease explain why actions are unavailable',()=>{
 assert.match(accessReason({role:'viewer'},null,true,false),/Viewer/);
 assert.match(accessReason({role:'operator',id:'a'},{holder:'b'},true,false),/b/);
 assert.match(accessReason({role:'operator',id:'a'},null,false,false),/Disconnected/);
});

test('guided preparation never reports running after rejected resume',async()=>{
 const result=await prepareAndStart(async p=>({status:p.action==='reset'?'applied':'rejected'}),{action:'reset'});assert.equal(result,undefined);
});

test('event roads use demand routes, readable names and explicit search',()=>{
 const world={routes:[['a']],roads:[{id:'a',name:'Market Road'},{id:'b',name:'Other Road'},{id:':a',internal:true}]};
 assert.deepEqual(eventRoads(world).map(r=>r.id),['a']);
 assert.deepEqual(eventRoads(world,'Other').map(r=>r.id),['b']);
});

test('comparison chooses fixed baseline in either navigation direction',()=>{
 assert.deepEqual(comparisonPair({run_id:'b',policy:'fixed'},{run_id:'r',policy:'bounded'}),{baseline:'b',response:'r'});
 assert.deepEqual(comparisonPair({run_id:'r',policy:'bounded'},{run_id:'b',policy:'fixed'}),{baseline:'b',response:'r'});
 assert.throws(()=>comparisonPair({run_id:'r',policy:'pressure'},{run_id:'x',policy:'bounded'}));
 assert.match(accessReason({role:'viewer',operator_requested:true},null,true,false),/requested/);
});

test('response policy is acknowledged before a prepared run starts',async()=>{
 const actions=[];
 await prepareAndStart(async p=>{actions.push(p);return {status:'applied'};},{action:'reset'},'bounded');
 assert.deepEqual(actions.map(p=>p.action),['reset','controller','resume']);
 assert.equal(actions[1].policy,'bounded');
 const blocked=[];
 assert.equal(await prepareAndStart(async p=>{blocked.push(p.action);return {status:p.action==='controller'?'rejected':'applied'};},{action:'reset'},'bounded'),undefined);
 assert.deepEqual(blocked,['reset','controller']);
});

import {phoneMapRows} from './protocol.mjs';
test('phone coverage maps bridge IDs to roads and never invents absent observations',()=>{const world={roads:[{id:'road.a'},{id:'road.b'}]};assert.deepEqual(phoneMapRows(world,{observations:[]}),[]);assert.deepEqual(phoneMapRows(world,{observations:[{edge_id:'edge.lig.1',coverage:'fresh',slowdown:.6}]}),[{edge_id:'road.b',coverage:'fresh',slowdown:.6}]);assert.deepEqual(phoneMapRows(world,{observations:[{edge_id:'unknown',coverage:'fresh'}]}),[]);});
