# T-Edition 3.0.7: character commands and character battle rules (static read)

Scope: commands and character-specific rules. Addresses are JP/T-Edition unless marked US.
Source: `T-Edition 3.0.7 (Mato).sfc` versus JP 1.0, read with `tools/ted_battle.py` and `snes_disasm.py`.
Odds are given as x/256 unless stated. A rule marked **(inferred)** was not read end to end.

## 0. Shared facts every section uses

- **Command jump table:** C2/19C2 (US C2/19C7), dispatched from C2/13F9 (`JSR ($19C2,X)`, X = $B5×2). T-Edition repoints these entries:
  - 00 Fight → C2/3FA3 → `JML 40/3700` (the Offering check, §18)
  - 0E Control → C2/FB64 (Snowstorm)
  - 11 Leap → C2/67D9 → `JML 47/6740` (Animal)
  - 1C Possess → C2/67DD → `JML 47/6789` (Spirit)
  - 1A Health is still C2/1719 (now Pray) and 1B Shock is C2/1715 (→ C2/67B5, same behaviour as vanilla).
- **Bank-47 problem.** Bank 47 holds an older copy of C2. Its own command table at 47/19C2 is mostly vanilla: Fight → 47/15C3, Leap → 47/1998, Possess → 47/17E0, only Control → FB64.
  - Execution enters bank 47 through these JMLs: Sketch (C2/1557), AI-script command $30 (C2/1E59), Runic absorb (C2/35A3), Interceptor counter queueing (C2/4CD8), monster-property load (C2/2EA8), and pre-strike effect $4E (C2/65B0).
  - Once there, it stays in bank 47 until the main loop passes C2/0019, which does `JML 40/0100` → `JML C2/001E`. In practice that is the rest of that main-loop iteration.
  - Bank-47 differences inside my scope are listed in §20. A port should implement the C2 behaviour. The bank-47 behaviour is an emulation artefact and should not be copied.
- **Special-effect tables ($11A9 = effect×2):** per target at C2/3DB5 (US 3DCD), dispatched from C2/387E; pre-strike at C2/42C9 (US 42E1), dispatched from C2/3E6A.
  - Weapon effect = high nibble of item byte $1B. Spell effect = spell byte 9 (spells at C4/6AC0, 14 bytes each).
  - T-Edition table changes: pre-strike $14 → C2/651A, $46 → C2/6527, $47 → C2/6590, $4E → C2/65B0. Per-target $0E → C2/3EB2, $0F → C2/3EBE (§13).
- **Damage incrementor $BC.** Damage += (damage/2)×$BC at C2/3706 (US 370B, vanilla). $BD seeds $BC when an attack starts (C2/3177).
- **New success counters** (16-bit, capped at $1FE = 510 unless noted). These are new save fields, carried into New Game+.

  | Address | Counter | Written at |
  |---|---|---|
  | $1E70 | Steal | CE/0120 |
  | $1E72 | Interceptor counter (Twin Fang), cap 255 | 47/1545 |
  | $1E74 | Runic absorb | 47/152F |
  | $1E76 | Sketch | 47/151A |
  | $1E7A | Slot uses | 40/0A00 |
  | $1E7C | Snowstorm | C2/FB64 |
  | $1E7E | Mimic | 40/0A20, via C2/0115 |

  Porting them needs plugin save fields. Only $1E70 has a gameplay effect (Orichalcum).

## 1. Steal

**Rule.**
- Fails at once if the target has nothing left to steal.
- Chance C = attacker Lv + 70 − target Lv. The original game used +50.
  - C < 0: fail.
  - Lv+70 ≥ 256, or C ≥ 128: automatic success.
  - "Enhanced Steal" ($3C45 bit0): C×2.
- Success if random(0..99) < C, so P = min(C, 100)/100.
- Rare slot ($3308) with 64/256 = 1/4 (vanilla 32/256). Otherwise the common slot ($3309). If the chosen slot is empty ($FF), the steal fails.
- On success: both slots are set to $FF (vanilla), $1447 = 1, and $1E70 += 1 (cap 510).

