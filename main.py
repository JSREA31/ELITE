import pygame


pygame.init()
pygame.font.init()
import time
import object
import wireframes
import ogl_render
import sys
import numpy as np
from status import global_flags, player,ship_data, game_constants,clear_messages
from scipy.spatial.transform import Rotation as R
from OpenGL.GL import (glMatrixMode, glLoadIdentity, glClear, GL_PROJECTION, GL_MODELVIEW, GL_COLOR_BUFFER_BIT, GL_ALL_ATTRIB_BITS, glClearColor)
from OpenGL.GLU import (gluOrtho2D)
from ogl_render import render_launch_tunnel
import info_screens
import game_events
from debug_overlay import show_debug_overlay

info_screen_renderers = {
    1: info_screens.render_buy_cargo_page,
    2: info_screens.render_sell_cargo_page,
    3: info_screens.render_equip_ship_page,
    4: info_screens.render_galactic_chart,
    5: info_screens.render_short_range_chart,
    6: info_screens.render_system_data,
    7: info_screens.render_market_prices,
    8: info_screens.render_status_page,
    9: info_screens.render_inventory_page,
    10: info_screens.render_save_game_page,
    11: info_screens.render_load_game_page,
    12: info_screens.render_mission_page,
    13: info_screens.render_incoming_message_page,
    14: info_screens.render_mission_complete_page
}

# Pygame set up
# for windowed mode 

pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)


if global_flags.FULLSCREEN:
    screen = pygame.display.set_mode((0, 0),pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.OPENGL)
    WIDTH,HEIGHT=pygame.display.get_window_size()
else:
    WIDTH, HEIGHT = 1000, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.OPENGL | pygame.SRCALPHA)
    

