import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

const $=id=>document.getElementById(id);
const titles={everyday:['A little room to breathe.','An everyday mix on Indore’s real streets.'],rush:['The evening commute.','More arrivals. The same road space.'],rain:['When the monsoon arrives.','A scripted slowdown around LIG Square.'],roadworks:['One lane changes everything.','Explore a capacity restriction on the approach.']};
const names={car:'Car',motorcycle:'Motorcycle',auto:'Auto-rickshaw',erickshaw:'E-rickshaw',bus:'City bus',delivery:'Delivery van'};
let snapshot=null,previous=null,lastReceived=performance.now(),world,selected=null,following=false,run=null,busy=false,mode='3d',lastSelectedPosition=null;
let history=[],lastChartTime=-1,retries=0,socket;
const canvas=$('world'), viewport=$('viewport');
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'high-performance'});}catch(error){$('loading').innerHTML='<b>WebGL is unavailable</b><span>Open this page in Chrome or Edge with hardware acceleration enabled.</span>';throw error;}
renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.setClearColor('#dfe6d7');renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.95;
const scene=new THREE.Scene();scene.background=new THREE.Color('#dfe6d7');scene.fog=new THREE.Fog('#dfe6d7',1250,2800);
const camera=new THREE.PerspectiveCamera(43,1,1,6000);camera.position.set(230,330,350);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.dampingFactor=.08;controls.target.set(0,0,0);controls.maxPolarAngle=Math.PI*.475;controls.minDistance=35;controls.maxDistance=2300;
scene.add(new THREE.HemisphereLight('#ffffff','#a3b090',1.45));
const sun=new THREE.DirectionalLight('#fff3d5',1.9);sun.position.set(-380,650,260);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-650,right:650,top:650,bottom:-650,near:1,far:1500});sun.shadow.bias=-.0006;scene.add(sun);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(7500,7500),new THREE.MeshStandardMaterial({color:'#dfe5d5',roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.08;ground.receiveShadow=true;scene.add(ground);
const matrices=new THREE.Object3D();const batches={};const streetSigns=[];const vehicleIndex=new Map();
const halo=new THREE.Mesh(new THREE.RingGeometry(3,3.45,40),new THREE.MeshBasicMaterial({color:'#db8245',side:THREE.DoubleSide}));halo.rotation.x=-Math.PI/2;halo.position.y=.5;halo.visible=false;scene.add(halo);

function toast(message){$('toast').textContent=message;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),4200);}
function geometryFrom(parts){
 const pos=[],normal=[],color=[];
 for(const [geometry,tint] of parts){const geo=geometry.index?geometry.toNonIndexed():geometry,c=new THREE.Color(tint),a=geo.attributes.position,n=geo.attributes.normal;for(let i=0;i<a.count;i++){pos.push(a.getX(i),a.getY(i),a.getZ(i));normal.push(n.getX(i),n.getY(i),n.getZ(i));color.push(c.r,c.g,c.b);}geo.dispose();}
 const result=new THREE.BufferGeometry();result.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));result.setAttribute('normal',new THREE.Float32BufferAttribute(normal,3));result.setAttribute('color',new THREE.Float32BufferAttribute(color,3));return result;
}
function meshFromVertices(pos,colors,roughness=1){const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));geo.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geo.computeVertexNormals();const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({vertexColors:true,roughness,side:THREE.DoubleSide}));mesh.receiveShadow=true;scene.add(mesh);return mesh;}
function ribbons(){
 const pos=[],colors=[];function triangle(points,tint){const c=new THREE.Color(tint);for(const p of points){pos.push(...p);colors.push(c.r,c.g,c.b);}}
 function ribbon(points,width,height,tint){for(let i=1;i<points.length;i++){let [ax,az]=points[i-1],[bx,bz]=points[i];az=-az;bz=-bz;const len=Math.hypot(bx-ax,bz-az);if(len<.01)continue;const dx=-(bz-az)/len*width/2,dz=(bx-ax)/len*width/2;const a=[ax+dx,height,az+dz],b=[ax-dx,height,az-dz],c=[bx+dx,height,bz+dz],d=[bx-dx,height,bz-dz];triangle([a,b,c],tint);triangle([b,d,c],tint);}}
 // Junction pavement comes from SUMO's real intersection polygons.
 for(const junction of world.junctions){if(junction.shape.length<3)continue;const shape=junction.shape.map(p=>new THREE.Vector2(p[0],p[1]));const tris=THREE.ShapeUtils.triangulateShape(shape,[]);for(const tri of tris)triangle(tri.map(i=>[shape[i].x,.03,-shape[i].y]),'#899084');}
 for(const road of world.roads){if(road.internal)continue;for(const lane of road.lanes){ribbon(lane.shape,lane.width+.55,.04,'#c3cab8');ribbon(lane.shape,lane.width-.08,.07,'#59675e');}
  if(road.lanes.length>1){for(let l=0;l<road.lanes.length-1;l++){const a=road.lanes[l],b=road.lanes[l+1];if(a.shape.length!==b.shape.length)continue;const line=a.shape.map((p,i)=>[(p[0]+b.shape[i][0])/2,(p[1]+b.shape[i][1])/2]);for(let i=1;i<line.length;i++){const p=line[i-1],q=line[i],length=Math.hypot(q[0]-p[0],q[1]-p[1]);for(let t=2;t<length;t+=9){const end=Math.min(length,t+3.5);ribbon([[p[0]+(q[0]-p[0])*t/length,p[1]+(q[1]-p[1])*t/length],[p[0]+(q[0]-p[0])*end/length,p[1]+(q[1]-p[1])*end/length]],.13,.095,'#d7dbcd');}}}}
 }
 meshFromVertices(pos,colors);
}
function buildings(){
 const parts=[],palette=['#e2dfcd','#d4d6c5','#e8e5d5','#d3d9c9'];
 for(const b of world.buildings){const points=b.shape;if(points.length<4)continue;const shape=new THREE.Shape(points.map(p=>new THREE.Vector2(p[0],p[1])));const geom=new THREE.ExtrudeGeometry(shape,{depth:b.height,bevelEnabled:false,steps:1,curveSegments:1});geom.rotateX(-Math.PI/2);geom.translate(0,.15,0);parts.push([geom,palette[b.tone]]);}
 const mesh=new THREE.Mesh(geometryFrom(parts),new THREE.MeshStandardMaterial({vertexColors:true,roughness:1}));mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);
 const parks=[];
 for(const park of world.parks){const shape=new THREE.Shape(park.shape.map(p=>new THREE.Vector2(p[0],p[1])));const g=new THREE.ShapeGeometry(shape);g.rotateX(-Math.PI/2);g.translate(0,.12,0);parks.push([g,'#b4c59f']);}
 if(parks.length){const m=new THREE.Mesh(geometryFrom(parks),new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,side:THREE.DoubleSide}));scene.add(m);}
}
function vehicleGeometry(kind){
 const parts=[];const add=(g,color,x=0,y=0,z=0)=>{g.translate(x,y,z);parts.push([g,color]);};
 const box=(w,h,l,color,x,y,z)=>add(new THREE.BoxGeometry(w,h,l),color,x,y,z);
 const wheel=(x,z,r=.32)=>{const g=new THREE.CylinderGeometry(r,r,.22,8);g.rotateZ(Math.PI/2);add(g,'#343d3b',x,r,z);};
 if(kind==='motorcycle'){
  box(.48,.45,1.5,'#ec9250',0,.65,0);box(.35,.22,.6,'#37444a',0,.96,.1);wheel(0,-.68,.34);wheel(0,.68,.34);
  box(.48,.65,.35,'#344755',0,1.32,.05);add(new THREE.SphereGeometry(.22,7,5),'#efe1b6',0,1.82,-.08);box(.9,.08,.08,'#253938',0,1.1,-.65);
 }else if(kind==='auto'||kind==='erickshaw'){
  const e=kind==='erickshaw';box(1.25,.55,2.35,e?'#3a9d86':'#dbc04a',0,.68,0);box(1.31,.15,1.9,e?'#bce2ce':'#eacb4f',0,1.8,.16);
  box(1.05,.45,.3,'#375b54',0,1.07,-.83);box(1.05,.35,.65,'#405148',0,1.1,.58);
  for(const x of [-.54,.54])for(const z of [-.68,.85])box(.06,.75,.06,'#526357',x,1.36,z);
  wheel(0,-.9);wheel(-.62,.78);wheel(.62,.78);
 }else{
  const bus=kind==='bus',van=kind==='delivery',w=bus?2.45:van?1.85:1.7,l=bus?10.1:van?5:4.1;
  const c=bus?'#bf6953':van?'#ad9aba':'#6785a0';
  box(w,.66,l,c,0,.82,0);box(w*.92,bus?1.35:van?1.35:.6,l*(bus?.92:van?.68:.56),bus?'#e1c3a5':van?'#d5cbdd':'#d6e0dc',0,bus?1.8:van?1.65:1.42,van?.45:.12);
  box(w*.94,bus?.6:.42,l*(bus?.88:van?.27:.5),'#557474',0,bus?2.05:1.53,van?-1.45:.08);
  box(w*.75,.14,.1,'#f9edd0',0,.91,-l/2-.02);box(w*.75,.12,.1,'#a45b50',0,.86,l/2+.02);
  for(const x of [-w/2,w/2])for(const z of [-l*.32,l*.32])wheel(x,z,bus?.46:.32);
 }
 return geometryFrom(parts);
}
function createVehicles(){for(const type of Object.keys(names)){const mesh=new THREE.InstancedMesh(vehicleGeometry(type),new THREE.MeshStandardMaterial({vertexColors:true,roughness:.8}),1600);mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);mesh.count=0;mesh.castShadow=true;mesh.frustumCulled=false;mesh.userData.type=type;mesh.userData.ids=[];batches[type]=mesh;scene.add(mesh);}}
const signalMesh=new THREE.InstancedMesh(new THREE.SphereGeometry(.9,6,5),new THREE.MeshBasicMaterial({color:'white'}),3000);signalMesh.count=0;signalMesh.frustumCulled=false;scene.add(signalMesh);
function updateSignals(signals){let index=0;for(const signal of signals){for(let i=0;i<signal.positions.length;i++){const p=signal.positions[i];if(!p||index>=3000)continue;matrices.position.set(p[0],1.1,-p[1]);matrices.rotation.set(0,0,0);matrices.scale.setScalar(1);matrices.updateMatrix();signalMesh.setMatrixAt(index,matrices.matrix);signalMesh.setColorAt(index,new THREE.Color('Gg'.includes(signal.state[i])?'#a6ce76':signal.state[i]==='y'?'#f3c063':'#df7d66'));index++;}}signalMesh.count=index;signalMesh.instanceMatrix.needsUpdate=true;if(signalMesh.instanceColor)signalMesh.instanceColor.needsUpdate=true;}
function streetLabels(){const seen=new Set();for(const r of world.roads){if(!r.name||r.internal||seen.has(r.name)||r.shape.length<2)continue;const p=r.shape[Math.floor(r.shape.length/2)];if(Math.hypot(...p)>800)continue;seen.add(r.name);const c=document.createElement('canvas');c.width=512;c.height=64;const ctx=c.getContext('2d');ctx.font='500 22px Segoe UI';ctx.fillStyle='#687b60';ctx.textAlign='center';ctx.fillText(r.name.toUpperCase(),256,37);const tex=new THREE.CanvasTexture(c);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,depthTest:false,transparent:true,opacity:.75}));sprite.position.set(p[0],5,-p[1]);sprite.scale.set(115,14,1);scene.add(sprite);streetSigns.push(sprite);if(seen.size>=12)break;}}
function home(top=false){following=false;lastSelectedPosition=null;controls.target.set(0,0,0);camera.position.set(...(top?[0,800,.1]:[230,330,350]));controls.update();mode=top?'2d':'3d';$('camera-top').classList.toggle('selected',top);$('camera-3d').classList.toggle('selected',!top);}
new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(viewport);
function render(){requestAnimationFrame(render);if(snapshot){const interval=previous?Math.max(.02,(snapshot.sim_time_s-previous.sim_time_s)/Math.max(snapshot.rate,1)):0;const fraction=snapshot.paused?1:Math.min(1,(performance.now()-lastReceived)/(interval*1000||250));const old=new Map(previous?.vehicles.map(v=>[v.id,v])||[]);const counts={};vehicleIndex.clear();for(const v of snapshot.vehicles){const mesh=batches[v.type];if(!mesh)continue;const index=counts[v.type]||0;if(index>=1600)continue;const p=old.get(v.id);let x=v.x,y=v.y,angle=v.angle;if(p&&fraction<1){x=p.x+(v.x-p.x)*fraction;y=p.y+(v.y-p.y)*fraction;const turn=((v.angle-p.angle+540)%360)-180;angle=p.angle+turn*fraction;}const length={car:4.3,motorcycle:2,auto:2.7,erickshaw:2.8,bus:10.5,delivery:5.2}[v.type];x-=Math.sin(angle*Math.PI/180)*length/2;y-=Math.cos(angle*Math.PI/180)*length/2;matrices.position.set(x,.15,-y);matrices.rotation.set(0,-angle*Math.PI/180,0);matrices.scale.setScalar(1);matrices.updateMatrix();mesh.setMatrixAt(index,matrices.matrix);mesh.userData.ids[index]=v.id;counts[v.type]=index+1;vehicleIndex.set(v.id,{...v,x,y});}for(const [type,mesh]of Object.entries(batches)){mesh.count=counts[type]||0;mesh.instanceMatrix.needsUpdate=true;}
 if(selected&&vehicleIndex.has(selected)){const v=vehicleIndex.get(selected);halo.visible=true;halo.position.set(v.x,.4,-v.y);if(following){const p=new THREE.Vector3(v.x,0,-v.y);if(lastSelectedPosition){const delta=p.clone().sub(lastSelectedPosition);camera.position.add(delta);controls.target.add(delta);}else{const offset=camera.position.clone().sub(controls.target).normalize().multiplyScalar(80);controls.target.copy(p);camera.position.copy(p).add(offset);}lastSelectedPosition=p;}}else{halo.visible=false;if(selected){$('vehicle-detail').textContent='Vehicle has left the network.';following=false;}}}
 controls.update();for(const sign of streetSigns)sign.visible=camera.position.distanceTo(controls.target)>220;const label=new THREE.Vector3(0,2,0).project(camera);$('lig-label').style.left=`${(label.x*.5+.5)*viewport.clientWidth+13}px`;$('lig-label').style.top=`${(-label.y*.5+.5)*viewport.clientHeight-32}px`;$('lig-label').style.visibility=label.z<1?'visible':'hidden';renderer.render(scene,camera);}
