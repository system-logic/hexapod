# Design notes

Why the hexapod looks the way it does, what was wrong in earlier versions and
how it was fixed, and what is still open.

## 1. Why six legs and these servos

1. **Six legs, not eight.** A hexapod can walk with a tripod gait: three feet are always
   on the ground, so the robot is statically stable at every step. Balance, code and
   debugging are much simpler than with eight legs (24 servos), with almost no loss
   at the start.
2. **Size and torque.** Target size about 30 cm, total mass about 2 kg. The femur joint
   needs about 15–18 kg·cm with a ×2–3 margin, so a 20 kg·cm digital hobby servo
   (DS3218 class) is used for the first prototype.
3. **Why not BLDC yet.** Quasi-direct-drive BLDC motors with field-oriented control
   are the natural next step (torque and speed set electronically, no gearbox
   switching), but hobby servos are the pragmatic start.
4. **Order of work:** build and debug one leg with inverse kinematics first, then copy
   to six. Assembling all six legs at once and debugging them together is the classic
   way to get stuck for months.

## 2. Leg — decisions

1. **Links mount on the servo horn, never on the shaft.** Spline + centre screw +
   4 × M2 + a Ø22 pocket in the link hub (see the README).
2. **Single-sided horn mount.** A double-shear support (bearing on the far side of each
   joint) was considered and postponed. Revisit it if the joints show play under load.
3. **Servos are held by their real flange.** Body window + 4 × M3 on the 49.5 × 10 pattern
   from the DS3218 datasheet.
4. **Foot:** a flat Ø20 pad fused to the tibia, with a Ø11 × 6 socket for a press-fit
   rubber tip (furniture cap). A printed TPU sphere was the alternative.
5. **Lengths for ~30 cm:** `L_FEM = 75`, `L_TIB = 100`. Changing them does not require
   any change to the joints.

## 3. Fixes made along the way

Each of these was found by checking the geometry numerically (volumes, solid count,
overlap volumes), not by eye.

1. Bracket mounting holes did not go through the walls — they were blind pits,
   so there would have been nowhere to put a screw after printing.
2. The tibia foot was a separate body floating in the air (2 solids instead of 1).
3. CoxaArm was bolted to the servo **body** instead of the **horn** — the arm would not
   have rotated.
4. The servo flange pattern was invented (30 × 12) instead of the datasheet value
   (49.5 × 10 at 27.7 mm height).
5. In the assembly the servos were positioned by their top face, so the flange hung
   12.8 mm away from the bracket wall. Now they are positioned by the flange plane,
   and the 4 flange holes of servo and bracket coincide exactly.
6. The femur plate was 16 mm too short (`L_FEM + 32` instead of `L_FEM + 48`),
   which cut off the distal flange.
7. CoxaArm ribs were asymmetric about the S1 axis (centres y = 10 / 24 around y = 17,
   while the shaft is at y = 16) and ran into the horn holes. Now y = 9 / 23,
   starting behind the Ø22 pocket.
8. FemurBracket had no slots for the CoxaArm ribs: the ribs hit the bracket base
   (735 mm³ overlap). Slots with 0.4 mm print clearance were added — overlap 0.
9. The bottom deck was 240 × 256.6 at first; one M3 hole of each 45° leg was outside
   the edge. Margin raised from 28 to 38 mm → 260 × 273.2.
10. The STM32F4-Discovery was first given standoffs, but the board has no mounting
    holes. Replaced by four printed corner clips.
11. (In this repository version) the bottom deck was placed **on top of** the leg's
    Chassis pad, i.e. inside the S1 flange ears. It now replaces the pad: the S1 body
    goes through the deck window and the flange rests on the deck, as on the real robot.

## 4. Left/right legs and servo calibration

The servo mounts are one-sided and identical on both sides, so the left legs are the
right leg turned by 180°, not a mirror copy. With the same shaft angle, a left knee
bends the opposite way to a right knee.

How to handle it in firmware:

1. Write the inverse kinematics **once**, in the leg frame (coxa axis = Z, leg along +X).
2. Convert a foot target from body coordinates to leg coordinates using the leg's mounting
   point and direction (45°, 0°, −45°, 135°, 180°, −135°). This step is where left and
   right differ in position — not the servo table.
3. Convert joint angles to servo commands through a table of 18 rows:
   - **zero** — the pulse that gives the reference pose (coxa along the leg axis,
     femur horizontal, tibia at 90°). It is always individual, because a horn cannot
     be fitted at an exact angle;
   - **sign** — +1 or −1. For femur and tibia it is inverted on the left legs
     (the shaft faces the other way); for coxa it is inverted too ("forward" is the
     opposite rotation on the left);
   - **limits** — min / max, so a joint never runs into the body.
4. Servo command = zero + sign × kinematic angle.
5. Take the zeros from the real robot, not from the drawing: put every servo at mid
   position, fit the horns as close as they go, then tune the zeros in firmware until
   all six legs stand in the same pose.
6. Limit the angles in firmware slightly tighter than the mechanics allow:
   a 20 kg·cm servo hitting a hard stop can strip the spline.

## 5. Power (plan)

Not built yet. These are the numbers the design is based on:

1. Each DS3218 draws about 1–1.5 A under load and up to about 2.5 A stalled. Not all
   18 stall at once, but real peaks during a step are **20–30 A**.
2. Battery: 2S LiPo, about 5000 mAh, 30C.
3. The DS3218 maximum is 6.8 V, so the servos cannot run straight from 2S. A buck
   converter to **6 V, 20–30 A continuous** (or 2–3 UBECs of ~10 A, one per group of legs).
4. **1000–2200 µF** electrolytic capacitors on the servo rail near the connectors —
   otherwise the voltage dips on fast moves will reset the STM32.
5. Servos are powered only from this rail. The STM32 and the Raspberry Pi have their own
   regulator. Common ground.
6. Thick wires to the servos.

## 6. Body

1. Thin laminate flexes over a 260 mm span. The main stiffening is the top deck on
   standoffs (two plates + standoffs act as one thick beam). If more is needed, in
   order of effort: glue a second laminate layer with epoxy; aluminium angle
   10 × 10 × 1 along the long edges, flange up, M3 every 40–50 mm; printed PETG ribs.
2. Acrylic for the top deck cracks around holes if screws are over-tightened:
   drill 0.3–0.5 mm oversize, use washers, tighten gently. PETG sheet or 1.5–2 mm
   laminate are more forgiving.
3. Route all servo harnesses inward through the cable holes while access is still easy.
4. With the femur nearly horizontal the stance is wide and stable, but the femur servo
   torque is at its maximum. If the servos get warm standing still, bend the knees a
   little and raise the body.

## 7. Known issues in the current models

1. **S2 and S3 flange ears sit inside the bracket wall / femur plate in the assembly**
   (about 545 mm³ overlap each, see `build_report.txt`). The printed parts are correct
   (window + holes); only the servo position in the assembly view is 2.5 mm off.
   To be fixed once it is confirmed which face of the wall the flange rests against.
2. **The front S1 flange ears touch the STM32 corner clips** (1.3 mm³ — a corner graze)
   in the model. To be checked on the real robot.
3. **Camera bracket hole pattern is for the Pi Camera v2 (21 × 12.5, M2).**
   The cameras actually used are Waveshare IMX296 modules, whose hole pattern may differ.
4. In the model the Raspberry Pi standoffs are fused into the deck (a printed-deck
   assumption). With a cut laminate deck use 6 mm M2.5 brass standoffs instead.
5. `Assembly_SpiderLeg.FCMacro` contains its own copy of every part builder. If a
   dimension is changed in a part macro, it must also be changed there.
