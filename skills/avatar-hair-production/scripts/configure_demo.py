#!/usr/bin/env python3
"""Write a separate Vite adapter: include gallery build entry and avoid URL MIME collisions.

Does not edit the existing Vite config. Use the generated config with Vite
--config for dev/build. The original build/static-copy plugin is retained.
"""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--demo-root',type=Path,required=True);p.add_argument('--gallery',default='hair-production-gallery.html');p.add_argument('--base-config');p.add_argument('--out',default='hair-production.vite.config.mjs');a=p.parse_args();root=a.demo_root.resolve()
base=root/a.base_config if a.base_config else next((root/n for n in ['vite.config.ts','vite.config.mts','vite.config.mjs','vite.config.js'] if (root/n).is_file()),None)
if base is None or not base.is_file():raise FileNotFoundError('Supply the existing project Vite configuration')
base=base.resolve();gallery=(root/a.gallery).resolve();out=(root/a.out).resolve()
if not all(x.is_relative_to(root) for x in [base,gallery,out]) or out==base or out.parent!=root:raise ValueError('Adapter must be a new root-level config; inputs must stay inside demo-root')
if not gallery.is_file():raise FileNotFoundError(gallery)
code='''// Generated Avatar hair preview adapter; original project config is unchanged.
import projectConfig from __BASE__
async function plugins(items) {
    const result = []
    for (const item of Array.isArray(items) ? items : [items]) {
        const value = await item
        if (Array.isArray(value)) result.push(...await plugins(value))
        else if (value) result.push(value)
    }
    return result
}
export default async (environment) => {
    const config = await (typeof projectConfig === 'function' ? projectConfig(environment) : projectConfig)
    const original = config.build?.rollupOptions?.input
    const entries = typeof original === 'string' ? { main: original }
        : Array.isArray(original) ? Object.fromEntries(original.map((value, index) => ['entry' + index, value]))
        : { ...(original ?? { main: 'index.html' }) }
    entries.hairProductionGallery = __GALLERY__
    return {
        ...config,
        // Root Assets already has native dev serving. The static-copy serve
        // middleware otherwise returns JSON for Vite's ?import&url modules.
        plugins: (await plugins(config.plugins ?? [])).filter(plugin => plugin.name !== 'vite-plugin-static-copy:serve'),
        build: { ...config.build, rollupOptions: { ...config.build?.rollupOptions, input: entries } },
    }
}
'''.replace('__BASE__',json.dumps('./'+base.relative_to(root).as_posix())).replace('__GALLERY__',json.dumps(gallery.relative_to(root).as_posix()))
if out.exists() and out.read_text()!=code:raise FileExistsError('Choose a fresh adapter filename; existing configuration is preserved')
out.write_text(code);print(f'Created {out.name}; run pnpm exec vite --config {out.name}, or pnpm exec vite build --config {out.name}')
