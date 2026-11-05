import json
import os
import re
import sys
import gzip
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from lxml import etree

# ===================== 配置 =====================
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866, "suffix": "w"},
    {"host": "192.168.19.254", "port": 8866, "suffix": "t"}
]

MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_XML_URL = "https://epg.112114.xyz/pp.xml"
EPG_GZ_URL = "https://epg.112114.xyz/pp.xml.gz"
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]
USE_SELENIUM = True
CACHE_MAP_FILE = "./epg_map.json"
REPORT_FILE = "./output/epg_mapping_report.txt"

LOGO_51ZMT_PREFIX = "https://epg.51zmt.top:8000/tb1/"
LOGO_51ZMT = {
    "CCTV1": "ys/CCTV1.png",
    "CCTV2": "ys/CCTV2.png",
    "CCTV3": "ys/CCTV3.png",
    "CCTV4": "ys/CCTV4.png",
    "CCTV5": "ys/CCTV5.png",
    "CCTV6": "ys/CCTV6.png",
    "CCTV7": "ys/CCTV7.png",
    "CCTV8": "ys/CCTV8.png",
    "CCTV9": "ys/CCTV9.png",
    "CCTV10": "ys/CCTV10.png",
    "CCTV11": "ys/CCTV11.png",
    "CCTV12": "ys/CCTV12.png",
    "CCTV13": "ys/CCTV13.png",
    "CCTV14": "ys/CCTV14.png",
    "CCTV15": "ys/CCTV15.png",
    "CCTV17": "ys/CCTV17.png",
    "CCTV4K": "ys/CCTV4K.png",
    "HunanTV": "ws/hunan.png",
    "ZhejiangTV": "ws/zhejiang.png",
    "JiangsuTV": "ws/jiangsu.png",
    "DragonTV": "ws/dongfang.png",
    "BeijingTV": "ws/beijing.png",
    "GuangdongTV": "ws/guangdong.png",
    "SichuanTV": "ws/sichuan.png",
    "ShenzhenTV": "ws/shenzhen.png",
    "ShandongTV": "ws/shandong.png",
    "CDTV1": "difang/cdtv1.png",
    "CDTV2": "difang/cdtv2.png",
    "CDTV3": "difang/cdtv3.png",
    "CDTV4": "difang/cdtv4.png",
    "CDTV5": "difang/cdtv5.png",
    "CDTV6": "difang/cdtv6.png",
    "CDTV8": "difang/cdtv8.png",
    "SCTV2": "difang/sctv2.png",
    "SCTV3": "difang/sctv3.png",
    "SCTV4": "difang/sctv4.png",
    "SCTV5": "difang/sctv5.png",
    "SCTV6": "difang/sctv6.png",
    "SCTV7": "difang/sctv7.png",
}

GROUP_CONFIG = {
    "央视频道": ["CCTV-"],
    "卫视频道": ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视", "广东卫视", "深圳卫视", "山东卫视", "四川卫视"],
    "四川地方台": ["CDTV-", "SCTV-", "i成都"],
    "其他频道": []
}

# ===================== EPG 拉取 =====================
def download_epg_xml() -> Optional[bytes]:
    try:
        resp = requests.get(EPG_GZ_URL, timeout=30)
        resp.raise_for_status()
        return gzip.decompress(resp.content)
    except Exception:
        try:
            resp = requests.get(EPG_XML_URL, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"[WARN] EPG 下载失败: {e}，尝试读取缓存")
            return None

def parse_epg_channels(xml_bytes: bytes) -> Dict[str, str]:
    parser = etree.XMLParser(no_network=True)
    root = etree.fromstring(xml_bytes, parser)
    name_to_id: Dict[str, str] = {}
    for ch in root.xpath("//channel"):
        cid = ch.get("id")
        if not cid:
            continue
        disp_name = ch.findtext("display-name")
        if not disp_name:
            continue
        norm = normalize_channel_name(disp_name)
        name_to_id[norm] = cid
    return name_to_id

def load_or_refresh_epg_map() -> Dict[str, str]:
    xml_data = download_epg_xml()
    if xml_data:
        mapping = parse_epg_channels(xml_data)
        with open(CACHE_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"[OK] 已刷新 EPG 映射，共 {len(mapping)} 个频道")
        return mapping
    else:
        if os.path.exists(CACHE_MAP_FILE):
            with open(CACHE_MAP_FILE, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            print(f"[CACHE] 使用缓存 EPG 映射，共 {len(mapping)}")
            return mapping
        print("[FATAL] 无 EPG、无缓存，无法继续")
        sys.exit(1)

def normalize_channel_name(name: str) -> str:
    s = name.strip()
    s = re.sub(r"[＋+]", "+", s)
    for kw in ["高清", "HD", "hd", "4K", "专区", "频道", "卫视", "超高清"]:
        s = s.replace(kw, "")
    s = re.sub(r"\s+", "", s)
    return s

def match_tvg_id(raw_name: str, epg_map: Dict[str, str]) -> str:
    norm = normalize_channel_name(raw_name)
    if norm in epg_map:
        return epg_map[norm]
    for k, vid in epg_map.items():
        if norm in k or k in norm:
            return vid
    return ""

# ===================== 台标 =====================
def get_channel_logo(tvid: str, raw_name: str) -> str:
    if tvid in LOGO_51ZMT:
        url = LOGO_51ZMT_PREFIX + LOGO_51ZMT[tvid]
        print(f"[LOGO 51ZMT] {raw_name} -> {url}")
        return url
    txt = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", raw_name)[:8]
    qtxt = urllib.parse.quote(txt)
    placeholder = f"https://via.placeholder.com/120x80?text={qtxt}"
    print(f"[LOGO placeholder] {raw_name} -> {placeholder}")
    return placeholder

# ===================== 网页抓取 =====================
def fetch_with_requests(url: str) -> str:
    resp = requests.get(url, verify=False, timeout=30)
    resp.raise_for_status()
    return resp.text

def fetch_with_selenium(url: str) -> str:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--ignore-certificate-errors")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.TAG_NAME, "table")
        )
        return driver.page_source
    finally:
        driver.quit()

