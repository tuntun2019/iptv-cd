import os
import re
import sys
import urllib.parse
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
    "CCTV-1": "1",
    "CCTV1": "1",
    "CCTV-2": "2",
    "CCTV2": "2",
    "CCTV-3": "3",
    "CCTV3": "3",
    "CCTV-4": "4",
    "CCTV4": "4",
    "CCTV-5": "5",
    "CCTV5": "5",
    "CCTV-5+": "6",
    "CCTV5+": "6",
    "CCTV-6": "7",
    "CCTV6": "7",
    "CCTV-7": "8",
    "CCTV7": "8",
    "CCTV-8": "9",
    "CCTV8": "9",
    "CCTV-9": "10",
    "CCTV9": "10",
    "CCTV-10": "11",
    "CCTV10": "11",
    "CCTV-11": "12",
    "CCTV11": "12",
    "CCTV-12": "13",
    "CCTV12": "13",
    "CCTV-13": "14",
    "CCTV13": "14",
    "CCTV-14": "15",
    "CCTV14": "15",
    "CCTV-15": "16",
    "CCTV15": "16",
    "CCTV-17": "17",
    "CCTV17": "17",
    "CGTN": "20",
    "海峡卫视": "21",
    "CCTV4EUO": "22",
    "CCTV4AME": "23",
    "湖南卫视": "27",
    "浙江卫视": "28",
    "江苏卫视": "29",
    "北京卫视": "30",
    "东方卫视": "31",
    "安徽卫视": "32",
    "广东卫视": "33",
    "深圳卫视": "34",
    "辽宁卫视": "36",
    "旅游卫视": "37",
    "山东卫视": "38",
    "天津卫视": "39",
    "重庆卫视": "40",
    "东南卫视": "41",
    "甘肃卫视": "42",
    "广西卫视": "43",
    "贵州卫视": "44",
    "河北卫视": "45",
    "黑龙江卫视": "46",
    "河南卫视": "47",
    "湖北卫视": "48",
    "江西卫视": "50",
    "吉林卫视": "51",
    "内蒙古卫视": "52",
    "宁夏卫视": "53",
    "山西卫视": "54",
    "陕西卫视": "55",
    "四川卫视": "56",
    "新疆卫视": "57",
    "云南卫视": "58",
    "青海卫视": "59",
    "兵团卫视": "61",
    "哈哈炫动": "62",
    "延边卫视": "63",
    "黄河卫视": "65",
    "卡酷动画": "67",
    "厦门卫视": "68",
    "金鹰卡通": "69",
    "康巴卫视": "70",
    "西藏卫视": "71",
    "三沙卫视": "72",
    "中国教育1台": "73",
    "CETV-1": "73",
    "中国教育2台": "74",
    "CETV-2": "74",
    "中国教育3台": "75",
    "CETV-3": "75",
    "CCTV-4K": "106",
    "CCTV4K": "106",
    "凤凰中文": "141",
    "凤凰资讯": "142",
    "天津文艺": "334",
    "天津影视": "335",
    "天津都市频道": "336",
    "天津体育": "337",
    "天津新闻": "340",
    "江苏城市": "344",
    "江苏影视": "345",
    "江苏休闲体育": "347",
    "优漫卡通": "348",
    "江苏新闻": "349",
    "江苏综艺": "351",
    "贵州影视": "534",
    "贵州大众": "535",
    "贵州科教": "537",
    "宁夏公共": "556",
    "河北都市": "565",
    "河北少儿": "567",
    "河北经济": "568",
    "浙江经视": "657",
    "浙江钱江都市": "658",
    "浙江科教影视": "659",
    "浙江民生休闲": "660",
    "浙江公共新闻": "661",
    "浙江少儿": "662",
    "山东齐鲁": "728",
    "山东体育": "729",
    "山东综艺": "734",
    "山东生活": "735",
    "河南民生": "832",
    "河南法制": "833",
    "河南电视剧": "834",
    "河南新闻": "835",
    "河南公共": "837",
    "河南新农村": "838",
    "河南都市": "839",
    "广西综艺": "892",
    "广西都市": "893",
    "广西影视": "895",
    "广西新闻": "897",
    "云南娱乐": "932",
    "云南都市": "933",
    "云南影视": "934",
    "安徽经济生活": "1025",
    "安徽影视": "1026",
    "安徽公共": "1027",
    "安徽农业科教": "1028",
    "湖北综合": "1079",
    "湖北影视": "1080",
    "湖北教育": "1081",
    "湖北经济": "1085",
    "湖北垄上": "1086",
    "海南综合": "1128",
    "海南新闻": "1129",
    "海南公共": "1130",
    "重庆影视": "1138",
    "重庆新闻": "1139",
    "重庆少儿": "1146",
    "甘肃少儿": "1152",
    "甘肃公共": "1153",
    "甘肃文化": "1155",
    "北京纪实": "1173",
    "BTV文艺": "1174",
    "BTV影视": "1176",
    "BTV财经": "1177",
    "BTV体育": "1178",
    "BTV生活": "1179",
    "BTV新闻": "1181",
    "内蒙蒙语卫视": "1185",
    "内蒙新闻综合": "1186",
    "内蒙经济生活": "1187",
    "内蒙文体娱乐": "1188",
    "内蒙农牧": "1189",
    "内蒙少儿": "1190",
    "黑龙江影视": "1215",
    "黑龙江文体": "1216",
    "黑龙江都市": "1217",
    "黑龙江新闻法治": "1218",
    "黑龙江少儿": "1220",
    "东方财经": "1258",
    "新视觉": "1263",
    "法治天地": "1273",
    "金色": "1274",
    "全纪实": "1276",
    "欢笑剧场": "1277",
    "动漫秀场": "1279",
    "生活时尚": "1281",
    "都市剧场": "1282",
    "游戏风云": "1283",
    "上视新闻频道": "1284",
    "第一财经": "1285",
    "东方影视": "1286",
    "五星体育频道": "1287",
    "中国交通频道": "1293",
    "湖南娱乐": "1317",
    "湖南电视剧": "1318",
    "湖南电影": "1320",
    "湖南经视": "1323",
    "金鹰纪实": "1324",
    "SCTV-2": "1353",
    "SCTV2": "1353",
    "SCTV-3": "1354",
    "SCTV3": "1354",
    "SCTV-4": "1355",
    "SCTV4": "1355",
    "SCTV-5": "1356",
    "SCTV5": "1356",
    "SCTV-7": "1358",
    "SCTV7": "1358",
    "峨嵋电影": "1359",
    "SCTV-8": "1361",
    "SCTV8": "1361",
    "CDTV-1": "1363",
    "CDTV1": "1363",
    "CDTV-2": "1364",
    "CDTV2": "1364",
    "CDTV-3": "1365",
    "CDTV3": "1365",
    "CDTV-4": "1366",
    "CDTV4": "1366",
    "CDTV-5": "1367",
    "CDTV5": "1367",
    "CDTV-6": "1368",
    "CDTV6": "1368",
    "风云足球": "1424",
    "辽宁都市": "1425",
    "辽宁影视剧": "1426",
    "辽宁青少": "1427",
    "辽宁生活": "1428",
    "辽宁公共": "1429",
    "辽宁北方": "1430",
    "辽宁体育": "1431",
    "辽宁经济": "1432",
    "嘉佳卡通": "1434",
    "广东体育": "1436",
    "广东新闻": "1439",
    "求索科学": "1638",
    "CHC高清电影": "1639",
    "求索动物": "1640",
    "求索记录": "1642",
    "CHC动作电影": "1643",
    "CHC家庭电影": "1644",
    "梨园": "1645",
    "风云音乐": "1646",
    "第一剧场": "1647",
    "风云剧场": "1648",
    "世界地理": "1649",
    "怀旧剧场": "1651",
    "兵器科技": "1652",
    "女性时尚": "1653",
    "高尔夫网球": "1657",
    "央视精品": "1658",
    "汽摩": "1662",
    "天元围棋": "1667",
    "早期教育": "1670",
    "证券资讯": "1671",
    "央视台球": "1673",
    "武术世界": "1675",
    "发现之旅": "1677",
    "环球奇观": "1678",
    "国学": "1679",
    "文物宝库": "1680",
    "老故事": "1683",
    "快乐垂钓": "1684",
    "书画频道": "1685",
    "四海钓鱼": "1695",
    "环球旅游": "1697",
    "财富天下": "1712",
    "珠江频道": "1759",
    "魅力足球": "1857",
    "中国教育4台": "1860",
    "CETV-4": "1860",
    "CCTV-16": "1864",
    "CCTV16": "1864",
    "广东影视": "1865",
    "广东综艺": "1866",
    "广东经济": "1867",
    "广东少儿": "1868",
    "新疆哈语": "1940",
    "新疆维语": "1942",
    "新疆汉语": "1943",
    "新疆体育": "1944",
    "新疆少儿": "1945",
    "宁夏文旅": "1953",
    "青海都市": "1954",
    "青海经视": "1955",
    "甘肃科教": "1957",
    "陕西新闻": "1960",
    "陕西都市": "1961",
    "陕西银龄": "1962",
    "陕西秦腔": "1963",
    "陕西体育": "1964",
    "云南康旅": "1967",
    "CHC影迷电影": "1969",
    "贵州生态": "1971",
    "四川乡村": "1984",
    "重庆社会与法": "1985",
    "重庆红岩文化": "1986",
    "重庆新农村": "1987",
    "重庆红叶": "1988",
    "海南自贸": "1990",
    "海南文旅": "1991",
    "海南少儿": "1992",
    "大湾区卫视": "1995",
    "广东民生": "1996",
    "湖南爱晚": "2002",
    "江西都市": "2011",
    "江西经济": "2012",
    "江西公共": "2014",
    "江西新闻": "2015",
    "江西少儿": "2019",
    "福建综合": "2020",
    "福建新闻": "2022",
    "福建旅游": "2024",
    "福建少儿": "2027",
    "安徽综艺体育": "2029",
    "黑龙江农业科教": "2033",
    "吉视都市": "2034",
    "吉视影视": "2035",
    "吉视乡村": "2036",
    "吉视综艺文化": "2037",
    "河北文旅公共": "2042",
    "河北三农": "2043",
    "天津教育": "2045",
    "山西经济与科技": "2046",
    "山西影视": "2047",
    "山西社会与法治": "2048",
    "山西文体生活": "2049",
    "吉视生活": "2051",
    "noepg": "9999"
}

