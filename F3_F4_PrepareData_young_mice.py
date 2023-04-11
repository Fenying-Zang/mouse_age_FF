"""
search for young mice data from public IBL database
calculate firing rate and fano factor, then save the results

@author: Fenying Zang, 2023
"""

from one.api import ONE
from ibllib.atlas import AllenAtlas
from brainbox.io.one import SpikeSortingLoader
from brainbox.task.trials import get_event_aligned_raster, filter_by_trial, find_trial_ids
from reproducible_ephys_functions import combine_regions, get_insertions
from myvariable import save_variable
import numpy as np

#searching&filtering sessions
one = ONE()
insertions = get_insertions(level=2, recompute=True, one=one, freeze=None) #return 49 insertions

del insertions[3] #delete one subject because its age is larger than 12 months
num_sess = len(insertions)


#%% Calculate FR+FF for each brain regions:
    
Brain_Regions = ['PPC','CA1', 'DG', 'LP', 'PO']
Align_Event = 'stimOn_times' 

list_FR_all_regions = list()
list_FF_all_regions = list()
len_timepoint=67

for ti, CurrentBrainRegion in enumerate(Brain_Regions):  # loop: all brain regions of interest

    aveFFofregion = np.zeros((num_sess,len_timepoint)) #to store the Fano Factor (time course) of all sessions; row：sess; column：time point
    dismiss_session_idx = np.array([], dtype = int)
    Number_Trials = np.array([], dtype = int)
    
    merge_FR_all_clusters = np.ones((1,len_timepoint))#FR
    merge_FF_all_clusters = np.ones((1,len_timepoint))#FF
    
    indexfordict = np.array([], dtype = int)
    number_clusters = np.array([], dtype = int)
    number_clusters2 = np.array([], dtype = int)
   
    
    for j , insertion in enumerate(insertions): #loop: all sessions
        eid = insertion['session']['id']
        pname = insertion['probe_name']
        
        one = ONE()
        ba = AllenAtlas()
        
        #Loading SpikeSorting Data of the current session
        sl = SpikeSortingLoader(eid=eid, pname=pname, one=one, atlas=ba)
        spikes, clusters, channels = sl.load_spike_sorting()
        clusters = sl.merge_clusters(spikes, clusters, channels)
    
        #load trials of the current session
        trials = one.load_object(eid, 'trials', collection='alf') 
        
        # modify and merge brain regions (PPC, VISa)
        clusters['merge_acronym'] = np.copy(clusters['acronym'])
        clusters['rep_site_acronym'] = combine_regions(clusters['merge_acronym'])
            
        #Step 2: filter neurons based on 1)brain region;2)label=1; 3)firing rate >1 sp/sec
        temp_arr = np.bitwise_and(clusters['rep_site_acronym'] == CurrentBrainRegion, clusters['label'] == 1)
        region_clusters_idx2 = np.where(np.bitwise_and(temp_arr, clusters['firing_rate'] > 1))[0]
        
        if np.size(region_clusters_idx2) > 0: #the number of neurons left            
            region_FanoFactor = np.zeros((len(region_clusters_idx2),75)) #row：clusters; column：time point; value：fano factor
            region_FR = np.zeros((len(region_clusters_idx2),75))#row：clusters; column：time point; value：firing rate

            number_clusters = np.append(number_clusters, len(region_clusters_idx2))
            for u in range(len(region_clusters_idx2)):#loop clusters belonging to current brain region
            
                clustID = region_clusters_idx2[u]
                spikeindex = np.where(spikes['clusters'] == clustID)[0]   #find all of the spikes belonging to this neuron
                
                all_event_raster, t = get_event_aligned_raster(spikes['times'][spikeindex],trials[Align_Event],tbin=0.02, values=None, epoch=[- 0.4, 1], bin=True)
                                            
                hist_win = 0.02
                fr_win = 0.1
        
                t_tot = t[-1]-t[0] #the earliest & latest time point 1.4
                n_bins_hist = int(t_tot / hist_win)#140-->70
                n_bins_fr = int(t_tot / fr_win) #28-->14
                step_sz = int(len(all_event_raster[0,:]) / n_bins_fr) #5
                firecount = np.zeros((len(all_event_raster[:,0]),75))#row:trials; column:time bin
                    
                for zl in range(len(all_event_raster[:,0])): # all trials
                    firecount[zl,:]= np.convolve(all_event_raster[zl,:], np.ones(step_sz))
    
                ffs = np.nanvar(firecount, axis=0) / np.nanmean(firecount, axis=0) 

                region_FanoFactor[u,:] = ffs
                region_FR[u,:] = np.mean(firecount, axis= 0)/fr_win
    
            region_FanoFactor = region_FanoFactor[:,4:-4]# due to the convolve() function & the causal setting
            region_FR = region_FR[:,4:-4]
            
            merge_FF_all_clusters = np.r_[merge_FF_all_clusters,region_FanoFactor]
            merge_FR_all_clusters = np.r_[merge_FR_all_clusters,region_FR]
        else:
            dismiss_session_idx = np.append(dismiss_session_idx, j)    
    merge_FF_all_clusters = np.delete(merge_FF_all_clusters, 0, axis = 0)
    merge_FR_all_clusters = np.delete(merge_FR_all_clusters, 0, axis = 0)
    
    list_FF_all_regions.append(merge_FF_all_clusters)
    list_FR_all_regions.append(merge_FR_all_clusters)     

# %% save the results into csv files:
filename = save_variable(list_FF_all_regions,'FF_all_regions_young_alltrials.csv')
filename = save_variable(list_FR_all_regions,'FR_all_regions_young_alltrials.csv')
