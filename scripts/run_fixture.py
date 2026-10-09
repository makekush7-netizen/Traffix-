"""Run the Traffix phone gate: python scripts/run_fixture.py --lan-ip ACTUAL_IP."""
import argparse
import ipaddress
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description='Start the offline Traffix fixture server')
    parser.add_argument('--lan-ip', help='Actual laptop IP reachable from the phones; use ipconfig')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if args.lan_ip:
        ipaddress.ip_address(args.lan_ip)
        os.environ['TRAFFIX_ALLOWED_HOSTS'] = args.lan_ip
    import uvicorn
    print(f'Laptop setup: http://localhost:{args.port}/setup')
    if args.lan_ip:
        print(f'Phone address: http://{args.lan_ip}:{args.port}/driver')
    print('FAKE FIXTURE ONLY. Codes expire after 120 wall seconds. Ctrl+C stops the server.')
    uvicorn.run('backend.app:app', host='0.0.0.0', port=args.port, workers=1, ws_max_size=16384)


if __name__ == '__main__':
    main()
