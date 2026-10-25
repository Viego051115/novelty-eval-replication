from pathlib import Path
import gzip,hashlib,json
r=Path(__file__).resolve().parent
m=json.loads((r/'results/raw_response_parts/manifest.json').read_text())
b=b''.join((r/'results/raw_response_parts'/name).read_bytes() for name in m['parts'])
assert hashlib.sha256(b).hexdigest()==m['gzip_sha256']
raw=gzip.decompress(b)
assert hashlib.sha256(raw).hexdigest()==m['raw_sha256']
p=r/'results/fig13_api_responses.jsonl'
p.write_bytes(raw)
print('Restored and verified',len(raw),'bytes')
