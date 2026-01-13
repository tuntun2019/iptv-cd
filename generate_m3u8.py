import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# ===================== 关键变更：更换为iptv-org公开台标源 =====================
# 台标源说明：https://github.com/iptv-org/logos （稳定公开，支持大部分主流频道）
# 匹配规则：频道名去后缀→转小写→拼接URL，匹配不到用默认台标
BASE_LOGO_URL = "https://github.com/iptv-org/logos/raw/master/logos/"
DEFAULT_LOGO = "https://github.com/iptv-org/logos/raw/master/logos/default.png"

# 特殊频道台标映射（iptv-org命名与我们的频道名不一致的情况）
SPECIAL_LOGO_MAPPING = {
    "CCTV-少儿": f"{BASE_LOGO_URL}cctv-14.png",
    "CCTV-17": f"{BASE_LOGO_URL}cctv-17.png",
    "CCTV-5＋": f"{BASE_LOGO_URL}cctv-5plus.png",
    "CGTN英语": f"{BASE_LOGO_URL}cgtn.png",
    "四川卫视": f"{BASE_LOGO_URL}sichuan.png",
    "湖南卫视": f"{BASE_LOGO_URL}hunan.png",
    "江苏卫视": f"{BASE_LOGO_URL}jiangsu.png",
    "浙江卫视": f"{BASE_LOGO_URL}zhejiang.png",
    "东方卫视": f"{BASE_LOGO_URL}dragon-tv.png",
    "北京卫视": f"{BASE_LOGO_URL}beijing.png",
    "广东卫视": f"{BASE_LOGO_URL}guangdong.png",
    "深圳卫视": f"{BASE_LOGO_URL}shenzhen.png",
    "天津卫视": f"{BASE_LOGO_URL}tianjin.png",
    "山东卫视": f"{BASE_LOGO_URL}shandong.png",
    "安徽卫视": f"{BASE_LOGO_URL}anhui.png",
    "辽宁卫视": f"{BASE_LOGO_URL}liaoning.png",
    "黑龙江卫视": f"{BASE_LOGO_URL}heilongjiang.png",
    "吉林卫视": f"{BASE_LOGO_URL}jilin.png",
    "河南卫视": f"{BASE_LOGO_URL}henan.png",
    "湖北卫视": f"{BASE_LOGO_URL}hubei.png",
    "江西卫视": f"{BASE_LOGO_URL}jiangxi.png",
    "广西卫视": f"{BASE_LOGO_URL}guangxi.png",
    "云南卫视": f"{BASE_LOGO_URL}yunnan.png",
    "贵州卫视": f"{BASE_LOGO_URL}guizhou.png",
    "山西卫视": f"{BASE_LOGO_URL}shanxi.png",
    "陕西卫视": f"{BASE_LOGO_URL}shaanxi.png",
    "青海卫视": f"{BASE_LOGO_URL}qinghai.png",
    "宁夏卫视": f"{BASE_LOGO_URL}ningxia.png",
    "内蒙古卫视": f"{BASE_LOGO_URL}neimenggu.png",
    "西藏卫视": f"{BASE_LOGO_URL}tibet.png",
    "新疆卫视": f"{BASE_LOGO_URL}xinjiang.png",
    "甘肃卫视": f"{BASE_LOGO_URL}gansu.png",
    "海南卫视": f"{BASE_LOGO_URL}hainan.png",
    "兵团卫视": f"{BASE_LOGO_URL}bingtuan.png",
    "东南卫视": f"{BASE_LOGO_URL}fujian.png",
    "延边卫视": f"{BASE_LOGO_URL}yanbian.png",
    "康巴卫视": f"{BASE_LOGO_URL}kangba.png",
    "CDTV-1": f"{BASE_LOGO_URL}chengdu.png"
}

# 过滤关键词：包含这些关键词的频道会被移除（画中画相关）
FILTER_KEYWORDS = ["画中画", "PIP", "pip", "画中", "中画"]

# 分组规则
def get_channel_group(channel_name):
    """根据频道名称判断所属分组"""
    if channel_name.startswith("CCTV") or channel_name.startswith("CGTN"):
        return "央视"
    elif any(prefix in channel_name for prefix in ["SCTV", "CDTV", "康巴卫视", "峨眉电影", "四川乡村"]):
        return "地方台-四川"
    elif any(suffix in channel_name for suffix in ["卫视", "湖南卫视", "江苏卫视", "浙江卫视"]):
        return "省级卫视"
    elif "4K" in channel_name or "专区" in channel_name:
        return "4K专区"
    else:
        return "其他频道"

