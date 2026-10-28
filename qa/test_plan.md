# SwarmRL Independent Quality Assurance Test Plan

**Version**: 1.0.0  
**Tested Commit**: `1bb20365573883f0d41a0e4f310d737a95a015b0`  
**Author**: Senior QA Engineer  
**Date**: 2026-10-28  
**Status**: APPROVED FOR EXECUTION  

---

## 1. Scope and Objectives

### 1.1 In Scope
- **Environment & Physics**: PettingZoo `ParallelEnv` API compliance, deterministic seeding, 50-agent vectorization, continuous Box(4,) action scaling and clipping, 81-dim observation space, 471-dim centralized critic state space, 50x50 exploration grid symmetry, cone sensor detections, wind dynamics, obstacle collision envelopes, boundary damping, and reward calculation breakdown.
- **Relay & Wire Protocol**: `server/schema.json` schema validation, WebSocket relay connection handshake, role segregation (publisher vs subscriber), message ordering, late-joiner state caching, backpressure frame dropping under subscriber lag, and 50-drone multi-client load tolerance.
- **True MAPPO RL Training**: Ray RLlib New API Stack custom `TorchRLModule` (decentralized actor on 81-dim local observation, centralized critic on 471-dim global state), parameter sharing across 50 drones, checkpointing with `manifest.json`, curriculum promotion across difficulty levels 0-4 without level-skipping, and policy evaluation vs random baseline.
- **3D WebGL Frontend**: React-Three-Fiber single `InstancedMesh` 50-drone rendering, 50x50 `DataTexture` ground painting from snapshots/deltas, 4 Hz throttled HUD telemetry display, out-of-order frame rejection, and connection lifecycle resilience.
- **End-to-End System Integration**: Real-time live simulator bridge (`scripts/run_live_sim.py`), multi-process stability, process crash/restart recovery, and telemetry cross-verification between Python simulator and client HUD.
- **Robustness & Security**: Dependency vulnerability audit, WebSocket fuzzing with oversized/malformed payloads, environment variable hygiene, and documentation accuracy.

### 1.2 Out of Scope
- Hardware-in-the-loop (HIL) physical drone deployment on real PX4 flight controllers.
- Multi-node distributed Ray cluster orchestration across cloud instances (local multi-worker only).
- Production multi-tenant authentication/TLS terminating reverse proxies.

---

## 2. Risk Assessment & Prioritization

| Risk ID | Risk Description | Impact | Likelihood | Mitigation / Focus Area |
|:-------:|:-----------------|:------:|:----------:|:------------------------|
| **R-01** | Repository state mismatch between git HEAD and working directory prevents fresh install | Critical | High | Execute Step 0 fresh-clone check; file S1 blocker if release files are uncommitted |
| **R-02** | Simulation memory leak or kinematic NaN explosion during long multi-step episodes | High | Med | 1000-step continuous simulation fuzzing; boundary position clamping assertions |
| **R-03** | Reward hacking or non-convergence in MAPPO due to policy/critic state leakage | High | Med | Test actor weight invariance to global state variations; benchmark trained vs random policy |
| **R-04** | WebSocket relay backpressure stalls simulation loop when clients lag | High | Med | Slow-subscriber starvation test; verify non-blocking drop-oldest buffer behavior |
| **R-05** | React rendering bottleneck at 30 Hz causing UI frame drop below 60 FPS | Med | Med | Verify mutable `FrameBuffer` decoupling and 4 Hz HUD update throttling |

---

## 3. Test Levels and Strategy

1. **Level A: Static & Build Verification**: Linting, syntax checks, type sanity, circular import detection, and secret/stray file scans.
2. **Level B: Unit & Component Testing**: Execution of existing Python (`pytest`) and Frontend (`vitest`) suites; 3x repeated runs to detect flake.
3. **Level C: Environment Functional Testing**: Black-box specification verification against `docs/env_spec.md`.
4. **Level D: Relay & Protocol Testing**: Schema validation, boundary payloads, late joiners, backpressure, and load scaling.
5. **Level E: MAPPO Training & Checkpoint Testing**: RLlib runner verification, actor-critic decoupling, checkpoint save/restore, and curriculum advancement.
6. **Level F: Frontend & 3D Viewport Testing**: InstancedMesh rendering, ground painting texture update, HUD metrics, and memory leak checks.
7. **Level G: End-to-End Live Integration**: Live simulation streaming with component restart resilience and physical metric cross-matching.
8. **Level H: Security & Robustness**: Malformed/fuzzed input payloads, dependency security audit, `.env` hygiene.
9. **Level I: Documentation Conformance**: Verifying every documented command in `README.md` and spec contract.
10. **Level J: Exploratory Stress Testing**: High-frequency resets, extreme wind parameters, stacked agent stress cases.

---

## 4. Test Environment Specification

- **Host Operating System**: macOS 27.2 (Darwin Kernel Version 27.2.0, arm64)
- **Hardware**: Apple Silicon 10-Core CPU, 16 GB Physical RAM
- **Python Runtime**: Python 3.12.16 (Conda / Virtualenv)
- **Key Python Packages**: `ray[rllib]==2.59.0`, `torch==2.14.1`, `gymnasium==1.2.2`, `pettingzoo==1.27.0`, `numpy==2.5.4`, `pytest==9.2.0`, `websockets==17.3`
- **Node Runtime**: Node.js v26.12.1, npm 11.2.0
- **Frontend Stack**: Vite 8.3.0, React 19.2.0, Three.js 0.186.0, @react-three/fiber 9.7.0, @react-three/drei 10.7.8, Zustand 5.0.15

---

## 5. Defect Severity Definitions

