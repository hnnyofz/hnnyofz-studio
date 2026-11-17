#!/usr/bin/env python3
"""Package 136 dual-pass frames. Requires Pillow; all input paths are explicit."""
import argparse, base64, hashlib, io, json, re
from collections import Counter
from pathlib import Path
from PIL import Image

TRACKS = ('front', 'back', 'speak_front', 'speak_back')
SIZES = {t: (576, 448) if t in ('front', 'back') else (320, 64) for t in TRACKS}
FIELDS = ('beauty', 'parts', 'proxyParts', 'hairOnlyBeauty', 'hairOnlyParts')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def cell(image, row, col): return image.crop((col * 64, row * 64, (col + 1) * 64, (row + 1) * 64))
def rgba(value, base):
    data = io.BytesIO(base64.b64decode(value.split(',', 1)[1], validate=True)) if value.startswith('data:image/png;base64,') else base / value
    with Image.open(data) as image:
        if image.format != 'PNG': raise ValueError('Expected PNG input')
        result = image.convert('RGBA')
    if result.size != (64, 64): raise ValueError('GPU frames must be 64×64')
    return result

def reference(assets, category, track):
    folder = assets / category / f'{category}_000' / ('speak' if category == 'face' and track == 'speak_front' else track)
    paths = sorted(folder.glob('*.png'))
    if not paths:
        if category == 'face' and track in ('back', 'speak_back'): return Image.new('RGBA', SIZES[track])
        raise FileNotFoundError(f'Missing actual {category} sprite: {folder}')
    with Image.open(paths[0]) as image: result = image.convert('RGBA')
    if result.size != SIZES[track]: raise ValueError(f'Unexpected reference size: {paths[0]}')
    return result

def components(points):
    points = set(points)
    while points:
        seed = min(points, key=lambda p: (p[1], p[0])); points.remove(seed); group = [seed]; queue = [seed]
        while queue:
            x, y = queue.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    p = (x + dx, y + dy)
                    if p in points: points.remove(p); queue.append(p); group.append(p)
        yield group

