# -*- coding: utf-8 -*-
"""
build_all.py — rebuild every model and export file from the macros, headless.

Usage (FreeCAD 1.x, from the repository root):
    freecadcmd cad/build_all.py            (Linux / macOS)
    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" cad\\build_all.py   (Windows)

What it produces:
    cad/leg/SpiderLeg.FCStd          one assembled leg (input for Hexapod.FCMacro)
    cad/body/Hexapod.FCStd           full robot
    stl/*.stl                        print-ready parts (already laid flat)
    step/*.step                      the same parts + assemblies as STEP
    build_report.txt                 validity, volume, size and collision checks
"""
import os
import sys
import FreeCAD as App
import Part
import Mesh
import MeshPart

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LEG = os.path.join(ROOT, "cad", "leg")
BODY = os.path.join(ROOT, "cad", "body")
STL = os.path.join(ROOT, "stl")
STEP = os.path.join(ROOT, "step")
os.makedirs(STL, exist_ok=True)
os.makedirs(STEP, exist_ok=True)

V = App.Vector
report = []


def log(line):
    report.append(line)
    print(line)


def run_macro(path, name="__main__", extra=None):
    g = {"__name__": name, "__file__": path}
    if extra:
        g.update(extra)
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), g)
    return g


def fresh_doc(name):
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    return App.newDocument(name)


def lay_flat(shape, axis):
    """Rotate so the large flat face lies on the print bed, then put it on z=0."""
    s = shape.copy()
    if axis == "x+90":
        s.rotate(V(0, 0, 0), V(1, 0, 0), 90)
    elif axis == "x-90":
        s.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    bb = s.BoundBox
    s.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))
    return s


def export_stl(shape, path):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                               AngularDeflection=0.2, Relative=False)
    m.write(path)
    return m


def describe(name, s, mesh=None):
    bb = s.BoundBox
    extra = ""
    if mesh is not None:
        extra = "  mesh facets=%d closed=%s" % (mesh.CountFacets, mesh.isSolid())
    log("  %-18s valid=%s solids=%d volume=%8.0f mm3 (~%4.0f g PLA)  size %.1f x %.1f x %.1f%s"
        % (name, s.isValid(), len(s.Solids), s.Volume, s.Volume * 1.24 / 1000,
           bb.XLength, bb.YLength, bb.ZLength, extra))


# --------------------------------------------------------------- 1. leg parts
# (macro file, object name, print orientation)
PARTS = [
    ("CoxaArm.FCMacro", "CoxaArm", None),          # base down, as modelled
    ("FemurBracket.FCMacro", "FemurBracket", None),  # base down, as modelled
    ("Femur.FCMacro", "Femur", "x-90"),            # flat face down
    ("Tibia.FCMacro", "Tibia", "x-90"),            # flat face down
    ("Horn.FCMacro", "Horn", None),                # optional spare
    ("DS3218.FCMacro", "DS3218", None),            # reference only, not printed
]
log("== Leg parts ==")
for macro, obj, orient in PARTS:
    doc = fresh_doc("SpiderLeg")
    run_macro(os.path.join(LEG, macro))
    s = doc.getObject(obj).Shape
    s.exportStep(os.path.join(STEP, obj + ".step"))
    mesh = None
    if obj != "DS3218":
        mesh = export_stl(lay_flat(s, orient), os.path.join(STL, obj + ".stl"))
    describe(obj, s, mesh)

# --------------------------------------------------------------- 2. leg assembly
log("== Leg assembly ==")
doc = fresh_doc("SpiderLeg")
run_macro(os.path.join(LEG, "Assembly_SpiderLeg.FCMacro"))
leg_file = os.path.join(LEG, "SpiderLeg.FCStd")
doc.saveAs(leg_file)
objs = {o.Name: o.Shape for o in doc.Objects}
log("  bodies: %d (%s)" % (len(objs), ", ".join(objs)))
Part.makeCompound(list(objs.values())).exportStep(os.path.join(STEP, "SpiderLeg_Assembly.step"))
# rib / slot check: CoxaArm vs FemurBracket must not overlap
ov = objs["CoxaArm"].common(objs["FemurBracket"]).Volume
log("  CoxaArm x FemurBracket overlap: %.3f mm3 (expected 0 — ribs sit in the slots)" % ov)
for a, b in [("Femur", "Tibia"), ("CoxaArm", "Servo_S2"), ("FemurBracket", "Servo_S2"), ("Femur", "Servo_S3"), ("Tibia", "Servo_S3")]:
    log("  %s x %s overlap: %.3f mm3" % (a, b, objs[a].common(objs[b]).Volume))

