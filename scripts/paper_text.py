"""Enlarge a figure's text for the paper.

The figures are drawn 7.5 in wide (15 in for the three-panel ones) and set at column (text) width,
about 0.43 of that, so 9 pt text prints at about 4 pt. Scaling every text by TEXT_SCALE brings it to
about 7 pt. The baked-in "Figure N." title is left alone: the paper trims it off by a fixed fraction
of the height (\\resultfig in main/main.tex), which a larger title would break.
"""

from matplotlib.text import Text

TEXT_SCALE = 1.7


def enlarge_text(fig, k: float = TEXT_SCALE, keep=()) -> None:
    """keep: further texts to leave alone, e.g. a trimmed title that does not start with "Figure "."""
    keep = set(map(id, keep))
    ticks = set()
    for ax in fig.axes:
        for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            ticks.update(map(id, axis.get_ticklabels(which="both")))
            major = axis.get_major_ticks()
            if major:
                ax.tick_params(axis=name, which="both", labelsize=major[0].label1.get_fontsize() * k)
    for t in fig.findobj(Text):
        if id(t) not in ticks | keep and not t.get_text().startswith("Figure "):
            t.set_fontsize(t.get_fontsize() * k)
