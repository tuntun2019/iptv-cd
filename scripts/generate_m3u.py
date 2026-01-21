import json
import os
import re
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== 核心配置（多源台标+自动降级）=====================
# 代理IP与文件名后缀映射
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866, "suffix": "w"},
    {"host": "192.168.19.254", "port": 8866, "suffix": "t"}
]
MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "https://epg.112114.xyz/epg.xml"
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]

# 3个公开稳定的台标库（按稳定性排序，自动降级）
LOGO_SOURCES = {
    # A源：epg.pw（优先使用，你目标格式中的源）
    "A": {
        "prefix": "https://epg.pw/logos/",
        "mapping": {
            "CCTV-1": "cctv1.png",
            "CCTV-2": "cctv2.png",
            "CCTV-3": "cctv3.png",
            "CCTV-5": "cctv5.png",
            "湖南卫视": "hunan.png",
            "浙江卫视": "zhejiang.png",
            "江苏卫视": "jiangsu.png",
            "东方卫视": "dongfang.png",
            "北京卫视": "beijing.png",
            "广东卫视": "guangdong.png",
        }
    },
    # B源：iptv-logo.com（备用源，公开免费）
    "B": {
        "prefix": "https://iptv-logo.com/logos/",
        "mapping": {
            "CCTV-1": "cctv-1.png",
            "CCTV-2": "cctv-2.png",
            "CCTV-3": "cctv-3.png",
            "CCTV-4": "cctv-4.png",
            "CCTV-5": "cctv-5.png",
            "CCTV-6": "cctv-6.png",
            "湖南卫视": "hunan-tv.png",
            "浙江卫视": "zhejiang-tv.png",
            "江苏卫视": "jiangsu-tv.png",
            "东方卫视": "dongfang-tv.png",
            "北京卫视": "beijing-tv.png",
            "广东卫视": "guangdong-tv.png",
            "深圳卫视": "shenzhen-tv.png",
            "山东卫视": "shandong-tv.png",
            "四川卫视": "sichuan-tv.png",
        }
    },
    # C源：tv-logo.com（备用源，公开免费）
    "C": {
        "prefix": "https://tv-logo.com/images/",
        "mapping": {
            "CCTV-1": "cctv1-hd.png",
            "CCTV-2": "cctv2-hd.png",
            "CCTV-3": "cctv3-hd.png",
            "CCTV-5": "cctv5-hd.png",
            "湖南卫视": "hunan-hd.png",
            "浙江卫视": "zhejiang-hd.png",
            "江苏卫视": "jiangsu-hd.png",
            "东方卫视": "dongfang-hd.png",
        }
    }
}

# TVG-ID 映射（对齐目标格式）
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
    "CCTV-4K": "cctv4k",
    "CCTV-5＋": "cctv5",
    "湖南卫视": "",
    "浙江卫视": "",
    "江苏卫视": "",
    "东方卫视": "",
    "北京卫视": "",
    "广东卫视": "",
    "深圳卫视": "",
    "山东卫视": "",
    "四川卫视": "",
    "湖南卫视4K": "4k",
    "浙江卫视4K": "4k",
    "江苏卫视4K": "4k",
    "东方卫视4K": "4k",
    "北京卫视4K": "4k",
    "广东卫视4K": "4k",
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
    "SCTV-科教": "sctv",
    "CETV-1": "cetv1",
    "CETV-2": "cetv2",
    "CETV-4": "cetv4",
    "CGTN英语": "cgtn",
    "CGTN西班牙语": "cgtn",
    "CGTN法语": "cgtn",
    "CHC家庭影院": "chc",
    "CHC影迷电影": "chc",
    "CHC动作电影": "chc",
    "i成都": "i",
    "中国体育1": "1",
    "中国体育2": "2",
    "中国体育3": "3",
    "4K视界专区": "4k",
    "4K纪实专区": "4k",
    "4K少儿专区": "4k",
    "四川卫视4K": "4k",
    "深圳卫视4K": "4k",
    "山东卫视4K": "4k",
    "欢笑剧场4K": "4k",
    "亲子趣学4k专区": "4k",
    "4K乐享超清专区": "4k",
    "default": ""
}

# 频道分组配置（对齐目标格式）
GROUP_CONFIG = {
    "央视频道": ["CCTV-"],
    "卫视频道": ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视", "广东卫视"],
    "其他频道": []
}

# ===================== 台标自动降级工具函数 =====================
def get_channel_logo(name):
    """多源台标自动降级+占位图兜底"""
    # 1. 提取频道核心名称（用于匹配）
    core_name = name
    for keyword in ["高清", "4K", "专区", "频道", "卫视"]:
        core_name = core_name.replace(keyword, "").strip()
    # 处理特殊情况
    if "CCTV-5＋" in name:
        core_name = "CCTV-5"
    elif "少儿" in name:
        core_name = "CCTV-14"
    
    # 2. 按A→B→C源顺序尝试匹配
    for source_key in ["A", "B", "C"]:
        source = LOGO_SOURCES[source_key]
        if core_name in source["mapping"]:
            logo_url = f"{source['prefix']}{source['mapping'][core_name]}"
            print(f"台标（{source_key}源）：{name} -> {logo_url}")
            return logo_url
    
    # 3. 无匹配时，使用占位图（对齐目标格式）
    placeholder_text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", name)[:8]
    placeholder_url = f"https://via.placeholder.com/120x80?text={placeholder_text}"
    print(f"台标（占位图）：{name} -> {placeholder_url}")
    return placeholder_url

