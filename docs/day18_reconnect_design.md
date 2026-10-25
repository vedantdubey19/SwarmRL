# Day 18: Server-Side Reconnect Logic Design

## Problem
A client can drop mid-session (network blip, tab reload) and reconnect moments later. Without handling, the server treats it as a brand-new, unknown client.

## Design
1. **Client ID on register**: the register message optionally carries a `clientId` that the frontend generates and keeps.
2. **Grace period**: on disconnect, hold the client's role for about 10 s, keyed by `clientId`, instead of deleting it immediately.
3. **Reconnect match**: if a new connection presents a held `clientId` inside the window, restore its role automatically.
4. **Expiry**: after the window, clean up as usual.

## Message shape addition
    { type: 'register', role: 'subscriber', clientId: 'uuid-...' }

## Status
Design only. Not implemented: the current server relays by message type with no roles (see docs/websocket_final.md). Late-joining clients are already covered by grid_snapshot and env_event keyframes.