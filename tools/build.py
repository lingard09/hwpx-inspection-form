#!/usr/bin/env python3
"""src/app.html 템플릿에 HWPX 패키지 조각과 JSZip을 끼워 넣어 index.html 한 파일로 만든다.

    python tools/build.py

외부 의존성 없음 (Python 3.8+ 표준 라이브러리만 사용).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
PKG = TOOLS / "package"

# HWPX XML 파트에 공통으로 선언되는 네임스페이스
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


def js_string(path: Path) -> str:
    return json.dumps(path.read_text(encoding="utf-8"), ensure_ascii=False)


def main() -> None:
    html = (ROOT / "src" / "app.html").read_text(encoding="utf-8")
    replacements = {
        "/*__JSZIP__*/": (TOOLS / "jszip.min.js").read_text(encoding="utf-8"),
        '/*__HEADER__*/""': js_string(PKG / "header.xml"),
        '/*__VERSION__*/""': js_string(PKG / "version.xml"),
        '/*__CONTAINER__*/""': js_string(PKG / "container.xml"),
        '/*__RDF__*/""': js_string(PKG / "container.rdf"),
        '/*__MANIFEST__*/""': js_string(PKG / "manifest.xml"),
        '/*__NS__*/""': json.dumps(NS),
    }
    for marker, value in replacements.items():
        if marker not in html:
            raise SystemExit(f"템플릿에서 {marker} 자리를 찾지 못했습니다.")
        html = html.replace(marker, value.replace("</script", "<\\/script"))

    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✔ {out.relative_to(ROOT)} ({len(html.encode('utf-8')) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
