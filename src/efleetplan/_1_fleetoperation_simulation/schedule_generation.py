"""
schedule_generation.py
=====================
Probabilistic schedule generator for EV fleet simulation.

Generates hourly (or sub-hourly) time-series of distance, energy consumption,
and location for each vehicle over a date range.

"""

from __future__ import annotations

import datetime as dt
import logging
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

from .config_loader_schedule import (
    CompanyConfig,
    EnvironmentConfig,
    PredefinedLibrary,
    RunConfig,
    ScheduleConfig,
    VehicleConfig,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

TIME_SLOTS = [0, 15, 30, 45]           # Valid minute values (15-min resolution)
PAUSE_MIN_DURATION = 15                 # Minimum pause duration in minutes
STOP_TIME_FACTOR = 0.25                 # Each stop ≈ 15 min → 0.25 hours
STOP_IMPACT_ON_RETURN = 0.1            # Each stop adds ~6 min to return time


# =============================================================================
# ScheduleGenerator
# =============================================================================

class ScheduleGenerator:
    """Generates a probabilistic driving schedule for one vehicle.

    Parameters
    ----------
    env : EnvironmentConfig
        simulation environment (dates, seed, file paths).
    sc : ScheduleConfig
        Schedule timing parameters (departure/return distributions).
    vc : VehicleConfig
        Vehicle energy parameters (consumption, battery, charging).
    cc : CompanyConfig
        Company distance/stops parameters.
    vehicle_id : str
        Identifier for this vehicle.
    schedule_type : str
        One of "typea", "typeb", "custom" — determines which generation method to use.
        Note: "typea" and "custom" use the same algorithm; the difference is only
        in the parameter values loaded from YAML.
    """

    def __init__(
        self,
        env: EnvironmentConfig,
        sc: ScheduleConfig,
        vc: VehicleConfig,
        cc: CompanyConfig,
        vehicle_id: str = "0",
        schedule_type: str = "typea",
    ):
        self.sc = sc
        self.vc = vc
        self.cc = cc
        self.vehicle_id = vehicle_id
        self.schedule_type = schedule_type

        self.starting_date = env.gen_start_date
        self.ending_date = env.gen_end_date
        self.freq = env.freq

        self.consumption_factors_df = self._load_consumption_factors(env.consumption_factor_file)

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_consumption_factors(path: Path) -> pd.DataFrame:
        """Load the external CSV of date-indexed energy consumption factors."""
        df = pd.read_csv(path, parse_dates=["date"], index_col="date")
        return df

    def _get_consumption_factor(self, step: pd.Timestamp) -> float:
        """Look up the consumption factor for a given timestamp's date."""
        date_only = step.normalize()
        try:
            return self.consumption_factors_df.loc[date_only, "Energy Consumption Factor"]
        except KeyError:
            logger.warning("Date %s not found in consumption factors. Using default 1.0", date_only)
            return 1.0

    @staticmethod
    def _sample_time(mean: float, dev: float, min_time: int, max_time: int) -> tuple[int, int]:
        """Sample a random time (hour, minute) from a normal distribution.

        The minute is snapped to the nearest 15-minute slot.
        The hour is clipped to [min_time, max_time].
        """
        t = np.random.normal(mean, dev)
        integer_part, fractional_part = math.modf(t)
        hour = int(fractional_part)
        minute_fraction = int(integer_part * 60)
        minute = TIME_SLOTS[np.abs(np.asarray(TIME_SLOTS) - minute_fraction).argmin()]
        hour = int(np.clip(hour, min_time, max_time))
        return hour, minute

    def _sample_lognormal_distance(self, mean: float, std: float) -> float:
        """Sample a lognormal-distributed daily distance, clipped to company min/max.

        Merges the old sample_lognormal_distance_wd and _we methods — they were
        identical except for which mean/std was passed in.
        """
        mu = np.log(mean**2 / np.sqrt(std**2 + mean**2))
        sigma = np.sqrt(np.log(1 + (std**2 / mean**2)))
        distance = np.random.lognormal(mu, sigma)
        return float(np.clip(distance, self.cc.min_distance, self.cc.max_distance))

    def _sample_consumption_rate(self, distance_per_step: float) -> float:
        """Sample a lognormal consumption rate (kWh/km), clipped to vehicle limits.

        Ensures that per-step consumption does not exceed the vehicle's capacity.
        """
        mean = self.vc.consumption_mean
        std = self.vc.consumption_std
        mu = np.log(mean**2 / np.sqrt(std**2 + mean**2))
        sigma = np.sqrt(np.log(1 + (std**2 / mean**2)))
        rate = np.random.lognormal(mu, sigma)
        rate = float(np.clip(rate, self.vc.consumption_min, self.vc.consumption_max))
        if distance_per_step > 0:
            rate = min(rate, self.vc.total_cons_clip / distance_per_step)
        return rate

    def _clamp_distance_per_step(
        self, distance_per_step: float, trip_timesteps: float
    ) -> tuple[float, float]:
        """Clamp distance_per_step to company min/max and recompute total_distance.

        Returns (clamped_distance_per_step, adjusted_total_distance).
        """
        clamped = float(np.clip(
            distance_per_step,
            self.cc.min_distance_per_step,
            self.cc.max_distance_per_step,
        ))
        total = clamped * trip_timesteps
        if total < 0:
            raise ValueError(f"Negative distance computed: {total}")
        return clamped, total

    def _create_empty_schedule(self) -> pd.DataFrame:
        """Create the base DataFrame with the date range and default values."""
        dates = pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq)
        return pd.DataFrame({
            "date": dates,
            "Distance_km": 0.0,
            "Consumption_kWh": 0.0,
            "Consumption_rate_corrected": 0.0,
            "Location": 1,
            "ChargingStation": 1,
            "ID": str(self.vehicle_id),
            "Battery_Capacity_kWh": self.vc.battery_capacity,
            "vehicle_type": self.vc.vehicle_type,
            "PowerRating_kW": self.vc.charging_power,
        })

    def _set_driving_step(
        self,
        schedule: pd.DataFrame,
        idx: int,
        distance_per_step: float,
        consumption_rate: float,
        consumption_factor: float,
    ) -> None:
        """Fill in a driving (on-road) timestep."""
        schedule.at[idx, "Distance_km"] = distance_per_step
        schedule.at[idx, "Consumption_kWh"] = distance_per_step * consumption_rate * consumption_factor
        schedule.at[idx, "Consumption_rate_corrected"] = consumption_rate * consumption_factor
        schedule.at[idx, "Location"] = 0
        schedule.at[idx, "ChargingStation"] = 0
        schedule.at[idx, "ID"] = str(self.vehicle_id)
        schedule.at[idx, "Battery_Capacity_kWh"] = self.vc.battery_capacity
        schedule.at[idx, "vehicle_type"] = self.vc.vehicle_type
        schedule.at[idx, "PowerRating_kW"] = self.vc.charging_power

    def _set_depot_step(
        self,
        schedule: pd.DataFrame,
        idx: int,
        consumption_factor: float,
    ) -> None:
        """Fill in a depot (at-home/charging) timestep."""
        schedule.at[idx, "Distance_km"] = 0.0
        schedule.at[idx, "Consumption_kWh"] = 0.0
        schedule.at[idx, "Consumption_rate_corrected"] = 0.0
        schedule.at[idx, "Location"] = 1
        schedule.at[idx, "ChargingStation"] = 1
        schedule.at[idx, "ID"] = str(self.vehicle_id)
        schedule.at[idx, "Battery_Capacity_kWh"] = self.vc.battery_capacity
        schedule.at[idx, "vehicle_type"] = self.vc.vehicle_type
        schedule.at[idx, "PowerRating_kW"] = self.vc.charging_power

    # -------------------------------------------------------------------------
    # Schedule dispatch
    # -------------------------------------------------------------------------

    def generate_schedule(self) -> pd.DataFrame:
        """Generate a schedule based on the schedule_type.

        Note: 'typea' and 'typec' use the same algorithm — the difference is only
        in the parameter values (which are already resolved from YAML).
        """
        if self.schedule_type in ("typea", "custom"):
            return self._generate_continuous()
        elif self.schedule_type in ("typeb"):
            return self._generate_with_break()
        else:
            raise ValueError(f"Unknown schedule type: '{self.schedule_type}'")

    # -------------------------------------------------------------------------
    # Type A / Custom Continuous — continuous schedule (no midday break)
    # -------------------------------------------------------------------------

    def _plan_continuous_day(self, step: pd.Timestamp, timestep_seconds: float) -> dict:
        """Plan departure, return, distance, and per-step distance for one day.

        Returns a dict with keys: dep_date, ret_date, trip_timesteps,
        total_distance, distance_per_step.
        """
        is_weekday = step.weekday() < 5

        if is_weekday:
            dep_hour, dep_min = self._sample_time(
                self.sc.dep_mean_wd, self.sc.dep_dev_wd, self.sc.min_dep, self.sc.max_dep
            )
            total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
            adjusted_ret_mean = self.sc.ret_mean_wd + (total_stops * STOP_TIME_FACTOR * STOP_IMPACT_ON_RETURN)
            ret_hour, ret_min = self._sample_time(
                adjusted_ret_mean, self.sc.ret_dev_wd, self.sc.min_return_hour, self.sc.max_return_hour
            )
            total_distance = self._sample_lognormal_distance(self.cc.avg_distance_wd, self.cc.dev_distance_wd)
        else:
            dep_hour, dep_min = self._sample_time(
                self.sc.dep_mean_we, self.sc.dep_dev_we, self.sc.min_dep, self.sc.max_dep
            )
            total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
            adjusted_ret_mean = self.sc.ret_mean_we + (total_stops * STOP_TIME_FACTOR * STOP_IMPACT_ON_RETURN)
            ret_hour, ret_min = self._sample_time(
                adjusted_ret_mean, self.sc.ret_dev_we, self.sc.min_return_hour, self.sc.max_return_hour
            )
            total_distance = self._sample_lognormal_distance(self.cc.avg_distance_we, self.cc.dev_distance_we)

        dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
        ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)
        trip_timesteps = (ret_date - dep_date).total_seconds() / timestep_seconds
        distance_per_step = total_distance / trip_timesteps if trip_timesteps > 0 else 0.0
        distance_per_step, total_distance = self._clamp_distance_per_step(distance_per_step, trip_timesteps)

        return {
            "dep_date": dep_date,
            "ret_date": ret_date,
            "trip_timesteps": trip_timesteps,
            "total_distance": total_distance,
            "distance_per_step": distance_per_step,
        }

    def _generate_continuous(self) -> pd.DataFrame:
        """Generate a continuous schedule (Type A / Custom Continuous).

        One trip per day: depart → drive → return. No midday break.
        """
        schedule = self._create_empty_schedule()
        offset = to_offset(self.freq)
        timestep_seconds = pd.Timedelta(offset).total_seconds()

        # Day-level state (recomputed at midnight)
        day = {"dep_date": None, "ret_date": None, "distance_per_step": 0.0}
        consumption_factor = 1.0

        for i, step in enumerate(schedule["date"]):
            # New day → plan the day's trip
            if step.hour == 0 and step.minute == 0:
                day = self._plan_continuous_day(step, timestep_seconds)

            # Trip ongoing
            if day["dep_date"] is not None and day["dep_date"] <= step < day["ret_date"]:
                consumption_rate = self._sample_consumption_rate(day["distance_per_step"])
                consumption_factor = self._get_consumption_factor(step)
                self._set_driving_step(
                    schedule, i,
                    day["distance_per_step"], consumption_rate, consumption_factor,
                )
            else:
                self._set_depot_step(schedule, i, consumption_factor)

        return schedule

    # -------------------------------------------------------------------------
    # Type B , Custom With Break — schedule with two-part
    # -------------------------------------------------------------------------

    def _plan_break_day_weekday(self, step: pd.Timestamp, timestep_seconds: float) -> dict:
        """Plans a weekday with a two-part schedule (Type B / Custom With Break)."""
        dep_hour, dep_min = self._sample_time(
            self.sc.dep_mean_wd, self.sc.dep_dev_wd, self.sc.min_dep, self.sc.max_dep
        )
        pause_beg_hour, pause_beg_min = self._sample_time(
            self.sc.pause_beg_mean_wd, self.sc.pause_beg_dev_wd,
            self.sc.min_beg_time, self.sc.max_beg_time,
        )
        pause_end_hour, pause_end_min = self._sample_time(
            self.sc.pause_end_mean, self.sc.pause_end_dev,
            self.sc.min_pause_end, self.sc.max_pause_end,
        )
        ret_hour, ret_min = self._sample_time(
            self.sc.ret_mean_wd, self.sc.ret_dev_wd,
            self.sc.min_return_hour, self.sc.max_return_hour,
        )

        dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
        pause_beg = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
        pause_end = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)
        ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

        # Ensure pause_end > pause_beg
        if (pause_end - pause_beg).total_seconds() < 0:
            diff_seconds = abs((pause_end - pause_beg).total_seconds())
            pause_end += dt.timedelta(seconds=diff_seconds, minutes=PAUSE_MIN_DURATION)

        first_trip_steps = (pause_beg - dep_date).total_seconds() / timestep_seconds
        second_trip_steps = (ret_date - pause_end).total_seconds() / timestep_seconds
        total_trip_steps = first_trip_steps + second_trip_steps

        pct_first = first_trip_steps / total_trip_steps if total_trip_steps > 0 else 0.5
        pct_second = 1.0 - pct_first

        total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)
        total_distance = float(np.clip(total_distance, self.cc.min_distance, self.cc.max_distance))

        return {
            "dep_date": dep_date,
            "pause_beg": pause_beg,
            "pause_end": pause_end,
            "ret_date": ret_date,
            "first_trip_steps": first_trip_steps,
            "second_trip_steps": second_trip_steps,
            "dist_first": pct_first * total_distance,
            "dist_second": pct_second * total_distance,
        }

    def _plan_break_day_weekend(self, step: pd.Timestamp, timestep_seconds: float) -> dict:
        """Plans a weekend day with a two-part schedule (Type B)."""
        dep_hour, dep_min = self._sample_time(
            self.sc.dep_mean_we, self.sc.dep_dev_we, self.sc.min_dep, self.sc.max_dep
        )
        pause_beg_hour, pause_beg_min = self._sample_time(
            self.sc.pause_beg_mean_we, self.sc.pause_beg_dev_we,
            self.sc.min_return_hour, self.sc.max_return_hour,
        )
        pause_end_hour, pause_end_min = self._sample_time(
            self.sc.pause_end_mean, self.sc.pause_end_dev,
            self.sc.min_return_hour, self.sc.max_return_hour,
        )
        ret_hour, ret_min = self._sample_time(
            self.sc.ret_mean_we, self.sc.ret_dev_we,
            self.sc.min_return_hour, self.sc.max_return_hour,
        )

        dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
        pause_beg = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
        pause_end = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)

        if (pause_end - pause_beg).total_seconds() < 0:
            diff_seconds = abs((pause_end - pause_beg).total_seconds())
            pause_end += dt.timedelta(seconds=diff_seconds, minutes=PAUSE_MIN_DURATION)

        ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

        first_trip_steps = (pause_beg - dep_date).total_seconds() / timestep_seconds
        second_trip_steps = (ret_date - pause_end).total_seconds() / timestep_seconds
        total_trip_steps = first_trip_steps + second_trip_steps

        pct_first = first_trip_steps / total_trip_steps if total_trip_steps > 0 else 0.5
        pct_second = 1.0 - pct_first

        total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)
        total_distance = float(np.clip(total_distance, self.cc.min_distance, self.cc.max_distance))

        return {
            "dep_date": dep_date,
            "pause_beg": pause_beg,
            "pause_end": pause_end,
            "ret_date": ret_date,
            "first_trip_steps": first_trip_steps,
            "second_trip_steps": second_trip_steps,
            "dist_first": pct_first * total_distance,
            "dist_second": pct_second * total_distance,
        }

    def _generate_with_break(self) -> pd.DataFrame:
        """Generate a break schedule (Type B).

        Two trips per day with a depot break in between:
        depart → drive → return to depot → break → depart → drive → return.
        """
        schedule = self._create_empty_schedule()
        offset = to_offset(self.freq)
        timestep_seconds = pd.Timedelta(offset).total_seconds()

        # Day-level state
        day: dict = {}
        consumption_factor = 1.0

        for i, step in enumerate(schedule["date"]):
            # New day → plan the day
            if step.hour == 0 and step.minute == 0:
                if step.weekday() < 5:
                    day = self._plan_break_day_weekday(step, timestep_seconds)
                else:
                    day = self._plan_break_day_weekend(step, timestep_seconds)

            if not day:
                continue

            # First trip: dep → pause_beg
            if day["dep_date"] <= step < day["pause_beg"]:
                dist_per_step = day["dist_first"] / day["first_trip_steps"] if day["first_trip_steps"] > 0 else 0.0
                consumption_rate = self._sample_consumption_rate(dist_per_step)
                consumption_factor = self._get_consumption_factor(step)
                self._set_driving_step(schedule, i, dist_per_step, consumption_rate, consumption_factor)

            # Second trip: pause_end → ret
            elif day["pause_end"] <= step < day["ret_date"]:
                dist_per_step = day["dist_second"] / day["second_trip_steps"] if day["second_trip_steps"] > 0 else 0.0
                consumption_rate = self._sample_consumption_rate(dist_per_step)
                consumption_factor = self._get_consumption_factor(step)
                self._set_driving_step(schedule, i, dist_per_step, consumption_rate, consumption_factor)

            # At depot (before departure, during pause, after return)
            else:
                self._set_depot_step(schedule, i, consumption_factor)

            # Emergency trip (Type B only, ~2% chance at end of day)
            if (step == dt.datetime(step.year, step.month, step.day, hour=23, minute=45)
                    and np.random.random() > 0.98):
                self._apply_emergency_trip(schedule, i, consumption_factor)

        return schedule

    def _apply_emergency_trip(
        self,
        schedule: pd.DataFrame,
        idx: int,
        consumption_factor: float,
    ) -> None:
        """Overwrite the day's last timestep with a rare emergency trip (Type B only)."""
        distance_per_step = np.random.uniform(self.cc.min_distance_per_step, self.cc.max_distance_per_step)
        consumption_rate = self._sample_consumption_rate(distance_per_step)
        self._set_driving_step(schedule, idx, distance_per_step, consumption_rate, consumption_factor)


