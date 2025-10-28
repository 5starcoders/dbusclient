from __future__ import annotations  # Postpone type hints (faster imports, fewer circular refs).

from typing import Optional, Dict, Tuple  # For precise annotations.
from xml.etree import ElementTree as ET   # Standard XML parser; fine for Introspect XML.

from PySide6.QtDBus import (             # Qt’s D-Bus bindings (C++ under the hood).
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
)


class MethodLocator:
    """
    Generic, reusable *introspection + cache* utility.

    Goal:
      - Given (service, object_path, method_name), find the *interface* that declares that method.
      - Cache results so repeated calls are O(1) and we don't re-parse XML.
      - Works for *any* D-Bus service → zero per-service “search classes”.

    Public API:
      - get_interface_for_method(conn, service, path, method) -> str | None
    """

    # In-memory caches:
    _xml_cache: Dict[Tuple[str, str], str] = {}           # Key: (service, path)  -> Introspection XML text
    _method_cache: Dict[Tuple[str, str, str], str] = {}   # Key: (service, path, method) -> interface name

    @classmethod
    def get_interface_for_method(
        cls,
        conn: QDBusConnection,
        service: str,
        object_path: str,
        method_name: str,
    ) -> Optional[str]:
        """
        Return the interface name that declares `method_name` at `object_path` for `service`.
        Uses caches when possible; otherwise calls Introspect once and parses it.
        """
        # First, try the fast method cache (service+path+method).
        mkey = (service, object_path, method_name)
        if mkey in cls._method_cache:
            return cls._method_cache[mkey]

        # If we don't have method-level cache, ensure we have the raw XML cached.
        xkey = (service, object_path)
        if xkey not in cls._xml_cache:
            cls._xml_cache[xkey] = cls._introspect_xml(conn, service, object_path)

        # Parse the XML to find which interface declares the requested method.
        iface = cls._find_interface_with_method(cls._xml_cache[xkey], method_name)
        if iface is not None:
            cls._method_cache[mkey] = iface  # Store for O(1) lookups next time.
        return iface

    # -------------------- internal helpers --------------------

    @staticmethod
    def _introspect_xml(conn: QDBusConnection, service: str, object_path: str) -> str:
        """
        Call org.freedesktop.DBus.Introspectable.Introspect on (service, object_path).
        Returns the XML text or raises RuntimeError on failure.
        """
        iface = QDBusInterface(
            service,
            object_path,
            "org.freedesktop.DBus.Introspectable",  # Standard interface for runtime introspection.
            conn,
        )
        if not iface.isValid():
            raise RuntimeError(
                f"Introspectable not available: service='{service}', path='{object_path}'"
            )

        reply: QDBusMessage = iface.call("Introspect")  # No args; returns XML string on success.
        if reply.type() == QDBusMessage.ErrorMessage:
            raise RuntimeError(f"Introspect failed: {reply.errorName()}: {reply.errorMessage()}")

        xml_text = reply.arguments()[0]  # The first (and only) return value is the XML.
        return xml_text

    @staticmethod
    def _find_interface_with_method(xml_text: str, method_name: str) -> Optional[str]:
        """
        Parse the introspection XML and return the interface that declares `method_name`, or None.
        """
        root = ET.fromstring(xml_text)  # <node>...</node>
        for iface_el in root.findall("interface"):
            iface_name = iface_el.get("name")
            if not iface_name:
                continue
            for method_el in iface_el.findall("method"):
                if method_el.get("name") == method_name:
                    return iface_name
        return None
