"""한글(HWP 5.x) 양식의 문서 정보(DocInfo)를 HWPX header.xml로 변환한다.

tools/package/header.xml 은 이 스크립트로 원본 양식에서 뽑아 둔 결과물이다.
양식이 바뀌었을 때만 다시 실행하면 된다.

    pip install pyhwp
    hwp5proc xml 양식.hwp > form.xml
    python tools/make_header.py form.xml tools/package/header.xml

글꼴·글자 모양·문단 모양·테두리/배경·스타일을 원본 ID 그대로 옮기므로,
src/app.html 의 charPr/paraPr/borderFill 번호가 원본 양식과 같은 의미를 가진다.
"""
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr as qa

NS = ('xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
      'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
      'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
      'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
      'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
      'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
      'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
      'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
      'xmlns:dc="http://purl.org/dc/elements/1.1/" '
      'xmlns:opf="http://www.idpf.org/2007/opf/" '
      'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
      'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
      'xmlns:epub="http://www.idpf.org/2007/ops" '
      'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"')

LANGS = [("HANGUL", "ko"), ("LATIN", "en"), ("HANJA", "cn"), ("JAPANESE", "jp"),
         ("OTHER", "other"), ("SYMBOL", "symbol"), ("USER", "user")]
ATTR = {"ko": "hangul", "en": "latin", "cn": "hanja", "jp": "japanese",
        "other": "other", "symbol": "symbol", "user": "user"}
COUNT_KEY = {"ko": "ko-fonts", "en": "en-fonts", "cn": "cn-fonts", "jp": "jp-fonts",
             "other": "other-fonts", "symbol": "symbol-fonts", "user": "user-fonts"}


def langattrs(el):
    return " ".join(f'{ATTR[k]}="{el.get(k)}"' for _, k in LANGS)


def stroke(s):
    return {"none": "NONE", "solid": "SOLID", "dashed": "DASH", "dotted": "DOT",
            "double": "DOUBLE_SLIM"}.get(s, "SOLID")


def width(w):
    return w.replace("mm", " mm")


