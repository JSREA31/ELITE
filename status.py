from enum import Enum
import pygame
pygame.font.init()
import system_data
import time
from sounds import SoundType

class LaserType(Enum):
    NOT_PRESENT = 0
    PULSE = 1
    BEAM = 2
    MILITARY = 3
    MINING = 4


class MissionStatus(Enum):
    NOT_STARTED = 0
    BRIEFING = 1
    IN_PROGRESS = 2
    GOT_PLANS = 3   #mission 2 only
    SUCCESS = 4
    COMPLETED = 5

class GlobalFlags:
    def __init__(self):
        self.reset()
    def reset(self):    
        self.FULLSCREEN = False
        self.DEBUG_MODE = False
        self.wireframe_mode = False
        self.STATE_DOCKED = 0
        self.STATE_DOCKING = 1
        self.STATE_LAUNCHING = 2
        self.STATE_FLYING = 3 
        self.STATE_HYPERSPACE_JUMPING = 4
        self.ESCAPE_POD_LAUNCHED = 5
        self.STATE_TITLE_SCREEN = 6
        self.STATE_GAME_OVER = 7
        self.STATE_SHORT_RANGE_JUMPING = 8
        
        self.next_face = False  # For debugging wireframe face order
        self.red_face=-1

        self.is_in_space_station_zone = False
        self.station_distance = 0.0
        self.planet_distance = 0.0
        self.sun_distance = 0.0
        self.just_jumped = False
        self.in_hyperspace_countdown = False
        self.in_hyperspace_countdown_start = 0.0
        self.game_state = self.STATE_DOCKED  # Initial game state
        self.text_input_active = False
        self.hyperspace_is_galactic=False
        self.reset_game=False
        self.targeting_missile = False
        self.locked_on_target = None
        self.locked_on_frame_count = 0

        self.station_is_hostile = False

        self.ecm_active = False
        self.ecm_counter=0
        self.ecm_duration = 100
        self.ecm_is_enemy = False

        self.firing_laser = False
        self.draw_laser = False
        self.laser_frame_end = 0

        self.frame_start =0

        self.energy_bomb_activated = False
        self.energy_bomb_frame_start =0
        self.energy_bomb_frames = 70
        self.energy_bomb_flicker=2
        self.energy_bomb_radius = 5000
        
        self.short_range_jump_distance = 65536/2
        self.warp_effect_frames = 25
        self.warp_movement_per_frame=20

        self.extra_vessels_counter=0

        self.radar_zoom_values = [100,50,25]
        self.radar_zoom_index = 2
        self.radar_zoom_direction = 1

        self.message_seen = False
        self.accept_input = True
        self.alert_on = False
        self.message_refresh = False

        self.is_paused = False

        self.laser_params ={
        LaserType.PULSE: {
            "frame_duration": 5,
            "temp_increase": 18,
            "sound": SoundType.PULSE_LASER,
            "off_frames": 15,
            "check_off": True,
            "laser_power": 15,
        },
        LaserType.BEAM: {
            "frame_duration": 10,
            "temp_increase": 6,
            "sound": SoundType.BEAM_LASER,
            "off_frames": 0,
            "check_off": False,
            "laser_power": 15,
        },
        LaserType.MILITARY: {
            "frame_duration": 8,
            "temp_increase": 5,
            "sound": SoundType.MILITARY_LASER,
            "off_frames": 0,
            "check_off": False,
            "laser_power": 23,
        },
        LaserType.MINING: {
            "frame_duration": 120,
            "temp_increase": 90,
            "sound": SoundType.MINING_LASER,
            "off_frames": 0,
            "check_off": False,
            "laser_power": 50,
        },
    }


    @property
    def is_docking(self):
        return self.game_state == self.STATE_DOCKING    

    @property
    def is_title_screen(self):
        return self.game_state == self.STATE_TITLE_SCREEN

    @property
    def is_game_over(self):
        return self.game_state == self.STATE_GAME_OVER

    @property
    def is_launching(self):
        return self.game_state == self.STATE_LAUNCHING
    
    @property
    def is_escape_pod_launched(self):
        return self.game_state == self.ESCAPE_POD_LAUNCHED

    @property
    def is_hyperspace_jumping(self):
        return self.game_state == self.STATE_HYPERSPACE_JUMPING
    
    @property
    def is_flying(self):
        return self.game_state == self.STATE_FLYING
    
    @property
    def is_docked(self):
        return self.game_state == self.STATE_DOCKED
  
    @property
    def is_short_range_jumping(self):
        return self.game_state == self.STATE_SHORT_RANGE_JUMPING
    
