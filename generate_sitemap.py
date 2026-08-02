import xml.etree.ElementTree as ET
from xml.dom import minidom
from urllib.parse import urlencode, quote
import os
from datetime import datetime

def generate_sitemap(domain="https://boss-news.pages.dev"):
    """
    구글 및 타 검색엔진을 위한 sitemap.xml 생성 스크립트.

    동일 호스트(URL만 포함. 기사 원문은 외부 도메인이므로 사이트맵에 넣지 않음
    (GSC: 다른 도메인 URL = URL not allowed).
    """
    base = domain.rstrip("/")
    today = datetime.now().strftime("%Y-%m-%d")

    urlset = ET.Element("urlset", {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
    })

    # 1. 메인 홈페이지 URL
    main_url = ET.SubElement(urlset, "url")
    ET.SubElement(main_url, "loc").text = base + "/"
    ET.SubElement(main_url, "lastmod").text = today
    ET.SubElement(main_url, "changefreq").text = "hourly"
    ET.SubElement(main_url, "priority").text = "1.0"

    # 2. 카테고리 필터 URL (쿼리 값 percent-encode)
    categories = ["정치/외교", "경제/부동산", "사회/사법", "IT/과학", "문화/연예/스포츠", "지역/사설", "일반/종합"]
    for cat in categories:
        cat_url = ET.SubElement(urlset, "url")
        query = urlencode({"category": cat}, quote_via=quote)
        ET.SubElement(cat_url, "loc").text = f"{base}/?{query}"
        ET.SubElement(cat_url, "lastmod").text = today
        ET.SubElement(cat_url, "changefreq").text = "hourly"
        ET.SubElement(cat_url, "priority").text = "0.8"

    # XML 정렬 및 파일 저장
    rough = ET.tostring(urlset, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    # encoding 인자 사용 시 bytes → str 변환 후 빈 줄 제거
    xml_str = pretty.decode("utf-8")
    lines = [line for line in xml_str.splitlines() if line.strip()]
    cleaned_xml = "\n".join(lines) + "\n"

    sitemap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(cleaned_xml)

    url_count = len(urlset.findall("url"))
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] sitemap.xml 생성 완료! ({url_count} URLs) ({sitemap_path})")

if __name__ == "__main__":
    generate_sitemap()
