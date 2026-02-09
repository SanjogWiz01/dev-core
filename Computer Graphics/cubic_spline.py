import numpy as np

# Simple cubic interpolation between 4 points (conceptual)
def cubic_spline_point(p0, p1, p2, p3, t):
    # Catmull-Rom style cubic spline (common in graphics)
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2*p1) +
                  (-p0 + p2) * t +
                  (2*p0 - 5*p1 + 4*p2 - p3) * t2 +
                  (-p0 + 3*p1 - 3*p2 + p3) * t3)

# Example 1D points
p0, p1, p2, p3 = 0, 1, 3, 4

for t in [0.0, 0.5, 1.0]:
    print(cubic_spline_point(p0, p1, p2, p3, t))
