# Simulator-to-real calibration specification

This document defines what must be measured on the real AlohaMini1 and matched
in Gazebo or another simulator. It is based on the repository state inspected
on 2026-07-20 and the companion `lerobot_alohamini` checkout at commit
`8e3e1225`.

Calibration should produce a versioned set of measured parameters and
validation results. It should not be a collection of unexplained edits to URDF,
controller, or simulator files.

## What “calibration” means here

Keep three classes of parameter separate:

1. **Portable measured parameters:** frame transforms, joint zeros and signs,
   encoder scale, link dimensions, masses, camera intrinsics/extrinsics, command
   delay, and sensor noise. These should be shared by every simulator and the
   hardware bridge.
2. **System-identification parameters:** motor response, backlash, damping,
   friction, compliance, and payload effects. These are fitted from real motion
   and force data.
3. **Simulator-specific parameters:** Gazebo/DART friction coefficients,
   MuJoCo contact solver settings, Bullet ERP/CFM, controller gains, and similar
   engine knobs. Match measured behavior, but do not copy their raw numeric
   values between physics engines—the coefficients do not have identical
   meanings.

Domain randomization comes after calibration. Randomize around measured values
and uncertainty bounds; do not use randomization to hide a wrong zero, axis, or
unit convention.

## Canonical conventions to freeze first

The following are interface definitions. The real-hardware adapter should map
encoders and motor commands into them, even if the native motor convention is
different.

| Quantity | Canonical definition |
| --- | --- |
| `base_link` | REP-103 body frame: `+X` is chest-forward, `+Y` is robot-left, `+Z` is up |
| Positive base yaw | Counter-clockwise about `+Z` |
| Arm joint position | Radians; `q=0` is the pose represented by the URDF zero transform for that joint |
| Wheel velocity | Radians/s about the URDF joint axis |
| Lift position | Metres above the repeatable mechanical bottom; `q=0` at bottom and positive upward |
| Gripper position | Radians; current simulation convention is `0` open and `-1.57` closed |
| Camera body frame | `+X` forward through the lens and `+Z` up |
| Camera optical frame | REP-103 optical convention: `+Z` forward, `+X` right, `+Y` down |
| Time | Capture/measurement time in one synchronized clock domain, not receipt time |

The fixed `base_link -> base_cad_link` transform currently rotates the original
SolidWorks model by `+pi/2` yaw. Verify physically that chest-forward motion is
`+X`; do not remove the adapter frame merely to make native CAD or motor signs
look simpler.

## Calibration priority

| Priority | Required before | Parameter groups |
| --- | --- | --- |
| P0 | Any safe hardware motion or meaningful kinematics | Frame conventions, bus IDs, joint/wheel signs, zeros, encoder scales, hard/soft limits, command units, watchdogs |
| P1 | Odometry, perception, manipulation planning, or data collection | Wheel geometry, lift scale, arm mount/joint geometry, tool frames, gripper aperture mapping, camera intrinsics/extrinsics, timestamps |
| P2 | Dynamics-sensitive control and useful sim-to-real training | Mass/CoM/inertia, actuator response, backlash, friction, contact, payload behavior, latency and noise distributions |
| P3 | Robustness training | Parameter uncertainty bounds, floor/material variation, lighting, camera noise, wear, temperature, payload variation |

P0 and P1 errors create systematic bias and should be fixed directly. P2 and P3
can be refined according to the task: a UI kinematics demo needs less dynamic
fidelity than contact-rich learned manipulation.

## Base and omni wheels

### Variables to measure

