"""
World system.
Manages zones, walls, pillars, destruction state, and collision queries.

UPDATED: Enhanced save/load to preserve exact map state including:
- wall_cache: which walls exist in explored areas
- pillar_cache: which pillars exist in explored areas
- All destruction and damage states
"""

import math
import random
from enum import Enum, auto
from config import (
    PILLAR_SPACING, PILLAR_SIZE, PILLAR_MODE, WALL_THICKNESS,
    ZONE_SIZE, HALLWAY_WIDTH, WALL_COLOR, PILLAR_COLOR,
    get_scaled_wall_height, get_scaled_floor_y
)
from procedural import ProceduralZone
from debris import Debris
from events import event_bus, EventType


class WallState(Enum):
    """Progressive damage states for walls."""
    INTACT = auto()      # Full health, no visible damage
    CRACKED = auto()     # Hairline cracks, still solid
    FRACTURED = auto()   # Major cracks, chunks missing
    BREAKING = auto()    # Actively falling/crumbling
    DESTROYED = auto()   # Gone, only debris remains


class World:
    """World state and procedural queries."""

    def __init__(self, world_seed=None):
        self.world_seed = world_seed if world_seed is not None else random.randint(0, 999999)

        # Caches - THESE ARE NOW SAVED TO PRESERVE MAP LAYOUT
        self.pillar_cache = {}  # (x, z) -> bool
        self.wall_cache = {}    # tuple(sorted([(x1,z1), (x2,z2)])) -> bool
        self.zone_cache = {}
        self.lamp_cache = {}
        self.trap_cache = {}

        # Destruction state
        self.destroyed_walls = set()
        self.destroyed_pillars = set()
        self.destroyed_lamps = set()
        self.triggered_traps = set()
        self.pre_damaged_walls = {}  # wall_key -> damage_state (0.0-1.0)

        # Progressive wall damage system
        self.wall_states = {}   # wall_key -> WallState
        self.wall_health = {}   # wall_key -> float (0.0 to 1.0)
        self.wall_cracks = {}   # wall_key -> list of (u, v, angle, length) tuples

        # Debris
        self.debris_pieces = []
        self._spawned_rubble = set()

        print(f"World seed: {self.world_seed}")

    # === ZONE SYSTEM ===

    def get_zone_at(self, x, z):
        """Get zone coordinates for a world position."""
        zone_x = int(x // ZONE_SIZE)
        zone_z = int(z // ZONE_SIZE)
        return (zone_x, zone_z)

    def get_zone_properties(self, zone_x, zone_z):
        """Get cached zone properties."""
        key = (zone_x, zone_z)
        if key not in self.zone_cache:
            self.zone_cache[key] = ProceduralZone.get_zone_properties(zone_x, zone_z, self.world_seed)
        return self.zone_cache[key]

    # === PILLAR QUERIES ===

    def has_pillar_at(self, px, pz):
        """Check if there's a pillar at this position."""
        key = (px, pz)
        if key in self.pillar_cache:
            return self.pillar_cache[key]

        if PILLAR_MODE == "none":
            self.pillar_cache[key] = False
            return False

        offset = PILLAR_SPACING // 2
        is_on_pillar_grid = (px % PILLAR_SPACING == offset) and (pz % PILLAR_SPACING == offset)

        if not is_on_pillar_grid:
            self.pillar_cache[key] = False
            return False

        if PILLAR_MODE == "all":
            self.pillar_cache[key] = True
            return True

        # Deterministic random based on position
        seed = hash((px, pz, self.world_seed)) % 100000
        rng = random.Random(seed)

        probability_map = {
            "sparse": 0.10,
            "normal": 0.30,
            "dense": 0.60,
        }

        probability = probability_map.get(PILLAR_MODE, 0.0)
        has_pillar = rng.random() < probability

        self.pillar_cache[key] = has_pillar
        return has_pillar

    def is_pillar_destroyed(self, pillar_key):
        """Check if a pillar has been destroyed."""
        return pillar_key in self.destroyed_pillars

    # === WALL QUERIES ===

    def has_wall_between(self, x1, z1, x2, z2):
        """Check if there's a wall between two grid points."""
        key = tuple(sorted([(x1, z1), (x2, z2)]))

        if key in self.wall_cache:
            return self.wall_cache[key]

        is_horizontal = (z1 == z2)
        is_vertical = (x1 == x2)

        if not (is_horizontal or is_vertical):
            self.wall_cache[key] = False
            return False

        # Check for pre-existing damage
        if key not in self.pre_damaged_walls:
            zone = self.get_zone_at((x1 + x2) / 2, (z1 + z2) / 2)
            props = self.get_zone_properties(*zone)

            # Deterministic decay check
            decay_seed = int(x1 * 7919 + z1 * 6577 + x2 * 4993 + z2 * 3571 + self.world_seed * 9973)
            rng = random.Random(decay_seed)

            if rng.random() < props['decay_chance']:
                damage = rng.uniform(0.0, 0.5)
                self.pre_damaged_walls[key] = damage

                # Fully destroyed
                if damage < 0.2:
                    self.destroyed_walls.add(key)

        has_wall = True
        self.wall_cache[key] = has_wall
        return has_wall

    def is_wall_destroyed(self, wall_key):
        """Check if a wall has been destroyed."""
        return wall_key in self.destroyed_walls

    def get_wall_damage(self, wall_key):
        """Get damage state for a wall (1.0 = intact, 0.0 = rubble)."""
        return self.pre_damaged_walls.get(wall_key, 1.0)

    def get_doorway_type(self, x1, z1, x2, z2):
        """Determine if a wall has a doorway or hallway."""
        is_horizontal = (z1 == z2)

        if is_horizontal:
            door_seed = int(z1 * 3571 + ((x1 + x2) // 2) * 2897 + self.world_seed * 9973)
        else:
            door_seed = int(x1 * 3571 + ((z1 + z2) // 2) * 2897 + self.world_seed * 9973)

        rng = random.Random(door_seed)
        roll = rng.random()

        if roll < 0.3:
            return "hallway"
        elif roll < 0.5:
            return "doorway"
        else:
            return None

    # === PROGRESSIVE WALL DAMAGE ===

    def get_wall_state(self, wall_key):
        """Get current damage state of a wall."""
        if wall_key in self.destroyed_walls:
            return WallState.DESTROYED
        return self.wall_states.get(wall_key, WallState.INTACT)

    def get_wall_health(self, wall_key):
        """Get wall health (1.0 = full, 0.0 = destroyed)."""
        if wall_key in self.destroyed_walls:
            return 0.0
        return self.wall_health.get(wall_key, 1.0)

    def get_wall_cracks(self, wall_key):
        """Get crack data for rendering."""
        return self.wall_cracks.get(wall_key, [])

    def _get_wall_center(self, wall_key):
        """Get world position of wall center."""
        (x1, z1), (x2, z2) = wall_key
        h = get_scaled_wall_height()
        floor_y = get_scaled_floor_y()
        return (
            (x1 + x2) / 2,
            (floor_y + h) / 2,
            (z1 + z2) / 2
        )

    def _add_crack(self, wall_key, hit_u=None, hit_v=None):
        """Add a crack at hit position (or random if not specified)."""
        if wall_key not in self.wall_cracks:
            self.wall_cracks[wall_key] = []

        u = hit_u if hit_u is not None else random.uniform(0.1, 0.9)
        v = hit_v if hit_v is not None else random.uniform(0.1, 0.9)
        angle = random.uniform(0, math.pi)
        length = random.uniform(0.1, 0.4)

        self.wall_cracks[wall_key].append((u, v, angle, length))

    def hit_wall(self, wall_key, damage=0.25):
        """
        Apply damage to a wall (progressive destruction).
        Returns True if wall was destroyed.
        """
        if wall_key in self.destroyed_walls:
            return False

        # Initialize health if needed
        if wall_key not in self.wall_health:
            self.wall_health[wall_key] = 1.0
            self.wall_states[wall_key] = WallState.INTACT

        # Apply damage
        self.wall_health[wall_key] -= damage
        health = self.wall_health[wall_key]

        # Get position for event
        position = self._get_wall_center(wall_key)

        # State transitions based on health
        if health <= 0.0:
            # DESTROYED
            self.destroyed_walls.add(wall_key)
            self.wall_states[wall_key] = WallState.DESTROYED
            self.spawn_wall_debris(wall_key)
            event_bus.emit(EventType.WALL_DESTROYED, wall_key=wall_key, position=position)
            return True

        elif health <= 0.33 and self.wall_states[wall_key] != WallState.FRACTURED:
            # FRACTURED
            self.wall_states[wall_key] = WallState.FRACTURED
            self._add_crack(wall_key)
            self._add_crack(wall_key)
            event_bus.emit(EventType.WALL_FRACTURED, wall_key=wall_key, position=position)

        elif health <= 0.66 and self.wall_states[wall_key] == WallState.INTACT:
            # CRACKED
            self.wall_states[wall_key] = WallState.CRACKED
            self._add_crack(wall_key)
            event_bus.emit(EventType.WALL_CRACKED, wall_key=wall_key, position=position)

        return False

    def destroy_wall(self, wall_key, destroy_sound):
        """Instantly destroy a wall (bypasses progressive damage)."""
        if wall_key in self.destroyed_walls:
            return

        self.destroyed_walls.add(wall_key)
        self.wall_states[wall_key] = WallState.DESTROYED
        self.wall_health[wall_key] = 0.0

        position = self._get_wall_center(wall_key)
        self.spawn_wall_debris(wall_key)
        event_bus.emit(EventType.WALL_DESTROYED, wall_key=wall_key, position=position)

        if destroy_sound:
            destroy_sound.play()

    def spawn_wall_debris(self, wall_key):
        """Spawn debris particles for a destroyed wall."""
        (x1, z1), (x2, z2) = wall_key
        h = get_scaled_wall_height()
        floor_y = get_scaled_floor_y()

        cx = (x1 + x2) / 2
        cz = (z1 + z2) / 2

        # Spawn debris particles
        for _ in range(150):
            offset_x = random.uniform(-PILLAR_SPACING/2, PILLAR_SPACING/2)
            offset_z = random.uniform(-WALL_THICKNESS, WALL_THICKNESS)
            py = random.uniform(floor_y, h)

            vx = random.uniform(-10, 10)
            vy = random.uniform(-5, 5)
            vz = random.uniform(-10, 10)

            color_var = random.randint(-40, 20)
            particle_color = (
                max(0, min(255, WALL_COLOR[0] + color_var)),
                max(0, min(255, WALL_COLOR[1] + color_var)),
                max(0, min(255, WALL_COLOR[2] + color_var))
            )

            if x1 == x2:  # Vertical wall
                px = cx + offset_z
                pz = cz + offset_x
            else:  # Horizontal wall
                px = cx + offset_x
                pz = cz + offset_z

            self.debris_pieces.append(Debris(
                (px, py, pz),
                particle_color,
                velocity=(vx, vy, vz)
            ))

    def destroy_pillar(self, pillar_key, destroy_sound):
        """Destroy a pillar."""
        if pillar_key in self.destroyed_pillars:
            return

        self.destroyed_pillars.add(pillar_key)
        px, pz = pillar_key
        h = get_scaled_wall_height()
        floor_y = get_scaled_floor_y()
        position = (px + PILLAR_SIZE/2, (floor_y + h)/2, pz + PILLAR_SIZE/2)

        # Spawn debris
        for _ in range(200):
            offset_x = random.uniform(0, PILLAR_SIZE)
            offset_z = random.uniform(0, PILLAR_SIZE)
            py = random.uniform(floor_y, h)

            dx = (px + PILLAR_SIZE/2) - (px + offset_x)
            dz = (pz + PILLAR_SIZE/2) - (pz + offset_z)
            dist = math.sqrt(dx ** 2 + dz ** 2) + 0.1

            speed = random.uniform(8, 20)
            vx = (dx / dist) * speed + random.uniform(-3, 3)
            vy = random.uniform(-20, -5)
            vz = (dz / dist) * speed + random.uniform(-3, 3)

            color_var = random.randint(-30, 30)
            particle_color = (
                max(0, min(255, PILLAR_COLOR[0] + color_var)),
                max(0, min(255, PILLAR_COLOR[1] + color_var)),
                max(0, min(255, PILLAR_COLOR[2] + color_var))
            )

            self.debris_pieces.append(Debris(
                (px, py, pz),
                particle_color,
                velocity=(vx, vy, vz)
            ))

        event_bus.emit(EventType.PILLAR_DESTROYED,
                      pillar_key=pillar_key, position=position)

        if destroy_sound:
            destroy_sound.play()

    def spawn_rubble_pile(self, x1, z1, x2, z2):
        """Spawn a persistent rubble pile for pre-destroyed walls."""
        wall_key = tuple(sorted([(x1, z1), (x2, z2)]))

        if wall_key in self._spawned_rubble:
            return

        self._spawned_rubble.add(wall_key)

        floor_y = get_scaled_floor_y()
        half_thick = WALL_THICKNESS / 2

        if x1 == x2:
            min_x, max_x = x1 - half_thick, x1 + half_thick
            min_z, max_z = min(z1, z2), max(z1, z2)
        else:
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_z, max_z = z1 - half_thick, z1 + half_thick

        # Spawn settled debris
        for _ in range(80):
            px = random.uniform(min_x, max_x)
            pz = random.uniform(min_z, max_z)

            color_var = random.randint(-40, 20)
            particle_color = (
                max(0, min(255, 200 + color_var)),
                max(0, min(255, 180 + color_var)),
                max(0, min(255, 160 + color_var))
            )

            self.debris_pieces.append(Debris(
                (px, floor_y, pz),
                particle_color,
                velocity=None  # Settled from the start
            ))

    # === DEBRIS UPDATE ===

    def update_debris(self, dt, player_x, player_z):
        """Update all debris particles."""
        floor_y = get_scaled_floor_y()
        MAX_DEBRIS = 12000
        DEBRIS_CULL_DIST = 900.0

        for d in self.debris_pieces:
            d.update(dt, floor_y)
            if not d.active:
                continue

            # Cull distant debris
            dx = d.cx - player_x
            dz = d.cz - player_z
            if (dx * dx + dz * dz) > (DEBRIS_CULL_DIST * DEBRIS_CULL_DIST):
                d.active = False

        # Remove inactive debris
        self.debris_pieces = [d for d in self.debris_pieces if d.active]

        # Enforce hard cap
        if len(self.debris_pieces) > MAX_DEBRIS:
            self.debris_pieces = self.debris_pieces[-MAX_DEBRIS:]

    # === COLLISION QUERIES ===

    def check_collision(self, x, z):
        """Check if a position collides with walls."""
        if not math.isfinite(x) or not math.isfinite(z):
            return True

        player_radius = 15.0
        half_thick = WALL_THICKNESS / 2
        check_range = PILLAR_SPACING * 2
        
        min_grid_x = int((x - check_range) // PILLAR_SPACING) * PILLAR_SPACING
        max_grid_x = int((x + check_range) // PILLAR_SPACING) * PILLAR_SPACING
        min_grid_z = int((z - check_range) // PILLAR_SPACING) * PILLAR_SPACING
        max_grid_z = int((z + check_range) // PILLAR_SPACING) * PILLAR_SPACING

        for px_grid in range(min_grid_x, max_grid_x + PILLAR_SPACING, PILLAR_SPACING):
            for pz_grid in range(min_grid_z, max_grid_z + PILLAR_SPACING, PILLAR_SPACING):

                # Check horizontal wall
                if self.has_wall_between(px_grid, pz_grid, px_grid + PILLAR_SPACING, pz_grid):
                    wall_key = tuple(sorted([(px_grid, pz_grid), (px_grid + PILLAR_SPACING, pz_grid)]))
                    if wall_key in self.destroyed_walls:
                        continue

                    opening_type = self.get_doorway_type(px_grid, pz_grid, px_grid + PILLAR_SPACING, pz_grid)
                    wall_z = pz_grid
                    wall_x_start = px_grid
                    wall_x_end = px_grid + PILLAR_SPACING

                    if opening_type == "hallway":
                        opening_width = HALLWAY_WIDTH
                    elif opening_type == "doorway":
                        opening_width = 60
                    else:
                        opening_width = 0

                    if opening_width > 0:
                        opening_start = wall_x_start + (PILLAR_SPACING - opening_width) / 2
                        opening_end = opening_start + opening_width

                        if abs(z - wall_z) < (half_thick + player_radius):
                            if (wall_x_start <= x <= opening_start - player_radius) or \
                                    (opening_end + player_radius <= x <= wall_x_end):
                                return True
                    else:
                        if (wall_x_start - player_radius <= x <= wall_x_end + player_radius and
                                abs(z - wall_z) < (half_thick + player_radius)):
                            return True

                # Check vertical wall
                if self.has_wall_between(px_grid, pz_grid, px_grid, pz_grid + PILLAR_SPACING):
                    wall_key = tuple(sorted([(px_grid, pz_grid), (px_grid, pz_grid + PILLAR_SPACING)]))
                    if wall_key in self.destroyed_walls:
                        continue

                    opening_type = self.get_doorway_type(px_grid, pz_grid, px_grid, pz_grid + PILLAR_SPACING)
                    wall_x = px_grid
                    wall_z_start = pz_grid
                    wall_z_end = pz_grid + PILLAR_SPACING

                    if opening_type == "hallway":
                        opening_width = HALLWAY_WIDTH
                    elif opening_type == "doorway":
                        opening_width = 60
                    else:
                        opening_width = 0

                    if opening_width > 0:
                        opening_start = wall_z_start + (PILLAR_SPACING - opening_width) / 2
                        opening_end = opening_start + opening_width

                        if abs(x - wall_x) < (half_thick + player_radius):
                            if (wall_z_start <= z <= opening_start - player_radius) or \
                                    (opening_end + player_radius <= z <= wall_z_end):
                                return True
                    else:
                        if (wall_z_start - player_radius <= z <= wall_z_end + player_radius and
                                abs(x - wall_x) < (half_thick + player_radius)):
                            return True

                # Check pillar collision
                offset = PILLAR_SPACING // 2
                pillar_x = px_grid + offset
                pillar_z = pz_grid + offset
                pillar_key = (pillar_x, pillar_z)
                
                if self.has_pillar_at(pillar_x, pillar_z) and pillar_key not in self.destroyed_pillars:
                    pillar_min_x = pillar_x
                    pillar_max_x = pillar_x + PILLAR_SIZE
                    pillar_min_z = pillar_z
                    pillar_max_z = pillar_z + PILLAR_SIZE

                    closest_x = max(pillar_min_x, min(x, pillar_max_x))
                    closest_z = max(pillar_min_z, min(z, pillar_max_z))

                    dist_x = x - closest_x
                    dist_z = z - closest_z
                    dist_sq = dist_x * dist_x + dist_z * dist_z

                    if dist_sq < player_radius * player_radius:
                        return True

        return False

    # === SAVE/LOAD ===

    def get_state_for_save(self):
        """
        Get complete world state for saving.
        
        IMPORTANT: Includes wall_cache and pillar_cache to preserve
        the exact map layout that was explored.
        """
        return {
            'seed': self.world_seed,
            
            # === MAP LAYOUT (NEW!) ===
            'wall_cache': {str(k): v for k, v in self.wall_cache.items()},
            'pillar_cache': {str(k): v for k, v in self.pillar_cache.items()},
            
            # === DESTRUCTION STATE ===
            'destroyed_walls': [list(wall) for wall in self.destroyed_walls],
            'destroyed_pillars': [list(pillar) for pillar in self.destroyed_pillars],
            'destroyed_lamps': [list(lamp) for lamp in self.destroyed_lamps],
            'triggered_traps': [list(trap) for trap in self.triggered_traps],
            
            # === WALL DAMAGE ===
            'wall_states': {str(k): v.name for k, v in self.wall_states.items()},
            'wall_health': {str(k): v for k, v in self.wall_health.items()},
            'wall_cracks': {str(k): v for k, v in self.wall_cracks.items()},
            'pre_damaged_walls': {str(k): v for k, v in self.pre_damaged_walls.items()},
            
            # === DEBRIS (limited to prevent huge files) ===
            'debris_pieces': [
                {
                    'cx': d.cx, 'cy': d.cy, 'cz': d.cz,
                    'color': d.color,
                    'vx': d.vx, 'vy': d.vy, 'vz': d.vz,
                    'is_settled': d.is_settled
                }
                for d in self.debris_pieces if d.active
            ][:1000]  # Limit to 1000 most recent pieces
        }

    def load_state(self, data):
        """
        Load complete world state from save data.
        
        IMPORTANT: Restores wall_cache and pillar_cache to restore
        the exact map layout.
        """
        self.world_seed = data.get('seed', self.world_seed)

        # === LOAD MAP LAYOUT (NEW!) ===
        wall_cache_data = data.get('wall_cache', {})
        self.wall_cache = {}
        for k_str, v in wall_cache_data.items():
            key = eval(k_str)  # Convert string back to tuple
            self.wall_cache[key] = v
        
        pillar_cache_data = data.get('pillar_cache', {})
        self.pillar_cache = {}
        for k_str, v in pillar_cache_data.items():
            key = eval(k_str)  # Convert string back to tuple
            self.pillar_cache[key] = v
        
        # === LOAD DESTRUCTION STATE ===
        destroyed_walls_list = data.get('destroyed_walls', [])
        self.destroyed_walls = {tuple(tuple(point) for point in wall) for wall in destroyed_walls_list}
        
        destroyed_pillars_list = data.get('destroyed_pillars', [])
        self.destroyed_pillars = {tuple(pillar) for pillar in destroyed_pillars_list}
        
        destroyed_lamps_list = data.get('destroyed_lamps', [])
        self.destroyed_lamps = {tuple(lamp) for lamp in destroyed_lamps_list}
        
        triggered_traps_list = data.get('triggered_traps', [])
        self.triggered_traps = {tuple(trap) for trap in triggered_traps_list}
        
        # === LOAD WALL DAMAGE ===
        wall_states_data = data.get('wall_states', {})
        self.wall_states = {}
        for k_str, v_name in wall_states_data.items():
            key = eval(k_str)
            self.wall_states[key] = WallState[v_name]
        
        wall_health_data = data.get('wall_health', {})
        self.wall_health = {eval(k): v for k, v in wall_health_data.items()}
        
        wall_cracks_data = data.get('wall_cracks', {})
        self.wall_cracks = {eval(k): v for k, v in wall_cracks_data.items()}
        
        pre_damaged_data = data.get('pre_damaged_walls', {})
        self.pre_damaged_walls = {eval(k): v for k, v in pre_damaged_data.items()}
        
        # === LOAD DEBRIS ===
        debris_data = data.get('debris_pieces', [])
        self.debris_pieces = []
        for d_dict in debris_data:
            velocity = (d_dict['vx'], d_dict['vy'], d_dict['vz']) if not d_dict.get('is_settled', False) else None
            debris = Debris(
                (d_dict['cx'], d_dict['cy'], d_dict['cz']),
                tuple(d_dict['color']),
                velocity=velocity
            )
            self.debris_pieces.append(debris)
        
        # Clear only the zone cache (zones are always regenerated)
        self.zone_cache.clear()

        print(f"Loaded world with seed: {self.world_seed}")
        print(f"Loaded {len(self.wall_cache)} cached walls")
        print(f"Loaded {len(self.pillar_cache)} cached pillars")
        print(f"Loaded {len(self.destroyed_walls)} destroyed walls")
        print(f"Loaded {len(self.destroyed_pillars)} destroyed pillars")
        print(f"Loaded {len(self.debris_pieces)} debris pieces")
