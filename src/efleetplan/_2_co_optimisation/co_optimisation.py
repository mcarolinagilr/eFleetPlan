import pyomo.environ as pyo
from pyomo.environ import quicksum, ConcreteModel, Var, Param, Constraint, Objective, Binary, RangeSet
from pyomo.opt import SolverFactory
import csv
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime


def calculate_days(start_str: str, end_str: str) -> int:
    fmt = "%Y-%m-%d %H:%M:%S"
    return (datetime.strptime(end_str, fmt) - datetime.strptime(start_str, fmt)).days + 1



def prepare_data(opt_config: dict):
    """Vectorized data preparation (same idea as your version 2)."""
    start_dt = pd.to_datetime(opt_config["opt_start_date"])
    end_dt   = pd.to_datetime(opt_config["opt_end_date"])
    EVs      = int(opt_config["EVs"])
    delta_t  = float(opt_config.get("delta_t", 1.0))
    freq     = opt_config.get("freq", "h")
    
    # --- Prices ---
    price_df = opt_config["electricity_price_grid"].copy()
    if 'date' in price_df.columns:
        date_col = 'date'
    elif 'Date' in price_df.columns:
        date_col = 'Date'
    else:
        raise ValueError("electricity_price_grid must have a 'date' or 'Date' column")
    price_df[date_col] = pd.to_datetime(price_df[date_col])
    price_df = price_df.set_index(date_col).sort_index()

    idx = pd.date_range(start_dt, end_dt, freq=freq, inclusive="both")
    if 'Elect_price' not in price_df.columns:
        raise ValueError("electricity_price_grid must have an 'Elect_price' column")

    price_series = price_df['Elect_price'].reindex(idx).ffill().bfill()

    hours = len(price_series)
    t_range = range(1, hours + 1)

    # --- Vehicle data ---
    def safe_prepare(df: pd.DataFrame) -> np.ndarray:
        if df is None or df.empty:
            raise ValueError("Empty input DataFrame")

        # Drop any non-numeric columns (timestamps, names, etc.)
        df = df.select_dtypes(include=[np.number])

        # Take only the first EVs columns
        veh_cols = df.columns[:EVs]
        df = df[veh_cols].copy()

        # build index, reindex to hourly idx, fill gaps
        df.index = pd.date_range(start_dt, periods=len(df), freq=freq)
        df = df.reindex(idx).ffill().bfill().iloc[:hours]

        return df.to_numpy()  # shape (hours, EVs)

    avail_np = safe_prepare(opt_config["EV_availability"])
    dist_np  = safe_prepare(opt_config["Ev_distance"])
    cons_np  = safe_prepare(opt_config["En_consumption"])
    bat_np   = safe_prepare(opt_config["Battery_Limitation"])
    pow_np   = safe_prepare(opt_config["PowerRate_Limitation"])

    bt_keys = [(b, t) for b in range(1, EVs+1) for t in t_range]

    EV_availability       = dict(zip(bt_keys, avail_np.T.ravel()))
    Distance_km           = dict(zip(bt_keys,  dist_np.T.ravel()))
    Energy_Consumption_km = dict(zip(bt_keys, cons_np.T.ravel()))
    Price                 = {t: float(price_series.iloc[t-1]) for t in t_range}

    Battery_Limitation   = {b: float(bat_np[:, b-1].max()) for b in range(1, EVs+1)}
    PowerRate_Limitation = {b: float(pow_np[:, b-1].max()) for b in range(1, EVs+1)}

    days = calculate_days(opt_config["opt_start_date"], opt_config["opt_end_date"])

    return (
        EV_availability, Distance_km, Energy_Consumption_km, Price,
        Battery_Limitation, PowerRate_Limitation,
        hours, days, EVs, delta_t
    )


