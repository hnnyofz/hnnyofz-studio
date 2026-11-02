// Small parameterized solid modeller. Z up; XY ground; geometry in model units.
// Each physical component owns one semantic ID, independent of material chunks.
export const add=(a,b)=>a.map((x,i)=>x+b[i]);
export const sub=(a,b)=>a.map((x,i)=>x-b[i]);
export const mul=(a,s)=>a.map(x=>x*s);
export const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);
export const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const norm=a=>mul(a,1/(Math.hypot(...a)||1));
const avg=ps=>ps.reduce((a,p)=>add(a,mul(p,1/ps.length)),[0,0,0]);
const rgb=s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16)/255);
function roundedRect(w,h,r,segments=6){
 if(!(w>0&&h>0))throw Error('Positive section dimensions required');
 r=Math.max(.001,Math.min(r,w/2-.0001,h/2-.0001));const points=[];
 for(const [cx,cy,start] of [[w/2-r,-h/2+r,-90],[w/2-r,h/2-r,0],[-w/2+r,h/2-r,90],[-w/2+r,-h/2+r,180]]){
  for(let i=0;i<=segments;i++){const a=(start+90*i/segments)*Math.PI/180;points.push([cx+r*Math.cos(a),cy+r*Math.sin(a)]);}
 }return points;
}
export class Scene{
 constructor({name,palette,outline,deepOutline,lightThreshold=.55,size=64,pivot=[0,0,0],cameraAngles=[30,45,60,90],groundShadow=true}){
  Object.assign(this,{name,palette,outline,deepOutline:deepOutline||outline,lightThreshold,size,pivot,cameraAngles,groundShadow});
  this.parts=[];this.materials=[];this.chunks=[];this.vertices=[];this.materialMap=new Map();
 }
 material(hex){if(!/^#[\da-f]{6}$/i.test(hex))throw Error('Invalid material '+hex);if(!this.materialMap.has(hex)){this.materialMap.set(hex,this.materials.length);this.materials.push({name:hex,color:rgb(hex),texture:-1});}return this.materialMap.get(hex);}
 solid(name,rings,tones,{moving=true}={}){
  if(this.parts.some(p=>p.name===name))throw Error('Duplicate part '+name);
  const id=this.parts.length+1;if(id>63)throw Error('Shader supports at most 63 physical parts');
  const all=rings.flat(),center=avg(all),chunks=new Map();
  const triangle=(a,b,c)=>{
   let n=cross(sub(b,a),sub(c,a));if(Math.hypot(...n)<1e-9)return;n=norm(n);
   if(dot(n,sub(avg([a,b,c]),center))<0){[b,c]=[c,b];n=mul(n,-1);}
   const light=dot(n,norm([.35,-.45,.83]));
   const hex=n[2]<-.45?(tones.under||tones.dark):light>.55?tones.light:light>.02?tones.mid:tones.dark;
   const material=this.material(hex);if(!chunks.has(material))chunks.set(material,[]);
   for(const p of [a,b,c]){chunks.get(material).push(...p,...n,0,0);this.vertices.push(p);}
  };
  for(let k=0;k<rings.length-1;k++){
   const a=rings[k],b=rings[k+1];if(a.length!==b.length)throw Error('Ring lengths differ');
   for(let i=0;i<a.length;i++){const j=(i+1)%a.length;triangle(a[i],a[j],b[j]);triangle(a[i],b[j],b[i]);}
  }
  for(const ring of [rings[0],rings.at(-1)]){const c=avg(ring);for(let i=0;i<ring.length;i++)triangle(c,ring[i],ring[(i+1)%ring.length]);}
  this.parts.push({id,name,moving});for(const [material,vertices]of chunks)this.chunks.push({name,structure:id,material,moving,vertices});return id;
 }
 // A rounded cuboid with optional bevelled top/bottom rims. center is true center.
 roundedBox(name,{center,size,radius,bevel=.6,tones,moving=true}){
  const [w,d,h]=size;bevel=Math.max(0,Math.min(bevel,h*.45,w*.2,d*.2));radius=Math.min(radius,w/2-.01,d/2-.01);
  const ring=(z,inset)=>roundedRect(w-2*inset,d-2*inset,Math.max(.001,radius-inset)).map(([x,y])=>add(center,[x,y,z]));
  const rings=bevel>0?[ring(-h/2,bevel),ring(-h/2+bevel,0),ring(h/2-bevel,0),ring(h/2,bevel)]:[ring(-h/2,0),ring(h/2,0)];
  return this.solid(name,rings,tones,{moving});
 }
 beam(name,{a,b,start,end=start,radius=.24,bevel=.45,tones,moving=true}){
  const axis=norm(sub(b,a)),len=Math.hypot(...sub(b,a));if(len<.01)throw Error('Zero-length beam');
  const u=norm(cross(axis,Math.abs(axis[2])>.9?[0,1,0]:[0,0,1])),v=cross(axis,u);
  bevel=Math.min(bevel,len*.08,...start.map(x=>x*.2),...end.map(x=>x*.2));
  const stations=bevel>0?[0,bevel/len,1-bevel/len,1]:[0,1];
  const rings=stations.map((t,i)=>{
   const w=start.map((x,k)=>x+(end[k]-x)*t),inset=bevel>0&&(i===0||i===3)?bevel:0;
   return roundedRect(w[0]-2*inset,w[1]-2*inset,Math.min(...w)*radius-inset*.25).map(([x,y])=>add(add(a,mul(sub(b,a),t)),add(mul(u,x),mul(v,y))));
  });return this.solid(name,rings,tones,{moving});
 }
 ellipsoid(name,{center,radii,tones,moving=true,segments=24,rings=12}){
  const rr=[];for(let j=0;j<=rings;j++){const lat=-Math.PI/2+j/rings*Math.PI;rr.push(Array.from({length:segments},(_,i)=>{const a=i/segments*2*Math.PI;return add(center,[radii[0]*Math.cos(lat)*Math.cos(a),radii[1]*Math.cos(lat)*Math.sin(a),radii[2]*Math.sin(lat)]);}));}
  return this.solid(name,rr,tones,{moving});
 }
 // Convex rotational bodies; profile is [[height,radius], ...] bottom to top.
 lathe(name,{center,profile,tones,moving=true,segments=32}){
  const rings=profile.map(([z,r])=>Array.from({length:segments},(_,i)=>{const a=i/segments*Math.PI*2;return add(center,[Math.cos(a)*r,Math.sin(a)*r,z]);}));
  return this.solid(name,rings,tones,{moving});
 }
 compile(){
  if(!this.vertices.length)throw Error('Scene has no geometry');
  const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const p of this.vertices)for(let k=0;k<3;k++){min[k]=Math.min(min[k],p[k]);max[k]=Math.max(max[k],p[k]);}
  const center=[this.pivot[0],this.pivot[1],(min[2]+max[2])/2],h=max[2]-min[2];
  const radius=this.vertices.reduce((r,p)=>Math.max(r,Math.hypot(p[0]-center[0],p[1]-center[1])),0);
  const cameras=this.cameraAngles.map(elevation=>{
   // +X is the model front: yaw 0 faces the front, 180 faces the back.
   const az=0,el=elevation*Math.PI/180;
   const right=[Math.sin(az),-Math.cos(az),0],up=[-Math.sin(el)*Math.cos(az),-Math.sin(el)*Math.sin(az),Math.cos(el)],toward=[Math.cos(el)*Math.cos(az),Math.cos(el)*Math.sin(az),Math.sin(el)];
   const orthographicSize=Math.max(2*radius,2*radius*Math.sin(el)+h*Math.cos(el))*1.16,depthRange=2*(radius+h+10),s=2/orthographicSize;
   const rows=[mul(right,s),mul(up,s),mul(toward,-2/depthRange)];
   const vp=[...Array(16)].map(()=>0);for(let col=0;col<3;col++)for(let row=0;row<3;row++)vp[col*4+row]=rows[row][col];
   for(let row=0;row<3;row++)vp[12+row]=-dot(rows[row],center);vp[15]=1;
   return {name:elevation+'°',elevation,orthographicSize,depthRange,viewProjection:vp,viewNormal:[right[0],up[0],toward[0],right[1],up[1],toward[1],right[2],up[2],toward[2]]};
  });
  return {schema:'chibi-pixel-1',name:this.name,parts:this.parts,chunks:this.chunks,materials:this.materials,textures:[],cameras,bounds:{min,max},settings:{name:this.name,size:this.size,pivot:this.pivot,rotationSign:-1,groundShadow:{enabled:this.groundShadow,groundZ:min[2],color:[.19,.15,.11],opacity:.26}}};
 }
}
