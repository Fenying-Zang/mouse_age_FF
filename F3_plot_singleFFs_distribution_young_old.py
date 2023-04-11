# -*- coding: utf-8 -*-
"""
plot F3: 
@author: Fenying Zang, 2023
"""
import pingouin as pg
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from myvariable import load_variable,smart_round

#%%load date
list_FF_all_regions_old = load_variable('FF_all_regions_old_alltrials.csv')
list_FR_all_regions_old = load_variable('FR_all_regions_old_alltrials.csv')
#young
list_FF_all_regions_young = load_variable('FF_all_regions_young_alltrials.csv')
list_FR_all_regions_young = load_variable('FR_all_regions_young_alltrials.csv')

#%%plot
Brain_Regions = ['LP', 'PO']
mycmap =  ['#78c679','#2c7fb8'] #green,blue

fig, ax =plt.subplots(1,2,sharex=False, sharey=False, figsize=(15, 5))#50
list_plot=[]

for b, brain in enumerate(Brain_Regions):
    current_ax=ax[b]
    
    idx_2 = np.where(np.logical_not(np.isnan(list_FF_all_regions_young[b+3][:,26])))[0]    
    ff_young=list_FF_all_regions_young[b+3][:,26]
    ff_young=ff_young[idx_2]
    
    for i in range(len(ff_young)):
        list_plot.append({'is_o':False,'group':'young','value':ff_young[i]})    

    idx_1 = np.where(np.logical_not(np.isnan(list_FF_all_regions_old[b+3][:,26])))[0]  
    ff_old=list_FF_all_regions_old[b+3][:,26]
    ff_old=ff_old[idx_1]
    
    for m in range(len(ff_old)):
        list_plot.append({'is_o':True,'group':'old','value':ff_old[m]})    

    sta = pg.mwu(ff_old,ff_young, alternative='two-sided') 
    pvalue = sta['p-val'][0]
    
    x_value = ['Young','Old']
    mydf = pd.DataFrame(list_plot)
    
    sns.histplot(data=mydf, ax=current_ax, x="value", hue="group", stat="percent",common_norm=False, palette=mycmap, multiple="dodge", binwidth=0.2,linewidth=1.1,shrink=1,kde=True, line_kws={"linewidth":4},fill=False,legend=False) #
    
    if sta['p-val'][0]<0.001:
        current_ax.text(3,7,str(['p < 0.001'][0]),font="Arial",fontsize=20)
    else:
        current_ax.text(3,7,'p = '+str(smart_round(sta['p-val'][0],3)),font="Arial",fontsize=20)
    
    current_ax.tick_params (labelsize =20)     
    current_ax.set_title(brain, font="Arial",fontsize=25,fontweight ="bold")
    current_ax.set_xlabel("  ", fontsize = 20)
    current_ax.set_ylabel("  ", fontsize = 20)  
    current_ax.set_xlim(0,6)
    current_ax.spines['top'].set_visible(False)
    current_ax.spines['right'].set_visible(False)

fig.supylabel('Percentage of neurons', fontsize=25, font="Arial",x=0.065,y=0.5,fontweight ="bold")  
fig.supxlabel('Fano Factor', fontsize=25, font="Arial",x=0.5,y=-0.05,fontweight ="bold")   
plt.legend(['Old','Young'],markerscale=1.6,fontsize=18)
plt.subplots_adjust(wspace=0.1)
plt.savefig('F3.svg',dpi=600,bbox_inches = 'tight')
plt.show()   
