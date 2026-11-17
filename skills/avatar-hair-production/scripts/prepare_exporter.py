#!/usr/bin/env python3
"""Add a calibrated 136-pose, dual-pass API to an approved hair viewer."""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

PITCHES = [-22, -16.5, -11, -5.5, 0, 7, 10]
PROFILE = dict(name='avatar-hair-136-v1', size=64, targetZ=26, offsetY=6,
               distance=120, near=90, far=150, rowPitches=PITCHES,
               semanticIDs=dict(head=1, front=2, rear=3), verticalScalePivotZ=16,
               speakFront=dict(yaw=339, pitches=[-5.5, -22, -14, -5.5, -22], scales=[1, 1.2, 1.1, 1, 1.2]),
               speakBack=dict(yaw=194, pitches=[5.5, 22, 14, 22, 14], scales=[1, 1.2, 1.1, 1.2, 1.1]))


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def unique(text, old, new):
    if text.count(old) != 1: raise ValueError(f'Unsupported approved runtime anchor ({text.count(old)} matches): {old[:90]}')
    return text.replace(old, new)


def transformed_runtime(runtime, model, style):
    """Only recognize known kernels. Never infer whether a cached drop is baked."""
    if 'window.exportAvatarAtlas' in runtime: raise ValueError('Run already contains an atlas API; use the original approved viewer')
    transform = model.get('renderTransform')
    if style.get('renderTransform'):
        if transform and transform != style['renderTransform']: raise ValueError('Conflicting declared renderTransform')
        transform = style['renderTransform']
    has_drop = 'wholeHairDrop' in runtime
    geometry_space = style.get('geometrySpace')
    if geometry_space not in (None, 'baked', 'cached'): raise ValueError('geometrySpace must be baked or cached')
    if (transform or has_drop) and geometry_space is None:
        raise ValueError('Pending transform requires explicit geometrySpace=baked or cached; do not guess or double-apply')
    drop = None
    if geometry_space == 'baked' and (transform or has_drop):
        raise ValueError('Baked geometry must not retain wholeHairDrop/renderTransform; rebuild a clean approved run')
    if geometry_space == 'cached':
        if not transform: raise ValueError('Cached geometry requires authoritative renderTransform')
        translation = transform.get('translation', [])
        ids = transform.get('applyToStructures')
        if transform.get('space') != 'world' or ids != [2, 3] or len(translation) != 3 or translation[:2] != [0, 0]:
            raise ValueError('Only declared world-space pure Z translation of structures [2,3] is supported')
        if not all(isinstance(n, (int, float)) and math.isfinite(n) for n in translation): raise ValueError('Invalid translation')
        if not re.fullmatch(r'[0-9a-f]{64}', transform.get('baselineGeometrySHA256', '')):
            raise ValueError('Cached geometry requires baselineGeometrySHA256')
        drop = translation[2]
    # Recognized vertex kernels, including previously approved speaking scale.
    plain = 'gl_Position=vp*vec4(moving?r*(position-pivot)+pivot:position,1);'
    dropped = 'vec3 pos=position;pos.z+=wholeHairDrop;gl_Position=vp*vec4(moving?r*(pos-pivot)+pivot:pos,1);'
    scaled = 'vec3 pos=position;pos.z=16.+(pos.z-16.)*verticalScale;gl_Position=vp*vec4(moving?r*(pos-pivot)+pivot:pos,1);'
    both = 'vec3 pos=position;pos.z+=wholeHairDrop;pos.z=16.+(pos.z-16.)*verticalScale;gl_Position=vp*vec4(moving?r*(pos-pivot)+pivot:pos,1);'
    matches = [k for k in (plain, dropped, scaled, both) if k in runtime]
    if len(matches) != 1 or runtime.count(matches[0]) != 1: raise ValueError('Unsupported/duplicate vertex transform kernel')
    kernel = matches[0]
    if has_drop and 'wholeHairDrop' not in kernel: raise ValueError('wholeHairDrop occurs outside a supported vertex kernel')
    if has_drop:
        if runtime.count('uniform float wholeHairDrop;') != 1: raise ValueError('Duplicate or unsupported drop uniform')
        # Replace exactly the per-chunk binding with the authoritative declaration.
        binding = re.compile(r"uni\(mesh,'wholeHairDrop',.*?,'1f'\);")
        if len(binding.findall(runtime)) != 1: raise ValueError('Expected one declared per-chunk drop binding')
        runtime = binding.sub("uni(mesh,'wholeHairDrop',[2,3].includes(c.structure)?" + json.dumps(drop) + ":0,'1f');", runtime)
    elif drop is not None:
        runtime = unique(runtime, 'uniform mat4 vp;', 'uniform float wholeHairDrop;uniform mat4 vp;')
        runtime = unique(runtime, "let m=data.materials[c.material];", "uni(mesh,'wholeHairDrop',[2,3].includes(c.structure)?" + json.dumps(drop) + ":0,'1f');let m=data.materials[c.material];")
    if 'uniform float verticalScale;' not in runtime:
        runtime = unique(runtime, 'uniform mat4 vp;', 'uniform float verticalScale;uniform mat4 vp;')
        runtime = unique(runtime, "uni(mesh,'vp',camera.viewProjection,'Matrix4fv');", "uni(mesh,'verticalScale',state.verticalScale||1,'1f');uni(mesh,'vp',camera.viewProjection,'Matrix4fv');")
    else:
        scale_binding = re.compile(r"uni\(mesh,'verticalScale',.*?,'1f'\);")
        if runtime.count('uniform float verticalScale;') != 1 or len(scale_binding.findall(runtime)) != 1:
            raise ValueError('Duplicate or unsupported verticalScale binding')
        runtime = scale_binding.sub("uni(mesh,'verticalScale',state.verticalScale||1,'1f');", runtime)
    target = 'vec3 pos=position;' + ('pos.z+=wholeHairDrop;' if drop is not None else '') + 'pos.z=16.+(pos.z-16.)*verticalScale;gl_Position=vp*vec4(moving?r*(pos-pivot)+pivot:pos,1);'
    runtime = unique(runtime, kernel, target)
    return runtime, dict(geometrySpace=geometry_space or 'baked', appliedCachedTranslationZ=drop, verticalScaleApplications=1)


