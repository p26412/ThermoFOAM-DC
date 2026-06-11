#!/usr/bin/env python3
"""
Generate CFD-quality contour/filled-contour plots and line-sample CSV files for
one OpenFOAM case using ParaView Python.

Outputs:
  contours/*.png
    - Ux, Uy, Uz, |U| on x-mid, y-mid, and z-mid slices
    - T, p_rgh, p, k, epsilon, omega, nut when available
    - black isoline overlays are enabled by default
  profiles/*.csv
    - centerline profiles along x, y, and z through the room centre

Run with ParaView Python or with system python if python3-paraview is installed:
  pvpython scripts/cfd_viz/pv_make_velocity_figures_one_case.py CASE_DIR OUT_DIR 8000

Notes:
  Ux = x-direction velocity
  Uy = y-direction velocity
  Uz = z-direction velocity; vertical if your OpenFOAM geometry uses z as vertical
  Umag = |U|
"""

import argparse
import math
import sys
from pathlib import Path

try:
    from paraview.simple import *  # noqa: F401,F403
except Exception as exc:
    print("ERROR: could not import paraview.simple. Run this with pvpython or python3-paraview.")
    print(str(exc))
    sys.exit(2)


# Field names are attempted in order. Missing arrays are skipped cleanly.
FIELD_SPECS = [
    ("Umag", "|U| velocity magnitude [m/s]", "Cool to Warm"),
    ("Ux", "Ux x-direction velocity [m/s]", "Cool to Warm"),
    ("Uy", "Uy y-direction velocity [m/s]", "Cool to Warm"),
    ("Uz", "Uz z-direction velocity [m/s]", "Cool to Warm"),
    ("T", "Temperature [K]", "Cool to Warm"),
    ("p_rgh", "p_rgh [Pa]", "Cool to Warm"),
    ("p", "Pressure p [Pa]", "Cool to Warm"),
    ("k", "Turbulent kinetic energy k [m2/s2]", "Cool to Warm"),
    ("epsilon", "Dissipation rate epsilon [m2/s3]", "Cool to Warm"),
    ("omega", "Specific dissipation rate omega [1/s]", "Cool to Warm"),
    ("nut", "Turbulent viscosity nut [m2/s]", "Cool to Warm"),
    ("alphat", "Turbulent thermal diffusivity alphat [kg/m/s]", "Cool to Warm"),
]

SLICE_SPECS = [
    ("x_mid_vertical_yz", (1.0, 0.0, 0.0), "x-mid vertical Y-Z plane"),
    ("y_mid_vertical_xz", (0.0, 1.0, 0.0), "y-mid vertical X-Z plane"),
    ("z_mid_horizontal_xy", (0.0, 0.0, 1.0), "z-mid horizontal X-Y plane"),
]

OPTIONAL_ARRAYS = [
    "U", "T", "p_rgh", "p", "k", "epsilon", "omega", "nut", "nuTilda",
    "alphat", "rho", "mu", "nu", "Cp", "h", "he", "e",
]


