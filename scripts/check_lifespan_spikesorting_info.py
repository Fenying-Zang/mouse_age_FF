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
# resultPath = '../data/IBL_lifespan_spikesorting_task_info2.xlsx'
# pd_ses_all.to_excel(resultPath, index = False, engine='xlsxwriter')

resultPath_simple = '../data/IBL_lifespan_spikesorting_task_info_simple_20240130.xlsx'
pd_ses_all_simple.to_excel(resultPath_simple, index = False, engine='xlsxwriter')
# %%
import numpy as np
exclude = np.bitwise_and(pd_ses_all_simple['version']=='pykilosort_1.5.0',pd_ses_all_simple['status']=='Complete')
eids_torerun = pd_ses_all_simple[~exclude]
print(len(eids_torerun['session']))
print(eids_torerun['session'].values)

"""
    Those 55 eids don't have completed pykilosort 1.5.0 at this moment
    (having errored pykilosort 1.5.0, having completed old pykilosort, or only having matlab version):
    ['078fb4b2-4bff-414c-92a8-a2fb97ffcf59' '7aa9fe27-3f10-4ee0-a5a3-a0c59884f2b6' '9a14e9b7-0f79-410b-a456-1e8e7887e621' 'f45e30cf-12aa-4fa0-8248-f9f885dfa9ef' '6f87f78d-f091-46c7-8226-e8b1936b28ee' 'a68ef902-026c-4dfa-857f-8bc799a3b5e5' 'bb2153e7-1052-491e-a022-790e755c7a54' 'bf358c9a-ef84-4604-b83a-93416d2827ff' 'a45e62df-9f7f-4429-95a4-c4e334c8209f' 'a06189b0-a66e-4a5a-a1ef-4afa80de8b31' 'b26295df-e78d-4368-b694-1bf584f25bfc' '38bdc37b-c8be-4f18-b0a2-8a22dfa5f47e' 'fe0ecca9-9279-4ce6-bbfe-8b875d30d34b' 'c875fc7d-0966-448a-813d-663088fbfae8' 'e38c3ca1-4c0e-4fac-bcaf-b94db6e1b8e0' '6f321eab-6dad-4f2e-8160-5b182f999bb6' '022dd14c-eff2-470f-863c-e019fafa53ae' 'f31752a8-a6bb-498b-8118-6339d3d74ecb' 'a0dfbbc6-0454-4dc6-ade0-9ba57c18241d' '804bc680-976b-4e3e-9a47-a7e94847bd06' '3a1b819b-71ef-4d71-aae6-9f83c1f509cb' '531e7ac0-cfcd-4593-9bf7-bb7bab5d66e9' '9b4f6a8d-c879-4348-aa7e-0b34f6c6dacb' 'ab8a5331-1d0f-4b8a-9e0f-7be41c4857f9' 'da9eeafc-d7af-4a19-bf1c-2064e5b1b696' 'f2545193-1c5c-420e-96ac-3cb4b9799ea5' 'fe80df7d-15f0-4f89-9bbb-d3e5725c4b0a' 'a5145869-a54a-4871-95ef-016421122844' '2d768cde-65d4-4374-af2e-6ff3bf606eb4' '2cff323c-1510-4b78-a5d1-ca07b203f60c' '5c936319-6829-41cb-abc7-c4430910a6a0' '945028b5-bb38-4379-8ae4-488bcd67bcf5' '87b628a4-f11a-429c-ad98-34d43cf3178b' '48cdc3ce-8e21-4090-9686-e26c6e4e851f' '2eb86e84-4b48-488c-81ed-b98335d9a922' '83292b0f-e30f-48e1-ad0a-6f2bfe04e8b0' '89e258e9-cbca-4eca-bac4-13a2388b5113' '308274fc-28e8-4bfd-a4e3-3903b7b48c28' '41dfdc2a-987a-402a-99ae-779d5f569566' '78fceb60-e623-431b-ab80-7e29209058ac' 'e71bd25a-8c1e-4751-8985-4463a91c1b66' 'a44fd8cc-ae4c-49b2-a6b4-97c6552ad9f6' '0fe99726-9982-4c41-a07c-2cd7af6a6733' '93374502-c701-4b83-aa1a-23050b514708' '27f3c7a6-7be5-40e2-b4d8-9393978aeae1' '8cfb0b3d-2877-4616-9e32-4139c4501691' '107249ca-0d03-4e56-a7eb-6fe6210550ae' '7ae3865a-d8f4-4b73-938e-ddaec33f8bc6' '150f92bc-e755-4f54-96c1-84e1eaf832b4' 'ba7fc4d0-0486-4415-9b12-3f13b1cff710' 'c94463ed-57da-4f02-8406-46f2f03924f3' 'c90cdfa0-2945-4f68-8351-cb964c258725' 'ded7c877-49cf-46ad-b726-741f1cf34cef' 'af74b29d-a671-4c22-a5e8-1e3d27e362f3' '9931191e-8056-4adc-a410-a4a93487423f']
"""
# %% 
keep_eids = []
for index,row in pd_ses_all_simple.iterrows():
    if ('pykilosort' in row['version']) & (row['status']=='Complete'):
        print(index)
    else:
        keep_eids.append(row['session'])
print(len(keep_eids))
print(keep_eids)

"""
    Those 32 eids don't have completed usable pykilosort at all (either having errored pykilosort or only having matlab version):
    ['6f87f78d-f091-46c7-8226-e8b1936b28ee', 'a68ef902-026c-4dfa-857f-8bc799a3b5e5', 'bb2153e7-1052-491e-a022-790e755c7a54', 'bf358c9a-ef84-4604-b83a-93416d2827ff', 'a45e62df-9f7f-4429-95a4-c4e334c8209f', 'a06189b0-a66e-4a5a-a1ef-4afa80de8b31', 'b26295df-e78d-4368-b694-1bf584f25bfc', '38bdc37b-c8be-4f18-b0a2-8a22dfa5f47e', 'fe0ecca9-9279-4ce6-bbfe-8b875d30d34b', 'c875fc7d-0966-448a-813d-663088fbfae8', '804bc680-976b-4e3e-9a47-a7e94847bd06', '3a1b819b-71ef-4d71-aae6-9f83c1f509cb', '9b4f6a8d-c879-4348-aa7e-0b34f6c6dacb', 'fe80df7d-15f0-4f89-9bbb-d3e5725c4b0a', 'a5145869-a54a-4871-95ef-016421122844', '5c936319-6829-41cb-abc7-c4430910a6a0', '945028b5-bb38-4379-8ae4-488bcd67bcf5', '87b628a4-f11a-429c-ad98-34d43cf3178b', '89e258e9-cbca-4eca-bac4-13a2388b5113', '308274fc-28e8-4bfd-a4e3-3903b7b48c28', '41dfdc2a-987a-402a-99ae-779d5f569566', 'e71bd25a-8c1e-4751-8985-4463a91c1b66', 'a44fd8cc-ae4c-49b2-a6b4-97c6552ad9f6', '0fe99726-9982-4c41-a07c-2cd7af6a6733', '93374502-c701-4b83-aa1a-23050b514708', '27f3c7a6-7be5-40e2-b4d8-9393978aeae1', '8cfb0b3d-2877-4616-9e32-4139c4501691', '107249ca-0d03-4e56-a7eb-6fe6210550ae', '150f92bc-e755-4f54-96c1-84e1eaf832b4', 'ba7fc4d0-0486-4415-9b12-3f13b1cff710', 'ded7c877-49cf-46ad-b726-741f1cf34cef', 'af74b29d-a671-4c22-a5e8-1e3d27e362f3']
"""