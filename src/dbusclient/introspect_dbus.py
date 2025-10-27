#!/usr/bin/env python3
import argparse
import ast
import datetime
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple

# =========================
# Helpers / Utilities
# =========================

def run_cmd(cmd: List[str], timeout: int) -> Tuple[int, str, str]:
    # Execute command and capture output; return code, stdout, stderr
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, text=True, check=False)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"

def bus_flag(bus: str) -> str:
    # Convert bus name to gdbus flag
    return "--system" if bus == "system" else "--session"

def decode_gdbus_tuple(stdout: str):
    # Parse gdbus tuple output into Python object
    try:
        tup = ast.literal_eval(stdout.strip())
        if isinstance(tup, tuple) and tup:
            return tup[0]
    except Exception:
        pass
    return None

def dotted_to_path(dotted: str) -> str:
    # Convert dotted service name to filesystem path
    return dotted.replace(".", "/")

def ensure_dir(path: str) -> None:
    # Create directory if it doesn't exist
    os.makedirs(path, exist_ok=True)

def now_iso() -> str:
    from datetime import datetime, UTC
    # Return current UTC time in ISO 8601 format without using deprecated utcnow()
    return datetime.now(UTC).isoformat()

def last_segment_of_service(service: str) -> str:
    # Extract last segment from dotted service name
    parts = [p for p in service.split('.') if p]
    return parts[-1] if parts else "Service"

def last_segment_of_path(obj_path: str) -> str:
    # Extract last segment from slash-separated path
    parts = [p for p in obj_path.split('/') if p]
    return parts[-1] if parts else "Root"

def extract_submodule_name(service: str, interface_name: str) -> Optional[str]:
    # Extract submodule name from interface; e.g., org.freedesktop.Accounts.User -> User
    service_prefix = service + "."
    if interface_name.startswith(service_prefix):
        return interface_name[len(service_prefix):]
    return None

def get_submodule_from_interfaces(service: str, interfaces: List[Dict]) -> Optional[str]:
    # Find first interface matching service.submodule pattern; return submodule name
    for iface in interfaces:
        submodule = extract_submodule_name(service, iface.get("name", ""))
        if submodule:
            return submodule
    return None

def normalize_object_path(obj_path: str, submodule: str) -> str:
    # Replace instance identifier in path with submodule name
    # e.g., /org/freedesktop/Accounts/User1000 -> /org/freedesktop/Accounts/User
    parts = obj_path.rstrip('/').split('/')
    if parts:
        parts[-1] = submodule
    return '/'.join(parts)

# =========================
# Discovery
# =========================

def list_services(bus: str, include_activatable: bool, timeout: int) -> List[str]:
    # Discover all service names on given bus
    names: Set[str] = set()

    # Query ListNames method
    rc, out, err = run_cmd(
        ["gdbus", "call", bus_flag(bus),
         "--dest", "org.freedesktop.DBus",
         "--object-path", "/org/freedesktop/DBus",
         "--method", "org.freedesktop.DBus.ListNames"],
        timeout
    )
    if rc == 0:
        arr = decode_gdbus_tuple(out)
        if isinstance(arr, list):
            names.update(arr)

    # Query ListActivatableNames if requested
    if include_activatable:
        rc, out, err = run_cmd(
            ["gdbus", "call", bus_flag(bus),
             "--dest", "org.freedesktop.DBus",
             "--object-path", "/org/freedesktop/DBus",
             "--method", "org.freedesktop.DBus.ListActivatableNames"],
            timeout
        )
        if rc == 0:
            arr = decode_gdbus_tuple(out)
            if isinstance(arr, list):
                names.update(arr)

    # Fallback to busctl if gdbus fails
    if not names and shutil.which("busctl"):
        rc, out, err = run_cmd(
            ["busctl", "--no-pager", "--no-legend",
             ("--system" if bus == "system" else "--user"), "list"],
            timeout
        )
        if rc == 0:
            for line in out.splitlines():
                cols = line.split()
                if cols:
                    names.add(cols[0])

    # Filter out unique names (starting with :)
    return sorted(n for n in names if not n.startswith(":"))

# =========================
# Introspection & Parsing
# =========================

