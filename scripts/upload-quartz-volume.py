# -*- coding: utf-8 -*-
# 并发上传 public/uploads/quartz 全部图片到生产持久卷（path-preserving）
import os, sys, json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

B = 'https://joefox-b2b-production.up.railway.app'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

s = requests.Session()
r = s.post(B + '/admin/login', data={'username': 'admin', 'password': 'joefox2026'}, timeout=30)
print('登录:', r.status_code, flush=True)

files = []
for dirpath, _, names in os.walk('public/uploads/quartz'):
    for n in names:
        rel = os.path.relpath(os.path.join(dirpath, n), 'public')
        # rel 形如 uploads/quartz/xxx.jpg；上传 relpath 需要去掉 uploads/ 前缀
        files.append((rel, rel[len('uploads/'):] if rel.startswith('uploads/') else rel))
print(f'待上传 {len(files)} 个文件', flush=True)

ok, fail = 0, []
lock_results = []

def up(item):
    rel, remote = item
    for attempt in range(3):
        try:
            with open('public/' + rel, 'rb') as f:
                r = s.post(B + '/admin/upload-image', files={'file': (os.path.basename(rel), f, 'image/jpeg')},
                           data={'relpath': remote}, timeout=120)
            if r.status_code == 200:
                return rel, 200
        except Exception as e:
            r = None
            err = str(e)
        import time; time.sleep(1.5 * (attempt + 1))
    return rel, getattr(r, 'status_code', 0) if r else 0

with ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(up, item) for item in files]
    for i, fut in enumerate(as_completed(futs)):
        rel, code = fut.result()
        if code == 200:
            ok += 1
        else:
            fail.append((rel, code))
        if (i + 1) % 200 == 0:
            print(f'进度 {i+1}/{len(files)} 成功{ok}', flush=True)

print(f'完成: 成功 {ok}/{len(files)}, 失败 {len(fail)}', flush=True)
for rel, code in fail[:20]:
    print('FAIL', rel, code)
json.dump([f[0] for f in fail], open('scripts/.quartz-fail.json', 'w'))
