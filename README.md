# eFleetPlan
Co-optimisation tool of charging infrastructure investment and electric fleet operations

**EFleetPlan** is a Python-based optimisation tool designed for the optimisation of charging infrastructure investment and operation for electric light commercial vehicles (LCV)

## Installation
**Option 1** (With package folder download)

**Step 1.** Create a new environment with the requirements described in "requirements.txt" file.
For example, in Python (Windows), write in the terminal:

    Python -m venv OPTI_env
    OPTI_env\Scripts\activate
    pip install -r requirements.txt

For example, in Python (macOS / Linux) write in the terminal:

    Python -m venv OPTI_env
    source OPTI_env/bin/activate
    pip install -r requirements.txt

**Step 2.** Install the package locally in the environment:
Run the following code in the terminal, after the activation of the environment: pip install .


**Option 2** (download directly from github in the command prompt)

**Step 1.** Clone the repository:

    cd "[folder path where to save the program folder]"
    git clone "https://github.com/mcarolinagilr/eFleetPlan"
    cd eFleetPlan
    
**Then run Step 1 and step 2 from previous option**
    
    Python -m venv OPTI_env
    source OPTI_env/bin/activate
    pip install -r requirements.txt
    pip install .


## How to use the tool
You can use the entire tool by running the Optimal charging tool notebook (notebooks/**0_OPTIMAL INVESTMENT AND OPERATION TOOL.ipynb**), or you can run the models individually:
- notebooks/Module 1. Schedule Generation Module.ipynb for Module 1, to create schedules for an electric LCV fleet
- notebooks/Module 2. Co-optimisation.ipynb for Module 2, to run the optimisation model

## Configurations
The software configuration is structured around four sections that manage the generation of schedules and the operation of the optimisation function:

1.1 Schedule generator configurations: Define the parameters required to generate the travel and charging patterns for each vehicle in the LCV fleet.

1.2. Fleet parameters configurations: Define the characteristics of the fleet used for schedule generation.

2.1 Optimisation parameters configurations: Define the settings for the cost minimisation model/ optimisation model.

2.2. Cost Configurations: Defines the economic structure behind the optimisation model.

To configure the case studies, it is important to replace the files in the data/input folder: **Energy consumption file** and **Electricity price file**. 

## Citation
If you use eFleetPlan, please cite:
**Gil Ribeiro, C and Thakur, J, eFleetPlan: Co-Optimisation tool of Charging Infrastructure Investment and Fleet Operations, 2025. DOI: 10.5281/zenodo.16448878**
