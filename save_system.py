"""
Save/load system.
Handles game state persistence to JSON files.

UPDATED: Now properly saves complete world state including:
- wall_cache and pillar_cache (the actual map layout)
- All destruction and damage states
- Debris particles
"""

import os
import json
from datetime import datetime
from config import SAVE_DIR


class SaveSystem:
    """Manages game saves and loads."""

    @staticmethod
    def ensure_save_dir():
        """Create save directory if it doesn't exist."""
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

    @staticmethod
    def get_save_path(slot=1):
        """Get filepath for a save slot."""
        SaveSystem.ensure_save_dir()
        return os.path.join(SAVE_DIR, f"save_slot_{slot}.json")

    @staticmethod
    def save_game(engine, slot=1):
        """
        Save complete game state to JSON file.
        
        Includes:
        - Player position and orientation
        - Complete world state (walls, pillars, damage, debris)
        - Play time statistics
        """
        # Get complete world state from world object
        world_state = engine.world.get_state_for_save()
        
        save_data = {
            'version': '1.1',  # Updated version to indicate new save format
            'timestamp': datetime.now().isoformat(),
            'player': {
                'x': engine.x,
                'y': engine.y,
                'z': engine.z,
                'pitch': engine.pitch,
                'yaw': engine.yaw
            },
            'world': world_state,
            'stats': {
                'play_time': engine.play_time
            }
        }

        save_path = SaveSystem.get_save_path(slot)
        with open(save_path, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"Game saved to slot {slot}")
        print(f"  Saved {len(world_state.get('wall_cache', {}))} walls")
        print(f"  Saved {len(world_state.get('pillar_cache', {}))} pillars")
        print(f"  Saved {len(world_state.get('destroyed_walls', []))} destroyed walls")
        print(f"  Saved {len(world_state.get('debris_pieces', []))} debris pieces")
        return True

    @staticmethod
    def load_game(slot=1):
        """Load game state from JSON file."""
        save_path = SaveSystem.get_save_path(slot)

        if not os.path.exists(save_path):
            print(f"No save found in slot {slot}")
            return None

        try:
            with open(save_path, 'r') as f:
                save_data = json.load(f)
            
            version = save_data.get('version', '1.0')
            print(f"Game loaded from slot {slot} (version {version})")
            
            # Show what was loaded
            world_data = save_data.get('world', {})
            if 'wall_cache' in world_data:
                print(f"  Loaded {len(world_data['wall_cache'])} walls")
            if 'pillar_cache' in world_data:
                print(f"  Loaded {len(world_data['pillar_cache'])} pillars")
            
            return save_data
        except Exception as e:
            print(f"Error loading save: {e}")
            return None

    @staticmethod
    def list_saves():
        """List all available save slots."""
        SaveSystem.ensure_save_dir()
        saves = []
        for i in range(1, 6):  # Check slots 1-5
            save_path = SaveSystem.get_save_path(i)
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r') as f:
                        data = json.load(f)
                    
                    # Get world stats if available
                    world_data = data.get('world', {})
                    walls_count = len(world_data.get('wall_cache', {}))
                    destroyed_count = len(world_data.get('destroyed_walls', []))
                    
                    saves.append({
                        'slot': i,
                        'timestamp': data.get('timestamp', 'Unknown'),
                        'play_time': data.get('stats', {}).get('play_time', 0),
                        'version': data.get('version', '1.0'),
                        'walls_explored': walls_count,
                        'walls_destroyed': destroyed_count
                    })
                except:
                    pass
        return saves
    
    @staticmethod
    def get_save_info(slot=1):
        """Get detailed info about a specific save slot."""
        save_path = SaveSystem.get_save_path(slot)
        
        if not os.path.exists(save_path):
            return None
        
        try:
            with open(save_path, 'r') as f:
                data = json.load(f)
            
            world_data = data.get('world', {})
            player_data = data.get('player', {})
            
            return {
                'version': data.get('version', '1.0'),
                'timestamp': data.get('timestamp', 'Unknown'),
                'play_time': data.get('stats', {}).get('play_time', 0),
                'player_position': (
                    player_data.get('x', 0),
                    player_data.get('y', 0),
                    player_data.get('z', 0)
                ),
                'world_seed': world_data.get('seed', 0),
                'walls_explored': len(world_data.get('wall_cache', {})),
                'pillars_explored': len(world_data.get('pillar_cache', {})),
                'walls_destroyed': len(world_data.get('destroyed_walls', [])),
                'pillars_destroyed': len(world_data.get('destroyed_pillars', [])),
                'debris_count': len(world_data.get('debris_pieces', []))
            }
        except Exception as e:
            print(f"Error reading save info: {e}")
            return None
