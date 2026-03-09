// ============================================================
//  YOUTUBE HORIZONTAL VIDEO ADS SAFE ZONE OVERLAY
//  Color: Red (#FF2D2D)
//  Canvas: 1920 × 1080 px  (16:9)
//
//  ✅ OFFICIAL GOOGLE SOURCE: support.google.com/google-ads/answer/9128498
//
//  The safe zone is an IRREGULAR POLYGON — NOT a simple rectangle.
//  Two notches are cut from the top corners for UI elements:
//
//    Top center strip:    38px  — system bar / top chrome
//    Left notch:         496px wide × 183px tall  — channel info, title
//    Right notch:        475px wide × 133px tall  — video controls, progress
//    Left body margin:    38px  — left edge clear zone
//    Right body margin:  162px  — right edge clear zone
//    Bottom margin:      387px  — engagement bar, recommended videos
//
//  Safe zone polygon vertices (clockwise):
//    (496, 38) → (1445, 38) → (1445, 133) → (1758, 133)
//    → (1758, 693) → (38, 693) → (38, 183) → (496, 183) → close
//
//  Source: support.google.com/google-ads/answer/9128498 (official)
// ============================================================
#target photoshop

(function () {

    var PLATFORM = "YouTube | Horizontal Video Ads";
    var COLOR      = [255, 45, 45];
    var COLOR_FILL = [255, 80, 80];
    var FILL_ALPHA = 30;

    // ── Official pixel values (1920×1080) ─────────────────────
    var TOP_CENTER  = 38;   // top chrome
    var LEFT_NOTCH_W  = 496;  var LEFT_NOTCH_H  = 183;  // channel info block
    var RIGHT_NOTCH_W = 475;  var RIGHT_NOTCH_H = 133;  // video controls block
    var LEFT_BODY   = 38;   // body left margin
    var RIGHT_BODY  = 162;  // body right margin
    var BOTTOM      = 387;  // engagement / recommendations

    if (!app.documents.length) { alert("Open a 1920×1080px document first."); return; }
    var doc  = app.activeDocument;
    var orig = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    var W = doc.width.as("px");   // 1920
    var H = doc.height.as("px"); // 1080

    // Derived polygon coordinates
    var TL_X = LEFT_NOTCH_W;            // 496  — top-left of safe zone top section
    var TR_X = W - RIGHT_NOTCH_W;       // 1445 — top-right of safe zone top section
    var R_X  = W - RIGHT_BODY;          // 1758 — right body edge
    var BOT_Y = H - BOTTOM;             // 693  — bottom of safe zone
    var L_X  = LEFT_BODY;               // 38   — left body edge

    var grp = doc.layerSets.add();
    grp.name = "▶ YouTube Horizontal Safe Zone  (official 1920×1080)";

    // ── 1. Danger zone fills ─────────────────────────────────
    var dangerLayer = grp.artLayers.add();
    dangerLayer.name = "danger-fill";
    dangerLayer.opacity = FILL_ALPHA;
    setFG(COLOR_FILL);

    fillRect(doc, 0,    0,    LEFT_NOTCH_W,  LEFT_NOTCH_H);   // top-left notch
    fillRect(doc, TL_X, 0,    TR_X - TL_X,   TOP_CENTER);     // top centre strip
    fillRect(doc, TR_X, 0,    RIGHT_NOTCH_W, RIGHT_NOTCH_H);  // top-right notch
    fillRect(doc, R_X,  RIGHT_NOTCH_H, RIGHT_BODY, BOT_Y - RIGHT_NOTCH_H);  // right margin
    fillRect(doc, 0,    BOT_Y, W,             BOTTOM);         // bottom strip
    fillRect(doc, 0,    LEFT_NOTCH_H, LEFT_BODY, BOT_Y - LEFT_NOTCH_H);     // left margin

    // ── 2. Safe zone polygon border ─────────────────────────
    var borderLayer = grp.artLayers.add();
    borderLayer.name = "safe-zone-border";
    borderLayer.opacity = 95;
    setFG(COLOR);
    var T = 4; // line thickness

    // Top edge (centre)
    fillRect(doc, TL_X, TOP_CENTER,         TR_X - TL_X, T);
    // Left notch vertical drop
    fillRect(doc, TL_X, TOP_CENTER,         T,            LEFT_NOTCH_H - TOP_CENTER);
    // Left shoulder horizontal
    fillRect(doc, L_X,  LEFT_NOTCH_H,       TL_X - L_X + T, T);
    // Left body vertical
    fillRect(doc, L_X,  LEFT_NOTCH_H,       T,            BOT_Y - LEFT_NOTCH_H);
    // Bottom edge
    fillRect(doc, L_X,  BOT_Y - T,          R_X - L_X,   T);
    // Right body vertical
    fillRect(doc, R_X - T, RIGHT_NOTCH_H,  T,            BOT_Y - RIGHT_NOTCH_H);
    // Right shoulder horizontal
    fillRect(doc, TR_X,    RIGHT_NOTCH_H,  R_X - TR_X,   T);
    // Right notch vertical rise
    fillRect(doc, TR_X,    TOP_CENTER,     T,            RIGHT_NOTCH_H - TOP_CENTER);

    // ── 3. Corner tick accents ───────────────────────────────
    var tickLayer = grp.artLayers.add();
    tickLayer.name = "corner-ticks";
    setFG(COLOR);
    var len = 28;
    // Top-left of safe zone top section
    fillRect(doc, TL_X, TOP_CENTER, len, T + 2);
    fillRect(doc, TL_X, TOP_CENTER, T + 2, len);
    // Top-right
    fillRect(doc, TR_X - len, TOP_CENTER, len, T + 2);
    fillRect(doc, TR_X - T - 2, TOP_CENTER, T + 2, len);
    // Bottom-left
    fillRect(doc, L_X, BOT_Y - T, len, T + 2);
    fillRect(doc, L_X, BOT_Y - len, T + 2, len);
    // Bottom-right
    fillRect(doc, R_X - len, BOT_Y - T, len, T + 2);
    fillRect(doc, R_X - T - 2, BOT_Y - len, T + 2, len);

    // ── 4. Dimension labels ──────────────────────────────────
    addTextLabel(doc, grp, TL_X + 12, TOP_CENTER + 34,
        PLATFORM + " Safe Zone", COLOR, 22);
    addTextLabel(doc, grp, TL_X + 12, TOP_CENTER + 60,
        "▲ " + TOP_CENTER + "px top (centre)  |  Left notch " + LEFT_NOTCH_W + "×" + LEFT_NOTCH_H + "px  |  Right notch " + RIGHT_NOTCH_W + "×" + RIGHT_NOTCH_H + "px",
        COLOR, 16);
    addTextLabel(doc, grp, TL_X + 12, TOP_CENTER + 82,
        "▼ " + BOTTOM + "px bottom  |  Left body " + LEFT_BODY + "px  |  Right body " + RIGHT_BODY + "px",
        COLOR, 16);
    addTextLabel(doc, grp, TL_X + 12, BOT_Y - 14,
        "Source: support.google.com/google-ads/answer/9128498  (official)", COLOR, 15);

    app.preferences.rulerUnits = orig;

    var safeW = R_X - L_X;
    var safeH = BOT_Y - LEFT_NOTCH_H;
    alert(
        "YouTube Horizontal Safe Zone overlay added ✓\n\n" +
        "OFFICIAL GOOGLE SPECS (1920×1080)\n" +
        "─────────────────────────────────\n" +
        "Top (centre):     " + TOP_CENTER + "px\n" +
        "Left notch:       " + LEFT_NOTCH_W + "px wide × " + LEFT_NOTCH_H + "px tall\n" +
        "Right notch:      " + RIGHT_NOTCH_W + "px wide × " + RIGHT_NOTCH_H + "px tall\n" +
        "Left body:        " + LEFT_BODY + "px\n" +
        "Right body:       " + RIGHT_BODY + "px\n" +
        "Bottom:           " + BOTTOM + "px\n" +
        "─────────────────────────────────\n" +
        "Main body area:   " + safeW + "×" + safeH + "px\n\n" +
        "⚠ Shape is an irregular polygon —\n" +
        "  not a simple rectangle."
    );

})();