# 新增：台标匹配核心函数（适配iptv-org源）
def get_channel_logo(channel_name):
    """根据频道名获取台标URL"""
    # 1. 优先匹配特殊频道映射
    if channel_name in SPECIAL_LOGO_MAPPING:
        return SPECIAL_LOGO_MAPPING[channel_name]
    
    # 2. 通用匹配：去除"高清""4K""＋"等后缀，转小写
    clean_name = channel_name.replace("高清", "").replace("4K", "").replace("＋", "plus").strip()
    # 处理CCTV系列（如CCTV-1 → cctv-1.png）
    if clean_name.startswith("CCTV"):
        logo_name = clean_name.lower()
    # 处理其他频道（如SCTV-2 → sctv-2.png）
    else:
        logo_name = clean_name.lower().replace(" ", "-")
    
    # 3. 拼接台标URL
    logo_url = f"{BASE_LOGO_URL}{logo_name}.png"
    # 4. 兜底：返回默认台标
    return logo_url

def get_multicast_html(url):
    """获取组播源的HTML页面"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, verify=False, timeout=30, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"获取HTML页面失败: {e}")
        raise

def parse_multicast_table(html_content):
    """解析HTML中的组播表格，过滤画中画频道，匹配台标"""
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    if not table:
        raise ValueError("未找到频道表格")
    
    channels = []
    filtered_count = 0
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        channel_name = cells[1].text.strip()
        multicast_addr = cells[2].text.strip()
        
        # 过滤画中画频道
        if any(keyword in channel_name for keyword in FILTER_KEYWORDS):
            filtered_count += 1
            continue
        
        if not channel_name or not multicast_addr:
            continue
        
        # 获取台标（核心变更：调用新的台标匹配函数）
        logo = get_channel_logo(channel_name)
        # 生成tvg-id
        tvg_id = channel_name.replace('高清', '').replace('＋', 'plus').replace('-', '').replace('4K', '').lower()
        # 获取分组
        group = get_channel_group(channel_name)
        
        channels.append({
            'name': channel_name,
            'multicast': multicast_addr,
            'logo': logo,
            'tvg_id': tvg_id,
            'group': group
        })
    
    print(f"成功解析到 {len(channels)} 个频道（过滤了 {filtered_count} 个画中画频道）")
    return channels

def generate_m3u8(channels, udpxy_proxy):
    """生成带分组、台标、EPG的m3u8内容"""
    m3u8_header = """#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml.gz"
"""
    m3u8_lines = [m3u8_header]

    # 按分组归类频道
    grouped_channels = {}
    for channel in channels:
        group = channel['group']
        grouped_channels[group] = grouped_channels.get(group, []) + [channel]
    
    # 分组显示顺序
    group_order = ["央视", "省级卫视", "地方台-四川", "4K专区", "其他频道"]
    for group in grouped_channels.keys():
        if group not in group_order:
            group_order.append(group)
    
    # 生成m3u8内容
    for group in group_order:
        if group not in grouped_channels:
            continue
        m3u8_lines.append(f"#EXTGRP:{group}")
        m3u8_lines.append("")
        for channel in grouped_channels[group]:
            name = channel['name']
            multicast = channel['multicast']
            logo = channel['logo']
            tvg_id = channel['tvg_id']
            
            multicast_parts = multicast.split(":")
            if len(multicast_parts) != 2:
                continue
            ip, port = multicast_parts
            udpxy_url = f"{udpxy_proxy.rstrip('/')}/udp/{ip}:{port}"
            
            channel_line = f"""#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}",{name}
{udpxy_url}
"""
            m3u8_lines.append(channel_line)
    
    return "".join(m3u8_lines)

def main():
    udpxy_proxy = os.getenv("UDPXY_PROXY", "http://192.168.16.254:8866")
    source_url = "https://epg.51zmt.top:8001/multicast/"
    output_file = "iptv.m3u8"

    try:
        print(f"开始请求组播数据源: {source_url}")
        html_content = get_multicast_html(source_url)
        channels = parse_multicast_table(html_content)
        
        if not channels:
            raise ValueError("未解析到任何频道数据")
        
        m3u8_content = generate_m3u8(channels, udpxy_proxy)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u8_content)
        
        print(f"\n✅ m3u8文件生成完成")
        print(f"📄 文件路径：{output_file}")
        print(f"🔌 udpxy代理：{udpxy_proxy}")
        print(f"📡 EPG源：http://epg.51zmt.top:8000/e.xml.gz")
        print(f"🖼️  台标源：iptv-org公开库（稳定可用）")
        print(f"\n📊 分组统计：")
        group_stats = {g:len(c) for g,c in grouped_channels.items()}
        for g,c in group_stats.items():
            print(f"  - {g}: {c} 个频道")
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# 数据获取失败，请检查数据源地址或网络\n")
        raise

if __name__ == "__main__":
    main()
