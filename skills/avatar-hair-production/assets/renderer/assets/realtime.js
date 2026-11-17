'use strict';
const SETTINGS=__SETTINGS__;
const $=id=>document.getElementById(id),canvas=$('view');
const gl=canvas.getContext('webgl2',{alpha:false,antialias:false,preserveDrawingBuffer:true});
function fail(e){$('error').hidden=false;$('error').textContent='实时渲染无法启动：'+e.message;$('stats').textContent='未启动';console.error(e)}
const fullscreen=`#version 300 es
precision highp float;out vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0,1);}`;
const meshVert=`#version 300 es
precision highp float;layout(location=0) in vec3 position;layout(location=1) in vec3 normal;layout(location=2) in vec2 texcoord;
uniform mat4 vp;uniform float yaw;uniform bool moving;uniform vec3 pivot;uniform float rotationSign;out vec2 uv;out vec3 n;
void main(){float a=moving?rotationSign*yaw:0.;float c=cos(a),s=sin(a);mat3 r=mat3(c,s,0,-s,c,0,0,0,1);gl_Position=vp*vec4(moving?r*(position-pivot)+pivot:position,1);uv=texcoord;n=r*normal;}`;
const meshFrag=`#version 300 es
precision highp float;
in vec2 uv;in vec3 n;
uniform sampler2D paint;uniform bool textured;uniform vec3 color;
uniform float part,structure,casterId;uniform mat3 viewNormal;uniform float fixedHairLight;
layout(location=0) out vec4 beauty;layout(location=1) out vec4 info;layout(location=2) out vec4 geometryInfo;
vec2 packDepth(float z){float v=floor(z*65535.+.5);return vec2(floor(v/256.),mod(v,256.))/255.;}
void main(){beauty=vec4(textured?texture(paint,uv).rgb:color,1);if(fixedHairLight>.5&&!textured){float diffuse=max(0.,dot(normalize(n),normalize(vec3(-.45,-.65,.73))));beauty.rgb=clamp(color*(.62+.65*diffuse),0.,1.);}info=vec4(packDepth(gl_FragCoord.z),casterId/5.,part/8.);geometryInfo=vec4(normalize(viewNormal*n)*.5+.5,structure/255.);}`;
const sampleFrag=`#version 300 es
precision highp float;
in vec2 uv;uniform sampler2D beauty,info,geometryInfo;uniform bool quantize;
layout(location=0) out vec4 pixel;layout(location=1) out vec4 partInfo;
layout(location=2) out vec4 surfaceDepth;layout(location=3) out vec4 surfaceNormal;
const vec3 pal[__PALETTE_COUNT__]=vec3[__PALETTE_COUNT__](__PALETTE__);
float depth(vec2 rg){return dot(rg*255.,vec2(256.,1.))/65535.;}
vec2 packDepth(float z){float v=floor(z*65535.+.5);return vec2(floor(v/256.),mod(v,256.))/255.;}
void main(){
 ivec2 origin=ivec2(gl_FragCoord.xy)*8;
 float counts[64];for(int k=0;k<64;k++)counts[k]=0.;float coverage=0.;
 for(int y=0;y<8;y++)for(int x=0;x<8;x++){
  ivec2 p=origin+ivec2(x,y);if(texelFetch(beauty,p,0).a>.5){coverage++;int s=int(round(texelFetch(geometryInfo,p,0).a*255.));counts[s]++;}
 }
 if(coverage<32.){pixel=partInfo=surfaceDepth=surfaceNormal=vec4(0);return;}
 int chosen=1;for(int k=2;k<64;k++)if(counts[k]>counts[chosen])chosen=k;
 float votes[__PALETTE_COUNT__];for(int k=0;k<__PALETTE_COUNT__;k++)votes[k]=0.;float families[8];for(int k=0;k<8;k++)families[k]=0.;
 vec3 sum=vec3(0),normalSum=vec3(0);float z=0.,samples=0.;
 // Color, depth and normal all belong to the same dominant visible component.
 // This avoids sampling a rear part's color into a front part's outline cell.
 for(int y=0;y<8;y++)for(int x=0;x<8;x++){
  ivec2 p=origin+ivec2(x,y);vec4 g=texelFetch(geometryInfo,p,0),c=texelFetch(beauty,p,0);
  if(c.a>.5&&int(round(g.a*255.))==chosen){
   vec4 i=texelFetch(info,p,0);samples++;sum+=c.rgb;normalSum+=g.rgb*2.-1.;z+=depth(i.rg);
   families[int(round(i.a*8.))]++;
   int best=0;float d=100.;for(int k=0;k<__PALETTE_COUNT__;k++){float v=dot(c.rgb-pal[k],c.rgb-pal[k]);if(v<d){d=v;best=k;}}votes[best]++;
  }
 }
 int color=0,family=1;for(int k=1;k<__PALETTE_COUNT__;k++)if(votes[k]>votes[color])color=k;
 for(int k=2;k<8;k++)if(families[k]>families[family])family=k;
 pixel=vec4(quantize?pal[color]:sum/samples,1);partInfo=vec4(float(family)/8.,float(chosen)/255.,0,1);
 surfaceDepth=vec4(packDepth(z/samples),0,1);surfaceNormal=vec4(normalize(normalSum)*.5+.5,1);
}`;
const finishFrag=`#version 300 es
precision highp float;
in vec2 uv;uniform sampler2D pixels,parts,depths,normals;uniform bool outline,shadow,structural;
uniform float worldPixel,depthRange;
layout(location=0) out vec4 result;layout(location=1) out vec4 edgeInfo;
const vec3 ink=vec3(__INK__),deep=ink;
vec4 at(ivec2 p){ivec2 s=textureSize(pixels,0);if(any(lessThan(p,ivec2(0)))||any(greaterThanEqual(p,s)))return vec4(0);return texelFetch(pixels,p,0);}
int id(ivec2 p){return at(p).a<.5?0:int(round(texelFetch(parts,p,0).r*8.));}
int component(ivec2 p){return at(p).a<.5?0:int(round(texelFetch(parts,p,0).g*255.));}
float depth(ivec2 p){return dot(texelFetch(depths,p,0).rg*255.,vec2(256.,1.))/65535.;}
vec3 normal(ivec2 p){return normalize(texelFetch(normals,p,0).rgb*2.-1.);}
// Compare the two surfaces at their shared pixel edge, not their centers.
// Normal-based plane extrapolation avoids assigning a sloped face's edge to
// its rear neighbor merely because the two samples are one pixel apart.
float edgeDepth(ivec2 p,vec2 delta){vec3 n=normal(p);vec2 slope=abs(n.z)>.25?clamp(n.xy/n.z,vec2(-2.),vec2(2.)):vec2(0);return depth(p)+dot(slope,delta)*worldPixel/depthRange;}
bool ownsContact(ivec2 p,ivec2 q){
 int a=component(p),b=component(q);if(b==0||a==b)return false;
 // Reuse an existing ink band at the shared boundary instead of adding a
 // second parallel stroke to its neighbor. Surface paint and shader ink
 // must share one edge budget, especially on two-pixel-thick seat bands.
 bool pa=distance(at(p).rgb,ink)<.01,pb=distance(at(q).rgb,ink)<.01;
 if(pa!=pb)return pa;
 vec2 delta=vec2(q-p)*.5;
 float za=edgeDepth(p,delta),zb=edgeDepth(q,-delta);
 // Near-equal contact depths use a stable component priority. Reversing p/q
 // selects the same owner, so each shared edge has exactly one owner.
 return abs(za-zb)>.0002?za<zb:a<b;
}
void main(){
 ivec2 p=ivec2(gl_FragCoord.xy);vec4 c=at(p);int k=id(p);
 ivec2 U=ivec2(0,1),D=ivec2(0,-1),L=ivec2(-1,0),R=ivec2(1,0);
 bool exterior=false,contact=false;
 if(c.a>.5&&outline){
  exterior=at(p+U).a<.5||at(p+D).a<.5||at(p+L).a<.5||at(p+R).a<.5;
  if(exterior)c.rgb=ink;
  contact=structural&&(ownsContact(p,p+U)||ownsContact(p,p+D)||ownsContact(p,p+L)||ownsContact(p,p+R));
  if(contact)c.rgb=ink;
 }

 result=c;edgeInfo=vec4(exterior?1.:0.,contact?1.:0.,0,1);
}`;
const displayFrag=`#version 300 es
precision highp float;in vec2 uv;uniform sampler2D source;uniform bool pixelated;uniform bool background;out vec4 result;
void main(){vec4 c;if(pixelated){ivec2 s=textureSize(source,0);c=texelFetch(source,clamp(ivec2(uv*vec2(s)),ivec2(0),s-1),0);}else c=texture(source,uv);if(!background){result=c;return;}float check=mod(floor(gl_FragCoord.x/12.)+floor(gl_FragCoord.y/12.),2.);vec3 bg=mix(vec3(.88,.91,.95),vec3(.84,.88,.93),check);result=vec4(mix(bg,c.rgb,c.a),1);}`;
function program(v,f){function shader(type,src){let s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}let p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p}
function uni(p,name,value,type='1i'){let u=gl.getUniformLocation(p,name);if(type==='Matrix4fv')gl.uniformMatrix4fv(u,false,value);else if(type==='Matrix3fv')gl.uniformMatrix3fv(u,false,value);else gl['uniform'+type](u,...(Array.isArray(value)?value:[value]))}
function bind(p,name,t,unit){gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);uni(p,name,unit)}
function texture(w,h,filter=gl.NEAREST){let t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,null);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,filter);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,filter);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return t}
function target(w,h,count=1,depth=false){let f=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,f);let ts=[];for(let i=0;i<count;i++){let t=texture(w,h);ts.push(t);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0+i,gl.TEXTURE_2D,t,0)}gl.drawBuffers(ts.map((_,i)=>gl.COLOR_ATTACHMENT0+i));let d=null;if(depth){d=gl.createRenderbuffer();gl.bindRenderbuffer(gl.RENDERBUFFER,d);gl.renderbufferStorage(gl.RENDERBUFFER,gl.DEPTH_COMPONENT24,w,h);gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.RENDERBUFFER,d)}if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('渲染缓冲区不可用');return {f,ts,d,w,h}}
function dispose(t){if(!t)return;t.ts.forEach(t=>gl.deleteTexture(t));if(t.d)gl.deleteRenderbuffer(t.d);gl.deleteFramebuffer(t.f)}
function useTarget(t){gl.bindFramebuffer(gl.FRAMEBUFFER,t?.f??null);gl.viewport(0,0,t?.w??canvas.width,t?.h??canvas.height)}
const state={angle:0,speed:30,direction:1,playing:false,draws:0,frames:0};
async function start(){if(!gl)throw Error('浏览器不支持WebGL2');const data=$('model-data')?JSON.parse($('model-data').textContent):await (await fetch('model.json')).json();let mesh=program(meshVert,meshFrag),sample=program(fullscreen,sampleFrag),finish=program(fullscreen,finishFrag),display=program(fullscreen,displayFrag);let empty=gl.createVertexArray();
const paints=data.textures.map(t=>{let tex=texture(t.width,t.height);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,t.width,t.height,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(t.rgba));return tex});
const fallback=texture(1,1);const chunks=data.chunks.map(c=>{let vao=gl.createVertexArray();gl.bindVertexArray(vao);let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(c.vertices),gl.STATIC_DRAW);for(let i=0;i<3;i++){gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,i===2?2:3,gl.FLOAT,false,32,i===0?0:i===1?12:24)}return {...c,vertices:null,vao,count:c.vertices.length/8}});
let high,low,final,dirty=true;let camera=data.cameras[0];$('elevation').innerHTML=data.cameras.map((c,i)=>`<option value="${i}">${c.name}</option>`).join('');$('elevation').onchange=()=>{camera=data.cameras[+$('elevation').value];dirty=true};$('grid').innerHTML=[...new Set([SETTINGS.size,48,64,96])].map(n=>`<option value="${n}">${n} × ${n}</option>`).join('');new ResizeObserver(()=>dirty=true).observe(canvas);function allocate(){let n=+$('grid').value;dispose(high);dispose(low);dispose(final);high=target(n*8,n*8,3,true);low=target(n,n,4);final=target(n,n,2);dirty=true}allocate();$('grid').onchange=allocate;
function geometry(){useTarget(high);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(mesh);uni(mesh,'pivot',SETTINGS.pivot,'3f');uni(mesh,'rotationSign',SETTINGS.rotationSign,'1f');uni(mesh,'vp',camera.viewProjection,'Matrix4fv');uni(mesh,'yaw',state.angle*Math.PI/180,'1f');uni(mesh,'viewNormal',camera.viewNormal,'Matrix3fv');for(const c of chunks){if($('baseOnly').checked&&c.moving)continue;let m=data.materials[c.material];uni(mesh,'fixedHairLight',SETTINGS.hairLighting==='fixed-normal'&&SETTINGS.hairPartIDs.includes(c.structure)&&m.texture<0?1:0,'1f');uni(mesh,'moving',c.moving?1:0);uni(mesh,'casterId',c.casterId||0,'1f');uni(mesh,'structure',c.structure,'1f');uni(mesh,'part',1,'1f');uni(mesh,'textured',m.texture>=0?1:0);uni(mesh,'color',m.color,'3f');bind(mesh,'paint',m.texture>=0?paints[m.texture]:fallback,0);gl.bindVertexArray(c.vao);gl.drawArrays(gl.TRIANGLES,0,c.count)}gl.disable(gl.DEPTH_TEST);gl.bindVertexArray(empty)}
function pixels(){useTarget(low);gl.useProgram(sample);bind(sample,'beauty',high.ts[0],0);bind(sample,'info',high.ts[1],1);bind(sample,'geometryInfo',high.ts[2],2);uni(sample,'quantize',$('palette').checked?1:0);gl.drawArrays(gl.TRIANGLES,0,3);useTarget(final);gl.useProgram(finish);bind(finish,'pixels',low.ts[0],0);bind(finish,'parts',low.ts[1],1);bind(finish,'depths',low.ts[2],2);bind(finish,'normals',low.ts[3],3);uni(finish,'worldPixel',camera.orthographicSize/low.w,'1f');uni(finish,'depthRange',camera.depthRange,'1f');uni(finish,'structural',$('structural').checked?1:0);uni(finish,'outline',$('outline').checked?1:0);uni(finish,'shadow',0);gl.drawArrays(gl.TRIANGLES,0,3)}
function screen(){const dpr=Math.min(devicePixelRatio,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}useTarget(null);gl.clearColor(.86,.90,.95,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(display);uni(display,'background',1);let panel=Math.floor(w/2),size=Math.min(panel-24*dpr,h-68*dpr);let ps=Math.max(1,Math.floor(size/final.w));let actual=ps*final.w;let y=Math.round((h-actual)/2-4*dpr);for(let side=0;side<2;side++){gl.viewport(Math.round(panel*side+(panel-actual)/2),y,actual,actual);bind(display,'source',side?final.ts[0]:high.ts[0],0);uni(display,'pixelated',side);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,side?gl.NEAREST:gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,side?gl.NEAREST:gl.LINEAR);gl.drawArrays(gl.TRIANGLES,0,3)}}
function draw(){geometry();pixels();screen();state.draws++;dirty=false;if(document.activeElement!==$('angleNumber'))$('angleNumber').value=state.angle.toFixed(1);$('angleText').textContent=state.angle.toFixed(1)+'°';$('angle').value=state.angle.toFixed(1)}
function playing(v){state.playing=v;dirty=true;$('play').textContent=v?'暂停':'播放';$('play').setAttribute('aria-pressed',v)}playing(state.playing);$('play').onclick=()=>playing(!state.playing);$('reverse').onclick=()=>{state.direction*=-1;$('reverse').textContent=state.direction===1?'反向':'恢复正向'};$('reset').onclick=()=>{playing(false);state.angle=0;dirty=true};$('angle').oninput=()=>{playing(false);state.angle=+$('angle').value;dirty=true};$('angleNumber').oninput=()=>{let a=+$('angleNumber').value;if(Number.isFinite(a)){playing(false);state.angle=(a+3600)%360;dirty=true}};for(const id of ['outline','structural','palette','baseOnly'])$(id).onchange=()=>dirty=true;$('speed').oninput=()=>{state.speed=+$('speed').value;$('speedText').textContent=state.speed+'° / 秒'};
let drag=null;canvas.onpointerdown=e=>{playing(false);drag={x:e.clientX,a:state.angle};canvas.setPointerCapture(e.pointerId)};canvas.onpointermove=e=>{if(drag){state.angle=(drag.a+(e.clientX-drag.x)*.55+3600)%360;dirty=true}};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;
function footVisibility(){let bytes=new Uint8Array(high.w*high.h*4);gl.bindFramebuffer(gl.FRAMEBUFFER,high.f);gl.readBuffer(gl.COLOR_ATTACHMENT1);gl.readPixels(0,0,high.w,high.h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);gl.readBuffer(gl.COLOR_ATTACHMENT0);let counts=[0,0,0,0],native=[0,0,0,0];for(let y=0;y<low.h;y++)for(let x=0;x<low.w;x++){let cell=[0,0,0,0];for(let v=0;v<8;v++)for(let u=0;u<8;u++){let b=((y*8+v)*high.w+x*8+u)*4;let id=Math.round(bytes[b+2]*5/255);if(bytes[b+3]&&id>=1&&id<=4){counts[id-1]++;cell[id-1]++;}}for(let i=0;i<4;i++)if(cell[i]>=32)native[i]++;}return {samples:counts,majorityPixels:native};}
// Export the actual depth-tested part buffer alongside review captures.
function targetPNG(t,attachment=0){
 let bytes=new Uint8Array(t.w*t.h*4);gl.bindFramebuffer(gl.FRAMEBUFFER,t.f);
 gl.readBuffer(gl.COLOR_ATTACHMENT0+attachment);gl.readPixels(0,0,t.w,t.h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);gl.readBuffer(gl.COLOR_ATTACHMENT0);
 let c=document.createElement('canvas');c.width=t.w;c.height=t.h;let ctx=c.getContext('2d'),out=ctx.createImageData(t.w,t.h);
 for(let y=0;y<t.h;y++)out.data.set(bytes.subarray((t.h-y-1)*t.w*4,(t.h-y)*t.w*4),y*t.w*4);
 ctx.putImageData(out,0,0);return c.toDataURL();
}
$('sweep').onclick=()=>{playing(false);let old=state.angle;$('diagnostics').innerHTML='';for(let a of [...Array.from({length:72},(_,i)=>i*5),57.3,179,181,360]){state.angle=a;draw();let visible=footVisibility();let n=final.w,bytes=new Uint8Array(n*n*4);gl.bindFramebuffer(gl.FRAMEBUFFER,final.f);gl.readPixels(0,0,n,n,gl.RGBA,gl.UNSIGNED_BYTE,bytes);let c=document.createElement('canvas');c.width=c.height=n;let ctx=c.getContext('2d'),out=ctx.createImageData(n,n);for(let y=0;y<n;y++)out.data.set(bytes.subarray((n-y-1)*n*4,(n-y)*n*4),y*n*4);ctx.putImageData(out,0,0);let im=document.createElement('img');im.alt='angle-'+a;im.dataset.legs=JSON.stringify(visible);im.dataset.parts=targetPNG(low,1);im.dataset.depth=targetPNG(low,2);im.dataset.normals=targetPNG(low,3);im.dataset.edges=targetPNG(final,1);im.dataset.raw=targetPNG(low,0);im.src=c.toDataURL();im.style='width:64px;height:64px;image-rendering:pixelated';$('diagnostics').appendChild(im)}state.angle=old;draw()};
$('diagnose').onclick=()=>{playing(false);draw();$('diagnostics').innerHTML='';for(let [name,target,attachment] of [['raw',low,0],['parts',low,1],['high',high,0],['object-ids',high,1],['structure',high,2],['depth',low,2],['normals',low,3],['edges',final,1]]){let n=target.w,bytes=new Uint8Array(n*n*4);gl.bindFramebuffer(gl.FRAMEBUFFER,target.f);gl.readBuffer(gl.COLOR_ATTACHMENT0+attachment);gl.readPixels(0,0,n,n,gl.RGBA,gl.UNSIGNED_BYTE,bytes);gl.readBuffer(gl.COLOR_ATTACHMENT0);let c=document.createElement('canvas');c.width=c.height=n;let ctx=c.getContext('2d'),out=ctx.createImageData(n,n);for(let y=0;y<n;y++)out.data.set(bytes.subarray((n-y-1)*n*4,(n-y)*n*4),y*n*4);ctx.putImageData(out,0,0);let im=document.createElement('img');im.id='diagnostic-'+name;im.alt=name;im.src=c.toDataURL();im.style='width:128px;height:128px;image-rendering:pixelated';$('diagnostics').appendChild(im)}screen()};
$('capture').onclick=()=>{playing(false);draw();let n=final.w,bytes=new Uint8Array(n*n*4);gl.bindFramebuffer(gl.FRAMEBUFFER,final.f);gl.readPixels(0,0,n,n,gl.RGBA,gl.UNSIGNED_BYTE,bytes);let c=document.createElement('canvas');c.width=c.height=n;let ctx=c.getContext('2d'),out=ctx.createImageData(n,n);for(let y=0;y<n;y++)out.data.set(bytes.subarray((n-y-1)*n*4,(n-y)*n*4),y*n*4);ctx.putImageData(out,0,0);let a=document.createElement('a');a.download=SETTINGS.name+'-'+state.angle.toFixed(1)+'deg-'+n+'px.png';a.href=c.toDataURL();$('snapshot').src=a.href;$('saved').hidden=false;$('savedText').textContent=state.angle.toFixed(1)+'° · '+n+' × '+n+' 透明 PNG';$('saveLink').href=a.href;$('saveLink').download=a.download;screen()};

