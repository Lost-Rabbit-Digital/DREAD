# SAIN-Style AI Overhaul: Zero Sievert Feasibility Analysis

## Executive Summary

**Overall Feasibility: LOW (10-15%)**

The Zero Sievert modding API is a **content creation API**, not an **AI behavior API**. It provides functions to spawn, configure, and manage game entities, but does NOT expose the underlying AI decision systems, pathfinding, sensory systems, or behavior trees that would be required to implement SAIN-like features.

SPT-AKI (the platform SAIN runs on) provides deep access to EFT's AI systems because it's essentially a server emulator with full code access. Zero Sievert's modding API is a sandboxed scripting layer on top of a GameMaker Studio game.

---

## Feature-by-Feature Analysis

### 1. Combat AI Replacement

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Replace combat logic | **NOT EXPOSED** | 0% |
| Run to cover while reloading | **NOT EXPOSED** | 0% |
| New decision framework | **NOT EXPOSED** | 0% |
| Move outside bot-zones | **NOT EXPOSED** | 0% |
| In-game GUI configuration | Partial (ShowMessage only) | 10% |

**Analysis:** ZS does not expose AI decision trees, state machines, or behavior logic. The NPC functions only allow configuration of static attributes (HP, weapon, armor, faction) not dynamic behaviors.

### 2. Tracking & Sensory Systems

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Last known position tracking | **NOT EXPOSED** | 0% |
| Visual/audio sensory info | **NOT EXPOSED** | 0% |
| Squad info sharing | **NOT EXPOSED** | 0% |
| Sound-based position accuracy | **NOT EXPOSED** | 0% |
| Flashlight detection | **NOT EXPOSED** | 0% |
| Weather affects vision | **NOT EXPOSED** | 0% |
| Time-of-day vision scaling | **NOT EXPOSED** | 0% |
| Sound occlusion | **NOT EXPOSED** | 0% |
| Rain affects hearing | **NOT EXPOSED** | 0% |

**Analysis:** No sensory system APIs are exposed. `ItemHeadsetSetVisionValues` exists but only affects player equipment, not AI perception.

### 3. Bot Extracts & Looting Behavior

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Move to extract at raid end | **NOT EXPOSED** | 0% |
| Leave when injured | **NOT EXPOSED** | 0% |
| Track loot value | **NOT EXPOSED** | 0% |
| React to player actions | **NOT EXPOSED** | 0% |

**Analysis:** AI goals, objectives, and reactions to player state are not exposed.

### 4. Cover System

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Dynamic cover from objects | **NOT EXPOSED** | 0% |
| NavMesh-based cover | **NOT EXPOSED** | 0% |
| Real-time cover evaluation | **NOT EXPOSED** | 0% |

**Analysis:** `CollisionWalkable()` exists but only checks if a position is traversable, not cover quality or sightlines.

### 5. Personality System

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Personality presets | Partial via `NpcSetPreset` | 20% |
| Gear-based aggression | **NOT EXPOSED** | 0% |
| Decision modifications | **NOT EXPOSED** | 0% |

**Analysis:** `NpcSetPreset` sets visual/equipment presets but cannot modify decision-making. The personality names (GigaChad, Rat, etc.) would be cosmetic labels only with no behavioral impact.

### 6. Squad Systems

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Squad coordination | **NOT EXPOSED** | 0% |
| Squad leader commands | **NOT EXPOSED** | 0% |
| Suppression while ally retreats | **NOT EXPOSED** | 0% |
| Regrouping behavior | **NOT EXPOSED** | 0% |
| Group aggression levels | **NOT EXPOSED** | 0% |

**Analysis:** `NpcSetFaction` sets faction relationships but doesn't control squad tactics. No group coordination APIs exist.

### 7. Voice & Communication

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Complex callout system | **NOT EXPOSED** | 0% |
| Enemy location callouts | **NOT EXPOSED** | 0% |
| Response to player voice | **NOT EXPOSED** | 0% |
| Personality voice behaviors | Partial via `NpcSetSpeaker` | 15% |

**Analysis:** `NpcSetSpeaker` and `SpeakerCreate` exist for dialogue but appear to be for trader/NPC conversations, not combat callouts.

### 8. Movement & Tactics

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Blind fire | **NOT EXPOSED** | 0% |
| Corner peeking | **NOT EXPOSED** | 0% |
| Dynamic lean | **NOT EXPOSED** | 0% |
| Stim/injector usage | **NOT EXPOSED** | 0% |
| Hand gestures | **NOT EXPOSED** | 0% |

