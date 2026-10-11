---
name: bjj-visual-memory
description: Design or implement the approved 2D-first BJJ positional UI while keeping memory mechanics as explicitly deferred ideas.
---

# bjj-visual-memory

Use when working on 2D fighter art, position poses, technique-memory cards, game-plan filters, chain previews, Memory Echoes or HUD.

Read Issue #40 first, then Issues #31/#32/#35/#37 only as relevant. Master Guide v10.4 still governs mechanics despite its superseded older 3D preference. Target readable 1366x768 Compatibility rendering with keyboard/mouse/tap/focus and reduced-motion alternatives.

Visualize both fighters together in authentic role-readable poses. Use unique curved/tapered memory cards, fanned/unfanned modes, compact immediate chain breadcrumb and opt-in inspector—not always-visible constellation occupying the fight screen. Display legal/conditional/known-unavailable/not-learned distinctly. Preserve always-required defenses.

UI reads detached snapshots/availability reason codes and dispatches validated action IDs during existing slow-motion windows. It must not compute tactical grade, resolve random cards, pause the simulated clock, auto-chain attacks or grant a technique merely because an animation played.

Prototype visual Memory Echo events with scripted fixtures if needed, not a new persistent learning policy. Old 3D greybox stays until explicitly replaced with a qualified smoke scene. Do not ship third-party art without source/license checks.
