"""
gz_migrator/migrator.py
=======================
Core migration engine: Gazebo Classic (.world / SDFormat ≤1.7)
→ Gazebo Harmonic (gz-sim8 / SDFormat 1.11)

Covers:
  1. SDF version header bump
  2. World-level structural changes
  3. Plugin migration (model + world plugins)
  4. Sensor tag migration (ray→gpu_lidar, camera, imu, depth, contact, sonar)
  5. Physics engine updates (ODE→DART/bullet parameters)
  6. Material migration (Ogre scripts → ambient/diffuse/specular)
  7. URI / resource path updates
  8. Deprecated tag removal / warnings
"""

import re
import copy
import logging
from lxml import etree
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

logger = logging.getLogger("gz_migrator")

# ---------------------------------------------------------------------------
# Plugin mapping table
# Classic filename  →  (new filename, new name attribute)
# ---------------------------------------------------------------------------
PLUGIN_MAP = {
    # Differential drive
    "libDiffDrivePlugin.so":              ("gz-sim-diff-drive-system",              "gz::sim::systems::DiffDrive"),
    "libgazebo_ros_diff_drive.so":        ("gz-sim-diff-drive-system",              "gz::sim::systems::DiffDrive"),
    # Joint state publisher
    "libgazebo_ros_joint_state_publisher.so": ("gz-sim-joint-state-publisher-system", "gz::sim::systems::JointStatePublisher"),
    "libJointStatePublisherPlugin.so":    ("gz-sim-joint-state-publisher-system",   "gz::sim::systems::JointStatePublisher"),
    # Skid steer drive
    "libSkidSteerDrivePlugin.so":         ("gz-sim-diff-drive-system",              "gz::sim::systems::DiffDrive"),
    "libgazebo_ros_skid_steer_drive.so":  ("gz-sim-diff-drive-system",              "gz::sim::systems::DiffDrive"),
    # Ackermann steering
    "libAckermannDrivePlugin.so":         ("gz-sim-ackermann-steering-system",      "gz::sim::systems::AckermannSteering"),
    # Velocity control
    "libVelocityPlugin.so":               ("gz-sim-velocity-control-system",        "gz::sim::systems::VelocityControl"),
    "libgazebo_ros_planar_move.so":       ("gz-sim-velocity-control-system",        "gz::sim::systems::VelocityControl"),
    # Pose publisher
    "libgazebo_ros_p3d.so":               ("gz-sim-pose-publisher-system",          "gz::sim::systems::PosePublisher"),
    "libPosePublisherPlugin.so":          ("gz-sim-pose-publisher-system",          "gz::sim::systems::PosePublisher"),
    # Buoyancy
    "libBuoyancyPlugin.so":               ("gz-sim-buoyancy-system",                "gz::sim::systems::Buoyancy"),
    # Wind
    "libWindPlugin.so":                   ("gz-sim-wind-effects-system",            "gz::sim::systems::WindEffects"),
    # Lift drag
    "libLiftDragPlugin.so":               ("gz-sim-lift-drag-system",               "gz::sim::systems::LiftDrag"),
    # Magnetometer
    "libMagnetometerPlugin.so":           ("gz-sim-magnetometer-system",            "gz::sim::systems::Magnetometer"),
    # Altimeter
    "libAltimeterPlugin.so":              ("gz-sim-altimeter-system",               "gz::sim::systems::Altimeter"),
    # Air pressure
    "libAirPressurePlugin.so":            ("gz-sim-air-pressure-system",            "gz::sim::systems::AirPressure"),
    # Battery
    "libLinearBatteryPlugin.so":          ("gz-sim-linearbatteryplugin-system",     "gz::sim::systems::LinearBatteryPlugin"),
    "libgazebo_ros_battery.so":           ("gz-sim-linearbatteryplugin-system",     "gz::sim::systems::LinearBatteryPlugin"),
    # Triggered publisher
    "libTriggeredPublisherPlugin.so":     ("gz-sim-triggered-publisher-system",     "gz::sim::systems::TriggeredPublisher"),
    # Logical camera
    "libLogicalCameraPlugin.so":          ("gz-sim-logical-camera-system",          "gz::sim::systems::LogicalCamera"),
    # Thermal camera
    "libThermalCameraPlugin.so":          ("gz-sim-thermal-sensor-system",          "gz::sim::systems::ThermalSensor"),
    # Depth camera / RGBD
    "libgazebo_ros_depth_camera.so":      ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    "libgazebo_ros_openni_kinect.so":     ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    # Camera
    "libgazebo_ros_camera.so":            ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    "libCameraPlugin.so":                 ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    # IMU
    "libgazebo_ros_imu_sensor.so":        ("gz-sim-imu-system",                     "gz::sim::systems::Imu"),
    "libgazebo_ros_imu.so":               ("gz-sim-imu-system",                     "gz::sim::systems::Imu"),
    "libImuSensorPlugin.so":              ("gz-sim-imu-system",                     "gz::sim::systems::Imu"),
    # Lidar / ray
    "libgazebo_ros_ray_sensor.so":        ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    "libgazebo_ros_laser.so":             ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    "libRayPlugin.so":                    ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    "libGpuRayPlugin.so":                 ("gz-sim-sensors-system",                 "gz::sim::systems::Sensors"),
    # GPS
    "libgazebo_ros_gps_sensor.so":        ("gz-sim-navsat-system",                  "gz::sim::systems::NavSat"),
    "libGpsPlugin.so":                    ("gz-sim-navsat-system",                  "gz::sim::systems::NavSat"),
    # Contact sensor
    "libgazebo_ros_bumper.so":            ("gz-sim-contact-system",                 "gz::sim::systems::Contact"),
    "libContactPlugin.so":                ("gz-sim-contact-system",                 "gz::sim::systems::Contact"),
    # Force torque
    "libgazebo_ros_ft_sensor.so":         ("gz-sim-forcetorque-system",             "gz::sim::systems::ForceTorque"),
    "libForceTorquePlugin.so":            ("gz-sim-forcetorque-system",             "gz::sim::systems::ForceTorque"),
    # Joint position controller
    "libgazebo_ros_joint_pose_trajectory.so": ("gz-sim-joint-position-controller-system", "gz::sim::systems::JointPositionController"),
    # Model mover / apply force
    "libgazebo_ros_force.so":             ("gz-sim-apply-joint-force-system",       "gz::sim::systems::ApplyJointForce"),
    # Wheel slip
    "libWheelSlipPlugin.so":              ("gz-sim-wheel-slip-system",              "gz::sim::systems::WheelSlip"),
    # Hydrodynamics
    "libHydrodynamicsPlugin.so":          ("gz-sim-hydrodynamics-system",           "gz::sim::systems::Hydrodynamics"),
    # Multicopter motor model
    "libgazebo_motor_model.so":           ("gz-sim-multicopter-motor-model-system", "gz::sim::systems::MulticopterMotorModel"),
    # Physics (world plugin)
    "libgazebo_ros_api_plugin.so":        ("gz-sim-physics-system",                 "gz::sim::systems::Physics"),
    # Gazebo ROS state
    "libgazebo_ros_state.so":             ("gz-sim-pose-publisher-system",          "gz::sim::systems::PosePublisher"),
    # Clock
    "libgazebo_ros_clock.so":             None,  # handled by gz-transport natively
}

