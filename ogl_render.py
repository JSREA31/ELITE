
import numpy as np
import pygame
import time
from status import global_flags, FONTS,ship_data, game_constants
from system_data import ObjectType
from OpenGL.GL import (glColor3f, glBegin, glEnd, glVertex2f, glPointSize, GL_POLYGON, GL_LINE_LOOP, GL_COLOR_BUFFER_BIT, 
                      glDrawPixels, glPushAttrib, glDisable, GL_DEPTH_TEST, GL_LIGHTING, GL_TEXTURE_2D, 
                      glWindowPos2d, GL_RGBA, GL_UNSIGNED_BYTE, glPopAttrib, GL_ALL_ATTRIB_BITS,
                      glGenTextures, glBindTexture, glTexImage2D, glTexParameteri, GL_TEXTURE_MIN_FILTER,
                      GL_TEXTURE_MAG_FILTER, GL_LINEAR, glEnable, glTexCoord2f, GL_QUADS,
                      GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE, GL_POINTS, GL_LINES, GL_TRIANGLE_FAN, glColor4f, glClear,
                      glDeleteTextures, GL_POINT_SMOOTH, glLineWidth)
import status
from collections import OrderedDict
from sounds import sound_manager, SoundType
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from object import Object

import wireframes
from text_strings import get_text
from status import game_constants



# Simple LRU cache for rendered text -> (texture_id, width, height)
_TEXT_CACHE = OrderedDict()
_TEXT_CACHE_MAX = 256  # max cached entries

class TitleScreenState:
    ship: Optional["Object"] = None
    ship_index=6
    last_rendered_ship_index=-1
    frame_counter=0
    first_time=True
    
class MissionState:
    ship: Optional["Object"] = None
    frame_counter=0

class GameOverScreenState:
    cobra: Optional["Object"] = None    
class EscapePodLaunchState:
    cobra: Optional["Object"] = None    

class jump_warp_state:
    initial_xy = []    

def _make_cache_key(text, font, text_color, bg_color):
    # font object is not hashable reliably, use its name+size attributes where possible
    try:
        font_key = (font.get_name(), font.get_linesize())
    except Exception:
        font_key = id(font)
    return (text, font_key, tuple(text_color), tuple(bg_color))

def _get_cached_text(text, font, text_color, bg_color):
    key = _make_cache_key(text, font, text_color, bg_color)
    if key in _TEXT_CACHE:
        # move to end (most recently used)
        _TEXT_CACHE.move_to_end(key)
        return _TEXT_CACHE[key]

    # render the surface
    textSurface = font.render(text, True, text_color)
    text_w = textSurface.get_width()
    text_h = textSurface.get_height()

    # Flip vertically for OpenGL texture coordinates
    flipped = pygame.transform.flip(textSurface, False, True)
    tex_data = pygame.image.tostring(flipped, "RGBA", True)

    # create GL texture
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_w, text_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
    glBindTexture(GL_TEXTURE_2D, 0)

    entry = (tex_id, text_w, text_h)
    _TEXT_CACHE[key] = entry
    # evict oldest if over limit (delete GL texture)
    if len(_TEXT_CACHE) > _TEXT_CACHE_MAX:
        old_key, old_entry = _TEXT_CACHE.popitem(last=False)
        try:
            glDeleteTextures([old_entry[0]])
        except Exception:
            pass
    return entry

def clear_text_cache():
    # delete GL textures
    for _, entry in _TEXT_CACHE.items():
        try:
            glDeleteTextures([entry[0]])
        except Exception:
            pass
    _TEXT_CACHE.clear()

# Constants for sun rendering
_SUN_NUM_SEGMENTS = 75
_SUN_PHASE_OFFSETS = np.random.uniform(0, 2*np.pi, _SUN_NUM_SEGMENTS)
_SUN_FROZEN_TIME_MS = 0  # Stores time_ms when paused, to freeze animation
# Global light direction constant
angle = np.radians(5)  # Convert degrees to radians
LIGHT_DIR = np.array([0, -np.sin(angle), np.cos(angle)])  # Normalized vector

def drawText(x, y, WIDTH, HEIGHT, text, font, text_color=(255, 255, 255), bg_color=(0, 0, 0, 0), centered=False):
    """Draw text in OpenGL using glDrawPixels with optional horizontal centering"""
    # Use cached GL texture if available (texture_id, width, height)
    tex_id, text_w, text_h = _get_cached_text(text, font, text_color, bg_color)

    # Center horizontally if requested
    if centered:
        x = WIDTH//2 - text_w // 2

    # Save attributes and prepare for textured quad rendering
    glPushAttrib(GL_ALL_ATTRIB_BITS)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)

    # Draw textured quad at (x, y). Note: textures were created with flipped vertical
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1.0, 1.0, 1.0, 1.0)

    glBegin(GL_QUADS)
    # bottom-left
    glTexCoord2f(0.0, 0.0); glVertex2f(x, y - text_h)
    # bottom-right
    glTexCoord2f(1.0, 0.0); glVertex2f(x + text_w, y - text_h)
    # top-right
    glTexCoord2f(1.0, 1.0); glVertex2f(x + text_w, y)
    # top-left
    glTexCoord2f(0.0, 1.0); glVertex2f(x, y)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glPopAttrib()

def get_countdown(msg):
    # msg = (text, duration, timestamp, type)
    if len(msg) > 3 and msg[3] == 1:
        return  max(0, int(msg[1] - (time.time() - msg[2])))
    return None

def render_messages(x, y, WIDTH, HEIGHT, font, text_color=(255,255,255,255), bg_color=(0,0,0,0)):
    """
    Render messages from status.message_list, cycling through each for 2 seconds.
    If only one message, display it continuously.
    """
    status.clean_old_messages()
    messages = status.message_list
    if not messages:
        return
    if len(messages) == 1:
        msg = messages[0]
        text = msg[0]
        countdown = get_countdown(msg)
        if countdown is not None:
            text += f" {countdown}"
        drawText(x, y, WIDTH, HEIGHT, text, font, text_color, bg_color,centered=True)
       
    else:
        interval=2
        status.current_message_index %= len(messages)
        if status.current_message_start_time !=0.0:
            elapsed = time.time() - status.current_message_start_time
            if elapsed > interval:
                status.current_message_start_time = time.time()
                status.current_message_index = (status.current_message_index + 1) % len(messages)     
        else:
            status.current_message_start_time = time.time()

        idx = status.current_message_index
        msg = messages[idx]
        text = msg[0]
        countdown = get_countdown(msg)
        if countdown is not None:
            text += f" {countdown}"
        drawText(x, y, WIDTH, HEIGHT, text, font, text_color, bg_color,centered=True)