| Variable | Unit | How to measure or identify | Model effect |
| --- | ---: | --- | --- |
| Wheel centre for each wheel in `base_link` | m, xyz | Survey axle centres relative to a marked base origin | Kinematic Jacobian, footprint, collision |
| Wheel drive azimuth and axle direction | rad or unit vector | Measure mount angles; confirm with single-wheel commands | Forward/lateral/yaw direction and coupling |
| Wheel order | names/IDs | Command one motor at a time and observe the matching physical wheel | Prevents correct numbers being applied to the wrong actuator |
| Direction sign per wheel | `+1/-1` | Positive command test with robot safely raised | Command and encoder polarity |
| Effective rolling radius per wheel | m | Roll each wheel through many encoder turns under normal load and fit distance/angle | Linear speed and odometry scale |
| Centre-to-wheel radius | m | Survey centre to contact/drive line; refine from pure-yaw trials | Yaw command and odometry scale |
| Encoder ticks per wheel revolution | ticks/rev | Compare raw encoder change over marked wheel revolutions | Encoder-to-radian conversion |
| Motor-to-wheel gear ratio | ratio | Part numbers plus marked input/output turns | Command/state scaling |
| Roller angle and effective lateral mobility | rad/behavior | Inspect wheel construction; fit lateral motion tests | Omni kinematics and anisotropic slip |
| Wheel width and contact offset | m | Caliper measurement under normal assembly | Ground contact pose and collision geometry |
| Static/kinetic traction by direction | behavior | Pull/drive tests on each target floor | Acceleration, stopping, lateral slip |
| Rolling resistance and deadband | N or command threshold | Low-speed ramp on level floor | Minimum controllable velocity and coast-down |
| Maximum wheel speed/acceleration | rad/s, rad/s^2 | Conservative ramps while logging command and encoder state | Saturation and trajectory realism |
| Base mass, CoM, and yaw inertia | kg, m, kg m^2 | Scale, corner scales, CAD/pendulum identification | Acceleration, load transfer, slip, collision |
| Body footprint and ground clearance | m | Survey outer body and lowest points | Navigation collision and traversability |

### Current values requiring verification

The Gazebo controller currently uses:

- wheel radius `0.0495 m`;
- symmetric centre radius `0.17878 m`;
- first-wheel offset `2.08538632679 rad` in the ROS-aligned frame;
- wheel order `wheel2_joint`, `wheel1_joint`, `wheel3_joint`;
- primitive collision radius `0.0495 m`, width `0.0399 m`, and local lateral
  offset `0.01577 m`.

The companion hardware code instead uses `wheel_radius=0.05 m` and
`base_radius=0.125 m`, with wheel angles `[150, -90, 30] degrees`. The
`0.17878 m` versus `0.125 m` centre-radius difference is too large to treat as
rounding; it indicates either a geometry mismatch or a different, undocumented
definition of radius/origin. Measure the real chassis, reconcile the definition,
and make both adapters consume the same calibration artifact.

Gazebo currently approximates the omni rollers with a smooth cylinder and
directional friction:

- rolling-direction `mu1=5.0`;
- lateral `mu2=0.01`;
- local high-friction direction `fdir1=(1,0,0)`;
- wheel-joint damping `0.5` and friction `0.1`.

These are simulator tuning values, not material measurements. Fit them against
straight, lateral, yaw, diagonal, coast-down, and stopping tests on every floor
material in the intended operating area. The floor matters: tile, wood, carpet,
seams, dust, and payload can change omni-wheel slip substantially.

### Odometry calibration

Use an external reference such as surveyed floor marks, AprilTags, or motion
capture. Repeat each test in both directions:

1. forward and reverse straight runs;
2. left and right lateral runs;
3. clockwise and counter-clockwise rotations;
4. diagonal motion;
5. a square path and a combined translation/yaw path;
6. the same tests with representative payload and on each target floor.

Fit wheel radii, wheel azimuths/positions, scale factors, and—only after the
geometry is correct—slip terms. Estimate odometry covariance from repeated
residuals rather than keeping the current placeholder pose/twist diagonals.

An IMU is not required to command the wheels. It is useful for yaw-rate and
state-estimation correction when wheel slip is significant. If an IMU is added,
calibrate its body-frame transform, axis signs, gyro/accelerometer biases,
scale, noise, temperature drift, and timestamp offset.

