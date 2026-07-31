const express = require('express');
const session = require('express-session');
const expressLayouts = require('express-ejs-layouts');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcryptjs');
const db = require('./lib/db');
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

app.use(session({
  secret: config.sessionSecret,
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 1000 * 60 * 60 * 24 } // 24 hours
}));

app.use((req, res, next) => {
  res.locals.user = req.session.user || null;
  res.locals.success = req.session.success || null;
  res.locals.error = req.session.error || null;
  delete req.session.success;
  delete req.session.error;
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
  const data = {
    settings,
    banners: db.getBanners(),
    highlights: db.getHighlights(),
    factory: db.getFactory(),
    oem: db.getOEM(),
    products: db.getProducts(),
    advantages: db.getAdvantages(),
    contact: db.getContact(),
    footer: db.getFooter()
  };
  const meta = db.getPage('home');
  res.render('public/index', { layout: 'public/layout', page: 'home', path: req.path, meta, ...data });
});

app.get('/our-factory', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings,
    factory: db.getFactory(),
    advantages: db.getAdvantages(),
    footer: db.getFooter()
  };
  const meta = db.getPage('factory');
  res.render('public/our-factory', { layout: 'public/layout', page: 'factory', path: req.path, meta, ...data });
});

app.get('/oem-odm-service', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings,
    oem: db.getOEM(),
    footer: db.getFooter()
  };
  const meta = db.getPage('oem');
  res.render('public/oem-odm-service', { layout: 'public/layout', page: 'oem', path: req.path, meta, ...data });
});

app.get('/quartz-watches', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings,
    products: db.getAllProducts().filter(p => p.active),
    footer: db.getFooter()
  };
  const meta = db.getPage('quartz');
  res.render('public/quartz-watches', { layout: 'public/layout', page: 'quartz', path: req.path, meta, ...data });
});

app.get('/contact', (req, res) => {
  const settings = db.getSettings();
  const data = {
    settings,
    contact: db.getContact(),
    footer: db.getFooter()
  };
  const meta = db.getPage('contact');
  res.render('public/contact', { layout: 'public/layout', page: 'contact', path: req.path, meta, ...data });
});

// ===================== SEO: SITEMAP & ROBOTS =====================

