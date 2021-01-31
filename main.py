import numpy as np
import pandas as pd
import spacy
from typing import List
from spacy.tokens import Token, Doc
from pyitlib import discrete_random_variable as drv
from scipy import sparse
from scipy.sparse.linalg import svds
from sklearn.metrics.cluster import adjusted_mutual_info_score
from sklearn.preprocessing import quantile_transform
from sortedcontainers import SortedSet
from tabulate import tabulate
import shutil

from abstractfirst.binned import make_age_bin2data, adjust_binned_data
from abstractfirst.co_occurrence import collect_left_and_right_co_occurrences, make_sparse_co_occurrence_mat
from abstractfirst.figs import plot_heatmap
from abstractfirst.memory import set_memory_limit
from abstractfirst.util import to_pyitlib_format, load_words, cluster
from abstractfirst import configs

set_memory_limit(0.9)

nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])

# ///////////////////////////////////////////////////////////////// parameters

CORPUS_NAME = 'childes-20201026'
AGE_STEP = 900
NUM_TOKENS_PER_BIN = 100_000   # TODO 2_527_000  # 2.5M is good with AGE_STEP=900
MAX_SUM = 300_000  # or None
ALLOWED_TARGETS = 'sem-all'

LEFT_ONLY = False
RIGHT_ONLY = True

PLOT_RECONSTRUCTION = True

# ///////////////////////////////////////////////////////////////// separate data by age

print('Raw age bins:')
age_bin2text_unadjusted = make_age_bin2data(CORPUS_NAME, AGE_STEP)
for age_bin, txt in age_bin2text_unadjusted.items():
    print(f'age bin={age_bin:>4} num tokens={len(txt.split()):,}')

print('Adjusted age bins:')
age_bin2text = adjust_binned_data(age_bin2text_unadjusted, NUM_TOKENS_PER_BIN)
for age_bin, txt in sorted(age_bin2text.items(), key=lambda i: i[0]):
    num_tokens_adjusted = len(txt.split())
    print(f'age bin={age_bin:>4} num tokens={num_tokens_adjusted :,}')
    assert num_tokens_adjusted >= NUM_TOKENS_PER_BIN

print(f'Number of age bins={len(age_bin2text)}')

# ///////////////////////////////////////////////////////////////// targets

targets_allowed = SortedSet(load_words(ALLOWED_TARGETS))

# ///////////////////////////////////////////////////////////////// init data collection

NXY = 'nxy'
NYX = 'nyx'
NMI = 'nmi'
AMI = 'ami'
_JE = ' je'
S1MS2U = 's1-s2'
S1MS2N = 's1-s2 / s1+s2'
S1DSR_ = 's1 / sum(s)'

var_names = [NXY, NYX, NMI, AMI, _JE, S1MS2U, S1MS2N, S1DSR_]

name2col = {n: [] for n in var_names}

# ///////////////////////////////////////////////////////////////// data collection

for age_bin, text in sorted(age_bin2text.items(), key=lambda i: i[0]):
    print()
    print(f'age bin={age_bin}')

    print('Tagging...')
    nlp.max_length = len(text)
    doc: Doc = nlp(text)  # todo use pipe() and input docs with doc boundaries intact
    print(f'Found {len(doc):,} tokens in text')

    # get co-occurrence data
    co_data = collect_left_and_right_co_occurrences(doc,
                                                    targets_allowed,
                                                    left_only=LEFT_ONLY,
                                                    right_only=RIGHT_ONLY,
                                                    )
    co_mat_coo: sparse.coo_matrix = make_sparse_co_occurrence_mat(*co_data, max_sum=MAX_SUM)

    # make less skewed
    co_mat_csr: sparse.csr_matrix = quantile_transform(co_mat_coo,
                                                       axis=1,
                                                       output_distribution='normal',
                                                       n_quantiles=co_mat_coo.shape[0],
                                                       copy=True,
                                                       ignore_implicit_zeros=True)
    co_mat_dense = co_mat_csr.toarray()

    # factor analysis
    print('Factor analysis...')
    # don't use sparse svd: doesn't result in accurate reconstruction
    U, s, VT = np.linalg.svd(co_mat_dense, compute_uv=True)
    assert np.max(s) == s[0]
    with np.printoptions(precision=2, suppress=True):
        print(s[:4])
    name2col[S1MS2U].append(s[0] - s[1])
    name2col[S1MS2N].append((s[0] - s[1]) / (s[0] + s[1]))
    name2col[S1DSR_].append(s[0] / np.sum(s))

    # info theory analysis
    print('Info theory analysis...')
    xs, ys = to_pyitlib_format(co_mat_coo)  # todo also get zs + calc interaction info
    xy = np.vstack((xs, ys))
    je = drv.entropy_joint(xy)
    name2col[NXY].append(drv.entropy_conditional(xs, ys).item() / je)
    name2col[NYX].append(drv.entropy_conditional(ys, xs).item() / je)
    name2col[NMI].append(drv.information_mutual_normalised(xs, ys, norm_factor='XY').item())
    name2col[AMI].append(adjusted_mutual_info_score(xs, ys, average_method="arithmetic"))
    name2col[_JE].append(je)

    if PLOT_RECONSTRUCTION:
        shutil.rmtree(configs.Dirs.images)
        configs.Dirs.images.mkdir()
        # plot projection of co_mat onto sing dims
        dg0, dg1 = None, None
        projections = np.zeros(co_mat_csr.shape, dtype=np.float)
        num_s = sum(s > 0)
        for dim_id in range(num_s):
            projection = s[dim_id] * U[:, dim_id].reshape(-1, 1) @ VT[dim_id, :].reshape(1, -1)
            projection_clustered, dg0, dg1 = cluster(projection, dg0, dg1)
            projections += projection_clustered
            if dim_id % 50 == 0:
                plot_heatmap(projections,
                             title=f'sing dim={dim_id}/{num_s}',
                             save_name=f'co_mat_projections_up_to_dim{dim_id}',
                             vmin=np.min(co_mat_csr),
                             vmax=np.max(co_mat_csr),
                             )

        plot_heatmap(cluster(co_mat_dense, dg0, dg1)[0],
                     title=f'original',
                     vmin=np.min(co_mat_csr),
                     vmax=np.max(co_mat_csr),
                     )
        raise SystemExit
# ///////////////////////////////////////////////////////////////// show data

df = pd.DataFrame(data=name2col, columns=var_names, index=age_bin2text.keys())
print(tabulate(df,
               headers=['age_onset (days)'] + var_names,
               tablefmt='simple'))
