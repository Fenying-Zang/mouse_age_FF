"""
General functions for reproducible ephys paper
"""

import pandas as pd
import seaborn as sns
import matplotlib
import numpy as np
import logging
from pathlib import Path
import shutil
from datetime import datetime
import scipy
import traceback

from neurodsp import voltage
from one.api import ONE
from one.alf.exceptions import ALFObjectNotFound
from iblutil.numerical import ismember
from ibllib.atlas import AllenAtlas
import brainbox.io.one as bbone
from brainbox.behavior import training
import yaml
from brainbox.io.spikeglx import Streamer

from one.params import get_cache_dir



LFP_RESAMPLE_FACTOR = 10
LFP_BAND = [20, 80]  # previously [49, 61]
THETA_BAND = [6, 12]


logger = logging.getLogger('paper_reproducible_ephys')


STR_QUERY = 'probe_insertion__session__project__name__icontains,ibl_neuropixel_brainwide_01,' \
            'probe_insertion__session__qc__lt,50,' \
            '~probe_insertion__json__qc,CRITICAL,' \
            'probe_insertion__session__n_trials__gte,400'

BRAIN_REGIONS = ['PPC', 'CA1', 'DG', 'LP', 'PO']


def labs():
    lab_number_map = {'cortexlab': 'Lab 1', 'mainenlab': 'Lab 2', 'churchlandlab': 'Lab 3',
                      'angelakilab': 'Lab 4', 'wittenlab': 'Lab 5', 'hoferlab': 'Lab 6',
                      'mrsicflogellab': 'Lab 6', 'danlab': 'Lab 7', 'zadorlab': 'Lab 8',
                      'steinmetzlab': 'Lab 9', 'churchlandlab_ucla': 'Lab 10',
                      'hausserlab' : 'Lab 11'}
    institution_map = {'cortexlab': 'UCL', 'mainenlab': 'CCU', 'zadorlab': 'CSHL (Z)',
                       'churchlandlab': 'CSHL (C)', 'angelakilab': 'NYU',
                       'wittenlab': 'Princeton', 'hoferlab': 'SWC', 'mrsicflogellab': 'SWC',
                       'danlab': 'Berkeley', 'steinmetzlab': 'UW', 'churchlandlab_ucla': 'UCLA',
                       'hausserlab': 'UCL (H)'}
    colors = np.vstack((sns.color_palette('tab10'), (0, 0, 0)))
    institutions = ['Berkeley', 'CCU', 'CSHL (C)', 'CSHL (Z)', 'NYU', 'Princeton', 'SWC', 'UCL',
                    'UCLA', 'UW', 'UCL (H)']
    institution_colors = {}
    for i, inst in enumerate(institutions):
        institution_colors[inst] = colors[i]
    return lab_number_map, institution_map, institution_colors