def safe_set(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def find_or_create_foam(case_dir):
    case_dir = Path(case_dir).resolve()
    existing = sorted(case_dir.glob("*.foam"))
    if existing:
        return existing[0]
    foam_file = case_dir / (case_dir.name + ".foam")
    foam_file.write_text("", encoding="utf-8")
    return foam_file


def choose_time(reader, requested_time):
    scene = GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    times = list(getattr(reader, "TimestepValues", []) or [])
    if not times:
        return float(requested_time)
    requested = float(requested_time)
    best = min(times, key=lambda t: abs(float(t) - requested))
    return float(best)


def setup_reader(foam_file, requested_time):
    reader = OpenFOAMReader(FileName=str(foam_file))

    for prop_name, value in [
        ("MeshRegions", ["internalMesh"]),
        ("CellArrays", OPTIONAL_ARRAYS),
        ("PointArrays", OPTIONAL_ARRAYS),
    ]:
        safe_set(reader, prop_name, value)

    safe_set(reader, "SkipZeroTime", 1)
    reader.UpdatePipelineInformation()
    actual_time = choose_time(reader, requested_time)
    reader.UpdatePipeline(actual_time)
    return reader, actual_time


def add_velocity_arrays(input_proxy, time_value):
    """Create point-data arrays Ux, Uy, Uz, and Umag, while passing all arrays."""
    c2p = CellDatatoPointData(Input=input_proxy)
    safe_set(c2p, "ProcessAllArrays", 1)
    safe_set(c2p, "PassCellData", 1)
    c2p.UpdatePipeline(time_value)

    calc = c2p
    for result_name, expression in [
        ("Ux", "U_X"),
        ("Uy", "U_Y"),
        ("Uz", "U_Z"),
        ("Umag", "mag(U)"),
    ]:
        new_calc = Calculator(Input=calc)
        safe_set(new_calc, "AttributeType", "Point Data")
        new_calc.ResultArrayName = result_name
        new_calc.Function = expression
        try:
            new_calc.UpdatePipeline(time_value)
            calc = new_calc
        except Exception as exc:
            print(f"WARNING: could not create calculated array {result_name}: {exc}")
            Delete(new_calc)
            break
    return calc


def get_bounds(proxy, time_value):
    proxy.UpdatePipeline(time_value)
    info = proxy.GetDataInformation()
    bounds = info.GetBounds()
    if bounds is None:
        raise RuntimeError("Could not get dataset bounds from ParaView reader.")
    return tuple(float(v) for v in bounds)


def slice_origin(bounds, normal):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xmid = 0.5 * (xmin + xmax)
    ymid = 0.5 * (ymin + ymax)
    zmid = 0.5 * (zmin + zmax)
    return (xmid, ymid, zmid)


def make_slice(input_proxy, bounds, normal, time_value):
    slc = Slice(Input=input_proxy)
    slc.SliceType = "Plane"
    slc.SliceType.Origin = slice_origin(bounds, normal)
    slc.SliceType.Normal = list(normal)
    safe_set(slc, "Triangulatetheslice", 0)
    slc.UpdatePipeline(time_value)
    return slc


def camera_for_slice(view, bounds, normal):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xmid = 0.5 * (xmin + xmax)
    ymid = 0.5 * (ymin + ymax)
    zmid = 0.5 * (zmin + zmax)
    dx = max(xmax - xmin, 1.0)
    dy = max(ymax - ymin, 1.0)
    dz = max(zmax - zmin, 1.0)
    dist = 2.5 * max(dx, dy, dz)

    if normal == (1.0, 0.0, 0.0):
        view.CameraPosition = [xmax + dist, ymid, zmid]
        view.CameraFocalPoint = [xmid, ymid, zmid]
        view.CameraViewUp = [0.0, 0.0, 1.0]
    elif normal == (0.0, 1.0, 0.0):
        view.CameraPosition = [xmid, ymax + dist, zmid]
        view.CameraFocalPoint = [xmid, ymid, zmid]
        view.CameraViewUp = [0.0, 0.0, 1.0]
    else:
        view.CameraPosition = [xmid, ymid, zmax + dist]
        view.CameraFocalPoint = [xmid, ymid, zmid]
        view.CameraViewUp = [0.0, 1.0, 0.0]

    safe_set(view, "InteractionMode", "2D")
    view.ResetCamera()


def style_scalar_bar(lut, view, title):
    bar = GetScalarBar(lut, view)
    bar.Title = title
    for name, value in [
        ("TitleColor", [0.0, 0.0, 0.0]),
        ("LabelColor", [0.0, 0.0, 0.0]),
        ("TitleFontSize", 18),
        ("LabelFontSize", 14),
        ("DrawTickMarks", 1),
        ("DrawTickLabels", 1),
        ("ScalarBarThickness", 18),
        ("ScalarBarLength", 0.55),
        ("WindowLocation", "Upper Right Corner"),
    ]:
        safe_set(bar, name, value)
    return bar


def add_title(view, text):
    title = Text()
    title.Text = text
    rep = Show(title, view)
    for loc in ["Upper Center", "Any Location"]:
        if safe_set(rep, "WindowLocation", loc):
            break
    safe_set(rep, "FontSize", 18)
    safe_set(rep, "Color", [0.0, 0.0, 0.0])
    return title, rep


def _array_range_from_info(data_info, field_name):
    for association_getter in [data_info.GetPointDataInformation, data_info.GetCellDataInformation]:
        try:
            data = association_getter()
            arr = data.GetArray(field_name)
        except Exception:
            arr = None
        if arr is None:
            continue
        for component in [0, -1]:
            try:
                rng = arr.GetRange(component)
            except Exception:
                try:
                    rng = arr.GetRange()
                except Exception:
                    continue
            if rng is None or len(rng) < 2:
                continue
            lo, hi = float(rng[0]), float(rng[1])
            if math.isfinite(lo) and math.isfinite(hi):
                return lo, hi
    return None


def get_array_range(proxy, field_name, time_value):
    try:
        proxy.UpdatePipeline(time_value)
        info = proxy.GetDataInformation()
        return _array_range_from_info(info, field_name)
    except Exception:
        return None


def contour_values_from_range(rng, n_levels):
    if rng is None:
        return []
    lo, hi = rng
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return []
    if abs(hi - lo) < 1e-14:
        return []
    n = max(1, int(n_levels))
    return [lo + (i + 1) * (hi - lo) / (n + 1) for i in range(n)]


def add_isoline_overlay(slc, view, field_name, time_value, n_lines=12, line_width=1.25):
    rng = get_array_range(slc, field_name, time_value)
    values = contour_values_from_range(rng, n_lines)
    if not values:
        print(f"WARNING: no valid contour-line levels for {field_name}; skipping isolines.")
        return None

    contour = Contour(Input=slc)
    ok = safe_set(contour, "ContourBy", ["POINTS", field_name])
    if not ok:
        ok = safe_set(contour, "ContourBy", ["CELLS", field_name])
    if not ok:
        print(f"WARNING: could not set ContourBy for {field_name}; skipping isolines.")
        Delete(contour)
        return None

    safe_set(contour, "Isosurfaces", values)
    try:
        contour.UpdatePipeline(time_value)
    except Exception as exc:
        print(f"WARNING: contour-line filter failed for {field_name}: {exc}")
        Delete(contour)
        return None

    rep = Show(contour, view)
    try:
        ColorBy(rep, None)
    except Exception:
        safe_set(rep, "ColorArrayName", [None, ""])
    safe_set(rep, "Representation", "Surface")
    safe_set(rep, "DiffuseColor", [0.0, 0.0, 0.0])
    safe_set(rep, "AmbientColor", [0.0, 0.0, 0.0])
    safe_set(rep, "LineWidth", float(line_width))
    safe_set(rep, "Opacity", 1.0)
    return contour


def save_contour(
    input_proxy,
    case_name,
    field_name,
    field_title,
    slice_name,
    normal,
    slice_label,
    bounds,
    out_png,
    time_value,
    image_width,
    image_height,
    contour_lines=True,
    num_contour_lines=12,
    contour_line_width=1.25,
):
    view = CreateView("RenderView")
    view.ViewSize = [int(image_width), int(image_height)]
    view.Background = [1.0, 1.0, 1.0]
    safe_set(view, "OrientationAxesVisibility", 1)

    slc = make_slice(input_proxy, bounds, normal, time_value)
    rep = Show(slc, view)
    rep.Representation = "Surface"

    try:
        ColorBy(rep, ("POINTS", field_name))
    except Exception:
        try:
            ColorBy(rep, ("CELLS", field_name))
        except Exception as exc:
            print(f"WARNING: cannot color by {field_name} on {slice_name}: {exc}")
            Delete(slc)
            Delete(view)
            return False

    try:
        rep.RescaleTransferFunctionToDataRange(True, False)
    except Exception:
        pass

    lut = GetColorTransferFunction(field_name)
    try:
        lut.ApplyPreset("Cool to Warm", True)
    except Exception:
        pass
    try:
        lut.RescaleTransferFunctionToDataRange()
    except Exception:
        pass

    rep.SetScalarBarVisibility(view, True)
    style_scalar_bar(lut, view, field_title)

    contour_proxy = None
    if contour_lines and num_contour_lines > 0:
        contour_proxy = add_isoline_overlay(
            slc,
            view,
            field_name,
            time_value,
            n_lines=num_contour_lines,
            line_width=contour_line_width,
        )

    title_text = f"{case_name} | {field_title} | {slice_label} | t = {time_value:g} s"
    title_proxy, _ = add_title(view, title_text)

    camera_for_slice(view, bounds, normal)
    Render(view)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(out_png), view, ImageResolution=[int(image_width), int(image_height)], TransparentBackground=0)

    try:
        Hide(slc, view)
    except Exception:
        pass
    Delete(title_proxy)
    if contour_proxy is not None:
        Delete(contour_proxy)
    Delete(slc)
    Delete(view)
    return True


