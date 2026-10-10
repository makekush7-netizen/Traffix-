"""Portable SUMO boot. The SUMO package wheel supplies tools and executable."""
import os
from pathlib import Path

def prepare_environment():
    import sumo
    home=Path(sumo.SUMO_HOME)
    os.environ['SUMO_HOME']=str(home)
    os.environ['PATH']=str(home/'bin')+os.pathsep+os.environ.get('PATH','')
    return home

def listen_addresses(host,lan=None):
    if not lan: return [host]
    import ipaddress
    address=ipaddress.ip_address(lan)
    allowed=any(address in ipaddress.ip_network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')) if address.version==4 else False
    if not allowed: raise ValueError('Use the laptop private Wi-Fi/hotspot IPv4 address')
    return list(dict.fromkeys([host,lan]))

def main():
    prepare_environment()
    import uvicorn
    import socket
    host=os.getenv('TRAFFIX_HOST','127.0.0.1');port=int(os.getenv('TRAFFIX_PORT','8005'))
    addresses=listen_addresses(host,os.getenv('TRAFFIX_LAN_ADDRESS'))
    sockets=[]
    try:
        for address in addresses:
            sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sockets.append(sock)
            sock.bind((address,port));sock.listen(128)
            print(f'Traffix listening on http://{address}:{port}',flush=True)
        uvicorn.Server(uvicorn.Config('backend.simulation.app:app',host=host,port=port,workers=1)).run(sockets=sockets)
    finally:
        for sock in sockets: sock.close()
if __name__=='__main__': main()
