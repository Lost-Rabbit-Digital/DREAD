#!/usr/bin/env python3
"""
Headless playtest + balance benchmark for DREAD, driven through the real mod
script by tools/catspeak_harness.py.

  python -I tools/simulate_raids.py stability          # crash matrix
  python -I tools/simulate_raids.py balance [--raids N] [--legacy old.catspeak]
  python -I tools/simulate_raids.py all

Assumptions (state them when quoting numbers):
  * A Forest raid lasts 15 minutes (54,000 frames at 60 fps).
  * The map is 3000 x 3000 px and 85% of in-bounds points are walkable.
    Spawn coordinates are still unverified estimates, so absolute counts are
    upper bounds: in game, unwalkable/out-of-bounds points are skipped.
  * Threat is measured in "rookie bandit equivalents" (RBE): a vanilla
    bandit_rookie (45 HP, aim radius 18-28) = 1.0. Human threat scales with
    HP x accuracy; mutant/fauna weights are rough estimates (see OBJ_THREAT).
"""
import argparse
import random
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catspeak_harness import FACTIONS_UNKNOWN_IDS, CatError, CatSyntaxError, ModSession  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "DREAD.catspeak"
EXPOSED = ROOT / "docs" / "api" / "exposed_values.txt"
GAMEDATA_CANDIDATES = [
    Path("C:/Program Files (x86)/Steam/steamapps/common/ZERO Sievert/ZS_vanilla/gamedata"),
    Path.home() / ".steam/steam/steamapps/common/ZERO Sievert/ZS_vanilla/gamedata",
]
GAMEDATA = next((p for p in GAMEDATA_CANDIDATES if p.exists()), None)

FPS = 60
RAID_FRAMES = 15 * 60 * FPS
MAP = 3000

ROOMS = {
    "forest": "r_forest", "makeshift_camp": "r_makeshift_camp", "industrial_area": "r_industrial_area",
    "swamp": "r_swamp", "mall": "r_mall", "zaton": "r_zaton", "city": "r_city_layout", "cnpp": "r_npp_layout",
}

ROOKIE_HP, ROOKIE_AIM = 45.0, 23.0
OBJ_THREAT = {
    "obj_bandit_preset_rookie": 1.0, "obj_bandit_preset_skilled": 1.4, "obj_bandit_preset_expert": 1.65,
    "obj_green_army_preset_rookie": 1.22, "obj_green_army_preset_skilled": 1.95,
    "obj_green_army_preset_expert": 2.3, "obj_green_army_preset_master": 4.5,
    "obj_hunter_preset_rookie": 1.22, "obj_hunter_preset_expert": 2.3,
    "obj_crimson_preset_rookie": 1.22, "obj_crimson_preset_skilled": 1.95, "obj_crimson_preset_master": 4.5,
    "obj_watcher_preset_rookie": 1.7, "obj_watcher_preset_skilled": 2.4, "obj_watcher_preset_expert": 3.3,
    "obj_enemy_ghoul": 0.8, "obj_enemy_ghoul_2": 1.2, "obj_enemy_blink": 1.2, "obj_enemy_spider": 1.0,
    "obj_enemy_spine": 1.5, "obj_enemy_big": 3.0, "obj_enemy_infestation": 2.0, "obj_enemy_zombie": 0.8,
    "obj_enemy_boar": 0.6, "obj_enemy_boar_zombie": 0.8, "obj_enemy_wolf_brown": 0.6,
    "obj_enemy_rabbit": 0.0, "obj_enemy_rat": 0.1, "obj_enemy_crow": 0.0,
    "obj_enemy_human_bandit_boss": 6.0, "obj_enemy_human_bandit_boss_guard": 2.5,
    "obj_watcher_devil": 8.0, "obj_boss_killa": 8.0, "obj_boss_city": 8.0, "obj_watcher_general": 8.0,
}
PASSIVE = {"obj_enemy_rabbit", "obj_enemy_crow"}


def set_difficulty(name):
    return lambda src: re.sub(r'difficulty:\s*"[a-z]+"', f'difficulty: "{name}"', src, count=1)