## Lift

### Canonical model

The simulator defines `vertical_move` as bottom-relative position in
`[0.00, 0.60] m`, with positive motion upward. The exported CAD pose occurs at
`q=0.40 m`. The physical adapter must home before it can expose this absolute
position contract.

Measure and record:

| Variable | Unit | Notes |
| --- | ---: | --- |
| Repeatable bottom reference | encoder ticks | Define whether zero is the hard stop or a safe backed-off position |
| Homing direction and speed | sign, raw/s or rad/s | Verify current threshold and no-motion detection separately |
| Homing backoff | mm | Execute it physically, then define `q=0`; test at least 20 home cycles |
| Encoder/motor scale | ticks/rev | Nominal STS value is 4096, but verify the complete path |
| Lead and gear ratio | mm/rev, ratio | Companion code assumes `84 mm/rev` and ratio `1.0` for AlohaMini1 |
| Direction sign | `+1/-1` | Companion code currently assumes `-1` |
| Usable lower/upper limits | m | Measure safe travel, not merely rail length |
| Backlash and lost motion | mm | Approach each height from both directions |
| Axis direction and lateral tilt | unit vector/rad | Survey carriage motion relative to `base_link` |
| Maximum velocity/acceleration | m/s, m/s^2 | Measure with the full moving assembly and payload |
| Static holding force/current | N, A | Test at multiple heights and payloads |
| Moving friction and stiction | N or response model | Fit upward/downward separately |
| Position tolerance and settling | mm, s | Include overshoot and repeatability |
| Limit-switch/current-stall behavior | state/A/time | Define fault and recovery behavior |

The current LeRobot lift configuration contains `home_backoff_deg=5`, but the
inspected homing implementation does not command that backoff before setting
zero. Treat the backoff and zero convention as unfinished until a repeated
hardware homing test proves otherwise.

Gazebo uses an effort PID (`p=3000`, `i=500`, `d=200`) to move an approximately
`2.76 kg` CAD-derived core lift subtree. The real hardware uses velocity mode.
Do not copy the Gazebo effort gains to the Pi. Identify the real height response
to the shared position command, then tune each adapter so rise time, overshoot,
settling, saturation, and failure semantics are comparable.

## Actuators and embedded control

The simulator and physical robot should expose the same task-level command
contract even when their internal control differs:

| Mechanism | Task-level command | Typical physical implementation |
| --- | --- | --- |
| Arms | Joint position in radians | Servo position loop |
| Grippers | Joint position or calibrated aperture | Servo position/current-limited grasp logic |
| Wheels | Joint velocity in radians/s | Servo velocity loop |
| Lift | Bottom-relative position in metres | Pi closes a position loop by issuing velocity commands |

For every actuator family, record or identify:

- motor and gearbox model, gear ratio, efficiency, backlash, and reflected
  inertia;
- native command mode and units, command quantization, deadband, and update
  rate;
- encoder location, resolution, filtering, sampling rate, and whether feedback
  is measured before or after the gearbox;
- no-load speed, loaded speed/torque behavior, torque or current constant when
  accessible, and continuous/peak limits;
- internal profile velocity/acceleration, position/velocity gains when
  configurable, saturation, anti-windup, and braking/coasting behavior;
- supply-voltage dependence, battery sag, thermal derating, and over-current or
  over-temperature shutdown behavior;
- command-to-motion delay, feedback delay, jitter, steady error, overshoot,
  settling, and disturbance rejection;
- timeout, disconnect, stall, limit, reboot, and recovery semantics.

If the servo firmware hides its low-level gains or current loop, fit a
black-box closed-loop response from command and encoder/current logs. Do not
invent an inaccurate motor electrical model merely because the simulator
supports one. Likewise, do not stack a detailed simulated servo loop under a
ROS PID unless the real robot actually has both loops; that can double-count
stiffness and damping.

## Arms

