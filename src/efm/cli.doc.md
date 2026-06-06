# `cli.py` — EFM CLI

What: Typer-based command-line interface (`efm up`, `efm down`, `efm status`).

Dependencies: `config.py`, `http_mock.py`, `db_mock.py`, `process.py`

Config values: None hard-coded; everything comes from the YAML config.

Caveats: `efm up` spawns background processes; on macOS `start_new_session`
places them in a new process group so `efm down` can kill them cleanly.
