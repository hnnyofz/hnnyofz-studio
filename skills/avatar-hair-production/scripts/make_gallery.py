#!/usr/bin/env python3
"""Write a manual gallery into an existing Avatar Demo; uses its real renderer."""
import argparse, html, json, os, re
from pathlib import Path
from urllib.parse import quote

def make(args):
    demo = args.demo_root.resolve()
    for file in ('index.ts', 'demo/demoAssets.ts'):
        if not (demo / file).is_file(): raise FileNotFoundError(f'Expected existing Avatar Demo API: {file}')
    out = args.out or Path('hair-production-gallery.html')
    out = (demo / out).resolve() if not out.is_absolute() else out.resolve()
    if not out.is_relative_to(demo): raise ValueError('--out must be inside --demo-root so the Demo server can serve it')
    names = json.loads(args.names.read_text()) if args.names else {}
    if isinstance(names, list): names = {row['id']: row.get('name', row['id']) for row in names}
    entries = []
    for hid in dict.fromkeys(args.ids):
        if not re.fullmatch(r'hair_\d{3,}', hid): raise ValueError(f'Invalid ID: {hid}')
        path = demo / '.hair-production/styles' / f'{hid}.json'
        manifest = json.loads(path.read_text()) if path.exists() else {}
        name = names.get(hid, manifest.get('name', hid))
        entries.append(dict(id=hid, name=str(name)))
    template = (Path(__file__).resolve().parents[1] / 'assets/gallery.html').read_text()
    base = quote(Path(os.path.relpath(demo, out.parent)).as_posix(), safe='/.' ) + '/'
    data = json.dumps(entries, ensure_ascii=False).replace('<', '\\u003c')
    content = template.replace('__BASE__', html.escape(base, quote=True)).replace('__ENTRIES__', data)
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(content)
    print(f'Created {out}; open /{out.relative_to(demo).as_posix()} through the existing Demo dev server.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo-root', type=Path, required=True); parser.add_argument('--ids', nargs='+', required=True)
    parser.add_argument('--names', type=Path, help='JSON {id: appearanceName} or [{id,name}]')
    parser.add_argument('--out', type=Path, help='Filename within Demo; default hair-production-gallery.html')
    make(parser.parse_args())
