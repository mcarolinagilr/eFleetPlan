

import pyomo.environ as pyo
from pyomo.opt import SolverFactory 
import pandas as pd
import numpy as np
import xlsxwriter as xl
import matplotlib.pyplot as plt
import os
from glob import glob
from matplotlib import rcParams

from datetime import datetime
from pyomo.opt.results import SolverStatus

def process_folder(folder_path, filename_pattern):
    # Find the file matching the pattern
    files = [f for f in os.listdir(folder_path) if f.endswith(filename_pattern.split('*')[-1])]
    if not files:
        print(f"No file matching {filename_pattern} found in {folder_path}.")
        return

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        # Read the file into a DataFrame (adjust separator if needed)
        data = pd.read_csv(file_path)

        # Calculate max, average, and sum per hour
        max_per_hour = data.groupby('Hour').max()
        avg_per_hour = data.groupby('Hour').mean()
        sum_per_hour = data.groupby('Hour').sum()

        # Extract the initial numbers from the filename
        initial_numbers = filename.split('_')[0]

        # Save results back to the folder with the initial numbers in the filenames
        max_file_path = os.path.join(folder_path, f'{initial_numbers}_max_variable_per_hour.csv')
        avg_file_path = os.path.join(folder_path, f'{initial_numbers}_avg_variable_per_hour.csv')
        sum_file_path = os.path.join(folder_path, f'{initial_numbers}_sum_variable_per_hour.csv')

        max_per_hour.to_csv(max_file_path, index=True)
        avg_per_hour.to_csv(avg_file_path, index=True)
        sum_per_hour.to_csv(sum_file_path, index=True)

        print(f"Processed {filename} in {folder_path}.")

def plot_summary_table(file_path):
    # Load the data
    df = pd.read_csv(file_path)

    # Preserve original order of 'Category'
    category_order = df['Category'].drop_duplicates().tolist()
    df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)

    # Pivot table while preserving order
    table_df = df.pivot_table(index='Category', columns='Description', values='Value', sort=False)

    # Round values for better display
    table_df = table_df.round(2)

    # Font setup
    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 12

    # Plot table
    fig, ax = plt.subplots(figsize=(8, len(table_df) * 0.5 ))
    ax.axis('off')

    table = ax.table(
        cellText=table_df.values,
        rowLabels=table_df.index,
        colLabels=table_df.columns,
        loc='center',
        cellLoc='center',
        rowLoc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.5)

    plt.title('Infrastructure and Electricity Cost Summary (in SEK)', fontsize=14, pad=20)
    plt.tight_layout()
    plt.show()
    
    
def graph_vehicles(file_path, n_days, n_vehicles):
    df = pd.read_csv(file_path)

    # Font setup
    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 12

    # Create a subplot for each vehicle
    fig, axs = plt.subplots(nrows=n_vehicles, ncols=1, figsize=(18, 3 * n_vehicles + 2), sharex=True)
    fig.subplots_adjust(hspace=0.6)

    # Ensure axs is always an array for consistent indexing
    if n_vehicles == 1:
        axs = [axs]

    # Define vertical line positions for day separators
    day_positions = [i * 24 for i in range(0, n_days)]
    hour_ticks = list(range(0, n_days * 24, 2))
    hour_labels = [f'{h % 24:02d}h' for h in hour_ticks]

    # Loop through each vehicle
    for i, vehicle_id in enumerate(range(1, n_vehicles + 1)):
        vehicle_data = df[(df['Vehicle ID'] == vehicle_id) & (df['Days'] >= 0) & (df['Days'] <= n_days)].copy()
        vehicle_data = vehicle_data.sort_values(by=['Days', 'Hour'])
        vehicle_data['TimeIndex'] = range(len(vehicle_data))

        ax = axs[i]

        # Plot charging/discharging power
        ax.plot(vehicle_data['TimeIndex'], vehicle_data['Charging Power'], label='Charging Power', linewidth=1.5, color='orange')
        ax.plot(vehicle_data['TimeIndex'], vehicle_data['Discharging Power'], label='Discharging Power', linewidth=1.5)

        # Day separator lines
        for pos in day_positions:
            ax.axvline(x=pos, linestyle='dashed', color='gray', linewidth=0.6)

        # Style
        ax.set_ylabel(f'V{vehicle_id}\nPower (kWh)', fontsize=11)
        ax.grid(True, axis='y', linestyle='dashed', linewidth=0.5, color='black')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.margins(x=0.01)
        # Add secondary axis for Storage Level
        ax2 = ax.twinx()
        ax2.plot(vehicle_data['TimeIndex'], vehicle_data['Storage Level'], label='SOC', linewidth=1.5, color='green', linestyle='dashed')
        ax2.set_ylabel('Storage Level (kWh)', fontsize=11)
        ax2.spines['top'].set_visible(False)
        ax2.grid(False)
        ax2.set_ylim(0, 100)

        # Show x-tick labels on all subplots
        ax.set_xticks(hour_ticks)
        ax.set_xticklabels(hour_labels[:len(hour_ticks)], rotation=90, fontsize=9)
        ax.tick_params(axis='x', labelbottom=True)

        # Add legend only to the first plot
        if i == 0:
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc='upper right', bbox_to_anchor=(1, 1.5), ncol=2, frameon=True, fontsize=11)

    # Top axis (Day labels) on first subplot
    ax_top = axs[0].twiny()
    ax_top.set_xlim(axs[0].get_xlim())
    day_tick_positions = [i * 24 for i in range(n_days)]
    day_labels = [f'Day {i+1}' for i in range(n_days)]
    ax_top.set_xticks(day_tick_positions)
    ax_top.set_xticklabels(day_labels)
    ax_top.tick_params(axis='x', pad=10)
    ax_top.grid(True, axis='x', linestyle='dashed', linewidth=0.5, color='black')

    # Title and save
    fig.suptitle('Charging and Discharging Power and SOC per Vehicle (Week 1)', fontsize=16, y=0.99)
    plt.tight_layout()

    plt.savefig(file_path, format='jpeg', bbox_inches='tight')
    plt.show()
    
    
