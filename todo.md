# AlohaMini — Vision-Only Mobile Manipulation Roadmap

> Status: `[ ]` not started · `[~]` in progress · `[x]` done
> Architecture: [arch.drawio](arch.drawio)

## 1. Demo contract

From an **arbitrary safe pose in a previously mapped house**, a user says or types:

> “Bring me an apple from the kitchen.”

The robot must:

1. parse the request;
2. globally relocalize without being given its initial map pose;
3. navigate to the kitchen using RGB cameras and wheel odometry;
4. find an apple on a known countertop;
5. align the omni base and lift, grasp the apple, and verify retention;
6. return to the requester or a designated delivery point;
7. present the apple and release it only after explicit confirmation;
8. recover safely or stop with a structured failure reason.

### First-demo operating envelope

- One known, pre-mapped simulated/real house.
- Arbitrary collision-free starts within the mapped operating area.
- One known countertop and one apple class.
- Controlled lighting and moderate, bounded clutter.
- A stationary requester or fixed delivery point.
- Five RGB cameras: chest/front, head/top, rear, and two wrist cameras.
- Wheel encoders are allowed; LiDAR and depth cameras are not assumed.

### Delivery order

1. **Gate A — simulation:** pass the complete task in a mapped Gazebo house.
2. **Gate B — real house:** deploy the same interfaces and behavior tree, then fine-tune only where real evaluation shows a gap.

Autonomous real-house integration starts only after Gate A passes. Hardware bring-up, calibration, teleoperation, mapping, and real-data collection may run earlier because they are prerequisites.

### Out of scope for the first demo

- Previously unseen houses.
- Unrestricted language-to-action control.
- General object retrieval or arbitrary countertops.
- Face recognition or a moving requester.
- Fully learned safety, task sequencing, or global planning.

---

## 2. System architecture

### Deployment boundaries

| Boundary | Responsibilities | Must not depend on |
|---|---|---|
| Operator clients | Web/phone UI, keyboard, gamepad, camera preview, control ownership, release confirmation | Simulator ground truth |
| GPU workstation | UI gateway, behavior tree, SLAM/relocalization, perception, planning, learned policies, visualization, logging, Gazebo | Safety-critical stopping as its only protection |
| Raspberry Pi 5 | Real sensor/motor I/O, hardware bridge, wheel kinematics, odometry acquisition, command watchdog, conservative limits, fault latch | Continuous workstation or network availability |
| Physical robot | Five RGB cameras, encoders, omni base, lift, dual arms, grippers, independent physical E-stop | UI or network for emergency stopping |
| Digital twin | Gazebo integration tests, mapped house, robot/sensor model, randomization, failure injection, privileged training labels | Privileged state at deployed runtime inputs |

Gazebo Harmonic is the primary integration simulator because the ROS 2 Jazzy and `ros2_control` stack already works. MuJoCo is optional for high-throughput manipulation training; it is not the Gate A acceptance environment.

### Runtime command path

`UI / keyboard / gamepad → control ownership → mode manager → safety supervisor → shared ROS 2 commands → simulator adapter or Raspberry Pi hardware bridge`

Operating modes are explicit: `DISABLED`, `MANUAL_BASE`, `MANUAL_WHOLE_BODY`, `AUTONOMOUS`, and `FAULT`.

### Runtime autonomy path

`request → behavior tree → perception/localization → global planner → local navigation or manipulation controller → safety supervisor → robot`

Visualization and logging subscribe to the shared ROS graph; they do not sit in the control path.

### Sim/real parity contract

Simulation and hardware must use the same:

- ROS topics, services, actions, TF frame names, and failure codes;
- behavior-tree states and transition rules;
- camera image shapes, rates, normalization, and calibration schema;
- policy observations, actions, command rates, and timeouts;
- safety supervisor semantics and operating modes.

Only the final adapter differs:

- simulation: `gz_ros2_control` and Gazebo sensor plugins;
- hardware: Raspberry Pi ROS/LeRobot bridge.

Simulator ground truth may be used for labels, training, reset, and scoring, but never as a deployed policy or behavior-tree input.

### Required TF and interface contract

