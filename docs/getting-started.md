# Getting started with eFLeetPlan
This page guide the user for installing running the eFleetPlan.

## Prerequisites

- **Python 3.9 or later**
- **Pyomo solver - Gurobi Optimizer** with a valid license (required for Package 2). Academic licences are available at [gurobi.com](https://www.gurobi.com/academia/academic-program-and-licenses/). It is also possible to use other solver incorporated in pyomo.

## Installation

There are two ways to install eFleetPlan, depending on what you want to do.

=== "Option A — From GitHub (clone the repo)"

    Use this if you want to run the example notebooks, reproduce the paper's illustrative examples, or edit the source code.

    #### Step 1. Clone the repository

    ```bash
    git clone https://github.com/mcarolinagilr/efleetplan.git
    cd efleetplan
    ```

    #### Step 2. Create a virtual environment

    **Linux / macOS:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

    **Windows:**

    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

    #### Step 3. Install the package

    ```bash
    pip install .
    ```

    This installs eFleetPlan and all its dependencies (NumPy, Pandas, Matplotlib, Pyomo, Pydantic, PyYAML, and others listed in `pyproject.toml`), and includes the `notebooks/`, `test/`, and `config/` folders from the repo.

    #### Step 4. Verify the installation

    ```bash
    python -m efleetplan
    ```

    If the command runs without errors, everything is correctly installed — including Gurobi.

    #### Initial test

    A first test can be performed by running the notebooks in the `test/` folder.

=== "Option B — From PyPI (use as a library)"

    Use this if you just want to call eFleetPlan's functions (`generate_fleet_schedules`, `optimisation`, etc.) from your own code, without cloning the repository.

    #### Step 1. Create a virtual environment

    **Linux / macOS:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

    **Windows:**

    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

    #### Step 2. Install the package

    ```bash
    pip install efleetplan
    ```

    #### Step 3. Create your config folder

    ```bash
    efleetplan-start
    ```

    This prompts for a destination folder and copies editable YAML templates there (`env.yaml`, `run_FleetSchedule_Config.yaml`, `run_Optimisation_Config.yaml`, the predefined vehicle/schedule/company/infrastructure library, and the illustrative example configs). Edit those files to define your fleet, then supply your own energy consumption factor and electricity price CSVs (see [Input data](#input-data) below).

    #### Step 4. Verify the installation

    ```bash
    python -c "from efleetplan import generate_fleet_schedules; print('OK')"
    ```

    Unlike Option A, this does not include the `notebooks/` or `test/` folders — call the functions directly from your own scripts, e.g.:

    Package 1 — generate fleet operation schedules:

    ```python
    from efleetplan import load_scheduler_config, generate_fleet_schedules

    env, run, predefined = load_scheduler_config(
        env_yaml="config/env.yaml",
        run_yaml="config/run_FleetSchedule_Config.yaml",
    )
    schedule = generate_fleet_schedules(env, run, predefined)
    ```

    Package 2 — co-optimise charging infrastructure and operations, using the same `env` object so both packages agree on where inputs/outputs live:

    ```python
    from efleetplan import load_opt_config, optimisation, save_results

    opt_config, cost_config, power_config, opt_run = load_opt_config(
        run_yaml="config/run_Optimisation_Config.yaml",
        infra_yaml="config/_1_predefined/infrastructure_configuration.yaml",
        env_yaml="config/env.yaml",
        input_folder=env.consumption_factor_file.parent,
        scheduler_output=env.output_base,     # where Package 1's schedule CSV is read from
        # optimisation_output=...,            # optional: where results are written; defaults to scheduler_output/Results
    )
    m, Price, EV_availability, Distance_km, days = optimisation(opt_config, cost_config, power_config)

    optimisation_output = opt_config["optimisation_output"]
    save_results(
        m, Price, EV_availability, Distance_km,
        csv_file_pathA=optimisation_output / "results_main_variables.csv",
        csv_file_pathB=optimisation_output / "results_summary.csv",
        csv_file_pathC=optimisation_output / "results_per_EV.csv",
        cost_config=cost_config, power_config=power_config, days=days,
    )
    ```

    `scheduler_output` and `optimisation_output` are independent — pass a different `optimisation_output` to run the optimisation standalone against schedules produced elsewhere while writing results somewhere else entirely.

## Project structure

```
eFleetPlan/
├── config/                                     # All configuration (YAML)
│   ├── _1_predefined/                          # Reusable parameter sets
│   │   ├── companies.yaml
│   │   ├── infrastructure_configuration.yaml
│   │   ├── schedules.yaml
│   │   └── vehicles.yaml
│   ├── _2_Ilustrative_examples/                # Files to reproduce the examples of software x paper
│   ├── env.yaml                                # Environment settings
│   ├── run_FleetSchedule_Config.yaml           # Schedule generation run config
│   └── run_Optimisation_Config.yaml            # Optimisation run config
├── data/
│   ├── Input/                                  # User-provided input files
│   └── Output/                                 # Generated outputs
├── docs/                                       # eFleetPlan documentation
├── site/                                       # Folder with files for the documentation site
├── notebooks/
│   ├── 1_Fleet_Operation_simulation.ipynb
│   └── 2_Co-optimisation.ipynb
├── src/efleetplan/                             # Source code (installable package)
│   ├── _1_fleetoperation_simulation/           # incl. config_loader_schedule.py
│   ├── _2_co_optimisation/                     # incl. config_loader_optimisation.py
│   ├── _config_templates/                      # YAML templates copied by `efleetplan-start`
│   └── _cli.py                                 # `efleetplan-start` command
└── test/                                       # files to perform a simples and fast test
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