function setFG(rgb) { var c=new SolidColor(); c.rgb.red=rgb[0]; c.rgb.green=rgb[1]; c.rgb.blue=rgb[2]; app.foregroundColor=c; }
function fillRect(doc,x,y,w,h) { if(w<=0||h<=0)return; var cx=Math.max(0,Math.round(x)),cy=Math.max(0,Math.round(y)); var cw=Math.min(Math.round(w),doc.width.as("px")-cx),ch=Math.min(Math.round(h),doc.height.as("px")-cy); if(cw<=0||ch<=0)return; try{doc.selection.select([[cx,cy],[cx+cw,cy],[cx+cw,cy+ch],[cx,cy+ch]],SelectionType.REPLACE,0,false);doc.selection.fill(app.foregroundColor,ColorBlendMode.NORMAL,100,false);doc.selection.deselect();}catch(e){} }
function addTextLabel(doc,parent,x,y,text,rgb,size) { try{var tl=parent.artLayers.add();tl.kind=LayerKind.TEXT;tl.name="label";var ti=tl.textItem;ti.kind=TextType.POINTTEXT;ti.contents=text;ti.size=new UnitValue(size,"pt");ti.antiAliasMethod=AntiAlias.SHARP;ti.fauxBold=true;var c=new SolidColor();c.rgb.red=rgb[0];c.rgb.green=rgb[1];c.rgb.blue=rgb[2];ti.color=c;ti.position=[x,y];}catch(e){} }
