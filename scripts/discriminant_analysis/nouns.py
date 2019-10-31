"""
Research questions:
1. How discriminative of nouns are contexts in partition 1 vs. partition 2?
"""

import attr
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

from preppy.legacy import TrainPrep

from wordplay.params import PrepParams
from wordplay.docs import load_docs
from wordplay.svd import make_term_by_window_co_occurrence_mat
from wordplay.pos import load_pos_words
from wordplay.memory import set_memory_limit

# /////////////////////////////////////////////////////////////////

CORPUS_NAME = 'childes-20180319'

SHUFFLE_DOCS = False
NUM_MID_TEST_DOCS = 0

docs = load_docs(CORPUS_NAME,
                 num_test_take_from_mid=NUM_MID_TEST_DOCS,
                 num_test_take_random=0,
                 shuffle_docs=SHUFFLE_DOCS)

params = PrepParams()
prep = TrainPrep(docs, **attr.asdict(params))

# /////////////////////////////////////////////////////////////////

WINDOW_SIZE = 2
NORMALIZE = False  # this makes all the difference - this means that the scales of variables are different and matter
MAX_FREQUENCY = 100 * 1000  # largest value in co-occurrence matrix
LOG_FREQUENCY = True  # take log of co-occurrence matrix element-wise

OFFSET = prep.midpoint

# ///////////////////////////////////////////////////////////////// TW matrix

# make term_by_window_co_occurrence_mats
start1, end1 = 0, OFFSET
start2, end2 = prep.store.num_tokens - OFFSET, prep.store.num_tokens
tw_mat1, xws1, yws1 = make_term_by_window_co_occurrence_mat(
    prep, start=start1, end=end1, window_size=WINDOW_SIZE, max_frequency=MAX_FREQUENCY, log=LOG_FREQUENCY)
tw_mat2, xws2, yws2 = make_term_by_window_co_occurrence_mat(
    prep, start=start2, end=end2, window_size=WINDOW_SIZE, max_frequency=MAX_FREQUENCY, log=LOG_FREQUENCY)


# ///////////////////////////////////////////////////////////////// LDA

set_memory_limit(prop=1.5)

nouns = load_pos_words(f'{CORPUS_NAME}-nouns')

# use only features common to both
common_yws = set(yws1).intersection(set(yws2))
print(f'Number of common contexts={len(common_yws)}')
x1 = tw_mat1.T.toarray()[:, [True if yw in common_yws else False for yw in yws1]]
x2 = tw_mat2.T.toarray()[:, [True if yw in common_yws else False for yw in yws2]]
y1 = [1 if w in nouns else 0 for w in xws1]
y2 = [1 if w in nouns else 0 for w in xws2]

for x, y in zip([x1, x2],
                [y1, y2]):

    print(f'Number of words included in LDA={len(y)}')
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
    
