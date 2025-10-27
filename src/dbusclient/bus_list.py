"""
bus_list.py
A tiny learning-first utility to list names on D-Bus (system or session).
We’ll build this file block by block.
"""

# Provides the event loop and 'await' support
import asyncio

# Async D-Bus client (connects to the bus)
from dbus_next.aio import MessageBus

# BusType selects system vs session; Message constructs a D-Bus method call
from dbus_next import BusType, Message

async def list_names(bus_type: BusType) -> list[str]:
    """
    Connect to the specified D-Bus (system or session) and return all registered names.

    Parameters:
        bus_type: A BusType enum value (BusType.SYSTEM or BusType.SESSION).

    Returns:
        A list of bus names (strings). These include both well-known names
        like 'org.freedesktop.Accounts' and unique names that start with ':'.
    """
    # Create an asynchronous connection object for the selected bus type.
    bus = await MessageBus(bus_type=bus_type).connect()

    # Build a D-Bus method call message to org.freedesktop.DBus.ListNames.
    # This call is supported by the bus itself and returns every current name.
    msg = Message(
        destination='org.freedesktop.DBus',
        path='/org/freedesktop/DBus',
        interface='org.freedesktop.DBus',
        member='ListNames'
    )

    # Send the message and await the reply. The reply body is a tuple;
    # element 0 is the list of names (strings).
    reply = await bus.call(msg)

    # Extract the list of names from the reply body and return it.
    names: list[str] = reply.body[0]
    return names

async def main():
    """
    Read --bus option, query that bus, and print names.
    """
    args = parse_arguments()
    print("args:", args)

    # Map CLI choice to BusType
    bus_type = BusType.SYSTEM if args.bus == "system" else BusType.SESSION

    # Fetch names from the chosen bus
    names = await list_names(bus_type)

    # Filter well-known names (skip unique ones that start with ':')
    well_known = [n for n in names if not n.startswith(":")]

    # Display short summary
    print(f"\nBus: {args.bus}")
    print(f"Total names: {len(names)}")
    print("First 15 well-known names:")
    for name in well_known[:15]:
        print(" -", name)


        
def parse_arguments():
    """
    Parse command-line options for this tool.

    Returns:
        An argparse.Namespace object containing the parsed values.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="List D-Bus names on the system or session bus."
    )


    # --bus allows user to choose which bus to query
    parser.add_argument(
        "--bus",
        choices=["system", "session"],
        default="system",
        help="Which D-Bus to query (default: system)."
    )

    return parser.parse_args()


if __name__ == "__main__":
    """
    Standard Python entry point.
    Runs the async main() function when the file is executed directly.
    """
    asyncio.run(main())

