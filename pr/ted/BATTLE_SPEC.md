# T-Edition battle spec (session ted-battle, 2026-11-20)

The spec plugin/TedPlugin is written from. Addresses: JP v1.0 / T-Edition unless marked US (the
JP->US pairs are in "Addresses" below; BNW's source and the community disassemblies use US).
Sources read: T-Edition 3.0.7 (Mato) code, its own change list and version history (Lua package
`HTML (TRANSLATED GUIDES...)/change.html`, `history.html`; text copies in this session's scratchpad
`ted_docs/`). Where the docs and the code disagree, the code is the rule (listed under "Docs vs code").
Character commands and statuses were read by two helpers: `ted-battle-commands.md` and
`ted-battle-status.md` in this folder (their rules are summarized in the table; details there).

## Tools (kit + T-Edition)
- `pr/tools/snes_disasm.py` (kit): 65816 disassembler (Rom: HiROM/ExHiROM/LoROM; linear and recursive
  tracing with M/X widths, PHP/PLP, jump tables, labels, xrefs, ROM table reads; `align` pairs two
  builds' instructions for JP<->US). Tests `pr/tests/test_snes_disasm.py` (8 OK): vanilla listings
  quoted in BNW's source, 471 of 501 BNW 3.0 `org` blocks (3,213 instructions) decode as written from
  BNW's ROM, a clean trace of US and JP C2 (0 width conflicts), JP/US alignment.
- `pr/tools/ted_battle.py`: T-Edition vs JP report -> `pr/build/t-edition/battle_code.txt` (+ `.json`):
  309 changed runs in C2 (259 in C1, 495 in C3 menus), each with JP and T-Edition code side by side, the
  US address and BNW's c2.asm section name, change class (hook, moved table, constant, retarget,
  code, changed jump-table entries), the 314 hooks, 843 new routines with callers/calls/tables, a labelled listing of all new
  code. `ted_battle.py at 47/0CE4 -n 60` lists one routine (cached, <1 s); `ted_battle.py jp C2/2C3B`
  maps JP -> US + BNW section; `--ex` does the same for EX.

## How T-Edition's battle code is laid out (needed to read anything)
- Hooks in C1/C2/C3 jump (JSL/JML/JSR/JMP) into new code in banks 40, 41, 4E, 58, CE and space freed
  in C0 (C0/D800-DFFF), C2 (C2/6450-67FF, C2/FA00-FFFF).
- **Bank 47 is a modified copy of T-Edition's C2** (63,932 of 65,536 bytes equal). Several hooks are
  `JML $47xxxx`: execution then stays in bank 47 (its JSR/JMP/branches are bank 47's) until a JML
  back; at worst until the main loop's next pass through C2/0019 (`JML 40/0100` -> `JML C2/001E`).
  Bank 47 still has older rules in places (Steal +50 and rare 1/8, desperation 1/2, Trance x2,
  vanilla pre-strike table): those run only after a bank-47 entry in the same loop pass (Sketch,
  AI command $30, Runic absorb, Interceptor counter, monster load, effect $4E). The port follows C2. On those paths bank 47's version is the one that runs (e.g. the Defend/back-row code at
  47/0CE4-0D1C, Valiant/GP Rain at 47/3F9F). Bank 40 likewise holds a copy of C0 (40/A02C...).
- Tables T-Edition moved (long loads; profile_tedition.py has most): items ED/8F00 (30 B), monsters
  57/3E00 (32 B x 512), steals+drops 41/EA00 (8 B), AI 5F/58F0 (ptrs) / FF/F300, formations CF/5900,
  formation flags CF/2400, command remap 40/3000 (CMP $403000,X / SBC $403010,X in C2/2703, new
  command ids $A4-$AD), HP growth 41/DD00, MP growth 41/E320, natural magic EC/E3A0 (Relm, new) +
  EC/E3C0 (Terra) + EC/E3E0 (Celes), Bushido/Blitz levels E6/F490/F498 (as vanilla).
- New RAM: $3E90 (target index saved in hit determination, C0/D800), $3E92 (attack kind for the
  half-damage check), $63A0,X (40/01E0), $6434/$6436 (CE/0050, CE/0090), $1440-$144D (4E/0A00..,
  cleared at battle end by 4E/1190), monster flag $3C95 bit 1 (monster byte $12 bit 1, unused in
  vanilla) = "half damage from ignore-defense attacks".

## Rule table
Kind: **data** = the porter writes PR data (csv/constants); **kit** = plugin code that belongs in
PrKit/Ff6 (other mods use or will use it); **ted** = TedPlugin-only code. PR hooks named from the
decompile/BNW's plugin (tools/decomp, plugin/BnwPlugin).

| # | Rule (T-Edition 3.0.7 code) | SNES (JP; US) | Kind | PR implementation |
|---|---|---|---|---|
| 1 | Drops: one roll per dead/petrified/zombie monster; r<174 slot 0, <224 slot 1, <244 slot 2, else slot 3 (67.97/19.53/7.81/4.69%); empty slot = no drop | 41/D300 from C2/5F06 (US 5F1E) | data | monster.drop_rate 100, MONSTER_DROP_RATE_0..3 = 68/19/8/5 (rest 0), 4 drop slots from 41/EA04 |
| 2 | Steals: 2 bytes at 41/EA00+8*id -> $3308 (rare, common) | 41/D32D from C2/2C3B (US 2C40) | data | as vanilla layout; Steal formula: see commands |
| 3 | HP/MP growth per character: HP gain = 41/DD00[112*char + level-2], MP 41/E320[...] (chars 0-13); guests (id >= 14) keep the shared E6/F49E/F500 tables | 41/D200 from C2/60CF (US 60E7); joining at level L: 41/D100 from C0/A1FE (sums levels 2..L) | data | porter: per-character growth (lead) |
| 4 | Espers give no stat bonus at level-up (the esper bonus call JSR ($6136,X) is skipped for everyone) | C2/60B2-60DE | kit (exists) | SnesEsperBonus with every bonus "none" (or the porter's esper data) |
| 5 | Relm learns magic by level: 16 (spell, level) pairs at EC/E3A0 (Terra E3C0, Celes E3E0); level-up check C2/FB96 replaces JSR $619E | C2/60A4 (US 60BC) | data | porter: natural magic table for Relm (profile_tedition reads only Terra/Celes at 0x2CE3C0) |
| 6 | Elements: damage split evenly over the attack's n elements (n counted before ForceField); per element: absorb -1, null 0, resist 1/2, weak or neutral 1, ForceField-nulled 0; sum < 0 heals; result = share * sum (+ remainder); overflow -> 16383 | C2/FAD0 from C2/0BD0 (US 0BD8) | ted | GetMagicStatus/GetFightStatus postfix (BattleFormulas pattern) with the target's element lists (EnemyCharacterParameter.ConfirmedResistanceAttributeList, as BNW's EngineRules elemental share) |
| 7 | Weakness: no x2; the target's Defense (physical) or MDef (magic) is quartered when any of the attack's elements is a weakness | C2/6560 from C2/0CC3 (US 0CCB) | ted | same hook: rescale the PR's defense step (255-Def/4)/(255-Def) |
| 8 | Ignore-defense attacks go through the defense step with Def/MDef 0 (so Safe/Shell, Defend, back row, Morph reductions now apply to them: Shell cuts heals and ignore-defense magic to 170/256) | 40/0140 from C2/0CB2 (US 0CBA) | ted | damage postfix: apply the PR's Safe/Shell/row/Defend factors to flag-5 ("ignore defense") abilities |
| 9 | Half damage from ignore-defense attacks for monsters with byte $12 bit 1 ($3C95 bit 1), also for attack kind $3E92 = $14 | C0/D854 from 47/0D1C (US 0D24) | ted + data | porter exports the flagged monster list; damage postfix x1/2 |
| 10 | Physical Defend 1/2 (unchanged); magic Defend x170/256+1 (new); back row (physical) x170/256+1 (was 1/2); magic on Morph/Trance target x170/256+1 (was 1/2) | 47/0CE4-0D1C via C2/0CF8 (US 0D00), C2/FA66 | ted | damage postfix factors ("Defend"/"Row" corrections, as BNW's BattleFormulas) |
| 11 | Golem/Interceptor block: the blocker's defense 119 (vanilla 192) | C2/0CD8 LDA #$78 (US 0CE0) | ted | low priority (needs the dog/golem block hook) |
| 12 | Damage and healing cap 32000 (9999) | C2/0C88 (US 0C90) | data | game_constant_int MAX_HIT_VALUE 32000 (check the PR draws 5 digits) |
| 13 | Two-handed (Gauntlet): no BP x1.75; instead damage incrementor +2 ($BC: +50% each) = final damage x2 | C2/2BBC (US 2BC1) | none | the PR's TwoHandedMagnification is already 2 |
| 14 | Dual wield (Genji): the vanilla -25% only for plain physical attacks ($11A2 == 1); Offering halving unchanged | C2/65E0 from C2/2C06 (US 2C0B) | kit | SnesRelicPenalties with "Genji only on Fight" |
| 15 | Earring/Atlas-type boosts: +25% once (no stacking: the x2-boost branch NOPed) and they now boost healing magic too | C2/0D47, 0D62 NOPs (US 0D4F, 0D6A) | kit | GetAccessoryMagic/PhysicalCorrectionValue postfix (BNW RelicRules pattern): cap at one boost; heals counted |
| 16 | Hawk-eye weapons (effect 8: Cards, Darts, Tarot, Antares): x2 ($BC+2) against a Float target ($3EF9 bit 7) when the command is Fight, nothing otherwise (vanilla: 50% +1, then +3 vs Float under Fight). change.txt's "flat x1.5" is wrong | C2/38EE-3904 (US 38FE) | ted | weapon effect hook (BNW WeaponProcs pattern) |
| 17 | Atma Weapon: Level -> 2*min(Stamina,127) in vanilla's formula damage*(Lv*(HP/256+1)/(MaxHP/256+1))/64+1; sprite thresholds 2000/5000 | 40/78A0 via C2/0E3A->0CB6 (US 0E42) | ted | Atma special function: decompile the PR's Atma calc (unknown hook) |
| 18 | Critical hits: random(256) < 20 (7.8%; vanilla < 8 = 3.1%) | C2/33FE (US 3403) | data | weapon.csv critical_rate 3 -> 8 (the PR keeps the rate per weapon: 90 weapons at 3, monsters 0) |
| 19 | Physical evasion uses Evade ($3B54), magic MBlock ($3B55): vanilla's carry bug fixed | C2/2327, 233A (US 232C, 233F) | none | the PR already uses Evade (PORTING "Evade works") |
| 20 | Blind attacker: physical hit rate halved (vanilla's code, now reached); target's $3C58 bit 2: halved too | C2/2345-2354 (US 234A) | kit | BlindRules variant: halve instead of BNW's 50 |
| 21 | No hit-rate change from target statuses (both PEA status lists zeroed) | C2/2356, 236D (US 235B, 2372) | kit (exists) | SnesHitRates with empty lists |
| 22 | Image: 50% to lose Image per dodge (vanilla 25%) | C2/232C (US 2331) | data | condition.csv Image until_value (BNW set 33 for 1/3) -> 50 |
| 23 | Vanish + Death fix: a vanished target immune to instant death ($3AA1 bit 2) is no longer auto-hit by Death, percent-damage or effect-$3E attacks (they take the normal hit roll) | 4E/1120 from C2/221B (US 2220) | none | the PR already fixed Vanish + Doom (patch 1.0.5) |
| 24 | Encounters: Back Guard bit moved to relic byte $3A6D bit 6 (vanilla bit 1); preemptive relic bit 5 multiplies the chance x4 (vanilla bit 0, x2); base preemptive 32/256 normal, 56/256 side (unchanged code); type weights unchanged (C2/5251+$10) | 47/2E30 from C2/2E35 (US 2E3A); 47/2EA5 from C2/2EA8 (US 2EAD) | data | game_constant_int encounter/preemptive rates by relic; relic bits in item data (porter) |
| 25 | Monster stats/AI/formations/items read from the moved tables | C2/2CA0-2E30 etc. | data | porter (profile_tedition) |
| 26 | New spell special effects (per-target table C2/42C9, dispatch C2/3E6D = US 3E85): $14 -> C2/651A, $46 -> 6527, $47 -> 6590: extra strikes $3A70 = 2 / 1 / 7 (3, 2, 8 hits) with $BA bit 6 set; $4E -> 47/1823; $0E/$0F now do nothing (3E72). Per-weapon table C2/3DB5 (dispatch 3881): effects $0E/$0F -> new 3EB2/3EBE | C2/42E5-4367, 3DD1 | data + kit | the PR's multi-hit abilities (ability data: hit count) where the PR has the shape; else a hook. Which abilities use them: spell byte 'special effect' in T-Edition's spell table |
| 27 | Steal: C = Lv + 70 - target Lv (vanilla +50), x2 with Enhanced Steal ($3C45 bit 0); success if random(0..99) < C (C >= 128 or Lv+70 >= 256 sure); rare slot 64/256 (vanilla 32); success count $1E70 (cap 510) | C2/39AB, 39CD (US 39BB, 39DD); CE/0120 | kit | CalcControllerProvider.GetStealStatus postfix (BNW CommandRules pattern); counter in ModSaves |
| 28 | Orichalcum (item $66): battle power = min(steals/2, 255) from $1E70 | CE/0140 from C2/29C9 (US 29CE) | ted | weapon attack hook (ConfirmedAttack / GetArmConfirmedAttack prefix, as RelicRules) + saved counter |
| 29 | Gil Toss: cost Lv x180; characters deal cost/2 (= Lv x90) to every target, no split; monsters pay from their gold and deal paid/2/targets | 47/3F9F (C2 entry 3F9F, US 3FB7) | ted | the PR's GP Rain function (decompile its cost/damage) |
| 30 | Sketch: hit min(1, RelmLv/TargetLv), brushes with Enhanced Sketch use TargetLv x170/256; 25% Wishing Star / 75% the monster's move (sketch table CF/1200 = data); sketched attacks use Relm's Mag.Pwr (C2/6710) and battle power (CE/0000) | C2/378D, 2B78, 2BA8 (US 2B7D, 2BAD) | data + ted | sketch odds/data via the porter; the stat swap as a damage-input prefix |
| 31 | Relic command swaps (8 entries, CE/01E8 -> CE/01F8 by $11D6 bit): Dance->Animal, Sketch->Spirit, Runic->Pray, Fight->Jump, Magic->X-Magic, Trance->Shock, Slot->Gil Toss, Steal->Mug; Spirit casts Bless $EC, Pray casts Sunbath $66, Shock spell $82, Animal one of spells $75-$7C (~1/8 each) | C2/5390 (US 53A8), 47/6740, 47/6789 | data + kit | the PR's accessory command changes (data where it has them: Thief Gloves etc.); new commands = command rows casting a fixed / random ability |
| 32 | Control removed (command $0E now Snowstorm: spell $54, all enemies); escape effect $A8 now always fails | C2/FB64, C2/3B59 | data | command data |
| 33 | Dance: one action, no lock, no stumble roll; steps 112/96/32/16 of 256 (vanilla code); Dancing Dagger: 50% a uniform dance move $65+random(16) | C2/178F-1798 (US 1794), C2/6740 via 3F91 | ted (+ data) | the PR's Dance continuation (decompile) + a weapon proc |
| 34 | Gau: learns the Rages of every formation monster with id < $100 on any victory with Gau in the party; Veldt registers any formation < $200 | C2/5ECD (US 5EE5), C2/49D4 | ted | victory hook (BNW BattleRewards pattern) |
| 35 | Gogo/Umaro may equip espers and learn magic (character-id limit $0C -> $0E) | C2/5574, 56B4, 5E44 | data | PR character flags |
| 36 | Umaro controllable; Fight picks from the vanilla weighted table: none 159/96 Fight/Charge; Berserker Ring adds Throw Ally, Power Belt adds Rampage (spell $EF) (full table in the commands file) | C2/091E, 1636 (US 0926, 163B) | kit | SnesUmaro (already the SNES odds) with T-Edition's relic ids and Rampage; controllable = drop the PR's auto-act |
| 37 | Slot: Mysidian Bunny heal = Lv x power, not split (effect $2A at C2/40F7, divide NOPed at 4115); Seven Flush/Dive Bomb data | C2/4115 (US 412D) | ted + data | ability data + heal hook |
| 38 | Interceptor: blocks a physical single-target hit 171/256 (code's branch is reversed: docs say 33%); counter 50%, always Twin Fang ($84) | C2/2283 -> FB84 (US 2288), C2/4CC7 | kit | WildFangConditionFunction.CheckDefendInvoke rate (BNW CoverRules hook) |
| 39 | Desperation: 1/32 per Fight while Near Fatal (docs say 1/8), no 768 timer, unlimited, Gau/Umaro/Gogo have one; skipped with the Offering (relic proxy $EE) or Elven Darts ($6C) in hand | 40/3700, C2/15CC-15FD (US 15D1-1602) | ted | the PR's desperation trigger (decompile) |
| 40 | Trance: attacker +1 $BC (x1.5, vanilla x2); magic taken x170/256 (rule 10); "no boost for non-elemental" not in code | C2/335F (US 3364) | ted | damage postfix |
| 41 | Dice: product x2 x Lv (2 dice) or x round(3Lv/4) (3 dice, C2/67C0), triples x face; /16 against $3C95 bit 1; $BC cleared (no Berserk boost); Fixed Dice hit 100 and dodgeable | C2/4140 (US 4158), C0/DA39, 40/01A0 | ted | the PR's Dice function |
| 42 | Bushido Tiger = MaxHP - HP (Revenge effect, data); Tiger Rush 3 random hits (effect $14); Phantom Rush physical; Throw loses the built-in x2 ($BD = 0, C2/1888); command wait times table C2/067B (Magic 30, Bushido 40, Blitz 40, Lore 40, ...) | see commands file 13 | data + ted | ability data; the wait table vs the PR's per-command wait (decompile) |
| 43 | New success counters $1E70 Steal, $1E72 Twin Fang, $1E74 Runic, $1E76 Sketch, $1E7A Slot, $1E7C Snowstorm, $1E7E Mimic (cap 510; carried into New Game+) | CE/0120, 47/1545.., 40/0A00, 40/0A20 | ted | ModSaves "TEdition" fields; only Steal's matters to battle (Orichalcum) |
| 44 | Action freeze: while an action plays, ATB, command waits, the status clock and the battle clock all stop (Active and Wait); $2F41 bit 1 set by four C1 animation sites, cleared by the main-loop hook | C2/1119 (US 1121), C2/2479-247F, 40/0000-00C0, 40/0100 | kit | BNW's NatbRules does the same for ATB/chant: move it to the kit (prefix on BattleProgressATB.UpdateGaugeIncrease/UpdateChantTime) and hold SnesStatusClock too |
| 45 | Battle speed: monster ATB factor 255 - 4*speed (vanilla - 24*speed; ~19% faster monsters at the default); Haste 96/64 (vanilla 84), Slow 32 | C2/2482 (US 2487), C2/09DA (US 09E2) | kit (config) | SnesAtb / SnesStatusClock constants per profile (AddHaste 96, speed term 4) |
| 46 | Command wait times: table C2/067B (Magic/Throw/Tools/Rage/Mimic/Dance/X-Magic/Spirit 48, Bushido/Blitz/Lore 64, Sketch/Slot/Gil Toss 32; Fight/Item/Steal 16) | C2/067B (same in US) | kit (data) | SnesCommandWait table by PR command |
| 47 | Near Fatal at HP <= MaxHP/4 (vanilla /8); Cover, desperation, SOS relics follow the status | C2/4523 (US 453B) | data | game_constant_int RATE_HAVE_NEAR_DEATH 8 -> 4 |
| 48 | "Critical Health": the six percent spells inflict only Near Fatal + vanilla's "miss if immune to all its statuses", so monsters immune to Near Fatal (byte $15 bit 1; 229 of 512) dodge them; death immunity no longer matters | C2/4444-4462 (US 445C), data | data | spell/monster data; check the PR applies "all statuses resisted -> miss" to damaging spells |
| 49 | Percent damage: the 10 listed spells (Gravity 1E, Tornado 34, Shamshir 6E, Cave-In 72, Magic Hammer 9D, AE, Whirlwind B2, Gravija BD, Launcher CD, Missile DD) keep vanilla (current HP - pending, min 1); all others (Diabolos 3/4, Wave Cannon 9/16, revives, ticks) use max HP, no minimum 1, cap 999 only with $11A7 bit 2 (ticks) | 40/7680 from C2/0D7F (US 0D87), C2/0D83 | ted (+ data) | the PR's percent formula types (current vs max) as data where they exist, else a damage hook |
| 50 | Poison 1/8 max HP, Regen 1/8 max HP (party) / 1/16 (monsters), no Stamina, Disease (Sap) and MP Slip 1/16 max MP (docs say 1/8), all capped 999, no Poison growth, then the element step (absorbers heal); cadence vanilla | C2/500A-5038 (US 5022), 40/3030 | kit | StatusTicks amounts (BNW StatusTicks pattern) on SnesStatusClock |
| 51 | Stop 9 status steps (vanilla 18); Sleep 18, Reflect 26, Freeze 34 unchanged; Sleep/Muddle broken by physical hits (vanilla) | C2/4668 (US 4680) | kit (data) | SnesStatusClock.StopSteps 9 |
| 52 | Status setting: removals of status 1-2 ignore immunity; Slow immunity no longer implies Haste immunity; being removed from battle (not by Jump) strips Reraise ($63A0); the $6434 gate (equipment statuses beat immunity, see unknowns); the undead-Life exemption reads a stale table EA/7000 (wrong monsters exempt) | C2/43B0, 26B8, 457A, 21D6, 0FA2, 44FF, 45FC, 4421 | ted | status-set hooks; implement the documented intent (Cursed Shield statuses stay with a Ribbon), not the gate's all-immunities reading |
| 53 | Reflect: bounced magic not halved (split for 2+ targets still applies first, so 3+ reflectors out-damage one hit) | C2/34B8 NOP (US 34BD) | ted | the PR's reflect damage (decompile) |
| 54 | Drain/absorb uncapped: the drainer gets the full computed damage (vanilla capped at the victim's HP/MP and the drainer's missing HP/MP) | C2/0DE5 = RTS (US 0DED) | ted | absorb hook |
| 55 | Espers can be summoned again (the $3F2E "summoned" mark is never set); costs are data | C2/4D88 NOPs (US 4DA0) | ted/data | the PR's one-summon-per-battle rule (decompile) |
| 56 | Coliseum fights and Umaro open the command menu | C2/0126, 092A, 091E | ted | the PR's Colosseum auto-battle and Umaro's auto-act |
| 57 | Reraise revives with spell $2D, Doom expiry casts $E8 Kill, SOS relics cast $29/$28/$31 | C2/079C, 5BAF, 0A62-0A7E | data | spell ids (porter) |
| 58 | Veldt registers any won formation <= $1FF; Shadow never leaves at random | C2/49D4, 486F (US 49EC, 4887) | ted | Veldt hook (kit Veldt code); Shadow: event/battle-end hook |
| 59 | Hidden debug win: default font colour + Select+Up kills all monsters once per battle | C2/6426 via 40/0100 | none | do not port |
| 60 | Valiant Knife no longer ignores defense (its effect's TSB $11A2 NOPed); its MaxHP - HP bonus stays | C2/3F73 (US 3F8B) | data | clear the PR's ignore-defense flag (content flag 5) on its ability |
| 61 | Magitek for everyone: six spells $85-$8A; a confused/uncontrolled pick is $85 + random(3) | C2/058A, 4E2B; menu not located (C1) | data | the PR's Magitek ability list per character |
| 62 | Cyan's gauge speed, "Runic speed", Offering's "normal accuracy, no procs" | not located (C1 battle menu / animation code, or not implemented) | ? | check in game against vanilla before writing code |
| 63 | Plain data the porter already carries (no engine rule): ninja swords dual-wield and Edges, Bushido/Blitz/Tools/Lore numbers and accuracies, Celes's magic, Strago's lores, new item types, MP costs of espers, the Veldt's formations | item/spell/esper tables | data | porter (profile_tedition) |

## Docs vs code (3.0.7)
- Defend: change.txt says physical 1/3; code (47/0CE6) halves physical, history.txt agrees ("block
  1/2 of a physical attack, now also 1/3 of magical").
- Ignore-defense: change.txt says party physical Def 1/2; code (40/0160, 40/0180) uses 0 for every
  case (both CPX #$08 branches load 0).
- Elements: change.txt's example (weak water + null ice) says "magic defense 1/4 ... ice nulled and
  damage halved": code agrees (MDef/4, then the ice share 0, water share 1 -> half).
- Two-handed: "double damage" = the PR's own x2 (vanilla x1.75 BP).
- Preemptive "twice the original" base: not found in code (the base is vanilla's); the relic's x4 is.
- The back/pincer/side "random number bug" fix: not found in C2 (C2/522F and its weights unchanged);
  the visible change is the Back Guard bit; may be in the formation flags data (porter) or C0.
- Drops: docs 68/20/8/4; code 174/50/20/12 of 256, and ids 32+ get other odds (bug, below).
- Interceptor: docs 50% -> 33%; the code's branch is reversed: blocks 171/256 (67%).
- Desperation: docs 1/16 -> 1/8; code AND #$1F = 1/32.
- Darts/cards vs flying: docs flat x1.5; code x2 against Float, Fight only.
- Dice vs "piercing-resist": docs x1.06; code /16 (1/16 mistranslated).
- Gil Toss: docs say enemies keep vanilla; they pay x180 too and deal paid/2/targets.
- Trance "no boost for non-elemental": not in code.
- Disease: docs 1/8 MP; code 1/16. Stop: docs "Sleep longer"; only Stop got shorter (9 steps).
- Monster ATB 255 - 4*speed: in code, undocumented (docs say the battle-speed change was reverted).
- Costumes: the 22-byte character table at 40/3100 (file 0x403100) is an older copy of ED/7CA0
  (5 records differ: Locke Attack 14 vs 19, Gogo's commands, guests 16/17/19), identical in EX, and
  no code reads it (searched all traced long operands and pointer setups). The costume system changes
  graphics only (change.txt: field/map/battle sprites). Port nothing from it.

## Drop quirk (for the record)
r = byte at C0/FD00 + ((id*8) & $FF00) + $1F6D (field RNG index, incremented): X is 16-bit, so ids
32+ read ROM past the 256-byte table. Real odds per 32-id band: 0-31 68/19.5/7.8/4.7; 32-63
93.8/1.6/3.5/1.2; 64-95 71.5/10.9/10.5/7.0; 96-127 76.6/11.7/10.2/1.6; 128-159 53.9/9.4/33.2/3.5;
160-191 74.6/15.6/6.2/3.5; 192-223 74.2/18.0/7.4/0.4; 224-255 77.0/16.4/5.9/0.8; 256-287
77.0/9.4/11.7/2.0; 288-319 81.6/7.4/6.6/4.3; 320-351 78.5/10.2/10.2/1.2; 352-383 79.7/12.5/3.9/3.9;
384-415 67.2/21.1/10.9/0.8; 416-447 88.7/9.0/2.0/0.4; 448-479 85.2/9.8/4.3/0.8; 480-511 81.6/7.0/8.2/3.1.
Decided with the lead (2026-11-20): the port uses the intended odds (profile_tedition.DROP_ODDS
68/19/8/5, drop_rate 100, empty slot = nothing); the overrun is a known T-Edition bug, not replicated.

## EX (T-Edition EX 2.0.6, Mato)
- Same battle engine: C2 differs from T-Edition only in table operands (monsters EA/7000 instead of
  57/3E00, AI pointers E9/7000 instead of 5F/58F0, two formation-id constants $2E9->$2D7 and
  $2EA->$2D8 at C2/2F73, 5D7F) and C1 by 3 bytes, C3 by 37 (menus); bank 47 the same 11 spots.
- EX-only: C2/271B and C2/2A5E JML to 4E/0568 / 4E/05A0: item data index + $1E00 (a second 256-item
  table at ED/AD00) when $1440 bit 0 is set (the EX dungeon's item set, presumably); 4E/1516-1535
  use spell ids $F5/$F7/$F6 (T-Edition $0B/$08/$09); 40/7683 the fraction-damage spell list differs
  (first id $AC instead of $1E); data banks 41 (growth, drops), 58, CE differ (EX's own data).
- For the merged mod: EX's monsters/AI/formations/items come from the EX ROM at those addresses
  (porter); the plugin needs nothing EX-specific except the $1440-bit-0 item switch if EX items are
  kept as separate PR items (then nothing at all).

## Addresses (JP -> US) of the vanilla code touched
C2/0019 0019, 0B7B 0B83, 0BD0 0BD8, 0C88 0C90, 0C96 0C9E, 0CB2 0CBA, 0CC3 0CCB, 0CF8 0D00, 0D09 0D11,
0D16 0D1E, 0D1C 0D24, 0D42 0D4A, 0D7F 0D87, 0E31 0E39, 0E3A 0E42, 2208 220D, 221B 2220, 2327 232C,
232C 2331, 233A 233F, 2345 234A, 2356 235B, 236D 2372, 2B98 2B9D, 2BA8 2BAD, 2BBC 2BC1, 2BFD 2C02,
2C06 2C0B, 2C2B 2C30, 2C3B 2C40, 2E35 2E3A, 2E96 2E9B, 2EA8 2EAD, 33FE 3403, 3706 370B, 38EE 38FE,
4B42 4B5A (random 0-255), 4B4D 4B65 (random 0..A-1), 4769 4781 (8x8 multiply), 477A 4792 (16/8
divide), 479F 47B7 (24-bit multiply), 51F6 520E (count bits), 522F 5247, 5F06 5F1E, 60A4 60BC,
60AA 60C2, 60CF 60E7. Every other one: `ted_battle.py jp ADDR` (JP code = US code shifted; C2
offsets grow from 0 at C2/0000 to +$18 by C2/4B00).

## Implementation plan (TedPlugin classes; kit where shared)
- Data (porter, lead): drops (68/19/8/5, drop_rate 100), growth, Relm's natural magic, cap 32000,
  Image 50, weapon critical_rate 8, RATE_HAVE_NEAR_DEATH 4, encounter/preemptive constants, empty
  esper bonuses, monster half-damage flag list, spell ids (Reraise/Doom/SOS), sketch table, command
  data (Snowstorm, Spirit, Pray, Animal, Fight for Gau), Gogo/Umaro magic flags.
- kit, already there: SnesHitRates (empty lists), SnesEsperBonus, SnesRelicPenalties (add a
  "Genji only on Fight" option), SnesStatusTicks/SnesStatusClock (status timers: see status file),
  NatbRules (BNW's action freeze: T-Edition's ATB freeze is the same idea; move it to the kit as
  SnesActionFreeze with BNW and TedPlugin both using it; see status file).
- kit, new: AccessoryBoost (non-stacking boosts + heals; BNW RelicRules' hooks), BlindHalving.
- TedPlugin classes:
  - TedDamage (rules 6-10, 17, 40, 49, 53, 54): one postfix on CalcControllerProvider.GetFightStatus /
    GetMagicStatus / GetRecoveryStatus computing T-Edition's steps from the PR's inputs (elements,
    weakness, defense 0 for ignore-defense, Defend/row/Morph/Shell factors, half damage on flagged
    monsters, Trance x1.5, percent damage base), like BnwPlugin/BattleFormulas; logs each rule once.
  - TedCommands (27-39, 41-43): Steal/Orichalcum (with ModSaves "TEdition" counters), Gil Toss,
    Sketch stats, Dance continuation, Dancing Dagger, Gau's rage learning, Umaro (via SnesUmaro),
    Interceptor rate, desperation, Dice, Hawk-eye.
  - TedStatuses (50-56): tick amounts, status-set rules, reflect, absorb, espers, Coliseum.
- Shared with BNW: the action freeze (BNW NatbRules -> kit), the damage-hook skeleton (BnwPlugin
  BattleFormulas' hook plumbing could move to the kit as a "SnesDamageSteps" base both plugins use).

## Unknowns
- Offering's "normal accuracy, no procs" (change.txt): not located. $6436 (set by CE/0090 from the
  combat routine C2/3350) is read only by CE/00A0, which nothing calls: dead code.
- $3E92 = $14 (rule 9) is set only at
  C0/D840 (STX $3E92 : TSB $11A2), which nothing calls: a disabled Valiant Knife variant, so in 3.0.7
  only the ignore-defense flag triggers the half damage.
- Valiant Knife: its effect (JP C2/3F71, the US 3F89 region) no longer sets ignore-defense
  (TSB $11A2 NOPed at C2/3F73): data-side the porter must clear the PR's flag 5 on its ability.
- Encounter "random bug" fix location (see Docs vs code).
- Whether the PR draws 5-digit damage (MAX_HIT_VALUE 32000).
- 7E:4310 at the battle-start equipment check (rule 52): CE/0050 sets $6434 = 1 when it is nonzero,
  and then every status-1/2 immunity is ignored all battle. No code in the ROM writes 7E:4310 (the
  only $4310 stores are DMA-register writes with DB = 0), so it holds whatever the battle RAM holds.
  One RAM watch in snes_harness at a battle start settles it; until then port the documented intent.
- The exact C1 animation events that freeze time (rule 44); Bushido gauge speed, "Runic speed", the
  six-entry Magitek menu (likely C1, not located); Sketch's Vigor source; $0223, $1444, $1E78.

## Ready-to-paste pr/MODDING.md section (under "Game data", after the SNES maps sections)

### SNES code: the 65816 disassembler (`tools/snes_disasm.py`)

For a mod whose rules live in SNES assembly with no source (T-Edition's battle engine), or to check
an assembly patch (Beyond Chaos's, BNW's) against the ROM it built:

```python
import snes_disasm as D
rom = D.Rom.load(path)                         # HiROM / ExHiROM / LoROM from the size and header
for i in D.linear(rom, 0xC250B3, count=8):     # straight down; REP/SEP and PHP/PLP followed
    print(i)                                   # C2/50B3: 20 C9 26     JSR $26C9
code = D.trace(rom, [(0xC20000, True, True)])  # recursive from entry points, (address, m8, x8)
code.routines[0xC24B5A].calls / .tables        # JSR/JSL targets; ROM tables it reads (TableRef)
print(code.listing(0xC24B5A, 0xC24B70))        # labels (sub_/L_ or yours), "from" xrefs, table notes
D.align(jp_insns, us_insns)                    # {addr: addr} for two builds of the same code
```

The tracer follows branches, JSR/JSL (a callee returns with the widths all its returns agree on),
JMP/JML (tail calls into other banks), `JSR ($xxxx,X)` / `JMP ($xxxx,X)` jump tables (sized by a hint,
`tables={addr: n}`, or read until an entry doesn't look like code; guessed tables are read only
after the sure code is traced, so data can't push real code aside), and records the long (or,
with `db=`, absolute) reads into ROM per routine. `widths={addr: (m8, x8)}` forces widths,
`stop={addr}` ends a path (data after a JSR). `code.conflicts` lists instructions reached with
widths that would decode them differently; `code.overlaps` paths that ran into the middle of an
instruction (both empty on vanilla FF6's battle bank). The listing follows the community
disassemblies (and BNW's comments): `$` hex, branch targets as in-bank addresses, `LDA $D85000,X`.
Command line: `tools/snes_disasm.py ROM C2/50B3 -n 20 [--m16] [--x16]`, `--trace [--bank C2]`.
Tested (`tests/test_snes_disasm.py`) against the vanilla listings quoted in BNW's source and BNW
3.0's own patches decoded from its ROM (471 of 501 `org` blocks, 3,213 instructions; the rest were
overwritten by later patches).

A mod's own reading of it goes in its own tool (T-Edition: `tools/ted_battle.py`, JP vs mod
report in `build/t-edition/battle_code.txt`; the JP v1.0 battle bank is US code at shifted
addresses, `ted_battle.py jp C2/xxxx` gives the US address and BNW's section name).
