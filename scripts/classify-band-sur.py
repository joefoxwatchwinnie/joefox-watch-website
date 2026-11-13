# -*- coding: utf-8 -*-
# 按目录规则重算颜色加价：
# - 金额与适用色调来自每款产品的 gold_option（目录页原文，如 "Gold、Blue & Black Tone +￥6.00/pc"）
# - 判定基于“表带颜色”（图片下半段）：银带=原价，表盘色不参与
# - 金色族（金/玫金/间金/间玫）→ Gold 档；尼龙带产品一律原价
import json, os, re
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
db = json.load(open('data/db.json'))

def parse_gold_option(note):
    if not note or note == 'None':
        return set(), 0
    m = re.search(r'\+\s*￥\s*(\d+(?:\.\d+)?)', note)
    amount = float(m.group(1)) if m else 0
    tones = set()
    if re.search(r'Gold', note, re.I): tones.add('gold')
    if re.search(r'Blue', note, re.I): tones.add('blue')
    if re.search(r'Black', note, re.I): tones.add('black')
    return tones, amount

def classify_band(path):
    """只看表带区域（下部 45% + 两侧带条），返回带色 bucket: gold/blue/black/silver"""
    im = Image.open('public' + path).convert('RGB')
    w, h = im.size
    # 表带区域：y > 0.55h 的整幅 + y in [0.2h,0.55h] 的左右两侧
    im.thumbnail((260, 260))
    w, h = im.size
    a = np.asarray(im).astype(np.float32) / 255.0
    ys, xs = np.mgrid[0:h, 0:w]
    region = (ys > 0.55 * h) | ((ys > 0.2 * h) & ((xs < 0.25 * w) | (xs > 0.75 * w)))
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(-1); mn = a.min(-1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    d = np.maximum(mx - mn, 1e-6)
    hue = np.zeros_like(mx)
    m_ = mx == r; hue[m_] = ((g - b)[m_] / d[m_]) % 6
    m_ = mx == g; hue[m_] = ((b - r)[m_] / d[m_]) + 2
    m_ = mx == b; hue[m_] = ((r - g)[m_] / d[m_]) + 4
    hue = hue * 60
    mask = region & ((mx < 0.92) | (s > 0.18))
    if mask.sum() < 30:
        return 'silver'
    hh, ss, vv = hue[mask], s[mask], v[mask]
    n = mask.sum()
    gold = ((hh >= 28) & (hh <= 62) & (ss > 0.30) & (vv > 0.25)).sum() / n
    rose = (((hh >= 332) | (hh <= 26)) & (ss > 0.22) & (ss < 0.65) & (vv > 0.45)).sum() / n
    blue = ((hh >= 185) & (hh <= 262) & (ss > 0.28)).sum() / n
    black = (vv < 0.22).sum() / n
    silver = ((ss < 0.16) & (vv > 0.45)).sum() / n
    if black > 0.45: return 'black'
    if blue > 0.28: return 'blue'
    if (gold > 0.10 or rose > 0.10) and silver > 0.10: return 'gold'  # 间金/间玫
    if gold > 0.22 or rose > 0.22: return 'gold'
    if black > 0.25: return 'black'
    return 'silver'

stats = {}
for p in db['products']:
    tones, amount = parse_gold_option(p.get('gold_option'))
    strap = (p.get('specs', {}) or {}).get('strap', '') or ''
    is_nylon = 'nylon' in strap.lower()
    for o in p.get('color_options', []):
        if amount == 0 or is_nylon:
            sur = 0
        else:
            try:
                band = classify_band(o['image'])
            except Exception as e:
                print('ERR', p['id'], o['image'], e); band = 'silver'
            sur = amount if band in tones else 0
            stats[(band, sur)] = stats.get((band, sur), 0) + 1
        o['sur'] = sur

json.dump(db, open('data/db.json', 'w'), ensure_ascii=False, indent=2)
print('带色→加价分布:', {f'{k[0]}/{k[1]}': v for k, v in sorted(stats.items())})
tot = sum(len(p.get('color_options', [])) for p in db['products'])
surcharged = sum(1 for p in db['products'] for o in p.get('color_options', []) if o.get('sur'))
print(f'总变体 {tot}，加价变体 {surcharged}')
# 抽查
for pid in ['qz-12055', 'qz-9103', 'qz-9156', 'dm-2812']:
    p = [x for x in db['products'] if x['id'] == pid][0]
    print(pid, p.get('gold_option'), [(o['name'], o['sur']) for o in p.get('color_options', [])][:12])
