''' Steps / Algorithm

Sort all polygon surfaces according to their smallest (farthest) Z-coordinate.

Resolve ambiguities if Z-ranges of polygons overlap (split polygons if necessary).

Scan convert and draw polygons in increasing Z order (i.e., farthest first, nearest last).

Each new surface is painted over the previously drawn surfaces in the refresh buffer.

Key Points (for exam)

Called Painter’s Algorithm because it paints background first, foreground last.

Simple and easy to implement.

Problem: Overlapping or intersecting polygons can cause sorting ambiguities'''


# Each polygon has a depth (z) and a color/intensity
polygons = [
    {"name": "A", "z": 5, "color": "red"},    # nearer
    {"name": "B", "z": 2, "color": "blue"},   # far
    {"name": "C", "z": 3, "color": "green"},  # middle
]

# Painter's Algorithm: sort from farthest to nearest (small z -> big z)
polygons_sorted = sorted(polygons, key=lambda p: p["z"])

framebuffer = []

# Draw (paint) in order: far -> near
for p in polygons_sorted:
    framebuffer.append(p["color"])  # in real case, this would draw on screen
    print(f"Drawing polygon {p['name']} with color {p['color']} at z={p['z']}")

print("Final drawing order (back to front):", [p["name"] for p in polygons_sorted])
