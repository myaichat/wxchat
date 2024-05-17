import numpy as np
from stl import mesh

# Create the Trident shape using vertices and faces
vertices = np.array([
    [0, 0, 0],  # 0: Bottom center
    [1, 0, 0],  # 1: Bottom right
    [0.5, 2, 0],  # 2: Middle top
    [0, 1.5, 0],  # 3: Left middle
    [1, 1.5, 0],  # 4: Right middle
    [0, 1.5, 1],  # 5: Left middle (3D depth)
    [1, 1.5, 1],  # 6: Right middle (3D depth)
    [0.5, 2, 1]   # 7: Middle top (3D depth)
])

# Define the 6 faces of the Trident (two triangular sides and the top and bottom rectangular parts)
faces = np.array([
    [0, 1, 2],  # Bottom triangle
    [0, 3, 2],  # Left side triangle
    [1, 4, 2],  # Right side triangle
    [3, 4, 2],  # Top middle triangle
    [3, 4, 5],  # Left 3D face
    [4, 6, 5],  # Right 3D face
    [5, 6, 7]   # Top 3D face
])

# Create the mesh
trident = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
for i, f in enumerate(faces):
    for j in range(3):
        trident.vectors[i][j] = vertices[f[j], :]

# Save as STL file
trident.save('ukrainian_tryzub.stl')

print("STL file created successfully.")
