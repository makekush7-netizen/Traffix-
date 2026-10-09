import test from 'node:test';

import assert from 'node:assert/strict';

import {commandEnvelope,commandId,previewEvent,observationRows,scenarioSettings,registrationPayload} from './protocol.mjs';

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
