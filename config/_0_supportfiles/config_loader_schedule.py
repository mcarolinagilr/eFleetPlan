"""
config_loader.py
================
This file aims to load all YAML configurations that will support the Fleet Operation simulation
-----
    In the notebook runner or in the executer file the user needs to call:

        from config_loader_schedule import load_config

        env, run, predefined = load_config(
        env_yaml=os.path.join(config_dir, 'env.yaml'), # location of environment parameters
        run_yaml=os.path.join(config_dir, 'run.yaml'), # location of Fleet Operation simulation parameters
        predefined_dir=os.path.join(config_dir, '_1_predefined'), # location of predefined parameters
    )
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Load all necessary YAML files linked to the fleet operation simulation package
# =============================================================================

def _load_yaml(path: Path) -> dict:
    """Read a YAML file and return a Python dict. errors: Raises FileNotFoundError if missing."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _resolve_path(relative: str, base_dir: Path) -> Path:
    """Resolve a path relative to a base directory. Absolute paths pass through unchanged."""
    p = Path(relative)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


# =============================================================================
# Config models — Schedule, Vehicle, Company
# =============================================================================

class ScheduleConfig(BaseModel):
    """
    Schedule time parameters 
    """
    model_config = {"extra": "forbid"}

    # Weekday departure
    dep_mean_wd: float | None = None
    dep_dev_wd: float | None = None
    min_dep: float | None = None
    max_dep: float | None = None

    # Weekday return
    ret_mean_wd: float | None = None
    ret_dev_wd: float | None = None
    min_return_hour: float | None = None
    max_return_hour: float | None = None

    # Weekend departure
    dep_mean_we: float | None = None
    dep_dev_we: float | None = None

    # Weekend return
    ret_mean_we: float | None = None
    ret_dev_we: float | None = None

    # Pause / break parameters (Type B schedules)
    pause_beg_mean_wd: float | None = None
    pause_beg_dev_wd: float | None = None
    pause_end_mean: float | None = None
    pause_end_dev: float | None = None
    max_beg_time: float | None = None
    min_beg_time: float | None = None
    max_pause_end: float | None = None
    min_pause_end: float | None = None
    pause_time_mean: float | None = None
    pause_time_dev: float | None = None

    pause_beg_mean_we: float | None = None
    pause_beg_dev_we: float | None = None

    prob_emergency: float | None = None


class VehicleConfig(BaseModel):
    """
    Vehicle energy consumption and battery parameters.
    """

    model_config = {"extra": "forbid"}

    consumption_mean: float = Field(gt=0, description="Average consumption in kWh/km")
    consumption_std: float = Field(gt=0, description="Standard deviation of consumption in kWh/km")
    consumption_min: float = Field(gt=0, description="Minimum consumption rate")
    consumption_max: float = Field(gt=0, description="Maximum consumption rate")
    total_cons_clip: float = Field(gt=0, description="Max kWh per timestep")
    battery_capacity: float = Field(gt=0, description="Battery capacity in kWh")
    charging_power: float = Field(gt=0, description="Charging power in kW")


class CompanyConfig(BaseModel):
    """
    Company distance and stop parameters.
    """
    model_config = {"extra": "forbid"}

    avg_distance_wd: float = Field(gt=0, description="Average weekday distance in km")
    dev_distance_wd: float = Field(gt=0, description="Standard deviation weekday distance")
    avg_distance_we: float = Field(gt=0, description="Average weekend distance in km")
    dev_distance_we: float = Field(gt=0, description="Standard deviation weekend distance")
    min_distance: float = Field(ge=0, description="Minimum daily distance in km")
    max_distance: float = Field(gt=0, description="Maximum daily distance in km")
    min_distance_per_step: float = Field(ge=0, description="Minimum distance per timestep in km")
    max_distance_per_step: float = Field(gt=0, description="Maximum distance per timestep in km")
    avg_stops: float = Field(ge=0, description="Average number of stops per day")
    dev_stops: float = Field(ge=0, description="Standard deviation of stops per day")


# =============================================================================
# Environment config
# =============================================================================

class EnvironmentConfig(BaseModel):
    """environment — dates, seed, file paths."""
    model_config = {"extra": "forbid"}

    seed: int
    original_seed: int
    gen_start_date: str
    gen_end_date: str
    freq: str = "h"
    consumption_factor_file: Path
    output_base: Path

    @classmethod
    def from_yaml(cls, data: dict, yaml_dir: Path) -> EnvironmentConfig:
        paths = data["paths"]
        sim = data["simulation"]
        return cls(
            seed=data["seed"],
            original_seed=data["seed"],
            gen_start_date=sim["start_date"],
            gen_end_date=sim["end_date"],
            freq=sim.get("freq", "h"),
            consumption_factor_file=_resolve_path(paths["consumption_factor_file"], yaml_dir),
            output_base=_resolve_path(paths["output_base"], yaml_dir),
        )


# =============================================================================
# Parameter library for predefined schedules, vehicles, and companies, loaded from YAML files in the predefined/ directory.
# =============================================================================

