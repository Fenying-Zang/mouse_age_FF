## Age-Related Changes in Neural Noise in a Decision-Making Task
Fenying Zang, Leiden University, 2023

### Requirements
-  install the iblenv: <https://github.com/int-brain-lab/iblenv>

### Instructions
~~~
conda activate iblenv
~~~

1. prepare data used to generate figures:
~~~
#Young mice:
F2_PrepareData_NeuralYield_young.py 
F3_F4_PrepareData_young_mice.py

#Old mice: the raw data is not yet published, analysis results can be found in those csv files:
# NeuralYield_filtering_old.csv
# FF_all_regions_old_alltrials.csv
# FR_all_regions_old_alltrials.csv
~~~
2. generate figures:
~~~
F2_plot_NeuralYield_young_old.py
F3_plot_singleFFs_distribution_young_old.py
F4_plot_FR_FF_timecourse_young_old.py
~~~
