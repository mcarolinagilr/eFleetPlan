# eFleetPlan
Co-optimisation tool of charging infrastructure investment and electric fleet operations

**EFleetPlan** is a Python-based tool for optimizing charging infrastructure and operations for electric light commercial vehicles (LCVs).

## Authors
Carolina Gil Ribeiro and Jagruti Thakur

## License
This software is licensed under the Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International License (CC BY-NC-SA 4.0).  
See the [LICENSE](./LICENSE) file or visit [https://creativecommons.org/licenses/by-nc-sa/4.0/](https://creativecommons.org/licenses/by-nc-sa/4.0/) for details.


## Citation
If you use eFleetPlan, please cite:
**Gil Ribeiro, C and Thakur, J, eFleetPlan: Co-Optimisation tool of Charging Infrastructure Investment and Fleet Operations, 2025. DOI:xxxxxxx


## Installation instructions
**Option 1** With package folder download

**Step 1.** Create a new environment using "requirements.txt" file.
For Python (Windows), run in the terminal:

    Python -m venv OPTI_env
    OPTI_env\Scripts\activate
    pip install -r requirements.txt

For  Python (macOS / Linux) run in the terminal:

    Python -m venv OPTI_env
    source OPTI_env/bin/activate
    pip install -r requirements.txt

**Step 2.** Install the package locally:
After activating the environment, run:
 pip install .


**Option 2** (Clone directly from GitHub in the command prompt)

**Step 1.** Clone the repository:
    cd "[folder path where to save the program folder]"
    git clone "https://github.com/mcarolinagilr/eFleetPlan"
    cd eFleetPlan
    
**Then, repeat Step 1 and Step 2 from the previous option:**
    
    Python -m venv OPTI_env
    source OPTI_env/bin/activate
    pip install -r requirements.txt
    pip install .

## Gurobi solver instalation
eFleetPlan requires the [Gurobi Optimizer](https://www.gurobi.com/) to solve mathematical optimization problems.
To use the optimisation feature, you need a valid Gurobi license and installation.



## How to use the tool
To use the full tool, run the Optimal Charging Tool notebook: 
(notebooks/**0_OPTIMAL INVESTMENT AND OPERATION TOOL.ipynb**)
You can run the models individually:
- notebooks/Module 1. Schedule Generation Module.ipynb for Module 1, to create schedules for an electric LCV fleet
- notebooks/Module 2. Co-optimisation.ipynb for Module 2, to run the optimisation model

## Configurations
The software configuration has five sections for schedule generation and optimization:

1.1 Schedule generator configurations: Define the parameters required to generate the travel and charging patterns for each vehicle in the LCV fleet.

1.2. Fleet parameters configurations: Define the characteristics of the fleet used for schedule generation.

2.1 Optimisation parameters configurations: Define the settings for the cost minimisation model/ optimisation model.

2.2. Cost Configurations: Defines the economic structure behind the optimisation model.

2.3. Battery and power configurations: Battery capacity limitations and powers to consider in the optimisation model.

To configure the case studies, it is important to replace the files in the data/input folder: **Energy consumption file** and **Electricity price file**. 






