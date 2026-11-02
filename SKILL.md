---
name: chibi-pixel-studio
description: Create cute, rounded, compact 3D props and furniture with synchronized side-by-side raw model and real-time pixel shader previews. Use for Q版建模, chibi objects, toy-like proportions, or paired 3D/pixel previews. Focus on silhouette and art direction; mechanism cutaways and exact sprite reconstruction are separate workflows.
---

# Chibi Pixel Studio

Create a readable, characterful solid model and deliver one offline HTML with **raw 3D on the left and the same model through the pixel shader on the right**. The default task is shape design. Do not automatically add cutaways, exploded assemblies, mechanism research, labels, simulation or game interactions. Add those only when they serve the user's brief.

## Shape first

Borrow Colorfigures' useful discipline: break an object into real volumes, establish proportions numerically, connect supports, give every part a back and underside, and inspect it around the full circle. Put the effort into the exterior silhouette and visual weight.

- Write a short shape brief in the scene source: identifying features, dominant mass, supporting masses, desired mood and intentional exaggerations. If a reference exists, distinguish retained features from stylization.
- Establish the silhouette with a few simple volumes before surface decoration. For cute props, consider broad dominant forms, shorter supports, thick rims, generous radii and clean gaps. Choose proportions for the object; do not apply one numeric chibi ratio to everything.
- Preserve what makes the object recognizable. An opening, handle or gap can matter more than extra detail. Exaggerate small essential features until they survive the chosen native pixel resolution.
- Model roundness in geometry. Add bevelled rims, tapered sections and gentle lean; use fewer, larger details. Faces, eyes and mascots are optional art direction, never an automatic interpretation of “cute”.
- Tune from large to small: silhouette → proportions → contact/gaps → corners → colors → sparse texture. If the pixel result fails, inspect the raw model and fix the earliest cause.

## Start a portable project

The bundled starter uses Node.js and Python 3, with no package installation or network dependencies. The browser needs WebGL2. Read [references/modeling.md](references/modeling.md) for the scene API and [references/renderer.md](references/renderer.md) before changing shaders or the preview shell.

```sh
python3 /absolute/path/to/chibi-pixel-studio/scripts/create_project.py /absolute/path/to/new-project
node /absolute/path/to/new-project/build.mjs
```

The scaffold refuses to overwrite an existing folder. It copies `scene.mjs`, `geometry.mjs`, `runtime.js`, `viewer.html`, `finishes.mjs` and `build.mjs` so the project remains editable without the skill installed. Replace the example chair scene with the requested object. The chair is a working example, not a shape template for every prop.

Edit project files, not the installed starter, during normal artwork tasks. Rebuild with `node build.mjs`; the default output is `dist/preview.html`. For revision history use a fresh output directory: `node build.mjs scene.mjs runs/v002`. The HTML embeds geometry and shaders and works offline. Serve the project via localhost to inspect it in the app browser.

The default source is procedural JavaScript geometry. Do not promise a `.blend` or GLB unless one has actually been produced. Existing Blender geometry can be adapted to the documented model contract when appropriate; do not rasterize its preview to fake depth or semantic IDs.

## Two views, one scene

- Author the model facing +X. Yaw 0° is the front, 90°/270° are sides, and 180° is the back; elevation is independent.
- Use one scene, one shared yaw, camera and zoom. Both views must be rendered from the same geometry and camera transform in the same draw call sequence. Dragging either half turns both.
- Left: unpixelated model beauty. Right: actual GPU pixel output. Use nearest-neighbor, integer enlargement for final pixels. The source image stays at high resolution.
- Keep the current angle when changing camera, density, palette quantization or outline settings. Offer a single row of eight yaw buttons from 0° through 315° in 45° steps; highlight only the exact selected preset. Keep free dragging, and omit angle sliders, numeric entry, playback, reverse and speed controls from the default UI. On narrow screens let the button row scroll horizontally. The starter also offers elevation presets, density, zoom, current PNG and rotation ZIP.
- Default UI is for judging shape and style. Put buffer diagnostics under development tools, keep semantic IDs internal, and omit irrelevant fixed-part or mechanism controls.
- Hot rebuilding the HTML requires a page refresh; do not claim live geometry editing unless implemented. Shared camera/rotation updates are real time.

## Page style and finishes

