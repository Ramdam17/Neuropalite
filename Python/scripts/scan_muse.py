"""Scan for nearby Muse BLE devices and update muse_config.yaml.

Usage::

    uv run python scripts/scan_muse.py
    uv run python scripts/scan_muse.py --timeout 15
    uv run python scripts/scan_muse.py --no-update   # scan only, don't write config

Discovers Muse headbands via Bluetooth Low Energy, displays their
addresses and signal strength, and optionally writes the addresses
into config/muse_config.yaml.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from bleak import BleakScanner

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "muse_config.yaml"


async def scan_muse_devices(timeout: float = 10.0) -> list[dict]:
    """Scan for Muse BLE devices.

    Parameters
    ----------
    timeout : float
        Scan duration in seconds.

    Returns
    -------
    list[dict]
        List of discovered Muse devices with name, address, and RSSI.
    """
    print(f"Scanning for Muse devices ({timeout}s)...")
    print()

    devices = await BleakScanner.discover(timeout=timeout)

    muse_devices = []
    for d in devices:
        name = d.name or ""
        # Muse devices advertise as "Muse-XXXX" or "MuseS-XXXX"
        if "muse" in name.lower():
            muse_devices.append({
                "name": name,
                "address": d.address,
                "rssi": d.rssi if hasattr(d, "rssi") else None,
            })

    # Sort by signal strength (strongest first)
    muse_devices.sort(key=lambda d: d["rssi"] or -999, reverse=True)
    return muse_devices


def display_devices(devices: list[dict]) -> None:
    """Print discovered devices in a formatted table."""
    if not devices:
        print("No Muse devices found.")
        print()
        print("Troubleshooting:")
        print("  - Make sure your Muse is powered on (hold power button 2s)")
        print("  - Bring it closer to your computer")
        print("  - Make sure Bluetooth is enabled")
        print("  - Try increasing --timeout (default: 10s)")
        return

    print(f"Found {len(devices)} Muse device(s):")
    print()
    for i, d in enumerate(devices, 1):
        rssi_str = f"RSSI: {d['rssi']} dBm" if d["rssi"] is not None else ""
        print(f"  [{i}]  {d['name']:<20}  {d['address']}  {rssi_str}")
    print()


def update_config(devices: list[dict]) -> None:
    """Write discovered addresses into muse_config.yaml.

    Assigns devices in order: first device → muse_1, second → muse_2.
    """
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    muse_keys = list(config["muse_devices"].keys())

    print("Assignment:")
    for i, key in enumerate(muse_keys):
        if i < len(devices):
            old_addr = config["muse_devices"][key]["bluetooth_address"]
            new_addr = devices[i]["address"]
            config["muse_devices"][key]["bluetooth_address"] = new_addr
            print(f"  {key} ({config['muse_devices'][key]['name']})  {old_addr} -> {new_addr}")
        else:
            print(f"  {key} ({config['muse_devices'][key]['name']})  — no device available")

    print()
    confirm = input("Write to muse_config.yaml? [Y/n] ").strip().lower()
    if confirm in ("", "y", "yes"):
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"Config saved: {CONFIG_PATH}")
    else:
        print("Cancelled.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan for Muse BLE devices")
    parser.add_argument(
        "--timeout", type=float, default=10.0,
        help="Scan duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--no-update", action="store_true",
        help="Scan only, don't update config",
    )
    args = parser.parse_args()

    devices = asyncio.run(scan_muse_devices(args.timeout))
    display_devices(devices)

    if not devices:
        sys.exit(1)

    if not args.no_update:
        update_config(devices)


if __name__ == "__main__":
    main()