**Code.**
- C2/398E effect (US C2/399E), per-target effect $A4.
- Constant at C2/39AB (US 39BB): $32 → $46.
- Rare threshold at C2/39CD (US 39DD): $20 → $40.
- Tail: C2/39D9 → `JML 4E/0B18` → C2/39DF → `JSL CE/0120` (counter).

**Data or code.** Plugin code (the formula constants). Enhanced Steal is an item flag: Thief's Bracer, and also Orichalcum (data).

**Docs vs code.** The docs write "(Lv+70−TLv)/99"; the code rolls 0..99, so the divisor is 100. Rare 1/4 matches.

**Confidence.** High.

## 2. Orichalcum (item $66)

**Rule.**
- Battle power = min(floor(steals/2), 255), with steals = $1E70.
- Base power is 0. Item byte $14 = 0: 0 steals gives power 0.
- Reaches 255 at 510 steals, which is also the counter cap.
- Works in either hand: X is the hand-adjusted index into $3CA8/$3CA9.
- The item also carries Enhanced Steal (data) and Throwable.

**Code.**
- Load Weapon Properties C2/29C9 (US C2/29CE): `LDA $3B68,X / STA $11A6` replaced by `JSL CE/0140`. Bank 47's copy calls it too.
- CE/0140 tests $3CA8,X for $66.
- It also tests $EB, which would give power = 255 − min(steals/2, 254). That branch is dead in 3.0.7 and EX: item $EB is Ether.
- Menu display: C3/8F2D → CE/01A0, which shows (count/2) + $80·(count ≥ 256).

**Data or code.** Plugin code: weapon power from a counter. PR has no data field for this.

**Docs vs code.** Matches change.txt and history.txt.

**Unknown (inferred).** Throwing Orichalcum takes power from the item-data path, so it probably throws at power 0.

## 3. Gil Toss (GP Rain, command $18)

**Rule.**
- Cost = Lv×180 (8×8 multiply of the level by $B4).
- Characters: gold is spent from the party (C2/37B1). If the party can't pay: no targets, message 8. Damage = cost/2 = Lv×90 to every target, not split.
- Monsters: they pay from their own gold ($3D98,Y), capped at what they have. Damage = paid/#targets/2.
- The command itself is vanilla (C2/1902, US 1907): power 1, $11A2 |= $60 (ignore defense, no split), effect $A2.

**Code.**
- Pre-strike $A2 → C2/3F9F (US C2/3FB7) → `JML 47/3F9F`. The new routine lives only in bank 47 (47/3F9F–3FF6).
- The C2 table and the 47 table both lead there.

**Data or code.** Plugin code: a gil-cost, gil-based damage formula.

**Docs vs code.**
- Players: matches (Lv50 → 9000 gil, 4500 each).
- "Enemies still use the original formula" is not true. Enemies also pay ×180 (vanilla ×30) and deal paid/2/targets, about Lv×90/targets against vanilla Lv×60/targets. Only the per-target split is kept.

## 4. Sketch (command $0D)

**Rule.**
1. **Hit.** The target must be a monster (Y ≥ 8) without the "can't sketch" flag ($3C80 bit5).
   - Chance q = floor(256·RelmLv / D), with D = target Lv. With Enhanced Sketch ($3C45 bit2), D = floor(TLv×170/256), about ×1.5.
   - q ≥ 256 → automatic; otherwise success if random(256) < q (C2/378D, vanilla).
   - Enhanced Sketch is on Chocobo, Magical, Lamia and Rainbow Brush (item byte, data). Artemis's Brush has it off. All brushes give the same bonus; there is no per-brush odds table.
2. **Attack picked.** random < $40 (25%) takes entry 0, otherwise entry 1 (75%), from the sketch table moved to CF/1200 (2 bytes × 384 monsters).
   - Entry 0 is $83 Wishing Star for every monster.
   - Entry 1 is the monster's own move, mostly $EF (the monster's Special).
3. **Stats.** The sketched attack runs with X = sketcher (C2/31E7, vanilla).
   - Level from the sketcher (C2/2C1C, vanilla).
   - New: magic formula $11AE := sketcher's Mag.Pwr ($3B41,X) when $3417 ≥ 0 (C2/2B78 → C2/6710, US 2B7D).
   - New: physical formula $11A6 := sketcher's right-hand battle power ($3B68,X) (C2/2BA8 → `JSL CE/0000`, US 2BAD).
