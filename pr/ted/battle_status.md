# T-Edition 3.0.7: statuses, timing, battle loop (static read)

Addresses are JP/T-Edition, US equivalent in brackets. "Inferred" = reasoned, not read. All findings checked
identical in the Lua (original JP) and Mato ROMs. Spell names are Mato's (spell table C4/6AC0, 14 bytes).

**Bank 47 caveat (applies to several rules).** Bank 47 is a stale copy of C2. Execution enters it only via
Sketch (C2/1557 [US 155C] -> 47/151A: Sketch counter $1E76, then the sketched command), Runic (C2/35A3 ->
47/152F), counter prep (C2/4CD8 -> 47/1545), AI script commands (C2/1E59 -> 47/1E59) and the Defend hook
(C2/0CF8 -> 47/0CE4, which leaves again via C0/D854 -> JML C2/0D20). The C2/0019 hook puts every main-loop
pass back in C2, so normal actions and periodic ticks run in C2. Bank 47 differs from C2 in my scope at
0D7F-0DC3 (vanilla fractional damage), 21D6, 457A, 45E3 (= JP), and 4F5E/5BAF (spell $10, an older Kill id).
Its monster-stat loader still reads the old table EA/7000.

## 1. ATB and every battle timer freeze while an action plays
- **Rule**: while an action's animation or messages play, nothing in the per-frame timer update moves:
  ATB gauges ($3218), command wait timers ($3AB4/$322C), the status clock (C2/5A6B [5A83]: Stop, Sleep,
  Reflect, Freeze, Condemned, Poison, Regen and Disease ticks) and the battle clock $3A3E (monster AI timers).
  This holds in Active and Wait mode. Menus open in Active mode still don't stop time (vanilla).
- **Code**: the per-frame update C2/1113 [111B] skips everything when `$2F41 AND $3A8F` is nonzero
  (C2/1119 [1121]). T-Ed adds two bits:
  - Battle init sets $3A8F to 2 (Active) or 3 (Wait), where vanilla used 0 or 1. Three `INC $3A8F` at
    C2/2479-247F [247E].
  - $2F41 bit 1 is set by 40/0000, 0040, 0080 and 00C0, called from C1 animation code at C1/96E3, C1/B711,
    C1/9755 [97A7] and C1/9521 [956E]. It is cleared by the main-loop hook C2/0019 -> 40/0100 on every pass.
  - Vanilla's `STZ $2F41` unpauses keep bit 1 now: C1/440C -> 40/0120 and C1/7A2B -> 40/0060 clear only
    bit 0, C1/7CBE -> CE/0030 skips the clear while bit 1 is set, and C1/7733 became NOPs.
- **Data or code**: plugin code. The PR stops time only for IsWaiting/IsForceWaiting (kit SnesAtb notes), so
  ATB fill, chant/wait timers and the kit's SnesStatusClock all have to hold while an act executes.
- **Docs vs code**: matches "freezes anytime an action/effect goes off" (change.txt, history 0.5.9). The docs
  don't say that status timers and the battle clock freeze too, which lengthens every timer in real time.
- **Confidence**: high on the mechanism. Inferred: exactly when the four C1 sites fire (all animation
  starts?). The C1 sites weren't traced.

## 2. Battle speed and Haste multipliers
- **Rule**:
  - The monster ATB factor is $3A90 = 255 − 4×s, where s is the config battle speed 0-5 ($1D4D AND 7). Vanilla
    is 255 − 24×s. Code at C2/2482-2488 [2487].
  - At the default s = 2, monsters fill at 247/256 instead of vanilla's 207/256, about 19% faster, and the
    setting barely matters (±1.6% a step).
  - The Haste multiplier $3ADD is 96 (vanilla 84). Slow is 32 and normal 64 (C2/09DA [09E2]).
  - Party ATB per 2 frames = (Speed + 20) × 1.5 × $3ADD / 16. That is ×96 normally, ×144 with Haste (exactly
    1.5×), ×48 with Slow. Monsters first scale (Speed + 20) by $3A90/256.
  - The status clock adds $3ADD per visit (one visit every 32 frames, a step at 256). With Haste a status
    step comes about every 85 frames (vanilla about 98, normal 128).
- **Data or code**: constants. These are the kit's `SnesAtb.SnesRate`/`SnesWaitSeconds` (k = 96/144/48,
  battle-speed term 4 instead of 24) and `SnesStatusClock.AddHaste = 96`, which belong in a profile. The PR's
  own ATB Haste is already ×1.5.