screen_center = (WIDTH // 2, HEIGHT // 2)
focal_length = 900


pygame.display.set_caption("Pygame Game Window")

# Set up 2D projection
glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluOrtho2D(0, WIDTH, HEIGHT, 0)  # Set up coordinate system (0 to WIDTH in x, HEIGHT to 0 in y) to match PyGame
glMatrixMode(GL_MODELVIEW)
glLoadIdentity()
glClearColor(0.0, 0.0, 0.0, 1.0)  # Black background


# Initialize cockpit console and input handler
player_position, movement_orientation, look_orientation, input_handler, cockpit_console, movement_forward, movement_right, movement_up, direction_text = game_events.newGameView(WIDTH,HEIGHT)

#initialize game data
planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield, particleList = game_events.newGameObjects(player_position)

clock = pygame.time.Clock()
running = True
main_loop_counter=0
sum_fps = 0.0

global_flags.game_state = global_flags.STATE_TITLE_SCREEN
player.info_screen_page = 0

# Initialize view_matrix with identity as a safe default
look_forward, look_right, look_up = input_handler.update_axes(look_orientation)
player_target = player_position + look_forward
_, player_right, _ = input_handler.update_axes(look_orientation)

while running:
    
    if global_flags.energy_bomb_activated:
        frame = main_loop_counter - global_flags.energy_bomb_frame_start
        if frame < global_flags.energy_bomb_frames:
            # Flicker: alternate every energy_bomb_flicker frames
            if (frame // global_flags.energy_bomb_flicker) % 2 == 0:
                glClearColor(1.0, 1.0, 1.0, 1.0)  # Red
            else:
                glClearColor(0.0, 0.0, 0.0, 1.0)  # Black
        else:
            global_flags.energy_bomb_activated = False  # End effect
            glClearColor(0.0, 0.0, 0.0, 1.0)  # Default
            game_events.handle_energy_bomb(objectList, particleList, player_position, player_right)
    else:
        glClearColor(0.0, 0.0, 0.0, 1.0)  # Default
    
    
    #clear screen
    glClear(GL_COLOR_BUFFER_BIT)
    
    #read keyboard
    events=pygame.event.get()
    running = input_handler.handle_events(events, player_position, movement_forward, objectList,planet_and_star, movement_orientation,main_loop_counter)
    if not running:
        break

    # Handle game reset    
    if global_flags.reset_game:
        game_events.reset()
        player_position, movement_orientation, look_orientation, input_handler, cockpit_console, movement_forward, movement_right, movement_up, direction_text = game_events.newGameView(WIDTH,HEIGHT)
        planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield, particleList = game_events.newGameObjects(player_position)
        
        player.info_screen_page = 8
      
    # Update altitude, cabin temp, shields, banks every 20 frames
    if main_loop_counter % 20 == 0 and not global_flags.is_game_over and not global_flags.is_title_screen and not global_flags.is_docked:
        if not global_flags.is_game_over and not global_flags.is_title_screen:
            game_events.update_altitude_and_cabin_temp(player_position,movement_forward, planet_and_star,input_handler,main_loop_counter)
            game_events.charge_shields_and_banks()
        
        # Only check collisions if NOT docked and NOT launching
    if not global_flags.is_docked and not global_flags.is_launching and not global_flags.is_docking and not global_flags.is_game_over and not global_flags.is_escape_pod_launched:
        collisions = game_events.check_player_collision(player_position, 10, objectList)
        if collisions:
            game_events.process_collisions(collisions, movement_forward,movement_up,input_handler, player_position,main_loop_counter,objectList)
    else:
        collisions = []

    

    #coundown to hyperspace jump
    if global_flags.in_hyperspace_countdown:
        elapsed = time.time() - global_flags.in_hyperspace_countdown_start
        if elapsed >= 10.0:
            global_flags.in_hyperspace_countdown = False
            global_flags.game_state = global_flags.STATE_HYPERSPACE_JUMPING
    
    


    # --- Main Game States ---
    if global_flags.is_flying:   
        keys = pygame.key.get_pressed()
        
        
        if global_flags.targeting_missile:
            game_events.handle_missile_targeting(objectList, player_position, movement_forward, input_handler,screen_center,focal_length)   
        # Handle continuous input
        if input_handler.docking_active:
            player_position, movement_orientation = input_handler.docking_computer(player_position, movement_orientation)
            look_orientation, direction_text = input_handler.handle_look_direction(keys, movement_orientation, direction_text)
            if player.info_screen_page != 0:
                input_handler.handle_info_screen_controls(events)
        elif player.info_screen_page == 0:
            player_position = input_handler.handle_movement(keys, player_position, movement_forward, movement_right, movement_up)
            movement_orientation = input_handler.handle_rotation(keys, movement_orientation)
            look_orientation, direction_text = input_handler.handle_look_direction(keys, movement_orientation, direction_text)
        else:
            player_position = input_handler.handle_movement(keys, player_position, movement_forward, movement_right, movement_up)
            look_orientation, direction_text = input_handler.handle_look_direction(keys, movement_orientation, direction_text)
            input_handler.handle_info_screen_controls(events)


        # Update axes after rotation
        look_forward, look_right, look_up = input_handler.update_axes(look_orientation)
        movement_forward, movement_right, movement_up = input_handler.update_axes(movement_orientation)

        # Calculate player_target for view matrix
        player_target = player_position + look_forward
        view_matrix = objectList[0].look_at_matrix(player_position, player_target, look_up)
        
        # Update starfield based on player position
        starfield.update( movement_orientation, player_position)

        # Update particles from explosions
        for particle in particleList:
            particle.update()
        particleList[:] = [p for p in particleList if p.is_alive()]

        #spawn new objects (maybe)
        if main_loop_counter%game_constants.SPAWN_INTERVAL==0 or global_flags.just_jumped:
            game_events.spawn_new_objects(objectList, player_position, movement_orientation, main_loop_counter)
            global_flags.just_jumped=False
        
        # Compute polygons, starfield and planets
        face_list, debug_lines, plotting = ogl_render.generate_face_list(
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
        ogl_render.ogl_render(face_list, movement_orientation)  # Pass orientation for lighting

        ogl_render.process_enemy_laser_beams(objectList, WIDTH, HEIGHT, view_matrix, focal_length, screen_center)
        
        if global_flags.DEBUG_MODE:
            # OPTIONAL: Draw debug lines (object axes etc)
            ogl_render.draw_debug_lines(debug_lines)   

            # Show debug overlay
            show_debug_overlay(WIDTH, HEIGHT, plotting, clock, input_handler, player_position, movement_forward, spaceStationCoords, spaceStationOrientation)

        

    elif  global_flags.is_title_screen and player.info_screen_page ==0:
        ship_data.reset()
        clear_messages()
        events=[]
        ogl_render.render_title_screen(screen_center,WIDTH, HEIGHT, main_loop_counter, focal_length)

    elif  global_flags.is_game_over:
        clear_messages()
        events=[]
        ogl_render.game_over_screen(screen_center, WIDTH, HEIGHT,player_position,player_right, movement_forward,look_forward, planet_and_star, objectList,particleList,main_loop_counter,focal_length,movement_orientation,starfield,player_target,look_up)
     
    elif global_flags.is_docked:
        input_handler.handle_info_screen_controls(events)

    elif global_flags.is_escape_pod_launched:
        ogl_render.render_escape_pod_launch(screen_center, WIDTH, HEIGHT, player_position,player_right, movement_forward,look_forward, planet_and_star, objectList,particleList,main_loop_counter,focal_length,movement_orientation,starfield,player_target,look_up)
        
    elif global_flags.is_launching:
        render_launch_tunnel(
            screen_center, WIDTH, HEIGHT, clock,
            cockpit_console, input_handler, direction_text, player_position,player_right,
            movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList,main_loop_counter, focal_length
        )
        planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield, particleList = game_events.newGameObjects(player_position)
        player_position, movement_orientation, look_orientation = game_events.set_player_launch_position(player.current_system, spaceStationCoords, player_position, movement_orientation, look_orientation, input_handler, global_flags)
        
        global_flags.game_state = global_flags.STATE_FLYING
        player.info_screen_page = 0        
       
    elif global_flags.is_docking:
        render_launch_tunnel(
            screen_center, WIDTH, HEIGHT, clock,
            cockpit_console, input_handler, direction_text, player_position,player_right,
            movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList,main_loop_counter, focal_length
        )
        global_flags.game_state = global_flags.STATE_DOCKED
        player.info_screen_page = 6
        global_flags.frame_start = main_loop_counter
        global_flags.message_seen = False
        game_events.reset_ship()

    elif global_flags.is_hyperspace_jumping:
        ogl_render.render_hyperspace_tunnel(screen_center, WIDTH, HEIGHT, clock, cockpit_console, input_handler, direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList,main_loop_counter, focal_length)
        player_position, movement_orientation, look_orientation, movement_forward, movement_right, movement_up, planet_and_star, spaceStationCoords, spaceStationOrientation, objectList, starfield = game_events.do_hyperspace_jump()

    elif global_flags.is_short_range_jumping:
        starfield.update( movement_orientation, player_position,allow_reset=False)
        ogl_render.render_jump_warp(screen_center, WIDTH, HEIGHT, player_position, player_right, movement_forward,look_forward, planet_and_star, objectList, particleList, main_loop_counter, focal_length,movement_orientation,starfield,player_target,look_up)
    
    # --- Info screen rendering (top part of display) ---
    renderer = info_screen_renderers.get(player.info_screen_page)
    if renderer:
        if player.info_screen_page in (1, 2, 3, 4, 10, 11):
            renderer(WIDTH, HEIGHT, input_handler)
        elif player.info_screen_page ==12:
            renderer(WIDTH, HEIGHT,screen_center, main_loop_counter, focal_length)
        elif player.info_screen_page in (6,13,14):
            renderer(WIDTH, HEIGHT, input_handler, main_loop_counter)
        elif player.info_screen_page ==8:
            renderer(WIDTH, HEIGHT, objectList)
        else:
            renderer(WIDTH, HEIGHT)

    #render cockpit console (including player laser fire)
    if not global_flags.is_game_over:
        cockpit_console.update_cockpit(input_handler,direction_text,player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList,particleList, WIDTH, HEIGHT,main_loop_counter,focal_length,screen_center)

    # Remove objects marked for removal and distant objects
    objectList = [obj for obj in objectList if not obj.ready_for_removal]
    
    

    main_loop_counter +=1

    pygame.display.flip()
    clock.tick(50)
   



pygame.quit()
sys.exit()