def project_point_to_screen(point, view_matrix, focal_length, screen_center):
    # point: np.array([x, y, z])
    point_hom = np.array([point[0], point[1], point[2], 1.0])
    point_cam = point_hom @ view_matrix.T
    if point_cam[2] > 0:  # In front of camera
        x_proj = (focal_length * point_cam[0]) / point_cam[2] + screen_center[0]
        y_proj = (focal_length * point_cam[1]) / point_cam[2] + screen_center[1]
        return np.array([x_proj, y_proj]), point_cam[2]  # screen coords, depth
    else:
        return None, None  # Behind camera

class StarField:
    def __init__(self, num_stars=200, max_depth=1500, player_position=None):
        self.num_stars = num_stars
        self.max_depth = max_depth       
        self.create_starfieldsphere(player_position)
        
    def create_starfieldsphere(self,player_position=None):
        center_pos = player_position if player_position is not None else np.array([0, 0, 0])
        
        # Distribute stars in sphere around player
        phi = np.random.uniform(0, 2*np.pi, self.num_stars)      # Azimuthal angle
        theta = np.arccos(np.random.uniform(-1, 1, self.num_stars))  # Polar angle
        radii = self.max_depth * np.cbrt(np.random.uniform(0, 1, self.num_stars))

        self.twinkle_phase = np.random.uniform(0, 2*np.pi, self.num_stars)
        self.twinkle_speed = np.random.uniform(0.01, 0.1, self.num_stars)


        # Convert spherical to Cartesian coordinates around player position
        self.stars = center_pos + np.column_stack([
            radii * np.sin(theta) * np.cos(phi),  # X
            radii * np.sin(theta) * np.sin(phi),  # Y
            radii * np.cos(theta)                 # Z
        ])

        self.prev_stars = np.empty_like(self.stars)
       


    def update(self, movement_orientation, player_position,allow_reset=True):  # Add player_position parameter
        # Move stars based on player movement
        if global_flags.is_paused:
            return

        self.twinkle_phase += self.twinkle_speed
        self.twinkle_phase %= 2 * np.pi

        # Check distances from player's world position
        distances = np.linalg.norm(self.stars - player_position, axis=1)
        beyond_mask = distances > self.max_depth
        
        if np.any(beyond_mask) and allow_reset:
            
            num_reset = np.sum(beyond_mask)
            forward = movement_orientation.apply([0, 0, 1])
            right = movement_orientation.apply([1, 0, 0])
            up = movement_orientation.apply([0, 1, 0])

            # Reset twinkle properties
            self.twinkle_speed[beyond_mask] = np.random.uniform(0.01, 0.1, num_reset)
            self.twinkle_phase[beyond_mask] = np.random.uniform(0, 2*np.pi, num_reset)
            
            if global_flags.just_jumped:
                self.create_starfieldsphere(player_position)
                #global_flags.just_jumped = False
                
            else:
                
                # Create points with better angular distribution
                phi = np.random.uniform(0, 2*np.pi, num_reset)  # Angle around forward axis
                
                # Use cosine distribution for more even spread across angles
                cos_theta = np.random.uniform(-1, 1, num_reset)  # Uniform in cos(theta) gives even distribution
                theta = np.arccos(cos_theta)  # Convert to angle
                
                # Calculate positions on unit sphere
                x = np.sin(theta) * np.cos(phi)
                y = np.sin(theta) * np.sin(phi)
                z = np.abs(np.cos(theta))  # Use abs to keep stars in front
                
                # Scale to max_depth and transform to world space
                positions = self.max_depth * (right.reshape(3,1) * x + 
                                            up.reshape(3,1) * y + 
                                            forward.reshape(3,1) * z)
            
                # Place relative to player position
                self.stars[beyond_mask] = player_position + positions.T


    

    def render(self, view_matrix, focal_length, screen_center, WIDTH, HEIGHT):
        """Render starfield and return face list entries."""

        face_list = []
        
        # Transform stars to view space - create homogeneous coordinates for the transform
        stars_homogeneous = np.column_stack([self.stars, np.ones(self.num_stars)])
        stars_view = (view_matrix @ stars_homogeneous.T).T
        stars_view = stars_view[:, :3]  # Extract 3D coordinates
        
        # Project visible stars
        visible_mask = stars_view[:, 2] > 0
        if not np.any(visible_mask):
            return face_list
            
        visible_stars = stars_view[visible_mask]
        
        # Project to screen space
        screen_pos = np.column_stack([
            (focal_length * visible_stars[:, 0] / visible_stars[:, 2]) + screen_center[0],
            (focal_length * visible_stars[:, 1] / visible_stars[:, 2]) + screen_center[1]
        ])

        screen_mask = (screen_pos[:, 0] >= 0) & (screen_pos[:, 0] < WIDTH) & \
                     (screen_pos[:, 1] >= 0) & (screen_pos[:, 1] < HEIGHT)
        
        if not np.any(screen_mask):
            return face_list
            
        # Calculate radii vectorized
        radii = np.minimum(2, np.maximum(0.5, 1 * focal_length / visible_stars[screen_mask, 2]))
        

        # Calculate brightness vectorized
        base_brightness = np.minimum(255, (255 * focal_length / visible_stars[screen_mask, 2])).astype(int)
        
        # Twinkle calculations vectorized
        phases = self.twinkle_phase[visible_mask][screen_mask]
        twinkle_factors = 0.7 + 0.3 * np.sin(phases)
        
        distance_factors = np.minimum(1.0, visible_stars[screen_mask, 2] / (self.max_depth * 0.5))
        twinkle_amounts = distance_factors * (twinkle_factors - 1.0) + 1.0
        
        brightness = (base_brightness * twinkle_amounts).astype(int)
        
        # Create all face entries at once
        face_entries = list(zip(
            visible_stars[screen_mask, 2],  # depths
            map(lambda b: (b, b, b), brightness),  # colors
            map(lambda b: (b, b, b), brightness), #dummy for outline color, same as star color for now
            ['starfield'] * np.sum(screen_mask),  # face types
            map(tuple, screen_pos[screen_mask]),  # positions
            radii  # radii
        ))
        
        
        return face_entries

