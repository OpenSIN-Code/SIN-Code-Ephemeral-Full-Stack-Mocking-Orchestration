# `config.py` — YAML Config Parser

What: Reads EFM YAML (or JSON) configs and validates the `services` list.

Dependencies: PyYAML (`pip install pyyaml`)

Usage:
```python
from efm.config import load_config, validate_config
cfg = load_config("mock_config.yaml")
validate_config(cfg)
```

Caveats: If PyYAML is missing, raises `RuntimeError` with an install hint.
