import numpy as np

P = np.array([2, 3, 1])      # point (2,3) in homogeneous form
T = np.array([[1, 0, 5],
              [0, 1, -1],
              [0, 0, 1]])

P_new = T @ P
print(P_new)  # [7 2 1]
