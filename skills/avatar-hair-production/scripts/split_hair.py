#!/usr/bin/env python3
"""Physically split a reviewed new hair work mesh at world Y=0 and close the cuts.

This initializer is not a repair tool for previously approved asymmetric parts
or near-side caps. Their semantic assignments must be preserved explicitly.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def worker():
 import bpy,bmesh
 def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
 from mathutils import Matrix
 request=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());p=Path(request['project']);cfg=json.loads((p/'realtime.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(p/'model/avatar.blend'));names=request['objects'] or cfg['parts']['hair_front'];assert names and not set(names)&set(cfg['parts']['head'])
 bpy.ops.object.select_all(action='DESELECT');objects=[bpy.data.objects[n] for n in names]
 for o in objects:o.hide_set(False);o.hide_viewport=False;o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();source=bpy.context.object;world=source.matrix_world.copy();source.parent=None;source.matrix_world=world;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);source.name='HAIR_SOURCE_CLEAN'
 root=bpy.data.objects[cfg['movingRoot']];source.parent=root;source.matrix_world=Matrix.Identity(4);source.hide_render=True;source.hide_set(True)
 mat=bpy.data.materials.new('Closed cut interior');mat.use_nodes=True;mat.node_tree.nodes.clear();em=mat.node_tree.nodes.new('ShaderNodeEmission');out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],out.inputs[0]);color=cfg['palette'][7];em.inputs[0].default_value=tuple(linear(int(color[i:i+2],16)/255) for i in [1,3,5])+(1,)
 counts={}
 for side in ['front','back']:
  ob=source.copy();ob.data=source.data.copy();bpy.context.scene.collection.objects.link(ob);ob.name='Hair.'+side;ob.hide_render=False;ob.hide_set(False);ob.data.materials.append(mat);bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
  cut=bmesh.ops.bisect_plane(bm,geom=[*bm.verts,*bm.edges,*bm.faces],dist=1e-6,plane_co=(0,0,0),plane_no=(0,1,0),clear_outer=side=='front',clear_inner=side=='back')
  edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
  if edges:
   new=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
   for face in new:face.material_index=len(ob.data.materials)-1
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert len(bm.faces),'Hair work mesh does not span both sides; fit/orient it first'
  if bm.calc_volume()<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
  xs=[v.co.y for v in bm.verts];assert max(xs)<=1e-5 if side=='front' else min(xs)>=-1e-5
  counts[side]=dict(vertices=len(bm.verts),faces=len(bm.faces),nonManifoldEdges=sum(not e.is_manifold for e in bm.edges));bm.to_mesh(ob.data);bm.free();ob['semantic_part']='hair_'+side;cfg['parts']['hair_'+side]=[ob.name]
 cfg['workStatus']='split_requires_geometry_material_and_head_contact_review';(p/'realtime.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(p/'model/avatar.blend'));style=json.loads((p/'style.json').read_text());style['sourceSHA256']=hashlib.sha256((p/'model/avatar.blend').read_bytes()).hexdigest();(p/'style.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n');(p/'qa/split-report.json').write_text(json.dumps(counts,indent=2)+'\n')
 for section in ['whole','front','back']:
  bpy.ops.wm.open_mainfile(filepath=str(p/'model/avatar.blend'));keep=[o for o in bpy.context.scene.objects if o.name in cfg['parts']['hair_front']+cfg['parts']['hair_back'] and (section=='whole' or o.name in cfg['parts']['hair_'+section])]
  assert keep
  for o in keep:
   world=o.matrix_world.copy();o.parent=None;o.matrix_world=world;o.hide_set(False);o.hide_render=False
   for c in list(o.users_collection):c.objects.unlink(o)
   bpy.context.scene.collection.objects.link(o)
  for o in list(bpy.context.scene.objects):
   if o not in keep and o.type!='CAMERA':bpy.data.objects.remove(o,do_unlink=True)
  bpy.ops.wm.save_as_mainfile(filepath=str(p/f'model/hair-{section}.blend'))
 print('PHYSICAL_SPLIT_REQUIRES_VISUAL_REVIEW',counts)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--objects',nargs='+');p.add_argument('--blender',default='blender');a=p.parse_args();assert (a.project/'model/avatar.blend').is_file();cfg=json.loads((a.project/'realtime.json').read_text());assert str(cfg.get('workStatus','')).startswith('requires_'),'Existing reviewed projects must retain their semantic parts; do not blindly re-split';job=a.project/'source/split-parameters.json';job.write_text(json.dumps(dict(project=str(a.project.resolve()),objects=a.objects),indent=2)+'\n');subprocess.run([a.blender,'--background','--python-exit-code','1','--python',str(Path(__file__).resolve()),'--',str(job.resolve())],check=True)
if __name__=='__main__':
 if '--' in sys.argv:worker()
 else:main()
