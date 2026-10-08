"""Plot clean dataset metadata without modifying source metadata or images.
Requires numpy and matplotlib. Run in the container's EDA virtual environment.
"""
import argparse
import csv
import hashlib
import html
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RANGES = [(0, 10)] + [(i, i + 9) for i in range(11, 100, 10)]
LABELS = [f'{lo}–{hi}%' for lo, hi in RANGES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, default=ROOT / 'extracted/crusher_dataset_v3/master_metadata_clean.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/v3_eda')
    parser.add_argument('--target', type=int, default=1000)
    args = parser.parse_args()
    if args.target <= 0:
        raise ValueError('Target must be positive')
    source = args.metadata.read_bytes()
    with args.metadata.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('The clean manifest is empty')
    values = np.array([float(r['fill_level']) for r in rows])
    if not np.all(np.isfinite(values) & (values >= 0) & (values <= 100)):
        raise ValueError('Fill labels must be finite values between 0 and 100')
    if not np.all(values == np.floor(values)):
        raise ValueError('These established inclusive ranges require integer labels; fractional labels need explicit range boundaries')
    ids = [int(r['recording_id']) for r in rows]
    recordings = sorted(set(ids))
    counts = np.array([np.count_nonzero((values >= lo) & (values <= hi)) for lo, hi in RANGES])
    gaps = np.maximum(args.target - counts, 0)
    exact = np.bincount(values.astype(int), minlength=101)
    matrix = np.array([[sum(1 for rid, value in zip(ids, values) if rid == rec and lo <= value <= hi) for lo, hi in RANGES] for rec in recordings])
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.titleweight': 'bold', 'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'pdf.fonttype': 42})
    subtitle = f'{len(rows):,} clean pairs · {len(recordings)} recordings · each pair = narrow + wide'
    figures = []

    def save(fig, stem, title, caption):
        for ext in ('png', 'pdf'):
            fig.savefig(args.output / f'{stem}.{ext}', dpi=180, bbox_inches='tight')
        plt.close(fig)
        figures.append((stem, title, caption))

    fig, ax = plt.subplots(figsize=(13, 6.5))
    x = np.arange(10)
    ax.bar(x, counts, color='#177d88', label='Clean pairs available', width=.7)
    ax.bar(x, gaps, bottom=counts, color='#e4e9ed', label='Additional pairs needed', width=.7)
    ax.axhline(args.target, color='#b65729', linestyle='--', linewidth=1.8, label=f'Target: {args.target:,} per range')
    for i, (n, gap) in enumerate(zip(counts, gaps)):
        ax.text(i, n/2, f'{n:,}', ha='center', va='center', color='white', weight='bold')
        if gap:
            ax.text(i, n+gap/2, f'+{gap:,}', ha='center', va='center', color='#39434c', fontsize=10)
    ax.set(xticks=x, xticklabels=LABELS, xlabel='Ground-truth fill range', ylabel='Number of paired samples', ylim=(0, max(args.target, counts.max())*1.1))
    ax.set_title('Fill coverage against the collection target', loc='left', pad=43, fontsize=18)
    ax.text(0, 1.045, subtitle, transform=ax.transAxes, color='#56616b')
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.17), ncol=3, frameon=False)
    ax.set_axisbelow(True)
    ax.grid(axis='y', alpha=.17)
    fig.tight_layout()
    save(fig, '01_fill_range_targets', 'Fill coverage and collection gaps', 'Colored bars count approved pairs; pale segments show additional pairs needed to reach the target. These ranges summarize collection coverage, not model classes.')

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(np.arange(101), exact, color='#177d88', width=.85)
    ax.set(xlim=(-1, 101), xticks=np.arange(0, 101, 5), xlabel='Exact ground-truth fill level (%)', ylabel='Number of paired samples')
    ax.set_title('Sample counts at each exact fill level', loc='left', pad=40, fontsize=18)
    ax.text(0, 1.05, subtitle, transform=ax.transAxes, color='#56616b')
    ax.set_axisbelow(True)
    ax.grid(axis='y', alpha=.17)
    fig.tight_layout()
    save(fig, '02_exact_fill_counts', 'Exact fill-level distribution', 'One bar per integer GT value from 0% to 100%. Repeated labels may come from different measurement timestamps; these counts do not establish visual diversity or statistical independence.')

    fig, ax = plt.subplots(figsize=(13, 15))
    image = ax.imshow(matrix, aspect='auto', cmap='YlGnBu', vmin=0)
    ax.set(xticks=np.arange(10), xticklabels=LABELS, yticks=np.arange(len(recordings)), yticklabels=[f'REC {rec}' for rec in recordings], xlabel='Ground-truth fill range', ylabel='Recording (ordered by ID, not date)')
    for row_idx in range(len(recordings)):
        for col_idx in range(10):
            count = matrix[row_idx, col_idx]
            ax.text(col_idx, row_idx, str(count) if count else '·', ha='center', va='center', fontsize=9, color='white' if count > matrix.max()*.5 else '#263547')
    ax.set_title('Which recordings provide each fill range?', loc='left', pad=43, fontsize=18)
    ax.text(0, 1.025, subtitle, transform=ax.transAxes, color='#56616b')
    fig.colorbar(image, ax=ax, pad=.025, shrink=.65, label='Paired sample count (absolute, not normalized)')
    fig.tight_layout()
    save(fig, '03_recording_fill_heatmap', 'Recording × fill-range heatmap', 'Each cell counts clean pairs from one recording in one fill range; a dot means zero. Colors use absolute counts, so longer recordings can appear darker. Recording IDs do not represent verified sessions or chronological order.')

    checksum = hashlib.sha256(source).hexdigest()
    low = Counter(rec for rec, fill in zip(ids, values) if fill <= 20)
    table = '\n'.join(f'| {label} | {n} | {gap} |' for label, n, gap in zip(LABELS, counts, gaps))
    report = f'''# Clean v3 dataset exploration\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\nSource: `{args.metadata}`\n\nSource SHA-256: `{checksum}`\n\n- Clean paired samples: **{len(rows):,}**\n- Recordings: **{len(recordings)}**\n- Expected image references: **{2*len(rows):,}** (two per row; not an independent image-file count)\n- Additional pairs needed across ranges: **{gaps.sum():,}**\n- Samples at 0–20% fill: **{sum(low.values()):,}** from **{len(low)}** recordings\n\n| Fill range | Current pairs | Needed to reach {args.target:,} |\n|---|---:|---:|\n{table}\n\n## Interpretation limits\n\nCounts describe metadata rows, not independent scenes. No split, synchronization change, QC change, or dataset freeze is performed. Integer labels use the established inclusive ranges 0–10, 11–20, ..., 91–100. Low-fill contributions by recording: {dict(sorted(low.items()))}.\n\n## Recreate\n\nRun `python3 "script v2/plot_clean_dataset_eda.py"` from an environment with NumPy and Matplotlib. Optional arguments: `--metadata PATH --output PATH --target 1000`.\n'''
    (args.output / 'README.md').write_text(report)
    cards = ''.join(f'<section><h2>{html.escape(title)}</h2><p>{html.escape(caption)}</p><a href="{stem}.png"><img src="{stem}.png" alt="{html.escape(title)}"></a><p><a href="{stem}.pdf">Download PDF</a> · <a href="{stem}.png">Open PNG</a></p></section>' for stem, title, caption in figures)
    (args.output / 'index.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V3 dataset exploration</title><style>body{{font:16px/1.6 system-ui,sans-serif;background:#f2f5f7;color:#20313b;max-width:1250px;margin:auto;padding:30px}}section{{background:white;padding:24px;margin:24px 0;border-radius:12px}}img{{width:100%;height:auto}}h1,h2{{line-height:1.2}}a{{color:#126773}}</style><h1>V3 · Clean daylight dataset</h1><p>{html.escape(subtitle)} · Collection target: {args.target:,} per range.</p><p>Exploration only. No dataset changes or split assignments. <a href="README.md">Source and analysis notes</a></p>{cards}</html>')
    print(f'Samples: {len(rows)} | Recordings: {len(recordings)} | Additional needed: {gaps.sum()}')
    print(f'0–20% fill: {sum(low.values())} pairs from {len(low)} recordings: {dict(sorted(low.items()))}')
    print('Counts per range:', counts.tolist())
    print('Saved 3 PNGs, 3 PDFs, index.html and README.md to:', args.output)


if __name__ == '__main__':
    main()
