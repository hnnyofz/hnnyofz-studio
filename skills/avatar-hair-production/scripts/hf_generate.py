#!/usr/bin/env python3
"""Inspect official Hunyuan3D-2mv; generate one anonymous shape job only on request.

Python 3.10+. Inspection uses only standard-library HTTP GETs. Generation also
needs gradio_client. No automatic submission retries, login, or paid fallback.
"""
from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

SPACE = 'tencent/Hunyuan3D-2mv'
PAGE = 'https://huggingface.co/spaces/' + SPACE
HOST = 'https://tencent-hunyuan3d-2mv.hf.space'
ENDPOINT = '/shape_generation'
PARAMETERS = ['caption', 'image', 'mv_image_front', 'mv_image_back',
              'mv_image_left', 'mv_image_right', 'steps', 'guidance_scale',
              'seed', 'octree_resolution', 'check_box_rembg', 'num_chunks', 'randomize_seed']


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    if private:
        temporary.touch(mode=0o600, exist_ok=True)
        temporary.chmod(0o600)
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def state(out, status, **fields):
    path = out / 'state.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    data.update(status=status, updated_at=now(), **fields)
    save(path, data)
    return data


def summary(data):
    # Never print raw responses, download URLs, client objects, or input bytes.
    print(json.dumps({key: data[key] for key in
                      ('status', 'reason', 'out', 'glb', 'sha256', 'bytes') if key in data}, ensure_ascii=False))


def classify(error):
    text = str(error).lower()
    if 'quota' in text or 'too many requests' in text or '429' in text:
        return 'quota_blocked'
    if any(term in text for term in ('unauthorized', 'forbidden', 'authenticate', 'sign in', '401', '403')):
        return 'login_required'
    if isinstance(error, TimeoutError) or 'timed out' in text or 'timeout' in text:
        return 'observation_timeout'
    return 'request_failed'


