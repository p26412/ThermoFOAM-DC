# v0.2 parameter-study cases

This folder contains the ten v0.2 OpenFOAM parameter-study case setups.

To regenerate these cases from the baseline:

```bash
python3 ../../scripts/create_parameter_cases_v02_10cases.py \
  ../01_baseline_RNGkEpsilon \
  . \
  --overwrite
```

To run all cases:

```bash
for case in C*/; do
    echo "Running $case"
    ( cd "$case" && ./Allclean && ./Allrun )
done
```

Raw time folders and solver logs are intentionally ignored by `.gitignore`.
