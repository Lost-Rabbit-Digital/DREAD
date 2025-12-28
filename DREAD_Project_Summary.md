# D.R.E.A.D.
## Dynamic Randomized Enemy Area Distribution
### A Spawning Overhaul Mod for Zero Sievert

---

## Overview

DREAD is a comprehensive spawning overhaul mod for Zero Sievert, inspired by SPT-AKI's approach to improving spawn systems in Escape from Tarkov. The mod aims to increase unpredictability, populate empty spaces, and add a Chaos Mode that breaks zone boundaries for enemy spawns.

**Current Status:** Design & Planning Phase

---

## Core Features (Planned)

### 1. Enhanced Spawn Distribution
- Add spawn points to traditionally empty areas (cabins, clearings, forest edges)
- Variable squad sizes and compositions
- Loadout variation based on spawn location
- Improved mutant spawn variety and positioning

### 2. Chaos Mode
An optional mode where enemies from any zone can appear in any zone, with weighted rarities:

| Rarity Tier | Weight | Description |
|-------------|--------|-------------|
| Native | ~60% | Enemies that normally spawn in this zone |
| Uncommon | ~25% | Enemies from adjacent/similar zones |
| Rare | ~12% | Enemies from distant zones |
| Anomalous | ~3% | Late-game enemies appearing early |

### 3. Configuration System
- JSON-based configuration for user customization
- Per-zone enable/disable toggles
- Spawn density adjustments
- Chaos Mode rarity weight tuning
- Preset difficulty profiles

---

## Proof of Concept: Forest Zone

The Forest zone was selected as the initial implementation target due to:
- Being the first zone players encounter
- Having clearly defined "dead zones" with no current spawns
- Relatively simple enemy roster for testing
- Contains zone-specific enemies (Lazar Guard, Lazar boss) for baseline testing

### Current Forest Spawns (Vanilla)
Based on map analysis, existing spawn points cluster around:
- Central village/compound area
- Southern road near extraction

### Identified Empty Areas for New Spawns
- Northwest forest quadrant
- Eastern lakeside area
- Scattered cabin locations throughout
- Northern forest edge
- Road intersections

### Forest Enemy Roster

**Human Enemies:**
| Enemy | Notes |
|-------|-------|
| Novice Bandit | Common, low threat |
| Regular Bandit | Standard enemy |
| Expert Bandit | Higher threat |
| Lazar Guard | Forest-exclusive |
| Hunter | Hostile loner, appears everywhere |

**Boss:**
| Enemy | Notes |
|-------|-------|
| Lazar | Forest zone boss |

**Fauna:**
| Entity | Notes |
|--------|-------|
| Boar | Everywhere except Bunker |
| Rabbit | Everywhere except Bunker |
| Wolf | Everywhere except Bunker |

**Mutants (Vanilla Forest):**
| Enemy | Notes |
|-------|-------|
| Ghoul | Standard mutant, everywhere |
| Crystallized Ghoul | Buffs nearby ghouls, drops Violet Crystal |

### Chaos Mode Additions (Forest)
When Chaos Mode is enabled, the following could spawn in Forest with appropriate rarity weights:

**Uncommon Tier:**
- Blink (from Industrial/Swamp/Mall)
- Rat (from Industrial/Sewer)

**Rare Tier:**
- Infestation (from Makeshift Camp/Swamp/Industrial/Mall)
- Spider (from Industrial Laboratory/Swamp)

**Anomalous Tier:**
- Big (from Industrial/Swamp/Mall)
- Rotfang (from Swamp Sewer)
- Electrical Anomaly (from Radio Tower/Swamp/Mall)

**Boss Invasion Events (Very Rare):**
- Potential for non-native bosses to appear as special events

---

## All Zones - Enemy Reference

### Bosses by Zone
| Boss | Zone |
|------|------|
| Lazar | Forest |
| Arman | Makeshift Camp |
| Orel | Makeshift Camp |
| Rotking | Swamp |
| Kibba | Mall (interior) |
| Devil | Mall (basement) |
| Valentin | Zakov |
| Commander Voss | Industrial Area |

