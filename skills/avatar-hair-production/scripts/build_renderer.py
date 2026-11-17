#!/usr/bin/env python3
"""Build the bundled Blender → side-by-side WebGL hair viewer."""
import argparse
import importlib.util
import json
import shutil
from pathlib import Path


def executable(value):
    resolved = shutil.which(value)
    if resolved: return resolved
    path = Path(value).expanduser()
    if path.is_file(): return str(path.resolve())
    raise FileNotFoundError(f'Executable not found: {value}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Project containing realtime.json and its .blend')
    parser.add_argument('--out', type=Path, required=True, help='Fresh run directory; never overwrites an approved run')
    parser.add_argument('--blender', default='blender', help='Blender executable or command on PATH')
    parser.add_argument('--node', default='node', help='Node executable for JS syntax validation')
    args = parser.parse_args()
    cfg = json.loads((args.project / 'realtime.json').read_text())
    if list(cfg['parts']) != ['head', 'hair_front', 'hair_back']:
        raise ValueError('Avatar semantics require ordered parts: head, hair_front, hair_back')
    if cfg.get('hairPartNames') != ['hair_front', 'hair_back'] or cfg.get('frontHairPartNames') != ['hair_front'] or cfg.get('backHairPartNames') != ['hair_back']:
        raise ValueError('Declare hair/front/back part-name lists explicitly in standard order')
    if len(cfg.get('cameras', [])) != 5:
        raise ValueError('Declare five actual orthographic cameras ordered at 0,30,45,60,90 degrees')
    if cfg.get('hairLighting', 'none') not in ('none', 'fixed-normal'):
        raise ValueError('hairLighting must be none or fixed-normal')
    root = Path(__file__).resolve().parents[1] / 'assets' / 'renderer' / 'scripts'
    import sys
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('hair_section_builder', root / 'build_section_viewers.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.build(args.project, args.out, executable(args.blender), executable(args.node))


if __name__ == '__main__': main()