- **Docs vs code**: change.txt says the battle-speed change was "reverted to vanilla as of 2.9". The ×4
  factor is a separate change that is still in, and no doc mentions it. History says only "Haste effect
  value increased".
- **Confidence**: high (bytes read in both ROMs).

## 3. Command wait times (input to action)
- **Rule**: $322C += the table byte at C2/067B[cmd] (C2/03F6) (same address in US). Changes from JP, in
  vanilla command ids:

  | Commands | JP | T-Ed |
  |---|---|---|
  | Magic $02, Throw $08, Tools $09, Control $0E, Rage $10, Leap $11, Mimic $12, Dance $13, X-Magic $17, Possess $1C | $10/$20 | $30 |
  | SwdTech/Bushido $07, Blitz $0A, Lore $0C | $10/$20 | $40 |
  | Sketch $0D, Slot $0F, GP Rain $18 | $10 | $20 |

  The rest are unchanged (Fight, Item, Steal $10; Jump $E0).
- **Data or code**: data (the kit's `SnesCommandWait` table, by PR command).
- **Docs vs code**: history 1.0.4 "changed the wait time for each command" (no values given).

## 4. Near Fatal ("critical health") at 1/4 max HP
- **Rule**: the status-2 bit 1 Near Fatal flag is set when HP ≤ floor(MaxHP/4) and cleared above that (vanilla
  /8). It is recomputed in the status-setting pass after every hit, and it ignores the target's immunity.
- **Code**: C2/4523 [453B] `LSR` -> NOP in `LDA $3C1C,Y; LSR; LSR; CMP $3BF4,Y` (C2/451E [4536]).
  Everything that keys on the status bit inherits the 1/4 threshold:
  - Cover (True Knight/Love Token, C2/125B [1260])
  - desperation attacks (C2/15CE [15D3])
  - SOS relics (C2/0A49 [0A51])
  - the ×0.75 hit-rate list at C2/2372, which the lead covers
- **Data or code**: plugin code (the PR's low-HP threshold).
- **Docs vs code**: matches. The docs also list "SOS" in history.

## 5. Fractional (percent) damage
- **Rule**: for attacks with $11A4 bit 7, damage = base × power ($11A6) / 16. Bit 7 of $11A3 makes the base MP
  instead of HP.
  - **Listed spells**, by $3410: Gravity 1E, Tornado 34, Shamshir 6E, Cave-In 72, Magic Hammer 9D, Reflect????
    AE, Whirlwind B2, Gravija BD, Launcher CD, Missile DD.
    - Vanilla rule: base = current HP (or MP) minus pending damage $33D0. Max HP is used instead for the
      Item command or when $11A2 bit 2 is set.
    - The result is at least 1 and has no cap.
  - **Everything else**: periodic ticks ($3410 = $FF), Diabolos 44, Wave Cannon B7, and the revives Raise 2D,
    Araise 33 and Phoenix 50.
    - Base = max HP (or MP).
    - No minimum of 1, so max HP < 16/power gives 0.
    - Capped at 999 when $11A7 bit 2 is set. Only the periodic ticks set it (C2/502E). No spell has spell
      byte 7 bit 2. Items weren't checked.
  - Examples: Diabolos does 12/16 = 3/4 of *max* HP and Wave Cannon 9/16 of max HP, both uncapped. Magic Hammer
    takes 2/16 of current MP.
- **Code**: C2/0D7F [0D87] `JML 40/7680` checks the list.
  - Listed spells: `JML 47/0D7F`, the unpatched vanilla copy.
  - Others: `JML C2/0D83`, the new body: `LDA $3C1C,Y`, ×E8 via C2/479F, >>4, then the cap at 0DA7-0DBA.
  - The caller is C2/0B90 [0B98]. If the action is running in bank 47, 47/0B90 calls 47/0D7F directly, so
    *every* fractional attack gets the vanilla rule there. Sketched percent attacks are an example.
- **Data or code**:
  - The current-vs-max choice per ability is data if the PR has separate current% and max% formula types.
  - The 999 cap and the missing minimum of 1 need code.
- **Docs vs code**:
  - History 1.6.7 lists Gravity, Tornado, Diabolos, Sonic Boom, Cave-In and Whirlwind as the percent spells.
    Diabolos is not on the current-HP list, so it hits max HP.
  - The "cap 999 when $11A7 bit 2" rule exists, but in practice only periodic ticks use it.
- **Confidence**: high. Unknown: whether "Shamshir" is the doc's "Sonic Boom" (it's a name question only).

## 6. "Critical Health" pseudo-element (percent attacks vs death-immune foes)
- **Rule**: a percent spell misses outright (no damage) when the target is immune to every status the spell
  would set or clear.
  - The six spells carry only Near Fatal (status byte 2 = $02) and have spell byte 7 bit 0 set. The six are
    Gravity, Tornado, Diabolos, Shamshir, Cave-In and Whirlwind.
  - So they miss exactly when the target is immune to Near Fatal: monster byte $15 bit 1, which goes to
    $331C via C2/2E15.
  - Death immunity is ignored. These spells have $11A2 bit 1 ("miss if death-immune") clear.
  - The party has no Near Fatal protection, so it can't block them.
  - 229 of 512 monster records have that immunity.
- **Code**: none new. This is vanilla's "immune to all its statuses -> miss" rule at C2/4444-4462 [445C],
  which sets $3A48, and C2/345A then skips the damage call.
- **Data or code**: pure data (spell flags, status bytes, monster immunity), provided the PR applies the same
  "all statuses resisted -> miss" rule to damaging spells. Otherwise one small plugin check.
- **Docs vs code**: matches history 1.6.7. Its note that these spells can't carry other statuses also fits:
  adding any status would break the "all immune" test.
- **Confidence**: high.

## 7. Periodic damage: Poison, Regen, Disease (Sap), MP Slip
- **Rule**: each tick is command $22 (queued at C2/5B37 [5B4F], cadence unchanged from vanilla). It sets
  $11A4 = $A0 (fractional, unblockable), $11A7 = $04 (999 cap), base power 4 and $11A2 = $68. $B6 then
  picks the case:

  | Status ($B6) | Effect | Element |
  |---|---|---|
  | Regen ($02) | heal; power 2 (MaxHP/8) for party slots (Y < 8), 1 (MaxHP/16) for monsters; no Stamina | none |
  | Disease = status-2 bit 6 ($40, vanilla Seizure), also MP Slip = $3E4D bit 6 (vanilla hidden "Phantasm", cleared only by death/petrify, C2/4605) | MP damage, power 1 = MaxMP/16 | $08 ("Darkness") |
  | Poison ($04) | damage, power 2 = MaxHP/8 | $08 |

  - All cases are capped at 999 with no minimum, then go through T-Ed's element step (C2/FAD0, so an absorber
    heals). The cap applies before the element step.
  - Vanilla's growing Poison ($3E24 counter into $BD) and the Stamina-based power are gone.
  - Cadence (vanilla): Regen and Disease every 4 status steps (512 frames), Poison every 8 (1024).
    Disease/MP Slip is checked before Regen in the same slot, so an MP Slip fighter with Regen gets no Regen
    ticks (inferred from C2/5B5C ordering).
  - Note that $11A2 $68 includes bit 3 (invert on undead): Regen hurts undead and Poison heals them, as in
    vanilla.
