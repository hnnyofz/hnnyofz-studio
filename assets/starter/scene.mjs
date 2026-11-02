import {Scene} from './geometry.mjs';
import {furnitureFinishes} from './finishes.mjs';
// The shape brief: a small, broad, soft wooden chair; thick biscuit seat,
// stubby splayed feet and a large crown. Preserve air between the back splats.
// Tune silhouette first, then inspect at 48/64px. No anatomy/exploded view needed.
export const design={seatWidth:54,seatDepth:49,seatThickness:6,seatHeight:36,seatRadius:8,legLength:30,footWidth:6.2,shoulderWidth:8.6,backTop:65,backLean:.1};
const oak={light:'#edbb78',mid:'#c88b4c',dark:'#926039',under:'#69452e'};
const s=new Scene({name:'圆木小椅',size:64,palette:['#30251d','#69452e','#926039','#c88b4c','#edbb78'],outline:'#30251d',deepOutline:'#69452e',cameraAngles:[35.264,30,45,60,90]});
const p=(x,y,z)=>[x-27,y-27,z];
const beam=(name,a,b,start,end=start)=>s.beam(name,{a:p(...a),b:p(...b),start,end,tones:oak});
for(const front of [false,true])for(const side of [false,true]){
 beam(`${front?'前':'后'}${side?'左':'右'}腿`,[front?47:6,side?48:6,0],[front?43:10,side?44:10,design.legLength],[design.footWidth,design.footWidth],[design.shoulderWidth,design.shoulderWidth]);
}
for(const [i,y]of [8.1,45.9].entries())beam('侧横撑'+i,[8.1,y,14],[44.9,y,14],[3.5,3.5]);
beam('中央横撑',[26,8.1,14],[26,45.9,14],[3.5,3.5]);
for(const [i,y]of [10,44].entries())beam('侧围板'+i,[10,y,27.2],[43,y,27.2],[3.4,5.6]);
for(const [i,x]of [10,43].entries())beam('前后围板'+i,[x,10,27.2],[x,44,27.2],[3.4,5.6]);
s.roundedBox('厚座板',{center:p(27.5,27,design.seatHeight-design.seatThickness/2),size:[design.seatDepth,design.seatWidth,design.seatThickness],radius:design.seatRadius,bevel:1.1,tones:oak});
const bx=z=>9-(z-design.seatHeight)*design.backLean;
for(const [i,y]of [9,45].entries())beam('靠背立柱'+i,[bx(35),y,35],[bx(design.backTop-4),y,design.backTop-4],[5.6,5.6]);
beam('靠背下横梁',[bx(41),9,41],[bx(41),45,41],[3.8,4.5]);
for(const [i,y]of [18,27,36].entries())beam('靠背竖条'+i,[bx(42),y,42],[bx(57),y,57],[3.4,6.3],[3.4,7.2]);
// Vertical rounded crown: reuse solid() with rings on the X plane.
const crown=new Scene({name:'construction',palette:s.palette,outline:s.outline});
crown.roundedBox('crown',{center:[0,0,0],size:[44,11.5,7],radius:4.1,bevel:.7,tones:oak});
// General axis rotation applied to triangles (and normals), retaining one part ID.
const cid=s.parts.length+1;s.parts.push({id:cid,name:'大圆角靠背',moving:true});
for(const c of crown.chunks){const out=[];for(let i=0;i<c.vertices.length;i+=8){const [x,y,z,nx,ny,nz,u,v]=c.vertices.slice(i,i+8),pt=p(6.7+z,27+x,design.backTop-5.75+y);out.push(...pt,nz,nx,ny,u,v);s.vertices.push(pt);}s.chunks.push({...c,structure:cid,name:'大圆角靠背',material:s.material(crown.materials[c.material].name),vertices:out});}
s.finishes=furnitureFinishes(oak);
s.finishName="原木色";
s.finishSwatches=[oak.light,oak.dark];
export default s;
