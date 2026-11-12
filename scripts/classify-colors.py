# -*- coding: utf-8 -*-
# 自动识别产品颜色变体图的主色 → 写入 products[].color_options
import json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
db = json.load(open('data/db.json'))

def classify(path):
    im = Image.open('public' + path).convert('RGB')
    im.thumbnail((220, 220))
    a = np.asarray(im).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(-1); mn = a.min(-1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    # hue
    d = np.maximum(mx - mn, 1e-6)
    hue = np.zeros_like(mx)
    m = mx == r; hue[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g; hue[m] = ((b - r)[m] / d[m]) + 2
    m = mx == b; hue[m] = ((r - g)[m] / d[m]) + 4
    hue = hue * 60  # 0-360

    # 只统计非白背景像素
    mask = (mx < 0.92) | (s > 0.18)
    if mask.sum() < 40: return 'White'
    hh, ss, vv = hue[mask], s[mask], v[mask]

    gold  = (hh >= 28) & (hh <= 62) & (ss > 0.35) & (vv > 0.25)
    rose  = (((hh >= 335) | (hh <= 24)) & (ss > 0.22) & (ss < 0.62) & (vv > 0.45))  # 排除高饱和红塑料
    blue  = (hh >= 185) & (hh <= 262) & (ss > 0.30)
    black = vv < 0.22
    silver= (ss < 0.16) & (vv > 0.45)
    n = mask.sum()
    fg, fr, fb, fk, fs = gold.sum()/n, rose.sum()/n, blue.sum()/n, black.sum()/n, silver.sum()/n

    if fk > 0.45: return 'Black'
    if fb > 0.30: return 'Blue'
    # 间色：金色/玫金与银色钢带共存（相对比例，排除黑盘干扰）
    if fg > 0.10 and fs > 0.10 and fg / max(fg + fs, 1e-6) > 0.15: return 'Two-Tone Gold'
    if fr > 0.10 and fs > 0.10 and fr / max(fr + fs, 1e-6) > 0.15: return 'Two-Tone Rose Gold'
    if fg > 0.25: return 'Gold'
    if fr > 0.25: return 'Rose Gold'
    if fs > 0.40: return 'Silver'
    if fk > 0.28: return 'Black'
    # 其它按主导色相
    hh2 = hh[ss > 0.25]
    if len(hh2) < n * 0.12: return 'White'
    hmed = np.median(hh2)
    for lo, hi, name in [(63,110,'Green'),(263,330,'Purple'),(111,165,'Green'),(166,184,'Teal'),
                         (23,27,'Orange'),(66,90,'Green')]:
        if lo <= hmed <= hi: return name
    if 331 <= hmed or hmed <= 24: return 'Red' if ss.mean() > 0.55 else 'Pink'
    if 63 <= hmed <= 110: return 'Green'
    return 'Other'

count = {}
for p in db['products']:
    opts = []
    for img in (p.get('gallery') or []):
        full = 'public' + img
        if not os.path.exists(full): continue
        try: name = classify(img)
        except Exception as e:
            print('ERR', p['id'], img, e); continue
        opts.append({'image': img, 'name': name})
    p['color_options'] = opts
    for o in opts: count[o['name']] = count.get(o['name'], 0) + 1

json.dump(db, open('data/db.json', 'w'), ensure_ascii=False, indent=2)
print('分类统计:', dict(sorted(count.items(), key=lambda x: -x[1])))
dm = sum(1 for p in db['products'] if p.get('series')=='dual-movement' and p.get('color_options'))
qz = sum(1 for p in db['products'] if p.get('series')=='quartz' and p.get('color_options'))
print(f'双机芯 {dm}/74, 石英 {qz}/145')