4. **Counter.** A successful sketch increments $1E76 at 47/151A. The sketched command is then dispatched through the bank-47 table (C2/1557 → 47/151A → `JMP ($19C2,X)`), so it runs in the bank-47 copy (§20).

**Wishing Star** ($83) is spell data: power 41, effect $1E (vanilla Traveler, damage = steps/power, C2/3E88).

**Data or code.**
- Data: hit rule (if PR exposes Sketch accuracy), sketch table (75/25 and Wishing Star), brush flag.
- Plugin code: using Relm's Mag.Pwr and battle power.

**Docs vs code.**
- "Works without a brush": I found no code change. Vanilla C2 has no brush requirement either (inferred). Brushes only add the Enhanced Sketch flag.
- "Uses Relm's stats": true for Mag.Pwr and weapon power. Vigor for physical sketched attacks is probably still the monster's ($11AE is loaded by C2/299A before the attacker swap) **(inferred)**.

**Confidence.** High for odds; medium for the stats.

## 5. Spirit (Embroidered Tippet) and the relic command swaps

**Rule.**
- The swap list was rebuilt: from-table CE/01E8, to-table CE/01F8, 8 entries tested against $11D6 bits. The JP table is C2/543A–5443 with 5 entries. Code at C2/5390 (US 53A8).

  | Bit | Swap | Relic |
  |---|---|---|
  | 0 | Dance $13 → Animal $11 | Pheasant Netsuke |
  | 1 | Sketch $0D → Spirit $1C | Embroidered Tippet |
  | 2 | Runic $0B → Pray $1A | Maiden's Prayer |
  | 3 | Fight → Jump | |
  | 4 | Magic → X-Magic | |
  | 5 | Morph/Trance $03 → Shock $1B | Zeidrich |
  | 6 | Slot → Gil Toss | Heiji's Jitte |
  | 7 | Steal → Mug | |

  Vanilla bits were 2 Jump, 3 X-Magic, 4 Control, 5 GP Rain, 6 Capture. T-Edition's item data sets the new bit layout.
- **Spirit:** command $1C → 47/6789 → casts spell $EC Bless (power 3, effect $42, whole party) through C2/175A, as a Lore-style cast.

**Data or code.** The swaps are data if PR's accessory-command-swap mechanism is data-driven (vanilla PR has Thief Gloves, Coin Toss and similar). Spirit, Pray and Shock are a command that casts a fixed spell.

**Docs vs code.** Matches.

**Note.** Relic slots hold 8-bit IDs. Page-2 items use proxy IDs: Master's Scroll $EE, Tippet $F4, Zeidrich $F6, Maiden's Prayer $FB. Bank 47 has an alternate item table at +$1E00 when $1440 bit0 is set (4E/0568, 4E/05A0).

## 6. Control removed

**Rule.**
- Command $0E now runs Snowstorm (§11).
- The Sketch → Control swap is gone from the list (§5).
- The Control code (command C2/1971, its use of C2/154F) is left in place but cannot be reached.
- Per-target effect $A8 at C2/3B59 (US 3B71) now starts with `BRA $3B78`, which always gives the "can't" message. Its space is reused for Gau's rage-learning entry (§9). $A8 was vanilla's escape effect, so any escape item that uses $A8 now always fails (see "Seen elsewhere").

**Data or code.** Data: just don't give the command.

**Docs vs code.** Matches.

## 7. Dance, Animal, Dancing Dagger

**Dance rule.**
- C2/1778 (US 177D) sets Dance status and clears it at once (C2/178F–1795). The dance lasts one action and Mog is not locked.
- The stumble roll is removed (vanilla C2/1798 `JSR 4B3B / BCC fail`). If the dance's terrain differs from the current one, the background always switches (D1/F9AB) and the dance runs.
- Step choice is vanilla C2/059C with thresholds C2/05CE = {$10, $30, $90}:

  | Step | Random range | Odds |
  |---|---|---|
  | 1 | ≥ $90 | 112/256 |
  | 2 | $30–$8F | 96/256 |
  | 3 | $10–$2F | 32/256 |
  | 4 (animal) | < $10 | 16/256 |

