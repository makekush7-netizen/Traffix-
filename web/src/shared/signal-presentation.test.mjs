import {test} from 'node:test';
import assert from 'node:assert/strict';
import {controllerPresentation,SignalActionTracker} from './signal-presentation.mjs';

const run=(extra={})=>({run_id:'r1',policy:'pressure',sim_time_s:30,signals:[{id:'tls.1'}],simulated_sensors:[{source_id:'tls.1',movements:[{fresh:true}]}],action_log:[],...extra});
test('fixed has no adaptive decoration; policy names do not claim ML or savings',()=>{
 assert.equal(controllerPresentation(run({policy:'fixed'})).adaptive,false);
 for(const policy of ['bounded','actuated','pressure'])assert.equal(controllerPresentation(run({policy})).adaptive,true);
 assert.equal(controllerPresentation(run({policy:'unknown'})).adaptive,false);
 assert.match(controllerPresentation(run()).label,/Pressure/);
});
test('offline, paused, ended and missing observations do not appear actively controlling',()=>{
 assert.equal(controllerPresentation(run(),{connected:false}).status,'disconnected');
 assert.equal(controllerPresentation(run({paused:true})).status,'paused');
 assert.equal(controllerPresentation(run({ended:true})).status,'completed');
 assert.equal(controllerPresentation(run({simulated_sensors:[]})).signals['tls.1'],'unavailable');
 assert.equal(controllerPresentation(run({simulated_sensors:[{source_id:'tls.1',movements:[{fresh:false}]}]})).signals['tls.1'],'unavailable');
 assert.equal(controllerPresentation(run()).signals['tls.1'],'adaptive');
 assert.match(controllerPresentation(run(),{recorded:true}).label,/Recorded/);
});
test('only newly confirmed matching actions flash, not natural greens, initial history or duplicates',()=>{
 const tracker=new SignalActionTracker();
 const extension={kind:'signal_extension',policy:'pressure',tls_id:'tls.1',sim_time_s:20,extension_s:5};
 assert.equal(tracker.update(run({action_log:[extension]})).flash.size,0);
 const complete={kind:'signal_transition_completed',tls_id:'tls.1',sim_time_s:31,target_phase:2};
 const next=run({sim_time_s:32,action_log:[extension,complete]});
 assert.equal(tracker.update(next).flash.has('tls.1'),true);
 assert.equal(tracker.update(next).flash.size,0);
 assert.equal(tracker.update(run({sim_time_s:33,action_log:[...next.action_log,{kind:'signal_transition_started',tls_id:'tls.1',sim_time_s:33}]})).flash.size,0);
 assert.equal(tracker.update(run({sim_time_s:34,action_log:[{...extension,policy:'bounded',sim_time_s:34}]})).flash.size,0);
});
test('reset, replay rewind, policy changes and paused frames clear or suppress historic flashes',()=>{
 const tracker=new SignalActionTracker();tracker.update(run());
 const action={kind:'signal_transition_completed',tls_id:'tls.1',sim_time_s:40,target_phase:2};
 assert.equal(tracker.update(run({run_id:'r2',sim_time_s:41,action_log:[action]})).flash.size,0);
 assert.equal(tracker.update(run({run_id:'r2',policy:'bounded',sim_time_s:42,action_log:[action]})).last,null);
 tracker.update(run({sim_time_s:50}));
 assert.equal(tracker.update(run({sim_time_s:45,action_log:[action]})).flash.size,0);
 assert.equal(tracker.update(run({paused:true,sim_time_s:51,action_log:[{...action,sim_time_s:51}]})).flash.size,0);
 assert.equal(tracker.update(run({sim_time_s:52,action_log:[{...action,sim_time_s:51}]})).flash.size,0);
});
