# eFleetPlan 
# Co-optimisation tool for charging infrastructure investment and electric fleet operations

---

## What is eFleetPlan?
eFleetPlan is a Python-based tool for jointly optimising charging infrastructure and operations for electric light commercial vehicles (LCVs). It combines probabilistic fleet schedule generation with a mixed-integer cost-minimisation model to determine the optimal infrastructure investment and charging strategy for a given fleet.

The tool is designed for researchers, fleet operators, and energy planners investigating the transition to electric commercial vehicles.

## Key features

- **FLeet operation silulation - a probabilistic schedule generation** — creates realistic hourly driving and charging patterns for heterogeneous fleets using configurable statistical distributions.
- **Infrastructure co-optimisation module** — solves a mixed-integer linear programme (MILP) that simultaneously determines the optimal number and type of chargers, charging schedules, and energy procurement strategy.
- **YAML-based configuration** — all parameters are defined in human-readable YAML files. No code editing required to set up and run scenarios.
- **Modular architecture** — Package 1 (schedule generation) and Package 2 (co-optimisation) can be run independently or together.
- **Built-in visualisation** — automatic generation of summary graphs for both packages.

## How it works

eFleetPlan consists of two packages:

**Package 1 — Fleet operation simulation** generates operational schedules for each vehicle in a fleet. It samples departure/return times, distances, energy consumption, and stop patterns from configurable probability distributions, producing hourly time-series over a full simulation period.

**Package 2 — Charging infrastructure co-optimisation** takes the generated schedules and solves a cost-minimisation problem using the Gurobi solver. The model jointly decides the number and type of charging stations (slow, fast, ultra-fast, and route chargers), the hourly charging profile for each vehicle, and the energy procurement from the grid — minimising total annualised infrastructure and electricity costs.

## Quick start

```bash
git clone https://github.com/carolinagr/eFleetPlan.git
cd eFleetPlan
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install .
```

Then edit the YAML files in `config/` and run the Jupyter notebooks in `notebooks/`. See the [Getting Started](getting-started.md) guide for details.

## Authors

Carolina Gil Ribeiro and Jagruti Thakur

## Citation

If you use eFleetPlan, please cite:

> Gil Ribeiro, C. and Thakur, J., *eFleetPlan: Co-Optimisation Tool for Charging Infrastructure Investment and Fleet Operations*, 2025. DOI: *forthcoming*

## License

Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International (CC BY-NC-SA 4.0).
See the [LICENSE](https://creativecommons.org/licenses/by-nc-sa/4.0/) for details.