### Mutants by Zone
| Mutant | Native Zones |
|--------|--------------|
| Ghoul | Everywhere |
| Crystallized Ghoul | Everywhere |
| Blink | Industrial, Swamp, Mall |
| Infestation | Makeshift Camp, Swamp, Industrial, Mall |
| Spider | Industrial (Laboratory), Swamp (church, Sewer) |
| Big | Industrial (Laboratory), Swamp, Mall |
| Rotfang | Swamp (Sewer) |
| Electrical Anomaly | Radio Tower, Swamp, Mall |

---

## Technical Requirements

### Modding API Documentation Needed
The Zero Sievert modding documentation folder contains:

```
Modding Documentation/
├── Constants and Macros/
├── Event Hooks/          # Priority: spawn trigger events
├── Functions/            # Priority: spawn manipulation functions
├── Images For Reference/
├── lib/
├── Objects/              # Priority: enemy/spawn definitions
├── Overview/
├── Programming Language (Catspeak)/
├── exposed_values.txt    # 64KB - likely contains moddable values
└── Start.html            # 344KB - main documentation
```

### Key Questions for API Review
1. How are spawn points defined? (coordinates, regions, markers?)
2. What events fire on raid start / during raid?
3. Can we add spawn points dynamically or only modify existing?
4. How are enemy types referenced? (string IDs, enums, object references?)
5. Can spawn weights/probabilities be modified?
6. Is mid-raid spawning supported?
7. What's the Catspeak syntax for conditionals and loops?

---

## Next Steps

### Immediate (Pre-Development)
- [ ] Create GitHub repository for DREAD
- [ ] Upload and review modding API documentation
- [ ] Document Catspeak language basics
- [ ] Identify relevant Event Hooks for spawning
- [ ] Map exposed_values.txt for spawn-related variables
- [ ] Determine technical feasibility of all planned features

### Phase 1: Forest Proof of Concept
- [ ] Define new spawn point coordinates for Forest
- [ ] Implement basic spawn distribution changes
- [ ] Test variable squad sizes
- [ ] Add spawns to empty cabin areas
- [ ] Validate with playtesting

### Phase 2: Chaos Mode Implementation
- [ ] Build rarity weight system
- [ ] Implement cross-zone enemy spawning
- [ ] Create configuration file structure
- [ ] Add toggle for Chaos Mode
- [ ] Balance testing

### Phase 3: Configuration & Polish
- [ ] Full JSON configuration system
- [ ] Difficulty presets
- [ ] Documentation for end users
- [ ] Steam Workshop preparation

### Phase 4: Expansion (Post-POC)
- [ ] Extend to Makeshift Camp
- [ ] Extend to remaining zones
- [ ] Special events (invasions, hordes)
- [ ] Community feedback integration

---

## Community Page Draft

### Title
**D.R.E.A.D. - Dynamic Randomized Enemy Area Distribution**

### Tagline
*"Every raid is different. Every corner is a threat."*

### Description

DREAD completely overhauls Zero Sievert's spawning system, bringing unpredictability and tension to every raid.

**Features:**

**Dynamic Spawns** — Enemies now appear in locations that were previously safe. Those empty cabins? Check your corners. That quiet forest path? Not anymore.

**Chaos Mode** — Enable this optional mode and zone boundaries no longer matter. A Spider might be waiting in the Forest. Rotfang could be lurking outside Makeshift Camp. Rarity weights keep things challenging but fair—you won't see endgame horrors on every run, but you'll never be *sure* you won't.

**Fully Configurable** — Tune spawn density, adjust Chaos Mode rarity weights, or disable features entirely. Your apocalypse, your rules.

**Current Version:** Forest Zone (Proof of Concept)
**Planned:** All zones, invasion events, boss encounters, horde mode

### Tags
`gameplay` `difficulty` `spawns` `enemies` `replayability` `configurable` `challenge`

---

## Repository Structure (Proposed)

```
DREAD/
├── README.md
├── LICENSE
├── docs/
│   ├── DESIGN.md
│   ├── API_NOTES.md
│   └── CHANGELOG.md
├── src/
│   ├── main.catspeak (or appropriate extension)
│   ├── config/
│   │   └── default_config.json
│   ├── spawns/
│   │   ├── forest.catspeak
│   │   └── (future zones)
│   └── chaos/
│       └── rarity_tables.catspeak
├── reference/
│   └── (modding API docs for team reference)
└── tools/
    └── (any helper scripts)
```

---

## Contact & Contribution

*To be added once repository is created*

---

*Document Version: 0.1*
*Last Updated: December 2024*
*Status: Pre-Development*
