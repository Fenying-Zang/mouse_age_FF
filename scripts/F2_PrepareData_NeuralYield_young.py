# -*- coding: utf-8 -*-
"""
calculating neural yield for the young group
@author: Fenying Zang, 2023
"""

from one.api import ONE
from ibllib.atlas import AllenAtlas
from reproducible_ephys_functions import combine_regions,get_insertions
from brainbox.io.one import SpikeSortingLoader
from myvariable import save_variable
import numpy as np

#filtering sessions/probes
one = ONE()
insertions = get_insertions(level=2, recompute=True, one=one, freeze=None) 
del insertions[3] #delete one subject because its age is larger than 12 months
num_sess = len(insertions)

#%%
all_brain_regions = ['PPC', 'CA1', 'DG', 'LP', 'PO']

Num_clusters = np.empty([5, num_sess], dtype=int)
Num_good_clusters = np.empty([5, num_sess], dtype=int)
Num_good_fr_clusters = np.empty([5, num_sess], dtype=int)

for k, Brain_Region in enumerate(all_brain_regions):
    #loop all sessions:
    for j , insertion in enumerate(insertions):
    
        current_sess_eid = insertion['session']['id']
        current_pname = insertion['probe_name']    
 
        one = ONE()
        ba = AllenAtlas()

        # load spikesorting data
        sl = SpikeSortingLoader(eid=current_sess_eid, pname=current_pname, one=one, atlas=ba)
        spikes, clusters, channels = sl.load_spike_sorting()
        clusters = sl.merge_clusters(spikes, clusters, channels)
        
        # modify and merge brain regions (PPC, VISa)
        clusters['merge_acronym'] = np.copy(clusters['acronym'])
        clusters['rep_site_acronym'] = combine_regions(clusters['merge_acronym'])

        idx_clusters_curr_region = clusters['cluster_id'][clusters['rep_site_acronym'] == Brain_Region]

        #Step 2: filter clusters based on 1)brain region;2)label=1; 3)firing rate >1 sp/sec
        good_clusters = np.bitwise_and(clusters['rep_site_acronym'] == Brain_Region, clusters['label'] == 1)

        good_clusterIDs = clusters['cluster_id'][good_clusters]
        good_fr_clusters = np.where(np.bitwise_and(good_clusters, clusters['firing_rate'] > 1))[0]

        Num_clusters[k,j] = len(idx_clusters_curr_region)
        Num_good_clusters[k,j] = len(good_clusterIDs)
        Num_good_fr_clusters[k,j] = len(good_fr_clusters)

# %%save the results
dict_neuron_filtering_young = {'Num_clusters':Num_clusters,'Num_good_clusters':Num_good_clusters,'Num_good_fr_clusters':Num_good_fr_clusters}
filename = save_variable(dict_neuron_filtering_young,'NeuralYield_filtering_young.csv')
