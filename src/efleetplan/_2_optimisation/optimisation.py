import pyomo.environ as pyo
from pyomo.opt import SolverFactory 
import pandas as pd
import numpy as np
import xlsxwriter as xl
import itertools
import matplotlib.pyplot as plt
import shutil
import sys
import os.path
import csv
import io
from datetime import datetime

def calculate_days(opt_start_date, opt_end_date):
    date_format = "%Y-%m-%d %H:%M:%S"
    start = datetime.strptime(opt_start_date, date_format)
    end = datetime.strptime(opt_end_date, date_format)
    delta = end - start
    return delta.days

def assign(opt_config):
    # Load data from CVS files
    project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))

    
    opt_start_date = opt_config["opt_start_date"]
    opt_end_date = opt_config["opt_end_date"]
 
    EVs = opt_config["EVs"]
              
    electricity_price_grid = opt_config["electricity_price_grid"]
              
  
    output_folder = opt_config["output_folder"]
    input_folder = opt_config["input_folder"]
   
    En_consumption = opt_config["En_consumption"]
    Ev_distance = opt_config["Ev_distance"]
    Ev_availability_file = opt_config["Ev_availability_file"]
    Battery_Limitation = opt_config["Battery_Limitation"]
    PowerRate_Limitation = opt_config["PowerRate_Limitation"]

    # Electricity price file (the example uses value from SE3 in stockholm, Sweden in krs/kWh)
    electricity_price_grid = pd.read_csv(os.path.join(input_folder, 'SE3_el_prices_2023_modified.csv'))
    # Convert the date column to datetime format
    electricity_price_grid['date'] = pd.to_datetime(electricity_price_grid['date'])
    # Filter the data between opt_start_date and opt_end_date
    mask = (electricity_price_grid['date'] >= opt_start_date) & (electricity_price_grid['date'] <= opt_end_date)
    Price_data = electricity_price_grid.loc[mask, 'Elect_price']  # Replace 'Elect_price' with the actual column name for prices


    days = calculate_days(opt_start_date, opt_end_date)
    days = days + 1
    
    print(f"Number of days: {days}")


    # Convert the dates to datetime objects
    start_date = pd.to_datetime(opt_start_date)
    end_date = pd.to_datetime(opt_end_date)

    # Ensure the indices of the DataFrames are DatetimeIndex
    Price_data.index = pd.date_range(start=start_date, periods=len(Price_data), freq='h')
    Ev_availability_file.index = pd.date_range(start=start_date, periods=len(Ev_availability_file), freq='h')
    Ev_distance.index = pd.date_range(start=start_date, periods=len(Ev_distance), freq='h')
    En_consumption.index = pd.date_range(start=start_date, periods=len(En_consumption), freq='h')
    Battery_Limitation.index = pd.date_range(start=start_date, periods=len(Battery_Limitation), freq='h')
    PowerRate_Limitation.index = pd.date_range(start=start_date, periods=len(PowerRate_Limitation), freq='h')

    # Filter the data between the specified dates
    filtered_price_data = Price_data[(Price_data.index >= start_date) & (Price_data.index <= end_date)]
    filtered_ev_availability = Ev_availability_file[(Ev_availability_file.index >= start_date) & (Ev_availability_file.index <= end_date)]
    filtered_ev_distance = Ev_distance[(Ev_distance.index >= start_date) & (Ev_distance.index <= end_date)]
    filtered_energy_consumption = En_consumption[(En_consumption.index >= start_date) & (En_consumption.index <= end_date)]
    filtered_Battery_Limitation = Battery_Limitation[(Battery_Limitation.index >= start_date) & (Battery_Limitation.index <= end_date)]
    filtered_PowerRate_Limitation = PowerRate_Limitation[(PowerRate_Limitation.index >= start_date) & (PowerRate_Limitation.index <= end_date)]

    # Check if the filtered data is not empty
    #if filtered_price_data.empty or filtered_ev_availability.empty or filtered_ev_distance.empty or filtered_energy_consumption.empty or filtered_Battery_Limitation.empty:
    #raise ValueError("The filtered data is empty. Check the dates and input data.")

    # Initialize the global dictionaries
    EV_availability = {(b, t): 1 for b in range(1, EVs + 1) for t in range(1, len(filtered_ev_availability) + 1)}
    Distance_km = {(b, t): 1 for b in range(1, EVs + 1) for t in range(1, len(filtered_ev_distance) + 1)}
    Energy_Consumption_km = {(b, t): 1 for b in range(1, EVs + 1) for t in range(1, len(filtered_energy_consumption) + 1)}
    Price = {t: 1 for t in range(1, len(filtered_price_data) + 1)}
    
    # Precompute the maximum battery limitation for each EV
    Battery_Limitation = {b: filtered_Battery_Limitation.iloc[:, b].max() for b in range(1, EVs + 1)}
    PowerRate_Limitation = {b: filtered_PowerRate_Limitation.iloc[:, b].max() for b in range(1, EVs + 1)}

    # Fill the Price dictionary with the filtered data
    for t in range(1, len(filtered_price_data) + 1):
        Price[t] = filtered_price_data.iloc[t - 1]

    # Loop over each EV
    for y in range(1, EVs + 1):
        EV_available = filtered_ev_availability.iloc[:, y]
        Distance_km_EVs = filtered_ev_distance.iloc[:, y]
        Energy_Consumption = filtered_energy_consumption.iloc[:, y]
        
        # Precompute the max battery limitation for this EV
        max_battery_limit = Battery_Limitation[y]
        max_power_rate_limit = PowerRate_Limitation[y]
        
        # Loop over time (hours)
        for t in range(1, len(filtered_price_data) + 1):
            EV_availability[y, t] = EV_available.iloc[t - 1]
            Distance_km[y, t] = Distance_km_EVs.iloc[t - 1]
            Energy_Consumption_km[y, t] = Energy_Consumption.iloc[t - 1]
            Battery_Limitation[y, t] = max_battery_limit
            PowerRate_Limitation[y, t] = max_power_rate_limit
    
                          
    return EV_availability, Distance_km, Energy_Consumption_km, Price, Battery_Limitation, PowerRate_Limitation, days, EVs



