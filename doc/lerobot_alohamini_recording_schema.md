# `lerobot_alohamini` recording schema and ranges

This document describes what
`lerobot_alohamini/examples/alohamini/record_bi.py` records, based on companion
repository commit `8e3e1225` inspected on 2026-07-20. It describes the source
code's declared and enforced ranges, not the empirical min/max of a particular
dataset or robot calibration.

## Summary

With the example's default `--robot_model alohamini1`, every recorded frame has:

- `observation.state`: 16 `float32` measured-state values;
- `action`: 16 `float32` requested-command values;
- no camera feature, because the default camera configuration is empty;
- `timestamp`, `frame_index`, `episode_index`, global `index`, and
  `task_index`, which LeRobot adds automatically.

`alohamini2` and `alohamini2pro` add `wrist_yaw` on both arms, making the state
and action vectors 18-dimensional.

The most important caveat is that `action` is the teleoperator request before
the follower's motor normalization, wheel scaling, or lift soft-limit handling.
It is not guaranteed to be the command actually executed by the hardware.

## Default AlohaMini1 vector order

`action` and `observation.state` use the same ordered names. The meanings and
ranges differ because one is a request and the other is feedback.

| Index | Name | Recorded observation | Recorded action |
| ---: | --- | --- | --- |
| 0 | `arm_left_shoulder_pan.pos` | Follower position; default host range `[-100, 100]` normalized | Leader position; default is degrees, approximately `[-180, 180]` |
| 1 | `arm_left_shoulder_lift.pos` | Same normalization as index 0 | Same units as index 0 |
| 2 | `arm_left_elbow_flex.pos` | Same normalization as index 0 | Same units as index 0 |
| 3 | `arm_left_wrist_flex.pos` | Same normalization as index 0 | Same units as index 0 |
| 4 | `arm_left_wrist_roll.pos` | Same normalization as index 0 | Degrees, approximately `[-180, 180]`; leader calibration treats this as a full-turn motor |
| 5 | `arm_left_gripper.pos` | Calibrated `[0, 100]` | Calibrated `[0, 100]` |
| 6 | `arm_right_shoulder_pan.pos` | Follower position; default host range `[-100, 100]` normalized | Leader position; default is degrees, approximately `[-180, 180]` |
| 7 | `arm_right_shoulder_lift.pos` | Same normalization as index 6 | Same units as index 6 |
| 8 | `arm_right_elbow_flex.pos` | Same normalization as index 6 | Same units as index 6 |
| 9 | `arm_right_wrist_flex.pos` | Same normalization as index 6 | Same units as index 6 |
| 10 | `arm_right_wrist_roll.pos` | Same normalization as index 6 | Degrees, approximately `[-180, 180]`; leader calibration treats this as a full-turn motor |
| 11 | `arm_right_gripper.pos` | Calibrated `[0, 100]` | Calibrated `[0, 100]` |
| 12 | `x.vel` | Wheel-feedback-derived forward velocity in m/s; no observation clamp | One of `0`, `+/-0.15`, `+/-0.20`, or `+/-0.25` m/s |
| 13 | `y.vel` | Wheel-feedback-derived lateral velocity in m/s; no observation clamp | One of `0`, `+/-0.15`, `+/-0.20`, or `+/-0.25` m/s |
| 14 | `theta.vel` | Wheel-feedback-derived yaw rate in degrees/s; no observation clamp | One of `0`, `+/-45`, `+/-60`, or `+/-75` degrees/s |
| 15 | `lift_axis.height_mm` | Height relative to the homed bottom in mm; intended operating interval `[0, 600]`, but feedback is not clamped | Current feedback height, or current height `+/-50` mm while a lift key is pressed |

### Arm and gripper range interpretation

The numeric range does not by itself define a physical joint angle:

- In the follower host's default `use_degrees=False` mode, each non-gripper arm
  joint is linearly normalized from its recorded calibration endpoints to
  `[-100, 100]`.
- With `use_degrees=True`, a non-gripper joint is expressed in degrees around
  the midpoint of its calibration range. One servo turn maps to approximately
  `[-180, 180]`; the safe physical range can be narrower.
- Grippers always use `[0, 100]`, independent of `use_degrees`. `0` means the
  calibration `range_min` and `100` means `range_max`. Open/closed direction is
  not inherent in those numbers and must be checked for each calibrated arm.

## Base command range

The keyboard starts at the slow level and selects these command magnitudes:

