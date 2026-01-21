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

# EPG 配置（稳定公共EPG源）
EPG_URL = "https://epg.112114.xyz/epg.xml"

# 过滤配置：剔除包含这些关键词的频道（画中画相关）
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]

# 台标映射（改用免费公共台标库，确保可访问）
LOGO_MAPPING = {
    # 优先使用：https://epg.pw 公共台标库（稳定、覆盖广）
    "CCTV-1": "https://epg.pw/logos/cctv1.png",
    "CCTV-2": "https://epg.pw/logos/cctv2.png",
    "CCTV-3": "https://epg.pw/logos/cctv3.png",
    "CCTV-4": "https://epg.pw/logos/cctv4.png",
    "CCTV-5": "https://epg.pw/logos/cctv5.png",
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
    "安徽卫视": "https://epg.pw/logos/anhui.png",
    "广东卫视": "https://epg.pw/logos/guangdong.png",
    "山东卫视": "https://epg.pw/logos/shandong.png",
    "四川卫视": "https://epg.pw/logos/sichuan.png",
    "深圳卫视": "https://epg.pw/logos/shenzhen.png",
    # 备用来源：https://iptv-logo.com （补充覆盖）
    "黑龙江卫视": "https://iptv-logo.com/logos/heilongjiang.png",
    "辽宁卫视": "https://iptv-logo.com/logos/liaoning.png",
    "河南卫视": "https://iptv-logo.com/logos/henan.png",
    # 通用降级方案：使用固定占位台标（避免502）
    "default": "https://via.placeholder.com/120x80?text={}"
}

# 频道分组配置（按频道名前缀分组）
GROUP_CONFIG = {
    "央视频道": ["CCTV-", "中央"],
    "卫视频道": ["湖南", "浙江", "江苏", "东方", "北京", "安徽", "广东", "山东", "四川"],
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
    """从指定URL获取组播数据并解析"""
    try:
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        channels = []
        
        # 适配表格形式
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    channel_name = cols[0].text.strip()
                    udp_url = cols[1].text.strip()
                    if channel_name and udp_url and udp_url.startswith("udp://"):
                        channels.append({"name": channel_name, "udp_url": udp_url})
        
        # 适配纯文本形式
        if not channels:
            lines = response.text.split("\n")
            for line in lines:
                line = line.strip()
                if "udp://" in line:
                    match = re.match(r"(.+?)\s*[\|\s]\s*(udp://.+)", line)
                    if match:
                        channel_name = match.group(1).strip()
                        udp_url = match.group(2).strip()
                        channels.append({"name": channel_name, "udp_url": udp_url})
        
        print(f"原始获取频道数：{len(channels)}")
        return channels
    except Exception as e:
        print(f"获取组播数据失败：{str(e)}")
        return []

def filter_pip_channels(channels):
    """过滤掉画中画频道"""
    filtered = []
    for channel in channels:
        if not any(keyword in channel["name"] for keyword in FILTER_KEYWORDS):
            filtered.append(channel)
    print(f"过滤画中画后频道数：{len(filtered)}")
    return filtered

def get_channel_group(channel_name):
    """根据频道名匹配分组"""
    for group_name, prefixes in GROUP_CONFIG.items():
        if any(channel_name.startswith(prefix) for prefix in prefixes):
            return group_name
    return "其他频道"

def get_channel_logo(channel_name):
    """获取频道台标URL（优化降级逻辑）"""
    try:
        # 1. 精确匹配已知台标
        for name_key, logo_url in LOGO_MAPPING.items():
            if name_key in channel_name and "placeholder" not in logo_url:
                return logo_url
        
        # 2. 通用降级：使用文字占位台标（显示频道名关键词）
        core_name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", channel_name)[:6]
        placeholder_logo = LOGO_MAPPING["default"].format(core_name)
        return placeholder_logo
    except Exception as e:
        # 终极降级：固定占位图
        return "https://via.placeholder.com/120x80?text=TV"

def get_epg_id(channel_name):
    """生成EPG ID（适配通用EPG格式）"""
    epg_id = re.sub(r"[^a-zA-Z0-9]", "", channel_name).lower()
    return epg_id

def parse_udp_url(udp_url):
    """解析UDP地址，提取组播IP和端口"""
    try:
        udp_part = udp_url.replace("udp://@", "").split(":")
        if len(udp_part) == 2:
            return {"ip": udp_part[0], "port": udp_part[1]}
        return None
    except:
        return None

def generate_udpxy_url(udp_info, proxy_host, proxy_port):
    """生成udpxy代理地址"""
    if not udp_info:
        return ""
    return f"http://{proxy_host}:{proxy_port}/udp/{udp_info['ip']}:{udp_info['port']}/"

def generate_m3u(channels, output_dir):
    """生成带代理的M3U文件"""
    grouped_channels = {}
    for channel in channels:
        group = get_channel_group(channel["name"])
        if group not in grouped_channels:
            grouped_channels[group] = []
        grouped_channels[group].append(channel)
    
    for proxy in UDPXY_PROXIES:
        m3u_lines = [
            f"#EXTM3U x-tvg-url=\"{EPG_URL}\"",
            f"# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 代理地址：{proxy['host']}:{proxy['port']}",
            ""
        ]
        
        for group_name, group_channels in grouped_channels.items():
            for channel in group_channels:
                udp_info = parse_udp_url(channel["udp_url"])
                udpxy_url = generate_udpxy_url(udp_info, proxy["host"], proxy["port"])
                if not udpxy_url:
                    print(f"跳过无效UDP地址：{channel['name']} -> {channel['udp_url']}")
                    continue
                
                logo_url = get_channel_logo(channel["name"])
                epg_id = get_epg_id(channel["name"])
                
                m3u_lines.append(f"#EXTINF:-1 group-title=\"{group_name}\" tvg-id=\"{epg_id}\" tvg-logo=\"{logo_url}\",{channel['name']}")
                m3u_lines.append(udpxy_url)
                m3u_lines.append("")
        
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"tv_channels_{proxy['host']}_{proxy['port']}.m3u")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
        
        print(f"已生成M3U文件：{output_file}")

# ===================== 主函数 =====================
def main():
    raw_channels = fetch_multicast_data(MULTICAST_DATA_URL)
    if not raw_channels:
        print("未获取到任何组播数据，终止生成")
        return
    
    filtered_channels = filter_pip_channels(raw_channels)
    if not filtered_channels:
        print("过滤后无有效频道，终止生成")
        return
    
    generate_m3u(filtered_channels, "./output")

if __name__ == "__main__":
    main()
