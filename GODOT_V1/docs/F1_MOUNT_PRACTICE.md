# F1 — First playable 2D Mount practice prototype

**Status:** implemented, deterministic, headless-tested. Stacked on F0 (PR #53). This is an **interactive positional-training
prototype**: one Mount position, one human-controlled fighter, no match from Standing, no combat AI, no scoring. It invents no rule.

## 1. How to open and play it

1. Install Godot 4.7.2-stable (standard build) and import `GODOT_V1/project.godot`.
2. Press **F5**. The default scene is now `res://scenes/mount_practice.tscn` (the old 3D greybox `scenes/mount_debug.tscn`
   is kept as a separate diagnostic scene: open it and press **F6**).
3. You see two fighters (names come from the F0 sample `.tres` definitions), their role (Top/Bottom), stamina bar,
   `current / maximum`, exhaustion band and held behavior, the simulated clock, the Mount control axis and band, the match
   banner, the current window owner, the legal techniques, the legal responses and the event log.
4. Play loop:
   * **Next Window** (button or **N**) opens the next decision window. Time advances only here (the engine applies its normal
     drift and stamina flow when a window opens, so the live panels can differ slightly from the "latest decision" panel).
   * When **Top** owns the window (you decide): pick a technique, then the **opponent's response** to it (any response the
     engine admits), optionally change the Top's **commitment**, then **Submit Decision** (button or **S**). The Top must choose
     a technique: the engine would also admit a Top no-action reset, which F1 deliberately does not offer.
   * When **Bottom** owns the window, the opponent is a **scripted practice behavior**: **Submit Decision** sends the
     engine's existing no-action Bottom decision (under the production policy this may be a plain reset or a recovery hold;
     the result text shows the engine's decision kind). Nothing else is chosen for the opponent, and the Bottom's held
     behavior (for example ESCAPE) still drives time and stamina flow, so its label can look odd next to a passive opponent.
   * Unavailable techniques and responses are disabled and show the engine's exact reason code first, for example
     `[unavailable: setup_not_ready]` or `[unavailable: inactive_submission]`.
   * **New Practice Match** starts an independent match (fresh stamina, clock, events and window numbering).
5. The banner distinguishes three states: **Active Mount practice match**, **TERMINAL OUTCOME: timeout | tap**, and
   **BLOCKED POSITION TRANSITION** (a Mount exit whose destination does not exist yet; not a victory or defeat; it names the
   exit label, the engine's reason and either "declared destination X is not implemented" or "destination unresolved (no
   landing)" for Reversal). After a halt or an end every command is disabled.

Screenshots (rendered by the real renderer into an offscreen 1152x648 viewport): `docs/images/f1_01_window_open.png`,
`docs/images/f1_02_selected.png`, `docs/images/f1_03_scripted_bottom.png`.

![Window open](images/f1_01_window_open.png)
![Technique and response selected](images/f1_02_selected.png)
![Scripted Bottom window](images/f1_03_scripted_bottom.png)

A tested, deterministic route to a tap exists (prefer the Americana finish, then the arm isolation, then High Mount Climb,
always answering with the first admitted response); choosing the second response each time runs the 300-second clock out to a timeout.

## 2. Architecture (who owns what)

```
mount_practice.tscn (Control nodes, containers/anchors)
  └ mount_practice_scene.gd  -- renders a model, forwards input; no simulation, no _process
       └ BjjMountPracticeController (RefCounted) -- UI selections + the last result text only
            ├ BjjPositionGraphMatch  -- the ONLY command path: open_window(), submit()
            └ BjjFighterSnapshotAdapter (F0) -- fighter-keyed read-only views over the same graph
```

* Every simulation command is `BjjPositionGraphMatch.open_window()` (never `open_window_for()`) or `.submit()`.
* Every displayed fact is a detached read of the graph's public views (`state_fields`, `window_fields`, `roles`,
  `action_options`, `response_options`, `selected_commitment`, `status`, `events`, `blocked_transition`) or of the F0 adapter,
  plus static lookups (catalog names, commitment ids, band names).
* The controller keeps only UI state (selected technique/response/commitment, the practice-match serial, the last command's
  message), the pre-rendered text of the last accepted decision (the before/after stamina comparison cannot be recovered later)
  and a deep copy of the last accepted report, which the tests compare with a reference graph (the panel itself does not read
  it). The event log is `graph.events()` itself, not a copy. The scene holds only the controller. The selection fields are public
  UI state; the engine re-validates everything at `submit`, so writing them cannot bypass it.
