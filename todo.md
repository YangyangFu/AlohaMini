# AlohaMini1 — Vision-Only Mobile Manipulation Roadmap

## End demo

From an **arbitrary safe location within a previously mapped house**, a user says or types **"bring me an apple from the kitchen."** The robot:

1. interprets the command;
2. globally relocalizes in a persistent visual map, then navigates to the kitchen using cameras and wheel odometry (no LiDAR);
3. finds an apple on a known countertop;
4. positions the omni base and lift, then grasps the apple;
5. visually locates the requesting person or a designated delivery point;
6. returns, presents the apple, and releases it only after confirmation.

The first complete demo should use a known, pre-mapped home, arbitrary collision-free starting poses within the mapped area, one known countertop, controlled lighting, one apple class, and a stationary requester. The robot may not assume its initial map pose. Generalization to new homes comes after this works reliably.

> Status convention: `[ ]` not started, `[~]` in progress, `[x]` done. Each milestone has an exit criterion so progress is measurable.

---

## Constraints and design choices

- **Vision only for exteroception:** no LiDAR. The baseline hardware has five RGB cameras: top, front, rear, and two wrist/arm cameras.
- **Wheel encoders are allowed:** fuse wheel odometry with vision; do not expect monocular vision alone to provide robust metric scale.
- **No depth camera is assumed:** obtain geometry from calibrated multi-view/stereo where camera overlap permits, visual SLAM, known object size, or learned monocular depth. Treat learned depth as uncertain near transparent, reflective, textureless, or thin objects.
- **Persistent house map is required:** arbitrary starting locations require global visual relocalization before navigation. AprilTags may bootstrap and validate the system, but a taught route between fixed stations is not sufficient.
- **Progressive autonomy:** first build a house-scale visual map with distributed AprilTags as robust relocalization anchors, then replace tag dependence with markerless visual place recognition and localization.
- **Offboard inference is acceptable initially:** Raspberry Pi 5 handles motor I/O and safety; a workstation may run SLAM and policies. Optimize or move inference onboard only after the pipeline works.
- **Safety is independent of perception:** vision can fail. Use an E-stop, deadman during development, command timeouts, speed/force limits, keep-out zones, and a human-supervised release.

### Proposed camera roles

| Camera | Primary role |
|---|---|
| Front/chest | visual navigation, obstacle detection, person/target detection |
| Rear | safe reverse motion and rear obstacle detection |
| Top | wide-context semantic localization and approach planning |
| Left/right wrist | grasp alignment, visual servoing, manipulation policy observations |

[ ] Record actual camera placement, field of view, frame rate, exposure controls, and whether any pair has useful stereo overlap. This determines whether metric stereo is practical.

---

## Current baseline and critical gaps

### Working

- [x] Gazebo Harmonic + ROS 2 Jazzy simulation stack is containerized.
- [x] `ros2_control` + `gz_ros2_control` has five active controllers: wheels, both arms, lift, and joint-state broadcaster.
- [x] Robot model includes a 3-wheel omni base, two 6-DOF arms, and a vertical lift.

### Blocking gaps

- [ ] Add the real follower grippers to URDF, Gazebo, and `ros2_control`; the current model ends at arm joint 6.
- [ ] Add all five RGB camera links, optical frames, intrinsics, and Gazebo sensor plugins. Do **not** add LiDAR to the roadmap.
- [ ] Replace placeholder arm/lift joint limits with measured range, velocity, and effort limits.
- [ ] Implement holonomic `cmd_vel` to wheel velocity mapping and wheel odometry.
- [ ] Inventory the real bus topology, servo IDs, signs, gear ratios, and existing LeRobot interfaces.
- [ ] Define stable ROS interfaces and TF frames shared by simulation and hardware.

---

## Milestone 0 — Safe manual robot

Goal: a person can safely drive and pose the complete robot before autonomy is attempted.

### Simulation