def calculate_normal(nodes_view, face):
    """Calculate face normal from first three vertices."""
    v = nodes_view[np.array(face[:3]), :3]  # Get first 3 vertices as a (3,3) array
    a = v[1] - v[0]
    b = v[2] - v[0]
    return np.cross(a, b)

def calculate_shading(normal, base_color):
    """Calculate shading intensity based on normal and light direction."""
    normal /= np.linalg.norm(normal)  # In-place normalization
    intensity = np.clip(np.dot(normal, LIGHT_DIR), 0.2, 1.0)
    return tuple(int(c * intensity) for c in base_color)

def calculate_shading_from_vertices(nodes_view, face, base_color):
    """Calculate normal and shading from vertices in one step."""
    # Calculate normal from first three vertices
    v = nodes_view[np.array(face[:3]), :3]
    a = v[1] - v[0]
    b = v[2] - v[0]
    normal = np.cross(a, b)
    norm = np.linalg.norm(normal)
    if norm != 0:
        normal /= norm
    intensity = np.clip(np.dot(normal, LIGHT_DIR), 0.2, 1.0)
    return tuple(int(c * intensity) for c in base_color)

def xis_visible_projected(poly, WIDTH, HEIGHT):
    xs = poly[:, 0]
    ys = poly[:, 1]
    # Quick check if any vertex is within screen bounds
    if np.any((xs >= 0) & (xs < WIDTH) & (ys >= 0) & (ys < HEIGHT)):
        return True, poly
    
    # If not visible, check if polygon might cross screen after clipping
    x_min, x_max = np.min(xs), np.max(xs)
    y_min, y_max = np.min(ys), np.max(ys)

    if (x_min < WIDTH and x_max >= 0 and
        y_min < HEIGHT and y_max >= 0):
        # Only clip if polygon might be partially visible
        margin = 1000
        clipped = np.clip(poly, [-margin, -margin],
                         [WIDTH + margin, HEIGHT + margin])
        return True, clipped
    
    return False, None

def is_visible_projected(poly, WIDTH, HEIGHT):
    xs = poly[:, 0]
    ys = poly[:, 1]
    # Fast path: any vertex on screen
    if np.any((xs >= 0) & (xs < WIDTH) & (ys >= 0) & (ys < HEIGHT)):
        return True, poly

    # Bounding box check
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    if (x_min < WIDTH and x_max >= 0 and y_min < HEIGHT and y_max >= 0):
        # Optionally skip clipping for speed
        return True, poly

    return False, None

def generate_face_list(objectList, view_matrix, player_position,player_right,player_forward, focal_length, screen_center, WIDTH, HEIGHT, starfield,particleList, planet_and_star,movement_orientation,main_loop_counter):
    
    """Main rendering function that processes all objects and returns face list."""
    face_list = []
    debug_lines = []  # New list for debug vectors
    targeting_boxes=[]
    plotting = 0
    
    # Handle starfield first
    if starfield:
            face_list.extend(starfield.render(view_matrix, focal_length, screen_center, WIDTH, HEIGHT))

    for obj in planet_and_star.objects.values():
        # Transform object position to view space
        pos_homogeneous = np.append(obj.position, 1)
        pos_view = view_matrix @ pos_homogeneous
        pos_view = pos_view[:3]  # Extract 3D coordinates
        
        # Skip if behind camera
        if pos_view[2] <= 0:
            continue
            
        # Project to screen space
        screen_pos = (
            focal_length * pos_view[0] / pos_view[2] + screen_center[0],
            focal_length * pos_view[1] / pos_view[2] + screen_center[1]
        )        # Calculate apparent size based on distance
        distance = np.linalg.norm(obj.position - player_position)
        apparent_radius = max(2, int(obj.radius * focal_length / distance))
        
        # Check if any part of circle is visible on screen
        x, y = screen_pos
        if (x + apparent_radius >= 0 and 
            x - apparent_radius < WIDTH and 
            y + apparent_radius >= 0 and 
            y - apparent_radius < HEIGHT):
            
            # Add to face list
            face_list.append((
                pos_view[2],  # depth for sorting
                obj.color,    # object color
                None,
                obj.obj_type,     # render as circle
                screen_pos,   # screen position
                apparent_radius  # circle radius
            ))

    for obj in objectList:
        if not global_flags.is_paused:
            obj.update(player_position,player_right,movement_forward = movement_orientation.apply([0, 0, 1]),objectList=objectList,particleList=particleList,main_loop_counter=main_loop_counter,planet_and_star=planet_and_star)
        
        nodes_view = obj.createView(view_matrix)
        
        #checks to see if object is visible or far away before rendering polygons    
        obj_center_view = np.mean(nodes_view, axis=0)
        if obj_center_view[2] < 0:
            continue  # Skip this object entirely as behind the camera
     

        if np.any(nodes_view[:, 2] <= 0):
            continue  # Skip this object if all vertices are behind camera    

        obj_distance = obj.distance_to_player

        if obj_distance > obj.view_threshold: 
            continue

        obj.is_visible = True  # Mark object as visible since it's within view threshold    
        obj.screen_pos = obj.projection_point(obj.coords, focal_length, screen_center, view_matrix)

        if obj_distance > obj.view_threshold / 2:
            # Draw a simple circle for distant objects
            if 0 <= obj.screen_pos[0] < WIDTH and 0 <= obj.screen_pos[1] < HEIGHT:
                circle_color = obj.colors[0] if obj.colors else (255, 255, 255)
                circle_radius = max(1, int(obj.dot_size / obj_distance))
                # Return a special "circle" face for rendering
                face_list.append((obj_distance, circle_color, None, 'circle', obj.screen_pos, circle_radius))
            continue

        #only render polygons for closer objects    
        projection = obj.projection(focal_length, screen_center)
        plotting += 1
        
    
            

        z_list=[]
        for i, face in enumerate(obj.faces):
            poly = projection[np.array(face)]
            avg_z = np.mean(nodes_view[face, 2])
            z_list.append(avg_z)

            visible, clipped_poly = is_visible_projected(poly, WIDTH, HEIGHT)
            if not visible or clipped_poly is None:
                continue
            cp = np.cross(clipped_poly[1] - clipped_poly[0], clipped_poly[2] - clipped_poly[1])
            if cp <= 0:
                continue

            if obj.detail_faces is not None and i in obj.detail_indices:
                avg_z = z_list[obj.detail_map[i]]-0.01

            # Use cached, rotated normal for shading
            if global_flags.wireframe_mode:
                shade = obj.line_color
            else:    
                normal = obj.get_face_normal(i)
                intensity = np.clip(np.dot(normal, -player_forward), 0.4, 1.0)
                base_color = obj.colors[i]
                shade = tuple(int(c * intensity) for c in base_color)
            
      
            if obj.distance_to_player < game_constants.RADAR_RANGE/5:
                outline = (0, 0, 0)  # Black outline for close objects
            else:
                outline = shade  # No outline for distant objects

            face_list.append((avg_z, shade,outline, 'polygon', poly, i))

        
    if global_flags.DEBUG_MODE:
        for obj in objectList:
            debug_vectors = obj.get_debug_vectors()
            for vector_name, (start, end, color) in debug_vectors.items():
                # Project start and end points to screen space
                start_2d = obj.projection_point(start, focal_length, screen_center, view_matrix)
                end_2d = obj.projection_point(end, focal_length, screen_center, view_matrix)
                
                if start_2d[0] >= 0 and end_2d[0] >= 0:  # Check if points are valid
                    debug_lines.append((
                        (int(start_2d[0]), int(start_2d[1])),
                        (int(end_2d[0]), int(end_2d[1])),
                        color
                    ))
    else:
        debug_lines = []  # Clear debug lines if not in debug mode                
    
    for obj in objectList:    
        if obj.locked_on_missile_index != -1:
            cx, cy = obj.screen_pos
            obj_distance = np.linalg.norm(obj.coords - player_position)
            box_size = max(5, int(obj.collision_radius * focal_length / obj_distance)) * 1.5
            half = box_size // 2
            box = [
                (cx - half, cy - half),
                (cx + half, cy - half),
                (cx + half, cy + half),
                (cx - half, cy + half)
            ]
            # Add to face_list for z-sorting
            face_list.append((obj_distance, (0, 255, 0), None, 'targeting_box', box, None))
      
        
    for particle in particleList:
        screen_pos, depth = project_point_to_screen(
            particle.position, view_matrix, focal_length, screen_center
        )
        if screen_pos is not None:
            face_list.append((
                depth,                # z/depth for sorting
                particle.color,       # color
                particle.color,     # placeholder for future use
                'particle',       
                screen_pos,           # 2D screen position
                particle.size         # size/radius
            ))

    return face_list, debug_lines, plotting

