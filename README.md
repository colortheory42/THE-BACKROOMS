# THE BACKROOMS

A continuous, walking-only procedural 3D environment built entirely in Python with Pygame.

Inspired by the Backrooms, this project prioritizes spatial consistency, physical presence, and persistence over scripted events or objectives.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/pygame-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## What This Is

**There are no monsters, objectives, or win conditions.**

The experience is defined entirely by movement, collision, and your interaction with the space. You walk. The space resists. Nothing explains itself. Nothing stops you.

This is not a game engine showcase—though it happens to demonstrate custom 3D rendering, physics, and procedural generation. It's a place you can enter.

## 🎮 Core Features

### Spatial Presence
- **Unbounded Procedural Space**: The environment has no predefined size or map. Space is revealed only through movement, and traversal is limited strictly to walking.
- **Seed-Based Consistency**: The same seed generates the same space, always. Return to where you've been.
- **Physical Collision**: Walls stop you. Movement has weight. The space resists in consistent ways.
- **Progressive Destruction**: Walls don't just disappear—they crack, lean, and fall. Debris accumulates where it lands.

### Technical Implementation
- **Custom 3D Engine**: Built from mathematical first principles using only Pygame and NumPy
- **Precision Collision**: Circle-vs-segment collision with sliding response for smooth movement
- **Debris Physics**: Realistic gravity, collision detection, and settling behaviors
- **Persistent State**: Save and return. Destroyed walls stay destroyed.
- **Spatial Audio**: Directional sound with stereo panning based on orientation

### Atmospheric Details
- **Procedural Zones**: Different areas have different characteristics (density, openness, ceiling height)
- **Found-Footage Aesthetic**: Subtle VHS-style visual treatment
- **Procedural Sound**: All audio generated at runtime—footsteps, ambient hum, destruction
- **Voice Echo System**: Optional microphone loopback for atmospheric presence

## 📋 Requirements

### Core Dependencies
```bash
pip install pygame numpy
```

### Optional (for voice echo)
```bash
pip install sounddevice  # Recommended
# OR
pip install pyaudio      # Alternative
```

## 🚀 Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/the-backrooms.git
cd the-backrooms
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run**
```bash
python main.py
```

Press ENTER to enter. Press ESC to pause or leave.

## 🎮 Controls

### Movement
- **WASD** or **Arrow Keys**: Move
- **SHIFT**: Run
- **C**: Toggle crouch
- **SPACE**: Jump
- **M**: Toggle mouse look
- **J/L**: Turn left/right (when mouse look is off)

### Interaction
- **LEFT CLICK** or **E**: Damage/destroy wall (aim at center)
- Walls crack before breaking. Debris falls and settles.

### System
- **H**: Toggle help overlay
- **R**: Toggle performance mode (render scale)
- **ESC**: Pause
- **N**: Toggle voice loopback (requires microphone)

### Persistence
- **F5**: Quick save to slot 1
- **F9**: Quick load from slot 1

## 🏗️ Architecture

The codebase follows clean modular separation:

```
main.py              # Game loop and state management
engine.py            # Main orchestrator
├── world.py         # Procedural generation and geometry
├── player.py        # Player state and input
├── camera.py        # Camera transforms and projection
├── renderer.py      # 3D rendering pipeline
├── collision.py     # Precise collision detection
├── debris.py        # Physics simulation for destruction
└── audio.py         # Procedural sound generation
```

### Key Systems

**World System** (`world.py`)
- Seed-based procedural generation
- Wall and pillar management
- Destruction tracking
- Debris spawning

**Collision System** (`collision.py`)
- Circle collider vs line segments
- Multi-pass resolution for corners
- Sliding collision response
- Depenetration for stuck states

**Renderer** (`renderer.py`)
- Custom 3D projection
- Near-plane clipping
- Painter's algorithm depth sorting
- Dynamic lighting and fog

**Debris System** (`debris.py`)
- Pixel-sized debris particles
- Realistic physics with gravity
- Settling detection
- Rubble chunk formation

