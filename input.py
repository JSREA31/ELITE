import time
import pygame
import numpy as np
from scipy.spatial.transform import Rotation as R
import object
import wireframes
from status import global_flags,player,ship_data, MissileStatus,MissionStatus
import status
import game_events
from sounds import sound_manager, SoundType
from text_strings import get_text

from enum import Enum, auto

class DockingPhase(Enum):
    INACTIVE = 0
    BACKING_AWAY = auto()
    TURNING_AROUND = auto()
    TURNING_TO_FACE = auto()
    CHECK_ACCESS_TO_PORTAL = auto()
    MOVING_TO_PORTAL_ROLLING = auto()
    PORTAL_NOT_VISIBLE = auto()
    ROLLING_TO_WAYPOINT = auto()
    PITCHING_TO_WAYPOINT = auto()
    MOVING_TO_WAYPOINT = auto()
    MOVING_TO_PORTAL_PITCHING = auto()
    MOVING_TO_PORTAL_FLYING = auto()
    FINAL_ROLL = auto()
    FINAL_PITCH = auto()
    FINAL_APPROACH = auto()

class InputHandler:
    def __init__(self, max_move_speed=4.0, rotate_speed=2):
      
        self.docking_music_playing = False
        # Orientation as scipy Rotation objects
        self.look_orientation = R.from_rotvec([0, 0, 0])  # Separate orientation for rendering
        self.movement_orientation = R.from_rotvec([0, 0, 0])  # Original orientation for movement

        # Joystick initialization
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Joystick detected: {self.joystick.get_name()}")
        else:
            print("No joystick detected.")

        #movement variables
        
        self.rotate_speed = rotate_speed

        # Movement variables with momentum
        self.current_speed = 0.0
        self.max_speed = max_move_speed  # Maximum speed is 4x base speed
        self.acceleration = max_move_speed / 80  # How quickly speed changes

        self.current_pitch_speed = 0.0
        self.max_pitch_speed = rotate_speed * 1.0  # Maximum pitch rate
        self.pitch_acceleration = rotate_speed / 20  # How quickly pitch rate changes
        self.pitch_deceleration = rotate_speed / 20  # Natural damping rate
        self.pitch_direction = 0  # Track pitch direction for damping

        self.current_roll_speed = 0.0
        self.max_roll_speed = rotate_speed * 1.0  # Maximum roll rate
        self.roll_acceleration = rotate_speed / 20  # How quickly roll rate changes
        self.roll_deceleration = rotate_speed / 20  # Natural damping rate
        self.roll_direction = 0  # Track roll direction for damping

        # Docking computer variables
        self.docking_text = get_text("docking_inactive")
        self.docking_move_speed = max_move_speed / 2
        self.waypoint = None
        self.docking_target = None
        self.docking_active = False
        self.minimum_docking_distance = 800
        self.turning_point_distance = 400
        self.waypoint_distance = 1000
        self.docking_stop_distance = 30
        self.docking_phase = DockingPhase.INACTIVE

        #keyboard input for info screens
        self.just_selected_page = False
        self.market_index=0
        self.market_input = ""
        self.market_check = False
        self.get_laser_location = False
        self.laser_to_equip = ""
        self.overwrite_check = False
        self.find_system=""

        #used for finding system in galactic chart
        self.find_system_input = ""
        self.find_system = False
        

    def set_docking_target(self, target_object, distance=5):
        """Set docking computer to fly towards target object."""
        self.docking_active = True
        self.docking_text = get_text("docking_active")
        self.docking_target = {
            'object': target_object,
            'distance': distance
        }
        # Store target object directly
        self.target_obj = target_object
        
        self.docking_phase = DockingPhase.INACTIVE

        # Start docking music if not already playing
        if not self.docking_music_playing:
            sound_manager.play_music(SoundType.DOCKING_MUSIC, loops=-1)  # Loop until stopped
            self.docking_music_playing = True
           
                                                 
    def handle_events(self, events, player_position, forward, objectList, planet_and_star, movement_orientation=None,main_loop_counter=0):
        

        """Handle discrete events (keydown/keyup)."""
        for event in events:
            if event.type == pygame.QUIT:
                return False  # Signal to quit
            
            # Add Cmd+Q (Meta+Q) quit support for macOS
            if (
                event.type == pygame.KEYDOWN and
                event.key == pygame.K_q and
                (event.mod & pygame.KMOD_META)
            ):
                return False  # Signal to quit on Cmd+Q


            if global_flags.is_flying and event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                global_flags.is_paused = not global_flags.is_paused

            if global_flags.is_paused:
                return True


            if event.type == pygame.KEYDOWN and status.global_flags.is_title_screen:
                if player.info_screen_page==0:
                    if event.key==pygame.K_y:
                        player.info_screen_page=11
                        sound_manager.stop_music()
                    
                    elif event.key==pygame.K_n:
                        global_flags.reset_game=True
                        sound_manager.stop_music()
                    elif event.key==pygame.K_SPACE:
                        #DEBUG CODE TO HELP WITH WIREFRAME NODE ORDER
                        global_flags.next_face = True

                elif player.info_screen_page==11:
                    self.handle_info_screen_controls([event])
                return True
            elif event.type == pygame.KEYDOWN and status.global_flags.is_game_over:
                #stop movment and return to title screen
                self.docking_active = False
                self.docking_text = get_text("docking_inactive")
                self.pitch_direction = 0
                self.roll_direction = 0
                self.current_speed = 0
                #objectList.clear()
                global_flags.game_state=global_flags.STATE_TITLE_SCREEN
                return True


            # Info screen key handling (1-9)
            if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9 and global_flags.accept_input:
                if player.info_screen_page != 1 and player.info_screen_page != 2 and player.info_screen_page != 3 and player.info_screen_page != 10:  # stops input interfering with buy/sell cargo page input
                    player.info_screen_page = event.key - pygame.K_0
                    
                    if not global_flags.is_docked and player.info_screen_page <4:
                        sound_manager.play(SoundType.ERROR)
                        player.info_screen_page = 0  # Can't access these pages unless docked
                    else:
                        sound_manager.play(SoundType.ON)    
                    if player.info_screen_page == 1 or player.info_screen_page == 2 or player.info_screen_page == 3:
                        self.just_selected_page = True
                        self.market_input = ""  # Clear input when entering market page
                        self.market_index = 0  # Reset index when entering market page
                        self.market_check = False  # Reset check flag
                    elif player.info_screen_page == 4:
                        self.just_selected_page = True  #
                        self.find_system_input = ""  # Clear input when entering find system page
                        self.find_system = False  # Reset find system flag
                    elif player.info_screen_page == 6:    
                        global_flags.message_refresh = True  # Force message refresh when opening info screen

            # Escape closes info screen
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and global_flags.accept_input:
                sound_manager.play(SoundType.OFF)
                if global_flags.is_docked:
                    player.info_screen_page = 6
                else:
                    player.info_screen_page = 0


            if global_flags.is_flying and player.info_screen_page==0:
                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_j and self.docking_phase == DockingPhase.INACTIVE:
                        # --- Short Range Jump Checks ---
                        
                        #check to see if ships are in radar range
                        for obj in objectList:
                            if obj.type == 'ship' and obj.distance_to_player <status.game_constants.RADAR_RANGE:
                                status.add_message(get_text("abort_jump"), duration=2, type=0)
                                sound_manager.play(SoundType.ERROR)
                                return True

                        # 1. No station within 4000 units (use global_flags.station_distance)
                        if global_flags.station_distance < 4000:
                            status.add_message(get_text("station_too_close"), duration=2, type=0)
                            sound_manager.play(SoundType.ERROR)
                            return True

                        if not game_events.check_jump_end_point(player_position, forward,planet_and_star):
                            return True

                        game_events.untarget_missiles()
                        global_flags.game_state = global_flags.STATE_SHORT_RANGE_JUMPING
                        global_flags.frame_start = main_loop_counter
                    elif event.key == pygame.K_x:
                        #radar zoom toggle
                        global_flags.radar_zoom_index += global_flags.radar_zoom_direction
                        if global_flags.radar_zoom_index >= len(global_flags.radar_zoom_values) or global_flags.radar_zoom_index < 0:
                            global_flags.radar_zoom_direction *= -1
                            global_flags.radar_zoom_index += global_flags.radar_zoom_direction *2
                        

                    elif event.key == pygame.K_c:  # 'C' for docking computer on
                        if not self.docking_active and global_flags.is_in_space_station_zone:
                            if not ship_data.docking_computer:
                                status.add_message(get_text("no_computer"), duration=2, type=0)
                                sound_manager.play(SoundType.OFF)
                                game_events.untarget_missiles()
                            else:       
                                # Target the space station
                                station = next((obj for obj in objectList if obj.type == 'station'), None)
                                if station is not None:
                                    self.set_docking_target(station, distance=20)
                                    self.current_speed = 0
                                    self.current_pitch_speed = 0
                                    self.current_roll_speed = 0
                                    sound_manager.play(SoundType.ON)
                                else:
                                    self.docking_active = False
                    elif event.key == pygame.K_e: #E for ECM
                        if not ship_data.ECM_System:
                            status.add_message(get_text("no_ecm"), duration=2, type=0)
                            sound_manager.play(SoundType.OFF)
                        elif not global_flags.ecm_active:
                            global_flags.ecm_active = True
                            global_flags.ecm_counter = 0
                            global_flags.ecm_is_enemy = False
                            status.add_message(get_text("ecm_activated"), duration=2, type=0)
                            sound_manager.play(SoundType.ON)

                    elif event.key == pygame.K_p: # 'P' to turn off docking computer
                        if self.docking_active:
                            self.docking_active = False
                            self.pitch_direction = 0
                            self.roll_direction = 0
                            self.current_speed = 0
                            self.docking_phase = DockingPhase.INACTIVE
                            self.docking_text = get_text("docking_inactive")
                            sound_manager.play(SoundType.OFF)
                            # Stop docking music only when docking just became inactive
                            if self.docking_music_playing:
                                sound_manager.stop_music()
                                self.docking_music_playing = False
                    
                    elif event.key == pygame.K_t: # 'T' to turn on missile targeting
                        if not global_flags.targeting_missile:
                            if any(status == MissileStatus.PRESENT for status in ship_data.missile_status):
                                global_flags.targeting_missile = True
                                status.add_message(get_text("targeting_on"), duration=2, type=0)
                                sound_manager.play(SoundType.ON)
                                sound_manager.play(SoundType.TARGETING, loops = -1, volume=0.2)

                                for i in reversed(range(len(ship_data.missile_status))):
                                    if ship_data.missile_status[i] == MissileStatus.PRESENT:
                                            ship_data.missile_status[i] = MissileStatus.TARGETING
                                            break
                            else:
                                sound_manager.play(SoundType.OFF)
                                status.add_message(get_text("no_missiles"), duration=2, type=0)        

                    elif event.key == pygame.K_u: # 'U' to turn off missile targeting
                        if global_flags.targeting_missile:
                            global_flags.targeting_missile = False
                            status.add_message(get_text("targeting_off"), duration=2, type=0)
                            if sound_manager.is_playing(SoundType.TARGETING):
                                sound_manager.stop(SoundType.TARGETING) 
                            if sound_manager.is_playing(SoundType.LOCKED_ON):
                                sound_manager.stop(SoundType.LOCKED_ON)
                            sound_manager.play(SoundType.OFF)
                            
                            for i in range(len(ship_data.missile_status)):
                                if ship_data.missile_status[i] in (MissileStatus.TARGETING, MissileStatus.LOCKED_ON):
                                    if ship_data.missile_status[i] == MissileStatus.LOCKED_ON:
                                        for obj in objectList:
                                            if obj.locked_on_missile_index == i:
                                                obj.locked_on_missile_index = -1
                                    ship_data.missile_status[i] = MissileStatus.PRESENT
                                    global_flags.locked_on_target = None
                                    global_flags.locked_on_frame_count = 0
                                    
                                    break
                    elif event.key == pygame.K_m: # 'M' to launch missile
                        
                        for i in range(len(ship_data.missile_status)):
                            if ship_data.missile_status[i] == MissileStatus.LOCKED_ON:
                                ship_data.missile_status[i] = MissileStatus.NOT_PRESENT
                                sound_manager.play(SoundType.ON)
                                status.add_message(f"{get_text('missile')} {i} {get_text('launched')}", duration=2, type=0)
                                if sound_manager.is_playing(SoundType.LOCKED_ON):
                                    sound_manager.stop(SoundType.LOCKED_ON)
                                # Reset targeting flags
                                global_flags.targeting_missile = False
                                game_events.launch_missile(player_position, forward, i, objectList, movement_orientation,global_flags.locked_on_target)
                                break
                    elif event.key == pygame.K_ESCAPE and (pygame.key.get_mods() & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT)):  
                        if ship_data.escape_capsule and not global_flags.is_in_space_station_zone:
                            global_flags.game_state = global_flags.ESCAPE_POD_LAUNCHED
                            ship_data.escape_capsule = False
                            global_flags.frame_start = main_loop_counter
                            self.pitch_direction = 0
                            self.roll_direction = 0
                            self.current_speed = 0
                            sound_manager.play(SoundType.ESCAPE_POD_LAUNCH)  
                            game_events.handle_escape_pod()
                            status.add_message(get_text("escape_pod"), duration=5, type=0)
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                        global_flags.is_paused = not global_flags.is_paused

                    #TO BE REMOVED - TEST CODE ONLY             
                    elif event.key == pygame.K_0:
                        # Add random cube
                        cube_pos = player_position + forward * 300
                        colors = [tuple(np.random.randint(0, 256, size=3)) for _ in wireframes.box_faces]
                        new_cube = object.Object(None,"object","cube",
                            wireframes.box_nodes,
                            wireframes.box_faces,
                            None,
                            colors,
                            scale=(10.0, 10.0, 10.0),
                            coords=cube_pos,
                            coords_inc=(0, 0, 0),
                            rotation_inc=tuple(np.random.uniform(-0.02, 0.02, size=3)),
                            
                        )
                        objectList.append(new_cube)
                    

                    elif event.key == pygame.K_TAB:
                        if ship_data.energy_bomb:
                            if not global_flags.energy_bomb_activated:
                                global_flags.energy_bomb_activated = True
                                global_flags.energy_bomb_frame_start = main_loop_counter
                                sound_manager.play(SoundType.ENERGY_BOMB)
                                status.add_message(get_text("energy_bomb"), duration=2, type=0)
                                ship_data.energy_bomb = False
                                 


                    elif event.key == pygame.K_h and (event.mod & pygame.KMOD_CTRL):
                        # Galactic hyperspace jump
                        if ship_data.galactic_hyperdrive:
                            global_flags.in_hyperspace_countdown = True
                            global_flags.in_hyperspace_countdown_start = time.time()
                            global_flags.hyperspace_is_galactic = True
                            sound_manager.play(SoundType.ON)
                            
                            status.add_message(get_text("galactic_hyperspace"), duration=10, type=1)
                        else:
                            sound_manager.play(SoundType.ERROR)
                            status.add_message(get_text("no_galactic"), duration=3, type=0)
                    
                    elif event.key == pygame.K_h:
                        if player.current_system != player.selected_system:
                            destination = player.selected_system.name
                            if ship_data.fuel_level/10 >= player.distance_to_selected:
                                global_flags.in_hyperspace_countdown = True
                                global_flags.in_hyperspace_countdown_start = time.time()
                                sound_manager.play(SoundType.ON)
                                
                                status.add_message(f"{get_text('hyperspace_countdown')} {destination}:", duration=10, type=1)
                            else:
                                sound_manager.play(SoundType.ERROR)
                                status.add_message(get_text("hyperspace_range"), duration=5, type=0)
                        else:        
                            status.add_message(get_text("no_target_selected"), duration=5, type=0)
                            sound_manager.play(SoundType.ERROR)
                                
        return True  # Continue running

    def handle_movement(self, keys, player_position, forward, right, up):
        """Handle continuous movement input."""
        global_flags.firing_laser = False
        if global_flags.is_paused:
            return player_position

        #if self.docking_active:
            #return player_position

        if player.info_screen_page==0:# Movement controls
            if keys[pygame.K_SPACE]:
                # Accelerate forward
                self.current_speed = min(self.current_speed + self.acceleration, self.max_speed)
            elif keys[pygame.K_SLASH]:
                # Decelerate
                self.current_speed = max(self.current_speed - self.acceleration, 0)
            elif keys[pygame.K_a]: #Fire Laser
                        global_flags.firing_laser = True
    
            

        # Apply forward movement based on current_speed
        if self.current_speed > 0:
            player_position += forward * self.current_speed

        

        return player_position

    def handle_rotation(self, keys, movement_orientation):
        if global_flags.is_paused:
            return movement_orientation
        
        """Handle rotation input and return new orientation. Supports joystick and keyboard with acceleration."""
        joystick_used = False
        target_pitch_speed = 0.0
        target_roll_speed = 0.0
        # Joystick axis mapping: axis 0 = roll (left/right), axis 1 = pitch (up/down)
        if self.joystick is not None:
            if self.joystick.get_button(0):
                global_flags.firing_laser = True    
            roll_axis = self.joystick.get_axis(0)  # left/right
            pitch_axis = self.joystick.get_axis(1)  # up/down
            deadzone = 0.1
            # Pitch: up is negative, down is positive
            if abs(pitch_axis) > deadzone:
                target_pitch_speed = min(abs(pitch_axis) * self.max_pitch_speed, self.max_pitch_speed)
                self.pitch_direction = 1 if pitch_axis > 0 else -1
                joystick_used = True
            else:
                target_pitch_speed = 0.0
            # Roll: left is negative, right is positive
            if abs(roll_axis) > deadzone:
                target_roll_speed = min(abs(roll_axis) * self.max_roll_speed, self.max_roll_speed)
                self.roll_direction = 1 if roll_axis < 0 else -1
                joystick_used = True
            else:
                target_roll_speed = 0.0

        if joystick_used:
            # Accelerate/decelerate pitch speed toward target
            if self.current_pitch_speed < target_pitch_speed:
                self.current_pitch_speed = min(self.current_pitch_speed + self.pitch_acceleration, target_pitch_speed)
            elif self.current_pitch_speed > target_pitch_speed:
                self.current_pitch_speed = max(self.current_pitch_speed - self.pitch_deceleration, target_pitch_speed)
            # Accelerate/decelerate roll speed toward target
            if self.current_roll_speed < target_roll_speed:
                self.current_roll_speed = min(self.current_roll_speed + self.roll_acceleration, target_roll_speed)
            elif self.current_roll_speed > target_roll_speed:
                self.current_roll_speed = max(self.current_roll_speed - self.roll_deceleration, target_roll_speed)
        else:
            # Pitch (keyboard)
            if keys[pygame.K_UP]:
                self.current_pitch_speed = min(self.current_pitch_speed + self.pitch_acceleration, self.max_pitch_speed)
                self.pitch_direction = 1
            elif keys[pygame.K_DOWN]:
                self.current_pitch_speed = min(self.current_pitch_speed + self.pitch_acceleration, self.max_pitch_speed)
                self.pitch_direction = -1
            else:
                self.current_pitch_speed = max(0, self.current_pitch_speed - self.pitch_deceleration)
            # Roll (keyboard)
            if keys[pygame.K_LEFT]:
                self.current_roll_speed = min(self.current_roll_speed + self.roll_acceleration, self.max_roll_speed)
                self.roll_direction = 1
            elif keys[pygame.K_RIGHT]:
                self.current_roll_speed = min(self.current_roll_speed + self.roll_acceleration, self.max_roll_speed)
                self.roll_direction = -1
            else:
                self.current_roll_speed = max(0, self.current_roll_speed - self.roll_deceleration)
        # Apply pitch rotation if there's any pitch speed
        if self.current_pitch_speed != 0:
            pitch_angle = -np.deg2rad(self.current_pitch_speed) * -self.pitch_direction
            movement_orientation = movement_orientation * R.from_rotvec(pitch_angle * np.array([1, 0, 0]))
        # Yaw (keyboard only)
        #if keys[pygame.K_z]:
        #    movement_orientation = movement_orientation * R.from_rotvec(-np.deg2rad(self.rotate_speed) * np.array([0, 1, 0]))
        ##if keys[pygame.K_x]:
        #    movement_orientation = movement_orientation * R.from_rotvec(np.deg2rad(self.rotate_speed) * np.array([0, 1, 0]))
        # Apply roll rotation if there's any roll speed
        if self.current_roll_speed != 0:
            roll_angle = -np.deg2rad(self.current_roll_speed) * self.roll_direction
            movement_orientation = movement_orientation * R.from_rotvec(roll_angle * np.array([0, 0, 1]))
        return movement_orientation

    def handle_look_direction(self, keys, base_orientation,direction_text):
        """Handle look direction changes without affecting movement."""
        # Look direction controls
        if keys[pygame.K_F1]:  # Num 2 - look forward
            self.look_orientation = R.from_rotvec([0, 0, 0])
            direction_text = "FRONT"
        elif keys[pygame.K_F2]:  # Num 8 - look backward
            self.look_orientation = R.from_rotvec([0, np.pi, 0])
            direction_text = "BACK"
        elif keys[pygame.K_F3]:  # Num 4 - look left
            self.look_orientation = R.from_rotvec([0, -np.pi/2, 0])
            direction_text = "RIGHT"
        elif keys[pygame.K_F4]:  # Num 6 - look right
            self.look_orientation = R.from_rotvec([0, np.pi/2, 0])
            direction_text = "LEFT"

        # Combine movement orientation with look orientation for rendering
        return base_orientation * self.look_orientation, direction_text

    def handle_info_screen_controls(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if player.info_screen_page==1 or player.info_screen_page==2:
                    if getattr(self, "just_selected_page", False):
                        self.just_selected_page = False  # Reset flag, skip this event
                        return

                    if event.key == pygame.K_DOWN:
                        self.market_index = max(0, self.market_index + 1)
                    elif event.key == pygame.K_UP:
                        self.market_index = max(0, self.market_index - 1)
                    elif pygame.K_0 <= event.key <= pygame.K_9:
                        self.market_input += str(event.key - pygame.K_0)
                    elif event.key == pygame.K_BACKSPACE:
                        self.market_input = self.market_input[:-1]  # Remove last character
                    elif event.key == pygame.K_RETURN:
                        self.market_check = True
                    return
                elif player.info_screen_page==3:
                    key_name = pygame.key.name(event.key)
                    if getattr(self, "just_selected_page", False):
                        self.just_selected_page = False  # Reset flag, skip this event
                        return
                    
                    if self.get_laser_location:
                        valid_keys = {'F', 'B', 'L', 'R'}
                        if event.key == pygame.K_RETURN:
                            self.market_check = True  
                        elif key_name.upper() in valid_keys:
                           self.market_input = key_name.upper()
                        else:
                            self.market_input = ""  # Reject input 
                    else:    
                        if len(key_name) == 1 and key_name.isnumeric():
                            self.market_input += key_name.upper()
                        elif event.key == pygame.K_BACKSPACE:
                            self.market_input = self.market_input[:-1]  # Remove last character
                        elif event.key == pygame.K_RETURN:
                            self.market_check = True

                elif player.info_screen_page==4:
                    key_name = pygame.key.name(event.key)
                    if getattr(self, "just_selected_page", False):
                        self.just_selected_page = False  # Reset flag, skip this event
                        return
                    
                    if len(key_name) == 1 and key_name.isalpha():
                        self.find_system_input += key_name.upper()
                    elif event.key == pygame.K_BACKSPACE:
                        self.find_system_input = self.find_system_input[:-1]  # Remove last character
                    elif event.key == pygame.K_RETURN:
                        self.find_system = True
                    return
                
                #hyperspace jump while viewing map
                elif player.info_screen_page==5 and global_flags.is_flying:
                    if event.key == pygame.K_h:
                        if player.current_system != player.selected_system:
                            if ship_data.fuel_level/10 >= player.distance_to_selected:
                                global_flags.in_hyperspace_countdown = True
                                global_flags.in_hyperspace_countdown_start = time.time()
                                sound_manager.play(SoundType.ON)
                                player.info_screen_page=0
                                destination = player.selected_system.name
                                status.add_message(f"{get_text('hyperspace_countdown')} {destination}:", duration=10, type=1)
                            else:
                                sound_manager.play(SoundType.ERROR)
                                status.add_message(get_text("hyperspace_range"), duration=5, type=0)
                        else:        
                            status.add_message(get_text("no_target_selected"), duration=5, type=0)
                            sound_manager.play(SoundType.ERROR)
                                
                #save commander page    
                elif player.info_screen_page==10:
                    key_name = pygame.key.name(event.key) 
                    if self.overwrite_check:
                        if len(key_name) == 1 and (key_name == "y" or key_name == "n" or key_name == "Y" or key_name == "N"):
                            self.market_input = key_name.upper()
                    else:
                        if len(key_name) == 1 and key_name.isalnum():
                            self.market_input += key_name.upper()
                        elif event.key == pygame.K_BACKSPACE:
                            self.market_input = self.market_input[:-1]  # Remove last character
                        elif event.key == pygame.K_RETURN:
                            self.market_check = True
                
                #load commander page
                elif player.info_screen_page==11:
                    key_name = pygame.key.name(event.key) 
                    if event.key == pygame.K_UP:
                        self.market_index -= 1
                    elif event.key == pygame.K_DOWN:
                        self.market_index += 1  
                    elif event.key == pygame.K_RETURN:
                        self.market_check = True
                
                #mission briefing page
                elif player.info_screen_page==12 and not global_flags.alert_on:
                    key_name = pygame.key.name(event.key) 
                    if len(key_name) == 1 and (key_name == "y" or key_name == "Y"):
                        status.add_message(get_text("mission_accepted"), duration=5, type=0)
                        player.mission_status=MissionStatus.IN_PROGRESS
                        player.info_screen_page=6
                        global_flags.accept_input = True
                        
                        #set galaxy chart to REESDICE if mission is 1
                        if player.mission_number == 1 and player.galaxy_number==0:
                            for system in player.all_systems:
                                if system.name == "REESDICE":
                                    player.galactic_xy = (system.x, system.y)
                                    player.selected_system = system
                                    break 
                        elif player.mission_number == 2 and player.galaxy_number==2:
                            for system in player.all_systems:
                                if system.name == "CEERDI":
                                    player.galactic_xy = (system.x, system.y)
                                    player.selected_system = system
                                    break

                    elif len(key_name) == 1 and (key_name == "n" or key_name == "N"):
                        status.add_message(get_text("mission_declined"), duration=5, type=0)
                        player.mission_status=MissionStatus.COMPLETED  
                        player.info_screen_page=6  
                        global_flags.accept_input = True
                
                #incoming mission message page
                elif player.info_screen_page==13 and not global_flags.alert_on:
                    keys = pygame.key.get_pressed()
                    if any(keys):
                        player.info_screen_page=6
                        global_flags.message_seen = True
                        global_flags.accept_input = True
                #mission completion page
                elif player.info_screen_page==14 and not global_flags.alert_on:
                    keys = pygame.key.get_pressed()
                    if any(keys):
                        player.info_screen_page=6
                        global_flags.accept_input = True
                else:
                    if event.key == pygame.K_F1 and global_flags.is_docked and not global_flags.alert_on:
                        # Initiate undocking sequence
                        global_flags.game_state = global_flags.STATE_LAUNCHING
                    elif event.key == pygame.K_s:
                        player.info_screen_page=10
                        self.market_input = player.name.upper()  # Clear input when entering page
                        self.market_index = 0  # Reset index when entering market page
                        self.market_check = False  # Reset check flag
                    elif event.key == pygame.K_l:
                        player.info_screen_page=11
                        #status.load_game_from_json("jameson.json")


        if player.info_screen_page==5 or player.info_screen_page==4:
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0

            # Cursor keys
            if keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_RIGHT]:
                dx += 1
            if keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_DOWN]:
                dy += 1

            # Joystick (axis 0 = left/right, axis 1 = up/down)
            joystick = None
            if pygame.joystick.get_count() > 0:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                axis_x = joystick.get_axis(0)
                axis_y = joystick.get_axis(1)
                # Use threshold and sign for both directions
                if abs(axis_x) > 0.2:
                    dx += int(np.sign(axis_x))
                if abs(axis_y) > 0.2:
                    dy += int(np.sign(axis_y))

            # Update player.short_range_xy or galactic_xy
            if player.info_screen_page==5:
                if dx != 0 or dy != 0:
                    x, y = player.short_range_xy
                    player.short_range_xy = (x + dx, y + dy)
            elif player.info_screen_page==4:
                if dx != 0 or dy != 0:
                    x, y = player.galactic_xy
                    player.galactic_xy = (x + dx, y + dy)


    def update_axes(self, movement_orientation):
        """Calculate forward, right, up vectors from orientation."""
        forward = movement_orientation.apply([0, 0, 1])
        right = movement_orientation.apply([1, 0, 0])
        up = movement_orientation.apply([0, 1, 0])
        return forward, right, up

    def docking_get_pitch_dir(self, movement_orientation, direction_normalized):
        up = movement_orientation.apply([0, 1, 0])
    
        # Simple check - if target is above us, pitch down; if below, pitch up
        vertical_component = np.dot(direction_normalized, up)
        dir = -1 if vertical_component > 0 else 1
        return dir

    def docking_get_roll_dir(self, movement_orientation, direction_normalized):
        """Determine roll direction based on target's quadrant position."""
        # Convert world direction to player's local space
        """Determine roll direction based on target's quadrant position."""
        # Convert world direction to player's local space
        local_direction = movement_orientation.inv().apply(direction_normalized)
        
        # Calculate angle in XY plane (between -π and π)
        angle = np.arctan2(local_direction[1], local_direction[0])
        
        # Debug info
        self.debug_info = {
            'phase': 'roll calculation',
            'angle_degrees': np.degrees(angle),
            'local_direction': local_direction,
            'quadrant': 'Q1' if angle >= 0 and local_direction[0] >= 0 else
                    'Q2' if angle >= 0 and local_direction[0] < 0 else
                    'Q3' if angle < 0 and local_direction[0] < 0 else 'Q4'
        }   

        # Determine roll direction based on quadrant
        if local_direction[0] >= 0:  # Right half
            roll_dir = -1 if angle > 0 else 1  # Q1: roll left, Q4: roll right
        else:  # Left half
            roll_dir = -1 if angle < 0 else 1  # Q3: roll left, Q2: roll right

        return roll_dir

    def xdocking_get_roll_dir(self, movement_orientation, direction_normalized):
        """Determine roll direction based on whether target is to left or right of player."""
        right = movement_orientation.apply([1, 0, 0])
        
        # Simple check - if target is to right, roll left; if to left, roll right
        side_component = np.dot(direction_normalized, right)
        return 1 if side_component > 0 else -1

    def docking_get_turning_point(self, target_obj, distance):
        "Calculate turning point using target's forward vector."
        # Use target's forward vector directly
       
        # Calculate turning point at specified distance along forward vector
        target_point = target_obj.coords + (target_obj.forward * distance)

        return target_point

    def direction_normalized(self, player_position, target_coords):
        direction_to_point = target_coords - player_position
        distance_to_point = np.linalg.norm(direction_to_point)
        direction_normalized = direction_to_point / distance_to_point
        return direction_normalized, distance_to_point

    def handle_roll_alignment(self, player_position, movement_orientation, target_point, threshold=0.05):

        """Handle roll alignment towards a target point."""
        direction_normalized, distance = self.direction_normalized(player_position, target_point)
        local_direction = movement_orientation.inv().apply(direction_normalized)
        x_offset = local_direction[0]  # Left/right offset in local space
        
        # Calculate deceleration zone
        decel_angle = np.pi/6  # 30 degrees
        
        # Add debug info
        self.debug_info = {
            'phase': 'roll alignment',
            'offset_angle_deg': np.degrees(np.arctan2(x_offset, local_direction[2])),
            'roll_speed': self.current_roll_speed,
            'roll_direction': self.roll_direction,
            'roll_direction': self.roll_direction,
            'in_decel_zone': abs(x_offset) <= decel_angle,
            'x_offset': x_offset,
            'threshold': threshold
        }

        if abs(x_offset) > threshold:
            min_roll_speed = self.max_roll_speed * 0.15  # 15% of max as minimum for responsiveness
            if abs(x_offset) > decel_angle:
                # Far from target - use full speed
                target_roll_speed = self.max_roll_speed
            else:
                # In deceleration zone - reduce speed proportionally to angle
                speed_factor = abs(x_offset) / decel_angle
                target_roll_speed = max(self.max_roll_speed * speed_factor, min_roll_speed)

            # Ensure minimum roll speed for responsiveness
            target_roll_speed = max(target_roll_speed, min_roll_speed)

            # Update current speed (always positive)
            if self.current_roll_speed < target_roll_speed:
                self.current_roll_speed = min(self.current_roll_speed + self.roll_acceleration, 
                                            target_roll_speed)
            elif self.current_roll_speed > target_roll_speed:
                self.current_roll_speed = max(self.current_roll_speed - self.roll_acceleration, 
                                            target_roll_speed)
        else:
            # At target - stop
            self.current_roll_speed = 0

        # Apply roll rotation if there's any roll speed
        if self.current_roll_speed != 0:
            roll_angle = np.deg2rad(self.current_roll_speed) * self.roll_direction
            return True, player_position, movement_orientation * R.from_rotvec(roll_angle * np.array([0, 0, 1]))
        
        return False, player_position, movement_orientation
         
    def handle_pitch_alignment(self, player_position, movement_orientation, target_point, threshold=0.05):
        """Handle pitch alignment with momentum and deceleration near target."""
        direction_normalized, distance = self.direction_normalized(player_position, target_point)
        local_direction = movement_orientation.inv().apply(direction_normalized)
        y_offset = local_direction[1]
        z_offset = local_direction[2]
        
        # Calculate angle to target
        pitch_angle = np.arctan2(y_offset, z_offset)
        angle_to_target = abs(pitch_angle)
        
        # Calculate deceleration zone - start slowing down when within 45 degrees
        decel_angle = np.pi/3  # 45 degrees
        
        self.debug_info = {
        'phase': 'pitch alignment',
        'angle_to_target_deg': np.degrees(angle_to_target),
        'pitch_speed': self.current_pitch_speed,
        'pitch_direction': self.pitch_direction,
        'pitch_direction': self.pitch_direction,
        'in_decel_zone': angle_to_target <= decel_angle,
        'y_offset': y_offset,
        'threshold': threshold
        }


        if angle_to_target > threshold:
            if angle_to_target > decel_angle:
                # Far from target - accelerate to max speed
                target_pitch_speed = self.max_pitch_speed
            else:
                # In deceleration zone - reduce speed proportionally to angle
                speed_factor = angle_to_target / decel_angle
                target_pitch_speed = (self.max_pitch_speed * speed_factor)
            

            
            # Accelerate/decelerate towards target speed
            if self.current_pitch_speed < target_pitch_speed:
                self.current_pitch_speed = min(self.current_pitch_speed + self.pitch_acceleration, target_pitch_speed)
            elif self.current_pitch_speed > target_pitch_speed:
                self.current_pitch_speed = max(self.current_pitch_speed - self.pitch_acceleration, target_pitch_speed)
        else:
            # At target - stop
            self.current_pitch_speed = 0
            self.pitch_direction = 0
        
        # Apply pitch rotation if there's any pitch speed
        if self.current_pitch_speed != 0:
            pitch_angle = -np.deg2rad(self.current_pitch_speed)*-self.pitch_direction
            return True, player_position, movement_orientation * R.from_rotvec(pitch_angle * np.array([1, 0, 0]))
        
        return False, player_position, movement_orientation

    def move_towards_point(self, player_position, movement_orientation, target_point, stop_distance=1.0,max_speed=None):
        """Move towards a target point until reaching stop_distance."""
        if max_speed is None:
            max_speed = self.max_speed

        direction_normalized, distance = self.direction_normalized(player_position, target_point)
        
        # Start decelerating when we're within deceleration distance
        decel_distance = (self.current_speed ** 2) / (2 * self.acceleration)
    
        if distance > stop_distance + decel_distance:
            # Far enough to accelerate/maintain speed
            self.current_speed = min(self.current_speed + self.acceleration, max_speed)
            moving = True
        elif distance > stop_distance:
            # Within deceleration zone
            self.current_speed = max(self.current_speed - self.acceleration, 0)
            moving = True
        else:
            # At target - stop
            self.current_speed = 0
            moving = False
        
        if moving and self.current_speed > 0:
            return True, player_position + direction_normalized * self.current_speed, movement_orientation
        
        return False, player_position, movement_orientation

    def docking_computer(self, player_position, movement_orientation):
        if not self.docking_active or self.docking_target is None:
            return player_position, movement_orientation

        # get direction and distance to target
        direction_normalized, distance = self.direction_normalized(player_position, self.target_obj.coords)

        # Get player's forward vector
        forward = movement_orientation.apply([0, 0, 1])

        # Dot product tells us if target is in front (> 0) or behind (< 0)
        is_behind = np.dot(forward, direction_normalized) < 0

        target_forward = self.target_obj.forward
        target_right = self.target_obj.right
        target_up = self.target_obj.up

        # set entry phase to docking
        if self.docking_phase == DockingPhase.INACTIVE and self.docking_active:
            if distance < self.minimum_docking_distance:
                self.docking_phase = DockingPhase.BACKING_AWAY
            elif is_behind:
                self.docking_phase = DockingPhase.TURNING_TO_FACE
                self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
            else:
                self.docking_phase = DockingPhase.CHECK_ACCESS_TO_PORTAL

        match self.docking_phase:
            case DockingPhase.TURNING_AROUND:
                self.docking_text = get_text("docking_too_close_turn")
                # Calculate angle between our forward vector and direction to target
                forward = movement_orientation.apply([0, 0, 1])
                current_angle = np.arccos(np.dot(forward, direction_normalized))

                # Calculate turn point 100 units away, rotated 180 degrees from current direction
                turn_matrix = R.from_rotvec([0, np.pi, 0])  # 180 degree rotation
                turn_direction = turn_matrix.apply(direction_normalized)
                turn_point = player_position + (turn_direction * 100)  # Point 100 units away

                # Update direction for turn
                turn_dir_normalized, _ = self.direction_normalized(player_position, turn_point)
                self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, turn_dir_normalized)

                self.debug_info = {
                    'phase': 'turning around using pitch helper',
                    'current_angle_deg': np.degrees(current_angle),
                    'player_location': player_position,
                    'turn_point': turn_point,
                    'current_pitch_speed': self.current_pitch_speed,
                    'pitch_dir': self.pitch_direction
                }

                # Use pitch alignment helper
                is_pitching, player_position, movement_orientation = self.handle_pitch_alignment(
                    player_position,
                    movement_orientation,
                    turn_point,
                    threshold=0.2
                )

                # Change phase when we're facing sufficiently away from target (>90 degrees)
                if current_angle > np.pi/2:  # >90 degrees
                    self.docking_phase = DockingPhase.BACKING_AWAY
                    self.current_pitch_speed = 0  # Reset pitch speed

                return player_position, movement_orientation

            case DockingPhase.BACKING_AWAY:
                self.docking_text = get_text("docking_too_close_away")
                if not is_behind:
                    #direction_normalized,distance = self.direction_normalized(player_position, self.target_obj.coords)
                    self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
                    self.docking_phase = DockingPhase.TURNING_AROUND
                    return player_position, movement_orientation

                # Calculate target point minimum_docking_distance away from target
                target_point = self.target_obj.coords + forward * self.minimum_docking_distance

                self.debug_info = {
                    'phase': 'backing away',
                    'distance': distance,
                    'target_distance': self.minimum_docking_distance,
                    'target_point': target_point,
                    'player_location': player_position,
                    'is_behind': is_behind
                }

                # Move to target point
                is_moving, player_position, movement_orientation = self.move_towards_point(
                    player_position,
                    movement_orientation,
                    target_point,
                    stop_distance=1.0
                )

                if not is_moving:
                    # Reached safe distance
                    if is_behind:
                        self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
                        self.docking_phase = DockingPhase.CHECK_ACCESS_TO_PORTAL
                    else:
                        self.docking_phase = DockingPhase.CHECK_ACCESS_TO_PORTAL

                return player_position, movement_orientation

            #Might be able to get rid of this phase, but leave in for now. -not currently part of flow
            case DockingPhase.TURNING_TO_FACE:
                self.docking_text = get_text("docking_turn_to_face")
                current_angle = np.arccos(np.dot(forward, direction_normalized))
                # Calculate direction to actual target (not a turn point)
                target_point = self.target_obj.coords

                self.debug_info = {
                    'phase': 'turning to face using pitch helper',
                    'current_angle_deg': np.degrees(current_angle),
                    'player_location': player_position,
                    'target_point': target_point,
                    'current_pitch_speed': self.current_pitch_speed
                }

                # Use pitch alignment helper with momentum
                is_pitching, player_position, movement_orientation = self.handle_pitch_alignment(
                    player_position,
                    movement_orientation,
                    target_point,
                    threshold=0.05
                )

                # Change phase when aligned with target
                if not is_pitching:
                    self.docking_phase = DockingPhase.CHECK_ACCESS_TO_PORTAL
                    self.current_pitch_speed = 0  # Reset pitch speed

                return player_position, movement_orientation

            case DockingPhase.CHECK_ACCESS_TO_PORTAL:
                # Get target's forward vector (points out of face 12 for dodo and face 0 for coriolis)
                face_normal = target_forward  # Negative because face 12 points opposite to forward

                # Calculate if face is visible from current position
                view_direction, _ = self.direction_normalized(self.target_obj.coords, player_position)
                face_visibility = np.dot(face_normal, view_direction)

                self.debug_info = {
                    'phase': 'check access to portal',
                    'distance': distance,
                    'face_normal': face_normal,
                    'face_visibility': face_visibility,
                    'target_location': self.target_obj.coords,
                    'is_behind': is_behind,
                    'player_location': player_position
                }

                if face_visibility > 0:
                    # Calculate turning point using dodo's position and forward vector
                    turning_point = (self.target_obj.coords +
                                    face_normal * self.turning_point_distance)

                    # Calculate direction to turning point
                    direction_normalized, distance_to_point = self.direction_normalized(
                        player_position, turning_point)

                    self.roll_direction = self.docking_get_roll_dir(
                        movement_orientation, direction_normalized)
                    self.docking_phase = DockingPhase.MOVING_TO_PORTAL_ROLLING
                else:
                    self.docking_phase = DockingPhase.PORTAL_NOT_VISIBLE

                return player_position, movement_orientation

            case DockingPhase.PORTAL_NOT_VISIBLE:
                # First get point along normal using existing helper
                point = self.docking_get_turning_point(self.target_obj, self.waypoint_distance)

                # Use target's right vector instead of calculating perpendicular
                self.waypoint = point + self.target_obj.right * self.waypoint_distance

                self.debug_info = {
                    'phase': 'phase2: portal not visible',
                    'point_on_normal': point,
                    'waypoint': self.waypoint,
                    'player_location': player_position,

                }
                direction_normalized,distance_to_point = self.direction_normalized(player_position, self.waypoint)
                self.roll_direction = self.docking_get_roll_dir(movement_orientation, direction_normalized)
                self.docking_phase = DockingPhase.ROLLING_TO_WAYPOINT

                return player_position, movement_orientation

            case DockingPhase.ROLLING_TO_WAYPOINT:
                self.docking_text = get_text("docking_align(roll)")
                self.debug_info = {
                    'phase': 'phase2: moving to opposite side, rolling',
                    'roll_dir': 'right' if self.roll_direction > 0 else 'left',
                    'player_location': player_position,
                    'waypoint': self.waypoint
                }
                    
                is_rolling, player_position, movement_orientation = self.handle_roll_alignment(player_position, movement_orientation, self.waypoint)
                if not is_rolling:
                    self.docking_phase = DockingPhase.PITCHING_TO_WAYPOINT
                    self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
                return player_position, movement_orientation
                                  
            case DockingPhase.PITCHING_TO_WAYPOINT:
                self.docking_text =get_text("docking_align(pitch)")
                self.debug_info = {
                    'phase': 'phase2: moving to opposite side, pitching',
                    'pitch_dir': 'up' if self.pitch_direction > 0 else 'down',
                    'player_location': player_position,
                    'waypoint': self.waypoint
                }
                
                is_pitching, player_position, movement_orientation = self.handle_pitch_alignment(player_position, movement_orientation, self.waypoint)
                if not is_pitching:
                    self.docking_phase = DockingPhase.MOVING_TO_WAYPOINT
                return player_position, movement_orientation
            
            case DockingPhase.MOVING_TO_WAYPOINT:
                self.docking_text = get_text("docking_move_to_wp")  
                self.debug_info = {
                    'phase': 'phase2: flying to waypoint',
                    'player_location': player_position,
                    'waypoint': self.waypoint
                }
                
                is_moving, player_position, movement_orientation = self.move_towards_point(
                    player_position, 
                    movement_orientation, 
                    self.waypoint,
                    stop_distance=1.0
                )
                
                if not is_moving:
                    # Calculate next phase parameters
                    turning_point = self.docking_get_turning_point(self.target_obj, self.turning_point_distance)
                    direction_normalized, _ = self.direction_normalized(player_position, turning_point)
                    self.roll_direction = self.docking_get_roll_dir(movement_orientation, direction_normalized)
                    self.docking_phase = DockingPhase.MOVING_TO_PORTAL_ROLLING
                return player_position, movement_orientation
 
            case DockingPhase.MOVING_TO_PORTAL_ROLLING:
                self.docking_text = get_text("docking_portal(roll)")
                target = self.docking_get_turning_point(self.target_obj, self.turning_point_distance)
                
                self.debug_info = {
                    'phase': 'phase2: rolling to align with turning point',
                    'roll_dir': 'right' if self.roll_direction > 0 else 'left',
                    'target': target,
                    'player_location': player_position
                }
                
                is_rolling, player_position, movement_orientation = self.handle_roll_alignment(player_position, movement_orientation, target)
                if not is_rolling:
                    self.docking_phase = DockingPhase.MOVING_TO_PORTAL_PITCHING
                    direction_normalized, _ = self.direction_normalized(player_position, target)
                    self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
                return player_position, movement_orientation

            case DockingPhase.MOVING_TO_PORTAL_PITCHING:
                self.docking_text = get_text("docking_portal(pitch)")
                target = self.docking_get_turning_point(self.target_obj, self.turning_point_distance)
                self.debug_info = {
                    'phase': 'phase2: pitching to align with turning point',
                    'pitch_dir': 'up' if self.pitch_direction > 0 else 'down',
                    'turning_point': target,
                    'player_pos': player_position,
                    'distance': distance
                }
                
                is_pitching, player_position, movement_orientation = self.handle_pitch_alignment(player_position, movement_orientation, target)
                if not is_pitching:
                    self.docking_phase = DockingPhase.MOVING_TO_PORTAL_FLYING
                return player_position, movement_orientation

            case DockingPhase.MOVING_TO_PORTAL_FLYING:
                self.docking_text = get_text("docking_portal(move)")
                target = self.docking_get_turning_point(self.target_obj,self.turning_point_distance)
                
                self.debug_info = {
                    'phase': 'phase2: flying to turning point',
                    'turning_point': target,
                    'player_pos': player_position
                }
                
                is_moving, player_position, movement_orientation = self.move_towards_point(
                    player_position, 
                    movement_orientation, 
                    target, 
                    stop_distance=1.0
                )
                
                if not is_moving:
                    self.docking_phase = DockingPhase.FINAL_ROLL
                    target = self.target_obj.coords
                    direction_normalized, _ = self.direction_normalized(player_position, target)
                    self.roll_direction = self.docking_get_roll_dir(movement_orientation, direction_normalized)
                return player_position, movement_orientation

            case DockingPhase.FINAL_ROLL:
                self.docking_text = get_text("docking_final(roll)")
                # Get docking port position
                target_point = self.target_obj.get_docking_port_position()
                direction_normalized, distance = self.direction_normalized(player_position, target_point)
                self.roll_direction = self.docking_get_roll_dir(movement_orientation, direction_normalized)
                
                self.debug_info = {
                    'phase': 'phase3: final roll alignment',
                    'roll_dir': 'right' if self.roll_direction > 0 else 'left',
                    'target': target_point,
                    'player_location': player_position
                }
                
                is_rolling, player_position, movement_orientation = self.handle_roll_alignment(player_position, movement_orientation, target_point, threshold=0.004)
                if not is_rolling:
                    self.docking_phase = DockingPhase.FINAL_PITCH
                    direction_normalized, _ = self.direction_normalized(player_position, target_point)
                    self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)
                return player_position, movement_orientation

            case DockingPhase.FINAL_PITCH:
                self.docking_text = get_text("docking_final(pitch)")
                # Get docking port position
                target_point= self.target_obj.get_docking_port_position()
                direction_normalized, distance = self.direction_normalized(player_position, target_point)
                self.pitch_direction = self.docking_get_pitch_dir(movement_orientation, direction_normalized)

                self.debug_info = {
                    'phase': 'phase3: final pitch alignment',
                    'pitch_dir': 'up' if self.pitch_direction > 0 else 'down',
                    'target': target_point,
                    'player_pos': player_position,
                    'distance': distance
                }
                
                is_pitching, player_position, movement_orientation = self.handle_pitch_alignment(
                    player_position, 
                    movement_orientation, 
                    target_point, 
                    threshold=0.005
                )
                if not is_pitching:
                    self.docking_phase = DockingPhase.FINAL_APPROACH
                return player_position, movement_orientation

            case DockingPhase.FINAL_APPROACH:
                # Get face center position rather than using dodo center
                player_up = movement_orientation.apply([0, 1, 0])
                dodo_up = self.target_obj.up
                up_alignment = abs(np.dot(player_up, dodo_up))

                # Get docking port position instead of dodo center
                target_point = self.target_obj.get_docking_port_position()
                direction_normalized, distance_to_point = self.direction_normalized(player_position, target_point)
                
                # Calculate required roll based on current alignment
                if up_alignment > 0.009:  # Not horizontally aligned
                    self.docking_text = get_text("docking_final(horiz)")
                    target_spin = self.target_obj.rotation_inc[2]  # Z-axis rotation
                    self.roll_direction = 1 if target_spin > 0 else -1  # Opposite to target's spin
                    self.current_roll_speed = self.max_roll_speed/4
                    # Apply the roll to movement_orientation
                    roll_angle = np.deg2rad(self.current_roll_speed) * self.roll_direction
                    movement_orientation = movement_orientation * R.from_rotvec(roll_angle * np.array([0, 0, 1]))
        

                elif distance_to_point > self.docking_stop_distance:
                    # Roll aligned, move forward
                    self.docking_text = get_text("docking_spin_match")
                    if global_flags.station_is_hostile:
                        self.docking_text = get_text("docking_abort")
                        self.docking_active = False
                        self.docking_phase = DockingPhase.INACTIVE
                        self.current_speed = 0
                        self.current_pitch_speed = 0
                        self.current_roll_speed = 0
                        self.pitch_direction = 0
                        self.roll_direction = 0
                        # Stop docking music only when docking just became inactive
                        if self.docking_music_playing:
                            sound_manager.stop_music()
                            self.docking_music_playing = False
                        
                    else:
                        is_moving, player_position, movement_orientation = self.move_towards_point(
                            player_position,
                            movement_orientation,
                            target_point,
                            stop_distance=self.docking_stop_distance,
                            max_speed=self.max_speed/5
                        )
                        
                        # Match dodo's rotation while moving
                        if is_moving:
                            rot_angle = -self.target_obj.rotation_inc[2]
                            self.current_roll_speed = np.rad2deg(rot_angle)  # Convert to degrees per frame
                            movement_orientation = movement_orientation * R.from_rotvec(rot_angle * np.array([0, 0, 1]))
                else:
                    self.docking_active = False
                    global_flags.game_state = global_flags.STATE_DOCKING
                    self.docking_phase = DockingPhase.INACTIVE
                    self.docking_text = get_text("docking_complete")
                    self.current_speed = 0
                    self.current_pitch_speed = 0
                    self.current_roll_speed = 0
                    self.pitch_direction = 0
                    self.roll_direction = 0
                    # Stop docking music only when docking just became inactive
                    if self.docking_music_playing:
                        sound_manager.stop_music()
                        self.docking_music_playing = False
                        
    


                self.debug_info = {
                    'phase': 'final approach',
                    'up_alignment': up_alignment,
                    'distance': distance_to_point,
                    'roll_direction': self.roll_direction
                }
                
                return player_position, movement_orientation


   