- [~] Freeze the TF tree: `map → odom → base_link → base_cad_link`, wheel frames, lift, arm/tool frames, and five optical frames; the ROS base is now chest-forward while wrist frames and the final contract remain.
- [~] Normalized base commands now use robot-relative `vx` forward (chest-facing), `vy` left, and positive counter-clockwise yaw; verify the same convention in the Raspberry Pi adapter.
- [ ] Define lift, arm, gripper, mode, stop, control-ownership, and release-confirmation interfaces.
- [ ] Define localization, perception, reachability, grasp-retention, and recipient status messages.
- [ ] Define command timestamps, confidence fields, timeout behavior, and structured failure codes.
- [ ] Add interface conformance tests that run against both Gazebo and the hardware bridge.

---

## 3. Baseline and immediate blockers

### Working

- [x] Gazebo Harmonic + ROS 2 Jazzy stack is containerized.
- [x] `ros2_control` + `gz_ros2_control` has wheel, dual-arm, dual-gripper, lift, and joint-state controllers.
- [x] The robot model contains a 3-wheel omni base, two 5-DOF arms, two 1-DOF moving-jaw grippers, and a vertical lift.
- [x] Chest, head, and rear RGB cameras publish simulated `image_raw` + `camera_info` streams with stable optical TF frames.

### Critical path

- [~] Gripper CAD geometry, collisions, `ros2_control` interfaces, and dedicated action controllers exist; validate them and calibrate endpoints/contact behavior against the real follower grippers.
- [~] Chest, head, and rear camera links, optical frames, provisional intrinsics, Gazebo sensors, and ROS bridges are implemented; add the two wrist cameras and replace provisional values after physical calibration.
- [~] The lift now uses a bottom-relative `[0.00, 0.60] m` joint coordinate, with the original CAD pose represented by `0.40 m`; replace placeholder arm/gripper limits and validate lift homing/backoff, endpoints, velocity, and effort on hardware.
- [~] Holonomic `/cmd_vel` mapping is implemented; verify/calibrate wheel geometry on hardware.
- [~] Simulation wheel odometry and `odom → base_link` are implemented; expose real encoder feedback through the Raspberry Pi hardware adapter and validate/calibrate hardware odometry.
- [ ] Inventory the real bus topology, servo IDs, signs, gear ratios, and LeRobot interfaces.
- [ ] Complete the shared ROS/TF interface contract above.

---

## 4. Milestones

### M0 — Safe manual control in simulation and hardware

**Goal:** safely drive and pose the complete robot before autonomy.

#### Operator and safety layer

- [~] A browser MVP commands base, lift, arms, grippers, speed scale, and software base stop; freeze normalized command semantics and add conformance tests before hardware use.
- [ ] Implement gamepad control with holonomic translation, yaw, lift, speed mode, and deadman.
- [ ] Implement keyboard fallback for base, yaw, lift, and stop.
- [~] The browser UI now has connection state, three camera previews, base/arm/lift/gripper controls, joint feedback, and odometry; add ownership, battery/controller health, localization confidence, calibrated limits, and faults.
- [ ] Prevent simultaneous command ownership by multiple clients.
- [ ] Add timestamps, watchdogs, deadman gating, rate/acceleration limits, and a latched fault state.
- [ ] Record operator inputs with synchronized observations and robot state.

#### Simulation and hardware adapters

- [~] Gripper geometry, collisions, and dedicated controllers exist; validate contact behavior and add the real hardware actuator mappings.
- [ ] Verify wheel radius, wheel poses, and drive angles from CAD/measurement.
- [ ] Connect all operator clients to the simulated base, lift, arms, and grippers.
- [ ] Bring up the real actuators through one Raspberry Pi hardware abstraction.
- [ ] Calibrate encoder zero, direction, scaling, motion/current limits, and gripper endpoints.
- [ ] Add an independent physical E-stop, startup checks, command timeout, and conservative hardware limits.
- [ ] Verify deadman release, Wi-Fi loss, browser closure, controller disconnect, and host crash all stop motion.
- [ ] Measure odometry over forward, lateral, rotation, and square trajectories.

**Exit:** all three operator clients use the same command path in sim and hardware; 30 minutes of supervised operation without stale/conflicting commands; ≤10 cm / 10° error over a 2 m indoor path; reliable stop on deadman, disconnect, timeout, mode change, fault, and E-stop.