Calibrate every left and right arm joint independently. For the current
AlohaMini1 model these are `left_joint1..5` and `right_joint1..5`; joint 6 is
the gripper moving jaw.

### Per-joint calibration record

| Variable | Unit/type | Purpose |
| --- | --- | --- |
| ROS joint name, bus, motor ID, motor model | identifiers | Stable hardware-to-model mapping |
| Parent/child link and physical pivot location | m, xyz | Kinematic chain geometry |
| Rotation axis in the parent/joint frame | unit vector | Correct motion plane |
| Encoder direction | `+1/-1` | Positive ROS motion convention |
| Encoder value at canonical `q=0` | ticks | Zero offset |
| Encoder resolution and gear ratio | ticks/rev, ratio | Tick-to-radian scale |
| Hard lower/upper stop | rad and ticks | Mechanical protection |
| Conservative software limits | rad | Normal command envelope inside hard stops |
| Maximum velocity/acceleration | rad/s, rad/s^2 | Safe commands and trajectory timing |
| Current/torque limit | A or N m | Safety and actuator saturation |
| Backlash/hysteresis | rad | Pose error and direction dependence |
| Static friction, damping, reflected inertia | fitted model | Dynamic response |
| Position-loop response | gain/step metrics | Match rise, overshoot, settle, steady error |
| Command and feedback delay/jitter | ms | Control stability and sim-to-real timing |

A useful initial affine encoder mapping is:

```text
q_ros = direction * (ticks - ticks_at_q0) * 2*pi
        / (ticks_per_motor_rev * motor_revs_per_joint_rev)
```

Do not assume the LeRobot half-turn homing midpoint is the same as URDF
`q=0`. Put the physical arm in a reproducible fixture pose that corresponds to
the chosen URDF zero pose, record every encoder value, and validate the result
with several independent end-effector poses.

The current URDF arm limits (`+/-3.14159 rad`), effort (`50 N m`), and velocity
(`3 rad/s`) are placeholders. Replace them with measured joint-specific values;
a shared limit for all ten joints is unlikely to be accurate.

### Arm geometry and tool frames

Also verify parameters that cannot be fixed by encoder offsets:

- left/right arm-base transforms on the lift carriage;
- distance and orientation between successive joint axes;
- link lengths and mesh scale;
- wrist/tool centre point and grasp reference frame;
- left/right manufacturing asymmetry;
- cable or hard-stop constraints not present in CAD;
- deflection versus arm pose and payload.

Attach a surveyed marker to the tool, measure many poses with an external
reference, and fit zero offsets first. Change link geometry only when residuals
show a repeatable pose-dependent error that offsets cannot explain.

## Grippers

`link5` is the gripper body and serrated static jaw. `link6` is the moving hook
jaw. The current simulator command interval is `0 rad` open to `-1.57 rad`
closed; its URDF hard stops are padded to `[-1.58, 0.01] rad` to avoid a DART
hard-limit pinning issue.

For each side, measure:

| Variable | Unit | Method |
| --- | ---: | --- |
| Unloaded fully-open endpoint | ticks, LeRobot %, rad | Move conservatively to the usable open stop |
| Unloaded fully-closed endpoint | ticks, LeRobot %, rad | Define by minimum jaw gap without damaging the mechanism |
| Direction | sign | Determine whether LeRobot `0` or `100` is open; do not assume |
| Jaw aperture versus encoder position | mm as a function of rad/% | Measure with gauges across the entire range; fit a curve/table if nonlinear |
| Tool/grasp frame versus jaw geometry | m/rad | Survey the useful grasp centre, not only the motor pivot |
| Backlash and repeatability | mm/rad | Approach test positions from open and closed directions |
| Closing speed | rad/s or mm/s | Measure unloaded and with representative objects |
| Grip force versus position/current | N | Use a load cell and several object widths/materials |
| Stall current, velocity threshold, timeout | A, rad/s, s | Separate object contact from jam/fault behavior |
| Jaw/object friction and compliance | behavior/model | Pull-out and retention tests on task objects |
| Collision geometry/contact padding | m | Ensure simulated contact occurs where physical surfaces touch |