- [ ] Add accurate gripper geometry, collision meshes, transmissions, and controllers.
- [ ] Verify wheel radius and wheel poses/drive angles from CAD or measurements.
- [ ] Implement `base_kinematics`: `/cmd_vel` → three wheel velocities.
- [ ] Implement forward wheel odometry: joint states → `/wheel/odom` and `odom → base_link`.
- [ ] Add a browser/phone-friendly joystick with holonomic X/Y/yaw, speed scaling, deadman, and E-stop controls.
- [ ] Add joint/lift/gripper teleoperation and command watchdogs.

### Hardware

- [ ] Bring up wheels, lift, arms, and grippers through one consistent hardware abstraction (ROS or a thin bridge to the existing LeRobot stack).
- [ ] Calibrate encoder zero, direction, scaling, motion limits, velocity/current limits, and gripper open/closed positions.
- [ ] Add physical E-stop, software command timeout, startup pose checks, and conservative speed limits.
- [ ] Measure base odometry error over forward, lateral, rotation, and square trajectories.

**Exit criterion:** 30 minutes of supervised manual operation with no stale-command motion; drive to within 10 cm / 10° over a 2 m indoor path; stop reliably on deadman release or E-stop.

---

## Milestone 1 — Calibrated vision and data plumbing

Goal: camera observations are synchronized, geometrically meaningful, and identical at the policy boundary in sim and hardware.

- [ ] Publish each camera as `image_raw` + `camera_info` with a stable optical TF frame.
- [ ] Calibrate intrinsics and distortion for all real cameras.
- [ ] Calibrate camera-to-base and wrist-camera-to-tool extrinsics; version the calibration files.
- [ ] Timestamp on the capture computer and synchronize images, joint states, wheel odometry, and commands.
- [ ] Create image health monitoring: frame age/rate, disconnect, frozen frame, excessive blur, and over/under-exposure.
- [ ] Record/replay synchronized ROS bags and LeRobot episodes with command, calibration version, and success metadata.
- [ ] Match sim image size, field of view, rate, topic names, and observation normalization to hardware.
- [ ] Create a calibration validation scene with AprilTags at surveyed poses.

**Exit criterion:** tag reprojection error <2 px, camera-to-robot transform validation <2 cm at manipulation distance, timestamp skew <20 ms for policy observations, and a 20-minute recording with no dropped camera stream.

---

## Simulation data factory — where learning-based control fits

Simulation should generate large, automatically labeled datasets for bounded control skills. Keep global task sequencing, safety checks, and recovery logic explicit in a behavior tree. Train each policy behind a stable observation/action interface so it can be tested independently and replaced without rewriting the demo.

### A. Navigation control data

**Useful simulation data**

- [ ] Generate trajectories from randomized arbitrary start poses to semantic goals using a privileged planner with ground-truth map and geometry.
- [ ] Record synchronized front/rear/top RGB, wheel odometry, robot velocity, goal direction, privileged pose, obstacle geometry, collisions, and expert velocity commands.
- [ ] Randomize furniture layout, people, lighting, textures, camera exposure/blur, wheel slip, latency, and odometry drift.
- [ ] Include recovery examples: blocked paths, localization loss, narrow passages, approaching people, and unsafe expert commands rejected by the safety layer.

**Policies it can train**

- local goal-conditioned visual navigation: images + relative goal → `cmd_vel`;
- visual obstacle avoidance / traversability prediction;
- learned monocular depth or occupancy prediction, supervised by simulator depth and segmentation;
- visual place descriptors for global relocalization, using simulator pose to construct positive/negative image pairs.

**Do not learn initially**

- the metric house map or global pose solely from simulation;
- the final safety stop;
- unrestricted end-to-end language → wheel commands.

Use the real house to build the deployment map. Retain a classical global planner and an independent velocity safety filter even when the local controller is learned.

### B. Base/lift pre-positioning data

**Useful simulation data**

- [ ] Randomize countertop height, apple pose, robot approach error, clutter, arm configuration, and camera calibration perturbations.
- [ ] Use ground-truth geometry and IK/reachability checks to label valid base pose, yaw, lift height, arm choice, collision margin, and predicted grasp reachability.
- [ ] Generate both successful and hard-negative placements near workspace and collision boundaries.

**Policy it can train**

- multi-view RGB + target mask + robot state → base/lift alignment command or target pose.

This is a strong simulation target because labels are cheap and failures on hardware are slow and potentially unsafe.

