# 同步到生产: 74款双机芯产品(features/gallery 全字段) + 工厂页图片路径
import json, time, urllib.request, urllib.parse, http.cookiejar

B = 'https://joefox-b2b-production.up.railway.app'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(B + '/admin/login', urllib.parse.urlencode({'username': 'admin', 'password': 'joefox2026'}).encode(), timeout=30)

db = json.load(open('data/db.json'))
dm = [p for p in db['products'] if p.get('series') == 'dual-movement']
ok, fail = 0, []
for i, p in enumerate(dm):
    fields = {
        'title': p.get('title', ''),
        'name': p.get('name', ''),
        'model': p.get('model', ''),
        'series': 'dual-movement',
        'movement': p.get('movement', ''),
        'japanese_option': p.get('japanese_option', ''),
        'gold_option': p.get('gold_option', ''),
        'moq_mono': str(p.get('moq_mono', '')),
        'moq_mixed': str(p.get('moq_mixed', '')),
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
    }
    for j, t in enumerate(p.get('tiers', [])[:4]):
        fields[f'tier_qty_{j}'] = str(t.get('qty', ''))
        fields[f'tier_price_{j}'] = str(t.get('price', ''))
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(B + '/admin/products/' + p['id'], data=body, method='POST')
    try:
        r = op.open(req, timeout=30)
        if r.status == 200: ok += 1
        else: fail.append((p['id'], r.status))
    except Exception as e:
        fail.append((p['id'], str(e)))
    if (i + 1) % 25 == 0: print(f'产品进度 {i+1}/{len(dm)}')

print(f'双机芯产品: 成功 {ok}/{len(dm)}, 失败 {len(fail)}')
for f in fail[:10]: print(f)

# 工厂页图片路径
fp = db['factory_page']
fields = {
    'f_hero.image': fp['hero']['image'],
    'f_about.image': fp['about']['image'],
    'f_capabilities.items.0.image': fp['capabilities']['items'][0]['image'],
    'f_capabilities.items.1.image': fp['capabilities']['items'][1]['image'],
    'f_capabilities.items.2.image': fp['capabilities']['items'][2]['image'],
    'f_capabilities.items.3.image': fp['capabilities']['items'][3]['image'],
    'f_qc.images.0': fp['qc']['images'][0],
    'f_qc.images.1': fp['qc']['images'][1],
}
body = urllib.parse.urlencode(fields).encode()
req = urllib.request.Request(B + '/admin/factory-page', data=body, method='POST')
r = op.open(req, timeout=30)
print('工厂页图片路径同步:', r.status)
