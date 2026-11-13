# -*- coding: utf-8 -*-
# 2026-11-13 第二轮同步：
# 1) 219款 color_options（黑/金/蓝/玫金钢带都加价、全黑无银款原价）
# 2) OEM 服务改为 3 项（删 Private Label Packaging）
# 3) public/uploads/products 的 640 张图补传到生产持久卷（relpath products/<name>）
import os, json, requests

B = 'https://joefox-b2b-production.up.railway.app'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))

# ---------- 1. OEM：3 项服务 ----------
oem = db['oem']
fields = {k: oem[k] for k in ('title', 'subtitle', 'content', 'moq', 'sample_lead', 'mass_lead')}
fields['service_count'] = str(len(oem['services']))
for i, svc in enumerate(oem['services']):
    fields[f'service_title_{i}'] = svc['title']
    fields[f'service_desc_{i}'] = svc['desc']
r = s.post(B + '/admin/oem', data=fields, timeout=120)
print('OEM 3项服务同步:', r.status_code)

# ---------- 2. 219 款产品 color_options ----------
ok, fail = 0, []
for i, p in enumerate(db['products']):
    fields = {
        'title': p.get('title', ''), 'name': p.get('name', ''), 'model': p.get('model', ''),
        'series': p.get('series', 'dual-movement'),
        'category': p.get('category', ''),
        'movement': p.get('movement', ''), 'japanese_option': p.get('japanese_option', ''),
        'gold_option': p.get('gold_option', ''),
        'moq_mono': str(p.get('moq_mono', '')), 'moq_mixed': str(p.get('moq_mixed', '')),
        'colors': str(p.get('colors', 0)),
        'description': p.get('description', ''),
        'features': '\n'.join(p.get('features', [])),
        'gallery': '\n'.join(p.get('gallery', [])),
        'sort_order': str(p.get('sort_order', i)),
        'active': 'on' if p.get('active', True) else '',
        'spec_thickness': p.get('specs', {}).get('case_thickness', ''),
        'spec_diameter': p.get('specs', {}).get('case_diameter', ''),
        'spec_band': p.get('specs', {}).get('band_width', ''),
        'spec_weight': p.get('specs', {}).get('weight', ''),
        'spec_crystal': p.get('specs', {}).get('crystal', 'Mineral Glass'),
        'spec_case': p.get('specs', {}).get('case', ''),
        'spec_strap': p.get('specs', {}).get('strap', ''),
        'color_options': json.dumps(p.get('color_options', []), ensure_ascii=False),
    }
    for j, t in enumerate(p.get('tiers', [])[:4]):
        fields[f'tier_qty_{j}'] = str(t.get('qty', ''))
        fields[f'tier_price_{j}'] = str(t.get('price', ''))
    try:
        r = s.post(B + '/admin/products/' + p['id'], data=fields, timeout=60)
        if r.status_code == 200:
            ok += 1
        else:
            fail.append((p['id'], r.status_code))
    except Exception as e:
        fail.append((p['id'], str(e)[:60]))
    if (i + 1) % 60 == 0:
        print(f'  产品进度 {i+1}/219')
print(f'产品同步: 成功 {ok}, 失败 {len(fail)}')
if fail:
    print('失败明细:', fail[:10])

# ---------- 3. 产品图补传到持久卷 ----------
pdir = 'public/uploads/products'
files = sorted(f for f in os.listdir(pdir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
up_ok, up_fail, skipped = 0, [], 0
for n, fn in enumerate(files):
    # 已在线上的跳过（HEAD 200）
    try:
        h = s.head(B + '/uploads/products/' + fn, timeout=15)
        if h.status_code == 200:
            skipped += 1
            continue
    except Exception:
        pass
    try:
        with open(os.path.join(pdir, fn), 'rb') as f:
            r = s.post(B + '/admin/upload-image',
                       data={'relpath': 'products/' + fn},
                       files={'file': (fn, f.read(), 'image/jpeg')}, timeout=60)
        if r.status_code == 200:
            up_ok += 1
        else:
            up_fail.append((fn, r.status_code))
    except Exception as e:
        up_fail.append((fn, str(e)[:60]))
    if (n + 1) % 80 == 0:
        print(f'  图片进度 {n+1}/{len(files)}')
print(f'图片补传: 新传 {up_ok}, 已存在跳过 {skipped}, 失败 {len(up_fail)}')
if up_fail:
    print('失败明细:', up_fail[:10])
