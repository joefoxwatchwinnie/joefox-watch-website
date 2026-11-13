#!/usr/bin/env python3
"""把多表拼合图拆成单表图。
默认报告模式：拆分并输出蒙太奇到 /tmp/split-check/ 供人工核验顺序；
--apply 才写入 public/uploads/products/<model>-cNN.jpg 并更新 db/seed 的 color_options+gallery。
颜色名用表带分类器（Silver/Black/Blue/Gold/Two-Tone/Rose Gold），双机芯规则：有银色选项时非银 +10，全黑/无银整款原价。"""
import json, sys, os, math
import numpy as np
from PIL import Image, ImageDraw

OUT_W, OUT_H = 900, 1200  # 3:4


def segments(profile, min_gap, min_size):
    """1D 投影 → 连续非零段 [(start,end)]，合并间隔<min_gap，丢弃<min_size"""
    idx = np.where(profile > 0)[0]
    if len(idx) == 0:
        return []
    segs, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > min_gap:
            segs.append((s, prev))
            s = i
        prev = i
    segs.append((s, prev))
    return [(a, b) for a, b in segs if b - a >= min_size]


def split_composite(path):
    from scipy import ndimage
    im = Image.open(path).convert('RGB')
    a = np.asarray(im)
    gray = a.mean(-1)
    mask = gray < 249  # 浅色银表也要能检出
    lab, n = ndimage.label(mask)
    cells = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < 2000:  # 噪点/阴影
            continue
        w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        # 单只表：占图面积合理
        if w < 80 or h < 120:
            continue
        cell = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        cells.append((ys.min(), xs.min(), cell))
    # 按阅读顺序：行（y 聚类 150px 内视为同行）内按 x 排序
    cells.sort(key=lambda t: (round(t[0] / 200), t[1]))
    return [c for _, _, c in cells]


def classify_band(path):
    """单表图（3:4 白底画布，表居中）的表带颜色判定：
    取样顶部 18%（上表带）+ 底部 28%（下表带）+ 左右边缘条，避开中央表盘。"""
    im = Image.open(path).convert('RGB')
    w, h = im.size
    a = np.asarray(im).astype(np.float32) / 255.0
    ys, xs = np.mgrid[0:h, 0:w]
    region = (ys < 0.18 * h) | (ys > 0.72 * h) | ((xs < 0.10 * w) | (xs > 0.90 * w)) & ((ys > 0.18 * h) & (ys < 0.72 * h))
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
    if mask.sum() < 50:
        return 'silver'
    hh, ss, vv = hue[mask], s[mask], v[mask]
    gold = ((hh >= 28) & (hh <= 62) & (ss > 0.30) & (vv > 0.25)).mean()
    rose = (((hh >= 332) | (hh <= 26)) & (ss > 0.22) & (ss < 0.65) & (vv > 0.45)).mean()
    blue = ((hh >= 185) & (hh <= 262) & (ss > 0.28)).mean()
    black = (vv < 0.24).mean()
    silver = ((ss < 0.16) & (vv > 0.45)).mean()
    med_v = float(np.median(vv))
    if black > 0.45 or med_v < 0.42:
        if blue > 0.30:
            return 'blue'
        return 'black'
    if blue > 0.28:
        return 'blue'
    if (gold > 0.10 or rose > 0.10) and silver > 0.10:
        return 'two-tone'
    if rose > 0.22:
        return 'rose'
    if gold > 0.22:
        return 'gold'
    if black > 0.25:
        return 'black'
    return 'silver'


