#!/usr/bin/env python3
"""Create a real editable hair project from the calibrated head and an optional GLB.

Run in host Python; invokes Blender with an explicit failure exit code. Imported
AI meshes are work copies requiring skin cleanup, fitting and material review.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
S=Path(__file__).resolve().parents[1]

def worker():
 import bpy
 def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
 from mathutils import Vector
 args=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());project=Path(args['project']);cfg=json.loads((S/'assets/head-proxy.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(S/'assets/head-proxy.blend'))
 before=set(bpy.data.objects);meshes=[]
 if args['glb']:
  bpy.ops.import_scene.gltf(filepath=args['glb']);objects=[o for o in bpy.data.objects if o not in before];meshes=[o for o in objects if o.type=='MESH']
  for ob in meshes:
   world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=world
  if args['fit']:
   points=[ob.matrix_world@Vector(corner) for ob in meshes for corner in ob.bound_box];lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)*.5;dimensions=hi-lo;scale=min(args['fit'][i]/max(dimensions[i],1e-8) for i in range(3))
   for ob in meshes:
    ob.scale*=scale;ob.location=Vector(args['center'])+(ob.location-center)*scale
  for ob in meshes:
   ob.name='HAIR_WORK_'+ob.name;world=ob.matrix_world.copy();ob.parent=bpy.data.objects[cfg['movingRoot']];ob.matrix_world=world;ob['semantic_part']='hair_front'
   for mat in ob.data.materials:
    if not mat:continue
    mat.use_nodes=True;nodes=mat.node_tree.nodes;bsdf=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None);tex=None
    if bsdf and bsdf.inputs['Base Color'].is_linked:
     n=bsdf.inputs['Base Color'].links[0].from_node
     if n.type=='TEX_IMAGE':tex=n.image
    nodes.clear();em=nodes.new('ShaderNodeEmission');out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],out.inputs[0]);rgb=[int(args['palette'][len(args['palette'])//2][i:i+2],16)/255 for i in [1,3,5]];em.inputs[0].default_value=(*[linear(v) for v in rgb],1)
    if tex:
     node=nodes.new('ShaderNodeTexImage');node.image=tex;mat.node_tree.links.new(node.outputs['Color'],em.inputs[0]);tex.pack()
   if not ob.data.materials:
    mat=bpy.data.materials.new('Hair base');mat.use_nodes=True;mat.node_tree.nodes.clear();em=mat.node_tree.nodes.new('ShaderNodeEmission');out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],out.inputs[0]);color=args['palette'][len(args['palette'])//2];em.inputs[0].default_value=tuple(linear(int(color[i:i+2],16)/255) for i in [1,3,5])+(1,);ob.data.materials.append(mat)
 cfg.update(name=args['name'],palette=cfg['palette']+args['palette'],hairLighting='fixed-normal');cfg['parts']['hair_front']=[o.name for o in meshes];cfg['model']='model/avatar.blend';cfg['workStatus']='requires_skin_cleanup_fit_and_hair_split';cfg['references']=[]
 (project/'realtime.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(project/'model/avatar.blend'))
 print('PROJECT_CREATED_REQUIRES_VISUAL_REVIEW',project)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--id',required=True);p.add_argument('--name',required=True);p.add_argument('--glb',type=Path);p.add_argument('--blender',default='blender');p.add_argument('--hair-palette',nargs='+',default=['#101622','#243147','#3d506a','#6b839c']);p.add_argument('--fit-box',nargs=3,type=float,help='Optional uniform rough-fit width depth height; requires subsequent visual fitting');p.add_argument('--center',nargs=3,type=float,default=[0,1,31]);a=p.parse_args();assert not a.project.exists(),'Choose a fresh project directory';assert len(a.hair_palette)<=25
 for c in a.hair_palette:assert len(c)==7 and c[0]=='#';int(c[1:],16)
 if a.glb:assert a.glb.is_file()
 a.project.mkdir(parents=True);(a.project/'model').mkdir();(a.project/'source').mkdir();(a.project/'references').mkdir();(a.project/'qa').mkdir()
 if a.glb:
  raw=a.project/'source/raw.glb';shutil.copy2(a.glb,raw)
  import hashlib
  (a.project/'source/raw-source.json').write_text(json.dumps(dict(file='raw.glb',sha256=hashlib.sha256(raw.read_bytes()).hexdigest()),indent=2)+'\n')
 params=dict(project=str(a.project.resolve()),name=a.name,glb=str((a.project/'source/raw.glb').resolve()) if a.glb else None,palette=a.hair_palette,fit=a.fit_box,center=a.center);job=a.project/'source/init-parameters.json';job.write_text(json.dumps(params,ensure_ascii=False,indent=2)+'\n');(a.project/'style.json').write_text(json.dumps(dict(id=a.id,kind=a.id,name=a.name),ensure_ascii=False,indent=2)+'\n');subprocess.run([a.blender,'--background','--python-exit-code','1','--python',str(Path(__file__).resolve()),'--',str(job.resolve())],check=True)
if __name__=='__main__':
 if '--' in sys.argv:worker()
 else:main()
