import datetime
import math
import pandas as pd
import numpy as np
import datetime as dt
import time
import os

from optimalcharge_modules._1_schedule.schedule_configure import ScheduleConfig, scheduletype, vehicletype, VehicleConfig, CompanyConfig, companytype


class ScheduleGenerator:
    """
    Probabilistic schedule generator. Loops through each 1h timeslot in the yearly dataframe and generates a row
    entry. The format is kept similar to emobpy to enable compatability and ease of use.
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
        # If sch_config is needed, pass it to ScheduleConfig here
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
        
        # Load the CSV file
        # Define the directory where the notebook or script is located
        # Get the project root directory (two levels up from this file)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        csv_path = os.path.join(project_root, "data", "Input", "Energy_consumption_factor_2023.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        df_consumption_factors = pd.read_csv(csv_path)

        # Ensure 'date' column is in datetime format
        df_consumption_factors['date'] = pd.to_datetime(df_consumption_factors['date'])

        # Set 'date' as the index for easier lookups
        df_consumption_factors.set_index('date', inplace=True)
                
        self.df_consumption_factors = df_consumption_factors
    
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
      
    
    def generate_schedule(self):

        """
        This method chooses the right generation method depending on the use-case. Returns the schedule dataframe.

        :return: pd.DataFrame of the schedule
        """

        if self.schedule_type == self.schedule_type.Typea:
            return self.generate_typea()        
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
                    dep_time = np.random.normal(self.sc.dep_mean_wd, self.sc.dep_dev_wd)
                    dep_hour = int(math.modf(dep_time)[1])
                    dep_hour = min([dep_hour, self.sc.max_dep])
                    dep_hour = max([dep_hour, self.sc.min_dep])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(dep_time)[0] * 60)).argmin()
                    dep_min = minutes[closest_index]
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * 0.25  
                                                                                          
                    ret_time = total_time_stops*0.1 + np.random.normal(self.sc.ret_mean_wd, self.sc.ret_dev_wd)
                    ret_hour = int(math.modf(ret_time)[1])
                    ret_hour = min([ret_hour, self.sc.max_return_hour])
                    ret_hour = max([ret_hour, self.sc.min_return_hour])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(ret_time)[0] * 60)).argmin()
                    ret_min = minutes[closest_index]                	                               
                                        
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_steps = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    


                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_steps if trip_steps > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_steps  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_steps  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")

                #weekend
                else:
                    dep_time = np.random.normal(self.sc.dep_mean_we, self.sc.dep_dev_we)
                    dep_hour = int(math.modf(dep_time)[1])
                    dep_hour = min([dep_hour, self.sc.max_dep])
                    dep_hour = max([dep_hour, self.sc.min_dep])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(dep_time)[0] * 60)).argmin()
                    dep_min = minutes[closest_index]
                    
                    total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    total_time_stops = total_stops * 0.25 
                                                                                          
                    ret_time = total_time_stops* 0.1 + np.random.normal(self.sc.ret_mean_we, self.sc.ret_dev_we)
                    ret_hour = int(math.modf(ret_time)[1])
                    ret_hour = min([ret_hour, self.sc.max_return_hour])
                    ret_hour = max([ret_hour, self.sc.min_return_hour])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(ret_time)[0] * 60)).argmin()
                    ret_min = minutes[closest_index]                	                               
                                        
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)

                    trip_steps = (ret_date - dep_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])
                    
 

                    # Calculate distance traveled per hour #NEW
                    distance_per_hour = total_distance / trip_steps if trip_steps > 0 else 0

                    # Apply min and max constraints #NEW
                    if distance_per_hour < self.cc.min_distance_per_hour:
                        distance_per_hour = self.cc.min_distance_per_hour
                        total_distance = distance_per_hour * trip_steps  # Adjust total distance accordingly

                    if distance_per_hour > self.cc.max_distance_per_hour:
                        distance_per_hour = self.cc.max_distance_per_hour
                        total_distance = distance_per_hour * trip_steps  # Adjust total distance accordingly
                    
                    if total_distance < 0:
                        raise ValueError("Distance is negative")
                    

            # if trip is ongoing
            if (step >= dep_date) and (step < ret_date):

                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / trip_steps
                cons_rating = max([np.random.normal(self.vc.consumption_mean, self.vc.consumption_std), self.vc.consumption_min])
                cons_rating = min([cons_rating, self.vc.consumption_max])
                cons_rating = min([cons_rating, self.vc.total_cons_clip / total_distance])

                consumption_factor = self.consumption_factor(step)
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (distance_per_hour) * cons_rating * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = cons_rating * consumption_factor    
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
                    dep_time = np.random.normal(self.sc.dep_mean_wd, self.sc.dep_dev_wd)
                    dep_hour = int(math.modf(dep_time)[1])
                    dep_hour = min([dep_hour, self.sc.max_dep])
                    dep_hour = max([dep_hour, self.sc.min_dep])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(dep_time)[0]*60)).argmin()
                    dep_min = minutes[closest_index]
                                                           
                    #total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    #total_time_stops = total_stops * 0.25                      

                    pause_beg_time = np.random.normal(self.sc.pause_beg_mean_wd, self.sc.pause_beg_dev_wd)
                    pause_beg_hour = int(math.modf(pause_beg_time)[1]) 
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(pause_beg_time)[0] * 60)).argmin()
                    pause_beg_min = minutes[closest_index]

                    pause_end_time =  np.random.normal(self.sc.pause_end_mean, self.sc.pause_end_dev)
                    pause_end_hour = int(math.modf(pause_end_time)[1])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(pause_end_time)[0] * 60)).argmin()
                    pause_end_min = minutes[closest_index]

                    ret_time = np.random.normal(self.sc.ret_mean_wd, self.sc.ret_dev_wd)
                    ret_hour = int(math.modf(ret_time)[1])
                    ret_hour = min([ret_hour, self.sc.max_return_hour])
                    ret_hour = max([ret_hour, self.sc.min_return_hour])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(ret_time)[0] * 60)).argmin()
                    ret_min = minutes[closest_index]

                    # make dates for easier comparison
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    pause_beg_date = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
                    pause_end_date = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)
                    if (pause_end_date - pause_beg_date).total_seconds() < 0:
                        diff = (pause_end_date - pause_beg_date).total_seconds()
                        pause_end_date += dt.timedelta(seconds=abs(diff))
                        pause_end_date += dt.timedelta(minutes=15)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)
                    
                    # amount of time steps per trip
                    first_trip_steps = (pause_beg_date - dep_date).total_seconds() / 3600
                    second_trip_steps = (ret_date - pause_end_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_wd, self.cc.dev_distance_wd)/2
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])



                # weekend
                else:
                    # time mean and std dev in config
                    dep_time = np.random.normal(self.sc.dep_mean_we, self.sc.dep_dev_we)
                    dep_hour = int(math.modf(dep_time)[1])
                    dep_hour = min([dep_hour, self.sc.max_dep])
                    dep_hour = max([dep_hour, self.sc.min_dep])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(dep_time)[0]*60)).argmin()
                    dep_min = minutes[closest_index]
                                                           
                    #total_stops = np.random.normal(self.cc.avg_stops, self.cc.dev_stops)
                    #total_time_stops = total_stops * 0.25                      

                    pause_beg_time = np.random.normal(self.sc.pause_beg_mean_we, self.sc.pause_beg_dev_we)
                    pause_beg_hour = int(math.modf(pause_beg_time)[1]) 
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(pause_beg_time)[0] * 60)).argmin()
                    pause_beg_min = minutes[closest_index]

                    pause_end_time =  np.random.normal(self.sc.pause_end_mean, self.sc.pause_end_dev)
                    pause_end_hour = int(math.modf(pause_end_time)[1])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(pause_end_time)[0] * 60)).argmin()
                    pause_end_min = minutes[closest_index]

                    ret_time = np.random.normal(self.sc.ret_mean_we, self.sc.ret_dev_we)
                    ret_hour = int(math.modf(ret_time)[1])
                    ret_hour = min([ret_hour, self.sc.max_return_hour])
                    ret_hour = max([ret_hour, self.sc.min_return_hour])
                    minutes = np.asarray([0, 15, 30, 45])
                    closest_index = np.abs(minutes - int(math.modf(ret_time)[0] * 60)).argmin()
                    ret_min = minutes[closest_index]

                    # make dates for easier comparison
                    dep_date = dt.datetime(step.year, step.month, step.day, hour=dep_hour, minute=dep_min)
                    pause_beg_date = dt.datetime(step.year, step.month, step.day, hour=pause_beg_hour, minute=pause_beg_min)
                    pause_end_date = dt.datetime(step.year, step.month, step.day, hour=pause_end_hour, minute=pause_end_min)
                    if (pause_end_date - pause_beg_date).total_seconds() < 0:
                        diff = (pause_end_date - pause_beg_date).total_seconds()
                        pause_end_date += dt.timedelta(seconds=abs(diff))
                        pause_end_date += dt.timedelta(minutes=15)
                    ret_date = dt.datetime(step.year, step.month, step.day, hour=ret_hour, minute=ret_min)
                    
                    # amount of time steps per trip
                    first_trip_steps = (pause_beg_date - dep_date).total_seconds() / 3600
                    second_trip_steps = (ret_date - pause_end_date).total_seconds() / 3600
                    
                    total_distance = np.random.normal(self.cc.avg_distance_we, self.cc.dev_distance_we)/2
                    total_distance = max([total_distance, self.cc.min_distance])
                    total_distance = min([total_distance, self.cc.max_distance])

                    
            # if trip is ongoing
            if (step >= dep_date) and (step < pause_beg_date):

                # dividing the total distance into equal parts
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / first_trip_steps

                # sampling consumption in kWh / km based on Emobpy German case statistics
                # Clipping to min
                cons_rating = max([np.random.normal(self.vc.consumption_mean, self.vc.consumption_std),
                                   self.vc.consumption_min])
                # Clipping to max
                cons_rating = min([cons_rating, self.vc.consumption_max])
                # Clipping such that the maximum amount of energy per trip is not exceeded
                cons_rating = min([cons_rating, self.vc.total_cons_clip / total_distance])
                consumption_factor = self.consumption_factor (step)
                               
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / first_trip_steps) * cons_rating * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = cons_rating * consumption_factor 

                # set relevant entries
                ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0
                ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

            elif (step >= pause_end_date) and (step < ret_date):
                # dividing the total distance into equal parts
                ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / second_trip_steps

                # sampling consumption in kWh / km based on Emobpy German case statistics
                # Clipping to min
                cons_rating = max([np.random.normal(self.vc.consumption_mean, self.vc.consumption_std),
                                   self.vc.consumption_min])
                # Clipping to max
                cons_rating = min([cons_rating, self.vc.consumption_max])
                # Clipping such that the maximum amount of energy per trip is not exceeded
                cons_rating = min([cons_rating, self.vc.total_cons_clip_afternoon / total_distance])
                consumption_factor = self.consumption_factor (step)
                
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / second_trip_steps) * cons_rating * consumption_factor
                ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = cons_rating * consumption_factor 

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
                    trip_steps = (em_end_date - em_start_date).total_seconds() / 3600
                    total_distance = np.random.normal(self.sc.avg_distance_em, self.sc.dev_distance_em)/2
                    total_distance = max([total_distance, self.sc.min_em_distance])

                    for step in dr:
                        # dividing the total distance into equal parts
                        ev_schedule.loc[ev_schedule["date"] == step, "Distance_km"] = total_distance / trip_steps

                        # sampling consumption in kWh / km based on Emobpy German case statistics
                        # Clipping to min
                        cons_rating = max([np.random.normal(self.vc.consumption_mean, self.vc.consumption_std),
                                           self.vc.consumption_min])
                        # Clipping to max
                        cons_rating = min([cons_rating, self.vc.consumption_max])
                        # Clipping such that the maximum amount of energy per trip is not exceeded
                        cons_rating = min([cons_rating, self.vc.total_cons_clip / total_distance])
                        consumption_factor = self.consumption_factor (step)
                        
                        ev_schedule.loc[ev_schedule["date"] == step, "Consumption_kWh"] = (total_distance / trip_steps) * cons_rating * consumption_factor
                        ev_schedule.loc[ev_schedule["date"] == step, "Consumption_km"] = cons_rating * consumption_factor 
                        
                        # set relevant entries
                        ev_schedule.loc[ev_schedule["date"] == step, "Location"] = 0
                        ev_schedule.loc[ev_schedule["date"] == step, "ChargingStation"] = 0
                        ev_schedule.loc[ev_schedule["date"] == step, "ID"] = str(self.vehicle_id)
                        ev_schedule.loc[ev_schedule["date"] == step, "PowerRating_kW"] = 0.0
                        ev_schedule.loc[ev_schedule["date"] == step, "consumption_factor"] = consumption_factor

        return ev_schedule