def optimisation(opt_config, cost_config, power_config):
    # ------------ Data preparation ------------
    (EV_availability, Distance_km, Energy_Consumption_km, Price,
     Battery_Limitation, PowerRate_Limitation,
     hours, days, EVs, delta_t) = prepare_data(opt_config)

    # ------------ Model ------------
    m = ConcreteModel("EV_Charging_CoOptim")

    m.t = RangeSet(1, hours)
    m.b = RangeSet(1, EVs)

    # ------------ Parameters ------------
    m.delta_t = Param(initialize=float(delta_t))

    m.Ch_losses = Param(initialize=float(power_config["Charging_losses"]))
    m.BatMax    = Param(initialize=float(power_config["Battery_Maximum_Limit"]))
    m.BatMin    = Param(initialize=float(power_config["Battery_Minimum_Limit"]))

    # Charger power levels (Python constants are fine)
    Charger_Power = power_config["Charger_Power"]

    # Annualization factor
    r = float(cost_config["Discount_rate"])
    n = int(cost_config["Infrastructure_life"])
    
    annuity = r * (1 + r)**n / ((1 + r)**n - 1) if n > 0 else 1.0

    Annualized_Infrastructure_cost = {
        'f1':  float(cost_config["Infrastructure_cost"]['f1'])  * annuity + float(cost_config["maintenance_cost"]['f1']),
        'f2': float(cost_config["Infrastructure_cost"]['f2']) * annuity + float(cost_config["maintenance_cost"]['f2']),
        'f3': float(cost_config["Infrastructure_cost"]['f3']) * annuity + float(cost_config["maintenance_cost"]['f3']),
        'f4': float(cost_config["Infrastructure_cost"]['f4']) * annuity + float(cost_config["maintenance_cost"]['f4']),
    }

    m.Infrastructure_subscription = Param(initialize=float(cost_config["Infrastructure_subscription"]))
    m.Price_FixedrateDT           = Param(initialize=float(cost_config["Price_FixedrateDT"]))
    m.Price_Fixedrateroute        = Param(initialize=float(cost_config["Price_Fixedrateroute"]))
    m.Demand_rate                 = Param(initialize=float(cost_config["Demand_rate"]))

    # Time series / vehicle params
    m.Price                 = Param(m.t, initialize=Price, within=pyo.Reals)
    m.EV_availability       = Param(m.b, m.t, initialize=EV_availability, within=pyo.Reals)
    m.Distance_km           = Param(m.b, m.t, initialize=Distance_km, within=pyo.Reals)
    m.Energy_Consumption_km = Param(m.b, m.t, initialize=Energy_Consumption_km, within=pyo.Reals)
    m.Battery_Limitation    = Param(m.b, initialize=Battery_Limitation, within=pyo.NonNegativeReals)
    m.PowerRate_Limitation  = Param(m.b, initialize=PowerRate_Limitation, within=pyo.NonNegativeReals)

    cap_f1  = {b: min(Charger_Power['f1'],     PowerRate_Limitation[b]) for b in range(1, EVs+1)}
    cap_f2    = {b: min(Charger_Power['f2'],    PowerRate_Limitation[b]) for b in range(1, EVs+1)}
    cap_f3    = {b: min(Charger_Power['f3'],    PowerRate_Limitation[b]) for b in range(1, EVs+1)}
    cap_f4    = {b: min(Charger_Power['f4'],    PowerRate_Limitation[b]) for b in range(1, EVs+1)}
    cap_route = {b: min(Charger_Power['route'], PowerRate_Limitation[b]) for b in range(1, EVs+1)}

    m.Cap_f1  = Param(m.b, initialize=cap_f1,  within=pyo.NonNegativeReals)
    m.Cap_f2    = Param(m.b, initialize=cap_f2,    within=pyo.NonNegativeReals)
    m.Cap_f3    = Param(m.b, initialize=cap_f3,    within=pyo.NonNegativeReals)
    m.Cap_f4    = Param(m.b, initialize=cap_f4,    within=pyo.NonNegativeReals)
    m.Cap_route = Param(m.b, initialize=cap_route, within=pyo.NonNegativeReals)

    # ------------ Variables ------------
    m.Total_Grid_purchase = Var(m.b, m.t, bounds=(0, None))
    m.DT_Grid_purchase    = Var(m.b, m.t, bounds=(0, None))

    m.Storage_level = Var(m.b, m.t, bounds=(0, None))
    m.Start_Storage = Var(m.b, bounds=(0, None))

    m.CS_f1 = Var(domain=pyo.NonNegativeIntegers)
    m.CS_f2 = Var(domain=pyo.NonNegativeIntegers)
    m.CS_f3 = Var(domain=pyo.NonNegativeIntegers)
    m.CS_f4 = Var(domain=pyo.NonNegativeIntegers)
    m.CS_route   = Var(domain=pyo.NonNegativeIntegers)

    m.Charge_pertime         = Var(m.b, m.t, bounds=(0, None))
    m.Discharge_pertime      = Var(m.b, m.t, bounds=(0, None))
    m.Charge_pertime_f1 = Var(m.b, m.t, bounds=(0, None))
    m.Charge_pertime_f2 = Var(m.b, m.t, bounds=(0, None))
    m.Charge_pertime_f3 = Var(m.b, m.t, bounds=(0, None))
    m.Charge_pertime_f4 = Var(m.b, m.t, bounds=(0, None))
    m.Charge_pertime_route   = Var(m.b, m.t, bounds=(0, None))

    m.Charging_f1    = Var(m.b, m.t, domain=Binary)
    m.Charging_f2 = Var(m.b, m.t, domain=Binary)
    m.Charging_f3 = Var(m.b, m.t, domain=Binary)
    m.Charging_f4 = Var(m.b, m.t, domain=Binary)
    m.Charging_route   = Var(m.b, m.t, domain=Binary)

    m.Max_Power = Var(bounds=(0, None))

    # -----------------------------
    # 1) Charging energy & power constraints
    # -----------------------------

    # 1.1) Grid energy purchase is equal to pertime charge (Including losses)

    @m.Constraint(m.b, m.t)
    def Total_Grid_Purchase_rule(m, b, t):
        return m.Total_Grid_purchase[b, t] * m.Ch_losses - m.Charge_pertime[b, t] == 0 
    
    # 1.2) Total pertime charging is equal to all types of charging

    @m.Constraint(m.b, m.t)
    def Sum_Total_Charge_pertime_rule(m, b, t):
        return m.Charge_pertime[b, t] == (
            m.Charge_pertime_f1[b, t] +
            m.Charge_pertime_f2[b, t] +
            m.Charge_pertime_f3[b, t] +
            m.Charge_pertime_f4[b, t] +
            m.Charge_pertime_route[b, t]
        )

    # 1.3. Constraints in maximum charging per type of charger
    
    @m.Constraint(m.b, m.t)
    def Charge_pertime_f1_rule(m, b, t):
        return m.Charge_pertime_f1[b, t] <= (
            m.delta_t * m.Cap_f1[b] * m.Charging_f1[b, t] * m.EV_availability[b, t]
        )

    @m.Constraint(m.b, m.t)
    def Charge_pertime_f2_rule(m, b, t):
        return m.Charge_pertime_f2[b, t] <= (
            m.delta_t * m.Cap_f2[b] * m.Charging_f2[b, t] * m.EV_availability[b, t]
        )

    @m.Constraint(m.b, m.t)
    def Charge_pertime_f3_rule(m, b, t):
        return m.Charge_pertime_f3[b, t] <= (
            m.delta_t * m.Cap_f3[b] * m.Charging_f3[b, t] * m.EV_availability[b, t]
        )

    @m.Constraint(m.b, m.t)
    def Charge_pertime_f4_rule(m, b, t):
        return m.Charge_pertime_f4[b, t] <= (
            m.delta_t * m.Cap_f4[b] * m.Charging_f4[b, t] * m.EV_availability[b, t]
        )

    @m.Constraint(m.b, m.t)
    def route_Charging_rule(m, b, t):
        return m.Charge_pertime_route[b, t] <= (
            m.delta_t * m.Cap_route[b] * m.Charging_route[b, t] * (1 - m.EV_availability[b, t])
        )

    # 1.6. Charging energy in the distribution terminal by vehicle (v) and time (t)

    @m.Constraint(m.b, m.t)
    def DT_Grid_Purchase_rule(m, b, t):
        return m.DT_Grid_purchase[b, t] * m.Ch_losses == (
            m.Charge_pertime_f1[b, t] +
            m.Charge_pertime_f2[b, t] +
            m.Charge_pertime_f3[b, t] +
            m.Charge_pertime_f4[b, t]
        )
    # 1.7. Variable maximum power demand from the grid at DT was constrained as the maximum power purchased from the grid at a specific timestep for the summation of all vehicles at the DT (Eq8)
    
    @m.Constraint(m.t)
    def Max_Power_Constraint_rule(m, t):
        return quicksum(m.DT_Grid_purchase[b, t] for b in m.b) <= m.Max_Power

    # -----------------------------
    # 2) Charger count constraints
    # -----------------------------

    # 2.1) Define the required amount of slow chargers (Eq9)

    @m.Constraint(m.t)
    def Balance_CS_f1_rule(m, t):
        return m.CS_f1 >= quicksum(m.Charging_f1[b, t] for b in m.b)

    @m.Constraint(m.t)
    def Balance_CS_f2_rule(m, t):
        return m.CS_f2 >= quicksum(m.Charging_f2[b, t] for b in m.b)

    @m.Constraint(m.t)
    def Balance_CS_f3_rule(m, t):
        return m.CS_f3 >= quicksum(m.Charging_f3[b, t] for b in m.b)

    @m.Constraint(m.t)
    def Balance_CS_f4_rule(m, t):
        return m.CS_f4 >= quicksum(m.Charging_f4[b, t] for b in m.b)

    @m.Constraint(m.t)
    def Balance_CS_route_rule(m, t):
        return m.CS_route >= quicksum(m.Charging_route[b, t] for b in m.b)

    @m.Constraint(m.b, m.t)
    def ChargersPerVehicle_rule(m, b, t):
        return (
            m.Charging_f1[b, t] +
            m.Charging_f2[b, t] +
            m.Charging_f3[b, t] +
            m.Charging_f4[b, t]
        ) <= 1
    
    # -----------------------------
    # 3) Discharge and SOC constraints
    # -----------------------------

    @m.Constraint(m.b, m.t)
    def Discharge_pertime_rule(m, b, t):
        return m.Discharge_pertime[b, t] == (
            m.Energy_Consumption_km[b, t] * m.Distance_km[b, t] * (1 - m.EV_availability[b, t])
        )

    @m.Constraint(m.b, m.t)
    def Storage_Level_rule(m, b, t):
        if t == 1:
            return m.Storage_level[b, t] == m.Start_Storage[b] + (m.Charge_pertime[b, t]* m.Ch_losses) - m.Discharge_pertime[b, t]
        return m.Storage_level[b, t] == m.Storage_level[b, t - 1] + m.Charge_pertime[b, t] - m.Discharge_pertime[b, t]

    @m.Constraint(m.b)
    def Storage_Level_Start_rule(m, b):
        return m.Start_Storage[b] == m.BatMax * m.Battery_Limitation[b]

    @m.Constraint(m.b, m.t)
    def Max_Storage_rule(m, b, t):
        return m.Storage_level[b, t] <= m.BatMax * m.Battery_Limitation[b]

    @m.Constraint(m.b, m.t)
    def Min_Storage_rule(m, b, t):
        return m.Storage_level[b, t] >= m.BatMin * m.Battery_Limitation[b]


    # ------------ Objective ------------
    def obj_rule(m):
        infra = (
            m.CS_f1 * Annualized_Infrastructure_cost['f1'] +
            m.CS_f2 * Annualized_Infrastructure_cost['f2'] +
            m.CS_f3 * Annualized_Infrastructure_cost['f3'] +
            m.CS_f4 * Annualized_Infrastructure_cost['f4'] +
            m.Infrastructure_subscription * days
        )

        energy_dt = quicksum(
            (m.Charge_pertime_f1[b, t] / m.Ch_losses * (m.Price[t] + m.Price_FixedrateDT)+
             m.Charge_pertime_f2[b, t] / m.Ch_losses * (m.Price[t] + m.Price_FixedrateDT)+
             m.Charge_pertime_f3[b, t] / m.Ch_losses * (m.Price[t] + m.Price_FixedrateDT)+
             m.Charge_pertime_f4[b, t] / m.Ch_losses * (m.Price[t] + m.Price_FixedrateDT))
            for b in m.b for t in m.t
        )

        energy_route = quicksum(
            m.Charge_pertime_route[b, t] / m.Ch_losses * m.Price_Fixedrateroute
            for b in m.b for t in m.t
        )

        demand = m.Max_Power * m.Demand_rate

        # Keep your penalty if you want to discourage route charging
        penalty = quicksum(m.Charging_route[b, t] * 99999 for b in m.b for t in m.t) + m.CS_route*0.1


        return infra + energy_dt + energy_route + demand + penalty

    m.objective = Objective(rule=obj_rule, sense=pyo.minimize)

    # ------------ Solver ------------
    solver = SolverFactory('gurobi')
    
    # Compromise: Semi-deterministic but faster

    solver.options['MIPGap'] = opt_config["MIPGap"]
    solver.options['ScaleFlag'] = 2
    solver.options['LogFile'] = "gurobi_log_V2.txt"

    # Speed vs determinism balance
    # Threads increase RAM pressure significantly (each worker needs its own state).
    # For large MILPs, fewer threads is often *more* stable.
    solver.options['Threads'] = 16
    solver.options['Seed'] = 42                   # Fixed seed for some reproducibility
    solver.options['Method'] = -1                  # Deterministic barrier method
    solver.options['Presolve'] = 2                # Keep presolve for speed
    solver.options['NodeMethod'] = 2              # Deterministic node method

    # Memory-friendly settings
    # Cuts can blow up memory; prefer fewer cuts on very large instances.
    solver.options['Cuts'] = 1
    solver.options['Cutpasses'] = 5
    solver.options['Heuristics'] = 0.5
    #solver.options['SolutionLimit'] = 5  # Stop after finding 5 good solutions
    #solver.options['BestObjStop'] = 5e6  # Stop if objective < 5M

    solver.options['NodefileStart'] = 2          # start writing B&B nodes to disk (GB) - earlier is safer
    
    # Optional safety rails (uncomment if you prefer a bounded run instead of risking OOM)
    # solver.options['TimeLimit'] = 6 * 3600       # e.g. 6 hours
    # solver.options['MemLimit'] = 0               # set to a value in MB to force early stop (license dependent)

    #solver.options['TimeLimit'] = 3600            # 1 hour limit per job
    solver.options['MIPFocus'] = 2  
    
      
    
    print(f"→ Solving model with {EVs} vehicles over {hours} time steps (delta_t={delta_t})...")
    t_start = time.time()
    result = solver.solve(m, tee=True)
    print(f"Solve completed in {time.time() - t_start:.1f} seconds")
    print(f"Termination condition: {result.solver.termination_condition}")

    return m, Price, EV_availability, Distance_km




