"""The data T-Edition's plugin (plugin/TedPlugin) reads, exported from the port.

    .venv/Scripts/python tools/ted_plugin_data.py [OUT.json]     (default build/t-edition/plugin/ted_data.json)

Installed as BepInEx/TEdition/ted_data.json (tools/ted_testinstall.py; plugin data stays out of the
plugins folder). Read by TedRules/TedData.cs, so the offline tests (plugin/Ted.Tests) check the same file:

  items              T-Edition's item slots (SNES ids) -> the PR content id and row item identity gave
                     each (tools/item_identity.py, as port.py does), and the name the game should show
                     (the port's message text over vanilla's): `tedcheck` compares the game's names
  new_weapons        the weapon rows the port added (92+: content id, attack, name)
  drop_rates         MONSTER_DROP_RATE_1.. as the port sets them; drop_monsters: monsters with 3-4 slots
  half_ignore_defense  monsters with T-Edition's monster byte $12 bit 1 ($3C95 bit 1, rule 9 of
                     pr/ted/BATTLE_SPEC.md): PR ids (SNES id + 1), and SNES ids 384+ (no PR row yet)
  esper_bonus_vanilla  vanilla's esper level-up bonus codes by magicite content id (rule 4: T-Edition has none)
  named, rows        content ids and table rows the rules test for (Orichalcum $66, Elven Darts $6C, Valiant
                     Knife, Atma Weapon, ...; the PR keys Atma and Valiant Knife on weapon rows 30 and 11)

Reads the port's output (mods/TEdition) and T-Edition's ROM (profile_tedition.MATO); run after port.py tedition.
"""
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import ff6snes as S  # noqa: E402
import idmap as M  # noqa: E402
import item_identity as I  # noqa: E402
import prdata as P  # noqa: E402

MOD = os.path.join(P.ROOT, "mods", "TEdition")
OUT = os.path.join(P.ROOT, "build", "t-edition", "plugin", "ted_data.json")
MASTER = os.path.join("master", "Assets", "GameAssets", "Serial", "Data", "Master")
MESSAGE = os.path.join("message", "Assets", "GameAssets", "Serial", "Data", "Message", "system_en.txt")
TYPES = {"item": "1", "weapon": "2", "armor": "3"}
# item slots the rules name (T-Edition's ids; pr/ted/battle_commands.md)
NAMED_SLOTS = {"orichalcum": 0x66, "elven_darts": 0x6C, "valiant_knife": 0x08, "atma_weapon": 0x61,
               "dancing_dagger": 0x06, "dice": 0x50, "fixed_dice": 0x52}


def mod_csv(name):
    path = os.path.join(MOD, MASTER, name + ".csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mod_messages():
    out = {}
    path = os.path.join(MOD, MESSAGE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if "\t" in line:
                    k, v = line.split("\t", 1)
                    out[k] = v
    return out


def main(argv):
    out_path = argv[0] if argv else OUT
    import profile_tedition as T
    T.build()                                   # T-Edition in the US layout (memory) + Mato's names
    rom = S.Rom(T.MATO)
    names = T._Image.names
    slots = I.identify(I.mod_items_from(rom, names.items, names.item_icons), log=lambda *_: None)

    # content rows as the game will have them: vanilla's, then the port's (new rows, changed keys)
    content = {int(r["id"]): r for r in P.Table("content")}
    for r in mod_csv("content"):
        content[int(r["id"])] = r
    by_row = {(r["type_id"], int(r["type_value"])): cid for cid, r in content.items() if r["type_id"] in TYPES.values()}
    vmsg, mmsg = P.messages(), mod_messages()

    def text(key):
        return mmsg.get(key, vmsg.get(key, ""))

    items, missing = [], []
    for s in slots:
        cid = by_row.get((TYPES[s.table], s.pr_id))
        if cid is None:
            missing.append(s.slot)
            continue
        items.append({"slot": s.slot, "content": cid, "table": s.table, "row": s.pr_id,
                      "name": text(content[cid]["mes_id_name"]), "how": s.how,
                      "moved": (s.table, s.pr_id) != M.default_item(s.slot)})

    weapons = []
    for r in mod_csv("weapon"):
        row = int(r["id"])
        if row < 92:
            continue
        cid = by_row.get(("2", row))
        weapons.append({"row": row, "content": cid or 0, "attack": int(r["attack"]),
                        "name": text(content[cid]["mes_id_name"]) if cid else ""})

    rates = {r["key_name"]: int(r["value1"]) for r in mod_csv("game_constant_int")}
    drop_rates = [rates.get(f"MONSTER_DROP_RATE_{k}", 0) for k in range(1, 5)]
    drop_monsters = sum(1 for r in mod_csv("monster") if r.get("drop_content_id3", "0") not in ("", "0"))

    with open(T.MATO, "rb") as f:            # the 6 MB ROM itself (S.Rom(T.MATO) is the US-layout image)
        raw = f.read()
    half = [e for e in range(512) if raw[T.MONSTERS + 32 * e + 0x12] & 0x02]
    named, rows = {}, {}
    for role, slot in NAMED_SLOTS.items():
        it = next((i for i in items if i["slot"] == slot), None)
        if it:
            named[role] = it["content"]
            rows[role] = it["row"]
    data = {
        "version": "T-Edition 3.0.7 (Mato A7 r1)",
        "made": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "drop_rates": drop_rates,
        "drop_monsters": drop_monsters,
        "items": items,
        "new_weapons": weapons,
        "half_ignore_defense": {"pr": [e + 1 for e in half if e < 384], "snes_new": [e for e in half if e >= 384]},
        "named": named,
        "rows": rows,
        # rule 4: T-Edition skips the esper level-up bonus call for everyone (C2/60B2-60DE): the plugin
        # answers every esper as "none" (PrKit SnesEsperBonus), which needs vanilla's codes by content id
        "esper_bonus_vanilla": [[M.esper_content(e), r[10]] for e, r in enumerate(S.Rom(P.VANILLA_ROM).table(*S.ESPERS))],
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{out_path}: {len(items)} items ({sum(1 for i in items if i['moved'])} on moved rows"
          f"{f', {len(missing)} without a content row: {missing}' if missing else ''}), {len(weapons)} new weapon rows, "
          f"drop rates {drop_rates} ({drop_monsters} monsters with 3-4 slots), "
          f"{len(half)} half-damage monsters ({len(data['half_ignore_defense']['snes_new'])} of them 384+), named {named}")


if __name__ == "__main__":
    main(sys.argv[1:])
