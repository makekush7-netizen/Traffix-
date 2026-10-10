// Presentation only: signal colours remain authoritative SUMO indications.
const names={fixed:'Fixed timing · baseline',bounded:'Adaptive control · Queue response',actuated:'Adaptive control · Actuated',pressure:'Adaptive control · Pressure'};
export function controllerPresentation(run={}, {connected=true,recorded=false}={}){
 const adaptive=['bounded','actuated','pressure'].includes(run.policy);
 const status=!connected?'disconnected':run.ended?'completed':run.paused?'paused':'running';
 const signals={};
 for(const signal of run.signals||[]){
  const movements=run.simulated_sensors?.find(s=>s.source_id===signal.id)?.movements;
  signals[signal.id]=status!=='running'?'inactive':!adaptive?'fixed':movements?.length&&movements.every(m=>m.fresh===true)?'adaptive':'unavailable';
 }
 const unavailable=Object.values(signals).filter(s=>s==='unavailable').length;
 return {adaptive,status,signals,label:(recorded?'Recorded · ':'')+(names[run.policy]||'Controller unavailable'),
  detail:status==='disconnected'?'Disconnected · showing last known policy':status==='paused'?'Paused · no new control actions':status==='completed'?'Run ended · no new control actions':adaptive?unavailable?`${unavailable} junction(s) lack fresh observations · fallback required`:'Cyan = adaptive policy enabled · red/amber/green = actual signal': 'Standard signal programme · adaptive response off'};
}
function confirmedActions(run){
 return (run.action_log||[]).filter(a=>Number.isFinite(a.sim_time_s)&&a.sim_time_s<=run.sim_time_s&&a.tls_id&&
  ((a.kind==='signal_extension'&&a.policy===run.policy)||(a.kind==='signal_transition_completed'&&run.policy==='pressure')));
}
const actionKey=a=>JSON.stringify([a.kind,a.tls_id,a.sim_time_s,a.phase,a.target_phase,a.extension_s]);
export class SignalActionTracker{
 update(run,{connected=true}={}){
  const reset=this.run!==run.run_id||this.policy!==run.policy||run.sim_time_s<this.time;
  const selectedAt=Math.max(-Infinity,...(run.action_log||[]).filter(a=>a.kind==='policy_selected'&&a.policy===run.policy&&a.sim_time_s<=run.sim_time_s).map(a=>a.sim_time_s));
  const actions=confirmedActions(run).filter(a=>a.sim_time_s>=selectedAt);
  const keys=new Set(actions.map(actionKey)),flash=new Set();
  if(!reset&&connected&&!run.paused&&!run.ended)for(const a of actions)if(!this.seen.has(actionKey(a)))flash.add(a.tls_id);
  this.run=run.run_id;this.policy=run.policy;this.time=run.sim_time_s;this.seen=keys;
  return {flash,last:actions.at(-1)||null,reset};
 }
}