class PredefinedLibrary(BaseModel):
    """Holds all predefined parameters loaded from the predefined/ directory.

    Provides typed lookup: predefined.get_vehicle("renault") → VehicleConfig.
    """
    schedules: dict[str, dict]
    vehicles: dict[str, dict]
    companies: dict[str, dict]

    @classmethod
    def from_directory(cls, predefined_dir: Path) -> PredefinedLibrary:
        schedules = _load_yaml(predefined_dir / "schedules.yaml")
        vehicles = _load_yaml(predefined_dir / "vehicles.yaml")
        companies = _load_yaml(predefined_dir / "companies.yaml")
        companies.pop("_defaults", None)  # Remove YAML anchor helper
        return cls(schedules=schedules, vehicles=vehicles, companies=companies)

    def get_schedule(self, name: str, custom: dict | None = None) -> ScheduleConfig:
        """Look up a schedule preset by name, or use a custom override dict."""
        raw = self._resolve("schedule", name, self.schedules, custom)
        return ScheduleConfig(**raw)

    def get_vehicle(self, name: str, custom: dict | None = None) -> VehicleConfig:
        raw = self._resolve("vehicle", name, self.vehicles, custom)
        return VehicleConfig(**raw)

    def get_company(self, name: str, custom: dict | None = None) -> CompanyConfig:
        raw = self._resolve("company", name, self.companies, custom)
        return CompanyConfig(**raw)

    @staticmethod
    def _resolve(kind: str, name: str, predefined: dict, custom: dict | None) -> dict:
        if name == "custom":
            if not custom:
                raise ValueError(f"'{kind}' set to 'custom' but no custom_{kind} block provided in run.yaml")
            return custom
        if name not in predefined:
            available = ", ".join(sorted(predefined.keys()))
            raise ValueError(f"Unknown {kind} '{name}'. Available: {available}")
        return predefined[name]


# =============================================================================
# Configuration class for the fleet: ables the creation of a fleet, that includes the electric vehicle mix.
# Mix includes: number of vehicles, schedule mix, vehicle mix, and company type. 
# =============================================================================

class RunConfig(BaseModel):
    """
    Defines the fleet — fleet size, composition, company type.
    """
    model_config = {"extra": "forbid"}

    schedule_name: str
    n_vehicles: int = Field(gt=0)
    schedule_mix: dict[str, int]
    vehicle_mix: dict[str, int]
    company_type: str
    custom_schedule: dict | None = None
    custom_schedule_with_break: dict | None = None
    custom_vehicle: dict | None = None
    custom_company: dict | None = None

    @model_validator(mode="after")
    def _validate_mix_totals(self) -> RunConfig:
        total_sched = sum(self.schedule_mix.values())
        total_veh = sum(self.vehicle_mix.values())
        if total_sched != self.n_vehicles:
            raise ValueError(
                f"schedule_mix sums to {total_sched}, expected n_vehicles={self.n_vehicles}"
            )
        if total_veh != self.n_vehicles:
            raise ValueError(
                f"vehicle_mix sums to {total_veh}, expected n_vehicles={self.n_vehicles}"
            )
        return self

    @classmethod
    def from_yaml(cls, data: dict) -> RunConfig:
        fleet = data["fleet"]
        return cls(
            schedule_name=data["schedule_name"],
            n_vehicles=fleet["n_vehicles"],
            schedule_mix=fleet["schedule_mix"],
            vehicle_mix=fleet["vehicle_mix"],
            company_type=fleet["company_type"],
            custom_schedule=data.get("custom_schedule"),
            custom_schedule_with_break=data.get("custom_schedule_with_break"),
            custom_vehicle=data.get("custom_vehicle"),
            custom_company=data.get("custom_company"),
        )


# =============================================================================
# Loading, formating and returning all parameters configurations for the fleet operation simulation.
# =============================================================================

def load_config(
    env_yaml: str | Path = "config/env.yaml",
    run_yaml: str | Path = "config/run.yaml",
    predefined_dir: str | Path | None = None,
) -> tuple[EnvironmentConfig, RunConfig, PredefinedLibrary]:
    """
    Read and validate all configuration from YAML files.

    Parameters:
    ----------
        env_yaml : path to environment config
        run_yaml : path to run/scenario config
        predefined_dir : path to predefined folder (default: predefined/ next to env_yaml)

    Returns:
    -------
        (EnvironmentConfig, RunConfig, PredefinedLibrary)

    Errors that can be raised:
    ------
        FileNotFoundError : If any file is missing.
        pydantic.ValidationError: If any field has wrong type, is out of range, or mixes don't sum correctly.
    """
    env_path = Path(env_yaml).resolve()
    run_path = Path(run_yaml).resolve()

    if predefined_dir is None:
        predefined_dir = env_path.parent / "predefined"
    else:
        predefined_dir = Path(predefined_dir).resolve()

    env = EnvironmentConfig.from_yaml(_load_yaml(env_path), env_path.parent)
    run = RunConfig.from_yaml(_load_yaml(run_path))         # validates on construction
    predefined = PredefinedLibrary.from_directory(predefined_dir)

    logger.info("Config loaded: %s, %d vehicles, company=%s",
                run.schedule_name, run.n_vehicles, run.company_type)
    return env, run, predefined