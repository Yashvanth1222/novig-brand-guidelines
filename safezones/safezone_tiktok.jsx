// ============================================================
//  TIKTOK TOPVIEW SAFE ZONE OVERLAY — Novig Brand Tool
//  Color: Dark Gray (#3C3C3C / "Light Black")
//  Canvas: 1080 × 1920 px
//
//  ✅ OFFICIAL TIKTOK SOURCE: TopView Ad Specifications
//     "TopView safe zones.zip" — TikTok Ads Manager documentation
//
//  TikTok TopView has TWO distinct phases with different safe zones:
//
//  PHASE 1 — Initial 3-second open screen (less restrictive)
//  ─────────────────────────────────────────────────────────────
//  Source canvas: 720×1280px → scaled ×1.5 to 1080×1920px
//    Top:    160px → 240px  (TikTok header bar + logo)
//    Bottom: 160px → 240px  (swipe-up / skip area)
//    Left:    80px → 120px  (device crop zone — blue zone)
//    Right:   80px → 120px  (device crop zone — blue zone)
//  Safe area: 840×1440px
//
//  PHASE 2 — After 3-sec in-feed (MORE RESTRICTIVE — use this for logos)
//  ─────────────────────────────────────────────────────────────
//  Source canvas: 720×1280px → scaled ×1.5 to 1080×1920px
//    Top:    160px → 240px  (TikTok header bar + username)
//    Bottom: 440px → 660px  (caption + CTA + engagement base)
//    Left:    80px → 120px  (device crop zone)
//    Right:  200px → 300px  (80px crop + 120px engagement column)
//  Safe area: 660×1020px
//
//  ZONE KEY (from official TikTok diagrams):
//    Red Zone  = blocked by UI elements — NO content here
//    Blue Zone = may be cropped by device — avoid critical content
//    Blank     = safe area for all content
//
//  Note: In-feed safe zone (Phase 2) is more restrictive than open
//  screen. TikTok recommends following BOTH to ensure logo/text
//  placement is safe across all stages of the TopView ad.
//
//  Source: TikTok Ads Manager — TopView Ad Specifications (official)
// ============================================================
#target photoshop

