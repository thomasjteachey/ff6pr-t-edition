using System;
using Last.Defaine.User;
using Last.Interpreter;
using Last.Management;
using PrKit;

namespace TEdition.PR
{
    // SysCall "TED:roster <c 0-13> <k 0-7> <var>" (ted-events' translation of T-Edition's A4/A5 bit tests on
    // $1850 + c): map-local variable <var> = bit k of the SNES's roster byte for character c, made from the PR's parties:
    //   bits 0-2 the party it is in (1-3, 0 none), 3-4 its order in that party (0-3), 5 back row, 6 in a party.
    // The PR keeps three party slots (UserDataManager.GetCorpsListClone(slot 0-2), each a List<Corps>: the position is
    // the order, Corps.CharacterId the OwnedCharacterData.Id, Corps.Id the row: CorpsId.Front 1 / Back 2).
    static class TedRoster
    {
        internal static string Last = "";

        public static int Byte(int c)
        {
            var udm = UserDataManager.Instance();
            if (udm == null || c < 0 || c > 13) return 0;
            int uid = 0;
            foreach (var o in udm.OwnedCharacterList)
                if (o != null && o.characterStatusId == c + 1) { uid = o.Id; break; }
            if (uid == 0) return 0;
            for (int slot = 0; slot < 3; slot++)
            {
                var list = udm.GetCorpsListClone(slot);
                if (list == null) continue;
                for (int i = 0; i < list.Count; i++)
                {
                    var e = list[i];
                    if (e == null || e.CharacterId != uid) continue;
                    return (slot + 1) | ((i & 3) << 3) | (e.Id == CorpsId.Back ? 0x20 : 0) | 0x40;
                }
            }
            return 0;
        }

        public static void Call(int c, int bit, int var)
        {
            int b = Byte(c);
            int value = bit >= 0 && bit < 8 ? (b >> bit) & 1 : 0;
            DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, var, value);
            Last = $"character {c}: roster byte {b:X2}, bit {bit} = {value} -> map-local {var}";
            Hooks.NoteOnce($"ted-roster-{c}-{bit}", () => $"[ted] roster: {Last}");
        }
    }
}
