import {commandId} from './protocol.mjs';
import {PhoneAcknowledgements} from './phone-state.mjs';
const $=id=>document.getElementById(id),acks=new PhoneAcknowledgements();
let session=null,ws=null,seq=0,stamp=0,frame=null,heartbeat=null,accepted=0,advisory=null,polling=false;
const hash=new URLSearchParams(location.hash.slice(1));$('code').value=hash.get('code')||hash.get('join')||'';
history.replaceState(null,'',location.pathname);
function send(type,payload){
 if(ws?.readyState!==WebSocket.OPEN)return null;
 const id='msg.phone.'+commandId();ws.send(JSON.stringify({v:1,type,msg_id:id,run_id:session.run_id,sender_id:session.session_id,seq:++seq,sim_time_s:stamp,payload}));
 if(['probe.toggle','driver.decision'].includes(type))acks.request(id,type,payload);
 return id;
}
function consentView(){
 $('sharing').checked=acks.reporting;$('sharing').disabled=ws?.readyState!==WebSocket.OPEN||acks.has('probe.toggle');
}
function adviceView(status=''){
 const box=$('advice');box.replaceChildren();if(status){const text=document.createElement('p');text.textContent=status;box.append(text);}
 if(!advisory)return;
 const text=document.createElement('p');text.textContent=advisory.message;box.append(text);
 if(stamp>=advisory.expires_sim_s){const note=document.createElement('p');note.textContent='Offer expired; original route retained.';box.append(note);return;}
 for(const choice of ['accept','ignore']){const button=document.createElement('button');button.textContent=choice;button.disabled=acks.has('driver.decision')||ws?.readyState!==WebSocket.OPEN;
  button.onclick=()=>{if(send('driver.decision',{advisory_id:advisory.advisory_id,choice}))adviceView('Waiting for host acknowledgement…');};box.append(button);}
}
async function ownState(){
 if(!session||polling||ws?.readyState!==WebSocket.OPEN)return;polling=true;const current=session;
 try{
  const query=new URLSearchParams({session_id:current.session_id,run_id:current.run_id});
  const response=await fetch('/api/v2/phones/state?'+query,{headers:{Authorization:'Bearer '+current.token},signal:AbortSignal.timeout(4000)});
  if(!response.ok)throw Error('Own-trip state unavailable ('+response.status+').');
  const state=await response.json();if(current!==session||ws?.readyState!==WebSocket.OPEN)return;
  $('alerts').textContent=(state.alerts||[]).map(event=>`${event.kind}: speed restriction on ${event.edge_id} until ${event.end_s.toFixed(1)} simulated s. No lane closure or automatic reroute.`).join(' ');
  $('alerts').hidden=!(state.alerts||[]).length;
 }catch{if(current===session){$('alerts').textContent='Route restriction status unavailable; reconnect to refresh.';$('alerts').hidden=false;}}
 finally{polling=false;}
}
function connect(){
 clearInterval(heartbeat);acks.reset();advisory=null;frame=null;adviceView();$('reconnect').hidden=true;
 const socket=ws=new WebSocket((location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/api/v2/phones/ws');consentView();
 socket.onopen=()=>{if(socket===ws)send('session.hello',{token:session.token,last_server_seq:0});};
 socket.onmessage=e=>{
  if(socket!==ws)return;const message=JSON.parse(e.data),p=message.payload;stamp=message.sim_time_s;
  if(message.type==='session.ready'){$('status').textContent='Connected to host · sharing off';consentView();heartbeat=setInterval(()=>send('heartbeat',{visible:!document.hidden}),2000);ownState();}
  if(message.type==='vehicle.frame'){
   frame=message;$('speed').textContent=p.pose?(p.pose.speed_mps*3.6).toFixed(1)+' km/h':'Journey finished';$('road').textContent=p.pose?.edge_id||'';$('journey').textContent='Simulated '+stamp.toFixed(1)+' s · '+p.state;
   if(acks.reporting&&!document.hidden&&p.pose)send('probe.sample',{vehicle_id:session.vehicle_id,frame_id:p.frame_id,pose:p.pose});
   if(advisory&&stamp>=advisory.expires_sim_s)adviceView();
  }
  if(message.type==='ack'){
   if(p.reason==='sample_accepted')$('samples').textContent=(++accepted)+' accepted probe samples';
   const result=acks.acknowledge(p);
   if(result?.type==='probe.toggle'){consentView();$('status').textContent=result.applied?(acks.reporting?'Sharing confirmed by host':'Sharing stopped by host'):'Sharing change rejected: '+p.reason;}
   if(result?.type==='driver.decision'){
    if(result.applied){advisory=null;adviceView(p.reason==='route_applied'?'Route applied by simulation host.':'Original route retained; host acknowledged your choice.');ownState();}
    else adviceView('Host rejected decision: '+p.reason);
   }else if(p.status==='rejected')$('status').textContent='Host rejected: '+p.reason;
  }
  if(message.type==='guidance'){advisory=p;adviceView();}
 };
 socket.onclose=e=>{
  if(socket!==ws)return;clearInterval(heartbeat);acks.reset();advisory=null;frame=null;consentView();adviceView('Connection lost. Pending actions need fresh host confirmation.');
  $('speed').textContent='—';$('journey').textContent='Last snapshot '+stamp.toFixed(1)+' s · stale';$('alerts').hidden=true;
  if(e.reason==='run_reset'||e.reason==='invalid_session_or_message'){$('join').hidden=false;$('code').value='';}
  $('status').textContent=e.reason==='run_reset'?'Host started a new run. Ask for a new join code.':'Disconnected. Probe sharing stopped. Reconnect or ask for a new code.';
  $('reconnect').hidden=e.reason==='run_reset';
 };socket.onerror=()=>socket.close();
}
$('join').onsubmit=async e=>{e.preventDefault();try{
 const response=await fetch('/api/v2/phones/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({join_code:$('code').value.trim()})});
 const data=await response.json();if(!response.ok)throw Error(data.detail||'Join failed');ws?.close();session=data;seq=0;accepted=0;$('samples').textContent='0 accepted probe samples';
 $('trip').hidden=false;$('vehicle').textContent='Your simulated vehicle: '+session.vehicle_id;$('join').hidden=true;connect();
 }catch(error){$('status').textContent=error.message;}};
$('sharing').onchange=()=>{const requested=$('sharing').checked;if(send('probe.toggle',{enabled:requested}))$('status').textContent='Waiting for sharing acknowledgement…';consentView();};
$('reconnect').onclick=connect;
document.addEventListener('visibilitychange',()=>{if(document.hidden&&acks.reporting){send('probe.toggle',{enabled:false});consentView();}});
setInterval(ownState,1000);