global_flags = GlobalFlags()

nearby_systems = []

font_file="fonts/bitwise.ttf"
def load_fonts():
    
    return {
        "small": pygame.font.Font(font_file, 14),
        "header": pygame.font.Font(font_file, 20),
        "body": pygame.font.Font(font_file, 16),
        "large": pygame.font.Font(font_file, 24),
        "xlarge": pygame.font.Font(font_file, 64),
        # Add more as needed
    }

FONTS = load_fonts()

class GameConstants:
    def __init__(self):
        self.SPACE_STATION_ZONE_RADIUS = 65536  #radius for space station zone
        self.LOCKED_ON_FRAMES_REQUIRED = 30  # Number of frames required to lock on a target
        self.CRASH_DAMAGE_AMOUNT = 200  # Damage amount on collision per frame
        self.MISSILE_IMPACT_DAMAGE = 250  # Damage caused by missile impact
        self.MISSILE_BLAST_DAMAGE =80 # Damage caused by missile blast radius
        self.MISSILE_BLAST_RADIUS = 512 # Radius of missile blast effect
        self.LASER_HIT_ANGLE = 5  # Degrees within which a laser can hit player
        self.LASER_ROUGH_ANGLE = 25  # Rough angle for laser firing
        self.LASER_MAX_DISTANCE = 3000  # Max distance for laser to hit
        self.MAX_OBJECT_DISTANCE = 65536 * 2  # Max distance for objects to be active
        self.MAX_MISSILE_TARGET_DISTANCE = 5000  # Max distance for missile targeting
        self.MIN_DISTANCE_TO_PLAYER = 300 # Minimum distance to player for AI ships to turn away
        self.MAX_DISTANCE_TO_PLAYER = 4000 # Distance at which AI ships might consider turning to attack
        self.ECM_EFFECTIVE_RANGE = 500  # Effective range for ECM
        self.MAX_ASTEROIDS = 3
        self.MAX_SHIPS_IN_GAME = 10
        self.TACTICS_SLOTS = 20
        self.SPAWN_INTERVAL = 400
        self.STATION_MAX_COPS = 7
        self.MAX_ROCK_HERMIT_SPAWNS = 1
        self.RADAR_RANGE = 7400  # Radar detection range

game_constants = GameConstants()

class MissileStatus(Enum):
    NOT_PRESENT = 0
    PRESENT = 1
    TARGETING = 2
    LOCKED_ON = 3


class LaserLocation(Enum):
    FRONT = 0
    BACK = 1
    LEFT = 2
    RIGHT = 3

class ShipData:
    def __init__(self):
        self.reset()
    def reset(self):
        self.energy_level = 256.0
        self.forward_shield = 255.0
        self.aft_shield = 255.0
        self.fuel_level = 70.0
        self.cabin_temp = 0.0
        self.laser_temp = 0.0
        self.altitude = 255.0
        self.missile_status = [MissileStatus.PRESENT] * 4
        self.missile_status[3] = MissileStatus.NOT_PRESENT  # Fourth missile not present
        self.lasers=[LaserType.NOT_PRESENT]*4
        self.lasers[LaserLocation.FRONT.value]=LaserType.PULSE
        self.lasers[LaserLocation.BACK.value]=LaserType.NOT_PRESENT
        self.lasers[LaserLocation.LEFT.value]=LaserType.NOT_PRESENT
        self.lasers[LaserLocation.RIGHT.value]=LaserType.NOT_PRESENT
        self.escape_capsule = False
        self.fuel_scoops = False
        self.ECM_System = False
        self.energy_bomb = False
        self.extra_energy_unit = False
        self.navy_energy_unit = False
        self.docking_computer = False
        self.galactic_hyperdrive = False
        self.large_cargo_bay = False

