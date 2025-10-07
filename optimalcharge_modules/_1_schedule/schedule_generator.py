import datetime
import math
import pandas as pd
import numpy as np
import datetime as dt
import time
import os
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Literal



from .schedule_configure import ScheduleConfig, scheduletype, vehicletype, VehicleConfig, CompanyConfig, companytype


class ChargingConstants:
    Time_slots = [0, 15, 30, 45]
    Pause_min_duration = 15  # in minutes
    Stop_time_factor = 0.25  # each stop takes on average Const.Pause_min_duration minutes, so factor is 0.25 hours
    Stop_impact_on_return = 0.1  # each stop adds on average 6 minutes to return time, so factor is 0.1 hours

Const = ChargingConstants()

class ScheduleGenerator:
    """
    Probabilistic schedule generator. Loops through each 1h timeslot in the yearly dataframe and generates a row
    entry. 
    """
         

    def __init__(self,
                 env_config: dict,
                 sch_config: dict,
                 schedule_type: scheduletype = scheduletype.Typea,
                 vehicle_type: vehicletype = vehicletype.Renault,
                 company_type: companytype = companytype.Distribution,
                 vehicle_id: str = "0"):

        """
        Initialise seed, directories, and other parameters.

        :param env_config: Includes all necessary parameters to specify schedule generation
        :param sch_config: Schedule configuration dictionary (currently not used directly, but can be passed to ScheduleConfig if needed)
        :param schedule_type: Use-case 
        :param vehicle_type: Vehicle type
        :param company_type: Company type
        :param vehicle_id: Vehicle ID column
        """

        # Set seed for reproducibility
        seed = env_config["seed"]
        np.random.seed(seed)

        # define schedule type
        self.schedule_type = schedule_type
        self.sc = ScheduleConfig(schedule_type=self.schedule_type, env_config=env_config, sch_config=sch_config)
        
        # define vehicle type
        self.vehicle_type = vehicle_type
        self.vc = VehicleConfig(vehicle_type=self.vehicle_type, env_config=env_config, sch_config=sch_config)
        
        # define company type
        self.company_type = company_type
        self.cc = CompanyConfig(company_type=self.company_type, env_config=env_config, sch_config=sch_config)

        # set starting, ending and frequency
        self.starting_date = env_config["gen_start_date"]
        self.ending_date = env_config["gen_end_date"]
        self.freq = env_config["freq"]
        self.vehicle_id = vehicle_id
        
        # Load the consumption factors CSV that is in env_config
        self.consumption_factors = self.load_consumption_factors(env_config)
        

    def quantize_to_quarter_hour(self, time_decimal: float) -> tuple:
        """Convert decimal time to (hour, minute) in 15min intervals."""
        hour = int(math.modf(time_decimal)[1])
        minute_fraction = int(math.modf(time_decimal)[0] * 60)
        minutes = np.asarray(Const.Time_slots)
        closest_index = np.abs(minutes - minute_fraction).argmin()
        return hour, minutes[closest_index]
        
    def Time_constraints(self, mean: float, dev: float, min_time: int, max_time: int) -> tuple:
        """Generate a time (hour, minute) based on mean and std deviation, clipped to min and max."""
        time = np.random.normal(mean, dev)
        hour, minute = self.quantize_to_quarter_hour(time)
        hour = np.clip(hour, min_time, max_time)
        return hour, minute
    
        
        
    
    def load_consumption_factors(self, env_config: dict) -> pd.DataFrame:
        csv_path = env_config["consumption_factor_file"]
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        self.df_consumption_factors = df
        return df
        
              

    def consumption_factor(self, step):
        # Ensure 'step' is a datetime object
        if not isinstance(step, pd.Timestamp):
            step = pd.to_datetime(step)

        # Strip the time component from step if necessary
        step_date_only = step.normalize()

        try:
            # Look up the consumption factor for the given date in df_consumption_factors
            return self.df_consumption_factors.loc[step_date_only, 'Energy Consumption Factor']
        except KeyError:
            # If the date is not found, return a default value, for example, 1000.0
            print(f"Date {step_date_only} not found in DataFrame. Returning default value 1000.0")
            return 1000.0       
    
    
    def get_consumption_factors_for_range(self):
        # Generate date range between starting_date and ending_date
        date_range = pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq)
        
        # Retrieve consumption factors for each date in the range
        consumption_factors = {}
        for date in date_range:
            consumption_factors[date] = self.consumption_factor(date)
        
        return consumption_factors    
      
    def consumption_rate(self, total_distance: float) -> float:
        """
        Calculate the consumption rate (kWh/km) based on total distance.

        :param total_distance: Total distance traveled in km
        :return: Consumption rate in kWh/km
        """
        rate = np.random.normal(self.vc.consumption_mean, self.vc.consumption_std)
        rate = max(rate, self.vc.consumption_min)
        rate = min(rate, self.vc.consumption_max)
        if total_distance > 0:
            rate = min(rate, self.vc.total_cons_clip / total_distance)
        return rate
    
    
    
    def generate_schedule(self):

        """
        This method chooses the right generation method depending on the use-case. Returns the schedule dataframe.

        :return: pd.DataFrame of the schedule
        """

        if self.schedule_type == self.schedule_type.Typea:
            return self.generate_typea()
        elif self.schedule_type == self.schedule_type.Typec:
            return self.generate_typec()
        elif self.schedule_type == self.schedule_type.Typeb:
            return self.generate_typeb() 
      
        else:
            raise TypeError("Company type not found!")

    def generate_typea(self):

        # make DataFrame and a date range, from start to end
        ev_schedule = pd.DataFrame({
            "date": pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq),
            "Distance_km": 0.0,
            "Consumption_kWh": 0.0,
            "Consumption_km": 0.0,
            "Location": "home",
            "ChargingStation": "home",
            "ID": str(self.vehicle_id),
            "PowerRating_kW": self.vc.charging_power,
            "consumption_factor": np.nan,  # Initialize with NaN or some default value
        })
                         
        ev_schedule["date"] = pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq)

        # Loop through each date entry and create the other entries
        for step in ev_schedule["date"]:

            # Set default consumption_factor in case there's no trip
            consumption_factor = 1.0  # or any default value you want
            
            # if new day, specify new random values
            if (step.hour == 0) and (step.minute == 0):
                # weekdays
                if step.weekday() < 5:
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * Const.Stop_time_factor

                    adjusted_ret_mean = self.sc.ret_mean_we + (total_time_stops * Const.Stop_impact_on_return)
                    ret_hour, ret_min = self.Time_constraints(
                        adjusted_ret_mean,
                        self.sc.ret_dev_we,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )

                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_hours = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    


                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_hours if trip_hours > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")

                #weekend
                else:
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * Const.Stop_time_factor 
                                                                                          
                    adjusted_ret_mean = self.sc.ret_mean_we + (total_time_stops * Const.Stop_impact_on_return)
                    ret_hour, ret_min = self.Time_constraints(
                        adjusted_ret_mean,
                        self.sc.ret_dev_we,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )             	                               
                                        
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_hours = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    
 

                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_hours if trip_hours > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")
                    

            # if trip is ongoing
            if (step >= dep_date) and (step < ret_date):

                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / trip_hours
                consumption_rate = self.consumption_rate(total_distance)  


                consumption_factor = self.consumption_factor(step)
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (distance_per_hour) * consumption_rate * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = consumption_rate * consumption_factor    
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0

            else:
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = 0.0 
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = self.vc.charging_power

            # Ensure that consumption_factor is assigned even if not driving
            ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

        return ev_schedule


    def generate_typeb(self):

        """
        """

        # make DataFrame and a date range, from start to end
        ev_schedule = pd.DataFrame({
            "date": pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq),
            "Distance_km": 0.0,
            "Consumption_kWh": 0.0,
            "Consumption_km": 0.0,
            "Location": 1,
            "ChargingStation": 1,
            "ID": str(self.vehicle_id),
            "PowerRating_kW": self.vc.charging_power,
            "consumption_factor": np.nan  # Initialize with NaN or 1.0 as default
        })
        
        consumption_factor = 1.0  # Default value
        
        ev_schedule["date"] = pd.date_range(start=self.starting_date, end=self.ending_date, freq = self.freq)

        # Loop through each date entry and create the other entries
        for step in ev_schedule["date"]:
            
            # if new day, specify new random values
            if (step.hour == 0) and (step.minute == 0):

                # weekdays
                if step.weekday() < 5:

                    # time mean and std dev in config
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                                                           
                    #total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    #total_time_stops = total_stops * Const.Stop_time_factor                      

                    pause_beg_hour, pause_beg_min = self.Time_constraints(
                        self.sc.pause_beg_mean_wd,
                        self.sc.pause_beg_dev_wd,
                        self.sc.min_return_hour,  # Or use proper pause min/max if you have them
                        self.sc.max_return_hour
                    )
                                        
                    pause_end_hour, pause_end_min = self.Time_constraints(
                        self.sc.pause_end_mean,
                        self.sc.pause_end_dev,
                        self.sc.min_return_hour,  # Or use proper pause min/max if you have them
                        self.sc.max_return_hour
                    )

                    ret_hour, ret_min = self.Time_constraints(
                        self.sc.ret_mean_wd,
                        self.sc.ret_dev_wd,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )

                    # make dates for easier comparison
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    pause_beg_date = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
                    pause_end_date = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)
                    if (pause_end_date - pause_beg_date).total_seconds() < 0:
                        diff = (pause_end_date - pause_beg_date).total_seconds()
                        pause_end_date += dt.timedelta(seconds=abs(diff))
                        pause_end_date += dt.timedelta(minutes=Const.Pause_min_duration)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)
                    
                    # amount of time steps per trip
                    first_trip_hours = (pause_beg_date - dep_date).total_seconds() / 3600
                    second_trip_hours = (ret_date - pause_end_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)/2
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])



                # weekend
                else:
                    # time mean and std dev in config
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                                                           
                    #total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    #total_time_stops = total_stops * Const.Stop_time_factor                      

                    pause_beg_hour, pause_beg_min = self.Time_constraints(
                        self.sc.pause_beg_mean_wd,
                        self.sc.pause_beg_dev_wd,
                        self.sc.min_return_hour,  # Or use proper pause min/max if you have them
                        self.sc.max_return_hour
                    )
                                        
                    pause_end_hour, pause_end_min = self.Time_constraints(
                        self.sc.pause_end_mean,
                        self.sc.pause_end_dev,
                        self.sc.min_return_hour,  # Or use proper pause min/max if you have them
                        self.sc.max_return_hour
                    )

                    ret_hour, ret_min = self.Time_constraints(
                        self.sc.ret_mean_wd,
                        self.sc.ret_dev_wd,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )

                    # make dates for easier comparison
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    pause_beg_date = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
                    pause_end_date = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)
                    if (pause_end_date - pause_beg_date).total_seconds() < 0:
                        diff = (pause_end_date - pause_beg_date).total_seconds()
                        pause_end_date += dt.timedelta(seconds=abs(diff))
                        pause_end_date += dt.timedelta(minutes=Const.Pause_min_duration)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)
                    
                    # amount of time steps per trip
                    first_trip_hours = (pause_beg_date - dep_date).total_seconds() / 3600
                    second_trip_hours = (ret_date - pause_end_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)/2
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])

                    
            # if trip is ongoing
            if (step >= dep_date) and (step < pause_beg_date):

                # dividing the total distance into equal parts
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / first_trip_hours

                consumption_rate = self.consumption_rate(total_distance)

                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / first_trip_hours) * consumption_rate * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = consumption_rate * consumption_factor

                # set relevant entries
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

            elif (step >= pause_end_date) and (step < ret_date):
                # dividing the total distance into equal parts
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / second_trip_hours

                consumption_rate = self.consumption_rate(total_distance)

                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / second_trip_hours) * consumption_rate * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = consumption_rate * consumption_factor

                # set relevant entries
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor
                

            else:
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = 0.0 
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = self.vc.charging_power
                ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor
         

            if step == dt.datetime(step.year, step.month, step.day, hour=23, minute=45):
                if np.random.random() > 0.98:
                    # emergency
                    em_start_date = dt.datetime(step.year, step.month, step.day, hour=2, minute=0)
                    em_end_date = dt.datetime(step.year, step.month, step.day, hour=4, minute=0)
                    dr = pd.date_range(start=em_start_date, end=em_end_date, freq="15T")
                    trip_hours = (em_end_date - em_start_date).total_seconds() / 3600
                    total_distance = np.random.normal(self.sc.avg_distance_em, self.sc.dev_distance_em)/2
                    total_distance = max([total_distance, self.sc.min_em_distance])

                    for step in dr:
                        # dividing the total distance into equal parts
                        ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / trip_hours

                        # sampling consumption in kWh / km based on Emobpy German case statistics
                        # Clipping to min
                        consumption_rate = self.consumption_rate(total_distance)

                        ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / trip_hours) * consumption_rate * consumption_factor
                        ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = consumption_rate * consumption_factor

                        # set relevant entries
                        ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                        ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                        ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                        ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0
                        ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

        return ev_schedule

    def generate_typec(self):

        # make DataFrame and a date range, from start to end
        ev_schedule = pd.DataFrame({
            "date": pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq),
            "Distance_km": 0.0,
            "Consumption_kWh": 0.0,
            "Consumption_km": 0.0,
            "Location": "home",
            "ChargingStation": "home",
            "ID": str(self.vehicle_id),
            "PowerRating_kW": self.vc.charging_power,
            "consumption_factor": np.nan,  # Initialize with NaN or some default value
        })
                         
        ev_schedule["date"] = pd.date_range(start=self.starting_date, end=self.ending_date, freq=self.freq)

        # Loop through each date entry and create the other entries
        for step in ev_schedule["date"]:

            # Set default consumption_factor in case there's no trip
            consumption_factor = 1.0  # or any default value you want
            
            # if new day, specify new random values
            if (step.hour == 0) and (step.minute == 0):
                # weekdays
                if step.weekday() < 5:
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * Const.Stop_time_factor  
                                                                                          
                    adjusted_ret_mean = self.sc.ret_mean_we + (total_time_stops * Const.Stop_impact_on_return)
                    ret_hour, ret_min = self.Time_constraints(
                        adjusted_ret_mean,
                        self.sc.ret_dev_we,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )              	                               
                                        
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_hours = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    


                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_hours if trip_hours > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")

                #weekend
                else:
                    dep_hour, dep_min = self.Time_constraints(
                        self.sc.dep_mean_wd,
                        self.sc.dep_dev_wd,
                        self.sc.min_dep,
                        self.sc.max_dep
                    )
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * Const.Stop_time_factor 
                                                                                          
                    adjusted_ret_mean = self.sc.ret_mean_we + (total_time_stops * Const.Stop_impact_on_return)
                    ret_hour, ret_min = self.Time_constraints(
                        adjusted_ret_mean,
                        self.sc.ret_dev_we,
                        self.sc.min_return_hour,
                        self.sc.max_return_hour
                    )                 	                               
                                        
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_hours = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    
 

                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_hours if trip_hours > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_hours  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")
                    

            # if trip is ongoing
            if (step >= dep_date) and (step < ret_date):

                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / trip_hours
                consumption_rate = self.consumption_rate(total_distance)


                consumption_factor = self.consumption_factor(step)
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (distance_per_hour) * consumption_rate * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = consumption_rate * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0

            else:
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = 0.0 
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 1
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = self.vc.charging_power

            # Ensure that consumption_factor is assigned even if not driving
            ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

        return ev_schedule
    
    
    

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
