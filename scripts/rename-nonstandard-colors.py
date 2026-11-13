#!/usr/bin/env python3
"""把非标准颜色名（Other/Pink/White/Green/Orange 等）按图片识别改成标准带色名。
默认报告模式（拼图供人工核验）；--apply 才写库。黑名单桶 brown 保持原名。"""
import json, os, sys, math
import numpy as np
from PIL import Image, ImageDraw

STANDARD = {'Silver', 'Black', 'Blue', 'Gold', 'Rose Gold', 'Two-Tone Gold', 'Two-Tone Rose Gold'}
BUCKET_NAME = {'black': 'Black', 'silver': 'Silver', 'gold': 'Gold', 'rose': 'Rose Gold',
               'two-tone': 'Two-Tone Gold', 'blue': 'Blue'}


def classify_band(path):
    """与 classify-band-sur.py v3 相同逻辑"""
    im = Image.open('public' + path).convert('RGB')
    im.thumbnail((260, 260))
    w, h = im.size
    a = np.asarray(im).astype(np.float32) / 255.0
    ys, xs = np.mgrid[0:h, 0:w]
    region = (ys > 0.72 * h) | ((ys > 0.2 * h) & (ys < 0.55 * h) & ((xs < 0.22 * w) | (xs > 0.78 * w)))
    mx = a.max(-1); mn = a.min(-1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    d = np.maximum(mx - mn, 1e-6)
    hue = np.zeros_like(mx)
    m_ = mx == a[..., 0]; hue[m_] = ((a[..., 1] - a[..., 2])[m_] / d[m_]) % 6
    m_ = mx == a[..., 1]; hue[m_] = ((a[..., 2] - a[..., 0])[m_] / d[m_]) + 2
    m_ = mx == a[..., 2]; hue[m_] = ((a[..., 0] - a[..., 1])[m_] / d[m_]) + 4
    hue *= 60
    mask = region & ((mx < 0.92) | (s > 0.18))
    if mask.sum() < 30:
        return 'silver'
    hh, ss, vv = hue[mask], s[mask], v[mask]
    gold = ((hh >= 28) & (hh <= 62) & (ss > 0.30) & (vv > 0.25)).mean()
    rose = (((hh >= 332) | (hh <= 26)) & (ss > 0.22) & (ss < 0.65) & (vv > 0.45)).mean()
    blue = ((hh >= 185) & (hh <= 262) & (ss > 0.28)).mean()
    brown = ((hh >= 8) & (hh <= 30) & (ss > 0.30) & (vv > 0.15) & (vv < 0.55)).mean()
    black = (vv < 0.22).mean()
    silver = ((ss < 0.16) & (vv > 0.45)).mean()
    med_v = float(np.median(vv))
    if black > 0.45 or med_v < 0.40:
        if blue > 0.30:
            return 'blue'
        if brown > 0.35:
            return 'brown'
        return 'black'
    if blue > 0.28:
        return 'blue'
    if (gold > 0.10 or rose > 0.10) and silver > 0.10:
        return 'two-tone'
    if rose > 0.22:
        return 'rose'
    if gold > 0.22:
        return 'gold'
    if brown > 0.30:
        return 'brown'
    if black > 0.25:
        return 'black'
    return 'silver'


def main():
    apply = '--apply' in sys.argv
    db = json.load(open('data/db.json', encoding='utf-8'))
    proposals = []  # (pid, model, old, new, sur, img)
    for p in db['products']:
        for o in p.get('color_options', []):
            name = o.get('name', '')
            if name in STANDARD:
                continue
            try:
                band = classify_band(o['image'])
            except Exception as e:
                print('ERR', p['id'], o['image'], e)
                continue
            if band == 'brown':
                continue  # 棕皮带保留原名
            # 只改 Other -> Gold/Silver（人工核验过的安全集合）。
            # Pink/Green/White 是学生塑料表的真实带色名，彩色带识别不可靠，一律不改。
            if name != 'Other' or band not in ('gold', 'silver'):
                continue
            new = BUCKET_NAME[band]
            if new != name:
                proposals.append((p['id'], p.get('model', ''), name, new, o.get('sur'), o['image']))
    print(f'待改名 {len(proposals)} 处')
    for t in proposals:
        print(f'  {t[0]} {t[1]}: {t[2]} -> {t[3]} (sur={t[4]}) {t[5].split("/")[-1]}')

    if apply:
        pm = {}
        for pid, model, old, new, sur, img in proposals:
            pm.setdefault(pid, {})[img] = new
        n = 0
        for p in db['products']:
            for o in p.get('color_options', []):
                if p['id'] in pm and pm[p['id']].get(o['image']) and o['name'] not in STANDARD:
                    o['name'] = pm[p['id']][o['image']]
                    n += 1
        json.dump(db, open('data/db.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('已写入 db.json，改名', n, '处')
        # 同步 seed
        seed = json.load(open('lib/seed-data.json', encoding='utf-8'))
        m = {p['id']: p for p in db['products']}
        for p in seed.get('products', []):
            src = m.get(p['id'])
            if src:
                p['color_options'] = src.get('color_options', [])
        json.dump(seed, open('lib/seed-data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('seed 已同步')
    else:
        # 报告模式：拼图核验（每批 24 张，标注 当前名 -> 建议名）
        os.makedirs('/tmp/rename-check', exist_ok=True)
        per, cols = 24, 6
        batches = math.ceil(len(proposals) / per)
        for b in range(batches):
            chunk = proposals[b * per:(b + 1) * per]
            cw, ch = 220, 260
            canvas = Image.new('RGB', (cols * cw, ((len(chunk) + cols - 1) // cols) * ch), 'white')
            d = ImageDraw.Draw(canvas)
            for i, (pid, model, old, new, sur, img) in enumerate(chunk):
                r, c = divmod(i, cols)
                try:
                    im = Image.open('public' + img).convert('RGB')
                    im.thumbnail((cw - 12, ch - 46))
                    canvas.paste(im, (c * cw + 6, r * ch + 4))
                except Exception:
                    pass
                d.text((c * cw + 6, r * ch + ch - 36), f'{old} -> {new}', fill='black')
                d.text((c * cw + 6, r * ch + ch - 22), f'{pid} {img.split("/")[-1][:18]}', fill='gray')
            canvas.save(f'/tmp/rename-check/batch{b+1}.jpg', quality=85)
        print(f'拼图 {batches} 张存 /tmp/rename-check/')


if __name__ == '__main__':
    main()
