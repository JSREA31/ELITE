import random
import numpy as np
import matrices as mx
from scipy.spatial.transform import Rotation as R
import game_events
from status import game_constants, global_flags,player
import status
from sounds import sound_manager, SoundType
from text_strings import get_text
from enum import Enum

VIEW_THRESHOLD_FACTOR = 600.0
DOT_SIZE_MULTIPLIER = 250.0

class AI_state(Enum):
    AI_IDLE = 0
    AI_ATTACKING = 1
    AI_EVADING = 2
    AI_TURNING = 3

class Object:
    def __init__(self, ship_dictionary,
                type='',
                name='',
                nodes=[],
                faces=[],
                detail=[],
                colors=[], 
                scale=(1.0, 1.0, 1.0), 
                coords=(0, 0, 0), 
                coords_inc=(0, 0, 0), 
                initial_rotation=(0, 0, 0), 
                rotation_inc=(0, 0, 0),
                orientation=(0, 0, 0),
                forward_speed=0.0):
        
        if ship_dictionary is not None:
            self.type = ship_dictionary['type']
            self.name = ship_dictionary['name']
            self.nodes_model = ship_dictionary['nodes']
            self.faces = ship_dictionary['faces']
            self.detail_faces = ship_dictionary['detail']
            self.colors = ship_dictionary['colors']
            self.scale = ship_dictionary['scale']
        else:
            self.type = type
            self.name = name
            self.nodes_model = np.array(nodes, dtype=float)
            self.faces = faces
            self.detail_faces = detail
            self.colors = colors
            self.scale = scale



        if self.detail_faces is not None:
            self.detail_indices = [group[1] for group in self.detail_faces]
            self.detail_map = {group[1]: group[0] for group in self.detail_faces}
        else:
            self.detail_indices = []
            self.detail_map = {}    
        
        self.line_color = [255, 255, 255]  # Default line color
        self.forward_speed = forward_speed
        self.is_visible = False
        self.screen_pos = np.array([-1, -1])  # Initialize screen position
        self.locked_on_missile_index = -1
        self.ready_for_removal = False
        self.frame_count = 0
        self.frame_count_life = -1
        self.radar_rect_size = 4
        self.distance_to_player = 0.0
        self.fire_laser=False
        self.draw_laser = False
        self.laser_frame_count_life = -1
        self.laser_duration = 8
        self.laser_refire = 0
        self.laser_refire_delay = 25
        self.aggression = 0
        self.just_been_hit = False
        self.is_docking = False
        self.docking_stage= 0
        self.prev_distance_to_point=0.0
        self.tactics_slot = random.randint(0, game_constants.TACTICS_SLOTS - 1)
        self.spawn_extra_count=0
        self.acceleration = 0.0
        self.slow_while_turning = True
        self.is_drifting = False
        self.turning_away = False
        self.turning_towards = False
        self.evading = False
        self.turning_away_frame_start=0
        self.evade_frame_start=0

        self.AI_state = AI_state.AI_IDLE
        

        # Movement properties
        self.coords = np.array(coords, dtype=float)
        self.coords_inc = np.array(coords_inc, dtype=float)
        self.initial_rotation = np.array(initial_rotation, dtype=float) 
        self.rotation = np.array([0,0,0], dtype=float)
        self.rotation_inc = np.array(rotation_inc, dtype=float)
        self.tumble_mode = False  # If True, rotations happen in world space (for asteroids)
        
        # Apply scaling first
        self.scaleObject()

        self.nodes_world = np.copy(self.nodes_model)  # Current world position nodes
        self.nodes_view = np.copy(self.nodes_model)   # View space nodes (keep this separate)
        
        # Orientation setup
        self.orientation = R.from_euler('xyz', np.array(orientation, dtype=float))
        # Initialize orientation vectors correctly:
        # forward is along positive Z axis (into the screen)
        # right is along positive X axis
        # up is along positive Y axis
        self.forward = self.orientation.apply([0, 0, 1])
        self.right = self.orientation.apply([1, 0, 0])
        self.up = self.orientation.apply([0, 1, 0])
        self.laser_orientation = self.orientation
                
        # Calculate size after scaling
        self.size = np.linalg.norm(np.max(self.nodes_model, axis=0) - np.min(self.nodes_model, axis=0))
        center_model = self.nodes_model.mean(axis=0)
        self.bounding_radius = np.linalg.norm(self.nodes_model[:, :3] - center_model[:3], axis=1).max()
        self.average_radius = np.linalg.norm(self.nodes_model[:, :3] - center_model[:3], axis=1).mean()
        self.collision_radius = (self.bounding_radius+self.average_radius)/2
        if self.type == 'missile':
            self.collision_radius = 5  # Smaller collision radius for missiles

        # Set view properties using constants
        self.view_threshold = self.size * VIEW_THRESHOLD_FACTOR
        self.dot_size = float(self.size * DOT_SIZE_MULTIPLIER)

        # Apply initial coordinates and rotation
        self.setInitialRotation()
        self.setInitialCoords(self.coords)

        # Create fragments for explosion rendering
        if self.type != "fragment" :
            self.fragments = self._create_fragments()

        # Precompute face normals in model space
        self.face_normals_model = self._compute_face_normals(self.nodes_model, self.faces)

        #add ship specific meta data, like bounty creidts, laser power etc
        self.add_ship_data(ship_dictionary)        
        

    @staticmethod
    def compute_normal(nodes, face):
        """Compute the unit normal for a face given nodes and face indices."""
        if len(face) < 3:
            return np.array([0.0, 0.0, 1.0])
        v = nodes[np.array(face[:3]), :3]
        n = np.cross(v[1] - v[0], v[2] - v[0])
        n_norm = np.linalg.norm(n)
        if n_norm == 0:
            return np.array([0.0, 0.0, 1.0])
        return n / n_norm

    def _compute_face_normals(self, nodes, faces):
        """Compute and return unit normals for each face in model space."""
        return np.array([self.compute_normal(nodes, face) for face in faces])


    def _create_fragments(self):
        fragments = []
        for i, face in enumerate(self.faces):
            face_nodes = self.nodes_model[face]
            double_sided_faces = [list(range(len(face_nodes))), list(reversed(range(len(face_nodes))))]
            # Compute normal for this fragment (same as face normal)
            normal = self.compute_normal(self.nodes_model, face)
            frag = {
                "nodes": face_nodes.copy(),
                "faces": double_sided_faces,
                "colors": self.colors,
                "index": i,
                "normal": normal
            }
            fragments.append(frag)
        return fragments


    def scaleObject(self):
        """Scale the object by the given scale factor."""
        scale = self.scale
        scale_matrix = mx.scaleMatrix(scale)
        self.nodes_model = self.nodes_model @ scale_matrix.T
        self.nodes_world = np.copy(self.nodes_model)  # Update world nodes to scaled model

        
    def setInitialRotation(self):
        self.setCenter(self.nodes_world)
        self.apply_rotation(self.initial_rotation)


    def setInitialCoords(self, coords):
        """Set initial coordinates for object."""
        self.coords = coords
        self.nodes_world[:, :3] += self.coords  # Fast vector addition
        self.setCenter(self.nodes_world)


    def setCenter(self,nodes):
        self.center = nodes.mean(axis=0)  

    
    def update(self,player_position,player_right,movement_forward,objectList,particleList,main_loop_counter,planet_and_star=None):
        """Update object position, rotation and orientation vectors."""
        # Handle rotation if any axis is changing
        self.frame_count += 1

        if self.acceleration!=0.0:
            self.forward_speed += self.acceleration
            self.forward_speed = max(self.minimum_speed, min(self.forward_speed, self.maximum_speed))
            if self.forward_speed == self.minimum_speed or self.forward_speed == self.maximum_speed:
                self.acceleration = 0.0

        self.distance_to_player = np.linalg.norm(self.coords - player_position)
        if self.distance_to_player > game_constants.MAX_OBJECT_DISTANCE and self.type !='station':
            self.ready_for_removal = True
            return
       

        if self.frame_count==self.frame_count_life and self.frame_count_life>0:
            self.ready_for_removal=True
            return

        if self.type=="fragment":
            self.colors = [[c * 0.99 for c in color] for color in self.colors]
            self.line_color = [c * 0.99 for c in self.line_color]


        if np.any(self.rotation_inc != 0):
            self.rotation += self.rotation_inc
            self.rotation = self.rotation % (2 * np.pi)
            
            # Apply rotation using either tumble (world space) or normal (local space) mode
            if self.tumble_mode:
                self.apply_tumble(self.rotation_inc)
            else:
                self.apply_rotation(self.rotation_inc)

        # Handle forward movement if set
        if self.forward_speed != 0:
            self.coords_inc = self.forward * self.forward_speed
        else:
            self.coords_inc = np.array([0.0, 0.0, 0.0])

        # Handle translation
        if np.any(self.coords_inc != 0):
            self.coords += self.coords_inc
            self.nodes_world[:, :3] += self.coords_inc
            self.setCenter(self.nodes_world)

        self.is_visible = False  # Reset visibility each frame, rendered will set to True if visible
        
        # Only call handle_tactics if this object's tactics slot matches the residual
        if self.type in ['ship', 'station'] and global_flags.is_flying:
            residual = main_loop_counter % game_constants.TACTICS_SLOTS
            if residual == self.tactics_slot:
                self.handle_tactics(player_position, objectList,planet_and_star)

        if self.is_docking:
            self.dock_with_station(objectList)
        elif self.AI_state == AI_state.AI_TURNING:
            self.turning_away_from_player(player_position)
        elif self.AI_state == AI_state.AI_ATTACKING:
            self.turning_towards_player(player_position)
        elif self.AI_state == AI_state.AI_EVADING:
            self.evade(player_position, player_right)        


        if self.draw_laser and self.frame_count > self.laser_frame_count_life:
            self.draw_laser = False
            self.laser_refire = self.frame_count + self.laser_refire_delay

        if self.fire_laser and self.frame_count >= self.laser_refire:    
            self.process_laser_fire(player_position,movement_forward,main_loop_counter)
            self.fire_laser=False
            self.draw_laser = True
            self.laser_frame_count_life = self.frame_count+self.laser_duration
    
 
    def get_angle_to_player(self,player_position): 
        # 1. Calculate vector from object to player
        vec_to_player = np.array(player_position) - self.coords
        vec_to_player_norm = vec_to_player / np.linalg.norm(vec_to_player)

        # 2. Get object's forward vector (already normalized)
        forward_norm = self.forward / np.linalg.norm(self.forward)

        # 3. Calculate angle between vectors
        dot = np.clip(np.dot(vec_to_player_norm, forward_norm), -1.0, 1.0)
        angle_deg = np.degrees(np.arccos(dot))
        return  angle_deg    

    def process_laser_fire(self, player_position,movement_forward,main_loop_counter):
        
        angle_deg= self.get_angle_to_player(player_position)
        self.laser_orientation = self.orientation


        o = self.coords
        d = self.forward / np.linalg.norm(self.forward)
        p = np.array(player_position)
        v = p - o
        # Project v onto d, then subtract to get perpendicular component
        v_parallel = np.dot(v, d) * d
        v_perp = v - v_parallel
        d = np.linalg.norm(v_perp)    


        print(f"Laser fired! Angle to player: {angle_deg:.2f} degrees, perpendicular distance: {d:.2f}")
        if angle_deg <= game_constants.LASER_HIT_ANGLE:
            sound_manager.play(SoundType.ENEMY_LASER)
                
            game_events.process_damage(self.coords, player_position, movement_forward, self.laser_power*6,main_loop_counter)
            self.acceleration = -0.1 # slow down if object gets a hit  
            


    def get_orientation_vectors(self):
        """Return current orientation vectors."""
        return self.forward, self.right, self.up


    def get_face_normal(self, face_index):
        """Get face normal in world space using precomputed model normal and current orientation."""
        n_model = self.face_normals_model[face_index]
        n_world = self.orientation.apply(n_model)
        return n_world
    

    def look_at_matrix(self, eye, target, up):
        """Create a view matrix for looking from eye to target with up direction.
        
        Note: This still returns a 4x4 matrix because the view transformation 
        requires both rotation and translation.
        """
        f = target - eye
        f /= np.linalg.norm(f)
        r = np.cross(f, up)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        
        # Create a 4x4 view matrix
        mat = np.zeros((4, 4))
        mat[0, :3] = r
        mat[1, :3] = u
        mat[2, :3] = f
        mat[3, 3] = 1.0
        mat[0, 3] = -np.dot(r, eye)
        mat[1, 3] = -np.dot(u, eye)
        mat[2, 3] = -np.dot(f, eye)
        return mat


    def createView(self, view_matrix):
        # Transform world coordinates to view space using the view matrix
        # Create homogeneous coordinates for transformation
        nodes_hom = np.ones((self.nodes_world.shape[0], 4), dtype=self.nodes_world.dtype)
        nodes_hom[:, :3] = self.nodes_world[:, :3]
        # Matrix multiplication with the 4x4 view matrix
        nodes_cam = nodes_hom @ view_matrix.T
        # Store the view space coordinates (xyz)
        self.nodes_view = nodes_cam[:, :3]
        return self.nodes_view

         
    def projection(self, focal_length, screen_center):
        nodes_cam = self.nodes_view[:, :3]
        z = nodes_cam[:, 2].copy()  # Avoid modifying the original array
        z[z == 0] = 1e-5            # Prevent division by zero
        x_proj = (focal_length * nodes_cam[:, 0]) / z + screen_center[0]
        y_proj = (focal_length * nodes_cam[:, 1]) / z + screen_center[1]
        out = np.empty((nodes_cam.shape[0], 2), dtype=nodes_cam.dtype)
        out[:, 0] = x_proj
        out[:, 1] = y_proj
        return out


    def projection_point(self, point, focal_length, screen_center, view_matrix):
        """Project a single 3D point to 2D screen coordinates."""
        # Transform point to homogeneous coordinates
        point_hom = np.array([point[0], point[1], point[2], 1.0])
        # Transform to camera space
        point_cam = point_hom @ view_matrix.T
        # Project to screen
        if point_cam[2] > 0:  # In front of camera
            x_proj = (focal_length * point_cam[0]) / point_cam[2] + screen_center[0]
            y_proj = (focal_length * point_cam[1]) / point_cam[2] + screen_center[1]
            return np.array([x_proj, y_proj])
        else:
            return np.array([-1, -1])  # Behind camera, invalid screen position


    def get_debug_vectors(self, vector_length=10.0):
        """Get debug vector lines for orientation in world space."""
        # Start point is object center
        start = self.center[:3]
        
        # Calculate end points for each vector
        forward_end = start + self.forward * vector_length
        right_end = start + self.right * vector_length
        up_end = start + self.up * vector_length
        
        return {
            'forward': (start, forward_end, (0, 0, 255)),    # Blue for forward
            'right': (start, right_end, (255, 0, 0)),        # Red for right
            'up': (start, up_end, (0, 255, 0))               # Green for up
        }
    

    def apply_rotation(self, rotation_angles, update_vectors=True):
        """Apply rotation around object's local axes.
        
        Args:
            rotation_angles: Array of [x,y,z] rotation angles in radians
            update_vectors: Whether to update orientation vectors (default: True)
        
        Returns:
            The combined rotation object
        """
        # Create rotation increments in the object's local coordinate system
        rot_x = R.from_rotvec(self.right * rotation_angles[0])
        rot_y = R.from_rotvec(self.up * rotation_angles[1])
        rot_z = R.from_rotvec(self.forward * rotation_angles[2])

        combined_rotation = rot_z * rot_y * rot_x

        if update_vectors:
            self.orientation = combined_rotation * self.orientation
            self.forward = self.orientation.apply([0, 0, 1])
            self.right = self.orientation.apply([1, 0, 0])
            self.up = self.orientation.apply([0, 1, 0])

        rot_matrix = combined_rotation.as_matrix()
        nodes_centered = self.nodes_world - self.center
        self.nodes_world = nodes_centered @ rot_matrix.T + self.center
        
        return combined_rotation


    def apply_tumble(self, rotation_angles):
        """Apply rotation around world axes (for objects like asteroids that tumble).
        Only rotates the geometry, not the orientation vectors used for movement.
        
        Args:
            rotation_angles: Array of [x,y,z] rotation angles in radians
        """
        # Create rotation increments in world coordinate system
        rot_x = R.from_rotvec(np.array([1, 0, 0]) * rotation_angles[0])  # Around world X axis
        rot_y = R.from_rotvec(np.array([0, 1, 0]) * rotation_angles[1])  # Around world Y axis
        rot_z = R.from_rotvec(np.array([0, 0, 1]) * rotation_angles[2])  # Around world Z axis

        combined_rotation = rot_z * rot_y * rot_x

        # Apply rotation to nodes around their center (geometry only)
        rot_matrix = combined_rotation.as_matrix()
        nodes_centered = self.nodes_world - self.center
        self.nodes_world = nodes_centered @ rot_matrix.T + self.center
        
        # NOTE: Do NOT update orientation vectors (forward, right, up) in tumble mode
        # This keeps movement direction constant while geometry spins


    def get_docking_port_position(self):
        """Return the center of the docking port in world space.
        
        For the dodo space station, this is the center of vertices 20-23,
        for coriolis station, this is the center of vertices  as 48-51,
        which define the entrance port. For other objects, returns the center.
        
        """
        if self.type != 'station':
            return self.coords
            
        if self.name == 'Coriolis station':
            # Calculate the center of the docking port (average of vertices 48-51)
            port_vertices = [48, 49, 50, 51]
         
        else:
            # Calculate the center of the docking port (average of vertices 20-23)
            port_vertices = [20, 21, 22, 23]      
              
        port_center = np.mean([self.nodes_world[i][:3] for i in port_vertices], axis=0)
        return port_center  # Return just the XYZ coordinates
    

    def add_ship_data(self,ship_dictionary=None):
        if self.type =='station':
            self.has_ecm = True
        else:
            self.has_ecm = False

        if  ship_dictionary is not None:
            self.energy = ship_dictionary.get('Maximum shield energy')
            self.max_energy = self.energy
            self.gun_vertex = ship_dictionary.get('Gun vertex')
            self.laser_power = ship_dictionary.get('Laser power')
            self.missile_count = ship_dictionary.get('Missile count')
            self.maximum_speed = ship_dictionary.get('Maximum speed')/10.0
            self.minimum_speed = self.maximum_speed * 0.4
            self.bounty = ship_dictionary.get('Bounty (Cr)')
            self.targetable_area = ship_dictionary.get('Targetable area')
            self.maximum_canisters_on_demise = ship_dictionary.get('Maximum canisters on demise')
            self.explosion_count = ship_dictionary.get('Explosion count')
            self.kill_points = ship_dictionary.get('kill points')
            self.is_innocent = ship_dictionary.get('is_innocent')
            self.is_a_pirate = ship_dictionary.get('is_a_pirate')
            self.is_a_bounty_hunter = ship_dictionary.get('is_a_bounty_hunter')
            self.is_a_trader = ship_dictionary.get('is_a_trader')
            self.is_a_cop = ship_dictionary.get('is_a_cop')
            self.is_hostile = ship_dictionary.get('is_hostile')
            self.has_escape_pod = ship_dictionary.get('has_escape_pod')
            self.radar_color= ship_dictionary.get('radar_color',[255, 215, 0])
        else:
            self.energy = 0
            self.max_energy = 0
            self.gun_vertex = 0
            self.laser_power = 0
            self.missile_count = 0
            self.maximum_speed = 0.0
            self.minimum_speed = 0.0
            self.bounty = 0
            self.targetable_area = 0.0
            self.maximum_canisters_on_demise = 0
            self.explosion_count = 0
            self.kill_points = 0
            self.is_innocent = False
            self.is_a_pirate = False
            self.is_a_bounty_hunter = False
            self.is_a_trader = False
            self.is_a_cop = False
            self.is_hostile = False
            self.has_escape_pod = False
            self.radar_color= [255, 215, 0]

    def handle_tactics(self,player_position, objectList,planet_and_star):
       #recharge energy by 1 unit
        if self.energy <self.max_energy:
            self.energy +=1  #simple energy recharge

        #object specifc tactics
        if self.type =='station':
            if global_flags.station_is_hostile:
                if self.spawn_extra_count < game_constants.STATION_MAX_COPS and random.random() < 0.062:  
                    self.spawn_extra_count +=1
                    spawn_coords =self.coords + self.forward *100
                    vec_to_player = np.array(player_position) - self.coords
                    vec_to_player_norm = vec_to_player / np.linalg.norm(vec_to_player)
                    station_orientation = tuple(self.orientation.as_euler('xyz'))
                    rot = R.align_vectors([vec_to_player_norm], [[0, 0, 1]])[0]
                    vector = rot.as_euler('xyz')
                    
                    speed=random.uniform(1.5,2.5)
                    type="Viper"
                    ECM=random.random() < 0.04
                    aggression = 56
                    game_events.spawn_ship_from_station(spawn_coords, objectList, type, aggression=aggression, has_ecm=ECM,  speed=speed, orientation=vector)
                        
                    #print(f'Station launching cop ship #{self.spawn_extra_count}')
            else:
                if random.random() < 0.008:
                    transporters = sum(obj.name in ('Transporter', 'Shuttle') for obj in objectList)
                    if transporters==0:
                        spawn_coords =self.coords + self.forward *100

                        
                        launch_angle= random.uniform(-np.pi/4,np.pi/4)
                        rot_90_z = R.from_euler('z', launch_angle)
                        station_orientation = rot_90_z * self.orientation
                        station_orientation = tuple(station_orientation.as_euler('xyz'))
                        speed=random.uniform(0.3,0.7)
                        type=random.choice(['Shuttle','Transporter'])
                        game_events.spawn_ship_from_station(spawn_coords, objectList, type, aggression=0, has_ecm=False,  speed=speed, orientation=station_orientation)
                        #print('Station launching shuttle or transporter')
        elif self.name =='Rock hermit':
            if random.random() < 0.22:
                if self.spawn_extra_count< game_constants.MAX_ROCK_HERMIT_SPAWNS:
                    ships = ['Sidewinder', 'Mamba', 'Krait', 'Adder', 'Gecko']
                    ship = random.choice(ships)
                    spawn_coords =self.coords + self.forward *30
                    aggression = random.randint(32,63)
                    ECM = False
                    docking = False
                    game_events.spawn_trader_or_hunter(spawn_coords, objectList,ship, aggression, ECM, docking)      
                    #print('Rock hermit spawing Sidewinder, Mamba, Krait, Adder or Gecko')
                    self.spawn_extra_count +=1
        elif self.name == "Thargon":
            num_thargoids = sum(obj.name == "Thargoid" for obj in objectList)
            #if there are no Thargoid motherships then disable Thargon
            if num_thargoids ==0:
                self.aggression=0
                self.ECM=False
                self.is_hostile=False
                self.forward_speed=0.2
        elif self.is_a_trader:
            #80% of time just carry on, 20% of time scan player and if 
            if random.random() > 0.80:
                if player.FIST >=40:
                    self.aggression=random.randint(32,63)
                    self.is_hostile=True
        elif self.is_a_bounty_hunter and not self.is_hostile:
            if player.FIST >=40:
                    self.aggression=random.randint(32,63)
                    self.is_hostile=True
        elif self.is_a_pirate and global_flags.is_in_space_station_zone:
            #stop pirates attacking with space station zone
            self.aggression=0
            self.is_hostile=False

        if self.type =='ship':
            #get orientation vectors
            forward=self.forward
            right=self.right
            up=self.up    

        #main code for mananaging behaviour of objects
            
            if self.is_hostile:

                
                if self.just_been_hit:
                    self.just_been_hit = False

                    # set probability of turning away based on aggression level, with lower aggression ships more likely to turn away and higher aggression ships more likely to keep attacking
                    if self.aggression < 20:
                            turn_away_chance = 1.0
                    elif self.aggression >= 63:
                        turn_away_chance = 0.20
                    else:
                        # Linear interpolation between 1.0 (at 20) and 0.25 (at 63)
                        turn_away_chance = 1.0 - ((self.aggression - 20) / (63 - 20)) * (1.0 - 0.20)
                    
                    evade_chance = turn_away_chance *2   
                        
                    
                    #if already turning and hit, take evasive action
                    if self.AI_state == AI_state.AI_TURNING:
                        if random.random() < evade_chance:
                            self.AI_state = AI_state.AI_EVADING
                            self.evade_frame_start = self.frame_count
                    else:   
                        #turn if random <  probability
                        if random.random() < turn_away_chance:
                            self.AI_state = AI_state.AI_TURNING
                            self.turning_away_frame_start = self.frame_count
                    
                                    


                if self.name =='Anaconda':
                    if random.random()<0.22 and self.spawn_extra_count==0:
                        random_ship = random.random()
                        if random_ship<0.61:
                            ship_type = "Worm"
                        else:
                            ship_type = "Sidewinder"

                        spawn_coords =self.coords + forward *50
                        aggression = random.randint(32,63)
                        ECM = False
                        docking = False
                        game_events.spawn_trader_or_hunter(spawn_coords, objectList,ship_type, aggression, ECM, docking)
                        self.spawn_extra_count +=1      

                
                #decide whether to fire weapons or launch escape pod
                #fire laser
                if self.energy >0.5 * self.max_energy:
                    if self.distance_to_player < game_constants.LASER_MAX_DISTANCE   :
                        if not self.draw_laser and self.laser_power >0:
                            angle_deg= self.get_angle_to_player(player_position)
                            if angle_deg <= game_constants.LASER_ROUGH_ANGLE:
                                self.fire_laser=True

                #launch missile or Thargon
                elif self.energy >= 0.125 * self.max_energy:
                    if self.distance_to_player < game_constants.MAX_MISSILE_TARGET_DISTANCE :
                        if (self.missile_count >0
                            and random.randint(0,31) < self.missile_count
                            and not global_flags.ecm_active):
                            
                            self.missile_count -=1
                            
                            if self.name == "Thargoid":
                                thargon_coords = self.coords + np.random.uniform(20, 30, 3)
                                orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
                                rotation_inc = (0.00,0.0,0.0)
                                forward_speed = random.uniform(2.0, 2.5)
                                thargon = game_events.addShip("Thargon", thargon_coords, rotation_inc=rotation_inc, orientation=orientation, forward_speed=forward_speed)
                                thargon.has_ecm = False
                                thargon.aggression=63
                                objectList.append(thargon)
                            else:
                                game_events.launch_enemy_missile(self.coords, self.orientation.apply([0, 0, 1]),objectList,self.orientation)

                #launchescape pod
                elif self.energy < 0.125 * self.max_energy:
                    if random.random() < 0.1 and self.has_escape_pod:
                        #print(f"{self.name} launching escape pod")
                        spawn_coords = self.coords + up * 20
                        game_events.spawn_escape_pod(spawn_coords, objectList)
                        self.has_escape_pod = False  # Only one escape pod
                        self.is_hostile = False
                        self.aggression = 0
                        self.has_ecm = False
                        self.is_a_bounty_hunter = False
                        self.is_a_pirate = False
                        self.is_a_trader = False
                        self.is_docking = False
                        self.is_drifting = True                 

                #check distance and AI mode
                long_distance_decision = self.aggression * 2 + int(self.has_ecm)
                
                #if alreday turning or evading carry-on
                if self.AI_state == AI_state.AI_TURNING or self.AI_state == AI_state.AI_EVADING: 
                    return
            

                elif self.distance_to_player < game_constants.MIN_DISTANCE_TO_PLAYER:
                    self.AI_state = AI_state.AI_TURNING
                    self.turning_away_frame_start = self.frame_count
                elif random.randint(0,170)< long_distance_decision:
                    if self.distance_to_player > game_constants.MIN_DISTANCE_TO_PLAYER *3.0:
                        self.AI_state = AI_state.AI_ATTACKING
                    
                
                print(self.name, self.AI_state, self.frame_count, self.turning_away_frame_start, self.evade_frame_start     )

            elif not self.is_drifting:
                #point ship at planet and fly towards it
                planet_coords = planet_and_star.objects['planet'].position
                vector_to_planet = planet_coords - self.coords
                vector_to_planet /= np.linalg.norm(vector_to_planet)
                forward_norm = forward / np.linalg.norm(forward)
                dot = np.clip(np.dot(forward_norm, vector_to_planet), -1.0, 1.0)
                angle_deg = np.degrees(np.arccos(dot))
                if angle_deg >= 10:
                    #not aligned with planet, so pitch or roll to align   
                    right_component = np.dot(vector_to_planet, right)
                    if abs(right_component) > 0.1:
                            roll_direction = np.sign(right_component)
                            self.rotation_inc = np.array([0.0, 0.0, roll_direction * 0.005])
                    else:
                        up_component = np.dot(vector_to_planet, up)
                        pitch_direction = -np.sign(up_component)
                        self.rotation_inc = np.array([pitch_direction * 0.005, 0.0, 0.0])
                else:
                    #aligned with planet, so just carry on forward
                    self.rotation_inc = np.array([0.0, 0.0, 0.0])
                    # Calculate distance to planet, if ship has reachjed surface clean-up
                    planet_coords = planet_and_star.objects['planet'].position
                    distance_to_planet = np.linalg.norm(self.coords - planet_coords)
                    if distance_to_planet < 24567:
                        self.ready_for_removal = True
                        game_events.check_missile_targets(self,objectList)

    def turning_away_from_player(self,player_position):
        #self.forward_speed = min(self.maximum_speed ,1.1*self.forward_speed)
        self.acceleration=0.05
       
        vec_to_player = np.array(player_position) - self.coords
        vec_to_player_norm = vec_to_player / np.linalg.norm(vec_to_player)
        forward_norm = self.forward / np.linalg.norm(self.forward)
        dot = np.clip(np.dot(forward_norm, vec_to_player_norm), -1.0, 1.0)
        angle_deg = np.degrees(np.arccos(dot))
        angle_deg = self.get_angle_to_player(player_position)

        if abs(angle_deg) < 95:
            pitch_step = 0.01  # radians (~1 degree)
            rot_up = R.from_rotvec(self.right * pitch_step) * self.orientation
            # Simulate pitching up
            forward_up = rot_up.apply([0, 0, 1])
            angle_up = np.degrees(np.arccos(np.clip(np.dot(forward_up / np.linalg.norm(forward_up), vec_to_player_norm), -1.0, 1.0)))

            # Simulate pitching down
            rot_down = R.from_rotvec(self.right * -pitch_step) * self.orientation
            forward_down = rot_down.apply([0, 0, 1])
            angle_down = np.degrees(np.arccos(np.clip(np.dot(forward_down / np.linalg.norm(forward_down), vec_to_player_norm), -1.0, 1.0)))

            # Choose the direction that increases the angle more
            if angle_up > angle_down:
                pitch_direction = 1.0  # Pitch up
            else:
                pitch_direction = -1.0  # Pitch down

            # Apply pitch increment in the chosen direction
            self.rotation_inc = np.array([pitch_direction * pitch_step, 0.0, 0.0])

            self.rotation_inc = np.array([pitch_direction * pitch_step, 0.0, 0.0])
        else:
            self.rotation_inc = np.array([0.0, 0.0, 0.0])    
            self.AI_state = AI_state.AI_IDLE

    def turning_towards_player(self,player_position):
        self.acceleration=-0.1
        self.forward_speed = max(self.forward_speed, self.maximum_speed*0.4)
        vec_to_player = np.array(player_position) - self.coords
        vec_to_player_norm = vec_to_player / np.linalg.norm(vec_to_player)
        forward_norm = self.forward / np.linalg.norm(self.forward)
        dot = np.clip(np.dot(forward_norm, vec_to_player_norm), -1.0, 1.0)
        angle_deg = np.degrees(np.arccos(dot))
        angle_deg = self.get_angle_to_player(player_position)
        
        align_threshold = 1.0  # degrees
        if angle_deg > align_threshold:
            
            # --- ROLL: Try both directions ---
            roll_step = 0.01
            rot_roll_plus = R.from_rotvec(self.forward * roll_step) * self.orientation
            right_plus = rot_roll_plus.apply([1, 0, 0])
            dot_plus = np.dot(right_plus, vec_to_player_norm)
            rot_roll_minus = R.from_rotvec(self.forward * -roll_step) * self.orientation
            right_minus = rot_roll_minus.apply([1, 0, 0])
            dot_minus = np.dot(right_minus, vec_to_player_norm)
            if abs(dot_plus) < abs(dot_minus):
                roll_direction = 1.0
            else:
                roll_direction = -1.0

            # --- PITCH: Try both directions ---
            pitch_step = 0.01
            rot_pitch_plus = R.from_rotvec(self.right * pitch_step) * self.orientation
            forward_pitch_plus = rot_pitch_plus.apply([0, 0, 1])
            angle_pitch_plus = np.degrees(np.arccos(np.clip(np.dot(forward_pitch_plus / np.linalg.norm(forward_pitch_plus), vec_to_player_norm), -1.0, 1.0)))
            rot_pitch_minus = R.from_rotvec(self.right * -pitch_step) * self.orientation
            forward_pitch_minus = rot_pitch_minus.apply([0, 0, 1])
            angle_pitch_minus = np.degrees(np.arccos(np.clip(np.dot(forward_pitch_minus / np.linalg.norm(forward_pitch_minus), vec_to_player_norm), -1.0, 1.0)))
            if angle_pitch_plus < angle_pitch_minus:
                pitch_direction = 1.0
            else:
                pitch_direction = -1.0

            # Combine pitch and roll for best alignment
            self.rotation_inc = np.array([
                pitch_direction * pitch_step,
                0.0,
                roll_direction * roll_step
            ])
        else:
            self.rotation_inc = np.array([0.0, 0.0, 0.0])
            self.AI_state = AI_state.AI_IDLE
            self.acceleration=0.05  # Accelerate towards player when aligned             


    def evade(self, player_position, player_right):
        #first time this is called
        if self.frame_count==self.evade_frame_start:
            randompitch_direction = random.choice([-1.0, 1.0])
            randomroll_direction = random.choice([-1.0, 1.0])
            self.rotation_inc = np.array([randompitch_direction * 0.01, 0.0, randomroll_direction * 0.01])
            random_acceleration = random.uniform(-0.05, 0.05)
            self.acceleration = random_acceleration
        #after 60 frames of evading, return to attacking
        elif self.frame_count >= self.evade_frame_start + 60:
            self.AI_state = AI_state.AI_IDLE

            return


    def dock_with_station(self,objectList):
        station  = next((obj for obj in objectList if getattr(obj, 'type') == 'station'))
        port = station.get_docking_port_position()
        turning_point = approach_point = port+ station.forward * 1000 
        approach_point = port + station.forward * 300
        docking_point = port  

        if self.docking_stage ==0:
            self.docking_stage=1
        
        elif self.docking_stage ==1:
            self.docking_stage=3
            if self.docking_align_with_point(turning_point):
                self.docking_stage=2
                #print("Aligned with turning point, stage 1 complete")
        
        elif self.docking_stage ==2:
            if self.docking_fly_to_point(turning_point,speed=-1,acclereration=True):
                self.docking_stage=3
                #print("Reached turning point, stage 2 complete")

        elif self.docking_stage ==3:     
            if self.docking_align_with_point(approach_point):
                self.docking_stage=4
                #print("Aligned with approach point, stage 3 complete")

        elif self.docking_stage ==4:
            if self.docking_fly_to_point(approach_point,speed=-1,acclereration=True):
                self.docking_stage=5
                #print("Reached approach point, stage 4 complete")
            
        elif self.docking_stage ==5:
            if self.docking_align_with_point(docking_point):
                self.docking_stage=6
                #print("Aligned with docking port, stage 5 complete")

        elif self.docking_stage == 6:
            # Stage 6: Roll ship until up vector is 90 degrees from station's up vector
            ship_up = self.up / np.linalg.norm(self.up)
            station_up = station.up / np.linalg.norm(station.up)
            dot_up = np.clip(np.dot(ship_up, station_up), -1.0, 1.0)
            angle_up = np.arccos(dot_up)
            angle_up_deg = np.degrees(angle_up)
            #print(f"{self.name} docking: up vector angle to station: {angle_up_deg:.2f} degrees")
            target_angle = 90.0
            align_threshold = 7.0  # degrees
            if abs(angle_up_deg - target_angle) > align_threshold:
                # Determine roll direction to move angle_up_deg toward 90
                roll_axis = station.forward / np.linalg.norm(station.forward)
                # Try both roll directions and pick the one that increases angle_up_deg toward 90
                test_angle = 1.0  # test roll step
                # Roll +
                rot_plus = R.from_rotvec(roll_axis * test_angle) * self.orientation
                up_plus = rot_plus.apply([0, 1, 0])
                angle_plus = np.degrees(np.arccos(np.clip(np.dot(up_plus/np.linalg.norm(up_plus), station_up), -1.0, 1.0)))
                # Roll -
                rot_minus = R.from_rotvec(roll_axis * -test_angle) * self.orientation
                up_minus = rot_minus.apply([0, 1, 0])
                angle_minus = np.degrees(np.arccos(np.clip(np.dot(up_minus/np.linalg.norm(up_minus), station_up), -1.0, 1.0)))
                # Choose direction that brings us closer to 90
                if abs(angle_plus - target_angle) < abs(angle_minus - target_angle):
                    roll_direction = -1.0
                else:
                    roll_direction = +1.0
                self.rotation_inc = np.array([0.0, 0.0, roll_direction * 0.05])
                #print(f"{self.name} rolling to achieve 90 degree up vector to station (dir {roll_direction:+.0f})")
            else:
                #print(f"{self.name} up vector is 90 degrees from station, proceeding to stage 7")
                self.docking_stage = 7
    
        elif self.docking_stage == 7:
            if self.docking_fly_to_point(docking_point,self.maximum_speed):
                #print("Docked with station, stage 7 complete")
                self.is_docking=False
                self.ready_for_removal=True
            else:    
                self.rotation_inc = np.array([0.0, 0.0, -station.rotation_inc[2]])
   

    def docking_align_with_point(self,point,angle=4):
        vector_to_point = point - self.coords
        vector_to_point_norm = vector_to_point / np.linalg.norm(vector_to_point)
        dot = np.dot(self.forward, vector_to_point_norm)
        dot = np.clip(dot, -1.0, 1.0)
        angle_deg = np.degrees(np.arccos(dot))
        #print(f"{self.name} docking:angle to point: {angle_deg:.2f} degrees")
        if self.slow_while_turning:
            self.forward_speed = self.minimum_speed/3
        else:
            self.forward_speed = self.maximum_speed *0.75
        
        if angle_deg <= angle:
            self.rotation_inc = np.array([0.0, 0.0, 0.0])
            self.prev_distance_to_point = np.linalg.norm(self.coords - point)
            return True
        else:
          
            right_component = np.dot(vector_to_point_norm, self.right)
            if abs(right_component) > 0.1:
                    #print(f"{self.name} Rolling to align with point")
                    roll_direction = np.sign(right_component)
                    self.rotation_inc = np.array([0.0, 0.0, roll_direction * 0.01])
                    #print(f"{self.name} Rolling to align with point")
            elif abs(right_component) > 0.05:  # Close to aligned, use best roll direction
                test_angle = 0.005  # Small roll step
                # Try rolling +test_angle
                rot_plus = R.from_rotvec(self.forward * test_angle) * self.orientation
                right_plus = rot_plus.apply([1, 0, 0])
                right_component_plus = np.dot(vector_to_point_norm, right_plus)
                # Try rolling -test_angle
                rot_minus = R.from_rotvec(self.forward * -test_angle) * self.orientation
                right_minus = rot_minus.apply([1, 0, 0])
                right_component_minus = np.dot(vector_to_point_norm, right_minus)
                # Choose direction that reduces misalignment
                if abs(right_component_plus) < abs(right_component_minus):
                    roll_direction = 1.0
                else:
                    roll_direction = -1.0
                self.rotation_inc = np.array([0.0, 0.0, roll_direction * test_angle])
            else:
                #print(f"{self.name} Pitching to align with point")
                up_component = np.dot(vector_to_point_norm, self.up)
                pitch_direction = -np.sign(up_component)
                if angle_deg <angle*2:
                    self.rotation_inc = np.array([pitch_direction * 0.005, 0.0, 0.0])
                else:
                    self.rotation_inc = np.array([pitch_direction * 0.01, 0.0, 0.0])                        

            return False      

    def docking_fly_to_point(self,point,speed,acclereration=False,angle=4):
        distance_to_point = np.linalg.norm(self.coords - point)
        vector_to_point = point - self.coords
        vector_to_point_norm = vector_to_point / np.linalg.norm(vector_to_point)
        dot = np.dot(self.forward, vector_to_point_norm)
        dot = np.clip(dot, -1.0, 1.0)
        angle_deg = np.degrees(np.arccos(dot))
        
        if angle_deg > angle*1.5 and distance_to_point >1000:
            if self.docking_stage!=7:
                self.docking_stage-=1
            else:
                self.docking_stage=5    
            self.slow_while_turning = False
            return False


        if speed==-1:
            speed = self.maximum_speed

        if int(distance_to_point)> int(self.prev_distance_to_point)+0.1 or distance_to_point<5.0:
            self.slow_while_turning = True
            return True

        else:
            self.prev_distance_to_point = distance_to_point
            if distance_to_point < 200:
                if acclereration:
                    self.acceleration = -0.02
                else:
                    self.forward_speed = speed*0.75
            else:
                if acclereration:
                    self.acceleration = 0.02
                else:
                    self.forward_speed = speed    
        
            #print(f"{self.name} flying to point {point}, distance {distance_to_point:.2f},angle {angle_deg:.2f}, speed {self.forward_speed:.2f}")
        
        return False                         




