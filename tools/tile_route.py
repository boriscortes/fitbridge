#!/usr/bin/env python3
"""Tile a base GPX loop to an exact target distance using haversine + linear interpolation."""

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.topografix.com/GPX/1/1"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_coords(gpx_path):
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    points = root.findall(f".//{{{NS}}}trkpt") or root.findall(f".//{{{NS}}}rtept")
    if not points:
        sys.exit(f"No track points found in {gpx_path}")
    return [(float(p.attrib["lat"]), float(p.attrib["lon"])) for p in points]


def tile_to_distance(coords, target_m):
    tiled = []
    total = 0.0
    for _ in range(200):  # safety cap
        for lat, lon in coords:
            if tiled:
                prev = tiled[-1]
                seg = haversine(prev[0], prev[1], lat, lon)
                if total + seg >= target_m:
                    frac = (target_m - total) / seg if seg > 0 else 0
                    ilat = prev[0] + frac * (lat - prev[0])
                    ilon = prev[1] + frac * (lon - prev[1])
                    tiled.append((ilat, ilon))
                    return tiled, target_m
                total += seg
            tiled.append((lat, lon))
    return tiled, total


def write_gpx(coords, name, out_path):
    ET.register_namespace("", NS)
    gpx = ET.Element(f"{{{NS}}}gpx", {"version": "1.1", "creator": "fitbridge"})
    ET.SubElement(gpx, f"{{{NS}}}name").text = name
    trk = ET.SubElement(gpx, f"{{{NS}}}trk")
    ET.SubElement(trk, f"{{{NS}}}name").text = name
    seg = ET.SubElement(trk, f"{{{NS}}}trkseg")
    for lat, lon in coords:
        ET.SubElement(seg, f"{{{NS}}}trkpt", {"lat": f"{lat:.8f}", "lon": f"{lon:.8f}"})
    tree = ET.ElementTree(gpx)
    ET.indent(tree, space="  ")
    tree.write(out_path, xml_declaration=True, encoding="utf-8")


def distance_label(km):
    """Convert km float to filename-safe label: 22.5 → 22km5, 10.0 → 10km."""
    whole = int(km)
    frac = round((km - whole) * 10)
    return f"{whole}km{frac}" if frac else f"{whole}km"


def main():
    parser = argparse.ArgumentParser(description='Tile a base GPX loop to an exact target distance')
    parser.add_argument("base_name", help="Base route name (e.g. central_park_loop)")
    parser.add_argument("distance_km", type=float, help="Target distance in km (e.g. 22.5)")
    parser.add_argument("--routes-base", default="routes/base")
    parser.add_argument("--routes-out",  default="routes/out")
    args = parser.parse_args()

    base_dir = Path(args.routes_base)
    out_dir  = Path(args.routes_out)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = list(base_dir.glob(f"{args.base_name}*.gpx"))
    if not candidates:
        candidates = [p for p in base_dir.glob("*.gpx") if args.base_name.lower() in p.stem.lower()]
    if not candidates:
        sys.exit(f"No GPX found matching '{args.base_name}' in {base_dir}/")
    base_path = candidates[0]

    coords = load_coords(base_path)
    target_m = args.distance_km * 1000
    tiled, actual_m = tile_to_distance(coords, target_m)

    label    = distance_label(args.distance_km)
    out_name = f"{base_path.stem}_{label}.gpx"
    out_path = out_dir / out_name

    write_gpx(tiled, f"{base_path.stem} - {args.distance_km} km", out_path)
    print(f"✅ {out_path}")
    print(f"   Points: {len(tiled)} | Distance: {actual_m/1000:.3f} km")


if __name__ == "__main__":
    main()
