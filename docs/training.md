# SwarmRL True MAPPO Training Specification

SwarmRL implements Multi-Agent Proximal Policy Optimization (MAPPO) with Centralized Training and Decentralized Execution (CTDE) on Ray RLlib's **New API Stack** using custom PyTorch `RLModule` architectures.

---

## 1. CTDE Formulation

In decentralized search-and-rescue, communication constraints prevent drones from observing global coordinates or peer states during real-time deployment. We formulate the problem as a Decentralized Partially Observable Markov Decision Process (Dec-POMDP):

- **Decentralized Actor Policy $\pi_\theta(a_i \mid o_i)$**:
  Evaluates **only** the private 81-dimensional local observation $o_i$ of drone $i$. All 50 drones share the identical actor weights $\theta$.
- **Centralized Critic Value Network $V_\phi(s)$**:
  Evaluates the global, fixed-size 471-dimensional state vector $s$ during training to compute centralized value baselines and generalized advantage estimates (GAE). At inference time, the critic network is completely discarded.

---

## 2. Space Definitions

### 2.1 Decentralized Observation Vector (81 float32)
Divisors are grounded in immutable physical world constants ($X, Z \in [-50, 50]$, $Y \in [0, 20]$):

| Feature Slice | Dimensions | Description | Normalization |
|:--------------|:----------:|:------------|:--------------|
| **Self State** | 9 | Normalized position $[x, y, z]$, velocity $[v_x, v_y, v_z]$, heading $[\sin(\psi), \cos(\psi)]$, alive status | Pos $\div 50$, Alt $\div 20$, Vel $\div 10$ |
| **Nearest Neighbors** | 30 | Relative $[\Delta x, \Delta y, \Delta z]$ to 10 nearest drones (zero-padded if $<10$) | Pos $\div 100$ |
| **Cone Detections** | 32 | Up to 8 detections $\times$ [distance, $\text{bearing}_x$, $\text{bearing}_y$, type] | Dist $\div 15$, angles $\in [-\pi, \pi]$ |
| **Exploration Patch** | 10 | $3 \times 3$ local binary occupancy patch around agent (9) + global explored fraction (1) | $[0, 1]$ binary & scalar |

### 2.2 Centralized Global State Vector (471 float32)
Fixed size before reset, mid-episode, and across difficulty levels:

| Component | Dimensions | Description |
|:----------|:----------:|:------------|
| **All 50 Drones** | 450 | $50 \text{ agents} \times 9 \text{ features}$ (pos, vel, sin/cos heading, alive status) |
| **Global Exploration** | 1 | Global explored fraction $\in [0, 1]$ |
| **Targets (Padded)** | 20 | Up to 4 targets $\times 5$ features: $[x, y, z, \text{found\_flag}, \text{presence\_flag}]$ |
| **Total Global State** | **471** | $\text{Box}(-1.0, 1.0, (471,), \text{float32})$ |

---

## 3. Network Architecture

The custom RLModule ([`training/rl_module.py`](file:///Users/vedantdubey_20/Downloads/SwarRL/training/rl_module.py)) constructs dedicated actor and critic sub-networks:

```text
Local Observation (81) ──> [Linear 256 + Tanh] ──> [Linear 256 + Tanh] ──> [Linear 4] (Action Mean)
                                                                       └──> [Log-Std Parameter] (-0.5 init)

Global State (471)      ──> [Linear 256 + Tanh] ──> [Linear 256 + Tanh] ──> [Linear 1] (State Value)
```

- **Actor Output**: 4D Gaussian distribution (clipped to $[-1, 1]$).
- **Initial Log-Std**: Pinned to $-0.5$ ($\sigma \approx 0.6$) to prevent initial policy entropy explosion.
- **Advantage Normalization**: Standardized across batch minibatches to stabilize value loss gradients.

---

## 4. Curriculum Strategy

Curriculum promotion is managed dynamically by [`training/curriculum.py`](file:///Users/vedantdubey_20/Downloads/SwarRL/training/curriculum.py):

| Difficulty | Obstacles | Wind Speed | Wind Gusts | Promotion Condition |
|:----------:|:---------:|:----------:|:----------:|:--------------------|
| **0** | 0 | 0.0 m/s | None | $K=3$ consecutive iters with reward $\ge 50$ & collisions $\le 15$ |
| **1** | 5 | 0.0 m/s | None | $K=3$ consecutive iters with reward $\ge 100$ & collisions $\le 10$ |
| **2** | 10 | 2.0 m/s | Moderate | $K=3$ consecutive iters with reward $\ge 150$ & collisions $\le 5$ |
| **3** | 15 | 4.0 m/s | Strong | $K=3$ consecutive iters with reward $\ge 200$ & collisions $\le 3$ |
| **4** | 20 | 6.0 m/s | Severe | Maximum difficulty |

- **No Level Skipping**: The curriculum increments strictly by $+1$.
- **Remote Runner Confirmation**: Promoted difficulties are broadcasted to all active Ray `EnvRunners` and acknowledged before the next training iteration commences.

---

## 5. Hyperparameter Reference

| Hyperparameter | Value | Description |
|:---------------|:-----:|:------------|
| `learning_rate` | $3 \times 10^{-4}$ | Adam optimizer with linear warmup |
| `gamma` | $0.99$ | Discount factor |
| `lambda` (GAE) | $0.95$ | Generalized advantage estimation parameter |
| `clip_param` | $0.20$ | PPO surrogate clipping epsilon |
| `entropy_coeff` | $0.01$ | Policy entropy regularization coefficient |
| `train_batch_size` | 4000 | Total environment steps per training iteration |
| `minibatch_size` | 256 | SGD minibatch sample size |
| `num_epochs` | 10 | SGD optimization passes per rollout batch |
| `num_env_runners` | 2 | Parallel rollout workers |
| `num_agents` | 50 | Drone swarm size per environment |
