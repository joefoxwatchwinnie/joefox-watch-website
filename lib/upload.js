const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const config = require('../config');

const uploadDir = path.join(__dirname, '..', config.uploadDir);
fs.mkdirSync(uploadDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const name = uuidv4() + ext;
    cb(null, name);
  }
});

function fileFilter(req, file, cb) {
  const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  if (allowed.includes(file.mimetype)) cb(null, true);
  else cb(new Error('Only image files (jpg, png, gif, webp) are allowed'));
}

function pdfFilter(req, file, cb) {
  if (file.mimetype === 'application/pdf') cb(null, true);
  else cb(new Error('Only PDF files are allowed for the catalog'));
}

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: config.maxFileSize }
});

const pdfUpload = multer({
  storage,
  fileFilter: pdfFilter,
  limits: { fileSize: 25 * 1024 * 1024 } // 25 MB
});

// Accepts both images and PDFs — used by the settings form (logos + catalog)
function mixedFilter(req, file, cb) {
  const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'];
  if (allowed.includes(file.mimetype)) cb(null, true);
  else cb(new Error('Only image (jpg, png, gif, webp) or PDF files are allowed'));
}

const uploadMixed = multer({
  storage,
  fileFilter: mixedFilter,
  limits: { fileSize: 25 * 1024 * 1024 } // 25 MB
});

function deleteUpload(relPath) {
  if (!relPath) return;
  const filePath = path.join(uploadDir, path.basename(relPath));
  if (fs.existsSync(filePath)) {
    try { fs.unlinkSync(filePath); } catch (e) { console.error('Failed to delete upload:', e.message); }
  }
}

module.exports = { upload, pdfUpload, uploadMixed, deleteUpload };
