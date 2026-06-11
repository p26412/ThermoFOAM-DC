#!/usr/bin/env python3
"""
Generate CFD-style ParaView figures for one OpenFOAM case.

Outputs:
  1. temperature_horizontal_midHeight.png
  2. temperature_vertical_centerplane_x.png
  3. temperature_vertical_centerplane_y.png
  4. pressure_vertical_slice.png
  5. velocity_magnitude_horizontal_midHeight.png
  6. streamlines_3D.png

This script is intentionally defensive because ParaView Python APIs behave
like they were assembled during a committee meeting in a basement.
"""

import argparse
import sys
from pathlib import Path


try:
    import paraview.simple as pvs
except Exception as exc:
    print("ERROR: Could not import paraview.simple.")
    print("Run with a Python that can import ParaView, for example:")
    print("  python3 -c \"import paraview.simple as pvs; print('OK')\"")
    print("  pvpython -c \"import paraview.simple as pvs; print('OK')\"")
    print("")
    print("Original error:")
    print(exc)
    sys.exit(1)


try:
    pvs._DisableFirstRenderCameraReset()
except Exception:
    pass


# ---------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate ParaView CFD figures for one OpenFOAM case."
    )

    parser.add_argument("--case", "--case-dir", dest="case_dir", default=None)
    parser.add_argument("--foam", "--foam-file", dest="foam_file", default=None)
    parser.add_argument("--out", "--output", "--output-dir", dest="output_dir", default=None)
    parser.add_argument("--time", dest="time_value", default=None)

    parser.add_argument("--width", dest="width", type=int, default=1800)
    parser.add_argument("--height", dest="height", type=int, default=1200)

    # Support older runner styles:
    #   script.py caseDir foamFile outputDir time
    #   script.py caseDir outputDir time
    parser.add_argument("positional", nargs="*")

    args = parser.parse_args()

    pos = list(args.positional)

    if args.case_dir is None and pos:
        args.case_dir = pos.pop(0)

    if pos and args.foam_file is None and pos[0].endswith(".foam"):
        args.foam_file = pos.pop(0)

    if args.output_dir is None and pos:
        args.output_dir = pos.pop(0)

    if args.time_value is None and pos:
        args.time_value = pos.pop(0)

    if args.case_dir is None:
        raise SystemExit("ERROR: case directory was not provided.")

    return args


# ---------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------