| Speed level | `abs(x.vel)`, `abs(y.vel)` | `abs(theta.vel)` |
| --- | ---: | ---: |
| Slow | `0.15 m/s` | `45 deg/s` |
| Medium | `0.20 m/s` | `60 deg/s` |
| Fast | `0.25 m/s` | `75 deg/s` |

Forward/backward and left/right keys can be combined, so both `x.vel` and
`y.vel` can be nonzero. Opposing keys cancel. The host converts the body command
to three wheel commands and scales the complete wheel vector if any wheel would
exceed raw speed 3000. Consequently, feedback can be smaller than the recorded
action, especially for combined translation and rotation.

The observation schema does not enforce a numeric velocity bound. Its values
come from measured wheel speeds transformed back into body velocity.

## Lift range

The lift is homed at the mechanical bottom and has configured soft limits of
`0` and `600 mm`. A key press constructs a target 50 mm above or below the most
recent feedback height. The target itself is not clamped before recording.

Therefore:

- the intended action and observation range is `[0, 600] mm`;
- boundary key presses can record a target near `-50 mm` or `650 mm`, even
  though the host blocks motion past its soft limits;
- the host also blocks descent at or below its `5 mm` descent guard;
- `lift_axis.vel` may exist temporarily in the command dictionary, but it is
  not part of the dataset schema and is not recorded.

## Model-dependent arm fields

| `robot_model` | Follower profile | Values per arm | Total state/action size | Required matching leader profile |
| --- | --- | ---: | ---: | --- |
| `alohamini1` | `so-arm-5dof` | 6: five joints plus gripper | 16 | `so-arm-5dof` |
| `alohamini2` | `am-follower-6dof` | 7: six joints plus gripper | 18 | `am-leader-6dof` |
| `alohamini2pro` | `am-follower-6dof-hd` | 7: six joints plus gripper | 18 | `am-leader-6dof` |

The six-DOF profiles insert `wrist_yaw` before `wrist_roll`. The record command
must select a leader profile matching the robot model. For example:

```bash
python examples/alohamini/record_bi.py \
  --dataset USER/DATASET \
  --robot_model alohamini2 \
  --arm_profile am-leader-6dof
```

The complete 18-element order for `alohamini2` and `alohamini2pro` is:

```text
 0  arm_left_shoulder_pan.pos
 1  arm_left_shoulder_lift.pos
 2  arm_left_elbow_flex.pos
 3  arm_left_wrist_flex.pos
 4  arm_left_wrist_yaw.pos
 5  arm_left_wrist_roll.pos
 6  arm_left_gripper.pos
 7  arm_right_shoulder_pan.pos
 8  arm_right_shoulder_lift.pos
 9  arm_right_elbow_flex.pos
10  arm_right_wrist_flex.pos
11  arm_right_wrist_yaw.pos
12  arm_right_wrist_roll.pos
13  arm_right_gripper.pos
14  x.vel
15  y.vel
16  theta.vel
17  lift_axis.height_mm
```

## Camera variables

No cameras are recorded by the current default. `lekiwi_cameras_config()`
returns an empty dictionary; `use_videos=True` does not create video fields by
itself.

The source contains commented examples for these potential fields:

- `observation.images.forward`
- `observation.images.backward`
- `observation.images.chest`
- `observation.images.wrist_left`
- `observation.images.wrist_right`

If enabled as written, each is a video feature with shape `(480, 640, 3)` at a
requested 30 FPS. Arrays are `uint8` with values `[0, 255]`; the camera is
configured for RGB, while the network transport passes it through OpenCV's
JPEG encoder and decoder without a separate color-space tag. The host first
JPEG-compresses each network frame at quality 90, and the dataset later encodes
video, so stored pixels are lossy and need not match the original array exactly.

## Automatically recorded metadata

| Feature | Type | Range or meaning |
| --- | --- | --- |
| `timestamp` | `float32` | `frame_index / fps`; at 30 FPS and a nominal 60-second episode, approximately `0` through `59.967 s` |
| `frame_index` | `int64` | `0` through `N-1` within each episode |
| `episode_index` | `int64` | Episode number; normally `0` through `num_episodes-1` for a new dataset |
| `index` | `int64` | Global frame index across all episodes |
| `task_index` | `int64` | Index into dataset task metadata; normally `0` when one task description is used |

The natural-language `task_description` is stored in dataset task metadata and
referenced by `task_index`. Reset motions between episodes are not recorded,
because the reset `record_loop` is called without a dataset.

## Signals not recorded

The example does not record:

- individual wheel positions or velocities;
- raw servo ticks, homing offsets, or calibration min/max values;
- motor current, torque, temperature, or fault state;
- lift velocity;
- keyboard key states or selected speed level;
- the hardware command after wheel scaling, motor normalization, or lift-limit
  enforcement;
- cameras unless they are explicitly enabled before dataset creation.

## Important consistency issues

### 1. Default arm action and observation units do not match

`SOLeaderConfig` defaults to `use_degrees=True`, so body-joint actions from the
leader are degrees. `LeKiwiConfig` on the follower host defaults to
`use_degrees=False`, so follower body-joint observations and commands use
`[-100, 100]` normalized units. The client schema does not encode which mode the
host is using.

With those defaults, even numerically equal values represent different physical
positions because their scales differ. A recorded action such as `120 degrees`
is additionally interpreted by the follower as normalized `120`, then clipped
to `100`, while the dataset still stores `120`. This makes actions and
observations inconsistent.

The safer current convention is to make the leader match the default follower
normalization explicitly:

```python
SOLeaderConfig(
    port="/dev/am_arm_leader_left",
    arm_profile=args.arm_profile,
    use_degrees=False,
)
```

Apply the same change to the right leader. This gives non-gripper arm actions
and observations the common calibrated range `[-100, 100]`; grippers remain
`[0, 100]`.

Alternatively, set the follower host to `use_degrees=True`, but that choice must
be explicit and consistent for recording, training, evaluation, and replay.

### 2. `action` is requested, not confirmed

The recording loop stores `action_values` before calling `robot.send_action()`.
It does not store the host-side return value after wheel scaling and actuator
limit handling. Treat `action` as the requested target. Use
`observation.state` at the next timestamps to evaluate what the robot achieved.

### 3. Missing remote state silently becomes zero

The client fills absent scalar observation keys with `0.0`. A disconnected or
misconfigured joint can therefore appear as valid zero-valued training data.
Validate dataset statistics and motion traces after every recording session.

## Mapping to this repository's ROS/Gazebo interface

Do not send the LeRobot vectors directly to ROS without unit conversion.

| Quantity | LeRobot example | ROS/Gazebo model in this repository |
| --- | --- | --- |
| Arm position | Degrees or calibrated `[-100, 100]` | Radians |
| Gripper | Calibrated `[0, 100]`, direction hardware-dependent | `0 rad` open, `-1.57 rad` closed |
| `x.vel`, `y.vel` | m/s | m/s |
| `theta.vel` | degrees/s | radians/s; multiply by `pi/180` |
| Lift height | mm | m; divide by 1000 |

For a calibrated gripper percentage `p`, use the measured endpoint mapping
rather than assuming its direction:

```text
q_ros = q_at_0_percent + (p / 100) * (q_at_100_percent - q_at_0_percent)
```

## Checking empirical ranges in a recorded dataset

The real dataset range depends on calibration and demonstrated motion. After
recording, inspect it directly:

```python
import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset("USER/DATASET")

for feature in ("observation.state", "action"):
    values = np.asarray(dataset.hf_dataset[feature], dtype=np.float32)
    names = dataset.features[feature]["names"]
    p01 = np.nanpercentile(values, 1, axis=0)
    p99 = np.nanpercentile(values, 99, axis=0)
    for i, name in enumerate(names):
        print(
            feature,
            name,
            "min=", float(np.nanmin(values[:, i])),
            "p01=", float(p01[i]),
            "p99=", float(p99[i]),
            "max=", float(np.nanmax(values[:, i])),
        )
```

The 1st and 99th percentiles help distinguish normal operating coverage from
single-frame spikes.

## Source locations

- `examples/alohamini/record_bi.py`: dataset construction and recorder options
- `src/lerobot/scripts/lerobot_record.py`: action merge and per-frame save path
- `src/lerobot/robots/alohamini/lekiwi_client.py`: schema order, base levels,
  lift targets, and network client
- `src/lerobot/robots/alohamini/lekiwi.py`: follower observations and actual
  hardware command path
- `src/lerobot/robots/alohamini/model_specs.py`: model-dependent joint lists
- `src/lerobot/robots/alohamini/lift_axis.py`: lift conversion and soft limits
- `src/lerobot/teleoperators/so_leader/`: leader normalization defaults
- `src/lerobot/motors/motors_bus.py`: normalized range conversions
- `src/lerobot/utils/feature_utils.py`: vector and camera dataset features
- `src/lerobot/utils/constants.py`: automatically populated dataset features
