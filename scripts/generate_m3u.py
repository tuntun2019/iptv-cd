import os
import re
import sys
import base64
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ===================== 核心配置 =====================
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866, "suffix": "w"},
    {"host": "192.168.19.254", "port": 8866, "suffix": "t"}
]

MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "http://epg.51zmt.top:8000/e1.xml.gz"
FILTER_KEYWORDS = ["画中画", "PIP", "pip", "测试", "广告"]

TVG_ID_MAPPING = {
    "CCTV-1": "cctv1",
    "CCTV-2": "cctv2",
    "CCTV-3": "cctv3",
    "CCTV-4": "cctv4",
    "CCTV-5": "cctv5",
    "CCTV-6": "cctv6",
    "CCTV-7": "cctv7",
    "CCTV-8": "cctv8",
    "CCTV-9": "cctv9",
    "CCTV-10": "cctv10",
    "CCTV-11": "cctv11",
    "CCTV-12": "cctv12",
    "CCTV-13": "cctv13",
    "CCTV-14": "cctv14",
    "CCTV-15": "cctv15",
    "CCTV-17": "cctv17",
    "CCTV-5+": "cctv5plus",
    "CCTV-4K": "cctv4k",
    "湖南卫视": "hunan",
    "浙江卫视": "zhejiang",
    "江苏卫视": "jiangsu",
    "东方卫视": "dongfang",
    "北京卫视": "btv",
    "广东卫视": "guangdong",
    "深圳卫视": "shenzhen",
    "山东卫视": "shandong",
    "四川卫视": "sichuan",
    "安徽卫视": "anhui",
    "河南卫视": "henan",
    "湖北卫视": "hubei",
    "河北卫视": "hebei",
    "江西卫视": "jiangxi",
    "辽宁卫视": "liaoning",
    "重庆卫视": "chongqing",
    "贵州卫视": "guizhou",
    "云南卫视": "yunnan",
    "广西卫视": "guangxi",
    "陕西卫视": "shaanxi",
    "山西卫视": "shanxi",
    "吉林卫视": "jilin",
    "黑龙江卫视": "heilongjiang",
    "海南卫视": "hainan",
    "宁夏卫视": "ningxia",
    "甘肃卫视": "gansu",
    "新疆卫视": "xinjiang",
    "内蒙古卫视": "neimenggu",
    "西藏卫视": "xizang",
    "青海卫视": "qinghai",
    "CETV-1": "cetv1",
    "CETV-2": "cetv2",
    "CETV-4": "cetv4",
    "CGTN英语": "cgtnen",
    "CGTN西班牙语": "cgtnes",
    "CGTN法语": "cgtnfr",
    "CGTN阿拉伯语": "cgtnar",
    "CGTN俄语": "cgtnru",
    "CHC家庭影院": "chc_home",
    "CHC影迷电影": "chc_movie",
    "CHC动作电影": "chc_action",
    "CDTV-1": "cdtv1",
    "CDTV-2": "cdtv2",
    "CDTV-3": "cdtv3",
    "CDTV-4": "cdtv4",
    "CDTV-5": "cdtv5",
    "CDTV-6": "cdtv6",
    "CDTV-8": "cdtv8",
    "SCTV-2": "sctv2",
    "SCTV-3": "sctv3",
    "SCTV-4": "sctv4",
    "SCTV-5": "sctv5",
    "SCTV-6": "sctv6",
    "SCTV-7": "sctv7",
    "SCTV-科教": "sctvke",
    "i成都": "ichengdu"
}

GROUP_RULES = [
    ("央视频道", [r"^CCTV\-", r"^CETV\-", r"CGTN"]),
    ("卫视频道", [r"卫视"]),
    ("四川地方", [r"^CDTV\-", r"^SCTV\-", r"i成都"]),
    ("CHC影院", [r"CHC"]),
]

