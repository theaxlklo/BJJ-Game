# Development setup (new Linux machine)

```bash
git clone https://github.com/theaxlklo/BJJ-Game.git && cd BJJ-Game   # or: git pull
python3 tools/setup_dev.py            # read-only check: what is ready, what is missing
python3 tools/setup_dev.py --install  # optional: confirm each safe install one by one
```

The check never installs anything by itself. `--install` needs a terminal, shows the exact commands for each component and
runs them only after you answer `y`. It never uses sudo, never changes system Python packages, never overwrites an existing
configuration and never downloads Godot. Rerunning it is always safe.

| Component | Needed for | If missing |
|---|---|---|
| Python 3.11+ | everything | install through your distribution |
| PyYAML (in the interpreter that runs the runner) | `tools/ci/run_godot_steps.py` | `--install` creates `.venv` and installs `PyYAML>=6` there |
| Godot **4.7.2-stable** Standard (not .NET) | Godot tests | **manual**: the check prints the pinned URL and sha256; verify, unzip, symlink to `~/.local/bin/godot-bjj` (or `export GODOT_BIN=...`) |
| Repo skills `godot-gdscript`, `godot-ui-control`, `systematic-debugging` | Claude Code | ship with the repo: `git pull` |
| Claude Code + `ponytail@ponytail` (recommended) | assistant workflow | Claude Code is manual; `--install` offers the Ponytail marketplace and plugin commands |
| Codex CLI (optional) | none yet | reported only; never installed here |

## Verify

When the check reports **Ready**, run the command it prints. With a project virtual environment that is:

```bash
.venv/bin/python tools/ci/run_godot_steps.py      # every Godot qualification step; use the interpreter that has PyYAML
python3 -m unittest discover -s tools/ci          # CI tooling tests, including the setup checker
PYTHONPATH=src python3 -m unittest discover -s tests   # Python suite, for Python/shared changes
```
