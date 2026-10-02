from bjj_game.interfaces import cli as _cli
from bjj_game.interfaces.cli import *  # noqa: F401,F403
from bjj_game.interfaces.cli import (  # explicit compatibility for tested internal helpers
    _choose_entity,
    _print_summary,
    _read_input,
    _tee_to_log,
)


def main(argv: list[str] | None = None) -> int:
    """Legacy Mount-v0 CLI: no commitment prompt and no stamina spending."""
    return _cli.main(argv, commitment_enabled=False)
