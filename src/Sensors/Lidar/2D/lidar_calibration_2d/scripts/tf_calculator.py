#!/usr/bin/env python3

"""
TF calculation utilities for LiDAR calibration.
Merged-LiDAR-centric approach: merged_lidar is the reference frame (origin),
scan_front and scan_rear are positioned relative to it via jog transforms.
"""

from dataclasses import dataclass
import math
import yaml
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class TFTransform2D:
    """2D rigid transform representation."""
    tx: float = 0.0
    ty: float = 0.0
    yaw: float = 0.0  # radians
    flipped: bool = False  # True if sensor is upside-down (roll=π, Y-negate in 2D)


@dataclass
class CalibrationOutput:
    """Complete calibration output data (merged_lidar-centric)."""
    icp_correction: TFTransform2D        # ICP median correction (dx, dy, dyaw)
    jog_front: TFTransform2D             # merged_lidar -> scan_front (user-set, unchanged)
    jog_rear_original: TFTransform2D     # merged_lidar -> scan_rear (before ICP)
    jog_rear_corrected: TFTransform2D    # merged_lidar -> scan_rear (after ICP)
    num_successful: int = 0
    median_correspondence_distance: float = 0.0


def compute_median(values: List[float]) -> float:
    """Compute median of a list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0
    else:
        return sorted_values[n // 2]


def compose_tf(parent: TFTransform2D, child: TFTransform2D) -> TFTransform2D:
    """Compose two 2D transforms: T_result = T_parent * T_child."""
    result_yaw = parent.yaw + child.yaw
    result_tx = (parent.tx
                + math.cos(parent.yaw) * child.tx
                - math.sin(parent.yaw) * child.ty)
    result_ty = (parent.ty
                + math.sin(parent.yaw) * child.tx
                + math.cos(parent.yaw) * child.ty)
    return TFTransform2D(tx=result_tx, ty=result_ty, yaw=result_yaw,
                         flipped=child.flipped)


def invert_tf(tf: TFTransform2D) -> TFTransform2D:
    """Compute inverse of 2D rigid transform."""
    inv_yaw = -tf.yaw
    inv_tx = -(math.cos(tf.yaw) * tf.tx + math.sin(tf.yaw) * tf.ty)
    inv_ty = -(-math.sin(tf.yaw) * tf.tx + math.cos(tf.yaw) * tf.ty)
    return TFTransform2D(tx=inv_tx, ty=inv_ty, yaw=inv_yaw,
                         flipped=tf.flipped)


def normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi] range."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def compute_symmetry_info(jog_front: TFTransform2D, jog_rear: TFTransform2D) -> dict:
    """Compute symmetry analysis between front and rear LiDAR positions.

    For perfect symmetry about merged_lidar origin:
      ideal_rear = (-front.tx, -front.ty, front.yaw + pi)

    Returns:
        dict with keys: ideal_rear_tx, ideal_rear_ty, ideal_rear_yaw,
                        delta_tx, delta_ty, delta_yaw, is_symmetric
    """
    ideal_rear_tx = -jog_front.tx
    ideal_rear_ty = -jog_front.ty
    ideal_rear_yaw = normalize_angle(jog_front.yaw + math.pi)

    delta_tx = abs(jog_rear.tx - ideal_rear_tx)
    delta_ty = abs(jog_rear.ty - ideal_rear_ty)
    delta_yaw = abs(normalize_angle(jog_rear.yaw - ideal_rear_yaw))

    # Consider symmetric if all deltas are below threshold
    threshold_pos = 0.002   # 2mm
    threshold_yaw = math.radians(0.5)  # 0.5 degree
    is_symmetric = (delta_tx < threshold_pos
                    and delta_ty < threshold_pos
                    and delta_yaw < threshold_yaw)

    return {
        'ideal_rear_tx': ideal_rear_tx,
        'ideal_rear_ty': ideal_rear_ty,
        'ideal_rear_yaw': ideal_rear_yaw,
        'delta_tx': delta_tx,
        'delta_ty': delta_ty,
        'delta_yaw': delta_yaw,
        'is_symmetric': is_symmetric,
    }


def mirror_front_to_rear(jog_front: TFTransform2D, rear_flipped: bool) -> TFTransform2D:
    """Create a perfectly symmetric rear transform from front transform.

    Mirror about merged_lidar origin:
      rear.tx = -front.tx, rear.ty = -front.ty, rear.yaw = front.yaw + pi
    """
    return TFTransform2D(
        tx=-jog_front.tx,
        ty=-jog_front.ty,
        yaw=normalize_angle(jog_front.yaw + math.pi),
        flipped=rear_flipped,
    )


def apply_symmetric_correction(
    jog_front: TFTransform2D,
    jog_rear_original: TFTransform2D,
    icp_correction: TFTransform2D,
) -> tuple:
    """Apply symmetric correction by splitting the ICP correction equally.

    ICP found that rear needs correction C to align with front.
    Instead of applying full C to rear only:
      - Apply -C/2 to front (push front toward rear by half)
      - Apply +C/2 to rear  (push rear toward front by half)

    This distributes the error equally, equivalent to averaging
    front-reference and rear-reference ICP results.

    Args:
        jog_front: merged_lidar -> scan_front (unchanged by ICP)
        jog_rear_original: merged_lidar -> scan_rear (BEFORE ICP correction)
        icp_correction: ICP correction transform (dx, dy, dyaw)

    Returns:
        (sym_front, sym_rear) tuple of TFTransform2D
    """
    half_corr = TFTransform2D(
        tx=icp_correction.tx / 2.0,
        ty=icp_correction.ty / 2.0,
        yaw=icp_correction.yaw / 2.0,
    )
    neg_half_corr = TFTransform2D(
        tx=-icp_correction.tx / 2.0,
        ty=-icp_correction.ty / 2.0,
        yaw=-icp_correction.yaw / 2.0,
    )

    # Front: push in opposite direction by half
    sym_front = compose_tf(neg_half_corr, jog_front)
    sym_front.flipped = jog_front.flipped

    # Rear: push toward front by half (from original, not corrected)
    sym_rear = compose_tf(half_corr, jog_rear_original)
    sym_rear.flipped = jog_rear_original.flipped

    return sym_front, sym_rear


def compute_full_calibration_merged(
    med_dx: float,
    med_dy: float,
    med_dyaw: float,
    jog_front: TFTransform2D,
    jog_rear: TFTransform2D,
    num_successful: int,
    med_corr_dist: float
) -> CalibrationOutput:
    """
    Compute calibration output in merged_lidar-centric frame.

    ICP correction transforms rear_in_merged to align with front_in_merged:
      corrected_rear_in_merged = R(dyaw) * rear_in_merged + (dx, dy)

    Equivalent to updating jog_rear:
      jog_rear_corrected = compose_tf(icp_correction, jog_rear)
    """
    icp_correction = TFTransform2D(tx=med_dx, ty=med_dy, yaw=med_dyaw)
    jog_rear_corrected = compose_tf(icp_correction, jog_rear)

    return CalibrationOutput(
        icp_correction=icp_correction,
        jog_front=jog_front,
        jog_rear_original=jog_rear,
        jog_rear_corrected=jog_rear_corrected,
        num_successful=num_successful,
        median_correspondence_distance=med_corr_dist
    )


def save_calibration_yaml(
    output: CalibrationOutput,
    filepath: str,
    scan_topic_front: str = "/scan_front",
    scan_topic_rear: str = "/scan_rear",
    num_samples: int = 0,
    average_filter_enabled: bool = False,
    downsample_stride: int = 1,
):
    """Save calibration results to YAML file (merged_lidar-centric)."""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "calibration": {
            "reference_frame": "merged_lidar",
            "reference_sensor": scan_topic_front,
            "calibrated_sensor": scan_topic_rear,
            "icp_correction": {
                "dx": round(float(output.icp_correction.tx), 6),
                "dy": round(float(output.icp_correction.ty), 6),
                "dyaw_rad": round(float(output.icp_correction.yaw), 6),
                "dyaw_deg": round(float(math.degrees(output.icp_correction.yaw)), 2)
            },
            "merged_lidar_to_scan_front": {
                "tx": round(float(output.jog_front.tx), 6),
                "ty": round(float(output.jog_front.ty), 6),
                "yaw_rad": round(float(output.jog_front.yaw), 6),
                "yaw_deg": round(float(math.degrees(output.jog_front.yaw)), 2),
                "flipped": bool(output.jog_front.flipped)
            },
            "merged_lidar_to_scan_rear_original": {
                "tx": round(float(output.jog_rear_original.tx), 6),
                "ty": round(float(output.jog_rear_original.ty), 6),
                "yaw_rad": round(float(output.jog_rear_original.yaw), 6),
                "yaw_deg": round(float(math.degrees(output.jog_rear_original.yaw)), 2),
                "flipped": bool(output.jog_rear_original.flipped)
            },
            "merged_lidar_to_scan_rear_corrected": {
                "tx": round(float(output.jog_rear_corrected.tx), 6),
                "ty": round(float(output.jog_rear_corrected.ty), 6),
                "yaw_rad": round(float(output.jog_rear_corrected.yaw), 6),
                "yaw_deg": round(float(math.degrees(output.jog_rear_corrected.yaw)), 2),
                "flipped": bool(output.jog_rear_corrected.flipped)
            },
            "statistics": {
                "num_samples": num_samples,
                "successful_alignments": int(output.num_successful),
                "median_correspondence_distance": round(float(output.median_correspondence_distance), 4),
                "average_filter_enabled": average_filter_enabled,
                "downsample_stride": downsample_stride
            }
        }
    }

    with open(output_path, 'w') as f:
        f.write(f"# Auto-generated by lidar_calibration_2d\n")
        f.write(f"# Generated: {timestamp}\n")
        f.write(f"# Method: merged_lidar-centric ICP alignment\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    print(f"Results saved to: {output_path}")
