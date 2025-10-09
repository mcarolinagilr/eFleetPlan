# Module and Function Reference

This section provides a detailed description of the modules, scripts, and functions used in the scheduling and optimization framework. Each function is documented with its main purpose, input parameters, and expected outputs, including generated files and figures.


## Schedule Module (_1_schedule)

Files: schedule_configure.py and schedule_generator.py

### File schedule_configure.py

Description: This file defines all configuration parameters and classes for schedule types, vehicle types, and company types. It acts as a central configuration repository used by other modules.
Functions: No executable functions are defined in this file.
Inputs: None (static configuration definitions).
Outputs: No direct outputs are generated. The configuration data is passed to schedule_generator.py for use in schedule generation.

### File schedule_generator.py

Description: This module contains functions that generate vehicle schedules based on configuration data. It produces detailed time-based activity and energy use profiles for one or more vehicles.

#### Function generate_schedule()
Purpose: Generates a complete daily schedule for a single vehicle using the configuration data provided.
Inputs: The active configuration context, which includes schedule type, vehicle type, and company type (derived from the configuration classes in schedule_configure.py).
Outputs: Returns an in-memory schedule object or dataframe representing one vehicle’s operation profile. This function does not write any output files directly.

#### Function generate_fleet_schedules(env_config, sch_config)
Purpose: Generates schedules for an entire vehicle fleet by repeatedly calling generate_schedule() and combining the individual outputs into comprehensive datasets.
Inputs:
- env_config (environmental configuration):

    - original_seed: Seed for the random number generator (optional).

    - gen_start_date / gen_end_date: Start and end dates for schedule generation.

    - freq: Temporal frequency of data (e.g., 'h' for hourly).

    - consumption_factor_file: Path to the CSV file containing hourly energy consumption factors.

- sch_config (schedule configuration):

    - Vehicles number: Number of vehicles in the fleet.

    - Type of schedule: Share of each schedule type (type a, type b, or type c).

    - Custom Schedule: Average and standard deviation of departure and return times (weekday/weekend) with minimum and maximum time bounds.

    - Type of vehicle: Share of each vehicle type (Renault, Toyota, Custom).

    - Custom Vehicle: Custom consumption parameters (mean, std, min, max) and battery capacity.

    - Company type: Specifies the operational profile (e.g., Distribution, LineHaul, Mail, Building, Custom).

    - Custom Distance: Average daily distance, standard deviations, and limits for weekdays and weekends, along with stop frequency.

    - Schedule name: Custom label for identifying the generated schedule.

Outputs: 

Generates several CSV files containing the full schedule datasets:

- 2_all_vehicles_consumption_km.csv: Hourly energy consumption (kWh) and distance per vehicle.

- 2_all_vehicles_Distance_km.csv: Hourly distance per vehicle (km).

- 2_all_vehicles_ChargingStation.csv: Vehicle availability at depot or on route.

- 2_all_vehicles_PowerRating_kW.csv: Charging power (kW) per vehicle.


## File generate_graphs.py

Description: Generates visual summaries of the schedules created by the schedule_generator.py module.


### Function generate_graphs()

Purpose: Creates plots showing the average number of vehicles at the depot and their average hourly energy consumption.

Inputs:

- Output CSV files from schedule_generator.py.

- A designated output folder path.

Outputs:

Generates and saves the following figures:

- hourly_avg_vehicles_at_depot_{folder}.jpeg — hourly average number of vehicles at the depot.

- hourly_avg_energy_consumption_{folder}.jpeg — hourly average energy consumption (kWh).



## Optimisation Module (_2_optimisation)
### File optimisation.py
Description: Executes the energy and cost optimization for a fleet based on generated schedules. The optimization process uses vehicle energy demand, availability, and pricing data to minimize total operational costs.

#### Function optimisation(opt_config, cost_config, power_config)
Purpose: Runs the full optimization model for a defined time window and fleet.
Inputs:
- opt_config (optimization environment):
    - opt_start_date / opt_end_date: Start and end time for optimization.
    - freq: Time resolution (e.g., 'h' for hourly).
    - EVs: Number of vehicles to optimize.
    - output_folder / input_folder: Paths for data input and output.
    - electricity_price_grid: DataFrame of hourly grid electricity prices.
    - En_consumption, Ev_distance, Ev_availability_file, Battery_Limitation: DataFrames generated from the schedule module containing consumption, distance, availability, and power rating data.
- power_config:
    - Charging_losses: Charging efficiency factor.
    - Battery_Maximum Limit, Battery_Minimum Limit: SOC boundaries.
    - Accumulated_Cycle_Capacity: Total battery lifetime throughput (kWh).
- cost_config:
    - Infrastructure_life: Expected infrastructure lifetime (years).
    - Infrastructure_cost: Capital cost for each charger type.
    - Charger_Power: Power rating (kW) per charger type.
    - maintenance_cost: Annual maintenance costs.
    - Infrastructure_subscription: Daily fixed cost (SEK/day).
    - Price_FixedrateDT, Price_FixedrateRoute: Fixed electricity rates.
    - Demand_rate: Maximum demand charge (SEK/kW).
    - Discount_rate: Discount rate used for financial calculations.
Outputs: Calls save_results() to generate detailed CSV reports summarizing optimization performance.

#### Function save_results()
Purpose: Saves all model results into structured CSV files, including hourly data, summary statistics, and per-vehicle performance.
Inputs:
- m: Solved optimization model (Pyomo instance).
- Price: Hourly electricity prices.
- EV_availability: Availability matrix (vehicle × hour).
- Distance_km: Distance matrix (vehicle × hour).
- cost_config, power_config: Configuration dictionaries.
- File paths for all outputs.
Outputs:
Creates four CSV output files:
1.	2_Main_variables_results.csv — Hourly charging power, price, grid purchase, and energy metrics.
2.	2_results_summary.csv — Infrastructure and electricity cost summary by charger category.
3.	2_results_per_EV.csv — Optional per-vehicle aggregate data.
4.	2_results_per_EV_descriptive.csv — Detailed hourly per-vehicle metrics, including power, SOC, cycles, and cost splits.

### File optimisation_graphs.py
Description: Generates all graphical outputs and summaries for optimization results, including per-vehicle plots and cost tables.

#### Function graph_vehicles(file_path, n_days, n_vehicles)
Purpose: Visualises charging power, discharging power, and state of charge (SOC) for a selection of vehicles over a defined number of days.
Inputs:
- file_path: Path to 2_results_per_EV_descriptive.csv.
- n_days: Number of days to plot.
- n_vehicles: Number of vehicles to include.
Outputs:
- Saves the generated plot as a JPEG (same file path) and displays it interactively.

#### Function plot_summary_table()
Purpose: Creates summary tables showing infrastructure and electricity costs per category (Slow, Fast, DT, and Route chargers).
Outputs: Displays formatted tables as figures.

#### Function graph_number_of_chargers_by_schedules()
Outputs: Displays the resulting plot (optionally can be saved if implemented).

#### Function: graph_chargingpower()
Purpose: Creates a bar and line plot of average hourly charging power alongside the corresponding hourly average electricity price.
Outputs: Displays the generated plot.
