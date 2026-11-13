const express = require('express');
const session = require('express-session');
const expressLayouts = require('express-ejs-layouts');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcryptjs');
const db = require('./lib/db');
const { t, langs } = require('./lib/i18n');
const { sendInquiryEmails } = require('./lib/mailer');
const { upload, pdfUpload, uploadMixed, deleteUpload } = require('./lib/upload');
const config = require('./config');

const app = express();

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(expressLayouts);
app.set('layout', 'admin/layout');
app.set('layout extractScripts', true);
app.set('layout extractStyles', true);

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Product images and user uploads are persisted via the single volume mounted at /app/data
const dataUploadsDir = path.join(__dirname, 'data', 'uploads');
fs.mkdirSync(dataUploadsDir, { recursive: true });
app.use('/uploads', express.static(dataUploadsDir));
// Seeded catalog images shipped with the repo
app.use('/uploads/products', express.static(path.join(__dirname, 'public', 'uploads', 'products')));

app.use(session({
  secret: config.sessionSecret,
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 1000 * 60 * 60 * 24 }
}));

// ---------- i18n & currency middleware ----------
app.use((req, res, next) => {
  const settings = db.getSettings();
  // language (multi-language ready: en / ru / ar with RTL)
  if (req.query.lang && langs.includes(req.query.lang)) req.session.lang = req.query.lang;
  const lang = req.session.lang || 'en';
  // currency (multi-currency display, prices stored in CNY)
  if (req.query.cur && settings.currency_rates && settings.currency_rates[req.query.cur]) req.session.cur = req.query.cur;
  const cur = req.session.cur || settings.currency_default || 'USD';
  const rate = (settings.currency_rates && settings.currency_rates[cur]) || 1;
  const symbol = (settings.currency_symbols && settings.currency_symbols[cur]) || '';
  res.locals.lang = lang;
  res.locals.langs = langs;
  res.locals.t = (key) => t(lang, key);
  res.locals.dir = lang === 'ar' ? 'rtl' : 'ltr';
  res.locals.currency = cur;
  res.locals.currencySymbol = symbol;
  res.locals.fmtPrice = (cny) => {
    const v = cny * rate;
    const digits = cur === 'CNY' ? 2 : (v >= 100 ? 1 : 2);
    return symbol + v.toFixed(digits);
  };
  res.locals.user = req.session.user || null;
  res.locals.success = req.session.success || null;
  res.locals.error = req.session.error || null;
  delete req.session.success;
  delete req.session.error;
  res.locals.whatsappLink = 'https://wa.me/' + String(settings.whatsapp || '').replace(/\D/g, '');
  next();
});

function requireAuth(req, res, next) {
  if (req.session && req.session.user) return next();
  req.session.error = 'Please login first';
  res.redirect('/admin/login');
}

function flash(req, type, msg) {
  req.session[type] = msg;
}

// ===================== PUBLIC FRONTEND =====================

app.get('/', (req, res) => {
  const settings = db.getSettings();
  const featured = db.getProducts().filter(p => p.series === 'dual-movement').slice(0, 8);
  const featuredQuartz = db.getProducts().filter(p => p.series === 'quartz').slice(0, 8);
  const data = {
    settings, banners: db.getBanners(), highlights: db.getHighlights(),
    factory: db.getFactory(), oem: db.getOEM(), featured, featuredQuartz, advantages: db.getAdvantages(),
    contact: db.getContact(), footer: db.getFooter()
  };
  const meta = db.getPage('home');
  res.render('public/index', { layout: 'public/layout', page: 'home', path: req.path, meta, ...data });
});

// Unified B2B catalog with series / movement / keyword filters
app.get('/products', (req, res) => {
  const settings = db.getSettings();
  const series = req.query.series || '';
  const movement = req.query.movement || '';
  const category = req.query.category || '';
  const q = (req.query.q || '').trim();
  let products = db.getProducts();
  if (series) products = products.filter(p => p.series === series);
  if (category) products = products.filter(p => (p.category || '') === category);
  if (movement) products = products.filter(p => (p.movement || '').toLowerCase().includes(movement.toLowerCase()));
  if (q) products = products.filter(p =>
    [p.model, p.name, p.title, p.description].join(' ').toLowerCase().includes(q.toLowerCase()));
  const data = {
    settings, products, filters: { series, movement, category, q },
    footer: db.getFooter()
  };
  const meta = db.getPage('products');
  res.render('public/products', { layout: 'public/layout', page: 'products', path: req.path, meta, ...data });
});