ship_data = ShipData()

class PlayerStatus:
    def __init__(self):
        self.reset()
    def reset(self):
        self.galaxy_number=0
        self.all_systems = system_data.get_all_system_data(self.galaxy_number)
        self.current_system=self.all_systems[7]
        self.selected_system=self.current_system
        self.short_range_xy=self.current_system.x,self.current_system.y
        self.galactic_xy = self.current_system.x, self.current_system.y
        self.galaxy_selected_system = self.current_system
        self.info_screen_page=6
        self.distance_to_selected = 0.0
        self.galaxy_distance_to_selected =0
        self.name = "Jameson"
        self.FIST=0.0
        self.kills=0.0
        self.credits=100.0
        self.random_market_factor=0
        self.market_data = []
        self.cargo_inventory=[]
        self.inventory_weight=0.0
        self.mission_number = 0
        self.mission_status = MissionStatus.NOT_STARTED
        


player = PlayerStatus()

# Global message list for player messages
message_list = []
current_message_index = 0
current_message_start_time = 0.0

def add_message(msg, duration=2, type=0):
    """Append a new message to the global message_list."""
    msg_str = str(msg)
    # Check if message already exists in the list
    for existing_msg, _, _, _ in message_list:
        if existing_msg == msg_str:
            return  # Don't add duplicate   
    message_list.append((str(msg), duration, time.time(),type))

def clean_old_messages(timeout=3):
    now = time.time()
    message_list[:] = [(m, d, t, ty) for m, d, t, ty in message_list if now - t < d]

def clear_messages():
    """Clear all messages from the global message_list."""
    message_list.clear()        

# --- Game Save/Load Functions ---
import json

def ship_data_to_dict():
    return {
        "energy_level": ship_data.energy_level,
        "forward_shield": ship_data.forward_shield,
        "aft_shield": ship_data.aft_shield,
        "fuel_level": ship_data.fuel_level,
        "cabin_temp": ship_data.cabin_temp,
        "laser_temp": ship_data.laser_temp,
        "altitude": ship_data.altitude,
        "missile_status": [ms.value for ms in ship_data.missile_status],
        "lasers": [lt.value for lt in ship_data.lasers],
        "escape_capsule": ship_data.escape_capsule,
        "fuel_scoops": ship_data.fuel_scoops,
        "ECM_System": ship_data.ECM_System,
        "energy_bomb": ship_data.energy_bomb,
        "extra_energy_unit": ship_data.extra_energy_unit,
        "navy_energy_unit": ship_data.navy_energy_unit,
        "docking_computer": ship_data.docking_computer,
        "galactic_hyperdrive": ship_data.galactic_hyperdrive,
        "large_cargo_bay": ship_data.large_cargo_bay,
    }

def player_to_dict():
    return {
        "galaxy_number": player.galaxy_number,
        "current_system_index": getattr(player.current_system, "number", 0),
        "selected_system_index": getattr(player.selected_system, "number", 0),
        "short_range_xy": player.short_range_xy,
        "galactic_xy": player.galactic_xy,
        "info_screen_page": player.info_screen_page,
        "distance_to_selected": player.distance_to_selected,
        "galaxy_distance_to_selected": player.galaxy_distance_to_selected,
        "name": player.name,
        "FIST": player.FIST,
        "kills": player.kills,
        "credits": player.credits,
        "random_market_factor": player.random_market_factor,
        "market_data": player.market_data,
        "cargo_inventory": player.cargo_inventory,
        "inventory_weight": player.inventory_weight,
        "mission_number": player.mission_number,
        "mission_status": player.mission_status.value,
    }