function zipStore(files){let chunks=[],directory=[],offset=0,encoder=new TextEncoder();
 function crc(bytes){let c=0xffffffff;for(let b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
 for(let [name,bytes] of files){let n=encoder.encode(name),sum=crc(bytes),h=new Uint8Array(30+n.length),v=new DataView(h.buffer);v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint32(14,sum,true);v.setUint32(18,bytes.length,true);v.setUint32(22,bytes.length,true);v.setUint16(26,n.length,true);h.set(n,30);chunks.push(h,bytes);
 let d=new Uint8Array(46+n.length),w=new DataView(d.buffer);w.setUint32(0,0x02014b50,true);w.setUint16(4,20,true);w.setUint16(6,20,true);w.setUint32(16,sum,true);w.setUint32(20,bytes.length,true);w.setUint32(24,bytes.length,true);w.setUint16(28,n.length,true);w.setUint32(42,offset,true);d.set(n,46);directory.push(d);offset+=h.length+bytes.length;}
 let end=new Uint8Array(22),v=new DataView(end.buffer);v.setUint32(0,0x06054b50,true);v.setUint16(8,files.length,true);v.setUint16(10,files.length,true);v.setUint32(12,directory.reduce((n,d)=>n+d.length,0),true);v.setUint32(16,offset,true);return new Blob([...chunks,...directory,end],{type:'application/zip'});
}
$('exportSequence').onclick=async()=>{playing(false);let old=state.angle,step=+$('exportStep').value,files=[],frames=[];$('exportSequence').disabled=true;
 try{for(let a=0;a<360;a+=step){state.angle=a;draw();let uri=targetPNG(final),bytes=Uint8Array.from(atob(uri.split(',')[1]),c=>c.charCodeAt(0)),name=`frames/angle-${String(a).padStart(3,'0')}.png`;files.push([name,bytes]);frames.push({angle:a,file:name});}
 files.push(['manifest.json',new TextEncoder().encode(JSON.stringify({name:SETTINGS.name,size:final.w,camera:camera.name,sourceSHA256:data.sourceSHA256,provenance:'live WebGL model, no original frame substitution',outline:$('outline').checked,structural:$('structural').checked,palette:$('palette').checked,frames},null,2))]);
 let url=URL.createObjectURL(zipStore(files));$('sequenceDownload').href=url;$('sequenceDownload').download=SETTINGS.name+'-'+step+'deg.zip';$('sequenceDownload').hidden=false;$('sequenceDownload').textContent='下载 '+frames.length+' 帧 PNG ZIP';
 }finally{state.angle=old;draw();$('exportSequence').disabled=false;}};
draw();$('controls').disabled=false;let previous=null,lastSample=performance.now(),count=0;document.addEventListener('visibilitychange',()=>previous=null);function tick(now){if(!document.hidden){if(previous!==null&&state.playing)state.angle=(state.angle+Math.min(now-previous,100)*state.speed*state.direction/1000+360)%360;if(state.playing||dirty){draw();count++}if(now-lastSample>=1000){$('stats').textContent=(state.playing?Math.round(count*1000/(now-lastSample))+' 帧/秒（页面刷新）':'已暂停')+' · '+low.w+'² 像素';count=0;lastSample=now}}previous=now;requestAnimationFrame(tick)}requestAnimationFrame(tick);
window.addEventListener('webglcontextlost',e=>{e.preventDefault();playing(false);fail(Error('图形上下文已中断，请刷新页面'))});$('stats').textContent='WebGL2 实时渲染';}
start().catch(fail);