def graph_number_of_chargers_by_schedules(folder_path, files_hourly_max):
    """    Graphs the total number of chargers by type of charging for each schedule profile. """  
    
    # Initialize lists to store the maximum values
    max_slow_charging = []
    max_fast_charging = []
    max_route_charging = []
    file_names = []

    # Process each file
    for file in files_hourly_max:
        
        # Extract the schedule number and map it to the name
        schedule_number = int(os.path.basename(file).split('_')[0])  # Extract "Schedule_X" and convert to integer
        print(schedule_number)
        #schedule_name = schedule_name_mapping.get(schedule_number, schedule_number)  # Default to schedule_number if not in mapping
        
        # Read the CSV file into a DataFrame
        df_hourly_max = pd.read_csv(file)
        
        # Calculate the maximum values for each type
        slow_charging = df_hourly_max['EVs slow charging'].max()
        fast_charging = (
            df_hourly_max['EVs fast charging 50kW'].max() +
            df_hourly_max['EVs fast charging 150kW'].max() +
            df_hourly_max['EVs fast charging 350kW'].max()
        )
        route_charging = df_hourly_max['EVs route charging'].max()
        
        # Append the results to the lists
        max_slow_charging.append(slow_charging)
        max_fast_charging.append(fast_charging)
        max_route_charging.append(route_charging)
        file_names.append(schedule_number)  # Original file name
        #mapped_names.append(schedule_name)  # Mapped name

    # Create a DataFrame for plotting using mapped names
    df_max_values = pd.DataFrame({
        'File': file_names,
        'Slow Charging': max_slow_charging,
        'Fast Charging': max_fast_charging,
        'Route Charging': max_route_charging
    })

    # Plot the maximum values as a bar chart
    ax = df_max_values.plot(
        x='File', 
        y=['Slow Charging','Fast Charging','Route Charging'], 
        kind='bar', 
        figsize=(10, 6),
        width=0.7,
        color=[ '#4A7C59','#4682B4', 'Chocolate']
    )

    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 16

    # Your plot
    #ax.set_title('Total number of chargers by Type of Charging', fontsize=24, pad=30)
    ax.set_xlabel('Schedule profiles', fontsize=20)
    ax.set_yticks(range(0, int(df_max_values[['Slow Charging', 'Fast Charging', 'Route Charging']].values.max()) + 1, 1))
    ax.set_ylabel('Number of chargers', fontsize=20)

    # Set x-axis tick labels explicitly
    ax.set_xticks(range(len(df_max_values['File'])))


    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, framealpha=0, prop={'size': 16})
    ax.yaxis.set_major_locator(plt.MultipleLocator(2))  # Set y-axis grid/ticks every 2 units
    ax.grid(True, which='both', axis='y', linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    # Save the plot as a JPG file
    plt.savefig(f'{folder_path}/Total_chargers_by_schedules.jpg', format='jpeg')
    plt.show()


def graph_chargingpower (file_path, folder_path):

    df_mean = pd.read_csv(file_path)

 
    # Define bar positions
    bar_width = 0.25

    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Assume df_mean has an 'Hour' column from 0 to 23 or index 0 to 23
    if 'Hour' in df_mean.columns:
        x = df_mean['Hour']
    else:
        x = np.arange(len(df_mean))
    ax1.bar(x, df_mean['Charging power'], width=bar_width, alpha=0.7, label='Charging Power')
    ax1.set_xlabel('Hour', fontsize=20)
    ax1.set_ylabel('Power (kWh)', fontsize=20, color='black')
    ax1.tick_params(axis='x', labelsize=14, color='black')
    ax1.tick_params(axis='y', labelsize=14, color='black')
    ax1.set_xticks(np.arange(0, 24, 1))
    ax1.set_xticklabels([str(h) for h in range(24)])
    ax1.spines['top'].set_visible(False)
    ax1.margins(x=0.01)

    # Add secondary y-axis for average price per hour
    average_price_per_hour = df_mean['Price']
    ax2 = ax1.twinx()
    ax2.plot(average_price_per_hour, color='black', linewidth=2, alpha=0.6, label='Average Price per Hour', 
                            solid_joinstyle='round', solid_capstyle='round')
    ax2.set_ylabel('Average Price (SEK)', fontsize=20, color='black')
    ax2.tick_params(axis='y', labelcolor='black', labelsize=14)
    #ax1.set_ylim(0,300)
    #ax2.set_ylim(0, 140)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    #ax2.set_yticks(range(0, 900, 100))  # Adjust range as needed
    ax2.spines['top'].set_visible(False)  # Remove the top axis line for ax1
    ax2.margins(x=0.01)

    # Title and Legend
    plt.title('Average charging power per hour', fontsize=20, loc='center', pad=30)

    # Adjust legend placement to avoid overlap
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0), ncol=3, framealpha=0, fontsize=16)

    # Save the figure
    plt.savefig(f'{folder_path}/EVChargers_chargingpower.jpg', 
                                    format='jpeg', bbox_inches='tight')
    plt.show()


