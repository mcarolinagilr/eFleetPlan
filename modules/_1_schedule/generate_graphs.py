import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def generate_graphs(distance_file_path, charging_file_path, consumption_file_path, folder, output_folder):
   
    # Process charging station data
    plt.rcParams['font.family'] = 'Times New Roman'
    df = pd.read_csv(charging_file_path)
    df['date'] = pd.to_datetime(df['date'])
    df['vehicles_at_depot'] = df.iloc[:, 1:].apply(lambda row: (row == 1).sum(), axis=1)
    df.set_index('date', inplace=True)
    df['hour'] = df.index.hour
    hourly_avg = df.groupby('hour')['vehicles_at_depot'].mean()
    
    # Plot hourly average of vehicles at depot
    plt.figure(figsize=(5, 3))
    plt.bar(hourly_avg.index, hourly_avg, label='Hourly Average of Vehicles at Depot', color='#4682B4')
    plt.xlabel('Hour of Day', fontsize=14)
    plt.ylabel('Number of Vehicles', fontsize=14)
    plt.xticks(ticks=range(0, 24, 1), fontsize=12)
    plt.yticks(fontsize=12)
    plt.ylim(0, df['vehicles_at_depot'].max())
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.title('Hourly Average of Vehicles at Depot', fontsize=16)
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f'hourly_avg_vehicles_at_depot_{folder}.jpeg'), format='jpeg')
    plt.show()
    
    # Process energy consumption data
    energy_consumption = pd.read_csv(consumption_file_path)
    energy_consumption['date'] = pd.to_datetime(energy_consumption['date'])
    energy_consumption['hour'] = energy_consumption['date'].dt.hour
    energy_consumption['Total_Consumption_kWh'] = energy_consumption.filter(like='Consumption_kWh_Vehicle_').sum(axis=1)
    hourly_avg_consumption = energy_consumption.groupby('hour')['Total_Consumption_kWh'].mean()
    
    # Plot hourly energy consumption
    plt.figure(figsize=(5, 3))
    plt.bar(hourly_avg_consumption.index, hourly_avg_consumption.values, color='chocolate')
    plt.xticks(range(24), fontsize=12)
    #plt.ylim(0, 600)  # Limit y-axis
    plt.title('Hourly Average Energy Consumption', fontsize=16)
    plt.xlabel('Hour of the Day', fontsize=14)
    plt.ylabel('Energy Consumption (kWh)', fontsize=14)
    plt.xticks(ticks=range(0, 24, 1), fontsize=12)
    
    plt.yticks(fontsize=12)
    plt.grid(True, axis='y')
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f'hourly_avg_energy_consumption_{folder}.jpeg'), format='jpeg')
    plt.show()
    