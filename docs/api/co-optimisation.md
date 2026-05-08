# Co-optimisation functions

**Package:** `src.efleetplan._2_optimisation.co_optimisation`

## `optimisation`

```python
def optimisation(
    opt_config: dict,
    cost_config: dict,
    power_config: dict,
) -> tuple[ConcreteModel, dict, dict, dict]
```

This function build and solve the charging infrastructure Co-optimisation model.
It constructs a Pyomo `ConcreteModel` with all parameters, variables, constraints, and the objective function, then solves it using Gurobi or other choosen solver.

**Parameters:**

- `opt_config` (dictionaries) — run settings and input data, as returned by `load_opt_config()`. Key entries include:
    - `opt_start_date`, `opt_end_date` — definition of time horizon (start and end date)
    - `EVs` — number of vehicles
    - `delta_time` — timestep duration in hours
    - `MIPGap` — Optimality solver gap tolerance of optimisation 
    - `electricity_price_grid` — load of price DataFrame included in the input folder
    - `En_consumption`, `Ev_distance`, `EV_availability`, `Battery_Limitation`, `PowerRate_Limitation` — pivoted vehicle dataFrames loaded from package 1 file, or user costum files.
- `cost_config` (dictionaries) — infrastructure and electricity cost parameters:
    - `Infrastructure_life`, Infrastructure lifetime
    - `Discount_rate`, Discount rate applied to infrastructure investment costs 
    - `Infrastructure_cost`, Infrastructure investment cost per type of charger power + Infrastructure installation cost per type of charger power
    - `maintenance_cost`, Infrastructure maintenance cost per type of charger powere
    - `Infrastructure_subscription`, Electricity subscription cost 
    - `Price_FixedrateDT`, Fixed rate of electricity price at the distribution terminal 
    - `Demand_rate`, Demand charge based on the annual maximum power  
    - `Price_Fixedrateroute`, Fix rate of electricity price on route 
- `power_config` (dictionairies) — charger and battery parameters:
    - `Charger_Power` — Charging power rates per type of charger 
    - `Charging_losses`, Charging losses rate 
    - `Battery_Maximum_Limit`, Maximum limit of the battery
    - `Battery_Minimum_Limit`, Minimum limit of the battery

**Returns:** `(model, Price, EV_availability, Distance_km)` — the solved Pyomo model and key data dictionaries for result extraction.

---

## `prepare_data`

```python
def prepare_data(opt_config: dict) -> tuple
```

This function prepares input data arrays from the configuration dictionaries. It converts the pivoted DataFrames and price data into indexed dictionaries suitable for Pyomo parameter initialisation.

**Returns:** `(EV_availability, Distance_km, Energy_Consumption_km, Price, Battery_Limitation, PowerRate_Limitation, hours, days, EVs, delta_t)`

---

## `save_results`

```python
def save_results(
    m, Price, EV_availability, Distance_km,
    csv_file_pathA, csv_file_pathB, csv_file_pathC,
    cost_config, power_config,
)
```
This function extract results from the solved model and save to CSV.

**Outputs:**

- **Path A** — Main variables per hour: charging energy, grid purchases, costs, and charger usage aggregated across all vehicles.
- **Path B** — Summary table: charger counts, infrastructure costs, and electricity costs per charger type and category.
- **Path C** — Per-vehicle results: hourly charging/discharging energy, storage level, electricity costs, charger usage, and distance for each vehicle.

---

## `calculate_days`

```python
def calculate_days(start_str: str, end_str: str) -> int
```

This function calculates the number of days between two datetime strings (inclusive).

**Parameters:**

- `start_str` — start date in `"YYYY-MM-DD HH:MM:SS"` format
- `end_str` — end date in the same format

**Returns:** number of days (int)

---

## Model structure

The Pyomo model (`ConcreteModel`) contains:

**Sets:**

- `m.t` — hourly timesteps (1 to total hours)
- `m.b` — vehicles (1 to EVs)

**Key decision variables:**

| Variable | Domain | Description |
|----------|--------|-------------|
| `m.CS_f1` ... `m.CS_f4` | NonNegativeInteger | Number of chargers per charger power type |
| `m.CS_route` | NonNegativeInteger | Number of route chargers |
| `m.Storage_level[b,t]` | NonNegative | Battery state of charge per vehicle per steptime |
| `m.Charge_pertime[b,t]` | NonNegative | Total charging energy per vehicle per steptime |
| `m.Total_Grid_purchase[b,t]` | NonNegative | Grid energy purchased per vehicle per steptime |
| `m.DT_Grid_purchase[b,t]` | NonNegative | Depot grid energy per vehicle per steptime |
| `m.Max_Power` | NonNegative | Peak power demand |


**Objective function:**

```python
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
```