(function () {

    var PLATFORM = "TikTok TopView";

    // ── PHASE 1 values at 1080×1920 (scaled from 720×1280 × 1.5) ──
    var P1_TOP    = 240;
    var P1_BOTTOM = 240;
    var P1_LEFT   = 120;
    var P1_RIGHT  = 120;

    // ── PHASE 2 values at 1080×1920 (scaled from 720×1280 × 1.5) ──
    var P2_TOP    = 240;
    var P2_BOTTOM = 660;
    var P2_LEFT   = 120;
    var P2_RIGHT  = 300;  // 80px crop zone + 120px engagement col, × 1.5

    // Colors
    var COLOR_P1   = [80, 80, 80];      // dark gray — Phase 1 border
    var COLOR_P2   = [30, 30, 30];      // near-black — Phase 2 border (primary)
    var COLOR_RED  = [200, 50, 50];     // red zone fill
    var COLOR_BLUE = [60, 120, 220];    // blue crop zone fill
    var FILL_ALPHA_RED  = 35;
    var FILL_ALPHA_BLUE = 25;

    if (!app.documents.length) { alert("Open a 1080×1920px document first."); return; }
    var doc  = app.activeDocument;
    var orig = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    var W = doc.width.as("px");
    var H = doc.height.as("px");

    // ── Master group ──────────────────────────────────────────
    var master = doc.layerSets.add();
    master.name = "🎵 TikTok TopView Safe Zones (official)";

    // ╔══════════════════════════════════════════════════════╗
    // ║  PHASE 2 — IN-FEED (primary, most restrictive)       ║
    // ╚══════════════════════════════════════════════════════╝
    var grp2 = master.layerSets.add();
    grp2.name = "PHASE 2 — In-Feed (after 3s)  ▲" + P2_TOP + " ▼" + P2_BOTTOM + " ▶" + P2_LEFT + " ◀" + P2_RIGHT;

    var P2_SX = P2_LEFT;
    var P2_SY = P2_TOP;
    var P2_SW = W - P2_LEFT - P2_RIGHT;
    var P2_SH = H - P2_TOP  - P2_BOTTOM;

    // Red danger fills
    var p2Red = grp2.artLayers.add();
    p2Red.name = "red-zone (UI blocked)";
    p2Red.opacity = FILL_ALPHA_RED;
    setFG(COLOR_RED);
    fillRect(doc, 0,           0,          W,        P2_TOP);       // top header
    fillRect(doc, 0,           H-P2_BOTTOM, W,       P2_BOTTOM);    // bottom caption/CTA
    fillRect(doc, W-P2_RIGHT,  P2_TOP,     P2_RIGHT, P2_SH);        // right engagement col

    // Blue crop zone fills
    var p2Blue = grp2.artLayers.add();
    p2Blue.name = "blue-zone (device crop)";
    p2Blue.opacity = FILL_ALPHA_BLUE;
    setFG(COLOR_BLUE);
    fillRect(doc, 0,           P2_TOP, P2_LEFT,  P2_SH);   // left crop zone
    // Right blue crop is already inside the red zone; skip to avoid double-fill

    // Safe zone border
    var p2Border = grp2.artLayers.add();
    p2Border.name = "safe-zone-border";
    p2Border.opacity = 95;
    setFG(COLOR_P2);
    drawBorder(doc, P2_SX, P2_SY, P2_SW, P2_SH, 4);
    drawCornerTicks(doc, P2_SX, P2_SY, P2_SW, P2_SH, 36, 4);

    // Labels
    addTextLabel(doc, grp2, P2_SX + 14, P2_SY + 38,
        "PHASE 2: In-Feed Safe Zone  —  " + P2_SW + "\u00d7" + P2_SH + "px", COLOR_P2, 22);
    addTextLabel(doc, grp2, P2_SX + 14, P2_SY + 66,
        "Use this zone for logos & key content", COLOR_P2, 17);
    addTextLabel(doc, grp2, P2_SX + 14, P2_SY + 90,
        "\u25b2 " + P2_TOP + "px  |  \u25bc " + P2_BOTTOM + "px  |  \u25b6 " + P2_LEFT + "px  |  \u25c4 " + P2_RIGHT + "px  (scaled from 720\u00d71280 \u00d71.5)", COLOR_P2, 15);
    addTextLabel(doc, grp2, P2_SX + 14, H - P2_BOTTOM - 10,
        "\u25bc " + P2_BOTTOM + "px  —  Caption + CTA + engagement col base", COLOR_RED, 17);
    addTextLabel(doc, grp2, P2_SX + 14, P2_SY + P2_SH / 2,
        "\u25c4 " + P2_RIGHT + "px  —  80px crop zone + 120px engagement column", COLOR_P2, 17);

    // ╔══════════════════════════════════════════════════════╗
    // ║  PHASE 1 — INITIAL 3-SECOND (reference only)         ║
    // ╚══════════════════════════════════════════════════════╝
    var grp1 = master.layerSets.add();
    grp1.name = "PHASE 1 — Open Screen (first 3s)  \u25b2" + P1_TOP + " \u25bc" + P1_BOTTOM + " \u25b6\u25c4" + P1_LEFT;

    var P1_SX = P1_LEFT;
    var P1_SY = P1_TOP;
    var P1_SW = W - P1_LEFT - P1_RIGHT;
    var P1_SH = H - P1_TOP  - P1_BOTTOM;

    // Dashed border for Phase 1 (secondary reference)
    var p1Border = grp1.artLayers.add();
    p1Border.name = "phase1-border (dashed)";
    p1Border.opacity = 55;
    setFG(COLOR_P1);
    drawDashedHLine(doc, P1_SX, P1_SY,            P1_SW, 20, 10, 3);  // top
    drawDashedHLine(doc, P1_SX, P1_SY + P1_SH - 3, P1_SW, 20, 10, 3); // bottom
    drawDashedVLine(doc, P1_SX,            P1_SY, P1_SH, 20, 10, 3);  // left
    drawDashedVLine(doc, P1_SX + P1_SW - 3, P1_SY, P1_SH, 20, 10, 3); // right

    addTextLabel(doc, grp1, P1_SX + 14, P1_SY + 38,
        "PHASE 1: Open Screen (first 3s)  \u2014  " + P1_SW + "\u00d7" + P1_SH + "px  [dashed = reference]", COLOR_P1, 18);
    addTextLabel(doc, grp1, P1_SX + 14, P1_SY + 62,
        "\u25b2\u25bc " + P1_TOP + "px  |  \u25b6\u25c4 " + P1_LEFT + "px each side", COLOR_P1, 15);

    app.preferences.rulerUnits = orig;

    alert(
        "TikTok TopView Safe Zone overlay added \u2713\n\n" +
        "SOURCE: Official TikTok TopView Ad Specifications\n" +
        "(720\u00d71280px reference \u00d71.5 \u2192 1080\u00d71920px)\n\n" +
        "PHASE 1 \u2014 Open Screen (first 3s)\n" +
        "  Top/Bottom: " + P1_TOP + "px  |  Left/Right: " + P1_LEFT + "px\n" +
        "  Safe area: " + P1_SW + "\u00d7" + P1_SH + "px\n\n" +
        "PHASE 2 \u2014 In-Feed after 3s  (USE FOR LOGOS)\n" +
        "  Top:    " + P2_TOP + "px\n" +
        "  Bottom: " + P2_BOTTOM + "px\n" +
        "  Left:   " + P2_LEFT + "px\n" +
        "  Right:  " + P2_RIGHT + "px\n" +
        "  Safe area: " + P2_SW + "\u00d7" + P2_SH + "px\n\n" +
        "ZONE KEY:\n" +
        "  Red fill  = UI blocked (no content)\n" +
        "  Blue fill = device crop zone (avoid)\n" +
        "  Blank     = safe for all content\n\n" +
        "Solid border = Phase 2 (primary)\n" +
        "Dashed border = Phase 1 (reference)"
    );

})();

