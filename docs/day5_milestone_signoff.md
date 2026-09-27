# SwarmRL Day-5 Milestone Review & Sign-Off Gate

## Executive Summary
This document records the official **Day-5 Milestone Sign-Off** for SwarmRL — the first synchronous checkpoint gate. The purpose of this gate is to verify that the environment engine, WebSocket streaming skeleton, and 3D viewport rendering are baseline-compatible before downstream feature development continues.

---

## 1. Go / No-Go Checklist

| Team / Subsystem | Status | Specific Evidence Needed to Call it a "PASS" |
| :--- | :---: | :--- |
| **Sensors & Rewards** *(Saju)* | **PASS** | `ConeSensor`, `ExplorationMap`, `calculate_reward`, and `SensorObservation` implemented and passing 20+ unit tests on `main` (`tests/test_sensors.py`, `tests/test_rewards.py`). |
| **Env & Physics Engine** *(Venkatesh / Vedant)* | **FAIL** | An executable PettingZoo `ParallelEnv` class (`env.py`) running 50 agents with `reset()` and `step(actions)`. Currently only exists as design blueprints in `docs/marl_space_design_spec.md`; action space diverges (claimed "velocity, pitch, yaw" vs. spec continuous 4-DoF $[v_x, v_y, v_z, \dot{\psi}]$). |
| **WebSocket Relay** *(Arya)* | **FAIL** | Pub/Sub broadcast mechanism in `server.js` forwarding publisher frames to connected frontend clients. Currently line 29 only executes `console.log('Valid agent update:', parsed)`, `schema.js` only allows single-drone objects, and `test-client.js` (PR #8) only tests single-socket loopback. |
| **Rendering & Viewport** *(Dhruv)* | **BLOCKED** | Live WebSocket hookup in `frontend/src/App.jsx` consuming streamed telemetry. Currently renders a static `<Grid />` with OrbitControls and disconnected client-side `Math.random()` spheres with zero WebSocket client code. |
| **RLlib Baseline Pipeline** *(Humera / Venkatesh)* | **BLOCKED** | Runnable rollout script executing training iterations against the 50-agent multi-agent environment. `rllib_config.py` on `origin/Venkatesh` sets `num_env_runners=0` with no environment registered. |

---

## 2. Critical Integration Gaps: "Done on Paper" but Untested End-to-End

1. **Env $\to$ WebSocket Integration (Zero End-to-End Pipeline)**
   * *Reality:* No Python script connects as a client to `ws://localhost:8080`. Arya’s Day 4 test (`test-client.js`) is a self-contained Node.js script pushing 3 hardcoded mock points. The actual Python simulation has never pushed a single frame through the broker.

2. **WebSocket $\to$ Frontend Relay (Broken Pipe)**
   * *Reality:* Even if Python published data, `server.js` lacks a subscriber broadcast loop (`wss.clients.forEach(...)`). Dhruv’s React frontend (`frontend/src/App.jsx`) contains no `WebSocket` listener, meaning the frontend has only ever displayed internal randomized coordinates.

3. **50-Drone Atomic Frame vs. Single-Drone Schema**
   * *Reality:* `schema.js` enforces single-drone payloads (`{ id, x, y, z, timestamp }`). Streaming 50 agents at 25 Hz produces 1,250 individual WebSocket messages/sec, which has not been tested against Node event loop latency or browser frame drops.

4. **Sensor-to-Env Loop Execution**
   * *Reality:* Saju’s `ConeSensor.detect()` and `ExplorationMap.mark_explored()` work in isolated unit tests, but have never been called inside a PettingZoo multi-agent `step()` loop containing 50 live agents.

5. **Coordinate Frame & Orientation Vector for Cones**
   * *Reality:* Rendering currently draws unoriented spheres. Saju's sensor heading assumes $0\text{ rad} = +X$ in the X-Z plane, whereas Three.js mesh forward is $-Z$ or $+Z$. Sensor cones cannot be drawn without this coordinate transformation verified end-to-end.

---

## 3. Carry-Forward Risks

### Must Resolve BEFORE Day 6 Work Starts (Hard Gates)
1. **Pub/Sub Broadcast & Batch Schema in `server.js`**: Implement client broadcast loop and replace single-drone message validation with atomic 50-drone frame payloads (`type: "frame"`).
2. **WebSocket Client in `frontend/src/App.jsx`**: Connect R3F to `ws://localhost:8080` to drive mesh coordinates from live incoming messages instead of local randomizers.
3. **Executable Minimal 50-Agent Env**: Commit a minimal runnable PettingZoo `ParallelEnv` returning dummy positions and yaw headings for all 50 drones.
4. **Coordinate Frame & Heading Lock**: Lock the yaw-to-Three.js transform (`rotation.y = -heading` or quaternion) so cone-of-vision meshes originate and point along true velocity vectors.

### OK to Carry into Week 2 (Non-Blocking Iterations)
1. **Real MAPPO Policy Convergence**: Initial policy weights, value baseline convergence, and training curve optimization.
2. **Ground-Painting Texture Optimization**: Transitioning exploration grid rendering from dynamic 2D canvas texture / instanced tiles to sparse binary bitmasks.
3. **High-Fidelity 3D Drone Meshes**: Swapping placeholder spheres for rigged glTF quadcopter models and rotor animations.
4. **Simulation Control Uplink**: Frontend Play/Pause/Reset commands sent upstream to Python.
5. **Dynamic Sensor Ray Visual FX**: Target highlight intersection rays and collision particle effects.
