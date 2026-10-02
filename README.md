# SwarmRL

SwarmRL is a reinforcement learning project focused on coordinated, swarm-inspired decision making for Axelero.

## Overview

This repository is intended to serve as the foundation for experimentation, training, and evaluation of reinforcement learning agents in environments that benefit from collective or coordinated behavior.

The project is designed to be extended with:

- environment definitions
- agent policies and training loops
- reward and evaluation logic
- experiment tracking and benchmarking
- simulation and visualization tools

## Multi-Agent Environment Architecture

- **Agent Count:** 50 homogeneous drones (`drone_0` through `drone_49`) performing collaborative Search-and-Rescue (SAR).
- **Environment Interface:** PettingZoo `ParallelEnv` (`SwarmRLParallelEnv` in `env.py`).
- **RLlib / MAPPO Target:** Supports Centralized Training with Decentralized Execution (CTDE). Each agent receives an 81-dimensional local observation vector, while the centralized value network consumes a 471-dimensional global state vector (`Box(471,)`).
- **Sensors & Rewards Integration:** Integrates with `sensors/rewards.py` (`calculate_reward`), `sensors/events.py` (`build_event_flags`), `sensors/sensors.py` (`ConeSensor`), and `sensors/exploration.py` (`ExplorationMap`). Step rewards are unpacked as `(total_reward: float, details: dict)` and exposed under `infos[agent_id]["reward_breakdown"]`.
- **WebSocket Relay Integration:** Emits atomic 50-drone telemetry frames (`type: "frame"`) to Node.js broker (`server.js`) on port 8080, which are relayed to the Three.js / React-Three-Fiber 3D viewport at 60 FPS using smooth lerp/slerp interpolation.

## Repository structure

```text
SwarmRL/
├── env.py                       # 50-agent PettingZoo ParallelEnv
├── rllib_config.py              # Ray RLlib MAPPO configuration
├── train_audit_trial1.py        # MAPPO baseline training harness
├── train.py                     # RLlib PPO training driver with checkpointing
├── server.js                    # Node.js 50-drone WebSocket relay broker
├── schema.js                    # Telemetry frame schema validation
├── sensors/                     # Sensor simulation & reward engine
│   ├── sensors.py               # ConeSensor (90° FoV, 20m range)
│   ├── rewards.py               # 7-component reward function
│   ├── events.py                # Collision, boundary & target detection
│   ├── exploration.py           # 2D occupancy & coverage grid
│   └── telemetry.py             # Metrics & telemetry payload builder
├── frontend/                    # Three.js / React-Three-Fiber 3D viewport
├── tests/                       # Unit & integration test suites
└── docs/                        # Architecture & interface specifications (env_spec.md is the env reference)
```

## Getting started

1. Clone the repository:

```bash
git clone https://github.com/vedantdubey19/SwarmRL.git
cd SwarmRL
```

2. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

> If a requirements file is not present yet, create one once the project dependencies are finalized.

4. Run the project or training scripts:

```bash
python main.py
```

## Typical goals

- explore multi-agent reinforcement learning approaches
- train efficient policies for coordination-heavy tasks
- evaluate performance against baselines and simulation scenarios
- iterate quickly on model architecture and reward design

## Contributing

Contributions are welcome as the project evolves. Suggested workflow:

1. create a feature branch
2. implement the change
3. validate with relevant tests or simulations
4. open a pull request with a clear summary

## Notes

This README is intentionally written as a practical starting point for the repository. Once the implementation details are added, it should be updated to describe the exact training pipeline, environment setup, and evaluation commands used by the project.

## License

The license has not yet been specified for this repository. Add a license file and update this section once the legal usage terms are decided.
