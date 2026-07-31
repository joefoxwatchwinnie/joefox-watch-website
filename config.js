module.exports = {
  port: process.env.PORT || 3000,
  sessionSecret: process.env.SESSION_SECRET || 'joefox-cms-secret-2026-change-in-production',
  uploadDir: './public/uploads',
  maxFileSize: 5 * 1024 * 1024, // 5MB
  admin: {
    defaultUsername: 'admin',
    defaultPassword: 'joefox2026'
  }
};
