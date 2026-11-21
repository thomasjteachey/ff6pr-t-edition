# T-Edition 3.0.7 + EX 2.0.6: feature audit of the Pixel Remaster port

Audit of 2026-11-21 (read-only; nothing built or run). Every feature T-Edition's own documents name, checked against
the port's code and data. A feature counts as done only where code or data that does it was found.

Sources read (all of them): the Lua package's HTML guides (`readme.html`, `change.html`, `history.html`, `EX readme.html`,
`EX history.html`, `newevent.html` (empty in this package), `dressroom.html`, `bgm.html`, `background.html`, `windowtype.html`,
`spoiler_free_new_quests.txt`, the long `readme translation ... .txt`), Mato's notes (`Final Fantasy VI T-Edition + EX README
(Mato Notes).txt`, `Readme A7 (v307).txt`, `Quick Advice For the Mod.txt`, `Hidden Secret Boss In EX Patch Info.txt`,
`Retro Achievements.txt`, `CURRENT KNOWN BUGS - READ ME.txt`, the strategy-guide pointer), and `For Producers/`.
Reference lists with no feature claims of their own (weapon/armor/magic/rage/coliseum/shop/veldt/worldmap lists) are
covered by the data rows that port them.

Status rules used: **TESTED** = an in-game run shows it working (log line or screenshot cited); **PORTED** = code or data
exists, not seen in game (a log line that only shows a hook installed or data loaded counts as PORTED, not TESTED);
**PARTIAL** = part is there, the rest is named; **MISSING** = nothing implements it; **LEFT OUT** = deliberately not ported.
For events: PORTED needs every event of the feature scripted with at most 10% of its translated commands still stubs
(`data/snes_event_ted_catalog.json`: `stubs` against `translated`); more stubs or unscripted events = PARTIAL. No event
script has run in game through its trigger yet (ted-7's quest scripts were refused: "didn't start (not in map 42's list,
or a script runs)", `build/test_logs/ted-7-laptop.out`).

In-game evidence available (ted-7, laptop, 2026-11-21; `build/test_logs/20261121-025612_*`, shots in
`build/t-edition/shots/`): teddamage 7 ok / 0 failed; tedsteal ok; tedcheck 312/313; new-monster battles 30723, 30726,
2542, 30696 started (shot `ted_mon_30723.png`: Seraph in battle); new maps 724, 697, 691 loaded by warp (shot
`maps2/room_724.png`); new-map scripts sc_tedm_03FAA5 (id 10073, Music Room, Mato's text and a Yes/No choice, ended)
and sc_tedm_037370 (room 697, Namingway's line; the script then never ended: "STEP FAILED: 'until scene field; map
697;(?!.*; script ) 120 ...' timed out", `20261121-025612_ted-maps-2@laptop.harness.txt` line 106). A harness battle
stalled ("the battle doesn't end") and ted-monsters hit `KeyNotFoundException` in `CalcControllerProvider.GetMagicStatus`
(`20261121-025612_ted-monsters@laptop.log` line 111).

## 1. Summary

| Area | Rows | TESTED | PORTED | PARTIAL | MISSING | LEFT OUT |
|---|---:|---:|---:|---:|---:|---:|
| Mechanics/battle | 44 | 5 | 23 | 7 | 8 | 1 |
| Items and equipment | 21 | 1 | 15 | 3 | 2 | 0 |
| Characters/commands/espers/magic | 31 | 1 | 18 | 8 | 4 | 0 |
| Monsters/formations/AI | 9 | 1 | 6 | 2 | 0 | 0 |
| Maps | 9 | 2 | 5 | 2 | 0 | 0 |
| Events/story scenes | 44 | 0 | 1 | 33 | 10 | 0 |
| Pub quests | 20 | 0 | 2 | 18 | 0 | 0 |
| NG+/post-game | 8 | 0 | 0 | 5 | 3 | 0 |
| Costumes/dressing room | 10 | 0 | 4 | 3 | 2 | 1 |
| Music | 8 | 0 | 3 | 4 | 1 | 0 |
| Graphics | 14 | 1 | 4 | 4 | 5 | 0 |
| Menus/UI/rooms (Collection, Achievements, Track Record) | 11 | 0 | 0 | 3 | 7 | 1 |
| Text/translation | 10 | 1 | 3 | 1 | 3 | 2 |
| EX | 13 | 0 | 8 | 2 | 0 | 3 |
| Platform patches (outside the game) | 4 | 0 | 0 | 0 | 0 | 4 |
| **All** | **256** | **12** | **92** | **95** | **45** | **12** |

## 2. Weighted completion

Done = PORTED + TESTED + half of PARTIAL, over all rows but LEFT OUT. Every row weighs the same (a quest counts as much
as a battle rule), so this is a feature count, not the effort-weighted table in `pr/PORTING.md`.

| Area | Counted rows | Done (T + P + PARTIAL/2) | Completion |
|---|---:|---:|---:|
| Mechanics/battle | 43 | 31.5 | 73% |
| Items and equipment | 21 | 17.5 | 83% |
| Characters/commands/espers/magic | 31 | 23 | 74% |
| Monsters/formations/AI | 9 | 8 | 89% |
| Maps | 9 | 8 | 89% |
| Events/story scenes | 44 | 17.5 | 40% |
| Pub quests | 20 | 11 | 55% |
| NG+/post-game | 8 | 2.5 | 31% |
| Costumes/dressing room | 9 | 5.5 | 61% |
| Music | 8 | 5 | 62% |
| Graphics | 14 | 7 | 50% |
| Menus/UI/rooms (Collection, Achievements, Track Record) | 10 | 1.5 | 15% |
| Text/translation | 8 | 4.5 | 56% |
| EX | 10 | 9 | 90% |
| Platform patches (outside the game) | 0 | 0 | (all LEFT OUT) |
| **All** | **244** | **151.5** | **62%** |

Read with care: only 12 of the 244 counted rows (5%) have been seen working in game; the 92 PORTED rows are code or data
that has never run through its real trigger. PORTING.md's own estimate (~60%, effort-weighted) is close to this count,
but the two areas the player meets most outside battle, events (40%) and menus/rooms (15%), sit lowest. Open risks from
ted-7 that may touch many rows at once: the stalled harness battle (rule 44's time freeze never logged in that run),
`KeyNotFoundException` in `GetMagicStatus` during new-monster fights, the quest scripts the game refused, and room 697's
Namingway script that never ended.

## 3. Checklist

Columns: feature, source (file and section), status, evidence, and for PARTIAL/MISSING the work needed with its owner in
brackets. `C2/xxxx`-style rule numbers refer to `pr/ted/BATTLE_SPEC.md`'s rule table ("spec N").

### Mechanics/battle

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| M1 | ATB and time stop while an action plays (FF5-like) | change.html §1 "ATB System" | PORTED | `TedStatuses.cs:54-57` (spec 44: UpdateGaugeIncrease/UpdateChantTime held, status clock held); ted-7 expected "rule 44" and saw it 0 times (its battle stalled) | — |
| M2 | Battle speed: monster ATB 255-4*speed, Haste 96 / Slow 32 | history (reverted note), spec 45 | PORTED | `Plugin.cs:112-119`; ted-7 log "rule 45: ATB: Haste x144, monster speed term 4" (hook installed) | — |
| M3 | Command wait times per command (Blitz/Bushido/Lore slower, X-Magic slightly faster) | readme.html §7 FAQ; spec 46 | PORTED | `Plugin.cs:112`, `TedRules/StatusMath.cs:24` | — |
| M4 | Accuracy/evasion bug fixed (physical uses Evade) | readme.html §6 "Evasion Bug"; change §2 "Accuracy Bug" | PORTED | spec 19 "none: the PR already uses Evade" | — |
| M5 | Blind lowers hit rate (vanilla bug fixed) | readme.html §6 "Blind Bug"; change §2 "Blind Status" | PARTIAL | spec 20; progress-2026-11.md (11-20 plugin row) "likely already the PR's: rules 20 ... (to confirm in a run)"; no TedPlugin code | probe the PR's blind penalty; if not a halving, use a kit BlindRules variant [TedPlugin] |
| M6 | Vanish no longer lets every spell (X-Zone) land | readme.html §6 "Vanish Magic Bug" | PORTED | spec 23 "the PR already fixed Vanish + Doom (patch 1.0.5)" | — |
| M7 | No hit-rate change from the target's statuses | spec 21 | PORTED | `Plugin.cs:163-180`; ted-7 log "rule 21: no hit-rate change ... (both lists emptied)" (installed) | — |
| M8 | Drop odds 68/20/8/4 over four drop slots | change §2 "Item Drop Rate" | PARTIAL | `profile_tedition.py:608`; ted-7 tedcheck "MONSTER_DROP_RATE 68/19/8/5" but "FAILED (1): monsters with 3-4 drop slots: game 281, port 220"; the PR's own rows 385-611 keep 2 slots (`docs/tedition.md:127-133`) | carry the 61 missing 3rd/4th slots; check what the PR does on an empty slot [lead] |
| M9 | Back/pincer/side attack odds fix; Back Guard (Alarm Earring) stronger | change §2 "Back Attack/Pincer..." | MISSING | spec 24 (Back Guard bit moved to $3A6D bit 6); `mods/TEditionPort/port_report.txt` "relic effect byte ... not portable as data (need plugin)" | encounter-type hook (kit SnesEncounterRules) reading T-Edition's relic bits [TedPlugin] |
| M10 | Pre-emptive strike chance doubled, Gale Hairpin x4 | change §2 "Pre-emptive Strike Increase" | MISSING | spec 24 (relic bit 5 = x4); no code | same hook as M9 [TedPlugin] |
| M11 | Defense-ignoring attacks go through Def 0 (Safe/Defend/row apply) | change §2 "Defense-Ignoring Attacks" | TESTED | `TedRules/DamageSteps.cs:155-158`; ted-7 teddamage "Fight on a monster (Attack #1) ... ignores defense ... ok" | — |
| M12 | Weakness quarters defense instead of x2 | change §2 "Weakness Attribute" | TESTED | spec 7, `TedDamage.cs:170-196`; teddamage "Fire on a monster ... rules' factor x1.038 [6,7] ok" | — |
| M13 | Multi-element attacks: each element counted separately | change §2 "Multiple Attribute Attacks" | PORTED | spec 6, `TedDamage.cs:306-323` (Resist_Postfix); teddamage "a multi-element spell on a monster: skipped" | — |
| M14 | Half damage from defense-ignoring attacks on flagged monsters | change §2 "Protection Against Defense-Ignoring Damage" | PORTED | `DamageSteps.cs:182-185` (spec 9); list from `tools/ted_plugin_data.py:13` | — |
| M15 | Equipment statuses win over Ribbon (Cursed Shield stays cursed) | change §2 "Status Ailments" | MISSING | spec 52, deferred (progress 11-20: "deferred ... 52(b,d,e,f)"); no code | status-set hook keeping equipment statuses through immunity [TedPlugin] |
| M16 | Near Fatal at 1/4 HP (Cover, desperation, SOS relics follow) | change §2 "Critical Health" | PORTED | `profile_tedition.py:609` RATE_HAVE_NEAR_DEATH 4 | — |
| M17 | "Critical Health" element: percent spells only inflict Near Fatal; Near-Fatal-immune monsters dodge them | change §2; EX history (Gravity/Tornado change) | PARTIAL | percent groups as data (`ted_plugin_data.py:47-233`, rule 49); spec 48's "all statuses resisted -> miss" step unchecked in the PR | check the PR misses on Near-Fatal-immune monsters; else a hook [TedPlugin] |
| M18 | Percent damage: listed spells on current HP, the rest (Diabolos 3/4, Wave Cannon 9/16) on max HP | history 2.9.5/2.9.7; spec 49 | PORTED | `ted_plugin_data.percent_damage` run by `ted_build.py:88-89` | — |
| M19 | Stop shorter than Sleep (9 steps) | change §2 "Stop Status" | PORTED | `Plugin.cs:125-127`; ted-7 log "rule 51: status clock: Stop 9 steps" (installed) | — |
| M20 | Poison 1/8 max HP a tick, cap 999 | change §2 "Poison Status" | PORTED | `TedStatuses.cs:71-95`, `StatusMath.cs:13`; ted-7 expected "rule 50" and saw it 0 times | — |
| M21 | Regen 1/8 (party) / 1/16 (monsters), cap 999, no Stamina | change §2 "Regen Status" | PORTED | `TedStatuses.cs:97-109`, `StatusMath.cs:14` | — |
| M22 | Sap renamed Disease, drains MP | change §2 "Disease Status" | PORTED | `TedStatuses.cs:111-125` (MP/16 per the code; docs say 1/8) | — |
| M23 | Critical hit rate 8% | change §2 "Critical Hit Rate" | PORTED | `profile_tedition.py:625`, `ted_build.py:48-74` | — |
| M24 | Espers summonable any number of times | change §2 "Summoning Eidolons" | PORTED | `TedStatuses.cs:52-53` (spec 55); MP costs are esper data (C9) | — |
| M25 | Defend: magic taken x2/3 as well | change §2 "Defend Status" | TESTED | spec 10; teddamage "monster Fire on a defending character ... [10] ok" | — |
| M26 | Back row: physical taken x2/3 (was 1/2) | change §2 "Back Row Status" | PORTED | spec 10, `TedDamage.cs:188` (BackRow); not in teddamage's samples | — |
| M27 | Shell also cuts healing and defense-ignoring magic | change §2 "Shell Status" | TESTED | teddamage "Cure on a Shelled character (Cure #76) ... x0.65 ... [8] ok" | — |
| M28 | Absorb gives the full computed damage | change §2 "Absorbing Damage" | PORTED | `TedStatuses.cs:51, 143-165` (spec 54) | — |
| M29 | Reflected magic not halved (3+ reflectors out-damage one hit) | change §2 "Reflect Status" | PARTIAL | spec 53; progress 11-20 "likely already the PR's: ... 53 (to confirm in a run)"; `TedSelfTest.cs:142` only logs it | probe a reflected spell in game; hook if the PR halves [TedPlugin] |
| M30 | Damage/heal cap 32000, 5-digit display | change §2 "Damage/Recovery Limit Increase" | PARTIAL | `profile_tedition.py:609` MAX_HIT_VALUE 32000; spec Unknowns "Whether the PR draws 5-digit damage" | check a 5-digit hit on screen [TedPlugin] |
| M31 | Desperation attacks: easier (code 1/32), unlimited, no 768 timer, new ones for Gau/Umaro, blocked by Offering | change §2 "Desperation Attacks" | MISSING | spec 39 deferred; no code (only `pr/ted/*.md` mention it) | trigger hook + Gau/Umaro/Gogo desperation abilities [TedPlugin] |
| M32 | Two-handed grip: double damage, lower evasion | change §4 "2 Hands" | PORTED | spec 13 "the PR's TwoHandedMagnification is already 2" | — |
| M33 | Dual wield: 0.75 per hand | change §4 "Dual Wield" | PORTED | `Plugin.cs:150-160` (spec 14, SnesRelicPenalties) | — |
| M34 | Master's Scroll/Offering: normal accuracy, no procs or desperation | change §4 "Barrage"; EX history | MISSING | spec 62 / Unknowns "Offering's 'normal accuracy, no procs': not located" | locate in C1/C2, then hook [TedPlugin] |
| M35 | Attack/magic boost relics don't stack; magic boost raises heals | change §4 "Physical/Magical Attack Power Up" | PORTED | `TedDamage.cs:73-86, 214-226, 243-273` (spec 15) | — |
| M36 | Bonus vs flying: darts/cards x2 vs Float under Fight | change §4 "Extra Damage to Flying Monsters"; 3.0.0 | PORTED | `TedDamage.cs:51-71` (spec 16) | — |
| M37 | Image lost on half of dodges | spec 22 | PORTED | `profile_tedition.py:611` | — |
| M38 | Golem/Interceptor blocker defense 119 | spec 11 | MISSING | deferred (progress 11-20); no code | dog/golem block hook [TedPlugin] |
| M39 | New multi-hit spell effects (Tiger Rush 3 hits, Meteor 2-4, 8-hit effect) | change §3 Sabin; EX history (Meteor); spec 26 | MISSING | no data or code found for effects $14/$46/$47 | hit counts as ability data where the PR has the shape, else a hook [lead] |
| M40 | Coliseum fights under the player's control | change §1 "Coliseum Battles" | PARTIAL | `TedStatuses.cs:40-47`, but behind `[Battle] ColiseumControl` default false (`Plugin.cs:63-64`) | test in game, then default on [TedPlugin] |
| M41 | Steal: (Lv+70-target Lv)/99, rare 1/4 | change §4 "Steal" | TESTED | `TedCommands.cs:95-125`; ted-7 "tedsteal: 264/400 stolen (66.0%), T-Edition's chance 68% ... ok" | — |
| M42 | Gil Toss: Lv x180 gil, Lv x90 to every target; monsters' own rule | change §4 "Gil Toss"; EX history | PARTIAL | characters: `TedCommands.cs:155-166`, `TedDamage.cs:227-233`; monsters: `CommandMath.MonsterGilToss` never called; ted-7 tedgil printed only the game's own values | apply the monster rule; verify cost and damage in game [TedPlugin] |
| M43 | Psycho Cyan bugs (Retort flag after death; Imp) fixed | readme.html §6 | MISSING | no check of the PR's behaviour, no code | probe the PR; hook if the flag survives death [TedPlugin] |
| M44 | Game over returns to the title (kills the airship bug) | readme.html §6 "Airship Bug" | LEFT OUT | a fix for an SNES-engine airship-state bug; the PR's game over is its own code (not re-checked here) | — |

### Items and equipment

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| I1 | Item list rebuilt: re-slotted and new items, the second bank of 24 relics | change §5 "Item Classification"; armor/weapon.html | TESTED | `tools/item_identity.py`; ted-7 tedcheck "items 279/279 (moved rows 205/205); new weapon rows 24/24" | — |
| I2 | Weapon and armor stats, equip lists, elements, worn statuses | weapon.html, armor.html; 3.0.0 notes | PORTED | port_report "weapon: 114 changed", "armor: 104 changed", "job_group: 32 new equip groups", "equipment resistances" | — |
| I3 | Weapon properties: MP Critical, HP/MP absorb, Row OK, throwable, bonus vs flying/human/magic/dragon | change §1 "Equipment Details Menu"; 3.0.0 | PARTIAL | port_report "weapon rules rebuild ... effective_species 114/114"; not portable: 2 weapons "with both a spell proc and HAWK_EYE", Zeus' Mace and Rune Bell "multi-element, kept first", 2 weak_attribute values, Trump's condition group | the listed weapons in TedPlugin [TedPlugin] |
| I4 | Weapon spell procs | weapon.html | PORTED | port_report "weapon procs: 34 weapons (20 new ...)" | — |
| I5 | Relic effects T-Edition re-coded (relic bits) | armor.html; history ("changed the address of the effect setting") | PARTIAL | port_report "not portable as data (need plugin)": ~35 item bits in bytes 5/9/11/12/13 + armor procs 0x8C-0x8E | decode each bit and implement (includes M9/M10's) [TedPlugin] |
| I6 | Relic command swaps: Zeidrich (Shock), Maiden's Prayer (Pray), Embroidered Tippet (Spirit), Pheasant Strap (Animal), Gem Box, Dragon Horn, Thief, Heiji's Jitte | change §3 Terra/Celes/Relm/Mog; spec 31 | PORTED | `profile_tedition.py:630-637`; `ted_build.py:221-239` (Pray casts Sunbath, Spirit Bless, Animal random) | — |
| I7 | Sprint Shoes and Fake Mustache removed (hold B to dash) | change §1 "Movement Speed"; §3 Relm | PORTED | neither in `mods/TEditionPort/ted_items.json`; the PR dashes by itself | — |
| I8 | Stat Tabs, Golden Apple, Soma Drop raise stats | 3.0.0 "Tab items"; Quick Advice | PORTED | `ted_build.py:276-319` (layout "inferred, not seen: check one Tab in game") | — |
| I9 | Combined cure items; Reincarnation | 3.0.0 "Added and combined status recovery items" | PORTED | `ted_build.py:277-342` | — |
| I10 | Orichalcum: power from steal count, shown in the item screen | change §3 Locke | PORTED | `TedCommands.cs:251-282` (spec 28, menu value via ConfirmedAttack); ted-7 only gave one ("gave 1 x Orichalcum") | — |
| I11 | Ultima (Atma) Weapon on Stamina, not Level | change §5 "Ultima Weapon" | PORTED | `DamageSteps.cs:190-196` (spec 17) | — |
| I12 | Ultima Weapon's blade changes with damage (dagger/sword/great sword) | change §5 "Ultima Weapon" | MISSING | spec 17 names thresholds 2000/5000; no code | weapon-sprite swap by computed damage [TedPlugin] |
| I13 | Valiant Knife no longer ignores defense | change §5 "Valiant Knife" | PORTED | `TedDamage.cs:145, 234` (spec 60) | — |
| I14 | Dancing Dagger: 50% a random dance | change §5 "Dancing Dagger" | PORTED | `ted_build.py:242-265` | — |
| I15 | Dice / Fixed Dice formula, accuracy, no Berserk boost | change §5 "Dice/Fixed Dice" | PORTED | `TedDamage.cs:151-169` (spec 41) | — |
| I16 | Other new items (Experience Egg, Gold Hairpin as relic, Kenkonken throwable, Power Belt, ...) | history 3.0.0, 2.9.5 | PORTED | names in `ted_items.json`; port_report "rods and throwing" | — |
| I17 | Shop stock, T-Edition's own shops included | shop.txt | PORTED | `ted_build.py:351-376`; port_report "79 SNES shops matched"; docs/tedition.md:11 "all 110 stocked shops mapped" | — |
| I18 | WoR shop prices double until Humbaba falls | Mato README "Legendary Fiend Humbaba"; spoiler_free_new_quests | MISSING | no code or data found | price hook on a story flag [TedPlugin] |
| I19 | Treasure chest contents on vanilla maps | readme translation (chests) | PARTIAL | port_report "129 PR chests changed in 92 map files; skipped {'no PR chest (new in BNW or unmatched)': 25}" | place or reroute the 25 [ted-maps] |
| I20 | Boss reward items on winning (42 fights) | spec (4B/4A00) | PORTED | `TedColiseum.cs:17-19`; ted-7 log "42 boss rewards" (loaded) | — |
| I21 | Coliseum wagers, opponents, prizes (Tabs farming, Typhon) | coliseum.txt; history | PORTED | `TedColiseum.cs:12-40`; ted-7 "278 Coliseum wagers (3 of 3 lookups hooked)" (loaded, no wager played) | — |

### Characters/commands/espers/magic

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| C1 | Starting stats and equipment | change §3 "Character Overview" | PORTED | port_report "characters: 16 changed" | — |
| C2 | Per-character HP/MP growth tables | change §1 "HP/MP Status Growth" | PORTED | `ted_build.py:139-172` (groups 101-114) | — |
| C3 | Espers give no stat growth (also ends the damage-overflow bug) | change §1; readme.html §6 | PORTED | `Plugin.cs:133-142`; ted-7 log "rule 4: espers give no level-up bonus (27 espers answer none)" (installed) | — |
| C4 | Spells removed (Reraise, Graviga, Quick, Imp; Merton enemy-only) and added (Blink, Flood, Scourge, Toad, Comet, Kill) | change §2 "Magic"; history | PORTED | `mods/TEditionPort/.../system_en.txt` MSG_MAGIC_NAME_06 Blink, _29 Flood, _30 Scourge, _20 Toad, _42 Comet, _267 Kill; port_report "ability: 229 changed" | — |
| C5 | Magic classes White / Black / Time | change §1 "Magic Classification" | PORTED | the port's spell names carry T-Edition's class icons (IC_WMGC/IC_BMGC/IC_IMGC) | — |
| C6 | Spell power, accuracy, MP, elements (magic.html) | magic.html; EX history | PORTED | `tools/port_spells.py:225-238` via the porter | — |
| C7 | Terra's and Celes's natural magic changed | change §3 Terra/Celes | PORTED | port_report "terra: Fire 3 ...", "celes: Blizzard 1 ..." | — |
| C8 | Relm learns magic by level | change §3 Relm | PORTED | `ted_build.py:379-407` (spec 5) | — |
| C9 | Esper data: spells taught, MP costs, new espers (Titan, Odin, Leviathan, Asura, Bahamut, Diabolos, Ultima, ...) | change §2 "Summoning Eidolons"; Mato README | PORTED | port_report "learning: 177 rows changed (60 esper spells)"; docs/tedition.md:35 "espers (27, 181 learning rows)" | — |
| C10 | Trance: x1.5 damage, magic taken x2/3 | change §3 Terra | TESTED | teddamage "Fight by a Morphed character ... [40] ok" and "monster Fire on a Morphed character ... [10] ok" | — |
| C11 | Cyan: Bushido effects/accuracy (Tiger = MaxHP-HP; Snow/Moon/Flower) | change §3 Cyan | PARTIAL | effects through the spell data; no Bushido rename in the port's text (`port_spells.py:242-246` renames only on a changed display name) | carry the renames and descriptions [lead] |
| C12 | Cyan: Bushido gauge fills faster | change §3 Cyan | MISSING | spec 62 "not located" | locate the gauge speed (C1), hook the PR's charge [TedPlugin] |
| C13 | Shadow: Interceptor blocks 2/3, one fixed counter (Twin Fang) | change §3 Shadow | PORTED | `TedCommands.cs:284-313` (spec 38) | — |
| C14 | Shadow never leaves at random | change §3 Shadow | PORTED | `TedVictory.cs:118-128` (spec 58) | — |
| C15 | Shadow: ninja swords dual-wield, scroll changes, Throw without its built-in x2 | change §3 Shadow; spec 42 | PARTIAL | swords/scrolls through the item data; Throw's x2 removal not implemented (spec 42 deferred) | Throw damage hook [TedPlugin] |
| C16 | Edgar: Tools changed (Particle Bomb new, Debilitator gone, Air Anchor inflicts Heat, single/all target) | change §3 Edgar | PARTIAL | port_report "tools: 7 tool items changed (power/hit only)"; Particle Bomb in `ted_items.json` slot 167 | Air Anchor's Heat and targeting [lead] |
| C17 | Sabin: Blitz changes (Tiger Rush, Phantom Rush physical, Chakra cures Poison) | change §3 Sabin | PARTIAL | names MSG_MAGIC_NAME_115/116; port_report "physical spells: 10 damage functions switched"; Tiger Rush's 3 hits = M39 | see M39 [lead] |
| C18 | Celes: Runic speed changed | change §3 Celes | MISSING | spec 62 "not located" | locate and port [TedPlugin] |
| C19 | Strago: Lores replaced (Mind Blast, Magic Hammer, Ancient Prayer) and retuned | change §3 Strago | PORTED | MSG_MAGIC_NAME_119/135/137 in the port's text | — |
| C20 | Relm: Sketch with Relm's stats, 75% move / 25% Wishing Star, works without a brush, brushes raise odds | change §3 Relm | PARTIAL | sketch table (port_report "sketch 349 monsters"), Wishing Star MSG_MAGIC_NAME_178; stat source and brush odds (spec 30) "likely already the PR's", unconfirmed, no code | check in game; hook the hit odds [TedPlugin] |
| C21 | Relm: Control removed | change §3 Relm; spec 32 | PORTED | `ted_build.py:221-239` (command slot 19 is Snowstorm) | — |
| C22 | Setzer: Slots retuned; Mysidian Bunny Lv x power, not split | change §3 Setzer | PORTED | `TedDamage.cs:198-213` (spec 37); teddamage flags "Mysidian Rabbit ... (CHECK: the game's split isn't 1/n)" | — |
| C23 | Mog: Dance always works, one dance per turn | change §3 Mog | PARTIAL | one dance per command: `TedCommands.cs:55-56, 183-197`; the PR's 50% stumble off-terrain stays (`tools/port_dances.py:5`, no `dance_rules` in `profile_tedition.py`) | no-stumble dance groups (a dance_rules mode) [lead] |
| C24 | Gau: Fight instead of Leap (ends the Shadow/Leap crash) | change §3 Gau; readme.html §6 | PORTED | `ted_build.py:224` (Leap slot = Animal); spec 63 | — |
| C25 | Gau learns Rages from any won battle | change §3 Gau | PORTED | `TedVictory.cs:12-15, 65-80` (spec 34) | — |
| C26 | Gau equips weapons (Rages keep his weapon) | change §3 Gau; Readme A7 | PARTIAL | equip lists in job_group (port_report); Rage animations with his own weapon not handled | Rage weapon graphic [TedPlugin] |
| C27 | Gogo and Umaro equip espers and learn magic | change §3; 3.0.0 | PORTED | `TedMagicite.cs:8-66`; ted-7 log "rule 35: ... 3 checks hooked" | — |
| C28 | Umaro controllable, Snowstorm command, Berserker Ring / Power Belt procs on Fight | change §3 Umaro | PARTIAL | Snowstorm command (`ted_build.py:230`); procs as attack odds (`TedCommands.cs:48-83`); the PR's auto-act (ActSelectUmalo) is never dropped (spec 36/56) | Umaro's command menu [TedPlugin] |
| C29 | Magitek: six options for every character | change §3 "Character Overview"; spec 61 | MISSING | no data or code; kit SnesMagitek not applied | per-character Magitek list [TedPlugin] |
| C30 | Veldt holds formations up to 511 | change §2 "Registering Monster Formations to the Veldt" | PORTED | `profile_tedition.py:623`; port_report "veldt: 511 formations in 64 groups" | — |
| C31 | Dispel and Vanish usable outside battle | history ("You can now use Dispel and Vanish in the field") | MISSING | the spell porter keeps the template's field use (`port_spells.py:236-237`) | menu use for the two spells [lead] |

### Monsters/formations/AI

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| B1 | New monsters (94) and formations past 576 | change §6 "Monster Changes" | TESTED | ted-monsters "battle 30723 started" ... "battle 30696 started"; shot `shots/ted_mon_30723.png` (Seraph in battle); log "monster 1472 uses ability [197]" | — |
| B2 | Monster stats, resistances, statuses, EXP (WoR EXP up) | change §6; 2.9.6 | PORTED | port_report "monster: 370 changed", "enemy resistances" | — |
| B3 | Monster special attacks | monsterspecial.txt | PORTED | port_report "monster special attacks: 353" | — |
| B4 | Steal and drop contents | scanstealdata.html; stealdropragworthit.txt | PORTED | porter (docs/tedition.md:36 "steals/drops (291)") | — |
| B5 | Monster AI on T-Edition's own scripts | change §6; history (boss behaviours) | PARTIAL | port_report "own script in the plugin: 309 ... boss (kept PR script): 46"; script status effects off (`Plugin.cs:89-92`, `profile_tedition.py:616`); ted-monsters KeyNotFoundException in GetMagicStatus | bring the 46 bosses onto T-Edition's scripts; test status effects; fix the exception [TedPlugin] |
| B6 | Formations and encounter packs (world, dungeons, Gogo's cave none) | worldmap.txt; history | PORTED | port_report "encounters: {'new parties': 337 ...}" | — |
| B7 | Metamorph (Ragnarok) sets | ragnarok.txt | PORTED | port_report "metamorph: ..." | — |
| B8 | Formation AP and escape flags (Ninja, Don runnable) | 3.0.0 notes | PORTED | port_report "monster_party AP: 111", "escape: 25 parties changed" | — |
| B9 | Kefka's Tower: new boss, new fixed battles, Number 024/128/Air Force on the Veldt | history | PARTIAL | formations through the porter; tower events (maps 334/354/355) scripted with 6-21% stubs, CA/0300 unscripted | wire CA/0300; play the fights [ted-ex] |

### Maps

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| P1 | T-Edition's relocated map tables (511 maps) read | For Producers/address changes | PORTED | `tools/ted_maps.py read`, `build/t-edition/ted_map_tables.json` | — |
| P2 | New maps (94) as PR maps | Mato README (new locations); history | TESTED | `data/ted_maps.json` (94 maps); maps-2 warped into 724, 697, 691; shot `shots/maps2/room_724.png` renders | walk them through doors [ted-maps] |
| P3 | Doors and world-map entrances into new maps | history ("new house north of Narshe", Phantom Forest WoR) | PORTED | `ted_maps.json` "into": 22 exits incl. Map_10010/Map_10020 | — |
| P4 | Chests on new maps (70) | history | PORTED | progress 11-20 "all 70 chests (flags 300-369)" | — |
| P5 | Random battles on new maps | history | PORTED | `ted_maps.json` random_battles; port_report "39 new maps with random battles on 27 packs" | — |
| P6 | Map names for new places | history ("Added some new map names") | TESTED | `room_724.png` title "South Figaro – Music Room" (TEDMAP_NAME keys) | — |
| P7 | Tile edits on vanilla maps (walkability) | history | PORTED | `TedTiles.cs:169-244`, `data/ted_tile_cells.json` | — |
| P8 | T-Edition's own tilesets/graphics sets (82-85, edited sets 5, 6, 19-22, 53) | MEDIA_INVENTORY §4.2 | PARTIAL | new maps use look-alike PR rooms ("neither converts T-Edition's own tile art") | PR tiles where a look-alike is wrong after a walk-through [bc-sprites] |
| P9 | Vanilla maps paired with PR rooms | (port need) | PARTIAL | progress 11-21 "337 of 416 vanilla maps paired (36 events without a spot)" | pair the rest [ted-maps] |

### Events/story scenes

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| E1 | Narshe defense: new scene when Cyan meets Kefka | change §7 | MISSING | CC/BC96 (map 22) in the catalog, no script | wire it [ted-events] |
| E2 | Night in Albrook: find Celes | change §7; Mato README | PARTIAL | CD/3DC0 (map 330) scripted, 0% stubs; the Celes search not traced | trace and wire the rest [ted-events] |
| E3 | Fewer fish to save Cid | change §7 | PARTIAL | CA/5366 scripted (12% stubs); CD/4300 unscripted | [ted-ex] |
| E4 | Sabin's new lines at Gerad | change §7 | MISSING | CA/91D0 (map 169) not scripted | build and wire CA/91D0 [ted-events] |
| E5 | Valigarmanda (WoR) needs Terra | change §7; readme.html §7 | MISSING | CC/370F (map 35) not scripted | build and wire CC/370F (also blocks Test of Strength's last step) [ted-events] |
| E6 | Cyan's Dream: new solo battles, throne after the memories | change §7; readme.html §7 | PARTIAL | CD/4000, CD/4003 scripted (~19% stubs); CD/3FE0 (map 126), CD/4002 not | [ted-events] |
| E7 | New Kefka battle on the Floating Continent | readme.html §7; Mato README | MISSING | no wired event found (CA/5A0C, map 10, unscripted) | find and wire [ted-events] |
| E8 | Shadow always gets off the Floating Continent | change §3 Shadow | MISSING | not located in the catalog | [ted-events] |
| E9 | WoR Figaro cave: collapsed soldier heals for free | readme.html §7 | MISSING | not located | [ted-events] |
| E10 | Water's Harmony learnable in the WoR | change §3 Mog | PARTIAL | Underwater Cave (map 481) events scripted, 28% stubs | [ted-maps] |
| E11 | Final battle: Gogo/Umaro lines, party select | history | PARTIAL | map 12: CA/3F2B/3F3B/3F73 scripted, CA/3F13, CD/15E0 not | [ted-events] |
| E12 | New merchants (Phantom Train ghost, Doma, Esper Village, Mobliz, Fanatics' Tower, Narshe WoR) | history 3.0.0 and earlier | PARTIAL | `TedSysCalls.cs:47-58` TED:shop; used in 59 script files of mods/TEdition; not run | play one shop [ted-events] |
| E13 | Beginner's House tutors rewritten, advanced-info NPC | readme translation; history | PARTIAL | maps 104-107 talk events scripted with 0 stubs; CD/4C79, CD/4B62 not | [ted-events] |
| E14 | Perfect banquet score (Ribbon, achievement) | Quick Advice; 3.0.0 | PARTIAL | CC/91B6 (map 250) scripted, 16% stubs | [ted-ex] |
| E15 | Ruby's Shine | spoiler_free_new_quests; Mato README | PARTIAL | 5/5 events scripted, 20% stubs (`snes_event_ted_readme.json`) | [ted-events] |
| E16 | Test of Strength | same | PARTIAL | 9/11 scripted, 21% stubs | [ted-events] |
| E17 | Stolen Magicite (Catoblepas; Carbuncle in WoR) | same; 2.9.5 | PARTIAL | 1/1 scripted, 11% stubs | [ted-ex] |
| E18 | Deep Earth Dweller (Sealed Gate staircase) | same | MISSING | `snes_event_ted_readme.json` lists no events for it | find its events, translate [ted-events] |
| E19 | Gilgamesh: Encounter, Reunion, Battle on the Big Bridge? | same | PARTIAL | 4/4 scripted, 23% stubs | [ted-events] |
| E20 | Return of the Narshe Residents (refugees, Ragnarok, shops, new pub) | same | PARTIAL | Narshe NPC events partly scripted (CD/1540, CD/1650 yes; CD/1E40 no); no per-quest mapping | map the quest's events and wire [ted-events] |
| E21 | Seeking the Legendary Weapon (Ragnarok sword, Omega Weapon) | same | PARTIAL | CC/FF90 (map 401) scripted, 24% stubs | [ted-ex] |
| E22 | The Giant Titan | same | PARTIAL | 1/1 scripted, 23% stubs | [ted-events] |
| E23 | Descendants of the Summoners (Mist Dragon) | same | PARTIAL | 9/15 scripted, 32% stubs | [ted-events] |
| E24 | The War God Odin (Zantetsuken) | same | PARTIAL | 7/7 scripted, 12% stubs | [ted-ex] |
| E25 | The Great Ocean King (Leviathan) | same | PARTIAL | 4/5 scripted, 14% stubs; CA/55DF not | [ted-ex] |
| E26 | Eternal Love (Asura) | same | PARTIAL | 1/1 scripted, 21% stubs | [ted-ex] |
| E27 | King of the Dragons: 8 dragons (Yellow/Skull moved, Holy Dragon after Omniscient, Red Dragon fight) -> Bahamut | same; readme.html §7 | PARTIAL | 27/37 scripted, 32% stubs; CC/36D5 "7 dragons remaining" (map 34) not | [ted-ex] |
| E28 | Waking Dreams (Diabolos) | same | PARTIAL | 1/1 scripted, 25% stubs | [ted-events] |
| E29 | The Sealed Legend (12 sealed weapons, 4 crystal guardians) | same | PARTIAL | 43/45 scripted, 25% stubs; CD/2930 "The crystal's guardian attacks!" not | [ted-ex] |
| E30 | Father and Daughter (Shadow's dreams) / A Mother's Hope | same | PARTIAL | 7/7 scripted, 25% stubs; Shadow's dream inn scenes CA/788A, CA/F644, CC/6649, CA/8EDB (2,100+ commands each) not scripted | [ted-events] |
| E31 | Mysterious Technique Inheritance (Sabin's last Blitz) | same | PARTIAL | 2/3 scripted, 9% stubs; CC/0BCE not | [ted-events] |
| E32 | A Demon's Favorite Food / Gau's father opens every Veldt formation | same; change §7 "Gau's Make-over" | PARTIAL | 1/2 scripted, 29% stubs; CB/681E not; `TED:veldt_open` (`TedSysCalls.cs:75-82`) used by no script | [ted-events] |
| E33 | Thoughts and Wishes (Cid, Celes) | same | MISSING | no catalog events identified | find and translate [ted-ex] |
| E34 | Owzer's Collection | same | PARTIAL | 5/5 scripted, 28% stubs | [ted-ex] |
| E35 | Unexpected Special Skill (Umaro's carving) | same | MISSING | no catalog events identified | [ted-ex] |
| E36 | The Last Dragon (Fanatics' Tower, Dried Meat) | same | PARTIAL | CD/46B0 (map 364) scripted, 21% stubs | [ted-ex] |
| E37 | Molulu's Gift | same | PARTIAL | 3/3 scripted, 20% stubs | [ted-ex] |
| E38 | A Priestess's Concern (Sabin costume) | same | MISSING | CA/6C7B (map 57) not scripted | build and wire CA/6C7B with the costume unlock [ted-events] |
| E39 | A Mother's Love (Terra costume, Maduin's house) | same | PARTIAL | CD/7D60, CD/7DD0 (map 468) scripted, 25% stubs | [ted-maps] |
| E40 | A Duel! The Dragon's Neck Coliseum (Gilgamesh, Excalibur) | same | PARTIAL | 5/5 scripted, 29% stubs | [ted-ex] |
| E41 | Forever Ultros (help in Kefka's Tower) | same | PORTED | 7/7 scripted, 9% stubs | — |
| E42 | The Sealed Gate, Again (esper fight, elder, Terra's gear) | same | PARTIAL | maps 435 (50% stubs), 437 (10%), 438 (24%) | [ted-maps] |
| E43 | Wandering Shadow (WoR Floating Continent, Atma Buster) | same | PARTIAL | map 509: 23/24 events scripted, 22% stubs | [ted-maps] |
| E44 | Know-It-All, the house north of Narshe | Mato README "Know-It-All"; history | PARTIAL | likely map 510 "Mr. Clio's Home" (WoR door at 111,15): built, no NPCs placed, its entrance event unchecked | confirm the map, place him [ted-maps] |

### Pub quests

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| Q1 | Pub job boards (6 pubs) | Mato README "NEW PUB QUEST DETAILS" | PARTIAL | `tools/ted_quests.py` BATCH wired; ted-7 ted-quests: "sc_tedq_q_ca7d09_20071_4_d didn't start (not in map 42's list ...)" for 44 scripts | reinstall, rerun ted-quests [ted-ex] |
| Q2 | Cave Monster Cleanup (South Figaro, WoB) | same | PARTIAL | South Figaro pub 10/10 scripted, 13% stubs; maps 440-443 19-23% stubs | [ted-ex] |
| Q3 | Defend Mt. Kolts! | same | PARTIAL | South Figaro pub group (13% stubs) | [ted-ex] |
| Q4 | I'll Buy Anything! (Nikeah) | same | PARTIAL | Nikeah pub 9/10 scripted, 29% stubs; CD/3BD0 not | [ted-ex] |
| Q5 | A Helping Hand (Kohlingen) | same | PARTIAL | Kohlingen pub 7/8 scripted, 12% stubs; CC/6F41 not | [ted-ex] |
| Q6 | The Dream Opera | same | PARTIAL | Kohlingen group | [ted-ex] |
| Q7 | Requiem (Setzer's lines) | same | PARTIAL | Kohlingen group | [ted-ex] |
| Q8 | Transporting Goods (Albrook) | same | PORTED | Albrook pub 4/4 wired, 5% stubs (CC/6565 recipient) | — |
| Q9 | Finding Food (Albrook WoR, repeatable) | same | PORTED | Albrook group | — |
| Q10 | Wanted! Research Materials (scholar, Goddess Bell) | same | PARTIAL | Albrook group; needs the Goddess Bell of N4 | [ted-ex] |
| Q11 | Defeat the Cave Monsters (South Figaro WoR, repeatable) | same | PARTIAL | South Figaro group | [ted-ex] |
| Q12 | A Girl's Wish | same | PARTIAL | South Figaro group | [ted-ex] |
| Q13 | Victory Drinks | same | PARTIAL | South Figaro group | [ted-ex] |
| Q14 | Delivery Service (Nikeah, Duane) | same | PARTIAL | CD/5BA0 12%, CD/5C60 14% stubs | [ted-ex] |
| Q15 | A Dancer's Depression (opens the Dressing Room) | same | PARTIAL | CA/8FFF scripted, 17% stubs | [ted-ex] |
| Q16 | The Will to Live for Tomorrow (Phantom Forest foe) | same | PARTIAL | Nikeah group; Phantom Forest maps 447-451 22-23% stubs | [ted-ex] |
| Q17 | A Restful Sleep (Kohlingen, Darill's grave) | same | PARTIAL | CE/0480 17% stubs; map 439 16% | [ted-ex] |
| Q18 | Imitation's Secret (Narshe pub, Gogo's quiz) | same | PARTIAL | Narshe pub map 461 5/5 scripted, 9% stubs; quiz flow uses stubbed case tests (175 `SNES:case_test` in mods/TEdition) | [ted-ex] |
| Q19 | Night Patrol (timed, repeatable, reward changes) | same | PARTIAL | maps 473-476 scripted, 8-23% stubs; `SNES:timer_start` 6, `SNES:timer_reset` 14 stubs remain | a field timer SysCall [TedPlugin] |
| Q20 | Super Doctor D (Zozo) | same | PARTIAL | Zozo pub 2/2 scripted, 44% stubs | [ted-ex] |

### NG+/post-game

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| N1 | New Game+ from the Beginner's House desk | change §1 "New Game+"; Mato README | MISSING | `tools/ted_events.py:20, 64-72` decodes command CB on map 104 as "story_reset"; no PR implementation, no SysCall, no script uses it; only its description text is ported (`story_mes_en.txt` TED_E0085) | NG+ in TedPlugin (reset flags, keep the carry-overs) and the clerk's event [TedPlugin] |
| N2 | NG+ carry-overs (items but key items, spells, espers, Lores/Rages/Dances, playtime, steps, success counters, achievements) | change §1 | MISSING | counters exist (`TedCommands.cs:316-373`) but nothing carries them | [TedPlugin] |
| N3 | NG+ resets (formations met, pub quests, chests, Trance time, Terra's Trance, Deathgaze, Dried Meat; secret costumes re-lock) | change §1; Mato README | MISSING | no code | [TedPlugin] |
| N4 | Holy Angel Ultima chain (page, sylph, Phantom Forest, Matoya's Crystal Eye, Goddess Bell, Labyrinth of the Ancients, Crystal Tower, Ultima) | Mato README "High Seraph Ultima" | PARTIAL | maps 447-458, 417-420, 497-505 built; their events 9-66% stubs (499: 57%, 504: 66%); the Goddess Bell airship landing not located | translate the rest; the landing [ted-maps] |
| N5 | Forbidden Land Eureka (optional, gear) | same | PARTIAL | maps 421-428 built; events 9-71% stubs | [ted-maps] |
| N6 | Soul Shrine (waves, re-fight chosen waves, shield on first clear, restart if left, save point, party change) | Mato README; soulshrine.txt | PARTIAL | maps 431-433; CD/12D0-CD/1340 scripted, 24-29% stubs | [ted-maps] |
| N7 | Developer's Room (after Ultima; lead-dependent reactions) | Mato README "Developer's Room" | PARTIAL | maps 463/464 15%/26% stubs, 465 11%; script ids >= 10000 run (maps-2) but room 697's Namingway script never ended | fix the hang; finish stubs [ted-maps] |
| N8 | Secret Present (Eureka gravestone unlocks every costume) | Mato README "Secret Present" | PARTIAL | map 494 "Secret Room" 36% stubs; Eureka events up to 71% stubs | [ted-maps] |

### Costumes/dressing room

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| D1 | Dressing Room on the Falcon | change §3 "Dressing Room"; dressroom.html | PARTIAL | map 459 built (35% stubs); `TedSysCalls.cs:103-104` TED:costume -> `TedCostumes.Wear` | finish the room's scripts; play it [ted-maps] |
| D2 | 56 costumes: field, battle and portrait art | dressroom.html; 3.0.7 menu images | PORTED | `tools/ted_art.py` costumes, `data/ted_costume_art.json`; ArtSwap layers (`Plugin.cs:55-59`) | — |
| D3 | Costume choice kept in the save | (system) | PORTED | `TedCostumes.cs:10-24` ("TEC1" block) | — |
| D4 | Unlocks by treasures, events, achievements (in order) | dressroom.html; Quick Advice | PARTIAL | unlocks listed in `data/ted_costumes.json`; achievements are U2 | [ted-maps] |
| D5 | "The Best Models": change clothes at 12 inns and halls | change §1 "New Game+" list | PARTIAL | TED:costume in inn scripts sc_tedq_e_cb4486 (Map_20151_5, 20191_2, 20331_2, 20431_5), sc_tedq_e_cc657d, sc_tedq_e_cc6140; not run | [ted-ex] |
| D6 | Falcon music by worn costume (53 songs) | dressroom.html; history | MISSING | PORTING.md music row "left: the Falcon's costume songs"; MEDIA_PLAN "the table isn't found yet" | find the table; a costume-to-bgm rule [TedPlugin] |
| D7 | Job title follows the costume | EX history ("changing costumes now changes job titles") | MISSING | no code | [TedPlugin] |
| D8 | Gogo's Chameleon Robe takes other characters' forms in battle | EX history | PORTED | `TedCostumes.cs:16-17` (10 forms) | — |
| D9 | Imp's Feelings / Piggy's Badge cosmetic relics | history ("2 new accessories") | PORTED | `TedCostumes.cs:17-18` (slots 277/278) | — |
| D10 | Costume stat bonuses | 2.9.x; removed in 3.0.0 | LEFT OUT | BATTLE_SPEC "Docs vs code": "The costume system changes graphics only ... Port nothing from it" (3.0.0 removed stats) | — |

### Music

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| S1 | ~200 new songs (two drivers, own samples) | change §1 "Added Music"; bgm.html | PORTED | `tools/ted_music.py`, `TedMusic.cs:15-56`; ted-7 "[ted music] 254 songs, 145 samples, 344 tracks, 191 areas, 478 battles" (loaded, not heard) | — |
| S2 | Area songs (66 new maps, 55 vanilla maps) | bgm.html | PARTIAL | `ted_music.map_rules`; PORTING.md "7 vanilla maps lack a PR room in the kit's table" | the 7 rooms [ted-maps] |
| S3 | Battle music per formation | change §1 "Battle Music - Fanfare Change" | PORTED | `ted_music.formation_music` (478 parties) | — |
| S4 | Victory fanfare per formation | same | PORTED | same (418 fanfares) | — |
| S5 | Songs and jingles in events | bgm.html | PARTIAL | translator emits bgm 1000+n; stubs left in mods/TEdition: `SNES:song_ctrl` 19, `SNES:song` 9, `SNES:sound_wait` 20 | [ted-events] |
| S6 | Music Player in Config > Sound (GBA-style), its 277 entries | change §1 "Music Player" | PARTIAL | `ted_music.player_rows` writes player.json; no sound_player_list.csv in mods/TEdition; PORTING.md "left: ... the music player's hookup" | install the rows (or a Config player) [TedPlugin] |
| S7 | Developer's Room music room: extra songs, patrons who comment on the song playing | Mato README | PARTIAL | map 485 (38% stubs); Hummingway's offer ran in game (maps-2 shot `sc_tedm_03FAA5_1.png`); "what is playing" check not located | a SysCall for the current song [TedPlugin] |
| S8 | Battle sound effects changed (FF5 Bio, whip, Time magic) | EX history | MISSING | no battle SE work found (`data/ted_se_ties.json` is field events only) | [TedPlugin] |

### Graphics

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| G1 | New monster sprites (incl. EX's) | change §6 "Monster Changes" | TESTED | ted-7 "[ted] monster images: made 226 of 226 (+226 bestiary thumbnails) from this game"; shot `ted_mon_30723.png` | — |
| G2 | Monster recolors and redraws in the vanilla range (52 recolors, 76 redrawn) | change §6 "Palette Changes" | PORTED | progress 11-20 (`tools/ted_art.py`: 174 new, 52 recolors, 15 swaps) | — |
| G3 | Characters redrawn to match official art (field, battle) | change §3 "Character Overview"; 2.9.5 | PORTED | `TedArt.cs:39` BaseLooks; ted-7 "[ted art] base looks: ... 833 sprites, 15 atlases" (loaded) | — |
| G4 | Default portraits redrawn | 3.0.0 | PORTED | `ted_art.py:284-317, 433` | — |
| G5 | Imp (toad) look, Mog's new pose | EX history | PORTED | progress 11-20 "the Imp, Kappa and Pig looks"; "Mog's 'new pose' is redrawn tiles only" | — |
| G6 | NPC sprites on the new maps (112 numbers) | MEDIA_INVENTORY §4.1 | PARTIAL | 72 of 112 with a PR look (`data/ted_npc_looks.json`), 40 on stand-ins (`data/ted_npc_standins.json`) | 40 new NPC sprites [bc-sprites] |
| G7 | NPC and story sprites changed on vanilla maps (Kefka, Gilgamesh, Yura, Arvis, Jun) | 2.9.5; EX history | PARTIAL | stand-ins listed in `ted_npc_standins.json` | [bc-sprites] |
| G8 | New and edited battle backgrounds (Crystal Room, Phoenix Cave fire, WoR variants ...) | background.html; 3.0.0 | MISSING | MEDIA_INVENTORY §4.3: "which ones: unknown until the table is decoded"; no PR asset past 58 | decode E6/F800, make PR backgrounds [bc-sprites] |
| G9 | Collection Room paintings | Mato README "Collection Room"; history | MISSING | MEDIA_INVENTORY §4.4 "I found no separate image table ... unknown" | [bc-sprites] |
| G10 | Animations for new/changed spells (Blink, Flood, Comet, Toad, Holy's new graphic ...) | change §2 "Magic"; 3.0.0 | PARTIAL | port_report "spells using their own slot's look (no name match): 10:Toad, 19:Flood, 20:Scourge, ... 32:Comet, 50:Blink ..." | pick PR effects per spell [lead] |
| G11 | Casting motions (White, Summon), Time magic animation and sound, Trance casting, Cyan's battle entry | change §2 "Magic Casting Motions"; §3 | MISSING | no code | [TedPlugin] |
| G12 | MP damage in pink, MP healing in blue | change §2 "MP Damage/Recovery Display" | MISSING | no code | number colour hook [TedPlugin] |
| G13 | Window types 2-8 after other Square games | change §1 "Window Type"; windowtype.html | MISSING | no code (MEDIA_INVENTORY §4.4 "not examined") | decide: PR window skins or leave out [lead] |
| G14 | Weapon and item icons/battle sprites changed | EX history | PARTIAL | item identity: new rows take a template item's look (port_report "48 rows took their template's look") | [bc-sprites] |

### Menus/UI/rooms (Collection, Achievements, Track Record)

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| U1 | Collection Room (key items on display, paintings per EX boss) | Mato README "Collection Room" | PARTIAL | maps 470, 486, 487-490 built; events 29-71% stubs (470: 71%); EX bits allocated (MEDIA_INVENTORY §4.4) | [ted-maps] |
| U2 | Achievement Room: 2 rooms, hint books, 20 achievements, finale | Mato README "Achievement Room"; spoiler_free_new_quests | PARTIAL | maps 471/472 58%/60% stubs; 21 `SNES:word_cmp` stubs; no script uses `TED:counter` (`TedSysCalls.cs:83-91`) | counter/playtime/step compares as SysCalls [ted-maps] |
| U3 | Track record: Steal, Twin Fang, Runic, Sketch, Slot, Snowstorm, Mimic counts | change §1 (NG+ list); spec 43 | PARTIAL | `TedCommands.cs:57-60, 168-178, 316-373`; Twin Fang is never bumped | bump on Interceptor's counter [TedPlugin] |
| U4 | Status screen pages: attributes, conditions, abilities | change §2 "Information Display on the Status Screen" | MISSING | no code | [TedPlugin] |
| U5 | Equipment details: MP Critical, absorb, Row OK, Throw OK, bonus vs flying/human/magic/dragon; Valiant Knife "???" | change §1 "Equipment Details Menu"; §5 | MISSING | no code | [TedPlugin] |
| U6 | X button: equipped esper, learning progress, mastered-esper star | change §1 "Magic Acquisition Status" | MISSING | no code | [TedPlugin] |
| U7 | Select in battle: icons for Reraise, Defend, Runic, Sky, Charm, Love Token, Cloudy Heaven | change §2 "Information Display of Status Ailments of Allies" | MISSING | no code | [TedPlugin] |
| U8 | Play time past 99:59 | change §1 "3 Digit Playtime" | MISSING | not checked on the PR, no code | check the PR's clock; hook if it stops [TedPlugin] |
| U9 | Treasure message depends on the party lead | change §1 "Treasure Chest Message" | MISSING | no code | [TedPlugin] |
| U10 | Rage list in alphabetical order | change §3 Gau | MISSING | no code | [TedPlugin] |
| U11 | Hidden debug win (Select+Up) | spec 59 | LEFT OUT | spec 59 "do not port" | — |

### Text/translation

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| T1 | Full English names (items, spells, monsters, attacks) | Mato README FAQ | PORTED | `docs/tedition.md:29-31`; port_report "item text: 223 names/descriptions" | — |
| T2 | Descriptions for every item (GBA-style) | change §1 "Item Descriptions" | PORTED | progress 11-20 (Mato's descriptions); 327 MSG_*_INF rows in TEditionPort | — |
| T3 | Spell and Lore descriptions (19 characters) | change §1 "Magic Skill Description" | PORTED | MSG_MAG_INF rows (63) | — |
| T4 | Blitz, Bushido, esper and Rage descriptions (Rage menu shows the attack) | change §3 Gau; EX history | MISSING | PORTING.md Text row "Blitz, Bushido, espers and rages not yet" | read 40/0E00, CF/FF9E, CF/FFAE [lead] |
| T5 | Mato's dialogue in new and changed scenes | Mato README FAQ | TESTED | maps-2: "Hummingway: Want to hear music not in the Music Player?" with Yes!/No! (`shots/maps2/sc_tedm_03FAA5_1.png`); Namingway (`sc_tedm_037370_1.png`) | coverage follows the event rows |
| T6 | Element names Fire / Earth / Darkness / Light | change §1 "Attribute Names" | MISSING | no rename found in the port's text or tools | [lead] |
| T7 | Job titles (Mog "Moogle Knight", others) | change §3 Mog; EX history | MISSING | not in the port's text | [lead] |
| T8 | Monster battle lines and battle messages | (AI F3) | PARTIAL | port_report "35 battle lines as the PR's text, 1 of our own, no line for messages [4, 9, 11, ...]" | [TedPlugin] |
| T9 | English Lua translation layer | Lua readme | LEFT OUT | emulator-only (snes9x-rr Lua); the port uses Mato's text | — |
| T10 | Added kanji and fonts | change §1 "Additional Kanji" | LEFT OUT | Japanese ROM font; the PR has its own fonts | — |

### EX

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| X1 | EX boss room behind the Mog House door, in the same game | EX readme.html §2 | PORTED | `docs/tedition.md:125` decision; map 467 (0% stubs); `data/ted_ex_maps.json` | — |
| X2 | The Moogle's 12 super-boss fights | EX readme.html §1; EX_PLAN table | PORTED | `data/ted_ex_scripts.json` (sc_tedx_moogle, _b1.._b13); parties 30768-30792 | — |
| X3 | EX bosses' AI (own 31 attacks, form changes) | EX history | PORTED | `tools/ted_ex_ai.py`; `TedEnemyAi.cs:42` (ted_ex_ai.json) | — |
| X4 | EX bosses' sprites | EX history | PORTED | 26 EX images in the 226 (G1) | — |
| X5 | EX boss songs | EX readme.html §1 | PORTED | PORTING.md music row "EX's 13 fights" | — |
| X6 | EX boss battle backgrounds | EX_PLAN ("4D command") | PORTED | port_report "event parties on the event's background" | — |
| X7 | EX shops (two shopkeepers) | EX readme.html §2 | PORTED | `tools/ted_ex_events.py` SHOPS {107: 128, 108: 129} | — |
| X8 | Wins fill the Collection Room and count for "EX Complete" | EX readme.html §3 | PARTIAL | win bits allocated; paintings art missing (G9); Collection Room events 41% stubs (map 469) | [ted-ex] |
| X9 | Omega Weapon as a 13th fight with Mato's reward (steal Megalixir, drop Omega Weapon) | Hidden Secret Boss info | PORTED | `ted_ex_events.py` EX_PATCH (pack 168); EX_PLAN line 1 decision | — |
| X10 | EX room's Moogle: party and costume changes | EX readme.html §2 | PARTIAL | map 467 NPCs (2 events, 0% stubs); party/costume menu not traced | trace and test [ted-ex] |
| X11 | Dragon's Den dungeon | Hidden Secret Boss info | LEFT OUT | `docs/tedition.md:125` "leave the Dragon's Den out" (user, 2026-11-20) | — |
| X12 | Save swap between two ROMs | EX readme.html §2 | LEFT OUT | `docs/tedition.md:84-85` one mod, "no save swap" | — |
| X13 | EX's own item set switch ($1440) and its broken leftovers (garbage randoms, flame NPC crash) | EX_PLAN | LEFT OUT | `pr/ted/EX_PLAN.md:158, 171-179` "not replicated" | — |

### Platform patches (outside the game)

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| O1 | MSU-1 audio | MSU-1 Setup | LEFT OUT | SNES/emulator hardware feature; the PR plays its own audio | — |
| O2 | 4-player multitap | 4-Player Multitap Patch | LEFT OUT | SNES controller hardware | — |
| O3 | Lua QoL scripts (bestiary, enemy status viewer, forced encounters) | Lua readme | LEFT OUT | snes9x-rr only; the PR has its own bestiary and Libra | — |
| O4 | Music fix patch / echo-buffer setting | Optional Patches | LEFT OUT | emulator audio-RAM workaround; songs play on the kit's player | — |

Not counted (optional add-on patches shipped beside 3.0.7, not part of it): rage_fix, Simple Blitz, long spell names,
Bushido rename, Default Portrait Remaster, the 3 extra window patches, 2.9.7 costume-stat patches, JP achievement-fix
patches, new Narshe icon. Alternative Omega Weapon steal/drop is X9.

## 4. Missing work

Every MISSING and PARTIAL row above, as a work item, by owner.

### TedPlugin (45)

- **M5** (PARTIAL) Blind lowers hit rate (vanilla bug fixed): probe the PR's blind penalty; if not a halving, use a kit BlindRules variant
- **M9** (MISSING) Back/pincer/side attack odds fix; Back Guard (Alarm Earring) stronger: encounter-type hook (kit SnesEncounterRules) reading T-Edition's relic bits
- **M10** (MISSING) Pre-emptive strike chance doubled, Gale Hairpin x4: same hook as M9
- **M15** (MISSING) Equipment statuses win over Ribbon (Cursed Shield stays cursed): status-set hook keeping equipment statuses through immunity
- **M17** (PARTIAL) "Critical Health" element: percent spells only inflict Near Fatal; Near-Fatal-immune monsters dodge them: check the PR misses on Near-Fatal-immune monsters; else a hook
- **M29** (PARTIAL) Reflected magic not halved (3+ reflectors out-damage one hit): probe a reflected spell in game; hook if the PR halves
- **M30** (PARTIAL) Damage/heal cap 32000, 5-digit display: check a 5-digit hit on screen
- **M31** (MISSING) Desperation attacks: easier (code 1/32), unlimited, no 768 timer, new ones for Gau/Umaro, blocked by Offering: trigger hook + Gau/Umaro/Gogo desperation abilities
- **M34** (MISSING) Master's Scroll/Offering: normal accuracy, no procs or desperation: locate in C1/C2, then hook
- **M38** (MISSING) Golem/Interceptor blocker defense 119: dog/golem block hook
- **M40** (PARTIAL) Coliseum fights under the player's control: test in game, then default on
- **M42** (PARTIAL) Gil Toss: Lv x180 gil, Lv x90 to every target; monsters' own rule: apply the monster rule; verify cost and damage in game
- **M43** (MISSING) Psycho Cyan bugs (Retort flag after death; Imp) fixed: probe the PR; hook if the flag survives death
- **I3** (PARTIAL) Weapon properties: MP Critical, HP/MP absorb, Row OK, throwable, bonus vs flying/human/magic/dragon: the listed weapons in TedPlugin
- **I5** (PARTIAL) Relic effects T-Edition re-coded (relic bits): decode each bit and implement (includes M9/M10's)
- **I12** (MISSING) Ultima Weapon's blade changes with damage (dagger/sword/great sword): weapon-sprite swap by computed damage
- **I18** (MISSING) WoR shop prices double until Humbaba falls: price hook on a story flag
- **C12** (MISSING) Cyan: Bushido gauge fills faster: locate the gauge speed (C1), hook the PR's charge
- **C15** (PARTIAL) Shadow: ninja swords dual-wield, scroll changes, Throw without its built-in x2: Throw damage hook
- **C18** (MISSING) Celes: Runic speed changed: locate and port
- **C20** (PARTIAL) Relm: Sketch with Relm's stats, 75% move / 25% Wishing Star, works without a brush, brushes raise odds: check in game; hook the hit odds
- **C26** (PARTIAL) Gau equips weapons (Rages keep his weapon): Rage weapon graphic
- **C28** (PARTIAL) Umaro controllable, Snowstorm command, Berserker Ring / Power Belt procs on Fight: Umaro's command menu
- **C29** (MISSING) Magitek: six options for every character: per-character Magitek list
- **B5** (PARTIAL) Monster AI on T-Edition's own scripts: bring the 46 bosses onto T-Edition's scripts; test status effects; fix the exception
- **Q19** (PARTIAL) Night Patrol (timed, repeatable, reward changes): a field timer SysCall
- **N1** (MISSING) New Game+ from the Beginner's House desk: NG+ in TedPlugin (reset flags, keep the carry-overs) and the clerk's event
- **N2** (MISSING) NG+ carry-overs (items but key items, spells, espers, Lores/Rages/Dances, playtime, steps, success counters, achievements): find its SNES events, translate and wire them, then play it
- **N3** (MISSING) NG+ resets (formations met, pub quests, chests, Trance time, Terra's Trance, Deathgaze, Dried Meat; secret costumes re-lock): find its SNES events, translate and wire them, then play it
- **D6** (MISSING) Falcon music by worn costume (53 songs): find the table; a costume-to-bgm rule
- **D7** (MISSING) Job title follows the costume: implement it, then test in game
- **S6** (PARTIAL) Music Player in Config > Sound (GBA-style), its 277 entries: install the rows (or a Config player)
- **S7** (PARTIAL) Developer's Room music room: extra songs, patrons who comment on the song playing: a SysCall for the current song
- **S8** (MISSING) Battle sound effects changed (FF5 Bio, whip, Time magic): implement it, then test in game
- **G11** (MISSING) Casting motions (White, Summon), Time magic animation and sound, Trance casting, Cyan's battle entry: implement it, then test in game
- **G12** (MISSING) MP damage in pink, MP healing in blue: number colour hook
- **U3** (PARTIAL) Track record: Steal, Twin Fang, Runic, Sketch, Slot, Snowstorm, Mimic counts: bump on Interceptor's counter
- **U4** (MISSING) Status screen pages: attributes, conditions, abilities: implement it, then test in game
- **U5** (MISSING) Equipment details: MP Critical, absorb, Row OK, Throw OK, bonus vs flying/human/magic/dragon; Valiant Knife "???": implement it, then test in game
- **U6** (MISSING) X button: equipped esper, learning progress, mastered-esper star: implement it, then test in game
- **U7** (MISSING) Select in battle: icons for Reraise, Defend, Runic, Sky, Charm, Love Token, Cloudy Heaven: implement it, then test in game
- **U8** (MISSING) Play time past 99:59: check the PR's clock; hook if it stops
- **U9** (MISSING) Treasure message depends on the party lead: implement it, then test in game
- **U10** (MISSING) Rage list in alphabetical order: implement it, then test in game
- **T8** (PARTIAL) Monster battle lines and battle messages: finish the part named in the evidence, then test in game

### ted-events (24)

- **E1** (MISSING) Narshe defense: new scene when Cyan meets Kefka: wire it
- **E2** (PARTIAL) Night in Albrook: find Celes: trace and wire the rest
- **E4** (MISSING) Sabin's new lines at Gerad: build and wire CA/91D0
- **E5** (MISSING) Valigarmanda (WoR) needs Terra: build and wire CC/370F (also blocks Test of Strength's last step)
- **E6** (PARTIAL) Cyan's Dream: new solo battles, throne after the memories: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E7** (MISSING) New Kefka battle on the Floating Continent: find and wire
- **E8** (MISSING) Shadow always gets off the Floating Continent: find its SNES events, translate and wire them, then play it
- **E9** (MISSING) WoR Figaro cave: collapsed soldier heals for free: find its SNES events, translate and wire them, then play it
- **E11** (PARTIAL) Final battle: Gogo/Umaro lines, party select: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E12** (PARTIAL) New merchants (Phantom Train ghost, Doma, Esper Village, Mobliz, Fanatics' Tower, Narshe WoR): play one shop
- **E13** (PARTIAL) Beginner's House tutors rewritten, advanced-info NPC: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E15** (PARTIAL) Ruby's Shine: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E16** (PARTIAL) Test of Strength: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E18** (MISSING) Deep Earth Dweller (Sealed Gate staircase): find its events, translate
- **E19** (PARTIAL) Gilgamesh: Encounter, Reunion, Battle on the Big Bridge?: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E20** (PARTIAL) Return of the Narshe Residents (refugees, Ragnarok, shops, new pub): map the quest's events and wire
- **E22** (PARTIAL) The Giant Titan: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E23** (PARTIAL) Descendants of the Summoners (Mist Dragon): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E28** (PARTIAL) Waking Dreams (Diabolos): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E30** (PARTIAL) Father and Daughter (Shadow's dreams) / A Mother's Hope: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E31** (PARTIAL) Mysterious Technique Inheritance (Sabin's last Blitz): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E32** (PARTIAL) A Demon's Favorite Food / Gau's father opens every Veldt formation: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E38** (MISSING) A Priestess's Concern (Sabin costume): build and wire CA/6C7B with the costume unlock
- **S5** (PARTIAL) Songs and jingles in events: finish the part named in the evidence, then test in game

### ted-ex (36)

- **B9** (PARTIAL) Kefka's Tower: new boss, new fixed battles, Number 024/128/Air Force on the Veldt: wire CA/0300; play the fights
- **E3** (PARTIAL) Fewer fish to save Cid: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E14** (PARTIAL) Perfect banquet score (Ribbon, achievement): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E17** (PARTIAL) Stolen Magicite (Catoblepas; Carbuncle in WoR): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E21** (PARTIAL) Seeking the Legendary Weapon (Ragnarok sword, Omega Weapon): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E24** (PARTIAL) The War God Odin (Zantetsuken): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E25** (PARTIAL) The Great Ocean King (Leviathan): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E26** (PARTIAL) Eternal Love (Asura): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E27** (PARTIAL) King of the Dragons: 8 dragons (Yellow/Skull moved, Holy Dragon after Omniscient, Red Dragon fight) -> Bahamut: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E29** (PARTIAL) The Sealed Legend (12 sealed weapons, 4 crystal guardians): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E33** (MISSING) Thoughts and Wishes (Cid, Celes): find and translate
- **E34** (PARTIAL) Owzer's Collection: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E35** (MISSING) Unexpected Special Skill (Umaro's carving): find its SNES events, translate and wire them, then play it
- **E36** (PARTIAL) The Last Dragon (Fanatics' Tower, Dried Meat): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E37** (PARTIAL) Molulu's Gift: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E40** (PARTIAL) A Duel! The Dragon's Neck Coliseum (Gilgamesh, Excalibur): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q1** (PARTIAL) Pub job boards (6 pubs): reinstall, rerun ted-quests
- **Q2** (PARTIAL) Cave Monster Cleanup (South Figaro, WoB): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q3** (PARTIAL) Defend Mt. Kolts!: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q4** (PARTIAL) I'll Buy Anything! (Nikeah): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q5** (PARTIAL) A Helping Hand (Kohlingen): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q6** (PARTIAL) The Dream Opera: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q7** (PARTIAL) Requiem (Setzer's lines): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q10** (PARTIAL) Wanted! Research Materials (scholar, Goddess Bell): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q11** (PARTIAL) Defeat the Cave Monsters (South Figaro WoR, repeatable): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q12** (PARTIAL) A Girl's Wish: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q13** (PARTIAL) Victory Drinks: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q14** (PARTIAL) Delivery Service (Nikeah, Duane): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q15** (PARTIAL) A Dancer's Depression (opens the Dressing Room): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q16** (PARTIAL) The Will to Live for Tomorrow (Phantom Forest foe): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q17** (PARTIAL) A Restful Sleep (Kohlingen, Darill's grave): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q18** (PARTIAL) Imitation's Secret (Narshe pub, Gogo's quiz): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **Q20** (PARTIAL) Super Doctor D (Zozo): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **D5** (PARTIAL) "The Best Models": change clothes at 12 inns and halls: finish the part named in the evidence, then test in game
- **X8** (PARTIAL) Wins fill the Collection Room and count for "EX Complete": translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **X10** (PARTIAL) EX room's Moogle: party and costume changes: trace and test

### ted-maps (17)

- **I19** (PARTIAL) Treasure chest contents on vanilla maps: place or reroute the 25
- **P9** (PARTIAL) Vanilla maps paired with PR rooms: pair the rest
- **E10** (PARTIAL) Water's Harmony learnable in the WoR: translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E39** (PARTIAL) A Mother's Love (Terra costume, Maduin's house): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E42** (PARTIAL) The Sealed Gate, Again (esper fight, elder, Terra's gear): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E43** (PARTIAL) Wandering Shadow (WoR Floating Continent, Atma Buster): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **E44** (PARTIAL) Know-It-All, the house north of Narshe: confirm the map, place him
- **N4** (PARTIAL) Holy Angel Ultima chain (page, sylph, Phantom Forest, Matoya's Crystal Eye, Goddess Bell, Labyrinth of the Ancients, Crystal Tower, Ultima): translate the rest; the landing
- **N5** (PARTIAL) Forbidden Land Eureka (optional, gear): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **N6** (PARTIAL) Soul Shrine (waves, re-fight chosen waves, shield on first clear, restart if left, save point, party change): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **N7** (PARTIAL) Developer's Room (after Ultima; lead-dependent reactions): fix the hang; finish stubs
- **N8** (PARTIAL) Secret Present (Eureka gravestone unlocks every costume): translate the stubbed commands and wire the unscripted events named in the evidence, then play it in game
- **D1** (PARTIAL) Dressing Room on the Falcon: finish the room's scripts; play it
- **D4** (PARTIAL) Unlocks by treasures, events, achievements (in order): finish the part named in the evidence, then test in game
- **S2** (PARTIAL) Area songs (66 new maps, 55 vanilla maps): the 7 rooms
- **U1** (PARTIAL) Collection Room (key items on display, paintings per EX boss): finish the part named in the evidence, then test in game
- **U2** (PARTIAL) Achievement Room: 2 rooms, hint books, 20 achievements, finale: counter/playtime/step compares as SysCalls

### lead (12)

- **M8** (PARTIAL) Drop odds 68/20/8/4 over four drop slots: carry the 61 missing 3rd/4th slots; check what the PR does on an empty slot
- **M39** (MISSING) New multi-hit spell effects (Tiger Rush 3 hits, Meteor 2-4, 8-hit effect): hit counts as ability data where the PR has the shape, else a hook
- **C11** (PARTIAL) Cyan: Bushido effects/accuracy (Tiger = MaxHP-HP; Snow/Moon/Flower): carry the renames and descriptions
- **C16** (PARTIAL) Edgar: Tools changed (Particle Bomb new, Debilitator gone, Air Anchor inflicts Heat, single/all target): Air Anchor's Heat and targeting
- **C17** (PARTIAL) Sabin: Blitz changes (Tiger Rush, Phantom Rush physical, Chakra cures Poison): see M39
- **C23** (PARTIAL) Mog: Dance always works, one dance per turn: no-stumble dance groups (a dance_rules mode)
- **C31** (MISSING) Dispel and Vanish usable outside battle: menu use for the two spells
- **G10** (PARTIAL) Animations for new/changed spells (Blink, Flood, Comet, Toad, Holy's new graphic ...): pick PR effects per spell
- **G13** (MISSING) Window types 2-8 after other Square games: decide: PR window skins or leave out
- **T4** (MISSING) Blitz, Bushido, esper and Rage descriptions (Rage menu shows the attack): read 40/0E00, CF/FF9E, CF/FFAE
- **T6** (MISSING) Element names Fire / Earth / Darkness / Light: implement it, then test in game
- **T7** (MISSING) Job titles (Mog "Moogle Knight", others): implement it, then test in game

### bc-sprites (6)

- **P8** (PARTIAL) T-Edition's own tilesets/graphics sets (82-85, edited sets 5, 6, 19-22, 53): PR tiles where a look-alike is wrong after a walk-through
- **G6** (PARTIAL) NPC sprites on the new maps (112 numbers): 40 new NPC sprites
- **G7** (PARTIAL) NPC and story sprites changed on vanilla maps (Kefka, Gilgamesh, Yura, Arvis, Jun): finish the part named in the evidence, then test in game
- **G8** (MISSING) New and edited battle backgrounds (Crystal Room, Phoenix Cave fire, WoR variants ...): decode E6/F800, make PR backgrounds
- **G9** (MISSING) Collection Room paintings: implement it, then test in game
- **G14** (PARTIAL) Weapon and item icons/battle sprites changed: finish the part named in the evidence, then test in game

## 5. The 15 most important MISSING items

Ranked by how much of T-Edition a player misses without them (all 45 MISSING rows are in section 4).

1. N1 (with N2, N3) New Game+: the clerk, the story reset, its carry-overs and resets [TedPlugin, ted-events]
2. M31 Desperation attacks, incl. Gau's, Umaro's and Gogo's new ones [TedPlugin]
3. C29 Magitek: six options for every character [TedPlugin]
4. M15 Equipment statuses win over immunity (Cursed Shield with a Ribbon) [TedPlugin]
5. M9 / M10 Back, pincer, side and pre-emptive odds with their relics (one hook) [TedPlugin]
6. E33 Thoughts and Wishes (Cid and Celes): no events found [ted-ex]
7. E35 Unexpected Special Skill (Umaro's carving): no events found [ted-ex]
8. E18 Deep Earth Dweller: no events found [ted-events]
9. E38 A Priestess's Concern (unlocks a Sabin costume): not wired [ted-events]
10. E5 Valigarmanda needs Terra, with the other unwired changed scenes E1, E4, E7, E8, E9 [ted-events]
11. I18 WoR shop prices doubled until Humbaba falls [TedPlugin]
12. U4 Status screen pages (attributes, conditions, abilities) [TedPlugin]
13. U5 Equipment detail labels [TedPlugin]
14. T4 Blitz, Bushido, esper and Rage descriptions (the Rage menu's attack text) [lead]
15. M39 Multi-hit spell effects (Tiger Rush, Meteor) [lead]

Next after these: U6 magic acquisition view, G8 battle backgrounds, D6 Falcon music per costume, C12 Bushido gauge,
M34 Offering rules, U7 battle status icons, G9 Collection Room paintings.
