"""
introspect_service.py
Step-by-step learning utility to call org.freedesktop.DBus.Introspectable.Introspect
on a target object path and parse the returned XML.

Blocks:
1) Docstring + imports (you’re here)
2) Minimal async helper to call Introspect on SYSTEM bus
3) Tiny main() that prints interface + method names
4) __main__ entry point
"""

# Standard library
import asyncio
import sys
from typing import List, Tuple
import xml.etree.ElementTree as ET

# D-Bus (async client)
from dbus_next.aio import MessageBus
from dbus_next import BusType, Message

# --- Block 2: minimal async helper (SYSTEM bus Introspect) ---

async def call_introspect_system(service: str, path: str = "/") -> str:
    """
    Connects to the SYSTEM bus and invokes org.freedesktop.DBus.Introspectable.Introspect
    on the given service + object path, returning the raw XML string.

    Args:
        service: The well-known/bus name to introspect (e.g., "org.freedesktop.login1").
        path:    Object path to introspect on that service (default "/").

    Returns:
        The XML string returned by the Introspect method.

    Why this is minimal:
        - Only uses the SYSTEM bus (as per our current scope).
        - No retries/backoff; any error is raised to the caller (Block 3 will handle UX).
        - Leaves XML parsing for the next block.
    """
    # Create an async connection to the SYSTEM bus. This is the global bus for OS services.
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    try:
        # Build a method-call message for org.freedesktop.DBus.Introspectable.Introspect.
        # Destination: target service. Path: target object path.
        # Interface: Introspectable. Member: "Introspect". No arguments/signature.
        msg = Message(
            destination=service,
            path=path,
            interface="org.freedesktop.DBus.Introspectable",
            member="Introspect",
            signature="",
            body=[],
        )

        # Perform the call and await the reply. If the service/path exist and support
        # Introspectable, the reply body[0] will be an XML string.
        reply = await bus.call(msg)

    
        if not reply.body or not isinstance(reply.body[0], str):
            raise RuntimeError("Introspect call returned no XML string in body[0]")

        return reply.body[0]

    finally:
        # Always close the D-Bus connection to avoid leaking sockets/file descriptors.
        bus.disconnect()


# --- Block 3: tiny main() that prints interface + method names ---

def parse_interfaces_and_methods(xml_text: str) -> List[Tuple[str, List[str]]]:
    root = ET.fromstring(xml_text)
    results: List[Tuple[str, List[str]]] = []
    for iface in root.findall("interface"):
        name = iface.get("name") or ""
        methods = [m.get("name") or "" for m in iface.findall("method")]
        results.append((name, methods))
    return results

def parse_interface_details(xml_text: str) -> List[Tuple[str, List[str], List[str], List[str]]]:
    print("XML Text:\n", xml_text)
    root = ET.fromstring(xml_text)
    out: List[Tuple[str, List[str], List[str], List[str]]] = []
    for iface in root.findall("interface"):
        name = iface.get("name") or ""
        methods = [e.get("name") or "" for e in iface.findall("method")]
        signals = [e.get("name") or "" for e in iface.findall("signal")]
        properties = [e.get("name") or "" for e in iface.findall("property")]
        out.append((name, methods, signals, properties))
    return out


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage: introspect_service.py <service> [path='/']")
        return 2

    service = argv[1]
    path = argv[2] if len(argv) >= 3 else "/"

    async def run() -> int:
        try:
            xml_text = await call_introspect_system(service, path)
            items = parse_interface_details(xml_text)
            if not items:
                print("(no interfaces found)")
                return 0
            for iface_name, methods, signals, props in items:
                print(f"[Interface] {iface_name}")
                for m in methods:
                    print(f"  - {m}")
                if signals:
                    print("  [Signals]")
                    for s in signals:
                        print(f"    * {s}")
                if props:
                    print("  [Properties]")
                    for p in props:
                        print(f"    · {p}")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    return asyncio.run(run())

# --- Block 4: __main__ entry point ---

if __name__ == "__main__":
    sys.exit(main(sys.argv))
