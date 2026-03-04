# 1.2. Package 1 — Fleet Operation simulation

Package 1 generates probabilistic operational schedules for an electric LCV fleet. For each vehicle in the fleet, it produces an hourly time-series of distance travelled, energy consumption, and depot availability over the full simulation period.

**Notebook:** `notebooks/1_Fleet_Operation_simulation.ipynb`

## What the Package does

For every vehicle and every hour in the simulation period, the schedule generator determines:

- Whether the vehicle is driving or at the depot (available for charging)
- The distance driven (km)
- The energy consumed (kWh), adjusted by a seasonal consumption factor
- The battery capacity and charging power rating available

The generator uses probability distributions (normal and lognormal) to sample departure times, return times, daily distances, and consumption rates. This creates realistic, heterogeneous schedules across the fleet.

## Schedule types

eFleetPlan supports two schedule structures:

**Type A — Continuous trip.** The vehicle departs once, drives throughout the day with multiple stops, and returns once in the evening. Parameters control the departure/return time distributions for weekdays and weekends.

**Type B — Two-part trip with break.** The vehicle makes two trips per day, separated by a depot break (e.g., morning delivery run, lunch break at depot, afternoon run). Additional parameters control the break timing.

The schedule type for each vehicle is determined by the `schedule_mix` in the run configuration.

## Step-by-step walkthrough

### 1. Edit the configuration files

**`config/env.yaml`** — set the simulation dates, random seed, and paths to your input files.

**`config/run_FleetSchedule_Config.yaml`** — define:

- `schedule_name` — a label for this scenario (used as the output folder name)
- `fleet.n_vehicles` — total number of vehicles
- `fleet.schedule_mix` — how many vehicles use each schedule type (must sum to `n_vehicles`)
- `fleet.vehicle_mix` — how many vehicles of each vehicle model (must sum to `n_vehicles`)
- `fleet.company_type` — the company distance/stop profile to use

### 2. Open the notebook

```bash
jupyter lab
# Open notebooks/1_Fleet_Operation_simulation.ipynb
```

### 3. Run the cells

The notebook is structured as follows:

1. **Import dependencies** — loads required libraries and the config loaders.
2. **Load configuration** — reads all YAML files and displays the resolved parameters. Check that the values match your intent.
3. **Validation tests** — runs input parameter validation checks (e.g., no negative battery capacities).
4. **Generate schedules** — calls `generate_fleet_schedules()` to create the full fleet schedule. A progress log shows each vehicle as it completes.
5. **Validation checks** — verifies that each vehicle has the expected number of timesteps and that values are within bounds.
6. **Visualisation** — generates summary graphs:
    - Average number of vehicles at depot per hour of day
    - Average total energy consumption per hour of day

### 4. Review outputs

Outputs are saved to `data/Output/<schedule_name>/`:

- `<schedule_name>.csv` — the complete schedule with one row per vehicle per timestep
- Graphs in JPEG format

The CSV contains the following columns:

| Column | Description |
|--------|-------------|
| `date` | Timestamp |
| `VehicleID` | Vehicle identifier |
| `Distance_km` | Distance driven in this timestep (km) |
| `Consumption_kWh` | Energy consumed in this timestep (kWh) |
| `Consumption_rate_corrected` | Consumption rate adjusted by seasonal factor (kWh/km) |
| `ChargingStation` | 1 if at depot (available for charging), 0 if driving |
| `Location` | 1 = depot, 0 = on road |
| `Battery_Capacity_kWh` | Battery capacity of this vehicle (kWh) |
| `PowerRating_kW` | Charging power rating of this vehicle (kW) |
| `ScheduleType` | Schedule type used (typea, typeb, etc.) |
| `VehicleType` | Vehicle model (renault, toyota, etc.) |
| `CompanyType` | Company profile used |

## Running multiple scenarios

You can generate schedules for multiple fleet configurations by creating additional `run_*.yaml` files and listing them in the notebook's generation cell:

```python
run_files = [
    'run_schedule1.yaml',
    'run_schedule2.yaml',
    'run_schedule3.yaml',
]
```

Each run file produces an independent output folder under `data/Output/`.

## Tips

!!! tip "Reproducibility"
    Each vehicle gets a deterministic seed derived from `env.seed` and its vehicle index. To reproduce an exact schedule, keep the same seed and configuration.

!!! tip "Custom parameters"
    If the predefined schedule, vehicle, or company profiles don't match your case, set any mix entry to `custom` and provide the custom parameters in the same run YAML. See the [Configuration Reference](../configuration/fleetoperation_simulation.md) for details.
