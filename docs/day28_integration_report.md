# Day 28: Full Integration Test (WebSocket side)

Run with `integration-test.js` against server.js + mock-env-feed.js.
Covers: batch_update (50 agents/frame), grid_delta (ground painting),
grid_snapshot, env_event (obstacles + wind), curriculum level changes.

Result: INTEGRATION: PASS (74 batch_update, 42 grid_delta, 4 grid_snapshot, 4 env_event, 0 malformed, 58.8% explored)

Known limits:
- feed is a mock; swap for Humera's real env when ready
- server.js relays four message types; the original register/frame/control protocol is not restored
