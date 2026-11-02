#!/usr/bin/env python3
"""Create a portable modelling workspace; no network or third-party packages."""
import argparse, shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('destination');a=p.parse_args()
dest=Path(a.destination).expanduser().resolve()
if dest.exists():p.error('Destination exists. Choose a fresh project folder.')
source=Path(__file__).resolve().parents[1]/'assets'/'starter'
shutil.copytree(source,dest)
print(f'Created {dest}\nEdit scene.mjs, then run: node "{dest}/build.mjs"')