# --------------------------------------------------------------- 3. full hexapod
log("== Hexapod ==")
for d in list(App.listDocuments().values()):
    App.closeDocument(d.Name)
g = run_macro(os.path.join(BODY, "Hexapod.FCMacro"), name="hexapod_lib")
g["LEG_FILE"] = leg_file
hdoc = g["main"]()
hex_file = os.path.join(BODY, "Hexapod.FCStd")
hdoc.saveAs(hex_file)
H = {o.Label: o for o in hdoc.Objects}
for n in ("BottomDeck", "TopDeck", "Standoffs", "CameraBrackets", "DiscoCornerClips"):
    bb = H[n].Shape.BoundBox
    log("  %-17s X[%7.1f, %7.1f] Y[%7.1f, %7.1f] Z[%6.1f, %6.1f]"
        % (n, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
body = ["BottomDeck", "TopDeck", "Standoffs", "CameraBrackets", "DiscoCornerClips",
        "RaspberryPi_mock", "STM32F4Disco_mock", "Cameras_mock"]
bad = 0
for i in range(1, 7):
    L = H["Leg_%d" % i]
    ls = L.Shape.copy()
    ls.Placement = L.Placement
    for bn in body:
        v = ls.common(H[bn].Shape).Volume
        if v > 0.5:
            log("  OVERLAP Leg_%d x %s: %.1f mm3" % (i, bn, v))
            bad += 1
for a, b in [("RaspberryPi_mock", "Standoffs"), ("STM32F4Disco_mock", "Standoffs"),
             ("RaspberryPi_mock", "STM32F4Disco_mock"), ("DiscoCornerClips", "Standoffs"),
             ("DiscoCornerClips", "RaspberryPi_mock"), ("CameraBrackets", "STM32F4Disco_mock")]:
    v = H[a].Shape.common(H[b].Shape).Volume
    if v > 0.5:
        log("  OVERLAP %s x %s: %.1f mm3" % (a, b, v))
        bad += 1
log("  overlaps found: %d" % bad)
# every leg M3 hole must be surrounded by deck material
deck = H["BottomDeck"].Shape
worst = 100.0
for x, y, a in g["LEG_MOUNTS"]:
    for hx, hy in g["CHASSIS_HOLES"]:
        gx, gy = g["rot_pt"](hx, hy, a)
        ring = g["cyl"](3.6, 2, x + gx, y + gy, -15.8).cut(g["cyl"](1.65, 2, x + gx, y + gy, -15.8))
        worst = min(worst, ring.common(deck).Volume / ring.Volume * 100)
log("  leg M3 holes: worst material ring around a hole = %.0f %% (100 = fully inside the deck)" % worst)
shapes = []
for o in hdoc.Objects:
    s = o.Shape.copy()
    s.Placement = o.Placement
    shapes.append(s)
Part.makeCompound(shapes).exportStep(os.path.join(STEP, "Hexapod_Assembly.step"))
deck.exportStep(os.path.join(STEP, "BottomDeck.step"))
H["TopDeck"].Shape.exportStep(os.path.join(STEP, "TopDeck.step"))

# --------------------------------------------------------------- 4. body printed parts
log("== Body printed parts ==")
br = g["make_camera_bracket"]()
br.exportStep(os.path.join(STEP, "CameraBracket.step"))
m = export_stl(lay_flat(br, "x+90"), os.path.join(STL, "CameraBracket.stl"))  # plate back on the bed
describe("CameraBracket", br, m)
clip = g["make_corner_clip"]()
clip.exportStep(os.path.join(STEP, "DiscoCornerClip.step"))
m = export_stl(lay_flat(clip, None), os.path.join(STL, "DiscoCornerClip.stl"))   # shelf down
describe("DiscoCornerClip", clip, m)

with open(os.path.join(ROOT, "build_report.txt"), "w", encoding="utf-8") as f:
    f.write("Generated by cad/build_all.py with FreeCAD %s\n\n" % ".".join(App.Version()[:3]))
    f.write("\n".join(report) + "\n")

# Hexapod.FCMacro also saves a copy next to the leg file, and FreeCAD writes
# .FCBak backups when overwriting — remove both.
import glob
for p in [os.path.join(LEG, "Hexapod.FCStd")] + glob.glob(os.path.join(ROOT, "cad", "*", "*.FCBak")):
    if os.path.exists(p):
        os.remove(p)
print("done")
