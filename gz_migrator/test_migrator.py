"""
test_migrator.py — Automated tests for the GZ Migrator engine
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from migrator import GazeboMigrator, migrate_file
from lxml import etree

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"

results = []

def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append(condition)
    print(f"  {status} {name}" + (f"  [{detail}]" if detail else ""))


def run_migration(xml):
    m = GazeboMigrator(xml)
    return m.migrate()


# ============================================================
# TEST 1: SDF version bump
# ============================================================
print("\n[1] SDF Version Bump")
xml = '<sdf version="1.6"><world name="t"/></sdf>'
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
test("version set to 1.11", tree.get("version") == "1.11")
test("change logged", any("1.6" in c for c in rep.changes))

# ============================================================
# TEST 2: Bare world wrapping
# ============================================================
print("\n[2] Bare World Wrapping")
xml = '<world name="bare"><physics type="ode"/></world>'
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
test("root is <sdf>", tree.tag == "sdf")
test("version 1.11", tree.get("version") == "1.11")
test("world preserved", tree.find("world") is not None)

# ============================================================
# TEST 3: Physics ODE → DART
# ============================================================
print("\n[3] Physics Migration (ODE → DART)")
xml = '''<sdf version="1.6"><world name="t">
  <physics type="ode">
    <max_step_size>0.001</max_step_size>
    <ode><solver><iters>50</iters><sor>1.3</sor></solver>
    <constraints><cfm>0</cfm><erp>0.2</erp></constraints></ode>
  </physics>
</world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
phys = tree.find(".//physics")
test("type changed to dart", phys.get("type") == "dart")
test("<ode> block removed", phys.find("ode") is None or phys.find("ode").text is None)
test("ODE iters warning issued", any("iters" in w for w in rep.warnings))
test("ODE cfm warning issued", any("cfm" in w for w in rep.warnings))

# ============================================================
# TEST 4: Plugin migration
# ============================================================
print("\n[4] Plugin Migration")
xml = '''<sdf version="1.6"><world name="t"><model name="r">
  <plugin filename="libgazebo_ros_diff_drive.so" name="dd">
    <ros><namespace>/robot</namespace></ros>
    <commandTopic>cmd_vel</commandTopic>
    <odometryTopic>odom</odometryTopic>
    <wheelDiameter>0.2</wheelDiameter>
    <wheel_separation>0.4</wheel_separation>
  </plugin>
</model></world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
# Find the model-level plugin (not the injected world plugins)
model_plugins = tree.findall(".//model/plugin")
plugin = model_plugins[0] if model_plugins else None
test("filename migrated", plugin is not None and plugin.get("filename") == "gz-sim-diff-drive-system")
test("name attribute set", plugin is not None and plugin.get("name") == "gz::sim::systems::DiffDrive")
test("<ros> removed", plugin is not None and plugin.find("ros") is None)
test("<commandTopic> → <topic>", plugin is not None and plugin.find("topic") is not None)
test("<odometryTopic> → <odom_topic>", plugin is not None and plugin.find("odom_topic") is not None)
test("<wheelDiameter> → <wheel_radius> halved",
     plugin is not None and plugin.find("wheel_radius") is not None and
     float(plugin.find("wheel_radius").text) == 0.1)

# ============================================================
# TEST 5: Sensor migration — ray → gpu_lidar
# ============================================================
print("\n[5] Sensor Migration (ray → gpu_lidar)")
xml = '''<sdf version="1.6"><world name="t"><model name="r"><link name="l">
  <sensor name="lidar" type="ray">
    <ray><scan><horizontal><samples>360</samples></horizontal></scan></ray>
    <plugin filename="libgazebo_ros_ray_sensor.so" name="lp">
      <ros><namespace>/robot</namespace></ros>
    </plugin>
  </sensor>
</link></model></world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
sensor = tree.find(".//sensor")
test("type changed to gpu_lidar", sensor.get("type") == "gpu_lidar")
test("<ray> renamed to <lidar>", sensor.find("lidar") is not None)
test("sensor plugin removed", sensor.find("plugin") is None)
test("<topic> added", sensor.find("topic") is not None)

# ============================================================
# TEST 6: Camera sensor migration
# ============================================================
print("\n[6] Sensor Migration (camera)")
xml = '''<sdf version="1.6"><world name="t"><model name="r"><link name="l">
  <sensor name="cam" type="camera">
    <camera name="front"><horizontal_fov>1.4</horizontal_fov>
      <image><width>640</width><height>480</height></image>
    </camera>
    <plugin filename="libgazebo_ros_camera.so" name="cp">
      <ros><namespace>/robot</namespace></ros>
    </plugin>
  </sensor>
</link></model></world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
sensor = tree.find(".//sensor")
test("camera type preserved", sensor.get("type") == "camera")
test("camera plugin removed", sensor.find("plugin") is None)
test("<topic> added", sensor.find("topic") is not None)
test("<camera_info_topic> added", sensor.find(".//camera_info_topic") is not None)

# ============================================================
# TEST 7: Material migration
# ============================================================
print("\n[7] Material Migration (Ogre → RGBA)")
xml = '''<sdf version="1.6"><world name="t"><model name="m"><link name="l">
  <visual name="v">
    <material>
      <script>
        <uri>file://media/materials/scripts/gazebo.material</uri>
        <name>Gazebo/Red</name>
      </script>
    </material>
  </visual>
</link></model></world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
mat = tree.find(".//material")
test("script removed", mat.find("script") is None)
test("<ambient> added", mat.find("ambient") is not None)
test("<diffuse> added", mat.find("diffuse") is not None)
test("<specular> added", mat.find("specular") is not None)
test("red color correct", mat.find("ambient").text.strip() == "1.0 0.0 0.0 1.0")

# ============================================================
# TEST 8: World default plugins injected
# ============================================================
print("\n[8] World Default Plugin Injection")
xml = '<sdf version="1.6"><world name="t"><model name="m"/></world></sdf>'
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
plugin_names = {p.get("name") for p in tree.findall(".//world/plugin")}
test("Physics injected",          "gz::sim::systems::Physics"          in plugin_names)
test("UserCommands injected",     "gz::sim::systems::UserCommands"     in plugin_names)
test("SceneBroadcaster injected", "gz::sim::systems::SceneBroadcaster" in plugin_names)
test("Sensors injected",          "gz::sim::systems::Sensors"          in plugin_names)
test("Imu injected",              "gz::sim::systems::Imu"              in plugin_names)

# ============================================================
# TEST 9: Deprecated tag removal
# ============================================================
print("\n[9] Deprecated Tag Removal")
xml = '''<sdf version="1.6"><world name="t">
  <include><uri>model://sun</uri><sdf_version>1.6</sdf_version></include>
  <allow_auto_disable>true</allow_auto_disable>
</world></sdf>'''
out, rep = run_migration(xml)
tree = etree.fromstring(out.encode())
test("<sdf_version> removed from include", tree.find(".//include/sdf_version") is None)
test("<allow_auto_disable> removed", tree.find(".//allow_auto_disable") is None)

# ============================================================
# TEST 10: File-based migration
# ============================================================
print("\n[10] File-based Migration (CLI)")
import tempfile, os
with tempfile.NamedTemporaryFile(mode='w', suffix='.world', delete=False) as f:
    f.write('<sdf version="1.6"><world name="t"><physics type="ode"/></world></sdf>')
    tmp_in = f.name
tmp_out = tmp_in.replace('.world', '_out.sdf')
try:
    rep = migrate_file(tmp_in, tmp_out)
    test("output file created", os.path.exists(tmp_out))
    test("no errors", len(rep.errors) == 0)
    with open(tmp_out) as f:
        content = f.read()
    test("output is valid XML", '<sdf version="1.11">' in content)
finally:
    os.unlink(tmp_in)
    if os.path.exists(tmp_out): os.unlink(tmp_out)

# ============================================================
# TEST 11: Full sample file migration
# ============================================================
print("\n[11] Full Sample File Migration")
rep = migrate_file("samples/classic_robot.world", "samples/migrated_robot.sdf")
test("no errors in sample migration", len(rep.errors) == 0)
test("changes > 20", len(rep.changes) > 20)
with open("samples/migrated_robot.sdf") as f:
    content = f.read()
test("output is valid XML", '<?xml' in content)
tree = etree.fromstring(content.encode())
test("SDF version 1.11", tree.get("version") == "1.11")

# ============================================================
# TEST 12: Bare world file migration
# ============================================================
print("\n[12] Bare World File Migration")
rep = migrate_file("samples/bare_world.world", "samples/migrated_bare.sdf")
test("no errors", len(rep.errors) == 0)
with open("samples/migrated_bare.sdf") as f:
    content = f.read()
tree = etree.fromstring(content.encode())
test("root is sdf", tree.tag == "sdf")
test("version 1.11", tree.get("version") == "1.11")

# ============================================================
# Summary
# ============================================================
total = len(results)
passed = sum(results)
failed = total - passed
print(f"\n{'='*50}")
print(f"Results: {passed}/{total} tests passed", end="")
if failed:
    print(f"  ({failed} FAILED)")
else:
    print("  — ALL PASSED ✓")
print('='*50)
sys.exit(0 if failed == 0 else 1)
