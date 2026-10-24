# -*- coding: utf-8 -*-
"""Step 1 of the preview renders (run with FreeCAD's Python after build_all.py):
tessellates the built models into triangle arrays for tools/render.py."""
import os
import numpy as np
import FreeCAD as App

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "build_tmp")
os.makedirs(OUT, exist_ok=True)

COLORS = {"Leg": (0.62, 0.64, 0.67), "BottomDeck": (0.22, 0.22, 0.26), "TopDeck": (0.36, 0.36, 0.42),
          "Standoffs": (0.45, 0.45, 0.5), "CameraBrackets": (0.9, 0.6, 0.15),
          "Cameras_mock": (0.15, 0.65, 0.3), "RaspberryPi_mock": (0.1, 0.55, 0.2),
          "STM32F4Disco_mock": (0.15, 0.35, 0.75), "DiscoCornerClips": (0.2, 0.45, 0.9),
          "Servo": (0.33, 0.33, 0.36), "Horn": (0.15, 0.15, 0.15), "Chassis": (0.6, 0.6, 0.6),
          "CoxaArm": (0.75, 0.22, 0.17), "FemurBracket": (0.16, 0.5, 0.73),
          "Femur": (0.15, 0.68, 0.38), "Tibia": (0.95, 0.61, 0.07)}


def dump(fcstd, tag, tol, skip=()):
    doc = App.openDocument(fcstd)
    tris, cols = [], []
    for o in doc.Objects:
        if any(o.Label.startswith(s) for s in skip):
            continue
        col = next((c for k, c in COLORS.items() if o.Label.startswith(k)), (0.6, 0.6, 0.6))
        verts, faces = o.Shape.tessellate(tol)
        if not faces:
            continue
        Vv = np.array([[v.x, v.y, v.z] for v in verts])
        T = Vv[np.array(faces)]
        tris.append(T)
        cols.append(np.tile(col, (len(T), 1)))
    np.save(os.path.join(OUT, tag + "_tris.npy"), np.concatenate(tris))
    np.save(os.path.join(OUT, tag + "_cols.npy"), np.concatenate(cols))
    App.closeDocument(doc.Name)


dump(os.path.join(ROOT, "cad", "body", "Hexapod.FCStd"), "hexapod", 1.0)
dump(os.path.join(ROOT, "cad", "leg", "SpiderLeg.FCStd"), "leg", 0.4, skip=("Chassis",))
print("tessellated")