def safe_set(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def update(proxy, time_value=None):
    try:
        if time_value is None:
            proxy.UpdatePipeline()
        else:
            proxy.UpdatePipeline(float(time_value))
        return
    except Exception:
        pass

    try:
        if time_value is None:
            pvs.UpdatePipeline(proxy=proxy)
        else:
            pvs.UpdatePipeline(float(time_value), proxy=proxy)
    except Exception:
        try:
            pvs.UpdatePipeline()
        except Exception:
            pass


def ensure_foam_file(case_dir, foam_file=None):
    case_dir = Path(case_dir).resolve()

    if foam_file:
        foam_path = Path(foam_file).resolve()
        if not foam_path.exists():
            print(f"WARNING: supplied .foam file does not exist, creating: {foam_path}")
            foam_path.touch()
        return foam_path

    found = sorted(case_dir.glob("*.foam"))
    if found:
        return found[0].resolve()

    foam_path = case_dir / f"{case_dir.name}.foam"
    print(f"No .foam file found. Creating: {foam_path}")
    foam_path.touch()
    return foam_path.resolve()


def choose_time(reader, requested_time):
    update(reader, None)

    values = []
    try:
        values = list(reader.TimestepValues)
    except Exception:
        values = []

    if not values:
        return None

    values = [float(v) for v in values]

    if requested_time is None:
        return values[-1]

    req_str = str(requested_time).strip().lower()
    if req_str in ("latest", "latesttime", "last"):
        return values[-1]

    req = float(requested_time)
    return min(values, key=lambda v: abs(v - req))


def get_bounds(proxy, time_value=None):
    update(proxy, time_value)
    try:
        bounds = proxy.GetDataInformation().GetBounds()
        return tuple(float(v) for v in bounds)
    except Exception:
        return (0.0, 7.0, 0.0, 5.0, 0.0, 3.0)


def span_and_center(bounds):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan = max(xmax - xmin, 1.0e-12)
    yspan = max(ymax - ymin, 1.0e-12)
    zspan = max(zmax - zmin, 1.0e-12)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    cz = 0.5 * (zmin + zmax)
    length = max(xspan, yspan, zspan)
    return xspan, yspan, zspan, cx, cy, cz, length


def list_arrays(proxy, time_value=None):
    update(proxy, time_value)

    arrays = {"POINTS": [], "CELLS": []}

    try:
        info = proxy.GetDataInformation()

        point_info = info.GetPointDataInformation()
        for i in range(point_info.GetNumberOfArrays()):
            arrays["POINTS"].append(point_info.GetArrayInformation(i).GetName())

        cell_info = info.GetCellDataInformation()
        for i in range(cell_info.GetNumberOfArrays()):
            arrays["CELLS"].append(cell_info.GetArrayInformation(i).GetName())

    except Exception:
        pass

    return arrays


def find_association(proxy, field_name, time_value=None):
    arrays = list_arrays(proxy, time_value)

    if field_name in arrays["POINTS"]:
        return "POINTS"

    if field_name in arrays["CELLS"]:
        return "CELLS"

    return None


def choose_existing_field(proxy, candidates, time_value=None):
    arrays = list_arrays(proxy, time_value)
    all_names = set(arrays["POINTS"]) | set(arrays["CELLS"])

    for name in candidates:
        if name in all_names:
            return name

    return None


def make_point_source(reader, time_value=None):
    """
    Convert cell data to point data where possible.
    This improves slices, contours, and streamlines.
    """
    try:
        c2p = pvs.CellDatatoPointData(Input=reader)
        safe_set(c2p, "PassCellData", 1)
        update(c2p, time_value)
        return c2p
    except Exception:
        pass

    try:
        c2p = pvs.CellDataToPointData(Input=reader)
        safe_set(c2p, "PassCellData", 1)
        update(c2p, time_value)
        return c2p
    except Exception:
        print("WARNING: Could not create CellDataToPointData filter. Using reader directly.")
        return reader


def make_umag_source(source, time_value=None):
    assoc = find_association(source, "U", time_value)
    if assoc is None:
        print("WARNING: U field not found. Velocity magnitude figures will be skipped.")
        return None

    try:
        calc = pvs.Calculator(Input=source)
        calc.ResultArrayName = "Umag"
        calc.Function = "mag(U)"
        update(calc, time_value)
        return calc
    except Exception as exc:
        print("WARNING: Could not calculate Umag = mag(U).")
        print(exc)
        return None


# ---------------------------------------------------------------------
# ParaView view and rendering utilities
# ---------------------------------------------------------------------

def new_view(width, height):
    view = pvs.CreateView("RenderView")
    pvs.SetActiveView(view)

    safe_set(view, "ViewSize", [int(width), int(height)])
    safe_set(view, "Background", [0.88, 0.88, 0.88])
    safe_set(view, "UseColorPaletteForBackground", 0)

    # Orientation axis in corner
    safe_set(view, "OrientationAxesVisibility", 1)
    safe_set(view, "OrientationAxesLabelColor", [0.0, 0.0, 0.0])

    # Optional center axis off
    safe_set(view, "CenterAxesVisibility", 0)	
    
    style_axes_grid(view)

    return view


def set_camera(view, bounds, mode):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan, yspan, zspan, cx, cy, cz, length = span_and_center(bounds)

    distance = 2.8 * length

    if mode == "top":
        position = [cx, cy, zmax + distance]
        focal = [cx, cy, cz]
        up = [0.0, 1.0, 0.0]
        scale = 0.58 * max(xspan, yspan)

    elif mode == "x":
        position = [xmax + distance, cy, cz]
        focal = [cx, cy, cz]
        up = [0.0, 0.0, 1.0]
        scale = 0.58 * max(yspan, zspan)

    elif mode == "y":
        position = [cx, ymax + distance, cz]
        focal = [cx, cy, cz]
        up = [0.0, 0.0, 1.0]
        scale = 0.58 * max(xspan, zspan)

    else:
        position = [xmax + 1.7 * length, ymin - 1.7 * length, zmax + 0.9 * length]
        focal = [cx, cy, cz]
        up = [0.0, 0.0, 1.0]
        scale = 0.72 * max(xspan, yspan)

    safe_set(view, "CameraPosition", position)
    safe_set(view, "CameraFocalPoint", focal)
    safe_set(view, "CameraViewUp", up)
    safe_set(view, "CameraParallelProjection", 1)
    safe_set(view, "CameraParallelScale", scale)
    safe_set(view, "CameraClippingRange", [1.0e-4, 1000.0 * max(length, 1.0)])

    try:
        pvs.Render(view)
    except Exception:
        pass


def add_title(view, title):
    """
    Uses modern ParaView WindowLocation value: 'Upper Center'.
    Never use 'UpperCenter'. That obsolete name caused your crash.
    """
    try:
        text = pvs.Text()
        text.Text = title
        rep = pvs.Show(text, view)
        safe_set(rep, "WindowLocation", "Upper Center")
        safe_set(rep, "FontSize", 16)
        safe_set(rep, "Color", [0.0, 0.0, 0.0])
        return text
    except Exception:
        return None


def add_outline(source, view, time_value=None):
    try:
        outline = pvs.Outline(Input=source)
        update(outline, time_value)

        rep = pvs.Show(outline, view)
        try:
            pvs.ColorBy(rep, None)
        except Exception:
            pass

        safe_set(rep, "DiffuseColor", [0.0, 0.0, 0.0])
        safe_set(rep, "LineWidth", 1.5)
        return outline

    except Exception:
        return None


def apply_coloring(display, view, proxy, field_name, title, units, time_value=None):
    assoc = find_association(proxy, field_name, time_value)

    if assoc is None:
        raise RuntimeError(f"Field '{field_name}' not found on proxy.")

    pvs.ColorBy(display, (assoc, field_name))

    try:
        display.RescaleTransferFunctionToDataRange(True, False)
    except Exception:
        pass

    try:
        display.SetScalarBarVisibility(view, True)
    except Exception:
        pass

    try:
        lut = pvs.GetColorTransferFunction(field_name)
        bar = pvs.GetScalarBar(lut, view)
        bar.Title = title
        bar.ComponentTitle = units
        bar.Visibility = 1

        # Make scalar-bar text visible on white/light background
        safe_set(bar, "TitleColor", [0.0, 0.0, 0.0])
        safe_set(bar, "LabelColor", [0.0, 0.0, 0.0])
        safe_set(bar, "TitleFontSize", 18)
        safe_set(bar, "LabelFontSize", 14)

        # Make legend easier to read
        safe_set(bar, "ScalarBarThickness", 18)
        safe_set(bar, "ScalarBarLength", 0.35)
        safe_set(bar, "DrawTickLabels", 1)
        safe_set(bar, "DrawTickMarks", 1)
    except Exception:
        pass


def style_axes_grid(view):
    """
    Add visible x, y, z coordinate axes around the CFD domain.
    ParaView sometimes chooses white text on white background because apparently
    readability was an optional elective.
    """
    try:
        view.AxesGrid = "GridAxes3DActor"
        grid = view.AxesGrid
    except Exception:
        return

    safe_set(grid, "Visibility", 1)

    safe_set(grid, "XTitle", "x (m)")
    safe_set(grid, "YTitle", "y (m)")
    safe_set(grid, "ZTitle", "z (m)")

    safe_set(grid, "XTitleColor", [0.0, 0.0, 0.0])
    safe_set(grid, "YTitleColor", [0.0, 0.0, 0.0])
    safe_set(grid, "ZTitleColor", [0.0, 0.0, 0.0])

    safe_set(grid, "XLabelColor", [0.0, 0.0, 0.0])
    safe_set(grid, "YLabelColor", [0.0, 0.0, 0.0])
    safe_set(grid, "ZLabelColor", [0.0, 0.0, 0.0])

    safe_set(grid, "GridColor", [0.25, 0.25, 0.25])
    safe_set(grid, "ShowGrid", 1)
    safe_set(grid, "ShowEdges", 1)
    safe_set(grid, "ShowTicks", 1)

    safe_set(grid, "XTitleFontSize", 16)
    safe_set(grid, "YTitleFontSize", 16)
    safe_set(grid, "ZTitleFontSize", 16)
    safe_set(grid, "XLabelFontSize", 12)
    safe_set(grid, "YLabelFontSize", 12)
    safe_set(grid, "ZLabelFontSize", 12)


def save_screenshot(view, output_path, width, height):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        pvs.Render(view)
    except Exception:
        pass

    try:
        pvs.SaveScreenshot(
            str(output_path),
            view,
            ImageResolution=[int(width), int(height)],
            TransparentBackground=0,
        )
    except TypeError:
        pvs.SaveScreenshot(
            str(output_path),
            view,
            ImageResolution=[int(width), int(height)],
        )

    print(f"Saved: {output_path}")


def delete_view(view):
    try:
        pvs.Delete(view)
    except Exception:
        pass


# ---------------------------------------------------------------------
# Filters and figure creation
# ---------------------------------------------------------------------

def make_slice(source, origin, normal, time_value=None):
    slc = pvs.Slice(Input=source)

    try:
        slc.SliceType = "Plane"
    except Exception:
        pass

    slc.SliceType.Origin = [float(origin[0]), float(origin[1]), float(origin[2])]
    slc.SliceType.Normal = [float(normal[0]), float(normal[1]), float(normal[2])]

    update(slc, time_value)
    return slc


def save_scalar_slice(
    source,
    bounds,
    field_name,
    scalar_title,
    scalar_units,
    origin,
    normal,
    camera_mode,
    output_path,
    figure_title,
    time_value,
    width,
    height,
):
    view = new_view(width, height)

    try:
        add_outline(source, view, time_value)

        slc = make_slice(source, origin, normal, time_value)

        rep = pvs.Show(slc, view)
        safe_set(rep, "Representation", "Surface")
        safe_set(rep, "Opacity", 1.0)

        apply_coloring(
            rep,
            view,
            slc,
            field_name,
            scalar_title,
            scalar_units,
            time_value,
        )
        
        # Optional black contour isolines on top of filled contours.
        # Skip quietly when a field cannot be contoured in the current ParaView build.
        try:
            assoc = find_association(slc, field_name, time_value)
            if assoc is not None:
                contour = pvs.Contour(Input=slc)
                contour.ContourBy = [assoc, field_name]

                if field_name in ("T", "thermo:T"):
                    contour.Isosurfaces = [300, 305, 310, 315, 320, 325, 330, 335, 340]
                elif field_name in ("p", "p_rgh"):
                    contour.Isosurfaces = []
                elif field_name == "Umag":
                    contour.Isosurfaces = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25]
                else:
                    contour.Isosurfaces = []

                update(contour, time_value)

                contour_rep = pvs.Show(contour, view)
                try:
                    pvs.ColorBy(contour_rep, None)
                except Exception:
                    pass

                safe_set(contour_rep, "DiffuseColor", [0.0, 0.0, 0.0])
                safe_set(contour_rep, "LineWidth", 1.2)
        except Exception:
            pass

        add_title(view, figure_title)
        set_camera(view, bounds, camera_mode)

        save_screenshot(view, output_path, width, height)

    except Exception as exc:
        print(f"WARNING: could not save figure: {output_path}")
        print(f"Reason: {exc}")

    finally:
        delete_view(view)