def legacy_scope_fix(src):
    """Make the v0.2.x script loadable (top-level `let` -> dynamic global, and
    `self.debug` -> `DREAD.debug`) so the original *design* can be measured.
    Everything else is left as written."""
    src = src.replace("self.debug", "DREAD.debug")
    out = []
    depth = 0
    for line in src.splitlines():
        code = line.split("--", 1)[0]
        if depth == 0 and re.match(r"\s*let\s+[A-Za-z_]", line):
            line = re.sub(r"^(\s*)let\s+", r"\1", line, count=1)
        depth += code.count("{") + code.count("(") + code.count("[")
        depth -= code.count("}") + code.count(")") + code.count("]")
        out.append(line)
    return "\n".join(out)


def set_debug(on):
    return lambda src: re.sub(r"debug_mode: (true|false),", f"debug_mode: {'true' if on else 'false'},", src, count=1)


def new_session(seed, script=SCRIPT, debug=False, src_transform=None, **kw):
    # Scenarios run with debug_mode off (the release setting) unless asked, so
    # "no popups" means "no errors and no interruptions for players".
    dbg = set_debug(debug)
    transform = (lambda src: src_transform(dbg(src))) if src_transform else dbg
    return ModSession(script, EXPOSED, GAMEDATA, seed=seed, map_w=MAP, map_h=MAP,
                      src_transform=transform, **kw)


def threat_of(spawn):
    if spawn["kind"] == "npc":
        d = spawn["def"]
        rmin, rmax = d["recoil"] if d["recoil"] else (20.0, 30.0)
        if rmax is None:
            rmax = rmin + 10.0
        return (d["hp"] / ROOKIE_HP) * (ROOKIE_AIM / ((rmin + rmax) / 2.0))
    return OBJ_THREAT.get(spawn["obj"], 1.5)


def classify(spawn):
    if spawn["kind"] == "npc":
        return "human"
    o = spawn["obj"]
    if "boss" in o or "devil" in o or "general" in o:
        return "boss"
    if "preset" in o or "human" in o:
        return "human"
    if o in PASSIVE:
        return "passive"
    if "boar" in o or "wolf" in o or o in ("obj_enemy_rat",):
        return "fauna"
    return "mutant"


# -----------------------------------------------------------------------------
# Stability matrix
# -----------------------------------------------------------------------------

def run_scenario(name, fn, seeds):
    t0 = time.time()
    fails = []
    for seed in seeds:
        try:
            fn(seed)
        except (CatError, CatSyntaxError, AssertionError) as e:
            fails.append((seed, f"{type(e).__name__}: {e}"))
    status = "PASS" if not fails else "FAIL"
    print(f"  [{status}] {name:58s} {len(seeds)} seeds  {time.time() - t0:5.1f}s")
    for seed, msg in fails[:3]:
        print(f"         seed {seed}: {msg}")
    return not fails


def raid(s, room="r_forest", frames=RAID_FRAMES, xy=None):
    rng = random.Random(s.world.rng.random())
    s.enter_room(room, xy or (rng.uniform(0, MAP), rng.uniform(0, MAP)))
    s.fire("enter_raid")
    s.step(frames)


def scenario_full_career(seed):
    s = new_session(seed)
    s.load()
    assert not s.world.popups, f"popups on load: {s.world.popups[:2]}"
    s.enter_room("r_hub", (100, 100))
    s.fire("enter_hub")
    s.step(600)
    for _ in range(3):
        raid(s)
        s.enter_room("r_hub", (100, 100))
        s.fire("enter_hub")
        s.step(300)
    assert not s.world.popups, f"popups during play: {s.world.popups[:2]}"


def scenario_death_mid_raid(seed):
    s = new_session(seed)
    s.load()
    raid(s, frames=4 * 60 * FPS)
    s.fire("player_death")
    n = len(s.world.spawns)
    s.step(10 * 60 * FPS)  # ragdoll/death screen still ticking in raid room
    assert len(s.world.spawns) == n, "enemies spawned after player death"
    s.enter_room("r_hub", (100, 100))
    s.fire("enter_hub")
    raid(s)


def scenario_prologue_and_unknown_rooms(seed):
    s = new_session(seed)
    s.load()
    for room in ("r_prologue_layout", "r_before_first_start", "r_base_general", "r_i_house_wood"):
        raid(s, room=room, frames=6 * 60 * FPS)
    assert not s.world.spawns, f"spawned {len(s.world.spawns)} enemies outside raid zones"