// Aliases for legacy / series landing pages
app.get('/dual-movement-watches', (req, res) => res.redirect('/products?series=dual-movement'));
app.get('/quartz-watches', (req, res) => res.redirect('/products?series=quartz'));

// Product detail with tier pricing & MOQ
app.get('/product/:id', (req, res) => {
  const settings = db.getSettings();
  const product = db.getProduct(req.params.id);
  if (!product || !product.active) return res.status(404).render('public/404', { layout: 'public/layout', path: req.path, settings, footer: db.getFooter(), meta: { title: 'Not Found', meta_description: '' }, page: '' });
  const related = db.getProducts().filter(p => p.series === product.series && p.id !== product.id).slice(0, 4);
  const meta = {
    title: `${product.model} ${product.name} | Wholesale & OEM - JOEFOX`,
    meta_description: `${product.name} (${product.model}) ${product.title || ''}. MOQ ${product.moq_mono || 100} pcs, tier FOB pricing, OEM/ODM supported. Contact JOEFOX watch factory for quotation.`
  };
  res.render('public/product-detail', {
    layout: 'public/layout', page: 'product', path: req.path, meta,
    settings, product, related, footer: db.getFooter()
  });
});

app.get('/our-factory', (req, res) => {
  const settings = db.getSettings();
  const data = { settings, factory: db.getFactory(), factoryPage: db.getFactoryPage(), advantages: db.getAdvantages(), footer: db.getFooter() };
  const meta = db.getPage('factory');
  res.render('public/our-factory', { layout: 'public/layout', page: 'factory', path: req.path, meta, ...data });
});

app.get('/oem-odm-service', (req, res) => {
  const settings = db.getSettings();
  const data = { settings, oem: db.getOEM(), footer: db.getFooter() };
  const meta = db.getPage('oem');
  res.render('public/oem-odm-service', { layout: 'public/layout', page: 'oem', path: req.path, meta, ...data });
});

app.get('/sample-request', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings, footer: db.getFooter(),
    products: db.getProducts(),
    preselect: req.query.product || ''
  };
  const meta = db.getPage('sample');
  res.render('public/sample-request', { layout: 'public/layout', page: 'sample', path: req.path, meta, ...data });
});

app.get('/contact', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings, contact: db.getContact(), footer: db.getFooter(),
    products: db.getProducts(), preselect: req.query.product || ''
  };
  const meta = db.getPage('contact');
  res.render('public/contact', { layout: 'public/layout', page: 'contact', path: req.path, meta, ...data });
});

// ---------- Inquiry / sample submission (shared) ----------
async function handleInquiry(req, res, type) {
  const settings = db.getSettings();
  const { name, company, country, email, phone, quantity, message, product_id } = req.body;
  if (!name || !email || !message) {
    flash(req, 'error', 'Name, email and message are required.');
    return res.redirect(req.headers.referer || '/contact');
  }
  const product = product_id ? db.getProduct(product_id) : null;
  const inquiry = db.addInquiry({
    type: type || 'inquiry',
    name, company: company || '', country: country || '',
    email, phone: phone || '', quantity: quantity || '',
    message,
    product_id: product ? product.id : null,
    product_model: product ? product.model : '',
    product_name: product ? product.name : ''
  });
  const mail = await sendInquiryEmails(settings, inquiry);
  db.updateInquiry(inquiry.id, { email_sent: mail.sent });
  flash(req, 'success', t(res.locals.lang, 'form.success'));
  res.redirect('/contact');
}

app.post('/inquiry', (req, res) => handleInquiry(req, res, 'inquiry'));
app.post('/sample-request', (req, res) => handleInquiry(req, res, 'sample'));

// ===================== SEO: SITEMAP & ROBOTS =====================