def plot_over_line(input_proxy, p1, p2, resolution, csv_path, time_value):
    line = PlotOverLine(Input=input_proxy)
    try:
        line.Source.Point1 = list(p1)
        line.Source.Point2 = list(p2)
        line.Source.Resolution = int(resolution)
    except Exception:
        safe_set(line, "Point1", list(p1))
        safe_set(line, "Point2", list(p2))
        safe_set(line, "Resolution", int(resolution))
    line.UpdatePipeline(time_value)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    SaveData(str(csv_path), proxy=line)
    Delete(line)


def save_profiles(input_proxy, bounds, profiles_dir, time_value, resolution):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xmid = 0.5 * (xmin + xmax)
    ymid = 0.5 * (ymin + ymax)
    zmid = 0.5 * (zmin + zmax)

    profiles = [
        ("profile_center_x.csv", (xmin, ymid, zmid), (xmax, ymid, zmid)),
        ("profile_center_y.csv", (xmid, ymin, zmid), (xmid, ymax, zmid)),
        ("profile_center_z.csv", (xmid, ymid, zmin), (xmid, ymid, zmax)),
        ("profile_near_floor_x.csv", (xmin, ymid, zmin + 0.05 * (zmax - zmin)), (xmax, ymid, zmin + 0.05 * (zmax - zmin))),
        ("profile_rack_height_x.csv", (xmin, ymid, zmin + 0.50 * (zmax - zmin)), (xmax, ymid, zmin + 0.50 * (zmax - zmin))),
        ("profile_near_ceiling_x.csv", (xmin, ymid, zmin + 0.95 * (zmax - zmin)), (xmax, ymid, zmin + 0.95 * (zmax - zmin))),
        ("profile_diagonal_supply_return.csv", (xmin, ymin, zmin), (xmax, ymax, zmax)),
    ]
    for filename, p1, p2 in profiles:
        csv_path = Path(profiles_dir) / filename
        print(f"Writing line profile: {csv_path}")
        plot_over_line(input_proxy, p1, p2, resolution, csv_path, time_value)


