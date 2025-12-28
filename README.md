# D.R.E.A.D.
## Dynamic Randomized Enemy Area Distribution
### A Spawn Overhaul Mod for Zero Sievert

> *"Every raid is different. Every corner is a threat."*

---

## Overview

DREAD is a comprehensive spawn overhaul mod for Zero Sievert that enhances the game's enemy spawning with new spawn points, SAIN-inspired enemy archetypes, squad mechanics, and invasion waves.

**Version:** 0.2.0
**Author:** Lost Rabbit Digital
**License:** MIT

---

## Features

### 1. Enhanced Spawn Distribution
- Adds spawn points to traditionally empty areas (cabins, clearings, forest edges)
- Variable squad sizes and compositions
- Position-based spawn validation to ensure walkable terrain
- Per-zone spawn density configuration

### 2. SAIN-Inspired Enemy Archetypes
Enemies spawn with varied equipment and stats based on archetype:

| Archetype | Spawn Weight | HP | Accuracy | Gear Tier |
|-----------|--------------|-----|----------|-----------|
| GigaChad | 5% | 150% | +30% | Master |
| Chad | 15% | 120% | +15% | Expert |
| Normal | 40% | 100% | Base | Intermediate |
| Rat | 25% | 80% | -10% | Skilled |
| Timmy | 15% | 60% | -20% | Rookie |

### 3. Squad Spawning
- Groups of 2-5 enemies spawn together as cohesive squads
- 30% chance for squad to have a Chad/GigaChad leader
- Configurable squad size and leader probability

### 4. Invasion Waves
Timed enemy waves spawn near the player during raids:
- First wave: 2 minutes after raid start
- Subsequent waves: Every 3 minutes
- Maximum 3 waves per raid
- Zone-appropriate enemy selection

### 5. Chaos Mode
Cross-zone enemy variety with weighted rarity tiers:

| Rarity | Chance | Description |
|--------|--------|-------------|
| Native | 60% | Normal zone enemies |
| Uncommon | 25% | Adjacent zone enemies |
| Rare | 12% | Distant zone enemies |
| Anomalous | 3% | Late-game threats appearing early |

---

## Installation

1. Download `DREAD.catspeak` and `dread_config.json`
2. Place both files in your Zero Sievert mods folder
3. Enable the mod in the game's mod menu
4. (Optional) Edit `dread_config.json` to customize settings

---

## Configuration

DREAD uses a JSON configuration file for customization:

```json
{
    "general": {
        "enabled": true,
        "debug_mode": true,
        "spawn_multiplier": 1.0
    },
    "zones": {
        "forest": { "enabled": true, "spawn_density": "normal" }
    },
    "chaos_mode": {
        "enabled": false
    },
    "squad_spawning": {
        "enabled": true,
        "min_squad_size": 2,
        "max_squad_size": 5,
        "leader_chance": 0.3
    },
    "invasion_events": {
        "enabled": true,
        "first_wave_delay_seconds": 120,
        "wave_interval_seconds": 180,
        "max_waves": 3
    }
}
```

### Spawn Density Options
- `sparse` - 50% spawn chance
- `normal` - 100% spawn chance (default)
- `dense` - 150% spawn chance
- `extreme` - 200% spawn chance

### Difficulty Presets
- **Tourist** - 30% spawns, easy archetypes
- **Normal** - Standard experience
- **Hardcore** - 150% spawns, tougher enemies
- **Nightmare** - 200% spawns, Chaos Mode enabled, elite enemies only

---

## Zone Support

| Zone | Status | Spawn Points |
|------|--------|--------------|
| Forest | Full | 18 points + boss |
| Makeshift Camp | Template | 4 points |
| Industrial Area | Template | 4 points |
| Swamp | Template | 4 points |
| Mall | Template | 4 points |
| Zakov | Template | 3 points |
| City | Template | 2 points |
| CNPP | Template | 2 points |

*Forest has detailed spawn configurations. Other zones use template spawns pending in-game coordinate mapping.*

---

## Project Structure

```
DREAD/
├── DREAD.catspeak           # Bundled mod for distribution
├── dread_config.json        # User configuration
├── src/
│   ├── main.catspeak        # Entry point (development)
│   ├── config/
│   │   └── default_config.json
│   ├── utils/
│   │   ├── core.catspeak    # Utility functions
│   │   ├── config.catspeak  # Config system
│   │   └── archetypes.catspeak
│   ├── systems/
│   │   ├── spawning.catspeak
│   │   └── invasion.catspeak
│   └── spawns/
│       ├── forest.catspeak
│       └── zones.catspeak
└── docs/
    ├── API_NOTES.md         # Technical reference
    └── SAIN_FEASIBILITY_ANALYSIS.md
```

---

## Technical Notes

### API Limitations
DREAD works within Zero Sievert's content-focused modding API. Features like AI behavior modification are not possible - see `docs/SAIN_FEASIBILITY_ANALYSIS.md` for details on what the API does and doesn't support.

### Event Hooks Used
- `enter_raid` - Triggers initial spawn execution
- `step_normal_event` - Updates invasion wave timer
- `enter_hub` - Cleans up invasion state

### Key Functions
- `DREAD_SpawnHuman(faction, x, y, archetype)` - Spawn human with archetype
- `DREAD_SpawnSquad(faction, x, y, size, with_leader)` - Spawn enemy squad
- `DREAD_SpawnMutant(type, x, y)` - Spawn mutant enemy
- `DREAD_ProcessSpawnPoint(point)` - Process spawn point definition

---

## Changelog

### v0.2.0
- Added SAIN-inspired archetype system
- Added squad spawning with leaders
- Added invasion wave system
- Added Chaos Mode with rarity tiers
- Full JSON configuration support
- Complete Forest zone spawn configuration
- Template spawns for all other zones

### v0.1.0
- Initial proof of concept
- Basic Forest spawn additions

---

## Roadmap

- [ ] Map actual coordinates for all zones via in-game testing
- [ ] Add more spawn variety per zone
- [ ] Special boss encounter events
- [ ] Steam Workshop release
- [ ] Community feedback integration

---

## Credits

- **Lost Rabbit Digital** - Development
- **SAIN Mod (SPT-AKI)** - Inspiration for archetype system
- **Zero Sievert Dev Team** - Modding API documentation

---

## License

MIT License - See LICENSE file for details.

---

*Document Version: 0.2.0*
*Last Updated: December 2024*
