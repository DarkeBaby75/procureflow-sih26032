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
  assert.match(await response.text(), /ProcureFlow/);
});

test('serves the custom alert composer', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/hosted.js'), env);
  assert.equal(response.status, 200);
  assert.match(await response.text(), /custom-alert-message/);
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