def query(behavior=False, n_trials=400, resolved=True, min_regions=2, exclude_critical=True, one=None, str_query=None,
          as_dataframe=False, bilateral=False):

    one = one or ONE()

    if isinstance(str_query, str):
        django_queries = [str_query]
    elif isinstance(str_query, list):
        django_queries = str_query
    else:
        django_queries = []

    django_queries.append('probe_insertion__session__project__name,ibl_neuropixel_brainwide_01')

    if exclude_critical:
        django_queries.append('probe_insertion__session__qc__lt,50,~probe_insertion__json__qc,CRITICAL')
    if resolved:
        django_queries.append('probe_insertion__json__extended_qc__alignment_resolved,True')
    if behavior:
        django_queries.append('probe_insertion__session__extended_qc__behavior,1')
    if n_trials > 0:
        django_queries.append(f'probe_insertion__session__n_trials__gte,{n_trials}')

    django_query = ','.join(django_queries)

    if bilateral:
        # Query bilateral insertions
        right_ins = one.alyx.rest('trajectories', 'list', provenance='Planned',
                                  x=2243, y=-2000, theta=15,
                                  django=django_query)
        trajectories = []
        for i, eid in enumerate([j['session']['id'] for j in right_ins]):
            left_ins = one.alyx.rest('trajectories', 'list', provenance='Planned',
                                     x=-2243, y=-2000, theta=15,
                                     django=django_query, session=eid)
            if len(left_ins) == 1:
                trajectories.append(left_ins[0])
                trajectories.append(right_ins[i])

    else:
        trajectories = one.alyx.rest('trajectories', 'list', provenance='Planned',
                                     x=-2243, y=-2000, theta=15,
                                     django=django_query)
    pids = [traj['probe_insertion'] for traj in trajectories]

    if min_regions > 0:
        region_traj = []
        query_regions = BRAIN_REGIONS.copy()
        query_regions[query_regions.index('PPC')] = 'VIS'
        # Query how many of the target regions were hit per recording
        for i, region in enumerate(query_regions):
            region_query = one.alyx.rest(
                'trajectories', 'list', provenance='Ephys aligned histology track',
                django=f'{django_query},channels__brain_region__acronym__icontains,{region},probe_insertion__in,{pids}')
            region_traj = np.append(region_traj, [i['probe_insertion'] for i in region_query])

        region_pids, num_regions = np.unique(region_traj, return_counts=True)
        isin, _ = ismember(np.array(pids), region_pids[num_regions >= min_regions])
        trajectories = [trajectories[i] for i, val in enumerate(isin) if val]

    # Convert to dataframe if necessary
    if as_dataframe:
        trajectories = traj_list_to_dataframe(trajectories)

    return trajectories


def traj_list_to_dataframe(trajectories):

    trajectories = pd.DataFrame(
        data={'subjects': [i['session']['subject'] for i in trajectories],
              'dates': [i['session']['start_time'][:10] for i in trajectories],
              'probes': [i['probe_name'] for i in trajectories],
              'lab': [i['session']['lab'] for i in trajectories],
              'eid': [i['session']['id'] for i in trajectories],
              'probe_insertion': [i['probe_insertion'] for i in trajectories]})

    trajectories['institution'] = trajectories.lab.map(labs()[1])

    return trajectories


def get_insertions(level=2, recompute=False, as_dataframe=False, one=None, freeze=None, bilateral=False):
    """
    Find insertions used for analysis based on different exclusion levels
    Level 0: minimum_regions = 0, resolved = True, behavior = False, n_trial >= 0, exclude_critical = True
    Level 1: minimum_regions = 2, resolved = True, behavior = False, n_trial >= 400, exclude_critical = True
    Level 2: minimum_regions = 2, resolved = True, behavior = False, n_trial >= 400, exclude_critical = True,
             max_ap_rms=40,  max_lfp_power=-140, min_channels_per_region=5, min_neurons_per_channel=0.1

    :param level: exclusion level 0, 1 or 2
    :param recompute: whether to recompute the metrics dataframe that is used to exclude recordings at level=2
    :param as_dataframe: whether to return a dict or a dataframe
    :param one: ONE instance
    :return: dict or pandas dataframe of probe insertions
    """
    one = one or ONE()

    if freeze is not None:
        # TODO for next freeze need to think about how to deal with bilateral
        ins_df = pd.read_csv(data_release_path().joinpath(f'{freeze}.csv'))
        pids = ins_df[ins_df['level'] >= level].pid.values
        insertions = one.alyx.rest('trajectories', 'list', provenance='Planned', django=f'probe_insertion__in,{list(pids)}')
        if recompute:
            _ = recompute_metrics(insertions, one)

        if as_dataframe:
            insertions = traj_list_to_dataframe(insertions)

        return insertions

    if bilateral:
        insertions = query(min_regions=0, n_trials=0, behavior=False, exclude_critical=True, one=one,
                           as_dataframe=as_dataframe, bilateral=True)

        return insertions

    if level == 0:
        insertions = query(min_regions=0, n_trials=0, behavior=False, exclude_critical=True, one=one,
                           as_dataframe=as_dataframe)
        return insertions

    if level == 1:
        insertions = query(one=one, as_dataframe=as_dataframe)
        if recompute:
            _ = recompute_metrics(insertions, one)
        return insertions

    if level >= 2:
        insertions = query(one=one, as_dataframe=False)
        pids = np.array([ins['probe_insertion'] for ins in insertions])
        if recompute:
            _ = recompute_metrics(insertions, one)
        ins = filter_recordings(min_neuron_region=0, one=one, freeze=freeze)
        ins = ins[ins['include']]

        if not as_dataframe:
            isin, _ = ismember(pids, ins['pid'].unique())
            ins = [insertions[i] for i, val in enumerate(isin) if val]

        return ins


