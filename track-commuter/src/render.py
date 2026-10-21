"""Shaded preview renders of the 3D model (matplotlib, no GPU needed)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEWS = {
    "side_drive": (0, -90),
    "three_quarter": (22, -58),
    "rear": (8, 180),
    "top": (90, -90),
}


def _mesh(shape, tol=0.4):
    verts, tris = shape.tessellate(tol, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in verts])
    return v[np.array(tris)]


def render(bodies, path, view, size=(12, 7.5), zoom=1.3):
    """bodies: list of (shape, rgb)."""
    elev, azim = VIEWS[view]
    fig = plt.figure(figsize=size, dpi=140)
    ax = fig.add_subplot(projection="3d", proj_type="ortho")
    light = np.array([0.3, 0.8, 0.6])
    light /= np.linalg.norm(light)
    allpts = []
    for shape, rgb in bodies:
        tri = _mesh(shape)
        # Model axes: X fwd, Y up, Z right -> plot axes: x=X, y=-Z, z=Y.
        tri = tri[:, :, [0, 2, 1]] * np.array([1, -1, 1])
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.35 + 0.65 * np.abs(n @ light)
        colors = np.clip(np.outer(shade, rgb), 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=colors, linewidths=0))
        allpts.append(tri.reshape(-1, 3))
    pts = np.vstack(allpts)
    lo, hi = pts.min(0), pts.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo, zoom=zoom)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
