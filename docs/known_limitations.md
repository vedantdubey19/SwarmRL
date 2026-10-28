# Known Limitations & Scaling Analysis

This document provides a realistic evaluation of current architectural boundaries, mathematical simplifications, sim-to-real fidelity gaps, and bottlenecks that would emerge if scaling from 50 to 500 agents.

---

## 1. Physical Modeling & Sim-to-Real Gaps

1. **Point-Mass Kinematics vs. Full Rigid-Body Aerodynamics**:
   - The simulator models drones as point masses driven by velocity commands ($v_x, v_z \in [-10, 10]\text{ m/s}$, $v_y \in [-3, 3]\text{ m/s}$) with direct yaw rate control ($\dot{\psi} \in [-\pi, \pi]\text{ rad/s}$).
   - **Sim-to-Real Gap**: Real quadrotors experience motor delay, inertia tensors, rotor downwash ground effect, aerodynamic drag, and blade stall during aggressive decelerations. Deploying policies on physical PX4/ArduPilot hardware requires an inner attitude controller (SE(3) geometric tracking or cascading PID).

2. **Simplified Wind Perturbations**:
   - Wind is modeled as a 2D horizontal vector with stochastic Gaussian per-step gusts.
   - **Gap**: Complex urban or mountainous search-and-rescue canyons produce turbulent boundary layer vortices, microbursts, and building updrafts that are not modeled by homogeneous velocity offsets.

3. **Sensor Cone Occlusion**:
   - The cone sensor performs vectorized ray distance and angular subtension checks, but does not calculate multi-bounce lidar scattering or partial optical occlusion across complex obstacle geometries.

---

## 2. Architectural Bounds at 50 Agents

1. **Exploration Grid Resolution**:
   - The $50 \times 50$ exploration grid uses 2.0-meter cells. While suitable for regional search, fine obstacle avoidance inside tight 1.5-meter corridors requires sub-meter spatial discretizations (e.g., $200 \times 200$ cells at 0.5m), which would quadruple the bitmask payload size.
2. **Fixed Target Buffer**:
   - The global centralized critic state buffers up to 4 targets (20 dimensions). Scenarios with variable or dynamic target distributions (>4 targets) require masked transformer architectures or attention-pooling critics rather than fixed MLP embeddings.

---

## 3. What Would Break at 500 Agents?

If the system were scaled directly from 50 to 500 agents without architectural refactoring, the following failure points would occur:

### 3.1 Centralized Critic Dimensionality ($O(N)$)
- **Current State**: $450\text{ dimensions} = 50 \times 9$.
- **At 500 Agents**: The global state would expand to $4500\text{ dimensions}$. Fully connected layers ($4500 \to 256$) would require tens of millions of parameters, suffering sample complexity collapse and critic variance explosion.
- **Remedy**: Replace the monolithic critic with an Attention-Based Multi-Agent Critic (MAPPO with Cross-Attention) or Graph Neural Network (GNN) that operates over local interaction graphs.

### 3.2 Matrix Distance Broadcasting ($O(N^2)$)
- **Current Cost**: A $50 \times 50$ distance matrix consumes $2500$ pairwise evaluations per step ($<0.05\text{ ms}$).
- **At 500 Agents**: $500 \times 500 = 250,000$ pairwise distances. While NumPy broadcasting can process $250\text{k}$ floats, computing the $k$-nearest neighbors across 500 drones without spatial partitioning would degrade throughput from $1100\text{ steps/s}$ down to $<100\text{ steps/s}$.
- **Remedy**: Introduce a spatial hash grid or k-d tree (`scipy.spatial.cKDTree`) to bound neighbor queries to $O(N \log N)$ or $O(N)$.

### 3.3 Telemetry Wire Bandwidth
- **Current Frame**: 50 drones $\approx 15\text{ KB}$ per frame uncompressed. At 30 Hz, telemetry throughput is $\approx 450\text{ KB/s}$ ($3.6\text{ Mbps}$).
- **At 500 Agents**: Telemetry payloads would scale to $\approx 150\text{ KB}$ per frame ($4.5\text{ MB/s}$ or $36\text{ Mbps}$). A single slow subscriber would trigger immediate relay backpressure and buffer drops.
- **Remedy**: Transition from verbose JSON to binary serialization formats (FlatBuffers, Protocol Buffers, or packed WebGL ArrayBuffers), compressing 500 drone transforms into $<12\text{ KB}$ per frame.

### 3.4 WebGL Frontend GPU Instancing
- The current Three.js `InstancedMesh` handles 500 instances easily on modern GPUs (up to 10,000 instances is feasible within 60 FPS). However, rendering 500 detection rays (up to 4000 lines) would overwhelm draw batches unless converted into instanced ray geometry or screen-space compute shaders.