def get_histology_insertions(one=None, freeze=None):
    one = one or ONE()
    if freeze is not None:
        ins_df = pd.read_csv(data_release_path().joinpath(f'{freeze}.csv'))
        pids = ins_df.pid.values
        insertions = one.alyx.rest('trajectories', 'list', provenance='Planned', django=f'probe_insertion__in,{list(pids)}')
    else:
        insertions = one.alyx.rest('trajectories', 'list', provenance='Planned', x=-2243, y=-2000, theta=15,
                                   django='probe_insertion__session__project__name,ibl_neuropixel_brainwide_01')
    return insertions


def recompute_metrics(insertions, one, bilateral=False):
    """
    Determine whether metrics need to be recomputed or not for given list of insertions
    :param insertions: list of insertions
    :param one: ONE object
    :return:
    """

    pids = np.array([ins['probe_insertion'] for ins in insertions])
    metrics = load_metrics(bilateral=bilateral)
    if (metrics is None) or (metrics.shape[0] == 0):
        metrics = compute_metrics(insertions, one=one, bilateral=bilateral)
    else:
        isin, _ = ismember(pids, metrics['pid'].unique())
        if not np.all(isin):
            metrics = compute_metrics(insertions, one=one, bilateral=bilateral)

    return metrics


def data_release_path():
    # Retrieve absolute path of paper-behavior dir
    repo_dir = Path(__file__).resolve().parent
    data_dir = repo_dir.joinpath('data_releases')

    return data_dir


def figure_style(return_colors=False):
    """
    Set seaborn style for plotting figures
    """
    sns.set(style="ticks", context="paper",
            font="Arial",
            rc={"font.size": 7,
                "axes.titlesize": 8,
                "axes.labelsize": 7,
                "axes.linewidth": 0.5,
                "lines.linewidth": 1,
                "lines.markersize": 4,
                "xtick.labelsize": 7,
                "ytick.labelsize": 7,
                "savefig.transparent": False,
                "xtick.major.size": 2.5,
                "ytick.major.size": 2.5,
                "xtick.major.width": 0.5,
                "ytick.major.width": 0.5,
                "xtick.minor.size": 2,
                "ytick.minor.size": 2,
                "xtick.minor.width": 0.5,
                "ytick.minor.width": 0.5
                })
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42
    if return_colors:
        return {'PPC': sns.color_palette('colorblind')[0],
                'CA1': sns.color_palette('colorblind')[2],
                'DG': sns.color_palette('muted')[2],
                'LP': sns.color_palette('colorblind')[4],
                'PO': sns.color_palette('colorblind')[6],
                'RS': sns.color_palette('Set2')[0],
                'FS': sns.color_palette('Set2')[1],
                'RS1': sns.color_palette('Set2')[2],
                'RS2': sns.color_palette('Set2')[3]}


def combine_regions(regions):
    """
    Combine all layers of cortex and the dentate gyrus molecular and granular layer
    Combine VISa and VISam into PPC
    """
    remove = ['1', '2', '3', '4', '5', '6a', '6b', '/']
    for i, region in enumerate(regions):
        if region[:2] == 'CA':
            continue
        if (region == 'DG-mo') or (region == 'DG-sg') or (region == 'DG-po'):
            regions[i] = 'DG'
        for j, char in enumerate(remove):
            regions[i] = regions[i].replace(char, '')
        if (regions[i] == 'VISa') | (regions[i] == 'VISam'):
            regions[i] = 'PPC'
    return regions


