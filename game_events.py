
import random
from unittest import result
import numpy as np
import pygame
import sys
from scipy.spatial.transform import Rotation as R
import status
from status import global_flags, player, ship_data, MissileStatus, game_constants, LaserType, MissionStatus
import wireframes
import system_data
from system_data import Planet_and_Star
import object
import ogl_render
import input
import ogl_cockpit
from particle import Particle
from market import get_all_market_data
from sounds import sound_manager, SoundType
from info_screens import get_text
import math

def newGameView(WIDTH, HEIGHT):
    input_handler = input.InputHandler(max_move_speed=4.0, rotate_speed=1)
    cockpit_console = ogl_cockpit.CockpitConsole(WIDTH)

    # Set initial orientation so player looks toward negative Z (default)
    player_position = np.array([0, 0, 0], dtype=float)
    movement_orientation = R.from_rotvec(np.pi * np.array([0, 1, 0]))  # 180° turn to face -Z
    look_orientation = R.from_rotvec(np.pi * np.array([0, 1, 0]))
    direction_text = "FRONT"
    movement_forward = movement_orientation.apply([0, 0, 1])  # This will now be [0, 0, -1]
    movement_right = movement_orientation.apply([1, 0, 0])
    movement_up = movement_orientation.apply([0, 1, 0])

    return player_position, movement_orientation, look_orientation, input_handler, cockpit_console, movement_forward, movement_right, movement_up, direction_text

def reset():
    status.global_flags.reset()
    status.ship_data.reset()
    status.player.reset()
    global_flags.reset_game = False



def newGameObjects(player_position):
    player.market_data = get_all_market_data(player.current_system.economy_trade_value, player.random_market_factor, player.current_system.government)   
    planet_and_star = Planet_and_Star(player.current_system.planetCoords, player.current_system.sunCoords, player.current_system.name)
    spaceStationCoords = system_data.get_spaceStation_coords(player.current_system.planetCoords)
    spaceStationOrientation = system_data.get_station_orientation_towards_planet(spaceStationCoords, player.current_system.planetCoords)
    
    # Initialize objects

    if player.current_system.tech_level<10:
        objectList = [ addShip("Coriolis station", spaceStationCoords, initial_rotation=spaceStationOrientation, rotation_inc = (0.0, 0.0, 0.002))]
    else:    
        objectList = [ addShip("Dodo station", spaceStationCoords, initial_rotation=spaceStationOrientation, rotation_inc = (0.0, 0.0, 0.002))]

    #ship = addShip("Constrictor",spaceStationCoords+np.array([800,800,200]),rotation_inc = (0.01, 0.0, 0.0),forward_speed=3.0)
    #ship.is_docking=True
    #ship.aggression=63
    #objectList.append(ship)
    #objectList.append(addShip("Cargo canister",spaceStationCoords+np.array([500,500,0]),rotation_inc = (0.01, 0.00, 0.00),forward_speed=0.0))
    

    global_flags.game_state = global_flags.STATE_DOCKED
    global_flags.station_is_hostile=False
    starfield = ogl_render.StarField(num_stars=1500,player_position=player_position)
    particleList=[]
    ogl_render.GameOverScreenState.cobra = None
    ogl_render.EscapePodLaunchState.cobra = None
    return planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield, particleList

def addShip(ship_type,coords,initial_rotation=(0,0,0),rotation_inc = (0,0,0), orientation=(0.0,0.0, 0.0),forward_speed=0.0):
    
    ship_dictionary = wireframes.ships.get(ship_type)
    if ship_dictionary is None:
        raise ValueError(f"Unknown ship type: {ship_type}")
    
    return object.Object(
        ship_dictionary,
        coords=coords,
        initial_rotation=initial_rotation,
        rotation_inc=rotation_inc,
        orientation=orientation,
        forward_speed=forward_speed
    )



def addMissile(coords, orientation_rot,locked_on_target,enemy=False):
    """Create a missile with the given orientation.
    
    Args:
        coords: Launch position
        orientation_rot: scipy Rotation object representing the missile's orientation
        ID: Missile identifier
    """
    ship_type = "Missile"
    ship_dictionary = wireframes.ships.get(ship_type)
    if ship_dictionary is None:
        raise ValueError(f"Unknown ship type: {ship_type}")

    return object.Missile(ship_dictionary,
        launch_position=coords,
        player_orientation=orientation_rot,
        locked_on_target=locked_on_target,
        forward_speed=4.5,
        enemy=enemy,
    )


def set_player_launch_position(current_system, spaceStationCoords, player_position, movement_orientation, look_orientation, input_handler, global_flags):
    planet_pos = np.array(current_system.planetCoords)
    station_pos = np.array(spaceStationCoords)
    docking_direction = planet_pos - station_pos
    docking_direction /= np.linalg.norm(docking_direction)  # Normalize
    slot_offset = 180  # Distance outside the slot
    player_position[:] = station_pos + docking_direction * slot_offset
    default_forward = np.array([0, 0, -1])  # or [0, 0, 1] depending on your convention
    result = R.align_vectors([-docking_direction], [default_forward])
    rot = result[0]
    movement_orientation = rot
    look_orientation = rot
    input_handler.current_speed = 1.0
    global_flags.just_jumped = True # forces starfield to redraw around new position
    global_flags.extra_vessels_counter = 0 #reset extra vessels counter on launch
    
    contraband = calculate_badness_level()
    # 8-bit logical OR of contraband and player.FIST - value is at least as high as either!
    player.FIST = (int(player.FIST) | contraband) & 0xFF
    global_flags.radar_zoom_index = 2
    global_flags.radar_zoom_direction = 1

    return(player_position, movement_orientation, look_orientation)