# ===================== 清洗辅助 =====================
def clean_channel_name(name: str) -> str:
    name = re.sub(r"[（(].*?[）)]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def extract_core_name(name: str) -> str:
    core = name
    core = re.sub(r"高清|HD|4K|超清|专区|频道", "", core, flags=re.IGNORECASE)
    core = core.replace("CCTV-5＋", "CCTV-5+")
    core = core.strip()
    return core

def get_channel_logo(name: str) -> str:
    """生成内嵌SVG base64占位图，原生支持中文，无外网依赖"""
    display_name = name if name else "Channel"
    svg = f'''<svg width="120" height="80" xmlns="http://www.w3.org/2000/svg">
  <rect width="120" height="80" fill="#8899aa"/>
  <text x="60" y="48" font-family="Noto Sans CJK SC,sans-serif" font-size="16" fill="#ffffff" text-anchor="middle">{display_name}</text>
</svg>'''
    b = svg.encode("utf-8")
    b64 = base64.b64encode(b).decode("ascii")
    data_uri = f"data:image/svg+xml;base64,{b64}"
    print(f"[LOGO] {name} -> svg base64")
    return data_uri

def get_channel_group(name: str) -> str:
    for group, patterns in GROUP_RULES:
        for pat in patterns:
            if re.search(pat, name):
                return group
    return "其他频道"

def get_tvg_id(name: str) -> str | None:
    core = extract_core_name(name)
    return TVG_ID_MAPPING.get(core)

def get_tvg_name(name: str) -> str:
    return name

def parse_udp_url(raw: str):
    raw = raw.strip()
    raw = raw.replace("udp://@", "")
    m = re.fullmatch(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)", raw)
    if not m:
        return None
    return {"ip": m.group(1), "port": m.group(2)}

def generate_udpxy_url(udp_info, host, port) -> str:
    if not udp_info:
        return ""
    return f"http://{host}:{port}/udp/{udp_info['ip']}:{udp_info['port']}/"

# ===================== 页面抓取：优先静态，失败再动态 =====================
def fetch_multicast_data(url: str):
    sess = requests.Session()
    sess.verify = False
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("尝试静态抓取页面 ...")
        resp = sess.get(url, timeout=20, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        chans = parse_page_channels(soup, resp.text)
        if chans:
            return chans
        print("静态解析为空，尝试 Selenium 动态渲染 ...")
    except Exception as e:
        print(f"静态请求失败：{e}，切换动态渲染")

    return fetch_with_selenium(url)

def parse_page_channels(soup: BeautifulSoup, raw_text: str):
    rows = soup.select("table tr")
    udp_re = re.compile(r"(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}")
    found = []
    seen = set()

    for tr in rows:
        tds = [clean_channel_name(td.get_text(strip=True)) for td in tr.select("td")]
        if len(tds) < 2:
            continue

        udp_url = None
        chan_name = None
        for cell in tds:
            m = udp_re.search(cell)
            if m:
                udp_url = m.group(0)
                if not udp_url.startswith("udp://"):
                    udp_url = f"udp://@{udp_url}"
            else:
                if cell and not chan_name and not re.fullmatch(r"\d+", cell):
                    chan_name = cell

        if not (chan_name and udp_url):
            continue
        chan_name = clean_channel_name(chan_name)
        if any(k in chan_name for k in FILTER_KEYWORDS):
            continue
        key = f"{chan_name}|{udp_url}"
        if key in seen:
            continue
        seen.add(key)
        found.append({"name": chan_name, "udp_url": udp_url})

    return found

def fetch_with_selenium(url: str):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except ImportError:
        service = Service()

    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        return parse_page_channels(soup, html)
    finally:
        driver.quit()

# ===================== M3U 生成 =====================
def generate_m3u(channels, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    grouped: dict[str, list] = {}
    for ch in channels:
        g = get_channel_group(ch["name"])
        grouped.setdefault(g, []).append(ch)

    for proxy in UDPXY_PROXIES:
        lines = [
            f'#EXTM3U x-tvg-url="{EPG_URL}"',
            f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# udpxy：{proxy['host']}:{proxy['port']}",
            ""
        ]
        for gname in grouped:
            for ch in grouped[gname]:
                udp_info = parse_udp_url(ch["udp_url"])
                stream_url = generate_udpxy_url(udp_info, proxy["host"], proxy["port"])
                if not stream_url:
                    print(f"跳过无效流：{ch['name']}")
                    continue

                tvg_id = get_tvg_id(ch["name"])
                tvg_name = get_tvg_name(ch["name"])
                tvg_logo = get_channel_logo(ch["name"])
                group_title = gname

                if tvg_id:
                    extinf = (
                        f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" '
                        f'tvg-logo="{tvg_logo}" group-title="{group_title}",{tvg_name}'
                    )
                else:
                    extinf = (
                        f'#EXTINF:-1 tvg-name="{tvg_name}" '
                        f'tvg-logo="{tvg_logo}" group-title="{group_title}",{tvg_name}'
                    )
                lines.append(extinf)
                lines.append(stream_url)
                lines.append("")

        fn = f"IPTV_{proxy['suffix']}.m3u"
        fp = os.path.join(output_dir, fn)
        with open(fp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"输出：{fp}")

def main():
    output_dir = "./output"
    print(f"输出目录：{os.path.abspath(output_dir)}")
    chans = fetch_multicast_data(MULTICAST_DATA_URL)
    if not chans:
        print("错误：没有解析到任何频道")
        sys.exit(1)
    print(f"成功解析频道数量：{len(chans)}")
    generate_m3u(chans, output_dir)
    print("\n✅ 完成")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
