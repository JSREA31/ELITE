

"""
Sound Manager for Elite Game

Centralized sound management system for all game audio.

Attribution:
- ding.wav by tim.kahn -- https://freesound.org/s/91926/ -- License: Attribution 4.0
- blip15.flac by tim.kahn -- https://freesound.org/s/38503/ -- License: Attribution 4.0
- sounds a bit like 'error'.flac by Timbre -- https://freesound.org/s/210579/ -- License: Attribution NonCommercial 4.0
- droid beep 01 by rubberduck9999 -- https://freesound.org/s/676302/ -- License: Creative Commons 0
- error by Licht2003 -- https://freesound.org/s/808522/ -- License: Creative Commons 0
- 2 alarm short b.wav by jobro -- https://freesound.org/s/33739/ -- License: Attribution 3.0
- SCIAlrm_Alarm, Repeat, Danger, Warning, Error_01_JW Audio by JW_Audio -- https://freesound.org/s/828578/ -- License: Creative Commons 0
- missile_launch_2.wav by smcameron -- https://freesound.org/s/51468/ -- License: Attribution 4.0
 - Deep Explosion by Kodack -- https://freesound.org/s/258195/ -- License: Creative Commons 0
 Oddity White Noise by curtiswcole -- https://freesound.org/s/717303/ -- License: Creative Commons 0
 Rocket Launch.flac by qubodup -- https://freesound.org/s/182794/ -- License: Creative Commons 0
 Title screen and docking computer music frtom original C64 Elite by Aiden Bell & Julie Dunn
"""

import pygame
import numpy as np
import os
from enum import Enum, auto


class SoundType(Enum):
    """Enumeration of all sound effects in the game"""
    LAUNCH = auto()
    HYPERSPACE = auto()
    DOCKING_MUSIC = auto()
    ON = auto()
    OFF = auto()
    ERROR = auto()
    ALARM = auto()
    TARGETING = auto()
    LOCKED_ON = auto()
    MISSILE_LAUNCH = auto()
    EXPLOSION = auto()
    ECM = auto()
    PULSE_LASER = auto()
    BEAM_LASER = auto()
    MINING_LASER = auto()
    MILITARY_LASER = auto()
    LASER_HIT = auto()
    TITLE_MUSIC = auto()
    ENEMY_LASER = auto()
    HIT = auto()
    ENERGY_BOMB = auto()
    ESCAPE_POD_LAUNCH = auto()

    # Add more sound types as needed