def do_hyperspace_jump():
    if global_flags.hyperspace_is_galactic:
        global_flags.hyperspace_is_galactic = False
        player.galaxy_number = (player.galaxy_number + 1) & 0x07
        player.all_systems = system_data.get_all_system_data(player.galaxy_number)
        global_flags.extra_vessels_counter = 0 #reset extra vessels counter on launch

        location_xy=[96,96/2]
        closest_system_index=0
        player.FIST = 0.0 #reset FIST on new galaxy jump
        min_distance = float('inf')
        for sys in player.all_systems:
            cross_dx = sys.x - location_xy[0]
            cross_dy = sys.y - location_xy[1]
            dist = (cross_dx**2 + cross_dy**2) ** 0.5
            if dist < min_distance:
                min_distance = dist
                closest_system_index = sys.number
        
        player.selected_system = player.all_systems[closest_system_index]      
    else:
        player.FIST = player.FIST/2 #reduce FIST when we jump within the galaxy
        ship_data.fuel_level -= int(player.distance_to_selected) * 10

    untarget_missiles()
    global_flags.in_hyperspace_countdown = False
    global_flags.game_state = global_flags.STATE_FLYING
    global_flags.station_is_hostile = False
    status.add_message(f"{get_text('welcome')} {player.selected_system.name.capitalize()}", duration=3, type=0)
    player.current_system = player.selected_system
    player.short_range_xy = player.current_system.x, player.current_system.y
    player.galactic_xy = player.current_system.x, player.current_system.y
    planet_and_star = Planet_and_Star(player.current_system.planetCoords, player.current_system.sunCoords,player.current_system.name)
    spaceStationCoords = system_data.get_spaceStation_coords(player.current_system.planetCoords)
    spaceStationOrientation = system_data.get_station_orientation_towards_planet(spaceStationCoords, player.current_system.planetCoords)
    player_position = np.array([0, 0, 0], dtype=float)
    starfield = ogl_render.StarField(num_stars=2000, player_position=player_position)
    global_flags.radar_zoom_index = 0
    global_flags.radar_zoom_direction = 1


    
    if player.current_system.tech_level<10:
        objectList = [ addShip("Coriolis station", spaceStationCoords, initial_rotation=spaceStationOrientation, rotation_inc = (0.0, 0.0, 0.002))]
    else:    
        objectList = [ addShip("Dodo station", spaceStationCoords, initial_rotation=spaceStationOrientation, rotation_inc = (0.0, 0.0, 0.002))]

    
   
    vec = np.random.normal(size=3)
    vec /= np.linalg.norm(vec)


    #movement_orientation = R.from_rotvec(np.pi * np.array([0, 1, 0]))
    #look_orientation = R.from_rotvec(np.pi * np.array([0, 1, 0]))
    
    movement_orientation = R.align_vectors([vec], [[0, 0, 1]])[0]
    look_orientation = R.align_vectors([vec], [[0, 0, 1]])[0]   
    
    movement_forward = movement_orientation.apply([0, 0, 1])
    movement_right = movement_orientation.apply([1, 0, 0])
    movement_up = movement_orientation.apply([0, 1, 0])
    player.random_market_factor = random.randint(0, 255)
    player.market_data = get_all_market_data(player.current_system.economy_trade_value, player.random_market_factor, player.current_system.government)
   
    return (player_position, movement_orientation, look_orientation, movement_forward, movement_right, movement_up,
            planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield)

def process_damage(obj_coords,player_position,movement_forward, damage_amount, main_loop_counter):
    to_object = obj_coords - player_position
    to_object = to_object / np.linalg.norm(to_object)  # Normalize

    # Player's forward vector (should already be normalized)
    forward = movement_forward / np.linalg.norm(movement_forward)

    dot = np.dot(forward, to_object)
    if dot > 0:
        ship_data.forward_shield -= damage_amount
        if ship_data.forward_shield < 0:
            ship_data.energy_level -= abs(ship_data.forward_shield)
            if not sound_manager.is_playing(SoundType.HIT):
                sound_manager.play(SoundType.HIT)
            ship_data.forward_shield = 0
            ouch()
    else:
        ship_data.aft_shield -= damage_amount
        if ship_data.aft_shield < 0:
            ship_data.energy_level -= abs(ship_data.aft_shield)
            if not sound_manager.is_playing(SoundType.HIT):
                sound_manager.play(SoundType.HIT)
            ship_data.aft_shield = 0
            ouch()
    
    if ship_data.energy_level < 0:
        ship_data.energy_level = 0
        global_flags.game_state = global_flags.STATE_GAME_OVER
        untarget_missiles()
        status.clear_messages()
        sound_manager.stop_all()
        global_flags.frame_start = main_loop_counter

        
def ouch():
    #maybe lose cargo or equipment
    if random.random() > 0.5:
        return
    
    item =  random.randint(0,255)
    if item>=22:
        return
    
    elif item<17:
        inventory = player.cargo_inventory
        if len(inventory) ==0:
            return
        
        item_name= player.market_data[item]['name']

        for cargo_item in inventory:
            if cargo_item['name'] == item_name:
                inventory.remove(cargo_item)      
                status.add_message(f"{item_name} {get_text('destroyed')}", duration=3, type=0)
                break
                   
    else:
        equipment_list = ("ECM_System","fuel_scoops","energy_bomb","extra_energy_unit","docking_computer")
        equipment_item = equipment_list[item-17]
        if getattr(ship_data, equipment_item):
            setattr(ship_data, equipment_item, False)
            status.add_message(f"{equipment_item.replace('_',' ')} {get_text('destroyed')}", duration=3, type=0)
        

            

