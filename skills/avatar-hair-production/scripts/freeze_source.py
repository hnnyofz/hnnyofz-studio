#!/usr/bin/env python3
"""Record the current editable source hash; this does not approve its appearance."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);a=p.parse_args();cfg=json.loads((a.project/'realtime.json').read_text());model=(a.project/cfg['model']).resolve();assert model.is_file();sha=hashlib.sha256(model.read_bytes()).hexdigest();style=json.loads((a.project/'style.json').read_text());style['sourceSHA256']=sha;(a.project/'style.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n');(a.project/'qa').mkdir(exist_ok=True);(a.project/'qa/source.json').write_text(json.dumps(dict(model=cfg['model'],sourceSHA256=sha,frozenAt=datetime.now(timezone.utc).isoformat(),status='hash_frozen_not_visual_approval'),indent=2)+'\n');print(sha)