def ogl_render(face_list,movement_orientation):
    """Render all faces using OpenGL."""
    def set_color(color_tuple):
        if len(color_tuple) == 4:
            glColor4f(color_tuple[0]/255.0, color_tuple[1]/255.0, color_tuple[2]/255.0, color_tuple[3]/255.0)
        else:
            glColor3f(color_tuple[0]/255.0, color_tuple[1]/255.0, color_tuple[2]/255.0)

    sorted_faces = sorted(face_list, reverse=True, key=lambda x: x[0])

    for depth, color_1,color_2, face_type, geometry, radius in sorted_faces:
        
        if face_type == 'polygon':
            if global_flags.wireframe_mode:
                set_color([0.3,0.3,0.3])
                glBegin(GL_POLYGON)
                for vertex in geometry:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()
                # draw outline:
                glColor3f(color_1[0]/255.0, color_1[1]/255.0, color_1[2]/255.0)
                glBegin(GL_LINE_LOOP)
                for vertex in geometry:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()

            else:    
                set_color(color_1)
                glBegin(GL_POLYGON)
                for vertex in geometry:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()
                # draw outline:
                glColor3f(color_2[0]/255.0, color_2[1]/255.0, color_2[2]/255.0)
            
                glBegin(GL_LINE_LOOP)
                for vertex in geometry:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()


            
        elif face_type == 'circle':
            glPointSize(radius * 1.5)
            set_color(color_1)
            glBegin(GL_POINTS)
            glVertex2f(geometry[0], geometry[1])
            glEnd()

        elif face_type == 'particle':
            glColor3f(color_1[0]/255.0, color_1[1]/255.0, color_1[2]/255.0)
            glPointSize(radius)
            glBegin(GL_POINTS)
            glVertex2f(geometry[0], geometry[1])
            glEnd()
        elif face_type == 'starfield':
            glEnable(GL_POINT_SMOOTH)
            glPointSize(radius * 1.5)
            set_color(color_1)
            glBegin(GL_POINTS)
            glVertex2f(geometry[0], geometry[1])
            glEnd()

        elif face_type == 'targeting_box':
            glColor3f(color_1[0]/255.0, color_1[1]/255.0, color_1[2]/255.0)
            glBegin(GL_LINE_LOOP)
            for corner in geometry:
                glVertex2f(corner[0], corner[1])
            glEnd()
        elif face_type == ObjectType.PLANET:
            # ...inside the PLANET drawing block...
            base_color = np.array(color_1) / 255.0
            num_segments = 32  # Try reducing for speed
            theta = np.linspace(0, 2*np.pi, num_segments)
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            
            if movement_orientation is not None:
                forward = movement_orientation.apply([0, 0, 1])
                up = movement_orientation.apply([0, 1, 0])
                light_dir_3d = 0.7 * up + 0.7 * forward
                light_dir_2d = np.array([light_dir_3d[0], light_dir_3d[1]])
                if np.linalg.norm(light_dir_2d) > 0:
                    light_dir_2d /= np.linalg.norm(light_dir_2d)
                else:
                    light_dir_2d = np.array([-0.7, -0.7])
            else:
                light_dir_2d = np.array([-0.7, -0.7])
            
            # Precompute shading intensities
            nx = cos_t
            ny = sin_t
            raw = 0.5 + 0.5 * (nx * light_dir_2d[0] + ny * light_dir_2d[1])
            intensity = 0.1 + 0.7 * (raw ** 1.7)
            intensity = np.clip(intensity, 0.2, 1)
            shaded = np.clip(base_color[None, :] * intensity[:, None], 0, 1)
            
            glBegin(GL_TRIANGLE_FAN)
            # Center
            glColor3f(float(base_color[0]), float(base_color[1]), float(base_color[2]))
            glVertex2f(geometry[0], geometry[1])
            for i in range(num_segments):
                x = geometry[0] + radius * nx[i]
                y = geometry[1] + radius * ny[i]
                glColor3f(float(shaded[i][0]), float(shaded[i][1]), float(shaded[i][2]))
                glVertex2f(x, y)
            # Close the fan
            glColor3f(float(shaded[0][0]), float(shaded[0][1]), float(shaded[0][2]))
            x = geometry[0] + radius * nx[0]
            y = geometry[1] + radius * ny[0]
            glVertex2f(x, y)
            glEnd()
        elif face_type == ObjectType.STAR:
            
            global _SUN_FROZEN_TIME_MS
            base_color = np.array(color_1) / 255.0
            num_segments = _SUN_NUM_SEGMENTS
            theta = np.linspace(0, 2*np.pi, num_segments)
            if global_flags.is_paused:
                time_ms = _SUN_FROZEN_TIME_MS
            else:
                time_ms = pygame.time.get_ticks() if pygame.get_init() else 0
                _SUN_FROZEN_TIME_MS = time_ms
            time_phase = (time_ms / 600.0) % (2*np.pi)
            phase_offsets = _SUN_PHASE_OFFSETS
            wave_amp_ratio = 0.02  # 2% of radius
            wave_freq = 1.0
            
            # Precompute cos/sin for all segments
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            
            # Get player yaw (rotation around Y axis) if available
            orientation_angle = 0.0
            if movement_orientation is not None:
                rot_matrix = movement_orientation.as_matrix()
                orientation_angle = np.arctan2(rot_matrix[0, 2], rot_matrix[2, 2])
            
            glBegin(GL_TRIANGLE_FAN)
            # Center
            glColor3f(float(base_color[0]), float(base_color[1]), float(base_color[2]))
            glVertex2f(geometry[0], geometry[1])
            for i in range(num_segments):
                t = theta[i]
                wavy = 1.0 + wave_amp_ratio * np.sin(wave_freq * t + time_phase + phase_offsets[i] + orientation_angle)
                x = geometry[0] + radius * wavy * cos_t[i]
                y = geometry[1] + radius * wavy * sin_t[i]
                nx = cos_t[i]
                ny = sin_t[i]
                edge_intensity = 0.8 + 0.2 * (1 + ny) / 2
                color_mod = np.clip(base_color * edge_intensity, 0, 1)
                glColor3f(float(color_mod[0]), float(color_mod[1]), float(color_mod[2]))
                glVertex2f(x, y)
            wavy = 1.0 + wave_amp_ratio * np.sin(wave_freq * theta[0] + time_phase + phase_offsets[0] + orientation_angle)
            x = geometry[0] + radius * wavy * cos_t[0]
            y = geometry[1] + radius * wavy * sin_t[0]
            nx = cos_t[0]
            ny = sin_t[0]
            edge_intensity = 0.8 + 0.2 * (1 + ny) / 2
            color_mod = np.clip(base_color * edge_intensity, 0, 1)
            glColor3f(float(color_mod[0]), float(color_mod[1]), float(color_mod[2]))
            glVertex2f(x, y)
            glEnd()

