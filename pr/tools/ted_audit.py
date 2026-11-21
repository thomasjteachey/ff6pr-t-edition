"""T-Edition's feature audit (pr/docs/tedition-audit.md): set rows' status and evidence, and recount the summary tables
from the checklist itself, so the % always matches the rows.

    .venv/Scripts/python tools/ted_audit.py                       # recount only
    .venv/Scripts/python tools/ted_audit.py set ID STATUS "evidence" ["work"]   # then recount

Rows are "| ID | feature | source | STATUS | evidence | work |" under "### <area>" in section 3; done = TESTED + PORTED
+ PARTIAL/2 over every row not LEFT OUT. The file's own line endings are kept.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "docs", "tedition-audit.md")
STATUSES = ("TESTED", "PORTED", "PARTIAL", "MISSING", "LEFT OUT")


def _read():
    raw = open(DOC, encoding="utf-8", newline="").read()
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def _write(text, crlf):
    with open(DOC, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", "\r\n") if crlf else text)


def rows(text):
    """[(area, id, status)] of the checklist (section 3)."""
    out, area, in3 = [], None, False
    for line in text.split("\n"):
        if line.startswith("## "):
            in3 = line.startswith("## 3.")
        elif in3 and line.startswith("### "):
            area = line[4:].strip()
        elif in3 and area and line.startswith("| ") and not line.startswith(("| ID", "|---")):
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            if len(cells) >= 4 and cells[3] in STATUSES:
                out.append((area, cells[0], cells[3]))
    return out


def set_row(text, rid, status, evidence, work=None):
    assert status in STATUSES, status
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(f"| {rid} | "):
            cells = line.strip().strip("|").split(" | ")
            cells = [c.strip() for c in cells]
            cells[3], cells[4] = status, evidence
            if work is not None and len(cells) > 5:
                cells[5] = work
            lines[i] = "| " + " | ".join(cells) + " |"
            return "\n".join(lines)
    raise SystemExit(f"no row {rid}")


def recount(text):
    rs = rows(text)
    areas = list(dict.fromkeys(a for a, _, _ in rs))
    count = {a: {s: 0 for s in STATUSES} for a in areas}
    for a, _, s in rs:
        count[a][s] += 1
    tot = {s: sum(count[a][s] for a in areas) for s in STATUSES}
    summary = ["| Area | Rows | TESTED | PORTED | PARTIAL | MISSING | LEFT OUT |", "|---|---:|---:|---:|---:|---:|---:|"]
    weighted = ["| Area | Counted rows | Done (T + P + PARTIAL/2) | Completion |", "|---|---:|---:|---:|"]

    def done(c):
        return c["TESTED"] + c["PORTED"] + c["PARTIAL"] / 2

    def fmt(x):
        return f"{x:g}"
    for a in areas:
        c = count[a]
        summary.append(f"| {a} | {sum(c.values())} | " + " | ".join(str(c[s]) for s in STATUSES) + " |")
        n = sum(c.values()) - c["LEFT OUT"]
        weighted.append(f"| {a} | {n} | {fmt(done(c))} | " + (f"{round(100 * done(c) / n)}%" if n else "(all LEFT OUT)") + " |")
    summary.append(f"| **All** | **{len(rs)}** | " + " | ".join(f"**{tot[s]}**" for s in STATUSES) + " |")
    n = len(rs) - tot["LEFT OUT"]
    weighted.append(f"| **All** | **{n}** | **{fmt(done(tot))}** | **{round(100 * done(tot) / n)}%** |")

    def replace_table(t, header, new):
        start = t.index(header)
        end = start
        while True:
            nl = t.find("\n", end)
            if nl < 0 or not t[nl + 1:].startswith("|"):
                end = len(t) if nl < 0 else nl
                break
            end = nl + 1
        return t[:start] + "\n".join(new) + t[end:]
    text = replace_table(text, summary[0], summary)
    text = replace_table(text, weighted[0], weighted)
    return text, {a: (count[a], round(100 * done(count[a]) / max(1, sum(count[a].values()) - count[a]["LEFT OUT"])))
                  for a in areas}, tot, round(100 * done(tot) / n)


# the dashboard's and PORTING.md's T-Edition rows: audit areas folded into them, with PORTING's weights
DASHBOARD = {"data": (20, ["Items and equipment", "Characters/commands/espers/magic", "Monsters/formations/AI"]),
             "maps": (15, ["Maps"]), "events": (20, ["Events/story scenes", "Pub quests", "NG+/post-game"]),
             "battle": (15, ["Mechanics/battle", "EX"]), "text": (8, ["Text/translation"]), "music": (7, ["Music"]),
             "graphics": (5, ["Graphics", "Costumes/dressing room"]),
             "menus": (5, ["Menus/UI/rooms (Collection, Achievements, Track Record)"])}


def dashboard(per, testing_pct=10):
    """{row: %} for the dashboard rows, and the weighted total (the testing row, weight 5, given)."""
    def done(c):
        return c["TESTED"] + c["PORTED"] + c["PARTIAL"] / 2

    def n(c):
        return sum(c.values()) - c["LEFT OUT"]
    out = {g: round(100 * sum(done(per[a][0]) for a in ar) / sum(n(per[a][0]) for a in ar)) for g, (_, ar) in DASHBOARD.items()}
    total = sum(w * out[g] for g, (w, _) in DASHBOARD.items()) / 100 + 5 * testing_pct / 100
    return out, total


PORTING_ROWS = {"data": "| Data through the porter:", "maps": "| Maps: T-Edition's NPC/exit/event tables",
                "events": "| Events: ~45 new events", "battle": "| Battle overhaul:",
                "text": "| Text: names (Mato's full names, done)", "music": "| Music: ~200 songs on the kit's SNES music player",
                "graphics": "| Graphics: new monster art", "menus": "| Menus: music player, dressing room"}


def sync_porting(rows, total, pct):
    """pr/PORTING.md's T-Edition weighted table, its Mod-table line and the audit figure, from the dashboard rows."""
    p = os.path.join(os.path.dirname(HERE), "PORTING.md")
    raw = open(p, encoding="utf-8", newline="").read()
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    lines = s.split("\n")
    for i, line in enumerate(lines):
        for g, prefix in PORTING_ROWS.items():
            if line.startswith(prefix):
                w = DASHBOARD[g][0]
                lines[i] = re.sub(r"\| %d \| \d+%% \| [\d.]+ \|$" % w, f"| {w} | {rows[g]}% | {w * rows[g] / 100:g} |", line)
    s = "\n".join(lines)
    s = re.sub(r"\| \*\*Total\*\* \| \*\*100\*\* \| \| \*\*~\d+\*\* \|", f"| **Total** | **100** | | **~{round(total)}** |", s, count=1)
    s = re.sub(r"\| T-Edition \(3\.0\.7 \+ EX, Mato's English\) \| ~\d+% \(table below, from the feature audit\)",
               f"| T-Edition (3.0.7 + EX, Mato's English) | ~{round(total)}% (table below, from the feature audit)", s, count=1)
    s = re.sub(r"The audit's own unweighted figure is \d+%", f"The audit's own unweighted figure is {pct}%", s, count=1)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s.replace("\n", "\r\n") if crlf else s)


def main(argv):
    text, crlf = _read()
    if argv and argv[0] == "set":
        text = set_row(text, argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else None)
    text, per, tot, pct = recount(text)
    _write(text, crlf)
    print(f"audit: {pct}% ({', '.join(f'{s} {tot[s]}' for s in STATUSES)})")
    for a, (c, p) in per.items():
        print(f"  {a}: {p}%")
    rows, total = dashboard(per)
    print(f"dashboard rows: {rows}, weighted total {total:.1f}")
    if "--porting" in argv:   # also write PORTING.md's T-Edition table from it
        sync_porting(rows, total, pct)
        print("PORTING.md synced")


if __name__ == "__main__":
    main(sys.argv[1:])