def process_collisions(collisions, movement_forward, movement_up, input_handler, player_position, main_loop_counter,objectList):
    
    for obj in collisions:
        if obj.type == "station" and not input_handler.docking_active and global_flags.is_flying:
            #check speed is low enough for docking
            if input_handler.current_speed > input_handler.max_speed * 0.25:
                status.add_message(get_text('too_fast'), duration=3, type=0)
                process_damage(obj.coords, player_position, movement_forward, game_constants.CRASH_DAMAGE_AMOUNT,main_loop_counter)
                return
    
            #check facing right direction
            player_forward = movement_forward / np.linalg.norm(movement_forward)
            station_forward = obj.orientation.apply([0, 0, -1])
            station_forward = station_forward / np.linalg.norm(station_forward)
            alignment = np.dot(player_forward, station_forward)
            angle_threshold = np.cos(np.deg2rad(30))  # ≈ 0.866

            if alignment < angle_threshold:
                    status.add_message(get_text('not_within_30'), duration=3, type=0)
                    process_damage(obj.coords,player_position, movement_forward,  game_constants.CRASH_DAMAGE_AMOUNT,main_loop_counter)
                    return

            if obj.name == "Coriolis station":
                face_indices = wireframes.coriolis_faces[14]
            else:    
                face_indices = wireframes.dodo_faces[12]
            
            face_vertices = obj.nodes_world[face_indices, :3]
            face_center = face_vertices.mean(axis=0)
            v1 = face_vertices[1] - face_vertices[0]
            v2 = face_vertices[2] - face_vertices[0]
            face_normal = np.cross(v1, v2)
            face_normal /= np.linalg.norm(face_normal)

            to_player = player_position - face_center
            to_player /= np.linalg.norm(to_player)

            dot = np.dot(face_normal, to_player)
            angle_deg = np.degrees(np.arccos(dot))
            player_dist = np.linalg.norm(player_position - face_center)

            #print (f"Angle to docking face normal: {angle_deg:.2f} degrees, Distance to face center: {player_dist:.2f}")
            if angle_deg > 30:
                status.add_message(get_text('outside_portal'), duration=3, type=0)
                #process_damage(obj.coords, player_position, movement_forward, game_constants.CRASH_DAMAGE_AMOUNT,main_loop_counter)
                return
            
            if player_dist < 30:    
                #now check if dodo slot is "almost" horizontal
                station_up = obj.orientation.apply([0, 1, 0])
                station_up = station_up / np.linalg.norm(station_up)
                up_alignment = np.dot(movement_up, station_up)
                up_angle_deg = np.degrees(np.arccos(up_alignment))
                angle_delta = abs(90-up_angle_deg)
                #print(f"angle delta: {angle_delta}")
                if angle_delta > 20:
                    status.add_message(get_text('not_aligned'), duration=3, type=0)
                    process_damage(obj.coords, player_position, movement_forward, game_constants.CRASH_DAMAGE_AMOUNT,main_loop_counter)
                    return
                    
                status.add_message(get_text('successful'), duration=3, type=0)
                global_flags.game_state = global_flags.STATE_DOCKING
                input_handler.current_speed = 0
                input_handler.current_pitch_speed = 0
                input_handler.current_roll_speed = 0
                input_handler.pitch_direction = 0
                input_handler.roll_direction = 0
                if obj.locked_on_missile_index != -1:
                    check_missile_targets(obj,objectList)
                untarget_missiles()

        elif obj.type == "missile":
            if obj.enemy:
                status.add_message(get_text('hit_by_hostile'), duration=2, type=0)
                process_damage(obj.coords, player_position, movement_forward, game_constants.MISSILE_IMPACT_DAMAGE,main_loop_counter)
                if not sound_manager.is_playing(SoundType.HIT):
                    sound_manager.play(SoundType.HIT)
                obj.ready_for_removal = True
        
        elif obj.name in ("Alloy", "Cargo canister", "Escape pod", "Thargon", "Raw Minerals"):
            obj.ready_for_removal = True
            if obj.locked_on_missile_index != -1:
                check_missile_targets(obj,objectList)
            damage = True
            if ship_data.fuel_scoops:
                if process_item_scoop(obj):
                    damage = False
            if damage:
                if not sound_manager.is_playing(SoundType.HIT):
                    sound_manager.play(SoundType.HIT)
                process_damage(obj.coords, player_position, movement_forward, game_constants.CRASH_DAMAGE_AMOUNT, main_loop_counter)


        elif obj.type == "ship" or obj.type == "asteroid":
            status.add_message(f"{get_text('collision_with')} {obj.name}", duration=2, type=0)
            if not sound_manager.is_playing(SoundType.HIT):
                    sound_manager.play(SoundType.HIT)
            process_damage(obj.coords, player_position, movement_forward, game_constants.CRASH_DAMAGE_AMOUNT,main_loop_counter)
            obj.ready_for_removal = True
            if obj.locked_on_missile_index != -1:
                check_missile_targets(obj,objectList)
            process_kill(obj,objectList)
        
        
def process_item_scoop(obj):
    if get_remaining_cargo_capacity()/1000000 >=1:
        #add to cargo inventory
        item_name = ""
        if obj.name == "Alloy":
            item_name="Alloys"
        elif obj.name == "Escape pod":    
            item_name="Slaves"
        elif obj.name == "Thargon":    
            item_name="Alien items"
        elif obj.name == "Raw Minerals":    
            item_name="Minerals"        
        else:
            random_cargo = random.randint(0,7)
            item_name = player.market_data[random_cargo]['name']

        # Update cargo inventory
        found = False
        for item in player.cargo_inventory:
            if item['name'] == item_name:
                item['quantity'] += 1
                found = True
                break
        if not found:
            player.cargo_inventory.append({
                'name':item_name,
                'quantity': 1,
                'unit':"t",
                'wt_factor':1000000,
                'string': item_name
            }) 

        status.add_message(f"{item_name} {get_text('added')}", duration=2, type=0)
        return True
    else:
        status.add_message(get_text('full'), duration=2, type=0)
        return False


