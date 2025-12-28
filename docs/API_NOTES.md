# DREAD API Notes
## Zero Sievert Modding Technical Reference

This document contains consolidated findings from analyzing the Zero Sievert modding API documentation for implementing the DREAD spawn overhaul mod.

---

## 1. Catspeak Language Basics

Catspeak is Zero Sievert's custom scripting language (based on [Catspeak](https://www.katsaii.com/catspeak-lang/)).

### Syntax Overview

```catspeak
-- This is a comment

-- Variables
let myVar = 10;
let myString = "hello";

-- Functions
let myFunc = func(arg1, arg2) {
    return arg1 + arg2;
};

-- Anonymous functions (common pattern)
EventAssignFunction("enter_raid", func() {
    -- Code runs when raid starts
});

-- Arrays
let arr = [1, 2, 3];
arr[0] = 5;

-- Structs
let data = { x: 100, y: 200, name: "spawn_point" };
data.x = 150;

-- With blocks (modify struct in scope)
with (data) {
    x += 50;
    y += 50;
}

-- While loops
let i = 0;
while (i < 10) {
    i += 1;
}

-- Conditionals
if (condition) {
    -- do something
} else {
    -- do something else
}

-- Match/Switch
match value {
    case "option1" { /* code */ }
    case "option2" { /* code */ }
    else { /* default */ }
}
```

### Key Differences from Standard Languages
- Use `func` not `fun` or `function`
- Comments use `--` (double dash)
- Semicolons optional but recommended
- Game objects accessed via exposed functions

---

## 2. Event Hooks

### Game Events
Use with `EventAssignFunction(event_id, function)`:

| Event ID | When Called | DREAD Use |
|----------|-------------|-----------|
| `"enter_raid"` | After loading screen, raid starts | **PRIMARY** - Spawn enemies here |
| `"exit_train"` | Player exits train in raid | Secondary spawn trigger |
| `"player_spawn"` | Player spawns into any room | Alternative trigger |
| `"enter_hub"` | Hub entered (load/return from raid) | Not needed |
| `"player_death"` | Player dies during raid | Not needed |
| `"trade_completed"` | Trade finished | Not needed |

**Example - Primary DREAD Hook:**
```catspeak
EventAssignFunction("enter_raid", func() {
    -- DREAD spawn logic goes here
    -- This runs once when the raid begins
});
```

### Object Events
Use with `ObjectSetScript(object, event, function)`:

| Event ID | When Called | Use Case |
|----------|-------------|----------|
| `"create_event"` | Object spawned | Initialize spawn timers |
| `"step_normal_event"` | Every frame | Mid-raid spawning |
| `"step_begin_event"` | Every frame (before normal) | - |
| `"step_end_event"` | Every frame (after normal) | - |
| `"destroy_event"` | Instance destroyed | Cleanup |

**Example - Continuous Spawning:**
```catspeak
ObjectSetScript("obj_player", "create_event", func(_inst) {
    _inst.spawn_timer = 0;
    _inst.spawn_rate = 60 * 5; -- Every 5 seconds (60 fps)
});

ObjectSetScript("obj_player", "step_normal_event", func(_inst) {
    if (RoomGetCurrent() != "r_hub") {
        _inst.spawn_timer += 1;
        if (_inst.spawn_timer >= _inst.spawn_rate) {
            -- Spawn enemy logic here
            _inst.spawn_timer = 0;
        }
    }
});
```

---

## 3. NPC/Enemy Spawning Functions

### Method 1: NpcCreate + NpcSpawn (Custom NPCs)
Create a custom NPC definition, configure it, then spawn:

```catspeak
-- Create NPC definition
NpcCreate("dread_bandit");

-- Configure using a preset
NpcSetPreset("dread_bandit", "bandit_expert");

-- Optionally override specific attributes
NpcSetFaction("dread_bandit", "bandits");
NpcSetWeapon("dread_bandit", "weapon_ak74");
NpcSetArmor("dread_bandit", "armor_heavy");
NpcSetHp("dread_bandit", 150);

-- Spawn at specific coordinates
NpcSpawn("dread_bandit", 400, 400);
```