- Steps come from CF/FE80 (8 dances × 4). T-Edition's third steps are enemy moves (E4, B2, ED, E9, BC, BE, 88, 54).

**Animal (Pheasant Netsuke) rule.** 47/6740 picks one of spells $75–$7C (Falcon … Snow Bunny) from a random byte:

| Animal | Spell | Odds |
|---|---|---|
| Falcon | $75 | 31/256 |
| Wombat | $76 | 32/256 |
| Meerkat | $77 | 32/256 |
| Tapir | $78 | 32/256 |
| Boar | $79 | 32/256 |
| Raccoon | $7A | 32/256 |
| Poison Frog | $7B | 32/256 |
| Snow Bunny | $7C | 33/256 |

It is cast as $B5 = 2 through `JML C2/175A`.

**Dancing Dagger (item $06, weapon effect $B) rule.**
- Pre-strike C2/3F87 (US 3F9F) → C2/64EA → C2/6740 (`JMP 6740` patched in at C2/3F91).
- random ≥ $80: normal attack.
- Otherwise, if either hand holds item $06: $11A6 = 0 and the strike is replaced by spell $65 + random(16) (carry is set by the CMP), uniform 1/16 over $65–$74.
- No animals. The range $65–$74 includes $71 Shadow Flare, which is no longer in any dance, and excludes the enemy-move third steps.

**Data or code.**
- Dance, no lock, no stumble: plugin code, unless PR Dance has a "one turn" option.
- Step odds and table: data.
- Animal: a weighted random-spell command (data if PR has random-ability tables).
- Dancing Dagger: plugin code (weapon proc).

**Docs vs code.** Matches. "Never Animal" holds on the C2 path only (§20).

## 8. Snowstorm and Slot counters

- **Snowstorm** (command $0E, C2/FB64): $B6 = $54 Snowstorm (power 71, ice, all enemies), $B5 = 2, through C2/175A; $1E7C += 1.
- **Slot:** C2/176C → C2/17AF. For Slot, MP cost is zeroed ($11A5 = 0, vanilla) and $1E7A += 1 (`JSL 40/0A00`).

## 9. Gau: Fight, Rage learning, Veldt

**Rule.**
- Gau's Fight command is character data. Leap is gone ($11 is now Animal).
- The vanilla Magitek-armor conversion of Gau's Rage → Fight → Magitek is removed (NOP at C2/5352, US 536A).
- **Rages on victory.** C2/5ECD (US 5EE5) now does `JSR 3B5B`: if Gau is in the battle party ($300B not $FF; alive or dead), C2/49EF (US 4A07, LearnRages) sets the $1D2C bit for every formation slot whose monster ID < $100 ($2002,X == 0).
  - Only victories count.
  - Monsters that never appeared or fled still count **(inferred)**.
  - Monster IDs ≥ $100 never become rages.
  - Mog's dance learning follows as before.
- **Veldt registration.** C2/49C8 (US 49E0): the "every monster < $100" test is NOPed at C2/49D4. Any formation with $3ED4 < $200 and without formation flag $2F4B bit1 is added to $1DDD.

**Data or code.** Plugin code: a learn-on-victory hook and the Veldt rule. The Fight command is data.

**Docs vs code.** Matches ("any battle with Gau in the party"). Not documented: monsters ≥ $100 can't be learned.

## 10. Gogo and Umaro: espers and magic

**Rule.** The character-ID limit $0C (Gogo and above excluded) is raised to $0E or $0F:
- Battle magic and esper list: C2/5574 (US 558C).
- Magic menu: C2/56B4 (US 56CC). Gogo's special case is removed.
- Victory AP and spell learning: C2/5E44, C2/5E9A (US 5E5C, 5EB2).
- Field menu: C3/542F, C3/5779, C3/57A6 (US C3/4D6F, 50AA, 50D7).

**Data or code.** Data if PR's per-character "can use magic/espers" flags are data, which is likely. Otherwise a small plugin.

**Docs vs code.** Matches.

## 11. Umaro

**Controllable.** The uncontrollable test at C2/091E (US 0926) changes `CMP #$0D` → `CMP #$FF`.

**Snowstorm.** Command $0E (§8).