// ── HELPERS ───────────────────────────────────────────────────
function setFG(rgb) { var c=new SolidColor(); c.rgb.red=rgb[0]; c.rgb.green=rgb[1]; c.rgb.blue=rgb[2]; app.foregroundColor=c; }
function fillRect(doc,x,y,w,h) { if(w<=0||h<=0)return; var cx=Math.max(0,Math.round(x)),cy=Math.max(0,Math.round(y)); var cw=Math.min(Math.round(w),doc.width.as("px")-cx),ch=Math.min(Math.round(h),doc.height.as("px")-cy); if(cw<=0||ch<=0)return; try{doc.selection.select([[cx,cy],[cx+cw,cy],[cx+cw,cy+ch],[cx,cy+ch]],SelectionType.REPLACE,0,false);doc.selection.fill(app.foregroundColor,ColorBlendMode.NORMAL,100,false);doc.selection.deselect();}catch(e){} }
function drawBorder(doc,x,y,w,h,t) { fillRect(doc,x,y,w,t);fillRect(doc,x,y+h-t,w,t);fillRect(doc,x,y,t,h);fillRect(doc,x+w-t,y,t,h); }
function drawCornerTicks(doc,x,y,w,h,len,t) { fillRect(doc,x,y,len,t);fillRect(doc,x,y,t,len);fillRect(doc,x+w-len,y,len,t);fillRect(doc,x+w-t,y,t,len);fillRect(doc,x,y+h-t,len,t);fillRect(doc,x,y+h-len,t,len);fillRect(doc,x+w-len,y+h-t,len,t);fillRect(doc,x+w-t,y+h-len,t,len); }
function drawDashedHLine(doc,x,y,w,dash,gap,t) { var pos=0,on=true; while(pos<w){var seg=Math.min(on?dash:gap,w-pos);if(on)fillRect(doc,x+pos,y,seg,t);pos+=seg;on=!on;} }
function drawDashedVLine(doc,x,y,h,dash,gap,t) { var pos=0,on=true; while(pos<h){var seg=Math.min(on?dash:gap,h-pos);if(on)fillRect(doc,x,y+pos,t,seg);pos+=seg;on=!on;} }
function addTextLabel(doc,parent,x,y,text,rgb,size) { try{var tl=parent.artLayers.add();tl.kind=LayerKind.TEXT;tl.name="label";var ti=tl.textItem;ti.kind=TextType.POINTTEXT;ti.contents=text;ti.size=new UnitValue(size,"pt");ti.antiAliasMethod=AntiAlias.SHARP;ti.fauxBold=true;var c=new SolidColor();c.rgb.red=rgb[0];c.rgb.green=rgb[1];c.rgb.blue=rgb[2];ti.color=c;ti.position=[x,y];}catch(e){} }
