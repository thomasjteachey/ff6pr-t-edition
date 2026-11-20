"""T-Edition's battle code against the Japanese v1.0 ROM it was built on (the T-Edition battle spec's
source: what changed, where, the hooks into new code and the tables that code reads).

    .venv/Scripts/python tools/ted_battle.py                 report -> build/t-edition/battle_code.txt + .json
    .venv/Scripts/python tools/ted_battle.py --ex            the same for T-Edition EX (battle_code_ex.*)
    .venv/Scripts/python tools/ted_battle.py at 47/1A15      one new routine / address, with labels
    .venv/Scripts/python tools/ted_battle.py jp C2/2C3B      JP address -> US address and BNW's section name

T-Edition (Tsushiy) ships no source: its battle engine changes are 65816 patches on the JP ROM's
banks C1-C3 that jump into new code (banks 40-5F of the 6 MB ExHiROM, and space T-Edition freed in
C0/CE/C2). This traces the JP ROM, the US ROM and T-Edition from the banks' entry vectors with the
kit's disassembler (tools/snes_disasm.py), then for every byte T-Edition changed in C1-C3:

  * the JP routine it sits in, its US address (JP and US code differ by shifted addresses: matched
    with snes_disasm.align) and BNW's name for that part of the US battle bank (section headers in
    BNW's c2.asm, US addresses), so the BNW source and the community disassemblies apply;
  * the JP and T-Edition instructions side by side, each change classed as a hook (a jump/call into
    new code), a moved table (the same load from another address), a changed constant, or new code;
  * every new routine T-Edition's code reaches (listing with labels), the ROM tables it reads.
"""
import argparse
import bisect
import collections
import json
import os
import re
import sys

import kitpath  # noqa: F401
import jp_layout as J
import prdata as P
import snes_disasm as D

