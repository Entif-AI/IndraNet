"""Read-only local scenario inspector. No ingestion, authorization or device server."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse
from .demo import SCENARIOS

def serve(root: Path, port: int=8787) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/health':
                content={'status':'local-reference','readOnly':True};status=200
            elif path=='/scenarios':
                content={'scenarios':list(SCENARIOS),'dataOrigin':'synthetic-fixture'};status=200
            elif path.startswith('/scenarios/') and path.removeprefix('/scenarios/') in SCENARIOS:
                name=path.removeprefix('/scenarios/')
                try: content=json.loads((root/(name+'.json')).read_text());status=200
                except FileNotFoundError: content={'error':'Run the demo generator first'};status=404
            else: content={'error':'Not found'};status=404
            raw=json.dumps(content).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(raw)
        def do_POST(self):
            self.send_error(405,'This reference is read-only')
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('outputs'));parser.add_argument('--port',type=int,default=8787)
    args=parser.parse_args();serve(args.root,args.port)
