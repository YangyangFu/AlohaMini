# AlohaMini — Capability Roadmap

Three target capabilities, each developed **in simulation first, then on hardware**:

1. **Navigation** — "go to the TV", "go to the kitchen" (mobile base).
2. **Manipulation** — imitation-learning policies driving the arms from a human command (ALOHA lead/follower data collection).
3. **Mobile manipulation** — move clothes from the washer to the dryer (navigation + manipulation together).

> Convention below: `[ ]` = not started, `[~]` = in progress, `[x]` = done. Nest sim vs. hardware under each item.

---

## Current state (baseline)

- **Sim stack:** Gazebo Harmonic + ROS 2 Jazzy, containerized (KasmVNC browser view).
- **Control:** `ros2_control` + `gz_ros2_control` **working & verified** — 5 controllers active:
  wheels (velocity), both arms (trajectory/position), lift (position), joint-state broadcaster.
  Base holds position (no drift).
- **Robot:** 3-wheel **omni** base + **2× 6-DOF arms** + prismatic **vertical lift**.

### Known gaps in the model (block everything below)

- [ ] **No grippers.** Arms are `left_joint1..6` / `right_joint1..6` only — no gripper/finger joints. Manipulation needs an end-effector.
- [ ] **No sensors.** No camera, depth, LiDAR, or IMU in the URDF. Nav needs range/odom sensing; manipulation needs cameras.
- [ ] **Placeholder joint limits.** Arm/lift limits are invented (±3.14 rad, 0–0.20 m). Must be replaced with measured values.
- [ ] **No holonomic base controller.** Only per-wheel velocity commands; no `cmd_vel` → wheel-speed mapping or odometry yet.

---

## Phase 0 — Foundations (shared prerequisites for all three)

### 0.1 Model fidelity (sim)
- [ ] Add **gripper** joints/links to each arm (parallel-jaw or the real EE); expose in `ros2_control`.
- [ ] Add **sensors** to the URDF + Gazebo:
  - [ ] Base: 2D LiDAR **or** forward depth camera (for nav costmaps).
  - [ ] Arms: wrist camera on each arm + one overhead/base camera (for manipulation).
  - [ ] IMU on the base (odometry fusion).
- [ ] Measure & set **real joint limits** (range, velocity, effort) — replace placeholders. *Do not infer from mesh geometry.*
- [ ] Verify base geometry constants from URDF: wheel positions `(xᵢ,yᵢ)`, drive angles `δᵢ`, wheel radius `r`.
- [ ] Sanity-check masses/inertias against the real robot (matters for dynamics/manipulation contact).

### 0.2 Base kinematics & odometry (sim → shared by nav + mobile-manip)
- [ ] `base_kinematics` node: subscribe `/cmd_vel` (`Twist`/`TwistStamped`) → publish wheel-speed `Float64MultiArray`.
- [ ] Forward kinematics odometry: wheel states → `/odom` + `odom→base_link` TF.
- [ ] Validate: commanded twist vs. measured motion in Gazebo (holonomic vx, vy, ω).

### 0.3 Hardware bring-up (real robot) — do once, reused by all
- [ ] Inventory actuators/sensors: audit `AlohaMini1/hardware/` and `software/`; list motor models, buses (Dynamixel? CAN? EtherCAT?), driver SDKs.
- [ ] Write **real `ros2_control` hardware interface plugin(s)** (arms, wheels, lift, grippers) exposing the *same* position/velocity interfaces as sim — so controllers/policies port unchanged.
- [ ] **Motor calibration** (per joint):
  - [ ] Encoder zero / home position for every arm & lift joint.
  - [ ] Direction (sign) convention vs. URDF axis.
  - [ ] Gear ratio / ticks-per-rad scaling.
  - [ ] Current/torque and velocity limits (safety).
  - [ ] Per-joint PID / gain tuning.
  - [ ] Gripper calibration (open/close range, force limit).
  - [ ] Wheel motor direction + velocity-loop tuning; confirm `r` and layout match URDF.
- [ ] Onboard compute set up (e.g. Jetson/mini-PC): ROS 2 Jazzy, time sync, autostart.
- [ ] Safety: E-stop, joint/current watchdogs, workspace/collision limits, deadman for teleop.
- [ ] Bench validation: `ros2_control` on hardware, echo `/joint_states`, move each joint safely, verify against sim behavior.

---

## Workstream 1 — Navigation ("go to X")

