"""Build a standalone preview with hash-pinned scripts and no network access."""
from pathlib import Path
import argparse, hashlib, base64
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT/'BuilderWars-Agentworld-Preview.html')
args=parser.parse_args()
html=(ROOT/'index.html').read_text()
hashes=[]
for filename in ['engine.js','ledger.js','consumer-quests.js','app.js']:
    script=(ROOT/filename).read_text()
    digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    hashes.append(f"'sha256-{digest}'")
    html=html.replace(f'<script src="{filename}"></script>', '<script>'+script+'</script>')
html=html.replace("script-src 'self'", 'script-src '+' '.join(hashes))
args.output.write_text(html)
print('Built standalone preview with hash-pinned scripts.')
