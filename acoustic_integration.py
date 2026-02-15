"""
Acoustic System Integration
============================
Integrates acoustic raycasting into the Backrooms engine.
Adds keyboard controls and visualization.
"""

import pygame
import numpy as np
from simple_loopback import SimpleAudioLoopback


class AcousticIntegration:
    """
    Simple audio loopback integration.
    Uses threaded playback for smoother audio.
    """
    
    def __init__(self, engine):
        self.engine = engine
        
        # Simple loopback (threaded)
        self.simple_loopback = SimpleAudioLoopback()
        self.enabled = False
        
        # Visualization (disabled)
        self.show_echo_viz = False
        self.echo_viz_fade = 0.0
        
    def toggle(self):
        """Toggle simple audio loopback."""
        if self.enabled:
            self.simple_loopback.stop()
            self.enabled = False
            print("🔇 Audio loopback OFF")
        else:
            if self.simple_loopback.start():
                self.enabled = True
                print("🔊 Audio loopback ON (pure passthrough)")
                print("   Speak into your microphone!")
            else:
                print("❌ Failed to start audio loopback")
    
    def toggle_visualization(self):
        """Toggle echo visualization (disabled in simple mode)."""
        print("ℹ️  Visualization only available in full raycasting mode")
    
    def update(self, dt):
        """Update acoustic system."""
        if self.enabled:
            self.simple_loopback.update()
    
    def render_visualization(self, screen, camera):
        """Render echo visualization (disabled in simple mode)."""
        pass  # No visualization in simple mode


def add_acoustic_controls_to_help(help_texts):
    """Add acoustic system controls to help overlay."""
    acoustic_help = [
        "=== AUDIO SYSTEM ===",
        "N: Toggle Voice Loopback (pure passthrough)",
        "Hear yourself with minimal delay!",
    ]
    return help_texts + [""] + acoustic_help
