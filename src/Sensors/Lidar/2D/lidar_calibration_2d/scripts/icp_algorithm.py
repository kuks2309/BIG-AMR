#!/usr/bin/env python3
"""
Python port of svd_aligner.hpp - SVD-based ICP alignment for 2D point clouds.

This module implements a 2D Iterative Closest Point (ICP) algorithm using
Singular Value Decomposition (SVD) for rigid-body transform estimation.

Reference: src/Sensor/Lidar/2D/lidar_calibration_2d/include/lidar_calibration_2d/svd_aligner.hpp
"""

import numpy as np
from scipy.spatial import KDTree
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ICPConfig:
    """Configuration parameters for ICP alignment."""
    max_iterations: int = 50
    transform_epsilon: float = 1e-6
    max_correspondence_dist: float = 0.3
    min_correspondences: int = 30


@dataclass
class CalibrationResult:
    """Result of ICP calibration."""
    dx: float = 0.0
    dy: float = 0.0
    dyaw: float = 0.0
    mean_correspondence_distance: float = float('inf')
    num_correspondences: int = 0
    converged: bool = False


def compute_svd_transform_2d(
    correspondences: List[Tuple[np.ndarray, np.ndarray]]
) -> Tuple[bool, np.ndarray, np.ndarray]:
    """
    Compute 2D rigid-body transform (R, t) that best aligns source points to target points
    using SVD decomposition on the cross-covariance matrix.

    Given N pairs (p_i, q_i):
      1. Compute centroids p_bar, q_bar
      2. Center points: p_i' = p_i - p_bar, q_i' = q_i - q_bar
      3. Build 2x2 cross-covariance: H = sum(p_i' @ q_i'^T)
      4. SVD: H = U @ S @ Vt
      5. R = Vt.T @ U.T (correct for reflection if det < 0)
      6. t = q_bar - R @ p_bar

    Args:
        correspondences: List of (source_pt, target_pt) pairs, each is (2,) numpy array

    Returns:
        Tuple of (success, R, t) where:
            success: bool - True if successful (enough points), False otherwise
            R: (2, 2) numpy array - rotation matrix
            t: (2,) numpy array - translation vector
    """
    n = len(correspondences)
    if n < 3:
        return False, np.eye(2), np.zeros(2)

    # Step 1: Compute centroids
    p_bar = np.zeros(2)
    q_bar = np.zeros(2)
    for p, q in correspondences:
        p_bar += p
        q_bar += q
    p_bar /= n
    q_bar /= n

    # Step 2-3: Build cross-covariance matrix H
    H = np.zeros((2, 2))
    for p, q in correspondences:
        p_centered = p - p_bar
        q_centered = q - q_bar
        H += np.outer(p_centered, q_centered)

    # Step 4: SVD decomposition
    U, S, Vt = np.linalg.svd(H)

    # Step 5: Compute rotation (correct for reflection)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[1, :] *= -1.0
        R = Vt.T @ U.T

    # Step 6: Compute translation
    t = q_bar - R @ p_bar

    return True, R, t


def align_svd_icp(
    source: np.ndarray,
    target: np.ndarray,
    config: ICPConfig
) -> CalibrationResult:
    """
    Run 2D ICP alignment using SVD for transform estimation.

    This implements a custom 2D ICP loop:
      1. Start with source and target point clouds (both in base_footprint)
      2. For each iteration:
         a. Find nearest-neighbor correspondences (using KDTree)
         b. Filter by max_correspondence_dist
         c. Estimate transform using SVD
         d. Apply incremental transform to source
         e. Check convergence
      3. Return cumulative transform as CalibrationResult

    Args:
        source: (N, 2) numpy array - source point cloud (rear scan in base_footprint)
        target: (M, 2) numpy array - target point cloud (front scan in base_footprint)
        config: ICPConfig - ICP configuration parameters

    Returns:
        CalibrationResult with dx, dy, dyaw
    """
    result = CalibrationResult()

    if source.shape[0] == 0 or target.shape[0] == 0:
        return result

    # Make a copy of source to avoid modifying input
    source = source.copy()

    # Cumulative transform
    R_total = np.eye(2)
    t_total = np.zeros(2)

    thresh_sq = config.max_correspondence_dist ** 2

    # Build KDTree from target points (rebuilt each iteration for mutual NN)
    for iteration in range(config.max_iterations):
        # Step a: Mutual Nearest Neighbor correspondences
        # Forward: source → target
        kdtree_target = KDTree(target)
        dists_st, idx_st = kdtree_target.query(source)

        # Reverse: target → source
        kdtree_source = KDTree(source)
        dists_ts, idx_ts = kdtree_source.query(target)

        correspondences = []
        total_dist = 0.0

        # Step b: Keep only mutual NN pairs within max distance
        for i in range(len(source)):
            j = idx_st[i]       # source[i]'s nearest in target
            dist = dists_st[i]
            if dist * dist >= thresh_sq:
                continue
            # Check mutual: target[j]'s nearest in source must be i
            if idx_ts[j] == i:
                correspondences.append((source[i], target[j]))
                total_dist += dist

        # Step c: Check minimum correspondences
        if len(correspondences) < config.min_correspondences:
            result.num_correspondences = len(correspondences)
            return result  # Not enough correspondences, return unconverged

        result.mean_correspondence_distance = total_dist / len(correspondences)
        result.num_correspondences = len(correspondences)

        # Step d: Estimate transform using SVD
        success, R_inc, t_inc = compute_svd_transform_2d(correspondences)
        if not success:
            return result

        # Step e: Apply incremental transform to source points
        source = (R_inc @ source.T).T + t_inc

        # Accumulate: T_total = T_inc * T_prev
        # R_total_new = R_inc * R_total_prev
        # t_total_new = R_inc * t_total_prev + t_inc
        t_new = R_inc @ t_total + t_inc
        R_total = R_inc @ R_total
        t_total = t_new

        # Step f: Check convergence
        translation_delta = np.linalg.norm(t_inc)
        rotation_delta = abs(np.arctan2(R_inc[1, 0], R_inc[0, 0]))

        if (translation_delta < config.transform_epsilon and
                rotation_delta < config.transform_epsilon):
            result.converged = True
            break

    # Extract 2D parameters from cumulative transform
    result.dyaw = np.arctan2(R_total[1, 0], R_total[0, 0])
    result.dx = t_total[0]
    result.dy = t_total[1]

    # If we exhausted iterations but got close, still mark as converged
    if not result.converged and result.mean_correspondence_distance < 0.05:
        result.converged = True

    return result