def main():
    parser = argparse.ArgumentParser(description="Make contour plots with isolines and CFD-profile CSV files for one OpenFOAM case.")
    parser.add_argument("case_dir", help="OpenFOAM case directory")
    parser.add_argument("out_dir", help="Output directory for figures")
    parser.add_argument("time", type=float, help="Requested OpenFOAM time, e.g. 8000")
    parser.add_argument("--width", type=int, default=1800, help="Screenshot width in pixels")
    parser.add_argument("--height", type=int, default=1200, help="Screenshot height in pixels")
    parser.add_argument("--profile-resolution", type=int, default=300, help="Number of profile sample intervals")
    parser.add_argument("--no-contour-lines", action="store_true", help="Disable black isoline overlay on contour plots")
    parser.add_argument("--num-contour-lines", type=int, default=12, help="Number of black isolines to overlay")
    parser.add_argument("--contour-line-width", type=float, default=1.25, help="Black isoline width")
    args = parser.parse_args()

    case_dir = Path(args.case_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    contour_dir = out_dir / "contours"
    profiles_dir = out_dir / "profiles"
    case_name = case_dir.name

    foam_file = find_or_create_foam(case_dir)
    print(f"Reading OpenFOAM case: {case_name}")
    print(f"Foam file: {foam_file}")

    reader, actual_time = setup_reader(foam_file, args.time)
    print(f"Using ParaView time: {actual_time:g}")

    data = add_velocity_arrays(reader, actual_time)
    bounds = get_bounds(data, actual_time)
    print(f"Bounds: {bounds}")

    made = 0
    for field_name, field_title, _preset in FIELD_SPECS:
        for slice_name, normal, slice_label in SLICE_SPECS:
            out_png = contour_dir / f"{field_name}_{slice_name}.png"
            ok = save_contour(
                data,
                case_name,
                field_name,
                field_title,
                slice_name,
                normal,
                slice_label,
                bounds,
                out_png,
                actual_time,
                args.width,
                args.height,
                contour_lines=not args.no_contour_lines,
                num_contour_lines=args.num_contour_lines,
                contour_line_width=args.contour_line_width,
            )
            if ok:
                made += 1
                print(f"Wrote: {out_png}")

    save_profiles(data, bounds, profiles_dir, actual_time, args.profile_resolution)
    print(f"Done. Contour images: {made}")
    print(f"Output folder: {out_dir}")


if __name__ == "__main__":
    main()
