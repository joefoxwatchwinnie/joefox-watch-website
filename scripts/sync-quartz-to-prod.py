# 将本地 db.json 中石英产品的 colors/gallery 同步到生产环境(经后台接口)
# 价格、规格等所有字段原样回传, 防止 parseProductBody 重建时丢失。
import json, time, urllib.request, urllib.parse, http.cookiejar

B = 'https://joefox-b2b-production.up.railway.app'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

data = urllib.parse.urlencode({'username': 'admin', 'password': 'joefox2026'}).encode()
op.open(B + '/admin/login', data, timeout=30)

db = json.load(open('data/db.json'))
qz = [p for p in db['products'] if p.get('series') == 'quartz']
ok, fail = 0, []
for i, p in enumerate(qz):
    fields = {
        'title': p.get('title', ''),
        'name': p.get('name', ''),
        'model': p.get('model', ''),
        'series': 'quartz',
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
        'active': 'on',
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
        if r.status == 200:
            ok += 1
        else:
            fail.append((p['id'], r.status))
    except Exception as e:
        fail.append((p['id'], str(e)))
    if (i + 1) % 25 == 0:
        print(f'进度 {i+1}/{len(qz)}')

print(f'成功 {ok}/{len(qz)}, 失败 {len(fail)}')
for f in fail[:10]:
    print(f)
