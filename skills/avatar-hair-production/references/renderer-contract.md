# Portable hair renderer contract

The renderer is bundled in this Skill. It does not load dated task directories or another installed Skill. The six vendored files under `assets/renderer/` implement Blender geometry export, the original 8×8 GPU sampling shader, its two-panel preview, and the continuous-camera/front–back wrappers. Python needs Pillow; model export needs Blender; syntax validation needs Node; browser capture needs Playwright and Chromium. Supply executable paths through CLI arguments when they are not on PATH.

```sh
python scripts/build_renderer.py --project PROJECT --out RUN --blender BLENDER
python scripts/prepare_exporter.py --run RUN --out EXPORTER --style STYLE.json
python scripts/capture_atlas.py --exporter EXPORTER --out gpu.json --timeout 180
```

All output directories must be fresh. `capture_atlas.py` requires a fresh output file unless `--overwrite` is explicit. Existing projects and approved runs remain read only. `--browser CHROMIUM` can select an installed browser; otherwise capture uses Playwright Chromium. `--no-rotations` skips only the supplementary 12-view check, retaining all 136 required poses. Capture serves the exporter on a temporary `127.0.0.1` port and closes the browser/server afterward. There is no remote rendering dependency.

## Project and Blender source

`PROJECT/realtime.json` declares the source `.blend`, scene, actual camera names, semantic membership, palette and orbit. Names below are examples except for the three standard semantic labels.

```json
{
  "name": "Short layered hair",
  "model": "avatar.blend",
  "scene": "Avatar",
  "size": 64,
  "rotationSign": -1,
  "pivot": [0, 0, 0],
  "movingRoot": "ROTATING",
  "fixedRoots": [],
  "palette": ["#131A25", "#29354A", "#4E617B", "#A6B4C7"],
  "outline": "#131A25",
  "cameras": ["Pitch0", "Pitch30", "Pitch45", "Pitch60", "Pitch90"],
  "parts": {
    "head": ["ProxyHead", "ProxyEarLeft", "ProxyEarRight"],
    "hair_front": ["FrontHair"],
    "hair_back": ["BackHair"]
  },
  "hairPartNames": ["hair_front", "hair_back"],
  "frontHairPartNames": ["hair_front"],
  "backHairPartNames": ["hair_back"],
  "hairLighting": "fixed-normal",
  "orbit": {"targetZ": 26, "distance": 120, "near": 90, "far": 150, "scale": 64},
  "references": []
}
```

`scene` is optional; without it the saved active scene is exported. Every visible mesh in the chosen scene needs exactly one part assignment and a declared moving/fixed root. Objects below `movingRoot` rotate together. The five cameras must be real orthographic Blender cameras in 0°, 30°, 45°, 60°, 90° order; the wrapper compares their matrices to the declared orbit. Camera/object names and project paths are configuration, never date-specific constants. The three part labels and their dictionary order are the Avatar package contract: head=1, front hair=2, rear hair=3. They are not inferred from object names or positions.

Use real, closed front/back geometry where a Y=0 split is required, with four directly openable scenes/projects produced upstream. This renderer does not fabricate a closed section or repair geometry. Keep the proxy head unchanged and fit hair against actual head000/face000 composites downstream.

Visible materials must use an Emission node whose Color is either a constant or directly connected to an Image Texture. Bake/convert PBR and procedural graphs upstream. The exported texture is the image's **packed bytes**; after editing an external image, reload and repack it into Blender before saving/freezing the source. Color changes only to an external PNG do not update an already packed texture.

`hairLighting: "fixed-normal"` affects only untextured chunks in the declared hair parts. It shades the sRGB base color by `0.62 + 0.65 * max(0, dot(rotatedNormal, normalize([-0.45,-0.65,0.73])))`, clamps to [0,1], then uses the original palette quantization. The key is fixed in world space and the surface normal rotates with the model. Head chunks and textured chunks are unchanged. `"none"` is the default when omitted, preserving baked texture shading and existing projects. New plain/white generated models should opt into fixed-normal after assigning the intended middle hair color. A palette with multiple meaningful light/mid/shadow colors is needed to retain visible shading.

The original textured pipeline consumes source baked shading. Existing approved back-light compensation remains inside its runtime and is preserved by exporter preparation; it is not replaced by a guessed generic profile. A flat textured source should be fixed/baked upstream or receive an explicitly reviewed lighting profile.

## Run files and GPU schema

`build_renderer.py` creates `asset.blend`, `realtime.json`, `model.json`, `runtime.js`, `preview.html`, and `build.json`, plus declared references. The preview retains synchronized raw 3D and pixel panels, orbit controls and front/back toggles. Source SHA256 is the byte hash of the saved Blender file. Builds use Blender `--python-exit-code 1`, so script failures cannot silently produce approved output.

`model.json` contains:

- `version`, `sourceSHA256`.
- `cameras[]`: name, column-major `viewProjection[16]`, column-major `viewNormal[9]`, `orthographicSize`, `depthRange`.
- `materials[]`: name, sRGB `color[3]`, and `texture` index or -1.
- `textures[]`: name, width, height, flat RGBA bytes. Input images are flipped vertically exactly once during preparation for WebGL upload.
- `parts[]`: object name, `part`, `structure`, moving flag, source vertex count and world matrix.
- `chunks[]`: object name, `part`, `structure`, moving flag, material index, casterId and flat triangle-list `vertices`.