### C. Apple grasp and manipulation data

**Useful simulation data**

- [ ] Create procedurally randomized apples, countertops, clutter, lighting, camera noise, gripper friction, object mass, and contact parameters.
- [ ] Generate expert demonstrations using scripted grasp sampling, IK, motion planning, privileged object pose, and automatic reset.
- [ ] Record policy observations only from RGB cameras and proprioception; retain privileged state only as training labels or critic inputs that are removed at deployment.
- [ ] Label grasp success, slip, collision, reachability, gripper closure, object retention, and failure reason automatically.
- [ ] Generate corrective trajectories from perturbed states, not only clean successful demonstrations.

**Policies it can train**

- apple detector/segmenter from perfectly rendered masks;
- grasp pose or affordance predictor;
- wrist-camera visual servo policy;
- ACT/Diffusion/Pi-style observation-to-action manipulation policy;
- grasp-success and object-retention estimator.

### D. Handoff data

- [ ] Simulate a bounded presentation task with randomized recipient position, hand pose, robot/person distance, and camera occlusion.
- [ ] Train only approach/presentation pose selection in simulation initially.
- [ ] Keep release confirmation rule-based and human-triggered until extensive real-world safety validation.

### Sim-to-real training recipe

1. Generate a large, diverse simulator dataset with privileged automatic labels.
2. Pretrain perception and control policies in simulation.
3. Validate policies in held-out simulator layouts and perturbations, not the training world.
4. Collect a smaller real dataset using teleoperation and autonomous rollouts with human abort.
5. Fine-tune on mixed real + simulation batches, oversampling real failure cases.
6. Evaluate only on fixed real-world test distributions and report sim-only versus fine-tuned performance.

**Data-factory exit criterion:** one command reproducibly generates versioned episodes with RGB/proprioceptive observations, deployable actions, privileged labels, domain-randomization parameters, and success/failure metadata; a policy pretrained on this data improves real-data sample efficiency over the real-only baseline.

---

## Milestone 2 — House-scale vision-only navigation

Goal: from an unknown initial pose anywhere in the mapped test area, globally relocalize and navigate to a named location without LiDAR.

### 2A. Build and validate the persistent house map

- [ ] Build a house/kitchen Gazebo world with realistic textures, furniture, people, lighting variation, and camera noise.
- [ ] Add automatic episode reset, arbitrary-start sampling, ground-truth state, collision labels, and expert trajectory generation for the navigation data factory.
- [ ] Define the mapped operating boundary, traversable regions, keep-out zones, and named semantic goals (`kitchen`, `counter`, `delivery`).
- [ ] Collect systematic mapping runs that cover rooms, corridors, intersections, and views in both travel directions.
- [ ] Build and save a metric visual map; version it with camera calibration and the physical environment revision.
- [ ] Place distributed AprilTags throughout the mapped area for the first reliable implementation—not only at destination stations.
- [ ] Fuse wheel odometry with tag/visual pose estimates in `robot_localization` (or equivalent) while preserving a separate `map → odom` correction.
- [ ] Implement global initialization: compare live images against the saved map/tag layout, generate pose candidates, reject ambiguous matches, and declare localization only when confidence passes a threshold.
- [ ] Add an active relocalization behavior: rotate/translate cautiously to gather views; stop and report failure if localization remains ambiguous.
- [ ] Implement global planning from the recovered pose to named semantic goals.
- [ ] Implement image-based free-space/obstacle detection for the front and rear cameras.
- [ ] Add a conservative local collision layer or velocity safety filter from visual obstacle estimates.
- [ ] Add kidnapped-robot detection and relocalization when the pose estimate jumps, becomes inconsistent, or tracking is lost.

### 2B. Markerless global relocalization

