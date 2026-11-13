#!/usr/bin/env python3
"""Round5: 全量恢复生产产品数据（round4 漏发 active 字段导致 219 款被误下架）。
发送全部字段 + active:'on'，本地 db.json 为准。"""
import json, requests

B = 'https://www.joefoxwatch.com'
s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))
ok, fail = 0, []
for i, p in enumerate(db['products'], 1):
    sp = p.get('specs') or {}
    fields = {
        'title': p.get('title', ''),
        'name': p.get('name', ''),
        'model': p.get('model', ''),
        'series': p.get('series', 'dual-movement'),
        'category': p.get('category', ''),
        'movement': p.get('movement', ''),
        'japanese_option': p.get('japanese_option', ''),
        'gold_option': p.get('gold_option', '') or '',
        'moq_mono': p.get('moq_mono', ''),
        'moq_mixed': p.get('moq_mixed', ''),
        'colors': str(p.get('colors', 0)),
        'description': p.get('description', ''),
        'features': '\n'.join(p.get('features') or []),
        'gallery': '\n'.join(p.get('gallery') or []),
        'sort_order': str(p.get('sort_order', 999)),
        'active': 'on',
        'spec_thickness': sp.get('case_thickness', ''),
        'spec_diameter': sp.get('case_diameter', ''),
        'spec_band': sp.get('band_width', ''),
        'spec_weight': sp.get('weight', ''),
        'spec_crystal': sp.get('crystal', 'Mineral Glass'),
        'spec_case': sp.get('case', ''),
        'spec_strap': sp.get('strap', ''),
        'color_options': json.dumps(p.get('color_options', []), ensure_ascii=False),
    }
    for j, t in enumerate((p.get('tiers') or [])[:4]):
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
print(f'恢复同步: 成功 {ok}, 失败 {len(fail)}')
if fail:
    print('失败明细:', fail[:10])