def build(form_xml):
    root = ET.parse(form_xml).getroot()
    idm = root.find(".//IdMappings")
    out = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hh:head {NS} version="1.5" secCnt="1">',
           '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/><hh:refList>']

    # --- fonts (HWP5 stores them in ko,en,cn,jp,other,symbol,user order)
    faces = list(idm.iter("FaceName"))
    out.append('<hh:fontfaces itemCnt="7">')
    pos = 0
    for lang, key in LANGS:
        n = int(idm.get(COUNT_KEY[key]))
        out.append(f'<hh:fontface lang="{lang}" fontCnt="{n}">')
        for i, f in enumerate(faces[pos:pos + n]):
            typ = "HFT" if f.get("font-file-type") == "hft" else "TTF"
            out.append(f'<hh:font id="{i}" face={qa(f.get("name"))} type="{typ}" isEmbedded="0"/>')
        out.append('</hh:fontface>')
        pos += n
    out.append('</hh:fontfaces>')

    # --- border fills (ids are 1-based)
    bfs = list(idm.iter("BorderFill"))
    out.append(f'<hh:borderFills itemCnt="{len(bfs)}">')
    for i, b in enumerate(bfs, 1):
        bd = {x.get("attribute-name"): x for x in b.findall("Border")}
        s = [f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">',
             '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>']
        for side in ("left", "right", "top", "bottom"):
            x = bd[side]
            s.append(f'<hh:{side}Border type="{stroke(x.get("stroke-type"))}" width="{width(x.get("width"))}" color="{x.get("color").upper()}"/>')
        dg = bd["diagonal"]
        s.append(f'<hh:diagonal type="{stroke(dg.get("stroke-type"))}" width="{width(dg.get("width"))}" color="{dg.get("color").upper()}"/>')
        fp = b.find("FillColorPattern")
        if fp is not None:
            s.append(f'<hc:fillBrush><hc:winBrush faceColor="{fp.get("background-color").upper()}" '
                     f'hatchColor="{fp.get("pattern-color").upper()}" alpha="0"/></hc:fillBrush>')
        s.append('</hh:borderFill>')
        out.append("".join(s))
    out.append('</hh:borderFills>')

    # --- char shapes
    css = list(idm.iter("CharShape"))
    out.append(f'<hh:charProperties itemCnt="{len(css)}">')
    for i, c in enumerate(css):
        s = [f'<hh:charPr id="{i}" height="{c.get("basesize")}" textColor="{c.get("text-color").upper()}" '
             f'shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">',
             f'<hh:fontRef {langattrs(c.find("FontFace"))}/>',
             f'<hh:ratio {langattrs(c.find("LetterWidthExpansion"))}/>',
             f'<hh:spacing {langattrs(c.find("LetterSpacing"))}/>',
             f'<hh:relSz {langattrs(c.find("RelativeSize"))}/>',
             f'<hh:offset {langattrs(c.find("Position"))}/>']
        if c.get("bold") == "1":
            s.append('<hh:bold/>')
        if c.get("italic") == "1":
            s.append('<hh:italic/>')
        ul = "NONE" if c.get("underline") == "none" else "BOTTOM"
        s.append(f'<hh:underline type="{ul}" shape="SOLID" color="{c.get("underline-color").upper()}"/>'
                 '<hh:strikeout shape="NONE" color="#000000"/><hh:outline type="NONE"/>'
                 f'<hh:shadow type="NONE" color="{c.get("shadow-color").upper()}" offsetX="10" offsetY="10"/></hh:charPr>')
        out.append("".join(s))
    out.append('</hh:charProperties>')

    # --- tabs
    tds = list(idm.iter("TabDef"))
    out.append(f'<hh:tabProperties itemCnt="{len(tds)}">')
    for i, td in enumerate(tds):
        tabs = td.findall(".//Tab")
        head = f'<hh:tabPr id="{i}" autoTabLeft="{td.get("autotab-left")}" autoTabRight="{td.get("autotab-right")}"'
        if not tabs:
            out.append(head + '/>')
        else:
            items = "".join(
                f'<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">'
                f'<hh:tabItem pos="{int(tb.get("pos")) // 2}" type="{tb.get("kind").upper()}" leader="DOT" unit="HWPUNIT"/></hp:case>'
                f'<hp:default><hh:tabItem pos="{tb.get("pos")}" type="{tb.get("kind").upper()}" leader="DOT"/></hp:default></hp:switch>'
                for tb in tabs)
            out.append(head + '>' + items + '</hh:tabPr>')
    out.append('</hh:tabProperties>')

    # --- numbering (outline numbering, copied pattern)
    fmts = [("DIGIT", "^1."), ("HANGUL_SYLLABLE", "^2."), ("DIGIT", "^3)"), ("HANGUL_SYLLABLE", "^4)"),
            ("DIGIT", "(^5)"), ("HANGUL_SYLLABLE", "(^6)"), ("CIRCLED_DIGIT", "^7")]
    nb = ['<hh:numberings itemCnt="1"><hh:numbering id="1" start="0">']
    for lv in range(1, 11):
        f, txt = fmts[lv - 1] if lv <= 7 else ("DIGIT", "")
        nb.append(f'<hh:paraHead start="1" level="{lv}" align="LEFT" useInstWidth="1" autoIndent="1" widthAdjust="0" '
                  f'textOffsetType="PERCENT" textOffset="50" numFormat="{f}" charPrIDRef="4294967295" checkable="0">{txt}</hh:paraHead>')
    nb.append('</hh:numbering></hh:numberings>')
    out.append("".join(nb))

    # --- para shapes
    ALIGN = {"both": "JUSTIFY", "left": "LEFT", "right": "RIGHT", "center": "CENTER",
             "distribute": "DISTRIBUTE", "divide": "DISTRIBUTE_SPACE"}
    LS = {"ratio": "PERCENT", "fixed": "FIXED", "spaceonly": "BETWEEN_LINES", "atleast": "AT_LEAST"}
    pss = list(idm.iter("ParaShape"))
    out.append(f'<hh:paraProperties itemCnt="{len(pss)}">')
    for i, p in enumerate(pss):
        g = p.get
        heading = "NONE"
        if g("head-shape") == "outline":
            heading = "OUTLINE"
        brk_h = "BREAK_WORD" if g("linebreak-hangul") == "char" else "KEEP_WORD"
        brk_l = "KEEP_WORD" if g("linebreak-alphabet") == "word" else "BREAK_WORD"
        ls_type = LS.get(g("linespacing-type"), "PERCENT")
        ls = int(g("linespacing"))
        vals = {"intent": int(g("indent")), "left": int(g("doubled-margin-left")),
                "right": int(g("doubled-margin-right")), "prev": int(g("doubled-margin-top")),
                "next": int(g("doubled-margin-bottom"))}

        def margin(div):
            m = "".join(f'<hc:{k} value="{v // div}" unit="HWPUNIT"/>' for k, v in vals.items())
            lsv = ls if ls_type == "PERCENT" else ls // div
            return f'<hh:margin>{m}</hh:margin><hh:lineSpacing type="{ls_type}" value="{lsv}" unit="HWPUNIT"/>'

        out.append(
            f'<hh:paraPr id="{i}" tabPrIDRef="{g("tabdef-id")}" condense="{g("minimum-space")}" '
            f'fontLineHeight="{g("lineheight-along-fontsize")}" snapToGrid="{g("use-paper-grid")}" suppressLineNumbers="0" checked="0">'
            f'<hh:align horizontal="{ALIGN[g("align")]}" vertical="{"CENTER" if g("valign") == "center" else "BASELINE"}"/>'
            f'<hh:heading type="{heading}" idRef="0" level="{g("level")}"/>'
            f'<hh:breakSetting breakLatinWord="{brk_l}" breakNonLatinWord="{brk_h}" widowOrphan="0" keepWithNext="0" '
            f'keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
            f'<hh:autoSpacing eAsianEng="{g("autospace-alphabet")}" eAsianNum="{g("autospace-number")}"/>'
            f'<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">{margin(2)}</hp:case>'
            f'<hp:default>{margin(1)}</hp:default></hp:switch>'
            f'<hh:border borderFillIDRef="{g("borderfill-id")}" offsetLeft="{g("border-left")}" offsetRight="{g("border-right")}" '
            f'offsetTop="{g("border-top")}" offsetBottom="{g("border-bottom")}" connect="{g("linked-border")}" '
            f'ignoreMargin="{g("ignore-margin")}"/></hh:paraPr>')
    out.append('</hh:paraProperties>')

    # --- styles
    sts = list(idm.iter("Style"))
    out.append(f'<hh:styles itemCnt="{len(sts)}">')
    for i, s in enumerate(sts):
        typ = "CHAR" if s.get("kind") == "character" else "PARA"
        out.append(f'<hh:style id="{i}" type="{typ}" name={qa(s.get("local-name"))} engName={qa(s.get("name"))} '
                   f'paraPrIDRef="{s.get("parashape-id")}" charPrIDRef="{s.get("charshape-id")}" '
                   f'nextStyleIDRef="{s.get("next-style-id")}" langID="{s.get("lang-id")}" lockForm="0"/>')
    out.append('</hh:styles>')

    out.append('</hh:refList><hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument>'
               '<hh:docOption><hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/></hh:docOption>'
               '<hh:trackchageConfig flags="56"/></hh:head>')
    return "".join(out)


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "form.xml"
    dst = sys.argv[2] if len(sys.argv) > 2 else "header.xml"
    h = build(src)
    ET.fromstring(h)  # well-formedness check
    open(dst, "w", encoding="utf-8").write(h)
    print(dst, len(h))
