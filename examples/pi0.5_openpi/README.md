# Pi-0.5 for Alohamini
<img src="video\deploy.gif" width="720">

This tutorial is designed for the official [OpenPI] repository, not the built-in Pi-0.5 implementation provided in LeRobot.

It introduces modifications based on both the [OpenPI] project and the [lerobot_alohamini] project to enable fine-tuning training and real-world deployment.

[openpi]: https://github.com/Physical-Intelligence/openpi.git
[lerobot_alohamini]: https://github.com/liyiteng/lerobot_alohamini.git

Technical Principle — Running Pi-0.5 on AlohaMini (16/18-DoF):
- Pi-0.5 uses an internal 18D action space.
- If your robot is 16-DoF, add virtual joints to align 16 -> 18.
- If your robot is 18-DoF, use direct passthrough (no virtual joints).

First, add `alohamini_policy.py` to the `policies` folder in the **openpi** project. The specific code is provided in this folder.

Then, add the following modifications to the `/src/openpi/training/config.py` file.

```python
@dataclasses.dataclass(frozen=True)
class LeRobotAlohaMiniDataConfig(DataConfigFactory):
    default_prompt: str | None = None
    bgr_to_rgb: bool = False
    flip_images_hw: bool = False
    robot_dof: int = 16  # 16 or 18
    dataset_action_dim: int = 16
    use_delta_actions: bool = True

    delta_action_mask: tyro.conf.Suppress[Sequence[bool]] = dataclasses.field(
        default_factory=lambda: [True] * 18
    )

    repack_transforms: tyro.conf.Suppress[_transforms.Group] = dataclasses.field(
        default=_transforms.Group(
            inputs=[
                _transforms.RepackTransform(
                    {
                        "images": {
                            "cam_high": "observation.images.head_top",
                            "cam_left_wrist": "observation.images.wrist_left",
                            "cam_right_wrist": "observation.images.wrist_right",
                        },
                        "state": "observation.state",
                        "actions": "action",
                    }
                )
            ]
        )
    )

    action_sequence_keys: Sequence[str] = ("action",)

    @override
    def create(self, assets_dirs: pathlib.Path, model_config: _model.BaseModelConfig) -> DataConfig:
        if self.robot_dof not in (16, 18):
            raise ValueError(f"robot_dof must be 16 or 18, got {self.robot_dof}")

        expanded_dim = 18  # Pi0.5 internal action space
        data_transforms = _transforms.Group(
            inputs=[
                alohamini_policy.AlohaMiniInputs(bgr_to_rgb=self.bgr_to_rgb),
                alohamini_policy.AlignToPi05ActionSpace(robot_dof=self.robot_dof),
            ],
            outputs=[
                alohamini_policy.AlohaMiniOutputs(internal_dim=18, robot_dof=self.robot_dof)
            ],
        )
        if self.flip_images_hw:
            data_transforms = _transforms.Group(
                inputs=[
                    alohamini_policy.AlohaMiniInputs(bgr_to_rgb=self.bgr_to_rgb),
                    _transforms.FlipImages(flip_h=True, flip_w=True),
                    alohamini_policy.AlignToPi05ActionSpace(robot_dof=self.robot_dof),
                ],
                outputs=data_transforms.outputs,
            )

        if self.use_delta_actions:
            mask = list(self.delta_action_mask)
            if len(mask) != 18:
                raise ValueError(
                    f"delta_action_mask length must be 18, got {len(mask)}")
            data_transforms = data_transforms.push(
                inputs=[_transforms.DeltaActions(mask)],
                outputs=[_transforms.AbsoluteActions(mask)],
            )

        model_transforms = ModelTransformFactory(
            default_prompt=self.default_prompt)(model_config)

        return dataclasses.replace(
            self.create_base_config(assets_dirs, model_config),
            repack_transforms=self.repack_transforms,
            data_transforms=data_transforms,
            model_transforms=model_transforms,
            action_sequence_keys=self.action_sequence_keys,
        )

```

```
TrainConfig(
        name="alohamini2pro",
        model=pi0_config.Pi0Config(pi05=True, action_horizon=10),
        data=LeRobotAlohaMiniDataConfig(
            repo_id="/path/to/your/dataset_root",
            base_config=DataConfig(prompt_from_task=True),
            default_prompt="your job description",
            robot_dof=18,
            dataset_action_dim=18,
            use_delta_actions=True,
            repack_transforms=_transforms.Group(
                inputs=[
                    _transforms.RepackTransform(
                        {
                            "images": {
                                "cam_high": "observation.images.chest",
                                "cam_left_wrist": "observation.images.wrist_left",
                                "cam_right_wrist": "observation.images.wrist_right",
                            },
                            "state": "observation.state",
                            "actions": "action",
                            "prompt": "prompt", # This parameter must be added, otherwise the model training will not include the task description
                        }
                    )
                ]
            ),
            # AlohaMini2Pro is native 18D: arm joints are trained as deltas,
            # grippers/base/lift stay absolute.
            delta_action_mask=[
                True, True, True, True, True, True, False,
                True, True, True, True, True, True, False,
                False, False, False, False,
            ],
            assets=AssetsConfig(
                assets_dir="/path/to/your/asset/path",
                asset_id="/dataset/file/name", # assets_dir and assed_id form your dataset path, the path is equivalent to repo_id
            ),
        ),
        weight_loader=weight_loaders.CheckpointWeightLoader(
            "gs://openpi-assets/checkpoints/pi05_base/params",
        ),
        num_train_steps=50000,
        batch_size=4,
        num_workers=2,
        wandb_enabled=False,
    ),
```

Note: Here, the **pi0.5_base** weights are used for fine-tuning training. Please modify the specific weight path accordingly. Before starting fine-tuning, make sure to compute the data normalization statistics according to the requirements of **openpi** by running `scripts/compute_norm_stats.py`.

We further provide the modified remote client `http_policy_server.py` and the local receiver `evaluate_bi.py` to enable remote server inference and local execution of actions on the AlohaMini robot.

```
python scripts/serve_policy_http.py \
        --port 8000 \
        --default_prompt "<prompt>" \
        policy:checkpoint \
        --policy.config=pi05_test2 \
        --policy.dir=<Weight path>
```

```
python -m lerobot.robots.alohamini.lekiwi_host \
  --arm_profile so-arm-5dof

python examples/pi0.5_openpi/evaluate_bi.py \
  --policy_mode remote_http \
  --server_url http://localhost:8000 \
  --task_description "<prompt>" \
  --remote_ip 10.100.74.7 \
  --robot_dof 16
```

For 18-DoF robots:
```
python examples/pi0.5_openpi/evaluate_bi.py \
  --policy_mode remote_http \
  --server_url http://localhost:8000 \
  --task_description "<prompt>" \
  --remote_ip 10.100.74.7 \
  --robot_dof 18
```
