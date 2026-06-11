#!/usr/bin/env pvpython
"""
Generate CFD-style contour and streamline figures from an OpenFOAM case using ParaView.

Run from cases/parameterstudy, for example:

    pvpython scripts/cfd_viz/pv_make_cfd_figures.py --case C00_baseline --time 8000

Outputs PNG figures to results/cfd_figures/<case> by default.

Notes:
- This script intentionally creates field plots, not bar charts.
- It is written defensively because ParaView/OpenFOAM reader properties differ by version.
- If a derived field such as Q or vorticity is missing, first run:
      bash scripts/cfd_viz/write_cfd_fields.sh C00_baseline
"""

import argparse
import math
import os
import sys

try:
    from paraview.simple import (  # type: ignore
        OpenFOAMReader,
        CellDatatoPointData,
        Slice,
        Calculator,
        StreamTracer,
        Contour,
        Show,
        Hide,
        Delete,
        GetActiveViewOrCreate,
        GetColorTransferFunction,
        GetOpacityTransferFunction,
        ColorBy,
        SaveScreenshot,
        Render,
        ResetCamera,
        Text,
        Layout,
        SetActiveSource,
    )
except Exception as exc:
    print("ERROR: This script must be run with pvpython, not normal python3.", file=sys.stderr)
    print(str(exc), file=sys.stderr)
    sys.exit(2)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--case", required=True, help="OpenFOAM case directory, e.g. C00_baseline")
    p.add_argument("--time", default="latest", help="Time to plot, e.g. 8000 or latest")
    p.add_argument("--outdir", default=None, help="Output directory")
    p.add_argument("--domain", nargs=3, type=float, default=[7.0, 5.0, 3.0], metavar=("LX", "LY", "LZ"))
    p.add_argument("--rack-height-z", type=float, default=1.5, help="Horizontal plane height for rack inlet/aisle plots")
    p.add_argument("--image-width", type=int, default=1800)
    p.add_argument("--image-height", type=int, default=1200)
    return p.parse_args()


def ensure_foam_file(case_dir):
    case_name = os.path.basename(os.path.abspath(case_dir))
    foam_file = os.path.join(case_dir, case_name + ".foam")
    if not os.path.exists(foam_file):
        open(foam_file, "a").close()
    return foam_file