app.get('/sitemap.xml', (req, res) => {
  const base = (db.getSettings().site_url || '').replace(/\/$/, '');
  const pages = [
    { url: '/', changefreq: 'weekly', priority: '1.0' },
    { url: '/our-factory', changefreq: 'monthly', priority: '0.8' },
    { url: '/oem-odm-service', changefreq: 'monthly', priority: '0.8' },
    { url: '/quartz-watches', changefreq: 'weekly', priority: '0.9' },
    { url: '/contact', changefreq: 'yearly', priority: '0.5' }
  ];
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
  pages.forEach(p => {
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
  res.render('admin/dashboard', { page: 'dashboard', title: 'Dashboard' });
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
    logo_invert: req.body.logo_invert === '1'
  };

  if (req.files.logo_dark) {
    deleteUpload(settings.logo_dark);
    updates.logo_dark = '/uploads/' + req.files.logo_dark[0].filename;
  }
  if (req.files.logo_light) {
    deleteUpload(settings.logo_light);
    updates.logo_light = '/uploads/' + req.files.logo_light[0].filename;
  }
  if (req.files.catalog_pdf) {
    deleteUpload(settings.catalog_pdf);
    updates.catalog_pdf = '/uploads/' + req.files.catalog_pdf[0].filename;
  }
  if (req.body.remove_catalog === '1') {
    deleteUpload(settings.catalog_pdf);
    updates.catalog_pdf = null;
  }

  db.updateSettings(updates);
  flash(req, 'success', 'Settings updated');
  res.redirect('/admin/settings');
});

// ===================== CATALOG DOWNLOAD =====================

app.get('/download-catalog', (req, res) => {
  const pdf = db.getSettings().catalog_pdf;
  const filePath = pdf ? path.join(__dirname, 'public', pdf.replace(/^\//, '')) : null;
  if (!pdf || !filePath || !fs.existsSync(filePath)) {
    flash(req, 'error', 'Catalog is not available yet. Please contact us for the latest product catalog.');
    return res.redirect('/contact');
  }
  res.download(filePath, 'JOEFOX-Product-Catalog.pdf');
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
    const image = req.files[key] ? '/uploads/' + req.files[key][0].filename : b.image;
    if (req.files[key]) deleteUpload(b.image);
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
  if (req.file) {
    deleteUpload(factory.image);
    updates.image = '/uploads/' + req.file.filename;
  }
  db.updateFactory(updates);
  flash(req, 'success', 'Factory section updated');
  res.redirect('/admin/factory');
});

// ===================== OEM =====================

app.get('/admin/oem', requireAuth, (req, res) => {
  res.render('admin/oem', { page: 'oem', title: 'OEM & ODM Service', oem: db.getOEM() });
});

app.post('/admin/oem', requireAuth, upload.single('image'), (req, res) => {
  const oem = db.getOEM();
  const updates = {
    title: req.body.title || oem.title,
    subtitle: req.body.subtitle || oem.subtitle,
    content: req.body.content || oem.content,
    moq: req.body.moq || oem.moq,
    sample_lead: req.body.sample_lead || oem.sample_lead,
    mass_lead: req.body.mass_lead || oem.mass_lead,
    services: [
      { title: req.body.service_title_0 || oem.services[0].title, desc: req.body.service_desc_0 || oem.services[0].desc },
      { title: req.body.service_title_1 || oem.services[1].title, desc: req.body.service_desc_1 || oem.services[1].desc },
      { title: req.body.service_title_2 || oem.services[2].title, desc: req.body.service_desc_2 || oem.services[2].desc },
      { title: req.body.service_title_3 || oem.services[3].title, desc: req.body.service_desc_3 || oem.services[3].desc }
    ]
  };
  if (req.file) {
    deleteUpload(oem.image);
    updates.image = '/uploads/' + req.file.filename;
  }
  db.updateOEM(updates);
  flash(req, 'success', 'OEM section updated');
  res.redirect('/admin/oem');
});

// ===================== PRODUCTS =====================

app.get('/admin/products', requireAuth, (req, res) => {
  res.render('admin/products', { page: 'products', title: 'Quartz Watches', products: db.getAllProducts() });
});

app.post('/admin/products/add', requireAuth, upload.single('image'), (req, res) => {
  const product = {
    title: req.body.title,
    model: req.body.model,
    movement: req.body.movement,
    moq: req.body.moq,
    description: req.body.description,
    sort_order: parseInt(req.body.sort_order) || 0,
    image: req.file ? '/uploads/' + req.file.filename : null
  };
  db.addProduct(product);
  flash(req, 'success', 'Product added');
  res.redirect('/admin/products');
});

app.post('/admin/products/:id', requireAuth, upload.single('image'), (req, res) => {
  const existing = db.getProduct(req.params.id);
  if (!existing) {
    flash(req, 'error', 'Product not found');
    return res.redirect('/admin/products');
  }
  const updates = {
    title: req.body.title || existing.title,
    model: req.body.model !== undefined ? req.body.model : existing.model,
    movement: req.body.movement || existing.movement,
    moq: req.body.moq || existing.moq,
    description: req.body.description !== undefined ? req.body.description : existing.description,
    sort_order: parseInt(req.body.sort_order) || existing.sort_order,
    active: req.body.active === 'on'
  };
  if (req.file) {
    deleteUpload(existing.image);
    updates.image = '/uploads/' + req.file.filename;
  }
  db.updateProduct(req.params.id, updates);
  flash(req, 'success', 'Product updated');
  res.redirect('/admin/products');
});

app.post('/admin/products/:id/delete', requireAuth, (req, res) => {
  const product = db.getProduct(req.params.id);
  if (product && product.image) deleteUpload(product.image);
  db.hardDeleteProduct(req.params.id);
  flash(req, 'success', 'Product deleted');
  res.redirect('/admin/products');
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
  const keys = ['home', 'factory', 'oem', 'quartz', 'contact'];
  const updates = {};
  keys.forEach(k => {
    updates[k] = {
      title: req.body[`title_${k}`] || '',
      meta_description: req.body[`desc_${k}`] || ''
    };
  });
  db.updatePages(updates);
  flash(req, 'success', 'Page SEO updated');
  res.redirect('/admin/pages');
});

// ===================== HIGHLIGHTS (HOME 4-COL) =====================

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

app.use((err, req, res, next) => {
  console.error(err.stack);
  if (req.path.startsWith('/admin')) {
    flash(req, 'error', err.message || 'Something went wrong');
    return res.redirect(req.headers.referer || '/admin');
  }
  res.status(500).send('Server error');
});

app.listen(config.port, () => {
  console.log(`JOEFOX CMS running at http://localhost:${config.port}`);
  console.log(`Admin panel at http://localhost:${config.port}/admin`);
});