**Analysis:** No movement behavior APIs exposed.

### 9. Weapon Handling

| SAIN Feature | ZS API Support | Feasibility |
|--------------|----------------|-------------|
| Semi-auto swap at range | **NOT EXPOSED** | 0% |
| Recoil-based fire rate | Partial via `NpcSetRecoilAimRadius` | 20% |
| Burst length control | **NOT EXPOSED** | 0% |

**Analysis:** `NpcSetRecoilAimRadius` and `NpcSetRecoilCrosshairDelay` exist but appear to affect accuracy, not firing behavior decisions.

---

## What IS Possible in Zero Sievert

Based on the API analysis, here's what a "SAIN-lite" mod COULD do:

### Spawn Manipulation (DREAD already covers this)
- Add/modify enemy spawn points
- Configure enemy loadouts (weapons, armor)
- Set faction relationships
- Adjust HP, damage values
- Create weighted spawn pools

### Static NPC Configuration
```catspeak
NpcCreate("elite_bandit");
NpcSetPreset("elite_bandit", "bandit_master");
NpcSetHp("elite_bandit", 200);
NpcSetWeapon("elite_bandit", "weapon_ak74");
NpcSetArmor("elite_bandit", "armor_heavy");
NpcSetRecoilAimRadius("elite_bandit", 5);  -- More accurate
NpcSpawn("elite_bandit", x, y);
```

### Difficulty Scaling via Presets
- Create difficulty tiers with different enemy configurations
- Scale enemy count via spawn multipliers
- Modify equipment quality based on difficulty

### Event-Based Spawning
- Trigger spawns on raid start
- Spawn enemies at intervals during raid (via step events)
- React to player entering zones (if zone detection is possible)

---

## Comparison: What SAIN Does vs. What ZS Allows

| System Layer | SAIN Access | ZS Access |
|--------------|-------------|-----------|
| Spawn/Configuration | Full | Full |
| Equipment/Stats | Full | Full |
| Pathfinding | Full | None |
| Decision Trees | Full | None |
| Sensory Systems | Full | None |
| Squad Coordination | Full | None |
| Animation Control | Full | None |
| Voice System | Full | Limited |
| Cover Evaluation | Full | None |

---

## Recommendations

### Option A: Accept Limitations
Focus on what IS possible:
- Enhanced spawn distribution (DREAD)
- Difficulty scaling through static configuration
- Equipment variety through preset manipulation
- Accept that AI behavior cannot be modified

### Option B: Request API Expansion
Contact Zero Sievert developers to request:
- AI behavior hooks
- Sensory system access
- Pathfinding APIs
- Squad coordination functions

### Option C: Alternative Approaches
Consider non-AI mods that enhance combat feel:
- Weapon rebalancing
- Damage scaling
- Enemy variety through spawn pools
- Environmental hazards
- Timed events and invasions

---

## Conclusion

A SAIN-equivalent mod is **not feasible** for Zero Sievert with the current modding API. The API provides excellent tools for content creation (items, weapons, spawns) but does not expose the AI behavior layer required for SAIN's features.

**DREAD remains the most impactful AI-adjacent mod possible** - it enhances the combat experience through spawn manipulation rather than behavior modification.

If AI behavior modification is a priority, the recommendation is to:
1. Contact the ZS developer to request AI hooks in future API updates
2. Monitor the modding documentation for new AI-related functions
3. Focus current efforts on maximizing what IS possible (DREAD, equipment mods, events)

---

## API Evidence

### Functions That DO Exist (Content Creation)
- `NpcCreate`, `NpcSpawn`, `NpcSetPreset`
- `NpcSetWeapon`, `NpcSetArmor`, `NpcSetHp`
- `NpcSetFaction`, `NpcSetRecoilAimRadius`
- `EventAssignFunction`, `ObjectSetScript`
- `InstanceCreate`, `CollisionWalkable`

### Functions That DON'T Exist (AI Behavior)
- No `NpcSetBehavior` or `NpcSetAI`
- No `NpcSetVisionRange` or `NpcSetHearingRange`
- No `NpcSetCoverPreference` or `NpcSetAggression`
- No `NpcSetSquad` or `NpcSetLeader`
- No `NpcSetPatrolPath` or `NpcSetGoal`
- No `NpcReactTo` or `NpcOnSense`
- No pathfinding or navigation functions
- No state machine or behavior tree access

---

*Analysis Date: December 2024*
*Based on: Zero Sievert Modding Documentation v1.0*
*Comparison Target: SAIN 3.0 for SPT-AKI*
