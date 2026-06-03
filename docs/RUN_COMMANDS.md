# Run commands

## Compile post-processing utility

```bash
cd src/dcMetricsPlus
wmake
cd ../..
```

## Run primary RNG baseline

```bash
cd cases/01_baseline_RNGkEpsilon
./Allclean
./Allrun
```

## Run metrics

```bash
dcMetricsPlus
```

This writes metrics for all available time folders under:

```text
postProcessing/dcMetricsPlus/
```

## Run y+ check

```bash
foamPostProcess -solver fluid -func yPlus -latestTime
python3 ../../scripts/yplus_fraction.py 8000/yPlus 30
```

## Create v0.2 parameter cases

From repository root:

```bash
python3 scripts/create_parameter_cases.py \
    cases/01_baseline_RNGkEpsilon \
    parameterStudy_RNG \
    --include-optional
```

## Collect metrics

```bash
python3 scripts/collect_metrics_plus.py \
    parameterStudy_RNG/C00_baseline \
    parameterStudy_RNG/C01_lowSupplyVelocity \
    parameterStudy_RNG/C02_highSupplyVelocity \
    parameterStudy_RNG/C03_warmerSupplyAir \
    parameterStudy_RNG/C04_highRackLoad \
    parameterStudy_RNG/C05_overloadedRack_L2 \
    --output results/tables/v02_parameter_metrics_raw.csv
```

For v0.2, compute late averages from 4000-8000 before making design conclusions.
