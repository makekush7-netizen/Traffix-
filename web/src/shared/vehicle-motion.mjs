// Render a short buffered history; never invent motion after the last received snapshot.
export class VehicleMotion {
 constructor(delayMs=240){this.delayMs=delayMs;this.frames=[];this.run=null;}
 push(state,wall){
  if(this.run!==state.run_id||state.sim_time_s<this.frames.at(-1)?.sim){this.frames=[];this.run=state.run_id;}
  if(state.paused||state.ended)this.frames=[];
  if(this.frames.at(-1)?.sim===state.sim_time_s)return;
  this.frames.push({wall,sim:state.sim_time_s,vehicles:new Map((state.vehicles||[]).map(v=>[v.id,v]))});
  if(this.frames.length>12)this.frames.shift();
 }
 sample(id,wall){
  if(!this.frames.length)return null;
  const at=wall-this.delayMs;let a=this.frames[0],b=a;
  for(const frame of this.frames){if(frame.wall<=at)a=frame;else{b=frame;break;}b=frame;}
  const p=a.vehicles.get(id),q=b.vehicles.get(id);if(!p)return q||null;if(!q)return p;
  const t=b.wall>a.wall?Math.max(0,Math.min(1,(at-a.wall)/(b.wall-a.wall))):1;
  const turn=((q.angle-p.angle+540)%360)-180;
  return {x:p.x+(q.x-p.x)*t,y:p.y+(q.y-p.y)*t,angle:p.angle+turn*t};
 }
}