def to_canvas(cell):
    """居中放到 3:4 白底画布"""
    cell.thumbnail((OUT_W - 60, OUT_H - 60))
    canvas = Image.new('RGB', (OUT_W, OUT_H), 'white')
    canvas.paste(cell, ((OUT_W - cell.width) // 2, (OUT_H - cell.height) // 2))
    return canvas


def main():
    apply = '--apply' in sys.argv
    db = json.load(open('data/db.json', encoding='utf-8'))
    cand = [p for p in db['products'] if not p.get('color_options') and (p.get('colors') or 0) > 0]
    os.makedirs('/tmp/split-check', exist_ok=True)
    results = {}
    for p in cand:
        src = 'public' + p['image']
        if not os.path.exists(src):
            print('MISSING', p['id']); continue
        cells = split_composite(src)
        results[p['id']] = (p, cells)
        print(f"{p['id']} {p['model']} {p['name']}: 拆出 {len(cells)} 只 (目录 colors={p['colors']})")

    if not apply:
        # 蒙太奇：每款一行，标注顺序号+分类色名
        cols = 10
        for idx, (pid, (p, cells)) in enumerate(results.items(), 1):
            cw, ch = 160, 240
            rows = math.ceil(len(cells) / cols)
            canvas = Image.new('RGB', (cols * cw, rows * ch + 30), 'white')
            d = ImageDraw.Draw(canvas)
            d.text((6, 4), f"{pid} {p['model']} {p['name']} ({len(cells)}只)", fill='black')
            tmpdir = f'/tmp/split-check/{pid}'
            os.makedirs(tmpdir, exist_ok=True)
            for i, cell in enumerate(cells):
                tmp = f'{tmpdir}/c{i:02d}.jpg'
                to_canvas(cell).save(tmp, quality=90)
                band = classify_band(tmp)
                thumb = Image.open(tmp); thumb.thumbnail((cw - 12, ch - 40))
                r, c = divmod(i, cols)
                canvas.paste(thumb, (c * cw + 6, r * ch + 34))
                d.text((c * cw + 6, r * ch + ch - 30), f'#{i+1} {band}', fill='black')
            canvas.save(f'/tmp/split-check/{pid}-montage.jpg', quality=85)
        print('蒙太奇存 /tmp/split-check/*-montage.jpg')
        return

    # apply：写入文件 + color_options + gallery
    # 颜色名为人工目检结果（视觉模型逐只确认，2026-11-13）
    COLOR_MAP = {
        'dm-1942':  ['Black', 'Silver', 'Silver', 'Gold'],
        'dm-1943B': ['Silver', 'Black', 'Blue', 'Two-Tone Gold'],
        'dm-1956':  ['Silver', 'Gold', 'Gold', 'Black'],
        'dm-1960':  ['Black', 'Black', 'Black', 'Silver', 'Blue', 'Silver', 'Gold', 'Gold', 'Gold', 'Silver'],
        'dm-2106':  ['Silver', 'Silver', 'Silver', 'Blue', 'Gold', 'Black'],
        'dm-2106B': ['Silver', 'Black', 'Blue'],
        'dm-2106C': ['Silver', 'Black', 'Blue', 'Gold', 'Silver'],
        'dm-2106E': ['Black', 'Black', 'Gold', 'Gold'],
        'dm-2106F': ['Black', 'Black', 'Gold', 'Gold'],
        'dm-2106H': ['Silver', 'Silver', 'Silver', 'Blue', 'Two-Tone Gold', 'Gold', 'Black'],
        'dm-2311':  ['Silver', 'Silver', 'Blue', 'Black', 'Black', 'Blue'],
        'dm-24007': ['Black', 'Grey', 'Green', 'White', 'Orange', 'Blue', 'White', 'White', 'Blue', 'Pink', 'Brown', 'Gold', 'White', 'Black', 'Black'],
        'dm-2420':  {'skip': [0], 'names': ['Black', 'Blue', 'Gold', 'White', 'White', 'Blue', 'Gold', 'Rose Gold', 'Black', 'Blue']},
        'dm-3028':  ['Two-Tone Gold', 'Two-Tone Gold', 'Two-Tone Gold', 'Blue', 'Gold'],
    }
    # 塑料壳/彩色硅胶带学生表：整款原价不改价
    PLASTIC = {'dm-24007', 'dm-2420'}
    for pid, (p, cells) in list(results.items()):
        conf = COLOR_MAP[pid]
        if isinstance(conf, dict):
            names = conf['names']
            skip = set(conf.get('skip', []))
        else:
            names, skip = conf, set()
        if len(names) != len(cells) - len([i for i in skip if i < len(cells)]):
            print(f'!! {pid}: 拆出 {len(cells)} 但映射 {len(names)}，跳过该款'); continue
        gi = 0
        opts, gallery = [], []
        for i, cell in enumerate(cells):
            if i in skip:
                continue
            fname = f"{p['model']}-c{i+1:02d}.jpg"
            fpath = 'public/uploads/products/' + fname
            to_canvas(cell).save(fpath, quality=90)
            rel = '/uploads/products/' + fname
            opts.append({'name': names[gi], 'image': rel, 'sur': 0})
            gallery.append(rel)
            gi += 1
        # 双机芯规则：整款有 Silver 选项时非银 +10；无 Silver（全黑等）或塑料款 → 原价
        has_silver = any(o['name'] == 'Silver' for o in opts)
        for o in opts:
            o['sur'] = 10.0 if (has_silver and o['name'] != 'Silver' and pid not in PLASTIC) else 0
        p['color_options'] = opts
        if len(gallery) >= len(p.get('gallery') or []):
            p['gallery'] = gallery
        p['colors'] = len(opts)
        print(pid, p['model'], [(o['name'], o['sur']) for o in opts])
    json.dump(db, open('data/db.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    seed = json.load(open('lib/seed-data.json', encoding='utf-8'))
    m = {p['id']: p for p in db['products']}
    for p in seed.get('products', []):
        src = m.get(p['id'])
        if src:
            p['color_options'] = src.get('color_options', [])
            p['gallery'] = src.get('gallery', [])
            p['colors'] = src.get('colors', 0)
    json.dump(seed, open('lib/seed-data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('已写入 db.json + seed')


if __name__ == '__main__':
    main()