def extract(frame, base, head, face, style, promote=False, cleanup=False):
    beauty, parts, only, ids = [rgba(frame[k], base) for k in ('beauty', 'parts', 'hairOnlyBeauty', 'hairOnlyParts')]
    proxy = rgba(frame['proxyParts'], base) if frame.get('proxyParts') else parts
    front = Image.new('RGBA', (64, 64)); rear = front.copy(); edits = []
    actual = Image.alpha_composite(head, face)
    for y in range(64):
        for x in range(64):
            p = (x, y); sid = parts.getpixel(p)[1]
            if sid == 2: front.putpixel(p, beauty.getpixel(p))
            elif sid == 3: rear.putpixel(p, beauty.getpixel(p))
            if proxy.getpixel(p)[1] == 1 and not actual.getpixel(p)[3] and not front.getpixel(p)[3] and not rear.getpixel(p)[3]:
                sample_id = ids.getpixel(p)[1]; color = only.getpixel(p)
                if sample_id in (2, 3) and color[3]:
                    target = front if sample_id == 2 else rear; target.putpixel(p, color)
                    edits.append(dict(reason='proxy-outside-actual-sprite', xy=list(p), layer='front' if sample_id == 2 else 'rear', rgba=list(color)))
    if promote and frame['track'] in ('front', 'speak_front'):
        protected = {tuple(c) for c in style['protectedEarColors']}
        candidates = [(x, y) for y in range(64) for x in range(64) if parts.getpixel((x, y))[1] == 3 and rear.getpixel((x, y))[3]
                      and head.getpixel((x, y))[3] and not face.getpixel((x, y))[3]
                      and head.getpixel((x, y))[:3] not in protected]
        for group in components(candidates):
            touches_front = any(0 <= x + dx < 64 and 0 <= y + dy < 64 and front.getpixel((x + dx, y + dy))[3]
                                for x, y in group for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
            if len(group) > style.get('maxPromotedPixelsPerComponent', 16) or not touches_front: continue
            for p in group:
                if front.getpixel(p)[3]: continue
                color = rear.getpixel(p); front.putpixel(p, color); rear.putpixel(p, (0, 0, 0, 0))
                edits.append(dict(reason='connected-depth-visible-rear-promotion', xy=list(p), layer='front', rgba=list(color)))
    if cleanup and frame['track'] in ('front', 'speak_front'):
        for group in components((x, y) for y in range(64) for x in range(64) if front.getpixel((x, y))[3]):
            if len(group) == 1 and actual.getpixel(group[0])[3]:
                p = group[0]; color = front.getpixel(p); front.putpixel(p, (0, 0, 0, 0))
                edits.append(dict(reason='opt-in-interior-singleton', xy=list(p), layer='front', removedRGBA=list(color)))
    return front, rear, edits

def package(args):
    style = json.loads(args.style.read_text()); data = json.loads(args.gpu.read_text())
    style.setdefault('kind', style['id']); style.setdefault('name', style['id'])
    if not re.fullmatch(r'hair_\d{3,}', style['id']): raise ValueError('Style id must be hair_NNN')
    if not style.get('name'): raise ValueError('Style name must describe the appearance')
    if not re.fullmatch(r'[0-9a-f]{64}', style['sourceSHA256']): raise ValueError('Frozen sourceSHA256 is required')
    if data.get('sourceSHA256') != style['sourceSHA256']: raise ValueError('GPU/source SHA mismatch')
    if args.promote_visible_rear:
        palette = style.get('protectedEarColors', [])
        if not palette or any(not isinstance(c, list) or len(c) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in c) for c in palette):
            raise ValueError('Promotion requires explicit protectedEarColors:[[R,G,B],...] from actual head sprites')
        if type(style.get('maxPromotedPixelsPerComponent', 16)) is not int or style.get('maxPromotedPixelsPerComponent', 16) < 1: raise ValueError('maxPromotedPixelsPerComponent must be a positive integer')
    expected = {(t, r, c) for t in TRACKS for r in range(7 if t in ('front', 'back') else 1) for c in range(9 if t in ('front', 'back') else 5)}
    frames = data['frames']; actual_keys = [(f['track'], f['row'], f['col']) for f in frames]
    if len(actual_keys) != 136 or set(actual_keys) != expected: raise ValueError('Expected exactly 63 front +63 back +5 speak_front +5 speak_back poses')
    for f in frames:
        if not all(f.get(k) for k in ('beauty', 'parts', 'hairOnlyBeauty', 'hairOnlyParts')): raise ValueError('Each pose needs both beauty/parts and hairOnlyBeauty/hairOnlyParts')
    heads = {t: reference(args.avatar_assets, 'head', t) for t in TRACKS}
    faces = {t: reference(args.avatar_assets, 'face', t) for t in TRACKS}
    gray_path = args.avatar_assets / 'hair/hair_004/icon_hair_004.png'
    with Image.open(gray_path) as im: gray = im.convert('RGBA')
    if gray.size != (64, 64): raise ValueError('Gray mannequin icon must be 64×64')
    out = args.out; out.mkdir(parents=True, exist_ok=True); (out / 'frames').mkdir(exist_ok=True)
    layers = {t: {p: Image.new('RGBA', SIZES[t]) for p in ('front', 'rear')} for t in TRACKS}
    composites = {t: Image.new('RGBA', SIZES[t]) for t in TRACKS}; records = []
    for f in frames:
        t, r, c = f['track'], f['row'], f['col']; head, face = cell(heads[t], r, c), cell(faces[t], r, c)
        front, rear, edits = extract(f, args.gpu.parent, head, face, style, args.promote_visible_rear, args.cleanup_singletons)
        for part, image in (('front', front), ('rear', rear)): layers[t][part].paste(image, (c * 64, r * 64))
        whole = Image.alpha_composite(rear, front); filename = f'frames/{t}-{r}-{c}.png'; whole.save(out / filename)
        comp = Image.new('RGBA', (64, 64))
        if t in ('front', 'speak_front'): comp.alpha_composite(rear)
        comp.alpha_composite(head); comp.alpha_composite(face)
        if t in ('back', 'speak_back'): comp.alpha_composite(rear)
        comp.alpha_composite(front); composites[t].paste(comp, (c * 64, r * 64))
        bbox = whole.getbbox(); contact = sum(bool(face.getpixel((x, y))[3] and front.getpixel((x, y))[3]) for y in range(64) for x in range(64))
        records.append({k: v for k, v in f.items() if k not in FIELDS} | dict(file=filename, sha256=sha(out / filename), bbox=bbox, facePixelsCovered=contact,
                       edgeTouch=bool(bbox and (0 in bbox[:2] or 64 in bbox[2:])), pixelCorrections=edits))
    for t in TRACKS:
        for p in ('front', 'rear'): layers[t][p].save(out / f'{t}-{p}.png')
        composites[t].save(out / f'{t}-composite.png')
    icon = Image.new('RGBA', (64, 64)); icon.paste(cell(layers['front']['rear'], 4, 6), (-1, -5)); icon.alpha_composite(gray)
    foreground = Image.new('RGBA', (64, 64)); foreground.paste(cell(layers['front']['front'], 4, 6), (-1, -5)); icon.alpha_composite(foreground); icon.save(out / f"icon_{style['id']}.png")
    generated = [r['file'] for r in records] + [f'{t}-{p}.png' for t in TRACKS for p in ('front', 'rear')] + [f'{t}-composite.png' for t in TRACKS] + [f"icon_{style['id']}.png"]
    manifest = style | dict(schemaVersion=1, frameCount=136, semanticGreenIDs=dict(head=1, front=2, rear=3), iconFrame=dict(track='front', row=4, col=6), iconOffset=[-1, -5],
                           grayHeadSHA256=sha(gray_path), packagerSHA256=sha(Path(__file__)), frames=records,
                           avatarReferenceFiles={str(p.relative_to(args.avatar_assets)): sha(p) for category in ('head', 'face') for p in sorted((args.avatar_assets / category / f'{category}_000').rglob('*.png'))},
                           correctionCounts=dict(Counter(e['reason'] for f in records for e in f['pixelCorrections'])),
                           eyeOverlapFrames=[f for f in records if f['facePixelsCovered']], edgeClippedFrames=[f for f in records if f['edgeTouch']],
                           files={name: sha(out / name) for name in sorted(generated)})
    write(out / 'manifest.json', manifest); print(f"Packaged {style['id']}: 136 poses, eight layers and gray-head icon at {out}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('gpu', 'style', 'avatar-assets', 'out'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--promote-visible-rear', action='store_true', help='Opt-in; requires style.protectedEarColors and only promotes small connected depth-visible components')
    parser.add_argument('--cleanup-singletons', action='store_true', help='Opt-in; remove only 8-connected isolated front pixels within actual sprite alpha')
    package(parser.parse_args())
