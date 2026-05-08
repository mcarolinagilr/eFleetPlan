
from matplotlib.ticker import MultipleLocator
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from matplotlib import rcParams

from datetime import datetime
from pyomo.opt.results import SolverStatus

def identify_resolution(df):
    """this function is important to identify time resolution from a DataFrame.
        Returns (step_col, steps_per_day, delta_t).
    """
    if 'Step' in df.columns:
        step_col = 'Step'
        steps_per_day = df['Step'].nunique()
    elif 'Hour' in df.columns:
        step_col = 'Hour'
        steps_per_day = df['Hour'].nunique()
    else:
        step_col = None
        steps_per_day = 24
    delta_t = 24.0 / steps_per_day
    return step_col, steps_per_day, delta_t

def process_folder(folder_path, filename_pattern):
    """
    Process one or more '*_Main_variables_results.csv' files in a folder and
    create per-step max/avg/sum CSVs.

    Accepts either strings or pathlib.Path objects for both arguments.
    """
    folder_path = Path(folder_path)

    # Support either a glob pattern (recommended) or a simple suffix filter.
    pattern_str = str(filename_pattern)
    if any(ch in pattern_str for ch in ["*", "?", "["]):
        file_paths = sorted(folder_path.glob(Path(pattern_str).name))
    else:
        suffix = Path(pattern_str).name
        file_paths = sorted([p for p in folder_path.iterdir() if p.is_file() and p.name.endswith(suffix)])

    if not file_paths:
        print(f"No file matching {filename_pattern} found in {folder_path}.")
        return

    for file_path in file_paths:
        filename = file_path.name

        # Read the file into a DataFrame (adjust separator if needed)
        data = pd.read_csv(file_path)
        
        step_col, _, _ = identify_resolution(data)
        group_col = step_col if step_col else data.columns[0]

        # Calculate max, average, and sum per step
        max_per_step = data.groupby(group_col).max()
        avg_per_step = data.groupby(group_col).mean()
        sum_per_step = data.groupby(group_col).sum()

        # Extract the initial numbers from the filename
        initial_numbers = filename.split('_')[0]

        # Save results back to the folder with the initial numbers in the filenames
        max_file_path = folder_path / f"{initial_numbers}_max_variable_per_step.csv"
        avg_file_path = folder_path / f"{initial_numbers}_avg_variable_per_step.csv"
        sum_file_path = folder_path / f"{initial_numbers}_sum_variable_per_step.csv"

        max_per_step.to_csv(max_file_path, index=True)
        avg_per_step.to_csv(avg_file_path, index=True)
        sum_per_step.to_csv(sum_file_path, index=True)

        print(f"Processed {filename} in {folder_path}.")

def plot_summary_table(file_path):
    # Load the data
    df = pd.read_csv(file_path)

    # Preserve original order of 'Category'
    category_order = df['Category'].drop_duplicates().tolist()
    df['Category'] = pd.Categorical(df['Category'], categories=category_order, ordered=True)

    # Separate DT category
    df_dt = df[df['Category'] == 'DT']
    df_other = df[df['Category'] != 'DT']

    # Pivot tables
    table_df = df_other.pivot_table(index='Category', columns='Description', values='Value', sort=False)
    table_dt = df_dt.pivot_table(index='Category', columns='Description', values='Value', sort=False)

    # Round values for better display
    table_df = table_df.round(2)
    table_dt = table_dt.round(2)

    # Font setup
    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 12

    # Plot main table
    fig, ax = plt.subplots(figsize=(8, len(table_df) * 0.5 + 1))
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

    # Plot DT table if exists
    if not table_dt.empty:
        fig_dt, ax_dt = plt.subplots(figsize=(8, 1.5))
        ax_dt.axis('off')
        table_dt_plot = ax_dt.table(
            cellText=table_dt.values,
            rowLabels=table_dt.index,
            colLabels=table_dt.columns,
            loc='center',
            cellLoc='center',
            rowLoc='center'
        )
        table_dt_plot.auto_set_font_size(False)
        table_dt_plot.set_fontsize(11)
        table_dt_plot.scale(1, 1.5)
        plt.title('Distribution Terminal Summary', fontsize=14, pad=20)
        plt.tight_layout()
        plt.show()
    
    