def load_metrics(bilateral=False, freeze=None):
    if freeze is not None:
        metrics = pd.read_csv(data_release_path().joinpath(f'metrics_{freeze}.csv'))
    else:
        fname = 'insertion_metrics_bilateral.csv' if bilateral else 'insertion_metrics.csv'
        if save_data_path().joinpath(fname).exists():
            metrics = pd.read_csv(save_data_path().joinpath(fname))
        else:
            metrics = None
    return metrics


def save_data_path(figure=None):
    """
    Path to save data
    :param figure: figure number e.g 'figure3'
    :return:
    """
    try:
        import reproducible_ephys_paths
        defined_paths = dir(reproducible_ephys_paths)
        if 'DATA_PATH' in defined_paths:
            data_path = Path(reproducible_ephys_paths.DATA_PATH)
        else:
            data_path = Path(get_cache_dir()).joinpath('paper_repro_ephys_data')

    except ModuleNotFoundError:
        data_path = Path(get_cache_dir()).joinpath('paper_repro_ephys_data')

    if figure is not None:
        data_path = data_path.joinpath(str(figure))

    data_path.mkdir(exist_ok=True, parents=True)

    return data_path


def save_figure_path(figure=None):
    """
    Path to save figures
    :param figure: figure number e.g 'figure3'
    :return:
    """
    try:
        import reproducible_ephys_paths
        defined_paths = dir(reproducible_ephys_paths)
        if 'FIG_PATH' in defined_paths:
            fig_path = Path(reproducible_ephys_paths.FIG_PATH)
        else:
            fig_path = Path(get_cache_dir()).joinpath('paper_repro_ephys_data')

    except ModuleNotFoundError:
        fig_path = Path(get_cache_dir()).joinpath('paper_repro_ephys_data')

    if figure is not None:
        fig_path = fig_path.joinpath(str(figure), 'figures')
    else:
        fig_path = fig_path.joinpath('figures')

    fig_path.mkdir(exist_ok=True, parents=True)

    return fig_path


