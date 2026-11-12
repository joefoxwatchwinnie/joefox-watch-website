# -*- coding: utf-8 -*-
# 重做石英配色变体图 v3: 完整手表(表盘+表带) → 白底 3:4 竖版 1200x1600
# 配色行位于页面下部 "N COLORS AVAILABLE" 文字下方 (约 875-1120pt)
# 自动定位: 在 y∈[0.64H, 0.94H] 窗口内找最高内容带(>40pt)即配色行
import json, re, os
import pymupdf
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = '/Users/cc/Desktop/cc/目录（更新中）/【JOEFOX】price-QuartzWatches Catalog.pdf'
Z = 5
CANVAS_W, CANVAS_H = 1200, 1600

db = json.load(open(os.path.join(ROOT, 'data/db.json')))
qz = [p for p in db['products'] if p.get('series') == 'quartz']
pdf = pymupdf.open(PDF)

pagecache = {}
def get_strip(page):
    """渲染页面并返回配色行内容带 (y0,y1, img)。粘连处理交给列分割。"""
    if page in pagecache:
        return pagecache[page]
    pg = pdf[page - 1]
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(Z, Z), alpha=False)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    a = np.asarray(img.convert('L'))
    Hpt = pg.rect.height
    y0 = int(0.63 * Hpt * Z)
    y1 = min(a.shape[0], int(0.95 * Hpt * Z))
    win = a[y0:y1]
    rowc = (win < 243).mean(axis=1)
    content = rowc > 0.008
    # 按连续内容段分组 (间隙 > 8pt 分段)
    gapmax = int(8 * Z)
    bands = []
    start = None
    gap = 0
    for i, c in enumerate(content):
        if c:
            if start is None: start = i
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap > gapmax:
                    bands.append((start, i - gap + 1)); start = None; gap = 0
    if start is not None:
        bands.append((start, len(content)))
    # 取带内最高的浅色段 (配色行), 排除深色规格条, 忽略微小行(分隔线)
    cands = []
    for s, e in bands:
        if e - s <= 40 * Z: continue
        seg = np.asarray(img.convert('L'))[y0 + s:y0 + e]
        if seg.mean() < 150: continue  # 深色 spec bar
        cands.append((s, e))
    if not cands:
        pagecache[page] = None
        return None
    s, e = max(cands, key=lambda b: b[1] - b[0])
    strip = img.crop((0, y0 + s - int(2 * Z), img.width, y0 + e + int(2 * Z)))
    pagecache[page] = strip
    return strip

def col_runs(strip):
    a = np.asarray(strip.convert('L'))
    col_min = a.min(axis=0)
    white = col_min > 242
    runs, start = [], None
    for x, w in enumerate(white):
        if not w and start is None: start = x
        elif w and start is not None:
            runs.append((start, x)); start = None
    if start is not None: runs.append((start, len(white)))
    return [(s, e) for s, e in runs if e - s > 60]

def to_canvas(sub):
    """白边裁剪 → 白底 3:4 画布居中, 高度占 88%"""
    sa = np.asarray(sub.convert('L'))
    rows = np.where(sa.min(axis=1) < 243)[0]
    cols = np.where(sa.min(axis=0) < 243)[0]
    if len(rows) and len(cols):
        sub = sub.crop((max(0, cols.min() - 6), max(0, rows.min() - 6),
                        min(sub.width, cols.max() + 7), min(sub.height, rows.max() + 7)))
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), 'white')
    h = int(CANVAS_H * 0.88)
    w = int(sub.width * h / sub.height)
    if w > int(CANVAS_W * 0.94):
        w = int(CANVAS_W * 0.94)
        h = int(sub.height * w / sub.width)
    sub2 = sub.resize((w, h), Image.LANCZOS)
    canvas.paste(sub2, ((CANVAS_W - w) // 2, (CANVAS_H - h) // 2))
    return canvas

changed = 0
no_strip = []
mismatch = []
for p in qz:
    m = re.search(r'-p(\d+)-main', p['image'])
    if not m:
        no_strip.append(p['id']); continue
    page = int(m.group(1))
    strip = get_strip(page)
    if strip is None:
        no_strip.append(p['id']); continue
    runs = col_runs(strip)
    N = int(p.get('colors') or 0)
    if len(runs) > N and N > 0:
        mismatch.append((p['id'], N, len(runs)))
        p['colors'] = len(runs)
        N = len(runs)
    elif len(runs) < N or N == 0:
        # 粘连: 内容范围内等分 N 份
        sa = np.asarray(strip.convert('L'))
        colmn = sa.min(axis=0)
        nz = np.where(colmn < 243)[0]
        x0, x1 = (nz.min(), nz.max()) if len(nz) else (0, strip.width - 1)
        W = x1 - x0 + 1
        runs = [(int(x0 + i * W / N), int(x0 + (i + 1) * W / N)) for i in range(N)]
    base = p['image'].rsplit('-main', 1)[0].split('/')[-1]
    for i, (s, e) in enumerate(runs[:N], 1):
        sub = strip.crop((max(0, s - 5), 0, min(strip.width, e + 5), strip.height))
        out = to_canvas(sub)
        out.save(os.path.join(ROOT, 'public/uploads/quartz', f'{base}-c{i}.jpg'),
                 'JPEG', quality=85, optimize=True)
    # 清理超出 N 的旧文件 & 重建 gallery
    for i in range(N + 1, 40):
        f = os.path.join(ROOT, 'public/uploads/quartz', f'{base}-c{i}.jpg')
        if os.path.exists(f): os.remove(f)
    p['gallery'] = [f'/uploads/quartz/{base}-c{i}.jpg' for i in range(1, N + 1)]
    changed += 1

json.dump(db, open(os.path.join(ROOT, 'data/db.json'), 'w'), ensure_ascii=False, indent=2)
print(f'重生成 {changed} 款')
print('无配色行:', no_strip[:10])
print('色数修正:', mismatch[:10])
EOF_MARKER_UNUSED = None
