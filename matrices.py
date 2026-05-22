import numpy as np

def translationMatrix(coords):
     """Return 3D translation matrix for translating by coords."""
     return np.array([[1, 0, 0],
                    [0, 1, 0],
                    [0, 0, 1]])

def translate_vector(vector, coords):
    """Translate a vector by coords (separate function since we don't use 4D matrices)."""
    return vector + coords

def rotateXYZMatrix(rx, ry, rz):
    """Return matrix for rotating about x, y, then z axes by rx, ry, rz radians respectively."""
    mx = rotateXMatrix(rx)
    my = rotateYMatrix(ry)
    mz = rotateZMatrix(rz)
    # Note: The order of multiplication matters!
    return mz @ my @ mx

def rotateXMatrix(radians):
    """ Return matrix for rotating about the x-axis by 'radians' radians """

    c = np.cos(radians)
    s = np.sin(radians)
    return np.array([[1, 0, 0],
                    [0, c, s],
                    [0, -s, c]])


def rotateYMatrix(radians):
    """ Return matrix for rotating about the y-axis by 'radians' radians """

    c = np.cos(radians)
    s = np.sin(radians)
    return np.array([[c, 0, -s],
                    [0, 1, 0],
                    [s, 0, c]])


def rotateZMatrix(radians):
    """ Return matrix for rotating about the z-axis by 'radians' radians """

    c = np.cos(radians)
    s = np.sin(radians)
    return np.array([[c, s, 0],
                    [-s, c, 0],
                    [0, 0, 1]])


def scaleMatrix(scale):
    """ Return matrix for scaling equally along all axes."""
    return np.array([[scale[0], 0, 0],
                    [0, scale[1], 0],
                    [0, 0, scale[2]]])


def perspectiveMatrix(sx=0.0, sy=0.0, sz=0.0):
    """ Return matrix for perspective scaling """
    return np.array([[sx, 0, 0],
                    [0, sy, 0],
                    [0, 0, sz]])


def camera_rotation_matrix(yaw, pitch, roll):
    """Return combined rotation matrix for camera angles (in radians)."""
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    # Yaw (Y), Pitch (X), Roll (Z)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rz @ Rx @ Ry


def rotateAxisMatrix(axis, angle):
    """Create a rotation matrix for rotating around an arbitrary axis.
    
    Args:
        axis (np.ndarray): 3D vector representing rotation axis
        angle (float): Rotation angle in radians
    """
    # Normalize the axis vector
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    
    # Build rotation matrix using Rodrigues' rotation formula (3x3 version)
    matrix = np.array([
        [t*x*x + c,    t*x*y - z*s,  t*x*z + y*s],
        [t*x*y + z*s,  t*y*y + c,    t*y*z - x*s],
        [t*x*z - y*s,  t*y*z + x*s,  t*z*z + c]
    ])
    
    return matrix