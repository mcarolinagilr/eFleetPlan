# 3.1 Configuration loaders
The config loaders read YAML files and return validated Python objects. 
Users do not need to modify these files.
The loaders are called automatically by the notebooks.

## Schedule Config Loader

**Package:** `config.0_supportfiles.config_loader_schedule`

### `load_config`

```python
def load_config(
    env_yaml: str | Path = "config/env.yaml",
    run_yaml: str | Path = "config/run.yaml",
    predefined_dir: str | Path | None = None,
) -> tuple[EnvironmentConfig, RunConfig, PredefinedLibrary]
```

Load and validate all configuration from YAML files for Package 1.

**Parameters:**

- `env_yaml` — path to `env.yaml`
- `run_yaml` — path to the schedule run configuration YAML
- `predefined_dir` — path to the predefined parameter directory (defaults to `predefined/` next to `env.yaml`)

**Returns:** `(EnvironmentConfig, RunConfig, PredefinedLibrary)`

**Raises:**

- `FileNotFoundError` if any YAML file is missing
- `pydantic.ValidationError` if any parameter fails validation

### Data classes

#### `EnvironmentConfig`

Holds simulation environment settings.

| Attribute | Type | Description |
|-----------|------|-------------|
| `seed` | int | Current random seed |
| `original_seed` | int | Original seed (preserved for reference) |
| `gen_start_date` | str | Simulation start date |
| `gen_end_date` | str | Simulation end date |
| `freq` | str | Frequency string |
| `consumption_factor_file` | Path | Path to consumption factor CSV |
| `output_base` | Path | Output directory |

#### `RunConfig`

Defines a single fleet scenario.

| Attribute | Type | Description |
|-----------|------|-------------|
| `schedule_name` | str | Scenario label |
| `n_vehicles` | int | Total vehicle count |
| `schedule_mix` | dict[str, int] | Vehicles per schedule type |
| `vehicle_mix` | dict[str, int] | Vehicles per vehicle model |
| `company_type` | str | Company profile name |
| `custom_schedule` | dict or None | Custom schedule overrides |
| `custom_vehicle` | dict or None | Custom vehicle overrides |
| `custom_company` | dict or None | Custom company overrides |

**Validation:** `schedule_mix` and `vehicle_mix` must each sum to `n_vehicles`.

#### `PredefinedLibrary`

Holds all predefined parameter sets loaded from the `predefined/` directory.

**Methods:**

- `get_schedule(name, custom=None)` — returns a `ScheduleConfig`
- `get_vehicle(name, custom=None)` — returns a `VehicleConfig`
- `get_company(name, custom=None)` — returns a `CompanyConfig`

If `name` is `"custom"`, the corresponding `custom` dict is used instead.

#### `ScheduleConfig`, `VehicleConfig`, `CompanyConfig`

Pydantic models holding the individual parameter sets. See the [Configuration Reference](../configuration/fleetoperation_simulation.md) for field descriptions.

---

## Optimisation Config Loader

**Package:** `config.config_loader_optimisation`

### `load_opt_config`

```python
def load_opt_config(
    run_yaml: str,
    infra_yaml: str,
    env_yaml: str = None,
    project_root: str = None,
) -> tuple[dict, dict, dict, RunOptConfig]
```

Load and validate YAML files for Package 2, then build the data structures that `optimisation()` expects.

**Parameters:**

- `run_yaml` — path to the optimisation run YAML
- `infra_yaml` — path to `infrastructure_configuration.yaml`
- `env_yaml` — path to `env.yaml` (optional; used to fill in dates)
- `project_root` — project root directory (auto-detected if not provided)

**Returns:** `(opt_config, cost_config, power_charge_config, run)`

- `opt_config` (dict) — all data needed by the optimisation function, including pivoted schedule DataFrames and electricity prices
- `cost_config` (dict) — infrastructure costs, financial parameters
- `power_charge_config` (dict) — charger powers, battery limits, charging losses
- `run` (`RunOptConfig`) — validated run settings

### Data classes

#### `RunOptConfig`

| Attribute | Type | Validation |
|-----------|------|------------|
| `schedule_name` | str | — |
| `schedule_number` | int | — |
| `opt_start_date` | str | — |
| `opt_end_date` | str | — |
| `freq` | str | Default `"h"` |
| `delta_time` | float | Default `1.0` |
| `EVs` | int | Must be > 0 |
| `Accumulated_Cycle_Capacity` | float | Default `3500.0` |
| `MIPGap` | float | Must be in (0, 1) |
| `electricity_price_file` | str | — |

#### `InfrastructureConfig`

Validates battery and charging loss parameters.

| Attribute | Type | Validation |
|-----------|------|------------|
| `Charging_losses` | float | Must be in (0, 1] |
| `Battery_Maximum_Limit` | float | Must be in (0, 1] |
| `Battery_Minimum_Limit` | float | Must be in (0, 1] |
