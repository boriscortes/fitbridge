---
name: route
description: Generate a GPS route GPX file at a specific distance by tiling a base loop. Use when the user wants to create, generate, or build a route — e.g. "generate a 26km route from central park", "make a 16km loop", "create a 30km route".
---

# route

Generate a target-distance GPX by tiling a base loop from `routes/base/`.

## How to run

```bash
python3 tools/tile_route.py <base_name> <distance_km>
```

The script fuzzy-matches `base_name` against GPX files in `routes/base/`, tiles the loop to the exact target distance using haversine math + linear interpolation, and saves to `routes/out/`.

## Examples

```bash
python3 tools/tile_route.py central_park_loop 26
python3 tools/tile_route.py central_park_loop 16.5
```

## If base name is ambiguous

List available loops first:
```bash
ls routes/base/
```
Then ask the user which one they want.

## After running

Report the output path and exact distance achieved. The GPX can be loaded directly into COROS or Garmin as a course.
