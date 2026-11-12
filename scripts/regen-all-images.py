#!/usr/bin/env python3
"""从两个目录 PPTX 提取原始高清产品图，统一为 3:4 竖版覆盖现有文件。
- 双机芯 (series=dual-movement): 主图 = slide 上面积最大的非背景竖版图; gallery = 全部颜色变体(按行优先排序)
- 石英 (series=quartz): 主图 = 对应 slide 上面积最大的原生竖版图（场景照），裁剪到 3:4
处理规则:
- RGBA 白底合成 + alpha 裁边 + 白底补齐到 3:4 (fit 92%)
- RGB 场景照: 顶部偏置裁剪到 3:4
输出统一 1200x1600 JPEG q85
"""
import json, re, os, sys, glob
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DM_PPTX = '/tmp/dm-pptx/dm-price'
QZ_PPTX = '/tmp/qz-pptx/qz'
OUT_W, OUT_H = 1200, 1600  # 3:4

db = json.load(open(os.path.join(ROOT, 'data/db.json')))

def slide_pics(base, n):
    """返回 slide n 的 [(media_name, cx, cy, off_x, off_y)]，EMU。"""
    xml = open(f'{base}/ppt/slides/slide{n}.xml').read()
    rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="\.\./media/([^"]+)"',
                           open(f'{base}/ppt/slides/_rels/slide{n}.xml.rels').read()))
    pics = []
    for m in re.finditer(r'<p:pic>.*?</p:pic>', xml, re.S):
        pic = m.group(0)
        rid = re.search(r'r:embed="(rId\d+)"', pic)
        if not rid: continue
        media = rels.get(rid.group(1))
        if not media: continue
        ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', pic)
        off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"', pic)
        cx, cy = (int(ext.group(1)), int(ext.group(2))) if ext else (0, 0)
        ox, oy = (int(off.group(1)), int(off.group(2))) if off else (0, 0)
        pics.append((media, cx, cy, ox, oy))
    return pics

def slide_texts(base, n):
    xml = open(f'{base}/ppt/slides/slide{n}.xml').read()
    return re.findall(r'<a:t>([^<]*)</a:t>', xml)

def load_media(base, name):
    return Image.open(f'{base}/ppt/media/{name}')

def finish_packshot(im):
    """RGBA 产品图 → 白底合成、裁边、白底补齐 3:4。"""
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    a = im.split()[3]
    bbox = a.point(lambda x: 255 if x > 8 else 0).getbbox()
    if bbox: im = im.crop(bbox)
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    out = Image.alpha_composite(bg, im).convert('RGB')
    return pad_34(out)

def pad_34(im):
    """白底补齐到 3:4，手表占 92%。"""
    w, h = im.size
    tw, th = OUT_W, OUT_H
    scale = min(tw * 0.92 / w, th * 0.92 / h)
    im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    canvas = Image.new('RGB', (tw, th), (255, 255, 255))
    canvas.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
    return canvas

def crop_34(im, top_bias=0.75):
    """RGB 场景照 → 裁剪到 3:4（偏顶部裁剪，保手表底部完整），再缩放到 1200x1600。"""
    w, h = im.size
    target = 3 / 4
    if w / h < target - 0.01:
        # 太窄：裁高度
        new_h = int(w / target)
        cut = h - new_h
        top = int(cut * top_bias)
        im = im.crop((0, top, w, top + new_h))
    elif w / h > target + 0.01:
        new_w = int(h * target)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    return im.resize((OUT_W, OUT_H), Image.LANCZOS)

def save(im, path):
    im.save(path, 'JPEG', quality=85, optimize=True, progressive=True)

report = {'dm_main': 0, 'dm_gal': 0, 'qz_main': 0, 'errors': []}

# ---------- 双机芯 ----------
dm_products = [p for p in db['products'] if p.get('series') == 'dual-movement']
dm_models = {p['model'] for p in dm_products}
n_slides = len(glob.glob(f'{DM_PPTX}/ppt/slides/slide*.xml'))
slide_model = {}
for n in range(1, n_slides + 1):
    tokens = [t.strip() for t in slide_texts(DM_PPTX, n)]
    # 只认在数据库里存在的型号 token（排除 MOQ 的 100/300 等）
    models = [t for t in tokens if t in dm_models]
    if models:
        slide_model.setdefault(models[0], []).append(n)
missing = dm_models - set(slide_model)
if missing:
    report['errors'].append(f'双机芯未匹配型号: {missing}')

