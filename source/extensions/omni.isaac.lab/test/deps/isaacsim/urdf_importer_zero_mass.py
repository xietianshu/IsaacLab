# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Launch Isaac Sim Simulator first."""

from isaacsim import SimulationApp

# launch omniverse app
simulation_app = SimulationApp({"headless": False})

"""Rest everything follows."""

import pathlib
import time
import torch

import omni.kit.commands
import omni.physics.tensors.impl.api as physx
from omni.isaac.core.world import World


@torch.jit.script
def quat_rotate(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Rotate a vector by a quaternion.

    Args:
        q: The quaternion in (w, x, y, z). Shape is (N, 4).
        v: The vector in (x, y, z). Shape is (N, 3).

    Returns:
        The rotated vector in (x, y, z). Shape is (N, 3).
    """
    shape = q.shape
    q_w = q[:, 0]
    q_vec = q[:, 1:]
    a = v * (2.0 * q_w**2 - 1.0).unsqueeze(-1)
    b = torch.cross(q_vec, v, dim=-1) * q_w.unsqueeze(-1) * 2.0
    c = q_vec * torch.bmm(q_vec.view(shape[0], 1, 3), v.view(shape[0], 3, 1)).squeeze(-1) * 2.0
    return a + b + c


def import_asset_from_urdf(save_usd: bool = False) -> str:
    """Import the simple two link robot from a URDF file.

    Args:
        save_usd: Whether to save the imported USD file. Default is False.

    Returns:
        The path to the root of the articulation.
    """
    # Setting up import configuration:
    status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
    import_config.merge_fixed_joints = False
    import_config.convex_decomp = False
    import_config.import_inertia_tensor = True
    import_config.fix_base = True
    import_config.make_default_prim = True
    import_config.distance_scale = 1
    import_config.create_physics_scene = False
    import_config.default_drive_strength = 0.0
    import_config.default_position_drive_damping = 0.05
    import_config.density = 0.0

    # Check if save_usd is True
    if save_usd:
        dest_path = f"{pathlib.Path(__file__).parent.resolve()}/usd/simple_pendulum.usd"
    else:
        dest_path = ""

    # Import URDF, stage_path contains the path the path to the usd prim in the stage.
    status, art_path = omni.kit.commands.execute(
        "URDFParseAndImportFile",
        urdf_path=f"{pathlib.Path(__file__).parent.resolve()}/urdf/simple_pendulum.urdf",
        import_config=import_config,
        get_articulation_root=True,
        dest_path=dest_path
    )
    # Return the path to the root of the articulation
    return art_path


def main():
    """Main function to run the simulation."""
    # create world
    # NOTE: Change the device to "cuda" if you have a GPU
    world = World(physics_dt=0.005, rendering_dt=0.005, backend="torch", device="cpu")

    # Load the stage
    articulation_path = import_asset_from_urdf()
    print("Imported URDF to:", articulation_path)

    # update world
    world.step(render=False)
    world.initialize_physics()

    # create physx views
    physx_sim_view = physx.create_simulation_view("torch")
    physx_sim_view.set_subspace_roots("/")

    # create views
    art_view = physx_sim_view.create_articulation_view("/simple_pendulum/base")
    link_1_view = physx_sim_view.create_rigid_body_view("/simple_pendulum/link_1/")
    imu_link_view = physx_sim_view.create_rigid_body_view("/simple_pendulum/imu_link/")

    # get com offsets
    link_1_com, _ = link_1_view.get_coms().split([3, 4], dim=-1)
    imu_link_com, _ = imu_link_view.get_coms().split([3, 4], dim=-1)

    dt = world.get_physics_dt()
    joint1_vel = torch.tensor([0], device=world.device)

    # offset of imu_link from link_1 on simple_pendulum see URDF
    PEND_POS_OFFSET = (0.4, 0.0, 0.1)
    PEND_ROT_OFFSET = (0.5, 0.5, 0.5, 0.5)

    while world.app.is_running():
        # step the simulation
        world.step()

        # joint state
        joint1_pos = art_view.get_dof_positions()
        joint1_vel_prev = joint1_vel.clone()
        joint1_vel = art_view.get_dof_velocities()
        joint1_acc = (joint1_vel - joint1_vel_prev) / dt

        # link_1 body states
        link_1_pos, link_1_quat = link_1_view.get_transforms().split([3, 4], dim=-1)
        link_1_quat = link_1_quat.roll(1, dims=-1)  # xyzw -> wxyz
        link_1_com_rot = quat_rotate(link_1_quat, -link_1_com)
        link_1_lin_vel, link_1_ang_vel = link_1_view.get_velocities().split([3, 3], dim=-1)
        link_1_lin_vel += torch.linalg.cross(link_1_ang_vel, link_1_com_rot, dim=-1)
        link_1_lin_acc, link_1_ang_acc = link_1_view.get_accelerations().split([3, 3], dim=-1)
        link_1_lin_acc += torch.cross(link_1_ang_acc, link_1_com_rot, dim=-1) + torch.cross(
            link_1_ang_vel, torch.cross(link_1_ang_vel, link_1_com_rot, dim=-1), dim=-1
        )

        # imu_link body states
        imu_link_pos, imu_link_quat = imu_link_view.get_transforms().split([3, 4], dim=-1)
        imu_link_quat = imu_link_quat.roll(1, dims=-1)  # xyzw -> wxyz
        imu_link_com_rot = quat_rotate(imu_link_quat, -imu_link_com)
        imu_link_lin_vel, imu_link_ang_vel = imu_link_view.get_velocities().split([3, 3], dim=-1)
        imu_link_lin_vel += torch.linalg.cross(imu_link_ang_vel, imu_link_com_rot, dim=-1)
        imu_link_lin_acc, imu_link_ang_acc = imu_link_view.get_accelerations().split([3, 3], dim=-1)
        imu_link_lin_acc += torch.cross(imu_link_ang_acc, imu_link_com_rot, dim=-1) + torch.cross(
            imu_link_ang_vel, torch.cross(imu_link_ang_vel, imu_link_com_rot, dim=-1), dim=-1
        )

        # analytical pendulum problem
        vx = -joint1_vel * PEND_POS_OFFSET[0] * torch.sin(joint1_pos)
        vy = torch.zeros(1, 1, device=world.device)
        vz = -joint1_vel * PEND_POS_OFFSET[0] * torch.cos(joint1_pos)

        gt_linear_vel = torch.cat([vx, vy, vz], dim=-1)
        
        ax = -joint1_acc * PEND_POS_OFFSET[0] * torch.sin(joint1_pos) - joint1_vel**2 * PEND_POS_OFFSET[0] * torch.cos(
            joint1_pos
        )
        ay = torch.zeros_like(ax, device=world.device)
        az = -joint1_acc * PEND_POS_OFFSET[0] * torch.cos(joint1_pos) + joint1_vel**2 * PEND_POS_OFFSET[0] * torch.sin(
            joint1_pos
        )
        gt_linear_acc = torch.cat([ax, ay, az], dim=-1)

        # checks

        # angular velocity
        if torch.max(torch.abs(link_1_ang_vel - imu_link_ang_vel)) > 1e-4:
            print("imu and link1 angular velocities do not match")
        if torch.max(torch.abs(link_1_ang_vel[:, 1] - joint1_vel)) > 1e-3:
            print("link1 angular velocities and joint velocity do not match")
        if torch.max(torch.abs(imu_link_ang_vel[:, 1] - joint1_vel)) > 1e-3:
            print("link1 angular velocities and joint velocity do not match")

        # linear velocity
        err_vel_imu_gt = torch.abs(imu_link_lin_vel - gt_linear_vel)
        if torch.max(err_vel_imu_gt) > 1e-2:
            print(f"lin_vel \t imu_link and analytical do not match error:\t {err_vel_imu_gt}")
        err_vel_link_gt = torch.abs(link_1_lin_vel - torch.zeros_like(gt_linear_vel))
        if torch.max(err_vel_link_gt) > 1e-2:
            print(f"lin_vel \t link_1 should be zero, error:\t {err_vel_link_gt}")

        # angular acceleration
        if torch.max(torch.abs(link_1_ang_acc - imu_link_ang_acc)) > 1e-4:
            print("imu and link1 angular acceleration do not match")
        if torch.max(torch.abs(link_1_ang_acc[:, 1] - joint1_acc)) > 1e-3:
            print("link1 angular acceleration and joint acceleration do not match")
        if torch.max(torch.abs(imu_link_ang_acc[:, 1] - joint1_acc)) > 1e-3:
            print("imu_link angular acceleration and joint acceleration do not match")

        # linear acc NOTE tolerances may be negotiable but a relative tolerance of 10% error would be good for dt=0.005
        err_acc_imu_gt = torch.abs(imu_link_lin_acc - gt_linear_acc)
        if torch.max(err_acc_imu_gt) > 1e-1:
            print(f"lin_acc \t imu_link and analytical  do not match, error:\t {err_acc_imu_gt}")
        err_acc_link_gt = torch.abs(link_1_lin_acc - torch.zeros_like(gt_linear_acc))
        if torch.max(link_1_lin_acc - torch.zeros_like(gt_linear_acc)) > 1e-1:
            print(f"lin_acc \t link_1 should be zero, error:\t {err_acc_link_gt}")

        time.sleep(0.1)


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()
