const $=id=>document.getElementById(id);
let advisory;
let follow=true,reconnectTimer;
let claim,seq=Number(sessionStorage.getItem('traffix.seq')||0),ws,frame,ready=false,sharing=false,retries=0,heartbeat,confirmed=0,leaving=false,sent=new Set(),pending=new Map(),world,center=null,zoom=.85,lastServer=0;
function notice(text){$('notice').textContent=text;clearTimeout(notice.timer);notice.timer=setTimeout(()=>$('notice').textContent='',6000);}
function send(type,payload,stamp=null){if(!ready&&type!=='session.hello')return;const n=++seq;sessionStorage.setItem('traffix.seq',seq);const msg={v:1,type,msg_id:`msg.phone.${n}`,run_id:claim.run_id,sender_id:claim.session_id,seq:n,sim_time_s:stamp,payload};ws.send(JSON.stringify(msg));pending.set(msg.msg_id,type);return msg.msg_id;}
function echo(){if(!sharing||!ready||frame?.payload.state!=='active'||sent.has(frame.payload.frame_id))return;const {frame_id,vehicle_id,pose}=frame.payload;sent.add(frame_id);if(sent.size>200)sent.delete(sent.values().next().value);send('probe.sample',{frame_id,vehicle_id,pose},frame.sim_time_s);}
function reflect(){ $('sharing').checked=sharing; $('sharing').disabled=!ready; $('sharing-status').textContent=sharing?'On · exact frames, securely validated':'Off · your choice, always'; $('share-dot').style.background=sharing?'#779958':'#b6c0ac';document.querySelectorAll('[data-report]').forEach(b=>b.disabled=!ready||frame?.payload.state!=='active'); }
function connect(){
 clearTimeout(reconnectTimer);
 ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
 const socket=ws;
 ws.onopen=()=>{if(ws===socket)send('session.hello',{token:claim.token,last_server_seq:lastServer});};
 ws.onmessage=e=>{
  if(ws!==socket)return;
  const msg=JSON.parse(e.data);lastServer=msg.seq;
  if(msg.type==='session.ready'){ready=true;sharing=false;retries=0;$('join').hidden=true;$('drive').hidden=false;$('connection').textContent='Connected';$('vehicle').textContent=claim.vehicle_id;$('session-detail').textContent=`Bound vehicle: ${claim.vehicle_id}. Run: ${claim.run_id}.`;reflect();clearInterval(heartbeat);heartbeat=setInterval(()=>send('heartbeat',{visible:!document.hidden}),2000);}
  if(msg.type==='vehicle.frame'){frame=msg;$('stamp').textContent=`Simulation time ${Math.floor(msg.sim_time_s/60).toString().padStart(2,'0')}:${Math.floor(msg.sim_time_s%60).toString().padStart(2,'0')}`;$('stage').textContent=msg.payload.state==='active'?(msg.payload.pose.speed_mps<.1?'Vehicle waiting':'On the move'):'Journey finished';$('speed').textContent=msg.payload.pose?Math.round(msg.payload.pose.speed_mps*3.6):'—';if((follow||!center)&&msg.payload.pose)center=[msg.payload.pose.x_m,msg.payload.pose.y_m];draw();reflect();echo();}
  if(msg.type==='ack'){
   const kind=pending.get(msg.payload.in_reply_to);pending.delete(msg.payload.in_reply_to);
   if(kind==='probe.toggle'&&msg.payload.status==='applied'){sharing=msg.payload.reason==='sharing_on';reflect();echo();}
   if(kind==='probe.sample'&&msg.payload.status==='applied'){$('uplinks').textContent=`${++confirmed} samples confirmed this session`;}
   if(kind==='driver.decision'){$('advisory-status').textContent=msg.payload.status==='applied'?'Confirmed · no route change':`Rejected: ${msg.payload.reason.replaceAll('_',' ')}`;}
   if(kind==='driver.report'){$('report-status').textContent=msg.payload.status==='received'?'Report received · awaiting operator review':`Report rejected: ${msg.payload.reason}`;}
   if(msg.payload.status==='rejected')notice(msg.payload.reason.replaceAll('_',' '));
  }
  if(msg.type==='guidance'){advisory=msg.payload;$('advisory').hidden=false;$('advisory-message').textContent=advisory.message;$('advisory-status').textContent='This note does not change your route.';document.querySelectorAll('[data-choice]').forEach(b=>b.disabled=false);}
  if(advisory&&msg.sim_time_s>=advisory.expires_sim_s){$('advisory-status').textContent='This note has expired.';document.querySelectorAll('[data-choice]').forEach(b=>b.disabled=true);}
 };
 ws.onclose=e=>{if(ws!==socket)return;ready=false;sharing=false;clearInterval(heartbeat);$('advisory').hidden=true;advisory=null;reflect();if(leaving)return;$('connection').textContent='Disconnected';$('speed').textContent='—';$('stage').textContent='Position unavailable';frame=null;draw();if(e.code===1008&&e.reason!=='heartbeat_timeout'){sessionStorage.removeItem('traffix.claim');claim=null;$('drive').hidden=true;$('join').hidden=false;notice('This session ended. Get a fresh code from the laptop.');return;}notice('Connection lost. Sharing is off. Reconnecting…');reconnectTimer=setTimeout(()=>claim&&connect(),Math.min(8000,1000*2**retries++));};
}
$('claim').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{const response=await fetch('/api/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({join_code:$('code').value.trim()})});const body=await response.json();if(!response.ok)throw Error(body.detail||'Join failed');claim=body;seq=0;confirmed=0;sent.clear();pending.clear();sessionStorage.setItem('traffix.claim',JSON.stringify(claim));sessionStorage.setItem('traffix.seq','0');connect();}catch(error){notice(error.message.replaceAll('_',' '));}finally{button.disabled=false;}};
$('sharing').onchange=e=>{const enabled=e.target.checked;e.target.checked=sharing;send('probe.toggle',{enabled});};
document.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{if(ready&&advisory){send('driver.decision',{advisory_id:advisory.advisory_id,choice:b.dataset.choice});$('advisory-status').textContent='Sending…';document.querySelectorAll('[data-choice]').forEach(button=>button.disabled=true);}});
document.querySelectorAll('[data-report]').forEach(b=>b.onclick=()=>{if(frame?.payload.state==='active'){send('driver.report',{frame_id:frame.payload.frame_id,vehicle_id:claim.vehicle_id,category:b.dataset.report},frame.sim_time_s);$('report-status').textContent='Sending report…';}});
$('leave').onclick=()=>{leaving=true;if(ready)send('probe.toggle',{enabled:false});ws?.close();sessionStorage.removeItem('traffix.claim');sessionStorage.removeItem('traffix.seq');location.reload();};
$('recenter').onclick=()=>{follow=true;const pose=frame?.payload.pose;center=pose?[pose.x_m,pose.y_m]:[0,0];zoom=.85;draw();};
const canvas=$('map'),ctx=canvas.getContext('2d');
function draw(){const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;const d=Math.min(devicePixelRatio,2);canvas.width=w*d;canvas.height=h*d;ctx.scale(d,d);ctx.fillStyle='#e4eadc';ctx.fillRect(0,0,w,h);if(!world)return;const c=center||[0,0],point=p=>[(p[0]-c[0])*zoom+w/2,h/2-(p[1]-c[1])*zoom];for(const road of world.roads){if(road.internal)continue;const pts=road.shape.map(point);if(!pts.some(p=>p[0]>-200&&p[0]<w+200&&p[1]>-200&&p[1]<h+200))continue;ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.strokeStyle='#c8d2be';ctx.lineWidth=Math.max(3,road.width*zoom+3);ctx.stroke();ctx.strokeStyle='#fcfdf5';ctx.lineWidth=Math.max(1,road.width*zoom);ctx.stroke();}const lig=point([0,0]);ctx.fillStyle='#7a8a6b';ctx.font='bold 11px Segoe UI';ctx.fillText('LIG SQUARE',lig[0]+12,lig[1]-12);const pose=frame?.payload.pose;if(pose){const p=point([pose.x_m,pose.y_m]);ctx.beginPath();ctx.arc(...p,19,0,Math.PI*2);ctx.fillStyle='#739a6633';ctx.fill();ctx.beginPath();ctx.arc(...p,8,0,Math.PI*2);ctx.fillStyle='#234e3c';ctx.fill();ctx.lineWidth=3;ctx.strokeStyle='#fff';ctx.stroke();}else{ctx.fillStyle='#7b8b71';ctx.font='12px Segoe UI';ctx.fillText('Waiting for your vehicle',20,h/2);}}
let drag;
canvas.onpointerdown=e=>{follow=false;canvas.setPointerCapture(e.pointerId);drag=[e.clientX,e.clientY,...(center||[0,0])];};
canvas.onpointermove=e=>{if(!drag)return;center=[drag[2]-(e.clientX-drag[0])/zoom,drag[3]+(e.clientY-drag[1])/zoom];draw();};
canvas.onpointerup=canvas.onpointercancel=()=>drag=null;
canvas.onwheel=e=>{e.preventDefault();zoom=Math.max(.15,Math.min(3,zoom*Math.exp(-e.deltaY*.001)));draw();};
new ResizeObserver(draw).observe(canvas);
fetch('/api/world').then(r=>r.json()).then(data=>{world=data;draw();}).catch(()=>notice('Map unavailable. Vehicle data will still connect.'));
const params=new URLSearchParams(location.hash.slice(1));$('code').value=params.get('join')||params.get('code')||'';if(location.hash){if($('code').value){sessionStorage.removeItem('traffix.claim');sessionStorage.removeItem('traffix.seq');seq=0;}history.replaceState(null,'',location.pathname);}
try{claim=JSON.parse(sessionStorage.getItem('traffix.claim')||'null');if(claim)connect();}catch{sessionStorage.removeItem('traffix.claim');}
reflect();