Store the mapping between LeRobot's calibrated `[0,100]` value and ROS joint
angle explicitly:

```text
q_ros(p) = q_at_0_percent + (p/100)
           * (q_at_100_percent - q_at_0_percent)
```

For grasping, a gripper command is not only a geometric endpoint. Match the
force/current limit, compliance, stall result, and object-retention behavior.

## Cameras

### Current provisional simulator values

| Camera | Parent | Provisional lens origin xyz (m) | Provisional rpy (rad) |
| --- | --- | --- | --- |
| Chest | `vertical_link` | `(0, -0.032, 0.625)` | `(0, 0, -1.570796)` |
| Head | `base_link` | `(0.102, 0, 1.064)` | `(0, 0.785398, 0)` |
| Rear | `base_link` | `(-0.155, 0, 1.057)` | `(0, 0.63429, 3.141593)` |

All three Gazebo cameras currently use `640x360`, `15 Hz`, an `80 degree`
horizontal field of view, and a pinhole model. These values are provisional.
The physical camera description gives 720p and a `2.4 mm` focal length, but
focal length alone is insufficient to derive field of view without the active
sensor dimensions and selected capture/cropping mode.

### Per-camera calibration record

- actual resolution, crop/binning, pixel format, frame rate, and rotation;
- intrinsic matrix `K`: `fx`, `fy`, `cx`, `cy`;
- distortion model and coefficients `D`;
- calibrated horizontal/vertical field of view derived from `K` and image size;
- rigid transform from the named parent frame to the optical centre;
- optical-frame axis validation;
- autofocus/focus distance, exposure, gain, white balance, and blur behavior;
- capture timestamp accuracy, transport delay, jitter, and inter-camera skew;
- rolling-shutter readout time if motion distortion matters;
- image noise, JPEG/video artifacts, dropout, and frozen-frame behavior.

Use a checkerboard or Charuco board for intrinsics and a surveyed AprilTag board
for base/lift/tool extrinsics. Calibrate the chest camera at several lift heights
to detect carriage tilt or flex. Wrist cameras, when added, require
hand-eye/tool-frame calibration across many arm poses.

The camera visual box and its mass are not camera calibration. The URDF
currently models each camera as `0.020 kg` and `18x36x36 mm`; weigh and measure
the complete camera plus bracket/cable if its inertia or collisions matter.

## Link mass, centre of mass, and inertia

The current CAD-derived core description sums to approximately `8.441 kg`
before the three `0.020 kg` camera bodies; the complete current model is about
`8.501 kg`. The core moving lift subtree is approximately `2.759 kg`, plus the
chest camera and any carried payload.

Verify:

- total robot and subassembly masses;
- CoM of base, lift carriage, each arm link, gripper, cameras, battery, computer,
  cables, and brackets;
- inertia tensors about each link's declared CoM;
- payload mass, CoM, and attachment frame;
- pose-dependent cable forces and structural flex when significant.

Use a scale for mass, multiple support scales or balance tests for CoM, and CAD
updated with actual materials/components for inertia. Pendulum or step-response
identification can refine important inertias. Do not spend equal effort on every
small fastener: prioritize base yaw inertia, the gravity-loaded lift subtree,
arm links, end effector, and task payload.

## Collision and contact

Visual meshes are not automatically good collision models. Calibrate or verify:

- base footprint, protrusions, ground clearance, and wheel guards;
- arm self-collision and arm-to-body collision envelopes;
- gripper contact surfaces and serration/contact approximation;
- contact stiffness, damping, restitution, penetration tolerance, and solver
  stability;
- wheel-floor anisotropic traction and slip;
- jaw-object friction, compliance, and pull-out force;
- collision filtering between adjacent mechanisms;
- task-object mass, CoM, inertia, friction, compliance, and dimensions.

