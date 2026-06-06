# `process.py` — Process Management

What: Tracks mock-service PIDs in `/tmp/efm-<name>.pid` and provides
start/stop/list helpers.

Dependencies: None beyond stdlib.

Caveats: `kill_service` sends `SIGTERM`; background processes started with
`start_new_session=True` so they survive the CLI exit but can be killed
 cleanly by their PID.
