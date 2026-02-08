import numpy as np

# 3D point (x, y, z, 1)
P = np.array([2, 2, 5, 1])

# Simple parallel projection matrix (drop z)
P_par = np.array([[1,0,0,0],
                  [0,1,0,0],
                  [0,0,0,0],
                  [0,0,0,1]]) @ P

# Simple perspective projection (divide by z)
P_pers = np.array([P[0]/P[2], P[1]/P[2]])

print("Parallel:", P_par[:2])
print("Perspective:", P_pers)
