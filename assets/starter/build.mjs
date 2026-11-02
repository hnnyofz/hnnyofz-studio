import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url));
const input=resolve(process.argv[2]||root+'/scene.mjs'),out=resolve(process.argv[3]||root+'/dist');
const scene=(await import(pathToFileURL(input))).default;
if(!scene?.compile)throw Error('Scene module must export a Scene as default');
if(!Number.isInteger(scene.size)||scene.size<8||scene.size>128)throw Error('size must be 8–128');
if(!Array.isArray(scene.palette)||scene.palette.length<1||scene.palette.length>32)throw Error('palette requires 1–32 colors');
if(!scene.palette.includes(scene.outline)||!scene.palette.includes(scene.deepOutline))throw Error('Outline colors must be in palette');
const rgb=c=>{if(!/^#[\da-f]{6}$/i.test(c))throw Error('Invalid color '+c);return [1,3,5].map(i=>parseInt(c.slice(i,i+2),16)/255);};
const model=scene.compile();
for(const c of model.chunks)if(c.vertices.length%24||c.vertices.some(v=>!Number.isFinite(v))||!model.parts.some(p=>p.id===c.structure))throw Error('Invalid mesh '+c.name);
for(const c of model.cameras)if(c.viewProjection.some(x=>!Number.isFinite(x)))throw Error('Invalid camera');
// Preserve material indices and topology; each finish supplies matching tone ramps.
const specs=[{id:'original',name:scene.finishName||'原配色',colors:{},swatches:scene.finishSwatches||scene.palette.slice(-2)},...(scene.finishes||[])];
const seen=new Set();
model.finishes=specs.map(f=>{
 if(!/^[a-z0-9-]+$/.test(f.id)||seen.has(f.id))throw Error('Invalid/duplicate finish ID');seen.add(f.id);
 for(const [from,to] of Object.entries(f.colors||{})){rgb(from);rgb(to);if(!scene.palette.includes(from)&&!model.materials.some(m=>m.name===from))throw Error('Unknown finish source '+from);}
 const mapped=c=>f.colors?.[c]||c;
 const palette=scene.palette.map(c=>rgb(mapped(c)));
 return {id:f.id,name:String(f.name),swatches:(f.swatches||[]).map(c=>rgb(c)),materials:model.materials.map(m=>rgb(mapped(m.name))),palette,ink:rgb(mapped(scene.outline)),deep:rgb(mapped(scene.deepOutline))};
});
const hash=t=>createHash('sha256').update(t).digest('hex');
model.sourceSHA256=hash(await readFile(input));model.geometrySHA256=hash(JSON.stringify(model.chunks));
let runtime=await readFile(root+'/runtime.js','utf8');
for(const [key,value]of Object.entries({__SETTINGS__:JSON.stringify(model.settings),__PALETTE_COUNT__:scene.palette.length,__PALETTE__:scene.palette.map(c=>'vec3('+rgb(c).join(',')+')').join(','),__INK__:rgb(scene.outline).join(','),__DEEP__:rgb(scene.deepOutline).join(','),__LIGHT_THRESHOLD__:Number(scene.lightThreshold).toFixed(6)}))runtime=runtime.replaceAll(key,String(value));
const title=scene.name.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const page=(await readFile(root+'/viewer.html','utf8')).replaceAll('__TITLE__',title).replace('__MODEL__',JSON.stringify(model).replaceAll('<','\\u003c')).replace('__RUNTIME__',runtime.replaceAll('</script','<\\/script'));
if(/__[A-Z_]+__/.test(page))throw Error('Unexpanded build token');
await mkdir(out,{recursive:true});
await writeFile(out+'/preview.html',page);await writeFile(out+'/model.json',JSON.stringify(model));await writeFile(out+'/runtime.js',runtime);
await writeFile(out+'/build.json',JSON.stringify({name:scene.name,sourceSHA256:model.sourceSHA256,geometrySHA256:model.geometrySHA256,runtimeSHA256:hash(runtime),parts:model.parts.length,triangles:model.chunks.reduce((n,c)=>n+c.vertices.length/24,0),status:'built_requires_browser_visual_review'},null,2));
console.log(out+'/preview.html');
