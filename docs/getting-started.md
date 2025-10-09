# Getting started

## Installation

There are different options to install or download the eFleetPlan. 

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



