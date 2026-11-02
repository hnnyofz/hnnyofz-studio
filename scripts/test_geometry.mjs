import assert from 'node:assert/strict';
import {Scene,cross,sub,dot} from '../assets/starter/geometry.mjs';
const tones={light:'#edbb78',mid:'#c88b4c',dark:'#926039',under:'#69452e'};
const s=new Scene({name:'Geometry checks',palette:Object.values(tones),outline:tones.under});
s.roundedBox('box',{center:[0,0,8],size:[12,10,6],radius:2,bevel:.7,tones});
s.beam('beam',{a:[0,0,0],b:[3,4,10],start:[3,4],end:[5,6],tones});
s.ellipsoid('sphere',{center:[0,0,8],radii:[6,7,8],tones});
s.lathe('bottle',{center:[0,0,0],profile:[[0,4],[1,5],[10,5],[13,3],[16,3]],tones});
const data=s.compile();assert.equal(data.parts.length,4);
for(const c of data.chunks){assert(c.structure>=1&&c.structure<=4);assert.equal(c.vertices.length%24,0);for(let i=0;i<c.vertices.length;i+=24){const a=c.vertices.slice(i,i+3),b=c.vertices.slice(i+8,i+11),cc=c.vertices.slice(i+16,i+19),n=c.vertices.slice(i+3,i+6);assert(Math.abs(Math.hypot(...n)-1)<1e-5);assert(dot(cross(sub(b,a),sub(cc,a)),n)>0);}}
for(const c of data.cameras){assert(c.viewProjection.every(Number.isFinite));assert(c.viewNormal.every(Number.isFinite));assert(c.orthographicSize>0);}
// All camera framing must contain the full yaw sweep, including top-down.
for(const camera of data.cameras)for(let a=0;a<360;a+=15)for(const p of s.vertices){const t=a*Math.PI/180,q=[p[0]*Math.cos(t)-p[1]*Math.sin(t),p[0]*Math.sin(t)+p[1]*Math.cos(t),p[2]],m=camera.viewProjection;for(const row of [0,1,2]){const v=m[row]*q[0]+m[4+row]*q[1]+m[8+row]*q[2]+m[12+row];assert(Math.abs(v)<1.001);}}
assert.throws(()=>s.roundedBox('box',{center:[0,0,0],size:[4,4,4],radius:1,tones}),/Duplicate/);
console.log('PASS: primitives, winding, normals, semantic IDs and full-turn camera framing');
