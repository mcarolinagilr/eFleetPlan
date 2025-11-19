from enum import Enum

# Enumerations for the schedule type and vehicle type  
    
class scheduletype(Enum):
    Typea = 1
    Typeb = 2
    Typec = 3 # Custom schedule, parameters will be set in the schedule generator

class vehicletype(Enum):
    Renault = 1
    Toyota = 2
    Custom = 3 # Custom vehicle, parameters will be set in the schedule generator
    
class companytype(Enum):
    Distribution = 1 # Distribution transport: Transport of goods or commodities with several stops for loading and unloading along the way, such as distribution rounds or collection rounds.
    LineHaul = 2 # Line haul: Transport of goods or commodities, where the whole load was carried directly from one place to another; one or more such trips may be made during the measurement day
    CraftServWithGoods = 3 # Crafts and services with goods: Craft or service vehicle with goods or merchandise which would be used or installed in the work – materials, white goods, spare parts, etc.
    CraftServWithoutGoods = 4 # Crafts and services without goods: Craft or service vehicle without goods or merchandise – only tools or machinery.
    Food = 5 # Food, beverage and tobacco: Transport of food, beverages and tobacco products.
    Mail = 6 # Mail and packages: Transport of mail and packages.
    Building = 7  # Building materials: Transport of building materials.
    Highdistance = 8
    Generalcargo = 9
    Nogoods = 10
    Custom = 11 # Custom company type, parameters will be set in the schedule generator
    
    
    
# Configuration classes for the schedule and vehicle    
    
class ScheduleConfig:

    """
    Statistical configurations for the schedule generator. Mean and standard deviation values are specified for each
    metric, allowing for a distributional and probabilistic generation approach.
    """

    def __init__(self, schedule_type: scheduletype, env_config: dict, sch_config: dict):
        """
        Values initialised depending on the Schedule Type / Use-case
        :param schedule_type: Type of schedule to be generated
        """
                
        if schedule_type == schedule_type.Typea:
            
            #continuous schedule (with no stops in the middle of the day)
            self.dep_mean_wd = 8  # mean departure time weekday
            self.dep_dev_wd = 1  # std deviation departure time weekday
            self.ret_mean_wd = 18  # mean return time weekday
            self.ret_dev_wd = 1  # std deviation return time weekday

            self.dep_mean_we = 8  # mean departure time weekend
            self.dep_dev_we = 1
            self.ret_mean_we = 18
            self.ret_dev_we = 1

            self.min_dep = 6
            self.max_dep = 11
            self.min_return_hour = 18  # Return step must be bigger or equal to this value
            self.max_return_hour = 22  # Return step must be smaller or equal to this value           
        
            
            
        if schedule_type == schedule_type.Typeb:
            # break schedule - stops in the depot to charge and take new parcels
            
            #weekdays
            self.dep_mean_wd = 6  # mean departure time weekday
            self.dep_dev_wd = 1  # std deviation departure time weekday
            self.min_dep = 3
            self.max_dep = 10
            
            self.pause_beg_mean_wd = 12  # mean pause beginning weekday
            self.pause_beg_dev_wd = 0.25  # std dev pause beginning weekday
            self.pause_end_mean = 13  # mean pause end weekday
            self.pause_end_dev = 0.25  # std dev pause end weekday
            self.max_beg_time = 13
            self.min_beg_time = 11
            self.max_pause_end = 15
            self.min_pause_end = 12
            
            self.pause_time_mean = 0.5
            self.pause_time_dev = 0.1
            
            self.ret_mean_wd = 19  # mean return time weekday
            self.ret_dev_wd = 1  # std deviation return time weekday
            self.max_return_hour = 22
            self.min_return_hour = 15 
            
            
            #weekends
                        
            self.dep_mean_we = 9  # mean departure time weekend
            self.dep_dev_we = 1  # std deviation departure time weekday
            
            self.pause_beg_mean_we = 12  # mean pause beginning weekday
            self.pause_beg_dev_we = 0.25  # std dev pause beginning weekday
            self.ret_mean_we = 19  # mean return time weekday
            self.ret_dev_we = 0.5  # std deviation return time weekday


            self.prob_emergency = 0.02 
                                                  
        if schedule_type == schedule_type.Typec:
            
            #continuous schedule (with no stops in the middle of the day)
            self.dep_mean_wd = sch_config["Custom Schedule"]["average departure weekday"]  # mean departure time weekday
            self.dep_dev_wd = sch_config["Custom Schedule"]["std deviation departure weekday"]  # std deviation departure time weekday
            self.ret_mean_wd = sch_config["Custom Schedule"]["average return weekday"]  # mean return time weekday
            self.ret_dev_wd = sch_config["Custom Schedule"]["std deviation return weekday"]  # std deviation return time weekday

            self.dep_mean_we = sch_config["Custom Schedule"]["average departure weekend"]  # mean departure time weekend
            self.dep_dev_we = sch_config["Custom Schedule"]["std deviation departure weekend"]  # std deviation departure time weekend
            self.ret_mean_we = sch_config["Custom Schedule"]["average return weekend"]  # mean return time weekend
            self.ret_dev_we = sch_config["Custom Schedule"]["std deviation return weekend"]  # std deviation return time weekend

            self.min_dep = sch_config["Custom Schedule"]["minimum departure"]
            self.max_dep = sch_config["Custom Schedule"]["maximum departure"]
            self.min_return_hour = sch_config["Custom Schedule"]["minimum return"]  # Return step must be bigger or equal to this value
            self.max_return_hour = sch_config["Custom Schedule"]["maximum return"]  # Return step must be smaller or equal to this value                                        
    
    