* Nothing advances in `_process`, `_physics_process`, animations or timers.
* **Controller-level codes:** `no_match`, `match_ended`, `window_already_open`, `no_open_window`, `technique_required`,
  `response_required`, `not_selectable`, `unknown_action`, `unknown_response`, `unknown_commitment`,
  `unsupported_practice_setting`. Every other code (the graph's `halted_unsupported_transition`, option reasons such as
  `setup_not_ready`, `inactive_submission`, `incompatible_ready_response`, and admission errors) is the engine's or graph's own,
  passed through unchanged.

### Exact practice configuration

`BjjMountPracticeController.match_configuration()` is the production stamina policy (Rule 1 ON, Rule 2 OFF, RECOVER, D3-B) plus
the three existing features the qualified graph and gateway suites also enable: setup (`enable_v02_setup`), submissions
(`enable_v03_submissions`) and commitment semantics (`enable_v04_commitment_semantics`). Stalling, Recognition and scoring are not
enabled. `start_new_match` may override only `clock`, `interval`, `axis`, `top_stamina` and `bottom_stamina` (the engine validates
the values); any other key, including `rules`, is refused with `unsupported_practice_setting`.

## 3. Feasibility record (transferable to the owner's HTML matrix)

Gate: concrete need, smallest alternative, benefit, change/maintenance cost, deterministic regression risk, can we live with the
current design, decision.

| # | Candidate | Concrete need | Smallest alternative | Benefit | Cost | Regression risk | Live with current? | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Drive the UI through `BjjPositionGraphMatch` (owner-approved), not the bare gateway | The graph is the real command path: it halts on unsupported exits and logs events; the UI must not bypass it | Bare gateway (no halt/event semantics) | Real position-graph behavior, blocked/terminal states for free | None (existing API) | None | No | **Implement** |
| 2 | Graph `behavior_fields()` pass-through | The F0 adapter needs held behaviors through the graph; the graph keeps its gateway private | Hold the raw gateway beside the graph (lets a caller bypass the halt) | Behavior in snapshots without exposing the gateway | 5 lines, read-only, detached | Very low (pure read; test-compared with the gateway and inertness-checked) | No | **Implement** |
| 3 | Extend `BjjFighterSnapshotAdapter` to accept a graph | One validated snapshot path for both owners | A second adapter class | One mapping, F0 validation preserved | One type check; the private handle becomes `_source: Variant`, which **weakens** the F0 private-member pin (it no longer constrains the type; `create()` carries the guarantee). One F0 expectation string was updated; its assertion count is unchanged at 750 | Low: every F0 gateway-path test passes unchanged; the graph path is compared with the gateway path step by step | No | **Implement** |
| 4 | Generalized position interface for the adapter | None until a second position exists | Mount-specific adapter | Hypothetical | Speculative abstraction | None | Yes | **Defer** |
| 5 | `RefCounted` controller separate from the scene | Testable input handling without rendering | Logic inside the scene script | Headless tests of the whole loop | ~350 lines | None | No | **Implement** |
| 6 | Scripted Bottom = the existing no-action decision | The brief: no invented AI | A response-picking AI | Deterministic, clearly labelled | None | None | Yes | **Implement** (AI rejected). Note the opponent never acts, yet its held behavior still spends and recovers stamina |
| 7 | Opponent response chosen by the player from the engine's admitted responses | The brief: explicit selectable practice response | Auto-pick | Nothing is fabricated | None | None | n/a | **Implement** |
| 8 | Responder commitment (`response_commitment`) control | None requested; the engine's own default applies when it is empty | Expose it | Hypothetical | Another input path | Low | Yes | **Defer** |
| 9 | Expose `open_window_for(duration)` | None; it is a session-owner test seam | n/a | n/a | Lets a UI manufacture windows | High | Yes | **Reject** |
| 10 | `extra` match settings on `start_new_match()` | Short practice matches and engine-driven test states | Hard-coded configuration only | Tests reach terminal states in seconds; later practice options | An allow-list of five keys; the engine validates values; `rules` and `production` cannot be replaced | Low | Mostly | **Implement** (allow-listed) |
| 11 | Project display settings (`window/stretch/mode=canvas_items`, `aspect=expand`) | A tiling window manager forced a 664x352 window on this machine and the unscaled UI was cropped | None (cropped UI) | The whole 2D UI scales into small windows | `[display]` section; only the two stretch lines change behavior (1152x648 are the defaults); no renderer change; affects canvas content only, so the 3D greybox's 3D rendering is unchanged (its HUD label scales) | None for the simulation | No | **Implement** |
| 12 | F0 sample definitions loaded from `res://tests/resources/` | Names from the F0 `.tres` files, per the brief | Copy them into a content folder | No duplicate content | The scene reads a tests path (provisional; an export that drops `tests/` would break the default scene) | None | Yes | **Adapt**: moving content to a real folder is a separate decision |
| 13 | Scene authored as a generated `.tscn` of containers | A real, editable Godot scene | Build nodes in code | Inspector/editor friendly; anchors/containers only | One text scene (a test pins its node types) | None | n/a | **Implement** |
| 14 | Blocked-transition path exercised by the UI | The brief asks the UI to distinguish it | Only render it | Correct display if the engine reaches it | n/a | n/a | n/a | **Render and test through engine-driven states**; see limitations |
| 15 | Offer a Top no-action reset | Not requested | Offer it | Hypothetical | Another path | Low | Yes | **Defer** (the controller requires a technique) |

