# 1.1. User Guide — Overview

eFleetPlan is organised into two sequential packages. Each Package is run through a dedicated Jupyter notebook. All configuration is done through YAML files — the notebooks themselves require no editing.

## Workflow

```
┌─────────────────────┐      ┌────────────────────────────────┐
│ Configuration YAML  │──────│  Package 1: Co-optimisation    │
│      (config/)      │      │     Operation Modelling        │
└─────────────────────┘      │    (schedule generation)       │
                             └───────────────┬────────────────┘
                                             │ CSV schedules
                                             ▼
                             ┌────────────────────────────────┐
                             │  Package 2: Co-optimisation    │
                             │  (infrastructure + cost        │
                             │   minimisation)                │
                             └───────────────┬────────────────┘
                                             │ Results
                                             ▼
                             ┌────────────────────────────────┐
                             │          Visualisation         │
                             └────────────────────────────────┘
```

## Configuration files

All parameters are included in the `config/` directory. User can/should edit these files before launching the notebooks.

| File | Purpose |
|------|---------|
| `env.yaml` | Global environment: time dates, seed, file paths |
| `run_FleetSchedule_Config.yaml` | LCV fleet definition for operation schedules generation |
| `run_Optimisation_Config.yaml` | Settings for the co-optimisation |

See the [Configuration settings](../configuration) for a full description of parameter predefined.

Predefined parameters 
This should not be changed, user can use custom option to use their specific parameters.

| File | Purpose |
|------|---------|
| `predefined/schedules.yaml` | Predefined schedule profiles |
| `predefined/vehicles.yaml` | Predefined vehicle specifications |
| `predefined/companies.yaml` | Predefined company profiles - distance/stop profiles |
| `predefined/infrastructure_configuration.yaml` | Charger power, investment costs, and battery limits |

See the [Predefined configuration](../configuration/predefined.md) for a full description of parameter predefined.

## Input data

Place these files in `data/Input/` before running:

- **Energy consumption factor file** — a CSV with columns `date` and `Energy Consumption Factor`, providing a daily multiplier for energy consumption (e.g. this file aims to account for seasonal temperature effects). - For package 1
- **Electricity price file** — a CSV with columns `date` (or `Date`) and `Elect_price`, providing hourly electricity prices for the co-optimisation of infrastructure and operation costs. - For package 2.

## Output data

All outputs are saved under `data/Output/<schedule_name>/`, more precisely:

- `<schedule_name>.csv` — the generated fleet schedule (Package 1)
- `Results/` — optimisation results (Package 2), including main variables per hour, summary tables, per-vehicle results
- Visualisation graphs in JPEG format
