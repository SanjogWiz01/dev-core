def bezier_point(P0, P1, P2, P3, t):
    # Cubic Bezier formula
    x = (1-t)**3 * P0[0] + 3*(1-t)**2*t * P1[0] + 3*(1-t)*t**2 * P2[0] + t**3 * P3[0]
    y = (1-t)**3 * P0[1] + 3*(1-t)**2*t * P1[1] + 3*(1-t)*t**2 * P2[1] + t**3 * P3[1]
    return (x, y)

# Example control points
P0 = (0, 0)
P1 = (1, 2)
P2 = (3, 2)
P3 = (4, 0)

# Compute a point on curve at t = 0.5
print(bezier_point(P0, P1, P2, P3, 0.5))