**Fight.** When Umaro (ID $0D) uses Fight and no desperation attack fires, C2/1636 (US 163B) builds $FE:
- bit2 if Berserker Ring (relic $E3; vanilla Rage Ring $C6) is worn and there is a throwable ally;
- bit3 if Power Belt ($E2; vanilla Blizzard Orb $C5) is worn.

A weighted pick (C2/522F over table C2/5251, US 5269, unchanged) then chooses the action. Each set option's weight is the table value + 1.

| Equipped | Fight | Charge | Rampage | Throw Ally |
|---|---|---|---|---|
| none | 159/255 | 96/255 | – | – |
| Berserker Ring | 95/255 | 64/255 | – | 96/255 |
| Power Belt | 95/255 | 64/255 | 96/255 | – |
| both | 63/255 | 64/255 | 64/255 | 64/255 |

- **Rampage:** C2/1708 → spell $EF (vanilla $54 Storm; constant at C2/170B): power 96, hit 130, physical, all enemies.
- **Charge:** C2/1679, vanilla tackle.
- **Throw Ally:** C2/168D, vanilla, ignores defense. With no throwable ally it falls back to Charge.

**Data or code.** Weights and spells could be data if the port has a "random action on Fight" table. Otherwise plugin code. Relic IDs are data.

**Docs vs code.** The docs omit Charge, which still fires 25–38% of the time. "Throw Ally rare when both are worn": it is 64/255, the same as Rampage.

## 12. Slot, and Darts/Cards against flying

**Rule.**
- **Mysidian Bunny** (spell $FE): data change, power 10 → 14 and effect $2A. Pre-strike $2A at C2/40F7: heal = Lv × power. The per-target division (JSR 477A at C2/4115, US 412D) is NOPed, so the heal is not split.
- **Seven Flush ($81) and Dive Bomb ($80):** data only.
  - Seven Flush: power $54 → $41, flags $10 → $50 (no-split added), elements $F7.
  - Dive Bomb: power $82 → $58, flags $10 → $60 (ignore defense + no split).
  - With no split, the halved power does not cut the damage.
- **Hawk-eye weapons** (weapon effect 8: Cards, Darts, Tarot of Ben, Antares), per-target C2/38EE (US 38FE):
  - Vanilla: 50% chance of +1 $BC, and +3 more against Float targets.
  - T-Edition: the random gate and the first INC are removed. Against a target with Float ($3EF9 bit7), when the command is Fight ($B5 == 0), $BC += 2, which doubles the damage. No bonus otherwise.

**Data or code.** Bunny: plugin code (Lv × power formula). Seven Flush and Dive Bomb: data. Hawk-eye: plugin code (conditional ×2), unless PR has a "vs flying" multiplier field.

**Docs vs code.**
- change.txt says the flying bonus is a flat ×1.5. The code adds 2 to $BC, which is ×2.
- The Float check applies only under Fight. Riot Blade, Vacuum Wave and Leaf Swirl carry effect 8 but run as $B5 = 2 or $0A, so their documented flying bonus probably does nothing **(inferred)**.
- Docs list Dive Bomb 65 and Seven Flush 42; the data holds 88 and 65 (technique.txt agrees on 88).

## 13. Blitz, Bushido, Tools and Throw changes that live in code

**Tachi: Tiger (spell $57).**
- Data: effect $3D (vanilla Revenge, pre-strike C2/41CE). $3414 = 0, so no defense or variance; $11B0 = MaxHP − HP of the attacker. Power 1, hit 100.
- Code: in the related Valiant Knife effect (weapon effect $A, C2/3F71, US 3F89), the `TSB $11A2` that forced ignore-defense is NOPed (C2/3F73). Affects Valiant Knife and Last Resort.

**Tiger Rush (Blitz $63).** Data: effect $14 → new pre-strike C2/651A (T-Edition only): $3A70 = 2 extra strikes (3 hits) at random targets ($BA bit6).

**Unused multi-hit effects.** C2/6527 (2 hits), C2/6590 (8 hits) and 47/1823 (2–4 hits, effect $4E, reached through C2/65B0) are unused in 3.0.7. EX uses them for Meteor, Artillery Drone and Pale Horse. In 47/1823 the hit roll is:

| Hits | Random range | Odds |
|---|---|---|
| 2 | ≥ 84 | 172/256 |
| 3 | 36–83 | 48/256 |
| 4 | < 36 | 36/256 |