function pulse(){const c=$('spark'),w=c.clientWidth,h=c.clientHeight,ratio=devicePixelRatio;c.width=w*ratio;c.height=h*ratio;const ctx=c.getContext('2d');ctx.scale(ratio,ratio);ctx.strokeStyle='#d8e0cb';ctx.lineWidth=.5;for(let y=8;y<h;y+=17){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}if(history.length<2)return;const points=history.slice(-100),max=Math.max(40,...points);ctx.beginPath();points.forEach((v,i)=>{const x=i/(points.length-1)*w,y=h-4-v/max*(h-8);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.strokeStyle='#76915c';ctx.lineWidth=1.5;ctx.stroke();ctx.lineTo(w,h);ctx.lineTo(0,h);ctx.closePath();const g=ctx.createLinearGradient(0,0,0,h);g.addColorStop(0,'#7d985b35');g.addColorStop(1,'#7d985b00');ctx.fillStyle=g;ctx.fill();}
function state(data){if(data.error){toast(data.error);$('connection').textContent='ENGINE ERROR';return;}if(!data.ready)return;const changed=run!==data.run_id;if(changed){run=data.run_id;previous=null;history=[];lastChartTime=-1;selected=null;following=false;$('inspector').hidden=true;}else if(snapshot?.sim_time_s!==data.sim_time_s)previous=snapshot;
 if(!snapshot||changed||snapshot.sim_time_s!==data.sim_time_s)lastReceived=performance.now();snapshot=data;
 $('active').textContent=data.metrics.active;$('speed').innerHTML=`${data.metrics.mean_speed_kph??'—'}<em> km/h</em>`;$('queued').textContent=data.metrics.queued;$('arrived').textContent=data.metrics.arrived;$('cohort').textContent=`of ${data.metrics.scheduled} scheduled`;
 $('clock').textContent=`${String(Math.floor(data.sim_time_s/60)).padStart(2,'0')}:${String(Math.floor(data.sim_time_s%60)).padStart(2,'0')}`;$('progress').style.width=`${data.sim_time_s/1200*100}%`;
 $('play').innerHTML=data.paused?'▶ <span>Run simulation</span>':'Ⅱ <span>Pause simulation</span>';$('play').disabled=busy||data.ended;$('step').disabled=busy||!data.paused||data.ended;
 document.querySelectorAll('[data-rate]').forEach(b=>b.classList.toggle('selected',Number(b.dataset.rate)===data.rate));document.querySelectorAll('[data-scenario]').forEach(b=>b.classList.toggle('active',b.dataset.scenario===data.scenario));
 $('scene-title').textContent=titles[data.scenario][0];$('scene-description').textContent=titles[data.scenario][1];$('run-id').textContent=`SEED ${data.seed} · ${data.run_id.toUpperCase()}`;
 $('incident').hidden=!data.incident_active;$('incident-title').textContent=data.scenario==='rain'?'Rain restriction active':'Approach restriction active';
 const faults=data.metrics.collisions+data.metrics.teleports;$('integrity').textContent=faults?`${data.metrics.collisions} collision involvements · ${data.metrics.teleports} teleports`:'No collisions or teleports';$('integrity-dot').style.background=faults?'#c77549':'#8caa73';$('run-note').textContent=data.ended?(data.metrics.arrived===data.metrics.scheduled&&!faults?'Completed cohort · export the record':'Incomplete / integrity faults · inspect export'):`Fixed signals · ${data.metrics.not_departed} not yet departed · ${data.metrics.co2_kg.toFixed(2)} kg modeled CO₂`;
 if(lastChartTime!==data.sim_time_s){lastChartTime=data.sim_time_s;history.push(data.metrics.mean_speed_kph||0);if(history.length>500)history.shift();pulse();}
 if(selected&&vehicleIndex.has(selected)){const v=vehicleIndex.get(selected);$('vehicle-detail').textContent=`${(v.speed*3.6).toFixed(1)} km/h · ${v.waiting.toFixed(0)} s current waiting`;}updateSignals(data.signals);$('loading').hidden=true;
}
async function command(payload){if(busy)return;busy=true;document.querySelectorAll('.scenario,#reset,#play,#step').forEach(b=>b.disabled=true);if(payload.action==='reset'){$('loading').hidden=false;$('loading').querySelector('b').textContent='Resetting the experiment';$('loading').querySelector('span').textContent='Building the seeded cohort and warming up 120 simulated seconds…';}try{const res=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await res.json();if(!res.ok)throw Error(data.detail||'Control rejected');state(data);}catch(error){toast(error.message);}finally{busy=false;document.querySelectorAll('.scenario,#reset,#play,#step').forEach(b=>b.disabled=false);if(snapshot)state(snapshot);$('loading').hidden=true;}}
function connect(){socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);socket.onopen=()=>{retries=0;$('connection').classList.add('online');$('connection').innerHTML='<i></i> ENGINE CONNECTED';};socket.onmessage=e=>state(JSON.parse(e.data));socket.onclose=()=>{$('connection').classList.remove('online');$('connection').innerHTML='<i></i> RECONNECTING';toast('Connection lost. Waiting for the local engine…');setTimeout(connect,Math.min(8000,1000*2**retries++));};}
function seed(){const n=Number($('seed').value);if(!Number.isInteger(n)||n<0||n>999999){toast('Use a seed from 0 to 999999');return null;}return n;}
document.querySelectorAll('[data-scenario]').forEach(b=>b.onclick=()=>{const n=seed();if(n!==null)command({action:'reset',scenario:b.dataset.scenario,seed:n});});
$('reset').onclick=()=>{const n=seed();if(n!==null)command({action:'reset',scenario:snapshot?.scenario||'rush',seed:n});};
$('play').onclick=()=>command({action:snapshot?.paused?'play':'pause'});$('step').onclick=()=>command({action:'step'});$('clear').onclick=()=>command({action:'clear_incident'});
document.querySelectorAll('[data-rate]').forEach(b=>b.onclick=()=>command({action:'set_rate',rate:Number(b.dataset.rate)}));
$('camera-3d').onclick=()=>home(false);$('camera-top').onclick=()=>home(true);$('camera-home').onclick=()=>home(mode==='2d');
$('zoom-in').onclick=()=>camera.position.copy(controls.target.clone().add(camera.position.clone().sub(controls.target).multiplyScalar(.75)));
$('zoom-out').onclick=()=>camera.position.copy(controls.target.clone().add(camera.position.clone().sub(controls.target).multiplyScalar(1.3)));
$('close-inspector').onclick=()=>{selected=null;following=false;$('inspector').hidden=true;};$('follow').onclick=()=>{following=!following;lastSelectedPosition=null;$('follow').textContent=following?'Stop following':'Follow vehicle ↗';};
const raycaster=new THREE.Raycaster();let down=null;canvas.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);canvas.addEventListener('click',e=>{if(down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const rect=canvas.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),camera);let hit=raycaster.intersectObjects(Object.values(batches))[0];if(!hit){let nearest=12;for(const [id,v] of vehicleIndex){const p=new THREE.Vector3(v.x,1,-v.y).project(camera);if(p.z>1)continue;const distance=Math.hypot((p.x*.5+.5)*rect.width+rect.left-e.clientX,(-p.y*.5+.5)*rect.height+rect.top-e.clientY);if(distance<nearest){nearest=distance;hit={object:{userData:{type:v.type,ids:[id]}},instanceId:0};}}}if(hit){selected=hit.object.userData.ids[hit.instanceId];following=false;lastSelectedPosition=null;$('inspector').hidden=false;$('vehicle-name').textContent=`${names[hit.object.userData.type]} · ${selected.split('.').pop()}`;$('follow').textContent='Follow vehicle ↗';const v=vehicleIndex.get(selected);$('vehicle-detail').textContent=v?`${(v.speed*3.6).toFixed(1)} km/h · ${v.waiting.toFixed(0)} s current waiting`:'';}});
try{const response=await fetch('/api/world');if(!response.ok)throw Error('Cannot load the road network');world=await response.json();ribbons();buildings();streetLabels();createVehicles();render();connect();}catch(error){$('loading').querySelector('b').textContent='Unable to load the world';$('loading').querySelector('span').textContent=error.message;console.error(error);}
