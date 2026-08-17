# eFleetPlan
Co-optimisation tool of charging infrastructure investment and electric fleet operations

**EFleetPlan** is a Python-based open source tool for optimizing charging infrastructure and operations for electric light commercial vehicles (LCVs).

## Authors
Carolina Gil Ribeiro and Jagruti Thakur

## License
This software is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.


## Citation
If you use eFleetPlan, please cite:

> Gil Ribeiro, C. and Thakur, J., *eFleetPlan: Co-optimisation of charging infrastructure investment and electric fleet operations*, SoftwareX, 2026, Article 102748. DOI: [10.1016/j.softx.2026.102748](https://doi.org/10.1016/j.softx.2026.102748)

## Project structure

```
eFleetPlan/
├── config/                          # All configuration files
│   ├── predefined/                  # Predefined parameter sets
│   │   ├── companies.yaml
│   │   ├── infrastructure_configuration.yaml
│   │   ├── schedules.yaml
│   │   └── vehicles.yaml
│   ├── env.yaml                     # Environment settings 
│   ├── run_FleetSchedule_Config.yaml# Schedule generation run configuration
│   └── run_Optimisation_Config.yaml # Optimisation run configuration
├── data/
│   ├── Input/                       # Energy consumption and electricity price files
│   └── Output/                      # Results files
├── docs/                            # Documentation
├── notebooks/
│   ├── 1_Fleet_Operation_simulation.ipynb
│   └── 2_Co-optimisation.ipynb
├── src/
│   └── efleetplan/
│       ├── _1_schedule/             # Fleet operation simulation package
│       │   ├── generate_graphs.py
│       │   └── schedule_generation.py
│       └── _2_optimisation/         # Co-optimisation package
│           ├── co_optimisation.py
│           └── optimisation_graphs.py
├── pyproject.toml
├── MANIFEST.in
└── mkdocs.yml
```

## Installation instructions

### Prerequisites

- Python 3.9 or later
- Solver for optimisation: default is [Gurobi Optimizer](https://www.gurobi.com/) with a valid license but can be changed for other solver in the co_optimisation.py file 

There are two ways to install eFleetPlan, depending on what you want to do.

### Option A — From GitHub (clone the repo)

Use this to run the example notebooks, reproduce the paper's illustrative examples, or edit the source code.

**Step 1 — Clone the repository**

```bash
git clone https://github.com/mcarolinagilr/efleetplan.git
cd efleetplan
```

**Step 2 — Create a virtual environment and install**

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install .
```

**Step 3 — Verify the installation**

```bash
python -m efleetplan
```

This confirms that all dependencies (including Gurobi) are correctly installed.

### Option B — From PyPI (use as a library)

Use this to call eFleetPlan's functions from your own code, without cloning the repository.

**Step 1 — Create a virtual environment and install**

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install efleetplan
```

**Step 2 — Create your config folder**

```bash
efleetplan-start
```

Prompts for a destination folder and copies editable YAML templates there (`env.yaml`, run configs, the predefined vehicle/schedule/company/infrastructure library, and the illustrative example configs). Edit those, then supply your own energy consumption factor and electricity price CSVs.

**Step 3 — Use it**

```python
from efleetplan import load_scheduler_config, generate_fleet_schedules

env, run, predefined = load_scheduler_config(
    env_yaml="config/env.yaml",
    run_yaml="config/run_FleetSchedule_Config.yaml",
)
schedule = generate_fleet_schedules(env, run, predefined)
```

## eFleetPlan Configurations

**All parameters are configured through YAML files in the `config/` directory. There is no need to edit the notebooks or Python source code.**

### Environment settings — `env.yaml`
Defines global settings such as file paths, simulation period, time resolution, and the random seed.

### Schedule generation — `run_FleetSchedule_Config.yaml`

Controls how fleet operational schedules are generated: the schedule name, number of vehicles, schedule and vehicle mix, and company type. 
User can use predefined parameters or define custom values.

Predefined values are loaded from `config/_1_predefined/`.

### Optimisation — `run_Optimisation_Config.yaml`

Defines settings for the Co-optimisation model: which schedule to optimise, fleet size, solver gap tolerance, and infrastructure configuration (Cost and power parameters). User can use predefined parameters or define custom values. 

Predefined values are loaded from `config/_1_predefined/infrastructure_configuration.yaml`.


### Predefined parameter sets — `config/_1_predefined/`

Contains reusable definitions for vehicles, schedules, companies, and infrastructure. These can be extended with new entries as needed.

### Input data — `data/Input/`

Place the following files in this folder before running the tool:

- **Energy consumption factor file** — energy consumption factor, that is linked to the environment temperature.
- **Electricity price file** — time-series electricity prices for the simulation period.



## How to use the eFLeetPlan tool

EFleetPlan is run through two Jupyter notebooks. Both notebooks load their configuration from the YAML files described above, so all parameter changes should be made there before launching.

### Fleet Operation simulation

**Notebook:** `notebooks/1_Fleet_Operation_simulation.ipynb`

Generates operational schedules (travel and charging patterns) for an electric LCV fleet based on the configured parameters. The notebook validates inputs, runs the generation, and produces visualisations of the resulting schedules.

**Workflow:**
1. Edit `config/env.yaml` and `config/run_FleetSchedule_Config.yaml` with your desired settings.
2. Open the notebook and run all cells.
3. Review the validation checks and output graphs.
4. Outputs are saved to `data/Output/<schedule_name>/`.

### Package 2 — Charging Infrastructure Co-optimisation

**Notebook:** `notebooks/2_Co-optimisation.ipynb`

Solves the cost-minimisation model that jointly optimises charging infrastructure investment and fleet charging operations. Requires Gurobi and a schedule generated by Package 1.

**Workflow:**
1. Edit `config/run_Optimisation_Config.yaml` with the target schedule and solver settings.
2. Open the notebook and run all cells.
3. Review the optimisation results and summary visualisations.
4. Results are saved to `data/Output/<schedule_name>/Results/`.

### Running the notebooks

```bash
# From the project root
jupyter lab
# or
jupyter notebook
```
Open the notebook for the Package you want to run and execute cells from top to bottom.

## Output

Package 1 produces CSV files with the generated fleet schedules and accompanying graphs in `data/Output/<schedule_name>/`.

Package 2 produces several result files in `data/Output/<schedule_name>/Results/`, including the main decision variables, per-vehicle results, summary tables, and hourly aggregated statistics (averages and maxima).








