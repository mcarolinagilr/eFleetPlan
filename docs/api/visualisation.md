# Visualisation functions

## Package 1 — Schedule Graphs

**Package:** `src.efleetplan._1_schedule.generate_graphs`

### `generate_graphs`

```python
def generate_graphs(schedule_csv: str, folder: str, output_folder: str)
```

Generate summary graphs from a schedule CSV produced by Package 1.

**Parameters:**

- `schedule_csv` — path to the schedule CSV file
- `folder` — schedule name (used in output filenames)
- `output_folder` — directory to save graphs

**Expected CSV columns:** `date`, `Distance_km`, `Consumption_kWh`, `ChargingStation`, `VehicleID`

**Outputs (saved as JPEG at 600 DPI):**

| File | Description |
|------|-------------|
| `pertime_avg_vehicles_at_depot_<folder>.jpeg` | Bar chart showing the average number of vehicles at the depot per hour of day |
| `pertime_avg_energy_consumption_<folder>.jpeg` | Bar chart showing average total fleet energy consumption per hour of day |

---

## Package 2 — Optimisation Graphs

**Package:** `src.efleetplan._2_optimisation.optimisation_graphs`

### `plot_summary_table`

```python
def plot_summary_table(file_path: str)
```

Display the cost summary as a formatted table plot.

**Parameters:**

- `file_path` — path to a `*_results_summary.csv` file

**Shows:** two tables — one for charger-level costs (f1, f2, f3, f4, route) and one for the distribution terminal (DT) totals.

---

### `graph_vehicles`

```python
def graph_vehicles(folder_path: str, file_path: str, n_days: int, n_vehicles: int)
```

Plot per-vehicle charging/discharging energy and state of charge over time.

**Parameters:**

- `folder_path` — output directory for the saved graph
- `file_path` — path to a `*_results_per_EV.csv` file
- `n_days` — number of days to display
- `n_vehicles` — number of vehicles to plot

**Shows:** a stacked subplot for each vehicle with bar charts for charging/discharging energy and a line plot for state of charge (SOC).

**Output:** `charging_discharge_SOC.jpeg`

---

### `graph_number_of_chargers_by_schedules`

```python
def graph_number_of_chargers_by_schedules(folder_path: str, files_pertime_max: list)
```

Compare the number of chargers required across different schedule profiles.

**Parameters:**

- `folder_path` — output directory
- `files_pertime_max` — list of paths to `*_max_variable_per_hour.csv` files

**Shows:** grouped bar chart with charger counts by type (f1, f2, f3, f4, route) for each schedule.

**Output:** `Total_chargers_by_schedules.jpg`

---

### `graph_chargingenergy`

```python
def graph_chargingenergy(file_path: str, folder_path: str)
```

Plot average charging energy per hour alongside the electricity price.

**Parameters:**

- `file_path` — path to a `*_avg_variable_per_hour.csv` file
- `folder_path` — output directory

**Shows:** bar chart of hourly charging energy (left axis) with a line overlay of average electricity price (right axis).

**Output:** `NumberEVChargers_perchargingenergy.jpg`

---

### `graph_energybytype`

```python
def graph_energybytype(file_path: str, folder_path: str)
```

Plot average charging energy per hour broken down by charger type.

**Parameters:**

- `file_path` — path to a `*_avg_variable_per_hour.csv` file
- `folder_path` — output directory

**Shows:** grouped bar chart with slow (f1), fast (f2-f4), and route charging energy per hour, plus a price line overlay.

**Output:** `EVChargers_chargingenergybytype.jpg`

---

### `process_folder`

```python
def process_folder(folder_path: str, filename_pattern: str)
```

Post-process result files by calculating hourly max, average, and sum aggregations.

**Parameters:**

- `folder_path` — directory containing the result CSVs
- `filename_pattern` — glob pattern to match input files (e.g. `*_Main_variables_results.csv`)

**Outputs (per matched file):**

| File | Content |
|------|---------|
| `<N>_max_variable_per_hour.csv` | Maximum value per hour across all days |
| `<N>_avg_variable_per_hour.csv` | Average value per hour across all days |
| `<N>_sum_variable_per_hour.csv` | Sum per hour across all days |