def compute_metrics(insertions, one=None, ba=None, spike_sorter='pykilosort', save=True, bilateral=False):
    one = one or ONE()
    ba = ba or AllenAtlas()
    lab_number_map, institution_map, _ = labs()
    metrics = pd.DataFrame()

    for i, ins in enumerate(insertions):
        eid = ins['session']['id']
        lab = ins['session']['lab']
        subject = ins['session']['subject']
        sess_date = ins['session']['start_time'][:10]
        pid = ins['probe_insertion']
        probe = ins['probe_name']
        collection = f'alf/{probe}/{spike_sorter}'

        try:
            subj = one.alyx.rest('subjects', 'list', nickname=subject)
            subj_dob = subj[0]['birth_date']
            age_at_recording = (datetime.strptime(sess_date, '%Y-%m-%d') - datetime.strptime(subj_dob, '%Y-%m-%d')).days
            n_sess = len(one.search(subject=subject, date_range=[subj_dob, sess_date]))
        except Exception:
            age_at_recording = np.nan
            n_sess = np.nan

        try:
            trials = one.load_object(eid, 'trials', collection='alf', attribute=training.TRIALS_KEYS)
            n_trials = trials["stimOn_times"].shape[0]
            behav = training.criterion_delay(n_trials=n_trials, perf_easy=training.compute_performance_easy(trials)).astype(bool)
        except Exception:
            sess_details = one.alyx.rest('sessions', 'read', id=eid)
            n_trials = sess_details['n_trials']
            behav = bool(sess_details['extended_qc']['behavior'])

        try:
            ap = one.load_object(eid, 'ephysChannels', collection=f'raw_ephys_data/{probe}', attribute=['apRMS'])
            if 'apRMS' not in ap.keys():
                pid_qc = one.alyx.rest('insertions', 'list', id=pid)[0]['json']['extended_qc']
                ap_val = pid_qc['apRms_p90_proc'] * 1e6 if 'apRms_p90_proc' in pid_qc.keys() else 0
        except ALFObjectNotFound:
            logger.warning(f'ephysChannels object not found for pid: {pid}')
            ap = {}
            try:
                pid_qc = one.alyx.rest('insertions', 'list', id=pid)[0]['json']['extended_qc']
                ap_val = pid_qc['apRms_p90_proc'] * 1e6 if 'apRms_p90_proc' in pid_qc.keys() else 0
            except Exception:
                ap_val = np.nan

        try:
            lfp = one.load_object(eid, 'ephysSpectralDensityLF', collection=f'raw_ephys_data/{probe}')
        except ALFObjectNotFound:
            logger.warning(f'ephysSpectralDensityLF object not found for pid: {pid}')
            lfp = {}


        df_lfp = compute_lfp_insertion(one=one, pid=ins['probe_insertion'])


        try:
            clusters = one.load_object(eid, 'clusters', collection=collection, attribute=['metrics', 'channels'])
            if 'metrics' not in clusters.keys():
                sl = bbone.SpikeSortingLoader(eid=eid, pname=probe, one=one, atlas=ba)
                spikes, clusters, channels = sl.load_spike_sorting()
                clusters = sl.merge_clusters(spikes, clusters, channels)
            else:
                clusters['label'] = clusters['metrics']['label']
                channels = bbone.load_channel_locations(eid, probe=probe, one=one, aligned=True, brain_atlas=ba)[probe]

            channels['rawInd'] = one.load_dataset(eid, dataset='channels.rawInd.npy', collection=collection)
            channels['rep_site_acronym'] = combine_regions(channels['acronym'])
            clusters['rep_site_acronym'] = channels['rep_site_acronym'][clusters['channels']]

        except Exception as err:
            logger.error(f'{pid}: {err}')

        try:
            for region in BRAIN_REGIONS:
                region_clusters = np.where(np.bitwise_and(clusters['rep_site_acronym'] == region,
                                                          clusters['label'] == 1))[0]
                region_chan = channels['rawInd'][np.where(channels['rep_site_acronym'] == region)[0]]

                if np.all(np.isnan(df_lfp['lfp_theta'])):
                    lfp_theta_region = np.nan
                else:
                    lfp_theta_region = df_lfp['lfp_theta'][region_chan].mean()

                if np.all(np.isnan(df_lfp['lfp_power'])):
                    lfp_region = np.nan
                else:
                    lfp_region = df_lfp['lfp_power'][region_chan].mean()

                if 'power' in lfp.keys() and region_chan.shape[0] > 0:
                    freqs = (lfp['freqs'] > LFP_BAND[0]) & (lfp['freqs'] < LFP_BAND[1])
                    chan_power = lfp['power'][:, region_chan]
                    lfp_region_raw = np.mean(10 * np.log(chan_power[freqs]))  # convert to dB

                    freqs = (lfp['freqs'] > THETA_BAND[0]) & (lfp['freqs'] < THETA_BAND[1])
                    chan_power = lfp['power'][:, region_chan]
                    lfp_theta_region_raw = np.mean(10 * np.log(chan_power[freqs]))  # convert to dB
                else:
                    # TO DO SEE IF THIS IS LEGIT
                    lfp_region = np.nan
                    lfp_theta_region = np.nan
                if 'apRMS' in ap.keys() and region_chan.shape[0] > 0:
                    ap_rms = np.percentile(ap['apRMS'][1, region_chan], 90) * 1e6
                elif region_chan.shape[0] > 0:
                    ap_rms = ap_val
                else:
                    ap_rms = 0

                metrics = pd.concat((metrics, pd.DataFrame(
                    index=[metrics.shape[0] + 1], data={'pid': pid, 'eid': eid, 'probe': probe,
                                                        'lab': lab, 'subject': subject, 'institute': institution_map[lab],
                                                        'lab_number': lab_number_map[lab],
                                                        'region': region, 'date': sess_date,
                                                        'n_channels': region_chan.shape[0],
                                                        'neuron_yield': region_clusters.shape[0],
                                                        'lfp_power': lfp_region,
                                                        'lfp_theta_power': lfp_theta_region,
                                                        'lfp_power_raw': lfp_region_raw,
                                                        'lfp_theta_power_raw': lfp_theta_region_raw,
                                                        'rms_ap_p90': ap_rms,
                                                        'n_trials': n_trials,
                                                        'behavior': behav,
                                                        'age_at_recording': age_at_recording,
                                                        'n_sess_before_recording': n_sess})))
        except Exception as err:
            logger.error(f'{pid}: {err}')

    if save:
        fname = 'insertion_metrics_bilateral.csv' if bilateral else 'insertion_metrics.csv'
        metrics.to_csv(save_data_path().joinpath(fname))

    return metrics


