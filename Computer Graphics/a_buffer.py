# A-buffer: each pixel stores a list of fragments (z, intensity, coverage)
width, height = 4, 4
abuffer = [[[] for _ in range(width)] for _ in range(height)]

def add_fragment(x, y, z, intensity, coverage=1.0):
    # store a surface fragment at pixel (x, y)
    abuffer[y][x].append((z, intensity, coverage))

def resolve_pixel(x, y):
    # sort fragments by depth (nearest first: larger z = closer, if using that convention)
    frags = sorted(abuffer[y][x], key=lambda f: -f[0])
    if not frags:
        return 0.0  # background intensity

    # simple area-averaged accumulation
    total = 0.0
    weight = 0.0
    for z, I, cov in frags:
        total += I * cov
        weight += cov
    return total / weight if weight > 0 else 0.0

# Example: two overlapping surfaces at pixel (1,1)
add_fragment(1, 1, z=5.0, intensity=0.8, coverage=0.6)  # nearer surface
add_fragment(1, 1, z=3.0, intensity=0.3, coverage=0.4)  # farther surface

final_intensity = resolve_pixel(1, 1)
print("Final pixel intensity:", final_intensity)
