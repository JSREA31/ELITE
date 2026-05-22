import random
import pygame
import math
import ogl_render
from status import global_flags,game_constants,ship_data, MissileStatus,LaserType, LaserLocation,FONTS,player
import status
import game_events
import numpy as np
from sounds import sound_manager, SoundType
from text_strings import get_text
from OpenGL.GL import (
    glGenTextures, glBindTexture, glTexImage2D, glTexParameteri,
    glEnable, glBlendFunc, GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    glDisable, glColor3f, glBegin, glTexCoord2f, glVertex2f, glEnd,
    GL_TEXTURE_2D, GL_QUADS, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
    GL_LINEAR, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE,
    glDrawPixels, glWindowPos2d, GL_RGBA, GL_UNSIGNED_BYTE, GL_LINE_LOOP, GL_TRIANGLE_FAN, GL_LINES,
    glPointSize, GL_POINTS,glLineWidth, glColor4f
)

# --- Missile Indicator Class ---
class OGLMissileIndicator:
    def __init__(self, bar_width, bar_height, label="M", gap=4):
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.label = label
        self.gap = gap
        self.flash_low = 40
        self.flash_high = 255
        self.flash_inc = 5
        self.current_flash_color = self.flash_low
        self.multiplier=1
        self.flashing = False

    def draw(self, x, y, missile_status_list, get_label_texture, draw_textured_quad, frame_count):
        # Draw label on the left
        label_tex_id, lw, lh = get_label_texture(self.label)
        draw_textured_quad(label_tex_id, x - lw - 8, y, lw, lh)
        # Draw 4 missile boxes, sized to match bar indicators
        box_w = (self.bar_width // 4) - self.gap
        box_h = self.bar_height
        
        # Determine if any missile is flashing or fast flashing
        if  any(status == MissileStatus.LOCKED_ON for status in missile_status_list):
            self.flashing = True
            self.multiplier=10
        if any(status == MissileStatus.TARGETING for status in missile_status_list):
            self.flashing = True
            self.multiplier=1    
            
        if self.flashing:
            self.current_flash_color += (self.flash_inc*self.multiplier)
            if not (self.flash_low <= self.current_flash_color <= self.flash_high):
                self.current_flash_color -= self.flash_inc*self.multiplier
                self.flash_inc = -self.flash_inc

        
        for i, status in enumerate(missile_status_list):
            box_x = x + i * (box_w + self.gap)
            box_y = y
            if status == MissileStatus.NOT_PRESENT:
                color = (0, 40, 0)
            elif status == MissileStatus.PRESENT:
                color = (0, 255, 0)
            elif status == MissileStatus.TARGETING or status == MissileStatus.LOCKED_ON:
                color = (0, self.current_flash_color, 0)
            else:
                color = (0, 40, 0)

            glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
            glBegin(GL_QUADS)
            glVertex2f(box_x, box_y)
            glVertex2f(box_x + box_w, box_y)
            glVertex2f(box_x + box_w, box_y + box_h)
            glVertex2f(box_x, box_y + box_h)
            glEnd()

# --- OpenGL Bar Indicator Classes ---
class OGLBarIndicator:
    def __init__(self, width, height, label, color_bg=(0,40,0), color_fill=(0,255,0), label_position='right', low_alert=None, high_alert=None):
        self.width = width
        self.height = height
        self.label = label
        self.color_bg = color_bg
        self.color_fill = color_fill
        self.label_position = label_position  # 'left' or 'right'
        #parameters for flashing bar due to above or below alert limits
        self.low_alert = low_alert
        self.high_alert = high_alert
        self.flash_low = 40
        self.flash_high = 255
        self.flash_inc = 5
        self.current_flash_color = self.flash_low
        self.flashing = False
        
    

    def draw(self, x, y, value, min_val, max_val, get_label_texture, HEIGHT, draw_textured_quad):
        norm = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
        # Label
        label_tex_id, lw, lh = get_label_texture(self.label)
        if self.label_position == 'left':
            label_x = x - lw - 8
            bar_x = x
        else:
            label_x = x + self.width + 8
            bar_x = x
        label_y = y + (self.height - lh) // 2
        
        
        # Background
        glColor3f(*(c/255.0 for c in self.color_bg))
        glBegin(GL_QUADS)
        glVertex2f(bar_x, y)
        glVertex2f(bar_x + self.width, y)
        glVertex2f(bar_x + self.width, y + self.height)
        glVertex2f(bar_x, y + self.height)
        glEnd()
        
        # Fill
        #flashing logic
        self.flashing = (
            (self.low_alert is not None and value <= self.low_alert) or
            (self.high_alert is not None and value >= self.high_alert)
        )

        if self.flashing:
            self.current_flash_color += self.flash_inc
            if not (self.flash_low <= self.current_flash_color <= self.flash_high):
                self.flash_inc = -self.flash_inc
            glColor3f(0, self.current_flash_color / 255.0, 0)
        else:
            glColor3f(*(c / 255.0 for c in self.color_fill))
        
        glBegin(GL_QUADS)
        glVertex2f(bar_x, y)
        glVertex2f(bar_x + self.width * norm, y)
        glVertex2f(bar_x + self.width * norm, y + self.height)
        glVertex2f(bar_x, y + self.height)
        glEnd()
        draw_textured_quad(label_tex_id, label_x, label_y, lw, lh)

class OGLCenteredBarIndicator:
    def __init__(self, width, height, label, color_bg=(0,40,0), color_fill=(0,255,0), color_center=(0,100,0), label_position='right'):
        self.width = width
        self.height = height
        self.label = label
        self.color_bg = color_bg
        self.color_fill = color_fill
        self.color_center = color_center
        self.label_position = label_position  # 'left' or 'right'

    def draw(self, x, y, value, min_val, max_val, get_label_texture, HEIGHT, draw_textured_quad):
        norm = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
        # Label
        label_tex_id, lw, lh = get_label_texture(self.label)
        if self.label_position == 'left':
            label_x = x - lw - 8
            bar_x = x
        else:
            label_x = x + self.width + 8
            bar_x = x
        label_y = y + (self.height - lh) // 2
        center_x = bar_x + self.width // 2
        # Background
        glColor3f(*(c/255.0 for c in self.color_bg))
        glBegin(GL_QUADS)
        glVertex2f(bar_x, y)
        glVertex2f(bar_x + self.width, y)
        glVertex2f(bar_x + self.width, y + self.height)
        glVertex2f(bar_x, y + self.height)
        glEnd()
        # Center line
        glColor3f(*(c/255.0 for c in self.color_center))
        glBegin(1)  # GL_LINES
        glVertex2f(center_x, y)
        glVertex2f(center_x, y + self.height)
        glEnd()
        # Fill
        fill_width = int(abs(norm - 0.5) * self.width)
        if value != 0:
            fill_x = center_x if value > 0 else center_x - fill_width
            glColor3f(*(c/255.0 for c in self.color_fill))
            glBegin(GL_QUADS)
            glVertex2f(fill_x, y)
            glVertex2f(fill_x + fill_width, y)
            glVertex2f(fill_x + fill_width, y + self.height)
            glVertex2f(fill_x, y + self.height)
            glEnd()
        draw_textured_quad(label_tex_id, label_x, label_y, lw, lh)

class CockpitConsole:
    def __init__(self, WIDTH):
        

        #setup bar indicators (right hand side)
        self.bar_width = 128
        self.bar_height = 14
        self.bar_gap = 6
        self.speed_bar = OGLBarIndicator(self.bar_width, self.bar_height, "SP")
        self.pitch_bar = OGLCenteredBarIndicator(self.bar_width, self.bar_height, "DC")
        self.roll_bar = OGLCenteredBarIndicator(self.bar_width, self.bar_height, "RL")
        # Energy bank indicators (4 bars, labeled 1-4)
        self.energy_bank_bars = [
            OGLBarIndicator(self.bar_width, self.bar_height, str(i+1))
            for i in range(4)
        ]

        # Setup bar indicators (left hand side)
        self.forward_shield_bar = OGLBarIndicator(self.bar_width, self.bar_height, "FS", label_position='left')
        self.aft_shield_bar = OGLBarIndicator(self.bar_width, self.bar_height, "AS", label_position='left')
        self.fuel_level_bar = OGLBarIndicator(self.bar_width, self.bar_height, "FU", label_position='left')
        self.cabin_temp_bar = OGLBarIndicator(self.bar_width, self.bar_height, "CT", label_position='left', high_alert=228)
        self.laser_temp_bar = OGLBarIndicator(self.bar_width, self.bar_height, "LT", label_position='left')
        self.altitude_bar = OGLBarIndicator(self.bar_width, self.bar_height, "AL", label_position='left', low_alert=20)
        self.missile_indicator = OGLMissileIndicator(self.bar_width, self.bar_height)

        # Create background image for radar and store as OpenGL texture
        # Setup colors and dimensions
        grid_color = (0, 100, 0)
        grid_color2 = (0, 150, 0)
        ellipse_color = (0, 120, 0)
        player_color = (0, 255, 0)
        self.radar_size = 150
        self.cockpit_height = 200
        self.squash = math.cos(math.radians(30))
        self.ellipse_rx = int(self.radar_size * 1.5)
        self.ellipse_ry = int(self.radar_size // 2 * self.squash)
        self.radar_rect_x = (WIDTH - self.ellipse_rx * 2) // 2
        self.radar_rect_y = self.cockpit_height - self.radar_size - 10  # 10px from the bottom of the cockpit area
        self.ellipse_center = (self.radar_rect_x + self.ellipse_rx, 
                              self.radar_rect_y + self.ellipse_ry)
        # draw into pygame surface using pygame.draw
        self.radar_background = pygame.Surface((WIDTH, self.cockpit_height), pygame.SRCALPHA)
        pygame.draw.ellipse(self.radar_background, ellipse_color, (
            self.ellipse_center[0] - self.ellipse_rx,
            self.ellipse_center[1] - self.ellipse_ry,
            self.ellipse_rx * 2,
            self.ellipse_ry * 2
        ), 3)
        grid_surface = pygame.Surface((self.ellipse_rx * 2, self.ellipse_ry * 2), pygame.SRCALPHA)
        horizontal_ys = np.array([0.5, 1.0, 1.65]) * self.ellipse_ry
        vertical_xs = np.array([
            [0.6, 0.2],
            [1.0, 1.0],
            [1.4, 1.8]
        ]) * self.ellipse_rx
        for y in horizontal_ys:
            pygame.draw.line(grid_surface, grid_color, 
                           (0, int(y)), 
                           (self.ellipse_rx * 2, int(y)), 2)
        for start_x, end_x in vertical_xs:
            pygame.draw.line(grid_surface, grid_color,
                           (int(start_x), 0),
                           (int(end_x), self.ellipse_ry * 2), 2)
        pygame.draw.aaline(grid_surface, grid_color2, (vertical_xs[0, 0]*0.89, 0), (self.ellipse_rx, self.ellipse_ry), 1)
        pygame.draw.aaline(grid_surface, grid_color2, (vertical_xs[2, 0]*1.11, 0), (self.ellipse_rx, self.ellipse_ry), 1)
        mask = pygame.Surface((self.ellipse_rx * 2, self.ellipse_ry * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(mask, (255, 255, 255, 255),
                          (0, 0, self.ellipse_rx * 2, self.ellipse_ry * 2))
        grid_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.radar_background.blit(grid_surface, 
                           (self.ellipse_center[0] - self.ellipse_rx,
                            self.ellipse_center[1] - self.ellipse_ry))
        pygame.draw.circle(self.radar_background, player_color, 
                         (self.ellipse_center[0], self.ellipse_center[1]), 2)
        
        # Create OpenGL texture for radar background
        bg_surface = pygame.transform.flip(self.radar_background, False, True)
        bg_data = pygame.image.tostring(bg_surface, "RGBA", True)
        self._radar_bg_tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._radar_bg_tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, 6408, bg_surface.get_width(), bg_surface.get_height(), 0, 6408, 5121, bg_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        # --- Dynamic overlay for radar objects ---
        self.radar_dynamic = pygame.Surface((WIDTH, self.cockpit_height), pygame.SRCALPHA)
        self._radar_dynamic_tex_id = glGenTextures(1)

        #create background image for compass
        self.compass_radius = 25
        self._compass_bg_size = int(self.compass_radius * 2 + 8)  # Add a little padding
        self.compass_surf = pygame.Surface((self._compass_bg_size, self._compass_bg_size), pygame.SRCALPHA)

        center = self._compass_bg_size // 2

        # Draw compass circle
        pygame.draw.circle(self.compass_surf, (0, 255, 0, 255), (center, center), self.compass_radius, 1)

        # Draw crosshair with empty center
        cross_gap = 8
        cross_len = self.compass_radius
        # Horizontal left
        pygame.draw.line(self.compass_surf, (0, 255, 0, 255), (center - cross_len, center), (center - cross_gap, center), 1)
        # Horizontal right
        pygame.draw.line(self.compass_surf, (0, 255, 0, 255), (center + cross_gap, center), (center + cross_len, center), 1)
        # Vertical top
        pygame.draw.line(self.compass_surf, (0, 255, 0, 255), (center, center - cross_len), (center, center - cross_gap), 1)
        # Vertical bottom
        pygame.draw.line(self.compass_surf, (0, 255, 0, 255), (center, center + cross_gap), (center, center + cross_len), 1)

        # Convert to OpenGL texture
        compass_data = pygame.image.tostring(self.compass_surf, "RGBA", True)
        self._compass_bg_tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._compass_bg_tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self._compass_bg_size, self._compass_bg_size, 0, GL_RGBA, GL_UNSIGNED_BYTE, compass_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

        self._crosshair_textures = self._create_crosshair_textures()
        

    def _create_crosshair_textures(self):
        # Pre-render crosshair types to textures for fast blitting
        
        crosshair_types = ['pulse', 'beam', 'military', 'mining']
        size = 128  # Texture size (pixels)
        center = size // 2
        textures = {}
        for ctype in crosshair_types:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            color = (0, 255, 0, 255)
            if ctype == 'pulse':
                pygame.draw.line(surf, color, (center, center-60), (center, center-24), 2)
                pygame.draw.line(surf, color, (center, center+24), (center, center+60), 2)
                pygame.draw.line(surf, color, (center-60, center), (center-24, center), 2)
                pygame.draw.line(surf, color, (center+24, center), (center+60, center), 2)
            elif ctype == 'beam':
                pygame.draw.line(surf, color, (center-50, center-50), (center+50, center-50), 2)
                pygame.draw.line(surf, color, (center-50, center+50), (center+50, center+50), 2)
                pygame.draw.line(surf, color, (center, center-50), (center, center-65), 2)
                pygame.draw.line(surf, color, (center, center+50), (center, center+65), 2)
                pygame.draw.line(surf, color, (center-50, center-50), (center-50, center-35), 2)
                pygame.draw.line(surf, color, (center+50, center-50), (center+50, center-35), 2)
                pygame.draw.line(surf, color, (center-50, center+50), (center-50, center+35), 2)
                pygame.draw.line(surf, color, (center+50, center+50), (center+50, center+35), 2)
            elif ctype == 'military':
                gap = 20
                tri = 40
                pygame.draw.polygon(surf, color, [(center, center-gap), (center-tri//2, center-tri), (center+tri//2, center-tri)], 2)
                pygame.draw.polygon(surf, color, [(center, center+gap), (center-tri//2, center+tri), (center+tri//2, center+tri)], 2)
                pygame.draw.polygon(surf, color, [(center-gap, center), (center-tri, center-tri//2), (center-tri, center+tri//2)], 2)
                pygame.draw.polygon(surf, color, [(center+gap, center), (center+tri, center-tri//2), (center+tri, center+tri//2)], 2)
            elif ctype == 'mining':
                # Outer box
                pygame.draw.line(surf, color, (center-50, center-50), (center+50, center-50), 2)
                pygame.draw.line(surf, color, (center-50, center+50), (center+50, center+50), 2)
                pygame.draw.line(surf, color, (center-50, center-50), (center-50, center-25), 2)
                pygame.draw.line(surf, color, (center+50, center-50), (center+50, center-25), 2)
                pygame.draw.line(surf, color, (center-50, center+50), (center-50, center+25), 2)
                pygame.draw.line(surf, color, (center+50, center+50), (center+50, center+25), 2)
                # Inner box
                pygame.draw.line(surf, color, (center-20, center-20), (center+20, center-20), 2)
                pygame.draw.line(surf, color, (center-20, center+20), (center+20, center+20), 2)
                pygame.draw.line(surf, color, (center-20, center-20), (center-20, center-10), 2)
                pygame.draw.line(surf, color, (center+20, center-20), (center+20, center-10), 2)
                pygame.draw.line(surf, color, (center-20, center+20), (center-20, center+10), 2)
                pygame.draw.line(surf, color, (center+20, center+20), (center+20, center+10), 2)
                # Crosshair
                pygame.draw.line(surf, color, (center, center-50), (center, center-20), 2)
                pygame.draw.line(surf, color, (center, center+20), (center, center+50), 2)
                pygame.draw.line(surf, color, (center-50, center), (center-20, center), 2)
                pygame.draw.line(surf, color, (center+20, center), (center+50, center), 2)
                # Diagonals
                pygame.draw.line(surf, color, (center-45, center-45), (center-25, center-25), 2)
                pygame.draw.line(surf, color, (center-25, center+25), (center-45, center+45), 2)
                pygame.draw.line(surf, color, (center+45, center-45), (center+25, center-25), 2)
                pygame.draw.line(surf, color, (center+45, center+45), (center+25, center+25), 2)
            # Convert to OpenGL texture
            data = pygame.image.tostring(surf, "RGBA", True)
            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size, size, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glBindTexture(GL_TEXTURE_2D, 0)
            textures[ctype] = (tex_id, size, size)

        return textures

    def get_label_texture(self, label, font_size=14, color=(0,255,0)):
        # Cache OpenGL texture for label
        if not hasattr(self, '_label_tex_cache'):
            self._label_tex_cache = {}
        if (label, font_size) in self._label_tex_cache:
            return self._label_tex_cache[(label, font_size)]
        font = pygame.font.Font(status.font_file, font_size)
        surf = font.render(label, True, color)
        surf = pygame.transform.flip(surf, False, True)
        data = pygame.image.tostring(surf, "RGBA", True)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surf.get_width(), surf.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        self._label_tex_cache[(label, font_size)] = (tex_id, surf.get_width(), surf.get_height())
        return tex_id, surf.get_width(), surf.get_height()

    def draw_cockpit_indicators_gl(self, input_handler, WIDTH, HEIGHT):
        
        # Bar position for right hand side bars
        bar_x = self.radar_rect_x + self.ellipse_rx * 2 + 35
        bar_y =  HEIGHT - self.radar_size - 10

        # Speed (normal bar)
        self.speed_bar.draw(
            bar_x, bar_y,
            input_handler.current_speed, 0.0, input_handler.max_speed,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Pitch (centered bar)
        self.pitch_bar.draw(
            bar_x, bar_y + self.bar_height + self.bar_gap,
            input_handler.current_pitch_speed * input_handler.pitch_direction,
            -input_handler.max_pitch_speed, input_handler.max_pitch_speed,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Roll (centered bar)
        self.roll_bar.draw(
            bar_x, bar_y + 2 * (self.bar_height + self.bar_gap),
            input_handler.current_roll_speed * -input_handler.roll_direction,
            -input_handler.max_roll_speed, input_handler.max_roll_speed,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Energy banks (draw under roll bar)
        energy_y_start = bar_y +  3* (self.bar_height + self.bar_gap)
        energy_per_bank = 64
        total_energy = ship_data.energy_level
        for i in range(4):
            # Deplete from 4 to 1
            
            bank_energy = min(max(total_energy - (3-i) * energy_per_bank, 0), energy_per_bank)
            self.energy_bank_bars[i].draw(
                bar_x,
                energy_y_start + i * (self.bar_height + self.bar_gap),  # 12px bar height + 4px gap
                bank_energy, 0, energy_per_bank,
                self.get_label_texture, HEIGHT,
                self._draw_textured_quad
            )

        # Bar position for left hand side bars
        left_bar_x = self.radar_rect_x - self.bar_width - 35
        left_bar_y = bar_y = HEIGHT - self.radar_size - 10

        # Forward shield (left bar)
        self.forward_shield_bar.draw(
            left_bar_x, left_bar_y,
            ship_data.forward_shield, 0, 255,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Aft shield (left bar)
        self.aft_shield_bar.draw(
            left_bar_x, left_bar_y + self.bar_height + self.bar_gap,
            ship_data.aft_shield, 0, 255,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Fuel level (left bar)
        self.fuel_level_bar.draw(
            left_bar_x, left_bar_y + 2 * (self.bar_height + self.bar_gap),
            ship_data.fuel_level, 0, 70,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )
        # Cabin temperature (left bar)
        self.cabin_temp_bar.draw(
            left_bar_x, left_bar_y + 3 * (self.bar_height + self.bar_gap),
            ship_data.cabin_temp, 0, 255,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Laser temperature (left bar)
        self.laser_temp_bar.draw(
            left_bar_x, left_bar_y + 4 * (self.bar_height + self.bar_gap),
            ship_data.laser_temp, 0, 255,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )

        # Altitude (left bar)
        self.altitude_bar.draw(
            left_bar_x, left_bar_y + 5 * (self.bar_height + self.bar_gap),
            ship_data.altitude, 0, 255,
            self.get_label_texture, HEIGHT,
            self._draw_textured_quad
        )
    
        # Missile indicator (under altitude bar)
        missile_indicator_y = left_bar_y + 6 * (self.bar_height + self.bar_gap) + 8
        frame_count = getattr(input_handler, 'frame_count', 0)
        self.missile_indicator.draw(
            left_bar_x,
            missile_indicator_y,
            ship_data.missile_status,
            self.get_label_texture,
            self._draw_textured_quad,
            frame_count
        )

    def _draw_textured_quad(self, texture_id, x, y, width, height):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor3f(1.0, 1.0, 1.0)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(x, y)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(x + width, y)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(x + width, y + height)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(x, y + height)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
    
    def update_radar(self, player_position, forward, right, up, objectList,HEIGHT):
        self.draw_radar_background(0,HEIGHT-self.cockpit_height)
        # Prepare radar marker geometry for OpenGL drawing (no Pygame surface)
        radar_size = self.radar_size
        squash = self.squash
        radar_scale = global_flags.radar_zoom_values[global_flags.radar_zoom_index]
        ellipse_rx = self.ellipse_rx
        ellipse_ry = self.ellipse_ry
        radar_center = (ellipse_rx, ellipse_ry)
        radar_rect_x = self.radar_rect_x
        radar_rect_y = self.radar_rect_y
        scale_x = ellipse_rx / (radar_size // 2)
        scale_y = squash
        self._radar_markers = []
        if global_flags.is_flying:
            for obj in objectList:
                rel = obj.coords - player_position
                dx = np.dot(rel, right) / radar_scale
                dz = np.dot(rel, forward) / radar_scale
                obj_radar_x = int(radar_center[0] - dx * scale_x)
                obj_radar_y = int(radar_center[1] - dz * scale_y)
                dx_ellipse = (obj_radar_x - radar_center[0]) / ellipse_rx
                dy_ellipse = (obj_radar_y - radar_center[1]) / ellipse_ry
                if dx_ellipse**2 + dy_ellipse**2 > 1:
                    continue
                height_diff = np.dot(rel, up)
                if abs(height_diff) < radar_scale*self.radar_size//2:
                    line_color = obj.radar_color
                    
                    line_length = -int((height_diff/radar_scale )* scale_y)
                    start_pos = (radar_rect_x + obj_radar_x, radar_rect_y + obj_radar_y)
                    end_pos = (radar_rect_x + obj_radar_x, radar_rect_y + obj_radar_y - line_length)
                    rect_size = obj.radar_rect_size
                    name = getattr(obj, 'name', str(obj)) if hasattr(obj, 'name') else str(obj) 
                    
                    self._radar_markers.append({
                        'line': (start_pos, end_pos, line_color),
                        'rect': (end_pos, rect_size, line_color),
                        'name': name,
                        'rect_center': end_pos
                    })
            self.draw_radar_objects(0, HEIGHT-self.cockpit_height, HEIGHT)
    
    def draw_radar_background(self, x,y):
        # Draw the radar background texture as a quad at the bottom of the window
        width = self.radar_background.get_width()
        height = self.radar_background.get_height()
        self._draw_textured_quad(self._radar_bg_tex_id, x, y, width, height)

    def draw_radar_objects(self, x, y, HEIGHT):
        # Draw radar markers directly in OpenGL (lines and rectangles)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        y_offset = y  # y is HEIGHT - self.cockpit_height
        for marker in getattr(self, '_radar_markers', []):
            obj_name = marker.get('name', '')
            if obj_name != "Cougar":            
                # Draw rectangle (as a filled quad)
                (rect_center, rect_size, rect_color) = marker['rect']
                glColor3f(rect_color[0]/255.0, rect_color[1]/255.0, rect_color[2]/255.0)
                rect_x = rect_center[0]
                rect_y = rect_center[1] + y_offset
                s = rect_size // 2
                glBegin(GL_QUADS)
                glVertex2f(rect_x - s, rect_y - s)
                glVertex2f(rect_x + s, rect_y - s)
                glVertex2f(rect_x + s, rect_y + s)
                glVertex2f(rect_x - s, rect_y + s)
                glEnd()
                
                # Draw object name  and line next to the dot, but not if fragment
                if obj_name and obj_name != "fragment":
                    # Draw line
                    (start, end, color) = marker['line']
                    glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
                    glBegin(1)  # GL_LINES
                    glVertex2f(start[0], start[1] + y_offset)
                    glVertex2f(end[0], end[1] + y_offset)
                    glEnd()

                    # Use cached OpenGL texture for text label
                    tex_id, text_w, text_h = self.get_label_texture(obj_name, font_size=10,color=(255,255,255))
                    # Position to the right of the box, vertically centered
                    label_x = rect_x + s + 2
                    label_y = rect_y - text_h // 2
                    self._draw_textured_quad(tex_id, label_x, label_y, text_w, text_h)
 
    def update_compass(self, player_position, forward, right, up, planet_and_star, objectList, WIDTH, HEIGHT):
        planet_pos = player.current_system.planetCoords
        global_flags.planet_distance = float(np.linalg.norm(planet_pos - player_position))  

        sun_pos = player.current_system.sunCoords
        global_flags.sun_distance = float(np.linalg.norm(sun_pos - player_position))    
        

        station_pos = None
        for obj in objectList:
            if obj.type== "station":
                station_pos = obj.coords  # or obj.position if that's the attribute
                station_distance = np.linalg.norm(station_pos - player_position)
                global_flags.station_distance = float(station_distance)
                if station_distance < game_constants.SPACE_STATION_ZONE_RADIUS:
                    global_flags.is_in_space_station_zone = True
                else:
                    global_flags.is_in_space_station_zone = False
                break


        if global_flags.is_in_space_station_zone and station_pos is not None:
            target_pos = station_pos
        else:
            target_pos = planet_pos

        to_target = target_pos - player_position

        forward_comp = np.dot(to_target, forward)
        right_comp = np.dot(to_target, right)
        up_comp = np.dot(to_target, up)

        horizontal_angle_rad = np.arctan2(right_comp, forward_comp)
        vertical_angle_rad = np.arctan2(up_comp, forward_comp)

        horizontal_angle_deg = np.degrees(horizontal_angle_rad)
        vertical_angle_deg = np.degrees(vertical_angle_rad)

        if abs(horizontal_angle_deg) > 90 or abs(vertical_angle_deg) > 90:
            in_front = False
            horizontal_angle_deg = 180-horizontal_angle_deg if horizontal_angle_deg > 0 else -180 - horizontal_angle_deg
            vertical_angle_deg = 180-vertical_angle_deg if vertical_angle_deg > 0 else -180 - vertical_angle_deg
        else:    
            in_front = True
        self.draw_compass(horizontal_angle_deg, vertical_angle_deg, in_front, WIDTH,HEIGHT)
        return

    def draw_compass(self, horizontal_angle_deg, vertical_angle_deg, in_front, WIDTH, HEIGHT):   

        width = self.compass_surf.get_width()
        height = self.compass_surf.get_height()
        ellipse_rx = int(self.radar_size * 1.5)
        radar_rect_x = (WIDTH - ellipse_rx * 2) // 2
        radar_rect_y = HEIGHT - self.radar_size - 10
        compass_x = radar_rect_x + ellipse_rx * 2 - 40
        compass_y = radar_rect_y - 20

        self._draw_textured_quad(self._compass_bg_tex_id, compass_x, compass_y, width, height)

        compass_x += width // 2
        compass_y += height //  2

        
        h = np.clip(horizontal_angle_deg, -90, 90)
        v = np.clip(vertical_angle_deg, -90, 90)

        h_rad = np.radians(h)
        v_rad = np.radians(v)

        x_dir = np.sin(h_rad) * np.cos(v_rad)
        y_dir = np.sin(v_rad)

        dot_x = compass_x - x_dir * self.compass_radius
        dot_y = compass_y + y_dir * self.compass_radius  # flip y-axis for display

        if global_flags.is_flying:
            # Draw target dot
            if in_front:
                glColor3f(0.0, 1.0, 0.0)
            else:
                glColor3f(0.0, 0.4, 0.0)
            dot_r = 4
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(dot_x, dot_y)
            for i in range(16 + 1):
                theta = 2.0 * np.pi * i / 16
                glVertex2f(dot_x + dot_r * np.cos(theta), dot_y + dot_r * np.sin(theta))
            glEnd()

            #draw space staion in range indicator
            if global_flags.is_in_space_station_zone:
                label_tex_id, lw, lh = self.get_label_texture("S", font_size=40)

                self._draw_textured_quad(label_tex_id, compass_x-20, compass_y+90, lw, lh)

            #draw radar range indicator
            radar_range= "x" + str(2**(global_flags.radar_zoom_index))
            label_tex_id, lw, lh = self.get_label_texture(radar_range, font_size=12)

            self._draw_textured_quad(label_tex_id, radar_rect_x+ellipse_rx, compass_y+125, lw, lh)

            #draw ECM active indicator
            if global_flags.ecm_active:
                if global_flags.ecm_counter ==0:
                        sound_manager.play(SoundType.ECM)

                global_flags.ecm_counter +=1
                if global_flags.ecm_counter > global_flags.ecm_duration:
                    global_flags.ecm_counter =0
                    global_flags.ecm_active = False
                else:
                    label_tex_id, lw, lh = self.get_label_texture("E", font_size=40)
                    self._draw_textured_quad(label_tex_id, radar_rect_x, compass_y+90, lw, lh)
                
                    if not global_flags.ecm_is_enemy:
                        ship_data.energy_level -=0.4  #drain energy when player ECM active    
                

    laser_map = {
    "FRONT": LaserLocation.FRONT,
    "BACK": LaserLocation.BACK,
    "LEFT": LaserLocation.LEFT,
    "RIGHT": LaserLocation.RIGHT,
    }

    crosshair_map = {
    LaserType.PULSE: 'pulse',
    LaserType.BEAM: 'beam',
    LaserType.MILITARY: 'military',
    LaserType.MINING: 'mining'
    }

    def draw_laser_crosshair(self, direction_text, WIDTH, HEIGHT):
        if global_flags.is_flying:
            laser_location = self.laser_map.get(direction_text, None)
            if laser_location is not None:
                laser_type = ship_data.lasers[laser_location.value]
                
                ctype = self.crosshair_map.get(laser_type)
                if ctype and ctype in self._crosshair_textures:
                    tex_id, tex_w, tex_h = self._crosshair_textures[ctype]
                    center_x = WIDTH // 2 - tex_w // 2
                    center_y = HEIGHT // 2 - tex_h // 2
                    self._draw_textured_quad(tex_id, center_x, center_y, tex_w, tex_h)

    def draw_laser_beams(self,laser_type,WIDTH,HEIGHT,jitter_amount=3):
        if laser_type == LaserType.NOT_PRESENT:
            return
    
        # Calculate center with jitter
        center_x = WIDTH // 2 + random.randint(-jitter_amount, jitter_amount)
        center_y = HEIGHT // 2 + random.randint(-jitter_amount, jitter_amount)
        inner_color = (0.0,0.75,1.0,0.5)


        # Bottom left and right corners
        left_origin = (0, HEIGHT)
        right_origin = (WIDTH, HEIGHT)
        end_point = (center_x, center_y)

        # Optional: draw inner umbra for each beam
        glLineWidth(5)
        glColor4f(*inner_color)
        glBegin(GL_LINES)
        glVertex2f(left_origin[0], left_origin[1])
        glVertex2f(end_point[0], end_point[1])
        glVertex2f(right_origin[0], right_origin[1])
        glVertex2f(end_point[0], end_point[1])
        glEnd()
        glLineWidth(1)
        
        return


    def xdraw_laser_crosshair(self, direction_text, WIDTH, HEIGHT):
        if global_flags.is_flying:
            laser_location = self.laser_map.get(direction_text, None)
            
            if laser_location is not None:
                laser_type = ship_data.lasers[laser_location.value]
                if laser_type == LaserType.PULSE:
                    self.draw_pulse_laser_crosshair(WIDTH, HEIGHT)
                elif laser_type == LaserType.BEAM:
                    self.draw_beam_laser_crosshair(WIDTH, HEIGHT)
                elif laser_type == LaserType.MILITARY:
                    self.draw_military_laser_crosshair(WIDTH, HEIGHT)
                elif laser_type == LaserType.MINING:
                    self.draw_mining_laser_crosshair(WIDTH, HEIGHT)

                

    def draw_pulse_laser_crosshair(self, WIDTH, HEIGHT):
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        size = 60
        middle=24
        glColor3f(0.0, 1.0, 0.0)
        # Vertical line (top)
        glBegin(GL_LINES)
        glVertex2f(center_x, center_y - size)
        glVertex2f(center_x, center_y - middle)
        glEnd()
        # Vertical line (bottom)
        glBegin(GL_LINES)
        glVertex2f(center_x, center_y + middle)
        glVertex2f(center_x, center_y + size)
        glEnd()
        # Horizontal line (left)
        glBegin(GL_LINES)
        glVertex2f(center_x - size, center_y)
        glVertex2f(center_x - middle, center_y)
        glEnd()
        # Horizontal line (right)
        glBegin(GL_LINES)
        glVertex2f(center_x + middle, center_y)
        glVertex2f(center_x + size, center_y)
        glEnd()

    def draw_beam_laser_crosshair(self, WIDTH, HEIGHT):

        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        vertical_half_size = 50
        horizontal_half_size = 50
        detail_size = 15
        left_x = center_x - horizontal_half_size
        right_x = center_x + horizontal_half_size
        top_y = center_y - vertical_half_size
        bottom_y = center_y + vertical_half_size
        glColor3f(0.0, 1.0, 0.0)
        # horizontal line (top)
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(right_x, top_y)
        glEnd()
        # horizontal line (bottom)
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(right_x, bottom_y)
        glEnd()
        #center line top
        glBegin(GL_LINES)
        glVertex2f(center_x, top_y)
        glVertex2f(center_x, top_y-detail_size)
        glEnd()
        #center line bottom
        glBegin(GL_LINES)
        glVertex2f(center_x, bottom_y)
        glVertex2f(center_x, bottom_y+detail_size)
        glEnd()
        #detail line top left
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(left_x, top_y + detail_size)
        glEnd()
        #detail line top right
        glBegin(GL_LINES)
        glVertex2f(right_x, top_y)
        glVertex2f(right_x, top_y + detail_size)
        glEnd()
        #detail line bottom left
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(left_x, bottom_y - detail_size)
        glEnd()
        #detail line bottom right
        glBegin(GL_LINES)
        glVertex2f(right_x, bottom_y)
        glVertex2f(right_x, bottom_y - detail_size)
        glEnd()

    def draw_military_laser_crosshair(self, WIDTH, HEIGHT):
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        triangle_size = 40
        center_half_gap = 20
       
        glColor3f(0.0, 1.0, 0.0)
        # Top triangle
        glBegin(GL_LINE_LOOP)
        glVertex2f(center_x, center_y - center_half_gap)
        glVertex2f(center_x - triangle_size // 2, center_y - triangle_size)
        glVertex2f(center_x + triangle_size // 2, center_y - triangle_size)
        glEnd()
        # Bottom triangle
        glBegin(GL_LINE_LOOP)
        glVertex2f(center_x, center_y + center_half_gap)    
        glVertex2f(center_x - triangle_size // 2, center_y + triangle_size)
        glVertex2f(center_x + triangle_size // 2, center_y + triangle_size)
        glEnd()
        # Left triangle
        glBegin(GL_LINE_LOOP)
        glVertex2f(center_x - center_half_gap, center_y)
        glVertex2f(center_x - triangle_size, center_y - triangle_size // 2)
        glVertex2f(center_x - triangle_size, center_y + triangle_size // 2)
        glEnd()
        # Right triangle
        glBegin(GL_LINE_LOOP)
        glVertex2f(center_x + center_half_gap, center_y)
        glVertex2f(center_x + triangle_size, center_y - triangle_size // 2)
        glVertex2f(center_x + triangle_size, center_y + triangle_size // 2)
        glEnd()           

    def draw_mining_laser_crosshair(self, WIDTH, HEIGHT):
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        vertical_half_size = 50
        horizontal_half_size = 50
        detail_size = 30
        left_x = center_x - horizontal_half_size
        right_x = center_x + horizontal_half_size
        top_y = center_y - vertical_half_size
        bottom_y = center_y + vertical_half_size
        glColor3f(0.0, 1.0, 0.0)
        # horizontal line (top)
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(right_x, top_y)
        glEnd()
        # horizontal line (bottom)
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(right_x, bottom_y)
        glEnd()
        #detail line top left
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(left_x, top_y + detail_size)
        glEnd()
        #detail line top right
        glBegin(GL_LINES)
        glVertex2f(right_x, top_y)
        glVertex2f(right_x, top_y + detail_size)
        glEnd()
        #detail line bottom left
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(left_x, bottom_y - detail_size)
        glEnd()
        #detail line bottom right
        glBegin(GL_LINES)
        glVertex2f(right_x, bottom_y)
        glVertex2f(right_x, bottom_y - detail_size)
        glEnd()

        #inner box
        vertical_half_size = 20
        horizontal_half_size = 20
        detail_size = 10
        left_x = center_x - horizontal_half_size
        right_x = center_x + horizontal_half_size
        top_y = center_y - vertical_half_size
        bottom_y = center_y + vertical_half_size
        glColor3f(0.0, 1.0, 0.0)
        # horizontal line (top)
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(right_x, top_y)
        glEnd()
        # horizontal line (bottom)
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(right_x, bottom_y)
        glEnd()
        #detail line top left
        glBegin(GL_LINES)
        glVertex2f(left_x, top_y)
        glVertex2f(left_x, top_y + detail_size)
        glEnd()
        #detail line top right
        glBegin(GL_LINES)
        glVertex2f(right_x, top_y)
        glVertex2f(right_x, top_y + detail_size)
        glEnd()
        #detail line bottom left
        glBegin(GL_LINES)
        glVertex2f(left_x, bottom_y)
        glVertex2f(left_x, bottom_y - detail_size)
        glEnd()
        #detail line bottom right
        glBegin(GL_LINES)
        glVertex2f(right_x, bottom_y)
        glVertex2f(right_x, bottom_y - detail_size)
        glEnd()

        #cross hair
        size = 50
        middle=20
        glColor3f(0.0, 1.0, 0.0)
        # Vertical line (top)
        glBegin(GL_LINES)
        glVertex2f(center_x, center_y - size)
        glVertex2f(center_x, center_y - middle)
        glEnd()
        # Vertical line (bottom)
        glBegin(GL_LINES)
        glVertex2f(center_x, center_y + middle)
        glVertex2f(center_x, center_y + size)
        glEnd()
        # Horizontal line (left)
        glBegin(GL_LINES)
        glVertex2f(center_x - size, center_y)
        glVertex2f(center_x - middle, center_y)
        glEnd()
        # Horizontal line (right)
        glBegin(GL_LINES)
        glVertex2f(center_x + middle, center_y)
        glVertex2f(center_x + size, center_y)
        glEnd()

        #vertical cross hair
        size = 45
        middle=25
        glColor3f(0.0, 1.0, 0.0)
        # diagonal top left
        glBegin(GL_LINES)
        glVertex2f(center_x-size, center_y - size)
        glVertex2f(center_x-middle, center_y - middle)
        glEnd()
        # diagonal bottom left
        glBegin(GL_LINES)
        glVertex2f(center_x-middle, center_y + middle)
        glVertex2f(center_x-size, center_y + size)
        glEnd()
        # diagonal top right
        glBegin(GL_LINES)
        glVertex2f(center_x + size, center_y - size)
        glVertex2f(center_x + middle, center_y - middle)
        glEnd()
        # diagonal bottomn right
        glBegin(GL_LINES)
        glVertex2f(center_x + size, center_y + size)
        glVertex2f(center_x + middle, center_y + middle)
        glEnd()


    def update_cockpit(self,input_handler,direction_text, player_position,player_right, movement_forward, movement_right, movement_up, planet_and_star, objectList, particleList, WIDTH, HEIGHT,main_loop_counter,focal_length,screen_center):

        ship_data.laser_temp = max(ship_data.laser_temp -0.5, 0)
        self.display_player_laser(direction_text, WIDTH, HEIGHT, main_loop_counter, player_position,player_right,objectList,particleList,focal_length,screen_center)   
        
        ogl_render.render_messages(0,HEIGHT - 180, WIDTH, HEIGHT, FONTS["header"])
        
        self.update_radar(player_position, movement_forward, movement_right, movement_up, objectList, HEIGHT)
        self.update_compass(player_position, movement_forward, movement_right, movement_up, planet_and_star, objectList, WIDTH, HEIGHT)
        self.draw_cockpit_indicators_gl(input_handler, WIDTH, HEIGHT)
        if player.info_screen_page==0:
            self.draw_laser_crosshair(direction_text, WIDTH, HEIGHT)
            
        if global_flags.is_flying or global_flags.is_short_range_jumping:
            ogl_render.drawText(WIDTH/2 - 50, 20, WIDTH,HEIGHT, f"{get_text(direction_text)}", FONTS['body'],
                   text_color=(255, 255, 255, 255), bg_color=(0, 0, 0, 255),centered=True)
            
        if input_handler.docking_active:
            status.add_message(input_handler.docking_text.capitalize(), duration=2)

            
    def display_player_laser(self,direction_text, WIDTH, HEIGHT, main_loop_counter,player_position,player_right,objectList,particleList,focal_length,screen_center):
        laser = ship_data.lasers[self.laser_map[direction_text].value]

        params = global_flags.laser_params.get(laser)

        if global_flags.draw_laser and main_loop_counter<global_flags.laser_frame_end:
            self.draw_laser_beams(laser,WIDTH,HEIGHT)
            if params is not None:
                ship_data.laser_temp = min(255, ship_data.laser_temp + params["temp_increase"]/params["frame_duration"])
                ship_data.energy_level = max(0, ship_data.energy_level - 0.4)

        else:
            global_flags.draw_laser = False
              
  

        if global_flags.firing_laser:
            global_flags.firing_laser = False  #reset flag
            
            if params:
                # For PULSE, check off_frames
                if params["check_off"] and main_loop_counter < (global_flags.laser_frame_end + params["off_frames"]):
                    return

                # For all, check if still in frame
                if not params["check_off"] and main_loop_counter < global_flags.laser_frame_end:
                    return

                temp_increase = params["temp_increase"]
                if ship_data.laser_temp + temp_increase < 255:
                    global_flags.draw_laser = True
                    global_flags.laser_frame_end = main_loop_counter + params["frame_duration"]
                    # Stop previous sound for BEAM/MILITARY/MINING if needed
                    if params["sound"] != SoundType.PULSE_LASER and sound_manager.is_playing(params["sound"]):
                        sound_manager.stop(params["sound"])
                    sound_manager.play(params["sound"])
                    
                    game_events.check_laser_hit(objectList, particleList, player_position,player_right, screen_center, focal_length, params['laser_power'],laser)
                else:
                    global_flags.draw_laser = False