def graph_powerbytype (file_path, folder_path):
    df_mean = pd.read_csv(file_path)
 
    # Define bar positions
    bar_width = 0.25

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Prepare the three bar values
    slow_charging = df_mean['Slow Charging Hourly']
    fast_charging = (df_mean['Fast Charging Hourly 50kW'] + df_mean['Fast Charging Hourly 150kW'] + df_mean['Fast Charging Hourly 350kW'])
    route_charging = df_mean['Route Charging Hourly']
    
    # Define x as the array of hour indices
    if 'Hour' in df_mean.columns:
        x = df_mean['Hour']
    else:
        x = np.arange(len(df_mean))
    # Bar positions for grouped bars
    bar1 = x - bar_width
    bar2 = x
    bar3 = x + bar_width
    
    ax1.bar(bar1, slow_charging, width=bar_width, alpha=0.7, label='Slow Charging Hourly', color='#4A7C59')
    ax1.bar(bar2, fast_charging, width=bar_width, alpha=0.7, label='Fast Charging Hourly', color='#4682B4')
    ax1.bar(bar3, route_charging, width=bar_width, alpha=0.7, label='Route Charging Hourly', color='Chocolate')
    ax1.set_xlabel('Hour', fontsize=20)
    ax1.set_ylabel('Power (kWh)', fontsize=20, color='black')
    ax1.tick_params(axis='x', labelsize=14, color='black')
    ax1.tick_params(axis='y', labelsize=14, color='black')
    ax1.set_xticks(np.arange(0, 24, 1))
    ax1.set_xticklabels([str(h) for h in range(24)])
    ax1.spines['top'].set_visible(False)
    ax1.margins(x=0.01)

    # Add secondary y-axis for average price per hour
    average_price_per_hour = df_mean['Price']
    ax2 = ax1.twinx()
    ax2.plot(average_price_per_hour, color='black', linewidth=2, alpha=0.6, label='Average Price per Hour', 
                            solid_joinstyle='round', solid_capstyle='round')
    ax2.set_ylabel('Average Price (SEK)', fontsize=20, color='black')
    ax2.tick_params(axis='y', labelcolor='black', labelsize=14)
    #ax1.set_ylim(0,300)
    #ax2.set_ylim(0, 140)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    #ax2.set_yticks(range(0, 900, 100))  # Adjust range as needed
    ax2.spines['top'].set_visible(False)  # Remove the top axis line for ax1
    ax2.margins(x=0.01)

    # Title and Legend
    plt.title('Average charging power per hour by type of charger', fontsize=20, loc='center', pad=30)

    # Adjust legend placement to avoid overlap
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0), ncol=3, framealpha=0, fontsize=16)

    # Save the figure
    plt.savefig(f'{folder_path}/EVChargers_chargingpowerbytype.jpg', 
                                    format='jpeg', bbox_inches='tight')
    plt.show()