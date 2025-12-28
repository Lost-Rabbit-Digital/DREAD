# DREAD: Next Steps

## Current Status: Technical Feasibility Complete
All API analysis is done. The mod is architecturally sound and ready for implementation.

---

## Phase 1: Forest Proof of Concept

### 1.1 Map Coordinate Gathering
- [ ] Launch Zero Sievert with debug/coordinate display enabled
- [ ] Document player X,Y coordinates at key Forest locations:
  - Northwest quadrant (currently empty)
  - Lakeside areas
  - Cabin surroundings
  - Road intersections
  - Forest edge areas
- [ ] Screenshot reference images with coordinate overlays
- [ ] Update `src/spawns/forest.catspeak` with real coordinates

### 1.2 Basic Hook Testing
- [ ] Create minimal test mod with just:
  ```catspeak
  EventAssignFunction("enter_raid", func() {
      ShowMessage("DREAD: Raid started!");
  });
  ```
- [ ] Verify mod loads and message displays
- [ ] Test in Forest zone specifically

### 1.3 Spawn Mechanics Testing
- [ ] Test `NpcObjectSpawnNearPlayer()` with single enemy
- [ ] Test `InstanceCreate()` at fixed coordinates
- [ ] Verify `CollisionWalkable()` works for position validation
- [ ] Test squad spawning (multiple enemies at once)
- [ ] Document any crashes or unexpected behavior

### 1.4 POC Implementation
- [ ] Implement 3-5 new spawn points in Forest
- [ ] Add variable squad sizes (2-4 enemies per point)
- [ ] Mix enemy types (bandits, fauna, mutants)
- [ ] Playtest for balance and fun factor

---

## Phase 2: Chaos Mode

### 2.1 Rarity System
- [ ] Implement weighted random enemy selection
- [ ] Test cross-zone enemy spawning
- [ ] Tune rarity percentages:
  - Native: 60%
  - Uncommon: 25%
  - Rare: 12%
  - Anomalous: 3%

### 2.2 Chaos Toggle
- [ ] Add chaos_mode flag to config
- [ ] Test enabling/disabling mid-game

---

## Phase 3: Configuration System

### 3.1 JSON Config Loading
- [ ] Test `FileDataRead()` with `default_config.json`
- [ ] Implement config loading on mod init
- [ ] Add per-zone enable/disable toggles
- [ ] Add spawn_multiplier scaling

### 3.2 Difficulty Presets
- [ ] Implement Easy/Normal/Hard/Nightmare presets
- [ ] Test preset switching

---

## Phase 4: Polish & Expansion

### 4.1 Additional Zones
- [ ] Makeshift Camp
- [ ] Industrial Area
- [ ] Swamp
- [ ] Mall
- [ ] Zakov/City
- [ ] CNPP

### 4.2 Special Events
- [ ] Chaos invasion waves
- [ ] Boss encounter triggers
- [ ] Timed spawn events

### 4.3 Documentation
- [ ] User guide
- [ ] Configuration reference
- [ ] Steam Workshop description

---

## Technical Notes

### Key Functions Reference
```catspeak
-- Primary hook for raid start
EventAssignFunction("enter_raid", func() { ... });

-- Spawn near player's view edge
NpcObjectSpawnNearPlayer(obj_bandit_preset_rookie, 3, true);

-- Spawn at specific coordinates
InstanceCreate(x, y, obj_enemy_ghoul);

-- Check walkable position
if (CollisionWalkable(x, y)) { ... }

-- Get current zone
let room = RoomGetCurrent();
```

### File Locations
- Main entry: `src/main.catspeak`
- Forest spawns: `src/spawns/forest.catspeak`
- Chaos tables: `src/chaos/rarity_tables.catspeak`
- Config: `src/config/default_config.json`
- API reference: `docs/API_NOTES.md`

---

## Questions to Resolve
1. How does mod loading work? (file placement, naming conventions)
2. Can we detect which zone the player is in via room name?
3. What's the coordinate system scale? (pixels? tiles?)
4. Are there any spawn limits or performance concerns?
5. How do we package for Steam Workshop?

---

*Last Updated: December 2024*
