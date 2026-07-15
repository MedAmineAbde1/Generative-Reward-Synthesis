#!/usr/bin/env python3
"""
migrate_to_harmonic.py

Convert old Gazebo/IGN world/model SDF files into a format closer to Gazebo Harmonic.
- Updates SDF version
- Renames common plugin shared libraries
- Normalizes resource URIs (model:// remains, classic fuel URLs mapped to gz fuel)
- Writes migrated file

Usage:
    python migrate_to_harmonic.py input.world -o output.world
    python migrate_to_harmonic.py input.sdf --in-place
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TARGET_SDF_VERSION = "1.10"

# Common classic/ign plugin filename migrations to newer gz sim system plugin libs.
# You may need to adjust depending on your installed Gazebo Harmonic packages.
PLUGIN_FILENAME_MAP = {
    # Physics / scene / user cmds
    "libignition-gazebo-physics-system.so": "gz-sim-physics-system",
    "libignition-gazebo-scene-broadcaster-system.so": "gz-sim-scene-broadcaster-system",
    "libignition-gazebo-user-commands-system.so": "gz-sim-user-commands-system",
    "libignition-gazebo-sensors-system.so": "gz-sim-sensors-system",
    "libignition-gazebo-imu-system.so": "gz-sim-imu-system",
    "libignition-gazebo-contact-system.so": "gz-sim-contact-system",

    # Newer ign->gz naming variants
    "libgz-sim-physics-system.so": "gz-sim-physics-system",
    "libgz-sim-scene-broadcaster-system.so": "gz-sim-scene-broadcaster-system",
    "libgz-sim-user-commands-system.so": "gz-sim-user-commands-system",
    "libgz-sim-sensors-system.so": "gz-sim-sensors-system",
    "libgz-sim-imu-system.so": "gz-sim-imu-system",
    "libgz-sim-contact-system.so": "gz-sim-contact-system",

    # Classic gazebo plugins often stay as-is in classic; map only if known harmonic system equivalent exists.
    # Add your own here.
}

FUEL_OLD_PREFIXES = [
    "https://fuel.ignitionrobotics.org/",
    "http://fuel.ignitionrobotics.org/",
]

FUEL_NEW_PREFIX = "https://fuel.gazebosim.org/"


def indent_xml(elem, level=0):
    """Pretty print XML in-place for ElementTree."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent_xml(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def migrate_plugin_filename(filename: str) -> str:
    if not filename:
        return filename

    stripped = filename.strip()

    # Direct map first
    if stripped in PLUGIN_FILENAME_MAP:
        return PLUGIN_FILENAME_MAP[stripped]

    # Heuristic: ignition->gz rename for lib names
    # libignition-gazebo-XYZ-system.so -> gz-sim-XYZ-system
    m = re.match(r"libignition-gazebo-(.*)\.so$", stripped)
    if m:
        return f"gz-sim-{m.group(1)}"

    # libgz-sim-XYZ-system.so -> gz-sim-XYZ-system
    m = re.match(r"libgz-sim-(.*)\.so$", stripped)
    if m:
        return f"gz-sim-{m.group(1)}"

    # Otherwise leave unchanged
    return stripped


def migrate_uri_text(text: str) -> str:
    if not text:
        return text
    t = text.strip()
    for p in FUEL_OLD_PREFIXES:
        if t.startswith(p):
            return FUEL_NEW_PREFIX + t[len(p):]
    return text


def migrate_tree(tree: ET.ElementTree):
    root = tree.getroot()

    # Ensure root is <sdf>
    if root.tag != "sdf":
        raise ValueError(f"Root tag is <{root.tag}>, expected <sdf>")

    # Update sdf version
    old_version = root.attrib.get("version")
    root.set("version", TARGET_SDF_VERSION)

    # Migrate all plugin filename attributes
    plugin_count = 0
    changed_plugins = 0
    for plugin in root.findall(".//plugin"):
        plugin_count += 1
        filename = plugin.attrib.get("filename")
        if filename:
            new_filename = migrate_plugin_filename(filename)
            if new_filename != filename:
                plugin.attrib["filename"] = new_filename
                changed_plugins += 1

    # Normalize uri tags
    uri_count = 0
    changed_uri = 0
    for uri in root.findall(".//uri"):
        uri_count += 1
        if uri.text:
            new_text = migrate_uri_text(uri.text)
            if new_text != uri.text:
                uri.text = new_text
                changed_uri += 1

    # Optional cleanup: convert deprecated <pose frame=''> usage? (left untouched safely)
    # Optional cleanup: world physics defaults? (left untouched)

    return {
        "old_sdf_version": old_version,
        "new_sdf_version": TARGET_SDF_VERSION,
        "plugin_count": plugin_count,
        "changed_plugins": changed_plugins,
        "uri_count": uri_count,
        "changed_uri": changed_uri,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Migrate SDF/world file to Gazebo Harmonic-friendly format")
    p.add_argument("input", type=Path, help="Input .world or .sdf file")
    p.add_argument("-o", "--output", type=Path, help="Output file path")
    p.add_argument("--in-place", action="store_true", help="Overwrite input file")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.input.exists():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.in_place and args.output:
        print("ERROR: use either --in-place or --output, not both", file=sys.stderr)
        sys.exit(1)

    if not args.in_place and not args.output:
        # default output next to input
        args.output = args.input.with_name(args.input.stem + "_harmonic" + args.input.suffix)

    out_path = args.input if args.in_place else args.output

    try:
        tree = ET.parse(args.input)
    except ET.ParseError as e:
        print(f"ERROR: XML parse failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        report = migrate_tree(tree)
    except Exception as e:
        print(f"ERROR: migration failed: {e}", file=sys.stderr)
        sys.exit(1)

    indent_xml(tree.getroot())
    tree.write(out_path, encoding="utf-8", xml_declaration=True)

    print("Migration complete.")
    print(f"Input:  {args.input}")
    print(f"Output: {out_path}")
    print(f"SDF version: {report['old_sdf_version']} -> {report['new_sdf_version']}")
    print(f"Plugins changed: {report['changed_plugins']} / {report['plugin_count']}")
    print(f"URIs changed:    {report['changed_uri']} / {report['uri_count']}")


if __name__ == "__main__":
    main()