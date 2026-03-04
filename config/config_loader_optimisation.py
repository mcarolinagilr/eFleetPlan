"""
Config loader for the co-optimisation Package (Package 2).

Reads:
  - run_opt.yaml: run-level settings (dates, fleet, solver)
  - infrastructure_configuration.yaml: power/battery parameters + infrastructure costs
  - env.yaml (optional): environment config with simulation dates

"""

import os
import yaml
import pandas as pd
from pydantic import BaseModel, field_validator
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Time resolution converter function
# ---------------------------------------------------------------------------

def _freq_to_delta_t(freq: str) -> float:
    """Convert pandas frequency string → delta_t in hours.  e.g. '15min' → 0.25, 'h' → 1.0."""
    _converter = {"h": 1.0, "30min": 0.5, "15min": 0.25}
    if freq in _converter:
        return _converter[freq]
    if freq.endswith("min"):
        return int(freq[:-3]) / 60.0
    if freq.endswith("h"):
        return float(int(freq[:-1]) if len(freq) > 1 else 1)
    raise ValueError(f"Unsupported freq: '{freq}'. Supported: {list(_converter.keys())} or any '<N>min'")



# ---------------------------------------------------------------------------
# Function for validation
# ---------------------------------------------------------------------------

class RunOptConfig(BaseModel):
    """Validates the run_opt.yaml file."""
    schedule_name: str
    schedule_number: int
    opt_start_date: str
    opt_end_date: str
    freq: str = "h"
    delta_t: float = None                  
    EVs: int
    Accumulated_Cycle_Capacity: float = 3500.0
    MIPGap: float
    electricity_price_file:str


    @field_validator("EVs")
    @classmethod
    def positive_vehicles(cls, v):
        if v <= 0:
            raise ValueError("EVs must be > 0")
        return v

    @field_validator("MIPGap")
    @classmethod
    def valid_gap(cls, v):
        if not 0 < v < 1:
            raise ValueError("MIPGap must be between 0 and 1")
        return v


