import {commandId} from './protocol.mjs';
const $=id=>document.getElementById(id);let session=null,ws=null,seq=0,stamp=0,frame=null,heartbeat=null,accepted=0;
$('code').value=new URLSearchParams(location.hash.slice(1)).get('code')||'';
history.replaceState(null,'',location.pathname);
function send(type,payload){if(ws?.readyState!==WebSocket.OPEN)return;ws.send(JSON.stringify({v:1,type,msg_id:'msg.phone.'+commandId(),run_id:session.run_id,sender_id:session.session_id,seq:++seq,sim_time_s:stamp,payload}));}
function connect(){clearInterval(heartbeat);$('reconnect').hidden=true;const socket=ws=new WebSocket((location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/api/v2/phones/ws');
 socket.onopen=()=>send('session.hello',{token:session.token,last_server_seq:0});
 socket.onmessage=e=>{const message=JSON.parse(e.data),p=message.payload;stamp=message.sim_time_s;
  if(message.type==='session.ready'){$('status').textContent='Connected to host';$('sharing').disabled=false;heartbeat=setInterval(()=>send('heartbeat',{visible:!document.hidden}),2000);}
  if(message.type==='vehicle.frame'){frame=message;$('speed').textContent=p.pose?(p.pose.speed_mps*3.6).toFixed(1)+' km/h':'Journey finished';$('road').textContent=p.pose?.edge_id||'';$('journey').textContent='Simulated '+stamp.toFixed(1)+' s · '+p.state;if($('sharing').checked&&p.pose)send('probe.sample',{vehicle_id:session.vehicle_id,frame_id:p.frame_id,pose:p.pose});}
  if(message.type==='ack'){if(p.reason==='sample_accepted')$('samples').textContent=(++accepted)+' accepted probe samples';if(p.status==='rejected')$('status').textContent='Host rejected: '+p.reason;}
  if(message.type==='guidance'){const box=$('advice');box.replaceChildren();const text=document.createElement('p');text.textContent=p.message;box.append(text);for(const choice of ['accept','ignore']){const button=document.createElement('button');button.textContent=choice;button.onclick=()=>{send('driver.decision',{advisory_id:p.advisory_id,choice});box.replaceChildren();};box.append(button);}}
 };
 socket.onclose=e=>{if(socket!==ws)return;clearInterval(heartbeat);$('speed').textContent='—';$('journey').textContent='Last snapshot '+stamp.toFixed(1)+' s · stale';if(e.reason==='run_reset'){$('join').hidden=false;$('code').value='';frame=null;}$('sharing').checked=false;$('sharing').disabled=true;$('status').textContent=e.reason==='run_reset'?'Host started a new run. Ask for a new join code.':'Disconnected. Probe sharing stopped. Reconnect or ask for a new code.';$('reconnect').hidden=e.reason==='run_reset';};socket.onerror=()=>socket.close();
}
$('join').onsubmit=async e=>{e.preventDefault();try{const response=await fetch('/api/v2/phones/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({join_code:$('code').value.trim()})});const data=await response.json();if(!response.ok)throw Error(data.detail||'Join failed');session=data;seq=0;accepted=0;$('trip').hidden=false;$('vehicle').textContent='Your simulated vehicle: '+session.vehicle_id;$('join').hidden=true;connect();}catch(error){$('status').textContent=error.message;}};
$('sharing').onchange=()=>{send('probe.toggle',{enabled:$('sharing').checked});if($('sharing').checked&&frame?.payload.pose)send('probe.sample',{vehicle_id:session.vehicle_id,frame_id:frame.payload.frame_id,pose:frame.payload.pose});};$('reconnect').onclick=connect;
