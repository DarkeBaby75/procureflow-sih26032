import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker from '../dist/server/index.js';

const env = {
  PUBLIC_SITE_ORIGIN: 'https://procureflow.example',
  TWILIO_ACCOUNT_SID: 'AC123',
  TWILIO_AUTH_TOKEN: 'secret',
  TWILIO_FROM_NUMBER: '+10000000000',
  TWILIO_TO_NUMBER: '+919999999999',
  TWILIO_TEMPLATE: 'sms_appointment_reminders',
};

test('serves the ProcureFlow application', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/'), env);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /ProcureFlow/);
  assert.doesNotMatch(html, /voice-button|🔊/);
});

test('serves the custom alert composer', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/hosted.js'), env);
  assert.equal(response.status, 200);
  assert.match(await response.text(), /custom-alert-message/);
});

test('serves the installable app and complete support interface', async () => {
  const page = await worker.fetch(new Request('https://procureflow.example/'), env);
  const html = await page.text();
  assert.match(html, /manifest\.webmanifest/);
  assert.match(html, /ProcureBot help/);
  assert.match(html, /Live admin chat/);
  assert.match(html, /accept="image\/\*,video\/\*,audio\/\*"/);
  const manifest = await worker.fetch(new Request('https://procureflow.example/manifest.webmanifest'), env);
  assert.equal(manifest.headers.get('Content-Type'), 'application/manifest+json; charset=utf-8');
  assert.equal((await manifest.json()).display, 'standalone');
});

test('serves the user manual and chat client behaviors', async () => {
  const manual = await worker.fetch(new Request('https://procureflow.example/manual.html'), env);
  assert.match(await manual.text(), /Seen ✓✓/);
  const script = await worker.fetch(new Request('https://procureflow.example/chat.js'), env);
  const javascript = await script.text();
  assert.match(javascript, /MediaRecorder/);
  assert.match(javascript, /\/api\/chat\/read/);
  assert.match(javascript, /data-delete/);
  assert.match(javascript, /beforeinstallprompt/);
});

test('keeps eligibility checkboxes compact and aligned', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/app.css'), env);
  assert.equal(response.status, 200);
  const css = await response.text();
  assert.match(css, /\.check-list input\[type=checkbox\]\{[^}]*width:20px!important[^}]*height:20px!important/);
  assert.match(css, /\.check-list label\{[^}]*grid-template-columns:20px minmax\(0,1fr\)/);
});

test('allows every modal to be cancelled without completing required fields', async () => {
  const page = await worker.fetch(new Request('https://procureflow.example/'), env);
  const html = await page.text();
  assert.match(html, /type="button" data-close-dialog>Cancel<\/button>/);
  assert.doesNotMatch(html, /value="cancel" aria-label="Close"/);
  const script = await worker.fetch(new Request('https://procureflow.example/hosted.js'), env);
  const javascript = await script.text();
  assert.match(javascript, /window\.addEventListener\('popstate'/);
  assert.match(javascript, /function openDialog\(dialog\)/);
});

test('serves complete dynamic Hindi and Marathi translation support', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/i18n.js'), env);
  const script = await response.text();
  assert.match(script, /MutationObserver/);
  assert.match(script, /सानुकूल शेतकरी सूचना/);
  assert.match(script, /कस्टम किसान अलर्ट/);
  assert.match(script, /Records explorer/);
});

test('blocks a foreign browser origin', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/api/send-sms', {
    method: 'POST',
    headers: { Origin: 'https://attacker.example' },
  }), env);
  assert.equal(response.status, 403);
});

test('blocks requests without a browser origin', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/api/send-sms', {
    method: 'POST',
  }), env);
  assert.equal(response.status, 403);
});

test('queues the fixed Twilio trial template', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    assert.match(options.headers.Authorization, /^Basic /);
    assert.match(options.body, /Body=sms_appointment_reminders/);
    assert.match(options.body, /To=%2B919999999999/);
    return new Response(JSON.stringify({ sid: 'SM123', status: 'queued' }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  try {
    const response = await worker.fetch(new Request('https://procureflow.example/api/send-sms', {
      method: 'POST',
      headers: { Origin: 'https://procureflow.example' },
    }), env);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).status, 'queued');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