Fit simulator contact behavior to measurable outcomes—stopping distance,
lateral drift, object pull-out force, bounce, grasp retention—not to a desired
friction number. Keep per-engine fits separate.

## Timing, noise, and communication

Measure the complete control and sensing timeline:

- UI/policy command timestamp to Pi receipt;
- Pi command to motor response;
- encoder sampling period and timestamp;
- camera exposure midpoint to published image timestamp;
- network delay, jitter, drops, reordering, reconnect behavior, and watchdog;
- controller update rate and command timeout;
- synchronization error among images, joints, odometry, and actions.

Record distributions, not only averages. Simulate bounded delay, jitter, noise,
quantization, dropped frames, and stale observations only after the real
distributions are measured. Preserve the same timeout and fault semantics in
simulation and hardware.

## Parameter ownership in this repository

| Parameter group | Current owner |
| --- | --- |
| Base frame, joint origins/axes, link geometry, limits, inertials, collision shapes | `AlohaMini1/simulation/src/Aloha/urdf/aloha_description.xacro` |
| Camera bodies, parents, lens/optical transforms | `AlohaMini1/simulation/src/Aloha/urdf/aloha_cameras.xacro` |
| Gazebo camera resolution, rate, FOV, clipping | `AlohaMini1/simulation/src/Aloha/urdf/aloha_gazebo_cameras.xacro` |
| Gazebo wheel directional friction and control plugin | `AlohaMini1/simulation/src/Aloha/urdf/aloha_gazebo.xacro` |
| Wheel kinematics, odometry covariance, controller gains/tolerances | `AlohaMini1/simulation/src/Aloha/config/controllers.yaml` |
| Physics engine, step size, ground and lighting | `AlohaMini1/simulation/src/Aloha/worlds/empty.sdf` |
| Current physical motor/calibration assumptions | companion `lerobot_alohamini/src/lerobot/robots/alohamini/` |
| Recorded learning variables and units | [`lerobot_alohamini_recording_schema.md`](lerobot_alohamini_recording_schema.md) |

Do not permanently duplicate measured numbers in all of these files. Create one
versioned robot calibration artifact and generate/pass its portable values into
simulator and hardware configurations. Keep engine-specific tuning in a
separate overlay.

## Recommended calibration artifact

A practical YAML schema is:

```yaml
schema_version: 1
calibration_id: alohamini1-ROBOT_SERIAL-YYYYMMDD-N
robot_serial: ROBOT_SERIAL
hardware_revision: REVISION
created_at: ISO-8601
source_commit: GIT_COMMIT
units: {length: m, angle: rad, time: s, mass: kg}

conventions:
  base_forward: +X
  base_left: +Y
  base_up: +Z
  lift_zero: safe_backoff_from_bottom
  gripper_zero: fully_open

base:
  mass_kg: null
  com_xyz_m: [null, null, null]
  inertia_kg_m2: [null, null, null, null, null, null]
  wheels:
    - {joint: wheel1_joint, motor_id: null, direction: null,
       centre_xyz_m: [null, null, null], axle_xyz: [null, null, null],
       radius_m: null, encoder_ticks_per_rev: null, gear_ratio: null}
  odometry_covariance: null

lift:
  zero_ticks: null
  home_backoff_m: null
  metres_per_tick: null
  direction: null
  lower_m: null
  upper_m: null
  max_velocity_m_s: null

arms:
  left_joint1:
    motor_id: null
    direction: null
    ticks_at_zero: null
    radians_per_tick: null
    lower_rad: null
    upper_rad: null
    max_velocity_rad_s: null
    max_current_a: null

grippers:
  left:
    q_at_0_percent_rad: null
    q_at_100_percent_rad: null
    open_gap_m: null
    closed_gap_m: null
    max_force_n: null

cameras:
  chest:
    parent: vertical_link
    xyz_m: [null, null, null]
    quat_xyzw: [null, null, null, null]
    resolution: [null, null]
    fps: null
    distortion_model: null
    K: [null, null, null, null, null, null, null, null, null]
    D: []
    latency_s: null

timing:
  motor_command_delay_s: null
  encoder_delay_s: null
  network_delay_s: null

validation:
  procedure_version: null
  date: null
  results: {}
```

