#!/usr/bin/env python3
"""Capture 136 dual-pass PNG poses with a local WebGL2 browser (Playwright)."""
import argparse
import asyncio
import base64
import functools
import hashlib
import io
import json
import math
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIELDS = ('beauty', 'parts', 'proxyParts', 'hairOnlyBeauty', 'hairOnlyParts')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_poses(profile):
    expected = {}
    for track in ('front', 'back'):
        for row, pitch in enumerate(profile['rowPitches']):
            for col in range(9):
                expected[(track, row, col)] = ((180 - (4-col)*7) if track == 'back' else (4-col)*7,
                                              -pitch if track == 'back' else pitch, 1)
    for track, spec in (('speak_front', profile['speakFront']), ('speak_back', profile['speakBack'])):
        for col, (pitch, scale) in enumerate(zip(spec['pitches'], spec['scales'])):
            expected[(track, 0, col)] = (spec['yaw'], pitch, scale)
    return expected


def validate(data, evidence):
    from PIL import Image
    if data.get('sourceSHA256') != evidence['sourceSHA256']: raise ValueError('GPU/source SHA mismatch')
    if data.get('profile') != evidence['profile']: raise ValueError('GPU profile mismatch')
    expected = expected_poses(evidence['profile']); seen = set()
    if len(data.get('frames', [])) != 136 or len(expected) != 136: raise ValueError('Expected exactly 136 poses')
    for frame in data['frames']:
        key = (frame.get('track'), frame.get('row'), frame.get('col'))
        if key not in expected or key in seen: raise ValueError(f'Duplicate/unexpected pose: {key}')
        seen.add(key)
        for name, target in zip(('yaw', 'pitch', 'verticalScale'), expected[key]):
            value = frame.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(value): raise ValueError(f'Invalid {name}: {key}')
            error = abs((value-target+180) % 360-180) if name == 'yaw' else abs(value-target)
            if error > 1e-7: raise ValueError(f'Wrong {name}: {key}')
        for name in FIELDS:
            value = frame.get(name, '')
            if not isinstance(value, str) or not value.startswith('data:image/png;base64,'): raise ValueError(f'Missing inline PNG {name}: {key}')
            binary = base64.b64decode(value.split(',', 1)[1], validate=True)
            with Image.open(io.BytesIO(binary)) as im:
                if im.format != 'PNG' or im.mode != 'RGBA' or im.size != (64, 64): raise ValueError(f'Expected 64×64 RGBA PNG: {name} {key}')
                im.load()
                if name in ('parts', 'proxyParts', 'hairOnlyParts'):
                    ids = {p[1] for p in im.getdata()}
                    allowed = {0, 2, 3} if name == 'hairOnlyParts' else {0, 1, 2, 3}
                    if not ids <= allowed: raise ValueError(f'Unknown semantic G byte: {key} {name} {ids}')
        if frame['parts'] != frame['proxyParts']: raise ValueError(f'proxyParts must be the untouched full depth pass: {key}')
    if seen != set(expected): raise ValueError('Incomplete pose set')
    if data.get('rotationFrames'):
        if [r.get('yaw') for r in data['rotationFrames']] != list(range(0, 360, 30)): raise ValueError('Invalid rotation checks')
        if data.get('wrapMatches') is not True: raise ValueError('Yaw 0/360 wrap mismatch')


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass


async def capture(args, url, evidence):
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError('Install playwright and its Chromium browser: pip install playwright; playwright install chromium') from exc
    async with async_playwright() as playwright:
        options = dict(headless=True, args=['--use-angle=swiftshader', '--enable-webgl', '--enable-unsafe-swiftshader'])
        if args.browser: options['executable_path'] = str(args.browser.expanduser().resolve())
        browser = await playwright.chromium.launch(**options)
        try:
            page = await browser.new_page(viewport=dict(width=1100, height=900))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(url, wait_until='load', timeout=int(args.timeout*1000))
            await page.wait_for_function("(window.exportAvatarAtlas && !document.getElementById('controls').disabled) || !document.getElementById('error').hidden", timeout=int(args.timeout*1000))
            startup_error = await page.locator('#error').inner_text()
            if startup_error: raise RuntimeError(startup_error)
            result = await page.evaluate('(options) => window.exportAvatarAtlas(options)', dict(rotations=not args.no_rotations))
            if errors: raise RuntimeError('Browser errors: ' + '; '.join(errors))
            validate(result, evidence)
            result['capture'] = dict(approvedRuntimeSHA256=evidence['approvedRuntimeSHA256'],
                                     preparedRuntimeSHA256=evidence['preparedRuntimeSHA256'],
                                     modelSHA256=evidence['modelSHA256'], browserVersion=browser.version,
                                     transport='loopback-http/playwright-evaluate', validation='136-pose-dual-pass-rgba-semantic-G')
            return result
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exporter', type=Path, required=True, help='Fresh directory from prepare_exporter.py')
    parser.add_argument('--out', type=Path, required=True, help='Destination GPU JSON for package_atlas.py')
    parser.add_argument('--browser', type=Path, help='Optional Chromium/Chrome executable; defaults to Playwright Chromium')
    parser.add_argument('--timeout', type=float, default=180, help='End-to-end seconds, including browser launch (1–3600)')
    parser.add_argument('--no-rotations', action='store_true', help='Skip supplementary 12-view and 0/360 checks; still captures all 136 poses')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly allow replacing the destination JSON')
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600: parser.error('--timeout must be between 1 and 3600 seconds')
    args.exporter = args.exporter.resolve(); args.out = args.out.resolve()
    if args.out.exists() and not args.overwrite: raise FileExistsError('Destination exists; use a fresh path or --overwrite')
    evidence = json.loads((args.exporter / 'prepare.json').read_text())
    for name, key in (('runtime.js', 'preparedRuntimeSHA256'), ('model.json', 'modelSHA256')):
        if sha(args.exporter / name) != evidence[key]: raise ValueError(f'Prepared {name} changed after validation')
    handler = functools.partial(QuietHandler, directory=str(args.exporter))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        async def bounded():
            return await asyncio.wait_for(capture(args, f'http://127.0.0.1:{server.server_port}/preview.html', evidence), timeout=args.timeout)
        result = asyncio.run(bounded())
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_name(args.out.name + f'.tmp-{os.getpid()}')
    try:
        temp.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
        os.replace(temp, args.out)
    finally:
        if temp.exists(): temp.unlink()
    print(f'{args.out}: 136 validated dual-pass frames')


if __name__ == '__main__': main()