def scenario_interior_pauses_invasions(seed):
    s = new_session(seed)
    s.load()
    s.enter_room("r_forest", (2500, 2500))
    s.fire("enter_raid")
    s.step(4 * 60 * FPS)               # 4 min outside (first wave is at 5 min)
    s.world.room = "r_i_house_wood"    # walk into a building for 6 minutes
    s.step(6 * 60 * FPS)
    waves = [sp for sp in s.world.spawns if sp.get("near_player")]
    assert not waves, "invasion wave spawned while the player was inside an interior"
    s.world.room = "r_forest"
    s.step(2 * 60 * FPS)
    waves = [sp for sp in s.world.spawns if sp.get("near_player")]
    assert waves, "invasion never resumed after leaving the interior"


def scenario_every_zone_enabled(seed):
    s = new_session(seed)
    s.load()
    for zcfg in s.rt.globals["DREAD_CONFIG"]["zones"].values():
        zcfg["enabled"] = True
    for zone, room in ROOMS.items():
        raid(s, room=room, frames=12 * 60 * FPS)
        s.enter_room("r_hub", (0, 0))
        s.fire("enter_hub")


def scenario_difficulty(name):
    def fn(seed):
        s = new_session(seed, src_transform=set_difficulty(name))
        s.load()
        assert s.rt.globals["DREAD"]["preset_name"] == name
        raid(s)
        assert len(s.world.spawns) <= s.rt.globals["DREAD"]["preset"]["max_enemies_per_raid"], "raid cap exceeded"
    return fn


def scenario_extreme_density_cap(seed):
    s = new_session(seed, src_transform=set_difficulty("nightmare"), walkable_ratio=1.0)
    s.load()
    s.rt.globals["DREAD_CONFIG"]["zones"]["forest"]["density"] = "extreme"
    raid(s)
    cap = s.rt.globals["DREAD"]["preset"]["max_enemies_per_raid"]
    assert len(s.world.spawns) <= cap, f"{len(s.world.spawns)} > cap {cap}"


def scenario_unmapped_coordinates(seed):
    s = new_session(seed, walkable_ratio=0.0)  # every fixed point is in a wall / off-map
    s.load()
    raid(s)


def scenario_player_on_spawn_cluster(seed):
    s = new_session(seed, walkable_ratio=1.0)
    s.load()
    px, py = 800, 500   # right on top of "Old Cabin Bandits"
    raid(s, xy=(px, py), frames=60)
    radius = s.rt.globals["DREAD_CONFIG"]["safe_start_radius"]
    for sp in s.world.spawns:
        if sp.get("near_player"):
            continue
        d = ((sp["x"] - px) ** 2 + (sp["y"] - py) ** 2) ** 0.5
        # +40 px squad scatter, +30 px position search
        assert d >= radius - 80, f"spawned {d:.0f}px from player (safe radius {radius})"


def scenario_reload_mods_twice(seed):
    # The mod menu "Refresh" re-runs the script (that is where the 12/28 crash
    # happened); a second load must not error.
    s = new_session(seed)
    s.load()
    s.load()
    raid(s, frames=60)


def scenario_factions_load_late(seed):
    # What 0.3.1 hit in game: no faction (not even "Player") exists while
    # init.script runs. DREAD creates its own factions at load and makes them
    # hostile once the player faction exists at raid start, with no popup
    # during load (a blocking popup trips Katspeak's 1000 ms limit).
    s = new_session(seed, debug=True, factions=set())
    s.load()
    assert not s.world.popups, f"popup during load: {s.world.popups}"
    s.world.factions |= {"Player", "Loners"}
    raid(s, frames=60)
    hostile = {a for (a, b), v in s.world.faction_relations.items() if b == "Player" and v == 250}
    assert hostile == {"dread_" + k for k in ("bandits", "green_army", "hunters", "watchers", "crimson")}, hostile
    assert not any("ERROR" in m for m in s.world.popups), s.world.popups