Each triangle-list vertex has eight numbers: world position XYZ, world inverse-transposed triangle normal XYZ, UV. Coordinates are rounded to six decimals. `part` is the original coarse family value **1**, not the semantic ID. `structure` is the semantic ID. Low-resolution part-buffer PNGs store the semantic byte in **G**: 0 background, 1 proxy head, 2 front hair, 3 rear hair. Do not decode its R channel as head/front/rear.

The shader uses 8×8 supersampling, at least 32 covered samples per output pixel, and the dominant visible semantic surface. Palette quantization and the existing silhouette outline are retained. Structural outlines are off for atlas capture. No chair-specific edge cleanup, isolated-pixel filter, or silhouette simplification is introduced into the renderer.

## Approved run → exporter

`STYLE.json` requires `id` (`hair_NNN`), `kind` (portable identifier), `name`, and `sourceSHA256` (64 lowercase hex). The input alias `sourceSHA` is accepted and normalized. Source, build report and optional run `asset.blend` hashes must match. The approved runtime hash must match its build report. Preparation copies the model into a fresh directory, keeps the preview shell, and adds `window.exportAvatarAtlas(options)` inside the existing runtime. It changes only the known geometry-transform kernel and export hooks; existing material, texture, palette and lighting code are preserved. Unsupported/duplicate kernels fail instead of receiving a guessed patch.

The generated `prepare.json` records the frozen source hash, approved/prepared runtime hashes, model JSON hash, profile and transform handling. Capture rechecks these hashes before opening the browser.

### Whole-hair translation and speaking stretch

Freshly exported, genuinely positioned Blender geometry uses `geometrySpace: "baked"` (also the default for clean runs). It must not retain a pending `wholeHairDrop` uniform or `renderTransform` record. A runtime with either pending marker requires an explicit geometry-space declaration. Baked geometry plus a cached drop is rejected to prevent double translation.

An intentionally cached original triangle stream instead declares `geometrySpace: "cached"` and an authoritative `renderTransform` in the model or style:

```json
{
  "geometrySpace": "cached",
  "renderTransform": {
    "applyToStructures": [2, 3],
    "translation": [0, 0, -0.5],
    "space": "world",
    "baselineGeometrySHA256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

Only a pure world-space Z translation of both hair structures is supported. The parent head is unchanged. The exporter applies this declared pending translation exactly once, **before** speaking `verticalScale`. Known pre-existing drop/scale kernels are normalized without adding another transform. Unknown transforms and ambiguous baked/cached state fail with a useful error. Do not copy a cached runtime onto already translated Blender geometry.

## The standard 136-pose profile

All tiles are 64×64; calibrated orthographic scale=64, targetZ=26, constant screen offsetY=6, distance=120, near=90, far=150. Stretch is about Z=16. The preview's original camera is restored after capture; export calibration does not permanently shift the initial two-panel preview.

| Track | Layout | Yaw | Pitches | Vertical scale |
|---|---|---|---|---|
| front | 9 cols × 7 rows | `(4-col)*7` | row `[-22,-16.5,-11,-5.5,0,7,10]` | 1 |
| back | 9 cols × 7 rows | `180-(4-col)*7` | negative of front row pitch | 1 |
| speak_front | 5 cols × 1 row | 339 | `[-5.5,-22,-14,-5.5,-22]` | `[1,1.2,1.1,1,1.2]` |
| speak_back | 5 cols × 1 row | 194 | `[5.5,22,14,22,14]` | `[1,1.2,1.1,1.2,1.1]` |

Every pose renders two actual depth-tested passes: full proxy+hair, then hair only. The JSON has `sourceSHA256`, `style`, `profile`, `frames[136]`, supplementary `rotationFrames[12]` and `wrapMatches`. Each required frame contains `track,row,col,yaw,pitch,verticalScale` plus five 64×64 RGBA data URLs: `beauty`, `parts`, `proxyParts`, `hairOnlyBeauty`, `hairOnlyParts`. `proxyParts` is an exact alias of the untouched full-depth `parts`, not a different rendered proxy. Hair-only part IDs cannot contain 1. Capture validates the complete unique pose set, numerical profile, PNG dimensions/mode and semantic G bytes. The optional 12 rotations cover yaw 0 through 330 by 30° and compare 0 to 360 for exact wrap.

This payload is directly accepted by `scripts/package_atlas.py`. Packaging needs the actual target application's head000/face000 sprite assets. Full-depth semantic extraction controls normal occlusion. Hair-only recovery is permitted only where the proxy lies outside the actual head+face alpha and no hair pixel is already present; never overlay the whole hair-only image across the face. The package stage owns any separately requested, reviewed layer-promotion rule.

The source/capture contract does not itself guarantee a hairstyle is approved. Inspect actual-sprite composites for neutral, both sides, upward/downward views, back and all speaking frames; check eyes, ear/cheek edges, seams, clipping, crown proportion and color against the frozen source before installing.