Use the Colorfigures-inspired shell: warm paper (#f2efe7), restrained paper grain, compact monospace labels, fine dark rules, outlined capsule buttons and circular color swatches with a selected ring. Keep the object central, with two synchronized views and a narrow divider. Show pixel density in the first control row immediately below the preview, followed by material swatches and the 45° view row. Keep elevation, zoom and PNG export directly visible; fold outline settings and sequence tools into a disclosure. Avoid large dashboard cards and repeated instructional copy. Presentation background is paper; export alpha remains transparent.

Provide multiple coordinated color/material finishes for each model. In furniture scenes, import `furnitureFinishes` from `finishes.mjs`, assign `scene.finishes=furnitureFinishes(primaryTones, optionalAccentTones)`, and set `scene.finishName` and `scene.finishSwatches` for the original. The helper adds walnut, cream, mint, blue, terracotta and charcoal variants. For other objects author appropriate maps rather than blindly forcing wood names. See [references/renderer.md](references/renderer.md) for the data contract.

These are flat-shaded material-color presets; do not claim physical roughness, metallic response or wood-grain textures. A preset updates raw mesh material colors, the pixel palette and ink together, preserving geometry, yaw, elevation, zoom and shadows. Shared source colors are remapped everywhere; use distinct source colors if props or interiors must remain independent. Keep original and alternative names accessible via swatch labels and a visible selected name. Export actual current finish pixels; include the preset in PNG filenames and ZIP metadata. Clear stale export links after switching finishes.

## Shader contract

The renderer reuses the pixel demo's GPU pipeline: high-resolution depth-tested geometry → 8×8 visible-part sampling → limited palette → silhouette/contact ink → integer display. Color, depth and normal come from the same dominant visible component. Silhouette ink is a one-native-pixel outer stroke in transparent four-neighbor cells; never replace occupied material pixels with silhouette ink. Read original buffers so ink cannot expand recursively. A shared contact is assigned one front-part owner and drawn on the rear surface; skip narrow recipients unless two same-part cells remain inward, and let existing ink consume the boundary budget. Hidden boundaries stay hidden. Selective lighter ink on bright upward faces is configurable for the asset palette.

Assign one semantic ID to each physically continuous part, regardless of color or the number of material chunks. Rounded corners of a single solid share its ID. Separate contacting pieces get separate IDs. Keep IDs within 1–63 and the palette within 1–32 colors. The starter includes a ground shadow from overhead sunlight (world direction 0,0,-1). Project the actual rotated geometry vertically onto the ground at the lowest model Z; never use a fixed ellipse or inherited chair footprint. Both views and transparent PNG exports include the same shadow. Keep it semitransparent and outside palette, silhouette and contact-ink detection. Set `groundShadow:false` in the Scene constructor when an asset needs no ground shadow.

Preserve this actual geometry pipeline. CSS pixelation, screenshots of SVG, pre-rendered angle frames and separate hand-drawn models do not satisfy the paired shader preview. Sources and adaptations are recorded in [references/provenance.json](references/provenance.json).

## Verify and deliver

Inspect the built preview, not only the build report. Use the current browser automation tool for interaction and save visual evidence in the project.

- Inspect front/back/both sides, diagonal angles and one top view; try a non-grid yaw such as 57.3°. Check rounded silhouette, support contacts, open gaps and underside coverage.
- Click all eight angle presets and drag each half; change elevation and zoom. Check that free dragging clears the preset highlight when between preset angles. Both halves must track the same state. Check narrow-screen layout, errors and WebGL availability.
- With contact ink disabled, verify every occupied pre-ink pixel is unchanged and new opaque pixels are exactly the four-neighbor outer border; semitransparent ground-shadow pixels are excluded from that assertion. Inspect thin side-on parts with contact ink enabled.
- Judge pixels at native scale and integer enlargement. Check thin features, touching same-color parts, double ink bands, color leaks and 0°/360° wrap.
- Check every material swatch, including a pale and dark finish, and verify that the raw and pixel views match. Changing finish must keep camera and zoom.
- Verify current PNG export against the visible output. If delivering a sequence, inspect its actual files and manifest. Build success alone is not visual acceptance.
- After shader changes, use a same-color overlapping-parts fixture at oblique and top cameras, plus the actual prop. After geometry changes, rerun affected views; avoid unrelated test expansion.

Deliver the preview link, a screenshot and editable scene source. Briefly name the defining shape choices and any observed limitation. Preserve original references and earlier accepted candidates. The target is an attractive Q版 object with a useful pixel preview, not a technical anatomy lesson.
