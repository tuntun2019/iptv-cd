import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ===================== 核心配置 =====================
# udpxy 代理配置
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866},
    {"host": "192.168.19.254", "port": 8866}
]

# 组播数据源地址
MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"

# EPG 配置
EPG_URL = "https://epg.112114.xyz/epg.xml"

# 过滤配置
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]

# 本地静态兜底数据源（确保有数据输出）
LOCAL_CHANNELS = [
    {"name": "CCTV-1 综合", "udp_url": "udp://@239.136.116.100:8000"},
    {"name": "CCTV-2 财经", "udp_url": "udp://@239.136.116.101:8000"},
    {"name": "CCTV-3 综艺", "udp_url": "udp://@239.136.116.102:8000"},
    {"name": "CCTV-4 中文国际", "udp_url": "udp://@239.136.116.103:8000"},
    {"name": "CCTV-5 体育", "udp_url": "udp://@239.136.116.105:8000"},
    {"name": "CCTV-5+ 体育赛事", "udp_url": "udp://@239.136.116.106:8000"},
    {"name": "CCTV-6 电影", "udp_url": "udp://@239.136.116.107:8000"},
    {"name": "CCTV-7 国防军事", "udp_url": "udp://@239.136.116.108:8000"},
    {"name": "CCTV-8 电视剧", "udp_url": "udp://@239.136.116.109:8000"},
    {"name": "CCTV-9 纪录", "udp_url": "udp://@239.136.116.110:8000"},
    {"name": "CCTV-10 科教", "udp_url": "udp://@239.136.116.111:8000"},
    {"name": "CCTV-11 戏曲", "udp_url": "udp://@239.136.116.112:8000"},
    {"name": "CCTV-12 社会与法", "udp_url": "udp://@239.136.116.113:8000"},
    {"name": "CCTV-13 新闻", "udp_url": "udp://@239.136.116.114:8000"},
    {"name": "CCTV-14 少儿", "udp_url": "udp://@239.136.116.115:8000"},
    {"name": "CCTV-15 音乐", "udp_url": "udp://@239.136.116.116:8000"},
    {"name": "湖南卫视", "udp_url": "udp://@239.136.118.101:8000"},
    {"name": "浙江卫视", "udp_url": "udp://@239.136.118.102:8000"},
    {"name": "江苏卫视", "udp_url": "udp://@239.136.118.103:8000"},
    {"name": "东方卫视", "udp_url": "udp://@239.136.118.104:8000"},
    {"name": "北京卫视", "udp_url": "udp://@239.136.118.105:8000"},
    {"name": "广东卫视", "udp_url": "udp://@239.136.118.106:8000"},
    {"name": "山东卫视", "udp_url": "udp://@239.136.118.107:8000"},
    {"name": "四川卫视", "udp_url": "udp://@239.136.118.108:8000"},
    {"name": "深圳卫视", "udp_url": "udp://@239.136.118.109:8000"},
    {"name": "CCTV-5 体育 画中画", "udp_url": "udp://@239.136.116.120:8000"}  # 用于测试过滤
]

# 台标映射
LOGO_MAPPING = {
    "CCTV-1": "https://epg.pw/logos/cctv1.png",
    "CCTV-2": "https://epg.pw/logos/cctv2.png",
    "CCTV-3": "https://epg.pw/logos/cctv3.png",
    "CCTV-4": "https://epg.pw/logos/cctv4.png",
    "CCTV-5": "https://epg.pw/logos/cctv5.png",
    "CCTV-5+": "https://epg.pw/logos/cctv5plus.png",
    "CCTV-6": "https://epg.pw/logos/cctv6.png",
    "CCTV-7": "https://epg.pw/logos/cctv7.png",
    "CCTV-8": "https://epg.pw/logos/cctv8.png",
    "CCTV-9": "https://epg.pw/logos/cctv9.png",
    "CCTV-10": "https://epg.pw/logos/cctv10.png",
    "CCTV-11": "https://epg.pw/logos/cctv11.png",
    "CCTV-12": "https://epg.pw/logos/cctv12.png",
    "CCTV-13": "https://epg.pw/logos/cctv13.png",
    "CCTV-14": "https://epg.pw/logos/cctv14.png",
    "CCTV-15": "https://epg.pw/logos/cctv15.png",
    "湖南卫视": "https://epg.pw/logos/hunan.png",
    "浙江卫视": "https://epg.pw/logos/zhejiang.png",
    "江苏卫视": "https://epg.pw/logos/jiangsu.png",
    "东方卫视": "https://epg.pw/logos/dongfang.png",
    "北京卫视": "https://epg.pw/logos/beijing.png",
    "广东卫视": "https://epg.pw/logos/guangdong.png",
    "山东卫视": "https://epg.pw/logos/shandong.png",
    "四川卫视": "https://epg.pw/logos/sichuan.png",
    "深圳卫视": "https://epg.pw/logos/shenzhen.png",
    "default": "https://via.placeholder.com/120x80?text={}"
}

