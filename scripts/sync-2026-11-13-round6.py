#!/usr/bin/env python3
"""Round6: 同步迪拜区改动——删第4张大图 + 文字/电话地址顺序（模板已改，数据清 images[3]）。"""
import json, requests

B = 'https://www.joefoxwatch.com'
s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)

db = json.load(open('data/db.json', encoding='utf-8'))
dub = db['factory_page']['dubai']
fields = {
    'f_dubai.text': dub.get('text', ''),
    'f_dubai.name': dub.get('name', ''),
    'f_dubai.address': dub.get('address', ''),
    'f_dubai.phone': dub.get('phone', ''),
    'f_dubai.email': dub.get('email', ''),
}
imgs = dub.get('images', [])
caps = dub.get('captions', [])
for i in range(4):
    fields[f'f_dubai.images.{i}'] = imgs[i] if i < len(imgs) else ''
    fields[f'f_dubai.captions.{i}'] = caps[i] if i < len(caps) else ''
r = s.post(B + '/admin/factory-page', data=fields, timeout=120)
print('dubai 同步:', r.status_code)