def render_pygame_surface_as_texture(surface, x, y):
    """
    Renders a Pygame surface as an OpenGL texture at the specified coordinates.
    
    Args:
        surface: The Pygame surface to render
        x, y: The coordinates to place the texture on screen
    """
    # Get the dimensions of the surface
    width, height = surface.get_width(), surface.get_height()
    
    # Convert the Pygame surface to an OpenGL-compatible string format
    # We need to flip the surface vertically for OpenGL coordinates
    flipped_surface = pygame.transform.flip(surface, False, True)
    texture_data = pygame.image.tostring(flipped_surface, "RGBA", True)
    
    # Generate a new OpenGL texture ID
    texture_id = glGenTextures(1)
    
    # Save current OpenGL state
    glPushAttrib(GL_ALL_ATTRIB_BITS)
    
    # Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    # Set texture parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    
    # Upload the texture data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    
    # Enable texture mapping
    glEnable(GL_TEXTURE_2D)
    
    # Set color to white (to not affect the texture colors)
    glColor3f(1.0, 1.0, 1.0)
    
    # Draw a textured quad
    glBegin(GL_QUADS)
    # Bottom-left
    glTexCoord2f(0.0, 0.0)
    glVertex2f(x, y)
    # Bottom-right
    glTexCoord2f(1.0, 0.0)
    glVertex2f(x + width, y)
    # Top-right
    glTexCoord2f(1.0, 1.0)
    glVertex2f(x + width, y + height)
    # Top-left
    glTexCoord2f(0.0, 1.0)
    glVertex2f(x, y + height)
    glEnd()
    
    # Disable texture mapping
    glDisable(GL_TEXTURE_2D)
    
    # Unbind the texture
    glBindTexture(GL_TEXTURE_2D, 0)
    
    # Restore OpenGL state
    glPopAttrib()
    
    return texture_id

def draw_debug_lines(debug_lines):
    glBegin(GL_LINES)
    for start, end, color in debug_lines:
        glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
        glVertex2f(start[0], start[1])
        glVertex2f(end[0], end[1])
    glEnd()

def draw_targeting_boxes(targeting_boxes):
    glBegin(GL_LINE_LOOP)
    for box in targeting_boxes:
        glColor3f(0.0, 1.0, 0.0)  # green color for targeting boxes
        for corner in box:
            glVertex2f(corner[0], corner[1])
    glEnd()

def process_enemy_laser_beams(objectList,WIDTH,HEIGHT,view_matrix, focal_length, screen_center, near_clip=0.1):
    for obj in objectList:
        if obj.draw_laser:
            draw_enemy_laser_beams(obj,WIDTH,HEIGHT,view_matrix, focal_length, screen_center)  
    
      