class VehicleConfig:
    
    def __init__(self, vehicle_type: vehicletype, env_config: dict, sch_config: dict):
        
        if vehicle_type == vehicle_type.Renault:
            
            self.consumption_mean = 0.192 #this can vary with the vehicle choosen
            self.consumption_std = 0.1365  # Standard deviation of consumption in kWh/km
            self.consumption_min = 0.1  # Minimum value of consumption, used as a floor for consumption levels
            self.consumption_max = 0.45  # Maximum consumption, ceiling of consumption levels
            self.total_cons_clip = 45  # max kWh that a trip can use in each time step
            self.total_cons_clip_afternoon = 45  # max kWh that a trip can use in each time step
            self.battery_capacity = 45  # Battery capacity in kWh
            self.charging_power = 80  # kW 
            
        if vehicle_type == vehicle_type.Toyota:
            
            self.consumption_mean = 0.269 #this can vary with the vehicle choosen
            self.consumption_std = 0.1365  # Standard deviation of consumption in kWh/km
            self.consumption_min = 0.1  # Minimum value of consumption, used as a floor for consumption levels
            self.consumption_max = 0.45  # Maximum consumption, ceiling of consumption levels
            self.total_cons_clip = 68 # max kWh that a trip can use in each time step
            self.total_cons_clip_afternoon = 68 # max kWh that a trip can use in each time step        
            self.battery_capacity = 68  # Battery capacity in kWh
            self.charging_power = 100  # kW 
            
        if vehicle_type == vehicle_type.Custom:
            # Custom vehicle, parameters will be set in the schedule generator
            self.consumption_mean = sch_config["Custom Vehicle"]["average consumption"] #this can vary with the vehicle choosen
            self.consumption_std = sch_config["Custom Vehicle"]["std deviation consumption"]  # Standard deviation of consumption in kWh/km
            self.consumption_min = sch_config["Custom Vehicle"]["min consumption"]  # Minimum value of consumption, used as a floor for consumption levels
            self.consumption_max = sch_config["Custom Vehicle"]["max consumption"]  # Maximum consumption, ceiling of consumption levels
            self.total_cons_clip = sch_config["Custom Vehicle"]["battery capacity"]  # max kWh that a trip can use in each time step
            self.total_cons_clip_afternoon = sch_config["Custom Vehicle"]["battery capacity"] # max kWh that a trip can use in each time step          
            self.charging_power = sch_config["Custom Vehicle"]["charging power"]  # kW
            
            