def handle_missile_targeting(objectList, player_position, movement_forward, input_handler,screen_center,focal_length):
    for obj in objectList:
        if obj.is_visible and obj.type != "missile" and obj.type != "fragment" and obj.distance_to_player < game_constants.MAX_MISSILE_TARGET_DISTANCE:
            dx = obj.screen_pos[0] - screen_center[0]
            dy = obj.screen_pos[1] - screen_center[1]
            distance_from_center = np.sqrt(dx**2 + dy**2)
            obj_distance = np.linalg.norm(obj.coords - player_position)
            apparent_radius = max(2, int(obj.collision_radius * focal_length / obj_distance))
            #print(f"Object: {obj.name}, Distance from center: {distance_from_center:.2f}, Apparent radius: {apparent_radius:.2f}")
            if distance_from_center - apparent_radius <= 0:  # within targeting reticle
                if global_flags.locked_on_target != obj:
                    # New target locked
                    global_flags.locked_on_target = obj
                    global_flags.locked_on_frame_count = 0
                else:
                    global_flags.locked_on_frame_count += 1
                    if global_flags.locked_on_frame_count >= game_constants.LOCKED_ON_FRAMES_REQUIRED:
                        status.add_message(f"{get_text('locked_on')} {obj.name}", duration=2, type=0)
                        if sound_manager.is_playing(SoundType.TARGETING):
                            sound_manager.stop(SoundType.TARGETING)
                        if not sound_manager.is_playing(SoundType.LOCKED_ON):
                            sound_manager.play(SoundType.LOCKED_ON, loops = -1, volume=0.2)
                        
                        for i in range(len(ship_data.missile_status)):
                            if ship_data.missile_status[i] == MissileStatus.TARGETING:
                                ship_data.missile_status[i] = MissileStatus.LOCKED_ON
                                obj.locked_on_missile_index = i
                                break  # Lock only one missile at a time
    
                
    return
   
def check_missile_targets(destroyed_object,objectList):
    #check to see if the object we've just destroyed was a missile target
    if destroyed_object.locked_on_missile_index != -1:
        missile_index = destroyed_object.locked_on_missile_index
        
        #check if missile is unlaunched and clear target lock
        if ship_data.missile_status[missile_index] == MissileStatus.LOCKED_ON:
            ship_data.missile_status[missile_index] = MissileStatus.PRESENT
            status.add_message(get_text('target_lost'), duration=2, type=0)
            destroyed_object.locked_on_missile_index = -1
            if sound_manager.is_playing(SoundType.LOCKED_ON):
                    sound_manager.stop(SoundType.LOCKED_ON)
            global_flags.targeting_missile = False        
        else:
            #missile already launched, find and clear target lock, skip any missile marked for removal as they likely killed the target and are already being de-targeted
            for obj in objectList:
                if obj.type == "missile" and not obj.enemy and not obj.ready_for_removal:
                    if obj.locked_on_target == destroyed_object:
                        obj.locked_on_target = None
                        destroyed_object.locked_on_missile_index = -1
                        global_flags.targeting_missile = False        
                        #obj.ready_for_removal = True
                        #handle_explosion(obj, objectList, particleList, player_position, player_right)
    

def check_player_collision(player_position, player_radius, objectList):
    collisions = []
    for obj in objectList:
        if obj.distance_to_player == 0.0: #newly spaned cargo objects, spawned after object update
            obj.distance_to_player = np.linalg.norm(obj.coords - player_position)
        if obj.distance_to_player < (player_radius + obj.collision_radius):
            collisions.append(obj)
    return collisions

def launch_missile(player_position, forward, missile_index, objectList, movement_orientation,locked_on_target):
    launch_position = player_position + forward * 10
    new_missile = addMissile(launch_position, movement_orientation,locked_on_target,enemy=False)
    new_missile.name = "Missile " + str(missile_index + 1)
    objectList.append(new_missile)
    sound_manager.play(SoundType.MISSILE_LAUNCH)

def launch_enemy_missile(launch_position, forward,objectList,movement_orientation):
    launch_position = launch_position + forward * 10
    new_missile = addMissile(launch_position, movement_orientation,-1,enemy=True)
    new_missile.name = "Hostile Missile"
    objectList.append(new_missile)
    status.add_message(get_text('hostile_launched'), duration=3, type=0)
                      


def update_altitude_and_cabin_temp(player_position,movement_forward,planet_and_star,input_handler,main_loop_counter):
    if global_flags.game_state == global_flags.STATE_DOCKED:
        ship_data.altitude = 0
        ship_data.cabin_temp = 30
        return

    Alarm = (ship_data.altitude < 20) or (ship_data.cabin_temp > 228)

    if Alarm:
        if not sound_manager.is_playing(SoundType.ALARM):
            sound_manager.play(SoundType.ALARM,loops=-1)
    else:
        if sound_manager.is_playing(SoundType.ALARM):
            sound_manager.stop(SoundType.ALARM)

    planet_radius = planet_and_star.objects['planet'].radius
    planet_coords = player.current_system.planetCoords
    altitude = (global_flags.planet_distance - planet_radius)/planet_radius

    if altitude <= 0.0:
        ship_data.altitude = 0
        process_damage(planet_coords,player_position,movement_forward,50, main_loop_counter)
    elif altitude >= 2.0:
        ship_data.altitude = 255
    else:
        # Linear interpolation between 0.0 and 2.0
        ship_data.altitude = int(altitude * 127.5)

    if ship_data.altitude < 20:
        status.add_message(get_text('low_altitude'), duration=2, type=0)
    
    sun_radius = planet_radius
    sun_coords = player.current_system.sunCoords
    distance_to_sun = (global_flags.sun_distance - sun_radius)/sun_radius

    if distance_to_sun >= 3.0:
        ship_data.cabin_temp = 30
    elif distance_to_sun <= 0.5:
        ship_data.cabin_temp = 255
        process_damage(sun_coords,player_position,movement_forward,50, main_loop_counter)
    else:
        # Linear interpolation between distance 3.0 (temp 30) and 0.5 (temp 255)
        ship_data.cabin_temp = int(30 + (3.0 - distance_to_sun) * (255 - 30) / 2.5)

    if ship_data.cabin_temp > 228:
        status.add_message(get_text('high_temp'), duration=2, type=0)
    
    
    if distance_to_sun <= 0.8 and ship_data.fuel_scoops:
        process_fuel_scooping(input_handler)