def optimisation(opt_config, cost_config, power_config):
    
    # Funtion to assign the data to the optimisation module
    EV_availability, Distance_km, Energy_Consumption_km, Price, Battery_Limitation, PowerRate_Limitation, days, EVs = assign(opt_config)
    
    # Convert all data to float format
    EV_availability = {k: int(v) for k, v in EV_availability.items()}
    Distance_km = {k: float(v) for k, v in Distance_km.items()}
    Energy_Consumption_km = {k: float(v) for k, v in Energy_Consumption_km.items()}
    Price = {k: float(v) for k, v in Price.items()}
    Battery_Limitation = {k: float(v) for k, v in Battery_Limitation.items()}
    PowerRate_Limitation = {k: float(v) for k, v in PowerRate_Limitation.items()}
    days = int(days)
    EVs = int(EVs)
    delta_t = opt_config["delta_time"]  # Time step in hours
    
    Battery_LimitMax = power_config["Battery_Maximum Limit"]  # Maximum battery limit
    Battery_LimitMin = power_config["Battery_Minimum Limit"]  # Minimum battery limit
    
    # Create Model
    m = pyo.ConcreteModel()

    # Define Sets
    m.t = pyo.Set(initialize=[x for x in range(1, 24 * days + 1)])  # Time steps
    m.b = pyo.Set(initialize=[x for x in range(1, EVs + 1)])        # EVs
    m.d = pyo.Set(initialize=[x for x in range(1, days + 1)])       # Days

    # Fast charging power levels from config
    fast_charging_levels = ['f1', 'f2', 'f3']                          # Fast charging power levels


    # Parameters
    Ch_losses = power_config["Charging_losses"]  # Charging efficiency
    
    Infrastructure_life = cost_config["Infrastructure_life"]
    r = cost_config["Discount_rate"]
    Annuity_factor = (r * (1 + r) ** Infrastructure_life) / ((1 + r) ** Infrastructure_life - 1)

    Infrastructure_cost = cost_config["Infrastructure_cost"]
    
    Charger_Power = {'s': 7.4, 'Route': 150, 'f1': 50, 'f2': 150, 'f3': 350}
    maintenance_cost = cost_config["maintenance_cost"]

    Annualized_Infrastructure_cost = {
        's': Infrastructure_cost['s'] * Annuity_factor + maintenance_cost['s'],
        'f1': Infrastructure_cost['f1'] * Annuity_factor + maintenance_cost['f1'],
        'f2': Infrastructure_cost['f2'] * Annuity_factor + maintenance_cost['f2'],
        'f3': Infrastructure_cost['f3'] * Annuity_factor + maintenance_cost['f3']
    }

    Infrastructure_subscription = cost_config["Infrastructure_subscription"]
    Price_FixedrateDT = cost_config["Price_FixedrateDT"]
    Demand_rate = cost_config["Demand_rate"]
    Price_FixedrateRoute = cost_config["Price_FixedrateRoute"]
    ACC = power_config["Accumulated_Cycle_Capacity"]

    
    for b in range(1, EVs + 1):
        B_Cycle = ((1 - Battery_LimitMax) * Battery_Limitation[b]) / ACC


    # Declare Decision Variables
    m.Total_Grid_purchase = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Total energy taken from the grid
    m.DT_Grid_purchase = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Energy taken from the grid at DT
    
    m.Storage_level = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Battery storage level
    m.Start_Storage = pyo.Var(m.b, within=pyo.NonNegativeReals)
    
    m.CS_slow = pyo.Var(within=pyo.NonNegativeIntegers)  # Number of slow charging stations (CS)
    m.CS_fast_f1 = pyo.Var(within=pyo.NonNegativeIntegers)
    m.CS_fast_f2 = pyo.Var(within=pyo.NonNegativeIntegers)
    m.CS_fast_f3 = pyo.Var(within=pyo.NonNegativeIntegers)
    m.CS_Route = pyo.Var(within=pyo.NonNegativeIntegers)  # Number of route charging stations (CS)

    m.Charge_pertime = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Amount of charging every hour
    m.Discharge_pertime = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Amount of discharge every hour
    m.Charge_pertime_slow = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Amount of charge with SC every hour
    m.Charge_pertime_fast_f1 = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Indexed by fast charging levels
    m.Charge_pertime_fast_f2 = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Indexed by fast charging levels
    m.Charge_pertime_fast_f3 = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Indexed by fast charging levels
    #m.Charge_pertime_fast = pyo.Var(m.b, m.t, m.f, within=pyo.NonNegativeReals)  # Indexed by fast charging levels
    m.Charge_pertime_Route = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)  # Amount of route charging every hour
        
    m.Charging_slow = pyo.Var(m.b, m.t, within=pyo.Binary)  # Decision Variable
    m.Charging_fast_f1 = pyo.Var(m.b, m.t, within=pyo.Binary)  # Indexed by fast charging levels
    m.Charging_fast_f2 = pyo.Var(m.b, m.t, within=pyo.Binary)  # Indexed by fast charging levels
    m.Charging_fast_f3 = pyo.Var(m.b, m.t, within=pyo.Binary)  # Indexed by fast charging levels
    m.Charging_Route = pyo.Var(m.b, m.t, within=pyo.Binary)  # Decision Variable
    
    m.Battery_Cycles = pyo.Var(m.b, m.t, within=pyo.NonNegativeReals)
    m.PowerRate_Limitation = pyo.Param(m.b, initialize=lambda model, b: PowerRate_Limitation[b], within=pyo.NonNegativeReals)
    
    # Power rate variables with bounds
    m.PowerRate_slow = pyo.Var(m.b, bounds=lambda m, b: (0, min(Charger_Power['s'], m.PowerRate_Limitation[b])))
    m.PowerRate_fast_f1 = pyo.Var(m.b, bounds=lambda m, b: (0, min(Charger_Power['f1'], m.PowerRate_Limitation[b])))
    m.PowerRate_fast_f2 = pyo.Var(m.b, bounds=lambda m, b: (0, min(Charger_Power['f2'], m.PowerRate_Limitation[b])))
    m.PowerRate_fast_f3 = pyo.Var(m.b, bounds=lambda m, b: (0, min(Charger_Power['f3'], m.PowerRate_Limitation[b])))
    m.PowerRate_Route = pyo.Var(m.b, bounds=lambda m, b: (0, min(Charger_Power['Route'], m.PowerRate_Limitation[b])))
  
        
    # Variables for objective
    m.Max_Power = pyo.Var(within=pyo.NonNegativeReals)
  

    # 1. Constraints on Charging energy and power
    # 1.1. Grid energy purchase is equal to pertime charge (Including losses) (Eq2)
    def Total_Grid_Purchase(m, b, t):
        return m.Total_Grid_purchase[b, t] * Ch_losses - m.Charge_pertime[b, t] == 0
    m.total_grid_purchase = pyo.Constraint(m.b, m.t, rule=Total_Grid_Purchase)
    
    # 1.2. Total pertime charging is equal to SC + FC + route charging (Eq3)
    def Sum_Total_Charge_pertime(m, b, t):
        return m.Charge_pertime[b, t] == (
            m.Charge_pertime_slow[b, t]
            + m.Charge_pertime_fast_f1[b, t]
            + m.Charge_pertime_fast_f2 [b, t]
            + m.Charge_pertime_fast_f3 [b, t]
            + m.Charge_pertime_Route[b, t]
        )
    m.sum_charge_pertime = pyo.Constraint(m.b, m.t, rule=Sum_Total_Charge_pertime)
    
    # 1.3. Constraints in slow charging - Define maximum pertime charging with Slow C (Eq4)
    def Charge_pertime_Slow(m, b, t):
        return m.Charge_pertime_slow[b, t] <= m.PowerRate_slow[b] * m.Charging_slow[b, t] * EV_availability[b, t] * delta_t
    m.charge_pertime_slow = pyo.Constraint(m.b, m.t, rule=Charge_pertime_Slow)
    
    # 1.4. Constraints in fast charging - Define maximum pertime charging with Fast C (Eq5)
    def Charge_pertime_Fast_f1(m, b, t):
        return m.Charge_pertime_fast_f1[b, t] <= m.PowerRate_fast_f1[b] * m.Charging_fast_f1[b, t] * EV_availability[b, t] * delta_t
    m.charge_pertime_fast_f1 = pyo.Constraint(m.b, m.t, rule=Charge_pertime_Fast_f1)

    def Charge_pertime_Fast_f2(m, b, t):
        return m.Charge_pertime_fast_f2[b, t] <= m.PowerRate_fast_f2[b] * m.Charging_fast_f2[b, t] * EV_availability[b, t] * delta_t
    m.charge_pertime_fast_f2 = pyo.Constraint(m.b, m.t, rule=Charge_pertime_Fast_f2)

    def Charge_pertime_Fast_f3(m, b, t):
        return m.Charge_pertime_fast_f3[b, t] <= m.PowerRate_fast_f3[b] * m.Charging_fast_f3[b, t] * EV_availability[b, t] * delta_t
    m.charge_pertime_fast_f3 = pyo.Constraint(m.b, m.t, rule=Charge_pertime_Fast_f3)
    
    # 1.5. Constraints a maximum allowed route charging for each timesetp and vehicle (Eq6) 
    def Route_Charging(m, b, t):
        return m.Charge_pertime_Route[b, t] <= m.PowerRate_Route[b] * m.Charging_Route[b, t] * (1 - EV_availability[b, t]) * delta_t
    m.route_charging = pyo.Constraint(m.b, m.t, rule=Route_Charging)    
    
     # 1.6. Charging energy in the distribution terminal by vehicle (v) and time (t) - (eq7)
    def DT_Grid_Purchase(m, b, t):
        return (m.DT_Grid_purchase[b, t] * Ch_losses) - m.Charge_pertime_slow[b, t] - m.Charge_pertime_fast_f1[b, t] - m.Charge_pertime_fast_f2[b, t] - m.Charge_pertime_fast_f3[b, t] == 0
    m.DT_grid_purchase = pyo.Constraint(m.b, m.t, rule=DT_Grid_Purchase)
    
    # 1.7. Variable maximum power demand from the grid at DT was constrained as the maximum power purchased from the grid at a specific timestep for the summation of all vehicles at the DT (Eq8)
    def Max_Power_Constraint(m, t):
        return sum(m.DT_Grid_purchase[b, t] for b in m.b) <= m.Max_Power
    m.max_power = pyo.Constraint(m.t, rule=Max_Power_Constraint)
    
       
    # 2. Constraints on the number of charging
    
    # 2.1. Define the required amount of slow chargers (Eq9)
    def Balance_CS_Slow(m, t):
        return m.CS_slow >= sum(m.Charging_slow[b, t] for b in m.b)
    m.balance_cs_slow = pyo.Constraint(m.t, rule=Balance_CS_Slow)
    
    # 2.2. Define the required amount of fast chargers (Eq10)
    def Balance_CS_Fast_F1(m, t):
        return m.CS_fast_f1 >= sum(m.Charging_fast_f1[b, t] for b in m.b)
    m.balance_cs_fast_f1 = pyo.Constraint(m.t, rule=Balance_CS_Fast_F1)
    
    def Balance_CS_Fast_F2(m, t):
        return m.CS_fast_f2 >= sum(m.Charging_fast_f2[b, t] for b in m.b)
    m.balance_cs_fast_f2 = pyo.Constraint(m.t, rule=Balance_CS_Fast_F2)
    
    def Balance_CS_Fast_F3(m, t):
        return m.CS_fast_f3 >= sum(m.Charging_fast_f3[b, t] for b in m.b)
    m.balance_cs_fast_f3 = pyo.Constraint(m.t, rule=Balance_CS_Fast_F3)
    
       
    # 2.3. Define the number of Route chargers (Eq11)
    def Balance_CS_Route(m, t):
        return m.CS_Route>= sum(m.Charging_Route[b, t] for b in m.b)
    m.balance_cs_route = pyo.Constraint(m.t, rule=Balance_CS_Route)
     
    # 2.4 Limits the choice only to allow 1 charger per vehicle and time at DT (Eq12) 
    def Charging(m, b, t):
        return (
            m.Charging_fast_f1[b, t]
            + m.Charging_fast_f2[b, t]
            + m.Charging_fast_f3[b, t]
            + m.Charging_slow[b, t]
            <= 1
        )
    m.ChargersPerVehicle = pyo.Constraint(m.b, m.t, rule=Charging)

    

    # 3. Constraints on charging and discharging

    # 3.1 Define discharging that takes place during EV movement (1-EV_Availability) - (Eq13)
    def Discharge_pertime(m, b, t):
        return m.Discharge_pertime[b, t] == Energy_Consumption_km[b, t] * Distance_km[b, t] * (1 - EV_availability[b, t])
    m.discharge_pertime = pyo.Constraint(m.b, m.t, rule=Discharge_pertime)
    
    # 3.2 Define storage level change during a day dependent on the pertime discharge (Eq14)
    def Storage_Level(m, b, t):
        if t == 1:
            return m.Storage_level[b, t] == m.Start_Storage[b] + (Ch_losses * m.Charge_pertime[b, t]) - m.Discharge_pertime[b, t]
        else:
            return m.Storage_level[b, t] == m.Storage_level[b, t - 1] + (Ch_losses * m.Charge_pertime[b, t]) - m.Discharge_pertime[b, t]
    m.storage_level = pyo.Constraint(m.b, m.t, rule=Storage_Level)
    
    # 3.3 When the storage starts (Eq18)
    def Storage_Level_Start(m, b, t):
        return m.Start_Storage[b] == Battery_LimitMax * Battery_Limitation[b]
    m.Storage_Level_Start = pyo.Constraint(m.b, m.t, rule=Storage_Level_Start)
    
    # 3.4 Maximum storage (Eq17)
    def Max_Storage_Level(m, b, t):
        return m.Storage_level[b, t] <= Battery_LimitMax * Battery_Limitation[b]
    m.Max_SL = pyo.Constraint(m.b, m.t, rule=Max_Storage_Level)
    
    # 3.5 Minimum storage (Eq16)
    def Min_Storage_Level(m, b, t):
        return m.Storage_level[b, t] >= Battery_LimitMin * Battery_Limitation[b]
    m.Min_SL = pyo.Constraint(m.b, m.t, rule=Min_Storage_Level)
    
    # 3.6 Battery cycles counting
    def Battery_Cycles(m, b, t):
        if t == 1:
            return m.Battery_Cycles[b, t] == 0
        else:
            return m.Battery_Cycles[b, t] == (Ch_losses * m.Charge_pertime[b, t]) / Battery_Limitation[b]
    m.Battery_Cycles_pertime = pyo.Constraint(m.b, m.t, rule=Battery_Cycles)
    
    
    # Objective Function
    def ObjectiveFunction(m):
        return (
            (m.CS_slow * Annualized_Infrastructure_cost['s'])
            +(m.CS_fast_f1* Annualized_Infrastructure_cost['f1'])
            +(m.CS_fast_f2 * Annualized_Infrastructure_cost['f2'])
            +(m.CS_fast_f3 * Annualized_Infrastructure_cost['f3'])
            #+ sum(m.CS_fast[f] * Annualized_Infrastructure_cost[f] for f in m.f)
            + (Infrastructure_subscription * days)
            + sum(m.Charge_pertime_fast_f1[b, t] / Ch_losses * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t)  # Electricity cost on fast charging f1
            + sum(m.Charge_pertime_fast_f2[b, t] / Ch_losses * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t)  # Electricity cost on fast charging f2
            + sum(m.Charge_pertime_fast_f3[b, t] / Ch_losses * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t)  # Electricity cost on fast charging f3
            + m.Max_Power * Demand_rate
            + sum(m.Charge_pertime_Route[b, t] / Ch_losses * Price_FixedrateRoute for b in m.b for t in m.t)
            + sum(m.Charging_Route[b, t] * 9999 for b in m.b for t in m.t)
        )
    m.objective = pyo.Objective(rule=ObjectiveFunction, sense=pyo.minimize)

    # Solver definition - DETERMINISTIC VERSION
    solver = pyo.SolverFactory('gurobi')

    # Compromise: Semi-deterministic but faster

    solver.options['MIPGap'] = opt_config["MIPGap"]        # MIP optimality gap
    solver.options['ScaleFlag'] = 2
    solver.options['LogFile'] = "gurobi_log.txt"

    # Speed vs determinism balance
    solver.options['Threads'] = 8                 
    solver.options['Seed'] = 42                   # Fixed seed for some reproducibility
    solver.options['Method'] = 2                  # Deterministic barrier method
    solver.options['Presolve'] = 2                # Keep presolve for speed
    solver.options['NodeMethod'] = 3              # Deterministic node method

    # Conservative optimizations
    solver.options['Cuts'] = -1                   # Conservative cuts (not 0)
    solver.options['Heuristics'] = 0.3            # Limited heuristics (not 0.0)
       
    solver.options['MIPFocus'] = 3  
    
    # Debug: Print all solver options being used
    print("=== SOLVER CONFIGURATION ===")
    for key, value in solver.options.items():
        print(f"  {key}: {value}")
    print("=" * 40)

    
    result = solver.solve(m, report_timing=True, tee=True, warmstart=False)

    # Validate Results
    if result.solver.status == pyo.SolverStatus.ok and result.solver.termination_condition == pyo.TerminationCondition.optimal:
       print("Optimal solution found!")
    else:
       print("Solver did not converge to an optimal solution.")
      
        
    # Now access the value of decision variables
    print(pyo.value(m.Charge_pertime[1,1]))
    
    print(result)
              

    return m, Price, EV_availability, Distance_km