def safe_set(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def get_time_value(reader, requested):
    try:
        reader.UpdatePipeline()
    except Exception:
        pass
    vals = []
    try:
        vals = list(reader.TimestepValues)
    except Exception:
        vals = []
    if not vals:
        return None
    if str(requested).lower() == "latest":
        return max(vals)
    try:
        target = float(requested)
        return min(vals, key=lambda x: abs(float(x) - target))
    except Exception:
        return max(vals)


def has_point_array(src, name, t=None):
    try:
        src.UpdatePipeline(t) if t is not None else src.UpdatePipeline()
        info = src.GetDataInformation().GetPointDataInformation()
        return info.GetArray(name) is not None
    except Exception:
        return False


def add_text(view, txt):
    try:
        t = Text()
        t.Text = txt
        d = Show(t, view)
        d.WindowLocation = "UpperLeftCorner"
        d.FontSize = 18
        return t
    except Exception:
        return None


def set_color(display, field, view, title=None):
    try:
        ColorBy(display, ("POINTS", field))
        display.RescaleTransferFunctionToDataRange(True, False)
        display.SetScalarBarVisibility(view, True)
        lut = GetColorTransferFunction(field)
        pwf = GetOpacityTransferFunction(field)
        try:
            lut.RescaleTransferFunctionToDataRange()
            pwf.RescaleTransferFunctionToDataRange()
        except Exception:
            pass
        if title:
            try:
                lut.ColorSpace = "Diverging"
            except Exception:
                pass
        return True
    except Exception as exc:
        print(f"WARNING: could not color by {field}: {exc}")
        return False


def save_current(view, path, width, height):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Render(view)
    SaveScreenshot(path, view, ImageResolution=[width, height], TransparentBackground=0)
    print("wrote", path)


def camera_vertical_xz(view, lx, ly, lz):
    view.CameraPosition = [lx / 2.0, -max(lx, ly, lz) * 2.8, lz / 2.0]
    view.CameraFocalPoint = [lx / 2.0, ly / 2.0, lz / 2.0]
    view.CameraViewUp = [0, 0, 1]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = max(lx, lz) * 0.62


def camera_horizontal_xy(view, lx, ly, lz):
    view.CameraPosition = [lx / 2.0, ly / 2.0, max(lx, ly, lz) * 2.8]
    view.CameraFocalPoint = [lx / 2.0, ly / 2.0, lz / 2.0]
    view.CameraViewUp = [0, 1, 0]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = max(lx, ly) * 0.62


def camera_3d(view, lx, ly, lz):
    view.CameraPosition = [lx * 1.6, -ly * 2.2, lz * 1.7]
    view.CameraFocalPoint = [lx / 2.0, ly / 2.0, lz / 2.0]
    view.CameraViewUp = [0, 0, 1]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = max(lx, ly, lz) * 0.78


def make_slice(src, view, field, origin, normal, camera_fn, outpath, title, args, t):
    if not has_point_array(src, field, t):
        print(f"WARNING: field {field} not found, skipping {outpath}")
        return
    sl = Slice(Input=src)
    sl.SliceType = "Plane"
    sl.SliceType.Origin = origin
    sl.SliceType.Normal = normal
    sl.Triangulatetheslice = 0
    try:
        sl.UpdatePipeline(t)
    except Exception:
        pass
    disp = Show(sl, view)
    disp.Representation = "Surface"
    set_color(disp, field, view, title)
    text = add_text(view, title)
    camera_fn(view, *args.domain)
    save_current(view, outpath, args.image_width, args.image_height)
    Hide(sl, view)
    if text:
        Delete(text)
    Delete(sl)


def make_calc(src, name, formula, t):
    calc = Calculator(Input=src)
    calc.AttributeType = "Point Data"
    calc.ResultArrayName = name
    calc.Function = formula
    try:
        calc.UpdatePipeline(t)
    except Exception:
        pass
    return calc


def main():
    args = parse_args()
    case_dir = os.path.abspath(args.case)
    case_name = os.path.basename(case_dir)
    if not os.path.isdir(case_dir):
        print("ERROR: case directory not found:", case_dir, file=sys.stderr)
        sys.exit(1)

    outdir = args.outdir or os.path.join("results", "cfd_figures", case_name)
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)

    lx, ly, lz = args.domain
    foam_file = ensure_foam_file(case_dir)
    reader = OpenFOAMReader(FileName=foam_file)

    # Different ParaView versions expose slightly different reader properties.
    # Keep all mesh regions when possible so boundary-only fields such as yPlus can be shown.
    safe_set(reader, "SkipZeroTime", 1)
    safe_set(reader, "CaseType", "Decomposed Case")

    t = get_time_value(reader, args.time)
    if t is None:
        print("WARNING: no time values detected. ParaView will use its default pipeline time.")
    else:
        print("Using time:", t)

    try:
        reader.UpdatePipeline(t)
    except Exception:
        reader.UpdatePipeline()

    point_data = CellDatatoPointData(Input=reader)
    safe_set(point_data, "PassCellData", 1)
    try:
        point_data.UpdatePipeline(t)
    except Exception:
        pass

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [args.image_width, args.image_height]
    view.Background = [1, 1, 1]
    safe_set(view, "OrientationAxesVisibility", 1)

    # Field contours: thermal and velocity physics.
    make_slice(point_data, view, "T", [lx / 2, ly / 2, lz / 2], [0, 1, 0], camera_vertical_xz,
               os.path.join(outdir, "01_T_vertical_center_XZ.png"),
               f"{case_name}: temperature T [K], vertical centre plane", args, t)
    make_slice(point_data, view, "T", [lx / 2, ly / 2, args.rack_height_z], [0, 0, 1], camera_horizontal_xy,
               os.path.join(outdir, "02_T_horizontal_rack_height_XY.png"),
               f"{case_name}: temperature T [K], rack-inlet height plane", args, t)

    if has_point_array(point_data, "U", t):
        magU = make_calc(point_data, "magU", "mag(U)", t)
        make_slice(magU, view, "magU", [lx / 2, ly / 2, lz / 2], [0, 1, 0], camera_vertical_xz,
                   os.path.join(outdir, "03_velocityMagnitude_vertical_center_XZ.png"),
                   f"{case_name}: velocity magnitude |U| [m/s], vertical centre plane", args, t)
        make_slice(magU, view, "magU", [lx / 2, ly / 2, args.rack_height_z], [0, 0, 1], camera_horizontal_xy,
                   os.path.join(outdir, "04_velocityMagnitude_horizontal_rack_height_XY.png"),
                   f"{case_name}: velocity magnitude |U| [m/s], rack-inlet height plane", args, t)

        for comp_name, formula, label in [
            ("Ux", "U_X", "Ux [m/s]"),
            ("Uy", "U_Y", "Uy [m/s]"),
            ("Uz", "U_Z", "Uz [m/s]"),
        ]:
            c = make_calc(point_data, comp_name, formula, t)
            make_slice(c, view, comp_name, [lx / 2, ly / 2, lz / 2], [0, 1, 0], camera_vertical_xz,
                       os.path.join(outdir, f"05_{comp_name}_vertical_center_XZ.png"),
                       f"{case_name}: velocity component {label}, vertical centre plane", args, t)
            try:
                Delete(c)
            except Exception:
                pass
        try:
            Delete(magU)
        except Exception:
            pass

    # Vorticity magnitude, if present.
    if has_point_array(point_data, "vorticity", t):
        vort = make_calc(point_data, "magVorticity", "mag(vorticity)", t)
        make_slice(vort, view, "magVorticity", [lx / 2, ly / 2, lz / 2], [0, 1, 0], camera_vertical_xz,
                   os.path.join(outdir, "06_vorticityMagnitude_vertical_center_XZ.png"),
                   f"{case_name}: vorticity magnitude [1/s], vertical centre plane", args, t)
        try:
            Delete(vort)
        except Exception:
            pass

    # Turbulence fields, if present.
    for fld, title in [("k", "turbulent kinetic energy k [m2/s2]"), ("epsilon", "epsilon [m2/s3]"), ("omega", "omega [1/s]"), ("nut", "eddy viscosity nut [m2/s]")]:
        make_slice(point_data, view, fld, [lx / 2, ly / 2, lz / 2], [0, 1, 0], camera_vertical_xz,
                   os.path.join(outdir, f"07_{fld}_vertical_center_XZ.png"),
                   f"{case_name}: {title}, vertical centre plane", args, t)

    # Streamlines from supply side. If seed line is not exactly on supply tiles, adjust points in the command line or script.
    if has_point_array(point_data, "U", t):
        try:
            st = StreamTracer(Input=point_data, SeedType="Line")
            st.Vectors = ["POINTS", "U"]
            st.MaximumStreamlineLength = max(lx, ly, lz) * 4
            st.SeedType.Point1 = [0.4 * lx, 0.15 * ly, 0.05]
            st.SeedType.Point2 = [0.6 * lx, 0.85 * ly, 0.05]
            st.SeedType.Resolution = 120
            st.UpdatePipeline(t)
            disp = Show(st, view)
            disp.Representation = "Surface"
            if has_point_array(st, "T", t):
                set_color(disp, "T", view, "T")
            else:
                set_color(disp, "U", view, "U")
            text = add_text(view, f"{case_name}: streamlines seeded near supply tiles")
            camera_3d(view, lx, ly, lz)
            save_current(view, os.path.join(outdir, "08_streamlines_supply_seeded.png"), args.image_width, args.image_height)
            Hide(st, view)
            if text:
                Delete(text)
            Delete(st)
        except Exception as exc:
            print("WARNING: streamlines failed:", exc)

    # Q criterion isosurface, if present.
    if has_point_array(point_data, "Q", t):
        try:
            q_info = point_data.GetDataInformation().GetPointDataInformation().GetArray("Q")
            rng = q_info.GetRange(0)
            q_val = max(1e-12, 0.15 * max(abs(rng[0]), abs(rng[1])))
            qiso = Contour(Input=point_data)
            qiso.ContourBy = ["POINTS", "Q"]
            qiso.Isosurfaces = [q_val]
            qiso.UpdatePipeline(t)
            disp = Show(qiso, view)
            disp.Representation = "Surface"
            set_color(disp, "Q", view, "Q")
            text = add_text(view, f"{case_name}: Q-criterion isosurface, Q = {q_val:.3g} [1/s2]")
            camera_3d(view, lx, ly, lz)
            save_current(view, os.path.join(outdir, "09_Qcriterion_isosurface.png"), args.image_width, args.image_height)
            Hide(qiso, view)
            if text:
                Delete(text)
            Delete(qiso)
        except Exception as exc:
            print("WARNING: Q isosurface failed:", exc)

    # Wall fields: try yPlus and wallShearStress if readable.
    for fld, title in [("yPlus", "wall y+ [-]"), ("wallShearStress", "wall shear stress")]:
        if has_point_array(point_data, fld, t):
            try:
                disp = Show(point_data, view)
                disp.Representation = "Surface With Edges" if fld == "yPlus" else "Surface"
                set_color(disp, fld, view, fld)
                text = add_text(view, f"{case_name}: {title}")
                camera_3d(view, lx, ly, lz)
                save_current(view, os.path.join(outdir, f"10_{fld}_surface.png"), args.image_width, args.image_height)
                Hide(point_data, view)
                if text:
                    Delete(text)
            except Exception as exc:
                print(f"WARNING: {fld} surface plot failed: {exc}")

    print("Done. Figures written to", outdir)


if __name__ == "__main__":
    main()