def process_fuel_scooping(input_handler):
    speed = input_handler.current_speed
    if speed > 0:
        ship_data.fuel_level = min(ship_data.fuel_level + 0.1 * speed, 70)
        if ship_data.fuel_level <70:
            status.add_message(get_text('fuel_scooping'), duration=2, type=0)

def charge_shields_and_banks():
    #only charge shields if energy banks >50%
    if ship_data.energy_level>128.0:
        energy_drain=0
        for attr in ['forward_shield', 'aft_shield']:
            old_val = getattr(ship_data, attr)
            new_val = min(old_val + 1, 255)
            setattr(ship_data, attr, new_val)
            if new_val > old_val:
                energy_drain += 1
        
        ship_data.energy_level = max(ship_data.energy_level-energy_drain, 0)
      

    #charge energy banks, double charge speed if extra energy unit fitted, 3 x if also navy
    charge_unit =1
    if ship_data.extra_energy_unit:
        charge_unit+=1
    if ship_data.navy_energy_unit:
        charge_unit+=1
    
    ship_data.energy_level=min(ship_data.energy_level+charge_unit,256)      

def handle_explosion(obj, objectList, particleList,player_position,player_right, energy_bomb=False):
    create_explosion(obj, objectList, particleList,energy_bomb)
    sound_manager.play(SoundType.EXPLOSION)
    obj.ready_for_removal = True

    sound_manager.play_3d_sound(
                        SoundType.EXPLOSION,
                        obj.coords,
                        player_position,
                        player_right,
                        obj.distance_to_player
    )


def create_explosion(obj, objectList, particleList, energy_bomb, num_particles=200):
    # Assume obj has: nodes, faces, coords, orientation, etc.
    
    fragment=None
    if not energy_bomb:
        for frag in obj.fragments:
            fragment = object.Object(
                ship_dictionary=None,
                type = "fragment",
                name="fragment",
                nodes=frag["nodes"],
                faces=frag["faces"],
                detail=None,
                colors=frag["colors"],
                coords=obj.coords + np.random.normal(-1, 1, 3),  # Slightly offset from original
                rotation_inc=tuple(np.random.uniform(-0.1, 0.1, 3)),
                orientation=tuple(np.random.uniform(0, 2 * np.pi, 3)),
                forward_speed=np.random.uniform(1, 2)
            )
            # Set the fragment's normal explicitly for shading
            fragment.face_normals_model = np.array([frag["normal"], -frag["normal"]])
            # Add a random frame count for life
            fragment.frame_count_life = np.random.randint(20, 200)
            fragment.radar_color= [255, 255, 255]
            fragment.radar_rect_size = 2
            fragment.tumble_mode = True
            # Optionally, add other explosion-specific attributes
            objectList.append(fragment)

    #Particle effect
    if particleList is not None:
        explosion_center = obj.coords  # This should be a 3D np.array
        num_particles = obj.explosion_count*20
        for _ in range(num_particles):
            velocity = np.random.uniform(-2, 2, 3)  # 3D velocity
            color = (255, np.random.randint(128, 255), 0)
            size = np.random.uniform(1, 4)
            lifetime = np.random.randint(20, 60)
            particle = Particle(explosion_center.copy(), velocity, color, size, lifetime)
            particleList.append(particle)  


def process_kill(object,objectList):
    old_points = player.kills
    player.kills += object.kill_points
    new_points = player.kills

    if math.floor(new_points/250) > math.floor(old_points/250):
        status.add_message(get_text('right_on'), duration=10)
       
    if object.is_a_cop:
        player.FIST = min(player.FIST + 64, 256)
    
    if object.bounty > 0:
        player.credits += object.bounty
        status.add_message(f"{get_text('bounty_collected')}: {object.bounty} {get_text('Cr')}", duration=3)

    if object.name=="Constrictor" and player.mission_number == 1 and player.mission_status==MissionStatus.IN_PROGRESS:
        player.mission_status=MissionStatus.SUCCESS
        status.add_message(get_text('mission_completed'), duration=5)

    #check for jettisoned cargo/alloy plates
    if object.maximum_canisters_on_demise >0:
        maybe_jettison(object, "Cargo canister", objectList)
        maybe_jettison(object, "Alloy plate", objectList)
        
def maybe_jettison(parent_object,item_type,objectList):
    value = random.randint(0, 255)
    if value & 128: #50% chance of something being jettisoned
        count = parent_object.maximum_canisters_on_demise & value
        count = count & 15
        if count > 0:
            for _ in range(count):

                coords = parent_object.coords + np.random.normal(-5, 5, 3)
                orientation = tuple(np.random.uniform(0, 2 * np.pi, 3))
                rotation_inc = tuple(np.random.uniform(-0.02, 0.02, 3))
                forward_speed = np.random.uniform(0.0, 1.0)
                new_object = addShip(item_type, coords, rotation_inc=rotation_inc, orientation=orientation, forward_speed=forward_speed)
                new_object.tumble_mode = True
                objectList.append(new_object)

    