## 4. Verification

* `tests/test_mount_practice.gd`: **1036 assertions**, negative-first, deterministic, headless, wired into `godot-v1.yml` through
  the existing fail-closed validator (`--name "Mount practice"`, exact pin 1036, a measured value).
* It proves: the graph-backed adapter equals the gateway-backed one step by step and applies the F0 refusal list to the graph path
  (non-sources, duck-typed objects, bad maps, unknown/missing/extra/odd keys, bad definitions) with detachment, inertness and
  role-by-identity preserved; controller refusals (no window, wrong role, unknown/unavailable technique, unknown/unavailable
  response, premature submit, stale and replayed decisions) change nothing and carry the engine's exact codes; the controller's
  reports and resulting graph state equal a separately driven reference graph for eight windows including every commitment
  choice; the scripted Bottom decision equals the engine's no-action path; 50 `view()` reads and 30 scene refreshes are inert; all
  three Mount exits (Half Guard, Open Guard, Reversal) render as blocked with the exact reason and destination, with every
  command refused by the controller and by the graph itself; a tap and a 300-second timeout are rendered as terminal and never as
  blocked; a new match shares nothing with the old one; a response the engine marks `incompatible_ready_response` can neither be
  selected nor submitted, in the controller and through the scene's lists; the practice configuration and the settings allow-list
  are pinned; and the scene is instantiated and played headlessly through its real buttons, lists, commitment widget and the N/S
  hotkeys (including their guards).
* Source-boundary scans keep the presentation code away from the gateway, the match, stamina pools, timers and per-frame hooks,
  and a scan of the scene file allows only 2D Control and container node types. They are tripwires, not proofs.
* During development 49 disposable mutants of the controller, scene, graph pass-through and adapter were all detected (the
  scripts are not committed).
* Pins unchanged: Mount slice 256,992; position registry 431; fighter foundation 750.
* Not covered headlessly: viewport input routing and focus (the tests call the hotkey handler directly; list type-ahead is turned
  off so it cannot swallow N/S), real-window scaling, and visual quality.

## 5. Limitations

* **A human cannot reach a blocked transition through this flow** (derived from the code: only an escape-capable Bottom action
  produces an exit destination, and the player never chooses Bottom actions). The player can only reach a tap or a timeout. The
  blocked state is rendered and tested through engine-driven escapes. Letting the player choose Bottom techniques is a separate decision.
* Fighters are fixed (Test Alpha on top, Test Bravo on the bottom); there is no fighter selection, no scoring, no game plan.
* No art, animation or sound; the layout targets keyboard and mouse on a PC. Long technique names are clipped in the lists (the
  full id is the tooltip) and disabled rows are low-contrast; the reason code always comes first.
* Content definitions still live under `tests/resources/` (see row 12).
* The adapter and controller are Mount-specific, and a bare `BjjPositionGraphMatch.new()` (never produced by `create()`) would
  raise a script error just like a bare gateway. Half Guard and Standing are not implemented and nothing here makes them playable.
* An interactive run needs a display; CI exercises the scene headlessly. Screenshots here were rendered locally.