def save_temperature_figures(source, bounds, out_dir, case_name, time_value, width, height):
    t_field = choose_existing_field(source, ["T", "thermo:T"], time_value)

    if t_field is None:
        print("WARNING: Temperature field T not found. Temperature figures skipped.")
        return

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan, yspan, zspan, cx, cy, cz, length = span_and_center(bounds)

    # Horizontal mid-height slice
    save_scalar_slice(
        source=source,
        bounds=bounds,
        field_name=t_field,
        scalar_title="Temperature",
        scalar_units="K",
        origin=[cx, cy, cz],
        normal=[0.0, 0.0, 1.0],
        camera_mode="top",
        output_path=out_dir / "temperature_horizontal_midHeight.png",
        figure_title=f"{case_name}: T horizontal slice, z={cz:.3g}, t={time_value}",
        time_value=time_value,
        width=width,
        height=height,
    )

    # Vertical x-normal slice: plane x = center
    save_scalar_slice(
        source=source,
        bounds=bounds,
        field_name=t_field,
        scalar_title="Temperature",
        scalar_units="K",
        origin=[cx, cy, cz],
        normal=[1.0, 0.0, 0.0],
        camera_mode="x",
        output_path=out_dir / "temperature_vertical_centerplane_x.png",
        figure_title=f"{case_name}: T vertical slice, x={cx:.3g}, t={time_value}",
        time_value=time_value,
        width=width,
        height=height,
    )

    # Vertical y-normal slice: plane y = center
    save_scalar_slice(
        source=source,
        bounds=bounds,
        field_name=t_field,
        scalar_title="Temperature",
        scalar_units="K",
        origin=[cx, cy, cz],
        normal=[0.0, 1.0, 0.0],
        camera_mode="y",
        output_path=out_dir / "temperature_vertical_centerplane_y.png",
        figure_title=f"{case_name}: T vertical slice, y={cy:.3g}, t={time_value}",
        time_value=time_value,
        width=width,
        height=height,
    )


