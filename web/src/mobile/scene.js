import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const theme=getComputedStyle(document.documentElement);
const colours=Object.fromEntries(['unknown','observed','slow','alert'].map(k=>[k,theme.getPropertyValue('--'+k).trim()]));
function geometryFrom(parts){
 const pos=[],normal=[],color=[];
 for(const [geometry,tint] of parts){const geo=geometry.index?geometry.toNonIndexed():geometry,c=new THREE.Color(tint),a=geo.attributes.position,n=geo.attributes.normal;for(let i=0;i<a.count;i++){pos.push(a.getX(i),a.getY(i),a.getZ(i));normal.push(n.getX(i),n.getY(i),n.getZ(i));color.push(c.r,c.g,c.b);}geo.dispose();}
 const result=new THREE.BufferGeometry();result.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));result.setAttribute('normal',new THREE.Float32BufferAttribute(normal,3));result.setAttribute('color',new THREE.Float32BufferAttribute(color,3));return result;
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

export class DemoScene{
 constructor(world,canvas,viewport,fps){
  this.world=world;this.models=new Map();this.labels=new Map();this.rings=new Map();this.spans=new Map();this.colours=new Map();this.pulses=new Map();this.fps=fps;this.low=false;this.followId=null;
  this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.setClearColor(0,0);this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  this.scene=new THREE.Scene();this.scene.fog=new THREE.Fog('#203945',600,1700);this.camera=new THREE.PerspectiveCamera(43,1,1,3500);this.controls=new OrbitControls(this.camera,canvas);this.controls.enableDamping=true;this.controls.maxPolarAngle=Math.PI*.48;this.controls.minDistance=25;this.controls.maxDistance=1300;this.home(false);
  this.scene.add(new THREE.HemisphereLight('#d8edf3','#20333c',1.7));const sun=new THREE.DirectionalLight('#ffe9bf',1.8);sun.position.set(-280,500,280);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-600,right:600,top:600,bottom:-600,near:1,far:1400});sun.shadow.bias=-.001;this.scene.add(sun);this.sun=sun;
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(5500,5500),new THREE.MeshStandardMaterial({color:'#203944',roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.15;ground.receiveShadow=true;this.scene.add(ground);
  this.build();this.vehicleGeometries=Object.fromEntries(['car','motorcycle','auto','erickshaw','bus','delivery'].map(k=>[k,vehicleGeometry(k)]));this.vehicleMaterial=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.8});this.time=performance.now();this.frames=0;
  new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}).observe(viewport);
  const render=()=>{requestAnimationFrame(render);const now=performance.now();for(const m of this.models.values()){if(m.visible){m.position.lerp(m.userData.target,.28);let turn=((m.userData.angle-m.rotation.y+Math.PI*3)%(Math.PI*2))-Math.PI;m.rotation.y+=turn*.28;}}
   for(const [id,label] of this.labels){const model=this.models.get(id);if(model?.visible){label.position.copy(model.position).add(new THREE.Vector3(0,10,0));const ring=this.rings.get(id);ring.position.set(model.position.x,.3,model.position.z);}}
   if(this.followId&&this.models.get(this.followId)?.visible){const p=this.models.get(this.followId).position;this.controls.target.lerp(p,.07);this.camera.position.lerp(p.clone().add(new THREE.Vector3(55,70,80)),.045);}
   if(!this.low&&this.pulses.size){for(const [edge,until] of this.pulses){this.paint(edge,this.colours.get(edge)||'unknown',1+.12*Math.sin(now/140));if(now>=until){this.pulses.delete(edge);this.paint(edge,this.colours.get(edge)||'unknown');}}}
   this.controls.update();this.renderer.render(this.scene,this.camera);this.frames++;if(now-this.time>=2000){this.fps(this.frames*1000/(now-this.time));this.frames=0;this.time=now;}
  };render();
 }
 build(){
  const positions=[],colors=[];const tri=(points,color)=>{const c=new THREE.Color(color);for(const p of points){positions.push(...p);colors.push(c.r,c.g,c.b);}};
  for(const road of this.world.roads){if(road.internal||!road.shape.some(p=>Math.hypot(...p)<800))continue;const start=colors.length;
   for(const lane of road.lanes){for(let i=1;i<lane.shape.length;i++){let [ax,az]=lane.shape[i-1],[bx,bz]=lane.shape[i];az=-az;bz=-bz;const len=Math.hypot(bx-ax,bz-az);if(!len)continue;const dx=-(bz-az)/len*lane.width/2,dz=(bx-ax)/len*lane.width/2,a=[ax+dx,.05,az+dz],b=[ax-dx,.05,az-dz],c=[bx+dx,.05,bz+dz],d=[bx-dx,.05,bz-dz];tri([a,b,c],colours.unknown);tri([b,d,c],colours.unknown);}}
   this.spans.set(road.contract_edge_id,[start,colors.length]);this.colours.set(road.contract_edge_id,'unknown');
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.computeVertexNormals();this.roadGeometry=g;this.scene.add(new THREE.Mesh(g,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide})));
  const parts=[],palette=['#425d66','#3b515f','#5a7077','#344a55'];
  for(const b of this.world.buildings){if(!b.shape.some(p=>Math.hypot(...p)<650))continue;const shape=new THREE.Shape(b.shape.map(p=>new THREE.Vector2(p[0],p[1]))),geo=new THREE.ExtrudeGeometry(shape,{depth:b.height,bevelEnabled:false,steps:1,curveSegments:1});geo.rotateX(-Math.PI/2);geo.translate(0,.1,0);parts.push([geo,palette[b.tone]]);}
  if(parts.length){const mesh=new THREE.Mesh(geometryFrom(parts),new THREE.MeshStandardMaterial({vertexColors:true,roughness:1}));mesh.castShadow=true;mesh.receiveShadow=true;this.scene.add(mesh);}
  const names=new Set();for(const r of this.world.roads){if(!r.name||names.has(r.name)||r.internal)continue;const p=r.shape[Math.floor(r.shape.length/2)];if(Math.hypot(...p)>450)continue;names.add(r.name);const label=this.label(r.name.toUpperCase(),'#9cb6c2');label.position.set(p[0],6,-p[1]);label.scale.set(100,10,1);this.scene.add(label);if(names.size>=8)break;}
 }
 label(text,color='#e2f8e9'){const c=document.createElement('canvas');c.width=512;c.height=80;const ctx=c.getContext('2d');ctx.font='bold 25px Traffix, Arial';ctx.textAlign='center';ctx.fillStyle=color;ctx.fillText(text,256,48);return new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,depthTest:false}));}
 paint(edge,kind,brightness=1){const span=this.spans.get(edge);if(!span)return;const c=new THREE.Color(colours[kind]||colours.unknown).multiplyScalar(brightness),array=this.roadGeometry.attributes.color.array;for(let i=span[0];i<span[1];i+=3){array[i]=c.r;array[i+1]=c.g;array[i+2]=c.b;}this.roadGeometry.attributes.color.needsUpdate=true;}
 frame(state,sessions,observations,roles){
  if(this.run!==state.run_id){this.run=state.run_id;this.followId=null;for(const edge of this.colours.keys()){this.colours.set(edge,'unknown');this.paint(edge,'unknown');}this.pulses.clear();}
  const active=new Set();for(const v of state.vehicles){active.add(v.id);let m=this.models.get(v.id);if(!m){m=new THREE.Mesh(this.vehicleGeometries[v.type],this.vehicleMaterial);m.userData.target=new THREE.Vector3();this.scene.add(m);this.models.set(v.id,m);m.position.set(v.x,.15,-v.y);}m.visible=true;m.userData.target.set(v.x,.15,-v.y);m.userData.angle=-v.angle*Math.PI/180;}
  for(const [id,m] of this.models)m.visible=active.has(id);
  const bound=new Set(sessions.map(s=>s.vehicle_id));for(const id of bound){if(!this.labels.has(id)){const label=this.label('YOU · '+(roles[id]||id).toUpperCase());label.scale.set(45,7,1);this.labels.set(id,label);this.scene.add(label);const ring=new THREE.Mesh(new THREE.RingGeometry(3.8,4.25,32),new THREE.MeshBasicMaterial({color:'#b2eccb',side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;this.rings.set(id,ring);this.scene.add(ring);}}
  for(const [id,label] of this.labels){label.visible=bound.has(id)&&active.has(id);this.rings.get(id).visible=label.visible;}
  const rows=new Map(observations.map(o=>[o.edge_id,o]));for(const edge of this.colours.keys()){const row=rows.get(edge),kind=row?.coverage==='fresh'&&row.slowdown!==null?(row.slowdown>=.7?'alert':row.slowdown>=.4?'slow':'observed'):'unknown';if(this.colours.get(edge)!==kind){if(kind!=='unknown')this.pulses.set(edge,performance.now()+1400);this.colours.set(edge,kind);this.paint(edge,kind);}}
 }
 home(top){this.followId=null;this.controls.target.set(-110,0,-90);this.camera.position.set(...(top?[-110,520,-89.9]:[70,240,190]));this.controls.update();}
 focus(id){if(id)this.followId=id;}
 reduced(enabled){this.low=enabled;this.renderer.setPixelRatio(enabled?1:Math.min(devicePixelRatio,1.5));this.renderer.shadowMap.enabled=!enabled;for(const edge of this.colours.keys())this.paint(edge,this.colours.get(edge));if(enabled)this.pulses.clear();}
}
