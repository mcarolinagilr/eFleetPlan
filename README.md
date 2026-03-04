# eFleetPlan
Co-optimisation tool of charging infrastructure investment and electric fleet operations

**EFleetPlan** is a Python-based open source tool for optimizing charging infrastructure and operations for electric light commercial vehicles (LCVs).

## Authors
Carolina Gil Ribeiro and Jagruti Thakur

## License
This software is licensed under the Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International License (CC BY-NC-SA 4.0).  
See the [LICENSE](./LICENSE) file or visit [https://creativecommons.org/licenses/by-nc-sa/4.0/](https://creativecommons.org/licenses/by-nc-sa/4.0/) for details.


## Citation
If you use eFleetPlan, please cite:
**Gil Ribeiro, C and Thakur, J, eFleetPlan: Co-Optimisation tool of Charging Infrastructure Investment and Fleet Operations, 2025. DOI:xxxxxxx

## Project structure

```
eFleetPlan/
├── config/                          # All configuration files
│   ├── predefined/                  # Predefined parameter sets
│   │   ├── companies.yaml
│   │   ├── infrastructure_configuration.yaml
│   │   ├── schedules.yaml
│   │   └── vehicles.yaml
│   ├── config_loader.py             # Config loader for schedule generation
│   ├── config_loader_optimisation.py# Config loader for optimisation
│   ├── env.yaml                     # Environment settings (paths, dates, seed)
│   ├── run_FleetSchedule_Config.yaml# Schedule generation run configuration
│   └── run_Optimisation_Config.yaml # Optimisation run configuration
├── data/
│   ├── Input/                       # Energy consumption and electricity price files
│   └── Output/                      # Results files
├── docs/                            # Documentation
├── notebooks/
│   ├── 1_Fleet_Operation_Modelling.ipynb
│   └── 2_Co-optimisation.ipynb
├── src/
│   └── efleetplan/
│       ├── _1_schedule/             # Fleet operation modelling package
│       │   ├── generate_graphs.py
│       │   └── schedule_generator.py
│       └── _2_optimisation/         # Co-optimisation package
│           ├── co_optimisation.py
│           └── optimisation_graphs.py
├── pyproject.toml
├── MANIFEST.in
└── mkdocs.yml
```

## Installation instructions

**Option 1** With package folder download

**Step 1.** Create a new environment using "requirements.txt" file.
For Python (Windows), run in the terminal:

    Python -m venv OPTI_env
    OPTI_env\Scripts\activate

    pip install hatch
    pip install .

For  Python (macOS / Linux) run in the terminal:

    Python -m venv OPTI_env
    source OPTI_env/bin/activate

    pip install hatch
    pip install .


**Option 2** Clone directly from GitHub in the command prompt

**Step 1.** Clone the repository:
    cd "[folder path where to save the program folder]"
    git clone "https://github.com/mcarolinagilr/eFleetPlan"
    cd eFleetPlan
    
**Then, repeat Step 1 and Step 2 from the previous option:**
    
    Python -m venv OPTI_env
    source OPTI_env/bin/activate
    pip install hatch
    pip install .

## Gurobi solver instalation
eFleetPlan requires the [Gurobi Optimizer](https://www.gurobi.com/) to solve mathematical optimization problems.
To use the optimisation feature, you need a valid Gurobi license and installation.

```bash
python -m efleetplan
```

This confirms that all dependencies (including Gurobi) are correctly installed.

## eFleetPlan Configurations

**All parameters are configured through YAML files in the `config/` directory. There is no need to edit the notebooks or Python source code.**

### Environment settings — `env.yaml`
Defines global settings such as file paths, simulation period, time resolution, and the random seed.

### Schedule generation — `run_FleetSchedule_Config.yaml`

Controls how fleet operational schedules are generated: the schedule name, number of vehicles, schedule and vehicle mix, and company type. 
User can use predefined parameters or define custom values.

Predefined values are loaded from `config/predefined/`.

### Optimisation — `run_Optimisation_Config.yaml`

Defines settings for the co-optimisation model: which schedule to optimise, fleet size, solver gap tolerance, and infrastructure configuration (Cost and power parameters). User can use predefined parameters or define custom values. 

Predefined values are loaded from `config/predefined/infrastructure_configuration.yaml`.


### Predefined parameter sets — `config/predefined/`

Contains reusable definitions for vehicles, schedules, companies, and infrastructure. These can be extended with new entries as needed.

### Input data — `data/Input/`

Place the following files in this folder before running the tool:

- **Energy consumption file** — energy consumption profiles for the vehicles.
- **Electricity price file** — time-series electricity prices for the simulation period.



## How to use the eFLeetPlan tool

EFleetPlan is run through two Jupyter notebooks. Both notebooks load their configuration from the YAML files described above, so all parameter changes should be made there before launching.

### Fleet Operation Modelling

**Notebook:** `notebooks/1_Fleet_Operation_Modelling.ipynb`

Generates operational schedules (travel and charging patterns) for an electric LCV fleet based on the configured parameters. The notebook validates inputs, runs the generation, and produces visualisations of the resulting schedules.

**Workflow:**
1. Edit `config/env.yaml` and `config/run_FleetSchedule_Config.yaml` with your desired settings.
2. Open the notebook and run all cells.
3. Review the validation checks and output graphs.
4. Outputs are saved to `data/Output/<schedule_name>/`.

### Module 2 — Charging Infrastructure Co-optimisation

**Notebook:** `notebooks/2_Co-optimisation.ipynb`

Solves the cost-minimisation model that jointly optimises charging infrastructure investment and fleet charging operations. Requires Gurobi and a schedule generated by Module 1.

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
Open the notebook for the module you want to run and execute cells from top to bottom.

## Output

Module 1 produces CSV files with the generated fleet schedules and accompanying graphs in `data/Output/<schedule_name>/`.

Module 2 produces several result files in `data/Output/<schedule_name>/Results/`, including the main decision variables, per-vehicle results, summary tables, and hourly aggregated statistics (averages and maxima).








