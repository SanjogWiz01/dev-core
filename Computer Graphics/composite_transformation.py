import numpy as np

# Point
P = np.array([1, 1, 1])

# Translation
T = np.array([[1, 0, 2],
              [0, 1, 3],
              [0, 0, 1]])

# Scaling
S = np.array([[2, 0, 0],
              [0, 2, 0],
              [0, 0, 1]])

# Composite: first scale, then translate
M = T @ S

P_new = M @ P
print(P_new)  # Result after composite transform
