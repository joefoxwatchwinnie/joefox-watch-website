# -*- coding: utf-8 -*-
# 重新上传工厂页 8 张图（裁边后的最新版本）
import json, requests, os
B = 'https://joefox-b2b-production.up.railway.app'
s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code)
db = json.load(open('data/db.json'))
fp = db['factory_page']
imgs = {
    'img_hero.image': fp['hero']['image'],
    'img_about.image': fp['about']['image'],
    'img_capabilities.items.0.image': fp['capabilities']['items'][0]['image'],
    'img_capabilities.items.1.image': fp['capabilities']['items'][1]['image'],
    'img_capabilities.items.2.image': fp['capabilities']['items'][2]['image'],
    'img_capabilities.items.3.image': fp['capabilities']['items'][3]['image'],
    'img_qc.images.0': fp['qc']['images'][0],
    'img_qc.images.1': fp['qc']['images'][1],
}
files = {k: ('real.jpg', open('public' + v, 'rb'), 'image/jpeg') for k, v in imgs.items()}
r = s.post(B + '/admin/factory-page', data={}, files=files, timeout=120)
print('工厂图重传:', r.status_code)