# World-level default plugins to inject when none present
WORLD_DEFAULT_PLUGINS = [
    ("gz-sim-physics-system",           "gz::sim::systems::Physics"),
    ("gz-sim-user-commands-system",     "gz::sim::systems::UserCommands"),
    ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
    ("gz-sim-sensors-system",           "gz::sim::systems::Sensors"),
    ("gz-sim-imu-system",               "gz::sim::systems::Imu"),
    ("gz-sim-contact-system",           "gz::sim::systems::Contact"),
    ("gz-sim-navsat-system",            "gz::sim::systems::NavSat"),
]

# Sensor type mapping
SENSOR_TYPE_MAP = {
    "ray":          "gpu_lidar",
    "gpu_ray":      "gpu_lidar",
    "sonar":        "gpu_lidar",   # approximate
    "wireless_transmitter": None,  # not supported, warn
    "wireless_receiver":    None,
}

# Gazebo material name → RGBA (ambient = diffuse)
GAZEBO_MATERIAL_COLORS = {
    "Gazebo/Red":           (1.0, 0.0, 0.0, 1.0),
    "Gazebo/Green":         (0.0, 1.0, 0.0, 1.0),
    "Gazebo/Blue":          (0.0, 0.0, 1.0, 1.0),
    "Gazebo/White":         (1.0, 1.0, 1.0, 1.0),
    "Gazebo/Black":         (0.0, 0.0, 0.0, 1.0),
    "Gazebo/Yellow":        (1.0, 1.0, 0.0, 1.0),
    "Gazebo/Orange":        (1.0, 0.5, 0.0, 1.0),
    "Gazebo/Purple":        (0.5, 0.0, 0.5, 1.0),
    "Gazebo/Turquoise":     (0.0, 1.0, 1.0, 1.0),
    "Gazebo/DarkYellow":    (0.7, 0.7, 0.0, 1.0),
    "Gazebo/Grey":          (0.5, 0.5, 0.5, 1.0),
    "Gazebo/DarkGrey":      (0.3, 0.3, 0.3, 1.0),
    "Gazebo/LightGrey":     (0.7, 0.7, 0.7, 1.0),
    "Gazebo/SkyBlue":       (0.5, 0.5, 1.0, 1.0),
    "Gazebo/ZincYellow":    (0.9, 0.8, 0.0, 1.0),
    "Gazebo/CoralOrange":   (1.0, 0.5, 0.3, 1.0),
    "Gazebo/WoodFloor":     (0.6, 0.4, 0.2, 1.0),
    "Gazebo/CastIron":      (0.2, 0.2, 0.2, 1.0),
    "Gazebo/Grass":         (0.2, 0.6, 0.1, 1.0),
}