def draw_enemy_laser_beams(obj,WIDTH,HEIGHT,view_matrix, focal_length, screen_center, near_clip=0.1):
   
    origin = obj.nodes_world[obj.gun_vertex]
    forward = obj.laser_orientation.apply([0, 0, 1])
    laser_length = 160000

    end_point = origin + forward * laser_length

    # Transform to camera space
    origin_hom = np.append(origin, 1.0)
    end_hom = np.append(end_point, 1.0)
    origin_cam = origin_hom @ view_matrix.T
    end_cam = end_hom @ view_matrix.T

    # If both points are behind camera, don't draw
    #if origin_cam[2] <= near_clip and end_cam[2] <= near_clip:
    if origin_cam[2] <= near_clip:
        return

    # Clip the segment to the near plane if needed
    def interpolate_to_near(p1, p2, z_near):
        t = (z_near - p1[2]) / (p2[2] - p1[2])
        return p1 + t * (p2 - p1)

    clipped_origin = origin_cam
    clipped_end = end_cam

    if origin_cam[2] <= near_clip:
        clipped_origin = interpolate_to_near(origin_cam, end_cam, near_clip)
    if end_cam[2] <= near_clip:
        clipped_end = interpolate_to_near(end_cam, origin_cam, near_clip)

    # Project to screen
    def project(cam_point):
        x_proj = (focal_length * cam_point[0]) / cam_point[2] + screen_center[0]
        y_proj = (focal_length * cam_point[1]) / cam_point[2] + screen_center[1]
        return np.array([x_proj, y_proj])

    origin_screen = project(clipped_origin)
    end_screen = project(clipped_end)

    # Draw the line (even if endpoints are off screen)
    glLineWidth(1)
    glColor3f(0.5, 0.6, 1.0)
    glBegin(GL_LINES)
    glVertex2f(origin_screen[0], origin_screen[1])
    glVertex2f(end_screen[0], end_screen[1])
    glEnd()

def render_launch_tunnel(screen_center, WIDTH, HEIGHT, clock, cockpit_console, input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, main_loop_counter,focal_length, duration=1.5, fps=60):
    sound_manager.play(SoundType.LAUNCH)

    frames = int(duration * fps)
    base_radius = 5
    color = (255, 255, 255)
    for frame in range(frames):
        glClear(GL_COLOR_BUFFER_BIT)
        radius = base_radius + frame *4
        r = radius
        while r < max(WIDTH, HEIGHT):
            num_segments = 25
            theta = np.linspace(0, 2 * np.pi, num_segments)
            glBegin(GL_LINE_LOOP)
            glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
            for t in theta:
                x = screen_center[0] + r * np.cos(t)
                y = screen_center[1] + r * np.sin(t)
                glVertex2f(x, y)
            glEnd()
            r *= 1.1
        cockpit_console.update_cockpit(input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, WIDTH, HEIGHT,main_loop_counter,focal_length,screen_center)
        pygame.display.flip()
        clock.tick(fps)

