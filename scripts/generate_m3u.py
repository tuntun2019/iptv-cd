import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
# Selenium相关导入
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== 核心配置 =====================
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866},
    {"host": "192.168.19.254", "port": 8866}
]
MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "https://epg.112114.xyz/epg.xml"
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]

# 本地兜底数据源
LOCAL_CHANNELS = [
    {"name": "CCTV-1 综合", "udp_url": "udp://@239.136.116.100:8000"},
    {"name": "CCTV-2 财经", "udp_url": "udp://@239.136.116.101:8000"},
    {"name": "CCTV-3 综艺", "udp_url": "udp://@239.136.116.102:8000"},
    {"name": "CCTV-5 体育", "udp_url": "udp://@239.136.116.105:8000"},
    {"name": "湖南卫视", "udp_url": "udp://@239.136.118.101:8000"},
    {"name": "浙江卫视", "udp_url": "udp://@239.136.118.102:8000"},
    {"name": "CCTV-5 体育 画中画", "udp_url": "udp://@239.136.116.120:8000"}
]

# 台标映射
LOGO_MAPPING = {
    "CCTV-1": "https://epg.pw/logos/cctv1.png",
    "CCTV-2": "https://epg.pw/logos/cctv2.png",
    "CCTV-3": "https://epg.pw/logos/cctv3.png",
    "CCTV-5": "https://epg.pw/logos/cctv5.png",
    "湖南卫视": "https://epg.pw/logos/hunan.png",
    "浙江卫视": "https://epg.pw/logos/zhejiang.png",
    "default": "https://via.placeholder.com/120x80?text={}"
}

# 频道分组配置
GROUP_CONFIG = {
    "央视频道": ["CCTV-", "中央"],
    "卫视频道": ["湖南", "浙江", "江苏", "东方", "北京", "广东"],
    "其他频道": []
}

# ===================== 暴力提取函数 =====================
def extract_multicast_data_from_text(full_text):
    """从页面全文本中暴力提取频道和组播地址"""
    channels = []
    # 正则匹配组播地址（兼容多种格式）
    # 匹配：239.xxx.xxx.xxx:xxxx 或 udp://@239.xxx.xxx.xxx:xxxx
    multicast_pattern = r'(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}'
    multicast_matches = re.findall(multicast_pattern, full_text, re.IGNORECASE)
    
    if not multicast_matches:
        return channels
    
    # 常见频道名列表（用于关联地址）
    common_channel_names = [
        "CCTV-1", "CCTV-2", "CCTV-3", "CCTV-4", "CCTV-5", "CCTV-5+",
        "CCTV-6", "CCTV-7", "CCTV-8", "CCTV-9", "CCTV-10", "CCTV-11",
        "CCTV-12", "CCTV-13", "CCTV-14", "CCTV-15",
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视",
        "广东卫视", "山东卫视", "四川卫视", "深圳卫视"
    ]
    
    # 遍历每个组播地址，匹配上下文的频道名
    for match in multicast_matches:
        # 标准化组播地址格式
        udp_url = match if match.startswith("udp://") else f"udp://@{match}"
        # 查找地址前后的频道名
        idx = full_text.find(udp_url.replace("udp://@", ""))
        # 取地址前后50个字符的上下文
        context = full_text[max(0, idx-50):min(len(full_text), idx+50)]
        
        # 匹配上下文里的常见频道名
        chan_name = "未知频道"
        for name in common_channel_names:
            if name in context:
                chan_name = name
                break
        
        # 去重并添加
        if not any(c["udp_url"] == udp_url for c in channels):
            channels.append({"name": chan_name, "udp_url": udp_url})
            print(f"暴力提取到：{chan_name} -> {udp_url}")
    
    return channels