@dataclass
class MigrationReport:
    """Structured report of all changes made during migration."""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_change(self, msg: str):
        self.changes.append(msg)
        logger.info("CHANGE: %s", msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        logger.warning("WARN: %s", msg)

    def add_error(self, msg: str):
        self.errors.append(msg)
        logger.error("ERROR: %s", msg)

    def summary(self) -> str:
        lines = [
            f"Migration Summary",
            f"=================",
            f"Changes applied : {len(self.changes)}",
            f"Warnings        : {len(self.warnings)}",
            f"Errors          : {len(self.errors)}",
            "",
        ]
        if self.changes:
            lines.append("Changes:")
            for c in self.changes:
                lines.append(f"  ✓ {c}")
            lines.append("")
        if self.warnings:
            lines.append("Warnings (manual review recommended):")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
            lines.append("")
        if self.errors:
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  ✗ {e}")
        return "\n".join(lines)


class GazeboMigrator:
    """
    Migrates a Gazebo Classic .world / .sdf file to Gazebo Harmonic SDFormat 1.11.
    """

    def __init__(self, input_xml: str):
        """
        Parameters
        ----------
        input_xml : str
            Raw XML string of the source .world / .sdf file.
        """
        self.report = MigrationReport()
        try:
            parser = etree.XMLParser(remove_comments=False, remove_blank_text=False)
            self.tree = etree.fromstring(input_xml.encode("utf-8"), parser)
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Invalid XML: {exc}") from exc

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def migrate(self) -> Tuple[str, MigrationReport]:
        """Run all migration steps and return (output_xml, report)."""
        self._step_sdf_version()
        self._step_world_plugins()
        self._step_model_plugins()
        self._step_sensors()
        self._step_physics()
        self._step_materials()
        self._step_uris()
        self._step_deprecated_tags()
        self._step_gravity()
        self._step_magnetic_field()
        self._step_atmosphere()

        output = etree.tostring(
            self.tree,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        ).decode("utf-8")
        return output, self.report

    # ------------------------------------------------------------------
    # Step 1 – SDF version
    # ------------------------------------------------------------------

    def _step_sdf_version(self):
        root = self.tree
        tag = root.tag.lower()

        # Handle both <sdf> root and bare <world> root (some .world files)
        if tag == "sdf":
            old_ver = root.get("version", "unknown")
            root.set("version", "1.11")
            self.report.add_change(f"SDF version updated: {old_ver} → 1.11")
        elif tag == "world":
            # Wrap bare <world> in <sdf version="1.11">
            sdf_root = etree.Element("sdf")
            sdf_root.set("version", "1.11")
            sdf_root.append(copy.deepcopy(root))
            self.tree = sdf_root
            self.report.add_change("Wrapped bare <world> element in <sdf version=\"1.11\">")
        else:
            self.report.add_warning(f"Unexpected root element <{root.tag}>; SDF version not updated")

    # ------------------------------------------------------------------
    # Step 2 – World-level plugins
    # ------------------------------------------------------------------

    def _step_world_plugins(self):
        worlds = self.tree.findall(".//world")
        for world in worlds:
            self._migrate_world_plugins(world)

    def _migrate_world_plugins(self, world: etree._Element):
        existing_plugins = world.findall("plugin")
        existing_names = {p.get("name", "") for p in existing_plugins}

        # Migrate existing world plugins
        for plugin in list(existing_plugins):
            self._migrate_plugin_element(plugin, context="world")

        # Inject required default plugins if missing
        needed = []
        for filename, name in WORLD_DEFAULT_PLUGINS:
            if name not in existing_names:
                needed.append((filename, name))

        if needed:
            # Insert after last existing plugin, or at start of world
            insert_idx = 0
            children = list(world)
            for i, child in enumerate(children):
                if child.tag == "plugin":
                    insert_idx = i + 1

            comment = etree.Comment(" Auto-injected by gz_migrator: required Gazebo Harmonic world plugins ")
            world.insert(insert_idx, comment)
            insert_idx += 1

            for filename, name in needed:
                p = etree.Element("plugin")
                p.set("filename", filename)
                p.set("name", name)
                if name == "gz::sim::systems::Sensors":
                    re_elem = etree.SubElement(p, "render_engine")
                    re_elem.text = "ogre2"
                world.insert(insert_idx, p)
                insert_idx += 1
                self.report.add_change(f"Injected world plugin: {name}")

    # ------------------------------------------------------------------
    # Step 3 – Model-level plugins
    # ------------------------------------------------------------------

    def _step_model_plugins(self):
        for plugin in self.tree.findall(".//model/plugin") + self.tree.findall(".//link/plugin"):
            self._migrate_plugin_element(plugin, context="model")

    # ------------------------------------------------------------------
    # Plugin migration helper
    # ------------------------------------------------------------------

    def _migrate_plugin_element(self, plugin: etree._Element, context: str):
        filename = plugin.get("filename", "")
        old_name = plugin.get("name", "")

        if filename not in PLUGIN_MAP:
            # Check for partial match (e.g. without lib prefix or .so suffix)
            matched = None
            for key in PLUGIN_MAP:
                if key.replace("lib", "").replace(".so", "") in filename:
                    matched = key
                    break
            if matched:
                filename = matched
            else:
                self.report.add_warning(
                    f"Unknown plugin '{filename}' (name='{old_name}') — kept as-is; manual migration required"
                )
                return

        mapping = PLUGIN_MAP[filename]

        if mapping is None:
            # Plugin is obsolete / handled natively
            parent = plugin.getparent()
            if parent is not None:
                parent.remove(plugin)
            self.report.add_change(
                f"Removed obsolete plugin '{filename}' (handled natively by Gazebo Harmonic)"
            )
            return

        new_filename, new_name = mapping

        # Migrate ROS-specific parameters inside the plugin
        self._migrate_plugin_params(plugin, filename, new_filename)

        plugin.set("filename", new_filename)
        plugin.set("name", new_name)
        self.report.add_change(
            f"Plugin migrated: '{filename}' → '{new_filename}' (name='{new_name}')"
        )

    def _migrate_plugin_params(self, plugin: etree._Element, old_filename: str, new_filename: str):
        """Migrate internal plugin parameters."""
        # Remove <ros> sub-element (ROS 1 style)
        for ros_elem in plugin.findall("ros"):
            plugin.remove(ros_elem)
            self.report.add_change("Removed <ros> sub-element from plugin (use ros_gz_bridge instead)")

        # DiffDrive specific — check both old and new filename
        is_diff_drive = (
            "diff_drive" in new_filename or "DiffDrive" in new_filename or
            "diff_drive" in old_filename or "DiffDrive" in old_filename or
            "DiffDrive" in old_filename.replace("lib", "").replace(".so", "") or
            "SkidSteer" in old_filename
        )
        if is_diff_drive:
            self._migrate_diff_drive_params(plugin)

        # JointStatePublisher
        if "joint-state-publisher" in new_filename:
            # <update_rate> not supported
            for ur in plugin.findall("update_rate"):
                plugin.remove(ur)
                self.report.add_warning("Removed <update_rate> from JointStatePublisher (not supported in Harmonic)")

        # Rename <commandTopic> → <topic>, <odometryTopic> → <odom_topic>
        renames = {
            "commandTopic": "topic",
            "command_topic": "topic",
            "odometryTopic": "odom_topic",
            "odometry_topic": "odom_topic",
            "odometryFrame": "frame_id",
            "odometry_frame": "frame_id",
            "robotBaseFrame": "child_frame_id",
            "robot_base_frame": "child_frame_id",
        }
        for old_tag, new_tag in renames.items():
            for elem in plugin.findall(old_tag):
                elem.tag = new_tag
                self.report.add_change(f"Plugin param renamed: <{old_tag}> → <{new_tag}>")

    def _migrate_diff_drive_params(self, plugin: etree._Element):
        """Handle DiffDrive-specific parameter conversions."""
        # <wheelDiameter> → <wheel_radius> (halved)
        for wd in plugin.findall("wheelDiameter"):
            try:
                diameter = float(wd.text.strip())
                wr = etree.Element("wheel_radius")
                wr.text = str(round(diameter / 2.0, 6))
                plugin.replace(wd, wr)
                self.report.add_change(f"DiffDrive: <wheelDiameter>{diameter}</wheelDiameter> → <wheel_radius>{diameter/2}</wheel_radius>")
            except (ValueError, AttributeError):
                wd.tag = "wheel_radius"
                self.report.add_warning("DiffDrive: <wheelDiameter> renamed to <wheel_radius>; divide by 2 manually")

        # <wheelSeparation> → <wheel_separation>
        for ws in plugin.findall("wheelSeparation"):
            ws.tag = "wheel_separation"
            self.report.add_change("DiffDrive: <wheelSeparation> → <wheel_separation>")

        # <max_wheel_acceleration> → approximate <max_linear_acceleration>
        for mwa in plugin.findall("max_wheel_acceleration"):
            mwa.tag = "max_linear_acceleration"
            self.report.add_warning(
                "DiffDrive: <max_wheel_acceleration> renamed to <max_linear_acceleration>; "
                "multiply value by wheel radius for accurate conversion"
            )

    # ------------------------------------------------------------------
    # Step 4 – Sensor migration
    # ------------------------------------------------------------------

    def _step_sensors(self):
        for sensor in self.tree.findall(".//sensor"):
            self._migrate_sensor(sensor)

    def _migrate_sensor(self, sensor: etree._Element):
        stype = sensor.get("type", "")

        # Migrate sensor type
        if stype in SENSOR_TYPE_MAP:
            new_type = SENSOR_TYPE_MAP[stype]
            if new_type is None:
                self.report.add_warning(
                    f"Sensor type '{stype}' (name='{sensor.get('name', '')}') is not supported in Gazebo Harmonic"
                )
                return
            sensor.set("type", new_type)
            self.report.add_change(f"Sensor type migrated: '{stype}' → '{new_type}'")

            # <ray> → <lidar>
            if stype in ("ray", "gpu_ray", "sonar"):
                for ray_elem in sensor.findall("ray"):
                    ray_elem.tag = "lidar"
                    self.report.add_change("Sensor: <ray> element renamed to <lidar>")

        # Remove sensor-level plugins (handled by world plugins now)
        for plugin in sensor.findall("plugin"):
            pfn = plugin.get("filename", "")
            sensor.remove(plugin)
            self.report.add_change(
                f"Removed sensor-level plugin '{pfn}' (sensors handled by world-level gz-sim-sensors-system)"
            )

        # Add <topic> if missing (use sensor name as default)
        if sensor.find("topic") is None:
            sname = sensor.get("name", "sensor")
            topic_elem = etree.SubElement(sensor, "topic")
            topic_elem.text = sname
            self.report.add_change(f"Added <topic>{sname}</topic> to sensor '{sname}'")

        # Camera: add <camera_info_topic>
        if sensor.get("type") == "camera":
            cam = sensor.find("camera")
            if cam is not None and cam.find("camera_info_topic") is None:
                sname = sensor.get("name", "camera")
                ci = etree.SubElement(cam, "camera_info_topic")
                ci.text = f"{sname}/camera_info"
                self.report.add_change(f"Added <camera_info_topic> to camera sensor '{sname}'")

        # IMU: ensure <always_on> present
        if sensor.get("type") == "imu":
            if sensor.find("always_on") is None:
                ao = etree.Element("always_on")
                ao.text = "true"
                sensor.insert(0, ao)

    # ------------------------------------------------------------------
    # Step 5 – Physics
    # ------------------------------------------------------------------

    def _step_physics(self):
        for physics in self.tree.findall(".//physics"):
            self._migrate_physics(physics)

    def _migrate_physics(self, physics: etree._Element):
        ptype = physics.get("type", "ode").lower()

        if ptype == "ode":
            physics.set("type", "dart")
            self.report.add_change("Physics engine type changed: 'ode' → 'dart'")

            # Migrate ODE-specific tags
            ode_elem = physics.find("ode")
            if ode_elem is not None:
                # Move solver settings to dart-compatible structure
                solver = ode_elem.find("solver")
                constraints = ode_elem.find("constraints")

                dart_elem = etree.SubElement(physics, "dart")

                if solver is not None:
                    # iters → max_step_size approximation
                    iters_elem = solver.find("iters")
                    if iters_elem is not None:
                        self.report.add_warning(
                            f"ODE <solver><iters>{iters_elem.text}</iters> has no direct DART equivalent; removed"
                        )
                    # sor → no direct equivalent
                    sor_elem = solver.find("sor")
                    if sor_elem is not None:
                        self.report.add_warning(
                            "ODE <solver><sor> has no direct DART equivalent; removed"
                        )

                if constraints is not None:
                    cfm = constraints.find("cfm")
                    erp = constraints.find("erp")
                    if cfm is not None:
                        self.report.add_warning(
                            f"ODE <constraints><cfm>{cfm.text}</cfm> has no direct DART equivalent; removed"
                        )
                    if erp is not None:
                        self.report.add_warning(
                            f"ODE <constraints><erp>{erp.text}</erp> has no direct DART equivalent; removed"
                        )

                # Remove old ODE block
                physics.remove(ode_elem)
                self.report.add_change("Removed <ode> physics block (replaced with <dart>)")

        elif ptype in ("bullet", "simbody"):
            self.report.add_warning(
                f"Physics type '{ptype}' — Gazebo Harmonic uses DART by default; "
                "consider switching to 'dart' for best compatibility"
            )

        # Ensure <max_step_size> and <real_time_factor> present
        if physics.find("max_step_size") is None:
            ms = etree.SubElement(physics, "max_step_size")
            ms.text = "0.001"
            self.report.add_change("Added default <max_step_size>0.001</max_step_size>")

        if physics.find("real_time_factor") is None:
            rf = etree.SubElement(physics, "real_time_factor")
            rf.text = "1"
            self.report.add_change("Added default <real_time_factor>1</real_time_factor>")

    # ------------------------------------------------------------------
    # Step 6 – Materials
    # ------------------------------------------------------------------

    def _step_materials(self):
        for material in self.tree.findall(".//material"):
            self._migrate_material(material)

    def _migrate_material(self, material: etree._Element):
        script = material.find("script")
        if script is None:
            return

        uri_elem = script.find("uri")
        name_elem = script.find("name")

        if uri_elem is None or name_elem is None:
            return

        uri_text = (uri_elem.text or "").strip()
        name_text = (name_elem.text or "").strip()

        # Check if it's a gazebo.material reference
        if "gazebo.material" in uri_text or "Gazebo/" in name_text:
            color = GAZEBO_MATERIAL_COLORS.get(name_text)
            if color:
                r, g, b, a = color
                # Replace <script> with <ambient>, <diffuse>, <specular>
                material.remove(script)

                ambient = etree.SubElement(material, "ambient")
                ambient.text = f"{r} {g} {b} {a}"

                diffuse = etree.SubElement(material, "diffuse")
                diffuse.text = f"{r} {g} {b} {a}"

                specular = etree.SubElement(material, "specular")
                specular.text = "0.1 0.1 0.1 1"

                self.report.add_change(
                    f"Material '{name_text}' converted from Ogre script to RGBA tags"
                )
            else:
                self.report.add_warning(
                    f"Material '{name_text}' uses Ogre script — not auto-convertible; "
                    "replace with <ambient>/<diffuse>/<specular> tags manually or use PBR textures"
                )
        elif "materials/scripts" in uri_text:
            self.report.add_warning(
                f"Material uses Ogre script at '{uri_text}' — Gazebo Harmonic does not support Ogre material scripts; "
                "use <ambient>/<diffuse>/<specular> or <pbr><metal><albedo_map> instead"
            )

    # ------------------------------------------------------------------
    # Step 7 – URIs
    # ------------------------------------------------------------------

    def _step_uris(self):
        for uri_elem in self.tree.findall(".//uri"):
            text = (uri_elem.text or "").strip()

            # model:// → keep as-is (still valid, but note env var change)
            if text.startswith("model://"):
                self.report.add_warning(
                    f"URI '{text}' uses model:// — ensure GZ_SIM_RESOURCE_PATH is set "
                    "(replaces GAZEBO_MODEL_PATH)"
                )

            # file:// media/materials → flag as Ogre resource
            if "media/materials" in text:
                self.report.add_warning(
                    f"URI '{text}' references Ogre media materials — not supported in Gazebo Harmonic"
                )

            # package:// → still valid for ROS 2 resource lookup
            # No change needed

    # ------------------------------------------------------------------
    # Step 8 – Deprecated tags
    # ------------------------------------------------------------------

    def _step_deprecated_tags(self):
        # <sdf_version> inside <include> is deprecated
        for sv in self.tree.findall(".//include/sdf_version"):
            parent = sv.getparent()
            parent.remove(sv)
            self.report.add_change("Removed deprecated <sdf_version> from <include>")

        # <static> on world is not valid
        for world in self.tree.findall(".//world"):
            for s in world.findall("static"):
                world.remove(s)
                self.report.add_change("Removed invalid <static> tag from <world>")

        # <allow_auto_disable> deprecated
        for aad in self.tree.findall(".//allow_auto_disable"):
            parent = aad.getparent()
            if parent is not None:
                parent.remove(aad)
                self.report.add_change("Removed deprecated <allow_auto_disable> tag")

        # <enable_wind> inside model — now handled by WindEffects system
        for ew in self.tree.findall(".//model/enable_wind"):
            self.report.add_warning(
                "<enable_wind> inside <model> — ensure gz-sim-wind-effects-system is loaded as a world plugin"
            )

    # ------------------------------------------------------------------
    # Step 9 – Gravity
    # ------------------------------------------------------------------

    def _step_gravity(self):
        for world in self.tree.findall(".//world"):
            # Old: <gravity>0 0 -9.8</gravity>  (valid in both)
            # New SDFormat 1.11 prefers <gravity> inside <physics> or at world level — already OK
            grav = world.find("gravity")
            if grav is not None:
                # Normalise to 3-component format
                text = (grav.text or "0 0 -9.8").strip()
                parts = text.split()
                if len(parts) == 3:
                    pass  # already correct
                elif len(parts) == 1:
                    grav.text = f"0 0 {parts[0]}"
                    self.report.add_change(f"Gravity normalised to 3-component vector: {grav.text}")

    # ------------------------------------------------------------------
    # Step 10 – Magnetic field
    # ------------------------------------------------------------------

    def _step_magnetic_field(self):
        for world in self.tree.findall(".//world"):
            # Old Gazebo used <magnetic_field> as a direct child of <world>
            # New: same tag is valid; just ensure it's present for NavSat
            mf = world.find("magnetic_field")
            if mf is None:
                # Add default Earth magnetic field
                mf = etree.SubElement(world, "magnetic_field")
                mf.text = "5.5645e-6 22.8758e-6 -42.3884e-6"
                self.report.add_change("Added default <magnetic_field> (Earth average) to world")

    # ------------------------------------------------------------------
    # Step 11 – Atmosphere
    # ------------------------------------------------------------------

    def _step_atmosphere(self):
        for world in self.tree.findall(".//world"):
            if world.find("atmosphere") is None:
                atm = etree.SubElement(world, "atmosphere")
                atm.set("type", "adiabatic")
                self.report.add_change("Added default <atmosphere type='adiabatic'> to world")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def migrate_file(input_path: str, output_path: str) -> MigrationReport:
    """
    Migrate a Gazebo Classic .world file to Gazebo Harmonic SDFormat 1.11.

    Parameters
    ----------
    input_path  : path to source .world / .sdf file
    output_path : path to write migrated .sdf file

    Returns
    -------
    MigrationReport
    """
    with open(input_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    migrator = GazeboMigrator(xml_content)
    output_xml, report = migrator.migrate()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_xml)

    return report


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate Gazebo Classic .world files to Gazebo Harmonic SDFormat 1.11"
    )
    parser.add_argument("input",  help="Input .world or .sdf file (Gazebo Classic)")
    parser.add_argument("output", help="Output .sdf file (Gazebo Harmonic)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s"
    )

    try:
        report = migrate_file(args.input, args.output)
        print(report.summary())
        print(f"\nOutput written to: {args.output}")
        sys.exit(0 if not report.errors else 1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