def save_pressure_figure(source, bounds, out_dir, case_name, time_value, width, height):
    pressure_field = choose_existing_field(source, ["p_rgh", "p"], time_value)

    if pressure_field is None:
        print("WARNING: pressure field p_rgh or p not found. Pressure figure skipped.")
        return

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan, yspan, zspan, cx, cy, cz, length = span_and_center(bounds)

    save_scalar_slice(
        source=source,
        bounds=bounds,
        field_name=pressure_field,
        scalar_title=pressure_field,
        scalar_units="Pa",
        origin=[cx, cy, cz],
        normal=[0.0, 1.0, 0.0],
        camera_mode="y",
        output_path=out_dir / "pressure_vertical_slice.png",
        figure_title=f"{case_name}: {pressure_field} vertical slice, y={cy:.3g}, t={time_value}",
        time_value=time_value,
        width=width,
        height=height,
    )


def save_velocity_magnitude_figure(source, bounds, out_dir, case_name, time_value, width, height):
    umag_source = make_umag_source(source, time_value)

    if umag_source is None:
        return

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan, yspan, zspan, cx, cy, cz, length = span_and_center(bounds)

    save_scalar_slice(
        source=umag_source,
        bounds=bounds,
        field_name="Umag",
        scalar_title="Velocity magnitude",
        scalar_units="m/s",
        origin=[cx, cy, cz],
        normal=[0.0, 0.0, 1.0],
        camera_mode="top",
        output_path=out_dir / "velocity_magnitude_horizontal_midHeight.png",
        figure_title=f"{case_name}: |U| horizontal slice, z={cz:.3g}, t={time_value}",
        time_value=time_value,
        width=width,
        height=height,
    )


