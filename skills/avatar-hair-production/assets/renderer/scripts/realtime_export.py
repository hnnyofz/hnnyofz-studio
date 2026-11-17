"""Export physical geometry and semantic components for the structural shader."""
import bpy,json,base64,hashlib
from pathlib import Path
from mathutils import Matrix
import sys
args=sys.argv[sys.argv.index('--')+1:];spec=Path(args[0]).resolve();P=Path(args[1]).resolve();cfg=json.loads(spec.read_text())
if cfg.get('scene'):
 assert cfg['scene'] in bpy.data.scenes, 'Missing declared scene: '+cfg['scene']
 bpy.context.window.scene=bpy.data.scenes[cfg['scene']]
s=bpy.context.scene;s.frame_set(cfg.get('frame',1));bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
cam=s.camera
def column(m):return [m[r][c] for c in range(4) for r in range(4)]
def srgb(c):return 12.92*c if c<=.0031308 else 1.055*c**(1/2.4)-.055
materials=[];ids={};images=[];imageids={};parts=[];chunks=[]
assignment={}
for sid,(label,names) in enumerate(cfg['parts'].items(),1):
 for name in names:
  assert name not in assignment, 'Duplicate part assignment: '+name
  assignment[name]=sid
assert 1<=len(cfg['parts'])<=63
for ob in s.objects:
 if ob.type!='MESH' or ob.hide_render:continue
 root=ob
 while root.parent:root=root.parent
 moving=root.name==cfg['movingRoot']
 assert ob.name in assignment, 'Missing part ID: '+ob.name
 assert moving or root.name in cfg.get('fixedRoots',[]), 'Undeclared fixed root: '+root.name
 part=1;sid=assignment[ob.name]
 ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();uv=me.uv_layers.active
 grouped={}
 for tri in me.loop_triangles:
  mat=me.materials[tri.material_index] if tri.material_index<len(me.materials) else None
  key=mat.name if mat else 'fallback'
  if key not in ids:
   color=[.3,.35,.45];texid=-1
   assert mat and mat.use_nodes, 'Use an Emission material: '+key
   if mat and mat.use_nodes:
    em=next((n for n in mat.node_tree.nodes if n.type=='EMISSION'),None)
    assert em is not None, 'Bake material to Emission color/image first: '+key
    if em:color=[srgb(c) for c in em.inputs['Color'].default_value[:3]]
    links=em.inputs['Color'].links
    tex=links[0].from_node if links else None
    assert tex is None or (tex.type=='TEX_IMAGE' and tex.image), 'Bake procedural color first: '+key
    if tex:
     im=tex.image
     if im.name not in imageids:
      if not im.packed_file:im.pack()
      imageids[im.name]=len(images);images.append({'name':im.name,'data':'data:image/png;base64,'+base64.b64encode(bytes(im.packed_file.data)).decode()})
     texid=imageids[im.name]
   ids[key]=len(materials);materials.append({'name':key,'color':color,'texture':texid})
  mi=ids[key];buf=grouped.setdefault(mi,[])
  normal=(ev.matrix_world.to_3x3().inverted().transposed()@tri.normal).normalized()
  for vi,li in zip(tri.vertices,tri.loops):
   v=ev.matrix_world@me.vertices[vi].co;u=uv.data[li].uv if uv else (0,0)
   buf.extend([round(x,6) for x in [*v,*normal,*u]])
 for mi,buf in grouped.items():chunks.append({'name':ob.name,'part':part,'structure':sid,'moving':moving,'material':mi,'casterId':int(ob.get('caster_id',0)),'vertices':buf})
 parts.append({'name':ob.name,'part':part,'structure':sid,'moving':moving,'vertices':len(me.vertices),'matrix':column(ev.matrix_world)})
 ev.to_mesh_clear()
cameras=[]
for name in cfg['cameras']:
 cam=s.objects[name];assert cam.type=='CAMERA' and cam.data.type=='ORTHO','Use actual orthographic cameras'
 vp=cam.calc_matrix_camera(deps,x=cfg['size'],y=cfg['size'])@cam.matrix_world.inverted()
 cameras.append({'name':name,'viewProjection':column(vp),'viewNormal':[cam.matrix_world.inverted().to_3x3()[r][c] for c in range(3) for r in range(3)],'orthographicSize':cam.data.ortho_scale,'depthRange':cam.data.clip_end-cam.data.clip_start})
data={'version':'1.0','cameras':cameras,'materials':materials,'textures':images,'chunks':chunks,'parts':parts,'sourceSHA256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()}
(P/'model.json').write_text(json.dumps(data,separators=(',',':')))
