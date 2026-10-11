---
name: bjj-window-gateway
description: Implement or review the production-safe match decision-window gateway without bypassing RECOVER, D3-B TOKEN or HOLD.
---

# bjj-window-gateway

Use when connecting player commands, PositionContract, MountMatch, initiative, production decision windows, time or D3-B.

Authoritative paths:
- `BjjMountContract.submit()` -> `BjjMountMatch.attempt()`: validated **exchange**, not full production window.
- `BjjMountMatch.next_window()`: free-window or simulated-time advance, D3-B post-advance observation.
- `BjjMountMatch.bottom_decision()`: production Bottom validation, selected commitment, D3-B decision, `LOCKOUT_HOLD` vs genuine RESET vs ATTEMPT.

Build a **narrow match-level owner** that calls these paths; it must never reimplement grades, costs, recovery or token state. Validate position, stable fighter ID, initiative, current window identity and stale/double submissions before any mutation. Treat wrong-fighter, stale, terminal and malformed requests as atomic failures. Do not let a UI craft a commitment that bypasses Bottom's selected LOW/MEDIUM policy. Free windows do not imply free exchanges.

Test from fresh and exhausted, clear/re-exhaust, armed/token consumed, HOLD with zero simulated time and stamina, no-action RESET, Top versus Bottom, external free-window ownership, invalid responses, duplicate/replayed commands, terminal events and deterministic histories. Compare baseline `bottom_decision()`/`next_window()` traces to the gateway. Do not alter D3-B controller or Python oracle as a shortcut.

This skill doesn't authorize a new human timer, stalling/Recognition, Side Control or a UI layer.