Its intended `TSB $BA` is mis-assembled (`0A BA`), so that effect does not randomize targets.

**Phantom Rush ($64).** Data: effect 2 (C2/402C) = ignore defense + $B2 bit1.

**Air Anchor.**
- Item $A9 sets $11A9 = $AE through the tools table C2/2B15 (US 2B1A).
- Per-target C2/3C60 (US 3C78): if the target has $3AA1 bit2, the branch now goes to an RTS (C2/3C65 `BNE $3C77`) instead of the miss exit. Damage still lands, and the "dies when it acts" flag is not set.
- Heat comes from item data.

**Particle Bomb.** The tools table entry for item $A7 (old Debilitator, which set $11A9 = $AC) now points to an RTS, so plain item data drives it.

**Drill.** Moved to C2/6534 with the same behaviour.

**Throw (command $08, C2/1888, US 188D).** `LDA #$02 / STA $BD` → `LDA #$00`. Thrown items lose vanilla's built-in ×2 ($BD seeds $BC).

**Command wait times.** Table C2/067B (US 067B), read at C2/03F6. Values are JP → T-Edition:

| Command | JP | T-Edition |
|---|---|---|
| Magic | 20 | 30 |
| Bushido | 10 | 40 |
| Throw | 10 | 30 |
| Tools | 10 | 30 |
| Blitz | 10 | 40 |
| Lore | 20 | 40 |
| Sketch | 10 | 20 |
| Snowstorm | 10 | 30 |
| Slot | 10 | 20 |
| Rage | 10 | 30 |
| Animal | 10 | 30 |
| Mimic | 10 | 30 |
| Dance | 10 | 30 |
| X-Magic | 20 | 30 |
| Gil Toss | 10 | 20 |
| Spirit | 10 | 30 |

Runic, Pray, Shock, Magitek, Fight and Item are unchanged. This is the "longer wait before Iaido executes" in history.txt.

**Data or code.** Tiger, Tiger Rush (as a hit count), Phantom Rush, Seven Flush and similar: data, provided PR offers Revenge-type and multi-hit fields. Air Anchor's no-miss rule, the Throw ×2 removal and the wait table are code or config.

**Docs vs code.** Bushido gauge speed: not located. It is not in C2; it is presumably the C1 battle-menu gauge code.

## 14. Magitek for everyone

**Rule.**
- The six Magitek spells are $85–$8A: Magitek Beam, Bio Blaster, Heal Force, Confuser, Banisher, Magitek Missile.
- In the armor, the command conversion at C2/5342 (US 535A) is vanilla: Fight → Magitek, other commands blanked except Magic, Item and Mimic. The Gau Rage-to-Fight case is removed.
- The confused/uncontrolled random Magitek pick is random(3) + $85 (C2/058A: $83 → $85), so Magitek Beam, Bio Blaster or Heal Force.

**Code.** I did not locate which code lets non-Terra characters see all six; it is presumably the C1 battle menu.

**Data or code.** Data: Magitek ability list per character.

**Note.** Heal Force carries effect $2A, which is no longer split (§12): heal = Lv × 60 per target.

**Latent bug.** C2/2815 still sets the Magitek default Mimic action to spell $83, which is now Wishing Star.

## 15. Trance (Morph, command $03) and Shock

**Rule.**
- Attacker boost at C2/335F (US 3364): `INC $BC` once instead of twice. Every attack by a tranced character does ×1.5 (vanilla ×2), physical and magic.
- Damage taken: a tranced target takes magic damage × 170/256 + 1, about −1/3, through C2/0CF8 → 47/0D0F (already decoded by the lead). Vanilla halved it.
- Physical damage taken while in Trance is not reduced (inferred from 47/0CE4).
- **Shock (Zeidrich):** relic swap $03 → $1B (§5). C2/1715 → C2/67B5 casts spell $82 (power 128, non-elemental, all) with $3412 = 5. Vanilla Shock was the same spell and path.

**Data or code.** Trance multipliers: plugin code (or PR Trance config if it exists). Shock: data.

