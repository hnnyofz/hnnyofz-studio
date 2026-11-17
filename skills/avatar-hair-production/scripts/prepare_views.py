#!/usr/bin/env python3
"""Crop actual three-view pixels to equal canvases; no redraw, mirroring or resizing."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sheet',type=Path,required=True);p.add_argument('--boxes',type=Path,required=True,help='JSON front/right/back [x0,y0,x1,y1] crop rectangles');p.add_argument('--out',type=Path,required=True);p.add_argument('--canvas',type=int);a=p.parse_args();sheet=Image.open(a.sheet).convert('RGBA');boxes=json.loads(a.boxes.read_text());assert set(boxes)=={'front','right','back'}
 crops={}
 for name,box in boxes.items():
  assert len(box)==4 and all(isinstance(v,int) for v in box);x0,y0,x1,y1=box;assert 0<=x0<x1<=sheet.width and 0<=y0<y1<=sheet.height,(name,box);crops[name]=sheet.crop(box)
 size=a.canvas or max(max(im.size) for im in crops.values())+32;assert all(max(im.size)<=size for im in crops.values()),'Canvas may not clip source pixels'
 a.out.mkdir(parents=True,exist_ok=True);records={}
 for name,crop in crops.items():
  dest=a.out/f'{name}.png';assert not dest.exists(),f'Choose a fresh output directory: {dest}';canvas=Image.new('RGBA',(size,size),'white');canvas.alpha_composite(crop,((size-crop.width)//2,(size-crop.height)//2));canvas.convert('RGB').save(dest);records[name]={'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'crop':boxes[name]}
 (a.out/'input-manifest.json').write_text(json.dumps(dict(source=a.sheet.name,sourceSHA256=hashlib.sha256(a.sheet.read_bytes()).hexdigest(),canvas=[size,size],operation='Exact rectangular source crop and common white padding; no resize/mirror/generation',views=records),ensure_ascii=False,indent=2)+'\n');print(a.out)
if __name__=='__main__':main()
