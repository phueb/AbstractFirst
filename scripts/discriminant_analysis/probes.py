"""
Research questions:
1. How discriminative of semantic categories are probe contexts in partition 1 vs. partition 2?
"""

import attr
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

from preppy.legacy import TrainPrep
from categoryeval.probestore import ProbeStore

from wordplay import config
from wordplay.word_sets import excluded
from wordplay.params import PrepParams
from wordplay.docs import load_docs
from wordplay.representation import make_context_by_term_matrix
from wordplay.memory import set_memory_limit

# /////////////////////////////////////////////////////////////////

CORPUS_NAME = 'childes-20180319'
PROBES_NAME = 'sem-all'

docs = load_docs(CORPUS_NAME)

params = PrepParams()
prep = TrainPrep(docs, **attr.asdict(params))

probe_store = ProbeStore(CORPUS_NAME, PROBES_NAME, prep.store.w2id, excluded=excluded)

# /////////////////////////////////////////////////////////////////

CONTEXT_SIZE = 3
NORMALIZE = False  # this makes all the difference - this means that the scales of variables are different and matter


OFFSET = prep.midpoint

# ///////////////////////////////////////////////////////////////// TW matrix

# make term_by_window_co_occurrence_mats
start1, end1 = 0, OFFSET
start2, end2 = prep.store.num_tokens - OFFSET, prep.store.num_tokens
tw_mat1, xws1, yws1 = make_context_by_term_matrix(
    prep.store.tokens, start=start1, end=end1, context_size=CONTEXT_SIZE, probe_store=probe_store)
tw_mat2, xws2, yws2 = make_context_by_term_matrix(
    prep.store.tokens, start=start2, end=end2, context_size=CONTEXT_SIZE, probe_store=probe_store)

# ///////////////////////////////////////////////////////////////// LDA

set_memory_limit(prop=1.0)

# use only features common to both
common_yws = set(yws1).intersection(set(yws2))
print(f'Number of common contexts={len(common_yws)}')
x1 = tw_mat1.T[:, [n for n, yw in enumerate(yws1) if yw in common_yws]].toarray()
x2 = tw_mat2.T[:, [n for n, yw in enumerate(yws2) if yw in common_yws]].toarray()
y1 = [probe_store.cat2id[probe_store.probe2cat[p]] for p in xws1]
y2 = [probe_store.cat2id[probe_store.probe2cat[p]] for p in xws2]

for x, y in zip([x1, x2],
                [y1, y2]):

    print(f'Number of probes included in LDA={len(y)}')
    clf = LinearDiscriminantAnalysis(n_components=None, priors=None, shrinkage=None,
                                     solver='svd', store_covariance=False)
    try:
        clf.fit(x, y)

    except MemoryError as e:
        raise SystemExit('Reached memory limit')

    # how well does discriminant function work for other part?
    score1 = clf.score(x1, y1)
    score2 = clf.score(x2, y2)
    print(f'partition-1 accuracy={score1:.3f}')
    print(f'partition-2 accuracy={score2:.3f}')

