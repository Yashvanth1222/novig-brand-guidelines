// ============================================================
//  SNAPCHAT SAFE ZONE OVERLAY — Novig Brand Tool
//  Color: Yellow (#FFD400)
//  Canvas: 1080 × 1920 px
//
//  Safe zone margins (sourced 2025/2026):
//    Top    150px — Progress bar, snap sender info, close button
//    Bottom 150px — Send button, emoji reaction, swipe-up CTA
//    Left    60px — General screen edge margin
//    Right   60px — General screen edge margin
//
//  OFFICIAL Snapchat guidance (businesshelp.snapchat.com):
//    "Keep logos, text and disclaimers out of top 150px and bottom 150px."
//    Recommended safe content area: 1080×1500px (420px total top+bottom).
//    Note: 1080×1500 centered = 210px each side, but Snap's official
//    minimum buffer is 150px. This script uses the official 150px value.
//
//  Source: businesshelp.snapchat.com (official), benly.ai, upbeatagency.com
// ============================================================
#target photoshop

(function () {

    var PLATFORM   = "Snapchat";
    var TOP        = 150;   // official: businesshelp.snapchat.com
    var BOTTOM     = 150;   // official: businesshelp.snapchat.com
    var LEFT       = 60;
    var RIGHT      = 60;
    var COLOR      = [255, 212, 0];     // Snapchat yellow
    var COLOR_FILL = [255, 230, 50];
    var FILL_ALPHA = 30;

    var UI = {
        top:    "Progress bar · Sender avatar · Close (X) button",
        bottom: "Send button · Emoji reaction · Swipe-up / CTA",
        right:  "Edge margin (no persistent icons)"
    };

    if (!app.documents.length) { alert("Open a 1080×1920px document first."); return; }
    var doc  = app.activeDocument;
    var orig = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    var W = doc.width.as("px");
    var H = doc.height.as("px");

    var SX = LEFT;
    var SY = TOP;
    var SW = W - LEFT - RIGHT;
    var SH = H - TOP  - BOTTOM;

    var grp = doc.layerSets.add();
    grp.name = "👻 Snapchat Safe Zone  ▲" + TOP + " ▼" + BOTTOM + " ◀" + RIGHT + " ▶" + LEFT;

    var fillLayer = grp.artLayers.add();
    fillLayer.name = "danger-fill";
    fillLayer.opacity = FILL_ALPHA;
    setFG(COLOR_FILL);
    fillRect(doc, 0,        0,          W,     TOP);
    fillRect(doc, 0,        H - BOTTOM, W,     BOTTOM);
    // Snapchat has minimal left/right UI — light fills only
    fillRect(doc, 0,        TOP,        LEFT,  SH);
    fillRect(doc, W - RIGHT, TOP,        RIGHT, SH);

    var borderLayer = grp.artLayers.add();
    borderLayer.name = "safe-zone-border";
    borderLayer.opacity = 95;
    setFG(COLOR);
    drawBorder(doc, SX, SY, SW, SH, 4);

    var tickLayer = grp.artLayers.add();
    tickLayer.name = "corner-ticks";
    setFG(COLOR);
    drawCornerTicks(doc, SX, SY, SW, SH, 32, 4);

    addTextLabel(doc, grp, SX + 14, SY + 36,
        "▲ " + TOP + "px from top  |  " + UI.top, COLOR, 18);
    addTextLabel(doc, grp, SX + 14, H - BOTTOM - 8,
        "▼ " + BOTTOM + "px from bottom  |  " + UI.bottom, COLOR, 18);
    addTextLabel(doc, grp, SX + 14, SY + SH / 2,
        "◀▶ " + RIGHT + "px each side  |  " + UI.right, COLOR, 18);
    addTextLabel(doc, grp, SX + 14, SY + 68,
        PLATFORM + " Safe Zone  —  " + SW + "×" + SH + "px clear area", COLOR, 22);

    app.preferences.rulerUnits = orig;
    alert("Snapchat Safe Zone overlay added ✓\n\nTop:    " + TOP + "px  (official)\nBottom: " + BOTTOM + "px  (official)\nLeft:   " + LEFT + "px\nRight:  " + RIGHT + "px\nSafe area: " + SW + "×" + SH + "px\n\nSource: businesshelp.snapchat.com\nSnap officially requires logos/text clear\nof top 150px and bottom 150px.\nRecommended content area: 1080×1500px.");

})();

function setFG(rgb) { var c=new SolidColor(); c.rgb.red=rgb[0]; c.rgb.green=rgb[1]; c.rgb.blue=rgb[2]; app.foregroundColor=c; }
function fillRect(doc,x,y,w,h) { if(w<=0||h<=0)return; var cx=Math.max(0,Math.round(x)),cy=Math.max(0,Math.round(y)); var cw=Math.min(Math.round(w),doc.width.as("px")-cx),ch=Math.min(Math.round(h),doc.height.as("px")-cy); if(cw<=0||ch<=0)return; try{doc.selection.select([[cx,cy],[cx+cw,cy],[cx+cw,cy+ch],[cx,cy+ch]],SelectionType.REPLACE,0,false);doc.selection.fill(app.foregroundColor,ColorBlendMode.NORMAL,100,false);doc.selection.deselect();}catch(e){} }
function drawBorder(doc,x,y,w,h,t) { fillRect(doc,x,y,w,t);fillRect(doc,x,y+h-t,w,t);fillRect(doc,x,y,t,h);fillRect(doc,x+w-t,y,t,h); }
function drawCornerTicks(doc,x,y,w,h,len,t) { fillRect(doc,x,y,len,t);fillRect(doc,x,y,t,len);fillRect(doc,x+w-len,y,len,t);fillRect(doc,x+w-t,y,t,len);fillRect(doc,x,y+h-t,len,t);fillRect(doc,x,y+h-len,t,len);fillRect(doc,x+w-len,y+h-t,len,t);fillRect(doc,x+w-t,y+h-len,t,len); }
function addTextLabel(doc,parent,x,y,text,rgb,size) { try{var tl=parent.artLayers.add();tl.kind=LayerKind.TEXT;tl.name="label";var ti=tl.textItem;ti.kind=TextType.POINTTEXT;ti.contents=text;ti.size=new UnitValue(size,"pt");ti.antiAliasMethod=AntiAlias.SHARP;ti.fauxBold=true;var c=new SolidColor();c.rgb.red=rgb[0];c.rgb.green=rgb[1];c.rgb.blue=rgb[2];ti.color=c;ti.position=[x,y];}catch(e){} }
