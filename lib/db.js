const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const config = require('../config');

const DB_PATH = path.join(__dirname, '..', 'data', 'db.json');

function getDefaultData() {
  const hash = bcrypt.hashSync(config.admin.defaultPassword, 10);
  return {
    settings: {
      site_title: 'JOEFOX Watch Factory',
      meta_description: 'JOEFOX is a professional watch manufacturer in China offering quartz watch wholesale and OEM/ODM custom manufacturing service.',
      logo_dark: null,
      logo_light: null,
      logo_invert: true,
      whatsapp: '+86 15360561168',
      email: 'joefoxwatch.winnie@gmail.com',
      address: 'GUANGZHOU GUANGDONG CHINA',
      site_url: 'https://www.joefoxwatchofficial.com',
      catalog_pdf: null,
      admin_username: config.admin.defaultUsername,
      admin_password_hash: hash
    },
    banners: [
      {
        id: 'banner-1',
        title: 'Quartz Watches Bulk Wholesale',
        subtitle: '石英手表批量批发',
        description: 'Premium quartz timepieces for global distributors, retailers and gift brands. Factory-direct pricing with reliable volume supply.',
        image: '/assets/placeholders/banner-1.svg',
        cta_text: 'Inquire Now',
        cta_link: '/contact',
        sort_order: 1,
        active: true
      },
      {
        id: 'banner-2',
        title: 'Watch OEM & ODM Custom Manufacturing Service',
        subtitle: '手表 OEM&ODM 定制代工服务',
        description: 'Custom dials, logo engraving, appearance modification and full private-label solutions backed by 17 years of watchmaking expertise.',
        image: '/assets/placeholders/banner-2.svg',
        cta_text: 'Inquire Now',
        cta_link: '/oem-odm-service',
        sort_order: 2,
        active: true
      }
    ],
    factory: {
      title: 'Our Factory',
      subtitle: 'Trusted Quality, Direct From Our Factory',
      content: 'JOEFOX designs and manufactures watches in our own facilities in Guangzhou, China. We serve global importers, wholesalers, retailers and brand distributors with stable supply, strict quality control and flexible OEM/ODM programs.',
      image: '/assets/placeholders/factory.svg',
      stats: [
        { value: '17+', label: 'Years Experience' },
        { value: '200K+', label: 'Annual Output' },
        { value: '80+', label: 'Team Members' },
        { value: '2,400m²', label: 'Facility' }
      ]
    },
    oem: {
      title: 'OEM & ODM Service',
      subtitle: 'Your Brand, Our Factory',
      content: 'Custom dial, Logo printing, color matching & dial texture customization.',
      moq: '300 pcs',
      sample_lead: '30 days',
      mass_lead: '20-30 days',
      image: null,
      services: [
        { title: 'Custom Dial', desc: 'Logo printing, color matching and dial texture customization.' },
        { title: 'Logo Engraving', desc: 'Case back, buckle and crown laser engraving with your brand.' },
        { title: 'Appearance Modification', desc: 'Case shape, strap material, hands and indexes adjustment.' },
        { title: 'Private Label Packaging', desc: 'Custom boxes, pouches and instruction manuals under your brand.' }
      ]
    },
    products: [
      {
        id: 'prod-1',
        title: 'Minimalist Quartz Dress Watch',
        model: 'JF-Q001',
        movement: 'Japanese Quartz',
        moq: '100 pcs',
        description: 'Slim case, clean dial, leather strap option. Ideal for corporate gifts and retail programs.',
        image: '/assets/placeholders/product.svg',
        sort_order: 1,
        active: true
      },
      {
        id: 'prod-2',
        title: 'Stainless Steel Business Watch',
        model: 'JF-Q002',
        movement: 'Japanese Quartz',
        moq: '100 pcs',
        description: 'Brushed steel case and bracelet, sapphire-coated glass, water-resistant construction.',
        image: '/assets/placeholders/product.svg',
        sort_order: 2,
        active: true
      },
      {
        id: 'prod-3',
        title: 'Chronograph Sport Watch',
        model: 'JF-Q003',
        movement: 'Japanese Quartz',
        moq: '100 pcs',
        description: 'Multi-function chronograph dial with date window and steel or leather strap options.',
        image: '/assets/placeholders/product.svg',
        sort_order: 3,
        active: true
      },
      {
        id: 'prod-4',
        title: 'Dual Display Casual Watch',
        model: 'JF-Q004',
        movement: 'Japanese Quartz',
        moq: '100 pcs',
        description: 'Analog-digital dual display with alarm and backlight, suitable for outdoor and youth markets.',
        image: '/assets/placeholders/product.svg',
        sort_order: 4,
        active: true
      }
    ],
    advantages: [
      { id: 'adv-1', title: '17 Years Watch Manufacturing Experience', desc: 'Deep expertise from movement sourcing to final assembly and export.', sort_order: 1 },
      { id: 'adv-2', title: 'Fast Sample Production Within 30 Days', desc: 'Bulk order lead time 20-30 days, keeping your time-to-market short.', sort_order: 2 },
      { id: 'adv-3', title: 'Strict Multi-stage Quality Inspection', desc: 'Incoming, in-process and final QC ensure every unit meets export standards.', sort_order: 3 },
      { id: 'adv-4', title: 'Stable Supply of Japanese Movements', desc: 'Reliable sourcing of proven Japanese movements for accuracy and longevity.', sort_order: 4 },
      { id: 'adv-5', title: 'One-stop Professional OEM Solution', desc: 'Design, sampling, production and logistics handled by a single team.', sort_order: 5 }
    ],
    pages: {
      home: { title: 'JOEFOX Watch Factory | Quartz Watch Wholesale & OEM/ODM', meta_description: 'JOEFOX is a China-based watch manufacturer offering quartz watch bulk wholesale and OEM/ODM custom manufacturing for global importers, wholesalers and retailers.' },
      factory: { title: 'Our Factory | JOEFOX Watch Manufacturer in China', meta_description: '17 years of watch manufacturing experience. Discover JOEFOX factory capabilities, production capacity and strict quality control.' },
      oem: { title: 'OEM & ODM Service | Custom Watch Manufacturing - JOEFOX', meta_description: 'Private label watch manufacturing: custom dial, logo engraving, MOQ 300 pcs, 7-day sampling and 15-20 days mass production lead time.' },
      quartz: { title: 'Quartz Watches Wholesale | JOEFOX B2B Catalog', meta_description: 'Wholesale quartz watches for global distributors and retailers. Japanese movement, IP68 waterproof, OEM/ODM supported.' },
      contact: { title: 'Contact Us | JOEFOX Watch Factory', meta_description: 'Get catalog, quotation and sample information via WhatsApp or email. Start your watch wholesale or OEM project with JOEFOX.' }
    },
    highlights: [
      { id: 'hl-1', icon: 'shipping', title: 'Worldwide Fast Shipping', desc: 'Ship to US, UK, EU and over 100 countries. Discount available for orders over $50', sort_order: 1 },
      { id: 'hl-2', icon: 'return', title: '30-Day Return Policy', desc: 'Full refund support within 30 days if you are not satisfied', sort_order: 2 },
      { id: 'hl-3', icon: 'water', title: 'IP68 Water Resistant', desc: '30m waterproof, suitable for daily shower and swimming', sort_order: 3 },
      { id: 'hl-4', icon: 'movement', title: 'Japanese Quartz Movement', desc: 'Precise timekeeping, battery life lasts 2-3 years, stable performance', sort_order: 4 }
    ],
    contact: {
      title: 'Contact Us',
      subtitle: 'Start Cooperation With Us',
      content: 'Get catalog, quotation and sample information via WhatsApp or email quickly.'
    },
    footer: {
      copyright: '© 2026 JOEFOX Watch Co., Ltd. All rights reserved.'
    }
  };
}