- [ ] Evaluate RGB visual-inertial/visual-wheel SLAM options against AlohaMini recordings. If no IMU is installed, use visual-wheel odometry or add an inexpensive IMU; this does not violate the no-LiDAR constraint.
- [ ] Select a SLAM/localization backend based on relocalization rate, drift, CPU/GPU load, and lighting robustness—not feature count alone.
- [ ] Add visual place recognition to retrieve candidate map locations from an arbitrary starting image, followed by geometric pose verification.
- [ ] Handle perceptual aliasing explicitly (similar corridors/doors) using multiple views and odometry before accepting a global pose.
- [ ] Associate named semantic places with verified poses in the saved visual map.
- [ ] Configure Nav2 for a holonomic base using the fused pose and a vision-derived local obstacle representation.
- [ ] Add semantic place recognition as a secondary relocalization cue.
- [ ] Add dynamic-person handling: slow down, stop, and replan; never rely on a person remaining visible.

### Validation

- [ ] Sample at least 20 arbitrary starting poses across every mapped room and corridor, including poses facing away from the kitchen.
- [ ] Test day/night lighting, texture-poor walls, motion blur, partial occlusion, moved chairs, and people crossing.
- [ ] Test a kidnapped-robot case by moving the powered robot to another mapped location without updating its pose estimate.
- [ ] Log localization confidence, intervention count, collisions/near misses, time, and final pose error.

**Exit criterion:** across at least 20 arbitrary starting poses covering the mapped test area, ≥90% correct global relocalization without operator pose input, zero confidently accepted wrong-room poses, ≥18/20 collision-free arrivals within 20 cm / 15° of the counter approach pose, successful recovery in ≥9/10 kidnapped-robot trials, and a safe stop on every injected camera/localization failure.

---

## Milestone 3 — Stationary apple manipulation

Goal: with the base parked at the counter, detect, grasp, lift, present, and release an apple.

### Task and perception

- [ ] Fix the first task envelope: counter height/range, reachable workspace, apple varieties, background clutter, lighting, and allowed initial poses.
- [ ] Detect/segment the apple from top/front and wrist views; start with a task-specific detector before open-vocabulary models.
- [ ] Estimate a grasp target from multi-view geometry, known approximate apple size, and/or visual servoing.
- [ ] Add target confidence and reachability checks; abstain and rescan rather than execute a low-confidence grasp.

### Teleoperation and learning

- [ ] Bring up dual leader-arm teleoperation, including grippers and lift/base commands where needed.
- [ ] Define a versioned episode schema: synchronized camera observations, proprioception, actions, language instruction, calibration ID, reset state, and outcome/failure label.
- [ ] Collect a small diagnostic dataset first; visualize timing and action alignment before scaling collection.
- [ ] Collect diverse real demonstrations across apple pose, lighting, clutter, and approach error. Preserve failures where useful.
- [ ] Build a simulation data factory for pretraining and edge cases, with randomized textures, illumination, camera parameters, dynamics, and object poses.
- [ ] Use privileged simulator state to generate expert grasp/correction trajectories and automatic success/failure labels; exclude privileged fields from deployed policy observations.
- [ ] Train a baseline ACT/Diffusion Policy or existing Pi policy; compare real-only vs. sim-pretrained + real-fine-tuned.
- [ ] Run closed-loop evaluation with action clipping, workspace limits, collision checks, and human abort.

### Prefer a hybrid controller

- [ ] Use classical/learned perception for coarse base/lift placement.
- [ ] Use an imitation policy or visual servo controller for final approach and grasp.
- [ ] Use explicit state checks for gripper closure, lift, transport pose, presentation, and confirmed release.

**Exit criterion:** from a parked base, ≥16/20 successful grasps over the defined apple pose range; ≥18/20 safe presentations; zero uncontrolled releases; failures end in abstain/retry rather than collision.

---

## Milestone 4 — Mobile manipulation integration

Goal: compose navigation and manipulation through explicit, observable states.

### Behavior tree / state machine

- [ ] `parse_command` — extract object (`apple`), source (`kitchen counter`), and recipient.
- [ ] `global_relocalize` — recover and verify the initial `map → base_link` pose from live images; actively scan or abort if ambiguous.
- [ ] `navigate_to_kitchen` — globally plan from the recovered arbitrary start pose and reach the kitchen approach area.
- [ ] `localize_counter` — detect the tagged or markerless counter and refine robot pose.
- [ ] `search_for_apple` — scan with top/front cameras and adjust lift if necessary.
- [ ] `select_base_pose` — choose a collision-free pose that puts the target in arm workspace.
- [ ] `servo_base_and_lift` — visually align while respecting reach and stability limits.
- [ ] `grasp_and_verify` — grasp, check closure/visual retention, then move to transport pose.
- [ ] `navigate_to_recipient` — use a fixed delivery point first; person identification later.
- [ ] `present_and_release` — hold a safe pose and release only after voice/button/visual confirmation.
- [ ] `recover_or_abort` — bounded retries for lost localization, missing apple, failed grasp, dropped object, blocked path, or missing recipient.

