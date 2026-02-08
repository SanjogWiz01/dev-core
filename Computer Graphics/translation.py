def translate_2d(x, y, tx, ty):
    return x + tx, y + ty

# Example
x, y = 2, 3
tx, ty = 5, -1
print(translate_2d(x, y, tx, ty))  # (7, 2)
