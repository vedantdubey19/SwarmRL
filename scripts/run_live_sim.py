#!/usr/bin/env python3
import argparse
import os
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from env import SwarmRLParallelEnv
from sensors.bridge import (
    build_world_message,
    build_frame_message,
    build_grid_snapshot_message,
    build_grid_delta_message,
)
from sensors.ws_publisher import SwarmPublisher
from training.evaluate import load_actor_from_checkpoint


def run_live_simulation(
    checkpoint_path: str | None = None,
    difficulty: int = 0,
    hz: float = 30.0,
    duration: float = 0.0,
    ws_url: str | None = None,
    num_agents: int = 50,
) -> None:
    print(f"=== SwarmRL Live Sim Bridge ===")
    print(f"Swarm Size:  {num_agents}")
    print(f"Difficulty:  {difficulty}")
    print(f"Target Rate: {hz} Hz")
    if checkpoint_path:
        print(f"Policy:      Checkpoint ({checkpoint_path})")
    else:
        print(f"Policy:      Random Actions")

    # Initialize environment
    env = SwarmRLParallelEnv(
        num_agents=num_agents,
        difficulty=difficulty,
        max_steps=500,
        render_mode=None,
    )

    # Initialize policy actor if provided
    actor = None
    if checkpoint_path and os.path.exists(checkpoint_path):
        actor = load_actor_from_checkpoint(checkpoint_path)
        print("Successfully loaded decentralized policy actor.")

    # Start WebSocket publisher
    resolved_url = ws_url or os.environ.get("WS_URL", "ws://127.0.0.1:8080")
    print(f"Connecting publisher to: {resolved_url}")
    publisher = SwarmPublisher(ws_url=resolved_url, target_hz=hz)
    publisher.start()

    # Wait briefly for connection
    time.sleep(0.3)

    target_period = 1.0 / hz
    start_time = time.time()
    stream_start_time = None
    stream_end_time = None
    step_count = 0
    episodes_run = 0

    # Timing metrics for diagnostics
    time_inference_list = []
    time_step_list = []
    time_build_list = []
    time_sleep_drift_list = []

    next_tick = time.perf_counter()

    try:
        while True:
            observations, infos = env.reset(options={"difficulty": difficulty})
            episodes_run += 1

            # Broadcast world and grid snapshot upon reset
            world_msg = build_world_message(env)
            publisher.publish(world_msg)

            snapshot_msg = build_grid_snapshot_message(env)
            publisher.publish(snapshot_msg)

            step_reward_sum = 0.0

            while env.agents:
                loop_start = time.perf_counter()
                if stream_start_time is None:
                    stream_start_time = loop_start

                # Action selection: batched policy inference or random
                t0 = time.perf_counter()
                actions = {}
                if actor is not None:
                    agent_ids = list(observations.keys())
                    obs_batch = np.stack([observations[aid][:81] for aid in agent_ids])
                    acts = actor.act(obs_batch)
                    actions = {aid: acts[idx] for idx, aid in enumerate(agent_ids)}
                else:
                    for agent_id in env.agents:
                        actions[agent_id] = env.action_space(agent_id).sample()
                t1 = time.perf_counter()
                time_inference_list.append(t1 - t0)

                # Environment step
                next_obs, rewards, terminations, truncations, next_infos = env.step(actions)
                step_reward_sum = sum(rewards.values())
                t2 = time.perf_counter()
                time_step_list.append(t2 - t1)

                # Collect newly explored indices
                delta_cells = getattr(env.exploration_map, "last_newly_explored_indices", [])

                # Broadcast frame message
                frame_msg = build_frame_message(env, infos=next_infos, step_reward_sum=step_reward_sum)
                publisher.publish(frame_msg)

                # Broadcast grid delta if any
                if delta_cells:
                    delta_msg = build_grid_delta_message(env.step_count, delta_cells)
                    publisher.publish(delta_msg)
                t3 = time.perf_counter()
                time_build_list.append(t3 - t2)

                step_count += 1
                observations = next_obs
                infos = next_infos

                if step_count % 30 == 0:
                    metrics = frame_msg.get("metrics", {})
                    col = metrics.get("collision_totals", {})
                    exp = metrics.get("explored_fraction", 0.0) * 100
                    tgt = metrics.get("targets_found", 0)
                    now = time.perf_counter()
                    actual_fps = step_count / max(0.001, (now - stream_start_time))
                    print(
                        f"Step {env.step_count:03d} | Exp: {exp:5.1f}% | "
                        f"Tgt: {tgt}/{len(env.targets)} | "
                        f"Colls(D/O/B): {col.get('drone', 0)}/{col.get('obstacle', 0)}/{col.get('boundary', 0)} | "
                        f"Sent: {publisher.sent_frames} | FPS: {actual_fps:5.1f}"
                    )

                # High-precision cumulative drift-compensated pacing
                next_tick += target_period
                sleep_dur = next_tick - time.perf_counter()
                if sleep_dur > 0:
                    before_sleep = time.perf_counter()
                    time.sleep(sleep_dur)
                    after_sleep = time.perf_counter()
                    time_sleep_drift_list.append((after_sleep - before_sleep) - sleep_dur)
                else:
                    time_sleep_drift_list.append(0.0)
                    if sleep_dur < -2.0 * target_period:
                        next_tick = time.perf_counter()

                # Check duration limit if set
                if duration > 0 and (time.time() - start_time) >= duration:
                    stream_end_time = time.perf_counter()
                    print(f"Duration limit ({duration}s) reached.")
                    return

    except KeyboardInterrupt:
        print("\nSimulator interrupted by user.")
    finally:
        if stream_end_time is None and stream_start_time is not None:
            stream_end_time = time.perf_counter()
        publisher.stop()
        env.close()
        total_time = (stream_end_time - stream_start_time) if (stream_start_time and stream_end_time) else 0.001
        mean_fps = step_count / max(0.001, total_time)
        print(f"\n=== Simulation Timing Summary ===")
        print(f"Total steps:             {step_count}")
        print(f"Total duration:          {total_time:.2f} s")
        print(f"Effective Rate:          {mean_fps:.2f} Hz (Target: {hz} Hz)")
        print(f"Frames Sent:             {publisher.sent_frames}")
        print(f"Frames Dropped:          {publisher.dropped_frames}")
        if time_step_list:
            import numpy as _np
            print(f"--- Timing Breakdown (mean per step) ---")
            print(f"Inference:               {_np.mean(time_inference_list)*1000:6.2f} ms")
            print(f"Environment step:        {_np.mean(time_step_list)*1000:6.2f} ms")
            print(f"Frame & Delta build:     {_np.mean(time_build_list)*1000:6.2f} ms")
            print(f"Sleep jitter/drift:      {_np.mean(time_sleep_drift_list)*1000:6.2f} ms")
            print(f"Total CPU work / step:   {(_np.mean(time_inference_list)+_np.mean(time_step_list)+_np.mean(time_build_list))*1000:6.2f} ms")


def main():
    parser = argparse.ArgumentParser(description="SwarmRL Live Real-Time Simulator Bridge")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to policy checkpoint")
    parser.add_argument("--difficulty", type=int, default=0, help="Difficulty level 0-4")
    parser.add_argument("--hz", type=float, default=30.0, help="Target simulation / telemetry Hz")
    parser.add_argument("--duration", type=float, default=0.0, help="Execution duration in seconds (0 = infinite)")
    parser.add_argument("--ws-url", type=str, default=None, help="WebSocket relay URL")
    parser.add_argument("--num-agents", type=int, default=50, help="Number of drone agents")

    args = parser.parse_args()
    run_live_simulation(
        checkpoint_path=args.checkpoint,
        difficulty=args.difficulty,
        hz=args.hz,
        duration=args.duration,
        ws_url=args.ws_url,
        num_agents=args.num_agents,
    )


if __name__ == "__main__":
    main()
