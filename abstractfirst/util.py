from typing import Tuple, Optional, List, Set
from scipy.cluster.hierarchy import linkage, dendrogram

import numpy as np
from scipy import sparse

from abstractfirst import configs


def split(l, split_size):
    for i in range(0, len(l), split_size):
        yield l[i:i + split_size]


def load_words(file_name: str
               ) -> Set[str]:
    p = configs.Dirs.words / f'{file_name}.txt'
    res = p.read_text().split('\n')
    return set(res)


def to_pyitlib_format(co_mat: sparse.coo_matrix,
                      remove_ones: bool,
                      ) -> Tuple[List[int], List[int]]:
    """
    convert data in co-occurrence matrix to two lists, each with realisations of one discrete RV.
    """
    xs = []
    ys = []
    new_sum = 0
    for i, j, v in zip(co_mat.row, co_mat.col, co_mat.data):
        if v > int(remove_ones):
            xs += [i] * v
            ys += [j] * v

            new_sum += v

    if remove_ones:
        print(f'WARNING: Excluded co-occurrences with frequency=1')

    print(f'Number of co-occurrences considered for further analysis={new_sum:,}')

    return xs, ys


def cluster(mat: np.ndarray,
            cluster_rows: bool = True,
            cluster_cols: bool = False,
            method: str = 'complete',
            metric: str = 'cityblock'):

    if cluster_rows:
        lnk0 = linkage(mat, method=method, metric=metric)
        dg0 = dendrogram(lnk0,
                         ax=None,
                         color_threshold=None,
                         no_labels=True,
                         no_plot=True)
        res = mat[dg0['leaves'], :]  # reorder rows
    else:
        res = mat

    if cluster_cols:
        lnk1 = linkage(mat.T, method=method, metric=metric)
        dg1 = dendrogram(lnk1,
                         ax=None,
                         color_threshold=None,
                         no_labels=True,
                         no_plot=True)
        res = res[:, dg1['leaves']]  # reorder cols

    return res