## ⚙️ Configuration

Edit `config.py` to customize the space:

```python
# Display
WIDTH = 960
HEIGHT = 540
FULLSCREEN = True
FPS = 60

# Pillar density modes
PILLAR_MODE = "normal"  # Options: none, sparse, normal, dense, all

# Movement speeds
WALK_SPEED = 75
RUN_SPEED = 100
CROUCH_SPEED = 10

# World generation
PILLAR_SPACING = 400
HALLWAY_WIDTH = 100
WALL_THICKNESS = 20
```

## 🎨 Customization

### Pillar Density
Change the `PILLAR_MODE` in `config.py`:
- `"none"`: Wide open spaces
- `"sparse"`: Occasional pillars (10%)
- `"normal"`: Balanced (30%)
- `"dense"`: Maze-like (60%)
- `"all"`: Grid of pillars (100%)

### Colors
Modify the color scheme in `config.py`:
```python
WALL_COLOR = (240, 220, 80)     # Yellow walls
FLOOR_COLOR = (30, 60, 120)     # Blue floor
CEILING_COLOR = (200, 200, 240) # Light ceiling
```

## 🔊 Audio Features

### Built-in Sounds
All sounds are procedurally generated at runtime:
- Ambient hum (low-frequency drone)
- Footsteps (player and ambient)
- Electrical buzz
- Wall destruction effects
- Crack and fracture sounds

### Voice Echo System
Optional microphone loopback with spatial audio:
```bash
pip install sounddevice
```
Press **N** in-game to toggle voice loopback.

## 💾 Save System

Saves are stored in JSON format in the `backrooms_saves/` directory:
- **F5**: Quick save to slot 1
- **F9**: Quick load from slot 1
- Saves include: player position, world seed, destroyed walls, play time

## 🎯 Design Philosophy

This project is built on several core principles:

1. **Build from First Principles**: Everything is constructed from mathematical foundations rather than using high-level frameworks

2. **Emergent Behavior**: Simple rules create complex, realistic behavior (debris physics, procedural generation)

3. **Spatial Honesty**: The space doesn't lie. Collision is consistent. Physics is predictable. Seeds are deterministic.

4. **Durable Architecture**: Clean separation of concerns makes the codebase maintainable and extensible

**The absence is intentional.** No monsters, no objectives, no narrative. The experience is walking, collision, space, and the player's own relationship to those elements.

## 🐛 Troubleshooting

### Audio Issues
If you encounter audio problems:
```bash
# Try sounddevice first
pip install sounddevice

# If that doesn't work, try pyaudio
pip install pyaudio

# Fallback: Test tone generator
# (automatically used if no microphone library found)
```

### Performance Issues
- Press **R** to toggle render scale (performance mode)
- Reduce `WIDTH` and `HEIGHT` in `config.py`
- Set `PILLAR_MODE = "sparse"` for open areas
- Disable fog: `FOG_ENABLED = False`

### Collision Problems
- Ensure `WALL_THICKNESS` is reasonable (10-30)
- Check `player_radius` in collision system (default: 15.0)
- Verify `PILLAR_SIZE` doesn't exceed `PILLAR_SPACING`

## 🚧 Possible Future Experiments

These features may or may not be added. Some could compromise the core experience:

- Raycast-based acoustic simulation
- Dynamic lighting with shadows
- Multiple floor levels
- Procedural textures
- Network multiplayer

**Note**: Entities, NPCs, and traditional game objectives are intentionally absent and unlikely to be added.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Technical Foundation

Built with:
- Python 3.8+
- Pygame for rendering
- NumPy for mathematics
- Custom 3D projection from first principles
- Inspired by the Backrooms creepypasta

## 📧 Contact

For questions, suggestions, or bug reports, please open an issue on GitHub.

---

**Built from mathematical precision. Experienced through walking.**

*In the Backrooms, every wall is temporary. Every step is yours.*