for p in dm_products:
    model = p['model']
    slides = slide_model.get(model)
    if not slides:
        continue
    n = slides[0]
    pics = slide_pics(DM_PPTX, n)
    # 变体图: 竖版显示 (cy>cx*1.15)、非整页背景 (cx < 11M EMU)、非小图标 (cx > 1.2M EMU)
    variants = [x for x in pics if x[2] > x[1] * 1.15 and 1_200_000 < x[1] < 11_000_000]
    if not variants:
        # 特殊版式（多色合集/横排大图）：用最大的非背景图白底补齐做主图
        cands = [x for x in pics if x[1] < 11_000_000 and x[1] * x[2] > 5_000_000_000_000]
        if not cands:
            report['errors'].append(f'{model} slide{n} 无可用图')
            continue
        best = max(cands, key=lambda v: v[1] * v[2])
        im = load_media(DM_PPTX, best[0])
        if im.mode != 'RGB':
            bg2 = Image.new('RGBA', im.size, (255, 255, 255, 255))
            im = Image.alpha_composite(bg2, im.convert('RGBA')).convert('RGB')
        w, h = im.size
        scale = min(OUT_W * 0.94 / w, OUT_H * 0.94 / h)
        im2 = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        canvas = Image.new('RGB', (OUT_W, OUT_H), (255, 255, 255))
        canvas.paste(im2, ((OUT_W - im2.width) // 2, (OUT_H - im2.height) // 2))
        save(canvas, os.path.join(ROOT, 'public', p['image'].lstrip('/')))
        report['dm_main'] += 1
        report['errors'].append(f'{model} slide{n} 使用合集版式兜底')
        continue
    # 行优先排序 gallery
    def rowkey(v): return (round(v[4] / 500_000), v[3])
    variants_sorted = sorted(variants, key=rowkey)
    main_pic = max(variants, key=lambda v: v[1] * v[2])
    main_path = os.path.join(ROOT, 'public', p['image'].lstrip('/'))
    im = load_media(DM_PPTX, main_pic[0])
    save(finish_packshot(im), main_path)
    report['dm_main'] += 1
    # gallery：以 slide 变体为准，补齐或裁剪
    gal = list(p.get('gallery') or [])
    base_name = os.path.basename(p['image']).replace('-main.jpg', '')
    gal_dir = os.path.dirname(os.path.join(ROOT, 'public', p['image'].lstrip('/')))
    if len(variants_sorted) > len(gal):
        for i in range(len(gal), len(variants_sorted)):
            fname = f'/uploads/products/{base_name}-c{i+1}.jpg'
            gal.append(fname)
    elif len(variants_sorted) < len(gal):
        for fname in gal[len(variants_sorted):]:
            fp = os.path.join(ROOT, 'public', fname.lstrip('/'))
            if os.path.exists(fp): os.remove(fp)
        gal = gal[:len(variants_sorted)]
    for i, v in enumerate(variants_sorted):
        save(finish_packshot(load_media(DM_PPTX, v[0])),
             os.path.join(ROOT, 'public', gal[i].lstrip('/')))
        report['dm_gal'] += 1
    p['gallery'] = gal

# ---------- 石英主图 ----------
qz_products = [p for p in db['products'] if p.get('series') == 'quartz']
seen_page = {}
for p in qz_products:
    m = re.search(r'-p(\d+)-main', p['image'])
    if not m: continue
    page = int(m.group(1))
    model = p['model']
    try:
        texts = slide_texts(QZ_PPTX, page)
    except FileNotFoundError:
        report['errors'].append(f'石英 slide{page} 不存在')
        continue
    if not any(t.strip() == model for t in texts):
        report['errors'].append(f'石英 p{page} slide 文本无型号 {model}')
    pics = [x for x in slide_pics(QZ_PPTX, page) if x[1] < 11_000_000]  # 排除背景
    # 原生竖版优先
    portrait = []
    for v in pics:
        try:
            im = load_media(QZ_PPTX, v[0])
            if im.height > im.width * 1.2:
                portrait.append((v, im.size))
        except Exception as e:
            report['errors'].append(f'{model} 读图失败 {v[0]}: {e}')
    if not portrait:
        report['errors'].append(f'石英 p{page} 无竖版图')
        continue
    best, _ = max(portrait, key=lambda x: x[0][1] * x[0][2])
    im = load_media(QZ_PPTX, best[0])
    if im.mode != 'RGB':
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im.convert('RGBA')).convert('RGB')
    out = crop_34(im)
    save(out, os.path.join(ROOT, 'public', p['image'].lstrip('/')))
    report['qz_main'] += 1

print(json.dumps(report, ensure_ascii=False, indent=1))
json.dump(db, open(os.path.join(ROOT, 'data/db.json'), 'w'), ensure_ascii=False, indent=1)
print('db.json 已保存（gallery 变更）')
