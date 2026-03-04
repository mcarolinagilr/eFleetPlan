# 3.2. Fleet operation simulation functions

**Package:** `src.efleetplan._1_schedule.schedule_generation`

## `generate_fleet_schedules`

```python
def generate_fleet_schedules(
    env: EnvironmentConfig,
    run: RunConfig,
    predefined: PredefinedLibrary,
) -> pd.DataFrame
```

Generate schedules for the full fleet and save to CSV.

This is the main entry point for Package 1. It iterates over all vehicles in the fleet, resolves their schedule/vehicle/company configurations from the predefined library, generates each vehicle's schedule using `ScheduleGenerator`, and concatenates the results.

**Parameters:**

- `env` — environment configuration (dates, seed, paths)
- `run` — fleet scenario (vehicle count, mix, company type)
- `predefined` — predefined parameter library loaded from YAML

**Returns:** `pd.DataFrame` — combined schedule for all vehicles, with one row per vehicle per timestep.

**Side effects:** saves the schedule CSV to `<output_base>/<schedule_name>/<schedule_name>.csv`.

**Seeding:** each vehicle gets a deterministic seed: `vehicle_index * 1000 + env.original_seed`.

---

## `ScheduleGenerator`

```python
class ScheduleGenerator(env, sc, vc, cc, vehicle_id="0", schedule_type="typea")
```

Generates a probabilistic driving/charging schedule for a single vehicle.

**Parameters:**

- `env` (`EnvironmentConfig`) — simulation environment
- `sc` (`ScheduleConfig`) — schedule timing parameters
- `vc` (`VehicleConfig`) — vehicle energy parameters
- `cc` (`CompanyConfig`) — company distance/stop parameters
- `vehicle_id` (str) — identifier for this vehicle
- `schedule_type` (str) — `"typea"` for continuous schedule, `"typeb"` for two-part schedule with break

### `generate_schedule()`

```python
def generate_schedule(self) -> pd.DataFrame
```

Generate the full schedule for this vehicle. Dispatches to the appropriate generation method based on `schedule_type`.

**Returns:** `pd.DataFrame` with columns: `date`, `Distance_km`, `Consumption_kWh`, `Consumption_rate_corrected`, `Location`, `ChargingStation`, `ID`, `Battery_Capacity_kWh`, `PowerRating_kW`, `consumption_factor`.

### Key internal methods

These are not typically called directly, but are documented for reference:

| Method | Description |
|--------|-------------|
| `_generate_continuous()` | Generates a Type A (single-trip) schedule |
| `_generate_with_break()` | Generates a Type B (two-trip with break) schedule |
| `_sample_time(mean, dev, min_t, max_t)` | Samples a random hour/minute from a normal distribution, snapped to 15-min slots |
| `_sample_lognormal_distance(mean, std)` | Samples a daily distance from a lognormal distribution |
| `_sample_consumption_rate(distance)` | Samples an energy consumption rate (kWh/km) |
| `_set_driving_step(...)` | Fills driving-state values for a timestep |
| `_set_depot_step(...)` | Fills depot-state values for a timestep |
| `_apply_emergency_trip(...)` | Adds a rare emergency trip at end of day (Type B) |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `TIME_SLOTS` | `[0, 15, 30, 45]` | Valid minute values for time sampling |
| `PAUSE_MIN_DURATION` | `15` | Minimum break duration in minutes |
| `STOP_TIME_FACTOR` | `0.25` | Time per stop in hours |
| `STOP_IMPACT_ON_RETURN` | `0.1` | Additional return delay per stop in hours |
