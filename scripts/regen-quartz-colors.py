# 从 price-QuartzWatches Catalog.pdf 高清重做石英表配色图 (v2)
# 策略: zoom 6 渲染色条区域(y 856-1106pt) → 剔除底部横贯装饰条(row_frac>0.9)
#   → 按列空白自动分割色块; 若粘连(run数 < colors)则在内容范围内按 colors 等分;
#   若 run数 > colors 则以目录实际为准(修正 colors)。
#   最后白边裁剪、覆盖保存, 并同步 db.json 的 colors/gallery。
import json, re, os
import pymupdf
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = '/Users/cc/Desktop/cc/目录（更新中）/【JOEFOX】price-QuartzWatches Catalog.pdf'
Z = 6
Y0, Y1 = 856, 1106

db = json.load(open(os.path.join(ROOT, 'data/db.json')))
qz = [p for p in db['products'] if p.get('series') == 'quartz']
pdf = pymupdf.open(PDF)

pagecache = {}
def analyze(page):
    """返回 (分段列表[(x0,x1)], 条带图)。粘连时返回 None 表示需等分。"""
    if page in pagecache:
        return pagecache[page]
    pg = pdf[page - 1]
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(Z, Z), alpha=False)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    strip = img.crop((0, int(Y0 * Z), img.width, int(Y1 * Z)))
    a = np.asarray(strip.convert('L'))
    row_frac = (a < 243).mean(axis=1)
    br = np.where(row_frac > 0.9)[0]
    if len(br):
        strip = strip.crop((0, 0, strip.width, int(br.min())))
        a = a[:br.min()]
    col_min = a.min(axis=0)
    white = col_min > 242
    runs, start = [], None
    for x, w in enumerate(white):
        if not w and start is None:
            start = x
        elif w and start is not None:
            runs.append((start, x)); start = None
    if start is not None:
        runs.append((start, len(white)))
    runs = [(s, e) for s, e in runs if e - s > 30]
    res = (runs, strip)
    pagecache[page] = res
    return res

def crop_swatch(strip, s, e, out_path):
    sub = strip.crop((max(0, s - 4), 0, min(strip.width, e + 4), strip.height))
    sa = np.asarray(sub.convert('L'))
    rows = np.where(sa.min(axis=1) < 243)[0]
    if len(rows):
        sub = sub.crop((0, max(0, rows.min() - 4), sub.width, min(sub.height, rows.max() + 5)))
    sub.save(out_path, 'JPEG', quality=85, optimize=True)

changed = 0
total = 0
fixed_colors = []
for p in qz:
    m = re.search(r'-p(\d+)-main', p['image'])
    if not m:
        print('跳过(无页码):', p['id']); continue
    page = int(m.group(1))
    runs, strip = analyze(page)
    N = p.get('colors') or 0
    base = p['image'].rsplit('-main', 1)[0].split('/')[-1]
    model_dir = os.path.join(ROOT, 'public/uploads/quartz')

    if len(runs) >= N and N > 0 and len(runs) == N:
        bounds = runs
    elif len(runs) > N:
        bounds = runs
        fixed_colors.append((p['id'], N, len(runs)))
        p['colors'] = len(runs)
    else:
        # 粘连或无 run: 内容范围等分
        a = np.asarray(strip.convert('L'))
        col_mean = a.mean(axis=0)
        xs = np.where(col_mean < 250)[0]
        if len(xs) == 0:
            print('跳过(空白页):', p['id']); continue
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        w = (x1 - x0) / N
        bounds = [(int(x0 + i * w), int(x0 + (i + 1) * w)) for i in range(N)]

    gallery = []
    for i, (s, e) in enumerate(bounds, 1):
        out = os.path.join(model_dir, f'{base}-c{i}.jpg')
        crop_swatch(strip, s, e, out)
        gallery.append(f'/uploads/quartz/{base}-c{i}.jpg')
        total += 1
    # 清理多余旧图
    for f in os.listdir(model_dir):
        mm = re.match(re.escape(base) + r'-c(\d+)\.jpg$', f)
        if mm and int(mm.group(1)) > len(bounds):
            os.remove(os.path.join(model_dir, f))
    p['gallery'] = gallery
    changed += 1

json.dump(db, open(os.path.join(ROOT, 'data/db.json'), 'w'), ensure_ascii=False, indent=1)
print(f'更新 {changed} 款 / {total} 张配色图')
print(f'色数修正(以目录为准): {fixed_colors}')
