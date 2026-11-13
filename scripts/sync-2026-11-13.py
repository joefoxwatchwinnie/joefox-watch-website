# -*- coding: utf-8 -*-
# 2026-11-13 同步：红色logo、工厂页定制项目(删Custom Packaging)+迪拜档口信息、
# 219款产品 category 分类 + color_options 加价(gold/blue/black tone)
import os, json, requests

B = 'https://joefox-b2b-production.up.railway.app'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))

# ---------- 1. 红色 logo ----------
logo_path = 'public/uploads/brand/joefox-logo-red.png'
with open(logo_path, 'rb') as f:
    files = {
        'logo_light': ('logo.png', f.read(), 'image/png'),
        'logo_dark': ('logo.png', open(logo_path, 'rb').read(), 'image/png'),
    }
    r = s.post(B + '/admin/settings', files=files, timeout=60)
print('logo 同步:', r.status_code)

# ---------- 2. 工厂页 process（定制项目5项，删包装） + 迪拜档口 ----------
fp = db['factory_page']
proc = fp['process']
fields = {
    'f_process[eyebrow]': proc['eyebrow'],
    'f_process[heading]': proc['heading'],
    'f_process[custom_label]': proc['custom_label'],
}
for i, st in enumerate(proc['steps']):
    fields[f'f_process[steps][{i}][title]'] = st['title']
    fields[f'f_process[steps][{i}][text]'] = st['text']
for i, item in enumerate(proc['custom_items']):
    fields[f'f_process[custom_items][{i}]'] = item

dub = fp['dubai']
fields.update({
    'f_dubai.text': dub['text'],
    'f_dubai.name': dub.get('name', ''),
    'f_dubai.address': dub.get('address', ''),
    'f_dubai.phone': dub.get('phone', ''),
    'f_dubai.email': dub.get('email', ''),
})
r = s.post(B + '/admin/factory-page', data=fields, timeout=120)
print('工厂页 process+迪拜 同步:', r.status_code)

# ---------- 3. 219 款产品：category + color_options(加价) ----------
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
    if (i + 1) % 40 == 0:
        print(f'  进度 {i+1}/219')
print(f'产品同步: 成功 {ok}, 失败 {len(fail)}')
if fail:
    print('失败明细:', fail[:10])

# ---------- 验证 ----------
r = s.get(B + '/our-factory', timeout=30)
print('线上 Custom Packaging 出现次数(应为0):', r.text.count('Custom Packaging'))
r = s.get(B + '/products?category=student', timeout=30)
print('线上学生表数量:', r.text.count('href="/product/'))