### Integration sequence

- [ ] Run the full behavior tree with mocked perception and manipulation results.
- [ ] Integrate house-map global relocalization + navigation + scripted grasp in simulation.
- [ ] Integrate house-map global relocalization + navigation + learned grasp on hardware.
- [ ] Replace tags one subsystem at a time: counter localization, navigation, then recipient localization.
- [ ] Keep module-level confidence and failure codes visible in one operator dashboard.

**Exit criterion:** ≥8/10 complete supervised runs in the controlled setup, no collisions or unsafe releases, no more than two autonomous retries per run, and every failure attributable from recorded logs.

---

## Milestone 5 — Robust final demo

- [ ] Replace the fixed delivery point with visual person detection/tracking; identify the requester by explicit interaction, not face recognition by default.
- [ ] Add voice input and a constrained intent grammar. Ask for clarification if object/source/recipient is ambiguous.
- [ ] Test multiple apple appearances, counter positions, start poses, moderate clutter, changing illumination, and pedestrian interruptions.
- [ ] Add a preflight checklist: calibration loaded, all cameras healthy, map available, battery sufficient, workspace clear, E-stop verified.
- [ ] Produce a one-command launch, operator runbook, recovery guide, and automated log bundle.
- [ ] Freeze a reproducible demo configuration: model weights, calibration, maps, dependencies, and hardware revision.

**Final acceptance:** ≥80% end-to-end success over 20 randomized trials across at least two days; 100% safe stop under injected camera, network, localization, and policy failures; no contact with people except the intentional handoff.

---

## Near-term execution order

### Sprint 1 — Make the platform controllable

- [ ] Model both grippers and five cameras.
- [ ] Implement omni-base kinematics and wheel odometry.
- [ ] Build joystick/deadman control in sim, then hardware.
- [ ] Measure and encode real limits and calibration values.

### Sprint 2 — Make observations trustworthy

- [ ] Bring up all real camera streams and TF frames.
- [ ] Complete intrinsic/extrinsic calibration and synchronized recording.
- [ ] Create the AprilTag validation and semantic-station setup.

### Sprint 3 — Prove the two halves independently

- [ ] Build the persistent house visual map and demonstrate global relocalization from arbitrary test poses.
- [ ] Demonstrate kitchen navigation from every mapped room with visual obstacle stopping.
- [ ] Demonstrate stationary teleoperated apple pick-and-present.
- [ ] Record the first well-instrumented manipulation dataset.

### Sprint 4 — Add learning and integration

- [ ] Train/evaluate the first apple grasp policy.
- [ ] Integrate coarse navigation, fine visual alignment, grasp verification, and return.
- [ ] Run repeated trials and prioritize fixes from measured failure frequency.

Markerless global relocalization is required for the intended final demo. Tags are acceptable as an engineering bootstrap and safety reference, but the roadmap should not treat navigation between fixed tagged stations as satisfying the arbitrary-start requirement. Open-vocabulary perception, language models, and generalization to previously unseen houses remain post-demo work.

---

## Metrics to log on every autonomous run

- command parsed correctly;
- initial global relocalization time, confidence, candidate poses, and pose error;
- localization confidence, drift, and relocalizations;
- minimum estimated obstacle distance and safety-filter activations;
- navigation arrival error and duration;
- apple detection confidence and target pose uncertainty;
- selected base/lift pose and reachability margin;
- grasp success, retries, retention, and release confirmation;
- interventions, E-stops, timeouts, dropped frames, and compute latency;
- final outcome and a structured failure code.

The roadmap should be updated from these measurements. A subsystem is not "done" because it worked once; it is done when it meets its exit criterion under the stated test distribution.
