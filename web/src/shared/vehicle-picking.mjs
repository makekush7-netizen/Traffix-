// CSS pixels, independent of display pixel ratio and render resolution.
export function vehicleClickGesture(pick,threshold=6){
 let start=null;
 const moved=e=>Math.hypot(e.clientX-start.x,e.clientY-start.y)>threshold;
 return {
  down(e){
   if(start||e.button!==0||e.isPrimary===false||e.shiftKey||e.ctrlKey||e.metaKey){start=null;return;}
   start={id:e.pointerId,x:e.clientX,y:e.clientY,dragged:false};
  },
  move(e){if(start&&e.pointerId===start.id&&moved(e))start.dragged=true;},
  up(e){
   if(!start||e.pointerId!==start.id)return;
   const click=e.button===0&&!start.dragged&&!moved(e);start=null;
   if(click)pick({x:e.clientX,y:e.clientY});
  },
  cancel(){start=null;}
 };
}

export function nearbyVehicles(point,candidates,radius=10){
 return candidates.filter(c=>c.visible!==false&&[c.x,c.y,c.z].every(Number.isFinite)&&c.z>=-1&&c.z<=1)
  .map(c=>({...c,distance:Math.hypot(c.x-point.x,c.y-point.y)}))
  .filter(c=>c.distance<=radius).sort((a,b)=>a.distance-b.distance||a.z-b.z);
}
