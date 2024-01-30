#%%
from one.api import ONE
from ibllib.atlas import AllenAtlas
from brainbox.io.one import SpikeSortingLoader
import pandas as pd

one = ONE()
ba = AllenAtlas()
###########################################################################################################################################
#%% get unique eids of the lifespan project:
all_lifespan_insertions = pd.DataFrame.from_dict(one.alyx.rest('trajectories', 'list',  django='probe_insertion__session__project__name__endswith,lifespan'))
list_eids=[]
for index, i in all_lifespan_insertions.iterrows():
    eid = i['session']['id']
    if eid not in list_eids:
        list_eids.append(eid)
print(len(list_eids)) #58

#%% check the task information
# here: only errored tasks
# ses = one.alyx.rest('tasks', 'list', status='Errored', name='SpikeSorting', django=f"session__in,{list_eids}") #return: 5 tasks with pykilosort 1.5.0
# %% check the task information of all those 58 sessions：status，version, log info 
ses_all = one.alyx.rest('tasks', 'list',  name='SpikeSorting', django=f"session__in,{list_eids}") #without specifying status='Errored'
pd_ses_all=pd.DataFrame.from_dict(ses_all)
# %% only export some key colomns --> a simple version
pd_ses_all_simple=pd_ses_all[['session','status','version','log','datetime']]
#%% SAVE final df into .xlsx file
resultPath = '../data/IBL_lifespan_spikesorting_task_info2.xlsx'
pd_ses_all.to_excel(resultPath, index = False, engine='xlsxwriter')

resultPath_simple = '../data/IBL_lifespan_spikesorting_task_info_simple2.xlsx'
pd_ses_all_simple.to_excel(resultPath_simple, index = False, engine='xlsxwriter')
# %%
