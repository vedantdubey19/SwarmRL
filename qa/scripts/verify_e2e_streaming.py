#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import websockets.sync.client

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PYTHON_EXE = sys.executable


def run_e2e_test():
    print("=== [QA LEVEL G] End-to-End Live Integration Verification ===")

    # 1. Start Relay Server
    print("  Starting Relay Server on port 8080...")
    relay_proc = subprocess.Popen(
        ["node", "server/server.js"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PORT="8080", HOST="127.0.0.1"),
    )
    time.sleep(0.5)

    try:
        # 2. Connect Subscriber Client
        print("  Connecting Subscriber client...")
        sub_ws = websockets.sync.client.connect("ws://127.0.0.1:8080")
        sub_ws.send(json.dumps({"type": "register", "role": "subscriber"}))

        # 3. Launch Live Sim Bridge (Publisher) in background
        print("  Starting Live Simulation Bridge with trained checkpoint...")
        sim_proc = subprocess.Popen(
            [
                PYTHON_EXE,
                "scripts/run_live_sim.py",
                "--checkpoint", "checkpoints/best_checkpoint",
                "--hz", "30",
                "--duration", "15",
                "--ws-url", "ws://127.0.0.1:8080",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        frames_received = 0
        world_received = False
        snapshot_received = False
        sample_drone_data = None
        start_ts = time.time()

        while frames_received < 150:
            try:
                raw = sub_ws.recv(timeout=5.0)
                msg = json.loads(raw)
                msg_type = msg.get("type")
                if msg_type == "world":
                    world_received = True
                elif msg_type == "grid_snapshot":
                    snapshot_received = True
                elif msg_type == "frame":
                    frames_received += 1
                    if frames_received == 50:
                        drones = {d["agent_id"]: d for d in msg["drones"]}
                        sample_drone_data = {
                            "step": msg["step"],
                            "explored": msg["metrics"]["explored_fraction"],
                            "collisions": msg["metrics"]["collision_totals"],
                            "d0_pos": drones.get("drone_0", {}).get("position"),
                            "d25_pos": drones.get("drone_25", {}).get("position"),
                            "d49_pos": drones.get("drone_49", {}).get("position"),
                        }
            except Exception as e:
                print(f"  Recv exception: {e}")
                break

        elapsed = time.time() - start_ts
        fps = frames_received / max(0.1, elapsed)

        print(f"  Initial Stream: Received {frames_received} frames in {elapsed:.2f}s ({fps:.1f} FPS)")
        assert world_received, "Never received world message!"
        assert snapshot_received, "Never received grid_snapshot message!"
        assert frames_received >= 100, f"Expected >= 100 frames, got {frames_received}"
        print(f"  Sample telemetry check (step {sample_drone_data['step']}):")
        print(f"    Explored: {sample_drone_data['explored']*100:.1f}% | Colls: {sample_drone_data['collisions']}")
        print(f"    drone_0  pos: {sample_drone_data['d0_pos']}")
        print(f"    drone_25 pos: {sample_drone_data['d25_pos']}")
        print(f"    drone_49 pos: {sample_drone_data['d49_pos']}")

        # 4. Resilience Check: Abruptly terminate simulator and restart
        print("\n  Testing Component Restart Resilience...")
        sim_proc.terminate()
        sim_proc.wait(timeout=2.0)
        print("  Simulation bridge stopped. Starting a new bridge instance...")

        sim_proc2 = subprocess.Popen(
            [
                PYTHON_EXE,
                "scripts/run_live_sim.py",
                "--checkpoint", "checkpoints/best_checkpoint",
                "--hz", "30",
                "--duration", "5",
                "--ws-url", "ws://127.0.0.1:8080",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        reconnect_frames = 0
        while reconnect_frames < 30:
            try:
                raw = sub_ws.recv(timeout=5.0)
                msg = json.loads(raw)
                if msg.get("type") == "frame":
                    reconnect_frames += 1
            except Exception:
                break

        print(f"  Recovery Stream: Received {reconnect_frames} frames from restarted simulation instance")
        assert reconnect_frames >= 20, "Failed to resume streaming after simulator restart"

        sim_proc2.terminate()
        sub_ws.close()
        print("\nLevel G End-to-End Validation: PASS")

    finally:
        relay_proc.terminate()
        relay_proc.wait()


if __name__ == "__main__":
    run_e2e_test()
