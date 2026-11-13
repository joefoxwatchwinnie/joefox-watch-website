#!/usr/bin/env python3
"""Round4: 同步颜色改名（Other->Gold/Silver 32处）到生产。只 POST 产品 color_options。"""
import json, requests

B = 'https://www.joefoxwatch.com'
s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))
ok, fail = 0, []
for i, p in enumerate(db['products'], 1):
    fields = {
        'model': p.get('model', ''),
        'name': p.get('name', ''),
        'title': p.get('title', ''),
        'series': p.get('series', ''),
        'category': p.get('category', ''),
        'movement': p.get('movement', ''),
        'japanese_option': p.get('japanese_option', ''),
        'gold_option': p.get('gold_option', '') or '',
        'moq': p.get('moq', ''),
        'description': p.get('description', ''),
        'spec_movement': p.get('specs', {}).get('movement', ''),
        'spec_case': p.get('specs', {}).get('case', ''),
        'spec_crystal': p.get('specs', {}).get('crystal', 'Mineral Glass'),
        'spec_case_size': p.get('specs', {}).get('case_size', ''),
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
        print(f'  进度 {i+1}/219')
print(f'产品同步: 成功 {ok}, 失败 {len(fail)}')
if fail:
    print('失败明细:', fail[:10])
