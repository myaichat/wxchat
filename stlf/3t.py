import numpy as np
from stl import mesh

# Define the vertices of the Ukrainian Tryzub
vertices = np.array([
    # Main trident body
    [0, 0, 0],    # 0: Bottom center
    [0, 2, 0],    # 1: Top center
    [-1, 1, 0],   # 2: Left middle
    [1, 1, 0],    # 3: Right middle
    [-0.5, 0.5, 0],  # 4: Left inner
    [0.5, 0.5, 0],   # 5: Right inner
    [0, 0, 1],    # 6: Bottom center (depth)
    [0, 2, 1],    # 7: Top center (depth)
    [-1, 1, 1],   # 8: Left middle (depth)
    [1, 1, 1],    # 9: Right middle (depth)
    [-0.5, 0.5, 1],  # 10: Left inner (depth)
    [0.5, 0.5, 1]    # 11: Right inner (depth)
])

# Define the faces of the Tryzub
faces = np.array([
    [0, 2, 1],    # Left face
    [0, 1, 3],    # Right face
    [2, 4, 1],    # Left inner face
    [3, 1, 5],    # Right inner face
    [4, 5, 1],    # Center face
    # Depth faces
    [0, 6, 8],
    [0, 8, 2],
    [1, 7, 8],
    [1, 8, 2],
    [1, 7, 9],
    [1, 9, 3],
    [2, 8, 10],
    [2, 10, 4],
    [3, 9, 11],
    [3, 11, 5],
    [4, 10, 7],
    [4, 7, 1],
    [5, 11, 7],
    [5, 7, 1],
    [6, 0, 3],
    [6, 3, 9],
    [6, 9, 11],
    [6, 11, 10],
    [6, 10, 8]
])

# Create the mesh
trident = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
for i, f in enumerate(faces):
    for j in range(3):
        trident.vectors[i][j] = vertices[f[j], :]

# Save as STL file
trident.save('/mnt/data/ukrainian_tryzub.stl')
print("STL file created successfully.")