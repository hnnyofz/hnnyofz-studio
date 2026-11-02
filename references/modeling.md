# Authoring geometry

`assets/starter/scene.mjs` is a complete chair example. Replace its object design; preserve the export contract. `geometry.mjs` is a small solid modeller, not a general CAD kernel. Z is up, XY is ground, units are arbitrary. Author the object facing +X: preview yaw 0° is front, 90°/270° are sides, and 180° is back. Camera elevation remains independent of this yaw convention. Keep the pivot near the object's XY centre so the entire object stays framed during rotation.

```js
import {Scene} from './geometry.mjs';
const tones = {light:'#edbb78', mid:'#c88b4c', dark:'#926039', under:'#69452e'};
const scene = new Scene({
  name:'小柜子', size:64, pivot:[0,0,0],
  palette:['#30251d','#69452e','#926039','#c88b4c','#edbb78'],
  outline:'#30251d', deepOutline:'#69452e', cameraAngles:[35.264,45,60,90]
});
scene.roundedBox('柜体', {center:[0,0,25],size:[30,36,40],radius:5,bevel:1,tones});
export default scene;
```

## Primitives

- `roundedBox(name,{center,size:[x,y,z],radius,bevel,tones,moving=true})`: rounded XY plan extruded in Z, with inset top/bottom bevel rings. It is not a uniformly spherical fillet. For a vertically rounded front panel, rotate the geometry or use `solid()` with rings mapped to that plane.
- `beam(name,{a,b,start:[u,v],end=start,radius=.24,bevel=.45,tones,moving=true})`: a tapered rounded rectangular section between two points. `radius` is a fraction of the smaller section dimension. For vertical beams local U generally follows X and V follows Y; inspect horizontal beams before choosing width versus thickness.
- `ellipsoid(name,{center,radii:[x,y,z],tones,segments=24,rings=12})`: rounded body useful for soft bulbs, feet or knobs.
- `lathe(name,{center,profile:[[height,radius],...],tones,segments=32})`: convex rotational bodies with closed ends. Useful for pots, bottles and rounded cylinders. Create open cavities as separately modelled inner walls/rims; this helper closes the end caps.
- `solid(name,rings,tones,{moving=true})`: equal-length closed 3D rings, joined into a capped solid. Rings must follow the same vertex order. Use convex solids; the centre-based winding correction is not suitable for arbitrary concave shells. Split a concave object into appropriate solids, merging IDs only when they represent one physically continuous part.

Every primitive returns its semantic part ID. Names must be unique. Group material chunks of a continuous shell under the same ID; do not create a new ID for every ring or color. Triangle normals and top/mid/dark/underside material assignments are generated from actual faces. The starter bakes simple directional shading into face colors; it does not emulate the original SVG ink/texture filter or a PBR renderer.

## Parameters and revisions

Expose the proportions that are actually useful for the new object. Derived dimensions should follow those values; do not advertise a parameter as a complete rig if other dependent coordinates are still fixed. The chair example exposes major dimensions for source editing, with joint positions in the scene code; substantial proportion changes require checking and updating those joints.

For a new concept, compare a plain-color silhouette at two diagonals before spending time on wood grain, seams or decals. Approximate useful feature width in final pixels as `feature_world_width / orthographicSize * native_size`. Roundness and small gaps often need more than a single pixel to read. Increasing native size is preferable to erasing a real silhouette feature.

`compile()` creates automatically framed orthographic cameras with a stable basis at 90°. It checks the full horizontal turning radius, so broad objects stay framed. `build.mjs` validates part IDs, geometry values, palette limits and camera matrices and writes hashes. Large external models should be simplified before importing; this starter is intended for compact stylized assets.

`Scene` defaults to `groundShadow:true`. It compiles the receiving plane at `bounds.min[2]`; the shared runtime projects model triangles down world -Z onto that plane. Pass `groundShadow:false` for floating/no-ground assets. Shadow tint and opacity are stored in `settings.groundShadow`, separately from the object palette.
