// getRandomValues also works on plain LAN HTTP, where randomUUID is unavailable.
export function commandId(random=globalThis.crypto){
 const bytes=random.getRandomValues(new Uint8Array(16));
 bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
 return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
export function commandEnvelope(state,payload,id=commandId()){
 if(!state?.run?.run_id||!Number.isInteger(state.revision))throw Error('A current run is required before changing the simulation.');
 return {api_version:'2.0',command_id:id,run_id:state.run.run_id,expected_revision:state.revision,payload};
}

export function previewEvent(reply){
 const event=reply?.state?.event_preview;
 if(reply?.status!=='applied'||!event?.event_id)throw Error('Host did not validate an event preview.');
 return {...event,duration_s:event.end_s-event.start_s};
}
export function observationRows(run){
 const rows=new Map();
 for(const source of run?.simulated_sensors||[])for(const m of source.movements||[]){
  const edge=m.incoming_edge||m.incoming_lane?.replace(/_\d+$/,'');
  if(!edge)continue;
  const prior=rows.get(edge),row={edge_id:edge,source_type:'simulated_sensor',coverage:m.fresh?'fresh':'stale',slowdown:m.fresh&&m.upstream_capacity>0?Math.min(1,m.queue/m.upstream_capacity):null};
  if(!prior||row.slowdown>prior.slowdown||row.coverage==='stale')rows.set(edge,row);
 }
 return [...rows.values()];
}
export function scenarioSettings(mode,duration,drain){
 if(!['experiment','explore'].includes(mode)||!Number.isFinite(duration)||duration<=0||duration>3600||!Number.isFinite(drain)||drain<0||drain>3600)throw Error('Duration must be 1–3600 seconds; drain 0–3600 seconds.');
 return {mode,duration_s:duration,drain_s:drain,location:'lig'};
}
