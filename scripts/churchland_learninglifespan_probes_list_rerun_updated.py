"""
@author: F. Zang

updated on 27 Aug: group probes by the target(planned) position and add group name

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
    # planned position (x, y)
    # target_location_name
"""
#%% extract all probes of churchland_learninglifespan project
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

#%%================================= extract the planned position and group probes===================================
planned_probes = ins.loc[ins['provenance']=='Planned']
planned_probes['target_location_cluster'] = planned_probes.groupby(['x', 'y']).ngroup() #Number each group from 0 to the number of groups - 1

# for g, group in planned_probes.groupby('target_location_cluster'):
#     print(g, group.iloc[0]['x'], group.iloc[0]['y'], 'N=%s'%str(group.shape[0]))

"""
0 -2243.0 -2000.0 N=21   left_RS
1 -2243.0 0.0 N=2        visSTR_left (visual striatum)
2 -1800.0 -2000.0 N=2    VTA_left
3 -1781.0 -4000.0 N=1
4 -1281.0 2000.0 N=1
5 -1281.0 2500.0 N=14   frontalBilateral_left
6 -800.0 1000.0 N=11    LSX_left (lateral septal nucleus, striatal regions close to the midline)
7 -797.0 958.0 N=1
8 455.0 -1586.0 N=1
9 464.0 1750.0 N=12    LSX_ACB_right (lateral septal nucleus & ventral striatum / nucleus acumbens)
10 469.0 1743.0 N=1
11 1281.0 2000.0 N=1
12 1281.0 2500.0 N=15  frontalBilateral_right
13 1781.0 -4000.0 N=1
14 1800.0 -2000.0 N=1
15 2243.0 -2000.0 N=19  right_RS

"""
def assign_location_name(cluster_value):
    if cluster_value == 0:
        return 'left_RS'
    elif cluster_value == 1:
        return 'visSTR_left'
    elif cluster_value == 2:
        return 'VTA_left'
    elif cluster_value == 5:
        return 'frontalBilateral_left'
    elif cluster_value == 6:
        return 'LSX_left'
    elif cluster_value == 9:
        return 'LSX_ACB_right'
    elif cluster_value == 12:
        return 'frontalBilateral_right'
    elif cluster_value == 15:
        return 'right_RS'
    else:
        return 'Others'
planned_probes['target_location_name']= planned_probes['target_location_cluster'].apply(assign_location_name)

#%%
#prepare the output dataframe
all_probes_df=pd.DataFrame.from_dict({'pid':ins['probe_insertion'].values,
                                      'eid':[sess['id'] for sess in ins['session']]}) 
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

#sort by the priority score
all_probes_df = all_probes_df.sort_values(by='priority_score', ascending=False).reset_index(drop=True)
#%% merge those two dfs:
planned_probes.rename(columns={'probe_insertion': 'pid', 'x': 'planned_x', 'y': 'planned_y'}, inplace=True)
selected_columns = ['pid', 'planned_x', 'planned_y','target_location_name']
# selected_columns = ['pid', 'target_location_name']
merged_df = pd.merge(all_probes_df, planned_probes[selected_columns], on='pid', how='left')
#%save results 
merged_df.to_csv(os.path.join(datapath, "churchland_learninglifespan_project_info_probes_rerun_updated.csv"), index=False) 