def check_laser_hit(objectList,particleList, player_position,player_right, screen_center,focal_length,laser_power,laser_type):
    for obj in objectList:
        if obj.is_visible and obj.type != "fragment" and obj.distance_to_player < game_constants.LASER_MAX_DISTANCE:
                dx = obj.screen_pos[0] - screen_center[0]
                dy = obj.screen_pos[1] - screen_center[1]
                distance_from_center = np.sqrt(dx**2 + dy**2)
                obj_distance = np.linalg.norm(obj.coords - player_position)
                apparent_radius = max(2, int(obj.collision_radius * focal_length / obj_distance))
                if distance_from_center - apparent_radius <= 0:  # within targeting reticle
                    if obj.type == "station":
                        sound_manager.play(SoundType.LASER_HIT)
                        global_flags.station_is_hostile = True
                    elif obj.type == "missile":
                        sound_manager.play(SoundType.LASER_HIT)
                        handle_explosion(obj, objectList, particleList,player_position,player_right)

                        if not obj.enemy:
                            obj.locked_on_target.locked_on_missile_index =-1
                    else:    
                        #Constrictor & Cougar take reduced damage and can only be hit by Military lasers.
                        if obj.name=="Constrictor" or obj.name=="Cougar":
                            if laser_type == LaserType.MILITARY:
                                obj.energy -= laser_power/4    
                        else:        
                            obj.energy -= laser_power

                        sound_manager.play(SoundType.LASER_HIT)
                        
                       
                        if obj.aggression>0:
                            obj.just_been_hit = True
                            #enable AI, give object a kick of speed and make it pitch up
                            if not obj.is_hostile:
                                obj.acceleration = 0.2
                                obj.agression =36
                                obj.is_hostile = True
                                obj.is_docking = False
                        
                        if obj.is_innocent and global_flags.is_in_space_station_zone:
                            global_flags.station_is_hostile = True      
                   

                        if obj.energy <=0:
                            check_missile_targets( obj,objectList)
                            handle_explosion(obj, objectList, particleList,player_position,player_right)
                            process_kill(obj,objectList)
                            if obj.type == "asteroid" and laser_type == LaserType.MINING:
                               spawn_asteroid_fragments(obj, objectList)

def spawn_asteroid_fragments(asteroid, objectList):
    num_fragments = random.randint(0, 3)
    for _ in range(num_fragments):
        coords = asteroid.coords + np.random.normal(-3, 3, 3)
        orientation = tuple(np.random.uniform(0, 2 * np.pi, 3))
        rotation_inc = tuple(np.random.uniform(-0.05, 0.05, 3))
        forward_speed = np.random.uniform(0.0, 0.5)
        new_fragment = addShip("Splinter", coords, rotation_inc=rotation_inc, orientation=orientation, forward_speed=forward_speed)
        new_fragment.tumble_mode = True
        objectList.append(new_fragment)

def handle_energy_bomb(objectList, particleList, player_position, player_right):
    for obj in objectList:
        if obj.type != "fragment" and obj.type != "station":
            if obj.distance_to_player <= global_flags.energy_bomb_radius:
                handle_explosion(obj, objectList, particleList,player_position,player_right,energy_bomb=True)
                process_kill(obj,objectList)
    return

def handle_escape_pod():
    player.FIST = 0.0  # Reset FIST on escape pod launch
    player.cargo_inventory = []  # Clear cargo inventory

def calculate_badness_level():
    #adjust legal status if carrying contrand items
    contraband=0
    for item in player.cargo_inventory:
        if item['name']=="Narcotics":
            contraband+=item['quantity']*2
        elif item['name']=="Slaves":
            contraband+=item['quantity']*2    
        elif item['name']=="Firearms":
            contraband+=item['quantity']

    return contraband        

def reset_ship():
    ship_data.altitude = 0
    ship_data.cabin_temp = 30
    ship_data.energy_level = 256
    ship_data.forward_shield = 255
    ship_data.aft_shield = 255

def check_jump_end_point(player_position, forward,planet_and_star):
    # 2. Altitude of endpoint > 1.5 planetary radii
    # Estimate jump endpoint as player_position + forward * short_range_jump_distance
    jump_distance = global_flags.short_range_jump_distance

    jump_endpoint = np.array(player_position) + np.array(forward) * jump_distance
    # Find planet object
    planet_radius = planet_and_star.objects['planet'].radius
    planet_coords = player.current_system.planetCoords
    altitude = np.linalg.norm(jump_endpoint - planet_coords)
    
    if altitude < 1.5 * planet_radius:
        status.add_message(f"{get_text('too_near_planet')} {int(altitude)})", duration=2, type=0)
        sound_manager.play(SoundType.ERROR)
        return False
    
    sun_radius = planet_and_star.objects['sun'].radius
    sun_coords =player.current_system.sunCoords
    altitude = np.linalg.norm(jump_endpoint - sun_coords)
    
    if altitude < 1.5 * sun_radius:
        status.add_message(f"{get_text('too_near_sun')} {int(altitude)})", duration=2, type=0)
        sound_manager.play(SoundType.ERROR)
        return False
    
    
    return True

def get_remaining_cargo_capacity():
    if ship_data.large_cargo_bay:
        capacity=35000000
    else:
        capacity=20000000

    remaining_capacity=(capacity - player.inventory_weight)
    return remaining_capacity       


   
