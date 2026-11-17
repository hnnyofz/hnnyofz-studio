#!/usr/bin/env python3
"""Report local prerequisites without installing, generating, or mutating assets."""
import argparse,importlib.metadata,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blender',default='blender');p.add_argument('--demo-root',type=Path);a=p.parse_args();s=Path(__file__).resolve().parents[1];report={'python':sys.version.split()[0],'skill':str(s),'assets':{n:(s/'assets'/n).is_file() for n in ['head-proxy.blend','head-proxy.json','gallery.html']},'packages':{}}
for name in ['Pillow','playwright','gradio_client']:
 try:report['packages'][name]=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:report['packages'][name]='not installed'
blender=shutil.which(a.blender) or (a.blender if Path(a.blender).is_file() else None);report['blender']=blender
if blender:
 try:report['blenderVersion']=subprocess.check_output([blender,'--version'],text=True,timeout=15).splitlines()[0]
 except (subprocess.SubprocessError,OSError) as e:report['blenderError']=type(e).__name__
report['node']=shutil.which('node');report['pnpm']=shutil.which('pnpm')
if a.demo_root:report['demoFiles']={n:(a.demo_root/n).exists() for n in ['index.ts','demo/demoAssets.ts','Assets/head/head_000','Assets/face/face_000','Assets/hair/hair_004/icon_hair_004.png']}
print(json.dumps(report,ensure_ascii=False,indent=2))