### 1.S Simulation
- [ ] Build a **house world** in Gazebo (rooms, furniture, washer/dryer for later reuse).
- [ ] **SLAM** to build a map (`slam_toolbox` or `cartographer`) driving the base around.
- [ ] **Localization** (AMCL or slam_toolbox localization mode) on the saved map.
- [ ] **Nav2** bring-up: costmaps, planner, **holonomic-capable controller** (e.g. MPPI to use vy), behavior tree, recovery.
  - [ ] Tune footprint/inflation for the omni base; confirm holonomic motion is exploited.
- [ ] **Semantic locations:** a named-waypoint store ("TV", "kitchen", "washer", "dryer") → map poses (YAML/DB + a small service).
- [ ] **Command → goal:** natural-language / keyword layer ("go to the kitchen") → look up pose → send Nav2 goal.
  - [ ] Start with keyword mapping; optionally add an LLM intent parser later.
- [ ] End-to-end test: type/speak a location, robot navigates there in sim; measure success rate & safety.

### 1.H Hardware
- [ ] Mount + driver-integrate the nav sensors (LiDAR/depth, IMU) chosen in 0.1.
- [ ] Real base hardware interface + calibration (from 0.3).
- [ ] Map the **real house**; save map + re-record semantic waypoints.
- [ ] Tune Nav2 for real sensor noise, floor friction, dynamic obstacles (people/pets).
- [ ] Safety pass: bump/e-stop, speed caps, recovery behaviors.
- [ ] Field test: named-location commands in the real house.

---

## Workstream 2 — Manipulation (imitation learning, arms only)

> ALOHA-style: **leader** arms teleoperate **follower** arms to record demonstrations; train an
> imitation-learning policy (e.g. ACT / Diffusion Policy via LeRobot); condition on human command.

### 2.S Simulation
- [ ] Finalize arm + **gripper** model and wrist/overhead **cameras** (0.1) in a manipulation scene (table + objects).
- [ ] **Teleoperation in sim** for data collection: leader-arm device, SpaceMouse/VR, or scripted/replay if no leader hardware yet.
- [ ] **Data pipeline:** record synchronized observations (camera images, joint states) + actions at fixed rate; store in LeRobot dataset format.
- [ ] Define 1–2 **benchmark tasks** (e.g. pick-place a cube, fold a towel) with reset & success criteria.
- [ ] **Train** a policy (ACT or Diffusion Policy); **language-condition** it on the human command.
- [ ] Closed-loop **eval in sim**; iterate on data quantity/quality; measure success rate.

### 2.H Hardware
- [ ] Physical **leader + follower** arm setup; calibration incl. grippers (0.3).
- [ ] Camera mounting + drivers; verify obs match sim topics/shapes (for sim→real transfer).
- [ ] **Teleop data collection** on real hardware (many demos per task).
- [ ] Train / fine-tune policy on real data (optionally sim-pretrained).
- [ ] Deploy with safety envelope; evaluate; iterate (DAgger / more demos).

---

## Workstream 3 — Mobile Manipulation (washer → dryer)

> Depends on Workstreams 1 and 2. This is the integration + task-planning layer.

### 3.S Simulation
- [ ] Reuse the house world; add **washer + dryer + clothes** (deformable/rigid proxies) as a manip scene.
- [ ] **Task decomposition** (behavior tree / state machine): navigate→washer → perceive clothes →
      position base → grasp → navigate→dryer → position → place → repeat/verify empty.
- [ ] **Base placement for manipulation:** compute a good stand pose so targets are in arm reach (use the lift).
- [ ] **Perception:** detect/segment clothes, estimate grasp (start scripted/heuristic, then learned).
- [ ] Integrate nav (WS1) + manip policy (WS2); handle handoffs and failure recovery.
- [ ] Optional: **language task planner** ("move clothes from washer to dryer") → sub-goals.
- [ ] End-to-end sim runs; measure task success & failure modes.

### 3.H Hardware
- [ ] Combine calibrated base + arms + sensors on the real robot.
- [ ] Whole-body validation: navigate, then manipulate at each station (reach, stability, no tip-over).
- [ ] Real washer/dryer trials; tune grasps for real fabric; robustness to clutter/lighting.
- [ ] Safety + reliability hardening; measure end-to-end success rate.

---

## Suggested ordering

1. **Phase 0.1–0.2** (model gaps + base kinematics in sim) — unblocks everything.
2. **WS1.S** and **WS2.S** in parallel (independent in sim).
3. **Phase 0.3** hardware bring-up + calibration (can start once sim interfaces are stable).
4. **WS1.H**, then **WS2.H**.
5. **WS3** (sim then hardware) last — it composes the other two.