class SoundManager:
    """
    Manages all sound effects and music for the game.
    
    Features:
    - Load and cache sound files
    - Play/stop individual sounds
    - Volume control (master and per-sound)
    - Support for looping sounds
    - Music playback (separate from sound effects)
    """
    
    def __init__(self, sound_dir='sound'):
        """
        Initialize the sound manager.
        
        Args:
            sound_dir: Directory containing sound files
        """
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        self.sound_dir = sound_dir
        self.sounds = {}  # Cache for loaded Sound objects
        self.channels = {}  # Track currently playing sounds
        self.master_volume = 1.0
        self.sound_volumes = {}  # Individual sound volumes
        self.music_playing = False
        self.current_music = None
        
        # Sound file mappings
        self.sound_files = {
            SoundType.LAUNCH: 'launch.wav',
            SoundType.HYPERSPACE: 'hyperspace.wav',
            SoundType.DOCKING_MUSIC: 'Docking Sequence.mp3',
            SoundType.ON: 'droid_beep_01.wav',
            SoundType.OFF: 'slow_droid_beep_01.wav',
            SoundType.ERROR: '808522__licht2003__error.mp3',
            SoundType.ALARM: 'SCIAlrm_Alarm_Repeat_Danger_Warning_Error_01_JW_Audio.wav',
            SoundType.TARGETING: 'targeting_33739__jobro__2-alarm-short-b.wav',
            SoundType.LOCKED_ON: 'locked_on_33739__jobro__2-alarm-short-b.wav',
            SoundType.MISSILE_LAUNCH: '51468__smcameron__missile_launch_2.wav',
            SoundType.EXPLOSION: '258195__kodack__deep-explosion.wav',
            SoundType.ECM: 'ecm.wav',
            SoundType.PULSE_LASER: 'pulse_laser.wav',
            SoundType.BEAM_LASER: 'beam_laser.wav',
            SoundType.MINING_LASER: 'mining_laser.wav',
            SoundType.MILITARY_LASER: 'military_laser.wav',
            SoundType.LASER_HIT: 'player_laser_hit.wav',
            SoundType.TITLE_MUSIC: 'title_music.wav',
            SoundType.ENEMY_LASER: 'enemy_laser.wav',
            SoundType.HIT: 'hit.wav',
            SoundType.ENERGY_BOMB: 'energy_bomb.wav',
            SoundType.ESCAPE_POD_LAUNCH: 'escape_pod.wav',
        }
        
    def load_sound(self, sound_type, filename=None):
        """
        Load and cache a sound file.
        
        Args:
            sound_type: SoundType enum or custom string name
            filename: Optional filename override. If not provided, uses sound_files mapping
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Determine filename
            if filename is None:
                if isinstance(sound_type, SoundType):
                    if sound_type not in self.sound_files:
                        print(f"Warning: No file mapping for {sound_type}")
                        return False
                    filename = self.sound_files[sound_type]
                else:
                    print(f"Warning: Must provide filename for custom sound type")
                    return False
                    
            # Build full path
            path = os.path.join(self.sound_dir, filename)
            
            # Load sound
            if not os.path.exists(path):
                print(f"Warning: Sound file not found: {path}")
                return False
                
            self.sounds[sound_type] = pygame.mixer.Sound(path)
            self.sound_volumes[sound_type] = 1.0
            return True
            
        except Exception as e:
            print(f"Error loading sound {sound_type}: {e}")
            return False
            
    def load_all(self):
        """Load all sounds defined in sound_files mapping"""
        for sound_type in self.sound_files.keys():
            self.load_sound(sound_type)
            
    def play(self, sound_type, loops=0, fade_ms=0, maxtime=0,volume=None):
        """
        Play a sound effect.
        
        Args:
            sound_type: SoundType enum or string name of the sound
            loops: Number of times to loop (-1 for infinite)
            fade_ms: Time in ms to fade in the sound
            maxtime: Maximum play time in ms (0 for unlimited)
            
        Returns:
            pygame.mixer.Channel object or None
        """
        # Auto-load if not already loaded
        if sound_type not in self.sounds:
            if not self.load_sound(sound_type):
                return None
                
        try:
            # Set volume
            if volume is not None:
                vol = self.master_volume * max(0.0, min(1.0, volume))
            else:
                vol = self.master_volume * self.sound_volumes.get(sound_type, 1.0)
            self.sounds[sound_type].set_volume(vol)
            
            # Play sound
            channel = self.sounds[sound_type].play(loops, maxtime, fade_ms)
            if channel:
                self.channels[sound_type] = channel
            return channel
        
        except Exception as e:
            print(f"Error playing sound {sound_type}: {e}")
            return None

    def play_3d_sound(self, sound_type, object_pos, player_pos, player_right, distance_to_player, max_distance=2000.0):
        """
        Play a sound with volume and stereo panning based on object position.
        sound_type: SoundType enum or string
        object_pos: np.array([x, y, z])
        player_pos: np.array([x, y, z])
        player_right: np.array([x, y, z]) - player's right direction vector
        distance_to_player: float - object's distance to player
        max_distance: float - distance at which sound is inaudible
        """
        # Calculate volume using object's distance_to_player
        volume = max(0.0, 1.0 - distance_to_player / max_distance)

        # Calculate left/right pan
        vec = object_pos - player_pos
        if np.linalg.norm(vec) > 0:
            vec_norm = vec / np.linalg.norm(vec)
            pan = np.dot(vec_norm, -player_right)  # -1 (left) to +1 (right)
        else:
            pan = 0.0

        # Map pan to left/right volumes
        left = volume * (0.5 - 0.5 * pan)
        right = volume * (0.5 + 0.5 * pan)

        # Auto-load if not already loaded
        if sound_type not in self.sounds:
            if not self.load_sound(sound_type):
                return None

        channel = self.sounds[sound_type].play()
        if channel:
            channel.set_volume(left, right)
        return channel

    def stop(self, sound_type, fade_ms=0):
        """
        Stop a specific sound.
        
        Args:
            sound_type: SoundType enum or string name of the sound
            fade_ms: Time in ms to fade out the sound
        """
        if sound_type in self.sounds:
            try:
                if fade_ms > 0:
                    self.sounds[sound_type].fadeout(fade_ms)
                else:
                    self.sounds[sound_type].stop()
                    
                # Remove from active channels
                if sound_type in self.channels:
                    del self.channels[sound_type]
                    
            except Exception as e:
                print(f"Error stopping sound {sound_type}: {e}")
                
    def stop_all(self, fade_ms=0):
        """
        Stop all currently playing sounds.
        
        Args:
            fade_ms: Time in ms to fade out all sounds
        """
        if fade_ms > 0:
            pygame.mixer.fadeout(fade_ms)
        else:
            pygame.mixer.stop()
        self.channels.clear()
        
    def is_playing(self, sound_type):
        """
        Check if a specific sound is currently playing.
        
        Args:
            sound_type: SoundType enum or string name
            
        Returns:
            True if sound is playing, False otherwise
        """
        if sound_type in self.channels:
            channel = self.channels[sound_type]
            if channel and channel.get_busy():
                return True
            else:
                # Clean up stale channel reference
                del self.channels[sound_type]
        return False
        
    def set_volume(self, sound_type, volume):
        """
        Set volume for a specific sound (0.0 to 1.0).
        
        Args:
            sound_type: SoundType enum or string name
            volume: Volume level from 0.0 (silent) to 1.0 (full)
        """
        volume = max(0.0, min(1.0, volume))
        self.sound_volumes[sound_type] = volume
        
        # Update volume if sound is loaded
        if sound_type in self.sounds:
            self.sounds[sound_type].set_volume(self.master_volume * volume)
            
    def set_master_volume(self, volume):
        """
        Set master volume for all sounds (0.0 to 1.0).
        
        Args:
            volume: Volume level from 0.0 (silent) to 1.0 (full)
        """
        self.master_volume = max(0.0, min(1.0, volume))
        
        # Update all loaded sounds
        for sound_type, sound in self.sounds.items():
            individual_vol = self.sound_volumes.get(sound_type, 1.0)
            sound.set_volume(self.master_volume * individual_vol)
            
    def play_music(self, sound_type, loops=-1, fade_ms=0):
        """
        Play music using pygame.mixer.music (good for long audio files).
        
        Args:
            sound_type: SoundType enum (e.g., DOCKING_MUSIC)
            loops: Number of times to loop (-1 for infinite)
            fade_ms: Time in ms to fade in the music
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Determine filename
            if isinstance(sound_type, SoundType) and sound_type in self.sound_files:
                filename = self.sound_files[sound_type]
            else:
                print(f"Warning: No music file mapping for {sound_type}")
                return False
                
            path = os.path.join(self.sound_dir, filename)
            
            if not os.path.exists(path):
                print(f"Warning: Music file not found: {path}")
                return False
                
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops, fade_ms=int(fade_ms / 1000))
            self.music_playing = True
            self.current_music = sound_type
            return True
            
        except Exception as e:
            print(f"Error playing music {sound_type}: {e}")
            return False
            
    def stop_music(self, fade_ms=0):
        """
        Stop currently playing music.
        
        Args:
            fade_ms: Time in ms to fade out the music
        """
        try:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
            self.music_playing = False
            self.current_music = None
        except Exception as e:
            print(f"Error stopping music: {e}")
            
    def is_music_playing(self):
        """Check if music is currently playing"""
        return pygame.mixer.music.get_busy()
        
    def set_music_volume(self, volume):
        """
        Set music volume (0.0 to 1.0).
        
        Args:
            volume: Volume level from 0.0 (silent) to 1.0 (full)
        """
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume * self.master_volume)


# Global singleton instance
sound_manager = SoundManager()

# Convenience functions for direct module access
def play(sound_type, **kwargs):
    """Play a sound. See SoundManager.play() for details."""
    return sound_manager.play(sound_type, **kwargs)

def stop(sound_type, **kwargs):
    """Stop a sound. See SoundManager.stop() for details."""
    sound_manager.stop(sound_type, **kwargs)

def play_music(sound_type, **kwargs):
    """Play music. See SoundManager.play_music() for details."""
    return sound_manager.play_music(sound_type, **kwargs)

def stop_music(**kwargs):
    """Stop music. See SoundManager.stop_music() for details."""
    sound_manager.stop_music(**kwargs)

def set_master_volume(volume):
    """Set master volume. See SoundManager.set_master_volume() for details."""
    sound_manager.set_master_volume(volume)
