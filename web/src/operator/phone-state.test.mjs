import test from 'node:test';
import assert from 'node:assert/strict';
import {PhoneAcknowledgements} from './phone-state.mjs';
test('consent awaits matching applied ACK and rejection retains confirmed consent',()=>{
 const state=new PhoneAcknowledgements();state.request('on','probe.toggle',{enabled:true});
 assert.equal(state.reporting,false);assert.equal(state.acknowledge({in_reply_to:'other',status:'applied'}),null);
 state.acknowledge({in_reply_to:'on',status:'applied'});assert.equal(state.reporting,true);
 state.request('off','probe.toggle',{enabled:false});state.acknowledge({in_reply_to:'off',status:'rejected'});
 assert.equal(state.reporting,true);assert.equal(state.has('probe.toggle'),false);
});
test('decision remains pending until its ACK; disconnect clears consent and pending actions',()=>{
 const state=new PhoneAcknowledgements();state.reporting=true;state.request('accept','driver.decision',{choice:'accept'});
 assert.equal(state.has('driver.decision'),true);
 assert.equal(state.acknowledge({in_reply_to:'accept',status:'rejected',reason:'expired_advisory'}).applied,false);
 state.request('retry','driver.decision',{choice:'accept'});state.reset();
 assert.equal(state.reporting,false);assert.equal(state.has('driver.decision'),false);
 assert.equal(state.acknowledge({in_reply_to:'retry',status:'applied',reason:'route_applied'}),null);
});