def graph_vehicles(folder_path, file_path, n_days, n_vehicles):
    df = pd.read_csv(file_path, encoding='utf-8-sig')

    step_col, steps_per_day, delta_t = identify_resolution(df)

    # Font setup
    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 16

    # Create a subplot for each vehicle
    fig, axs = plt.subplots(nrows=n_vehicles, ncols=1, figsize=(16, 3 * n_vehicles + 2), sharex=True)
    fig.subplots_adjust(hspace=0.6)

    # Ensure axs is always an array for consistent indexing
    if n_vehicles == 1:
        axs = [axs]

    # Define vertical line positions for day separators
    day_positions = [i * steps_per_day for i in range(0, n_days)]
    
    # Tick every 2 hours worth of steps                                             
    steps_per_2h = int(round(2.0 / delta_t))                                       
    total_steps = n_days * steps_per_day                                            
    step_ticks = list(range(0, total_steps, steps_per_2h))                          
    step_labels = [f'{int((s % steps_per_day) * delta_t):02d}h' for s in step_ticks]  

    # Determine sort columns based on available columns
    step_col = step_col if step_col else 'Hour' 
    
    # Loop through each vehicle
    for i, vehicle_id in enumerate(range(1, n_vehicles + 1)):
        vehicle_data = df[(df['Vehicle ID'] == vehicle_id) & (df['Day'] >= 0) & (df['Day'] <= n_days)].copy()
        vehicle_data = vehicle_data.sort_values(by=['Day', step_col])
        vehicle_data['TimeIndex'] = range(len(vehicle_data))

        ax = axs[i]

        # Plot charging/discharging energy as bar charts
        ax.bar(vehicle_data['TimeIndex'], vehicle_data['Charging Energy'], label='Charging Energy', width=0.8, color='orange', alpha=0.7)
        ax.bar(vehicle_data['TimeIndex'], vehicle_data['Discharging Energy'], label='Discharging Energy', width=0.8, alpha=0.7)

        # Day separator lines
        for pos in day_positions:
            ax.axvline(x=pos, linestyle='dashed', color='gray', linewidth=0.6)

        # Style
        ax.set_ylabel(f'V{vehicle_id}\nCharging/discharging \nenergy per timestep (kWh)', fontsize=14)
        ax.grid(True, axis='y', linewidth=0.5, color='black')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.margins(x=0.01)
        ax.set_ylim(0, 10)
        # Add secondary axis for Storage Level
        ax2 = ax.twinx()
        ax2.plot(vehicle_data['TimeIndex'], vehicle_data['Storage Level'], label='SOC', linewidth=1.5, color='green', linestyle='dashed')
        ax2.set_ylabel('Battery Storage Level \nSOC (kWh)', fontsize=16)
        ax2.spines['top'].set_visible(False)
        ax2.grid(False)
        ax2.set_ylim(0, 40)

        # Show x-tick labels on all subplots
        ax.set_xticks(step_ticks)
        ax.set_xticklabels(step_labels[:len(step_ticks)], rotation=90, fontsize=12)
        ax.tick_params(axis='x', labelbottom=True)

        # Add legend only to the first plot
        if i == 2:
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, framealpha=0, fontsize=16)

    # Top axis (Day labels) on first subplot
    ax_top = axs[0].twiny()
    ax_top.set_xlim(axs[0].get_xlim())
    day_tick_positions = [i * steps_per_day for i in range(n_days)]
    day_labels = [f'Day {i+1}' for i in range(n_days)]
    ax_top.set_xticks(day_tick_positions)
    ax_top.set_xticklabels(day_labels)
    ax_top.tick_params(axis='x', pad=10)
    ax_top.grid(True, axis='x', linestyle='dashed', linewidth=0.5, color='black')

    # Title and save
    fig.suptitle('Charging and discharging energy and SOC per vehicle', fontsize=20, y=0.99)
    plt.tight_layout()

    plt.savefig(f'{folder_path}/charging_discharge_SOC.jpeg', format='jpeg', bbox_inches='tight')
    plt.show()
    
    
