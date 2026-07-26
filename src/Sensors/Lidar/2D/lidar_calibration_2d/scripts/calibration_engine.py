#!/usr/bin/env python3
"""
Calibration Orchestration Module (merged_lidar-centric).

Workflow:
1. Raw scan points (sensor-local) + jog transforms (merged→front, merged→rear)
2. Transform both scans into merged_lidar frame
3. Run region-based ICP (rear→front alignment in merged frame)
4. Aggregate results with MAD outlier rejection
5. Compute corrected jog_rear via compose_tf(icp_correction, jog_rear)
"""

import math
import numpy as np
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal

from icp_algorithm import ICPConfig, CalibrationResult, align_svd_icp
from region_manager import Region, filter_points
from ros_scan_bridge import RosScanBridge
from tf_calculator import (
    TFTransform2D,
    CalibrationOutput,
    compute_median,
    compute_full_calibration_merged,
    save_calibration_yaml
)


class CalibrationEngine(QObject):
    """
    Orchestrates multi-region calibration in merged_lidar frame.

    Signals:
        region_result_ready: (region_index, CalibrationResult)
        calibration_complete: (CalibrationOutput)
        calibration_error: error message
        progress_updated: status text
    """

    region_result_ready = pyqtSignal(int, object)
    calibration_complete = pyqtSignal(object)
    calibration_error = pyqtSignal(str)
    progress_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._last_output = None

    @property
    def last_output(self):
        """Public accessor for the last calibration output."""
        return self._last_output

    def run_calibration(
        self,
        raw_front: np.ndarray,
        raw_rear: np.ndarray,
        jog_front: TFTransform2D,
        jog_rear: TFTransform2D,
        regions: List[Region],
        config: ICPConfig,
    ):
        """
        Run region-based ICP calibration in merged_lidar frame.

        Args:
            raw_front: (N,2) front scan points in scan_front local frame
            raw_rear: (M,2) rear scan points in scan_rear local frame
            jog_front: merged_lidar -> scan_front transform (from URDF + user jog)
            jog_rear: merged_lidar -> scan_rear transform (from URDF + user jog)
            regions: List[Region] ROIs in merged_lidar frame
            config: ICPConfig
        """
        try:
            self.progress_updated.emit("Transforming scans to merged_lidar frame...")

            # Transform raw points to merged_lidar frame
            front_merged = RosScanBridge.transform_points_2d(raw_front, jog_front)
            rear_merged = RosScanBridge.transform_points_2d(raw_rear, jog_rear)

            if front_merged is None or len(front_merged) == 0:
                self.calibration_error.emit("No front scan points available")
                return
            if rear_merged is None or len(rear_merged) == 0:
                self.calibration_error.emit("No rear scan points available")
                return

            self.progress_updated.emit(
                f"Points in merged frame: front={len(front_merged)}, rear={len(rear_merged)}")

            region_results = []

            for i, region in enumerate(regions):
                self.progress_updated.emit(
                    f"Processing region {i+1}/{len(regions)}: {region.label}")

                filtered_front = filter_points(front_merged, region)
                filtered_rear = filter_points(rear_merged, region)

                if len(filtered_front) < config.min_correspondences:
                    self.progress_updated.emit(
                        f"Region {i+1} skipped: front points "
                        f"({len(filtered_front)} < {config.min_correspondences})")
                    continue

                if len(filtered_rear) < config.min_correspondences:
                    self.progress_updated.emit(
                        f"Region {i+1} skipped: rear points "
                        f"({len(filtered_rear)} < {config.min_correspondences})")
                    continue

                # ICP: rear (source) -> front (target) in merged frame
                result = align_svd_icp(filtered_rear, filtered_front, config)

                self.region_result_ready.emit(i, result)
                region_results.append(result)

                status = "converged" if result.converged else "did not converge"
                self.progress_updated.emit(
                    f"Region {i+1} {status}: "
                    f"dx={result.dx:.4f}, dy={result.dy:.4f}, "
                    f"dyaw={math.degrees(result.dyaw):.3f}\u00b0, "
                    f"mean_dist={result.mean_correspondence_distance:.4f}")

            converged_results = [r for r in region_results if r.converged]

            if len(converged_results) == 0:
                self.calibration_error.emit("No regions converged successfully")
                return

            self.progress_updated.emit(
                f"Aggregating {len(converged_results)} converged regions...")

            dx_values = [r.dx for r in converged_results]
            dy_values = [r.dy for r in converged_results]
            dyaw_values = [r.dyaw for r in converged_results]
            corr_dist_values = [r.mean_correspondence_distance for r in converged_results]

            dx_filtered = self.reject_outliers_mad(dx_values)
            dy_filtered = self.reject_outliers_mad(dy_values)
            dyaw_filtered = self.reject_outliers_mad(dyaw_values)
            corr_dist_filtered = self.reject_outliers_mad(corr_dist_values)

            if not dx_filtered or not dy_filtered or not dyaw_filtered:
                self.calibration_error.emit("All results rejected as outliers")
                return

            self.progress_updated.emit(
                f"Outlier rejection: kept {len(dx_filtered)}/{len(dx_values)} results")

            med_dx = compute_median(dx_filtered)
            med_dy = compute_median(dy_filtered)
            med_dyaw = compute_median(dyaw_filtered)
            med_corr_dist = compute_median(corr_dist_filtered)

            output = compute_full_calibration_merged(
                med_dx, med_dy, med_dyaw,
                jog_front, jog_rear,
                len(dx_filtered), med_corr_dist
            )

            self._last_output = output

            self.progress_updated.emit("Calibration complete!")
            self.calibration_complete.emit(output)

        except Exception as e:
            error_msg = f"Calibration failed: {str(e)}"
            self.progress_updated.emit(error_msg)
            self.calibration_error.emit(error_msg)

    @staticmethod
    def reject_outliers_mad(values: List[float], threshold: float = 2.0) -> List[float]:
        """Reject outliers using Median Absolute Deviation (MAD)."""
        if len(values) <= 1:
            return values

        median = compute_median(values)
        deviations = [abs(v - median) for v in values]
        mad = compute_median(deviations)

        if mad == 0.0:
            return values

        return [v for v in values if abs(v - median) <= threshold * mad]

    def save_results(self, output: CalibrationOutput, filepath: str):
        save_calibration_yaml(output, filepath)
        self.progress_updated.emit(f"Results saved to {filepath}")