def save_game_to_json(filename):

    data = {
        "ship_data": ship_data_to_dict(),
        "player": player_to_dict(),
    }
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_game_from_json(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    # Restore ship_data
    sd = data.get("ship_data", {})
    ship_data.energy_level = sd.get("energy_level", ship_data.energy_level)
    ship_data.forward_shield = sd.get("forward_shield", ship_data.forward_shield)
    ship_data.aft_shield = sd.get("aft_shield", ship_data.aft_shield)
    ship_data.fuel_level = sd.get("fuel_level", ship_data.fuel_level)
    ship_data.cabin_temp = sd.get("cabin_temp", ship_data.cabin_temp)
    ship_data.laser_temp = sd.get("laser_temp", ship_data.laser_temp)
    ship_data.altitude = sd.get("altitude", ship_data.altitude)
    ship_data.missile_status = [MissileStatus(ms) for ms in sd.get("missile_status", [ms.value for ms in ship_data.missile_status])]
    ship_data.lasers = [LaserType(lt) for lt in sd.get("lasers", [lt.value for lt in ship_data.lasers])]
    ship_data.escape_capsule = sd.get("escape_capsule", ship_data.escape_capsule)
    ship_data.fuel_scoops = sd.get("fuel_scoops", ship_data.fuel_scoops)
    ship_data.ECM_System = sd.get("ECM_System", ship_data.ECM_System)
    ship_data.energy_bomb = sd.get("energy_bomb", ship_data.energy_bomb)
    ship_data.extra_energy_unit = sd.get("extra_energy_unit", ship_data.extra_energy_unit)
    ship_data.navy_energy_unit = sd.get("navy_energy_unit", ship_data.navy_energy_unit)
    ship_data.docking_computer = sd.get("docking_computer", ship_data.docking_computer)
    ship_data.galactic_hyperdrive = sd.get("galactic_hyperdrive", ship_data.galactic_hyperdrive)
    ship_data.large_cargo_bay = sd.get("large_cargo_bay", ship_data.large_cargo_bay)

    # Restore player
    pd = data.get("player", {})
    player.galaxy_number = pd.get("galaxy_number", player.galaxy_number)
    player.all_systems = system_data.get_all_system_data(player.galaxy_number)
    # Restore system references by index if possible
    all_systems = player.all_systems
    cs_idx = pd.get("current_system_index", getattr(player.current_system, "number", 0))
    ss_idx = pd.get("selected_system_index", getattr(player.selected_system, "number", 0))
    if all_systems and 0 <= cs_idx < len(all_systems):
        player.current_system = all_systems[cs_idx]
    if all_systems and 0 <= ss_idx < len(all_systems):
        player.selected_system = all_systems[ss_idx]
    player.short_range_xy = tuple(pd.get("short_range_xy", player.short_range_xy))
    player.galactic_xy = tuple(pd.get("galactic_xy", player.galactic_xy))
    player.info_screen_page = pd.get("info_screen_page", player.info_screen_page)
    player.distance_to_selected = pd.get("distance_to_selected", player.distance_to_selected)
    player.galaxy_distance_to_selected = pd.get("galaxy_distance_to_selected", player.galaxy_distance_to_selected)
    player.name = pd.get("name", player.name)
    player.FIST = pd.get("FIST", player.FIST)
    player.kills = pd.get("kills", player.kills)
    player.credits = pd.get("credits", player.credits)
    player.random_market_factor = pd.get("random_market_factor", player.random_market_factor)
    player.market_data = pd.get("market_data", player.market_data)
    player.cargo_inventory = pd.get("cargo_inventory", player.cargo_inventory)
    player.inventory_weight = pd.get("inventory_weight", player.inventory_weight)
    player.mission_number = pd.get("mission_number", player.mission_number)
    player.mission_status = MissionStatus(pd.get("mission_status", player.mission_status.value))


