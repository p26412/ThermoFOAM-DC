# Optional `residualControl` snippets for OpenFOAM-dev

Do not paste the old `tolerance/relTol` dictionary style inside `PIMPLE.residualControl`.
Your OpenFOAM-dev build expects single scalar values.

For `kEpsilon`:

```cpp
PIMPLE
{
    nOuterCorrectors         1;
    nCorrectors              2;
    nNonOrthogonalCorrectors 1;
    momentumPredictor        no;

    residualControl
    {
        p_rgh     1e-4;
        U         1e-4;
        T         1e-6;
        k         1e-5;
        epsilon   1e-5;
    }
}
```

For `kOmegaSST`:

```cpp
PIMPLE
{
    nOuterCorrectors         1;
    nCorrectors              2;
    nNonOrthogonalCorrectors 1;
    momentumPredictor        no;

    residualControl
    {
        p_rgh     1e-4;
        U         1e-4;
        T         1e-6;
        k         1e-5;
        omega     1e-5;
    }
}
```

For publication, residuals alone are not enough. Use `dcMetricsPlus` to monitor physical quantities between late checkpoints.