def graph_number_of_chargers_by_schedules(folder_path, files_pertime_max):
    """    Graphs the total number of chargers by type of charging for each schedule profile. """  
    
    # Initialize lists to store the maximum values
    max_f1_charging = []
    max_f2_charging = []
    max_f3_charging = []
    max_f4_charging = []
    max_route_charging = []
    file_names = []

    # Process each file
    for file in files_pertime_max:
        
        # Extract the schedule number and map it to the name
        schedule_number = int(os.path.basename(file).split('_')[0])  # Extract "Schedule_X" and convert to integer
        print(schedule_number)
        #schedule_name = schedule_name_mapping.get(schedule_number, schedule_number)  # Default to schedule_number if not in mapping
        
        # Read the CSV file into a DataFrame
        df_pertime_max = pd.read_csv(file)
        
        # Calculate the maximum values for each type
        f1_charging = df_pertime_max['EVs f1 charging'].max()
        f2_charging = df_pertime_max['EVs f2 charging'].max()
        f3_charging = df_pertime_max['EVs f3 charging'].max()
        f4_charging = df_pertime_max['EVs f4 charging'].max()
        route_charging = df_pertime_max['EVs route charging'].max()
        
        # Append the results to the lists
        max_f1_charging.append(f1_charging)
        max_f2_charging.append(f2_charging)
        max_f3_charging.append(f3_charging)
        max_f4_charging.append(f4_charging)
        max_route_charging.append(route_charging)
        file_names.append(schedule_number)  # Original file name
        #mapped_names.append(schedule_name)  # Mapped name

    # Create a DataFrame for plotting using mapped names
    df_max_values = pd.DataFrame({
        'File': file_names,
        'f1 Charging': max_f1_charging,
        'f2 Charging': max_f2_charging,
        'f3 Charging': max_f3_charging,
        'f4 Charging': max_f4_charging,
        'route Charging': max_route_charging
    })

    # Plot the maximum values as a bar chart
    ax = df_max_values.plot(
        x='File', 
        y=['f1 Charging','f2 Charging','f3 Charging','f4 Charging','route Charging'], 
        kind='bar', 
        figsize=(10, 6),
        width=0.7,
        color=[ "#7DE19B","#04643F", "#9D6402", "#FFD700", "#FF4500"]
    )

    rcParams['font.family'] = 'Times New Roman'
    rcParams['font.size'] = 16

    #ax.set_title('Total number of chargers by Type of Charging', fontsize=24, pad=30)
    ax.set_xlabel('Schedule profiles', fontsize=20)
    ax.set_xticks(range(len(df_max_values['File'])))
    ax.set_xticklabels(df_max_values['File'])
    
    max_val = int(df_max_values[['f1 Charging','f2 Charging','f3 Charging','f4 Charging','route Charging']].values.max())
    ax.set_ylabel('Number of chargers', fontsize=20)
    ax.set_ylim(0, max_val + 1)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, framealpha=0, prop={'size': 16})
    
    
    ax.grid(True, which='both', axis='y', linestyle='--')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    plt.savefig(f'{folder_path}/Total_chargers_by_schedules.jpg', format='jpeg')
    plt.show()

    fig=plt.gcf()

    return ax, fig


def graph_chargingenergy (file_path, folder_path):

    df_mean = pd.read_csv(file_path)

    step_col, steps_per_day, delta_t = identify_resolution(df_mean)
 
    # Define bar positions
    bar_width = 0.25

    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    
    if 'Step' in df_mean.columns:                                                    
        x = df_mean['Step']                                                          
    elif 'Hour' in df_mean.columns:                                                  
        x = df_mean['Hour']
    else:
        x = np.arange(len(df_mean))
        
    ax1.bar(x, df_mean['Charging energy'], width=bar_width, alpha=0.7, label='Charging Energy', color= "#04643F")
    ax1.set_xlabel('Time of day', fontsize=20)
    ax1.set_ylabel('Energy (kWh)', fontsize=20, color='black')
    ax1.tick_params(axis='x', labelsize=14, color='black')
    ax1.tick_params(axis='y', labelsize=14, color='black')
    
    if 'Step' in df_mean.columns:
        steps_per_1h = int(round(1.0 / delta_t))
        tick_positions = np.arange(0, steps_per_day, steps_per_1h)
        tick_labels = [f'{int(s * delta_t)}' for s in tick_positions]
        ax1.set_xticks(tick_positions) 
        ax1.set_xticklabels(tick_labels)
    else:
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
    max_val = int(df_mean['Charging energy'].max())
    ax1.set_ylim(0, max_val + 1)
    max_price = average_price_per_hour.max()
    ax2.set_ylim(0, max_price + 1)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    
    ax2.spines['top'].set_visible(False)  
    ax2.margins(x=0.01)

    # Title and Legend
    plt.title('Average charging energy per time step', fontsize=20, loc='center', pad=30)

    # Adjust legend placement to avoid overlap
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0), ncol=3, framealpha=0, fontsize=16)

    # Save the figure
    plt.savefig(f'{folder_path}/NumberEVChargers_perchargingenergy.jpg', 
                                    format='jpeg', bbox_inches='tight')
    plt.show()


