'''
create .stl file of Ukrainian Tryzub
'''
import trimesh
import numpy as np

from shapely.geometry import Polygon

# Define the polygon
polygon = Polygon([
    (0, 0),
    (0.2, 0),
    (0.4, 1),
    (0.2, 2),
    (-0.2, 2),
    (-0.4, 1),
    (-0.2, 0)
])

# Extrude the polygon to create a prism
prism = trimesh.creation.extrude_polygon(polygon, 3)

# Create three copies of the prism and apply different rotations to each
prisms = [
    prism.copy().apply_transform(trimesh.transformations.rotation_matrix(np.radians(-30), (0, 0, 1))),
    prism.copy().apply_transform(trimesh.transformations.rotation_matrix(np.radians(30), (0, 0, 1))),
    prism.copy()
]

# Combine the prisms into a single mesh
tryzub = trimesh.util.concatenate(prisms)

# Export the Tryzub as an .stl file
tryzub.export('ukrainian_tryzub.stl')