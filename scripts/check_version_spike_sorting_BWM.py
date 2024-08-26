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
    # included: if it is included in our current analysis?

"""
#%% 
from one.api import ONE
from brainwidemap import bwm_query, bwm_loading
from brainbox.io.one import EphysSessionLoader, SpikeSortingLoader, SessionLoader
# from ibllib.atlas import AllenAtlas
import pandas as pd
import os

one = ONE(base_url='https://alyx.internationalbrainlab.org')

loaded_time = one.refresh_cache('refresh')  # Explicitly refresh the cache, do it only once on Monday june 10th then it is not necessary anymore
bwm_df = bwm_query(freeze='2023_12_bwm_release', one=one, return_details=True)

for index, rec in bwm_df.iterrows():

    # print(index)
    pid = rec['pid']
    sl = SpikeSortingLoader(pid=pid, one=one)
    #check the version number of current spikesorting
    info = one.alyx.rest('datasets', 'list', session=sl.eid, name='spikes.times.npy', collection=sl.collection)[0]

    #add info to bwm_df
    bwm_df.loc[index,'session']=info['session']
    bwm_df.loc[index,'revision']=info['revision']
    bwm_df.loc[index,'version']=info['version'] #2.35.2; 
    bwm_df.loc[index,'auto_datetime']=info['auto_datetime'] #2.35.2; 

#%% print all unique values of 'version':
print(bwm_df.version.unique())
""" 
    ['1.5.36' 'pykilosort_ibl_1.2.0' '2.35.0' 'pykilosort_ibl_1.2.1' '1.10.2'
    'e8c9d765764778b7ee5bda08c982037f8f07e690' 'patched_pykilosort_ibl_1.3.3'
    '2.17.1' 'patched_pykilosort_ibl_1.4.1' '2.32.4'
    'patched_pykilosort_ibl_1.4.5' 'patched_pykilosort_1.4.4'
    'patched_pykilosort_1.4.6' 'c65e3ada92de4d0d8f880ba4039de3d5650f6036'
    'pykilosort_ibl_1.3.0' '4991ceba3cd423df027bc0d77e2314e9d7909e04'
    'patched_pykilosort_1.4.3' 'patched_pykilosort_ibl_1.4.0'
    'patched_pykilosort_ibl_1.4.2' '2.6.0' '1.5.24'
    'd8e9e95d5348f2428b50ffefda34cd93a37a531c' 'pykilosort_ibl_1.4.5'
    '1.5.37' '1.5.39' 'pykilosort_ibl_1.4.2' '1.4.14']
"""
#%% load pids we use in the analysis (this can be skipped if you're not interested in any further filtering)
pid_eid_included_info = pd.read_parquet(os.path.join(datapath,'pid_eid_age_info.pqt'))
pids_filtered = pid_eid_included_info['pid'].values
bwm_df['included']=bwm_df['pid'].map(lambda x: True if x in pids_filtered else False)

#%%save the results
datapath = '../data'
bwm_df.to_csv(os.path.join(datapath, "check_BWM_SpikeSorting_version.csv"),index=False)  # 254 (out of 699) probes have '2.35.0' (revision 2024-05-06)
# bwm_df.to_excel(os.path.join(datapath, "check_BWM_SpikeSorting_version.xlsx"))  # 254 (out of 699) probes have '2.35.0' (revision 2024-05-06)