- **Code**: C2/500A-5038 [5022-5050] sets the defaults and calls `JSL 40/3030`, which picks the case from
  $B6. Its default branch (physical $69, power 4) can't be reached. The damage then goes through §5's C2/0D83
  path; ticks run in C2.
- **Data or code**: the amounts need plugin code (max-HP fractions, party vs monster split, 999 cap). Cadence
  is the kit's existing SnesStatusClock.
- **Docs vs code**:
  - **Disease is 1/16 MP in code; change.txt and history say 1/8.**
  - Poison 1/8 and Regen 1/8 (party) / 1/16 (monster) match.
  - "1/8 HP" in the docs means *max* HP.
  - Bank 47 would give current HP, but ticks don't run there.
- **Confidence**: high.

## 8. Stop vs Sleep timers; Sleep broken by hits
- **Rule**:
  - On-set timers in status steps (128 frames each at normal speed, frozen during actions):

    | Status | Steps (about) | Note |
    |---|---|---|
    | Stop | 9 (19 s) | vanilla 18 |
    | Sleep | 18 (38 s) | unchanged |
    | Reflect | 26 | unchanged |
    | Freeze | 34 | unchanged |

  - Sleep and Muddle are removed from a target hit by a physical attack ($11A2 bit 0) with nonzero power that
    wasn't blocked by Golem or the dog ($3A82/$3A83), unless the attack itself inflicts them. This is vanilla
    code, unchanged.
  - Stop is never broken by hits.
