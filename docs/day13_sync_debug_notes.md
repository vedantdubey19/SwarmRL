# Day 13: WebSocket Sync Debug Notes (retrospective)

Written on Oct 19 as a summary of the sync problems found and fixed during the sprint.

| Problem | Symptom | Fix |
|---|---|---|
| Dead connections (Day 9) | stale clients never cleaned up | 30 s heartbeat ping |
| Merge damage in server.js (Day 19) | extra `}`, duplicate server instance, broken exports | repaired and re-tested |
| Batches not relayed (Day 20) | a second client connected but received nothing | server relays batch_update to all other clients |
| Late joiners (Day 29) | a client opening mid-run saw an empty map | feed resends grid_snapshot + env_event every 25 steps |
| Non-object payloads (Day 29) | JSON like `null` threw inside the message handler | server replies with an error instead |

Verified by: late-joiner-test.js, bad-payload-test.js, integration-test.js, threejs-feed-client.js.