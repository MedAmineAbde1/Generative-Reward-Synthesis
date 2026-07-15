# GZ Migrator — Gazebo Classic → Gazebo Harmonic

A comprehensive migration tool that automatically converts Gazebo Classic `.world` / `.sdf` files (SDFormat ≤1.7) to Gazebo Harmonic (gz-sim8, SDFormat 1.11).

---

## What Gets Migrated

| Category | Details |
|---|---|
| **SDF Version** | Updates `<sdf version>` from 1.6/1.7 → **1.11**; wraps bare `<world>` roots |
| **World Plugins** | Auto-injects: Physics, UserCommands, SceneBroadcaster, Sensors, Imu, Contact, NavSat |
| **Model Plugins** | Remaps 40+ `lib*.so` plugins to `gz-sim-*-system` equivalents with correct `name` attributes |
| **Sensor Tags** | `ray` → `gpu_lidar`, `<ray>` → `<lidar>`, removes sensor-level plugins, adds `<topic>` |
| **Physics Engine** | `type="ode"` → `type="dart"`, removes ODE solver/constraint blocks with warnings |
| **Materials** | Ogre `<script>` materials (Gazebo/Red, Blue, etc.) → `<ambient>`/`<diffuse>`/`<specular>` RGBA |
| **URIs** | Warns about `model://` needing `GZ_SIM_RESOURCE_PATH` (replaces `GAZEBO_MODEL_PATH`) |
| **Deprecated Tags** | Removes `<sdf_version>`, `<allow_auto_disable>`, `<ros>` sub-elements, invalid `<static>` on world |
| **DiffDrive params** | `<wheelDiameter>` → `<wheel_radius>` (halved), `<commandTopic>` → `<topic>`, etc. |

---

## Usage

### Option 1 — Web App (recommended)

```bash
pip3 install flask lxml
cd gz_migrator
python3 app.py
```

Then open **http://localhost:7860** in your browser.

- Drag & drop your `.world` file or paste XML directly
- View the migration report (changes, warnings, errors)
- Compare original vs migrated in side-by-side diff view
- Download the migrated `.sdf` file

### Option 2 — CLI Script

```bash
pip3 install lxml
python3 migrator.py input.world output.sdf
```

**Options:**
- `-v` / `--verbose` — Enable verbose logging

**Example output:**
```
Migration Summary
=================
Changes applied : 33
Warnings        : 7
Errors          : 0

Changes:
  ✓ SDF version updated: 1.6 → 1.11
  ✓ Injected world plugin: gz::sim::systems::Physics
  ✓ Plugin migrated: 'libgazebo_ros_diff_drive.so' → 'gz-sim-diff-drive-system'
  ✓ Sensor type migrated: 'ray' → 'gpu_lidar'
  ✓ Physics engine type changed: 'ode' → 'dart'
  ✓ Material 'Gazebo/Red' converted from Ogre script to RGBA tags
  ...
```

### Option 3 — Python API

```python
from migrator import GazeboMigrator, migrate_file

# From file
report = migrate_file("my_robot.world", "my_robot_harmonic.sdf")
print(report.summary())

# From string
with open("my_robot.world") as f:
    xml = f.read()

migrator = GazeboMigrator(xml)
output_xml, report = migrator.migrate()
print(f"{len(report.changes)} changes, {len(report.warnings)} warnings")
```

---

## Plugin Mapping Reference

| Classic Plugin | Harmonic System |
|---|---|
| `libgazebo_ros_diff_drive.so` | `gz-sim-diff-drive-system` |
| `libgazebo_ros_imu_sensor.so` | `gz-sim-imu-system` |
| `libgazebo_ros_ray_sensor.so` | `gz-sim-sensors-system` |
| `libgazebo_ros_camera.so` | `gz-sim-sensors-system` |
| `libgazebo_ros_gps_sensor.so` | `gz-sim-navsat-system` |
| `libgazebo_ros_joint_state_publisher.so` | `gz-sim-joint-state-publisher-system` |
| `libgazebo_ros_bumper.so` | `gz-sim-contact-system` |
| `libBuoyancyPlugin.so` | `gz-sim-buoyancy-system` |
| `libWheelSlipPlugin.so` | `gz-sim-wheel-slip-system` |
| `libLinearBatteryPlugin.so` | `gz-sim-linearbatteryplugin-system` |
| ... (40+ total) | |

---

## What Requires Manual Review

The tool generates **warnings** for items that cannot be automatically converted:

1. **ODE physics parameters** (`iters`, `sor`, `cfm`, `erp`) — no direct DART equivalent
2. **Unknown custom plugins** — kept as-is with a warning
3. **Ogre material scripts** that aren't plain Gazebo colors
4. **`model://` URIs** — ensure `GZ_SIM_RESOURCE_PATH` is set
5. **DiffDrive `max_wheel_acceleration`** — renamed to `max_linear_acceleration` (multiply by wheel radius)
6. **ROS topic bridging** — use `ros_gz_bridge` with a YAML config file

---

## After Migration

1. **Set environment variable:**
   ```bash
   export GZ_SIM_RESOURCE_PATH=/path/to/your/models
   ```
   or:
   ```bash
   export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:/home/mohamed_admin/Desktop/Gazebo_worlds
   ```

2. **Set up ROS bridge** (replaces `gazebo_ros_pkgs` plugins):
   ```bash
   ros2 run ros_gz_bridge parameter_bridge /cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist
   ```

3. **Launch with Gazebo Harmonic:**
   ```bash
   gz sim my_robot_harmonic.sdf
   # or with ROS 2 Jazzy:
   ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r my_robot_harmonic.sdf"
   ```

---

## Running Tests

```bash
python3 test_migrator.py
# Expected: 45/45 tests passed — ALL PASSED ✓
```

---

## References

- [Gazebo Classic Migration Guide](https://gazebosim.org/docs/latest/gazebo_classic_migration/)
- [Migration from Gazebo Classic: SDF](https://gazebosim.org/api/sim/8/migrationsdf.html)
- [Migration from Gazebo Classic: Plugins](https://gazebosim.org/api/sim/9/migrationplugins.html)
- [Migrating ROS 2 packages](https://gazebosim.org/docs/latest/migrating_gazebo_classic_ros2_packages/)
- [SDFormat Specification](https://sdformat.org/)
