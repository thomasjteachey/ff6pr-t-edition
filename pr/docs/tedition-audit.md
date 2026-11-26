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

Stubs and PORTED (the lead, 2026-11-21): a translated event or quest is PORTED only when every stub it still has is cosmetic (sound, animation, facing, screen effects); any logic stub (a branch, random jump, condition test, flag, warp, item or party change) keeps it PARTIAL, with those stubs named in its work column.

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
| Mechanics/battle | 44 | 9 | 30 | 4 | 0 | 1 |
| Items and equipment | 21 | 1 | 19 | 1 | 0 | 0 |
| Characters/commands/espers/magic | 31 | 3 | 22 | 4 | 1 | 1 |
| Monsters/formations/AI | 9 | 1 | 6 | 2 | 0 | 0 |
| Maps | 9 | 2 | 5 | 2 | 0 | 0 |
| Events/story scenes | 44 | 0 | 8 | 31 | 5 | 0 |
| Pub quests | 20 | 0 | 7 | 13 | 0 | 0 |
| NG+/post-game | 8 | 0 | 3 | 5 | 0 | 0 |
| Costumes/dressing room | 10 | 0 | 6 | 3 | 0 | 1 |
| Music | 8 | 0 | 4 | 3 | 1 | 0 |
| Graphics | 14 | 1 | 5 | 6 | 1 | 1 |
| Menus/UI/rooms (Collection, Achievements, Track Record) | 11 | 0 | 7 | 3 | 0 | 1 |
| Text/translation | 10 | 1 | 7 | 0 | 0 | 2 |
| EX | 13 | 0 | 9 | 1 | 0 | 3 |
| Platform patches (outside the game) | 4 | 0 | 0 | 0 | 0 | 4 |
| **All** | **256** | **18** | **138** | **78** | **8** | **14** |

## 2. Weighted completion

Done = PORTED + TESTED + half of PARTIAL, over all rows but LEFT OUT. Every row weighs the same (a quest counts as much
as a battle rule), so this is a feature count, not the effort-weighted table in `pr/PORTING.md`.

| Area | Counted rows | Done (T + P + PARTIAL/2) | Completion |
|---|---:|---:|---:|
| Mechanics/battle | 43 | 41 | 95% |
| Items and equipment | 21 | 20.5 | 98% |
| Characters/commands/espers/magic | 30 | 27 | 90% |
| Monsters/formations/AI | 9 | 8 | 89% |
| Maps | 9 | 8 | 89% |
| Events/story scenes | 44 | 23.5 | 53% |
| Pub quests | 20 | 13.5 | 68% |
| NG+/post-game | 8 | 5.5 | 69% |
| Costumes/dressing room | 9 | 7.5 | 83% |
| Music | 8 | 5.5 | 69% |
| Graphics | 13 | 9 | 69% |
| Menus/UI/rooms (Collection, Achievements, Track Record) | 10 | 8.5 | 85% |
| Text/translation | 8 | 8 | 100% |
| EX | 10 | 9.5 | 95% |
| Platform patches (outside the game) | 0 | 0 | (all LEFT OUT) |
| **All** | **242** | **195** | **81%** |

