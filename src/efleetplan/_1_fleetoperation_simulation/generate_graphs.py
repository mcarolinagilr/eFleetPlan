import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def generate_graphs(schedule_csv: str, folder: str, output_folder: str):
    """
    Generate summary graphs from a single unified schedule CSV.

    Expected columns: date, Distance_km, Consumption_kWh, ChargingStation, VehicleID
    """

    plt.rcParams['font.family'] = 'Times New Roman'
    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv(schedule_csv, parse_dates=['date'])
    df['hour'] = df['date'].dt.hour

    # ------------------------------------------------------------------
    # Graph 1: Average vehicles at depot per hour
    # ------------------------------------------------------------------
    # Count vehicles with ChargingStation == 1 per timestep

    vehicles_at_depot = (
        df.groupby('date')['ChargingStation']
        .sum()
        .reset_index(name='vehicles_at_depot')
    )
    vehicles_at_depot['hour'] = pd.to_datetime(vehicles_at_depot['date']).dt.hour
    pertime_avg = vehicles_at_depot.groupby('hour')['vehicles_at_depot'].mean()

    n_vehicles = df['VehicleID'].nunique()

    plt.figure(figsize=(10, 6))
    plt.bar(pertime_avg.index, pertime_avg.values, color="#04643F")
    plt.xlabel('Hour of Day', fontsize=18)
    plt.ylabel('Number of Vehicles', fontsize=18)
    plt.xticks(ticks=range(0, 24, 1), fontsize=16)
    plt.yticks(fontsize=16)
    plt.ylim(0, max(n_vehicles, pertime_avg.max()) * 1.1)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(
        os.path.join(output_folder, f'pertime_avg_vehicles_at_depot_{folder}.jpeg'),
        format='jpeg', dpi=600,
    )
    plt.show()

    # ------------------------------------------------------------------
    # Graph 2: Average total energy consumption per hour
    # ------------------------------------------------------------------
    # Sum consumption across all vehicles per timestep, then average by hour
    
    consumption_per_timestep = (
        df.groupby('date')['Consumption_kWh']
        .sum()
        .reset_index(name='Total_Consumption_kWh')
    )
    consumption_per_timestep['hour'] = pd.to_datetime(consumption_per_timestep['date']).dt.hour
    pertime_avg_consumption = consumption_per_timestep.groupby('hour')['Total_Consumption_kWh'].mean()

    plt.figure(figsize=(10, 6))
    plt.bar(pertime_avg_consumption.index, pertime_avg_consumption.values, color="#FFC155")
    plt.xlabel('Hour of the Day', fontsize=18)
    plt.ylabel('Energy Consumption (kWh)', fontsize=18)
    plt.xticks(ticks=range(0, 24, 1), fontsize=16)
    plt.yticks(fontsize=16)
    plt.grid(True, axis='y')
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(
        os.path.join(output_folder, f'pertime_avg_energy_consumption_{folder}.jpeg'),
        format='jpeg', dpi=600,
    )
    plt.show()