def save_streamlines(source, bounds, out_dir, case_name, time_value, width, height):
    u_assoc = find_association(source, "U", time_value)

    if u_assoc is None:
        print("WARNING: U field not found. Streamline figure skipped.")
        return

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    xspan, yspan, zspan, cx, cy, cz, length = span_and_center(bounds)

    view = new_view(width, height)

    try:
        add_outline(source, view, time_value)

        # Add a semi-transparent mid-height temperature slice in the background.
        t_field = choose_existing_field(source, ["T", "thermo:T"], time_value)
        if t_field is not None:
            t_slice = make_slice(
                source,
                origin=[cx, cy, cz],
                normal=[0.0, 0.0, 1.0],
                time_value=time_value,
            )
            t_rep = pvs.Show(t_slice, view)
            safe_set(t_rep, "Representation", "Surface")
            safe_set(t_rep, "Opacity", 0.35)
            try:
                apply_coloring(t_rep, view, t_slice, t_field, "Temperature", "K", time_value)
            except Exception:
                pass

        stream = pvs.StreamTracer(Input=source, SeedType="Line")
        stream.Vectors = [u_assoc, "U"]

        safe_set(stream, "MaximumStreamlineLength", 4.0 * length)
        safe_set(stream, "IntegrationDirection", "BOTH")
        safe_set(stream, "ComputeVorticity", 0)

        # Seed line near the lower part of the room, spanning x direction.
        # This is deliberately general because the exact supply-tile layout
        # changes between user cases.
        try:
            stream.SeedType.Point1 = [
                xmin + 0.10 * xspan,
                cy,
                zmin + 0.08 * zspan,
            ]
            stream.SeedType.Point2 = [
                xmax - 0.10 * xspan,
                cy,
                zmin + 0.08 * zspan,
            ]
            stream.SeedType.Resolution = 80
        except Exception:
            pass

        update(stream, time_value)

        # Color streamlines by velocity magnitude.
        stream_umag = pvs.Calculator(Input=stream)
        stream_umag.ResultArrayName = "Umag"
        stream_umag.Function = "mag(U)"
        update(stream_umag, time_value)

        stream_rep = pvs.Show(stream_umag, view)
        safe_set(stream_rep, "Representation", "Surface")
        safe_set(stream_rep, "LineWidth", 2.5)

        try:
            apply_coloring(
                stream_rep,
                view,
                stream_umag,
                "Umag",
                "Velocity magnitude",
                "m/s",
                time_value,
            )
        except Exception:
            pass

        add_title(view, f"{case_name}: velocity streamlines, t={time_value}")
        set_camera(view, bounds, "iso")

        save_screenshot(view, out_dir / "streamlines_3D.png", width, height)

    except Exception as exc:
        print("WARNING: could not save streamline figure.")
        print(f"Reason: {exc}")

    finally:
        delete_view(view)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def configure_openfoam_reader(foam_file):
    reader = pvs.OpenFOAMReader(FileName=str(foam_file))

    # These properties vary between ParaView versions. Try them, but do not
    # let the entire script die if one version disagrees. Very mature software.
    safe_set(reader, "CaseType", "Reconstructed Case")

    try:
        reader.MeshRegions = ["internalMesh"]
    except Exception:
        pass

    # Try to request the important fields. If ParaView rejects the list, it
    # usually still loads default arrays.
    for prop_name in ("CellArrays", "PointArrays"):
        try:
            setattr(reader, prop_name, ["T", "U", "p_rgh", "p"])
        except Exception:
            pass

    return reader