def graph_energybytype (file_path, folder_path):
    df_mean = pd.read_csv(file_path)
    
    step_col, steps_per_day, delta_t = identify_resolution(df_mean)
 
    bar_width = 0.25

    fig, ax1 = plt.subplots(figsize=(12, 6))

    slow_charging = df_mean['f1 Charging pertime']
    fast_charging = (df_mean['f2 Charging pertime'] + df_mean['f3 Charging pertime'] + df_mean['f4 Charging pertime'])
    route_charging = df_mean['route Charging pertime']
    
    if step_col == 'Step':
        x = df_mean['Step'].values
    elif 'Hour' in df_mean.columns:
        x = df_mean['Hour'].values
    else:
        x = np.arange(len(df_mean))
        
    # Bar positions for grouped bars
    bar1 = x - bar_width
    bar2 = x
    bar3 = x + bar_width
    
    ax1.bar(bar1, slow_charging, width=bar_width, alpha=0.7, label='f1 Charging pertime', color= "#7DE19B")
    ax1.bar(bar2, fast_charging, width=bar_width, alpha=0.7, label='f2-f4 Charging pertime', color="#04643F")
    ax1.bar(bar3, route_charging, width=bar_width, alpha=0.7, label='Route charging pertime', color="#9D6402")
    ax1.set_xlabel('Time of day', fontsize=20)
    ax1.set_ylabel('Energy (kWh)', fontsize=20, color='black')
    ax1.tick_params(axis='x', labelsize=14, color='black')
    ax1.tick_params(axis='y', labelsize=14, color='black')
    
    if 'Step' in df_mean.columns:
        steps_per_1h = int(round(1.0 / delta_t))
        tick_positions = np.arange(0, steps_per_day, steps_per_1h)
        tick_labels = [f'{int(s * delta_t)}' for s in tick_positions]
        ax1.set_xticks(tick_positions) 
        ax1.set_xticklabels(tick_labels)
    else:
        ax1.set_xticks(np.arange(0, 24, 1))
        ax1.set_xticklabels([str(h) for h in range(24)])
        
        
    ax1.spines['top'].set_visible(False)
    ax1.margins(x=0.01)

    # Add secondary y-axis for average price per timestep
    average_price_per_hour = df_mean['Price']
    ax2 = ax1.twinx()
    ax2.plot(average_price_per_hour, color='black', linewidth=2, alpha=0.6, label='Average Price per timestep', 
                            solid_joinstyle='round', solid_capstyle='round')
    ax2.set_ylabel('Average Price (SEK)', fontsize=20, color='black')
    ax2.tick_params(axis='y', labelcolor='black', labelsize=14)
    max_val= int(df_mean[['f1 Charging pertime','f2 Charging pertime','f3 Charging pertime','f4 Charging pertime','route Charging pertime']].values.max())
    ax1.set_ylim(0, max_val + 1)
    max_price = average_price_per_hour.max()
    ax2.set_ylim(0, max_price + 1)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    #ax2.set_yticks(range(0, 900, 100))  # Adjust range as needed
    ax2.spines['top'].set_visible(False)  # Remove the top axis line for ax1
    ax2.margins(x=0.01)

    # Title and Legend
    plt.title('Average charging energy per timestep by type of charger', fontsize=20, loc='center', pad=30)

    # Adjust legend placement to avoid overlap
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0), ncol=3, framealpha=0, fontsize=16)

    # Save the figure
    plt.savefig(f'{folder_path}/EVChargers_chargingenergybytype.jpg', 
                                    format='jpeg', bbox_inches='tight')
    plt.show()

    return ax1, ax2