app.get('/sitemap.xml', (req, res) => {
  const base = (db.getSettings().site_url || '').replace(/\/$/, '');
  const urls = [
    { url: '/', changefreq: 'weekly', priority: '1.0' },
    { url: '/products', changefreq: 'weekly', priority: '0.9' },
    { url: '/products?series=dual-movement', changefreq: 'weekly', priority: '0.9' },
    { url: '/products?series=quartz', changefreq: 'weekly', priority: '0.8' },
    { url: '/our-factory', changefreq: 'monthly', priority: '0.8' },
    { url: '/oem-odm-service', changefreq: 'monthly', priority: '0.8' },
    { url: '/sample-request', changefreq: 'monthly', priority: '0.6' },
    { url: '/contact', changefreq: 'yearly', priority: '0.5' }
  ];
  db.getProducts().forEach(p => {
    urls.push({ url: '/product/' + p.id, changefreq: 'monthly', priority: '0.7' });
  });
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
  urls.forEach(p => {
    xml += `  <url><loc>${base}${p.url}</loc><changefreq>${p.changefreq}</changefreq><priority>${p.priority}</priority></url>\n`;
  });
  xml += '</urlset>';
  res.header('Content-Type', 'application/xml');
  res.send(xml);
});

app.get('/robots.txt', (req, res) => {
  const base = (db.getSettings().site_url || '').replace(/\/$/, '');
  res.type('text/plain');
  res.send(`User-agent: *\nAllow: /\n\nSitemap: ${base}/sitemap.xml\n`);
});

// ===================== CATALOG DOWNLOAD =====================

