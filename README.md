# JOEFOX B2B Watch Factory Website — Multi-Page CMS

A full-stack **English B2B** website for the JOEFOX watch brand, built as a Node.js + Express + EJS app with a built-in admin panel. Factory-wholesale positioning (no retail/shopping-cart features); every button is an **Inquiry** CTA (WhatsApp / email), images are upload-slot placeholders until you add them.

## Live Links (local dev)

- **Public website:** http://localhost:3000/
- **Admin panel:** http://localhost:3000/admin
- **Admin account:** `admin` / `joefox2026`
- **XML sitemap:** http://localhost:3000/sitemap.xml
- **robots.txt:** http://localhost:3000/robots.txt

## Pages (independent routes, not single-page scroll)

| Route | Page | Editable SEO |
|-------|------|--------------|
| `/` | Home | ✅ |
| `/our-factory` | Our Factory | ✅ |
| `/oem-odm-service` | OEM & ODM Service | ✅ |
| `/quartz-watches` | Quartz Watches | ✅ |
| `/contact` | Contact Us | ✅ |

Every page has its own `<title>` and meta description (edit in **Admin → SEO / Page Meta**), a canonical link, Open Graph tags, and Organization JSON-LD for Google indexing. `sitemap.xml` is generated automatically from these routes using your domain.

## Run locally

```bash
cd joefox-cms
npm install
npm start            # or: npm run dev  (auto-reload)
# open http://localhost:3000/
```

> The managed runtime used during development points `NODE_PATH` at a shared
> `node_modules`. On a normal machine `npm install` puts dependencies in the
> project and `npm start` just works.

## Admin — what you can edit yourself (no code)

1. **Site Settings** — logo (transparent PNG, 60–80px height), WhatsApp, email, address, site domain, default meta description, and **Product Catalog PDF** (upload your watch catalog; visitors download it from the homepage "Download Catalog" button and the footer).
2. **Home Banners** — 2 carousel slides: background image, title, subtitle, description, CTA text & link.
3. **Home Highlights** — the 4-column core-advantages strip (icon, title, description).
4. **Our Factory** — heading, text, stats, factory photo (1200×800px).
5. **OEM & ODM Service** — MOQ, sample lead time, mass-production lead time, customization line, 4 service cards.
6. **Quartz Watches** — add / edit / delete products, upload 800×800px images, set model/movement/MOQ.
7. **Our Advantages** — the 5 "Why Choose JOEFOX" items (shown on the Factory page).
8. **Contact Us** — heading, subtitle, intro text.
9. **SEO / Page Meta** — per-page title + description for Google.
10. **Account** — change admin username / password.

All data is stored in `data/db.json`; uploaded images and the catalog PDF live in `data/uploads/`.

## Image specs

| Slot | Recommendation |
|------|----------------|
| Nav logo | transparent PNG, height 60–80px |
| Home banners | 1200×800px |
| Factory photo | 1200×800px |
| Product cards | 800×800px, white background, real photos |

### Default placeholders
Every image slot ships with a clean, monochrome **placeholder** in `public/assets/placeholders/`
(`banner-1.svg`, `banner-2.svg`, `factory.svg`, `product.svg`). They are pre-filled so the site
looks complete out of the box; upload a real image in the admin and it replaces the placeholder.
If you ever clear an image, the slot falls back to an upload-prompt box.

## Layout notes
- **Home 4-column highlights** render as 4 side-by-side columns on desktop and stack vertically on phones (responsive grid; tablet shows 2 columns).
- The site is fully responsive; the nav collapses into a hamburger menu on mobile.

## Content / positioning rules already applied

- No mechanical watches, no kids / silicone watches, no "Hot Selling Samples" — these were removed.
- No retail/shopping-cart; every CTA is **Inquire Now / Quick Inquiry / Contact** (WhatsApp or email).
- Default contact placeholders: WhatsApp `+86 15360561168`, email `joefoxwatch.winnie@gmail.com`, address `GUANGZHOU GUANGDONG CHINA`.
- Default domain used for sitemap/canonical: `https://www.joefoxwatchofficial.com` (change in **Site Settings**).

---

## Public deployment (公网部署)

This is a **Node.js server** (not a static site), so it needs a host that runs Node. The in-app tooling here only deploys *static* sites, so use one of the Node hosts below. The repo is already deploy-ready (see `Dockerfile`, `railway.json`, `render.yaml`, `Procfile`).

### Option A — Railway (recommended, free tier, no card)
1. Push this folder to a GitHub repo.
2. Go to https://railway.app → **New Project → Deploy from GitHub**.
3. It auto-detects the Dockerfile and deploys.
4. **Important:** add **one Volume** mounted at `/app/data` (size 1 GB). This single
   volume persists BOTH the CMS database (`db.json`) and all uploaded images/PDFs
   (`data/uploads/`). Railway allows only one volume per service, so we consolidated
   both into `/app/data` — do **not** add a second volume.
5. Set env var `SESSION_SECRET` to a random string.
6. Your site is live at the Railway URL; point your domain `www.joefoxwatchofficial.com` to it and update **Site Settings → site domain** so sitemap/canonical match.

### Option B — Render (free tier)
1. Push to GitHub, then https://render.com → **New → Web Service** → connect repo.
2. Render uses `render.yaml` automatically (Docker runtime + 1 disk at /app/data).
3. Set `SESSION_SECRET`.
4. Attach a custom domain `www.joefoxwatchofficial.com` in Render, then update **Site Settings**.

### Option C — Any VPS / Docker
```bash
docker build -t joefox-cms .
docker run -d -p 3000:3000 \
  -v joefox-data:/app/data \
  -e SESSION_SECRET=your-random-string \
  --name joefox-cms joefox-cms
```
Put it behind Nginx/Caddy with HTTPS and a domain.

### Why the volumes / disks matter
The CMS writes `data/db.json` and uploaded files (`data/uploads/`) to the local filesystem. On platforms with **ephemeral** storage, those would reset on every redeploy. Mounting a single persistent disk/volume at `/app/data` keeps both your content and images safe. (If you prefer a database later, the data layer in `lib/db.js` is the only file to swap.)

## Environment variables

| Var | Default | Notes |
|-----|---------|-------|
| `PORT` | `3000` | Listen port |
| `SESSION_SECRET` | built-in dev secret | **Set a random value in production** |
