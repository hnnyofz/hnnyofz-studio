"""Build the existing head shader viewer with continuous real camera elevation.

Only camera/UI/export metadata change. The mesh, palette, depth sampling and ink
GLSL are unchanged. Uses the source Blender cameras at their exact preset angles.
"""
from pathlib import Path
import argparse,json,math,subprocess,sys,hashlib

def orbit_matrix(pitch,scale=32,z=26,distance=120,near=90,far=150):
 a=math.radians(pitch);s=math.sin(a);c=math.cos(a);q=2/scale;r=far-near
 return [q,0,0,0,0,q*s,2*c/r,0,0,q*c,-2*s/r,0,0,-q*z*c,(2*(distance+z*s)-far-near)/r,1]

def build(project,out,blender="blender",node="node"):
 project=Path(project).resolve();out=Path(out).resolve()
 builder=Path(__file__).parent/'realtime.py'
 subprocess.run([sys.executable,str(builder),'--spec',str(project/'realtime.json'),'--out',str(out),'--blender',str(blender)],check=True)
 model=json.loads((out/'model.json').read_text());cfg=json.loads((project/'realtime.json').read_text())
 orbit=cfg.get('orbit',dict(targetZ=26,distance=120,near=90,far=150,scale=32))
 differences=[]
 for pitch,camera in zip([0,30,45,60,90],model['cameras']):
  calc=orbit_matrix(pitch,orbit['scale'],orbit['targetZ'],orbit['distance'],orbit['near'],orbit['far'])
  error=max(abs(a-b) for a,b in zip(calc,camera['viewProjection']));differences.append(error)
  assert error<1e-5,(camera['name'],error,'Orbit parameters must match saved Blender camera')
 old=(out/'runtime.js').read_text();runtime=old
 def change(a,b):
  nonlocal runtime
  assert runtime.count(a)==1,(a[:100],runtime.count(a))
  runtime=runtime.replace(a,b)
 change('const state={angle:0,','const state={pitch:0,angle:0,')
 change("uni(mesh,'yaw',state.angle*Math.PI/180,'1f')","uni(mesh,'yaw',((state.angle%360+360)%360)*Math.PI/180,'1f')")
 hair_ids=[list(cfg['parts']).index(label)+1 for label in cfg.get('hairPartNames',['hair'])]
 change("if($('baseOnly').checked&&c.moving)continue;",f"const mode=$('displayMode').value,isHair={json.dumps(hair_ids)}.includes(c.structure);if((mode==='hair'&&!isHair)||(mode==='face'&&isHair))continue;")
 change("for(const id of ['outline','structural','palette','baseOnly'])$(id).onchange=()=>dirty=true;","for(const id of ['outline','structural','palette','displayMode'])$(id).onchange=()=>{dirty=true;$('sequenceDownload').hidden=true;$('saved').hidden=true};")
 reference_yaw=cfg.get('referencePoseYaw',0)
 if reference_yaw:
  change('const state={pitch:0,angle:0,',f'const state={{pitch:0,angle:{reference_yaw},')
 old_camera="let camera=data.cameras[0];$('elevation').innerHTML=data.cameras.map((c,i)=>`<option value=\"${i}\">${c.name}</option>`).join('');$('elevation').onchange=()=>{camera=data.cameras[+$('elevation').value];dirty=true};"
 camera_code='''let camera=data.cameras[0];
const orbitConfig=ORBIT_JSON,presetPitches=[0,30,45,60,90];
$('elevation').innerHTML=data.cameras.map((c,i)=>`<option value="${i}">${c.name}</option>`).join('')+'<option value="orbit">自定义上下角度</option>';
function setPitch(value){
 if(!Number.isFinite(value))return;
 state.pitch=Math.max(-35,Math.min(90,value));
 const index=presetPitches.findIndex(p=>Math.abs(p-state.pitch)<.00001);
 if(index>=0)camera=data.cameras[index];
 else{
  const a=state.pitch*Math.PI/180,s=Math.sin(a),c=Math.cos(a),q=2/orbitConfig.scale,r=orbitConfig.far-orbitConfig.near,z=orbitConfig.targetZ,d=orbitConfig.distance;
  camera={name:'上下 '+state.pitch.toFixed(1)+'°',orthographicSize:orbitConfig.scale,depthRange:r,
   viewProjection:[q,0,0,0,0,q*s,2*c/r,0,0,q*c,-2*s/r,0,0,-q*z*c,(2*(d+z*s)-orbitConfig.far-orbitConfig.near)/r,1],
   viewNormal:[1,0,0,0,s,-c,0,c,s]};
 }
 $('pitch').value=state.pitch;
 if(document.activeElement!==$('pitchNumber'))$('pitchNumber').value=state.pitch.toFixed(1);
 $('elevation').value=index<0?'orbit':String(index);
 $('sequenceDownload').hidden=true;dirty=true;
}
$('pitch').oninput=()=>{playing(false);setPitch(Number($('pitch').value))};
$('pitchNumber').oninput=()=>{if($('pitchNumber').value!==''){playing(false);setPitch(Number($('pitchNumber').value))}};
$('pitchNumber').onblur=()=>$('pitchNumber').value=state.pitch.toFixed(1);
$('elevation').onchange=()=>{if($('elevation').value!=='orbit')setPitch(presetPitches[Number($('elevation').value)])};
setPitch(0);
'''.replace('ORBIT_JSON',json.dumps(orbit))
 change(old_camera,camera_code)
 change("$('reset').onclick=()=>{playing(false);state.angle=0;dirty=true}","$('reset').onclick=()=>{playing(false);state.angle=0;setPitch(0);dirty=true}")
 change("$('play').onclick=()=>playing(!state.playing);",f"$('play').onclick=()=>playing(!state.playing);$('referencePose').onclick=()=>{{playing(false);state.angle={reference_yaw};setPitch(0);dirty=true}};")
 change("drag={x:e.clientX,a:state.angle}","drag={x:e.clientX,y:e.clientY,a:state.angle,p:state.pitch}")
 change("state.angle=(drag.a+(e.clientX-drag.x)*.55+3600)%360;dirty=true", "state.angle=(drag.a+(e.clientX-drag.x)*.55+3600)%360;setPitch(drag.p+(e.clientY-drag.y)*.35);dirty=true")
 change("im.alt='angle-'+a;im.dataset.legs", "im.alt='angle-'+a;im.dataset.pitch=state.pitch;im.dataset.legs")
 change("state.angle.toFixed(1)+'deg-'+n+'px.png'", "state.angle.toFixed(1)+'deg-pitch'+state.pitch.toFixed(1)+'-'+n+'px-'+$('displayMode').value+'.png'")
 change("state.angle.toFixed(1)+'° · '+n+' × '+n+' 透明 PNG'", "state.angle.toFixed(1)+'° · 上下 '+state.pitch.toFixed(1)+'° · '+n+' × '+n+' · '+({full:'完整头部',hair:'纯发型',face:'仅脸部'}[$('displayMode').value])+' 透明 PNG'")
 change("camera:camera.name,sourceSHA256", "camera:camera.name,pitchDegrees:state.pitch,orthographicSize:camera.orthographicSize,displayMode:$('displayMode').value,hiddenHair:$('displayMode').value==='face',hiddenHead:$('displayMode').value==='hair',sourceSHA256")
 change("SETTINGS.name+'-'+step+'deg.zip'", "SETTINGS.name+'-'+step+'deg-pitch'+state.pitch.toFixed(1)+'-'+$('displayMode').value+'.zip'")
 page=(out/'preview.html').read_text();assert old in page;page=page.replace(old,runtime)
 pitch_control='''<label><span class="control-title"><span>上下角度</span><span><input id="pitchNumber" aria-label="上下角度数值" type="number" min="-35" max="90" step="0.5" value="0">°</span></span><input id="pitch" aria-label="上下角度" type="range" min="-35" max="90" step="0.5" value="0"></label>'''
 marker='<div class="control"><span class="control-title">播放</span>'
 assert page.count(marker)==1;page=page.replace(marker,pitch_control+'\n'+marker)
 page=page.replace('<button id="reset">归零</button>','<button id="reset">正脸归零</button><button id="referencePose"'+(' hidden' if not reference_yaw else '')+'>设计图角度</button>')
 page=page.replace('拖动模型连续旋转；像素效果由实体模型实时生成。','左右拖动旋转，上下拖动俯仰；两侧视角同步。')
 page=page.replace('相机 / 仰角 ','上下视角预设 ')
 old_mode='<label><input id="baseOnly" type="checkbox">仅看固定部件</label>'
 assert page.count(old_mode)==1;page=page.replace(old_mode,'')
 fieldset='<fieldset id="controls" class="controls" aria-label="实时渲染设置" disabled>'
 mode_control='<label class="display-mode"><span>显示内容</span><select id="displayMode" aria-label="显示内容"><option value="full">完整头部</option><option value="hair">纯发型（隐藏头部）</option><option value="face">仅脸部（隐藏头发）</option></select></label>'
 assert page.count(fieldset)==1;page=page.replace(fieldset,fieldset+mode_control)
 page=page.replace('</style>','.display-mode{grid-column:1/-1;display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:12px;max-width:360px}.display-mode select{min-width:0;width:100%}</style>')
 # Keep the source design's colored hairline readable; silhouette ink stays on.
 page=page.replace('id="structural" type="checkbox" checked','id="structural" type="checkbox"')
 page=page.replace('aria-label="左侧实时3D模型，右侧实时像素效果"','aria-label="左侧实时3D模型，右侧实时像素效果，可左右和上下拖动"')
 (out/'runtime.js').write_text(runtime);(out/'preview.html').write_text(page)
 report=json.loads((out/'build.json').read_text());report.update(runtimeSHA256=hashlib.sha256(runtime.encode()).hexdigest(),orbit=orbit,presetMatrixMaxErrors=differences,continuousPitchRange=[-35,90],defaultStructuralOutline=False)
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 subprocess.run([str(node),'--check',str(out/'runtime.js')],check=True)
 print('ORBIT_VIEWER',out)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--out',required=True);p.add_argument('--blender',default='blender');p.add_argument('--node',default='node');a=p.parse_args();build(a.project,a.out,a.blender,a.node)
