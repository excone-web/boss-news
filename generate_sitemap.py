import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import json
from datetime import datetime

def generate_sitemap(domain="https://boss-news.pages.dev"):
    """
    구글 및 타 검색엔진을 위한 sitemap.xml 생성 스크립트
    """
    urlset = ET.Element("urlset", {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "xmlns:news": "http://www.google.com/schemas/sitemap-news/0.9"
    })

    # 1. 메인 홈페이지 URL
    main_url = ET.SubElement(urlset, "url")
    ET.SubElement(main_url, "loc").text = domain.rstrip('/') + '/'
    ET.SubElement(main_url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(main_url, "changefreq").text = "hourly"
    ET.SubElement(main_url, "priority").text = "1.0"

    # 2. 카테고리별 URL 파라미터 링크
    categories = ["정치/외교", "경제/부동산", "사회/사법", "IT/과학", "문화/연예/스포츠", "지역/사설", "일반/종합"]
    for cat in categories:
        cat_url = ET.SubElement(urlset, "url")
        ET.SubElement(cat_url, "loc").text = f"{domain.rstrip('/')}/?category={cat}"
        ET.SubElement(cat_url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
        ET.SubElement(cat_url, "changefreq").text = "hourly"
        ET.SubElement(cat_url, "priority").text = "0.8"

    # 3. articles.json 읽어 최신 기사 정보가 있으면 포함
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "articles.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
                
            # 최근 100개 기사만 sitemap-news로 등록
            for art in articles[:100]:
                art_url = ET.SubElement(urlset, "url")
                ET.SubElement(art_url, "loc").text = art.get("url", domain)
                
                pub_date = art.get("published_at", "")
                if pub_date:
                    try:
                        date_str = pub_date[:10]
                    except Exception:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                ET.SubElement(art_url, "lastmod").text = date_str
                ET.SubElement(art_url, "changefreq").text = "daily"
                ET.SubElement(art_url, "priority").text = "0.6"
        except Exception as e:
            print(f"[Sitemap Error] 기사 목록 파싱 중 오류: {e}")

    # XML 정렬 및 파일 저장
    xml_str = minidom.parseString(ET.tostring(urlset, 'utf-8')).toprettyxml(indent="  ")
    
    # XML 선언 태그 깔끔히 정리
    lines = [line for line in xml_str.splitlines() if line.strip()]
    cleaned_xml = "\n".join(lines)

    sitemap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(cleaned_xml)
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] sitemap.xml 생성 완료! ({sitemap_path})")

if __name__ == "__main__":
    generate_sitemap()
