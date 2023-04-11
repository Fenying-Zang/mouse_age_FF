# -*- coding: utf-8 -*-
"""
plot F1
@author: Fenying Zang, 2023
"""
from myvariable import load_variable, smart_round
import pingouin as pg
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# %%young group

#load data of the young group:
dict_neuron_filtering_young = load_variable('NeuralYield_filtering_young.csv')
Number_Sessions_young = len(dict_neuron_filtering_young['Num_clusters'][0,:])

#%%old group
#load data of the old group:
dict_neuron_filtering_old = load_variable('NeuralYield_filtering_old.csv')
Number_Sessions_old = len(dict_neuron_filtering_old['Num_clusters'][0,:])

#%%
mycmap =  ['#78c679','#2c7fb8'] #green,blue
Index_remain_t_old= np.delete(range(Number_Sessions_old),[10,12]) #delete these two sessions because they don't have enough trials

#%%generate figure:
fig, ax =plt.subplots(2,5, sharex=True, sharey='row', figsize=(15, 10))
Brain_Regions = ['PPC','CA1', 'DG', 'LP', 'PO']
neuron_type = ['Num_clusters','Num_good_fr_clusters']
neuron_type_title = ['All neurons','Good neurons, fr > 1']

list_plot=[]

for region in range(len(Brain_Regions)):
    for num_fig in range(len(neuron_type)):   
        list_plot=[]
        curr_type = neuron_type[num_fig]
        ax_current=ax[num_fig,region]
        num_neuron_young = dict_neuron_filtering_young[curr_type][region,:]        #1 column 14values
        for i in range(len(num_neuron_young)):
            list_plot.append({'is_o':False,'group':'Young','value':num_neuron_young[i]})
        num_neuron_old = dict_neuron_filtering_old[curr_type][region,Index_remain_t_old]
        for k in range(len(num_neuron_old)):
            list_plot.append({'is_o':True,'group':'Old','value':num_neuron_old[k]})
        df = pd.DataFrame(list_plot)
        sns.stripplot(data=df, x="group", y="value",hue='is_o', ax=ax_current, palette=mycmap,dodge=False, alpha=1, zorder=1, legend=False) #scatter
        sns.barplot(data=df, x="group", y="value",ax=ax_current,linewidth=2, edgecolor=".5", palette=mycmap, alpha=.4,ci=0) 

        #statistical comparison:
        sta = pg.mwu(num_neuron_young, num_neuron_old, alternative='two-sided')
        pvalue = sta['p-val'][0]
        #put the p-value on the figure
        if pvalue <= 0.001:
                ax_current.text(-0.13,240,str(['p < 0.001'][0]),color='k',fontsize=20,font="Arial",fontweight ="bold")
        else:
            if pvalue <= 0.05:
                if num_fig==0:
                    ax_current.text(-0.13,240,'p = '+str(np.around(pvalue,3)),color='k',fontsize=23,font="Arial",fontweight ="bold") 
                else:
                    ax_current.text(-0.13,60,'p = '+str(np.around(pvalue,3)),color='k',fontsize=23,font="Arial",fontweight ="bold") 
        
            else:
                if num_fig==0:
                    ax_current.text(-0.13,240,'p = '+str(np.around(pvalue,3)),color='k',fontsize=23,font="Arial") 
                else:
                    ax_current.text(-0.13,60,'p = '+str(np.around(pvalue,3)),color='k',fontsize=23,font="Arial") 
                 
        ax_current.tick_params (labelsize =20) 

        if num_fig ==0:
            ax_current.set_title(Brain_Regions[region],font="Arial",fontsize=30,x=0.5,y=1.02)
        if region==0:            
            ax_current.set_ylabel(neuron_type_title[num_fig], font="Arial",fontsize=26,labelpad=15)

        ax_current.set_xlabel("", fontsize = 20)
        ax_current.set_xticklabels(labels = ['Young','Old'], font="Arial",fontsize=24)
        ax_current.spines['top'].set_visible(False)
        ax_current.spines['right'].set_visible(False)

fig.supylabel('Number of neurons', fontsize=36, font="Arial",x=0,y=0.5,fontweight ="bold")  
plt.savefig('F2.svg',dpi=600)
plt.show()
















