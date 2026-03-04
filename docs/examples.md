# Examples & Tutorials
This page shows different examples of  cases studies for eFleetPlan.

## Example 1 — Basic scenario with 50 vehicles

This is the default scenario included in the repository.

### Case study parameters configuration

**`env.yaml`:**

```yaml
seed: 42
simulation:
  start_date: "2024-01-01 00:00:00"
  end_date: "2024-01-31 23:00:00"
  freq: "h"
paths:
  consumption_factor_file: "../data/Input/consumption_factor_2024.csv"
  output_base: "../data/Output"
```

**`run_FleetSchedule_Config.yaml`:**

```yaml
schedule_name: "schedule_1"
fleet:
  n_vehicles: 50
  schedule_mix:
    typea: 50
    typeb: 0
  vehicle_mix:
    renault: 25
    toyota: 25
  company_type: distribution
```

**`run_Optimisation_Config.yaml`:**

```yaml
schedule_name: "schedule_1"
schedule_number: 1
electricity_price_file: "el_prices_2024.csv"
EVs: 50
MIPGap: 0.005
infrastructure_configurations: predefined
```

### Steps

1. Place input data in `data/Input/`.
2. Run notebook 1 to generate schedules.
3. Run notebook 2 to optimise infrastructure.
4. Results are saved to `data/Output/schedule_1/Results/`.

---

## Example 2 — Mixed fleet with Type A and Type B schedules

This scenario splits the fleet between continuous (Type A) and two-part (Type B) schedules to model a fleet with different operational patterns.

### Case study parameters configurations
**`run_FleetSchedule_Config.yaml`:**

```yaml
schedule_name: "schedule_mixed"
fleet:
  n_vehicles: 50
  schedule_mix:
    typea: 25
    typeb: 25
  vehicle_mix:
    renault: 25
    toyota: 25
  company_type: food
```

### Steps
1. Place input data in `data/Input/`.
2. Run notebook 1 to generate schedules.
3. Run notebook 2 to optimise infrastructure.
4. Results are saved to `data/Output/schedule_1/Results/`.

---

## Example 3 — Custom vehicle, company parameters and Infrastructure parameters

In the example, user defines the vehicle and the type of company to generate different schedules.
Next, user also define the infrastructure costs and charging power to include in the co-optimisation model.

### Case study parameters configuration 

**`run_FleetSchedule_Config.yaml`:**

```yaml
schedule_name: "schedule_custom"
fleet:
  n_vehicles: 30
  schedule_mix:
    typea: 30
  vehicle_mix:
    custom: 30
  company_type: custom

custom_vehicle:
  consumption_mean: 0.25
  consumption_std: 0.08
  consumption_min: 0.12
  consumption_max: 0.35
  total_cons_clip: 50
  battery_capacity: 60
  charging_power: 100

custom_company:
  avg_distance_wd: 120
  dev_distance_wd: 15
  avg_distance_we: 70
  dev_distance_we: 15
  min_distance: 30
  max_distance: 300
  min_distance_per_step: 1
  max_distance_per_step: 50
  avg_stops: 30
  dev_stops: 10

```

**`run_Optimisation_Config.yaml`:**

```yaml
schedule_name: "schedule_custom"
infrastructure_configurations: custom 

lifetime: 20 #years
Infrastructure_subscription: 50 #currency/day
Price_FixedrateDT: 0.0331 #currency/kWh
Demand_rate: 1352 #kW
Price_Fixedrateroute: 8.90 #currency/route
Discount_rate: 0.05 #%

Charging_losses: 0.964

Charger_Power: 
  f1: 7.4
  f2: 50
  f3: 150
  f4: 350
  route: 150
  

Battery_Maximum_Limit: 0.8  # Maximum limit of the battery (80% of its capacity)
Battery_Minimum_Limit: 0.2   # Minimum limit of the battery (20% of its capacity)

investment cost: 
  f1: 1000 #currency
  f2: 1000000 #currency
  f3: 10000000 #currency
  f4: 100000000 #currency

installation cost:
  f1: 100 #currency
  f2: 100 #currency
  f3: 100 #currency
  f4: 100 #currency

maintenance cost:
  f1: 100 #currency/year
  f2: 200 #currency/year
  f3: 300 #currency/year
  f4: 400 #currency/year


```
### Steps
1. Place input data in `data/Input/`.
2. Run notebook 1 to generate schedules.
3. Run notebook 2 to optimise infrastructure.
4. Results are saved to `data/Output/schedule_1/Results/`.
