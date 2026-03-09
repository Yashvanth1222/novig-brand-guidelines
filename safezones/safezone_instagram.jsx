// ============================================================
//  INSTAGRAM REELS SAFE ZONE OVERLAY — Novig Brand Tool
//  Color: Pink (#FF4FA0)
//  Canvas: 1080 × 1920 px
//
//  ✅ OFFICIAL META SOURCE: Meta Ads Manager / Meta Business Help
//     "Understand the safe zone for ads" — Meta for Business
//     Applies to: Stories, Reels, Facebook in-stream Reels (9:16)
//
//  The safe zone is an IRREGULAR POLYGON — NOT a simple rectangle.
//  Meta publishes percentage-based margins; converted to pixels below.
//
//  OFFICIAL PERCENTAGES → PIXELS (1080×1920):
//    Top:                14% → 269px  (header bar, username, sponsored)
//    Left:                6% →  65px  (left edge margin)
//    Right (upper):       6% →  65px  (right edge margin, above engagement col)
//    Engagement col width:21% → 227px from right → left edge at x=853
//    Engagement col height:40%→ 768px from bottom → top at y=1152
//    Bottom (left side):  35% → 672px from bottom → y=1248
//
//  SAFE ZONE POLYGON VERTICES (clockwise):
//    (65, 269) → (1015, 269) → (1015, 1152) → (853, 1152)
//    → (853, 1248) → (65, 1248) → close
//
//  Source: Meta Ads Manager Safe Zone guardrail / Meta for Business
//          "Understand the safe zone for ads" (official)
// ============================================================
#target photoshop

(function () {

    var PLATFORM = "Instagram Reels";
    var COLOR      = [255, 79, 160];    // pink
    var COLOR_FILL = [255, 105, 180];
    var FILL_ALPHA = 30;

    // ── Official Meta pixel values (1080×1920) ────────────────
    var TOP      = 269;   // 14% × 1920
    var LEFT     = 65;    // 6%  × 1080
    var RIGHT_UPPER = 65; // 6%  × 1080 (right margin for upper zone)
    var ENG_COL_W = 227;  // 21% × 1080 — engagement column width from right
    var ENG_COL_TOP = 1152; // 1920 - (40% × 1920) — top of engagement col
    var BOT_LEFT = 1248;    // 1920 - (35% × 1920) — bottom of left safe area

    // Derived coordinates
    var X_LEFT   = LEFT;                       // 65
    var X_RIGHT  = 1080 - RIGHT_UPPER;         // 1015
    var X_ENG    = 1080 - ENG_COL_W;           // 853 — engagement col left edge

    var UI = {
        top:    "Header bar · Username · Sponsored label",
        engCol: "Like · Comment · Share · More icons (21% wide, 40% tall)",
        bottom: "Caption · Audio track · CTA (35% from bottom)"
    };

    if (!app.documents.length) { alert("Open a 1080\u00d71920px document first."); return; }
    var doc  = app.activeDocument;
    var orig = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    var W = doc.width.as("px");
    var H = doc.height.as("px");

    var grp = doc.layerSets.add();
    grp.name = "\ud83d\udcf8 Instagram Safe Zone (official Meta) \u2014 polygon shape";

    // ── 1. Danger zone fills ─────────────────────────────────
    var fillLayer = grp.artLayers.add();
    fillLayer.name = "danger-fill";
    fillLayer.opacity = FILL_ALPHA;
    setFG(COLOR_FILL);

    fillRect(doc, 0,       0,    W,           TOP);               // top header strip
    fillRect(doc, 0,       TOP,  LEFT,        BOT_LEFT - TOP);    // left margin
    fillRect(doc, X_RIGHT, TOP,  W - X_RIGHT, ENG_COL_TOP - TOP);// right upper margin
    fillRect(doc, X_ENG,   ENG_COL_TOP, W - X_ENG, H - ENG_COL_TOP); // engagement col + below
    fillRect(doc, 0,       BOT_LEFT, X_ENG,   H - BOT_LEFT);     // bottom-left strip

    // ── 2. Safe zone polygon border ─────────────────────────
    var borderLayer = grp.artLayers.add();
    borderLayer.name = "safe-zone-polygon-border";
    borderLayer.opacity = 95;
    setFG(COLOR);
    var T = 4;

    // Polygon segments (clockwise):
    // Top edge:      (X_LEFT, TOP)      → (X_RIGHT, TOP)
    fillRect(doc, X_LEFT,  TOP,             X_RIGHT - X_LEFT, T);
    // Right edge:    (X_RIGHT, TOP)     → (X_RIGHT, ENG_COL_TOP)
    fillRect(doc, X_RIGHT - T, TOP,         T, ENG_COL_TOP - TOP);
    // Step in:       (X_RIGHT, ENG_COL_TOP) → (X_ENG, ENG_COL_TOP)
    fillRect(doc, X_ENG,   ENG_COL_TOP,     X_RIGHT - X_ENG, T);
    // Right col edge:(X_ENG, ENG_COL_TOP) → (X_ENG, BOT_LEFT)
    fillRect(doc, X_ENG - T, ENG_COL_TOP,  T, BOT_LEFT - ENG_COL_TOP);
    // Bottom edge:   (X_ENG, BOT_LEFT)  → (X_LEFT, BOT_LEFT)
    fillRect(doc, X_LEFT,  BOT_LEFT - T,    X_ENG - X_LEFT, T);
    // Left edge:     (X_LEFT, BOT_LEFT) → (X_LEFT, TOP)
    fillRect(doc, X_LEFT,  TOP,             T, BOT_LEFT - TOP);

    // ── 3. Corner ticks ──────────────────────────────────────
    var tickLayer = grp.artLayers.add();
    tickLayer.name = "corner-ticks";
    setFG(COLOR);
    var len = 32;
    // Top-left
    fillRect(doc, X_LEFT, TOP, len, T + 2); fillRect(doc, X_LEFT, TOP, T + 2, len);
    // Top-right
    fillRect(doc, X_RIGHT - len, TOP, len, T + 2); fillRect(doc, X_RIGHT - T - 2, TOP, T + 2, len);
    // Bottom-left
    fillRect(doc, X_LEFT, BOT_LEFT - T, len, T + 2); fillRect(doc, X_LEFT, BOT_LEFT - len, T + 2, len);
    // Inner corner (engagement col top-left)
    fillRect(doc, X_ENG, ENG_COL_TOP, len, T + 2); fillRect(doc, X_ENG - T - 2, ENG_COL_TOP, T + 2, len);
    // Inner corner (engagement col bottom = BOT_LEFT)
    fillRect(doc, X_ENG - len, BOT_LEFT - T, len, T + 2); fillRect(doc, X_ENG - T - 2, BOT_LEFT - len, T + 2, len);

    // ── 4. Disclaimer Ads Layer (40% full-width bottom) ─────
    //  Official Meta: "If you're including disclaimers on your Reels ads,
    //  leave the bottom 40% of your ad free from text, logos and other
    //  key creative elements." → 40% × 1920 = 768px from bottom = y=1152
    var DISCLAIMER_Y = ENG_COL_TOP; // 1152px = 40% from bottom (same y as eng col top)
    var disclaimerGrp = grp.layerSets.add();
    disclaimerGrp.name = "⚠ Disclaimer Ads — bottom 40% (768px) full width";

    var disclaimerFill = disclaimerGrp.artLayers.add();
    disclaimerFill.name = "disclaimer-danger-fill";
    disclaimerFill.opacity = 22;
    setFG([255, 140, 0]);  // orange
    fillRect(doc, 0, DISCLAIMER_Y, W, H - DISCLAIMER_Y);

    var disclaimerLine = disclaimerGrp.artLayers.add();
    disclaimerLine.name = "disclaimer-boundary";
    disclaimerLine.opacity = 90;
    setFG([255, 140, 0]);
    drawDashedHLine(doc, 0, DISCLAIMER_Y, W, 24, 12, 3);

    addTextLabel(doc, disclaimerGrp, X_LEFT + 14, DISCLAIMER_Y - 12,
        "⚠ Disclaimer Ads: bottom 40% (768px) must be fully clear — orange dashed line",
        [255, 140, 0], 15);

    // ── 5. Labels ────────────────────────────────────────────
    addTextLabel(doc, grp, X_LEFT + 14, TOP + 38,
        PLATFORM + " Safe Zone  \u2014  Official Meta Spec (polygon)", COLOR, 22);
    addTextLabel(doc, grp, X_LEFT + 14, TOP + 64,
        "\u25b2 " + TOP + "px (14%)  |  \u25b6\u25c4 " + LEFT + "px (6%) each side  |  Source: Meta Ads Manager", COLOR, 16);
    addTextLabel(doc, grp, X_LEFT + 14, BOT_LEFT - 14,
        "\u25bc " + (H - BOT_LEFT) + "px from bottom (35%)  |  " + UI.bottom, COLOR, 16);
    addTextLabel(doc, grp, X_ENG + 6, ENG_COL_TOP + 30,
        "Engagement col\n21% wide / 40% tall", COLOR, 15);
    addTextLabel(doc, grp, X_LEFT + 14, ENG_COL_TOP + 30,
        "Safe area: " + (X_ENG - X_LEFT) + "\u00d7" + (BOT_LEFT - ENG_COL_TOP) + "px (lower-left strip)", COLOR, 15);

    app.preferences.rulerUnits = orig;

    alert(
        "Instagram Reels Safe Zone overlay added \u2713\n\n" +
        "SOURCE: Official Meta — Meta Ads Manager\n" +
        "\"Understand the safe zone for ads\"\n\n" +
        "POLYGON VERTICES:\n" +
        "  (" + X_LEFT + ", " + TOP + ") \u2192 (" + X_RIGHT + ", " + TOP + ")\n" +
        "  \u2192 (" + X_RIGHT + ", " + ENG_COL_TOP + ") \u2192 (" + X_ENG + ", " + ENG_COL_TOP + ")\n" +
        "  \u2192 (" + X_ENG + ", " + BOT_LEFT + ") \u2192 (" + X_LEFT + ", " + BOT_LEFT + ")\n\n" +
        "Top:              " + TOP + "px  (14%)\n" +
        "Left/Right:       " + LEFT + "px  (6% each)\n" +
        "Engagement col:   " + ENG_COL_W + "px wide (21%), " + (H - ENG_COL_TOP) + "px tall (40%)\n" +
        "Bottom (L side):  " + (H - BOT_LEFT) + "px  (35%)\n\n" +
        "Shape is an IRREGULAR POLYGON\u2014not a rectangle."
    );

})();

function setFG(rgb) { var c=new SolidColor(); c.rgb.red=rgb[0]; c.rgb.green=rgb[1]; c.rgb.blue=rgb[2]; app.foregroundColor=c; }
function fillRect(doc,x,y,w,h) { if(w<=0||h<=0)return; var cx=Math.max(0,Math.round(x)),cy=Math.max(0,Math.round(y)); var cw=Math.min(Math.round(w),doc.width.as("px")-cx),ch=Math.min(Math.round(h),doc.height.as("px")-cy); if(cw<=0||ch<=0)return; try{doc.selection.select([[cx,cy],[cx+cw,cy],[cx+cw,cy+ch],[cx,cy+ch]],SelectionType.REPLACE,0,false);doc.selection.fill(app.foregroundColor,ColorBlendMode.NORMAL,100,false);doc.selection.deselect();}catch(e){} }
function drawDashedHLine(doc,x,y,w,dash,gap,t) { var pos=0,on=true; while(pos<w){var seg=Math.min(on?dash:gap,w-pos);if(on)fillRect(doc,x+pos,y,seg,t);pos+=seg;on=!on;} }
function addTextLabel(doc,parent,x,y,text,rgb,size) { try{var tl=parent.artLayers.add();tl.kind=LayerKind.TEXT;tl.name="label";var ti=tl.textItem;ti.kind=TextType.POINTTEXT;ti.contents=text;ti.size=new UnitValue(size,"pt");ti.antiAliasMethod=AntiAlias.SHARP;ti.fauxBold=true;var c=new SolidColor();c.rgb.red=rgb[0];c.rgb.green=rgb[1];c.rgb.blue=rgb[2];ti.color=c;ti.position=[x,y];}catch(e){} }