def fetch_dynamic_multicast_data(url):
    """动态解析+暴力提取"""
    try:
        print(f"\n=== 启动无头浏览器解析动态页面 ===")
        # Chrome配置
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        # 适配新版Selenium
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 加载页面
        driver.get(url)
        # 等待页面完全加载（延长等待时间到15秒）
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 获取页面全文本（核心：提取所有文本，而非仅表格）
        full_text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        
        print(f"页面全文本前500字符：\n{full_text[:500]}")
        
        # 第一步：尝试表格解析
        soup = BeautifulSoup(driver.page_source, "lxml")
        table_channels = []
        all_tables = soup.find_all("table")
        print(f"找到{len(all_tables)}个表格，尝试表格解析...")
        
        for table in all_tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                cell_texts = [cell.text.strip() for cell in cells]
                if len(cell_texts) >= 2:
                    table_channels.extend(extract_multicast_data_from_text(" ".join(cell_texts)))
        
        # 第二步：表格解析失败则暴力提取全文本
        if len(table_channels) == 0:
            print("表格解析无数据，尝试暴力提取全文本...")
            table_channels = extract_multicast_data_from_text(full_text)
        
        print(f"=== 动态解析完成，共提取{len(table_channels)}个频道 ===")
        return table_channels
    
    except Exception as e:
        print(f"\n=== 动态解析失败：{str(e)} ===")
        return []

# ===================== 工具函数 =====================
def filter_pip_channels(channels):
    """过滤画中画频道"""
    print(f"\n=== 过滤画中画频道 ===")
    filtered = []
    for chan in channels:
        if not any(kw in chan["name"] for kw in FILTER_KEYWORDS):
            filtered.append(chan)
        else:
            print(f"过滤掉：{chan['name']}")
    print(f"过滤后剩余：{len(filtered)}个频道")
    return filtered

def get_channel_group(name):
    """匹配分组"""
    for group, prefixes in GROUP_CONFIG.items():
        if any(name.startswith(p) for p in prefixes):
            return group
    return "其他频道"

def get_channel_logo(name):
    """获取台标"""
    try:
        for key, url in LOGO_MAPPING.items():
            if key in name and "placeholder" not in url:
                return url
        core_name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", name)[:6]
        return LOGO_MAPPING["default"].format(core_name)
    except:
        return "https://via.placeholder.com/120x80?text=TV"

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

def generate_m3u(channels, output_dir):
    """生成M3U文件"""
    print(f"\n=== 生成M3U文件 ===")
    grouped = {}
    for chan in channels:
        group = get_channel_group(chan["name"])
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(chan)
    
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
                udpxy = generate_udpxy_url(udp_info, proxy["host"], proxy["port"])
                if not udpxy:
                    print(f"跳过无效UDP：{chan['name']}")
                    continue
                
                logo = get_channel_logo(chan["name"])
                epg_id = re.sub(r"[^a-zA-Z0-9]", "", chan["name"]).lower()
                
                lines.append(f"#EXTINF:-1 group-title=\"{group_name}\" tvg-id=\"{epg_id}\" tvg-logo=\"{logo}\",{chan['name']}")
                lines.append(udpxy)
                lines.append("")
        
        # 写入文件
        filename = f"tv_channels_{proxy['host']}_{proxy['port']}.m3u"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"已生成：{filepath}")

# ===================== 主函数 =====================
def main():
    # 确保输出目录存在
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"=== 初始化完成，输出目录：{os.path.abspath(output_dir)} ===")
    
    # 1. 优先尝试动态+暴力提取远程数据
    raw_chans = fetch_dynamic_multicast_data(MULTICAST_DATA_URL)
    
    # 2. 提取失败时，使用本地兜底数据
    if len(raw_chans) == 0:
        print(f"\n=== 远程解析无数据，启用本地兜底 ===")
        raw_chans = LOCAL_CHANNELS
    
    # 3. 过滤画中画频道
    filtered_chans = filter_pip_channels(raw_chans)
    
    # 4. 生成M3U文件
    if filtered_chans:
        generate_m3u(filtered_chans, output_dir)
    else:
        print("无有效频道（兜底数据也为空，不可能发生）")
    
    print("\n=== 执行完成 ===")

if __name__ == "__main__":
    # 禁用不必要的警告
    requests.packages.urllib3.disable_warnings()
    main()