### M1 — Calibrated vision and reproducible data

**Goal:** policy observations are synchronized, geometrically meaningful, and identical in sim and hardware.

- [ ] Record physical camera placement, field of view, rate, exposure controls, and stereo overlap.
- [~] Chest, head, and rear simulation cameras publish `image_raw` + `camera_info` with stable optical TF frames; add and validate both wrist streams and the hardware publishers.
- [ ] Calibrate and version intrinsics, distortion, base-camera extrinsics, and wrist-tool extrinsics.
- [ ] Timestamp at capture and synchronize images, joints, wheel odometry, and commands.
- [ ] Monitor frame age/rate, disconnects, frozen frames, blur, and exposure.
- [ ] Record/replay ROS bags and LeRobot episodes with calibration ID and outcome metadata.
- [ ] Match sim image size, field of view, rate, names, and normalization to hardware.
- [ ] Build a surveyed AprilTag calibration-validation scene.

**Exit:** tag reprojection error <2 px; camera-to-robot validation <2 cm at manipulation distance; policy-observation skew <20 ms; no dropped camera stream in a 20-minute recording.

### M2 — House-scale vision-only navigation

**Goal:** globally relocalize from an unknown mapped pose and safely reach named places without LiDAR.

#### Map and localization

- [ ] Build a realistic mapped Gazebo house with kitchen, counter, delivery area, clutter, people, and lighting variation.
- [ ] Define operating boundaries, traversable regions, keep-out zones, and semantic goals: `kitchen`, `counter`, and `delivery`.
- [ ] Collect mapping runs covering rooms, corridors, intersections, and both travel directions.
- [ ] Save and version the metric visual map with calibration and environment revision.
- [ ] Bootstrap with distributed AprilTags as relocalization anchors, not only destination markers.
- [ ] Fuse wheel odometry with tag/visual pose while preserving `map → odom` correction.
- [ ] Implement global pose candidate generation, geometric verification, ambiguity rejection, and confidence thresholds.
- [ ] Implement cautious active relocalization and safe failure when ambiguity remains.
- [ ] Detect kidnapped-robot/localization-loss conditions and trigger relocalization.

#### Navigation

- [ ] Implement global planning from the verified pose to named semantic goals.
- [ ] Implement front/rear image-based free-space and obstacle estimation.
- [ ] Add a conservative local collision layer or velocity safety filter.
- [ ] Configure Nav2 for the holonomic base and vision-derived obstacle representation.
- [ ] Slow, stop, and replan around people without assuming they remain visible.

#### Markerless target configuration

- [ ] Evaluate visual-wheel or visual-inertial SLAM on AlohaMini recordings.
- [ ] Select the backend by relocalization rate, drift, compute load, and lighting robustness.
- [ ] Add visual place retrieval followed by geometric pose verification.
- [ ] Resolve similar corridors/doors using multiple views plus odometry before accepting a pose.
- [ ] Associate named semantic places with verified map poses.
- [ ] Remove tag dependence one subsystem at a time while retaining tags for validation/safety reference.

**Exit:** across ≥20 starts spanning every mapped room/corridor, ≥90% correct global relocalization without pose input; zero confidently accepted wrong-room poses; ≥18/20 collision-free arrivals within 20 cm / 15°; ≥9/10 kidnapped-robot recoveries; safe stop for every injected camera/localization failure.

### M3 — Stationary apple manipulation

**Goal:** from a parked base, detect, grasp, lift, present, and safely release an apple.

- [ ] Freeze the task envelope: counter range, reachable workspace, apple appearances, clutter, lighting, and initial poses.
- [ ] Detect/segment the apple from top/front and wrist views with a task-specific baseline.
- [ ] Estimate the grasp target from multi-view geometry, known size, and/or visual servoing.
- [ ] Add target-confidence and reachability checks; rescan instead of executing low-confidence grasps.
- [ ] Bring up leader-arm teleoperation including grippers and required base/lift commands.
- [ ] Validate episode timing/alignment on a small diagnostic dataset before scaling collection.
- [ ] Collect diverse real demonstrations and retain useful labeled failures.
- [ ] Train and compare real-only versus sim-pretrained + real-fine-tuned baselines.
- [ ] Use coarse base/lift placement, closed-loop final approach, grasp verification, and an explicit transport pose.
- [ ] Enforce workspace limits, collision checks, action clipping, and human abort.
- [ ] Keep release rule-based and explicitly confirmed.

