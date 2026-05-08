# 2.3. Co-optimisation configurations
**File:** `config/run_Optimisation_Config.yaml`
This file defines one Co-optimisation run for Package 2. Create a separate file for each scenario.

## 2.3.1 Example
```yaml
schedule_name: "schedule_1"
schedule_number: 1
electricity_price_file: "el_prices_2024.csv"

EVs: 50
MIPGap: 0.005

infrastructure_configurations: predefined
# Set to "custom" to use the parameters below instead of infrastructure_configuration.yaml
```

## 2.3.2 Parameters
### Run settings
| Parameter | Type | Description |
|-----------|------|-------------|
| `schedule_name` | string | Name of the schedule folder in `data/Output/`. |
| `schedule_number` | int | Numeric identifier for the schedule (used in output filenames). |
| `electricity_price_file` | string | Filename of the electricity price CSV in `data/Input/`. Must contain columns `date` (or `Date`) and `Elect_price`. |
| `EVs` | int (> 0) | Number of electric vehicles. Must match the schedule. |
| `MIPGap` | float (0, 1) | Solver optimality gap. Smaller values give tighter solutions but take longer. |
| `infrastructure_configurations` | string | `"predefined"` to load from `predefined/infrastructure_configuration.yaml`, or `"custom"` to use parameters defined in this file. |

### Automatically resolved settings
These are loaded from `env.yaml` if not specified in the run config:

| Parameter | Type | Default source | Description |
|-----------|------|----------------|-------------|
| `opt_start_date` | string | `env.yaml` → `simulation.start_date` | Optimisation start datetime. |
| `opt_end_date` | string | `env.yaml` → `simulation.end_date` | Optimisation end datetime. |
| `freq` | string | `"h"` | Time resolution. |
| `delta_time` | float | `1.0` | Timestep duration in hours. |
| `Accumulated_Cycle_Capacity` | float | `3500.0` | Accumulated battery cycle capacity. |

### Custom infrastructure parameters
When `infrastructure_configurations: custom`, the following parameters are read from this file instead of the predefined YAML:

**Cost and financial parameters:**
| Parameter | Type | Unit | Description |
|-----------|------|------|-------------|
| `lifetime` | int | years | Infrastructure economic lifetime |
| `Discount_rate` | float | — | Discount rate for annualisation (e.g. 0.05 = 5%) |
| `Infrastructure_subscription` | float | currency/day | Daily subscription fee |
| `Price_FixedrateDT` | float | currency/kWh | Fixed electricity rate at the depot |
| `Demand_rate` | float | currency/kW | Demand charge rate |
| `Price_Fixedrateroute` | float | currency/route | Fixed cost per route charging event |

**Charger power levels:**
```yaml
Charger_Power:
  f1: 7.4      # kW
  f2: 50       # kW
  f3: 150      # kW
  f4: 350      # kW
  route: 150   # kW
```

**Battery limits:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `Charging_losses` | float (0, 1] | Charging efficiency (e.g. 0.964 = 96.4%) |
| `Battery_Maximum_Limit` | float (0, 1] | Maximum SoC as fraction of capacity (e.g. 0.8 = 80%) |
| `Battery_Minimum_Limit` | float (0, 1] | Minimum SoC as fraction of capacity (e.g. 0.2 = 20%) |

**Investment and maintenance costs (per charger type):**
```yaml
investment cost:
  f1: 1000        # currency
  f2: 1000000
  f3: 10000000
  f4: 100000000
  route: 100000000

installation cost:
  f1: 1
  f2: 1
  f3: 1
  f4: 1
  route: 1

maintenance cost:
  f1: 1           # currency/year
  f2: 1
  f3: 1
  f4: 1
  route: 1
```

The total annualised cost per charger is calculated as: `(investment + installation) * annuity_factor + maintenance`, where the annuity factor is derived from the discount rate and lifetime.

## 2.3.3 Validation
The config loader validates:
- `EVs` must be positive
- `MIPGap` must be between 0 and 1 (exclusive)
- `Charging_losses` must be in (0, 1]
- `Battery_Maximum_Limit` and `Battery_Minimum_Limit` must be in (0, 1]
