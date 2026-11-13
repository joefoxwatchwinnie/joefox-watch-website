#!/usr/bin/env python3
"""Round7: 拼合图拆色——上传 ~89 张单表图 + trust 新图，同步 14 款 color_options/gallery/image。"""
import json, os, requests

B = 'https://www.joefoxwatch.com'
s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))
IDS = ('dm-24007', 'dm-2420', 'dm-3028', 'dm-1942', 'dm-1943B', 'dm-1956', 'dm-2106B',
       'dm-2106C', 'dm-2106E', 'dm-2106F', 'dm-2106', 'dm-2106H', 'dm-1960', 'dm-2311')

# 1) 上传单表图 + trust 图
uploads = ['public/uploads/factory/trust-new.jpg']
for p in db['products']:
    if p['id'] in IDS:
        for o in p['color_options']:
            f = 'public' + o['image']
            if os.path.exists(f):
                uploads.append(f)
up_ok, up_fail = 0, []
for f in uploads:
    rel = f.replace('public/uploads/', '', 1)
    with open(f, 'rb') as fh:
        r = s.post(B + '/admin/upload-image',
                   data={'relpath': rel},
                   files={'file': (os.path.basename(f), fh, 'image/jpeg')}, timeout=60)
    if r.status_code == 200 and r.json().get('ok'):
        up_ok += 1
    else:
        up_fail.append((rel, r.status_code, r.text[:50]))
print(f'图片上传: {up_ok}/{len(uploads)}, 失败 {up_fail[:5]}')

# 2) trust 图
r = s.post(B + '/admin/factory-page', data={'f_trust.image': '/uploads/factory/trust-new.jpg'}, timeout=120)
print('trust 图同步:', r.status_code)

# 3) 同步 14 款
ok, fail = 0, []
for p in db['products']:
    if p['id'] not in IDS:
        continue
    sp = p.get('specs') or {}
    fields = {
        'title': p.get('title', ''), 'name': p.get('name', ''), 'model': p.get('model', ''),
        'series': p.get('series', ''), 'category': p.get('category', ''),
        'movement': p.get('movement', ''), 'japanese_option': p.get('japanese_option', ''),
        'gold_option': p.get('gold_option', '') or '',
        'moq_mono': p.get('moq_mono', ''), 'moq_mixed': p.get('moq_mixed', ''),
        'colors': str(p.get('colors', 0)), 'description': p.get('description', ''),
        'features': '\n'.join(p.get('features') or []),
        'gallery': '\n'.join(p.get('gallery') or []),
        'sort_order': str(p.get('sort_order', 999)), 'active': 'on',
        'image': p.get('image', ''),
        'spec_thickness': sp.get('case_thickness', ''), 'spec_diameter': sp.get('case_diameter', ''),
        'spec_band': sp.get('band_width', ''), 'spec_weight': sp.get('weight', ''),
        'spec_crystal': sp.get('crystal', 'Mineral Glass'), 'spec_case': sp.get('case', ''),
        'spec_strap': sp.get('strap', ''),
        'color_options': json.dumps(p.get('color_options', []), ensure_ascii=False),
    }
    for j, t in enumerate((p.get('tiers') or [])[:4]):
        fields[f'tier_qty_{j}'] = str(t.get('qty', ''))
        fields[f'tier_price_{j}'] = str(t.get('price', ''))
    r = s.post(B + '/admin/products/' + p['id'], data=fields, timeout=60)
    if r.status_code == 200:
        ok += 1
    else:
        fail.append((p['id'], r.status_code))
print(f'14款同步: 成功 {ok}, 失败 {fail}')
