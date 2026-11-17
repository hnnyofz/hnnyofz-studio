#!/usr/bin/env python3
"""Build a portable real-time viewer from a declared Blender scene."""
import argparse,base64,hashlib,html,io,json,shutil,subprocess
from pathlib import Path
from PIL import Image
S=Path(__file__).resolve().parents[1]
def build(spec,out,blender):
 spec=Path(spec).resolve();out=Path(out).resolve();cfg=json.loads(spec.read_text())
 assert not out.exists(),'Use a fresh output directory'
 assert isinstance(cfg['size'],int) and 8<=cfg['size']<=128
 assert cfg['rotationSign'] in [-1,1] and len(cfg['pivot'])==3
 assert 1<=len(cfg['palette'])<=32
 assert cfg['outline'] in cfg['palette'],'Outline must be in palette'
 def rgb(s):
  assert len(s)==7 and s[0]=='#'
  return [int(s[i:i+2],16)/255 for i in [1,3,5]]
 palette=[rgb(c) for c in cfg['palette']];ink=rgb(cfg['outline'])
 model=(spec.parent/cfg['model']).resolve();assert model.is_file()
 out.mkdir(parents=True);shutil.copy2(model,out/'asset.blend');shutil.copy2(spec,out/'realtime.json')
 subprocess.run([blender,'-b',str(model),'--python-exit-code','1','--python',str(S/'scripts/realtime_export.py'),'--',str(spec),str(out)],check=True)
 data=json.loads((out/'model.json').read_text())
 for t in data['textures']:
  im=Image.open(io.BytesIO(base64.b64decode(t.pop('data').split(',')[1]))).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  t['width'],t['height']=im.size;t['rgba']=list(im.tobytes())
 runtime=(S/'assets/realtime.js').read_text().replace('__SETTINGS__',json.dumps({**{k:cfg[k] for k in ['name','size','pivot','rotationSign']},'hairLighting':cfg.get('hairLighting','none'),'hairPartIDs':[list(cfg['parts']).index(label)+1 for label in cfg.get('hairPartNames',[])]})).replace('__PALETTE_COUNT__',str(len(palette))).replace('__PALETTE__',','.join('vec3('+','.join(map(str,c))+')' for c in palette)).replace('__INK__',','.join(map(str,ink)))
 page=(S/'assets/realtime.html').read_text().replace('__TITLE__',html.escape(cfg['name'])).replace('__MODEL__',json.dumps(data,separators=(',',':')).replace('<','\\u003c')).replace('__RUNTIME__',runtime.replace('</script','<\\/script'))
 (out/'model.json').write_text(json.dumps(data,separators=(',',':')));(out/'runtime.js').write_text(runtime);(out/'preview.html').write_text(page)
 evidence={'sourceSHA256':data['sourceSHA256'],'runtimeSHA256':hashlib.sha256(runtime.encode()).hexdigest(),'objects':len(data['parts']),'cameras':[c['name'] for c in data['cameras']],'status':'built_requires_browser_visual_review','references':[]}
 for ref in cfg.get('references',[]):
  f=(spec.parent/ref).resolve();dest=out/'references'/f.name;dest.parent.mkdir(exist_ok=True)
  assert not dest.exists(),'Reference basename collision'
  shutil.copy2(f,dest);evidence['references'].append({'file':str(dest.relative_to(out)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 (out/'build.json').write_text(json.dumps(evidence,indent=2));print(out/'preview.html')
 portable=dict(cfg);portable['model']='asset.blend';portable['references']=[r['file'] for r in evidence['references']]
 (out/'realtime.json').write_text(json.dumps(portable,indent=2,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--out',required=True);p.add_argument('--blender',default='blender');a=p.parse_args();build(a.spec,a.out,a.blender)
