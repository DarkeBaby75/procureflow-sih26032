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

class FakeD1 {
  constructor() { this.conversations = new Map(); this.messages = new Map(); }
  prepare(sql) {
    const db = this;
    return { values: [], bind(...values) { this.values = values; return this; },
      async run() {
        const v = this.values;
        if (sql.includes('INSERT INTO chat_conversations')) db.conversations.set(v[0], { id:v[0], participant_id:v[1], participant_name:v[2], participant_role:v[3], created_at:'2026-09-10 10:00:00', updated_at:'2026-09-10 10:00:00' });
        else if (sql.includes('INSERT INTO chat_messages')) db.messages.set(v[0], { id:v[0], conversation_id:v[1], sender_id:v[2], sender_name:v[3], sender_role:v[4], body:v[5], media_key:v[6], media_name:v[7], media_type:v[8], created_at:'2026-09-10 10:01:00', edited_at:null, deleted_at:null, seen_at:null });
        else if (sql.includes('SET body=?,edited_at')) Object.assign(db.messages.get(v[1]), { body:v[0], edited_at:'2026-09-10 10:02:00' });
        else if (sql.includes("SET body='',media_key=NULL")) Object.assign(db.messages.get(v[0]), { body:'', media_key:null, deleted_at:'2026-09-10 10:03:00' });
        else if (sql.includes('SET seen_at=')) for (const m of db.messages.values()) if (m.conversation_id===v[0] && m.sender_role!==v[1]) m.seen_at='2026-09-10 10:02:00';
        return { success:true };
      },
      async first() {
        const id=this.values[0];
        if (sql.includes('FROM chat_conversations')) return db.conversations.get(id)||null;
        if (sql.includes('WHERE media_key=')) return [...db.messages.values()].find(message=>message.media_key===id&&!message.deleted_at)||null;
        if (sql.includes('FROM chat_messages')) return db.messages.get(id)||null;
        return null;
      },
      async all() {
        if (sql.includes('FROM chat_messages WHERE conversation_id')) return { results:[...db.messages.values()].filter(m=>m.conversation_id===this.values[0]) };
        return { results:[...db.conversations.values()] };
      }
    };
  }
}

test('serves the ProcureFlow application', async () => {
  const response = await worker.fetch(new Request('https://procureflow.example/'), env);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /ProcureFlow/);
  assert.doesNotMatch(html, /voice-button|🔊/);
});

test('admin receives named conversations and farmer receives a seen reply', async () => {
  const db = new FakeD1();
  const r2Objects = new Map();
  const chatEnv = { ...env, DB:db, CHAT_MEDIA:{
    put:async(key,body,options)=>r2Objects.set(key,{ body, options }),
    get:async key=>r2Objects.get(key)||null,
    delete:async key=>r2Objects.delete(key),
  }};
  const farmer = { Origin:env.PUBLIC_SITE_ORIGIN, 'X-ProcureFlow-User':'farmer-ramesh', 'X-ProcureFlow-Name':'Ramesh Patil', 'X-ProcureFlow-Role':'farmer' };
  const admin = { Origin:env.PUBLIC_SITE_ORIGIN, 'X-ProcureFlow-User':'admin-demo', 'X-ProcureFlow-Name':'System Administrator', 'X-ProcureFlow-Role':'admin' };
  const opened = await worker.fetch(new Request('https://procureflow.example/api/chat/conversations', { headers:farmer }), chatEnv);
  const cid = (await opened.json()).conversations[0].id;
  const farmerForm = new FormData(); farmerForm.set('conversation_id',cid); farmerForm.set('body','My queue is delayed');
  await worker.fetch(new Request('https://procureflow.example/api/chat/messages',{method:'POST',headers:farmer,body:farmerForm}),chatEnv);
  const inbox = await worker.fetch(new Request('https://procureflow.example/api/chat/conversations',{headers:admin}),chatEnv);
  assert.equal((await inbox.json()).conversations[0].participant_name,'Ramesh Patil');
  await worker.fetch(new Request('https://procureflow.example/api/chat/read',{method:'POST',headers:{...admin,'Content-Type':'application/json'},body:JSON.stringify({conversation_id:cid})}),chatEnv);
  assert.ok([...db.messages.values()][0].seen_at);
  const reply = new FormData(); reply.set('conversation_id',cid); reply.set('body','Please use Baramati centre');
  const replied = await worker.fetch(new Request('https://procureflow.example/api/chat/messages',{method:'POST',headers:admin,body:reply}),chatEnv);
  assert.equal(replied.status,201);
  const farmerView = await worker.fetch(new Request(`https://procureflow.example/api/chat/messages?conversation_id=${cid}`,{headers:farmer}),chatEnv);
  assert.equal((await farmerView.json()).messages.length,2);
  const stranger = {...farmer,'X-ProcureFlow-User':'farmer-other','X-ProcureFlow-Name':'Other Farmer'};
  const forbidden = await worker.fetch(new Request(`https://procureflow.example/api/chat/messages?conversation_id=${cid}`,{headers:stranger}),chatEnv);
  assert.equal(forbidden.status,404);
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

test('persists, edits, reads and deletes a support message', async () => {
  const chatEnv = { ...env, DB:new FakeD1(), CHAT_MEDIA:{ put:async()=>{}, get:async()=>null, delete:async()=>{} } };
  const identity = { Origin:env.PUBLIC_SITE_ORIGIN, 'X-ProcureFlow-User':'farmer-demo', 'X-ProcureFlow-Name':'Ramesh Patil', 'X-ProcureFlow-Role':'farmer' };
  const opened = await worker.fetch(new Request('https://procureflow.example/api/chat/conversations', { headers:identity }), chatEnv);
  const conversation = (await opened.json()).conversations[0];
  const form = new FormData(); form.set('conversation_id', conversation.id); form.set('body', 'Please help with my token');
  const sent = await worker.fetch(new Request('https://procureflow.example/api/chat/messages', { method:'POST', headers:identity, body:form }), chatEnv);
  assert.equal(sent.status, 201); const message = (await sent.json()).message;
  const edited = await worker.fetch(new Request(`https://procureflow.example/api/chat/messages/${message.id}`, { method:'PATCH', headers:{...identity,'Content-Type':'application/json'}, body:JSON.stringify({body:'Please help with token PF-001'}) }), chatEnv);
  assert.equal(edited.status, 200);
  const listed = await worker.fetch(new Request(`https://procureflow.example/api/chat/messages?conversation_id=${conversation.id}`, { headers:identity }), chatEnv);
  assert.equal((await listed.json()).messages[0].body, 'Please help with token PF-001');
  const removed = await worker.fetch(new Request(`https://procureflow.example/api/chat/messages/${message.id}`, { method:'DELETE', headers:identity }), chatEnv);
  assert.equal(removed.status, 200);
  assert.ok(chatEnv.DB.messages.get(message.id).deleted_at);
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