def filter_recordings(df=None, one=None, max_ap_rms=40, max_lfp_power=-140, min_neurons_per_channel=0.1, min_channels_region=5,
                      min_regions=3, min_neuron_region=4, min_lab_region=3, min_rec_lab=4, n_trials=400, behavior=False,
                      exclude_subjects=['ibl_witten_13', 'ibl_witten_26'], recompute=True, freeze='release_2022_11'):
    """
    Filter values in dataframe according to different exclusion criteria
    :param df: pandas dataframe
    :param by_anatomy_only: bool
    :param max_ap_rms:
    :param max_lfp_power:
    :param min_neurons_per_channel:
    :param min_channels_region:
    :param min_regions:
    :param min_neuron_region:
    :param min_lab_region:
    :param n_trials:
    :param behavior:
    :return:
    """

    # Load in the insertion metrics
    metrics = load_metrics(freeze=freeze)

    if df is None:
        df = metrics
        if df is None:
            ins = get_insertions(level=0, recompute=False, freeze=freeze)
            df = compute_metrics(ins, one=ONE(), save=True)
        df['original_index'] = df.index
    else:
        # make sure that all pids in the dataframe df are included in metrics otherwise recompute metrics
        if metrics is None:
            one = ONE()
            ins = get_insertions(level=0, one=one, recompute=False, freeze=freeze)
            metrics = compute_metrics(ins, one=one, save=True)

        isin, _ = ismember(df['pid'].unique(), metrics['pid'].unique())
        if ~np.all(isin):
            logger.warning(f'Warning: {np.sum(~isin)} recordings are missing metrics')
            if recompute:
                one = ONE()
                ins = get_insertions(level=0, one=one, recompute=False, freeze=freeze)
                metrics = compute_metrics(ins, one=one, save=True)

        # merge the two dataframes
        df['original_index'] = df.index
        df = df.merge(metrics, on=['pid', 'region', 'subject', 'eid', 'probe', 'date', 'lab'])

    # Region Level
    # no. of channels per region
    df['region_hit'] = df['n_channels'] > min_channels_region
    # no. of neurons per region
    df['low_neurons'] = df['neuron_yield'] < min_neuron_region

    # PID level
    df = df.groupby('pid').apply(lambda m: m.assign(high_noise=lambda m: m['rms_ap_p90'].median() > max_ap_rms))
    df = df.groupby('pid').apply(lambda m: m.assign(high_lfp=lambda m: m['lfp_power_raw'].median() > max_lfp_power))
    df = df.groupby('pid').apply(lambda m: m.assign(low_yield=lambda m: (m['neuron_yield'].sum() / m['n_channels'].sum())
                                                    < min_neurons_per_channel))
    df = df.groupby('pid', group_keys=False).apply(lambda m: m.assign(missed_target=lambda m: m['region_hit'].sum() < min_regions))
    df = df.groupby('pid', group_keys=False).apply(lambda m: m.assign(low_trials=lambda m: m['n_trials'] < n_trials))

    sum_metrics = df['high_noise'] + df['high_lfp'] + df['low_yield'] + df['missed_target'] + df['low_trials'] + df['low_neurons']
    # if by_anatomy_only:
    #     sum_metrics = df['missed_target'] # by_anatomy_only exclusion criteria applied
    if behavior:
        sum_metrics += ~df['behavior']

    df['include'] = sum_metrics == 0

    # Exclude subjects indicated to exclude from further analysis
    df['artifacts'] = bool(0)
    for subj in exclude_subjects:
        idx = df.loc[(df['subject'] == subj)].index
        df.loc[idx, 'include'] = False
        df.loc[idx, 'artifacts'] = True

    df['lab_include'] = bool(0)
    df['permute_include'] = bool(0)

    # For permutation tests
    df_red = df[df['include'] == 1]

    # Have minimum number of recordings per lab
    inst_count = df_red.groupby(['institute']).pid.nunique()
    institutes = [key for key, val in inst_count.items() if val >= min_rec_lab]

    for lab in institutes:
        idx = df.loc[(df['institute'] == lab) & df['include'] == 1].index
        df.loc[idx, 'lab_include'] = True

    # Now for permutation test
    df_red = df_red[df_red['institute'].isin(institutes)]

    # Minimum number of recordings per lab per region with enough good units
    labreg = {val: {reg: 0 for reg in df.region.unique()} for val in institutes}
    df_red = df_red.groupby(['institute', 'pid', 'region'])
    for key in df_red.groups.keys():
        df_k = df_red.get_group(key)
        # needs to be based on the neuron_yield
        if df_k.iloc[0]['neuron_yield'] >= min_neuron_region:
            labreg[key[0]][key[2]] += 1

    for lab, regs in labreg.items():
        for reg, count in regs.items():
            if count >= min_lab_region:
                idx = df.loc[(df['region'] == reg) & (df['institute'] == lab) & df['include'] == 1].index
                df.loc[idx, 'permute_include'] = True

    # Sort the index so it is the same as the orignal frame that was passed in
    df = df.sort_values('original_index').reset_index(drop=True)

    return df


