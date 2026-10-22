"""Estimate the smallest readable text in a figure at its printed width (FIG_TEXT_SIZE heuristic).

Finds glyph-sized connected ink components (dark on light and light on dark), takes the smallest height shared by at
least 8 glyphs and a quarter of the busiest height (so i-dots and punctuation don't count), treats it as the x-height (0.5 em; typical sans-serif text faces measure 0.47-0.55) and converts it to points at the printed width. Needs Pillow and
NumPy only. Accuracy is about +/-15% for 6-12 pt text; very small text fragments and reads smaller, so it warns early. Returns None when it can't tell (too few glyphs, or a missing library), which callers report, never pass.
"""
import numpy as np


def _components(mask):
    """Heights and widths of 4-connected ink components, via row runs and union-find (no SciPy)."""
    parent = []
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    runs_prev, boxes = [], []
    for y in range(mask.shape[0]):
        row = mask[y]
        if not row.any():
            runs_prev = []; continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur = []
        j = 0
        for s, e in zip(starts.tolist(), ends.tolist()):
            lab = len(parent); parent.append(lab); boxes.append([y, y, s, e])
            while j < len(runs_prev) and runs_prev[j][1] <= s:
                j += 1
            k = j
            while k < len(runs_prev) and runs_prev[k][0] < e:
                a, b = find(lab), find(runs_prev[k][2])
                if a != b:
                    parent[b] = a
                    ba, bb = boxes[a], boxes[b]
                    boxes[a] = [min(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), max(ba[3], bb[3])]
                k += 1
            cur.append((s, e, lab))
        runs_prev = cur
    out = {}
    for i in range(len(parent)):
        r = find(i); b = boxes[i]
        o = out.setdefault(r, list(b))
        out[r] = [min(o[0], b[0]), max(o[1], b[1]), min(o[2], b[2]), max(o[3], b[3])]
    return [(b[1] - b[0] + 1, b[3] - b[2]) for b in out.values()]


def min_text_pt(path, printed_width_in, max_side=2400):
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as im:
        g = im.convert("L")
        w0 = g.size[0]
        if max(g.size) > max_side:
            f = max_side / float(max(g.size)); g = g.resize((int(g.size[0] * f), int(g.size[1] * f)))
        scale = g.size[0] / float(w0)
        a = np.asarray(g, dtype=np.int16)
    pt_per_px = printed_width_in * 72.0 / (w0 * scale)
    heights = []
    for mask in (a < 170, a > 150):
        if mask.mean() > 0.6:
            continue
        for h, w in _components(mask):
            if 4 <= h <= 80 and 2 <= w <= 2.2 * h + 2:
                heights.append(h)
    if len(heights) < 8:
        return None
    hs = np.array(heights)
    counts = {h: int(((hs >= h) & (hs <= h + 1)).sum()) for h in range(4, 81)}
    need = max(8, 0.25 * max(counts.values()))
    for h in range(4, 81):
        if counts[h] >= need:
            return round(h * pt_per_px / 0.5, 1)
    return None