def render_hyperspace_tunnel(screen_center, WIDTH, HEIGHT, clock, cockpit_console, input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, main_loop_counter, focal_length, duration=1.5, fps=60):
    sound_manager.play(SoundType.HYPERSPACE)

    frames = int(duration * fps)
    base_radius = 5
    max_radius = max(WIDTH, HEIGHT)
    color = (255, 255, 255)
    # First half: expand
    for frame in range(frames // 2):
        glClear(GL_COLOR_BUFFER_BIT)
        radius = base_radius + (max_radius - base_radius) * (frame / (frames // 2))
        r = radius
        while r < max_radius:
            num_segments = 25
            theta = np.linspace(0, 2 * np.pi, num_segments)
            glBegin(GL_LINE_LOOP)
            glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
            for t in theta:
                x = screen_center[0] + r * np.cos(t)
                y = screen_center[1] + r * np.sin(t)
                glVertex2f(x, y)
            glEnd()
            r *= 1.1
        cockpit_console.update_cockpit(input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, WIDTH, HEIGHT,main_loop_counter, focal_length,screen_center)
        pygame.display.flip()
        clock.tick(fps)
    # Second half: contract
    for frame in range(frames // 2):
        glClear(GL_COLOR_BUFFER_BIT)
        radius = max_radius - (max_radius - base_radius) * (frame / (frames // 2))
        r = radius
        while r < max_radius:
            num_segments = 25
            theta = np.linspace(0, 2 * np.pi, num_segments)
            glBegin(GL_LINE_LOOP)
            glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
            for t in theta:
                x = screen_center[0] + r * np.cos(t)
                y = screen_center[1] + r * np.sin(t)
                glVertex2f(x, y)
            glEnd()
            r *= 1.1
        cockpit_console.update_cockpit(input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, WIDTH, HEIGHT,main_loop_counter, focal_length,screen_center)
        pygame.display.flip()
        clock.tick(fps)

def render_title_screen(screen_center, WIDTH, HEIGHT, main_loop_counter, focal_length):
    
    if not sound_manager.is_music_playing():
        sound_manager.play_music(SoundType.TITLE_MUSIC, loops=-1)  # Loop until stopped


    ship_list = ("Adder","Anaconda","Asp Mk II","Asteroid","Boa","Cobra Mk I","Cobra Mk III","Fer-de-Lance","Gecko","Krait","Mamba","Moray","Python","Shuttle","Sidewinder","Thargoid","Thargon","Transporter","Viper","Worm")    

    # --- Render spinning Ship ---
    # Only create the Ship once, store as a static attribute
    
    if TitleScreenState.ship is None or TitleScreenState.ship_index != TitleScreenState.last_rendered_ship_index:
        TitleScreenState.frame_counter=0
        TitleScreenState.last_rendered_ship_index=  TitleScreenState.ship_index
        from object import Object
        #ship_type = "Cobra Mk III"
        ship_type = ship_list[TitleScreenState.ship_index]
        ship_dictionary = wireframes.ships.get(ship_type)
        
        if ship_dictionary is None:
            raise ValueError(f"Unknown ship type: {ship_type}")
        
        TitleScreenState.ship = Object(
            ship_dictionary,
            coords=(0, 0, 1400),
            rotation_inc=(0.02, 0.03, -0.02)
            )
        print(f"view theshold for {ship_type}: {TitleScreenState.ship.view_threshold}")

    ship =TitleScreenState.ship


    # Set up a simple camera/view matrix
    camera_pos = np.array([0, 0, 0])
    target = np.array([0, 0, -120])
    up = np.array([0, 1, 0])
    def look_at(eye, target, up):
        f = (target - eye)
        f = f / np.linalg.norm(f)
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        u = np.cross(s, f)
        m = np.identity(4)
        m[0, :3] = s
        m[1, :3] = u
        m[2, :3] = -f
        m[:3, 3] = -eye
        return m
    view_matrix = look_at(camera_pos, target, up)

   
    # Generate face list for just the Cobra
    face_list, debug_lines, plotting = generate_face_list(
        [ship],  # Only the Cobra
        view_matrix,
        camera_pos,
        np.array([1, 0, 0]),  # player_right (arbitrary for single object)
        np.array([0, 0, -1]),  # player_forward (arbitrary for single object)
        focal_length,
        screen_center,
        WIDTH,
        HEIGHT,
        None,  # No starfield
        [],    # No particles
        type('Dummy', (), {'objects': {}})(),  # Empty planet_and_star
        ship.orientation,
        main_loop_counter
    )

    ogl_render(face_list, ship.orientation)


    TitleScreenState.frame_counter += 1
    if TitleScreenState.frame_counter <255:
        ship.nodes_world[:, :3] += [0.0,0.0,-5.0]
        ship.setCenter(ship.nodes_world)
    elif TitleScreenState.frame_counter >800:
        TitleScreenState.frame_counter =0
        TitleScreenState.ship_index +=1
        if TitleScreenState.ship_index >= len(ship_list):
            TitleScreenState.ship_index =0
    elif TitleScreenState.frame_counter >700:
        ship.nodes_world[:, :3] += [0.0,0.0,10.0]
        ship.setCenter(ship.nodes_world)
        ship.colors = [[int(c * 0.95) for c in color]for color in ship.colors]
        ship.line_color = [int(c * 0.95) for c in ship.line_color]
              
    else:
        # --- Render Ship Name ---
        text = ship_list[TitleScreenState.ship_index]
        font = FONTS['small']
        y_pos = int(HEIGHT * 0.6)
        x_pos = int(WIDTH*0.7)
        drawText(
            x=x_pos,
            y=y_pos,
            WIDTH=WIDTH,
            HEIGHT=HEIGHT,
            text=text,
            font=font,
            text_color=(255, 255, 255),
            bg_color=(0, 0, 0, 0),
            centered=False
    )
        


   
    
    # --- Render ELITE title ---
    font = FONTS['xlarge']
    text = get_text('ELITE')
    y_pos = int(HEIGHT * 0.1)
    drawText(
        x=0,
        y=y_pos,
        WIDTH=WIDTH,
        HEIGHT=HEIGHT,
        text=text,
        font=font,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0, 0),
        centered=True
    )
    
    font = FONTS['small']
    text = get_text("python_edition")
    y_pos = int(HEIGHT * 0.11)
    drawText(
        x=0,
        y=y_pos,
        WIDTH=WIDTH,
        HEIGHT=HEIGHT,
        text=text,
        font=font,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0, 0),
        centered=True
    )

    # --- Render menu prompt ---
    text = get_text("load_prompt")
    font = FONTS['large']
    y_pos = int(HEIGHT * 0.75)
    drawText(
        x=0,
        y=y_pos,
        WIDTH=WIDTH,
        HEIGHT=HEIGHT,
        text=text,
        font=font,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0, 0),
        centered=True
    )

    

def game_over_screen(screen_center, WIDTH, HEIGHT, player_position, player_right, movement_forward,look_forward, planet_and_star, objectList, particleList, main_loop_counter, focal_length,movement_orientation,starfield,player_target,look_up):
    
    
    explosion_point=100

    if GameOverScreenState.cobra is None:
        from object import Object
        ship_type = "Cobra Mk III"
        ship_dictionary = wireframes.ships.get(ship_type)
        
        if ship_dictionary is None:
            raise ValueError(f"Unknown ship type: {ship_type}")
        
        # Place Cobra 50 units behind the player along the forward vector
        cobra_coords = np.array(player_position) - 20 * np.array(movement_forward)
        GameOverScreenState.cobra = Object(
            ship_dictionary,
            coords=cobra_coords,
            rotation_inc=(0.005, 0.004, 0),
        )
        
        cobra = GameOverScreenState.cobra
        cobra.forward = cobra.orientation.apply([0, 0, 1])
        cobra.right = cobra.orientation.apply([1, 0, 0])
        cobra.up = cobra.orientation.apply([0, 1, 0])
        
        # Apply rotation to the mesh nodes so it visually points the right way
        rot_matrix = movement_orientation.as_matrix()
        nodes_centered = cobra.nodes_world - cobra.center
        nodes_rotated = nodes_centered[:, :3] @ rot_matrix.T
        cobra.nodes_world[:, :3] = nodes_rotated + cobra.center[:3]
        cobra.name = "Player Cobra"
        
    
    cobra = GameOverScreenState.cobra    
    zoom_out = main_loop_counter - global_flags.frame_start
    camera_offset = min(zoom_out,100)*3
    camera_position = player_position - camera_offset * movement_forward
    view_matrix = objectList[0].look_at_matrix(camera_position, player_target, look_up)


    
    if zoom_out == 1:
        objectList.append(cobra)

    elif zoom_out==explosion_point+50:
        cobra.ready_for_removal = True
        from game_events import handle_explosion
        handle_explosion(cobra, objectList, particleList,player_position,player_right)   
    

    for particle in particleList[:]:
            particle.update()
            if not particle.is_alive():
                particleList.remove(particle)    


    face_list, _, _ = generate_face_list(
            objectList,
            view_matrix,
            player_position,
            movement_orientation.apply([1, 0, 0]),
            look_forward,
            focal_length,
            screen_center,
            WIDTH,
            HEIGHT,
            starfield,
            particleList,
            planet_and_star,
            movement_orientation,
            main_loop_counter
        )
        
        # Draw all objects, starfield and planets
        
    
    ogl_render(face_list, movement_orientation)


    # --- Render GAME OVER ---
    font = FONTS['xlarge']
    text = get_text("game_over")
    y_pos = int(HEIGHT * 0.8)
    drawText(
        x=0,
        y=y_pos,
        WIDTH=WIDTH,
        HEIGHT=HEIGHT,
        text=text,
        font=font,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0, 0),
        centered=True
    )

    # --- Render menu prompt ---
    text =get_text("restart_prompt")
    font = FONTS['large']
    y_pos = int(HEIGHT * 0.9)
    drawText(
        x=0,
        y=y_pos,
        WIDTH=WIDTH,
        HEIGHT=HEIGHT,
        text=text,
        font=font,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0, 0),
        centered=True
    )

    
    return
def render_escape_pod_launch(screen_center, WIDTH, HEIGHT, player_position, player_right, movement_forward,look_forward, planet_and_star, objectList, particleList, main_loop_counter, focal_length,movement_orientation,starfield,player_target,look_up):
    end_point=500

    if EscapePodLaunchState.cobra is None:
        from object import Object
        ship_type = "Cobra Mk III"
        ship_dictionary = wireframes.ships.get(ship_type)
        
        if ship_dictionary is None:
            raise ValueError(f"Unknown ship type: {ship_type}")
        
        # Place Cobra 50 units behind the player along the forward vector
        cobra_coords = np.array(player_position) - 20 * np.array(movement_forward)
        EscapePodLaunchState.cobra = Object(
            ship_dictionary,
            coords=cobra_coords+look_forward*50,
            rotation_inc=(0.005, 0.004, 0),
        )
        
        cobra = EscapePodLaunchState.cobra
        cobra.forward = cobra.orientation.apply([0, 0, 1])
        cobra.right = cobra.orientation.apply([1, 0, 0])
        cobra.up = cobra.orientation.apply([0, 1, 0])
        
        # Apply rotation to the mesh nodes so it visually points the right way
        rot_matrix = movement_orientation.as_matrix()
        nodes_centered = cobra.nodes_world - cobra.center
        nodes_rotated = nodes_centered[:, :3] @ rot_matrix.T
        cobra.nodes_world[:, :3] = nodes_rotated + cobra.center[:3]
        cobra.name = "Player Cobra"
    
    cobra = EscapePodLaunchState.cobra    
    frames = main_loop_counter - global_flags.frame_start
    camera_offset = frames*4
    camera_position = player_position - camera_offset * movement_forward
    view_matrix = objectList[0].look_at_matrix(camera_position, player_target, look_up)

    
    if frames == 1:
        
        objectList.append(cobra)

    elif frames > end_point:
        global_flags.game_state = global_flags.STATE_DOCKING
    

    for particle in particleList[:]:
            particle.update()
            if not particle.is_alive():
                particleList.remove(particle)    


    face_list, _, _ = generate_face_list(
            objectList,
            view_matrix,
            player_position,
            movement_orientation.apply([1, 0, 0]),
            look_forward,
            focal_length,
            screen_center,
            WIDTH,
            HEIGHT,
            starfield,
            particleList,
            planet_and_star,
            movement_orientation,
            main_loop_counter
        )
        
    # Draw all objects, starfield and planets
    ogl_render(face_list, movement_orientation)

def render_jump_warp(screen_center, WIDTH, HEIGHT, player_position, player_right, movement_forward,look_forward, planet_and_star, objectList, particleList, main_loop_counter, focal_length,movement_orientation,starfield,player_target,look_up):
    
    if main_loop_counter == global_flags.frame_start:
        #store initial screen x,y of stars in starfield
        player_target = player_position + look_forward
        view_matrix = objectList[0].look_at_matrix(player_position, player_target, look_up)
        jump_warp_state.initial_xy = []
        for star in starfield.stars:
            proj, _ = project_point_to_screen(star, view_matrix, focal_length, screen_center)
            jump_warp_state.initial_xy.append(proj.tolist() if proj is not None else None)

    
    elif main_loop_counter< global_flags.frame_start + global_flags.warp_effect_frames:
        player_position += movement_forward * global_flags.warp_movement_per_frame
        player_target = player_position + look_forward
        view_matrix = objectList[0].look_at_matrix(player_position, player_target, look_up)
        
        
        # Compute polygons, starfield and planets
        face_list, debug_lines, plotting = generate_face_list(
            objectList,
            view_matrix,
            player_position,
            movement_orientation.apply([1, 0, 0]),
            look_forward,
            focal_length,
            screen_center,
            WIDTH,
            HEIGHT,
            [],
            [],
            planet_and_star,  # Empty planet_and_star
            movement_orientation,
            main_loop_counter
        )
        
        # Draw all objects, starfield and planets
        ogl_render(face_list, movement_orientation)  # Pass orientation for lighting

        # Draw star streaks
        glLineWidth(2.0)
        glColor3f(1.0, 1.0, 1.0)  # White lines
        glBegin(GL_LINES)
        for curr, init_proj in zip(starfield.stars, jump_warp_state.initial_xy):
            curr_proj, _ = project_point_to_screen(curr, view_matrix, focal_length, screen_center)
            if init_proj is not None and curr_proj is not None:
                glVertex2f(init_proj[0], init_proj[1])
                glVertex2f(curr_proj[0], curr_proj[1])
        glEnd()

        
    
        
    else:
        global_flags.game_state = global_flags.STATE_FLYING

        limit =min(global_flags.station_distance, global_flags.planet_distance, global_flags.sun_distance)

        if limit > global_flags.short_range_jump_distance:
            jump_distance = global_flags.short_range_jump_distance-(global_flags.warp_effect_frames * global_flags.warp_movement_per_frame)
        else:
            jump_distance = limit/2 - (global_flags.warp_effect_frames * global_flags.warp_movement_per_frame)

        global_flags.just_jumped=True
        player_position += movement_forward * jump_distance
        global_flags.extra_vessels_counter = 0 #reset extra vessels counter on jump
        
def render_constrictor(screen_center, WIDTH, HEIGHT, main_loop_counter, focal_length):
    
    # --- Render spinning Ship ---
    # Only create the Ship once, store as a static attribute
    
    if MissionState.ship is None: 
        from object import Object
        ship_type = "Constrictor"
        ship_dictionary = wireframes.ships.get(ship_type)
        
        if ship_dictionary is None:
            raise ValueError(f"Unknown ship type: {ship_type}")
        
        MissionState.ship = Object(
            ship_dictionary,
            coords=(0, 0, 100),
            rotation_inc=(0.02, 0.03, -0.02)
            )
        

    ship =MissionState.ship
    

    # Set up a simple camera/view matrix
    camera_pos = np.array([0, 0, 0])
    target = np.array([0, 0, -120])
    up = np.array([0, 1, 0])
    def look_at(eye, target, up):
        f = (target - eye)
        f = f / np.linalg.norm(f)
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        u = np.cross(s, f)
        m = np.identity(4)
        m[0, :3] = s
        m[1, :3] = u
        m[2, :3] = -f
        m[:3, 3] = -eye
        return m
    view_matrix = look_at(camera_pos, target, up)

   
    # Generate face list for just the Constrictor
    face_list, debug_lines, plotting = generate_face_list(
        [ship],  # Only the Constrictor
        view_matrix,
        camera_pos,
        np.array([1, 0, 0]),  # player_right (arbitrary for single object)
        np.array([0, 0, -1]),  # player_forward (arbitrary for single object)
        focal_length,
        screen_center,
        WIDTH,
        HEIGHT,
        None,  # No starfield
        [],    # No particles
        type('Dummy', (), {'objects': {}})(),  # Empty planet_and_star
        ship.orientation,
        main_loop_counter
    )

    ogl_render(face_list, ship.orientation)


              
    
        

   