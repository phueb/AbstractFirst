"""
Research questions:
1. How well does noun-context selectivity correlate with semantic complexity?

A caveat:
The context-selectivity measure is extremely sensitive to the number of tokens.
THis means that comparing selectivity at age bins,
 care must be taken to sample an equal number of words at each bin

"""
import spacy
import matplotlib.pyplot as plt

from categoryeval.probestore import ProbeStore

from wordplay.binned import make_age_bin2tokens
from wordplay.representation import make_context_by_term_matrix
from wordplay.measures import calc_selectivity
from wordplay.sentences import get_sentences_from_tokens
from wordplay.utils import plot_best_fit_line
from wordplay.svo import subject_verb_object_triples

# ///////////////////////////////////////////////////////////////// parameters

CORPUS_NAME = 'childes-20191112'
PROBES_NAME = 'syn-4096'
AGE_STEP = 100
CONTEXT_SIZE = 3
NUM_TOKENS_PER_BIN = 50 * 1000  # 100K is good with AGE_STEP=100
POS = 'VERB'

# ///////////////////////////////////////////////////////////////// combine docs by age

age_bin2word_tokens = make_age_bin2tokens(CORPUS_NAME, AGE_STEP)
age_bin2tag_tokens = make_age_bin2tokens(CORPUS_NAME, AGE_STEP, suffix='_tags')

for word_tokens in age_bin2word_tokens.values():  # this is used to determine maximal NUM_TOKENS_PER_BIN
    print(f'{len(word_tokens):,}')

# /////////////////////////////////////////////////////////////////

nlp = spacy.load("en_core_web_sm", disable=['ner'])

x = []
y = []
age_bins = []
for age_bin in age_bin2tag_tokens.keys():

    word_tokens = age_bin2word_tokens[age_bin]
    tag_tokens = age_bin2tag_tokens[age_bin]

    assert len(word_tokens) == len(tag_tokens)
    assert word_tokens != tag_tokens

    # pos_words
    w2id = {w: n for n, w in enumerate(set(word_tokens))}
    probe_store = ProbeStore('childes-20180319', PROBES_NAME, w2id)
    pos_words = probe_store.cat2probes[POS]
    print(len(pos_words))

    # get same number of tokens at each bin
    if len(word_tokens) < NUM_TOKENS_PER_BIN:
        print(f'WARNING: Number of tokens at age_bin={age_bin} < NUM_TOKENS_PER_BIN')
        continue
    else:
        word_tokens = word_tokens[:NUM_TOKENS_PER_BIN]

    # compute num SVO triples as measure of semantic complexity
    sentences = get_sentences_from_tokens(word_tokens, punctuation={'.', '!', '?'})
    texts = [' '.join(s) for s in sentences]
    unique_triples = set()
    for doc in nlp.pipe(texts):
        for t in subject_verb_object_triples(doc):  # only returns triples, not partial triples
            unique_triples.add(t)
    num_unique_triples_in_part = len(unique_triples)
    comp = num_unique_triples_in_part

    # co-occurrence matrix
    tw_mat_observed, xws_observed, _ = make_context_by_term_matrix(word_tokens,
                                                                   context_size=CONTEXT_SIZE,
                                                                   shuffle_tokens=False)
    tw_mat_chance, xws_chance, _ = make_context_by_term_matrix(word_tokens,
                                                               context_size=CONTEXT_SIZE,
                                                               shuffle_tokens=True)

    # calc selectivity of noun contexts
    cttr_chance, cttr_observed, sel = calc_selectivity(tw_mat_chance,
                                                       tw_mat_observed,
                                                       xws_chance,
                                                       xws_observed,
                                                       pos_words)
    print(f'age_bin={age_bin} selectivity={sel} semantic-complexity={comp}')
    print()

    # collect
    x.append(comp)
    y.append(sel)
    age_bins.append(age_bin)

# figure
fig, ax = plt.subplots(1, figsize=(7, 7), dpi=192)
ax.set_xlabel('Semantic Complexity', fontsize=14)
ax.set_ylabel(f'{POS}-Context Selectivity\n(context-size={CONTEXT_SIZE})', fontsize=14)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.tick_params(axis='both', which='both', top=False, right=False)
# plot
ax.scatter(x, y, color='black')
plot_best_fit_line(ax, x, y, fontsize=12, x_pos=0.75, y_pos=0.75)
for xi, yi, age_bin in zip(x, y, age_bins):
    s = f'days=\n{age_bin}-{age_bin + AGE_STEP}'
    ax.text(xi + 10, yi, s, fontsize=10)

plt.tight_layout()
plt.show()