function ensureDb() {
  if (!fs.existsSync(DB_PATH)) {
    const dir = path.dirname(DB_PATH);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(DB_PATH, JSON.stringify(getDefaultData(), null, 2));
  }
}

function read() {
  ensureDb();
  return JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
}

function write(data) {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
}

function update(fn) {
  const data = read();
  const result = fn(data);
  write(data);
  return result !== undefined ? result : data;
}

module.exports = {
  // Settings
  getSettings() { return read().settings; },
  updateSettings(settings) {
    return update(data => {
      data.settings = { ...data.settings, ...settings };
      return data.settings;
    });
  },

  // Banners
  getBanners() { return read().banners; },
  updateBanners(banners) {
    return update(data => {
      data.banners = banners;
      return data.banners;
    });
  },

  // Factory
  getFactory() { return read().factory; },
  updateFactory(factory) {
    return update(data => {
      data.factory = { ...data.factory, ...factory };
      return data.factory;
    });
  },

  // OEM
  getOEM() { return read().oem; },
  updateOEM(oem) {
    return update(data => {
      data.oem = { ...data.oem, ...oem };
      return data.oem;
    });
  },

  // Products
  getProducts() { return read().products.filter(p => p.active).sort((a,b) => a.sort_order - b.sort_order); },
  getAllProducts() { return read().products.sort((a,b) => a.sort_order - b.sort_order); },
  getProduct(id) { return read().products.find(p => p.id === id); },
  addProduct(product) {
    return update(data => {
      const id = 'prod-' + uuidv4().split('-')[0];
      const newProduct = {
        id,
        title: product.title || 'New Quartz Watch',
        model: product.model || '',
        movement: product.movement || 'Japanese Quartz',
        moq: product.moq || '100 pcs',
        description: product.description || '',
        image: product.image || '/assets/placeholders/product.svg',
        sort_order: product.sort_order || data.products.length + 1,
        active: true
      };
      data.products.push(newProduct);
      return newProduct;
    });
  },
  updateProduct(id, updates) {
    return update(data => {
      const idx = data.products.findIndex(p => p.id === id);
      if (idx === -1) return null;
      data.products[idx] = { ...data.products[idx], ...updates };
      return data.products[idx];
    });
  },
  deleteProduct(id) {
    return update(data => {
      const idx = data.products.findIndex(p => p.id === id);
      if (idx === -1) return false;
      data.products[idx].active = false;
      return true;
    });
  },
  hardDeleteProduct(id) {
    return update(data => {
      const idx = data.products.findIndex(p => p.id === id);
      if (idx === -1) return false;
      data.products.splice(idx, 1);
      return true;
    });
  },

  // Advantages
  getAdvantages() { return read().advantages.sort((a,b) => a.sort_order - b.sort_order); },
  updateAdvantages(advantages) {
    return update(data => {
      data.advantages = advantages;
      return data.advantages;
    });
  },

  // Pages (per-page SEO meta)
  getPages() { return read().pages; },
  getPage(key) { return read().pages[key] || { title: 'JOEFOX', meta_description: '' }; },
  updatePages(pages) {
    return update(data => {
      data.pages = { ...data.pages, ...pages };
      return data.pages;
    });
  },

  // Highlights (home 4-column core advantages)
  getHighlights() { return read().highlights.sort((a,b) => a.sort_order - b.sort_order); },
  updateHighlights(highlights) {
    return update(data => {
      data.highlights = highlights;
      return data.highlights;
    });
  },

  // Contact
  getContact() { return read().contact; },
  updateContact(contact) {
    return update(data => {
      data.contact = { ...data.contact, ...contact };
      return data.contact;
    });
  },

  // Footer
  getFooter() { return read().footer; },
  updateFooter(footer) {
    return update(data => {
      data.footer = { ...data.footer, ...footer };
      return data.footer;
    });
  },

  // Auth
  getAdminUser() { return { username: read().settings.admin_username, passwordHash: read().settings.admin_password_hash }; },
  updateAdminPassword(username, passwordHash) {
    return update(data => {
      data.settings.admin_username = username;
      data.settings.admin_password_hash = passwordHash;
      return true;
    });
  },

  // Raw
  getRaw() { return read(); }
};