def save_results(m, Price, EV_availability, Distance_km, csv_file_pathA, csv_file_pathB, csv_file_pathC, cost_config, power_config):
    
    # Parameters
    Ch_losses = power_config["Charging_losses"]  # Charging efficiency
    Infrastructure_life = cost_config["Infrastructure_life"]
    r = cost_config["Discount_rate"]
    Annuity_factor = (r * (1 + r) ** Infrastructure_life) / ((1 + r) ** Infrastructure_life - 1)

    Infrastructure_cost = cost_config["Infrastructure_cost"]
    
    Charger_Power = power_config["Charger_Power"]
    maintenance_cost = cost_config["maintenance_cost"]

    Annualized_Infrastructure_cost = {
        'f1': Infrastructure_cost['f1'] * Annuity_factor + maintenance_cost['f1'],
        'f2': Infrastructure_cost['f2'] * Annuity_factor + maintenance_cost['f2'],
        'f3': Infrastructure_cost['f3'] * Annuity_factor + maintenance_cost['f3'],
        'f4': Infrastructure_cost['f4'] * Annuity_factor + maintenance_cost['f4']
    }

    Infrastructure_subscription = cost_config["Infrastructure_subscription"]
    Price_FixedrateDT = cost_config["Price_FixedrateDT"]
    Price_Fixedrateroute = cost_config["Price_Fixedrateroute"]
    

    """
    Optimized function to save results from the optimisation model
    """
    
    delta_t = pyo.value(m.delta_t)                                                  # ◄◄◄ NEW — read delta_t from model
    steps_per_day = int(round(24.0 / delta_t))
    
    # 1. Save Main Variables Per Hour
    data = []

    def day(t):                                                                     # ◄◄◄ CHANGED — was hardcoded to 24
        return (t - 1) // steps_per_day + 1                                         # ◄◄◄ CHANGED

    def step_of_day(t):                                                             # ◄◄◄ NEW — replaces old hour calc
        return (t - 1) % steps_per_day 

    for t in m.t:
        data.append({
            'Date': day(t),
            'Step': step_of_day(t),
            'Time': f"{step_of_day(t) * delta_t:.2f}", 
            'Charging energy': sum(pyo.value(m.Charge_pertime[b, t]) for b in m.b),
            'Price': Price[t],
            'Energy Purchase from grid': sum(pyo.value(m.Total_Grid_purchase[b, t]) for b in m.b),
            'Cost of energy supply from grid at DT': sum(pyo.value(m.DT_Grid_purchase[b, t] * (Price[t] + Price_FixedrateDT)) for b in m.b),
            'Cost of energy supply on route': sum(pyo.value((m.Total_Grid_purchase[b, t] - m.DT_Grid_purchase[b, t]) * (Price_Fixedrateroute)) for b in m.b),
            'EVs f1 charging': sum(pyo.value(m.Charging_f1[b, t]) for b in m.b),
            'EVs f2 charging': sum(pyo.value(m.Charging_f2[b, t]) for b in m.b),
            'EVs f3 charging': sum(pyo.value(m.Charging_f3[b, t]) for b in m.b),
            'EVs f4 charging': sum(pyo.value(m.Charging_f4[b, t]) for b in m.b),
            'EVs route charging': sum(pyo.value(m.Charging_route[b, t]) for b in m.b),
            'f1 Charging pertime': sum(pyo.value(m.Charge_pertime_f1[b, t]) for b in m.b),
            'f2 Charging pertime': sum(pyo.value(m.Charge_pertime_f2[b, t]) for b in m.b),
            'f3 Charging pertime': sum(pyo.value(m.Charge_pertime_f3[b, t]) for b in m.b),
            'f4 Charging pertime': sum(pyo.value(m.Charge_pertime_f4[b, t]) for b in m.b),
            'route Charging pertime': sum(pyo.value(m.Charge_pertime_route[b, t]) for b in m.b)
        })
    
    df = pd.DataFrame(data)
    df.to_csv(csv_file_pathA, index=False)  # Save to CSV efficiently

  

    # 2. Save Summary Data 
    with open(csv_file_pathB, mode='w', newline='') as file:
        fieldnames = ['Category', 'Description', 'Value']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        # Charging Stations f1
        writer.writerow({'Category': 'f1 CS', 'Description': 'Chargers number', 
                 'Value': pyo.value(m.CS_f1)})

        writer.writerow({'Category': 'f1 CS', 'Description': 'Infrastructure Cost', 
                 'Value': pyo.value(m.CS_f1) * Annualized_Infrastructure_cost['f1']})

        writer.writerow({'Category': 'f1 CS', 'Description': 'Electricity Cost', 'Value': sum(pyo.value(m.Charge_pertime_f1[b, t])  / Ch_losses * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t)})

        # Charging Stations f2
        writer.writerow({'Category': f'f2 CS {Charger_Power["f2"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_f2)}) 

        writer.writerow({'Category': f'f2 CS {Charger_Power["f2"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_f2) * Annualized_Infrastructure_cost['f2']})

        writer.writerow({'Category': f'f2 CS {Charger_Power["f2"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_f2[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})

        # Charging Stations f3
        writer.writerow({'Category': f'f3 CS {Charger_Power["f3"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_f3)}) 

        writer.writerow({'Category': f'f3 CS {Charger_Power["f3"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_f3) * Annualized_Infrastructure_cost['f3']})

        writer.writerow({'Category': f'f3 CS {Charger_Power["f3"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_f3[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})

        # Charging Stations f4
        writer.writerow({'Category': f'f4 CS {Charger_Power["f4"]}kW', 'Description': 'Chargers number', 
            'Value': pyo.value(m.CS_f4)}) 

        writer.writerow({'Category': f'f4 CS {Charger_Power["f4"]}kW', 'Description': 'Infrastructure Cost', 
            'Value': pyo.value(m.CS_f4) * Annualized_Infrastructure_cost['f4']})

        writer.writerow({'Category': f'f4 CS {Charger_Power["f4"]}kW', 'Description': 'Electricity Cost', 
            'Value': sum(pyo.value(m.Charge_pertime_f4[b, t]) / Ch_losses * (Price[t] + Price_FixedrateDT) 
                    for b in m.b for t in m.t)})
            
        writer.writerow({'Category': 'DT', 'Description': 'Infrastructure Cost', 'Value': (
            pyo.value(m.CS_f1) * Annualized_Infrastructure_cost['f1'] +
            pyo.value(m.CS_f2) * Annualized_Infrastructure_cost['f2'] +
            pyo.value(m.CS_f3) * Annualized_Infrastructure_cost['f3'] +
            pyo.value(m.CS_f4) * Annualized_Infrastructure_cost['f4']
        )})
        writer.writerow({'Category': 'DT', 'Description': 'Electricity Cost', 'Value': sum((pyo.value(m.DT_Grid_purchase[b, t]) * (Price[t] + Price_FixedrateDT) for b in m.b for t in m.t))})
        writer.writerow({'Category': 'DT', 'Description': 'Chargers number', 'Value': pyo.value(m.CS_f1) + pyo.value(m.CS_f2) + pyo.value(m.CS_f3) + pyo.value(m.CS_f4)})
        writer.writerow({'Category': 'DT', 'Description': 'Max Power [kW]', 'Value': pyo.value(m.Max_Power)})

        writer.writerow({'Category': 'route CS', 'Description': 'Chargers number', 'Value': pyo.value(m.CS_route)})
        #writer.writerow({'Category': 'route CS', 'Description': 'Times', 'Value': sum(pyo.value(m.Charging_route[b, t]) for b in m.b for t in m.t)})
        writer.writerow({'Category': 'route CS', 'Description': 'Electricity Cost', 'Value': sum(pyo.value(m.Charge_pertime_route[b, t]) * Price_Fixedrateroute for b in m.b for t in m.t)})

    # 3. EV descriptive file
    with open(csv_file_pathC,  mode='w', newline='') as file:
        writer = csv.writer(file)

        header = [
            'Day', 'Step', 'Time', 'Price', 'Vehicle ID', 'Charging Energy',
            'Discharging Energy', 'Storage Level', 
            'Cost of energy supply from grid at DT', 'Cost of energy supply on route', 'EV Available',
            'f1 Charging', 'f2 Charging', 'f3 Charging',
            'f4 Charging', 'route Charging', 'Distance travelled by hour'
        ]

        writer.writerow(header)

        for t in m.t:
            for b in m.b:
                writer.writerow([
                    day(t),                                                         
                    step_of_day(t),                                                 
                    f"{step_of_day(t) * delta_t:.2f}",                              
                    Price[t],
                    b,
                    pyo.value(m.Charge_pertime[b, t]),
                    pyo.value(m.Discharge_pertime[b, t]),
                    pyo.value(m.Storage_level[b, t]),
                    pyo.value(m.DT_Grid_purchase[b, t] * (Price[t] + Price_FixedrateDT)),
                    pyo.value((m.Total_Grid_purchase[b, t] - m.DT_Grid_purchase[b, t]) * (Price_Fixedrateroute)),
                    EV_availability[b, t],
                    pyo.value(m.Charge_pertime_f1[b, t]),
                    pyo.value(m.Charge_pertime_f2[b, t]),
                    pyo.value(m.Charge_pertime_f3[b, t]),
                    pyo.value(m.Charge_pertime_f4[b, t]),
                    pyo.value(m.Charge_pertime_route[b, t]),
                    pyo.value(Distance_km[b, t])
                ])
    print("✅ Results saved successfully as CSV!")