def introspect(bus: str, service: str, obj_path: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    # Call Introspect method on object; return XML and optional error
    rc, out, err = run_cmd(
        ["gdbus", "call", bus_flag(bus),
         "--dest", service,
         "--object-path", obj_path,
         "--method", "org.freedesktop.DBus.Introspectable.Introspect"],
        timeout
    )
    if rc != 0:
        return None, f"gdbus rc={rc} err={err.strip()}"
    xml = decode_gdbus_tuple(out)
    if not isinstance(xml, str) or not xml.strip():
        return None, "empty introspection"
    return xml, None

def parse_xml(xml: str) -> Tuple[List[str], List[Dict]]:
    # Parse introspection XML; return child names and interface definitions
    children: List[str] = []
    interfaces: List[Dict] = []
    try:
        root = ET.fromstring(xml)
    except Exception:
        return children, interfaces

    # Extract child node names
    for node in root.findall("node"):
        n = node.get("name")
        if n:
            children.append(n)

    # Extract interface definitions
    for iface in root.findall("interface"):
        name = iface.get("name", "")
        methods, signals, properties = [], [], []

        # Parse methods
        for m in iface.findall("method"):
            in_args, out_args = [], []
            for a in m.findall("arg"):
                d = a.get("direction", "in")
                entry = {"name": a.get("name", ""), "type": a.get("type", "")}
                (out_args if d == "out" else in_args).append(entry)
            methods.append({"name": m.get("name", ""), "in_args": in_args, "out_args": out_args})

        # Parse signals
        for s in iface.findall("signal"):
            s_args = [{"name": a.get("name", ""), "type": a.get("type", "")} for a in s.findall("arg")]
            signals.append({"name": s.get("name", ""), "args": s_args})

        # Parse properties
        for p in iface.findall("property"):
            properties.append({
                "name": p.get("name", ""),
                "type": p.get("type", ""),
                "access": p.get("access", "")
            })

        interfaces.append({
            "name": name,
            "methods": methods,
            "signals": signals,
            "properties": properties
        })

    return children, interfaces

# =========================
# README Generation
# =========================

def gen_readme(bus: str, service: str, obj_path: str, interfaces: List[Dict]) -> str:
    # Generate human-readable README for this object
    lines = []
    
    # Title: service root uses service name, submodules use submodule name
    svc_ns = "/" + dotted_to_path(service)
    if obj_path == svc_ns:
        title = last_segment_of_service(service)
    else:
        title = last_segment_of_path(obj_path)
    
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Bus:** {bus}")
    lines.append(f"**Object Path:** `{obj_path}`")
    lines.append(f"**Service:** `{service}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## What is this?")
    lines.append("TODO: Add description")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Collect all methods from all interfaces
    all_methods = []
    for iface in interfaces:
        all_methods.extend(iface.get("methods", []))

    if all_methods:
        lines.append("## Methods")
        lines.append("")
        lines.append("| Method | Input | Output | Purpose |")
        lines.append("|--------|-------|--------|---------|")
        for m in all_methods:
            in_sig = ", ".join([f"{a['name']}: {a['type']}" for a in m.get("in_args", [])]) or "—"
            out_sig = ", ".join([a['type'] for a in m.get("out_args", [])]) or "—"
            lines.append(f"| {m['name']} | {in_sig} | {out_sig} | TODO |")
        lines.append("")

    # Collect all signals from all interfaces
    all_signals = []
    for iface in interfaces:
        all_signals.extend(iface.get("signals", []))

    if all_signals:
        lines.append("## Signals")
        lines.append("")
        lines.append("| Signal | When Emitted |")
        lines.append("|--------|--------------|")
        for s in all_signals:
            lines.append(f"| {s['name']} | TODO |")
        lines.append("")

    # Collect all properties from all interfaces
    all_properties = []
    for iface in interfaces:
        all_properties.extend(iface.get("properties", []))

    if all_properties:
        lines.append("## Properties")
        lines.append("")
        lines.append("| Property | Type | Access | Description |")
        lines.append("|----------|------|--------|-------------|")
        for p in all_properties:
            lines.append(f"| {p['name']} | `{p['type']}` | {p['access']} | TODO |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"**Last Updated:** {now_iso()}")
    lines.append("")

    return "\n".join(lines)

# =========================
# Writers & Layout
# =========================

def bus_root(project_dir: str, bus: str) -> str:
    # Root directory for a bus
    return os.path.join(project_dir, "org", bus)

def service_root_dir(project_dir: str, bus: str, service: str) -> str:
    # Root directory for a service
    return os.path.join(bus_root(project_dir, bus), dotted_to_path(service))

def write_introspection_set(base_dir: str, file_stem: str, xml: str, jdoc: Dict, readme: str) -> None:
    # Write XML, JSON, and README into __introspection/ folder
    intros_dir = os.path.join(base_dir, "__introspection")
    ensure_dir(intros_dir)
    with open(os.path.join(intros_dir, f"{file_stem}.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    with open(os.path.join(intros_dir, f"{file_stem}.json"), "w", encoding="utf-8") as f:
        json.dump(jdoc, f, indent=2, ensure_ascii=False)
    with open(os.path.join(intros_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

# =========================
# Crawl
# =========================
def crawl_service(bus: str, service: str, args, logf) -> Dict[str, int]:
    # Crawl service root and direct children; extract submodule names from interfaces
    stats = {"nodes_written": 0, "errors": 0}
    svc_ns = "/" + dotted_to_path(service)

    # 1) Introspect service root
    xml, err = introspect(bus, service, svc_ns, args.timeout)
    if err:
        stats["errors"] += 1
        logf.write(f"[{bus}] {service} {svc_ns} : ERROR {err}\n")
        return stats

    children_rel, interfaces = parse_xml(xml)

    # 2) Write service root triplet
    node_dir = service_root_dir(args.project, bus, service)
    ensure_dir(node_dir)
    stem = last_segment_of_service(service)
    readme = gen_readme(bus, service, svc_ns, interfaces)
    jdoc = {
        "meta": {"bus": bus, "service": service, "object_path": svc_ns, "timestamp": now_iso()},
        "interfaces": interfaces
    }
    write_introspection_set(node_dir, stem, xml, jdoc, readme)
    stats["nodes_written"] += 1
    logf.write(f"[{bus}] {service} {svc_ns} : WROTE {stem}.xml/json\n")

    # Track written submodules to avoid duplicates (e.g., User1000 & User1001 → User)
    written_submodules: Set[str] = set()

    # 3) Handle direct children as submodules
    for rel in children_rel:
        child_path = f"{svc_ns}/{rel}"
        xml, err = introspect(bus, service, child_path, args.timeout)
        if err:
            low = (err or "").lower()
            # Down-level dynamic/optional objects to SKIPPED (do not count as error)
            if (
                "unknownobject" in low
                or "org.freedesktop.dbus.error.unknownobject" in low
                or "no such object" in low
                or "not a valid object path" in low
            ):
                logf.write(f"[{bus}] {service} {child_path} : SKIPPED UnknownObject\n")
                continue
            # Any other failure is a real error
            stats["errors"] += 1
            logf.write(f"[{bus}] {service} {child_path} : ERROR {err}\n")
            continue

        _, interfaces = parse_xml(xml)

        # Pick submodule from interface; fallback to child name (note: informational warning)
        submodule = get_submodule_from_interfaces(service, interfaces)
        if not submodule:
            submodule = rel
            logf.write(f"[{bus}] {service} {child_path} : WARNING no matching interface, using child name\n")

        # Dedupe: write each submodule only once
        if submodule in written_submodules:
            logf.write(f"[{bus}] {service} {child_path} : SKIPPED (submodule '{submodule}' already written)\n")
            continue

        submodule_dir = os.path.join(node_dir, submodule)
        ensure_dir(submodule_dir)
        normalized_path = normalize_object_path(child_path, submodule)
        readme = gen_readme(bus, service, normalized_path, interfaces)
        jdoc = {
            "meta": {"bus": bus, "service": service, "object_path": normalized_path, "timestamp": now_iso()},
            "interfaces": interfaces
        }
        write_introspection_set(submodule_dir, submodule, xml, jdoc, readme)
        written_submodules.add(submodule)
        stats["nodes_written"] += 1
        logf.write(f"[{bus}] {service} {child_path} : WROTE submodule '{submodule}'\n")

    logf.write(f"[{bus}] {service} : SUMMARY nodes_written={stats['nodes_written']} errors={stats['errors']}\n")
    return stats


def crawl_bus(bus: str, args, logf) -> Dict[str, Dict[str, int]]:
    # Crawl all services on a bus
    results: Dict[str, Dict[str, int]] = {}
    services = list_services(bus, args.include_activatable, args.timeout)
    if args.service:
        services = [s for s in services if fnmatch.fnmatch(s, args.service)]
    if not services:
        logf.write(f"[{bus}] No services discovered.\n")
        return results

    for svc in services:
        res = crawl_service(bus, svc, args, logf)
        results[svc] = res
    return results

# =========================
# CLI / Main
# =========================

def parse_args():
    p = argparse.ArgumentParser(
        description="Snapshot D-Bus services; write service root + submodules from interface names."
    )
    p.add_argument("project", help="Project folder path where 'org/' will be created.")
    p.add_argument("--bus", choices=["system", "session", "all"], default="all",
                   help="Which bus(es) to crawl (default: all).")
    p.add_argument("--include-activatable", action="store_true",
                   help="Include activatable (not yet owned) service names.")
    p.add_argument("--service", default=None,
                   help="Glob filter for service name(s), e.g., 'org.freedesktop.*'.")
    p.add_argument("--timeout", type=int, default=8,
                   help="Per-Introspect call timeout seconds.")
    p.add_argument("--overwrite", action="store_true",
                   help="Remove existing 'org/' before writing.")
    return p.parse_args()

def main():
    args = parse_args()

    if shutil.which("gdbus") is None:
        print("ERROR: 'gdbus' not found in PATH. Please install GLib utilities.", file=sys.stderr)
        sys.exit(2)

    args.project = os.path.abspath(args.project)
    org_root = os.path.join(args.project, "org")

    if args.overwrite and os.path.isdir(org_root):
        shutil.rmtree(org_root)

    ensure_dir(org_root)
    ensure_dir(os.path.join(org_root, "system"))
    ensure_dir(os.path.join(org_root, "session"))

    log_path = os.path.join(org_root, "crawl.log")
    start = time.time()
    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write(f"DBus Crawl started at {now_iso()}\n")
        buses = ["system", "session"] if args.bus == "all" else [args.bus]
        for b in buses:
            logf.write(f"=== BUS: {b} ===\n")
            crawl_bus(b, args, logf)
        elapsed = time.time() - start
        logf.write(f"Completed at {now_iso()} (duration: {elapsed:.1f}s)\n")

    print(f"✅ D-Bus introspection completed successfully.\nOutput saved to: {org_root}")

if __name__ == "__main__":
    main()