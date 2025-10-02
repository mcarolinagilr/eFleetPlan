import datetime as dt
import numpy as np
import math
import matplotlib.pyplot as plt
from typing import Literal
import pandas as pd
import time
import os

from optimalcharge_modules._1_schedule.schedule_generator_1 import ScheduleGenerator
from optimalcharge_modules._1_schedule.schedule_configure import scheduletype, vehicletype, companytype


def generate_schedules(env_config, sch_config):
                       
    n_vehicles = sch_config["Vehicles number"]
    n_typea = sch_config["Type of schedule"]["type a"]
    n_typeb = sch_config["Type of schedule"]["type b"]
    n_typec = sch_config["Type of schedule"]["type c"]
    n_Renault = sch_config["Type of vehicle"]["Renault"]
    n_Toyota = sch_config["Type of vehicle"]["Toyota"]
    n_Custom = sch_config["Type of vehicle"]["Custom"]
    schedule_name =sch_config["Schedule name"]
    company_type = sch_config["Company type"]
                   
          
    vehicle_ids = [str(i) for i in range(n_vehicles)]

    # Validate input counts
    assert n_vehicles == n_typea + n_typeb + n_typec, "Mismatch in total schedule types and vehicle count"
    assert n_vehicles == n_Renault + n_Toyota + n_Custom, "Mismatch in vehicle types and total vehicle count"

    # Define schedule and vehicle types
    schedule_types = [scheduletype.Typea] * n_typea + [scheduletype.Typeb] * n_typeb + [scheduletype.Typec] * n_typec
    vehicle_types = [vehicletype.Renault] * n_Renault + [vehicletype.Toyota] * n_Toyota + [vehicletype.Custom] * n_Custom
    company_types = [company_type] * n_vehicles

    all_schedules = []

    for vehicle_id, schedule_type, vehicle_type, company_type in zip(vehicle_ids, schedule_types, vehicle_types, company_types):
        env_config["seed"] = int(vehicle_id) * 1000 + env_config["original_seed"]
        np.random.seed(env_config["seed"])

        schedule_generator = ScheduleGenerator(
            env_config,
            sch_config,
            schedule_type=schedule_type, 
            vehicle_type=vehicle_type, 
            vehicle_id=vehicle_id, 
            company_type=company_type
        )

        schedule = schedule_generator.generate_schedule()
        schedule['VehicleID'] = vehicle_id
        schedule['ScheduleType'] = schedule_type.name
        schedule['VehicleType'] = vehicle_type.name
        schedule['CompanyType'] = company_type.name

        if 'Vehicletype' in schedule.columns:
            schedule.drop(columns=['Vehicletype'], inplace=True)

        all_schedules.append(schedule)

    # Ensure required columns exist (logging only)
    required_columns = [
        'Consumption_kWh', 'Consumption_km', 'Location', 
        'ChargingStation', 'PowerRating_kW', 'ScheduleType', 
        'VehicleType', 'CompanyType', 'consumption_factor'
    ]

    for i, schedule in enumerate(all_schedules):
        for col in required_columns:
            if col not in schedule.columns:
                print(f"Adding missing column '{col}' to schedule {i}")

    
    if not all_schedules:
        raise ValueError("No schedules were generated. Check your input parameters.")

    final_schedule = pd.concat(all_schedules, ignore_index=True)

    if 'Vehicletype' in final_schedule.columns:
        final_schedule.drop(columns=['Vehicletype'], inplace=True)

    
    # Go up from /notebooks to project root
    project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))

    # Create the proper output path
    output_folder = os.path.join(project_root, 'data', 'Output', schedule_name)
    os.makedirs(output_folder, exist_ok=True)

    # Create full file path
    output_file = os.path.join(output_folder, f"{schedule_name}.csv")

    # Save
    final_schedule.to_csv(output_file, index=False)

    return final_schedule
