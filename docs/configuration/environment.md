# 2.1. Environment configurations
**File:** `config/env.yaml`
The environment configuration controls the global simulation settings shared by both packages.

## 2.1.1 Full example
```yaml
seed: 42

#timeplan for simulation and optimisation
simulation:
  start_date: "2024-01-01 00:00:00"
  end_date: "2024-12-31 23:00:00"
  freq: "h" # "h", "30 min", "15min"

paths:
  consumption_factor_file: "../data/Input/consumption_factor_2024.csv"
  output_base: "../data/Output"
  input_for_optimisation: "../data/Output"
```

## 2.1.2 Parameter reference
### Top-level

| Parameter | Type | Description |
|-----------|------|-------------|
| `seed` | int | Random seed for reproducibility. Each vehicle derives its own seed from this value. |

### `simulation` section

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | — | Simulation start datetime in `"YYYY-MM-DD HH:MM:SS"` format. |
| `end_date` | string | — | Simulation end datetime. |
| `freq` | string | `"h"` | Pandas frequency string. `"h"` = hourly timesteps. |

### `paths` section
All paths are resolved relative to the location of `env.yaml`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `consumption_factor_file` | string | Path to the daily energy consumption factor CSV. |
| `output_base` | string | Base directory for all output files. |
| `input_for_optimisation` | string | Directory where Package 1 outputs are stored (used by Package 2). Typically the same as `output_base`. |

## 2.2.3 Notes
- The `freq` parameter must match the resolution of your input data. Currently only hourly (`"h"`) is fully supported.
- Changing the `seed` produces different stochastic schedules while keeping all other parameters fixed — useful for Monte Carlo analysis.