### Method 2: NpcObjectSpawnNearPlayer (Quick Spawn)
Spawn pre-existing enemy objects near the player:

```catspeak
-- Spawn 3 bandits that move toward player
NpcObjectSpawnNearPlayer(obj_bandit_preset_rookie, 3, true);

-- Spawn 2 ghouls that don't move toward player
NpcObjectSpawnNearPlayer(obj_enemy_ghoul, 2, false);
```

**Parameters:**
- `npc_object` - Pre-existing object from Pre-Existing Objects list
- `amount` - Number to spawn (default: 1)
- `move_towards_player` - Chase player after spawn (default: false)

### Method 3: InstanceCreate (Direct Object Creation)
Create any game object at specific coordinates:

```catspeak
-- Check if position is walkable first
if (CollisionWalkable(x, y)) {
    InstanceCreate(x, y, obj_enemy_boar);
}
```

### Utility Functions

| Function | Description |
|----------|-------------|
| `CollisionWalkable(x, y)` | Returns true if position is walkable |
| `RoomGetCurrent()` | Returns current room name (e.g., "r_hub") |
| `Irandom(max)` | Random integer 0 to max |
| `LengthDirX(len, dir)` | X component of vector |
| `LengthDirY(len, dir)` | Y component of vector |

---

## 4. Pre-Existing Enemy Objects

### Mutants/Creatures
| Object | Enemy Type |
|--------|------------|
| `obj_enemy_ghoul` | Ghoul |
| `obj_enemy_ghoul_2` | Crystallized Ghoul |
| `obj_enemy_blink` | Blink |
| `obj_enemy_big` | Big |
| `obj_enemy_spider` | Spider |
| `obj_enemy_spine` | Spine/Rotfang |
| `obj_enemy_infestation` | Infestation |
| `obj_enemy_zombie` | Zombie |
| `obj_enemy_rat` | Rat |
| `obj_enemy_anomaly_electric` | Electrical Anomaly |
| `obj_enemy_anomaly_fire` | Fire Anomaly |

### Fauna
| Object | Enemy Type |
|--------|------------|
| `obj_enemy_boar` | Boar |
| `obj_enemy_boar_zombie` | Zombie Boar |
| `obj_enemy_wolf_brown` | Wolf |
| `obj_enemy_rabbit` | Rabbit |
| `obj_enemy_crow` | Crow |

### Human Enemies (Preset-based)
| Object | Faction |
|--------|---------|
| `obj_bandit_preset_rookie` | Bandits |
| `obj_bandit_preset_skilled` | Bandits |
| `obj_bandit_preset_expert` | Bandits |
| `obj_bandit_preset_veteran` | Bandits |
| `obj_bandit_preset_master` | Bandits |
| `obj_green_army_preset_*` | Green Army |
| `obj_hunter_preset_*` | Hunters |
| `obj_watcher_preset_*` | Watchers |
| `obj_crimson_preset_*` | Crimson |

### Bosses
| Object | Boss |
|--------|------|
| `obj_enemy_human_bandit_boss` | Lazar (Forest) |
| `obj_enemy_human_bandit_boss_guard` | Lazar's Guard |
| `obj_enemy_human_bandit_boss_outpost` | Orel (Makeshift Camp) |
| `obj_boss_arman` | Arman (Makeshift Camp) |
| `obj_boss_city` | Valentine (Zakov) |
| `obj_watcher_devil` | Devil (Mall) |
| `obj_boss_killa` | Kibba (Mall) |

---

## 5. NPC Presets

For use with `NpcSetPreset()` when creating custom NPCs:

| Preset | Faction |
|--------|---------|
| `"bandit_rookie"` | Bandits |
| `"bandit_skilled"` | Bandits |
| `"bandit_intermediate"` | Bandits |
| `"bandit_expert"` | Bandits |
| `"bandit_veteran"` | Bandits |
| `"bandit_master"` | Bandits |
| `"green_army_*"` | Green Army (same tiers) |
| `"hunter_*"` | Hunters (same tiers) |
| `"watcher_*"` | Watchers (same tiers) |
| `"crimson_*"` | Crimson (same tiers) |

