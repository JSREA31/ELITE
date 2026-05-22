from ogl_render import drawText
import numpy as np
from status import player
from scipy.spatial.transform import Rotation as R
import pygame

small_font = pygame.font.Font(pygame.font.get_default_font(), 10)
def show_debug_overlay(WIDTH, HEIGHT, plotting, clock, input_handler, player_position, movement_forward, spaceStationCoords, spaceStationOrientation):

    drawText(20, 30, WIDTH,HEIGHT, input_handler.docking_text, small_font,
                text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    drawText(20, 50, WIDTH,HEIGHT, "FPS: " + str(int(clock.get_fps())), small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    drawText(20, 70, WIDTH,HEIGHT, "Plotting:" + str(plotting), small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    # Show distance from player to planet
    planet_pos = np.array(player.current_system.planetCoords)
    player_to_planet = np.linalg.norm(player_position - planet_pos)
    drawText(20, 90, WIDTH,HEIGHT, f"Distance to planet: {int(player_to_planet)}", small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    # Show distance from player to space station
    station_pos = np.array(spaceStationCoords)
    player_to_station = np.linalg.norm(player_position - station_pos)
    drawText(20, 110, WIDTH,HEIGHT, f"Distance to station: {int(player_to_station)}", small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    return
    
    drawText(20, 120, WIDTH,HEIGHT, f"forward vector: {movement_forward}", small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))

    orientation = R.from_euler('xyz', spaceStationOrientation)
    spacestation_forward = orientation.apply([0, 0, -1])
    drawText(20, 130, WIDTH,HEIGHT, f"dodo forward vector: {spacestation_forward}", small_font,
            text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255))