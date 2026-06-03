#!/usr/bin/env python3
"""Calculate percentage of wall-patch yPlus values below a threshold.

Usage:
    python3 scripts/yplus_fraction.py 8000/yPlus 30
"""

import re
import sys
from pathlib import Path


def iter_patch_blocks(text):
    m = re.search(r'\bboundaryField\s*\{', text)
    if not m:
        raise RuntimeError('Could not find boundaryField block')
    i = m.end()
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i < n and text[i] == '}':
            break
        name_match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*\{', text[i:])
        if not name_match:
            i += 1
            continue
        patch_name = name_match.group(1)
        block_start = i + name_match.end()
        depth = 1
        j = block_start
        while j < n and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        yield patch_name, text[block_start:j-1]
        i = j


def extract_nonuniform_values(block):
    m = re.search(r'value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;', block, flags=re.S)
    if not m:
        return None
    declared_count = int(m.group(1))
    values = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', m.group(2))]
    if len(values) != declared_count:
        print(f'WARNING: declared {declared_count}, parsed {len(values)} values', file=sys.stderr)
    return values


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 yplus_fraction.py 8000/yPlus [threshold]')
        sys.exit(1)
    yplus_file = Path(sys.argv[1])
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    text = yplus_file.read_text()
    total_faces = 0
    total_below = 0
    print(f'\nChecking yPlus file: {yplus_file}')
    print(f'Threshold: y+ < {threshold:g}\n')
    print(f"{'patch':<15}{'faces':>10}{'below':>10}{'percent_below':>18}{'min':>12}{'avg':>12}{'max':>12}")
    print('-' * 89)
    for patch_name, block in iter_patch_blocks(text):
        values = extract_nonuniform_values(block)
        if values is None:
            continue
        n_faces = len(values)
        n_below = sum(v < threshold for v in values)
        vmin, vmax = min(values), max(values)
        vavg = sum(values) / n_faces if n_faces else 0.0
        pct = 100.0 * n_below / n_faces if n_faces else 0.0
        total_faces += n_faces
        total_below += n_below
        print(f'{patch_name:<15}{n_faces:>10d}{n_below:>10d}{pct:>17.4f}%{vmin:>12.4f}{vavg:>12.4f}{vmax:>12.4f}')
    print('-' * 89)
    total_pct = 100.0 * total_below / total_faces if total_faces else 0.0
    print(f'{"TOTAL":<15}{total_faces:>10d}{total_below:>10d}{total_pct:>17.4f}%')
    if total_pct < 5:
        print('\nDecision: acceptable for wall-function RANS, if other metrics are stable.')
    elif total_pct < 10:
        print('\nDecision: borderline. Mention it clearly.')
    else:
        print('\nDecision: too much below y+ = 30. Use a coarser/controlled first-cell mesh or redesign.')


if __name__ == '__main__':
    main()