**Exit:** ≥16/20 successful grasps over the defined pose range; ≥18/20 safe presentations; zero uncontrolled releases; failures end in abstain/retry rather than collision.

### M4 — End-to-end behavior tree

**Goal:** compose navigation and manipulation through explicit, observable, recoverable states.

| State | Success output | Recovery/failure |
|---|---|---|
| `parse_command` | object, source, recipient | ask for clarification |
| `global_relocalize` | verified map pose | active scan, then abort |
| `navigate_to_kitchen` | kitchen approach reached | replan or safe stop |
| `localize_counter` | counter pose/confidence | rescan or abort |
| `search_for_apple` | target mask/pose | change view or report missing |
| `select_base_pose` | reachable collision-free pose | choose alternate pose |
| `servo_base_and_lift` | aligned robot state | bounded retry |
| `grasp_and_verify` | retained apple in transport pose | retry or report drop |
| `navigate_to_recipient` | delivery pose reached | replan or report missing |
| `present_and_release` | confirmed safe release | hold; never auto-release |
| `recover_or_abort` | bounded recovery or safe stop | structured failure code |

- [ ] Run the complete tree with mocked module outputs and injected failures.
- [ ] Integrate relocalization + navigation + scripted grasp in Gazebo.
- [ ] Replace the scripted grasp with the deployable manipulation controller.
- [ ] Expose state, confidence, retries, and failure codes in one operator dashboard.
- [ ] Limit every recovery loop to explicit retry/time bounds.

**Exit:** ≥8/10 controlled end-to-end simulation runs; no collisions or unsafe releases; ≤2 autonomous retries per run; every failure attributable from recorded logs.

### M5 — Gate A simulation release

- [ ] Use arbitrary unknown safe starts across all simulated rooms and viewing directions.
- [ ] Use only deployable RGB, wheel/joint state, and allowed command context at runtime.
- [ ] Run the exact hardware-target behavior tree, interfaces, observation/action shapes, rates, timeouts, and failure codes.
- [ ] Randomize apple pose/appearance, lighting, textures, furniture, clutter, camera noise, wheel slip, latency, and selected dynamic obstacles.
- [ ] Evaluate held-out world seeds/layouts not used for training.
- [ ] Inject camera dropout, localization loss, network loss, blocked paths, failed grasps, object drops, and missing-recipient cases.
- [ ] Produce a reproducible bundle: world/config seeds, calibration, maps, weights, logs, and one-command launch.
- [ ] Freeze interfaces, behavior tree, models, maps, and configuration after acceptance.

**Gate A acceptance:** ≥16/20 successful held-out end-to-end trials; zero collisions or unsafe releases; 100% safe stop/abort for injected critical sensor, localization, network, and policy failures; every failure explained by state history and a failure code.

### M6 — Gate B real-house release

- [ ] Survey the operating boundary, counter, delivery area, keep-out zones, and emergency access.
- [ ] Recalibrate cameras, kinematics, odometry, lift, arms, and grippers; version the real map with calibration.
- [ ] Validate relocalization, navigation, base/lift alignment, grasp, transport retention, and confirmed handoff independently.
- [ ] Collect teleoperation and correction episodes, then fine-tune only modules with measured sim-to-real gaps.
- [ ] Start with low-speed supervised segmented trials; unlock end-to-end autonomy only after each segment passes its safety test.
- [ ] Add constrained voice input and clarification for ambiguous object/source/recipient.
- [ ] Locate the requester through explicit interaction; do not use face recognition by default.
- [ ] Test start poses, apple appearance/position, clutter, illumination changes, and pedestrian interruptions.
- [ ] Add a preflight check for calibration, camera health, map, battery, workspace, network, and E-stop.
- [ ] Freeze weights, calibration, maps, dependencies, hardware revision, launch command, runbook, and recovery guide.

**Gate B acceptance:** ≥16/20 end-to-end trials over at least two days and arbitrary mapped starts; zero confidently accepted wrong-room poses; no collision, uncontrolled release, or unsafe human contact; 100% safe stop under injected critical failures.