GROUP_RULES = [
    ("央视频道", [r"^CCTV\-", r"^CCTV\d", r"^CETV\-", r"中国教育", r"CGTN", r"央视"]),
    ("卫视频道", [r"卫视"]),
    ("四川地方", [r"^CDTV\-", r"^CDTV\d", r"^SCTV\-", r"^SCTV\d", r"四川", r"峨眉",r"康巴卫视"]),
    ("CHC影院", [r"CHC"]),
    ("数字付费", [r"风云", "求索", "梨园", "第一剧场", "世界地理", "怀旧剧场", "兵器科技", "书画频道", "四海钓鱼", "快乐垂钓", "天元围棋"]),
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
    display_name = name.strip() if name else "Channel"
    if len(display_name) > 10:
        display_name = display_name[:9] + "…"
    encoded_text = urllib.parse.quote(display_name, safe="")
    logo_url = (
        f"https://mockimg.dev/120x80/4A4545/FFFFFF.svg"
        f"?text={encoded_text}&bold=true"
    )
    return logo_url

def get_channel_group(name: str) -> str:
    for group, patterns in GROUP_RULES:
        for pat in patterns:
            if re.search(pat, name):
                return group
    return "其他频道"

def get_tvg_id(name: str) -> str | None:
    core = extract_core_name(name)
    tid = TVG_ID_MAPPING.get(core)
    print(f"[EPG DEBUG] raw={name} → core={core} → tvg-id={tid}")
    return tid

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

# ===================== 页面抓取 =====================
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

    chrome_options.binary_location = "/usr/bin/chromium-browser"
    service = Service("/usr/lib/chromium-browser/chromedriver")

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