- **S1 (Blocker)**: Complete system crash, impossible to install from fresh clone, critical security vulnerability, data loss, or blocking test progression.
- **S2 (Major)**: Core specification broken (e.g. incorrect observation dimensions, collision detection failure, MAPPO actor depending on critic state), no viable workaround.
- **S3 (Minor)**: Feature partially impaired or non-conforming but functional with an identifiable workaround; performance slight degradation.
- **S4 (Trivial)**: Cosmetic defect, typo in documentation, unformatted log output with no functional impact.

---

## 6. Entry and Exit Criteria

### 6.1 Entry Criteria
1. Clean environment available with documented dependencies installed.
2. Unit test suites can be executed via terminal command.
3. Baseline commit hash identified (`1bb20365573883f0d41a0e4f310d737a95a015b0`).

### 6.2 Exit Criteria for Release Recommendation
1. Zero open S1 (Blocker) defects.
2. Zero open S2 (Major) defects.
3. 100% of specification requirements traced to passing test cases.
4. WebSocket relay sustains 50-drone telemetry at 30 Hz with average latency $<15\text{ ms}$ and 0 dropped frames.
5. Trained MAPPO policy demonstrates statistically significant advantage over random baseline in both collision rate and explored area.
6. Clean install successfully verified from `README.md` instructions alone.

---

## 7. Requirement-to-Test Traceability Matrix

| Requirement Spec Source | Specific Requirement | Test ID | Description |
|:------------------------|:---------------------|:-------:|:------------|
| `docs/env_spec.md` §World | $X, Z \in [-50, 50]$, $Y \in [0, 20]$ bounds | `TC-ENV-01` | World constants & boundary enforcement |
| `docs/env_spec.md` §World | Velocity limits $\pm 10$ m/s horiz, $\pm 3$ m/s vert, $\pm \pi$ yaw | `TC-ENV-02` | Action scaling & velocity clamping |
| `docs/env_spec.md` §World | Boundary violation: clip pos, damp vel by 90%, raise flag | `TC-ENV-03` | Boundary collision & velocity damping |
| `docs/env_spec.md` §Agents | 50 agents named `drone_0`..`drone_49`, no removal on collision | `TC-ENV-04` | Agent persistence & swarm sizing |
| `docs/env_spec.md` §Agents | No `"__all__"` in termination or truncation dicts | `TC-ENV-05` | PettingZoo termination dictionary format |
| `docs/env_spec.md` §Obs | (81,) float32 obs: 9 self, 30 neighbors, 32 cone, 10 exploration | `TC-ENV-06` | Observation vector dimensionality & bounds |
| `docs/env_spec.md` §State | (471,) float32 state: 450 swarm, 20 targets, 1 explored fraction | `TC-ENV-07` | Centralized critic global state invariance |
| `docs/env_spec.md` §Exploration | 50x50 2m grid, symmetric credit assignment | `TC-ENV-08` | Exploration map symmetric credit |
| `docs/env_spec.md` §Sensors | Cone sensor: 15m range, 30° half-angle, detection classification | `TC-ENV-09` | Cone sensor detection accuracy |
| `docs/env_spec.md` §Events | Vectorized collision: drone $<2$m, obstacle $<1$m, target $<3$m | `TC-ENV-10` | Vectorized collision thresholds |
| `docs/env_spec.md` §Wind | Deterministic trajectory when wind strength is 0.0 | `TC-ENV-11` | Wind zero-strength determinism |
| `docs/env_spec.md` §Difficulty | Levels 0-4 obstacle and wind scaling; spawn clearance $\ge 4$m | `TC-ENV-12` | Scenario difficulty configuration & spawn clearance |
| `docs/env_spec.md` §Rewards | RewardConfig breakdown in info dict, float step reward | `TC-ENV-13` | Reward breakdown verification |
| `docs/protocol.md` §Roles | Role handshake (`publisher` vs `subscriber`) | `TC-REL-01` | WebSocket registration handshake |
| `docs/protocol.md` §Messages | `world`, `frame`, `grid_snapshot`, `grid_delta` validation | `TC-REL-02` | Protocol schema adherence (`server/schema.json`) |
| `docs/protocol.md` §LateJoin | Late joiner receives cached `world` and `grid_snapshot` | `TC-REL-03` | Relay late joiner caching |
| `docs/protocol.md` §Backpressure | Dropping frames on `bufferedAmount > 512KB` | `TC-REL-04` | Slow-subscriber non-blocking backpressure |
| `docs/protocol.md` §Ordering | Drop out-of-order frames by step and timestamp | `TC-REL-05` | Client frame-ordering filter |
| `docs/training.md` §CTDE | Decentralized actor invariance to global state changes | `TC-TRN-01` | MAPPO actor-critic decoupling |
| `docs/training.md` §Curriculum | Promotion after $K=3$ consecutive iters, never skip levels | `TC-TRN-02` | Curriculum progression logic |
| `docs/training.md` §Checkpoints | Checkpoint saving every 10 iters with `manifest.json` | `TC-TRN-03` | Checkpoint manifest integrity |
| `README.md` §Design | Single InstancedMesh 50-drone rendering at 60 FPS | `TC-FE-01` | InstancedMesh rendering performance |
| `README.md` §Design | 50x50 DataTexture ground painting alignment | `TC-FE-02` | DataTexture exploration painting |
| `README.md` §Design | Ref-based FrameBuffer with 4 Hz HUD throttling | `TC-FE-03` | Zustand store HUD throttling |
| `README.md` §Quickstart | Install, train, relay, live sim, verify from README commands | `TC-DOC-01` | README quickstart end-to-end execution |