---

## 5. Simulation data factory

**Purpose:** train bounded perception/control skills behind stable interfaces. The behavior tree, global planner, release rule, and final safety filter remain explicit.

### Common episode schema

- [ ] Record synchronized RGB, proprioception, wheel odometry, commands/actions, task context, calibration ID, randomization seed, and outcome/failure label.
- [ ] Store privileged pose, depth, segmentation, contact, and collision state in a separate training/scoring namespace.
- [ ] Version datasets, simulator configuration, expert generator, observation/action schema, and train/test splits.
- [ ] Generate corrective and failure trajectories, not only clean successes.
- [ ] Evaluate on held-out layouts, seeds, and perturbations.

### Navigation data

- [ ] Generate expert trajectories from randomized starts to semantic goals.
- [ ] Randomize layout, people, lighting, texture, blur/exposure, slip, latency, and odometry drift.
- [ ] Include blocked paths, narrow passages, localization loss, approaching people, and rejected unsafe commands.
- [ ] Train/evaluate local goal-conditioned navigation, traversability/obstacle prediction, monocular depth/occupancy, and visual place descriptors.

### Base/lift alignment data

- [ ] Randomize counter height, apple pose, approach error, clutter, arm state, and calibration perturbations.
- [ ] Label base pose, yaw, lift height, arm choice, reachability, and collision margin using privileged geometry/IK.
- [ ] Include hard negatives near workspace and collision boundaries.

### Grasp and handoff data

- [ ] Randomize apples, counter/clutter, lighting, camera noise, friction, mass, and contacts.
- [ ] Generate expert grasp/correction trajectories with scripted sampling, IK, and motion planning.
- [ ] Label grasp, slip, collision, closure, retention, reachability, and failure reason.
- [ ] Simulate bounded presentation-pose selection with varied recipient position and occlusion.
- [ ] Do not train automatic release for the first demo.

### Sim-to-real recipe

1. Generate diverse, automatically labeled simulation data.
2. Pretrain bounded perception/control modules.
3. Validate on held-out simulator distributions.
4. Collect smaller real datasets with teleoperation and human abort.
5. Fine-tune on mixed batches, oversampling real failures.
6. Report sim-only, real-only, and sim-pretrained + real-fine-tuned results.

**Exit:** one command generates versioned episodes with deployable observations/actions, isolated privileged labels, randomization metadata, and outcomes; simulation pretraining measurably improves real-data sample efficiency over the real-only baseline.

---

## 6. Execution order

1. **Platform:** gripper validation/calibration, cameras, measured limits, omni kinematics, odometry, Raspberry Pi bridge.
2. **Manual safety:** shared commands, modes, ownership, deadman/watchdogs, UI/gamepad/keyboard.
3. **Observations:** TF, camera calibration, synchronization, health monitoring, recording/replay.
4. **Independent skills:** arbitrary-start relocalization/navigation and stationary pick/present.
5. **Integration:** behavior tree, visual alignment, grasp verification, return, confirmed handoff.
6. **Simulation release:** held-out trials, randomization, failure injection, Gate A freeze.
7. **Real transfer:** real map/calibration, module tests, targeted fine-tuning, low-speed integration, Gate B.

Markerless relocalization is required for the final Gate A and Gate B configurations. AprilTags are acceptable as an engineering bootstrap and safety reference, but navigation between fixed tagged stations does not satisfy the arbitrary-start requirement.

---

## 7. Run metrics and definition of done

Log on every autonomous run:

- parsed object, source, recipient, and clarification outcome;
- initial relocalization time, candidates, confidence, accepted pose, and pose error;
- localization drift, loss events, and relocalizations;
- minimum estimated obstacle distance and safety-filter activations;
- navigation duration and arrival error;
- apple confidence, target uncertainty, selected base/lift pose, and reachability margin;
- grasp attempts, retention checks, drops, presentation result, and release confirmation;
- behavior-tree states, retries, transitions, and structured failure code;
- interventions, E-stops, timeouts, network loss, dropped frames, and compute latency;
- final outcome plus simulator/config/map/calibration/model versions.

A subsystem is done only when it meets its exit criterion over the stated test distribution. A one-off success is evidence, not completion. Update priorities from measured failure frequency and safety impact.
