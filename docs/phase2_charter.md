# SwarmRL Phase 2 Operational Charter: MAPPO & Deployment Sprint (Days 16–22)

**Document ID:** `CHARTER-PHASE2-2026-10-03`  
**Effective Date:** October 3, 2026  
**Status:** APPROVED & SIGNED OFF  
**Authority:** Project & Integration Lead (Vedant Dubey)

---

## 1. Executive Summary & Purpose

Following the Day 15 Mid-Project Review and the resolution of the Go/No-Go conditions, this charter formally ratifies the structural track reassignment for Phase 2 (Days 16–22). Due to unaddressed sub-team attrition across earlier tracks, this charter realigns core responsibilities to guarantee on-time delivery of the coordinated search-and-rescue MAPPO milestone.

---

## 2. Track Ownership Reassignment Matrix

| Prior Owner | Subsystem / Scope | Reassignment Status | New Phase 2 Owner | Direct Deliverables |
| :--- | :--- | :--- | :--- | :--- |
| **Humera** | Multi-Agent Reinforcement Learning (MARL), `env.py` | **Relieved** (0 commits recorded) | **Vedant Dubey** *(Integration & RL Lead)* | Centralized Critic architecture, observation pipelines, and training execution. |
| **Venkatesh** | Centralized Critic (`ModelV2`), PPO tuning | **Relieved** (Discontinued after Day 5) | **Vedant Dubey** *(Integration & RL Lead)* | Ray RLlib cluster configuration, PPO hyperparameter tuning, checkpoint validation. |
| **Arya** | WebSocket Broker (`server.js`), Relay Protocol | **Reassigned to Shared Lead** | **Vedant Dubey** *(Bridge & Protocol)* & **Arya** *(Dockerization)* | Python environment telemetry publisher bridge (`sensors/bridge.py`), broker daemonization. |
| **Saju** | Telemetry Analytics & Metrics Framework | **Expanded Scope** | **Saju** *(Analytics & Curriculum)* | Scenario curriculum generation (`sensors/scenario.py`), session summaries, training diagnostics. |
| **Dhruv** | 3D Viewport (`frontend/`) | **Maintained with Strict Guardrails** | **Dhruv** *(Rendering)* | Three.js / React-Three-Fiber instanced mesh rendering consuming live WebSocket frames only. |

---

## 3. Core Milestones for Days 16–22

### Day 16–17: Centralized Training with Decentralized Execution (CTDE)
* **Lead:** Vedant Dubey
* **Tasks:**
  1. Complete integration of `SwarmRLParallelEnv` with the Python WebSocket telemetry bridge (`sensors/bridge.py`).
  2. Implement Ray RLlib rollout worker compatibility for continuous action spaces.
  3. Validate observation vectors (81-dim local + 471-dim global state).

### Day 18–19: Scenario Curriculum & Diagnostic Pipelines
* **Lead:** Saju
* **Tasks:**
  1. Integrate curriculum scenario configurations into training evaluation loops.
  2. Stream per-episode telemetry to `TelemetrySessionSummary` and export JSON/CSV records.
  3. Validate metric convergence across varying obstacle densities.

### Day 20–21: End-to-End Visual Rollout & Soak Testing
* **Lead:** Vedant Dubey & Dhruv
* **Tasks:**
  1. Stream live environment stepping from Python to Node.js broker at 20–30 Hz.
  2. Verify Three.js rendering of 50 active drones with lerp/slerp interpolation and yaw rotation alignment.
  3. Execute 15-minute continuous broker soak test with zero memory leaks.

### Day 22: Final Milestone Gate & Evaluation
* **Lead:** Vedant Dubey
* **Tasks:**
  1. Final checkpoint evaluation across 50 episodes.
  2. Production delivery evidence pack compilation.

---

## 4. Sign-Off & Verification

* **Project & Integration Lead:** Vedant Dubey (`vedantdubey.1302@gmail.com`) — *Confirmed & Signed*
* **Date:** October 3, 2026