---

## 6. Map Constants

| Constant | Zone |
|----------|------|
| `MAP_forest` | Forest |
| `MAP_makeshift_camp` | Makeshift Camp |
| `MAP_industrial_area` | Industrial Area |
| `MAP_swamp` | Swamp |
| `MAP_mall` | Mall |
| `MAP_zaton` | Zakov (City) |
| `MAP_city` | City |
| `MAP_cnpp` | CNPP (Bunker) |

---

## 7. DREAD Implementation Strategy

### Phase 1: Basic Spawn on Raid Start
```catspeak
EventAssignFunction("enter_raid", func() {
    -- Check which map we're on
    let currentRoom = RoomGetCurrent();

    -- Only run on Forest for POC
    if (currentRoom == "r_forest") {
        -- Spawn enemies at predefined coordinates
        DREAD_SpawnForestEnemies();
    }
});

let DREAD_SpawnForestEnemies = func() {
    -- Northwest quadrant spawns (example coordinates)
    let spawn_points = [
        { x: 500, y: 500 },
        { x: 800, y: 300 },
        { x: 1200, y: 600 }
    ];

    let i = 0;
    while (i < ArrayLength(spawn_points)) {
        let point = spawn_points[i];
        if (CollisionWalkable(point.x, point.y)) {
            -- Spawn a bandit group
            NpcObjectSpawnNearPlayer(obj_bandit_preset_skilled, 2, false);
        }
        i += 1;
    }
};
```

### Phase 2: Chaos Mode (Cross-Zone Enemies)
```catspeak
let DREAD_GetChaosEnemy = func() {
    let roll = Irandom(100);

    if (roll < 60) {
        -- Native (60%): Normal forest enemies
        return obj_enemy_ghoul;
    } else if (roll < 85) {
        -- Uncommon (25%): Adjacent zone enemies
        return obj_enemy_blink;
    } else if (roll < 97) {
        -- Rare (12%): Distant zone enemies
        return obj_enemy_spider;
    } else {
        -- Anomalous (3%): Late-game enemies
        return obj_enemy_big;
    }
};
```

### Phase 3: Configuration System
Use `FileDataRead` and `FileDataWrite` for JSON config:

```catspeak
-- Read configuration
let config = FileDataRead("dread_config.json");
let chaos_enabled = config.chaos_mode;
let spawn_multiplier = config.spawn_density;
```

---

## 8. Key Technical Questions Answered

| Question | Answer |
|----------|--------|
| How are spawn points defined? | X,Y coordinates passed to NpcSpawn or InstanceCreate |
| What events fire on raid start? | `"enter_raid"` via EventAssignFunction |
| Can we add spawn points dynamically? | Yes, via NpcSpawn with any walkable coordinates |
| How are enemy types referenced? | Object names (obj_enemy_*) or NPC IDs (strings) |
| Can spawn weights be modified? | Yes, via Catspeak logic (Irandom for weights) |
| Is mid-raid spawning supported? | Yes, via ObjectSetScript step events |
| What's the Catspeak syntax for loops? | `while (cond) { }` - no for loops |

---

## 9. File References

| File | Purpose |
|------|---------|
| `docs/api/Event Hooks/Game Events.md` | Game event documentation |
| `docs/api/Functions/NPCs/*.md` | NPC spawn functions |
| `docs/api/Constants and Macros/Enemy Names.md` | Enemy string IDs |
| `docs/api/Constants and Macros/Pre-Existing Objects.md` | Spawnable objects |
| `docs/api/Constants and Macros/NPC Presets.md` | Human enemy presets |
| `docs/api/Constants and Macros/Map Names.md` | Zone constants |
| `docs/api/Programming Language (Catspeak)/*.md` | Language reference |
| `docs/api/exposed_values.txt` | All exposed API values |

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Status: Technical Feasibility Confirmed*
