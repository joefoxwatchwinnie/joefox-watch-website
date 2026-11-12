// Optional SMTP mailer for inquiry notifications and auto-reply quotations.
// If SMTP is not configured in admin settings, mail sending is skipped gracefully.
const nodemailer = require('nodemailer');

function getTransporter(settings) {
  if (!settings || !settings.smtp_host || !settings.smtp_user || !settings.smtp_pass) return null;
  const secure = settings.smtp_secure !== '0';
  return nodemailer.createTransport({
    host: settings.smtp_host,
    port: parseInt(settings.smtp_port || '465', 10),
    secure,
    auth: { user: settings.smtp_user, pass: settings.smtp_pass }
  });
}

async function sendInquiryEmails(settings, inquiry) {
  const transporter = getTransporter(settings);
  if (!transporter) return { sent: false, reason: 'SMTP not configured' };
  const from = settings.smtp_from || settings.smtp_user;
  const typeLabel = inquiry.type === 'sample' ? 'SAMPLE REQUEST' : 'INQUIRY';
  const productLine = inquiry.product_model ? `Product: ${inquiry.product_model} (${inquiry.product_name || ''})\n` : '';
  const qtyLine = inquiry.quantity ? `Quantity: ${inquiry.quantity}\n` : '';
  const adminHtml = `
    <h2>New ${typeLabel} from website</h2>
    <p><b>Name:</b> ${inquiry.name}<br/>
    <b>Company:</b> ${inquiry.company || '-'}<br/>
    <b>Country:</b> ${inquiry.country || '-'}<br/>
    <b>Email:</b> ${inquiry.email}<br/>
    <b>Phone/WhatsApp:</b> ${inquiry.phone || '-'}<br/>
    ${productLine}${qtyLine}
    <b>Message:</b><br/>${(inquiry.message || '-').replace(/\n/g, '<br/>')}</p>`;
  const customerHtml = `
    <p>Dear ${inquiry.name},</p>
    <p>Thank you for contacting JOEFOX Watch Factory. We have received your ${typeLabel.toLowerCase()}${inquiry.product_model ? ` for model <b>${inquiry.product_model}</b>` : ''} and will send you a quotation shortly (usually within 24 hours).</p>
    <p>If you need an urgent reply, reach us directly on WhatsApp: ${settings.whatsapp}.</p>
    <p>Best regards,<br/>JOEFOX Watch Co., Ltd.<br/>${settings.email}</p>`;
  try {
    await transporter.sendMail({
      from, to: settings.email,
      subject: `[JOEFOX] New ${typeLabel}: ${inquiry.name}${inquiry.product_model ? ' - ' + inquiry.product_model : ''}`,
      html: adminHtml
    });
    await transporter.sendMail({
      from, to: inquiry.email,
      subject: 'We received your inquiry - JOEFOX Watch Factory',
      html: customerHtml
    });
    return { sent: true };
  } catch (err) {
    console.error('Mail sending failed:', err.message);
    return { sent: false, reason: err.message };
  }
}

module.exports = { sendInquiryEmails, getTransporter };
