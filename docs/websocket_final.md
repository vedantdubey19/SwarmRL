# WebSocket + Env: Final Documentation (Day 30)

## Run it
    npm install
    node server.js                       # relay server on ws://localhost:8080
    node mock-env-feed.js                # mock env, 5 steps/sec, 50 drones
    STEPS_PER_LEVEL=20 node mock-env-feed.js   # (optional) fast curriculum demo; default is 150

PowerShell: `$env:STEPS_PER_LEVEL=20; node mock-env-feed.js`

## Message types
All messages are JSON. The server relays every message of these types to all
OTHER connected clients.

| type | sent | key fields |
|---|---|---|
| batch_update | every step | step, timestamp, level, agents[50]: id, x, y, z, reward, cumulativeReward, nearestNeighbors[3]: id, distance |
| grid_delta | when new cells are painted | step, timestamp, cells[]: ix, iy, by; percentExplored |
| grid_snapshot | every 25 steps | step, gridSize (20), cells[]: ix, iy (all explored cells); percentExplored |
| env_event | step 1, level change, every 25 steps | kind "environment", level, wind, obstacles[]: id, x, y, z, r |
| error | server to sender | message |

Anything that is not a JSON object gets an `error` reply.

## Connecting mid-run (frontend)
Deltas alone are not enough for a late joiner. After connecting, wait up to 5 s
for the next `env_event` and `grid_snapshot`, replace local state with them,
then keep applying `grid_delta` and `batch_update`.

## Curriculum
| level | obstacles | radius | wind |
|---|---|---|---|
| 1 | 3 | 3.0 | 0.0 |
| 2 | 6 | 3.5 | 0.2 |
| 3 | 9 | 4.0 | 0.4 |
| 4 | 12 | 4.5 | 0.6 |
| 5 | 15 | 5.0 | 0.8 |

Level advances every STEPS_PER_LEVEL steps; level 5 continues after that.
Obstacle collision = -100 reward, otherwise +1 (80%) or 0.

## Reliability
- Heartbeat ping every 30 s; dead clients are terminated.
- Feed reconnects automatically after 2 s if the server drops.
- Invalid JSON or non-object payloads are rejected with an error reply.

## Tests
- test-grid-paint.js, test-obstacles.js, test-wind.js, test-curriculum.js: unit tests
- verify-mappo-dataflow.js: per-agent observation check (10 frames)
- integration-test.js: all message types arrive, 50 agents/frame, steps in order
- late-joiner-test.js: a client joining mid-run can rebuild map + environment
- bad-payload-test.js: malformed payloads do not take the server down
- threejs-feed-client.js: frontend stand-in turns each batch into a Float32Array
- validate-50-agents.js, throughput-stress-test.js: load scripts (throughput script targets the older register/frame protocol)

## Known limits
- The feed is a mock (random walk), not the real PettingZoo env.
- The original register/frame/control/grid_delta protocol from the Sep 21 design is not restored; the server relays by message type to every other client, with no publisher/subscriber roles.
- batch_update, grid_delta, grid_snapshot and env_event are relayed without schema validation.