class Missile(Object):
    """Missile subclass with special initialization for player-launched missiles."""

    def __init__(self, ship_dictionary, launch_position, player_orientation, locked_on_target, forward_speed=0.1,enemy=False):
        self.locked_on_target = locked_on_target
        self.enemy = enemy
        # Initialize parent Object with default orientation
        super().__init__(
            ship_dictionary,
            coords=launch_position,
            coords_inc=(0, 0, 0),
            initial_rotation=(0, 0, 0),
            rotation_inc=(0, 0, 0),
            orientation=(0, 0, 0),
            forward_speed=forward_speed
        )
        
        #override visibility threshold
        self.view_threshold = self.size * VIEW_THRESHOLD_FACTOR * 2  # Missiles can be seen from further away        

        # Override orientation with player's orientation
        self.orientation = player_orientation
        self.forward = self.orientation.apply([0, 0, 1])
        self.right = self.orientation.apply([1, 0, 0])
        self.up = self.orientation.apply([0, 1, 0])
        
        # Apply rotation to the mesh nodes so it visually points the right way
        rot_matrix = player_orientation.as_matrix()
        nodes_centered = self.nodes_world - self.center
        nodes_rotated = nodes_centered[:, :3] @ rot_matrix.T
        self.nodes_world[:, :3] = nodes_rotated + self.center[:3]


    def update(self,player_position,player_right,movement_forward,objectList,particleList,main_loop_counter,planet_and_star=None):
        
        # Missile homing logic
        
        if global_flags.ecm_active and global_flags.ecm_counter>global_flags.ecm_counter/2:
            msg = get_text('self_ECM') if not self.enemy else get_text('enemy_ECM')
            status.add_message(msg, duration=2, type=0)
            if not self.enemy:
                self.locked_on_target.locked_on_missile_index =-1
            game_events.handle_explosion(self, objectList, particleList,player_position,player_right)
            return
        else:
            if not self.enemy and self.locked_on_target.has_ecm:
                if random.random()<0.03 or self.locked_on_target.type=='station':
                    distance = np.linalg.norm(self.coords - self.locked_on_target.coords)
                    if distance < game_constants.ECM_EFFECTIVE_RANGE:
                            global_flags.ecm_active = True
                            global_flags.ecm_counter = 0
                            global_flags.ecm_is_enemy = True
                            return
                

            if self.enemy:
                target_coords = player_position
            else:
                target_coords = self.locked_on_target.coords

            # Calculate direction to target
            direction_to_target = target_coords - self.coords
            distance_to_target = np.linalg.norm(direction_to_target)
            
            # Check if missile hit another object
            #if true, then remove missile and target, create explosiions and add kill points
            if not self.enemy and distance_to_target < self.locked_on_target.collision_radius :
                game_events.handle_explosion(self,objectList,particleList,player_position,player_right)
                game_events.check_missile_targets(self.locked_on_target,objectList)
                if self.locked_on_target.type !='station':
                    self.locked_on_target.ready_for_removal = True
                    game_events.create_explosion(self.locked_on_target,objectList,particleList,energy_bomb=False)
                    game_events.process_kill(self.locked_on_target,objectList)
                    
                    if self.locked_on_target.is_innocent and global_flags.is_in_space_station_zone:
                            global_flags.station_is_hostile = True
                    
                    sound_manager.play_3d_sound(
                        SoundType.EXPLOSION,
                        self.locked_on_target.coords,
                        player_position,
                        player_right,
                        self.locked_on_target.distance_to_player
                    )                     
                else:
                    global_flags.station_is_hostile = True
                    self.locked_on_target.locked_on_missile_index =-1    

                #check if player is within blast radius and apply damage
                if self.distance_to_player < game_constants.MISSILE_BLAST_RADIUS:
                    game_events.process_damage(self.coords, player_position, movement_forward, game_constants.MISSILE_BLAST_DAMAGE,main_loop_counter)    
                    status.add_message(get_text('too_close_to_blast'), duration=2, type=0)
            else:
                # Normalize direction to target
                direction_normalized = direction_to_target / distance_to_target
                
                # Calculate desired orientation (align with target direction)
                # Get the rotation that would align [0,0,1] with direction_to_target
                current_forward = self.forward
                
                # Calculate angle between current forward and target direction
                dot_product = np.dot(current_forward, direction_normalized)
                # Clamp to avoid numerical issues with arccos
                dot_product = np.clip(dot_product, -1.0, 1.0)
                angle_to_target = np.arccos(dot_product)
                
                # Only adjust if angle is significant (> 0.1 degrees)
                if angle_to_target > np.deg2rad(0.1):
                    # Calculate rotation axis (perpendicular to both vectors)
                    rotation_axis = np.cross(current_forward, direction_normalized)
                    rotation_axis_length = np.linalg.norm(rotation_axis)
                    
                    if rotation_axis_length > 1e-6:  # Avoid division by zero
                        rotation_axis = rotation_axis / rotation_axis_length

                        # Limit rotation to 2 degrees per frame
                        max_rotation = np.deg2rad(2)
                        actual_rotation = min(angle_to_target, max_rotation)
                        
                        # Create rotation and apply it
                        rotation = R.from_rotvec(rotation_axis * actual_rotation)
                        self.orientation = rotation * self.orientation
                        
                        # Update direction vectors
                        self.forward = self.orientation.apply([0, 0, 1])
                        self.right = self.orientation.apply([1, 0, 0])
                        self.up = self.orientation.apply([0, 1, 0])
                        
                        # Apply rotation to mesh nodes
                        rot_matrix = rotation.as_matrix()
                        nodes_centered = self.nodes_world - self.center
                        nodes_rotated = nodes_centered[:, :3] @ rot_matrix.T
                        self.nodes_world[:, :3] = nodes_rotated + self.center[:3]
        
        # Call parent Object's update method for movement
        super().update(player_position,player_right,movement_forward,objectList,particleList,main_loop_counter)
       
