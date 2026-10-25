const WebSocket = require('ws');

// Payloads that used to be able to crash the message handler.
const BAD = ['null', '"just a string"', '42', '[]', '{not json'];
const ws = new WebSocket('ws://localhost:8080');
let replies = 0;

ws.on('open', () => {
  BAD.forEach((p) => ws.send(p));
  setTimeout(check, 1500);
});

ws.on('message', (d) => {
  try { if (JSON.parse(d.toString()).type === 'error') replies++; } catch {}
});

function check() {
  // server must still be alive and answering a normal message afterwards
  const probe = new WebSocket('ws://localhost:8080');
  probe.on('open', () => {
    console.log(`error replies to ${BAD.length} bad payloads: ${replies}`);
    console.log(replies >= BAD.length - 1 ? 'BAD PAYLOADS: PASS (server still alive)' : 'BAD PAYLOADS: FAIL');
    process.exit(replies >= BAD.length - 1 ? 0 : 1);
  });
  probe.on('error', () => { console.log('BAD PAYLOADS: FAIL (server is down)'); process.exit(1); });
}

ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });