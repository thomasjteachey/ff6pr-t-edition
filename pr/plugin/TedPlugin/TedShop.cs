using System;
using PrKit;

namespace TEdition.PR
{
    // Audit I18: in the World of Ruin every shop's buy price is doubled until Humbaba falls (T-Edition's price code).
    // The PR builds each shop's list when the shop opens (ShopUtility.CreateProductData -> ShopProductData.SetData(content,
    // productId, name, message, buy, sell, limit); decompiled tools/decomp/ted_ui1), and both the display and the purchase
    // read that buy: a prefix doubles it while the World of Ruin flag is set and the Humbaba flag isn't. The flags come
    // from ted_flags.json (TedFlags): "wor", and "humbaba" (his defeat) else "humbaba_scared_off" (T-Edition's price code
    // wasn't found: the first WoR Mobliz fight, ted-events' pick); without them the rule is off.
    static class TedShop
    {
        static string humbaba;
        internal static string State = "off (no flags)";
        internal static int Doubled;

        public static void Apply(HarmonyLib.Harmony h)
        {
            humbaba = TedFlags.Has("humbaba") ? "humbaba" : TedFlags.Has("humbaba_scared_off") ? "humbaba_scared_off" : null;
            if (!TedFlags.Has("wor") || humbaba == null) { State = "off (ted_flags.json lacks wor/humbaba)"; return; }
            Hooks.Patch(h, typeof(Last.Data.ShopProductData), "SetData", typeof(TedShop), prefix: nameof(SetData_Prefix));
            State = $"on (World of Ruin flag, Humbaba flag '{humbaba}')";
            Plugin.L.LogInfo($"[ted] shop prices: {State}");
        }

        public static bool Active => humbaba != null && TedFlags.IsSet("wor") && !TedFlags.IsSet(humbaba);

        public static void SetData_Prefix(ref int buy)
        {
            try
            {
                if (!Plugin.TedMode || buy <= 0 || !Active) return;
                buy *= 2;
                Doubled++;
                TedLog.Rule(0, "wor-prices", () => "World of Ruin shop prices doubled until Humbaba falls (audit I18)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-shop", e); }
        }
    }
}