# ===================== 精准解析函数 =====================
def fetch_dynamic_multicast_data(url):
    try:
        print(f"\n=== 启动无头浏览器解析动态页面 ===")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table//tr")))
        
        page_source = driver.page_source
        full_text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        
        print(f"页面表格行数：{len(rows)}")
        print(f"页面全文本（前1000字符）：\n{full_text[:1000]}")
        
        soup = BeautifulSoup(page_source, "lxml")
        channels = []
        table = soup.find("table")
        
        if not table:
            raise Exception("页面未找到表格元素")
        
        for row_idx, row in enumerate(table.find_all("tr")):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            
            cell_texts = [cell.text.strip() for cell in cells]
            print(f"第{row_idx+1}行单元格内容：{cell_texts}")
            
            chan_name = ""
            udp_url = ""
            for text in cell_texts:
                # 匹配组播地址（兼容两种格式）
                if re.match(r'(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}', text):
                    udp_url = text if text.startswith("udp://") else f"udp://@{text}"
                # 提取频道名（优先包含“高清”“4K”“专区”等关键词的文本）
                elif text and not re.match(r'^\d+$', text) and not udp_url:
                    if any(keyword in text for keyword in ["高清", "4K", "专区", "频道", "卫视", "CCTV"]):
                        chan_name = text
                    elif not chan_name:
                        chan_name = text
            
            if chan_name and udp_url:
                # 过滤画中画
                if not any(kw in chan_name for kw in FILTER_KEYWORDS):
                    channels.append({"name": chan_name, "udp_url": udp_url})
                    print(f"成功解析频道：{chan_name} -> {udp_url}")
        
        if len(channels) == 0:
            multicast_pattern = r'(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}'
            udp_matches = re.findall(multicast_pattern, full_text)
            if udp_matches:
                raise Exception(f"解析到{len(udp_matches)}个组播地址，但未匹配到频道名")
            else:
                raise Exception("页面未解析到任何组播地址")
        
        print(f"\n=== 解析完成，共提取{len(channels)}个有效频道 ===")
        return channels
    
    except Exception as e:
        print(f"\n=== 动态解析失败：{str(e)} ===")
        raise e

# ===================== 其他工具函数 =====================
def get_channel_group(name):
    """匹配分组（对齐目标格式）"""
    for group, prefixes in GROUP_CONFIG.items():
        if any(prefix in name for prefix in prefixes):
            return group
    return "其他频道"

def get_tvg_id(name):
    """获取tvg-id（对齐目标格式）"""
    core_name = name
    for keyword in ["高清", "4K", "专区", "频道", "卫视"]:
        core_name = core_name.replace(keyword, "").strip()
    if "CCTV-5＋" in name:
        core_name = "CCTV-5"
    return TVG_ID_MAPPING.get(core_name, TVG_ID_MAPPING["default"])

def get_tvg_name(name):
    """获取tvg-name（与频道名一致，对齐目标格式）"""
    return name

def parse_udp_url(udp_url):
    """解析UDP地址"""
    try:
        part = udp_url.replace("udp://@", "").split(":")
        if len(part) == 2:
            return {"ip": part[0], "port": part[1]}
        return None
    except:
        return None

def generate_udpxy_url(udp_info, host, port):
    """生成代理地址"""
    if not udp_info:
        return ""
    return f"http://{host}:{port}/udp/{udp_info['ip']}:{udp_info['port']}/"

# ===================== 生成M3U文件（完全对齐目标格式）=====================
def generate_m3u(channels, output_dir):
    print(f"\n=== 生成M3U文件 ===")
    grouped = {}
    for chan in channels:
        group = get_channel_group(chan["name"])
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(chan)
    
    os.makedirs(output_dir, exist_ok=True)
    
    for proxy in UDPXY_PROXIES:
        lines = [
            f"#EXTM3U x-tvg-url=\"{EPG_URL}\"",
            f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 代理地址：{proxy['host']}:{proxy['port']}",
            ""
        ]
        
        for group_name, chans in grouped.items():
            for chan in chans:
                udp_info = parse_udp_url(chan["udp_url"])
                udpxy_url = generate_udpxy_url(udp_info, proxy["host"], proxy["port"])
                if not udpxy_url:
                    print(f"跳过无效UDP：{chan['name']}")
                    continue
                
                # 对齐目标格式的字段顺序和内容
                tvg_id = get_tvg_id(chan["name"])
                tvg_name = get_tvg_name(chan["name"])
                tvg_logo = get_channel_logo(chan["name"])
                group_title = group_name
                
                # 拼接EXTINF行（完全对齐目标格式）
                extinf_line = f"#EXTINF:-1 tvg-id=\"{tvg_id}\" tvg-name=\"{tvg_name}\" tvg-logo=\"{tvg_logo}\" group-title=\"{group_title}\",{tvg_name}"
                lines.append(extinf_line)
                lines.append(udpxy_url)
                lines.append("")
        
        # 按要求命名文件
        filename = f"IPTV_{proxy['suffix']}.m3u"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"已生成：{filepath}")

# ===================== 主函数 =====================
def main():
    output_dir = "./output"
    print(f"=== 初始化完成，输出目录：{os.path.abspath(output_dir)} ===")
    
    try:
        raw_chans = fetch_dynamic_multicast_data(MULTICAST_DATA_URL)
        generate_m3u(raw_chans, output_dir)
        print("\n=== 执行完成：成功解析并生成M3U文件（台标多源自动降级） ===")
    
    except Exception as e:
        print(f"\n=== 执行失败：{str(e)} ===")
        sys.exit(1)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