def main():
    args = parse_args()

    case_dir = Path(args.case_dir).resolve()
    foam_file = ensure_foam_file(case_dir, args.foam_file)

    if args.output_dir is None:
        out_dir = case_dir / "postProcessing" / "cfd_figures"
    else:
        out_dir = Path(args.output_dir).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)

    case_name = case_dir.name

    print(f"Reading OpenFOAM case: {case_name}")
    print(f"Case directory: {case_dir}")
    print(f"Foam file: {foam_file}")
    print(f"Output directory: {out_dir}")

    reader = configure_openfoam_reader(foam_file)

    chosen_time = choose_time(reader, args.time_value)

    if chosen_time is None:
        print("No time values found in reader. Using static/latest pipeline state.")
        time_value = None
        time_label = "latest"
    else:
        time_value = float(chosen_time)
        time_label = f"{time_value:g}"

    print(f"Using ParaView time: {time_label}")

    update(reader, time_value)

    source = make_point_source(reader, time_value)
    update(source, time_value)

    bounds = get_bounds(source, time_value)
    print(f"Bounds: {bounds}")

    arrays = list_arrays(source, time_value)
    print("Available point arrays:", ", ".join(arrays["POINTS"]) if arrays["POINTS"] else "none")
    print("Available cell arrays: ", ", ".join(arrays["CELLS"]) if arrays["CELLS"] else "none")

    save_temperature_figures(
        source=source,
        bounds=bounds,
        out_dir=out_dir,
        case_name=case_name,
        time_value=time_value,
        width=args.width,
        height=args.height,
    )

    save_pressure_figure(
        source=source,
        bounds=bounds,
        out_dir=out_dir,
        case_name=case_name,
        time_value=time_value,
        width=args.width,
        height=args.height,
    )

    save_velocity_magnitude_figure(
        source=source,
        bounds=bounds,
        out_dir=out_dir,
        case_name=case_name,
        time_value=time_value,
        width=args.width,
        height=args.height,
    )

    save_streamlines(
        source=source,
        bounds=bounds,
        out_dir=out_dir,
        case_name=case_name,
        time_value=time_value,
        width=args.width,
        height=args.height,
    )

    print("")
    print("Finished CFD figure generation for one case.")
    print(f"Output folder: {out_dir}")


if __name__ == "__main__":
    main()
