import asyncio
import json
import math
import random
import time
import sys
import websockets

PORT = 8765
AGENT_COUNT = 50
SIM_BOUNDS = 50.0  # Matches 120x120 terrain bounds

def get_terrain_height(x: float, z: float) -> float:
    """Procedural multi-frequency elevation formula matching Terrain.jsx."""
    return (
        math.sin(x * 0.08) * math.cos(z * 0.08) * 3.5 +
        math.sin(x * 0.03 + 1.2) * math.cos(z * 0.03 + 0.8) * 4.0
    )

class SwarmSimulator:
    def __init__(self, count: int = 50):
        self.count = count
        self.agents = []
        for i in range(count):
            angle = (i / count) * math.pi * 2
            radius = 10.0 + (i % 6) * 6.0
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = get_terrain_height(x, z) + 4.0 + (i % 4) * 0.5
            
            self.agents.append({
                "id": f"agent-{str(i + 1).zfill(2)}",
                "x": x,
                "y": y,
                "z": z,
                "vx": random.uniform(-0.35, 0.35),
                "vz": random.uniform(-0.35, 0.35),
                "yaw": random.uniform(0, math.pi * 2),
                "collision": False
            })

    def step(self):
        for agent in self.agents:
            agent["x"] += agent["vx"]
            agent["z"] += agent["vz"]

            # Boundary bounce
            if abs(agent["x"]) > SIM_BOUNDS:
                agent["vx"] *= -1
                agent["x"] = math.copysign(SIM_BOUNDS, agent["x"])
            if abs(agent["z"]) > SIM_BOUNDS:
                agent["vz"] *= -1
                agent["z"] = math.copysign(SIM_BOUNDS, agent["z"])

            # Height adaptation
            terrain_h = get_terrain_height(agent["x"], agent["z"])
            target_y = terrain_h + 4.5
            agent["y"] += (target_y - agent["y"]) * 0.1
            agent["yaw"] = math.atan2(agent["vx"], agent["vz"])

        # Proximity collision check
        for i in range(len(self.agents)):
            self.agents[i]["collision"] = False
            for j in range(i + 1, len(self.agents)):
                dx = self.agents[i]["x"] - self.agents[j]["x"]
                dz = self.agents[i]["z"] - self.agents[j]["z"]
                if math.sqrt(dx * dx + dz * dz) < 2.0:
                    self.agents[i]["collision"] = True
                    self.agents[j]["collision"] = True

        now_ms = int(time.time() * 1000)
        return [
            {
                "id": a["id"],
                "x": round(a["x"], 3),
                "y": round(a["y"], 3),
                "z": round(a["z"], 3),
                "yaw": round(a["yaw"], 3),
                "collision": a["collision"],
                "timestamp": now_ms
            }
            for a in self.agents
        ]

simulator = SwarmSimulator(AGENT_COUNT)

async def handler(websocket):
    client_ip = websocket.remote_address
    print(f"\n[WebSocket] Client connected: {client_ip}", flush=True)
    step_count = 0
    try:
        while True:
            payload = simulator.step()
            await websocket.send(json.dumps(payload))
            step_count += 1
            if step_count % 40 == 0:
                print(f"[WebSocket] Broadcast step #{step_count} (50 agents) -> {client_ip}", flush=True)
            await asyncio.sleep(0.05)  # 20 Hz
    except websockets.exceptions.ConnectionClosed:
        print(f"[WebSocket] Client disconnected: {client_ip}", flush=True)

async def main():
    print(f"==================================================", flush=True)
    print(f" SwarmRL Mock Telemetry Broadcaster (Day 06)", flush=True)
    print(f" Status: LISTENING on ws://localhost:{PORT}", flush=True)
    print(f" Agents: {AGENT_COUNT} | Bounds: +/-{SIM_BOUNDS}m | Rate: 20Hz", flush=True)
    print(f"==================================================", flush=True)
    
    async with websockets.serve(handler, "localhost", PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SwarmRL] Telemetry server stopped.", flush=True)