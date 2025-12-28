# Steam Forum Post: AI Behavior API Request

---

## Title: [Modding Request] AI Behavior Hooks for Advanced Combat Mods

---

## Post Content:

Hey devs and community! 👋

I've been diving deep into the Zero Sievert modding API to create **DREAD** (Dynamic Randomized Enemy Area Distribution), a spawn overhaul mod. The current API is fantastic for content creation - spawning enemies, configuring loadouts, creating items, etc.

However, I hit a wall when trying to implement more advanced AI features inspired by mods like **SAIN** (for Escape from Tarkov's SPT). After thoroughly analyzing the modding documentation, I wanted to share what's currently possible vs. what would unlock a whole new tier of mods.

---

### What the Current API Does Well ✅

- **NPC Spawning**: `NpcCreate`, `NpcSpawn`, `NpcObjectSpawnNearPlayer`
- **Equipment Configuration**: `NpcSetWeapon`, `NpcSetArmor`, `NpcSetPreset`
- **Stats**: `NpcSetHp`, `NpcSetRecoilAimRadius`, `NpcSetMeleeDamage`
- **Factions**: `NpcSetFaction`, `FactionSetRelationship`
- **Events**: `EventAssignFunction` for raid start, player spawn, etc.
- **Items/Weapons**: Full creation and modification

This lets us make great spawn overhaul and content mods!

---

### What Would Enable Next-Level Mods 🚀

**AI Behavior Hooks** - Functions to influence how bots make decisions:

```
// Example wishlist functions
NpcSetAggressionLevel(npc_id, 0.0-1.0)     // Passive to aggressive
NpcSetVisionRange(npc_id, distance)         // How far they can see
NpcSetHearingRange(npc_id, distance)        // How far they hear
NpcSetCoverPreference(npc_id, 0.0-1.0)     // How much they seek cover
NpcSetAccuracyModifier(npc_id, modifier)    // Aim skill
NpcSetReactionTime(npc_id, seconds)         // How fast they respond
NpcSetFleeThreshold(npc_id, hp_percent)     // When they run away
```

**Sensory Events** - Know when bots detect things:

```
EventAssignFunction("npc_spotted_player", func(npc, player) {...})
EventAssignFunction("npc_heard_sound", func(npc, x, y, loudness) {...})
EventAssignFunction("npc_taking_fire", func(npc, attacker) {...})
```

**Squad/Group Functions**:

```
NpcCreateSquad(squad_id)
NpcAddToSquad(npc_id, squad_id)
NpcSetSquadLeader(npc_id, squad_id)
SquadSetTactic(squad_id, "aggressive" | "defensive" | "patrol")
```

**Pathfinding Access**:

```
NpcMoveTo(npc_id, x, y)
NpcPatrolPath(npc_id, [points])
NpcInvestigate(npc_id, x, y)
NpcRetreat(npc_id)
```

---

### What This Would Enable

With these hooks, modders could create:

1. **SAIN-style AI Overhaul**: Smarter enemies that use cover, coordinate, and react realistically
2. **Dynamic Difficulty**: AI that adapts to player skill
3. **Stealth Gameplay**: Enemies with tunable detection
4. **Squad Tactics**: Coordinated enemy groups
5. **Personality Systems**: Aggressive vs cautious enemies
6. **Investigation Behavior**: Enemies that search for players

---

### Current Workaround: DREAD

For now, I'm building DREAD to maximize what IS possible:

- Fill dead zones with new spawn points
- SAIN-inspired "archetypes" (GigaChad, Rat, Timmy) via equipment/stat configs
- Chaos Mode for cross-zone enemy variety
- Invasion waves during raids
- Squad spawning with "leader" units

It'll improve variety but can't change HOW enemies behave, only WHERE they spawn and WHAT they carry.

---

### The Ask

Would the dev team consider exposing any AI behavior functions in a future API update? Even just a few basic hooks would massively expand what's possible for combat-focused mods.

I understand if the AI systems are too deeply integrated to expose safely, but wanted to put this request out there. The modding API you've built is already impressive - this would take it to the next level.

Thanks for reading, and thanks for the amazing game! 🎮

---

**TL;DR**: Current API = great for spawns/items. Adding AI behavior hooks would enable SAIN-style smart AI mods. Any chance of future support?

---

*- Lost Rabbit Digital*
*Working on: DREAD (spawn overhaul mod)*