app.get('/download-catalog', (req, res) => {
  const pdf = db.getSettings().catalog_pdf;
  const filePath = pdf ? path.join(__dirname, 'data', pdf.replace(/^\//, '')) : null;
  if (!pdf || !filePath || !fs.existsSync(filePath)) {
    flash(req, 'error', 'Catalog is not available yet. Please contact us for the latest product catalog.');
    return res.redirect('/contact');
  }
  res.download(filePath, 'JOEFOX-Product-Catalog.pdf');
});

// ===================== ADMIN AUTH =====================

app.get('/admin/login', (req, res) => {
  if (req.session.user) return res.redirect('/admin');
  res.render('admin/login', { layout: false, title: 'Admin Login' });
});

app.post('/admin/login', async (req, res) => {
  const { username, password } = req.body;
  const admin = db.getAdminUser();
  if (username === admin.username && await bcrypt.compare(password, admin.passwordHash)) {
    req.session.user = { username };
    flash(req, 'success', 'Welcome to JOEFOX CMS');
    return res.redirect('/admin');
  }
  flash(req, 'error', 'Invalid username or password');
  res.redirect('/admin/login');
});

app.get('/admin/logout', (req, res) => {
  req.session.destroy(() => res.redirect('/admin/login'));
});

// ===================== ADMIN DASHBOARD =====================

app.get('/admin', requireAuth, (req, res) => {
  const inquiries = db.getInquiries();
  res.render('admin/dashboard', {
    page: 'dashboard', title: 'Dashboard',
    stats: {
      products: db.getAllProducts().length,
      activeProducts: db.getProducts().length,
      inquiries: inquiries.length,
      newInquiries: inquiries.filter(q => q.status === 'new').length,
      samples: inquiries.filter(q => q.type === 'sample').length
    },
    recent: inquiries.slice(0, 5)
  });
});

// ===================== SETTINGS =====================

app.get('/admin/settings', requireAuth, (req, res) => {
  res.render('admin/settings', { page: 'settings', title: 'Site Settings', settings: db.getSettings() });
});

app.post('/admin/settings', requireAuth, uploadMixed.fields([
  { name: 'logo_dark', maxCount: 1 },
  { name: 'logo_light', maxCount: 1 },
  { name: 'catalog_pdf', maxCount: 1 }
]), (req, res) => {
  const settings = db.getSettings();
  const updates = {
    site_title: req.body.site_title || settings.site_title,
    meta_description: req.body.meta_description || settings.meta_description,
    whatsapp: req.body.whatsapp || settings.whatsapp,
    email: req.body.email || settings.email,
    address: req.body.address || settings.address,
    site_url: req.body.site_url || settings.site_url,
    currency_default: req.body.currency_default || settings.currency_default,
    logo_invert: req.body.logo_invert === '1',
    smtp_host: req.body.smtp_host ?? settings.smtp_host,
    smtp_port: req.body.smtp_port ?? settings.smtp_port,
    smtp_user: req.body.smtp_user ?? settings.smtp_user,
    smtp_pass: req.body.smtp_pass || settings.smtp_pass,
    smtp_from: req.body.smtp_from ?? settings.smtp_from,
    smtp_secure: req.body.smtp_secure === '1' ? '1' : '0'
  };
  if (req.files?.logo_dark) { deleteUpload(settings.logo_dark); updates.logo_dark = '/uploads/' + req.files.logo_dark[0].filename; }
  if (req.files?.logo_light) { deleteUpload(settings.logo_light); updates.logo_light = '/uploads/' + req.files.logo_light[0].filename; }
  if (req.files?.catalog_pdf) { deleteUpload(settings.catalog_pdf); updates.catalog_pdf = '/uploads/' + req.files.catalog_pdf[0].filename; }
  if (req.body.remove_catalog === '1') { deleteUpload(settings.catalog_pdf); updates.catalog_pdf = null; }
  // currency rates & symbols (CNY is the base)
  try {
    const rates = JSON.parse(req.body.currency_rates || '{}');
    const symbols = JSON.parse(req.body.currency_symbols || '{}');
    updates.currency_rates = { ...settings.currency_rates, ...rates };
    updates.currency_symbols = { ...settings.currency_symbols, ...symbols };
  } catch (e) { /* keep old rates on parse error */ }
  db.updateSettings(updates);
  flash(req, 'success', 'Settings updated');
  res.redirect('/admin/settings');
});

// ===================== BANNERS =====================

app.get('/admin/banners', requireAuth, (req, res) => {
  res.render('admin/banners', { page: 'banners', title: 'Home Banners', banners: db.getBanners() });
});

app.post('/admin/banners', requireAuth, upload.fields([
  { name: 'image_0', maxCount: 1 },
  { name: 'image_1', maxCount: 1 }
]), (req, res) => {
  const banners = db.getBanners().map((b, idx) => {
    const key = `image_${idx}`;
    const image = req.files?.[key] ? '/uploads/' + req.files[key][0].filename : b.image;
    if (req.files?.[key]) deleteUpload(b.image);
    return {
      ...b,
      title: req.body[`title_${idx}`] || b.title,
      subtitle: req.body[`subtitle_${idx}`] || b.subtitle,
      description: req.body[`description_${idx}`] || b.description,
      image,
      cta_text: req.body[`cta_text_${idx}`] || b.cta_text,
      cta_link: req.body[`cta_link_${idx}`] || b.cta_link,
      active: req.body[`active_${idx}`] === 'on'
    };
  });
  db.updateBanners(banners);
  flash(req, 'success', 'Banners updated');
  res.redirect('/admin/banners');
});

// ===================== FACTORY =====================

app.get('/admin/factory', requireAuth, (req, res) => {
  res.render('admin/factory', { page: 'factory', title: 'Our Factory', factory: db.getFactory() });
});

app.post('/admin/factory', requireAuth, upload.single('image'), (req, res) => {
  const factory = db.getFactory();
  const updates = {
    title: req.body.title || factory.title,
    subtitle: req.body.subtitle || factory.subtitle,
    content: req.body.content || factory.content,
    stats: [
      { value: req.body.stat_value_0 || factory.stats[0].value, label: req.body.stat_label_0 || factory.stats[0].label },
      { value: req.body.stat_value_1 || factory.stats[1].value, label: req.body.stat_label_1 || factory.stats[1].label },
      { value: req.body.stat_value_2 || factory.stats[2].value, label: req.body.stat_label_2 || factory.stats[2].label },
      { value: req.body.stat_value_3 || factory.stats[3].value, label: req.body.stat_label_3 || factory.stats[3].label }
    ]
  };
  if (req.file) { deleteUpload(factory.image); updates.image = '/uploads/' + req.file.filename; }
  db.updateFactory(updates);
  flash(req, 'success', 'Factory section updated');
  res.redirect('/admin/factory');
});

// ===================== OEM =====================

app.get('/admin/oem', requireAuth, (req, res) => {
  res.render('admin/oem', { page: 'oem', title: 'OEM & ODM Service', oem: db.getOEM() });
});

app.post('/admin/oem', requireAuth, upload.any(), (req, res) => {
  const oem = db.getOEM();
  const svcImg = (i) => {
    const f = (req.files || []).find(x => x.fieldname === 'service_image_' + i);
    if (!f) return oem.services[i].image;
    if (oem.services[i].image) deleteUpload(oem.services[i].image);
    return '/uploads/' + f.filename;
  };
  const updates = {
    title: req.body.title || oem.title,
    subtitle: req.body.subtitle || oem.subtitle,
    content: req.body.content || oem.content,
    moq: req.body.moq || oem.moq,
    sample_lead: req.body.sample_lead || oem.sample_lead,
    mass_lead: req.body.mass_lead || oem.mass_lead,
    services: oem.services.map((s, i) => ({
      title: req.body['service_title_' + i] || s.title,
      desc: req.body['service_desc_' + i] || s.desc,
      image: svcImg(i)
    }))
  };
  const mainImg = (req.files || []).find(x => x.fieldname === 'image');
  if (mainImg) { deleteUpload(oem.image); updates.image = '/uploads/' + mainImg.filename; }
  db.updateOEM(updates);
  flash(req, 'success', 'OEM section updated');
  res.redirect('/admin/oem');
});

// ===================== PRODUCTS (extended B2B) =====================

app.get('/admin/products', requireAuth, (req, res) => {
  res.render('admin/products', { page: 'products', title: 'Product Catalog', products: db.getAllProducts() });
});

function parseProductBody(body, existing) {
  const tiers = [];
  for (let i = 0; i < 4; i++) {
    const qty = (body[`tier_qty_${i}`] || '').trim();
    const price = parseFloat(body[`tier_price_${i}`]);
    if (qty && !isNaN(price)) tiers.push({ qty, price });
  }
  const specs = {
    case_thickness: body.spec_thickness || '',
    case_diameter: body.spec_diameter || '',
    band_width: body.spec_band || '',
    weight: body.spec_weight || '',
    crystal: body.spec_crystal || 'Mineral Glass',
    case: body.spec_case || '',
    strap: body.spec_strap || ''
  };
  let colorOptions;
  if (body.color_options !== undefined) {
    try { colorOptions = JSON.parse(body.color_options); } catch (e) { colorOptions = null; }
  }
  return {
    title: body.title ?? (existing ? existing.title : ''),
    name: body.name ?? (existing ? existing.name : ''),
    model: body.model ?? (existing ? existing.model : ''),
    series: body.series || 'dual-movement',
    category: body.category !== undefined ? (body.category || '') : (existing ? (existing.category || '') : ''),
    movement: body.movement || '',
    japanese_option: body.japanese_option || '',
    moq_mono: body.moq_mono || '',
    moq_mixed: body.moq_mixed || '',
    colors: parseInt(body.colors) || 0,
    description: body.description ?? '',
    features: (body.features || '').split('\n').map(s => s.trim()).filter(Boolean),
    tiers, specs,
    gallery: (body.gallery || '').split('\n').map(s => s.trim()).filter(Boolean),
    ...(colorOptions ? { color_options: colorOptions } : {})
  };
}

app.post('/admin/products/add', requireAuth, upload.single('image'), (req, res) => {
  const fields = parseProductBody(req.body, null);
  const product = {
    ...fields,
    id: 'prod-' + Math.random().toString(36).slice(2, 8),
    image: req.file ? '/uploads/' + req.file.filename : '/assets/placeholders/product.svg',
    sort_order: parseInt(req.body.sort_order) || 999,
    active: true
  };
  db.addProduct(product);
  flash(req, 'success', 'Product added');
  res.redirect('/admin/products');
});

app.post('/admin/products/:id', requireAuth, upload.single('image'), (req, res) => {
  const existing = db.getProduct(req.params.id);
  if (!existing) { flash(req, 'error', 'Product not found'); return res.redirect('/admin/products'); }
  const updates = {
    ...parseProductBody(req.body, existing),
    sort_order: parseInt(req.body.sort_order) || existing.sort_order,
    active: req.body.active === 'on'
  };
  if (req.file) { deleteUpload(existing.image); updates.image = '/uploads/' + req.file.filename; }
  db.updateProduct(req.params.id, updates);
  flash(req, 'success', 'Product updated');
  res.redirect('/admin/products');
});

app.post('/admin/products/:id/delete', requireAuth, (req, res) => {
  const product = db.getProduct(req.params.id);
  if (product && product.image && product.image.startsWith('/uploads/') && !product.image.includes('/uploads/products/')) {
    deleteUpload(product.image);
  }
  db.hardDeleteProduct(req.params.id);
  flash(req, 'success', 'Product deleted');
  res.redirect('/admin/products');
});

// ===================== IMAGE TOOLS (rotate / crop orientation) =====================

const sharp = require('sharp');

const IMAGE_ROOTS = [
  { root: path.join(__dirname, 'data', 'uploads'), urlBase: '/uploads/' },                     // persisted volume
  { root: path.join(__dirname, 'public', 'uploads', 'products'), urlBase: '/uploads/products/' } // seeded catalog
];

function listImageDirs() {
  const dirs = new Set();
  IMAGE_ROOTS.forEach(({ root }) => {
    const walk = (dir, rel) => {
      let entries = [];
      try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
      dirs.add(rel);
      entries.filter(e => e.isDirectory()).forEach(e => walk(path.join(dir, e.name), rel ? rel + '/' + e.name : e.name));
    };
    walk(root, '');
  });
  return [...dirs].sort();
}

function listImagesInDir(dir) {
  const out = [];
  IMAGE_ROOTS.forEach(({ root, urlBase }) => {
    const abs = path.resolve(root, dir || '');
    if (!abs.startsWith(root)) return;
    let entries = [];
    try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch (e) { return; }
    entries.filter(e => e.isFile() && /\.(jpe?g|png|webp|gif)$/i.test(e.name)).forEach(e => {
      out.push({ rel: dir ? dir + '/' + e.name : e.name, url: urlBase + (dir ? dir + '/' + e.name : e.name) });
    });
  });
  return out.sort((a, b) => a.rel.localeCompare(b.rel));
}

app.get('/admin/image-tools', requireAuth, (req, res) => {
  const dir = req.query.dir || '';
  const images = listImagesInDir(dir).map(im => ({ ...im, url: im.url + '?v=' + Date.now() }));
  res.render('admin/image-tools', {
    page: 'image-tools', title: 'Image Tools',
    dirs: listImageDirs(), currentDir: dir, images
  });
});

app.post('/admin/image-tools', requireAuth, async (req, res) => {
  const { img, rotate, crop } = req.body;
  const rel = String(img || '').replace(/\\/g, '/');
  let file = null;
  for (const { root } of IMAGE_ROOTS) {
    const abs = path.resolve(root, '.' + '/' + rel);
    if (abs.startsWith(root) && fs.existsSync(abs)) { file = abs; break; }
  }
  if (!file) { flash(req, 'error', 'Image not found: ' + rel); return res.redirect('/admin/image-tools'); }
  try {
    const rot = parseInt(rotate) || 0;
    const meta = await sharp(file).metadata();
    let width = meta.width, height = meta.height;
    if (rot === 90 || rot === 270) { const tmp = width; width = height; height = tmp; }
    let pipeline = sharp(file);
    if (rot) pipeline = pipeline.rotate(rot);
    const aspects = { 'square': 1, 'portrait': 3 / 4, 'landscape': 4 / 3, 'wide': 16 / 10 };
    if (crop && aspects[crop]) {
      const ar = aspects[crop];
      let tw, th;
      if (width / height > ar) { th = height; tw = Math.round(height * ar); }
      else { tw = width; th = Math.round(width / ar); }
      pipeline = pipeline.resize({ width: tw, height: th, fit: 'cover', position: 'centre' });
    }
    const buf = await pipeline.toBuffer();
    fs.writeFileSync(file, buf);
    flash(req, 'success', `Image updated (${rel}${rot ? ', rotated ' + rot + '°' : ''}${crop ? ', cropped ' + crop : ''})`);
    res.redirect('/admin/image-tools?dir=' + encodeURIComponent(req.body.dir || ''));
  } catch (e) {
    console.error('Image tools error:', e.message);
    flash(req, 'error', 'Failed to update image: ' + e.message);
    res.redirect('/admin/image-tools?dir=' + encodeURIComponent(req.body.dir || ''));
  }
});

// ===================== INQUIRIES =====================

app.get('/admin/inquiries', requireAuth, (req, res) => {
  const status = req.query.status || '';
  const all = db.getInquiries();
  let inquiries = all;
  if (status) inquiries = inquiries.filter(q => q.status === status);
  const counts = {
    all: all.length,
    new: all.filter(q => q.status === 'new').length,
    contacted: all.filter(q => q.status === 'contacted').length,
    quoted: all.filter(q => q.status === 'quoted').length,
    archived: all.filter(q => q.status === 'archived').length
  };
  res.render('admin/inquiries', { page: 'inquiries', title: 'Inquiries & Samples', inquiries, status, counts });
});

app.post('/admin/inquiries/:id', requireAuth, (req, res) => {
  const inquiry = db.getInquiry(req.params.id);
  if (!inquiry) { flash(req, 'error', 'Inquiry not found'); return res.redirect('/admin/inquiries'); }
  const notes = inquiry.notes || [];
  if (req.body.note && req.body.note.trim()) {
    notes.unshift({ text: req.body.note.trim(), at: new Date().toISOString() });
  }
  db.updateInquiry(req.params.id, {
    status: req.body.status || inquiry.status,
    notes
  });
  flash(req, 'success', 'Inquiry updated');
  res.redirect('/admin/inquiries');
});

app.post('/admin/inquiries/:id/delete', requireAuth, (req, res) => {
  db.deleteInquiry(req.params.id);
  flash(req, 'success', 'Inquiry deleted');
  res.redirect('/admin/inquiries');
});

// ===================== FACTORY PAGE CONTENT (editable) =====================

function setByPath(obj, pathStr, value) {
  const parts = pathStr.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const k = parts[i];
    if (cur[k] === undefined || cur[k] === null) cur[k] = /^\d+$/.test(parts[i + 1]) ? [] : {};
    cur = cur[k];
  }
  cur[parts[parts.length - 1]] = value;
}

// Path-preserving upload into the persistent volume (bulk product image sync)
app.post('/admin/upload-image', requireAuth, upload.single('file'), (req, res) => {
  const rel = String(req.body.relpath || '').replace(/\\/g, '/').replace(/^\/+/, '').replace(/^uploads\//, '');
  if (!rel || rel.includes('..') || !/\.(jpe?g|png|gif|webp|ico|svg)$/i.test(rel)) {
    return res.status(400).json({ error: 'bad relpath' });
  }
  const dest = path.join(dataUploadsDir, rel);
  if (!dest.startsWith(dataUploadsDir)) return res.status(400).json({ error: 'bad relpath' });
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(req.file.path, dest);
  fs.unlinkSync(req.file.path);
  res.json({ ok: true, path: '/uploads/' + rel });
});

app.get('/admin/factory-page', requireAuth, (req, res) => {
  res.render('admin/factory-page', { page: 'factory-page', title: 'Factory Page Content', fp: db.getFactoryPage() || {} });
});

app.post('/admin/factory-page', requireAuth, upload.any(), (req, res) => {
  let fp = db.getFactoryPage() || {};
  fp = JSON.parse(JSON.stringify(fp));
  Object.keys(req.body).forEach(k => {
    if (k.startsWith('f_')) setByPath(fp, k.slice(2), req.body[k]);
  });
  (req.files || []).forEach(f => {
    if (f.fieldname.startsWith('img_')) setByPath(fp, f.fieldname.slice(4), '/uploads/' + f.filename);
  });
  db.updateFactoryPage(fp);
  flash(req, 'success', 'Factory page content updated');
  res.redirect('/admin/factory-page');
});

// ===================== ADVANTAGES =====================

app.get('/admin/advantages', requireAuth, (req, res) => {
  res.render('admin/advantages', { page: 'advantages', title: 'Our Advantages', advantages: db.getAdvantages() });
});

app.post('/admin/advantages', requireAuth, (req, res) => {
  const advantages = db.getAdvantages().map((a, idx) => ({
    ...a,
    title: req.body[`title_${idx}`] || a.title,
    desc: req.body[`desc_${idx}`] || a.desc,
    sort_order: parseInt(req.body[`sort_${idx}`]) || a.sort_order
  }));
  db.updateAdvantages(advantages);
  flash(req, 'success', 'Advantages updated');
  res.redirect('/admin/advantages');
});

// ===================== PAGES (SEO META) =====================

app.get('/admin/pages', requireAuth, (req, res) => {
  res.render('admin/pages', { page: 'pages', title: 'SEO / Page Meta', pages: db.getPages() });
});

app.post('/admin/pages', requireAuth, (req, res) => {
  const keys = ['home', 'factory', 'oem', 'quartz', 'contact', 'dual', 'products', 'sample'];
  const updates = {};
  keys.forEach(k => {
    if (req.body[`title_${k}`] !== undefined) {
      updates[k] = {
        title: req.body[`title_${k}`] || '',
        meta_description: req.body[`desc_${k}`] || ''
      };
    }
  });
  db.updatePages(updates);
  flash(req, 'success', 'Page SEO updated');
  res.redirect('/admin/pages');
});

// ===================== HIGHLIGHTS =====================

app.get('/admin/highlights', requireAuth, (req, res) => {
  res.render('admin/highlights', { page: 'highlights', title: 'Home Highlights', highlights: db.getHighlights() });
});

app.post('/admin/highlights', requireAuth, (req, res) => {
  const highlights = db.getHighlights().map((h, idx) => ({
    ...h,
    icon: req.body[`icon_${idx}`] || h.icon,
    title: req.body[`title_${idx}`] || h.title,
    desc: req.body[`desc_${idx}`] || h.desc,
    sort_order: parseInt(req.body[`sort_${idx}`]) || h.sort_order
  }));
  db.updateHighlights(highlights);
  flash(req, 'success', 'Highlights updated');
  res.redirect('/admin/highlights');
});

// ===================== CONTACT =====================

app.get('/admin/contact', requireAuth, (req, res) => {
  res.render('admin/contact', { page: 'contact', title: 'Contact Us', contact: db.getContact() });
});

app.post('/admin/contact', requireAuth, (req, res) => {
  db.updateContact({
    title: req.body.title,
    subtitle: req.body.subtitle,
    content: req.body.content
  });
  flash(req, 'success', 'Contact section updated');
  res.redirect('/admin/contact');
});

// ===================== ACCOUNT =====================

app.get('/admin/account', requireAuth, (req, res) => {
  res.render('admin/account', { page: 'account', title: 'Account Settings', settings: db.getSettings() });
});

app.post('/admin/account', requireAuth, async (req, res) => {
  const { username, password, password_confirm } = req.body;
  if (!username) {
    flash(req, 'error', 'Username is required');
    return res.redirect('/admin/account');
  }
  if (password) {
    if (password !== password_confirm) {
      flash(req, 'error', 'Passwords do not match');
      return res.redirect('/admin/account');
    }
    const hash = await bcrypt.hash(password, 10);
    db.updateAdminPassword(username, hash);
  } else {
    const settings = db.getSettings();
    db.updateAdminPassword(username, settings.admin_password_hash);
  }
  flash(req, 'success', 'Account updated');
  res.redirect('/admin/account');
});

// ===================== ERROR HANDLING =====================

app.use((req, res) => {
  if (req.path.startsWith('/admin')) return res.status(404).send('Not found');
  res.status(404).render('public/404', {
    layout: 'public/layout', path: req.path, settings: db.getSettings(),
    footer: db.getFooter(), meta: { title: 'Page Not Found', meta_description: '' }, page: ''
  });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  if (req.path.startsWith('/admin')) {
    flash(req, 'error', err.message || 'Something went wrong');
    return res.redirect(req.headers.referer || '/admin');
  }
  res.status(500).send('Server error');
});

app.listen(config.port, () => {
  console.log(`JOEFOX B2B site running at http://localhost:${config.port}`);
  console.log(`Admin panel at http://localhost:${config.port}/admin`);
});
