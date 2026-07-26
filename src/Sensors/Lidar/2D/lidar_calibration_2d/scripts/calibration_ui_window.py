#!/usr/bin/env python3
"""
Main UI Window for 2D LiDAR Calibration (merged_lidar-centric).

Workflow:
  1. Load initial TF from config parameters → populate jog spinboxes
  2. User adjusts jog (merged→front, merged→rear) for coarse alignment
  3. Both scans displayed in merged_lidar frame (raw × jog transform)
  4. User draws ROI regions, runs ICP for precise alignment
  5. ICP corrects jog_rear → display updated overlay
"""

import os
import math
import numpy as np

from PyQt5.QtWidgets import QMainWindow, QFileDialog
from PyQt5.QtCore import pyqtSlot, Qt, QThread, pyqtSignal
from PyQt5 import uic

from scan_canvas import ScanCanvas, InteractionMode
from region_manager import RegionManager
from ros_scan_bridge import RosScanBridge
from calibration_engine import CalibrationEngine
from icp_algorithm import ICPConfig
from tf_calculator import (
    CalibrationOutput, TFTransform2D,
    compute_symmetry_info, mirror_front_to_rear, apply_symmetric_correction,
    save_calibration_yaml,
)

from geometry_msgs.msg import TransformStamped
import tf2_ros
from ament_index_python.packages import get_package_share_directory