def get_json(url, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Inspection deadline reached')
    with urlopen(url, timeout=min(30, remaining)) as response:
        return json.load(response)


def inspect_service(out, deadline):
    public = get_json('https://huggingface.co/api/spaces/' + SPACE, deadline)
    space = {key: public.get(key) for key in ('id', 'sdk', 'private', 'gated', 'disabled')}
    space['runtime_stage'] = public.get('runtime', {}).get('stage')
    save(out / 'space.json', space)
    config = get_json(HOST + '/config', deadline)
    info = get_json(HOST + '/info', deadline)
    endpoint = info.get('named_endpoints', {}).get(ENDPOINT, {})
    schema = dict(endpoint=ENDPOINT, gradio_version=config.get('version'),
                  parameters=[{key: parameter.get(key) for key in
                               ('parameter_name', 'parameter_default', 'python_type', 'label')}
                              for parameter in endpoint.get('parameters', [])],
                  returns=[{key: item.get(key) for key in ('python_type', 'label')}
                           for item in endpoint.get('returns', [])])
    save(out / 'schema.json', schema)
    names = [parameter['parameter_name'] for parameter in schema['parameters']]
    errors = []
    if names != PARAMETERS:
        errors.append('Parameter names/order differ from the verified 13-field shape endpoint')
    types = [p.get('python_type', {}).get('type') for p in schema['parameters']]
    if len(types) == 13:
        if types[:6] != ['str', 'filepath', 'filepath', 'filepath', 'filepath', 'filepath']:
            errors.append('Text/image parameter types changed')
        if any(types[i] not in ('int', 'float') for i in (6, 7, 8, 9, 11)):
            errors.append('Numeric parameter types changed')
        if types[10] != 'bool' or types[12] != 'bool':
            errors.append('Boolean parameter types changed')
    if not schema['returns'] or schema['returns'][0].get('python_type', {}).get('type') != 'filepath':
        errors.append('First result is no longer a downloadable model file')
    status = 'inspected'
    if space.get('private') or space.get('gated'):
        status = 'login_required'
    elif space.get('disabled') or space.get('runtime_stage') != 'RUNNING':
        status = 'space_unavailable'
    elif errors:
        status = 'schema_changed'
    report = dict(status=status, inspected_at=now(), space_url=PAGE, endpoint=ENDPOINT,
                  schema_matches=not errors, schema_errors=errors,
                  observation='Public metadata only; no GPU call made and no quota availability guaranteed')
    save(out / 'inspection.json', report)
    return report


def validate_glb(path):
    with path.open('rb') as source:
        header = source.read(20)
        if len(header) != 20:
            raise ValueError('Truncated GLB header')
        magic, version, length, json_length, json_kind = struct.unpack('<4sIIII', header)
        if magic != b'glTF' or version != 2 or length != path.stat().st_size or json_kind != 0x4E4F534A:
            raise ValueError('Invalid glTF 2 binary container')
        document = json.loads(source.read(json_length))
    primitives = [primitive for mesh in document.get('meshes', []) for primitive in mesh.get('primitives', [])]
    vertices = sum(document['accessors'][p['attributes']['POSITION']]['count'] for p in primitives)
    if not primitives or vertices <= 0:
        raise ValueError('Downloaded file has no actual mesh geometry')
    return dict(meshes=len(document['meshes']), primitives=len(primitives), vertices=vertices)


def worker(request_path):
    request = json.loads(request_path.read_text())
    out = Path(request['out'])
    attempted = False
    try:
        from gradio_client import Client, handle_file
        client = Client(SPACE, hf_token=False, download_files=False, verbose=False,
                        max_workers=1, httpx_kwargs={'timeout': min(30, request['timeout'])})
        kwargs = dict(request['params'])
        for key in ('mv_image_front', 'mv_image_back', 'mv_image_right'):
            kwargs[key] = handle_file(str(out / kwargs[key]))
        # Durable single-attempt guard, created before the one submission call.
        with (out / 'submission-once.json').open('x') as marker:
            json.dump(dict(attempted_at=now(), space_url=PAGE, endpoint=ENDPOINT), marker)
        attempted = True
        state(out, 'submission_attempted', submission_count=1,
              note='A network failure after this point may leave an unknown remote job; do not resubmit')
        job = client.submit(**kwargs, api_name=ENDPOINT)
        state(out, 'submitted', submission_count=1)
        result = job.result(timeout=request['timeout'])
        candidate = result[0]
        while isinstance(candidate, dict) and 'value' in candidate:
            candidate = candidate['value']
        url = candidate.get('url') if isinstance(candidate, dict) else candidate
        if not isinstance(url, str) or urlsplit(url).scheme != 'https':
            raise ValueError('No recognized HTTPS model result; no second generation will be submitted')
        # Retain the same result before downloading. A temporary asset URL is
        # private provenance, never a console message or a new submission.
        save(out / 'download-result.json', dict(model_url=url, received_at=now(), space_url=PAGE), private=True)
        state(out, 'generated', result_host=urlsplit(url).hostname,
              note='Remote result received; downloading the original GLB once')
        target = out / 'raw/model.glb'
        target.parent.mkdir(exist_ok=True)
        partial = target.with_suffix('.glb.part')
        digest = hashlib.sha256()
        with urlopen(url, timeout=min(30, request['timeout'])) as response, partial.open('wb') as destination:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                destination.write(chunk)
                digest.update(chunk)
        mesh = validate_glb(partial)
        partial.replace(target)
        try:
            target.chmod(0o444)
        except OSError:
            pass
        state(out, 'succeeded', glb='raw/model.glb', sha256=digest.hexdigest(),
              bytes=target.stat().st_size, mesh=mesh, original_model_unchanged=True)
        return 0
    except ImportError:
        state(out, 'dependency_missing', reason='Generation requires gradio_client; inspection does not')
    except Exception as error:
        status = classify(error)
        if attempted and status == 'request_failed':
            status = 'submission_or_result_unknown'
        hint = re.search(r'try again in\s+([0-9:]+)', str(error), re.IGNORECASE)
        state(out, status, reason=type(error).__name__, submission_attempted=attempted,
              retry_after_hint=hint.group(1) if hint else None,
              note='Stopped without retry, login, or fallback; preserve this directory for review')
    return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--inspect', action='store_true', help='Read public status/schema only (default; no GPU)')
    mode.add_argument('--generate', action='store_true', help='Explicitly submit at most one anonymous shape job')
    parser.add_argument('--front', type=Path)
    parser.add_argument('--right', type=Path)
    parser.add_argument('--back', type=Path)
    parser.add_argument('--out', type=Path, help='Persistent inspection/job directory; required')
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--timeout', type=float, default=300, help='Maximum total observation time in seconds (default: 300)')
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    if args.out is None or args.timeout <= 0:
        parser.error('--out and a positive --timeout are required')
    if args.generate and not all((args.front, args.right, args.back)):
        parser.error('--generate requires --front, --right, and --back')
    if not 0 <= args.seed <= 10000000:
        parser.error('--seed must be in 0..10000000')
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.generate and (out / 'submission-once.json').exists():
        summary(dict(status='existing_submission', out=str(out), reason='Do not resubmit this job, including after an observation timeout'))
        return 2
    if args.generate:
        lock = out / '.generation.lock'
        try:
            with lock.open('x') as handle:
                json.dump(dict(pid=os.getpid(), created_at=now()), handle)
        except FileExistsError:
            summary(dict(status='existing_observer', out=str(out), reason='Another invocation or unresolved interrupted observer owns this directory'))
            return 2
        atexit.register(lambda: lock.unlink(missing_ok=True))
    deadline = time.monotonic() + args.timeout
    try:
        report = inspect_service(out, deadline)
    except Exception as error:
        report = dict(status=classify(error), reason=type(error).__name__, inspected_at=now())
        save(out / 'inspection.json', report)
    if not args.generate or report['status'] != 'inspected':
        summary({**report, 'out': str(out)})
        return 0 if report['status'] == 'inspected' else 2
    inputs = {}
    for side in ('front', 'right', 'back'):
        source = getattr(args, side).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
            parser.error(f'--{side} must point to an existing PNG/JPEG/WebP file')
        target = out / 'inputs' / (side + source.suffix.lower())
        target.parent.mkdir(exist_ok=True)
        if source != target:
            shutil.copy2(source, target)
        inputs[side] = dict(file=str(target.relative_to(out)), bytes=target.stat().st_size,
                            sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    params = dict(caption=None, image=None, mv_image_front=inputs['front']['file'],
                  mv_image_back=inputs['back']['file'], mv_image_left=None,
                  mv_image_right=inputs['right']['file'], steps=5, guidance_scale=5.0,
                  seed=args.seed, octree_resolution=256, check_box_rembg=True,
                  num_chunks=8000, randomize_seed=False)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        summary(state(out, 'observation_timeout', reason='Inspection consumed the deadline; no job submitted'))
        return 2
    request = dict(out=str(out), timeout=remaining, params=params)
    save(out / 'generation-request.json', request)
    state(out, 'prepared', out=str(out), space_url=PAGE, endpoint=ENDPOINT,
          inputs=inputs, params=params, anonymous=True, created_at=now(), submission_count=0)
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', str(out / 'generation-request.json')],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        code = process.wait(timeout=remaining)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        latest = json.loads((out / 'state.json').read_text())
        if latest.get('status') == 'succeeded':
            code = 0
        else:
            state(out, 'observation_timeout', previous_status=latest.get('status'),
                  reason='Observation ended; a submitted remote job may still exist. Do not submit a replacement')
            code = 2
    latest = json.loads((out / 'state.json').read_text())
    summary(latest)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
