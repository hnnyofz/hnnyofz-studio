#!/usr/bin/env python3
"""Install one verified export into an Avatar Demo. Requires Pillow; no Git operations."""
import argparse, hashlib, json, os, re, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

TRACKS = ('front', 'back', 'speak_front', 'speak_back')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n'); os.replace(temp, path)
def catalog(path):
    data = json.loads(path.read_text()) if path.exists() else dict(directories=[], files=[])
    if not all(isinstance(data.get(k), list) and all(isinstance(s, str) for s in data[k]) for k in ('directories', 'files')): raise ValueError(f'Invalid folder catalog: {path}')
    return data

def install(args):
    export = args.export.resolve(); demo = args.demo_root.resolve(); hid = args.id
    if not re.fullmatch(r'hair_\d{3,}', hid): raise ValueError('Expected --id hair_NNN')
    manifest = json.loads((export / 'manifest.json').read_text())
    if manifest['id'] != hid or manifest.get('frameCount') != 136: raise ValueError('Export ID/136-frame contract mismatch')
    if manifest.get('iconFrame') != dict(track='front', row=4, col=6) or manifest.get('iconOffset') != [-1, -5]: raise ValueError('Icon must use row4 col6 and offset[-1,-5]')
    if not re.fullmatch(r'[0-9a-f]{64}', manifest.get('sourceSHA256', '')): raise ValueError('Missing frozen source SHA')
    files = manifest.get('files', {})
    if not files: raise ValueError('Manifest file hashes are required')
    sources = {}
    for track in TRACKS:
        for part in ('rear', 'front'):
            slot = ('slot010_HairRear.png' if part == 'rear' else 'slot168_HairFront.png') if track in ('front', 'speak_front') else ('slot177_HairRear.png' if part == 'rear' else 'slot178_HairFront.png')
            sources[f'{track}/{slot}'] = f'{track}-{part}.png'
    sources[f'icon_{hid}.png'] = f'icon_{hid}.png'
    # Verify every declared file and every installable asset before writing anything.
    for rel, digest in files.items():
        path = (export / rel).resolve()
        if not path.is_relative_to(export) or not path.is_file() or sha(path) != digest: raise ValueError(f'Export hash/path mismatch: {rel}')
        if path.suffix.lower() == '.png':
            with Image.open(path) as image:
                expected = (64, 64) if rel.startswith('frames/') or rel.startswith('icon_') else (576, 448) if rel.startswith(('front-', 'back-')) else (320, 64)
                if image.format != 'PNG' or image.mode != 'RGBA' or image.size != expected: raise ValueError(f'Invalid RGBA8 PNG dimensions: {rel}')
    if not set(sources.values()) <= set(files): raise ValueError('Missing layer/icon hashes')
    hair = demo / 'Assets/hair'; target = hair / hid
    top_path = hair / 'catalog.json'; root_path = demo / 'Assets/catalog.json'
    top = catalog(top_path); root = catalog(root_path)
    if (target.exists() or hid in top['directories']) and not args.replace: raise ValueError(f'{hid} already exists; pass --replace to replace only this variant')
    if args.dry_run:
        print(json.dumps(dict(state='verified', id=hid, files=9, target=str(target), replace=args.replace), indent=2)); return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    transaction = demo / '.hair-production/transactions' / stamp; transaction.mkdir(parents=True)
    style_path = demo / '.hair-production/styles' / f'{hid}.json'
    originals = {p: p.read_bytes() if p.exists() else None for p in (top_path, root_path, style_path)}
    for p, data in originals.items():
        if data is not None:
            backup = transaction / 'backup' / p.relative_to(demo); backup.parent.mkdir(parents=True, exist_ok=True); backup.write_bytes(data)
    existed = target.exists()
    if existed: shutil.copytree(target, transaction / 'backup/variant')
    hair.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hair-install-', dir=transaction) as temporary:
        staged = Path(temporary) / hid
        if existed: shutil.copytree(target, staged)
        else: staged.mkdir()
        for rel, source in sources.items():
            destination = staged / rel; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(export / source, destination)
        for track in TRACKS:
            p = staged / track / 'catalog.json'; row = catalog(p)
            row['files'] = sorted(set(row['files']) | {Path(rel).name for rel in sources if rel.startswith(track + '/')}); write(p, row)
        row = catalog(staged / 'catalog.json'); row['directories'] = sorted(set(row['directories']) | set(TRACKS)); row['files'] = sorted(set(row['files']) | {f'icon_{hid}.png'}); write(staged / 'catalog.json', row)
        try:
            if existed: shutil.rmtree(target)
            shutil.copytree(staged, target)
            top['directories'] = sorted(set(top['directories']) | {hid}); write(top_path, top)
            root['directories'] = sorted(set(root['directories']) | {'hair'}); write(root_path, root)
            write(style_path, manifest)
            installed = {rel: sha(target / rel) for rel in sources}
            write(transaction / 'transaction.json', dict(state='installed', id=hid, sourceSHA256=manifest['sourceSHA256'], exportDirectory=str(export), replaced=existed,
                                                        backup=str(transaction / 'backup'), installedFiles=installed, installedAt=stamp))
        except Exception:
            if target.exists(): shutil.rmtree(target)
            if existed: shutil.copytree(transaction / 'backup/variant', target)
            for p, data in originals.items():
                if data is None: p.unlink(missing_ok=True)
                else: p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
            write(transaction / 'transaction.json', dict(state='rolled-back', id=hid)); raise
    print(f'Installed {hid}; backup and transaction: {transaction}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True); parser.add_argument('--id', required=True)
    parser.add_argument('--demo-root', type=Path, required=True); parser.add_argument('--replace', action='store_true')
    parser.add_argument('--dry-run', action='store_true'); install(parser.parse_args())