class CalibrationWorker(QThread):
    """Run ICP calibration in a background thread to avoid UI freeze."""
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, engine, raw_front, raw_rear, jog_front, jog_rear, regions, config):
        super().__init__()
        self._engine = engine
        self._raw_front = raw_front
        self._raw_rear = raw_rear
        self._jog_front = jog_front
        self._jog_rear = jog_rear
        self._regions = regions
        self._config = config

    def run(self):
        try:
            self._engine.run_calibration(
                self._raw_front, self._raw_rear,
                self._jog_front, self._jog_rear,
                self._regions, self._config)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class CalibrationUIWindow(QMainWindow):
    """Main window for LiDAR calibration UI."""

    def __init__(self, ros_bridge: RosScanBridge, parent=None):
        super().__init__(parent)

        ui_path = self._get_ui_path()
        uic.loadUi(ui_path, self)

        self._ros_bridge = ros_bridge
        self._node = ros_bridge._node

        self._region_manager = RegionManager()
        self._engine = CalibrationEngine()

        self._setup_canvas()

        # Raw scan data (sensor-local frames)
        self._raw_front = None
        self._raw_rear = None

        # Current jog transforms (merged_lidar → sensor)
        self._jog_front = TFTransform2D()
        self._jog_rear = TFTransform2D()

        self._connect_signals()
        self.statusbar.showMessage("Ready — click 'Load Initial TF' to start")

    @staticmethod
    def _get_ui_path():
        try:
            from ament_index_python.packages import get_package_share_directory
            pkg_share = get_package_share_directory('lidar_calibration_2d')
            ui_path = os.path.join(pkg_share, 'ui', 'calibration_main.ui')
            if os.path.exists(ui_path):
                return ui_path
        except Exception:
            pass
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(script_dir), 'ui', 'calibration_main.ui')

    def _setup_canvas(self):
        self._canvas = ScanCanvas()
        placeholder = self.canvasPlaceholder
        parent_layout = placeholder.parent().layout()
        index = parent_layout.indexOf(placeholder)
        parent_layout.removeWidget(placeholder)
        placeholder.deleteLater()
        parent_layout.insertWidget(index, self._canvas)

    def _connect_signals(self):
        # ROS bridge → raw scan storage (QueuedConnection for cross-thread safety)
        self._ros_bridge.front_scan_updated.connect(
            self._on_front_scan, Qt.QueuedConnection)
        self._ros_bridge.rear_scan_updated.connect(
            self._on_rear_scan, Qt.QueuedConnection)
        self._ros_bridge.connection_status_changed.connect(
            self._on_connection_status, Qt.QueuedConnection)
        self._ros_bridge.scan_info_updated.connect(
            self._on_scan_info, Qt.QueuedConnection)

        # Canvas signals
        self._canvas.rectangle_completed.connect(self._on_rectangle_completed)
        self._canvas.mouse_world_pos.connect(self._on_mouse_world_pos)

        # Region manager
        self._region_manager.regions_changed.connect(self._update_region_list)

        # UI buttons
        self.btnLoadURDF.clicked.connect(self._on_load_tf)
        self.btnAddRegion.clicked.connect(self._on_add_region_clicked)
        self.btnRemoveRegion.clicked.connect(self._on_remove_region)
        self.btnClearRegions.clicked.connect(self._on_clear_regions)
        self.btnReconnect.clicked.connect(self._on_reconnect)
        self.btnRunCalibration.clicked.connect(self._on_run_calibration)
        self.btnSaveResults.clicked.connect(self._on_save_results)
        self.btnSaveCurrentJog.clicked.connect(self._on_save_current_jog)
        self.btnApplyBroadcast.clicked.connect(self._on_apply_broadcast)
        self.btnCheckSymmetry.clicked.connect(self._on_check_symmetry)
        self.btnMirrorFrontToRear.clicked.connect(self._on_mirror_front_to_rear)
        self.btnSymmetricCorrection.clicked.connect(self._on_symmetric_correction)

        # Sensor flip (upside-down mounting)
        self.chkFlipFront.stateChanged.connect(self._on_flip_front_changed)
        self.chkFlipRear.stateChanged.connect(self._on_flip_rear_changed)

        # Jog spinbox → live update
        self.spinJogFrontX.valueChanged.connect(self._on_jog_changed)
        self.spinJogFrontY.valueChanged.connect(self._on_jog_changed)
        self.spinJogFrontYaw.valueChanged.connect(self._on_jog_changed)
        self.spinJogRearX.valueChanged.connect(self._on_jog_changed)
        self.spinJogRearY.valueChanged.connect(self._on_jog_changed)
        self.spinJogRearYaw.valueChanged.connect(self._on_jog_changed)

        # Calibration engine
        self._engine.region_result_ready.connect(self._on_region_result)
        self._engine.calibration_complete.connect(self._on_calibration_complete)
        self._engine.calibration_error.connect(self._on_calibration_error)
        self._engine.progress_updated.connect(self._on_progress_update)

    # ── Sensor flip (upside-down mounting) ──

    @pyqtSlot(int)
    def _on_flip_front_changed(self, state):
        """Toggle front sensor flip (roll=π, Y-negate in 2D)."""
        self._jog_front.flipped = (state == Qt.Checked)
        self._update_canvas_points()

    @pyqtSlot(int)
    def _on_flip_rear_changed(self, state):
        """Toggle rear sensor flip (roll=π, Y-negate in 2D)."""
        self._jog_rear.flipped = (state == Qt.Checked)
        self._update_canvas_points()

    # ── Jog handling ──

    def _read_jog_from_spinboxes(self):
        """Read current jog values from UI spinboxes (preserves flipped state)."""
        self._jog_front = TFTransform2D(
            tx=self.spinJogFrontX.value(),
            ty=self.spinJogFrontY.value(),
            yaw=math.radians(self.spinJogFrontYaw.value()),
            flipped=self._jog_front.flipped,
        )
        self._jog_rear = TFTransform2D(
            tx=self.spinJogRearX.value(),
            ty=self.spinJogRearY.value(),
            yaw=math.radians(self.spinJogRearYaw.value()),
            flipped=self._jog_rear.flipped,
        )

    def _write_jog_to_spinboxes(self, jog_front: TFTransform2D, jog_rear: TFTransform2D):
        """Write jog values to UI spinboxes (blocks signals to avoid feedback loop)."""
        for spin in [self.spinJogFrontX, self.spinJogFrontY, self.spinJogFrontYaw,
                     self.spinJogRearX, self.spinJogRearY, self.spinJogRearYaw]:
            spin.blockSignals(True)

        self.spinJogFrontX.setValue(jog_front.tx)
        self.spinJogFrontY.setValue(jog_front.ty)
        self.spinJogFrontYaw.setValue(math.degrees(jog_front.yaw))
        self.spinJogRearX.setValue(jog_rear.tx)
        self.spinJogRearY.setValue(jog_rear.ty)
        self.spinJogRearYaw.setValue(math.degrees(jog_rear.yaw))

        for spin in [self.spinJogFrontX, self.spinJogFrontY, self.spinJogFrontYaw,
                     self.spinJogRearX, self.spinJogRearY, self.spinJogRearYaw]:
            spin.blockSignals(False)

        self._jog_front = jog_front
        self._jog_rear = jog_rear

    @pyqtSlot()
    def _on_jog_changed(self):
        """User changed a jog spinbox → update display."""
        self._read_jog_from_spinboxes()
        self._update_canvas_points()

    def _update_canvas_points(self):
        """Transform raw scans to merged_lidar frame and send to canvas."""
        if self._raw_front is not None:
            front_merged = RosScanBridge.transform_points_2d(
                self._raw_front, self._jog_front)
            self._canvas.set_front_points(front_merged)

        if self._raw_rear is not None:
            rear_merged = RosScanBridge.transform_points_2d(
                self._raw_rear, self._jog_rear)
            self._canvas.set_rear_points(rear_merged)

        # Update sensor crosshair positions
        self._canvas.set_sensor_positions(
            (self._jog_front.tx, self._jog_front.ty, self._jog_front.yaw),
            (self._jog_rear.tx, self._jog_rear.ty, self._jog_rear.yaw),
        )

    # ── Scan callbacks ──

    @pyqtSlot(object)
    def _on_front_scan(self, points):
        self._raw_front = points
        if self._raw_front is not None:
            front_merged = RosScanBridge.transform_points_2d(
                self._raw_front, self._jog_front)
            self._canvas.set_front_points(front_merged)

    @pyqtSlot(object)
    def _on_rear_scan(self, points):
        self._raw_rear = points
        if self._raw_rear is not None:
            rear_merged = RosScanBridge.transform_points_2d(
                self._raw_rear, self._jog_rear)
            self._canvas.set_rear_points(rear_merged)

    @pyqtSlot(bool, bool)
    def _on_connection_status(self, front_connected, rear_connected):
        parts = []
        parts.append("Front: Connected" if front_connected else "Front: Disconnected")
        parts.append("Rear: Connected" if rear_connected else "Rear: Disconnected")
        self.statusbar.showMessage(" | ".join(parts))

    @pyqtSlot(int, int)
    def _on_scan_info(self, front_count, rear_count):
        self.statusbar.showMessage(f"Front: {front_count} pts | Rear: {rear_count} pts")

    @pyqtSlot(float, float)
    def _on_mouse_world_pos(self, x, y):
        self.statusbar.showMessage(f"Cursor: ({x:.3f}, {y:.3f}) m", 2000)

    # ── Load TF from config ──

    @pyqtSlot()
    def _on_load_tf(self):
        """Load initial TF from config parameters, populate jog spinboxes."""
        initial = self._ros_bridge.get_initial_tfs()
        if initial is None:
            self.statusbar.showMessage("Failed to load TF from config parameters", 5000)
            return

        jog_front = initial['merged_to_front']
        jog_rear = initial['merged_to_rear']
        tf_base_front = initial['tf_base_front']
        tf_base_rear = initial['tf_base_rear']

        self._write_jog_to_spinboxes(jog_front, jog_rear)

        # Sync flip checkboxes with config values
        self.chkFlipFront.blockSignals(True)
        self.chkFlipRear.blockSignals(True)
        self.chkFlipFront.setChecked(jog_front.flipped)
        self.chkFlipRear.setChecked(jog_rear.flipped)
        self.chkFlipFront.blockSignals(False)
        self.chkFlipRear.blockSignals(False)

        self._update_canvas_points()

        text = "Config TF Loaded\n"
        text += "=" * 50 + "\n\n"
        text += "1) base_link frame:\n"
        text += f"  base_link -> scan_front:\n"
        text += f"    tx={tf_base_front.tx:.4f} ty={tf_base_front.ty:.4f} "
        text += f"yaw={tf_base_front.yaw:.4f} rad ({math.degrees(tf_base_front.yaw):.2f}\u00b0) "
        text += f"flipped={tf_base_front.flipped}\n"
        text += f"  base_link -> scan_rear:\n"
        text += f"    tx={tf_base_rear.tx:.4f} ty={tf_base_rear.ty:.4f} "
        text += f"yaw={tf_base_rear.yaw:.4f} rad ({math.degrees(tf_base_rear.yaw):.2f}\u00b0) "
        text += f"flipped={tf_base_rear.flipped}\n\n"
        text += "2) Merged_lidar frame (jog values):\n"
        text += f"  merged -> scan_front:\n"
        text += f"    tx={jog_front.tx:.4f} ty={jog_front.ty:.4f} "
        text += f"yaw={jog_front.yaw:.4f} rad ({math.degrees(jog_front.yaw):.2f}\u00b0)\n"
        text += f"  merged -> scan_rear:\n"
        text += f"    tx={jog_rear.tx:.4f} ty={jog_rear.ty:.4f} "
        text += f"yaw={jog_rear.yaw:.4f} rad ({math.degrees(jog_rear.yaw):.2f}\u00b0)\n\n"
        text += "(Jog spinboxes show merged_lidar-relative values)\n"
        self.textResults.setPlainText(text)

        self.statusbar.showMessage(
            f"Config loaded: base->front yaw={math.degrees(tf_base_front.yaw):.1f}\u00b0, "
            f"base->rear yaw={math.degrees(tf_base_rear.yaw):.1f}\u00b0 | "
            f"merged->front yaw={math.degrees(jog_front.yaw):.1f}\u00b0, "
            f"merged->rear yaw={math.degrees(jog_rear.yaw):.1f}\u00b0", 10000)

    # ── Region management ──

    @pyqtSlot(float, float, float, float)
    def _on_rectangle_completed(self, x1, y1, x2, y2):
        region_idx = self._region_manager.add_region(x1, y1, x2, y2)
        self.statusbar.showMessage(
            f"Region {region_idx} added: ({x1:.2f}, {y1:.2f}) to ({x2:.2f}, {y2:.2f})", 3000)
        self._canvas.set_interaction_mode(InteractionMode.PAN)

    @pyqtSlot()
    def _on_add_region_clicked(self):
        self._canvas.set_interaction_mode(InteractionMode.DRAW_REGION)
        self.statusbar.showMessage("Draw region: Click two corners", 5000)

    @pyqtSlot()
    def _on_remove_region(self):
        current_row = self.listRegions.currentRow()
        if current_row >= 0:
            self._region_manager.remove_region(current_row)

    @pyqtSlot()
    def _on_clear_regions(self):
        self._region_manager.clear_all()

    @pyqtSlot()
    def _update_region_list(self):
        self.listRegions.clear()
        regions = self._region_manager.get_regions()
        for idx, region in enumerate(regions):
            label = region.label if region.label else f"Region {idx}"
            bounds = f"({region.x_min:.2f}, {region.y_min:.2f}) to ({region.x_max:.2f}, {region.y_max:.2f})"
            self.listRegions.addItem(f"{label}: {bounds}")
        self._canvas.set_regions(regions)

    @pyqtSlot()
    def _on_reconnect(self):
        front_topic = self.editFrontTopic.text().strip()
        rear_topic = self.editRearTopic.text().strip()
        self._ros_bridge.scan_topic_front = front_topic
        self._ros_bridge.scan_topic_rear = rear_topic
        self.statusbar.showMessage(
            f"Topics updated: {front_topic}, {rear_topic} (restart to reconnect)", 5000)

    # ── Calibration ──

    @pyqtSlot()
    def _on_run_calibration(self):
        if self._raw_front is None or self._raw_rear is None:
            self.textResults.setPlainText("Error: No scan data available")
            return

        regions = self._region_manager.get_regions()
        if len(regions) == 0:
            self.textResults.setPlainText("Error: No regions defined. Add at least one region.")
            return

        config = ICPConfig(
            max_iterations=self.spinMaxIter.value(),
            max_correspondence_dist=self.spinMaxCorrDist.value(),
            min_correspondences=self.spinMinCorr.value()
        )

        downsample_stride = self.spinDownsample.value()
        raw_front = self._raw_front
        raw_rear = self._raw_rear

        if downsample_stride > 1:
            raw_front = raw_front[::downsample_stride]
            raw_rear = raw_rear[::downsample_stride]

        self._read_jog_from_spinboxes()

        self.textResults.clear()
        self.btnRunCalibration.setEnabled(False)
        self.btnSaveResults.setEnabled(False)
        self.btnApplyBroadcast.setEnabled(False)

        # Run ICP in background thread to avoid UI freeze
        self._calibration_worker = CalibrationWorker(
            self._engine, raw_front, raw_rear,
            self._jog_front, self._jog_rear,
            regions, config)
        self._calibration_worker.error.connect(
            lambda msg: self.textResults.setPlainText(f"Error: {msg}"))
        self._calibration_worker.finished.connect(self._on_calibration_worker_finished)
        self._calibration_worker.start()

    def _on_calibration_worker_finished(self):
        """Re-enable button when worker finishes (success or failure)."""
        if not self.btnRunCalibration.isEnabled():
            # Only re-enable if calibration_complete didn't already do it
            pass  # calibration_complete/error handlers manage button state

    @pyqtSlot(int, object)
    def _on_region_result(self, region_idx, result):
        text = self.textResults.toPlainText()
        status = "CONVERGED" if result.converged else "NOT CONVERGED"
        text += (
            f"Region {region_idx}: [{status}]\n"
            f"  dx={result.dx:.4f} m, dy={result.dy:.4f} m, "
            f"dyaw={math.degrees(result.dyaw):.3f}\u00b0\n"
            f"  correspondences={result.num_correspondences}\n"
            f"  mean_dist={result.mean_correspondence_distance:.4f} m\n\n"
        )
        self.textResults.setPlainText(text)

    @pyqtSlot(object)
    def _on_calibration_complete(self, output: CalibrationOutput):
        text = self.textResults.toPlainText()
        text += "=" * 50 + "\n"
        text += "CALIBRATION RESULTS (merged_lidar-centric)\n"
        text += "=" * 50 + "\n\n"

        text += f"ICP Correction (median):\n"
        text += f"  dx={output.icp_correction.tx:.4f} m\n"
        text += f"  dy={output.icp_correction.ty:.4f} m\n"
        text += f"  dyaw={math.degrees(output.icp_correction.yaw):.3f}\u00b0\n\n"

        text += f"merged_lidar -> scan_front (unchanged):\n"
        text += f"  tx={output.jog_front.tx:.4f} ty={output.jog_front.ty:.4f} "
        text += f"yaw={math.degrees(output.jog_front.yaw):.2f}\u00b0\n\n"

        text += f"merged_lidar -> scan_rear (before ICP):\n"
        text += f"  tx={output.jog_rear_original.tx:.4f} ty={output.jog_rear_original.ty:.4f} "
        text += f"yaw={math.degrees(output.jog_rear_original.yaw):.2f}\u00b0\n\n"

        text += f"merged_lidar -> scan_rear (after ICP):\n"
        text += f"  tx={output.jog_rear_corrected.tx:.4f} ty={output.jog_rear_corrected.ty:.4f} "
        text += f"yaw={math.degrees(output.jog_rear_corrected.yaw):.2f}\u00b0\n\n"

        text += f"Statistics:\n"
        text += f"  Successful regions: {output.num_successful}\n"
        text += f"  Median corr distance: {output.median_correspondence_distance:.4f} m\n"

        self.textResults.setPlainText(text)

        # Update jog_rear spinboxes with corrected values
        self._write_jog_to_spinboxes(output.jog_front, output.jog_rear_corrected)
        self._update_canvas_points()

        self.btnRunCalibration.setEnabled(True)
        self.btnSaveResults.setEnabled(True)
        self.btnApplyBroadcast.setEnabled(True)
        self.statusbar.showMessage("Calibration complete!", 5000)

    @pyqtSlot(str)
    def _on_calibration_error(self, error_msg):
        self.textResults.setPlainText(f"CALIBRATION ERROR:\n{error_msg}")
        self.btnRunCalibration.setEnabled(True)
        self.statusbar.showMessage("Calibration failed", 5000)

    @pyqtSlot(str)
    def _on_progress_update(self, status_text):
        self.statusbar.showMessage(status_text)

    # ── Save / Broadcast ──

    @pyqtSlot()
    def _on_save_results(self):
        if self._engine.last_output is None:
            self.statusbar.showMessage("No results to save", 3000)
            return

        try:
            # Default to source config directory so results persist across builds
            default_dir = os.path.join('src', 'Sensor', 'Lidar', '2D', 'lidar_calibration_2d', 'config')
            default_file = os.path.join(default_dir, "calibration_result.yaml")

            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Calibration Results",
                default_file,
                "YAML files (*.yaml *.yml);;All files (*)",
                options=QFileDialog.DontUseNativeDialog)

            if not filepath:
                return  # User cancelled

            self._engine.save_results(self._engine.last_output, filepath)
            self.statusbar.showMessage(f"Saved: {filepath}", 5000)
        except Exception as e:
            self.statusbar.showMessage(f"Save failed: {str(e)}", 5000)

    @pyqtSlot()
    def _on_apply_broadcast(self):
        """Broadcast current jog TFs as static transforms (merged_lidar-centric)."""
        self._read_jog_from_spinboxes()
        broadcaster = tf2_ros.StaticTransformBroadcaster(self._node)

        transforms = []

        # merged_lidar -> scan_front (current spinbox values)
        t_front = self._make_transform_stamped(
            "merged_lidar", "scan_front_calibrated", self._jog_front)
        transforms.append(t_front)

        # merged_lidar -> scan_rear (current spinbox values)
        t_rear = self._make_transform_stamped(
            "merged_lidar", "scan_rear_calibrated", self._jog_rear)
        transforms.append(t_rear)

        broadcaster.sendTransform(transforms)

        self.statusbar.showMessage(
            "Broadcasting: merged_lidar -> scan_front_calibrated, scan_rear_calibrated", 5000)
        self._node.get_logger().info(
            f"Static TF broadcast: merged_lidar -> front "
            f"[{self._jog_front.tx:.4f}, {self._jog_front.ty:.4f}, "
            f"{math.degrees(self._jog_front.yaw):.2f}deg], "
            f"merged_lidar -> rear "
            f"[{self._jog_rear.tx:.4f}, {self._jog_rear.ty:.4f}, "
            f"{math.degrees(self._jog_rear.yaw):.2f}deg]")

    def _make_transform_stamped(self, parent_frame, child_frame, tf2d: TFTransform2D):
        t = TransformStamped()
        t.header.stamp = self._node.get_clock().now().to_msg()
        t.header.frame_id = parent_frame
        t.child_frame_id = child_frame
        t.transform.translation.x = tf2d.tx
        t.transform.translation.y = tf2d.ty
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = math.sin(tf2d.yaw / 2.0)
        t.transform.rotation.w = math.cos(tf2d.yaw / 2.0)
        return t

    # ── Symmetry Review ──

    @pyqtSlot()
    def _on_check_symmetry(self):
        """Analyze symmetry between current front/rear jog values."""
        self._read_jog_from_spinboxes()
        info = compute_symmetry_info(self._jog_front, self._jog_rear)

        text = "Symmetry Analysis\n"
        text += "=" * 40 + "\n\n"
        text += "Current values:\n"
        text += f"  Front: tx={self._jog_front.tx:.4f}  "
        text += f"ty={self._jog_front.ty:.4f}  "
        text += f"yaw={math.degrees(self._jog_front.yaw):.2f}\u00b0\n"
        text += f"  Rear:  tx={self._jog_rear.tx:.4f}  "
        text += f"ty={self._jog_rear.ty:.4f}  "
        text += f"yaw={math.degrees(self._jog_rear.yaw):.2f}\u00b0\n\n"

        text += "Ideal symmetric rear:\n"
        text += f"  tx={info['ideal_rear_tx']:.4f}  "
        text += f"ty={info['ideal_rear_ty']:.4f}  "
        text += f"yaw={math.degrees(info['ideal_rear_yaw']):.2f}\u00b0\n\n"

        text += "Asymmetry:\n"
        text += f"  \u0394tx={info['delta_tx']:.4f} m  "
        text += f"\u0394ty={info['delta_ty']:.4f} m  "
        text += f"\u0394yaw={math.degrees(info['delta_yaw']):.3f}\u00b0\n\n"

        if info['is_symmetric']:
            text += ">> SYMMETRIC (within threshold)"
        else:
            text += ">> NOT SYMMETRIC\n"
            text += "   Use 'Mirror Front->Rear' or manually adjust."

        self.textSymmetry.setPlainText(text)
        self.statusbar.showMessage(
            f"Symmetry: \u0394tx={info['delta_tx']:.4f} "
            f"\u0394ty={info['delta_ty']:.4f} "
            f"\u0394yaw={math.degrees(info['delta_yaw']):.3f}\u00b0", 5000)

    @pyqtSlot()
    def _on_mirror_front_to_rear(self):
        """Set rear jog to perfect mirror of front jog."""
        self._read_jog_from_spinboxes()
        mirrored_rear = mirror_front_to_rear(self._jog_front, self._jog_rear.flipped)
        self._write_jog_to_spinboxes(self._jog_front, mirrored_rear)
        self._update_canvas_points()

        self.textSymmetry.setPlainText(
            f"Mirror applied:\n"
            f"  Rear tx={mirrored_rear.tx:.4f}  "
            f"ty={mirrored_rear.ty:.4f}  "
            f"yaw={math.degrees(mirrored_rear.yaw):.2f}\u00b0\n\n"
            f"Adjust spinboxes if fine-tuning needed,\n"
            f"then Save Current Jog.")
        self.statusbar.showMessage("Mirror applied: rear = symmetric of front", 5000)

    @pyqtSlot()
    def _on_symmetric_correction(self):
        """Split ICP correction equally between front and rear.
        Requires ICP calibration to have been run first."""
        if self._engine.last_output is None:
            self.textSymmetry.setPlainText(
                "ICP calibration result required.\n"
                "Run Calibration first, then apply Symmetric Correction.")
            self.statusbar.showMessage("No ICP result — run calibration first", 5000)
            return

        output = self._engine.last_output
        before_front = output.jog_front
        before_rear_orig = output.jog_rear_original
        icp_corr = output.icp_correction

        sym_front, sym_rear = apply_symmetric_correction(
            before_front, before_rear_orig, icp_corr)

        # Update engine's last_output so Save Results also reflects symmetric values
        half_corr = TFTransform2D(
            tx=icp_corr.tx / 2.0, ty=icp_corr.ty / 2.0, yaw=icp_corr.yaw / 2.0)
        self._engine._last_output = CalibrationOutput(
            icp_correction=half_corr,
            jog_front=sym_front,
            jog_rear_original=before_rear_orig,
            jog_rear_corrected=sym_rear,
            num_successful=output.num_successful,
            median_correspondence_distance=output.median_correspondence_distance,
        )

        self._write_jog_to_spinboxes(sym_front, sym_rear)
        self._update_canvas_points()

        text = "Symmetric Correction Applied\n"
        text += "=" * 40 + "\n\n"
        text += f"ICP correction: dx={icp_corr.tx:.4f}  "
        text += f"dy={icp_corr.ty:.4f}  "
        text += f"dyaw={math.degrees(icp_corr.yaw):.3f}\u00b0\n\n"
        text += "Before (ICP full to rear only):\n"
        text += f"  Front: tx={before_front.tx:.4f}  "
        text += f"ty={before_front.ty:.4f}  "
        text += f"yaw={math.degrees(before_front.yaw):.2f}\u00b0\n"
        text += f"  Rear:  tx={output.jog_rear_corrected.tx:.4f}  "
        text += f"ty={output.jog_rear_corrected.ty:.4f}  "
        text += f"yaw={math.degrees(output.jog_rear_corrected.yaw):.2f}\u00b0\n\n"
        text += "After (correction split equally):\n"
        text += f"  Front: tx={sym_front.tx:.4f}  "
        text += f"ty={sym_front.ty:.4f}  "
        text += f"yaw={math.degrees(sym_front.yaw):.2f}\u00b0\n"
        text += f"  Rear:  tx={sym_rear.tx:.4f}  "
        text += f"ty={sym_rear.ty:.4f}  "
        text += f"yaw={math.degrees(sym_rear.yaw):.2f}\u00b0\n\n"
        text += "Front: -correction/2, Rear: +correction/2\n"
        text += "Save Current Jog to persist."
        self.textSymmetry.setPlainText(text)
        self.statusbar.showMessage("Symmetric correction: ICP split equally to both sensors", 5000)

    @pyqtSlot()
    def _on_save_current_jog(self):
        """Save current spinbox jog values to YAML (independent of ICP result)."""
        self._read_jog_from_spinboxes()

        # Build a CalibrationOutput from current spinbox values
        icp_correction = TFTransform2D()  # zero correction
        jog_rear_original = self._jog_rear
        if self._engine.last_output is not None:
            icp_correction = self._engine.last_output.icp_correction
            jog_rear_original = self._engine.last_output.jog_rear_original

        output = CalibrationOutput(
            icp_correction=icp_correction,
            jog_front=self._jog_front,
            jog_rear_original=jog_rear_original,
            jog_rear_corrected=self._jog_rear,
            num_successful=(self._engine.last_output.num_successful
                            if self._engine.last_output else 0),
            median_correspondence_distance=(
                self._engine.last_output.median_correspondence_distance
                if self._engine.last_output else 0.0),
        )

        try:
            default_dir = os.path.join('src', 'Sensor', 'Lidar', '2D', 'lidar_calibration_2d', 'config')
            default_file = os.path.join(default_dir, "calibration_result.yaml")

            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Current Jog Values",
                default_file,
                "YAML files (*.yaml *.yml);;All files (*)",
                options=QFileDialog.DontUseNativeDialog)

            if not filepath:
                return

            save_calibration_yaml(output, filepath)
            self.statusbar.showMessage(f"Current jog saved: {filepath}", 5000)
        except Exception as e:
            self.statusbar.showMessage(f"Save failed: {str(e)}", 5000)
