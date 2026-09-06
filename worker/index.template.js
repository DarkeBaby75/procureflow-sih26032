const ASSETS = __PROCUREFLOW_ASSETS__;
const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
};
let lastSmsAt = 0;

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  },
});

function contentType(pathname) {
  const dot = pathname.lastIndexOf('.');
  return CONTENT_TYPES[dot >= 0 ? pathname.slice(dot) : '.html'] || 'application/octet-stream';
}

async function sendSms(request, env) {
  const origin = request.headers.get('Origin');
  if (!origin || origin !== env.PUBLIC_SITE_ORIGIN) return json({ message: 'Request blocked' }, 403);

  const required = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER', 'TWILIO_TO_NUMBER'];
  if (required.some(key => !env[key])) return json({ message: 'SMS service is not configured' }, 503);

  const now = Date.now();
  if (now - lastSmsAt < 60_000) return json({ message: 'Please wait one minute before sending another alert' }, 429);

  const form = new URLSearchParams({
    To: env.TWILIO_TO_NUMBER,
    From: env.TWILIO_FROM_NUMBER,
    Body: env.TWILIO_TEMPLATE || 'sms_appointment_reminders',
  });
  const authorization = btoa(`${env.TWILIO_ACCOUNT_SID}:${env.TWILIO_AUTH_TOKEN}`);
  const response = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${encodeURIComponent(env.TWILIO_ACCOUNT_SID)}/Messages.json`,
    {
      method: 'POST',
      headers: {
        Authorization: `Basic ${authorization}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: form.toString(),
    },
  );
  const result = await response.json();
  if (!response.ok) return json({ message: result.message || 'Twilio could not send the alert' }, 502);

  lastSmsAt = now;
  return json({ message: 'SMS alert queued successfully', status: result.status, sid: result.sid });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/health') return json({ status: 'ok', sms: 'hosted' });
    if (url.pathname === '/api/send-sms') {
      if (request.method !== 'POST') return json({ message: 'Method not allowed' }, 405);
      return sendSms(request, env);
    }

    if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('Method not allowed', { status: 405 });
    const key = url.pathname === '/' ? '/' : url.pathname;
    const body = ASSETS[key];
    if (body === undefined) return new Response('Not found', { status: 404 });
    return new Response(request.method === 'HEAD' ? null : body, {
      headers: {
        'Content-Type': contentType(key),
        'Cache-Control': 'no-cache',
      },
    });
  },
};
