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


export function registrationPayload(username,password,confirmation){
 const name=username.trim();
 if(!/^[a-z][a-z0-9_.-]{2,31}$/.test(name))throw Error('Use a lowercase team username of 3–32 characters, starting with a letter.');
 if(password.length<8||password.length>256)throw Error('Password must contain 8–256 characters.');
 if(password!==confirmation)throw Error('Passwords do not match.');
 return {username:name,password,request_operator:true};
}

export async function prepareAndStart(send,payload,policy='fixed'){
 const reset=await send(payload);if(reset?.status!=='applied')return undefined;
 if(policy!=='fixed'){
  const selected=await send({action:'controller',policy});
  if(selected?.status!=='applied')return undefined;
 }
 const resumed=await send({action:'resume'});
 return resumed?.status==='applied'?resumed:undefined;
}
export function accessReason(identity,lease,connected,replay){
 if(!connected)return 'Disconnected. Actions stay disabled until a fresh host snapshot arrives.';
 if(replay)return 'Recorded run: read only. Return to live to change the shared host.';
 if(identity?.role==='viewer'&&identity.bootstrap)return 'Host-configured viewer access. You can inspect traffic and results. Join with your own account or ask the host owner for operator access.';
 if(identity?.role==='viewer'&&identity.operator_requested)return 'Operator access requested. The owner approves it in Control → Team access. Sign out and sign in after approval.';
 if(identity?.role!=='operator')return 'Viewer access: you can inspect the scene and results. Operator access requires owner approval; sign in again after approval.';
 if(lease?.holder&&lease.holder!==identity.id)return 'Shared control is held by '+lease.holder+'. Ask them to release it or wait for lease expiry.';
 return lease?.holder===identity.id?'You control this run. Changes are applied by the simulation host.':'Start automatically requests available control. Other operators keep their existing lease.';
}

export function eventRoads(world,query=''){
 const routeEdges=new Set((world?.routes||[]).flat()),q=query.trim().toLowerCase();
 return (world?.roads||[]).filter(r=>!r.internal&&(q?(r.name||'').toLowerCase().includes(q)||r.id.toLowerCase().includes(q):routeEdges.has(r.id)))
  .sort((a,b)=>(a.name||a.id).localeCompare(b.name||b.id));
}
export function comparisonPair(current,other){
 if(current.policy==='fixed'&&other.policy!=='fixed')return {baseline:current.run_id,response:other.run_id};
 if(current.policy!=='fixed'&&other.policy==='fixed')return {baseline:other.run_id,response:current.run_id};
 throw Error('Choose one fixed baseline and one response policy.');
}
