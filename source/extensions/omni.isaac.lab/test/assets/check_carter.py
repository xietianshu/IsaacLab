# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse

from omni.isaac.lab.app import AppLauncher

# Add argparse arguments
parser = argparse.ArgumentParser(description="Tutorial on adding sensors on a robot.")
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to spawn.")
# Append AppLauncher CLI args
AppLauncher.add_app_launcher_args(parser)
# Parse the arguments
args_cli = parser.parse_args()

# Launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import os
import torch

from omni.isaac.core.utils.extensions import enable_extension, get_extension_path_from_name

import omni.isaac.lab.envs.mdp as mdp
import omni.isaac.lab.sim as sim_utils
from omni.isaac.lab.actuators.actuator_cfg import ImplicitActuatorCfg
from omni.isaac.lab.assets import ArticulationCfg, AssetBaseCfg
from omni.isaac.lab.envs import ManagerBasedEnv, ManagerBasedEnvCfg
from omni.isaac.lab.managers import EventTermCfg as EventTerm
from omni.isaac.lab.scene import InteractiveSceneCfg
from omni.isaac.lab.utils import configclass


# Define constant forward velocity
def constant_forward_velocity(env: ManagerBasedEnv) -> torch.Tensor:
    """Generates constant forward velocity command."""
    return torch.tensor([[10.0, 10.0]], device=env.device).repeat(env.num_envs, 1)


@configclass
class SceneCfg(InteractiveSceneCfg):
    """Design the scene with sensors on the robot."""

    # Ground plane
    ground = AssetBaseCfg(prim_path="/World/defaultGroundPlane", spawn=sim_utils.GroundPlaneCfg())

    # Lights
    dome_light = AssetBaseCfg(
        prim_path="/World/Light", spawn=sim_utils.DomeLightCfg(intensity=2000.0, color=(0.75, 0.75, 0.75))
    )

    # Robot
    robot = ArticulationCfg(
        prim_path="/World/Robot",
        spawn=sim_utils.UrdfFileCfg(
            asset_path="carter.urdf",  # filled in post_init with full path from extension
            merge_fixed_joints=True,
            fix_base=False,
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(enabled_self_collisions=False),
        ),
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, 0.25), rot=(1, 0, 0, 0)),
        actuators={
            "wheels": ImplicitActuatorCfg(
                joint_names_expr=["left_wheel", "right_wheel"], stiffness=0.0, damping=1.0e3, effort_limit=100.0
            ),
        },
    )

    def __post_init__(self):
        # resolve directory for carter
        enable_extension("omni.importer.urdf")
        ext_dir = get_extension_path_from_name("omni.importer.urdf")
        # Robot
        self.robot.spawn.asset_path = os.path.join(ext_dir, "data/urdf/robots/carter/urdf/carter.urdf")


@configclass
class ObservationsCfg:
    pass


@configclass
class EventCfg:
    """Configuration for events."""

    reset_scene = EventTerm(func=mdp.reset_scene_to_default, mode="reset")


@configclass
class ActionsCfg:
    """Action specifications for the MDP."""

    wheel_velocity = mdp.JointVelocityActionCfg(
        asset_name="robot",
        joint_names=["left_wheel", "right_wheel"],
        scale=1.0,
    )


@configclass
class StretchEnvCfg(ManagerBasedEnvCfg):
    scene: SceneCfg = SceneCfg(num_envs=1, env_spacing=2.5)
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    events: EventCfg = EventCfg()

    def __post_init__(self):
        self.sim.dt = 1 / 120.0
        self.decimation = 2


def main():
    # Create the environment
    env_cfg = StretchEnvCfg()
    env_cfg.sim.device = "cpu"
    env_cfg.sim.use_gpu_pipeline = False
    env_cfg.sim.use_fabric = False
    env_cfg.sim.physx.use_gpu = False
    env = ManagerBasedEnv(cfg=env_cfg)

    # Initialize the robot and actuators
    # env.scene.robot = Articulation(env_cfg.scene.robot)
    # env.scene.robot.initialize()

    # Print all joints and links
    print("All joint names:", env.scene["robot"].joint_names)
    print("All link names:", env.scene["robot"].body_names)

    env.reset()
    while simulation_app.is_running():
        # Print joint positions and velocities before the action
        print(f"Left wheel joint position: {env.scene['robot'].data.joint_pos[:, 0]}")
        print(f"Right wheel joint position: {env.scene['robot'].data.joint_pos[:, 1]}")
        print(f"Left wheel joint velocity: {env.scene['robot'].data.joint_vel[:, 0]}")
        print(f"Right wheel joint velocity: {env.scene['robot'].data.joint_vel[:, 1]}")

        # Apply constant forward velocity to the wheels
        action = constant_forward_velocity(env)
        env.step(action)

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