class InfrastructureConfig(BaseModel):
    """Validates the common power and battery parameters in infrastructure_configuration.yaml."""
    Charging_losses: float
    Battery_Maximum_Limit: float
    Battery_Minimum_Limit: float

    @field_validator("Charging_losses")
    @classmethod
    def valid_efficiency(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Charging_losses must be in (0, 1]")
        return v

    @field_validator("Battery_Maximum_Limit")
    @classmethod
    def max_above_zero(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Battery_Maximum_Limit must be in (0, 1]")
        return v

    @field_validator("Battery_Minimum_Limit")
    @classmethod
    def min_above_zero(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Battery_Minimum_Limit must be in (0, 1]")
        return v


# ---------------------------------------------------------------------------
# Support functions
# read YAML and build dictionaries
# ---------------------------------------------------------------------------



def _read_yaml(path):

    with open(path, "r") as f:
        return yaml.safe_load(f)


def _build_power_dicts(infra_raw):
    """
    From infrastructure_configuration.yaml, extract the power-related
    dicts that optimisation() expects.
    """
    power_charge_config = {
        "Charger_Power": infra_raw['Charger_Power'],
    }
    return power_charge_config


def _build_cost_dicts(infra_raw):
    """
    From infrastructure_configuration.yaml, extract the cost-related
    dicts that optimisation() expects.
    """
    inv_cost = infra_raw['investment cost']
    inst_cost = infra_raw['installation cost']

    # Combine investment + installation per charger type
    infrastructure_cost = {
        k: inv_cost[k] + inst_cost[k]
        for k in inv_cost
    }

    cost_config = {
        "Infrastructure_life":         infra_raw['lifetime'],
        "Discount_rate":               infra_raw['Discount_rate'],
        "Infrastructure_cost":         infrastructure_cost,
        "maintenance_cost":            infra_raw['maintenance cost'],
        "Infrastructure_subscription": infra_raw['Infrastructure_subscription'],
        "Price_FixedrateDT":           infra_raw['Price_FixedrateDT'],
        "Demand_rate":                 infra_raw['Demand_rate'],
        "Price_Fixedrateroute":        infra_raw['Price_Fixedrateroute'],
    }
    return cost_config


# ---------------------------------------------------------------------------
# Main loader function
# ---------------------------------------------------------------------------

def load_opt_config(run_yaml: str,
                    infra_yaml: str,
                    env_yaml: str = None,
                    project_root: str = None):
    """
    Load and validate both YAML files, then build the dictionaries
    that ``optimisation()`` expects.

    Parameters
    ----------
    run_yaml   : path to run_opt.yaml
    infra_yaml : path to infrastructure_configuration.yaml
    env_yaml   : path to env.yaml

    Returns
    -------
    opt_config, cost_config, power_charge_config, run
    """
    
    if project_root is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

 
    run_raw   = _read_yaml(run_yaml)

    if run_raw.get('infrastructure_configurations') == 'custom':
        infra_raw = run_raw         
    else:
        infra_raw = _read_yaml(infra_yaml)
    
    if env_yaml:
        env_raw = _read_yaml(env_yaml)
        sim = env_raw.get('simulation', {})          
        run_raw.setdefault('opt_start_date', sim.get('start_date'))
        run_raw.setdefault('opt_end_date', sim.get('end_date'))
    
    run = RunOptConfig(**run_raw)

    InfrastructureConfig(
        Charging_losses=infra_raw['Charging_losses'],
        Battery_Maximum_Limit=infra_raw['Battery_Maximum_Limit'],
        Battery_Minimum_Limit=infra_raw['Battery_Minimum_Limit'],
    )

    # --- Build power_charge_config ---
    power_charge_config = {
        "Charging_losses":            infra_raw['Charging_losses'],
        "Battery_Maximum_Limit":      infra_raw['Battery_Maximum_Limit'],
        "Battery_Minimum_Limit":      infra_raw['Battery_Minimum_Limit'],
        "Accumulated_Cycle_Capacity": run.Accumulated_Cycle_Capacity,
    }

    # Merge in charger power dict
    power_charge_config.update(_build_power_dicts(infra_raw))

    # --- Build cost configurations ---
    cost_config = _build_cost_dicts(infra_raw)

    # --- Build opt_config ---
    sname = run.schedule_name

    input_folder  = os.path.join(project_root, "data", "Input")
    output_folder = os.path.join(project_root, "data", "Output", sname)


    def _pivot_table(schedule_csv):
        df = pd.read_csv(schedule_csv, parse_dates=['date'])
        return {
            'En_consumption':       df.pivot(index='date', columns='VehicleID', values='Consumption_rate_corrected'),
            'Ev_distance':          df.pivot(index='date', columns='VehicleID', values='Distance_km'),
            'EV_availability': df.pivot(index='date', columns='VehicleID', values='ChargingStation'),
            'Battery_Limitation':   df.pivot(index='date', columns='VehicleID', values='Battery_Capacity_kWh'),
            'PowerRate_Limitation': df.pivot(index='date', columns='VehicleID', values='PowerRating_kW'),
        }

    schedule_csv = os.path.join(project_root, "data", "Output", f"{sname}", f"{sname}.csv")
    vehicle_data = _pivot_table(schedule_csv)

    opt_config = {
        "opt_start_date": run.opt_start_date,
        "opt_end_date":   run.opt_end_date,
        "freq":           run.freq,
        "delta_t":         _freq_to_delta_t(run.freq),  # Convert freq to delta_t
        "Schedule name":  sname,
        "EVs":            run.EVs,

        "output_folder":  output_folder,
        "input_folder":   input_folder,

        # Load the CSV inputs produced by Fleet Operation simulation
        "electricity_price_grid": pd.read_csv(
            os.path.join(input_folder, run.electricity_price_file)
        ),

        # Load the CSV inputs produced by Fleet Operation simulation
        "En_consumption":       vehicle_data['En_consumption'],
        "Ev_distance":          vehicle_data['Ev_distance'],
        "EV_availability": vehicle_data['EV_availability'],
        "Battery_Limitation":   vehicle_data['Battery_Limitation'],
        "PowerRate_Limitation": vehicle_data['PowerRate_Limitation'],

        "MIPGap": run.MIPGap,
    }

    return opt_config, cost_config, power_charge_config, run