# =============================================================================
# Fleet-level generation
# =============================================================================

def generate_fleet_schedules(
    env: EnvironmentConfig,
    run: RunConfig,
    predefined: PredefinedLibrary,
) -> pd.DataFrame:
    
    """Generate schedules for the full fleet and save to CSV.

    Parameters
    ----------
    env : EnvironmentConfig
        simulation environment (dates, seed, paths).
    run : RunConfig
        Fleet scenario (vehicle count, mix, company type).
    predefined : PredefinedLibrary
        Parameter predefined loaded from YAML.

    Returns
    -------
    pd.DataFrame
        Combined schedule for all vehicles.
    """
    # Expand mix dicts into per-vehicle lists
    schedule_names = _expand_mix(run.schedule_mix)
    vehicle_names = _expand_mix(run.vehicle_mix)

    all_schedules: list[pd.DataFrame] = []

    for vid, (sched_name, veh_name) in enumerate(zip(schedule_names, vehicle_names)):
        vehicle_id = str(vid)

        # Deterministic per-vehicle seed
        seed = vid * 1000 + env.original_seed
        np.random.seed(seed)

        # Resolve configs from predefined
        sc = predefined.get_schedule(sched_name, run.custom_schedule)
        vc = predefined.get_vehicle(veh_name, run.custom_vehicle)
        cc = predefined.get_company(run.company_type, run.custom_company)

        # Update env seed for this vehicle
        env.seed = seed

        generator = ScheduleGenerator(
            env=env, sc=sc, vc=vc, cc=cc,
            vehicle_id=vehicle_id,
            schedule_type=sched_name,
        )

        schedule = generator.generate_schedule()
        schedule["VehicleID"] = vehicle_id
        schedule["ScheduleType"] = sched_name
        schedule["VehicleType"] = veh_name
        schedule["CompanyType"] = run.company_type

        all_schedules.append(schedule)
        logger.info("Vehicle %s done (schedule=%s, vehicle=%s)", vehicle_id, sched_name, veh_name)

    if not all_schedules:
        raise ValueError("No schedules generated. Check run config.")

    final_schedule = pd.concat(all_schedules, ignore_index=True)

    # Save output
    output_dir = env.output_base / run.schedule_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{run.schedule_name}.csv"
    final_schedule.to_csv(output_file, index=False)

    # Save a copy of the run config for reproducibility
    logger.info("Saved %d rows to %s", len(final_schedule), output_file)

    return final_schedule


def _expand_mix(mix: dict[str, int]) -> list[str]:
    """Expand {'typea': 3, 'typeb': 2} → ['typea', 'typea', 'typea', 'typeb', 'typeb'].
    
    Supports all schedule types: 'typea', 'typeb', 'custom'.
    """
    result = []
    for name, count in mix.items():
        result.extend([name] * count)
    return result