def scenario_faction_ids_unknown(seed):
    # 0.3.0 crashed at load: the game had no faction "Bandits". Model a faction
    # table with none of the documented names; DREAD must fall back to its own
    # player-hostile factions instead of calling NpcSetFaction with a bad id.
    s = new_session(seed, factions=FACTIONS_UNKNOWN_IDS)
    s.load()
    assert not s.world.popups, f"popups on load: {s.world.popups[:2]}"
    dread = {d["faction"] for n, d in s.world.npc_defs.items() if n.startswith("dread_")}
    assert dread and all(f.startswith("dread_") for f in dread), f"factions: {sorted(dread)}"
    raid(s, frames=60)
    hostile = {a for (a, b), v in s.world.faction_relations.items() if b == "player" and v == 250}
    assert dread <= hostile, f"not hostile to player: {sorted(dread - hostile)}"


def scenario_faction_ids_documented(seed):
    # With the documented names present, DREAD uses the vanilla factions
    # (hunters have no documented faction, so they get their own).
    s = new_session(seed)
    s.load()
    used = {d["faction"] for n, d in s.world.npc_defs.items() if n.startswith("dread_")}
    expected = {"Bandits", "Green Army", "Watcher", "Crimson Corporation", "dread_hunters"}
    assert used == expected, f"factions: {sorted(used)}"


def scenario_debug_mode_popups(seed):
    # Debug mode (the playtest default). A popup blocks while Katspeak's 1000 ms
    # budget keeps counting, so none may open during load or a spawn loop: they
    # are queued and shown together on the next player step. Per-spawn detail
    # goes to ShowDebugMessage.
    s = new_session(seed, debug=True)
    s.load()
    assert not s.world.popups, f"popup during load: {s.world.popups}"
    assert any("[DREAD:Faction]" in m for m in s.world.debug_log), "no faction debug log"
    s.enter_room("r_forest", (1500, 1500))
    s.fire("enter_raid")
    assert not s.world.popups, f"popup during enter_raid: {s.world.popups}"
    s.step(1)
    assert len(s.world.popups) == 1, f"popups: {s.world.popups}"
    text = s.world.popups[0]
    assert "Factions:" in text and "Raid start" in text and "exist at raid start" in text, text
    s.step(600)
    assert len(s.world.popups) == 1, f"extra popups: {s.world.popups[1:3]}"


def scenario_faction_create_fails(seed):
    # Worst case: no usable faction ids and FactionCreate does nothing. DREAD
    # must still load and fall back to vanilla preset objects.
    s = new_session(seed, factions=set(), faction_create_works=False)
    s.load()
    assert not [n for n in s.world.npc_defs if n.startswith("dread_")], "defined NPCs without a faction"
    errors = [m for m in s.world.popups if "ERROR" in m]
    assert len(errors) == len(set(errors)), f"repeated error popups: {errors}"
    raid(s, frames=60)
    humans = [sp for sp in s.world.spawns if "_preset_" in sp.get("obj", "")]
    assert humans, "no vanilla fallback humans spawned"


def scenario_missing_objects(seed):
    # Objects missing from this game version read as undefined; spawns using
    # them are skipped instead of crashing.
    strip = lambda src: re.sub(r"\bobj_enemy_ghoul\b(?!_)", "obj_does_not_exist", src)
    s = new_session(seed, src_transform=strip)
    s.load()
    raid(s, frames=60)


def scenario_disabled(seed):
    s = new_session(seed, src_transform=lambda src: src.replace("enabled: true,\n\n    -- true = a summary", "enabled: false,\n\n    -- true = a summary", 1))
    s.load()
    assert not s.world.npc_defs and not s.rt.globals["DREAD"]["initialized"]
    raid(s, frames=60)
    assert not s.world.spawns