API = r'''
// Portable atlas API: all pixels come from this approved GPU runtime.
const atlasStyle=__STYLE__,atlasProfile=__PROFILE__;
let atlasBusy=false;
function atlasPose(yaw,pitch,scale=1){
 state.angle=((yaw%360)+360)%360;state.pitch=pitch;state.verticalScale=scale;
 const a=pitch*Math.PI/180,s=Math.sin(a),c=Math.cos(a),q=2/64,r=60,z=26,d=120;
 camera={name:'avatar-atlas',orthographicSize:64,depthRange:60,
 viewProjection:[q,0,0,0,0,q*s,2*c/r,0,0,q*c,-2*s/r,0,0,-q*(z*c+6),(2*(d+z*s)-240)/r,1],
 viewNormal:[1,0,0,0,s,-c,0,c,s]};
}
function atlasPass(mode){$('displayMode').value=mode;draw();return {beauty:targetPNG(final),parts:targetPNG(low,1)}}
window.exportAvatarAtlas=async function(options={}){
 if(atlasBusy)throw Error('Atlas capture already running');atlasBusy=true;
 const ids=['grid','displayMode','frontHair','backHair','palette','outline','structural'];
 const saved=ids.map(id=>({id,value:$(id).value,checked:$(id).checked}));
 const oldState={...state},oldCamera=camera;playing(false);
 try{
  $('grid').value='64';allocate();$('frontHair').checked=$('backHair').checked=true;
  $('palette').checked=$('outline').checked=true;$('structural').checked=false;
  const poses=[];
  for(const track of ['front','back'])for(let row=0;row<7;row++)for(let col=0;col<9;col++){
   const back=track==='back',yaw=back?180-(4-col)*7:(4-col)*7;
   poses.push({track,row,col,yaw,pitch:atlasProfile.rowPitches[row]*(back?-1:1),verticalScale:1});
  }
  for(const [track,spec] of [['speak_front',atlasProfile.speakFront],['speak_back',atlasProfile.speakBack]])
   for(let col=0;col<5;col++)poses.push({track,row:0,col,yaw:spec.yaw,pitch:spec.pitches[col],verticalScale:spec.scales[col]});
  const frames=[];
  for(const pose of poses){
   atlasPose(pose.yaw,pose.pitch,pose.verticalScale);
   const full=atlasPass('full'),hair=atlasPass('hair');
   frames.push({...pose,beauty:full.beauty,parts:full.parts,proxyParts:full.parts,hairOnlyBeauty:hair.beauty,hairOnlyParts:hair.parts});
   window.avatarAtlasProgress={complete:frames.length,total:136};
   if(frames.length%9===0)await new Promise(resolve=>requestAnimationFrame(resolve));
  }
  const rotations=[];let wrapMatches=null;
  if(options.rotations!==false){
   for(let yaw=0;yaw<360;yaw+=30){atlasPose(yaw,0);const full=atlasPass('full');rotations.push({yaw,...full})}
   atlasPose(360,0);wrapMatches=atlasPass('full').beauty===rotations[0].beauty;
  }
  return {version:'avatar-hair-gpu-v1',sourceSHA256:data.sourceSHA256,style:atlasStyle,profile:atlasProfile,
   frames,rotationFrames:rotations,wrapMatches,frameCount:frames.length};
 }finally{
  for(const x of saved){$(x.id).value=x.value;$(x.id).checked=x.checked}
  Object.assign(state,oldState);camera=oldCamera;allocate();draw();playing(oldState.playing);atlasBusy=false;
 }
};
'''