class CompanyConfig:
    
    def __init__(self, company_type: companytype, env_config: dict, sch_config: dict):
        
        if company_type == company_type.Distribution:
            
            self.avg_distance_wd = 124  # mean distance travelled weekday
            self.dev_distance_wd = 15  # std deviation distance weekday
            self.avg_distance_we = 73  # mean distance weekend
            self.dev_distance_we = 15
            self.min_distance = 30
            self.max_distance = 300
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 52.4  # average number of stops per day 
            self.dev_stops = 11.7  # standard deviation of stops per day
            
        if company_type == company_type.LineHaul:
            
            self.avg_distance_wd = 73  # mean distance travelled weekday
            self.dev_distance_wd = 16  # std deviation distance weekday
            self.avg_distance_we = 43 # mean distance weekend
            self.dev_distance_we = 16
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 3.6 #average number of stops per day 
            self.dev_stops = 1.1 # standard deviation of stops per day
            
        if company_type == company_type.CraftServWithGoods:
            
            self.avg_distance_wd = 75  # mean distance travelled weekday
            self.dev_distance_wd = 7  # std deviation distance weekday
            self.avg_distance_we = 45  # mean distance weekend
            self.dev_distance_we = 7
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 52.4  # average number of stops per day 
            self.dev_stops = 11.7  # standard deviation of stops per day
            
        if company_type == company_type.CraftServWithoutGoods:
            
            self.avg_distance_wd = 71  # mean distance travelled weekday
            self.dev_distance_wd = 8  # std deviation distance weekday
            self.avg_distance_we = 42  # mean distance weekend
            self.dev_distance_we = 8
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 3.7  # average number of stops per day 
            self.dev_stops = 0.5  # standard deviation of stops per day
            
        if company_type == company_type.Food:
            
            self.avg_distance_wd = 81  # mean distance travelled weekday
            self.dev_distance_wd = 21  # std deviation distance weekday
            self.avg_distance_we = 48  # mean distance weekend
            self.dev_distance_we = 21
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 11  # average number of stops per day 
            self.dev_stops = 4.1  # standard deviation of stops per day
            
        if company_type == company_type.Mail:
            
            self.avg_distance_wd = 122  # mean distance travelled weekday
            self.dev_distance_wd = 23  # std deviation distance weekday
            self.avg_distance_we = 72  # mean distance weekend
            self.dev_distance_we = 23
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 98.1  # average number of stops per day 
            self.dev_stops = 21.8  # standard deviation of stops per day
            
        if company_type == company_type.Building:
            
            self.avg_distance_wd = 75  # mean distance travelled weekday
            self.dev_distance_wd = 8  # std deviation distance weekday
            self.avg_distance_we = 44  # mean distance weekend
            self.dev_distance_we = 8
            self.min_distance = 30
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 4.1  # average number of stops per day 
            self.dev_stops = 0.3  # standard deviation of stops per day

        if company_type == company_type.Highdistance:
            
            self.avg_distance_wd = 350  # mean distance travelled weekday
            self.dev_distance_wd = 50  # std deviation distance weekday
            self.avg_distance_we = 300  # mean distance weekend
            self.dev_distance_we = 50
            self.min_distance = 30
            self.max_distance = 400
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 70  # example maximum distance in km
            self.avg_stops = 52.4  # average number of stops per day 
            self.dev_stops = 11.7  # standard deviation of stops per day
            
        if company_type == company_type.Generalcargo:
            
            self.avg_distance_wd = 108.6  # mean distance travelled weekday
            self.dev_distance_wd = 23  # std deviation distance weekday
            self.avg_distance_we = 64  # mean distance weekend
            self.dev_distance_we = 23
            self.min_distance = 20
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 11.7  # average number of stops per day 
            self.dev_stops = 3.3  # standard deviation of stops per day
            
        if company_type == company_type.Nogoods:
            
            self.avg_distance_wd = 67.4  # mean distance travelled weekday
            self.dev_distance_wd = 6.8  # std deviation distance weekday
            self.avg_distance_we = 39.9  # mean distance weekend
            self.dev_distance_we = 6.8
            self.min_distance = 20
            self.max_distance = 200
            self.min_distance_per_step = 1  # example minimum distance in km
            self.max_distance_per_step = 50  # example maximum distance in km
            self.avg_stops = 3.4  # average number of stops per day 
            self.dev_stops = 0.4  # standard deviation of stops per day

        if company_type == company_type.Custom:
            # Custom company type, parameters will be set in the schedule generator
            self.avg_distance_wd = sch_config["Custom Distance"]["average weekday"]
            self.dev_distance_wd = sch_config["Custom Distance"]["standard deviation weekday"]
            self.avg_distance_we = sch_config["Custom Distance"]["average weekend"]
            self.dev_distance_we = sch_config["Custom Distance"]["standard deviation weekend"]
            self.min_distance = sch_config["Custom Distance"]["min distance"]
            self.max_distance = sch_config["Custom Distance"]["max distance"]
            self.min_distance_per_step = sch_config["Custom Distance"]["min distance per step"]
            self.max_distance_per_step = sch_config["Custom Distance"]["max distance per step"]
            self.avg_stops = sch_config["Custom Distance"]["average stops"]
            self.dev_stops = sch_config["Custom Distance"]["standard deviation stops"]

