// User-visible consent and decisions are confirmed only by their matching ACK.
export class PhoneAcknowledgements {
 constructor(){this.reset();}
 reset(){this.reporting=false;this.pending=new Map();}
 request(id,type,payload){if(id)this.pending.set(id,{type,payload});}
 acknowledge(payload){
  const request=this.pending.get(payload.in_reply_to);if(!request)return null;
  this.pending.delete(payload.in_reply_to);
  const applied=payload.status==='applied';
  if(request.type==='probe.toggle'&&applied)this.reporting=request.payload.enabled;
  return {...request,applied,reason:payload.reason};
 }
 has(type){return [...this.pending.values()].some(row=>row.type===type);}
}
