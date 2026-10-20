# D.R.E.A.D.
## Dynamic Randomized Enemy Area Distribution
### A Spawn Overhaul Mod for Zero Sievert

> *"Every raid is different. Every corner is a threat."*

---

## Overview

DREAD is a comprehensive spawn overhaul mod for Zero Sievert that enhances the game's enemy spawning with new spawn points, SAIN-inspired enemy archetypes, squad mechanics, and invasion waves.

**Version:** 0.3.1
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

Each archetype picks a rung on the vanilla preset ladder (rookie > intermediate > skilled > expert > veteran > master) relative to the zone, then scales that preset's own HP and aim. In the Forest a GigaChad is an expert-tier bandit. Loot chest, armor, XP and faction come from the matching vanilla preset.

| Archetype | Weight (Normal) | Tier in Forest | HP vs preset | Aim radius vs preset |
|-----------|-----------------|----------------|--------------|----------------------|
| GigaChad | 4% | Expert | 130% | 85% |
| Chad | 14% | Skilled | 115% | 92% |
| Normal | 42% | Intermediate | 100% | 100% |
| Rat | 22% | Rookie | 90% | 110% |
| Timmy | 18% | Rookie | 80% | 120% |

### 3. Squad Spawning
- Groups of 2-4 enemies spawn together as cohesive squads
- 30% chance for squad to have a Chad/GigaChad leader
- Configurable squad size and leader probability

### 4. Invasion Waves
Timed enemy waves spawn at the edge of the player's view and move toward them:
- Normal: first wave at 5:00, then every 4:00, 2 waves of 1-3 enemies
- Hardcore: first wave at 2:00, then every 3:00, 3 waves of 2-5 enemies
- The wave clock pauses inside buildings and stops on death/extract

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

1. Subscribe on the Steam Workshop, or copy `workshop/DREAD/` into `ZERO Sievert/Mods/`
   (`init.script` there is a copy of `DREAD.catspeak`)
2. Enable DREAD in the game's mod menu
3. Start a Forest raid. DREAD runs silently unless `debug_mode` is on

---

## Configuration

Zero Sievert mods cannot read their own JSON files (`FileDataRead` reads save-data keys), so all
settings live in the `DREAD_CONFIG` block at the top of `init.script`:

```
DREAD_CONFIG = {
    difficulty: "normal",       -- tourist | normal | hardcore | nightmare
    debug_mode: false,          -- popup logs + F8 coordinate logger
    safe_start_radius: 400,     -- no fixed spawns this close to you at raid start
    squads: { enabled: true, min_size: 2, max_size: 4, leader_chance: 0.3 },
    zones: { forest: { enabled: true, density: "normal" }, ... }
};
```

Density: `sparse` x0.5, `normal` x1, `dense` x1.5, `extreme` x2 spawn chance.

### Difficulty Presets
Benchmarked headlessly with `tools/simulate_raids.py` (15-minute Forest raid, 60 raids; see `docs/PLAYTEST_REPORT.md`):

| Preset | Added hostiles | Invasion enemies | Threat (rookie-bandit eq.) | Raid cap |
|--------|----------------|------------------|----------------------------|----------|
| Tourist | ~9 | none | ~7 | 20 |
| **Normal** (default) | ~14 | ~4 from 5:00 | ~17 | 30 |
| Hardcore | ~22 | ~16 from 2:00 | ~47 | 50 |
| Nightmare | ~28 + Chaos | ~35 from 1:30 | ~100 | 70 |

### Mapping spawn coordinates
Set `debug_mode: true`, enter a raid and press **F8** to show the room and your x/y.

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

*All coordinates (Forest included) are estimates pending in-game mapping; non-Forest zones are disabled by default. Unwalkable points are skipped.*

---

## Project Structure

```
DREAD/
├── DREAD.catspeak           # Bundled mod for distribution
├── workshop/DREAD/          # Mods-folder package (init.script = DREAD.catspeak)
├── tools/                   # lint_catspeak.py, catspeak_harness.py, simulate_raids.py
├── src/
│   ├── main.catspeak        # Older modular draft (stale, not shipped)
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

### Catspeak gotcha: no closures
Catspeak 3.1.1 functions cannot see top-level `let` variables; inside a `func` they resolve as file
globals and read `undefined`. That crashed v0.2.x on load ("value is not a function, got 'undefined'").
Shared values are declared without `let` at the top level.

### Testing before you ship
```
python -I tools/lint_catspeak.py DREAD.catspeak
python -I tools/simulate_raids.py all
```

### Event Hooks Used
- `enter_raid` - initial spawns
- `obj_player` `step_end_event` - invasion timer (step_end avoids replacing other mods' step_normal scripts)
- `enter_hub` / `player_death` - stop invasions

### Key Functions
- `DREAD_SpawnHuman(faction, x, y, archetype)` - Spawn human with archetype
- `DREAD_SpawnSquad(faction, x, y, size, with_leader)` - Spawn enemy squad
- `DREAD_SpawnMutant(type, x, y)` - Spawn mutant enemy
- `DREAD_ProcessSpawnPoint(point)` - Process spawn point definition

---

## Changelog

### v0.3.1
- Fixed crash on load: "assigning the NPC ... to a non-existent faction, "Bandits"". Faction ids are
  now checked with `FactionExists` against several candidates; if none exist DREAD creates its own
  faction hostile to the player instead of aborting the mod load
- Crash guards: if a faction can't be created, its spawns use vanilla preset objects instead of DREAD
  NPCs; enemy objects missing from the game, empty spawn tables, spawn points without coordinates and a
  missing player instance are skipped instead of crashing; repeated errors pop up only once
- `enabled` kill switch in `DREAD_CONFIG`
- `debug_mode` is ON for playtesting: one popup on load (with the faction mapping) and one per raid
  start; per-spawn detail goes to `ShowDebugMessage` instead of popups. Turn it off for release
- Harness models the game's faction table (`FactionExists`/`FactionCreate`/`FactionSetRelationship`)
  instead of trusting the documented names

### v0.3.0
- Fixed crash on load (top-level `let` used from functions; Catspeak has no closures)
- Fixed crashes in every Forest raid (`result.members` on an array; `NpcSetRecoilAimRadius` missing max)
- Fixed chaos waves passing `undefined` to the spawner; spawn chances no longer compound each raid
- Fixed spawned humans inheriting the friendly Loners faction and fixed loot of `loner_novice`
- Fixed `r_industrial` room name; DREAD idles in prologue, interiors and unknown rooms
- Rebalanced around vanilla preset stats; gentler Normal preset; per-preset raid cap; safe-start radius
- Config moved into `init.script` (the JSON file was never read); F8 coordinate logger
- Added linter, headless Catspeak harness and raid simulator

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