def repo_path():
    """
    Return path of repo
    :return:
    """
    return Path(__file__).parent.resolve()


def save_dataset_info(one, figure):

    uuid_path = save_data_path(figure=figure).joinpath('one_uuids')
    uuid_path.mkdir(exist_ok=True, parents=True)

    _, filename = one.save_loaded_ids(clear_list=False)
    if filename:
        shutil.move(filename, uuid_path.joinpath(f'{figure}_dataset_uuids.csv'))

    # Save the session IDs
    _, filename = one.save_loaded_ids(sessions_only=True)
    if filename:
        shutil.move(filename, uuid_path.joinpath(f'{figure}_session_uuids.csv'))


def compute_lfp_insertion(one, pid, recompute=False):
    """
    From a PID, downloads several snippets of raw data, apply destriping, and output the PSD per channel
    in the theta and LFP bands in a dataframe
    :param one:
    :param pid:
    :param recompute:
    :return:
    """
    pid_directory = save_data_path().joinpath('lfp_destripe_snippets').joinpath(pid)
    saved_file = save_data_path().joinpath('lfp_destripe_snippets').joinpath(f"lfp_{pid}.pqt")
    if recompute is False and saved_file.exists():
        return pd.read_parquet(saved_file)
    try:
        lfp_destripe(pid, one=one, typ='lf', prefix="", destination=pid_directory, remove_cached=True, clobber=False)
        # then we loop over the snippets and compute the RMS of each
        lfp_files = list(pid_directory.rglob('lf.npy'))
        for j, lfp_file in enumerate(lfp_files):
            lfp = np.load(lfp_file).astype(np.float32)
            f, pow = scipy.signal.periodogram(lfp, fs=250, scaling='density')
            if j == 0:
                rms_lf_band, rms_lf, rms_theta_band = (np.zeros((lfp.shape[0], len(lfp_files))) for i in range(3))
            rms_lf_band[:, j] = np.nanmean(
                10 * np.log10(pow[:, np.logical_and(f >= LFP_BAND[0], f <= LFP_BAND[1])]), axis=-1)
            rms_theta_band[:, j] = np.nanmean(
                10 * np.log10(pow[:, np.logical_and(f >= THETA_BAND[0], f <= THETA_BAND[1])]), axis=-1)
            rms_lf[:, j] = np.mean(np.sqrt(lfp.astype(np.double) ** 2), axis=-1)
        lfp_power = np.nanmedian(rms_lf_band - 20 * np.log10(f[1]), axis=-1) * 2
        lfp_theta = np.nanmedian(rms_theta_band - 20 * np.log10(f[1]), axis=-1) * 2
        df_lfp = pd.DataFrame.from_dict({'lfp_power': lfp_power, 'lfp_theta': lfp_theta})
        df_lfp.to_parquet(saved_file)
    except Exception:
        print(f'pid: {pid} RAW LFP ERROR \n', traceback.format_exc())
        lfp_power = np.nan
        lfp_theta = np.nan
        df_lfp = pd.DataFrame.from_dict({'lfp_power': lfp_power, 'lfp_theta': lfp_theta})
    return df_lfp


