import os
import json
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions.normal import Normal
from torch.utils.tensorboard import SummaryWriter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from env import SwarmRLParallelEnv, DEFAULT_NUM_AGENTS

RUN_DIR = "runs/trial1_real_env"
CHECKPOINT_DIR = "checkpoints/trial1_real_env"
os.makedirs(RUN_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

class ActorNet(nn.Module):
    def __init__(self, obs_dim=81, act_dim=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 128),
            nn.Tanh(),
        )
        self.mean_head = nn.Linear(128, act_dim)
        self.log_std = nn.Parameter(torch.zeros(act_dim))

    def forward(self, obs):
        feat = self.net(obs)
        mean = torch.tanh(self.mean_head(feat))
        std = torch.exp(torch.clamp(self.log_std, -2.0, 1.0))
        return mean, std

    def get_action_and_log_prob(self, obs, action=None):
        mean, std = self.forward(obs)
        dist = Normal(mean, std)
        if action is None:
            action = dist.sample()
            action = torch.clamp(action, -1.0, 1.0)
        log_prob = dist.log_prob(action).sum(axis=-1)
        entropy = dist.entropy().sum(axis=-1)
        return action, log_prob, entropy

class CentralizedCriticNet(nn.Module):
    def __init__(self, state_dim=471):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, 1),
        )

    def forward(self, state):
        return self.net(state).squeeze(-1)

