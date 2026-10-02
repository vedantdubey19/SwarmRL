# Day 17 — WebSocket Throughput Stress-Test Plan

## Goal
Determine the server's safe operating limits before MAPPO training + live frontend rendering both hit it simultaneously.

## What we're measuring
1. **Max concurrent clients** — how many publisher/subscriber connections before degradation
2. **Message rate ceiling** — batches/sec the server can relay without backlog
3. **Payload size limits** — behavior as agent count or observation richness grows (Day 16 added nearestNeighbors, increasing payload size per agent)
4. **Broadcast fan-out cost** — relay latency as subscriber count increases (1 publisher → N subscribers)

## Test scenarios planned
| Scenario | Publishers | Subscribers | Rate | Duration |
|---|---|---|---|---|
| Baseline | 1 | 1 | 5 msg/sec | 30s |
| Current load | 1 | 1 | 5 msg/sec (50 agents/batch) | 60s |
| Multi-subscriber | 1 | 5 | 5 msg/sec | 60s |
| Rate stress | 1 | 1 | 20 msg/sec | 30s |

## Metrics to capture
- Messages sent vs received (drop rate)
- Round-trip / relay latency (avg, p95, max)
- Server memory/CPU if observable
- First failure point (where it breaks)

## Status
Plan ready. Execution blocked on server.js fix (see Day 15/16 notes) — cannot run live tests until the server starts without error.