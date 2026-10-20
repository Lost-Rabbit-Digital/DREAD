# DREAD Playtest & Balance Report — v0.3.0 (2026-10-20)

Headless playtest of the real mod script via `tools/catspeak_harness.py` (Catspeak 3.1.1 scoping rules,
GML-strict runtime errors, ZS API mocks validated against `ZS_vanilla/gamedata`).

**Harness validation:** it reproduces the real in-game crash from `CrashReport_12_28_2025.txt` exactly
(installed build, line 1401: *"value is not a function, got 'undefined'"*), and runs the known-good
"Feral Hogs" workshop mod without errors.

## Crash-level bugs found in v0.2.1 (all fixed)

| # | Severity | Bug | Effect |
|---|----------|-----|--------|
| 1 | Critical | Top-level `let` values used inside functions (Catspeak has no closures) | Crash on load / mod-menu refresh, 100% of the time. The "fix" in edebee0 only moved it to line 1402 |
| 2 | Critical | `result.members` read on an array in `DREAD_ExecuteForestSpawns` | Crash in Forest raids |
| 3 | Critical | `NpcSetRecoilAimRadius(id, r)` missing its `max` argument | Crash/undefined behaviour on first human spawn (100% of Forest raids) |
| 4 | High | Chaos wave passed `undefined` to `NpcObjectSpawnNearPlayer` 60% of rolls | Crash whenever Chaos Mode is on |
| 5 | High | `self.debug` in log methods (`self` is not the struct) | Crash or logging silently broken |
| 6 | High | `FileDataRead("dread_config.json")` reads a save-data key, not the file | Config file ignored; template zones with fake coordinates enabled; if it returns `undefined`, 35 modal popups by the first second of a raid |
| 7 | High | `NpcSetFaction("bandits")` etc. — invalid faction names; `NpcCreate` clones friendly `loner_novice` | Wrong/friendly faction, fixed loner loot for every tier |
| 8 | Medium | Template spawn chances multiplied by density in place each raid | Spawns compound every raid (dense) or decay to zero (sparse) |
| 9 | Medium | Room `r_industrial` doesn't exist (`r_industrial_area`); unknown rooms counted as "in raid" | Invasions could fire in the prologue/interiors |

## Balance: Forest, 15-minute raid (60 raids/profile)

Threat = rookie-bandit equivalents (RBE): vanilla `bandit_rookie` (45 HP, aim radius 18–28) = 1.0.

| Profile | Added hostiles | Invasion enemies | Chasing by 5:00 | Total threat | Human HP | Per-human threat |
|---------|----------------|------------------|-----------------|--------------|----------|------------------|
| v0.2.1 design (crashes ignored) | 21.4 | 10.9 | 7.3 | 56.2 | 97 (60–150) | 3.36 |
| v0.3.0 tourist | 8.9 | 0 | 0 | 7.5 | 44 | 0.96 |
| **v0.3.0 normal (default)** | 13.9 | 3.7 | 1.9 | 17.4 | 50 (36–85) | 1.23 |
| v0.3.0 hardcore | 21.9 | 15.7 | 10.9 | 47.4 | 62 | 1.99 |
| v0.3.0 nightmare | 27.6 | 35.5 | 17.9 | 99.9 | 80 | 3.71 |

The v0.2.1 design gave every Forest human 60–150 HP and veteran-grade aim (vanilla Forest bandits:
45–55 HP, rookie aim) plus 7 chasers in the first 5 minutes — roughly 3x the threat of a hardcore
v0.3.0 human. The default is now a busier-but-fair first zone; the old intensity lives in Hardcore.

## Stability matrix (strict, 5 seeds each): 13/13 pass
Load → hub → 3 raids; death mid-raid; prologue/first-start/base/interior rooms (no spawns);
interior pauses invasions; every zone enabled; all 4 difficulties; raid cap under nightmare+extreme;
unwalkable map; player spawning on a spawn cluster (safe-start radius); mod reloaded twice.

## Not verified (needs the real game)
- Spawn coordinates are placeholders, so absolute counts are upper bounds.
- `NpcSpawn` reusing one definition for many instances; `ObjectSetScript` replace-vs-chain semantics.
- Room names for Zakov/City/CNPP; 60 fps step assumption; walkability model.
- Mutant/fauna threat weights are estimates.