- **Code**: Stop: C2/4668 [4680] `LDA #$09; STA $3AF1,Y` (JP $12). Sleep: C2/461F [4637] $3CF9 = $12. Reflect
  C2/466F and Freeze C2/4679 are unchanged. The wake rule is C2/0C25-0C52 [0C2D].
- **Data or code**: data (timer lengths: the kit's SnesStatusClock.StopSteps, or the PR condition timer if it
  has one). The wake rule is probably already the PR's behaviour.
- **Docs vs code**: "Sleep is set to be longer" isn't a code change: Sleep stays 18 and only Stop got
  shorter. "Cured by physical attack" is vanilla behaviour.

## 9. Status setting: equipment statuses, immunity, Reraise, undead+Life
- **Rule (code facts)**:
  - **a. $6434 gate (new RAM).**
    - The equipment check sets $6434 per equipped item: 1 if `$2F44 = 0` and WRAM 7E:4310 ≠ 0, 0 if
      7E:4310 = 0. When $2F44 ≠ 0 it skips the item's status protection (`TSB $11D2`) as well. Code:
      C2/0FA2 [0FAA] -> CE/0050.
    - While $6434 = 1, statuses 1-2 are set *without* the target's immunity mask $331C (C2/44FF [4517] ->
      CE/0070).
    - Also while $6434 = 1, Death or Petrify no longer clear statuses 3-4 (C2/45FC [4614] -> CE/00C0).
    - Nothing else writes $6434, so it holds for the whole battle.
  - **b.** Status 1-2 *removals* ignore immunity/permanence. C2/43B0 [43C8] `AND $331C,Y` was NOPed; status
    3-4 removals are still filtered (C2/43C8).
  - **c.** Slow immunity no longer implies Haste immunity (C2/26B8 [26BD] branch retarget). Haste immunity
    still implies Slow immunity, and Regen ↔ Disease immunity stay linked.
  - **d.**
    - Jump take-off sets $63A0,X = 1 (C2/21D6 [21DB] -> 40/01E0).
    - After every status write, an entity with status-4 bit 5 (removed/hidden) whose $63A0 ≠ 1 loses Reraise
      (status-4 bit 2) (C2/457A [4592] -> 40/01C0). So escaping, Snort, Sneeze and the like strip Reraise,
      and jumping keeps it.
    - No code clears $63A0 in battle.
  - **e.** Clearing Death or Petrify also clears the entity's bit in $3A56 ("died this action", read by
    counter prep at C2/4BEA). The bit is C2/45E3 [45FB] -> C2/3FC6. Inferred effect: a monster killed and
    revived in one action no longer fires its death counter.
  - **f.** Life on undead: vanilla kills an undead target hit by a lift-Death/Zombie spell with the
    invert-on-undead flag. T-Ed skips the kill when bit 3 of byte $14 of a 32-byte record is set at
    EA/7000 + MonsterID×32 (C2/4421 [4439] -> C0/D940). EA/7000 is a stale address: monster stats live at
    57/3E00, and EA/7000 now holds unrelated T-Ed data.
    - Intended (inferred): monster byte $14 bit 3. Among undead that would be Vampiress, Death Penalty,
      Phantom Train and EX ids 394-470.
    - Actual: Nightwalker, Revenant and ids 399, 402, 470. Everything else dies to Raise/Phoenix as in
      vanilla.
- **Data or code**: all plugin code. (f) can be expressed as a per-monster flag list once the intent is
  chosen.
- **Docs vs code**:
  - change.txt says "Cursed Shield + Ribbon: you still get Cursed Shield's statuses". (a) is the mechanism,
    but its trigger value 7E:4310 can't be resolved statically.
  - If $6434 really is 1 in battle, *all* status-1/2 immunities are ignored for every attack, which would be a
    large bug.
  - History 0.5.9 says equipping a resist accessory *removes* the ailment. That is menu code, not battle
    code. The task brief's "equipment no longer cures" isn't in this code.
- **Confidence**: (b)-(e) high. (a) gate unresolved. (f) intent inferred.

## 10. Reflect: no halving; "FF5 boost" is emergent
- **Rule**:
  - Bounced magic keeps full base damage (vanilla halved $11B0 once for the bounce).
  - The multi-target split (base /2 when there are 2+ targets and $11A2 bit 6 is clear, C2/3379 [337E]) still
    applies first.
  - Each reflector sends one bounce at a random foe. With a split spell, N reflectors deal N × 1/2, so 3+
    reflectors beat one unsplit hit (1.5×, 2× at 4).
  - A single-target reflect does 100% (vanilla 50%).
  - Multi-missile hits that use the same routine ($3405 ≥ 0, Launcher) are no longer halved either.
