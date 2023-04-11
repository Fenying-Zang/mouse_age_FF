# -*- coding: utf-8 -*-
"""
plot F4
@author: Fenying Zang
"""
import numpy as np
import matplotlib.pyplot as plt
from myvariable import load_variable

#load data:
list_FF_all_regions_old = load_variable('FF_all_regions_old_alltrials.csv')
list_FR_all_regions_old = load_variable('FR_all_regions_old_alltrials.csv')

list_FF_all_regions_young = load_variable('FF_all_regions_young_alltrials.csv') #
list_FR_all_regions_young = load_variable('FR_all_regions_young_alltrials.csv')

#%%plot firing rate+fano factor in LP and PO area
mycmap = ['#2c7fb8','#78c679'] 
Brain_Regions = ['PPC','CA1', 'DG', 'LP', 'PO']
fig, ax =plt.subplots(2,2,sharex=True, sharey=False, figsize=(15, 6))
x = np.linspace(-0.32, 1, 67) #time points

for num_fig in range(3,len(Brain_Regions)):   
    current_ax=ax[num_fig-3, 0]
    
    current_FR_all_clusters_old = list_FR_all_regions_old[num_fig]
    current_FF_all_clusters_old = list_FF_all_regions_old[num_fig]
    
    current_FR_all_clusters_young = list_FR_all_regions_young[num_fig]
    current_FF_all_clusters_young = list_FF_all_regions_young[num_fig]  
    
    baseline_FR_old = np.nanmean(np.nanmean(current_FR_all_clusters_old, axis = 0)[8:18])
    baseline_FR_young = np.nanmean(np.nanmean(current_FR_all_clusters_young, axis = 0)[8:18])
    
    #calculate standard error
    semofff1_old = np.nanstd(current_FR_all_clusters_old, axis = 0, ddof=1) / np.sqrt(np.size(current_FR_all_clusters_old[:,0]))
    current_ax.plot(x, np.nanmean(current_FR_all_clusters_old, axis = 0) - baseline_FR_old,c = mycmap[0], lw=2, label='Old Mice') 
    semofff1_young = np.nanstd(current_FR_all_clusters_young, axis = 0, ddof=1) / np.sqrt(np.size(current_FR_all_clusters_young[:,0]))
    current_ax.plot(x, np.nanmean(current_FR_all_clusters_young, axis = 0) - baseline_FR_young,c = mycmap[1], lw=2, label='Young Mice') 

    #plot errorbar:
    current_ax.fill_between(x, np.nanmean(current_FR_all_clusters_old, axis = 0) - baseline_FR_old-semofff1_old,np.nanmean(current_FR_all_clusters_old, axis = 0) - baseline_FR_old+semofff1_old, alpha=0.15, color = mycmap[0])
    current_ax.fill_between(x, np.nanmean(current_FR_all_clusters_young, axis = 0) - baseline_FR_young-semofff1_young,np.nanmean(current_FR_all_clusters_young, axis = 0) - baseline_FR_young+semofff1_young, alpha=0.25,  color = mycmap[1])

    current_ax.axvline(x = 0, ls='--', lw=1.2, alpha=0.8, c = 'gray') #add an auxiliary line
    current_ax.set_ylabel(Brain_Regions[num_fig],  fontsize=25, font="Arial",fontweight ="bold")
    current_ax.set_xlim(-0.2, 1)
    current_ax.spines['top'].set_visible(False)
    current_ax.spines['right'].set_visible(False)
    
    current_ax.tick_params (labelsize = 15)
    ###################################
    #for fano factor
    current_ax=ax[num_fig-3, 1]
    current_ax.plot(x, np.nanmean(current_FF_all_clusters_old, axis = 0),c = mycmap[0], lw=2, label='Old mice') 
    current_ax.plot(x, np.nanmean(current_FF_all_clusters_young, axis = 0),c = mycmap[1], lw=2,  label='Young mice') 
    semofff_old = np.nanstd(current_FF_all_clusters_old, axis = 0, ddof=1) / np.sqrt(np.size(current_FF_all_clusters_old[:,0]))
    semofff_young = np.nanstd(current_FF_all_clusters_young, axis = 0, ddof=1) / np.sqrt(np.size(current_FF_all_clusters_young[:,0]))
    #errorbar:
    current_ax.fill_between(x, np.nanmean(current_FF_all_clusters_young, axis = 0)-semofff_young,np.nanmean(current_FF_all_clusters_young, axis = 0)+semofff_young, alpha=0.25,color = mycmap[1])
    current_ax.fill_between(x, np.nanmean(current_FF_all_clusters_old, axis = 0)-semofff_old,np.nanmean(current_FF_all_clusters_old, axis = 0)+semofff_old, alpha=0.15,color = mycmap[0])

    current_ax.axvline(x = 0, ls='--', lw=1.2, alpha=0.8, c = 'gray') 
    current_ax.set_xlim(-0.2, 1) 
    current_ax.tick_params (labelsize = 15) 
    current_ax.spines['top'].set_visible(False)
    current_ax.spines['right'].set_visible(False)
    if num_fig ==4:
        current_ax.legend(frameon=False, ncol=1, bbox_to_anchor=(0.42,-0.2), loc=2, markerscale=2, fontsize=17)#(0.12,1.6)

fig.subplots_adjust(hspace=0.15) 
fig.subplots_adjust(wspace=0.25) 
fig.supxlabel('Time from stimulus onset (s)', fontsize=25, font="Arial",x=0.5,y=-0.02,fontweight ="bold")
plt.text(-1.45,2.9,'ΔFiring Rate (spikes/s)', fontsize=25, font="Arial",fontweight ="bold") 
plt.text(0.2,2.9,'Fano Factor', fontsize=25, font="Arial",fontweight ="bold") 
plt.subplots_adjust(wspace=0.2) 
plt.savefig('F4.svg',dpi=600,bbox_inches = 'tight')
plt.show()