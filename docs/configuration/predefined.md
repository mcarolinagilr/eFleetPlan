# 2.4. Predefined parameters

**Directory:** all the configuration setting already defined are located in `config/predefined/`

The predefined directory contains reusable parameter sets for schedules, vehicles, companies, and infrastructure. These are referenced by name in the run configuration files.

##  2.4.1 Type of schedules
The `schedules.yaml` includes schedule profiles, with the main focus on defining the departure and return times, which can vary by weekday and weekend, and whether the schedule is continuous or split into two parts. 
Each profile name can used a `schedule_mix`.

### **Available profiles:**

- `typea` — Continuous single-trip schedule (depart once, return once)
- `typeb` — Two-part schedule with a midday distribution terminal break

Each profile contains the schedule timing parameters described in the [Schedule Generation](fleetoperation_simulation.md) configuration reference.
To add a new schedule type, add a new top-level key with all required fields, but you can also use the custom option in the run_FleetSchedule_Config.yaml file.

```yaml
typea:
  dep_mean_wd: 8
  dep_dev_wd: 1
  ret_mean_wd: 18
  ret_dev_wd: 1
  dep_mean_we: 8
  dep_dev_we: 1
  ret_mean_we: 18
  ret_dev_we: 1
  min_dep: 6
  max_dep: 11
  min_return_hour: 18
  max_return_hour: 22

typeb:
  dep_mean_wd: 6
  dep_dev_wd: 1
  min_dep: 3
  max_dep: 10
  pause_beg_mean_wd: 12
  pause_beg_dev_wd: 0.25
  pause_end_mean: 13
  pause_end_dev: 0.25
  max_beg_time: 13
  min_beg_time: 11
  max_pause_end: 15
  min_pause_end: 12
  pause_time_mean: 0.5
  pause_time_dev: 0.1
  ret_mean_wd: 19
  ret_dev_wd: 1
  max_return_hour: 22
  min_return_hour: 15
  dep_mean_we: 9
  dep_dev_we: 1
  pause_beg_mean_we: 12
  pause_beg_dev_we: 0.25
  ret_mean_we: 19
  ret_dev_we: 0.5
  prob_emergency: 0.02
```

##  2.4.2 Type of vehicle
  File `vehicles.yaml` includes vehicle specifications. Each top-level key is a vehicle model name that can be used in `vehicle_mix`.
  Each vehicle model profile contains the vehicle parameters described in the [Schedule Generation](fleetoperation_simulation.md) configuration reference (consumption rates, battery capacity, charging power).

  **Available profiles:**
  - `renault` — Based on Renault electric LCV specifications
  - `toyota` — Based on Toyota electric LCV specifications

  


##  2.4.3 Type of companies
  The file `companies.yaml` includes company profiles (distance patterns and stop behaviour). Each top-level key is a company type that can be used in `company_type`. The company types are based on findings from a survey on light goods vehicles in Sweden conducted by Transport Analysis (2022). Types include different transport use cases such as distribution transport, line haul, and service/craft operations.
  Each company profile contains the company parameters described in the [Schedule Generation](fleetoperation_simulation.md) configuration settings. Reference: Transport Analysis, “Light goods vehicles 2022,” Stockolm, 2023.



##  2.4.4 Type of charging infrastructures
  The file `infrastructure_configuration.yaml` includes chargers specifications and costs for Package 2 - Co-optimisation function. This file is used when `infrastructure_configurations: predefined` is set in the optimisation run config. 
  The structure matches the custom infrastructure parameters described in the [Co-optimisation](Co-optimisation.md) configuration reference: charger power levels, investment costs, installation costs, maintenance costs, battery limits, and financial parameters.


## 2.4.5 Adding predefined parameters

To add new entries to the predefined parameters:
1. Open the relevant YAML file in `config/predefined/`.
2. Add a new top-level key with all required fields, following the same structure as existing entries.
3. Reference the new key by name in your run configuration.

For example, to add a new vehicle type:
```yaml
# In vehicles.yaml
my_new_van:
  consumption_mean: 0.25
  consumption_std: 0.08
  consumption_min: 0.12
  consumption_max: 0.35
  total_cons_clip: 50
  battery_capacity: 60
  charging_power: 100
```

Then reference it in `run_FleetSchedule_Config.yaml`:
```yaml
fleet:
  vehicle_mix:
    my_new_van: 30
    renault: 20
```