def lfp_destripe(pid, one=None, typ='ap', prefix="", destination=None, remove_cached=True, clobber=False):
    """
    Stream chunks of data from a given probe insertion

    Output folder architecture (the UUID is the probe insertion UUID):
        f4bd76a6-66c9-41f3-9311-6962315f8fc8
        ├── T00500
        │   ├── ap.npy
        │   ├── ap.yml
        │   ├── lf.npy
        │   ├── lf.yml
        │   ├── spikes.pqt
        │   └── waveforms.npy

    :param pid:
    :param one:
    :param typ:
    :param prefix:
    :param destination:
    :return:
    """
    assert one
    assert destination
    eid, pname = one.pid2eid(pid)

    butter_kwargs = {'N': 3, 'Wn': 300 / 30000 * 2, 'btype': 'highpass'}
    sos = scipy.signal.butter(**butter_kwargs, output='sos')

    if typ == 'ap':
        sample_duration, sample_spacings, skip_start_end = (10 * 30_000, 1_000 * 30_000, 500 * 30_000)
    elif typ == 'lf':
        sample_duration, sample_spacings, skip_start_end = (20 * 2_500, 1_000 * 2_500, 500 * 2_500)
    sr = Streamer(pid=pid, one=one, remove_cached=remove_cached, typ=typ)
    chunk_size = sr.chunks['chunk_bounds'][1]
    nsamples = np.ceil((sr.shape[0] - sample_duration - skip_start_end * 2) / sample_spacings)
    t0_samples = np.round((np.arange(nsamples) * sample_spacings + skip_start_end) / chunk_size) * chunk_size

    for s0 in t0_samples:
        t0 = int(s0 / chunk_size)
        file_destripe = destination.joinpath(f"T{t0:05d}", f"{typ}.npy")
        file_yaml = file_destripe.with_suffix('.yml')
        if file_destripe.exists() and clobber is False:
            continue
        tsel = slice(int(s0), int(s0) + int(sample_duration))
        raw = sr[tsel, :-sr.nsync].T
        if typ == 'ap':
            destripe = voltage.destripe(raw, fs=sr.fs, neuropixel_version=1, channel_labels=True)
            # saves a 0.05 secs snippet of the butterworth filtered data at 0.5sec offset for QC purposes
            butt = scipy.signal.sosfiltfilt(sos, raw)[:, int(sr.fs * 0.5):int(sr.fs * 0.55)]
            fs_out = sr.fs
        elif typ == 'lf':
            destripe = voltage.destripe_lfp(raw, fs=sr.fs, neuropixel_version=1, channel_labels=True)
            destripe = scipy.signal.decimate(destripe, LFP_RESAMPLE_FACTOR, axis=1, ftype='fir')
            fs_out = sr.fs / LFP_RESAMPLE_FACTOR
        file_destripe.parent.mkdir(exist_ok=True, parents=True)
        np.save(file_destripe, destripe.astype(np.float16))
        with open(file_yaml, 'w+') as fp:
            yaml.dump(dict(fs=fs_out, eid=eid, pid=pid, pname=pname, nc=raw.shape[0], dtype="float16"), fp)
        if typ == 'ap':
            np.save(file_destripe.parent.joinpath('raw.npy'), butt.astype(np.float16))