# ========== 重点重写：解析表格，正确区分序号 / 中文名称 / UDP ==========
def parse_multicast_page(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        raise RuntimeError("页面无表格")

    out: List[Dict[str, str]] = []
    seen: set = set()
    udp_re = re.compile(r"(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}")
    chinese_re = re.compile(r"[\u4e00-\u9fa5]")

    for tr in table.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        udp_url: Optional[str] = None
        chan_name: Optional[str] = None

        for text in tds:
            m = udp_re.search(text)
            if m:
                udp_url = m.group(0)
                if not udp_url.startswith("udp://"):
                    udp_url = f"udp://@{udp_url}"
                continue
            # 包含中文的单元格，才是频道名
            if chinese_re.search(text):
                chan_name = text

        # 如果没有抓到中文名字，直接丢弃这一行（就是你之前那些数字行）
        if not udp_url or not chan_name:
            continue
        if any(k in chan_name for k in FILTER_KEYWORDS):
            continue

        key = f"{chan_name}||{udp_url}"
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": chan_name, "udp_url": udp_url})

    if not out:
        raise RuntimeError("解析不到带中文名称的有效频道")
    return out

# ===================== M3U 生成 =====================
def get_channel_group(name: str) -> str:
    for gname, prefix_list in GROUP_CONFIG.items():
        if any(p in name for p in prefix_list):
            return gname
    return "其他频道"

def parse_udp(udp_url: str) -> Optional[Dict[str, str]]:
    raw = udp_url.replace("udp://@", "")
    m = re.fullmatch(r"(\d+\.\d+\.\d+\.\d+):(\d+)", raw)
    if not m:
        return None
    return {"ip": m.group(1), "port": m.group(2)}

def build_udpxy(udp_info: Dict[str, str], host: str, port: int) -> str:
    return f"http://{host}:{port}/udp/{udp_info['ip']}:{udp_info['port']}/"

def generate_m3u_and_report(channels: List[Dict], epg_map: Dict[str, str], outdir: str):
    os.makedirs(outdir, exist_ok=True)
    grouped: Dict[str, List] = {}
    hit = 0
    miss = 0
    report_lines = []

    for ch in channels:
        g = get_channel_group(ch["name"])
        grouped.setdefault(g, []).append(ch)
        tid = match_tvg_id(ch["name"], epg_map)
        if tid:
            hit += 1
            report_lines.append(f"[HIT] {ch['name']:25} -> tvg-id={tid}")
        else:
            miss += 1
            report_lines.append(f"[MISS] {ch['name']:25} -> NO tvg-id")

    for g in grouped:
        grouped[g].sort(key=lambda x: x["name"])

    for proxy in UDPXY_PROXIES:
        lines = [
            f'#EXTM3U x-tvg-url="{EPG_XML_URL}"',
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# udpxy: {proxy['host']}:{proxy['port']}",
            ""
        ]
        for gname, chlist in grouped.items():
            for ch in chlist:
                udp_info = parse_udp(ch["udp_url"])
                if not udp_info:
                    print(f"跳过无效 UDP: {ch['name']}")
                    continue
                link = build_udpxy(udp_info, proxy["host"], proxy["port"])
                tid = match_tvg_id(ch["name"], epg_map)
                tname = ch["name"]
                logo = get_channel_logo(tid, ch["name"])
                gtitle = gname
                ext = (
                    f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{tname}" '
                    f'tvg-logo="{logo}" group-title="{gtitle}",{tname}'
                )
                lines.append(ext)
                lines.append(link)
                lines.append("")
        fn = f"IPTV_{proxy['suffix']}.m3u"
        fp = os.path.join(outdir, fn)
        with open(fp, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        print(f"输出：{fp}")

    report_lines.insert(0, f"匹配统计：命中 {hit} / 缺失 {miss}\n")
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"匹配报告：{REPORT_FILE}")

def main():
    requests.packages.urllib3.disable_warnings()
    outdir = "./output"
    print(f"输出目录：{os.path.abspath(outdir)}")
    epg_map = load_or_refresh_epg_map()
    if USE_SELENIUM:
        html = fetch_with_selenium(MULTICAST_DATA_URL)
    else:
        html = fetch_with_requests(MULTICAST_DATA_URL)
    chans = parse_multicast_page(html)
    print(f"解析频道总数：{len(chans)}")
    generate_m3u_and_report(chans, epg_map, outdir)
    print("✅ 全部完成")

if __name__ == "__main__":
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    main()