def stability(seeds=range(5)):
    print("\nSTABILITY MATRIX (strict: any runtime error = crash in game)")
    seeds = list(seeds)
    results = [
        run_scenario("load -> hub -> 3 full Forest raids -> hub", scenario_full_career, seeds),
        run_scenario("player dies mid-raid, then raids again", scenario_death_mid_raid, seeds),
        run_scenario("prologue / first-start / base / interior rooms", scenario_prologue_and_unknown_rooms, seeds),
        run_scenario("interior mid-raid pauses invasion clock", scenario_interior_pauses_invasions, seeds),
        run_scenario("every zone enabled, raid in each room", scenario_every_zone_enabled, seeds),
        *[run_scenario(f"difficulty '{d}' full raid", scenario_difficulty(d), seeds)
          for d in ("tourist", "normal", "hardcore", "nightmare")],
        run_scenario("nightmare + extreme density respects raid cap", scenario_extreme_density_cap, seeds),
        run_scenario("unmapped coordinates (nothing walkable)", scenario_unmapped_coordinates, seeds),
        run_scenario("player spawns on top of a spawn cluster", scenario_player_on_spawn_cluster, seeds),
        run_scenario("mod reloaded twice from the mod menu", scenario_reload_mods_twice, seeds[:2]),
        run_scenario("game has none of the documented faction ids", scenario_faction_ids_unknown, seeds[:2]),
        run_scenario("documented faction ids use vanilla factions", scenario_faction_ids_documented, seeds[:2]),
        run_scenario("no factions exist until after load (0.3.1 in game)", scenario_factions_load_late, seeds[:2]),
        run_scenario("no factions and FactionCreate fails", scenario_faction_create_fails, seeds[:2]),
        run_scenario("enemy object missing from the game", scenario_missing_objects, seeds[:2]),
        run_scenario("DREAD disabled in config", scenario_disabled, seeds[:2]),
        run_scenario("debug mode: summary popups only", scenario_debug_mode_popups, seeds[:2]),
    ]
    ok = all(results)
    print(f"\n  {'ALL PASS' if ok else 'FAILURES PRESENT'}: {sum(results)}/{len(results)} scenarios")
    return ok


# -----------------------------------------------------------------------------
# Balance benchmark
# -----------------------------------------------------------------------------

def pct(values, p):
    if not values:
        return 0
    v = sorted(values)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def benchmark(label, raids, make_session, frames=RAID_FRAMES):
    rows = []
    errors = Counter()
    for seed in range(raids):
        s = make_session(seed)
        try:
            s.load()
            rng = random.Random(seed * 7919)
            px, py = rng.uniform(0, MAP), rng.uniform(0, MAP)
            s.enter_room("r_forest", (px, py))
            s.fire("enter_raid")
            s.step(frames)
        except CatError as e:
            errors[str(e).split(":")[0] + ": " + e.msg[:70]] += 1
            continue
        static = [sp for sp in s.world.spawns if not sp.get("near_player")]
        waves = [sp for sp in s.world.spawns if sp.get("near_player")]
        humans = [sp for sp in static if classify(sp) == "human"]
        near_start = [sp for sp in static
                      if ((sp["x"] - px) ** 2 + (sp["y"] - py) ** 2) ** 0.5 < 400]
        first_wave = min((sp["frame"] for sp in waves), default=None)
        rows.append({
            "static": len([sp for sp in static if classify(sp) != "passive"]),
            "humans": len(humans),
            "mutants": len([sp for sp in static if classify(sp) == "mutant"]),
            "fauna": len([sp for sp in static if classify(sp) == "fauna"]),
            "boss": len([sp for sp in static if classify(sp) == "boss"]),
            "wave_enemies": len(waves),
            "chasers_by_5min": len([sp for sp in waves if sp["chase"] and sp["frame"] <= 5 * 60 * FPS]),
            "chasers_by_10min": len([sp for sp in waves if sp["chase"] and sp["frame"] <= 10 * 60 * FPS]),
            "first_wave_s": first_wave / FPS if first_wave else None,
            "threat_static": sum(threat_of(sp) for sp in static),
            "threat_waves": sum(threat_of(sp) for sp in waves),
            "human_hp": [sp["def"]["hp"] for sp in humans if sp["kind"] == "npc"],
            "human_threat": [threat_of(sp) for sp in humans if sp["kind"] == "npc"],
            "factions": Counter(sp["def"]["faction"] for sp in humans if sp["kind"] == "npc"),
            "presets": Counter(sp["def"]["preset"] for sp in humans if sp["kind"] == "npc"),
            "near_start": len(near_start),
            "popups": len(s.world.popups),
            "warnings": len(s.world.warnings) + len(s.rt.lenient_hits),
        })
    return label, rows, errors