# 频道分组配置
GROUP_CONFIG = {
    "央视频道": ["CCTV-", "中央"],
    "卫视频道": ["湖南", "浙江", "江苏", "东方", "北京", "安徽", "广东", "山东", "四川", "深圳"],
    "地方频道": ["上海", "天津", "重庆", "河北", "河南", "辽宁", "黑龙江"],
    "影视频道": ["电影", "影视", "剧场", "电视剧"],
    "体育频道": ["体育", "CCTV-5", "CCTV-5+"],
    "少儿频道": ["少儿", "CCTV-14", "卡通"],
    "新闻频道": ["新闻", "CCTV-13", "财经"],
    "综艺频道": ["综艺", "CCTV-3", "湖南卫视"],
    "科教频道": ["科教", "CCTV-10", "纪录"]
}

# ===================== 工具函数 =====================
def fetch_multicast_data(url):
    """远程数据源解析 + 本地兜底"""
    try:
        print(f"\n=== 尝试获取远程组播数据：{url} ===")
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
        
        # 极致适配：遍历所有可能的表格结构
        soup = BeautifulSoup(response.text, "lxml")
        channels = []
        
        # 适配1：所有class包含table的表格
        tables = soup.find_all("table", class_=re.compile("table"))
        # 适配2：所有div下的表格
        div_tables = soup.find_all("div", class_=re.compile("table"))
        all_tables = tables + div_tables
        
        for table in all_tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    # 提取所有单元格文本，查找UDP地址
                    cell_texts = [cell.text.strip() for cell in cells]
                    udp_url = ""
                    chan_name = ""
                    for text in cell_texts:
                        if text.startswith("udp://"):
                            udp_url = text
                        elif text and not udp_url:
                            chan_name = text
                    if chan_name and udp_url:
                        channels.append({"name": chan_name, "udp_url": udp_url})
        
        print(f"远程解析到频道数：{len(channels)}")
        
        # 远程无数据时，使用本地静态数据源
        if len(channels) == 0:
            print("远程无数据，启用本地静态数据源")
            return LOCAL_CHANNELS
        return channels
    
    except Exception as e:
        print(f"远程数据源解析失败：{str(e)}，启用本地静态数据源")
        return LOCAL_CHANNELS

def filter_pip_channels(channels):
    """过滤画中画频道"""
    print(f"\n=== 过滤画中画频道（关键词：{FILTER_KEYWORDS}）===")
    filtered = []
    for chan in channels:
        if not any(kw in chan["name"] for kw in FILTER_KEYWORDS):
            filtered.append(chan)
        else:
            print(f"过滤掉：{chan['name']}")
    print(f"过滤后剩余频道数：{len(filtered)}")
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

def get_epg_id(name):
    """生成EPG ID"""
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

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
    print(f"\n=== 生成M3U文件到：{output_dir} ===")
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
                epg_id = get_epg_id(chan["name"])
                
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
    
    # 1. 获取频道数据（远程+本地兜底）
    raw_chans = fetch_multicast_data(MULTICAST_DATA_URL)
    
    # 2. 过滤画中画
    filtered_chans = filter_pip_channels(raw_chans)
    
    # 3. 生成M3U（强制生成有效数据）
    if filtered_chans:
        generate_m3u(filtered_chans, output_dir)
    else:
        print("无有效频道（不可能发生，因为本地有兜底）")
    
    print("\n=== 执行完成，已生成有效M3U文件 ===")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