Read with care: only 12 of the 244 counted rows (5%) have been seen working in game; the 92 PORTED rows are code or data
that has never run through its real trigger. PORTING.md's own estimate (~60%, effort-weighted) is close to this count,
but the two areas the player meets most outside battle, events (40%) and menus/rooms (15%), sit lowest. Open risks from
ted-7 that may touch many rows at once: the stalled harness battle (rule 44's time freeze never logged in that run),
`KeyNotFoundException` in `GetMagicStatus` during new-monster fights, the quest scripts the game refused, and room 697's
Namingway script that seemed not to end (corrected: the test opened the naming screen by answering Yes; not a bug).

## 3. Checklist

Columns: feature, source (file and section), status, evidence, and for PARTIAL/MISSING the work needed with its owner in
brackets. `C2/xxxx`-style rule numbers refer to `pr/ted/BATTLE_SPEC.md`'s rule table ("spec N").

### Mechanics/battle

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| M1 | ATB and time stop while an action plays (FF5-like) | change.html §1 "ATB System" | TESTED | TESTED 2026-11-25 (ted-gate-1, PC): on the kit's SnesActionFreeze now (TED's own hooks never held); log "rule 44", "action freeze: time held 1.61-2.36 s for an action"; `TedStatuses.cs:54-57` (spec 44: UpdateGaugeIncrease/UpdateChantTime held, status clock held); ted-7 expected "rule 44" and saw it 0 times (its battle stalled) | — |
| M2 | Battle speed: monster ATB 255-4*speed, Haste 96 / Slow 32 | history (reverted note), spec 45 | PORTED | `Plugin.cs:112-119`; ted-7 log "rule 45: ATB: Haste x144, monster speed term 4" (hook installed) | — |
| M3 | Command wait times per command (Blitz/Bushido/Lore slower, X-Magic slightly faster) | readme.html §7 FAQ; spec 46 | PORTED | `Plugin.cs:112`, `TedRules/StatusMath.cs:24` | — |
| M4 | Accuracy/evasion bug fixed (physical uses Evade) | readme.html §6 "Evasion Bug"; change §2 "Accuracy Bug" | PORTED | spec 19 "none: the PR already uses Evade" | — |
| M5 | Blind lowers hit rate (vanilla bug fixed) | readme.html §6 "Blind Bug"; change §2 "Blind Status" | PORTED | the PR's own: PhysicalExecution halves a blinded attacker's hit rate and skips it for 255-accuracy (never-miss) attacks (tools/decomp/physical; BnwPlugin/BlindRules.cs notes), which is T-Edition's rule 20 (vanilla's halving, now reached) | tedprobe blind in ted-8pc confirms |
| M6 | Vanish no longer lets every spell (X-Zone) land | readme.html §6 "Vanish Magic Bug" | PORTED | spec 23 "the PR already fixed Vanish + Doom (patch 1.0.5)" | — |
| M7 | No hit-rate change from the target's statuses | spec 21 | TESTED | TESTED 2026-11-25 (ted-gate-1/ted-battles, PC): rule 21 logged in every battle; `Plugin.cs:163-180`; ted-7 log "rule 21: no hit-rate change ... (both lists emptied)" (installed) | — |
| M8 | Drop odds 68/20/8/4 over four drop slots | change §2 "Item Drop Rate" | PORTED | 2026-11-21 lead: verified offline that every drop slot T-Edition fills is in the port, by slot: monsters 0-383 (set_drop_slots, drop_content_id1..4) and the 104 new monsters (port_monster_ext); the in-game tedcheck's 3-4-slot count mismatch is the check's counting, not missing data | in game: what the PR does when its pick lands on an empty slot |
| M9 | Back/pincer/side attack odds fix; Back Guard (Alarm Earring) stronger | change §2 "Back Attack/Pincer..." | PORTED | 2026-11-21 TedPlugin TedEncounters: back/pincer/side odds and Back Guard; builds, Ted.Tests 21 | test in game |
| M10 | Pre-emptive strike chance doubled, Gale Hairpin x4 | change §2 "Pre-emptive Strike Increase" | PORTED | 2026-11-21 TedPlugin TedEncounters: Gale Hairpin pre-emptive 1 in 2 (x4), no enemy first strike | test in game |
| M11 | Defense-ignoring attacks go through Def 0 (Safe/Defend/row apply) | change §2 "Defense-Ignoring Attacks" | TESTED | `TedRules/DamageSteps.cs:155-158`; ted-7 teddamage "Fight on a monster (Attack #1) ... ignores defense ... ok" | — |
| M12 | Weakness quarters defense instead of x2 | change §2 "Weakness Attribute" | TESTED | spec 7, `TedDamage.cs:170-196`; teddamage "Fire on a monster ... rules' factor x1.038 [6,7] ok" | — |
| M13 | Multi-element attacks: each element counted separately | change §2 "Multiple Attribute Attacks" | PORTED | spec 6, `TedDamage.cs:306-323` (Resist_Postfix); teddamage "a multi-element spell on a monster: skipped" | — |
| M14 | Half damage from defense-ignoring attacks on flagged monsters | change §2 "Protection Against Defense-Ignoring Damage" | PORTED | `DamageSteps.cs:182-185` (spec 9); list from `tools/ted_plugin_data.py:13` | — |
| M15 | Equipment statuses win over Ribbon (Cursed Shield stays cursed) | change §2 "Status Ailments" | PORTED | TedRibbon.cs: PlayerCharacterParameter.ConfirmedResistanceCondtionList postfix drops, from a character's immunities, the statuses its own equipment grants (GetEquipmentConfirmedConditionList), so a Cursed Shield's statuses stay on a Ribbon wearer (spec 52's documented intent) | ted-8pc's Ribbon + Cursed Shield step (log 'rule 52') |
| M16 | Near Fatal at 1/4 HP (Cover, desperation, SOS relics follow) | change §2 "Critical Health" | PORTED | `profile_tedition.py:609` RATE_HAVE_NEAR_DEATH 4 | — |
| M17 | "Critical Health" element: percent spells only inflict Near Fatal; Near-Fatal-immune monsters dodge them | change §2; EX history (Gravity/Tornado change) | PORTED | percent groups as data (rule 49); TedNearFatal.cs: BattleFunction2.HitCalc postfix turns a hit of a percent spell (ted_data percent_abilities, 15) on a monster immune to Near Fatal (ted_data near_fatal_immune: byte $15 bit 1, 229 of 512) into a miss | whether the PR still misses death-immune bosses (spec 48: death immunity no longer matters): probe Gravity on a boss |
| M18 | Percent damage: listed spells on current HP, the rest (Diabolos 3/4, Wave Cannon 9/16) on max HP | history 2.9.5/2.9.7; spec 49 | PORTED | `ted_plugin_data.percent_damage` run by `ted_build.py:88-89` | — |
| M19 | Stop shorter than Sleep (9 steps) | change §2 "Stop Status" | PORTED | `Plugin.cs:125-127`; ted-7 log "rule 51: status clock: Stop 9 steps" (installed) | — |
| M20 | Poison 1/8 max HP a tick, cap 999 | change §2 "Poison Status" | TESTED | TESTED 2026-11-25 (ted-gate-1, PC): "rule 50: Poison tick on a character: max HP/8 = 999 (the game's 624)"; `TedStatuses.cs:71-95`, `StatusMath.cs:13`; ted-7 expected "rule 50" and saw it 0 times | — |
| M21 | Regen 1/8 (party) / 1/16 (monsters), cap 999, no Stamina | change §2 "Regen Status" | TESTED | TESTED 2026-11-25 (ted-gate-1, PC): "rule 50: Regen tick on a character: max HP/8 = 999 (the game's 255)"; `TedStatuses.cs:97-109`, `StatusMath.cs:14` | — |
| M22 | Sap renamed Disease, drains MP | change §2 "Disease Status" | PORTED | `TedStatuses.cs:111-125` (MP/16 per the code; docs say 1/8) | — |
| M23 | Critical hit rate 8% | change §2 "Critical Hit Rate" | PORTED | `profile_tedition.py:625`, `ted_build.py:48-74` | — |
| M24 | Espers summonable any number of times | change §2 "Summoning Eidolons" | PORTED | `TedStatuses.cs:52-53` (spec 55); MP costs are esper data (C9) | — |
| M25 | Defend: magic taken x2/3 as well | change §2 "Defend Status" | TESTED | spec 10; teddamage "monster Fire on a defending character ... [10] ok" | — |
| M26 | Back row: physical taken x2/3 (was 1/2) | change §2 "Back Row Status" | PORTED | spec 10, `TedDamage.cs:188` (BackRow); not in teddamage's samples | — |
| M27 | Shell also cuts healing and defense-ignoring magic | change §2 "Shell Status" | TESTED | teddamage "Cure on a Shelled character (Cure #76) ... x0.65 ... [8] ok" | — |
| M28 | Absorb gives the full computed damage | change §2 "Absorbing Damage" | PORTED | `TedStatuses.cs:51, 143-165` (spec 54) | — |
| M29 | Reflected magic not halved (3+ reflectors out-damage one hit) | change §2 "Reflect Status" | PORTED | the PR's own: CalcExecuteFF6.MagicExecution has no reflect input and no halving step for a bounced spell (tools/decomp/battle: MagicExecution, CalcControllerProvider), which is T-Edition's rule 53 (C2/34B8 NOPed); TedSelfTest logs rule 53 on a bounce | a probe: tedcast Fire on a Reflected ally vs on a monster (same Magic), damage equal |
| M30 | Damage/heal cap 32000, 5-digit display | change §2 "Damage/Recovery Limit Increase" | PORTED | profile_tedition MAX_HIT_VALUE 32000; TedDamageDigits.cs: the PR draws digit i into its damage prefab's child i (ViewDamageEntity.CreateDamageValue, tools/decomp/ted_m30) and the prefab has 4: CreateDamagePrefab postfix adds slots for 10000+; harness teddigits [value] | teddigits in a battle + a shot |
| M31 | Desperation attacks: easier (code 1/32), unlimited, no 768 timer, new ones for Gau/Umaro, blocked by Offering | change §2 "Desperation Attacks" | PORTED | 2026-11-21 TedPlugin TedDesperation (1/32 per Fight at Near Fatal, no timer, all 14 incl. Gau/Gogo/Umaro, blocked by Elven Darts/Master's Scroll); ted_build desperation_rule makes 226/227 desperation rows | test in game |
| M32 | Two-handed grip: double damage, lower evasion | change §4 "2 Hands" | PORTED | spec 13 "the PR's TwoHandedMagnification is already 2" | — |
| M33 | Dual wield: 0.75 per hand | change §4 "Dual Wield" | PORTED | `Plugin.cs:150-160` (spec 14, SnesRelicPenalties) | — |
| M34 | Master's Scroll/Offering: normal accuracy, no procs or desperation | change §4 "Barrage"; EX history | PARTIAL | accuracy: TedBarrage.cs clears PhysicalExecution's mikiriBracelet (its only use: the hit rate halved, 255 -> 127; tools/decomp/physical); desperation: TedDesperation skips the Master's Scroll / Barrage | no weapon procs (instant death, spell procs) with Barrage: check the PR in game, hook if they fire [TedPlugin] |
| M35 | Attack/magic boost relics don't stack; magic boost raises heals | change §4 "Physical/Magical Attack Power Up" | PORTED | `TedDamage.cs:73-86, 214-226, 243-273` (spec 15) | — |
| M36 | Bonus vs flying: darts/cards x2 vs Float under Fight | change §4 "Extra Damage to Flying Monsters"; 3.0.0 | PORTED | `TedDamage.cs:51-71` (spec 16) | — |
| M37 | Image lost on half of dodges | spec 22 | PORTED | `profile_tedition.py:611` | — |
| M38 | Golem/Interceptor blocker defense 119 | spec 11 | PORTED | TedBlocker.cs: T-Edition C2/0CD0-0CD8 (either block flag -> defense #$78 = 119); the PR's PhysicalExecution (tools/decomp/physical) only logs 192 and uses the target's ConfirmedDefense, moving a Golem block into the pool inside: a prefix marks the blocked target (isDefendInvoked/isDefencedGolem) and PlayerCharacterParameter.ConfirmedDefense answers 119 for it during that calculation | see 'rule 11' with a Golem block in game |
| M39 | New multi-hit spell effects (Tiger Rush 3 hits, Meteor 2-4, 8-hit effect) | change §3 Sabin; EX history (Meteor); spec 26 | PARTIAL | Tiger Rush (effect $14, 3 hits): ted_plugin_data.multi_hit_rule gives ability 138 the PR's multi-hit shape (Flurry's: function 2 value1 2 value2 3, range 13 random enemy) at power 69; effects $46/$47 are used by no 3.0.7 spell | Meteor (spell $23, PR 75; effect $4E -> 47/1823: 2 hits, +1 if rand<84, +1 more if rand<36 = 2/3/4 hits at 67/19/14%): the PR's shape takes a fixed count, so a hook that varies it per cast [TedPlugin] |
| M40 | Coliseum fights under the player's control | change §1 "Coliseum Battles" | PARTIAL | `TedStatuses.cs:40-47`, but behind `[Battle] ColiseumControl` default false (`Plugin.cs:63-64`) | test in game, then default on [TedPlugin] |
| M41 | Steal: (Lv+70-target Lv)/99, rare 1/4 | change §4 "Steal" | TESTED | `TedCommands.cs:95-125`; ted-7 "tedsteal: 264/400 stolen (66.0%), T-Edition's chance 68% ... ok" | — |
| M42 | Gil Toss: Lv x180 gil, Lv x90 to every target; monsters' own rule | change §4 "Gil Toss"; EX history | PORTED | characters: TedCommands.cs Gil Toss cost (Lv x180, once per act) + TedDamage rule 29 (Lv x90 each, no split); monsters: TedDamage rule 29 'monster Gil Toss' (GIL_THROW by an enemy: min(Lv x180, its gil) / 2 / targets via CommandMath.MonsterGilToss) | see both in game (log 'rule 29') |
| M43 | Psycho Cyan bugs (Retort flag after death; Imp) fixed | readme.html §6 | PARTIAL | the PR's Sky stance (ConditionType 626, condition 61) has erase group 1 = Poison, Dark, Mute, Imp (601), Petrify, Sap: Imp ends Retort in the PR's own data; Wound (5) isn't in that group | check Retort is gone after Cyan dies and is revived (tedcast Sky, kill, raise, hit him); hook only if it stays [TedPlugin] |
| M44 | Game over returns to the title (kills the airship bug) | readme.html §6 "Airship Bug" | LEFT OUT | a fix for an SNES-engine airship-state bug; the PR's game over is its own code (not re-checked here) | — |

### Items and equipment

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| I1 | Item list rebuilt: re-slotted and new items, the second bank of 24 relics | change §5 "Item Classification"; armor/weapon.html | TESTED | `tools/item_identity.py`; ted-7 tedcheck "items 279/279 (moved rows 205/205); new weapon rows 24/24" | — |
| I2 | Weapon and armor stats, equip lists, elements, worn statuses | weapon.html, armor.html; 3.0.0 notes | PORTED | port_report "weapon: 114 changed", "armor: 104 changed", "job_group: 32 new equip groups", "equipment resistances" | — |
| I3 | Weapon properties: MP Critical, HP/MP absorb, Row OK, throwable, bonus vs flying/human/magic/dragon | change §1 "Equipment Details Menu"; 3.0.0 | PORTED | equip menu (U5, TedEquipDetails); MP Critical: TedMpCritical.cs sets CalcExecuteCorrection.UseMpCriticalWeaponIds to T-Edition's effect-7 weapons; flying/magical/dragons: TedDamage x2 (T-Edition's pre-damage table C2/3DB5: 8 = target Float, E = monster byte $12 bit 0, F = bit 5; ted_data monster_kinds 111 magical / 51 dragons); HP Absorb (wear group 100), MP Absorb (Soul Eater), humans (species 2) as data | see a x2 log line in game; Dragon Spear/Amanomurakumo also carry the porter's wear group 108 (PR function 62/257): check it isn't a second bonus |
| I4 | Weapon spell procs | weapon.html | PORTED | port_report "weapon procs: 34 weapons (20 new ...)" | — |
| I5 | Relic effects T-Edition re-coded (relic bits) | armor.html; history ("changed the address of the effect setting") | PORTED | 2026-11-21 TedPlugin TedRelics + ted_data relic_bits (9.0/9.1 +25%, 11.7 +50%, 11.0, 11.2 Sketch up, 12.2 Blade Grasp as +20 evasion, 12.7 multi-jump, 13.5, 13.6, 13.2, 12.0); profile relic_bit_funcs 9.2 HP+25%, 9.3 HP+50%, 12.0 as PR wear functions | test in game |
| I6 | Relic command swaps: Zeidrich (Shock), Maiden's Prayer (Pray), Embroidered Tippet (Spirit), Pheasant Strap (Animal), Gem Box, Dragon Horn, Thief, Heiji's Jitte | change §3 Terra/Celes/Relm/Mog; spec 31 | PORTED | `profile_tedition.py:630-637`; `ted_build.py:221-239` (Pray casts Sunbath, Spirit Bless, Animal random) | — |
| I7 | Sprint Shoes and Fake Mustache removed (hold B to dash) | change §1 "Movement Speed"; §3 Relm | PORTED | neither in `mods/TEditionPort/ted_items.json`; the PR dashes by itself | — |
| I8 | Stat Tabs, Golden Apple, Soma Drop raise stats | 3.0.0 "Tab items"; Quick Advice | PORTED | `ted_build.py` consumable_rule: each stat item gets its own parameter_group row and function 4 points at it (the PR's IsPersistenceParameter reads value1 as a parameter_group id; TedPlugin's decompile, 11-21). ted-8's teduse had 241/244 unusable before this fix; check queued in ted-8c | in-game: teduse in ted-8c |
| I9 | Combined cure items; Reincarnation | 3.0.0 "Added and combined status recovery items" | PORTED | `ted_build.py:277-342` | — |
| I10 | Orichalcum: power from steal count, shown in the item screen | change §3 Locke | PORTED | `TedCommands.cs:251-282` (spec 28, menu value via ConfirmedAttack); ted-7 only gave one ("gave 1 x Orichalcum") | — |
| I11 | Ultima (Atma) Weapon on Stamina, not Level | change §5 "Ultima Weapon" | PORTED | `DamageSteps.cs:190-196` (spec 17) | — |
| I12 | Ultima Weapon's blade changes with damage (dagger/sword/great sword) | change §5 "Ultima Weapon" | PORTED | the PR already picks the Ultima Weapon's blade (weapon row 30 = T-Edition's slot 0x61) by the hit's damage in DoEffectActFunction.ChangeUltimaWeaponSprite (tools/decomp/ted_i12: <500 Default_02, <1000 Default_01, else Default_00 + max-power after-images); TedUltima.cs maps the value it reads so the steps fall at T-Edition's 2000 / 5000 | see the three blades in game (log 'rule 17') |
| I13 | Valiant Knife no longer ignores defense | change §5 "Valiant Knife" | PORTED | `TedDamage.cs:145, 234` (spec 60) | — |
| I14 | Dancing Dagger: 50% a random dance | change §5 "Dancing Dagger" | PORTED | `ted_build.py:242-265` | — |
| I15 | Dice / Fixed Dice formula, accuracy, no Berserk boost | change §5 "Dice/Fixed Dice" | PORTED | `TedDamage.cs:151-169` (spec 41) | — |
| I16 | Other new items (Experience Egg, Gold Hairpin as relic, Kenkonken throwable, Power Belt, ...) | history 3.0.0, 2.9.5 | PORTED | names in `ted_items.json`; port_report "rods and throwing" | — |
| I17 | Shop stock, T-Edition's own shops included | shop.txt | PORTED | `ted_build.py:351-376`; port_report "79 SNES shops matched"; docs/tedition.md:11 "all 110 stocked shops mapped" | — |
| I18 | WoR shop prices double until Humbaba falls | Mato README "Legendary Fiend Humbaba"; spoiler_free_new_quests | PARTIAL | 2026-11-21 ted-events: ted_flags.json (TEditionEvents top level) wor = ScenarioFlag2 41, humbaba_scared_off = SF2 100 (SNES 0BF), humbaba_returns = SF2 99 (292); TedPlugin's hook on with wor + humbaba_scared_off | T-Edition's price code (which bit) not found; the final-defeat bit, if it differs [ted-events, TedPlugin] |
| I19 | Treasure chest contents on vanilla maps | readme translation (chests) | PORTED | ted_maps.vanilla_chests: the 13 chests T-Ed added on vanilla maps (new SNES bits) are TEditionChest objects in their vanilla PR rooms, TreasureFlag 370-382 (ted_maps.json vanilla_chests; test_vanilla_chests); the rest of the porter's 25 are story-copy duplicates its PR chests cover; 300's monster box is the translator's | in-game: ted-10 shot of Map_20081_3 |
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
| C11 | Cyan: Bushido effects/accuracy (Tiger = MaxHP-HP; Snow/Moon/Flower) | change §3 Cyan | PORTED | 2026-11-21 lead: Bushido named from Mato's own SWDTCH NAMES table (55/A990: Fang, Sky, Tiger, Dance, Dragon, Snow, Moon, Flower, the menu's Tachi prefix dropped as the PR's names have none); the spell table's leftover at slot 85 (Joker Doom) no longer renames Fang; Mato's Bushido descriptions (T4); effects through the spell data | test in game |
| C12 | Cyan: Bushido gauge fills faster | change §3 Cyan | LEFT OUT | the PR's Bushido has no filling gauge: the level is picked first, then Cyan charges (the Accumulate condition, ConditionType 421); T-Edition's faster SNES gauge (C1 menu code, not located in a bank-C1 diff against the JP ROM) has no counterpart to port |  |
| C13 | Shadow: Interceptor blocks 2/3, one fixed counter (Twin Fang) | change §3 Shadow | PORTED | `TedCommands.cs:284-313` (spec 38) | — |
| C14 | Shadow never leaves at random | change §3 Shadow | TESTED | TESTED 2026-11-25 (ted-battles, PC): "rule 58: Shadow's after-battle draw: he stays" after every won battle; `TedVictory.cs:118-128` (spec 58) | — |
| C15 | Shadow: ninja swords dual-wield, scroll changes, Throw without its built-in x2 | change §3 Shadow; spec 42 | PARTIAL | swords/scrolls through the item data; Throw: T-Edition's C2/1888 stores $BD = 0 (vanilla 2); the PR's PhysicalExecution (tools/decomp/physical, ability type 609 Throw) takes the thrown item's ability UseValue as attack and has no x2 step for Throw | compare a Throw's damage with the thrown weapon's attack in game (tedcast); hook only if the PR doubles somewhere else [TedPlugin] |
| C16 | Edgar: Tools changed (Particle Bomb new, Debilitator gone, Air Anchor inflicts Heat, single/all target) | change §3 Edgar | PARTIAL | port_report "tools: 7 tool items changed (power/hit only)"; Particle Bomb in `ted_items.json` slot 167 | Air Anchor's Heat and targeting [lead] |
| C17 | Sabin: Blitz changes (Tiger Rush, Phantom Rush physical, Chakra cures Poison) | change §3 Sabin | PORTED | names MSG_MAGIC_NAME_115/116; Phantom Rush physical (fg 2022 function 2); Chakra cures (fg 2020: function 23 + condition group 2010); Tiger Rush: the porter had read T-Edition's effect $14 as vanilla's Spiraler (power 9999, the user's life for the party's HP); multi_hit_rule makes it 3 random physical hits at power 69 (M39) | use the Blitzes in game |
| C18 | Celes: Runic speed changed | change §3 Celes | MISSING | spec 62 "not located" | locate and port [TedPlugin] |
| C19 | Strago: Lores replaced (Mind Blast, Magic Hammer, Ancient Prayer) and retuned | change §3 Strago | PORTED | MSG_MAGIC_NAME_119/135/137 in the port's text | — |
| C20 | Relm: Sketch with Relm's stats, 75% move / 25% Wishing Star, works without a brush, brushes raise odds | change §3 Relm | PARTIAL | sketch table as data (port_report: sketch 349 monsters; 75% the monster's move / 25% Wishing Star); hit odds: TedRelics.Sketch_Postfix + RandPlus_Postfix answer the PR's roll (UniqueUpdateParameterProvider.HitCalc: rand(100) < (its Lv-difference threshold), tools/decomp/gilthrow) with T-Edition's min(1, Relm Lv / target Lv), target Lv x170/256 with an Enhanced Sketch item (bit 11.2) | sketched attacks with Relm's Mag.Pwr / battle power (spec 30: C2/6710, CE/0000): check the PR in game |
| C21 | Relm: Control removed | change §3 Relm; spec 32 | PORTED | `ted_build.py:221-239` (command slot 19 is Snowstorm) | — |
| C22 | Setzer: Slots retuned; Mysidian Bunny Lv x power, not split | change §3 Setzer | PORTED | `TedDamage.cs:198-213` (spec 37); teddamage flags "Mysidian Rabbit ... (CHECK: the game's split isn't 1/n)" | — |
| C23 | Mog: Dance always works, one dance per turn | change §3 Mog | PORTED | one dance per command: TedCommands; always works: ted_plugin_data.dance_rule (data_rules) sets the off-background groups 37-44 to the native odds with the stumble (ability 262) at 0 (40 rows; the porter and profile untouched) | dance off its own background in game |
| C24 | Gau: Fight instead of Leap (ends the Shadow/Leap crash) | change §3 Gau; readme.html §6 | PORTED | `ted_build.py:224` (Leap slot = Animal); spec 63 | — |
| C25 | Gau learns Rages from any won battle | change §3 Gau | PORTED | `TedVictory.cs:12-15, 65-80` (spec 34) | — |
| C26 | Gau equips weapons (Rages keep his weapon) | change §3 Gau; Readme A7 | PARTIAL | equip lists in job_group (port_report); Rage animations with his own weapon not handled | art/sound: needs the art owner (ted-maps) or LEFT OUT [lead decides] |
| C27 | Gogo and Umaro equip espers and learn magic | change §3; 3.0.0 | PORTED | `TedMagicite.cs:8-66`; ted-7 log "rule 35: ... 3 checks hooked" | — |
| C28 | Umaro controllable, Snowstorm command, Berserker Ring / Power Belt procs on Fight | change §3 Umaro | PORTED | 2026-11-21: TedPlugin TedUmaro (player commands; T-Edition's Fight table: Charge/Rampage/Throw Ally); ted_build umaro_rule (Attack, Snowstorm, Magic, Items; no initial Umalo); ted_plugin_data rampage_rule (ability 9903, power 96, physical, all enemies) | test in game |
| C29 | Magitek: six options for every character | change §3 "Character Overview"; spec 61 | TESTED | TESTED 2026-11-25 (ted-gate-1, PC): "rule 61: Magitek for everyone: T-Edition's six (220-225)"; 2026-11-21 TedPlugin: every character has T-Edition's six Magitek options (PR 220-225) | test in game |
| C30 | Veldt holds formations up to 511 | change §2 "Registering Monster Formations to the Veldt" | PORTED | `profile_tedition.py:623`; port_report "veldt: 511 formations in 64 groups" | — |
| C31 | Dispel and Vanish usable outside battle | history ("You can now use Dispel and Vanish in the field") | PORTED | ted_plugin_data.field_spells_rule (data_rules): a spell is menu-usable with a menu function group and range; the port's Dispel row (ability 55) already has them (group 468, range 7); Vanish (ability 33) gets its battle group 463 and range | use both from the field menu in game |

### Monsters/formations/AI

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| B1 | New monsters (94) and formations past 576 | change §6 "Monster Changes" | TESTED | ted-monsters "battle 30723 started" ... "battle 30696 started"; shot `shots/ted_mon_30723.png` (Seraph in battle); log "monster 1472 uses ability [197]" | — |
| B2 | Monster stats, resistances, statuses, EXP (WoR EXP up) | change §6; 2.9.6 | PORTED | port_report "monster: 370 changed", "enemy resistances" | — |
| B3 | Monster special attacks | monsterspecial.txt | PORTED | port_report "monster special attacks: 353" | — |
| B4 | Steal and drop contents | scanstealdata.html; stealdropragworthit.txt | PORTED | porter (docs/tedition.md:36 "steals/drops (291)") | — |
| B5 | Monster AI on T-Edition's own scripts | change §6; history (boss behaviours) | PARTIAL | profile_tedition snes_ai_status=True with T-Edition's hybrid scripts/events/start_shows/pr_ends (BNW's route, each checked against T-Edition's own script); port_report: boss (kept PR script) 46 -> 27, own script in the plugin 309 -> 350; ted_ai.json status_effects=true turns the host's FB 0B/0C/02 on (TedEnemyAi.DataStatus) | test the 19 moved bosses' fights (parties 436 437 438 440 447 448 451 464 469 470 515 474 478 423 490); the 27 left: final battle (9), no formation of their own (9), PR-staged fights (King Behemoth, Tentacles x4, Wrexsoul, Relm/Ultros, 371, 372, Air Force 324) |
| B6 | Formations and encounter packs (world, dungeons, Gogo's cave none) | worldmap.txt; history | PORTED | port_report "encounters: {'new parties': 337 ...}" | — |
| B7 | Metamorph (Ragnarok) sets | ragnarok.txt | PORTED | port_report "metamorph: ..." | — |
| B8 | Formation AP and escape flags (Ninja, Don runnable) | 3.0.0 notes | PORTED | port_report "monster_party AP: 111", "escape: 25 parties changed" | — |
| B9 | Kefka's Tower: new boss, new fixed battles, Number 024/128/Air Force on the Veldt | history | PARTIAL | Kefka's Tower: entrance CC/118E and the 7 tower tiles (maps 334/354/355) built in mods/TEditionQuests (tiles as new triggers in Map_30870/30871_*, 0-24% stubs; the rest are untied vanilla bits 126/2Ax/067/071); CA/0300 isn't an event (decoration-NPC bytes); new formations through the porter | untied-bit ties [ted-events]; play the fights [ted-ex] |

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
| P9 | Vanilla maps paired with PR rooms | (port need) | PARTIAL | data/snes_pr_maps.json 357 of 416 SNES maps (door pass + 33 hand pairs, kit-published cf21b07); catalog events without a PR spot 78 -> 36 | the rest: maps with no PR room (unused slots, redrawn scenes) |

### Events/story scenes

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| E1 | Narshe defense: new scene when Cyan meets Kefka | change §7 | MISSING | CC/BC96 (map 22) in the catalog, no script | wire it [ted-events] |
| E2 | Night in Albrook: find Celes | change §7; Mato README | PARTIAL | CD/3DC0 (map 330) scripted, 0% stubs; the Celes search not traced | trace and wire the rest [ted-events] |
| E3 | Fewer fish to save Cid | change §7 | PARTIAL | CA/5366 scripted (12% stubs, ted-events' edit of PR sc_e_0616); CD/4300 is not an event (decoration NPC pointer bytes on map 334: ted-ex 2026-11-21) | the scene's stubs [ted-events] |
| E4 | Sabin's new lines at Gerad | change §7 | PORTED | 2026-11-21 ted-events: CA/91D0 (map 169 NPC 10) in TEditionEvents (ted_events.EVENTS), 0 stubs: its facing switch through vanilla's facing routine -> BranchByPlayerDirection | test in game [ted-events] |
| E5 | Valigarmanda (WoR) needs Terra | change §7; readme.html §7 | PORTED | 2026-11-21 ted-events: CC/370F (map 35 tile 9,14) in TEditionEvents, Map_20040; its condition's facing (1B0-1B3 -> BranchByPlayerDirection) and A-button bit (1B4, decided by the event's trigger) translate; cosmetic stub: one sound | test in game; also the Test of Strength's last step [ted-events] |
| E6 | Cyan's Dream: new solo battles, throne after the memories | change §7; readme.html §7 | PARTIAL | CD/4000, CD/4003 scripted (~19% stubs); CD/3FE0 (map 126), CD/4002 not | [ted-events] |
| E7 | New Kefka battle on the Floating Continent | readme.html §7; Mato README | MISSING | no wired event found (CA/5A0C, map 10, unscripted) | find and wire [ted-events] |
| E8 | Shadow always gets off the Floating Continent | change §3 Shadow | MISSING | not located in the catalog | [ted-events] |
| E9 | WoR Figaro cave: collapsed soldier heals for free | readme.html §7 | MISSING | not located | [ted-events] |
| E10 | Water's Harmony learnable in the WoR | change §3 Mog | PORTED | Underwater Cave (map 481) events scripted (69 commands), no stubs: lead-status tests via TED:leadstatus, status changes via TED:status add (11-21) | test in game |
| E11 | Final battle: Gogo/Umaro lines, party select | history | PARTIAL | map 12: CA/3F2B/3F3B/3F73 scripted, CA/3F13, CD/15E0 not | [ted-events] |
| E12 | New merchants (Phantom Train ghost, Doma, Esper Village, Mobliz, Fanatics' Tower, Narshe WoR) | history 3.0.0 and earlier | PARTIAL | `TedSysCalls.cs:47-58` TED:shop; used in 59 script files of mods/TEdition; not run | play one shop [ted-events] |
| E13 | Beginner's House tutors rewritten, advanced-info NPC | readme translation; history | PARTIAL | maps 104-107 talk events scripted with 0 stubs; CD/4C79, CD/4B62 not | [ted-events] |
| E14 | Perfect banquet score (Ribbon, achievement) | Quick Advice; 3.0.0 | PARTIAL | CC/91B6 (map 250) wired: the banquet switch translates now; 2 bit_set stubs (logic) left | the 2 bit_sets [ted-events]; play it [ted-ex] |
| E15 | Ruby's Shine | spoiler_free_new_quests; Mato README | PARTIAL | 5/5 events scripted, 20% stubs (`snes_event_ted_readme.json`) | [ted-events] |
| E16 | Test of Strength | same | PARTIAL | 9/11 scripted, 21% stubs | [ted-events] |
| E17 | Stolen Magicite (Catoblepas; Carbuncle in WoR) | same; 2.9.5 | PARTIAL | 1/1 scripted, 11% stubs | [ted-ex] |
| E18 | Deep Earth Dweller (Sealed Gate staircase) | same | MISSING | `snes_event_ted_readme.json` lists no events for it | find its events, translate [ted-events] |
| E19 | Gilgamesh: Encounter, Reunion, Battle on the Big Bridge? | same | PARTIAL | 4/4 scripted, 23% stubs | [ted-events] |
| E20 | Return of the Narshe Residents (refugees, Ragnarok, shops, new pub) | same | PARTIAL | Narshe NPC events partly scripted (CD/1540, CD/1650 yes; CD/1E40 no); no per-quest mapping | map the quest's events and wire [ted-events] |
| E21 | Seeking the Legendary Weapon (Ragnarok sword, Omega Weapon) | same | PORTED | CC/FF90 (map 401) wired: 0 stubs in 18 commands | play it in game [ted-ex] |
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
| E32 | A Demon's Favorite Food / Gau's father opens every Veldt formation | same; change §7 "Gau's Make-over" | PARTIAL | 2026-11-21 ted-events: Gau's father's 83 writes into the Veldt bits (CD/C113-C193) -> TED:veldt_open with the formations' PR parties (491); CB/681E itself not built (173 stubs: scene objects the PR room lacks) | CB/681E's NPCs [ted-events] |
| E33 | Thoughts and Wishes (Cid, Celes) | same | PARTIAL | 2026-11-21 ted-events: PR script edits (ted_events.SCRIPT_EDITS): sc_e_0625 gets CD/4130's tests (0C1 -> D56, 0CD -> D44, 0C9 -> D45 + the Celes/Locke scene, the Tynar Rouge) before 'I'm all better now'; sc_e_0616 doubles Cid's health per fish. Logic stub: one map load (warp) in the Celes/Locke scene; cosmetic: a song fade-in | the scene's warp; test in game [ted-events] |
| E34 | Owzer's Collection | same | PARTIAL | 5/5 scripted, 28% stubs | [ted-ex] |
| E35 | Unexpected Special Skill (Umaro's carving) | same | PORTED | CC/D6E1 (map 283, Umaro's Cave, Bone Sculpture, Berserker Ring): placed as a new object in Map_30771_1 (stand-in look); 16 stubs in 434 commands, all cosmetic (14 sound, 2 song_ctrl) | play it in game; its look (bc-sprites stand-in list) [ted-ex] |
| E36 | The Last Dragon (Fanatics' Tower, Dried Meat) | same | PARTIAL | CD/46B0 (map 364) wired: 4 stubs in 53 commands: 1 if_battle_bit_clear (logic), 3 sound | the battle-bit test [ted-events]; play it [ted-ex] |
| E37 | Molulu's Gift | same | PARTIAL | 3/3 scripted, 20% stubs | [ted-ex] |
| E38 | A Priestess's Concern (Sabin costume) | same | PARTIAL | 2026-11-21 ted-events: CA/6C7B (map 57 NPC 1) wired in Map_20371_6 (ev_e_0028 jumps into the PR's own sc_e_0028 for vanilla's part); bit 1C3 = Sabin's costume unlock -> TreasureFlag3 15 (ted_flags.json for TedPlugin). Logic stub on the second wiring (entity_default 12): a character rename (7F 05 05); cosmetic: sprite/palette | the rename on the second wiring; test in game [ted-events] |
| E39 | A Mother's Love (Terra costume, Maduin's house) | same | PORTED | CD/7D60, CD/7DD0 (map 468, sc_tedm_037D60/037DD0) and the room's 11 other events scripted with no stubs (ted_map_events_report 11-21) | test in game |
| E40 | A Duel! The Dragon's Neck Coliseum (Gilgamesh, Excalibur) | same | PARTIAL | 5/5 scripted, 29% stubs | [ted-ex] |
| E41 | Forever Ultros (help in Kefka's Tower) | same | PORTED | 7/7 scripted, 9% stubs | — |
| E42 | The Sealed Gate, Again (esper fight, elder, Terra's gear) | same | PARTIAL | maps 435/437/438: 10% stubs; 435's 50% = 2 bg_palette (60) stubs in a 4-op entrance (cosmetic, no PR op) | translator-level stubs (ted-events) |
| E43 | Wandering Shadow (WoR Floating Continent, Atma Buster) | same | PARTIAL | map 509: ted-maps' 2 events scripted, no logic stubs (1 screen, cosmetic); the room's other events are ted-ex's (data/ted_quests_maps.json) | ted-ex's events on 509 [ted-ex]; test in game |
| E44 | Know-It-All, the house north of Narshe | Mato README "Know-It-All"; history | PORTED | Know-It-All = Mr. Clio, map 415 NPC 0 (CD/FD10, 'I'm Mr. Clio. I know everything...'), room Map_20471_2 inside map 510 'Mr. Clio's Home'; placed with his look, script 10162 (retagged to ted-maps) |  |

### Pub quests

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| Q1 | Pub job boards (6 pubs) | Mato README "NEW PUB QUEST DETAILS" | PARTIAL | `tools/ted_quests.py` BATCH wired; ted-7 ted-quests: "sc_tedq_q_ca7d09_20071_4_d didn't start (not in map 42's list ...)" for 44 scripts | reinstall, rerun ted-quests [ted-ex] |
| Q2 | Cave Monster Cleanup (South Figaro, WoB) | same | PORTED | South Figaro pub group: all events built; 3 stubs in 568 commands, all cosmetic (2 spotlight, 1 song); no logic stubs (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q3 | Defend Mt. Kolts! | same | PORTED | South Figaro pub group: all events built; 3 stubs in 568 commands, all cosmetic (2 spotlight, 1 song); no logic stubs (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q4 | I'll Buy Anything! (Nikeah) | same | PARTIAL | Nikeah pub group: all events built; stubs: 10 random_jump + 2 gil_add (logic) | random_jump (BD) and gil_add translation [ted-events]; play it [ted-ex] |
| Q5 | A Helping Hand (Kohlingen) | same | PARTIAL | Kohlingen pub group: all events built; stubs: 1 case_test (logic), 3 mosaic + 2 sound (cosmetic) in 1,587 commands | the last case_test [ted-events]; play it [ted-ex] |
| Q6 | The Dream Opera | same | PARTIAL | Kohlingen pub group: all events built; stubs: 1 case_test (logic), 3 mosaic + 2 sound (cosmetic) in 1,587 commands | the last case_test [ted-events]; play it [ted-ex] |
| Q7 | Requiem (Setzer's lines) | same | PARTIAL | Kohlingen pub group: all events built; stubs: 1 case_test (logic), 3 mosaic + 2 sound (cosmetic) in 1,587 commands | the last case_test [ted-events]; play it [ted-ex] |
| Q8 | Transporting Goods (Albrook) | same | PARTIAL | Albrook pub group: all events built; stubs: 4 gil_add (logic), 1 mosaic (cosmetic) | gil_add translation [ted-events]; play it [ted-ex] |
| Q9 | Finding Food (Albrook WoR, repeatable) | same | PARTIAL | Albrook pub group: all events built; stubs: 4 gil_add (logic), 1 mosaic (cosmetic) | gil_add translation [ted-events]; play it [ted-ex] |
| Q10 | Wanted! Research Materials (scholar, Goddess Bell) | same | PARTIAL | Albrook pub group: all events built; stubs: 4 gil_add (logic), 1 mosaic (cosmetic); needs the Goddess Bell of N4 | gil_add [ted-events]; Goddess Bell (N4) [ted-maps]; play it [ted-ex] |
| Q11 | Defeat the Cave Monsters (South Figaro WoR, repeatable) | same | PORTED | South Figaro pub group: all events built; 3 stubs in 568 commands, all cosmetic (2 spotlight, 1 song); no logic stubs (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q12 | A Girl's Wish | same | PORTED | South Figaro pub group: all events built; 3 stubs in 568 commands, all cosmetic (2 spotlight, 1 song); no logic stubs (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q13 | Victory Drinks | same | PORTED | South Figaro pub group: all events built; 3 stubs in 568 commands, all cosmetic (2 spotlight, 1 song); no logic stubs (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q14 | Delivery Service (Nikeah, Duane) | same | PARTIAL | Nikeah pub group: all events built; stubs: 10 random_jump + 2 gil_add (logic) | random_jump (BD) and gil_add translation [ted-events]; play it [ted-ex] |
| Q15 | A Dancer's Depression (opens the Dressing Room) | same | PARTIAL | Kohlingen pub group: all events built; stubs: 1 case_test (logic), 3 mosaic + 2 sound (cosmetic) in 1,587 commands | the last case_test [ted-events]; play it [ted-ex] |
| Q16 | The Will to Live for Tomorrow (Phantom Forest foe) | same | PARTIAL | Nikeah pub group: all events built; stubs: 10 random_jump + 2 gil_add (logic) | random_jump (BD) and gil_add translation [ted-events]; play it [ted-ex] |
| Q17 | A Restful Sleep (Kohlingen, Darill's grave) | same | PARTIAL | Kohlingen pub group: all events built; stubs: 1 case_test (logic), 3 mosaic + 2 sound (cosmetic) in 1,587 commands | the last case_test [ted-events]; play it [ted-ex] |
| Q18 | Imitation's Secret (Narshe pub, Gogo's quiz) | same | PORTED | Narshe pub group (map 461 etc., 46 events on ted-maps' rooms): 5 stubs in 2,277 commands, all sound; the quiz's case tests and the field timers (TED:timer_start/reset) translate (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |
| Q19 | Night Patrol (timed, repeatable, reward changes) | same | PARTIAL | maps 473-476 scripted, 8-23% stubs; SNES:timer_start 6, SNES:timer_reset 14 stubs remain; the plugin side is in: TED:timer_start/_reset/_left (TedTimers.cs, on-screen countdown, expiry script) | ted-events: translate the timer stubs to TED:timer_* (format sent 11-21) [ted-events]; play it |
| Q20 | Super Doctor D (Zozo) | same | PORTED | Zozo pub: 2 events wired; 5 stubs in 242 commands, all sound; if_lead_status -> TED:leadstatus (06:36) | play it in game (quests-2 runs the scripts) [ted-ex] |

### NG+/post-game

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| N1 | New Game+ from the Beginner's House desk | change §1 "New Game+"; Mato README | PARTIAL | TED:ngplus (TedSysCalls): clears ted_flags.json ngplus_clear (491), sets ngplus_set (32), as T-Edition's C0/DB58 handler; items/characters/espers/gil/counters stay | ted-events wires the clerk's script; play it |
| N2 | NG+ carry-overs (items but key items, spells, espers, Lores/Rages/Dances, playtime, steps, success counters, achievements) | change §1 | PARTIAL | carry-overs are what T-Edition's handler leaves untouched (items, characters, espers, Lores/Rages/Dances, play time, steps, counters): TED:ngplus touches only story flags | play it |
| N3 | NG+ resets (formations met, pub quests, chests, Trance time, Terra's Trance, Deathgaze, Dried Meat; secret costumes re-lock) | change §1; Mato README | PARTIAL | resets: every story bit 000-2FF incl. costume/dream bits (ngplus_clear), NPC show bits to T-Edition's table (ngplus_set) | play it |
| N4 | Holy Angel Ultima chain (page, sylph, Phantom Forest, Matoya's Crystal Eye, Goddess Bell, Labyrinth of the Ancients, Crystal Tower, Ultima) | Mato README "High Seraph Ultima" | PARTIAL | maps 447-458, 417-420, 497-505 built; events scripted (1116 commands) | logic stubs: 1 untied_bit, 1 bit_set (vanilla bits with no PR tie) [ted-events]; the Goddess Bell airship landing not located [ted-maps]; cosmetic: 14 sound, 1 mosaic |
| N5 | Forbidden Land Eureka (optional, gear) | same | PORTED | maps 421-428 built and scripted (352 commands), no logic stubs (11-21); cosmetic: 3 sound, 1 mosaic | test in game |
| N6 | Soul Shrine (waves, re-fight chosen waves, shield on first clear, restart if left, save point, party change) | Mato README; soulshrine.txt | PARTIAL | maps 431-433 built; CD/12D0-CD/1340 scripted (3943 commands) | logic stubs: 4 party_map, 4 bit_set, 1 case_test [ted-events]; cosmetic: 4 sound |
| N7 | Developer's Room (after Ultima; lead-dependent reactions) | Mato README "Developer's Room" | PORTED | Developer's Room maps 463/464 built and scripted (2733 commands), no logic stubs since the translator knows each event's trigger (pressed_a, 11-21); script ids >= 10000 run (maps-2) | test in game |
| N8 | Secret Present (Eureka gravestone unlocks every costume) | Mato README "Secret Present" | PORTED | Eureka gravestone (map 428, sc_tedm_0451E0) scripted, no logic stubs (1B4 decided by pressed_a, 11-21); cosmetic: 2 sound | test in game |

### Costumes/dressing room

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| D1 | Dressing Room on the Falcon | change §3 "Dressing Room"; dressroom.html | PARTIAL | dressing room (map 459, sc_tedm_03ACB0, 6429 commands) scripted; costume switch TED:costume live on ArtSwap layers | logic stubs: 2 map_fade to SNES map 5 (CD/5A39, CD/7EEB; a blank 16x16 holding map with no PR pair) [ted-maps]; 16 bit set/clear + 7 tests on vanilla bits 124-126 (no PR tie) and engine bits A0-A3 [ted-events]. Cosmetic: 32 obj_palette, 2 obj_graphics |
| D2 | 56 costumes: field, battle and portrait art | dressroom.html; 3.0.7 menu images | PORTED | `tools/ted_art.py` costumes, `data/ted_costume_art.json`; ArtSwap layers (`Plugin.cs:55-59`) | — |
| D3 | Costume choice kept in the save | (system) | PORTED | `TedCostumes.cs:10-24` ("TEC1" block) | — |
| D4 | Unlocks by treasures, events, achievements (in order) | dressroom.html; Quick Advice | PARTIAL | unlocks listed in `data/ted_costumes.json`; achievements are U2 | [ted-maps] |
| D5 | "The Best Models": change clothes at 12 inns and halls | change §1 "New Game+" list | PARTIAL | TED:costume in inn scripts sc_tedq_e_cb4486 (Map_20151_5, 20191_2, 20331_2, 20431_5), sc_tedq_e_cc657d, sc_tedq_e_cc6140; not run | [ted-ex] |
| D6 | Falcon music by worn costume (53 songs) | dressroom.html; history | PORTED | 2026-11-21 ted-events: the Falcon's entrance (map 12, EB/0EA0) in TEditionEvents for Map_20391_1/2/3: the leader's per-character song (A5 -> TED:roster), then TED:falconsong (ted_events.ENTRANCE_TAILS) for the worn costume's song; 838 costume-sprite commands (37/43) are Nops | test in game: board the Falcon with and without a costume [ted-events, TedPlugin] |
| D7 | Job title follows the costume | EX history ("changing costumes now changes job titles") | PORTED | 2026-11-21 TedPlugin: costume job titles from data/ted_costumes.json (BepInEx/TEdition) | test in game; ship ted_costumes.json in the zip |
| D8 | Gogo's Chameleon Robe takes other characters' forms in battle | EX history | PORTED | `TedCostumes.cs:16-17` (10 forms) | — |
| D9 | Imp's Feelings / Piggy's Badge cosmetic relics | history ("2 new accessories") | PORTED | `TedCostumes.cs:17-18` (slots 277/278) | — |
| D10 | Costume stat bonuses | 2.9.x; removed in 3.0.0 | LEFT OUT | BATTLE_SPEC "Docs vs code": "The costume system changes graphics only ... Port nothing from it" (3.0.0 removed stats) | — |

### Music

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| S1 | ~200 new songs (two drivers, own samples) | change §1 "Added Music"; bgm.html | PORTED | `tools/ted_music.py`, `TedMusic.cs:15-56`; ted-7 "[ted music] 254 songs, 145 samples, 344 tracks, 191 areas, 478 battles" (loaded, not heard) | — |
| S2 | Area songs (66 new maps, 55 vanilla maps) | bgm.html | PARTIAL | of the 7 song maps: 217, 297, 344, 404 paired (door-confirmed); 317 Dream Dungeon, 358, 415 have no PR room by doors/tiles/entities | 317/358/415: name PR maps by hand or play the song from the event |
| S3 | Battle music per formation | change §1 "Battle Music - Fanfare Change" | PORTED | `ted_music.formation_music` (478 parties) | — |
| S4 | Victory fanfare per formation | same | PORTED | same (418 fanfares) | — |
| S5 | Songs and jingles in events | bgm.html | PARTIAL | translator emits bgm 1000+n; stubs left in mods/TEdition: `SNES:song_ctrl` 19, `SNES:song` 9, `SNES:sound_wait` 20 | [ted-events] |
| S6 | Music Player in Config > Sound (GBA-style), its 277 entries | change §1 "Music Player" | PORTED | 2026-11-21 ted_build calls ted_music.install_player: 175 Extras player rows (ids 159-333) and their names in 12 languages | test in game |
| S7 | Developer's Room music room: extra songs, patrons who comment on the song playing | Mato README | PARTIAL | TED:song [var] and TED:cmp 1300 give the song playing (pack slot, or a vanilla track's SNES song via ted_music.json pr_songs); the patrons' events are ted-events' | wire the Developer's Room patrons (ted-events) |
| S8 | Battle sound effects changed (FF5 Bio, whip, Time magic) | EX history | MISSING | no battle SE work found (`data/ted_se_ties.json` is field events only) | art/sound: needs the art owner (ted-maps) or LEFT OUT [lead decides] |

### Graphics

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| G1 | New monster sprites (incl. EX's) | change §6 "Monster Changes" | TESTED | ted-7 "[ted] monster images: made 226 of 226 (+226 bestiary thumbnails) from this game"; shot `ted_mon_30723.png` | — |
| G2 | Monster recolors and redraws in the vanilla range (52 recolors, 76 redrawn) | change §6 "Palette Changes" | PORTED | progress 11-20 (`tools/ted_art.py`: 174 new, 52 recolors, 15 swaps) | — |
| G3 | Characters redrawn to match official art (field, battle) | change §3 "Character Overview"; 2.9.5 | PORTED | `TedArt.cs:39` BaseLooks; ted-7 "[ted art] base looks: ... 833 sprites, 15 atlases" (loaded) | — |
| G4 | Default portraits redrawn | 3.0.0 | PORTED | `ted_art.py:284-317, 433` | — |
| G5 | Imp (toad) look, Mog's new pose | EX history | PORTED | progress 11-20 "the Imp, Kappa and Pig looks"; "Mog's 'new pose' is redrawn tiles only" | — |
| G6 | NPC sprites on the new maps (112 numbers) | MEDIA_INVENTORY §4.1 | PARTIAL | tools/ted_npc_art.py: 19 sprite numbers on free vanilla NPC groups + 15 on kit ArtSwap new_groups (mo_ted_sNNN) = 116 of 119 new-map placements with a sheet; served from costumes/default | 166-168 (33 NPCs) have no sheet in T-Ed's table: stand-ins; in-game check ted-10 |
| G7 | NPC and story sprites changed on vanilla maps (Kefka, Gilgamesh, Yura, Arvis, Jun) | 2.9.5; EX history | PARTIAL | Kefka (slot 21) and the merchant (224 over vanilla 49 everywhere: mo_ff6_n008_c00/c01) redrawn in costumes/default; Gilgamesh 221, Vargas 225, Arvis 176, Jun 171, sprite 95 on new groups, mapobject rows 3100-3104 (ted_npc_art.vanilla_looks); Yura (468, sprite 207) is vanilla 45's sheet | ted-events sets those NPCs' asset_id; in-game check |
| G8 | New and edited battle backgrounds (Crystal Room, Phoenix Cave fire, WoR variants ...) | background.html; 3.0.0 | PARTIAL | T-Ed's bg table (26F800, 6 B) + palettes (26FC00) decoded (tools/ted_battle_bgs.py): of 0-57, entries 4/10/43/49/56 are recolours, served as ArtSwap sprites at BG_FF6_05/11/44/50/57 from costumes/default (PR painting recoloured in Lab from vanilla to T-Ed palette); 5/42/45 need nothing. SNES battle-bg format solved, renderer matches the game (notes: ted-bg-new-design.md). In-game probe: QA ted-maps-5 | after ted-maps-5 proves ArtSwap reaches battle bgs: new entries 64-78 (14, on ~66 maps; recolours of vanilla graphics, 64/66/73/74 unchanged vanilla looks) as new PR groups bg_ff6_65+ (lead: battle_background_asset rows + porter map) [ted-maps]; 80 (new graphics, Fanatics'/Mirage Tower) with a known gap, stand-in: SNES render (softened 2x; painted art only from an artist later) |
| G9 | Collection Room paintings | Mato README "Collection Room"; history | PARTIAL | the Collection Room's paintings (map 469) are NPC sprites 191/195/198-202/213/214, not tiles; each gets T-Edition's own drawing via the G6 NPC art (ted_npc_looks 'ted art': new groups mo_ted_s191..s214, mo_ff6_n048_c05 for 195; frames in costumes/default/ted_npc_NNN.png) | see them in game: the paintings show once their EX boss bits are set (X8's play test, ted-ex); the group serving is proved by ted-10's mo_ted_s192 probe |
| G10 | Animations for new/changed spells (Blink, Flood, Comet, Toad, Holy's new graphic ...) | change §2 "Magic"; 3.0.0 | PARTIAL | port_report "spells using their own slot's look (no name match): 10:Toad, 19:Flood, 20:Scourge, ... 32:Comet, 50:Blink ..." | pick PR effects per spell [lead] |
| G11 | Casting motions (White, Summon), Time magic animation and sound, Trance casting, Cyan's battle entry | change §2 "Magic Casting Motions"; §3 | MISSING | no code | art/sound: needs the art owner (ted-maps) or LEFT OUT [lead decides] |
| G12 | MP damage in pink, MP healing in blue | change §2 "MP Damage/Recovery Display" | PORTED | 2026-11-21 TedPlugin: MP numbers in T-Edition's colours (kit SnesMpNumbers, reviewed) | test in game |
| G13 | Window types 2-8 after other Square games | change §1 "Window Type"; windowtype.html | LEFT OUT | the PR draws its own windows: T-Edition's SNES window types (after other Square games) have no counterpart; the PR's own window options stay (lead, 2026-11-21) |  |
| G14 | Weapon and item icons/battle sprites changed | EX history | PARTIAL | item identity: new rows take a template item's look (port_report "48 rows took their template's look") | [bc-sprites] |

### Menus/UI/rooms (Collection, Achievements, Track Record)

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| U1 | Collection Room (key items on display, paintings per EX boss) | Mato README "Collection Room" | PARTIAL | maps 470, 486, 487-490 built and scripted (868 commands); EX bits allocated (MEDIA_INVENTORY §4.4) | logic stubs: 3 untied_bit (vanilla bits with no PR tie) [ted-events]; cosmetic: 1 sound |
| U2 | Achievement Room: 2 rooms, hint books, 20 achievements, finale | Mato README "Achievement Room"; spoiler_free_new_quests | PARTIAL | map 471's 15 hint-book tiles scripted, no logic stubs (1B4 decided: read when stepped onto facing up; SNES also reads them with A on the tile, which PR step-on triggers can't). Map 472 is ted-ex's | the achievements on 472 [ted-ex]; no script uses TED:counter (TedSysCalls.cs:83-91); test in game |
| U3 | Track record: Steal, Twin Fang, Runic, Sketch, Slot, Snowstorm, Mimic counts | change §1 (NG+ list); spec 43 | PORTED | TedCounters (TED1 save block): Steal, Runic, Sketch, Slot, Snowstorm, Mimic counted; Twin Fang on Interceptor's block (TedCommands.Defend_Postfix) | check Twin Fang's exact trigger in game |
| U4 | Status screen pages: attributes, conditions, abilities | change §2 "Information Display on the Status Screen" | PORTED | TedStatusPage.cs: the free Level Up Bonus row shows elements (weak/resist/immune/absorb), status immunities by name and equipment effects (relic bits); tedstatus prints them | shot of the status screen in a run |
| U5 | Equipment details: MP Critical, absorb, Row OK, Throw OK, bonus vs flying/human/magic/dragon; Valiant Knife "???" | change §1 "Equipment Details Menu"; §5 | PORTED | TedEquipDetails.cs: EquipmentDescriptionWindowController.SetDescriptionText prefix adds a weapon's labels under its description; ted_data weapon_details (ted_plugin_data.weapon_details: byte $1B high nibble 4 humans/5 HP absorb/6 MP absorb/7 MP critical/8 flying/E magical/F dragons, checked against T-Edition's weapon guide by name; $13 bit 5 Row OK; $00 bit 4 Throw OK): 97 weapons | Valiant Knife's '???' not done; see it in the equip menu |
| U6 | X button: equipped esper, learning progress, mastered-esper star | change §1 "Magic Acquisition Status" | PORTED | the PR's own Magicite menu shows all three: MagicStoneListContentView masterImage (mastered mark) and equipIcon (equipped esper), MagicStoneDetails AcquisitionValue (learning progress per spell) (dump.cs 289750, 298264); T-Edition's X-button summary was the SNES menu's way to them |  |
| U7 | Select in battle: icons for Reraise, Defend, Runic, Sky, Charm, Love Token, Cloudy Heaven | change §2 "Information Display of Status Ailments of Allies" | PARTIAL | TedAllyStatus.cs: Select held in battle shows each ally's Reraise/Defend/Runic/Sky (PR ConditionType 602/1/612/626) in a box; harness tedallies prints the lines | Charm, Love Token, Cloudy Heaven are T-Edition mechanics with no PR status (port them first); words, not T-Edition's icons; check Select does nothing else in the PR's battle |
| U8 | Play time past 99:59 | change §1 "3 Digit Playtime" | PORTED | no cap in the PR: UserSaveData.playTime is an unbounded double, PlayTimeStringProvider.GetPlayTime formats hours unbounded (decompiled, tools/decomp/ted_umaro2) |  |
| U9 | Treasure message depends on the party lead | change §1 "Treasure Chest Message" | PORTED | TedChestLines.cs: EventActionTreasure.GetMessage prefix points the chest's T0001_01_01 at TED_CHEST_<lead 00-13> (T-Edition's EE dialogues 657-670, ted_plugin_data.chest_rule into system_en via ted_build data_rules); empty lead/Banon/Ghost/Leo keep the generic line | open a chest in game (English) |
| U10 | Rage list in alphabetical order | change §3 Gau | PORTED | TedRageOrder.cs: Gau's stored Rage entries kept in name order outside battle (OwnedAbilityList, every 2 s; the battle menu lists the stored order) plus the field menu's OwnedCharacterClient.Sort postfix for command 23 | see Gau's Rage list in battle |
| U11 | Hidden debug win (Select+Up) | spec 59 | LEFT OUT | spec 59 "do not port" | — |

### Text/translation

| ID | Feature | Source | Status | Evidence | Work needed [owner] |
|---|---|---|---|---|---|
| T1 | Full English names (items, spells, monsters, attacks) | Mato README FAQ | PORTED | `docs/tedition.md:29-31`; port_report "item text: 223 names/descriptions" | — |
| T2 | Descriptions for every item (GBA-style) | change §1 "Item Descriptions" | PORTED | progress 11-20 (Mato's descriptions); 327 MSG_*_INF rows in TEditionPort | — |
| T3 | Spell and Lore descriptions (19 characters) | change §1 "Magic Skill Description" | PORTED | MSG_MAG_INF rows (63) | — |
| T4 | Blitz, Bushido, esper and Rage descriptions (Rage menu shows the attack) | change §3 Gau; EX history | PORTED | 2026-11-21 lead: profile_tedition DESC_TABLES espers CF/FE40, blitz CF/FF9E, bushido CF/FFAE -> extra_messages ("descriptions: Mato's on 27 espers, 8 bushido, 8 blitz"); rage_descriptions() -> port_dances names 252 Rages' attacks | test in game |
| T5 | Mato's dialogue in new and changed scenes | Mato README FAQ | TESTED | maps-2: "Hummingway: Want to hear music not in the Music Player?" with Yes!/No! (`shots/maps2/sc_tedm_03FAA5_1.png`); Namingway (`sc_tedm_037370_1.png`) | coverage follows the event rows |
| T6 | Element names Fire / Earth / Darkness / Light | change §1 "Attribute Names" | PORTED | ted_plugin_data.element_names_rule (data_rules): MSG_SYSTEM_377 Poison -> Darkness, MSG_SYSTEM_375 Holy -> Light (the element keys; the Poison status keeps MSG_SYSTEM_112); English Fire / Earth were already right; English only |  |
| T7 | Job titles (Mog "Moogle Knight", others) | change §3 Mog; EX history | PORTED | MSG_JOB_NAME_11 Moogle -> Moogle Knight (ted_plugin_data JOB_TITLES); costume titles (D7) restore this base |  |
| T8 | Monster battle lines and battle messages | (AI F3) | PORTED | Mato's battle lines from its moved table (CF/E000, text bank 55; tools/ted_dialog.BattleMessages) as story_mes TED_BTL_<n>_<line>: profile_tedition battle_messages + battle_lines (port_ai's new profile hook); port_report: 211 lines, only message 62 (empty in the ROM) without one; test_mod OK on TEditionPort | see a line in a fight (Ultros 474) |
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
| X8 | Wins fill the Collection Room and count for "EX Complete" | EX readme.html §3 | PARTIAL | Collection Room (map 469, Map_20151_9) moved to ted-ex 11-21. E9/E700 (each EX painting hidden until its boss bit) and 21 plaque/painting tiles are translated through ted-maps' NPC entity ids; 34 stubs in 710 commands. Win bits are pinned (ScenarioFlag4 5-17). | paintings art (G9) [ted-maps]; play it [ted-ex] |
| X9 | Omega Weapon as a 13th fight with Mato's reward (steal Megalixir, drop Omega Weapon) | Hidden Secret Boss info | PORTED | `ted_ex_events.py` EX_PATCH (pack 168); EX_PLAN line 1 decision | — |
| X10 | EX room's Moogle: party and costume changes | EX readme.html §2 | PORTED | Traced: EX 2.0.6's room Moogle (CD/A780) offers the fights only (13 with Omega). Its scene, the room's entrance (EA/0000) and NPCs have no party or costume ops; the shopping is the two shopkeepers (EX shops 128/129). Ported in mods/TEditionEX: 16 scripts, 0 stubs in 264 commands. Map 467's NPCs (CD/80F0/80F4, Mog House lines) are in TEditionQuests, 0 stubs. The readme's party/costume change isn't in EX's code: T-Edition's Dressing Room (D1). | play the room (QA ted-ex-bossroom) [ted-ex] |
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