##############################################################################################################

#SCRIPT TO SAVE RESULTS

def save_results(m, Price, EV_availability, Distance_km, csv_file_pathA, csv_file_pathB, csv_file_pathC, csv_file_pathD, cost_config, power_config):
    
    # Parameters
    
    fast_charging_levels = ['f1', 'f2', 'f3']

    
    Ch_losses = power_config["Charging_losses"]  # Charging efficiency
    Infrastructure_life = cost_config["Infrastructure_life"]
    r = cost_config["Discount_rate"]
    Annuity_factor = (r * (1 + r) ** Infrastructure_life) / ((1 + r) ** Infrastructure_life - 1)

    Infrastructure_cost = cost_config["Infrastructure_cost"]
    
    Charger_Power = {'s': 7.4, 'Route': 150, 'f1': 50, 'f2': 150, 'f3': 350}
    maintenance_cost = cost_config["maintenance_cost"]

    Annualized_Infrastructure_cost = {
        's': Infrastructure_cost['s'] * Annuity_factor + maintenance_cost['s'],
        'f1': Infrastructure_cost['f1'] * Annuity_factor + maintenance_cost['f1'],
        'f2': Infrastructure_cost['f2'] * Annuity_factor + maintenance_cost['f2'],
        'f3': Infrastructure_cost['f3'] * Annuity_factor + maintenance_cost['f3']
    }

    Infrastructure_subscription = cost_config["Infrastructure_subscription"]
    Price_FixedrateDT = cost_config["Price_FixedrateDT"]
    Price_FixedrateRoute = cost_config["Price_FixedrateRoute"]
    

    """
    Optimized function to save results from the optimisation model
    """
    
    # 1. Save Main Variables Per Hour
    data = []

    def day(t):
        if t%24!=0:
            return t//24+1
        else:
            return t//24 

    for t in m.t:
        data.append({
            'Date': day(t),
            'Hour': (t - 1) - (day(t) - 1) * 24,
            'Charging energy': sum(pyo.value(m.Charge_pertime[b, t]) for b in m.b),
            'Price': Price[t],
            'Energy Purchase from grid': sum(pyo.value(m.Total_Grid_purchase[b, t]) for b in m.b),
            'Cost of energy supply from grid at DT': sum(pyo.value(m.DT_Grid_purchase[b, t] * (Price[t] + Price_FixedrateDT)) for b in m.b),
            'Cost of energy supply on route': sum(pyo.value((m.Total_Grid_purchase[b, t] - m.DT_Grid_purchase[b, t]) * (Price_FixedrateRoute)) for b in m.b),
            'EVs slow charging': sum(pyo.value(m.Charging_slow[b, t]) for b in m.b),
            'EVs fast charging 50kW': sum(pyo.value(m.Charging_fast_f1[b, t]) for b in m.b),
            'EVs fast charging 150kW': sum(pyo.value(m.Charging_fast_f2[b, t]) for b in m.b),
            'EVs fast charging 350kW': sum(pyo.value(m.Charging_fast_f3[b, t]) for b in m.b),
            'EVs route charging': sum(pyo.value(m.Charging_Route[b, t]) for b in m.b),
            'Slow Charging pertime': sum(pyo.value(m.Charge_pertime_slow[b, t]) for b in m.b),
            'Fast Charging pertime 50kW': sum(pyo.value(m.Charge_pertime_fast_f1[b, t]) for b in m.b),
            'Fast Charging pertime 150kW': sum(pyo.value(m.Charge_pertime_fast_f2[b, t]) for b in m.b),
            'Fast Charging pertime 350kW': sum(pyo.value(m.Charge_pertime_fast_f3[b, t]) for b in m.b),
            'Route Charging pertime': sum(pyo.value(m.Charge_pertime_Route[b, t]) for b in m.b)
        })
    
    df = pd.DataFrame(data)
    df.to_csv(csv_file_pathA, index=False)  # Save to CSV efficiently

  

    # 2. Save Summary Data 
    with open(csv_file_pathB, mode='w', newline='') as file:
        fieldnames = ['Category', 'Description', 'Value']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        # Slow Charging Station
        writer.writerow({'Category': 'Slow CS', 'Description': 'Chargers number', 
                 'Value': pyo.value(m.CS_slow)})

        writer.writerow({'Category': 'Slow CS', 'Description': 'Infrastructure Cost', 
                 'Value': pyo.value(m.CS_slow) * Annualized_Infrastructure_cost['s']})

        writer.writerow({'Category': 'Slow CS', 'Description': 'Electricity Cost', 'Value': sum(pyo.value(m.Charge_pertime_slow[b, t])  / Ch_losses * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t)})

        # Fast Charging Stations f1 (50kW)
        writer.writerow({'Category': f'Fast CS {Charger_Power["f1"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_fast_f1)}) 

        writer.writerow({'Category': f'Fast CS {Charger_Power["f1"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_fast_f1) * Annualized_Infrastructure_cost['f1']})

        writer.writerow({'Category': f'Fast CS {Charger_Power["f1"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_fast_f1[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})

        # Fast Charging Stations f2 (150kW)
        writer.writerow({'Category': f'Fast CS {Charger_Power["f2"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_fast_f2)}) 

        writer.writerow({'Category': f'Fast CS {Charger_Power["f2"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_fast_f2) * Annualized_Infrastructure_cost['f2']})

        writer.writerow({'Category': f'Fast CS {Charger_Power["f2"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_fast_f2[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})

        # Fast Charging Stations f3 (350kW)
        writer.writerow({'Category': f'Fast CS {Charger_Power["f3"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_fast_f3)}) 

        writer.writerow({'Category': f'Fast CS {Charger_Power["f3"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_fast_f3) * Annualized_Infrastructure_cost['f3']})

        writer.writerow({'Category': f'Fast CS {Charger_Power["f3"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_fast_f3[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})
            
        writer.writerow({'Category': 'DT', 'Description': 'Infrastructure Cost', 'Value': (
            pyo.value(m.CS_slow) * Annualized_Infrastructure_cost['s'] +
            pyo.value(m.CS_fast_f1) * Annualized_Infrastructure_cost['f1'] +
            pyo.value(m.CS_fast_f2) * Annualized_Infrastructure_cost['f2'] +
            pyo.value(m.CS_fast_f3) * Annualized_Infrastructure_cost['f3']
        )})
        writer.writerow({'Category': 'DT', 'Description': 'Electricity Cost', 'Value': sum((pyo.value(m.DT_Grid_purchase[b, t]) * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t))})
        writer.writerow({'Category': 'DT', 'Description': 'Chargers number', 'Value': pyo.value(m.CS_slow) + pyo.value(m.CS_fast_f1) + pyo.value(m.CS_fast_f2) + pyo.value(m.CS_fast_f3)})
        writer.writerow({'Category': 'DT', 'Description': 'Max Power [kW]', 'Value': pyo.value(m.Max_Power)})

        writer.writerow({'Category': 'Route CS', 'Description': 'Chargers number', 'Value': pyo.value(m.CS_Route)})
        #writer.writerow({'Category': 'Route CS', 'Description': 'Times', 'Value': sum(pyo.value(m.Charging_Route[b, t]) for b in m.b for t in m.t)})
        writer.writerow({'Category': 'Route CS', 'Description': 'Electricity Cost', 'Value': sum(pyo.value(m.Charge_pertime_Route[b, t]) * Price_FixedrateRoute for b in m.b for t in m.t)})

    # 3. EV descriptive file
    with open(csv_file_pathD,  mode='w', newline='') as file:
        writer = csv.writer(file)

        header = [
            'Day', 'Hour', 'Price', 'Vehicle ID', 'Charging Energy',
            'Discharging Energy', 'Storage Level', 'pertime Battery Cycles',
            'Cost of energy supply from grid at DT', 'Cost of energy supply on route', 'EV Available',
            'Slow Charging', 'Fast Charging 50kW', 'Fast Charging 150kW',
            'Fast Charging 350kW', 'Route Charging', 'Distance travelled by hour'
        ]

        writer.writerow(header)

        for t in m.t:
            for b in m.b:
                writer.writerow([
                    day(t),
                    (t - 1) - (day(t) - 1) * 24,
                    Price[t],
                    b,
                    pyo.value(m.Charge_pertime[b, t]),
                    pyo.value(m.Discharge_pertime[b, t]),
                    pyo.value(m.Storage_level[b, t]),
                    pyo.value(m.Battery_Cycles[b, t]),
                    pyo.value(m.DT_Grid_purchase[b, t] * (Price[t] + Price_FixedrateDT)),
                    pyo.value((m.Total_Grid_purchase[b, t] - m.DT_Grid_purchase[b, t]) * (Price_FixedrateRoute)),
                    EV_availability[b, t],
                    pyo.value(m.Charge_pertime_slow[b, t]),
                    pyo.value(m.Charge_pertime_fast_f1[b, t]),
                    pyo.value(m.Charge_pertime_fast_f2[b, t]),
                    pyo.value(m.Charge_pertime_fast_f3[b, t]),
                    pyo.value(m.Charge_pertime_Route[b, t]),
                    pyo.value(Distance_km[b, t])
                ])
    print("✅ Results saved successfully as CSV!")