def spawn_new_objects(objectList, player_position, movement_orientation, main_loop_counter):
    random_value = random.randint(0, 255)
    asteroids_maxed_out=False
    if random_value < 35:                               #13% chance
        if random.choice([True, False]):                    #50% chance asteroid or cannister : 50% trader
            if random.random()<0.012:
                #print("Rock hermit")
                spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=3000, vertical_range=3000)  
                spawn_junk(spawn_coords, objectList,"Rock hermit")
                return                     

            if random.random()<0.985:                           #98.5% chance asteroid
                asteroids = sum(1 for obj in objectList if obj.type == "asteroid")
                if asteroids<game_constants.MAX_ASTEROIDS:
                    #print("spawn asteroid")
                    spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=3000, vertical_range=3000)  
                    spawn_junk(spawn_coords, objectList,"Asteroid")   
                else:
                    asteroids_maxed_out=True     
            else:
                #print("spawn cannister")                        #1.5% chance cannister
                spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=3000, vertical_range=3000) 
                spawn_junk(spawn_coords, objectList, "Cargo canister")
        
        else:                                           #87% chance
            traders = ("Cobra Mk III", "Python", "Boa", "Anaconda")
            ship = traders[random.randint(0,3)]
            #print(f"spawn Trader: {ship}")
            ECM = random.choice([True, False])
            docking = random.choice([True, False])
            aggression = random.randint(0,63)  
            spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=3000, vertical_range=3000)  
            spawn_trader_or_hunter(spawn_coords, objectList,ship, aggression, ECM, docking)
            

    if random_value>=35 or asteroids_maxed_out:
       
        if not global_flags.is_in_space_station_zone:
            badness = calculate_badness_level() *2
            if any(obj.is_a_cop for obj in objectList):
                badness = (int(player.FIST) | (badness & 0xFF)) & 0xFF
            if random.randint(0,255)<badness:
                
                ship = "Viper"
                #print(f"spawn a cop {ship}")
                ECM=random.random() < 0.04
                aggression = random.randint(32,63) 
                spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                spawn_cop_in_space( spawn_coords, objectList,ship, aggression, ECM)
                
            else:
                global_flags.extra_vessels_counter-=1
                if global_flags.extra_vessels_counter<0:
                    global_flags.extra_vessels_counter=0
                    random_value = random.randint(0,255)
                    gov_check =random_value & 7
                    if player.mission_number==2 and player.mission_status==MissionStatus.GOT_PLANS and random_value >=200:
                        #maybe spawn a Thargoid as this is the Thargoid mission and we've gfot the plans!.
                        ship="Thargoid"
                        #(f"spawn Special {ship}")
                        spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                        spawn_thargoid(spawn_coords, objectList)
                        global_flags.extra_vessels_counter+=2

                    elif (random_value<90 and gov_check>=player.current_system.government) or player.current_system.government==0:
                        random_value = random.randint(0,255)
                        if random_value<100:
                            if player.mission_number==1 and player.mission_status==MissionStatus.IN_PROGRESS and player.current_system.name == "ORARRA":
                                if not any(obj.name == "Constrictor" for obj in objectList):
                                    ship="Constrictor"
                                    print(f"spawn Special {ship}")
                                    aggression =63
                                    ECM = True
                                    docking = False
                                    spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                                    spawn_trader_or_hunter(spawn_coords, objectList,ship, aggression, ECM, docking)
                                    global_flags.extra_vessels_counter+=1
                            else:        
                                hunters = ("Cobra Mk III (pirate)", "Asp Mk II", "Python (pirate)", "Fer-de-Lance", "Moray", "Special")
                                ship = hunters[random.randint(0,5)]
                                if ship=="Special":
                                    if random.random()<0.968:
                                        ship="Thargoid"
                                        #(f"spawn Special {ship}")
                                        spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                                        spawn_thargoid(spawn_coords, objectList)
                                        global_flags.extra_vessels_counter+=2
                                    else:
                                        ship="Cougar"
                                        #print(f"spawn Special {ship}")
                                        aggression = 32
                                        ECM = True
                                        docking = False
                                        spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                                        spawn_trader_or_hunter(spawn_coords, objectList,ship, aggression, ECM, docking)
                                        global_flags.extra_vessels_counter+=1
                                else:
                                    #print(f"spawn Bounty hunter: {ship}")
                                    ECM = random.random() < 0.22
                                    aggression = random.randint(32,63)
                                    docking = False
                                    spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)  
                                    spawn_trader_or_hunter(spawn_coords, objectList,ship, aggression, ECM, docking,is_a_bounty_hunter=True)
                                    global_flags.extra_vessels_counter+=1
                            
                        else:    
                            offset_array = [[0, 0, 0],  
                                            [-50, -50, -50],  
                                            [-50, 50, 50],  
                                            [50, -50, 0]] 
                            
                            num_pirates = random.randint(1,4)
                            pirates = ("Sidewinder", "Mamba", "Krait", "Adder", "Gecko", "Cobra Mk I", "Worm", "Cobra Mk III (pirate)")
                            spawn_coords = get_spawn_coords(player_position, movement_orientation, min_distance=6500, max_distance=7400, side_range=2000, vertical_range=2000)
                            aggression = random.randint(32,63)
                            
                            forward_speed = random.uniform(2.0, 2.5)
                            for i in range(num_pirates):
                                ship = pirates[random.randint(0,7)]
                                #print(f"spawn Pirate: {ship}")
                                new_spawn_coords = spawn_coords + offset_array[i]
                                spawn_pirates(new_spawn_coords,player_position, forward_speed,objectList,ship, aggression)

                            global_flags.extra_vessels_counter+=num_pirates

def get_spawn_coords(player_position, movement_orientation, min_distance=6000, max_distance=7200, side_range=2000,vertical_range=2000):
    forward = movement_orientation.apply([0, 0, 1])
    right = movement_orientation.apply([1, 0, 0])
    up = movement_orientation.apply([0, 1, 0])

    # Spawn in front, but offset to the side and up/down
    forward_distance = random.uniform(min_distance, max_distance)
    side_offset = np.random.uniform(-side_range, side_range)  # Random left/right
    vertical_offset = np.random.uniform(-vertical_range, vertical_range)  # Random up/down

    spawn_coords = (player_position + 
                    forward_distance * forward + 
                    side_offset * right + 
                    vertical_offset * up)
    return spawn_coords

def get_orientation_towards_player(from_position, player_position):
    direction = np.array(player_position) - np.array(from_position)
    direction = direction / np.linalg.norm(direction)
    # Find rotation from port_normal to direction
    result = R.align_vectors([direction], [[0,0,1]])
    rot = result[0]
    return rot.as_euler('xyz')  # or rot.as_quat() for quaternion


def spawn_junk(spawn_coords,objectList, name):
    
    rotation_inc = tuple(np.random.uniform(-0.02, 0.02, 3))
    forward_speed = np.random.uniform(0.0, 0.5)
    if name == "Cargo canister":
        new_junk = addShip("Cargo canister", spawn_coords, rotation_inc=rotation_inc, forward_speed=forward_speed)
    elif name=="Asteroid":
        new_junk = addShip("Asteroid", spawn_coords, rotation_inc=rotation_inc, forward_speed=forward_speed)
    else:
        new_junk = addShip("Rock hermit", spawn_coords, rotation_inc=rotation_inc, forward_speed=forward_speed)
    
    new_junk.tumble_mode = True
    objectList.append(new_junk)
   
