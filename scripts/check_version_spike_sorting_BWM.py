"""
@author: F. Zang, based on working example from Olivier Winter

checklist:
# the paper-brain-wide-map repository should be set on the develop branch
# the ibllib repositor should be on the develop branch
# you are working off the internal alyx database

the output dataframe includes:
    # default info from bwm_query
    # session: link to the data
    # revision
    # version: the version number of spike sorting
    # auto_datetime
    # [optional] included: if it is included in our current analysis?

"""
#%% 
from one.api import ONE
from brainwidemap import bwm_query, bwm_loading
from brainbox.io.one import EphysSessionLoader, SpikeSortingLoader, SessionLoader
# from ibllib.atlas import AllenAtlas
import pandas as pd
import os

one = ONE(base_url='https://alyx.internationalbrainlab.org')
# one.alyx.clear_rest_cache()
# loaded_time = one.refresh_cache('refresh')  # Explicitly refresh the cache, do it only once on Monday june 10th then it is not necessary anymore
bwm_df = bwm_query(freeze='2023_12_bwm_release', one=one, return_details=True)

#%%
bwm_df_temp = bwm_df.head()
for index, rec in bwm_df_temp.iterrows():
    # if rec.included:
    print(index)
    pid = rec['pid']
    sl = SpikeSortingLoader(pid=pid, one=one)
    # spikes, clusters, channels = sl.load_spike_sorting(revision="2024-05-06")
    
    #check the version number of current spikesorting
    info = one.alyx.rest('datasets', 'list', session=sl.eid, name='spikes.times.npy', collection=sl.collection, revision="2024-05-06")[0]
    print(info['version'])
    #add info to bwm_df
    bwm_df.loc[index,'session']=info['session']
    bwm_df.loc[index,'revision']=info['revision']
    bwm_df.loc[index,'version']=info['version'] #2.35.2; 
    bwm_df.loc[index,'auto_datetime']=info['auto_datetime'] #2.35.2; 

#%% print all unique values of 'version':
print(bwm_df.version.unique())

"""
['2.35.2' '2.35.0']

"""
#%%  [optional] load pids we use in the analysis [optional]
# datapath = '../scripts/data'
# pid_eid_included_info = pd.read_parquet('pid_eid_age_info.pqt')
# pids_filtered = pid_eid_included_info['pid'].values
# bwm_df['included']=bwm_df['pid'].map(lambda x: True if x in pids_filtered else False)

#%%save the results
datapath = '../scripts/data'
bwm_df.to_csv(os.path.join(datapath, "check_BWM_SpikeSorting_version_newrevision.csv"),index=False)  