Expand repeated entries for all wheels, arm joints, grippers, and cameras. Store
raw measurements and fitting scripts beside the derived YAML so every value is
auditable.

## Recommended calibration sequence

1. Photograph and inventory the exact hardware revision, motor IDs, gearboxes,
   cameras, wheels, firmware, and wiring.
2. Establish safe current/speed limits, physical E-stop, supports, and command
   watchdog before powered tests.
3. Freeze base, joint, lift, gripper, tool, and optical frame conventions.
4. Measure static geometry, masses, joint axes, hard stops, signs, and encoder
   scales with motors unloaded or moving slowly.
5. Implement and repeat lift homing/backoff; define the bottom-relative zero.
6. Calibrate arm zeros and limits, then validate forward kinematics at many
   independent poses.
7. Calibrate gripper endpoints, aperture curve, force/current, and contact.
8. Calibrate camera intrinsics, then base/lift/tool extrinsics and timing.
9. Fit base kinematics and odometry on a low-slip reference floor; repeat on
   operating floors to characterize slip.
10. Identify actuator response, backlash, damping, contact, delays, and noise.
11. Validate with held-out trajectories, poses, payloads, floors, and lighting.
12. Freeze the calibration ID and record it in ROS bags, LeRobot episodes,
    simulator runs, maps, and policy metadata.

Change one parameter class at a time and keep held-out validation runs. Tuning
several coupled values against one trajectory can produce a simulator that fits
that trajectory but is physically wrong elsewhere.

## Initial acceptance targets

These are starting engineering targets, not claims about the present hardware.
Adjust them only from task-level evidence and safety requirements.

| Subsystem | Suggested acceptance test |
| --- | --- |
| Joint mapping | Every positive command moves the documented direction; no command crosses a measured software limit |
| Arm kinematics | Repeated tool-frame position error <=10 mm and orientation error <=2 degrees over held-out poses |
| Lift | Home repeatability <=2 mm; commanded height error <=5 mm over the usable range |
| Gripper | Endpoint repeatability <=1 mm aperture; force/current limit reliably distinguishes grasp from jam |
| Base odometry | <=10 cm translation and <=10 degrees yaw error over the roadmap's 2 m indoor test; report floor and payload |
| Cameras | Tag reprojection error <2 px; camera-to-robot validation error <2 cm and <2 degrees at manipulation distance |
| Synchronization | Image/joint/odometry/action skew <20 ms for recorded policy observations |
| Dynamic response | Rise time, overshoot, settling, saturation, and stopping distance within an agreed 10-20% band on held-out tests |
| Safety | Timeout, disconnect, stale command, limit, over-current, and E-stop tests always reach the defined safe state |

Report mean, standard deviation, worst case, direction, payload, floor, battery
state, and temperature where relevant. A single successful trial is not a
calibration result.

## Minimum set before relying on the simulator

Before using the model for hardware control, odometry, or learned-policy
transfer, complete at least:

- bus/motor inventory and sign tests;
- measured wheel positions, angles, radii, encoder scaling, and odometry trials;
- repeatable lift homing/backoff, scale, and limits;
- all arm zero offsets, signs, encoder-to-radian scales, and safe limits;
- both gripper endpoints, direction, aperture mapping, and safe force/current;
- camera resolution/rate, intrinsics, base/lift extrinsics, and timestamps;
- total/subassembly mass checks and payload definition;
- command/state unit and rate conformance between ROS, Gazebo, and the Pi;
- a versioned calibration ID with held-out validation results.

Until then, the simulator is suitable for interface integration and qualitative
motion checks, but its joint reach, odometry, contact, camera geometry, and
dynamic behavior should not be treated as quantitative predictions of the real
robot.
