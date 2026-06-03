# y+ verification

The simulations use wall-function RANS turbulence modelling, so the near-wall y+ range must be checked.

The RNG k-epsilon y+ values were computed using:

```bash
foamPostProcess -solver fluid -func yPlus -latestTime
```

Then the percentage of wall faces below y+ = 30 was computed using:

```bash
python3 scripts/yplus_fraction.py 8000/yPlus 30
```

## RNG k-epsilon y+ summary

See:

```text
results/tables/yplus_uniform_RNGkEpsilon.csv
results/tables/yplus_fraction_grid14_uniform_RNGkEpsilon.csv
```

For the fine grid, only 8 out of 26,763 wall faces were below y+ = 30, corresponding to 0.0299% of wall faces.

| Patch | Faces | Faces with y+ < 30 | Percent below 30 | Min y+ | Avg y+ | Max y+ |
|---|---:|---:|---:|---:|---:|---:|
| floor | 6526 | 0 | 0.0000% | 32.1298 | 91.7744 | 160.0916 |
| ceiling | 6209 | 2 | 0.0322% | 27.4215 | 116.0299 | 183.3349 |
| walls | 14028 | 6 | 0.0428% | 27.4215 | 89.9197 | 266.7922 |
| total | 26763 | 8 | 0.0299% | - | - | - |

## Conclusion

The fine grid maintains an acceptable wall-function y+ distribution. The local y+ values below 30 are negligible in area/face-count fraction. Therefore, grid_14 is retained as the fine-grid reference, while grid_10 remains the practical production mesh candidate.
