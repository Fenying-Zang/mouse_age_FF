"""
please specify the datapath if you want to save the results

the output dataframe includes:
    # pid 
    # eid 
    # not critical?
    # pass behavior QC?
    # alignment resolved?
    # pass trial count QC (>=400 trials)?
    # priority scores, from 3 (high priority) to 0 (low priority)
        3: resolved; not critical; pass behavior QC & trial count QC
        2: resolved; not critical; pass only trial count QC
        1: resolved; not critical
        0: all the rest
    # any old comments
"""
#%%
import numpy as np
import pandas as pd
import os
from one.api import ONE
from brainbox.io.one import SessionLoader

datapath ='../data'  

one=ONE()
#% search by this project name: 
django_str = ['probe_insertion__session__projects__name__icontains,churchland_learninglifespan']
ins = pd.DataFrame.from_dict(one.alyx.rest('trajectories', 'list', django=django_str))

#prepare the dataframe
all_probes_df=pd.DataFrame.from_dict({'pid':ins['probe_insertion'].values,'eid':[sess['id'] for sess in ins['session']] }) 
all_probes_df.drop_duplicates(inplace=True) 

query_items = [
                '~probe_insertion__json__qc,CRITICAL', #not critical?
                'probe_insertion__session__extended_qc__behavior,1', #pass behavior QC?
                'probe_insertion__json__extended_qc__alignment_resolved,True'#alignment resolved?
            ]
# short name
query_items_short = ['~json_qc','qc_behavior','qc_alignment_resolved'] 

for q, query_item in enumerate(query_items):
    base_query = ['probe_insertion__session__projects__name__icontains,churchland_learninglifespan']
    base_query.append(query_item)
    django_query = ','.join(base_query)
    ins0 = pd.DataFrame.from_dict(one.alyx.rest('trajectories', 'list', django=django_query))
    if not ins0.empty: 
        for index, row in all_probes_df.iterrows():
            if row['pid'] in ins0.probe_insertion.values:
                all_probes_df.at[index,query_items_short[q]] = True
            else:
                all_probes_df.at[index,query_items_short[q]] = False

#% check # trials in each session
for eid in all_probes_df.eid.unique():
    sess_loader = SessionLoader(eid=eid,one=one) 
    sess_loader.load_trials()
    n_trials = sess_loader.trials.shape[0]
    all_probes_df.loc[all_probes_df['eid'] == eid, 'num_trials'] = n_trials

# create qc in number of trials
all_probes_df['qc_num_trials'] = all_probes_df['num_trials'] >= 400

#% set priority scores
# ['~json_qc','qc_behavior','qc_alignment_resolved','qc_num_trials']
for index, row in all_probes_df.iterrows():
    if (row['~json_qc']+row['qc_alignment_resolved']+row['qc_behavior']+row['qc_num_trials'])==4:
        all_probes_df.at[index,'priority_score']=3
    elif (row['qc_behavior']==False) and ((row['~json_qc']+row['qc_alignment_resolved']+row['qc_num_trials'])==3):
        all_probes_df.at[index,'priority_score']=2
    elif (row['qc_behavior']+row['qc_num_trials']==0) and ((row['~json_qc']+row['qc_alignment_resolved'])==2):
        all_probes_df.at[index,'priority_score']=1
    else:
        all_probes_df.at[index,'priority_score']=0

all_probes_df = all_probes_df.sort_values(by='priority_score', ascending=False).reset_index(drop=True)

#%save results 
all_probes_df.to_excel(os.path.join(datapath, "churchland_learninglifespan_project_info_probes_rerun.xlsx")) 
# %%
