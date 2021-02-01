from pathlib import Path


class Dirs:
    src = Path(__file__).parent
    root = src.parent
    scripts = root / 'scripts'
    corpora = root / 'corpora'
    words = root / 'words'
    images = root / 'images'


class Fig:
    ax_fontsize = 20
    leg_fontsize = 12
    dpi = 300
    max_projection = 0  # set to 0 to prevent plotting of reconstructions


class Data:
    make_last_bin_larger = True


class Conditions:
    directions = ['r']  # ['l', 'r', 'b']