**Docs vs code.**
- "No boost for non-elemental": I found no element test on the Trance boost or in the $BC incrementor. Treat it as unimplemented or unverified.
- character.txt "magic taken −1/3" matches the code. history.txt 0.8.6 ("reduction 1/3 → 1/2") predates the current code.

## 16. Runic and Pray

**Runic.**
- Absorb hook C2/35A3 (US 35A8) → 47/152F adds to the counter $1E74 (and continues in bank 47).
- The Runic command and its wait (10) are unchanged.
- "Runic speed changed" was not found in C2 or the wait table; it may be animation in C1 **(unknown)**.

**Pray (Maiden's Prayer).**
- Relic swap $0B → $1A.
- C2/1719 (US 171E) casts spell $66 Sunbath (power 42, heals the party) instead of vanilla $2E, with $3412 = 5.
- Reflect bypass comes from spell data.

**Data or code.** Data.

## 17. Interceptor (Shadow)

**Rule.**
- **Block.** Applies to a physical, single-target attack on a character with $3EF9 bit6. C2/2283 (US 2288) `JSR FB84` = random; `CMP #$55`; `BCC no-block`. The dog therefore blocks when random ≥ $55: 171/256 ≈ 67% (vanilla 50%).
- **Counter.** In Prepare Counterattacks C2/4CC7 (US 4CDF), when X == $3416 (the protected character): random bit0 = 1 (50%) → counter with $3A7A = 2, $3A7B = $84 Twin Fang (power 68). Vanilla picked $FC or $FD at random.
- Then `JML 47/1545` adds to $1E72 (cap 255) and queues the counter in bank 47.

**Data or code.** Plugin code, unless PR's Interceptor has rate and ability fields. The counter attack is data.

**Docs vs code.**
- Docs and history.txt (0.8.5) say the block was lowered from 50% to 33%. The polarity in the code gives 67%. The author probably meant 85/256 and branched the wrong way.
- "Very high chance" of a counter is 50% in the code.

**Confidence.** High on the branch polarity.

## 18. Desperation attacks

**Rule.**
- Entry: Fight → `JML 40/3700`. If either hand holds item $6C (Elven Darts, which has the Offering flag) or either relic slot is $EE (the Master's Scroll proxy), it skips straight to the normal fight at C2/160B.
- Otherwise C2/15C3 (US 15C8) checks, in order:
  - character only;
  - the 768-frame timer test ($3A3F ≥ 3) is NOPed at C2/15CC (US 15D1);
  - Near Fatal ($3EE5 bit1; its threshold of 1/4 HP is set elsewhere);
  - not $3EE5 & $24, not $3EE4 & $12, $B9 ≠ 0;
  - random AND $1F == 0, so 1/32 (vanilla AND $0F = 1/16) at C2/15E7 (US 15EC);
  - the once-per-battle flag $3F2F is still set, but its BNE is NOPed at C2/15F1, so it can repeat;
  - the "Gau and Umaro excluded, Gogo remapped" tests at C2/15F8–15FD are NOPed.
- The attack is spell $F0 + character ID:

  | ID | Character | Spell |
  |---|---|---|
  | $0B | Gau | $FB Wild Buster |
  | $0C | Gogo | $FC Punish Meteor |
  | $0D | Umaro | $FD Aura Boost |

  It runs as $B5 = 2 through C2/170F.

**Data or code.** Plugin code (trigger rule and odds). The attack spells are data.

**Docs vs code.** Docs say 1/16 → 1/8. The code is 1/32: the byte changed from $0F to $1F, a halving. The other claims match: no 768 timer, unlimited, Gau and Umaro included, Offering blocks it (and so does Elven Darts).

## 19. Dice and Fixed Dice (weapon effect 9)

**Rule.** Pre-strike C2/4140 (US 4158) does $3414 = 0, $11A4 |= $20 (unblockable), and rolls dice. Hit byte = number of dice: Dice 2, Fixed Dice 3.

1. **Base.** product × 2 × L′.
   - L′ = Lv with 2 dice.
   - L′ = ((Lv+1)>>1 + Lv + carry)>>1, about round(3·Lv/4), with 3 or more dice (C2/41A6 → C2/67C0).
2. **Triple.** If all three dice match, the base is multiplied by the face value (vanilla loop C2/41B1–41BF).
3. **Piercing-resist.** Each pass of that loop calls C0/DA39. If the highest-indexed target in $A4 has $3C95 bit1, $11B0 is shifted right 4 times. The result is base/16 (non-triple), and triples add only about 1/16 each.
4. **After the roll.** `JSL 40/01A0` clears $BC (no Berserk, Trance or other incrementor). If dice == 3, it also sets $11A4 = 0 (drops unblockable and every other flag) and hit rate = 100.

**Data or code.** Plugin code.

**Docs vs code.**
- "×1.06 vs piercing-resist": the code divides by 16. "1.06" is probably a mistranslation of 1/16; note the triple loop gives about ×1.06 on top of the /16.
- "Accuracy 100 like Dice": Dice keeps "can't be dodged"; only Fixed Dice gets hit 100, and it can now be dodged.
- "Berserk no effect": true via `STZ $BC`. It assumes Berserk's INC at C2/3375 runs before pre-strike effects **(inferred)**.

## 20. Bank-47 divergences inside this scope

These run only after an earlier bank-47 entry in the same main-loop iteration (§0):

- **Steal:** 47/39AB is still +50 and 47/39CD still rare 1/8.
- **Desperation:** 47/15E8 is `AND #$20`, so 1/2 chance. The bank-47 Fight is reached directly through 47/19C2 → 15C3, without the Offering check.
- **Trance boost:** 47/3361 is still ×2.
- **Dancing Dagger:**
  - 47/64EA keeps the Gekkabijin ($60) random-spell branch.
  - Its 50% branch jumps to 47/6740, which is the Animal routine. A bank-47 Dancing Dagger proc can therefore summon an animal.
- **Pre-strike table** 47/42C9 is vanilla: Tiger Rush is a single hit there, and effects $46/$47/$4E do nothing.
- **Per-target $0E/$0F:** absent in bank 47.
- **Command wait table** 47/067B is older (Magic 40, Tools 40, Animal 10, X-Magic 10, Gil 10, Spirit 10).
- **Hawk-eye:** 47/38E9–3904 differs.

A sketched attack always takes this path.

## Seen elsewhere (outside scope, noted only)

- **Effect $2A no-split** also hits Flare Star ($C6) and Heal Force ($87).
- **Escape effect $A8** (C2/3B59) is disabled: always fails.
- **New weapon effects.**
  - E (Shadow Blade, Hrunting, Gram, Arondight): ×2 against $3C95 bit0.
  - F (Balmung, Dragon Spear, Amanomurakumo, Dragon Claw, Artemis Brush): ×2 against $3C95 bit5.
  - Both are per-target C2/3EB2/3EBE. Effect 4 (Man Eater, ×2 against bit4) is used by Moulin Rouge.
- **Item command:** C2/1892 → C2/653A skips damage modification only for characters, so monster-used items now take defense.
- **Wishing Star / Traveler** (effect $1E): ÷8 against $3C95 bit1 (C0/D8C0).
- **Ancient Prayer** uses effect $49 (random summon, C2/3F95; the summon picker C2/37DC was changed).
- **Level ? Death** ($94) uses effect $1D (gold-digit level).
- **C2/0791:** queued command $26 now gets $B8 = $2D (was $30); purpose unknown.
- **Mimic counter $1E7E** is incremented through C2/0115 → 40/0A20 on every turn's Mimic bookkeeping. Whether it counts only real Mimics was not checked.

## Unknowns

1. Bushido gauge fill speed: C1 code not located.
2. "Runic speed changed": no change found in C2, the wait table, or Runic's command.
3. Magitek: the menu code that gives non-Terra characters six entries ($85–$8A) was not located (likely C1).
4. Trance "no boost for non-elemental": not found in code.
5. Sketch physical attacks: whose Vigor is used ($11AE from C2/299A before the X swap)?
6. Rage learning includes monsters that never appeared or fled: inferred from the loop over all 6 formation slots, not tested.
7. Dice/Berserk ordering (Berserk INC versus the dice `STZ $BC`): inferred, not traced.
8. Thrown Orichalcum: power is probably 0 (item-data path), not traced.
9. How often the bank-47 paths actually run during play (AI command $30, Runic, counters, monster loads).
10. Purpose of the $1E78 counter slot: unused or unseen.
