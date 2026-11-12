# -*- coding: utf-8 -*-
# 同步到生产：工厂页实拍图 + 迪拜档口栏目 + OEM 服务图 + 219款产品 color_options
import os, json, requests

B = 'https://joefox-b2b-production.up.railway.app'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json'))

def upload_file(path):
    return open('public' + path, 'rb')

# ---------- 1. 工厂页：实拍图上传 + 迪拜栏目 ----------
fp = db['factory_page']
files = {}
fields = {
    'f_dubai.eyebrow': fp['dubai']['eyebrow'],
    'f_dubai.heading': fp['dubai']['heading'],
    'f_dubai.text': fp['dubai']['text'],
}
for i, (cap, local) in enumerate(zip(fp['dubai']['captions'], fp['dubai']['images'])):
    fields[f'f_dubai.captions.{i}'] = cap
    files[f'img_dubai.images.{i}'] = ('dubai.jpg', upload_file(local), 'image/jpeg')

# 实拍图上传（img_ 字段上传后自动写路径）
factory_imgs = {
    'img_hero.image': fp['hero']['image'],
    'img_about.image': fp['about']['image'],
    'img_capabilities.items.0.image': fp['capabilities']['items'][0]['image'],
    'img_capabilities.items.1.image': fp['capabilities']['items'][1]['image'],
    'img_capabilities.items.2.image': fp['capabilities']['items'][2]['image'],
    'img_capabilities.items.3.image': fp['capabilities']['items'][3]['image'],
    'img_qc.images.0': fp['qc']['images'][0],
    'img_qc.images.1': fp['qc']['images'][1],
}
for field, local in factory_imgs.items():
    files[field] = ('real.jpg', upload_file(local), 'image/jpeg')

r = s.post(B + '/admin/factory-page', data=fields, files=files, timeout=120)
print('工厂页+迪拜同步:', r.status_code)

# ---------- 2. OEM 服务卡片图 ----------
oem = db['oem']
fields = {k: oem[k] for k in ('title', 'subtitle', 'content', 'moq', 'sample_lead', 'mass_lead')}
files = {}
for i, svc in enumerate(oem['services']):
    fields[f'service_title_{i}'] = svc['title']
    fields[f'service_desc_{i}'] = svc['desc']
    files[f'service_image_{i}'] = ('svc.jpg', upload_file(svc['image']), 'image/jpeg')
r = s.post(B + '/admin/oem', data=fields, files=files, timeout=120)
print('OEM 服务图同步:', r.status_code)

# ---------- 3. 219 款产品 color_options ----------
ok, fail = 0, []
for i, p in enumerate(db['products']):
    fields = {
        'title': p.get('title', ''), 'name': p.get('name', ''), 'model': p.get('model', ''),
        'series': p.get('series', 'dual-movement'),
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
        if r.status == 200 if False else r.status_code == 200:
            ok += 1
        else:
            fail.append((p['id'], r.status_code))
    except Exception as e:
        fail.append((p['id'], str(e)))
    if (i + 1) % 40 == 0:
        print(f'产品进度 {i+1}/{len(db["products"])}')

print(f'产品 color_options: 成功 {ok}/{len(db["products"])}, 失败 {len(fail)}')
for f in fail[:10]:
    print(f)
