# 2.2. Fleet Operation simulation configurations
**File:** `config/run_FleetSchedule_Config.yaml`
This file defines one fleet profile for Package 1. Create a separate file for different profiles, if you want to generate different fleets profiles schedules (e.g. `run_schedule1.yaml`, `run_schedule2.yaml`).

## Example

```yaml
schedule_name: "schedule_1"

fleet:
  n_vehicles: 50
  schedule_mix:
    typea: 50
    typeb: 0
    custom: 0
  vehicle_mix:
    renault: 25
    toyota: 25
    custom: 0
  company_type: distribution

# Custom parameters (used only when a mix entry is set to "custom")
custom_schedule:
  dep_mean_wd: 8
  dep_dev_wd: 1
  ret_mean_wd: 18
  ret_dev_wd: 1
  # ... (see full parameter list below)

custom_vehicle:
  consumption_mean: 0.2
  consumption_std: 0.1
  consumption_min: 0.1
  consumption_max: 0.3
  total_cons_clip: 45
  battery_capacity: 45
  charging_power: 60

custom_company:
  avg_distance_wd: 120
  dev_distance_wd: 15

  # ... (see full parameter list below)
```

## Parameters

### Top-level

| Parameter | Type | Description |
|-----------|------|-------------|
| `schedule_name` | string | Label for this run. Used as the output folder name under `data/Output/`. |

### `fleet` section

| Parameter | Type | Description |
|-----------|------|-------------|
| `n_vehicles` | int (> 0) | Total number of vehicles in the fleet. |
| `schedule_mix` | dict | Number of vehicles per schedule type. Keys must match entries in `predefined/schedules.yaml` or be `custom`. Values must sum to `n_vehicles`. |
| `vehicle_mix` | dict | Number of vehicles per vehicle model. Keys must match entries in `predefined/vehicles.yaml` or be `custom`. Values must sum to `n_vehicles`. |
| `company_type` | string | Company profile name. Must match a key in `predefined/companies.yaml` or be `custom`. |

### Schedule parameters (predefined or custom)

These are the fields in `predefined/schedules.yaml` or in the `custom_schedule` block. All times are in decimal hours (e.g. 8.5 = 08:30).

**Weekday departure/return (Type A and B):**

| Parameter | Description |
|-----------|-------------|
| `dep_mean_wd` | Average departure time during weekdays  |
| `dep_dev_wd` | Standard deviation of departure time during weekdays  |
| `min_dep` | Minimum allowed departure time  |
| `max_dep` | Maximum allowed departure time  |
| `ret_mean_wd` | Average return time during weekdays  |
| `ret_dev_wd` | Standard deviation of return time during weekdays  |
| `min_return_hour` | Minimum allowed departure time |
| `max_return_hour` | Maximum allowed return time  |

**Weekend departure/return:**

| Parameter | Description |
|-----------|-------------|
| `dep_mean_we` | Average departure time during weekend days  |
| `dep_dev_we` | Standard deviation of departure time during weekend days |
| `ret_mean_we` | Average return time during weekend days |
| `ret_dev_we` | Standard deviation of return time during weekend days |

**Parameters for schedules with two parts/ with break (Type B only):**

| Parameter | Description |
|-----------|-------------|
| `pause_beg_mean_wd` | Average weekday break start hour |
| `pause_beg_dev_wd` | Standard deviation of break start hour|
| `pause_end_mean` | Average break end hour |
| `pause_end_dev` | Standard deviation of break end hour|
| `max_beg_time` / `min_beg_time` | Limits the time for break start|
| `max_pause_end` / `min_pause_end` | Limits the time for break end |
| `pause_time_mean` / `pause_time_dev` | Average and Standard deviation of break duration |
| `pause_beg_mean_we` / `pause_beg_dev_we` | Weekend break start average and Standard deviation distribution |
| `prob_emergency` | Probability of an emergency trip at end of day |

### Vehicle parameters (predefined or custom)

| Parameter | Type | Description |
|-----------|------|-------------|
| `consumption_mean` | float (> 0) | Average electricity consumption rate (kWh/km) |
| `consumption_std` | float (> 0) | Standard deviation of electricity consumption rate (kWh)|
| `consumption_min` | float (> 0) | Minimum electricity consumption rate (kWh)|
| `consumption_max` | float (> 0) | Maximum electricity consumption rate (kWh)|
| `total_cons_clip` | float (> 0) | Maximum electricity consumption per time step (kWh)|
| `battery_capacity` | float (> 0) | Battery capacity (kW) |
| `charging_power` | float (> 0) | Maximum charging power (kW) |

### Company parameters (predefined or custom)

| Parameter | Type | Description |
|-----------|------|-------------|
| `avg_distance_wd` | float (> 0) | Average distance travelled during weekdays  (km) |
| `dev_distance_wd` | float (> 0) | Standard deviation of distance travelled during weekdays  |
| `avg_distance_we` | float (> 0) | Average distance travelled during weekend days (km) |
| `dev_distance_we` | float (> 0) | SStandard deviation of distance travelled during weekend days  |
| `min_distance` | float (>= 0) | Minimum daily distance travelled (km) |
| `max_distance` | float (> 0) | Maximum daily distance travelled (km) |
| `min_distance_per_step` | float (>= 0) | Minimum distance travelled per time step (km) |
| `max_distance_per_step` | float (> 0) | Maximum distance travelled per time step  (km) |
| `avg_stops` | float (>= 0) | Average number of stops per day |
| `dev_stops` | float (>= 0) | Standard deviation of number of stops per day |

## Validation

The config loader validates all parameters on load using Pydantic:

- `n_vehicles` must be positive
- `schedule_mix` and `vehicle_mix` must each sum to `n_vehicles`
- All vehicle numeric parameters must be positive
- If any mix entry is set to `custom`, the corresponding `custom_*` block must be present