def summarise(label, rows, errors, raids):
    print(f"\n== {label}  ({len(rows)}/{raids} raids completed)")
    if errors:
        for msg, n in errors.most_common(3):
            print(f"   CRASHED {n}/{raids} raids: {msg}")
    if not rows:
        return None

    def stat(key):
        vals = [r[key] for r in rows]
        return statistics.mean(vals), pct(vals, 10), pct(vals, 90), max(vals)

    out = {}
    print(f"   {'metric':34s} {'mean':>7s} {'p10':>6s} {'p90':>6s} {'max':>6s}")
    for key, desc in [("static", "hostiles added at raid start"), ("humans", "  of which humans"),
                      ("mutants", "  of which mutants"), ("fauna", "  of which hostile fauna"),
                      ("boss", "  of which bosses/guards"), ("wave_enemies", "invasion enemies per raid"),
                      ("chasers_by_5min", "chasing the player by 5:00"),
                      ("chasers_by_10min", "chasing the player by 10:00"),
                      ("threat_static", "static threat (RBE)"), ("threat_waves", "wave threat (RBE)"),
                      ("near_start", "spawned <400px from player start"), ("popups", "popup dialogs")]:
        m, p10, p90, mx = stat(key)
        out[key] = m
        print(f"   {desc:34s} {m:7.2f} {p10:6.1f} {p90:6.1f} {mx:6.1f}")
    hp = [h for r in rows for h in r["human_hp"]]
    th = [t for r in rows for t in r["human_threat"]]
    fw = [r["first_wave_s"] for r in rows if r["first_wave_s"]]
    if hp:
        print(f"   human HP: mean {statistics.mean(hp):.0f}, range {min(hp):.0f}-{max(hp):.0f}  "
              f"(vanilla Forest bandits: 45-55)")
        print(f"   per-human threat: mean {statistics.mean(th):.2f} RBE, max {max(th):.2f}")
        out["human_hp_mean"] = statistics.mean(hp)
        out["human_threat_mean"] = statistics.mean(th)
    if fw:
        print(f"   first invasion wave at {statistics.mean(fw):.0f}s")
    factions = sum((r["factions"] for r in rows), Counter())
    presets = sum((r["presets"] for r in rows), Counter())
    if factions:
        print("   factions: " + ", ".join(f"{k} {v / sum(factions.values()):.0%}" for k, v in factions.most_common()))
    if presets:
        print("   presets:  " + ", ".join(f"{k} {v / sum(presets.values()):.0%}" for k, v in presets.most_common(6)))
    warn = statistics.mean(r["warnings"] for r in rows)
    if warn:
        print(f"   API misuse per raid (lenient mode, would be errors/no-ops in game): {warn:.1f}")
    return out


def balance(raids, legacy=None):
    print(f"\nBALANCE BENCHMARK: Forest, {RAID_FRAMES // (60 * FPS)}-minute raid, {raids} raids per profile")
    print("   (counts are upper bounds until spawn coordinates are mapped in game)")
    profiles = []
    if legacy:
        profiles.append(("v0.2.1 as written (strict)",
                         lambda seed: new_session(seed, script=legacy, src_transform=legacy_scope_fix)))
        profiles.append(("v0.2.1 design, crashes ignored (lenient)",
                         lambda seed: new_session(seed, script=legacy, src_transform=legacy_scope_fix,
                                                  lenient=True)))
    for d in ("tourist", "normal", "hardcore", "nightmare"):
        profiles.append((f"v0.3.0 '{d}'", lambda seed, d=d: new_session(seed, src_transform=set_difficulty(d))))
    results = {}
    for label, make in profiles:
        t0 = time.time()
        lbl, rows, errors = benchmark(label, raids, make)
        results[label] = summarise(lbl, rows, errors, raids)
        print(f"   ({time.time() - t0:.0f}s)")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stability", "balance", "all"])
    ap.add_argument("--raids", type=int, default=40)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--legacy", help="path to a v0.2.x script to benchmark for comparison "
                                     "(e.g. `git show v0.2.1:DREAD.catspeak > old.catspeak`)")
    args = ap.parse_args()
    if GAMEDATA is None:
        print("warning: ZS_vanilla/gamedata not found; preset/chest/armor ids will not be validated")
    ok = True
    if args.mode in ("stability", "all"):
        ok = stability(range(args.seeds))
    if args.mode in ("balance", "all"):
        balance(args.raids, args.legacy)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