def run_training_trial(num_iterations=12, steps_per_iter=1000):
    writer = SummaryWriter(log_dir=RUN_DIR)
    env = SwarmRLParallelEnv(num_agents=DEFAULT_NUM_AGENTS, max_steps=500, include_global_state=True)
    
    actor = ActorNet(obs_dim=81, act_dim=4)
    critic = CentralizedCriticNet(state_dim=471)
    
    actor_opt = optim.Adam(actor.parameters(), lr=3e-4)
    critic_opt = optim.Adam(critic.parameters(), lr=1e-3)

    metrics_history = []
    global_step = 0
    start_wall_time = time.time()

    print(f"=== Starting Real MAPPO Training Audit Trial 1 ===")
    print(f"Environment: SwarmRLParallelEnv (50 agents, real kinematics, centralized state)")
    print(f"TensorBoard logdir: {RUN_DIR}")
    print(f"Checkpoint dir: {CHECKPOINT_DIR}")
    print(f"Running {num_iterations} iterations x {steps_per_iter} steps = {num_iterations * steps_per_iter} total timesteps\n")

    for iter_idx in range(1, num_iterations + 1):
        obs_buf = []
        state_buf = []
        action_buf = []
        log_prob_buf = []
        reward_buf = []
        done_buf = []
        value_buf = []

        iter_team_cells = []
        iter_min_neighbor_dists = []
        iter_team_target_found_count = 0
        iter_drone_colls = 0
        iter_obs_colls = 0
        iter_bound_viols = 0
        iter_rewards = []
        iter_team_new_area = []
        iter_prox_penalties = []
        iter_entropies = []
        iter_active_agents = []

        obs_dict, _ = env.reset()
        episode_reward = 0.0

        for step in range(steps_per_iter):
            global_step += 1
            active_agents = env.agents
            iter_active_agents.append(len(active_agents))

            if len(active_agents) == 0:
                obs_dict, _ = env.reset()
                active_agents = env.agents

            current_global_state = env.state()
            state_tensor = torch.tensor(current_global_state, dtype=torch.float32)

            actions = {}
            step_obs = []
            step_actions = []
            step_log_probs = []
            step_values = []

            for a in active_agents:
                local_obs = obs_dict[a]["obs"]
                step_obs.append(local_obs)
                obs_tensor = torch.tensor(local_obs, dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    act, log_prob, ent = actor.get_action_and_log_prob(obs_tensor)
                    val = critic(state_tensor.unsqueeze(0))
                act_np = act.squeeze(0).numpy()
                actions[a] = act_np
                step_actions.append(act_np)
                step_log_probs.append(log_prob.item())
                step_values.append(val.item())
                iter_entropies.append(ent.item())

            next_obs_dict, rewards, terms, truncs, infos = env.step(actions)

            for i, a in enumerate(active_agents):
                r = rewards[a]
                done = terms[a] or truncs[a]
                obs_buf.append(step_obs[i])
                state_buf.append(current_global_state)
                action_buf.append(step_actions[i])
                log_prob_buf.append(step_log_probs[i])
                value_buf.append(step_values[i])
                reward_buf.append(r)
                done_buf.append(done)

                rb = infos[a]["reward_breakdown"]
                iter_rewards.append(r)
                iter_team_new_area.append(rb.get("team_new_area", 0.0))
                iter_prox_penalties.append(rb.get("proximity_penalty", 0.0))
                if rb.get("team_cells") is not None:
                    iter_team_cells.append(rb["team_cells"])
                if rb.get("min_neighbor_dist") is not None:
                    iter_min_neighbor_dists.append(rb["min_neighbor_dist"])
                if rb.get("team_target_found_flag"):
                    iter_team_target_found_count += 1
                if rb.get("drone_collision", 0.0) < 0:
                    iter_drone_colls += 1
                if rb.get("obstacle_collision", 0.0) < 0:
                    iter_obs_colls += 1
                if rb.get("boundary_violation", 0.0) < 0:
                    iter_bound_viols += 1

            obs_dict = next_obs_dict
            if terms.get("__all__") or truncs.get("__all__"):
                obs_dict, _ = env.reset()

        # Advantage & Returns computation (GAE)
        rewards_arr = np.array(reward_buf, dtype=np.float32)
        values_arr = np.array(value_buf, dtype=np.float32)
        dones_arr = np.array(done_buf, dtype=np.float32)

        returns = np.zeros_like(rewards_arr)
        advantages = np.zeros_like(rewards_arr)
        running_return = 0.0
        running_adv = 0.0
        gamma = 0.99
        lam = 0.95

        for t in reversed(range(len(rewards_arr))):
            if dones_arr[t]:
                next_val = 0.0
                running_return = 0.0
                running_adv = 0.0
            else:
                next_val = values_arr[t + 1] if t + 1 < len(values_arr) else 0.0
            delta = rewards_arr[t] + gamma * next_val - values_arr[t]
            running_adv = delta + gamma * lam * running_adv
            advantages[t] = running_adv
            running_return = rewards_arr[t] + gamma * running_return
            returns[t] = running_return

        norm_adv = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PyTorch PPO update
        b_obs = torch.tensor(np.array(obs_buf), dtype=torch.float32)
        b_states = torch.tensor(np.array(state_buf), dtype=torch.float32)
        b_acts = torch.tensor(np.array(action_buf), dtype=torch.float32)
        b_old_log_probs = torch.tensor(np.array(log_prob_buf), dtype=torch.float32)
        b_returns = torch.tensor(returns, dtype=torch.float32)
        b_advs = torch.tensor(norm_adv, dtype=torch.float32)

        batch_size = len(b_obs)
        indices = np.arange(batch_size)
        total_p_loss = 0.0
        total_v_loss = 0.0

        for _ in range(4):
            np.random.shuffle(indices)
            for start in range(0, batch_size, 256):
                end = start + 256
                mb_idx = indices[start:end]
                
                _, new_log_prob, mb_entropy = actor.get_action_and_log_prob(b_obs[mb_idx], b_acts[mb_idx])
                ratio = torch.exp(new_log_prob - b_old_log_probs[mb_idx])
                surr1 = ratio * b_advs[mb_idx]
                surr2 = torch.clamp(ratio, 0.8, 1.2) * b_advs[mb_idx]
                policy_loss = -torch.min(surr1, surr2).mean() - 0.01 * mb_entropy.mean()

                new_vals = critic(b_states[mb_idx])
                value_loss = 0.5 * ((new_vals - b_returns[mb_idx]) ** 2).mean()

                actor_opt.zero_grad()
                policy_loss.backward()
                nn.utils.clip_grad_norm_(actor.parameters(), 0.5)
                actor_opt.step()

                critic_opt.zero_grad()
                value_loss.backward()
                nn.utils.clip_grad_norm_(critic.parameters(), 0.5)
                critic_opt.step()

                total_p_loss += policy_loss.item()
                total_v_loss += value_loss.item()

        # Telemetry aggregations
        mean_rew = float(np.mean(iter_rewards))
        mean_ent = float(np.mean(iter_entropies))
        mean_team_cells = float(np.mean(iter_team_cells)) if iter_team_cells else 0.0
        mean_min_dist = float(np.mean(iter_min_neighbor_dists)) if iter_min_neighbor_dists else 0.0
        mean_active = float(np.mean(iter_active_agents))
        mean_team_new_area = float(np.mean(iter_team_new_area))
        mean_prox_pen = float(np.mean(iter_prox_penalties))

        # Write to TensorBoard
        writer.add_scalar("Reward/Total_Mean", mean_rew, iter_idx)
        writer.add_scalar("Reward/Team_New_Area", mean_team_new_area, iter_idx)
        writer.add_scalar("Reward/Proximity_Penalty", mean_prox_pen, iter_idx)
        writer.add_scalar("Policy/Entropy", mean_ent, iter_idx)
        writer.add_scalar("Policy/Active_Agents", mean_active, iter_idx)
        writer.add_scalar("Collisions/Drone", iter_drone_colls, iter_idx)
        writer.add_scalar("Collisions/Obstacle", iter_obs_colls, iter_idx)
        writer.add_scalar("Collisions/Boundary", iter_bound_viols, iter_idx)
        writer.add_scalar("Telemetry/Team_Cells", mean_team_cells, iter_idx)
        writer.add_scalar("Telemetry/Min_Neighbor_Dist", mean_min_dist, iter_idx)
        writer.add_scalar("Telemetry/Team_Target_Found", iter_team_target_found_count, iter_idx)

        # Save checkpoint
        ckpt_path = os.path.join(CHECKPOINT_DIR, f"checkpoint_iter_{iter_idx:03d}.pt")
        torch.save({
            "iteration": iter_idx,
            "actor_state_dict": actor.state_dict(),
            "critic_state_dict": critic.state_dict(),
            "actor_opt_state_dict": actor_opt.state_dict(),
            "critic_opt_state_dict": critic_opt.state_dict(),
            "mean_reward": mean_rew,
            "mean_entropy": mean_ent,
        }, ckpt_path)

        rec = {
            "iteration": iter_idx,
            "global_step": global_step,
            "mean_reward": round(mean_rew, 4),
            "policy_entropy": round(mean_ent, 4),
            "active_agents_mean": round(mean_active, 1),
            "drone_collisions": iter_drone_colls,
            "obstacle_collisions": iter_obs_colls,
            "boundary_violations": iter_bound_viols,
            "team_cells_mean": round(mean_team_cells, 2),
            "team_new_area_mean": round(mean_team_new_area, 4),
            "team_target_found_count": iter_team_target_found_count,
            "min_neighbor_dist_mean": round(mean_min_dist, 3),
            "proximity_penalty_mean": round(mean_prox_pen, 4),
            "checkpoint": ckpt_path,
        }
        metrics_history.append(rec)

        print(f"[Iter {iter_idx:02d}/{num_iterations}] Rew: {mean_rew:+.4f} | Ent: {mean_ent:.4f} | "
              f"Active: {mean_active:.1f} | Collisions: (drone={iter_drone_colls}, obs={iter_obs_colls}, bnd={iter_bound_viols}) | "
              f"team_cells: {mean_team_cells:.1f} | min_dist: {mean_min_dist:.2f}m | TargetsFound: {iter_team_target_found_count}")

    writer.close()
    
    # Save JSON summary metrics
    summary_file = os.path.join(RUN_DIR, "training_summary.json")
    with open(summary_file, "w") as f:
        json.dump(metrics_history, f, indent=2)

    # Generate training curves plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    iters = [m["iteration"] for m in metrics_history]

    axes[0, 0].plot(iters, [m["mean_reward"] for m in metrics_history], "b-o")
    axes[0, 0].set_title("Mean Reward per Agent-Step")
    axes[0, 0].set_xlabel("Iteration")
    axes[0, 0].set_ylabel("Reward")
    axes[0, 0].grid(True)

    axes[0, 1].plot(iters, [m["policy_entropy"] for m in metrics_history], "g-s")
    axes[0, 1].set_title("Policy Entropy Decay")
    axes[0, 1].set_xlabel("Iteration")
    axes[0, 1].set_ylabel("Entropy (nats)")
    axes[0, 1].grid(True)

    axes[1, 0].plot(iters, [m["drone_collisions"] for m in metrics_history], "r-^", label="Drone Collisions")
    axes[1, 0].plot(iters, [m["obstacle_collisions"] for m in metrics_history], "m-v", label="Obstacle Collisions")
    axes[1, 0].set_title("Collision Rate Trend")
    axes[1, 0].set_xlabel("Iteration")
    axes[1, 0].set_ylabel("Collision Count")
    axes[1, 0].legend()
    axes[1, 0].grid(True)

    axes[1, 1].plot(iters, [m["team_cells_mean"] for m in metrics_history], "c-d", label="Team Cells")
    axes[1, 1].plot(iters, [m["min_neighbor_dist_mean"] for m in metrics_history], "y-o", label="Min Neighbor Dist (m)")
    axes[1, 1].set_title("Exploration & Separation Metrics")
    axes[1, 1].set_xlabel("Iteration")
    axes[1, 1].legend()
    axes[1, 1].grid(True)

    plt.tight_layout()
    plot_file = os.path.join(RUN_DIR, "training_curves.png")
    plt.savefig(plot_file, dpi=150)
    plt.close()

    total_time = time.time() - start_wall_time
    print(f"\n=== Training Complete in {total_time:.2f}s ===")
    print(f"Summary JSON saved: {summary_file}")
    print(f"Curves Plot saved: {plot_file}")
    print(f"TensorBoard events saved: {RUN_DIR}")
    print(f"Latest Checkpoint: {ckpt_path}")

if __name__ == "__main__":
    run_training_trial(num_iterations=12, steps_per_iter=1000)