- **Code**: C2/34B8 [34BD] `LSR $11B0` -> NOP, in the bounce routine C2/347E [3483], which is called from
  C2/323B [3240].
- **Data or code**: plugin code (PR reflect damage).
- **Docs vs code**: matches. "×2 when reflected 4 times" in history = 4 × 1/2. There's no dedicated boost code.
  $6436 is set at C2/3350 -> CE/0090, an animation-queue site in the combat routine whose meaning wasn't
  decoded. It is read only by unreferenced code at CE/00A0 (an absorb-element check skipped once), so it's
  dead.

## 11. Absorb (drain) isn't capped
- **Rule**: an HP/MP drain gives the drainer the full computed damage.
  - Vanilla capped it at the victim's remaining HP/MP and at the drainer's missing HP/MP.
  - Now it pays out even from a 0-MP or near-dead victim. The normal max-HP clamp still applies on heal.
- **Code**: C2/0C55 [0C5D] calls C2/0DE5 [0DED], whose first byte is now RTS (vanilla cap routine).
- **Data or code**: plugin code.
- **Docs vs code**: matches "absorb what the damage would have been even if 0 is dealt".

## 12. Shell reduces heals and ignore-defense magic (and more)
- **Rule**:
  - Ignore-defense attacks ($11A2 bit 5) no longer skip the damage-modification block. Defense becomes 0
    (40/0140), then the rest of the pipeline runs.
  - Shell (magic) and Safe (physical) multiply by 170/256 (C2/0CE4-0CF4 [0CEC]). Heals carry ignore-def
    (Cure $28), so a Shelled target receives ×170/256 healing.
  - Side effects also reach ignore-def damage and heals:
    - Defend: magic ×170/256, physical ½
    - back row: physical ×170/256
    - a Morphed target: magic ×170/256
    - 47/0CE4, plus C0/D854 halving vs $3C95 bit 1
- **Code**: C2/0CB2 [0CBA] -> 40/0140 -> C2/0CCC (vanilla `BIT #$20; BNE $0D1A` removed).
- **Data or code**: plugin code.
- **Docs vs code**: the docs say only Shell, but Defend, back row and Morph also cut heals (inferred from the
  shared path). "Used on an enemy with Shell" in the doc means any target.

## 13. Espers summonable every turn
- **Rule**: summoning no longer marks the caster in $3F2E, so the menu's grey-out (C2/5773 [578B]
  `BIT $3F2E`) never triggers. Only MP limits summons; MP costs are spell data.
- **Code**: C2/4D88-4D8E [4DA0] `LDA $3018,Y; TSB $3F2E` -> NOPs, in the command-queue routine C2/4D71
  [4D89].
- **Data or code**: plugin code if the PR enforces one summon per battle; MP costs are data.

## 14. MP cost code
- **Rule**: unchanged. The task's C2/4F5F and 500B carry BNW's "MP cost" labels, but they are §16 and §7.
  Summon cost increases are data (spell byte 5).

## 15. Coliseum player-controlled (and Umaro)
- **Rule**: Coliseum fights ($3A97 ≠ 0) open the command menu and no longer force random actions. Umaro (char
  $0D) also gets a menu.
- **Code**:
  - C2/0126 [0126] `BNE $0134` (random action) -> `BNE $0128` (no-op).
  - C2/092A [0932] `BNE $08BD` -> no-op.
  - C2/091E [0926] `CMP #$0D` -> `CMP #$FF`.
