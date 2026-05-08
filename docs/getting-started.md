# Getting started with eFLeetPlan
This page guide the user for installing running the eFleetPlan.

## Prerequisites

- **Python 3.9 or later**
- **Pyomo solver - Gurobi Optimizer** with a valid license (required for Package 2). Academic licences are available at [gurobi.com](https://www.gurobi.com/academia/academic-program-and-licenses/). It is also possible to use other solver incorporated in pyomo.

## Installation

### Step 1. Clone the repository

```bash
git clone https://github.com/carolinagr/eFleetPlan.git
cd eFleetPlan
```

### Step 2. Create a virtual environment

=== "Linux / macOS"

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

=== "Windows"

    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

### Step 3. Install the package

```bash
pip install .
```

This installs eFleetPlan and all its dependencies (NumPy, Pandas, Matplotlib, Pyomo, Pydantic, PyYAML, and others listed in `pyproject.toml`).

### Step 4. Verify the installation

```bash
python -m efleetplan
```

If the command runs without errors, everything is correctly installed — including Gurobi.

### Initial test : A first test can be performed by running the notebooks in the folder Test.

## Project structure

```
eFleetPlan/
├── config/                            # All configuration (YAML)
│   ├── predefined/                    # Reusable parameter sets
│   │   ├── companies.yaml
│   │   ├── infrastructure_configuration.yaml
│   │   ├── schedules.yaml
│   │   └── vehicles.yaml
│   ├── config_loader_schedule.py      # Config loader — schedule Package
│   ├── config_loader_optimisation.py  # Config loader — optimisation Package
│   ├── env.yaml                       # Environment settings
│   ├── run_FleetSchedule_Config.yaml  # Schedule generation run config
│   └── run_Optimisation_Config.yaml   # Optimisation run config
├── data/
│   ├── Input/                         # User-provided input files
│   └── Output/                        # Generated outputs
├── notebooks/
│   ├── 1_Fleet_Operation_simulation.ipynb
│   └── 2_Co-optimisation.ipynb
├── src/efleetplan/                    # Source code
│   ├── _1_schedule/
│   └── _2_optimisation/
└── docs/                              # This documentation
```

## Input data

Before running, place the following files in `data/Input/`:

| File | Description |
|------|-------------|
| `consumption_factor_YYYY.csv` | Daily energy consumption correction factors. Must have columns `date` and `Energy Consumption Factor`. |
| `el_prices_YYYY.csv` | Hourly electricity prices. Must have columns `date` (or `Date`) and `Elect_price`. |

## Running your case study

### Step 1 — Configure the environment

Open `config/env.yaml` and set the simulation period and paths:

```yaml
seed: 42
simulation:
  start_date: "2024-01-01 00:00:00"
  end_date: "2024-12-31 23:00:00"
  freq: "h"
paths:
  consumption_factor_file: "../data/Input/consumption_factor_2024.csv"
  output_base: "../data/Output"
```

### Step 2 — Configure the LCV fleet

Edit `config/run_FleetSchedule_Config.yaml` to define your fleet:

```yaml
schedule_name: "schedule_1"
fleet:
  n_vehicles: 50
  schedule_mix:
    typea: 50
    typeb: 0
  vehicle_mix:
    renault: 25
    toyota: 25
  company_type: distribution
```

### Step 3 — Run Package 1 - Fleet operation modeling package
To generate different schedule per vehicle.

Launch Jupyter and open `notebooks/1_Fleet_Operation_simulation.ipynb`:

```bash
jupyter lab
```

Run all cells. The notebook will load the configuration, generate schedules, validate them, and produce visualisations. Outputs are saved to `data/Output/schedule_1/`.

### Step 4 — Configure the Co-optimisation model

Edit `config/run_Optimisation_Config.yaml`:

```yaml
schedule_name: "schedule_1"
schedule_number: 1
electricity_price_file: "el_prices_2024.csv"
EVs: 50
MIPGap: 0.005
infrastructure_configurations: predefined
```

### Step 5 — Run Package 2 - Co-optimisation

Open `notebooks/2_Co-optimisation.ipynb` and run all cells. Results are saved to `data/Output/schedule_1/Results/`.

## Next steps

- See the [User Guide](user-guide/overview.md) for a detailed walkthrough of both packages.
- See the [Configuration Reference](configuration/environment.md) for a complete description of every YAML parameter.
- See the [Examples & Tutorials](examples.md) for common use cases.