def prepare(args):
    run, out = args.run.resolve(), args.out.resolve()
    if out.exists(): raise FileExistsError('Use a fresh exporter directory')
    style = json.loads(args.style.read_text())
    if 'sourceSHA256' not in style and 'sourceSHA' in style: style['sourceSHA256'] = style.pop('sourceSHA')
    for key in ('id', 'kind', 'name', 'sourceSHA256'):
        if not isinstance(style.get(key), str) or not style[key]: raise ValueError(f'Style requires {key}')
    if not re.fullmatch(r'hair_\d{3,}', style['id']) or not re.fullmatch(r'[A-Za-z0-9_-]+', style['kind']): raise ValueError('Invalid style id/kind')
    if not re.fullmatch(r'[0-9a-f]{64}', style['sourceSHA256']): raise ValueError('Invalid source SHA256')
    model = json.loads((run / 'model.json').read_text()); cfg = json.loads((run / 'realtime.json').read_text())
    build = json.loads((run / 'build.json').read_text())
    if model['sourceSHA256'] != style['sourceSHA256'] or build['sourceSHA256'] != style['sourceSHA256']: raise ValueError('Frozen source SHA mismatch')
    if (run / 'asset.blend').exists() and sha(run / 'asset.blend') != style['sourceSHA256']: raise ValueError('Frozen asset.blend SHA mismatch')
    if list(cfg['parts']) != ['head', 'hair_front', 'hair_back']: raise ValueError('Expected semantic IDs head=1/front=2/rear=3')
    if cfg.get('frontHairPartNames') != ['hair_front'] or cfg.get('backHairPartNames') != ['hair_back']: raise ValueError('Expected standard front/back assignments')
    if any(c['structure'] not in (1, 2, 3) for c in model['chunks']): raise ValueError('Unknown chunk semantic ID')
    approved_runtime = (run / 'runtime.js').read_text()
    if build.get('runtimeSHA256') and sha(run / 'runtime.js') != build['runtimeSHA256']: raise ValueError('Approved runtime SHA mismatch')
    runtime, transform_report = transformed_runtime(approved_runtime, model, style)
    helper = API.replace('__STYLE__', json.dumps(style, ensure_ascii=False)).replace('__PROFILE__', json.dumps(PROFILE))
    runtime = unique(runtime, "draw();$('controls').disabled=false;", helper + "\ndraw();$('controls').disabled=false;")
    page = (run / 'preview.html').read_text()
    # Preserve all preview UI; remove the old inline data and exact runtime module only.
    if '<script id="model-data"' in page:
        page = re.sub(r'<script id="model-data"[^>]*>.*?</script>', '', page, count=1, flags=re.S)
    inline = re.compile(r'<script type="module">.*?</script>', re.S)
    if len(inline.findall(page)) == 1:
        page = inline.sub('<script type="module" src="runtime.js"></script>', page)
    else:
        external = re.compile(r'<script\s+(?=[^>]*type=["\']module["\'])(?=[^>]*src=["\']runtime\.js[^"\']*["\'])[^>]*>\s*</script>')
        if len(external.findall(page)) != 1: raise ValueError('Expected one runtime module in approved preview shell')
        page = external.sub('<script type="module" src="runtime.js"></script>', page)
    out.mkdir(parents=True)
    shutil.copy2(run / 'model.json', out / 'model.json')
    (out / 'runtime.js').write_text(runtime); (out / 'preview.html').write_text(page)
    write(out / 'style.json', style)
    evidence = dict(sourceSHA256=model['sourceSHA256'], approvedRuntimeSHA256=sha(run / 'runtime.js'),
                    preparedRuntimeSHA256=sha(out / 'runtime.js'), modelSHA256=sha(out / 'model.json'),
                    profile=PROFILE, transforms=transform_report)
    write(out / 'prepare.json', evidence)
    subprocess.run([args.node, '--check', str(out / 'runtime.js')], check=True)
    print(out / 'preview.html')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='Approved side-by-side run (read only)')
    parser.add_argument('--out', type=Path, required=True, help='Fresh exporter directory')
    parser.add_argument('--style', type=Path, required=True, help='JSON: id, kind, name, sourceSHA256; explicit cached transform when needed')
    parser.add_argument('--node', default='node')
    prepare(parser.parse_args())

if __name__ == '__main__': main()