- **Data or code**: plugin code (the PR's Colosseum auto-battle). The enemy behaviour is AI data.

## 16. Status-triggered casts use new spell ids
- **Rule**:
  - Reraise revives with spell $2D Raise (C2/079C [07A4], JP $30).
  - Doom expiry casts $E8 "Kill" (C2/5BAF [5BC7], JP $0D). Per the docs, Kill ignores Death immunity.
  - SOS Shell/Safe/Reflect use $29/$28/$31 (C2/0A62/0A70/0A7E [0A6A/0A78/0A86]).
  - In C2/4F47 [4F5F] (command $26) the vanilla Doom branch (`CMP #$0D`: set $3204 bit 4, skip if no monsters
    are left, then load $E8) is now unreachable from the Doom timer. Kill skips those checks.
  - Bank 47 still uses spell $10 there.
- **Data or code**: data (spell ids). The Kill semantics are spell data/effect $35 (not decoded here).

## 17. Veldt registration
- **Rule**: a won formation is recorded in the $1DDD bitfield if the formation flag $2F4B bit 1 is clear and the
  formation id ≤ $1FF. The "every monster id < $100" test is gone.
- **Code**: C2/49D4 [49EC] `BNE $49EA` -> NOP. The loop now falls straight to the formation check.
- **Data or code**: plugin code (PR Veldt logic). Docs match.

## 18. End of battle and battle init
- Shadow never leaves at random. C2/486F [4887] `BIT $1EDE; BNE` -> NOPs, so the 1/16 post-battle leave branch
  at C2/488E is never taken. Matches change.txt.
- Inventory write-back:
  - The inventory moved to 7E:ECA0 (ids) and 7E:EDD0 (quantities), 304 slots (C2/4969 -> 4E/1190,
    C2/4972 -> 4E/0360). 4E/1190 also clears $1440-$144F.
  - Item consumption (C2/499A -> 4E/0A80) treats quantity bit 7 as a flag: with $1444 = 0, flagged items
    aren't used up; with $1444 ≠ 0, only flagged items are. The meaning of $1444 is unknown.
  - This is outside status scope.
- Battle init: C2/249C/249F were refactored into subroutines $24A5 and $508E. Formation changes (cmd $20, C2/5071
  [5089]) now run the same init sequence. This plausibly fixes history 2.x's "Regen/Poison lost after
  disappear/appear" (inferred).
- C2/262B -> 4E/1560 sets $0223 bits 0-2 (meaning unknown). Its Mimic init ($3F24/$3F28 = $12) is unchanged.

## 19. Blind
- No Blind code outside the lead's C2/2215-2384 range. The only attacker-Dark read is C2/2345 (halves the hit
  rate $EE). C2/595B is vanilla targeting.

## Seen elsewhere (other scopes)
- C2/0019 hook -> C2/6426 is a hidden debug win. With the font colour at the default ($1D55 = $7BDE) and Select+Up
  (joypad $4219 = $28) held, it queues cmd $24 effect 5 on all monsters (removed and killed), once per battle
  ($3A96 bit 1).
- Desperation (C2/15C3 [15C8]): the 768-tick wait, once-per-battle and Gau/Umaro exclusions were removed, but
  the roll is `(rand AND $1F) = 0` = **1/32** (JP $0F = 1/16). change.txt says 1/8.
- Critical hit roll C2/33FE [3403]: rand < $14 = 20/256 (JP 8).
- Morph attacker bonus is +50% (C2/3364, JP +100%).
- Back-row attacker halving at C2/338D.
- Golem/dog block defense is $78 (C2/0CD8, JP $C1).
- Earring bonus (C2/0D42): it now also applies to heals, and the double-earring +50% branch is gone (history
  0.5.9 "effects don't overlap").
- Hit determination:
  - C2/2356-2372 status hit-rate masks are zeroed.
  - The Image dodge is 128/256 (C2/232C).
  - C2/221B -> 4E/1120 makes Vanished death-immune targets ($3AA1 bit 2) no longer auto-hit by Death,
    percent or effect-$3E spells (the Vanish+Doom fix).
- C2/0115 counts Mimic uses into $1E7E, and 47/152F/1545 count into $1E74/$1E72 (achievement counters).
- Magitek spell base is $85 (C2/4E2B, JP $83). The random-esper map changed (C2/37DC).
- C2/5E44/5E9A: `CMP #$0C` -> `#$0E` (Gogo/Umaro included in esper-related victory code).
- C2/28D6 relic byte $11D6 -> $11D9 feeds $3C44/$3A6D (encounter-odds relics).
- Cursed Shield id $66 -> $7C (C2/5FE2).
- Leap removed (cmd $11 -> C2/67D9).

## Unknowns
1. The value of WRAM 7E:4310 (and $2F44) during the battle-start equipment check. This decides whether $6434
   is ever 1 in battle (§9a). It needs one RAM watch.
2. The exact C1 animation events that set $2F41 bit 1 (C1/96E3, B711, 9755, 9521). For example: do
   damage-number or message-only waits freeze time?
3. T-Ed's intended table for the undead-Life exemption (§9f).
4. Whether $63A0 is zeroed at battle start (no code found), $0223 (4E/1560), and $1444 (inventory flag).
5. Whether the PR natively applies "miss if immune to all the spell's statuses" to damaging spells (decides
   whether §6 is pure data).
