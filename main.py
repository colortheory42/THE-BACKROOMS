"""
The Backrooms - Main Game Loop
Destructible walls with pixel debris physics.

Now includes:
- MENU (title / home screen)
- PLAYING (normal gameplay)
- PAUSED (pause overlay)
"""

import pygame
import sys
from enum import Enum, auto

from config import *
from engine import BackroomsEngine
from audio import (
    generate_backrooms_hum,
    generate_footstep_sound,
    generate_player_footstep_sound,
    generate_crouch_footstep_sound,
    generate_electrical_buzz,
    generate_destroy_sound,
    generate_crack_sound,
    generate_fracture_sound
)
from save_system import SaveSystem

# Acoustic system (optional - graceful degradation if not available)
try:
    from acoustic_integration import AcousticIntegration, add_acoustic_controls_to_help
    ACOUSTIC_AVAILABLE = True
except ImportError:
    ACOUSTIC_AVAILABLE = False
    print("⚠️  Acoustic system not available")
    print("   Install PyAudio for voice echo: pip install pyaudio")


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()

def set_mouse_locked(engine, locked: bool):
    if engine.mouse_look != locked:
        engine.toggle_mouse()


def _draw_dim_overlay(screen, alpha=180):
    """Draw a translucent black overlay over the whole screen."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, max(0, min(255, alpha))))
    screen.blit(overlay, (0, 0))


def _draw_centered_text(screen, font, text, y, color=(220, 220, 220)):
    surf = font.render(text, True, color)
    x = WIDTH // 2 - surf.get_width() // 2
    screen.blit(surf, (x, y))
    return surf


def _start_hum(hum_sound):
    """Start ambient hum if not already playing."""
    if hum_sound:
        hum_sound.play(loops=-1)
        hum_sound.set_volume(0.4)


def _stop_hum(hum_sound):
    """Stop hum cleanly."""
    if hum_sound:
        hum_sound.stop()


def main():
    # Initialize Pygame
    pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 1024)  # Lower latency
    pygame.mixer.init()
    pygame.mixer.set_num_channels(32)  # Increase channels for acoustic playback

    # Create display
    SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("The Backrooms - Destructible")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    small_font = pygame.font.SysFont("consolas", 12)
    title_font = pygame.font.SysFont("consolas", 28, bold=True)

    # Create engine
    engine = BackroomsEngine(WIDTH, HEIGHT)

    engine.mouse_look = False
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    # Generate sounds
    print("Generating ambient sounds...")
    hum_sound = generate_backrooms_hum()
    footstep_sound = generate_footstep_sound()
    player_footstep_sound = generate_player_footstep_sound()
    crouch_footstep_sound = generate_crouch_footstep_sound()
    buzz_sound = generate_electrical_buzz()
    destroy_sound = generate_destroy_sound()
    crack_sound = generate_crack_sound()
    fracture_sound = generate_fracture_sound()

    sound_effects = {
        'footstep': footstep_sound,
        'player_footstep': player_footstep_sound,
        'crouch_footstep': crouch_footstep_sound,
        'buzz': buzz_sound,
        'destroy': destroy_sound,
        'crack': crack_sound,
        'fracture': fracture_sound
    }

    # Give engine access to sound effects for event-driven playback
    engine.sound_effects = sound_effects

    # Initialize acoustic system (if available)
    acoustic = None
    if ACOUSTIC_AVAILABLE:
        acoustic = AcousticIntegration(engine)
        print("🎤 Acoustic system ready - press V to enable voice echoes")

    # -------------------------
    # UI state
    # -------------------------
    show_help = True
    help_timer = 5.0
    save_message = ""
    save_message_timer = 0.0

    # -------------------------
    # Game state
    # -------------------------
    state = GameState.MENU

    # Start in MENU with mouse released
    if not engine.mouse_look:
        engine.toggle_mouse()

    # Don't start hum until you actually "enter" the world
    hum_playing = False

    # Main loop
    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        mouse_rel = None

        # Timers only matter while playing (or keep them global; either is fine)
        if state == GameState.PLAYING:
            if show_help and help_timer > 0:
                help_timer -= dt
                if help_timer <= 0:
                    show_help = False

            if save_message_timer > 0:
                save_message_timer -= dt
                if save_message_timer <= 0:
                    save_message = ""

        # -------------------------
        # Event handling
        # -------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # MOUSE motion only matters in PLAYING
            if event.type == pygame.MOUSEMOTION and state == GameState.PLAYING and engine.mouse_look:
                mouse_rel = event.rel

            if event.type == pygame.KEYDOWN:

                # Global quit (ESC in menu, or explicit quit in pause)
                if state == GameState.MENU:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    # Enter world
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        state = GameState.PLAYING
                        set_mouse_locked(engine, True)
                        show_help = True
                        help_timer = 5.0
                        save_message = ""
                        save_message_timer = 0.0

                        # Start hum now
                        if not hum_playing:
                            _start_hum(hum_sound)
                            hum_playing = True

                    # Optional: quick load straight from menu
                    if event.key == pygame.K_F9:
                        save_data = SaveSystem.load_game(slot=1)
                        if save_data:
                            engine.load_from_save(save_data)
                            save_message = "Loaded slot 1."
                            save_message_timer = 2.0
                        else:
                            save_message = "No save found in slot 1."
                            save_message_timer = 2.0

                elif state == GameState.PLAYING:
                    # Pause toggle
                    if event.key == pygame.K_ESCAPE:
                        # If mouse look is on, pause should also release mouse so menu feels normal
                        if engine.mouse_look:
                            engine.toggle_mouse()
                        set_mouse_locked(engine, False)
                        state = GameState.PAUSED

                        continue



                    # Render scale
                    if event.key == pygame.K_r:
                        engine.toggle_render_scale()

                    # Help toggle
                    if event.key == pygame.K_h:
                        show_help = not show_help
                        if show_help:
                            help_timer = 999

                    # Acoustic system controls (if available)
                    if ACOUSTIC_AVAILABLE and acoustic:
                        if event.key == pygame.K_n:
                            acoustic.toggle()  # Simple smooth loopback

                    # Quick save
                    if event.key == pygame.K_F5:
                        SaveSystem.save_game(engine, slot=1)
                        save_message = "Game saved to slot 1!"
                        save_message_timer = 3.0

                    # Quick load
                    if event.key == pygame.K_F9:
                        save_data = SaveSystem.load_game(slot=1)
                        if save_data:
                            engine.load_from_save(save_data)
                            save_message = "Game loaded from slot 1!"
                            save_message_timer = 3.0
                        else:
                            save_message = "No save found in slot 1!"
                            save_message_timer = 3.0

                    # Destroy wall (E key)
                    if event.key == pygame.K_e:
                        target = engine.find_targeted_wall_or_pillar()
                        if target:
                            target_type, target_key = target
                            if target_type == 'wall':
                                engine.destroy_wall(target_key, sound_effects['destroy'])
                            elif target_type == 'pillar':
                                engine.destroy_pillar(target_key, sound_effects['destroy'])

                elif state == GameState.PAUSED:
                    # Resume
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        state = GameState.PLAYING
                        set_mouse_locked(engine, True)
                        # If you want mouse locked on resume, toggle it back on (optional)
                        # Only do this if you prefer "game feel" by default:
                        # if not engine.mouse_look: engine.toggle_mouse()
                        continue

                    # Return to menu
                    if event.key == pygame.K_BACKSPACE:
                        state = GameState.MENU
                        if not engine.mouse_look:
                            engine.toggle_mouse()
                        continue

                    # Quit from pause
                    if event.key == pygame.K_q:
                        running = False

            # Mouse click destruction only in PLAYING
            # Mouse click - progressive damage
            if event.type == pygame.MOUSEBUTTONDOWN and state == GameState.PLAYING:
                if event.button == 1:
                    target = engine.find_targeted_wall_or_pillar()
                    if target:
                        target_type, target_key = target
                        if target_type == 'wall':
                            # Progressive damage - takes multiple hits
                            destroyed = engine.hit_wall(target_key, damage=0.35)
                            if destroyed:
                                sound_effects['destroy'].play()
                        elif target_type == 'pillar':
                            # Pillars still instant destroy
                            engine.destroy_pillar(target_key, sound_effects['destroy'])

        # -------------------------
        # Update + Render
        # -------------------------
        if state == GameState.MENU:
            # Render a simple “background” (reuse engine render so it still feels like a place)
            engine.render(SCREEN)
            _draw_dim_overlay(SCREEN, alpha=190)

            _draw_centered_text(SCREEN, title_font, "THE BACKROOMS", HEIGHT // 2 - 120, (250, 240, 150))
            _draw_centered_text(SCREEN, font, "Destructible • Procedural • Infinite", HEIGHT // 2 - 80, (200, 220, 250))

            _draw_centered_text(SCREEN, font, "Press ENTER to enter", HEIGHT // 2 - 10, (220, 220, 220))
            _draw_centered_text(SCREEN, font, "Press ESC to quit", HEIGHT // 2 + 20, (180, 180, 180))
            _draw_centered_text(SCREEN, small_font, "Tip: F9 loads Slot 1 from the menu", HEIGHT // 2 + 60, (160, 160, 160))

            if save_message and save_message_timer > 0:
                _draw_centered_text(SCREEN, font, save_message, HEIGHT // 2 + 95, (100, 255, 100))

            pygame.display.flip()
            continue

        if state == GameState.PAUSED:
            # Render the world behind pause overlay (freeze gameplay)
            engine.render(SCREEN)
            _draw_dim_overlay(SCREEN, alpha=170)

            _draw_centered_text(SCREEN, title_font, "PAUSED", HEIGHT // 2 - 90, (250, 240, 150))
            _draw_centered_text(SCREEN, font, "ENTER / ESC: Resume", HEIGHT // 2 - 20, (220, 220, 220))
            _draw_centered_text(SCREEN, font, "BACKSPACE: Return to Menu", HEIGHT // 2 + 10, (200, 200, 200))
            _draw_centered_text(SCREEN, font, "Q: Quit", HEIGHT // 2 + 40, (180, 180, 180))

            pygame.display.flip()
            continue

        # PLAYING
        keys = pygame.key.get_pressed()
        engine.update(dt, keys, mouse_rel)
        engine.update_sounds(dt, sound_effects)
        engine.update_player_footsteps(
            dt,
            sound_effects['player_footstep'],
            sound_effects['crouch_footstep']
        )
        engine.update_flicker(dt)
        engine.update_render_scale(dt)

        # Update acoustic system
        if ACOUSTIC_AVAILABLE and acoustic:
            acoustic.update(dt)

        engine.render(SCREEN)

        # Render acoustic visualization (if enabled)
        if ACOUSTIC_AVAILABLE and acoustic:
            acoustic.render_visualization(SCREEN, engine.camera)

        

        # Save message
        if save_message:
            save_msg_surface = font.render(save_message, True, (100, 255, 100))
            msg_x = WIDTH // 2 - save_msg_surface.get_width() // 2
            SCREEN.blit(save_msg_surface, (msg_x, 70))

        # Help overlay
        if show_help:
            help_y = HEIGHT - 280
            help_texts = [
                "=== CONTROLS ===",
                "WASD: Move | M: Mouse Look | JL: Turn",
                "SHIFT: Run | C: Crouch | SPACE: Jump",
                "LEFT CLICK or E: Destroy Wall (aim at wall)",
                "R: Toggle Performance | H: Help | ESC: Pause",
                "=== SAVE/LOAD ===",
                "F5: Quick Save (Slot 1) | F9: Quick Load (Slot 1)",
                "=== DESTRUCTION ===",
                "Aim center crosshair at wall and click to destroy",
                "Watch debris pile form on the floor!",
            ]
            
            # Add acoustic controls if available
            if ACOUSTIC_AVAILABLE:
                help_texts = add_acoustic_controls_to_help(help_texts)

            for i, text in enumerate(help_texts):
                help_surface = font.render(text, True, (250, 240, 150))
                SCREEN.blit(help_surface, (10, help_y + i * 25))

        pygame.display.flip()

    # Cleanup
    try:
        _stop_hum(hum_sound)
    except Exception:
        pass
    
    # Stop acoustic system
    if ACOUSTIC_AVAILABLE and acoustic and acoustic.enabled:
        acoustic.simple_loopback.stop()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