PROJECT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TED_ROM = os.path.join(PROJECT, "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
EX_ROM = os.path.join(PROJECT, "build", "t-edition", "T-Edition EX 2.0.6 (Mato).sfc")
BNW_C2 = os.path.join(PROJECT, "mods", "brave-new-world", "source", "asm", "banks", "c2.asm")
OUT = os.path.join(P.ROOT, "build", "t-edition")

# entry vectors: C2/0000-0009 (battle: main, ...), C3/0000-0018 (menus), C1/0000 (battle graphics
# dispatcher, JMP ($0008,X)). Widths at entry: C2 sets its own (SEP #$30); C1/C3 run with 16-bit X.
ENTRIES = [(0xC20000, True, True), (0xC20003, True, True), (0xC20006, True, True), (0xC20009, True, True),
           (0xC10000, True, False)] + [(0xC30000 + 3 * k, True, False) for k in range(9)]
BANKS = (0xC1, 0xC2, 0xC3)

# Vanilla routines (US v1.0 addresses) named after BNW's own comments on its calls (c2.asm)
US_NAMES = {
    0xC2000C: "BattleMain", 0xC200F9: "TurnPostprocess", 0xC2083F: "EndOfTurn", 0xC20B4A: "PalidorPost",
    0xC21471: "AddEntities", 0xC22D71: "LoadMonsterAI", 0xC23293: "CombatRoutine", 0xC24391: "StatusesAfterTurn",
    0xC24781: "Mul8x8", 0xC24792: "Div16by8", 0xC247B7: "Mul24_E8", 0xC24A07: "LearnRages",
    0xC24B53: "Rand50", 0xC24B5A: "Rand256", 0xC24B65: "RandA", 0xC24BF4: "RunMonsterScript",
    0xC24C5B: "PrepareCounters", 0xC25072: "CmdBattleChange", 0xC250DD: "CmdScan", 0xC251F0: "BitNumber",
    0xC25217: "BitMask", 0xC2522A: "RandomBit", 0xC254DC: "CopyItemData", 0xC257C2: "ProcessAnimation",
    0xC25C54: "CopyGauges", 0xC25D91: "Victory", 0xC25FD4: "ShowMessage", 0xC2606D: "CheckLevelUp",
    0xC26235: "AddExperience", 0xC262C7: "AddReserveItems",
}


def bnw_sections(path=BNW_C2):
    """BNW's c2.asm section titles ('; #####' then '; Title') at the `org` that follows: sorted
    [(us_addr, title)] (US addresses inside each part of the battle bank)."""
    out, title = [], None
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for k, line in enumerate(lines):
        if line.startswith("; #####") and k + 1 < len(lines) and lines[k + 1].startswith("; "):
            title = lines[k + 1][2:].strip()
        m = re.match(r"^org \$(C2[0-9A-Fa-f]{4})", line)
        if m and title:
            out.append((int(m.group(1), 16), title))
            title = None
    return sorted(out)


class Builds:
    """The three ROMs traced, and the JP <-> US address maps."""

    def __init__(self, ted_path=TED_ROM):
        self.ted = D.Rom.load(ted_path)
        self.jp = D.Rom.load(J.jp_rom_path())
        self.us = D.Rom.load(P.VANILLA_ROM)
        self.jp_code = D.trace(self.jp, ENTRIES, max_table=128)
        self.us_code = D.trace(self.us, ENTRIES, max_table=128)
        # T-Edition: the vectors, then every JP routine T-Edition left in place (its own jumps reach
        # vanilla code through paths a trace from the vectors can't follow), then the targets of
        # hooks found in changed code until none is new
        self.ted_tracer = D.Tracer(self.ted, max_table=128)
        keep = [(e, r.m8, r.x8) for e, r in sorted(self.jp_code.routines.items())
                if self.ted.is_rom(e) and self._same(e, 4)]
        self.ted_code = self.ted_tracer.run(ENTRIES + keep)
        for _ in range(8):
            more = self._hook_targets()
            if not more:
                break
            self.ted_tracer.run(more)
        self.jp2us = {}
        for b in BANKS:
            a = [self.jp_code.insns[k] for k in sorted(self.jp_code.insns) if k >> 16 == b]
            u = [self.us_code.insns[k] for k in sorted(self.us_code.insns) if k >> 16 == b]
            self.jp2us.update(D.align(a, u))
        self._jp_keys = sorted(self.jp2us)
        self.sections = bnw_sections()
        self._sec_keys = [a for a, _ in self.sections]
        self._jp_insn_keys = sorted(self.jp_code.insns)

    def _same(self, addr, n):
        try:
            return self.ted.read(addr, n) == self.jp.read(addr, n)
        except ValueError:
            return False

    def _hook_targets(self):
        """Calls/jumps in T-Edition's changed C1-C3 code to code not traced yet."""
        out = set()
        for bank in BANKS:
            for s, e in diff_runs(self.jp, self.ted, bank):
                a = s - 4
                for _ in range(64):
                    if a >= e:
                        break
                    i = self.ted_code.insns.get(a)
                    if i is None:
                        ji = self.jp_code.insns.get(a)
                        try:
                            i = D.decode(self.ted, a, *(ji.m8, ji.x8) if ji else (True, True))
                        except ValueError:
                            break
                    if i.target is not None and i.kind in ("call", "jump") and self.ted.is_rom(i.target)                             and i.target not in self.ted_code.insns:
                        out.add((i.target, i.m8, i.x8))
                    a = i.next
        return sorted(out)

    def us_addr(self, jp_addr):
        """The US address of a JP instruction (nearest matched instruction before it + offset)."""
        if jp_addr in self.jp2us:
            return self.jp2us[jp_addr]
        k = bisect.bisect_right(self._jp_keys, jp_addr) - 1
        if k < 0 or self._jp_keys[k] >> 16 != jp_addr >> 16 or jp_addr - self._jp_keys[k] > 0x40:
            return None
        return self.jp2us[self._jp_keys[k]] + (jp_addr - self._jp_keys[k])

    def section(self, us_addr):
        if us_addr is None or us_addr >> 16 != 0xC2:
            return ""
        k = bisect.bisect_right(self._sec_keys, us_addr) - 1
        return self.sections[k][1] if k >= 0 else ""

    def jp_insn_at(self, addr):
        """The traced JP instruction covering `addr` (None if not traced code)."""
        k = bisect.bisect_right(self._jp_insn_keys, addr) - 1
        if k < 0:
            return None
        i = self.jp_code.insns[self._jp_insn_keys[k]]
        return i if i.addr <= addr < i.addr + i.size else None

    def jp_routine(self, addr):
        return self.jp_code.owner.get(addr)

    def us_name(self, us_addr):
        return US_NAMES.get(us_addr, "")

    def describe(self, jp_addr):
        """'C2/2C3B (US C2/2C40, Load Monster Stats)'."""
        us = self.us_addr(jp_addr)
        bits = [f"US {D.snes_str(us)}" if us else "US ?"]
        n = self.us_name(us) if us else ""
        sec = self.section(us)
        if n:
            bits.append(n)
        if sec:
            bits.append(f"BNW: {sec}")
        return f"{D.snes_str(jp_addr)} ({', '.join(bits)})"


def cached_builds(ted_path=TED_ROM):
    """Builds, pickled under build/t-edition (rebuilt when a ROM or the tools change)."""
    import pickle
    deps = [ted_path, J.jp_rom_path(), P.VANILLA_ROM, __file__, D.__file__, BNW_C2]
    key = [(os.path.abspath(p), os.path.getmtime(p)) for p in deps if os.path.exists(p)]
    path = os.path.join(OUT, ".battle_cache_" + os.path.splitext(os.path.basename(ted_path))[0].replace(" ", "_") + ".pkl")
    sys.setrecursionlimit(100000)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                k, b = pickle.load(f)
            if k == key:
                return b
        except Exception:
            pass
    b = Builds(ted_path)
    os.makedirs(OUT, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump((key, b), f, protocol=pickle.HIGHEST_PROTOCOL)
    return b


def diff_runs(a, b, bank, gap=3):
    """[(start, end)] of bytes that differ in a bank (runs closer than `gap` merged)."""
    runs, start = [], None
    base = bank << 16
    da, db = a.read(base, 0x10000), b.read(base, 0x10000)
    for o in range(0x10000):
        d = da[o] != db[o]
        if d and start is None:
            start = o
        elif not d and start is not None:
            if runs and start - runs[-1][1] <= gap:
                runs[-1] = (runs[-1][0], o)
            else:
                runs.append((start, o))
            start = None
    if start is not None:
        runs.append((start, 0x10000))
    return [(base | s, base | e) for s, e in runs]


def is_new_code(builds, addr):
    """T-Edition code that isn't the JP ROM's: the expansion banks, or bytes T-Edition changed."""
    bank = addr >> 16
    if 0x40 <= bank < 0x7E:
        return True
    try:
        return builds.ted.read(addr, 4) != builds.jp.read(addr, 4)
    except ValueError:
        return True


def classify(j, t, builds):
    """One changed instruction pair (JP, T-Edition) -> kind."""
    if t is None:
        return "removed"
    if j is None:
        return "added"
    if t.kind in ("call", "jump") and t.target is not None and t.target != j.target and is_new_code(builds, t.target):
        return "hook"
    if t.mn == "JSL" or t.mn == "JML":
        return "hook" if t.target != (j.target if j else None) else "same"
    if j.mn == t.mn and j.mode == t.mode:
        if t.mode in (D.LONG, D.LONGX) and j.value != t.value:
            return "moved table"
        if t.mode in (D.IMM_M, D.IMM_X, D.IMM8):
            return "constant"
        if t.mode in (D.REL, D.RELL) or (t.mn in ("JSR", "JMP") and t.mode == D.ABS):
            return "retarget"
        return "operand"
    if t.mn == "NOP":
        return "nop"
    return "code"


def pair_up(builds, start, end):
    """JP and T-Edition instructions over a changed run, from the JP instruction boundary before it
    to a common boundary after it: [(jp_insn, ted_insn)]."""
    ji = builds.jp_insn_at(start)
    if ji is None:
        return None
    a = b = ji.addr
    js, ts = [], []
    jm = tm = (ji.m8, ji.x8)
    for _ in range(600):
        if a == b and a >= end:
            break
        if a <= b:
            i = builds.jp_code.insns.get(a) or D.decode(builds.jp, a, *jm)
            js.append(i)
            jm = D.apply_flags(i, i.m8, i.x8)
            a = i.next
        else:
            i = builds.ted_code.insns.get(b) or D.decode(builds.ted, b, *tm)
            ts.append(i)
            tm = D.apply_flags(i, i.m8, i.x8)
            b = i.next
    return js, ts


def new_routines(builds):
    """T-Edition routines whose entry is new code, by entry."""
    out = {}
    for e, r in builds.ted_code.routines.items():
        if r.insns and is_new_code(builds, e):
            out[e] = r
    return out


def report(builds, path_txt, path_json):
    code, ted = builds.ted_code, builds.ted
    lines, items = [], []
    w = lines.append
    w("T-Edition battle code vs the JP v1.0 ROM (tools/ted_battle.py; addresses JP unless marked US)")
    w(f"traced: JP {len(builds.jp_code.insns)} instructions, US {len(builds.us_code.insns)}, "
      f"T-Edition {len(code.insns)} ({len(code.routines)} routines); width conflicts T-Edition "
      f"{len(code.conflicts)}, overlaps {len(code.overlaps)}")
    hooks = []
    for bank in BANKS:
        runs = diff_runs(builds.jp, ted, bank)
        w("")
        w(f"=== bank {bank:02X}: {len(runs)} changed runs, {sum(e - s for s, e in runs)} bytes")
        for s, e in runs:
            pu = pair_up(builds, s, e)
            tab = next((t for t, ents in builds.jp_code.tables.items() if t <= s < t + 2 * max(len(ents), 1)), None)
            if pu is None and tab is not None:
                ents = builds.jp_code.tables[tab]
                ks = sorted({(a - tab) // 2 for a in range(s, e) if (a - tab) // 2 < len(ents)})
                xs = sorted(builds.jp_code.xrefs.get(ents[0], ()) & {a for a in builds.jp_code.insns
                                                                         if builds.jp_code.insns[a].mode == D.ABSIX})
                w(f"\n-- {D.snes_str(s)}-{e & 0xFFFF:04X} jump table {D.snes_str(tab)}"
                  f" (dispatch {', '.join(builds.describe(x) for x in xs[:2]) or '?'}): entries changed:")
                for k in ks:
                    old = ents[k]
                    new = (tab & 0xFF0000) | ted.word(tab + 2 * k)
                    w(f"   #{k} (${k:02X}): {D.snes_str(old)} -> {D.snes_str(new)}"
                      + ("  [new code]" if is_new_code(builds, new) else ""))
                items.append({"jp": D.snes_str(s), "end": D.snes_str(e), "kind": "jump table",
                              "table": D.snes_str(tab), "entries": {k: [D.snes_str(ents[k]), D.snes_str(
                                  (tab & 0xFF0000) | ted.word(tab + 2 * k))] for k in ks}})
                continue
            if pu is None:
                cov = code.insns.get(s)
                w(f"\n-- {D.snes_str(s)}-{e & 0xFFFF:04X} ({e - s} bytes) not in traced JP code: "
                  f"JP {builds.jp.read(s, min(e - s, 16)).hex(' ')} -> T-Ed {ted.read(s, min(e - s, 16)).hex(' ')}"
                  + (" [T-Edition code]" if cov else ""))
                items.append({"jp": D.snes_str(s), "end": D.snes_str(e), "kind": "data/untraced",
                              "jp_bytes": builds.jp.read(s, e - s).hex(), "ted_bytes": ted.read(s, e - s).hex()})
                continue
            js, ts = pu
            rt = builds.jp_routine(js[0].addr)
            w(f"\n-- {D.snes_str(s)}-{e & 0xFFFF:04X} in {builds.describe(rt) if rt else '?'}"
              f" at {builds.describe(js[0].addr)}")
            kinds = []
            n = max(len(js), len(ts))
            same_shape = len(js) == len(ts) and all(x.size == y.size for x, y in zip(js, ts))
            if same_shape:
                for j, t in zip(js, ts):
                    if j.raw == t.raw:
                        continue
                    k = classify(j, t, builds)
                    kinds.append(k)
                    w(f"   {str(j):<42} | {t.bytes_hex():<12} {t.text:<16} [{k}]")
                    if k == "hook":
                        hooks.append((t, builds.describe(t.addr)))
            else:
                w("   JP:")
                for j in js:
                    w(f"     {j}")
                w("   T-Edition:")
                for t in ts:
                    tag = ""
                    if t.kind in ("call", "jump") and t.target is not None and is_new_code(builds, t.target):
                        tag = "   [hook]"
                        hooks.append((t, builds.describe(t.addr)))
                    w(f"     {t}{tag}")
                kinds.append("code")
            items.append({"jp": D.snes_str(s), "end": D.snes_str(e), "routine": D.snes_str(rt) if rt else None,
                          "us": D.snes_str(builds.us_addr(js[0].addr)) if builds.us_addr(js[0].addr) else None,
                          "section": builds.section(builds.us_addr(js[0].addr)), "kinds": sorted(set(kinds)),
                          "jp_code": [j.text for j in js], "ted_code": [t.text for t in ts]})

    w("")
    w("=== hooks: JP-ROM code calling or jumping into new code")
    for t, where in hooks:
        w(f"   {str(t):<44} at {where}")

    news = new_routines(builds)
    w("")
    w(f"=== new code: {len(news)} routines")
    tables = collections.defaultdict(set)
    for e in sorted(news):
        r = news[e]
        callers = sorted(code.xrefs.get(e, ()))
        w("")
        w(f"## {D.snes_str(e)} ({len(r.insns)} instructions) from " +
          ", ".join(D.snes_str(c) for c in callers[:8]) + (" ..." if len(callers) > 8 else ""))
        for t in r.tables:
            tables[t.table].add(e)
    w("")
    w("=== ROM tables read by new code (address: routines)")
    for t in sorted(tables):
        w(f"   {D.snes_str(t)}: " + " ".join(D.snes_str(e) for e in sorted(tables[t])))
    w("")
    w("=== listing of the new code")
    labels = {}
    for e in news:
        labels[e] = f"ted_{e:06X}"
    code.labels.update(labels)
    for b in sorted({a >> 16 for a in code.insns if is_new_code(builds, a)}):
        w("")
        w(f"--- bank {b:02X}")
        w(code.listing(b << 16, (b + 1) << 16 if b != 0xFF else None) if 0x40 <= b < 0x7E else
          "\n".join(str(code.insns[a]) for a in sorted(code.insns) if a >> 16 == b and is_new_code(builds, a)))
    os.makedirs(os.path.dirname(path_txt), exist_ok=True)
    with open(path_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump({"changes": items, "hooks": [{"at": D.snes_str(t.addr), "insn": t.text, "where": wh}
                                               for t, wh in hooks],
                   "new_routines": {D.snes_str(e): {"insns": len(r.insns),
                                                   "callers": [D.snes_str(c) for c in sorted(code.xrefs.get(e, ()))],
                                                   "calls": [D.snes_str(c) for c in sorted(r.calls)],
                                                   "tables": sorted({D.snes_str(t.table) for t in r.tables})}
                                    for e, r in sorted(news.items())},
                   "tables": {D.snes_str(t): [D.snes_str(e) for e in sorted(v)] for t, v in sorted(tables.items())}},
                  f, indent=1)
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="report", choices=("report", "at", "jp"))
    ap.add_argument("addr", nargs="?")
    ap.add_argument("-n", type=int, default=60)
    ap.add_argument("--ex", action="store_true", help="T-Edition EX instead of T-Edition")
    ap.add_argument("--m16", action="store_true", help="at: start with 16-bit A (if not traced)")
    ap.add_argument("--x16", action="store_true", help="at: start with 16-bit X/Y (if not traced)")
    a = ap.parse_args(argv)
    builds = cached_builds(EX_ROM if a.ex else TED_ROM)
    tag = "_ex" if a.ex else ""
    if a.cmd == "report":
        lines = report(builds, os.path.join(OUT, f"battle_code{tag}.txt"), os.path.join(OUT, f"battle_code{tag}.json"))
        print("\n".join(lines[:2]))
        print(f"-> {os.path.join(OUT, f'battle_code{tag}.txt')}")
    elif a.cmd == "jp":
        print(builds.describe(D.parse_addr(a.addr)))
    else:
        addr = D.parse_addr(a.addr)
        code = builds.ted_code
        if addr not in code.insns:
            builds.ted_tracer.run([(addr, not a.m16, not a.x16)])
        print(code.listing(addr, addr + 0x10000)[:20000].split("\n\n")[0] if a.n <= 0 else
              "\n".join(code.listing(addr, (addr | 0xFFFF) + 1).splitlines()[:a.n]))


if __name__ == "__main__":
    main()