def spawn_trader_or_hunter(spawn_coords, objectList,ship_name, aggression, has_ecm, docking,is_a_bounty_hunter=False):
    if ship_maxium_reached(objectList):
        #print("Ship maximum reached, not spawning new trader/hunter")
        return
    
    orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
    rotation_inc = (0.00,0.0,0.0)
    forward_speed = random.uniform(1.0, 2.5)
    new_ship = addShip(ship_name, spawn_coords,  rotation_inc=rotation_inc, initial_rotation=orientation, forward_speed=forward_speed)
    new_ship.is_a_cop = False
    new_ship.aggression = aggression
    new_ship.has_ecm = has_ecm
    new_ship.is_docking = docking
    new_ship.is_a_bounty_hunter = is_a_bounty_hunter
    objectList.append(new_ship)

def spawn_escape_pod(spawn_coords, objectList):
    orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
    rotation_inc = (0.00,0.0,0.0)
    forward_speed = random.uniform(1.0, 2.5)
    new_ship = addShip("Escape pod", spawn_coords,  rotation_inc=rotation_inc, initial_rotation=orientation, forward_speed=forward_speed)
    new_ship.is_a_cop = False
    new_ship.aggression = 0
    new_ship.has_ecm = False
    new_ship.is_docking = False
    objectList.append(new_ship)


def spawn_ship_from_station(spawn_coords, objectList,ship_name, aggression, has_ecm, speed,orientation):
    if ship_maxium_reached(objectList):
        #print("Ship maximum reached, not spawning ship from station")
        return
    
    rotation_inc = (0.00,0.0,0.0)
    forward_speed = speed
    new_ship = addShip(ship_name, spawn_coords,   rotation_inc=rotation_inc, initial_rotation=orientation,  forward_speed=forward_speed)
    if ship_name=="Viper":
        new_ship.is_a_cop = True
        new_ship.is_hostile = True
    else:
        new_ship.is_a_cop = False
    new_ship.aggression = aggression
    new_ship.has_ecm = has_ecm
    new_ship.is_docking = False
    objectList.append(new_ship)



def spawn_cop_in_space(spawn_coords, objectList,ship_name, aggression, has_ecm):
    if ship_maxium_reached(objectList):
        #print("Ship maximum reached, not spawning new cop")
        return
    
    orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
    rotation_inc = (0.00,0.0,0.0)
    forward_speed = random.uniform(0.5, 2.5)
    new_ship = addShip(ship_name, spawn_coords, rotation_inc=rotation_inc, initial_rotation=orientation, forward_speed=forward_speed)
    new_ship.is_a_cop = True
    new_ship.aggression = aggression
    new_ship.has_ecm = has_ecm
    new_ship.is_hostile = True
    objectList.append(new_ship)

def spawn_pirates(spawn_coords,player_position, forward_speed, objectList,ship_name, aggression):
    if ship_maxium_reached(objectList):
        #("Ship maximum reached, not spawning new pirate")
        return
    
    orientation = get_orientation_towards_player(spawn_coords, player_position)
    rotation_inc = (0.0, 0.0, random.uniform(-0.01, 0.01))
    new_ship = addShip(ship_name, spawn_coords, initial_rotation=orientation,rotation_inc=rotation_inc, forward_speed=forward_speed)
    
    new_ship.is_a_cop = False
    new_ship.aggression = aggression
    new_ship.has_ecm = False
    new_ship.is_docking = False
    objectList.append(new_ship)

def ship_maxium_reached(objectList):
    ship_count = sum(1 for obj in objectList if obj.type == "ship")
    if ship_count>=game_constants.MAX_SHIPS_IN_GAME:
        return True
    return False

def spawn_thargoid(spawn_coords, objectList):
    if ship_maxium_reached(objectList):
        #print("Ship maximum reached, not spawning new Thargoid")
        return
    
    orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
    rotation_inc = (0.01,0.0,0.0)
    forward_speed = random.uniform(0.5, 2.5)
    new_ship = addShip("Thargoid", spawn_coords, rotation_inc=rotation_inc, initial_rotation=orientation, forward_speed=forward_speed)
    new_ship.is_a_cop = False
    new_ship.aggression = 63
    new_ship.has_ecm = True
    new_ship.is_docking = False
    new_ship.missile_count -= 1
    objectList.append(new_ship)

    thargon_coords = spawn_coords + np.random.uniform(20, 30, 3)
    orientation=tuple(np.random.uniform(0, 2 * np.pi, 3))
    rotation_inc = (0.00,0.0,0.0)
    forward_speed = random.uniform(2.0, 2.5)
    thargon = addShip("Thargon", thargon_coords, rotation_inc=rotation_inc, orientation=orientation, forward_speed=forward_speed)
    thargon.has_ecm = False
    objectList.append(thargon)

def untarget_missiles():
    global_flags.targeting_missile = False
    if sound_manager.is_playing(SoundType.LOCKED_ON):
        sound_manager.stop(SoundType.LOCKED_ON)
    if sound_manager.is_playing(SoundType.TARGETING):
            sound_manager.stop(SoundType.TARGETING)    
    
    for i, missile in enumerate(ship_data.missile_status):
        if missile == MissileStatus.LOCKED_ON or missile == MissileStatus.TARGETING:
            ship_data.missile_status[i] = MissileStatus.PRESENT
            if missile == MissileStatus.LOCKED_ON:
                status.add_message(get_text('target_lost'), duration=2, type=0)
     
def mission_complete_actions():
    mission = player.mission_number
    if mission == 1:
       player.credits += 5000
       player.kills += 256
       
    elif mission == 2:
        ship_data.navy_energy_unit=True
       
   
    player.mission_status=MissionStatus.COMPLETED
