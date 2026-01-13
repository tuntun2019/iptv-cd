import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# ===================== 基础配置 =====================
# 1. GitHub代理（台标用）
GITHUB_PROXY = "https://ghfast.top/"
RAW_LOGO_BASE = "https://github.com/iptv-org/logos/raw/master/logos/"
DEFAULT_LOGO = GITHUB_PROXY + "https://github.com/iptv-org/logos/raw/master/logos/default.png"

# 2. 回放配置（核心新增）
# 回放服务器基础地址（可根据实际回放服务器调整，以下为通用格式示例）
PLAYBACK_BASE_URL = "http://epg.51zmt.top:8002/playback"  # 替换为实际回放服务器地址
# 回放频道名称后缀（区分直播/回放）
PLAYBACK_NAME_SUFFIX = "【回放】"

# 3. 过滤画中画关键词
FILTER_KEYWORDS = ["画中画", "PIP", "pip", "画中", "中画"]

# 4. 直播udpxy配置（原有）
UDPXY_CONFIGS = [
    {"udpxy_url": "http://192.168.16.254:8866", "output_file": "iptv.m3u8"},
    {"udpxy_url": "http://192.168.19.254:8866", "output_file": "iptv-t.m3u8"}
]

# 5. 数据源和EPG配置
SOURCE_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "http://epg.51zmt.top:8000/e.xml.gz"

# ===================== 特殊台标映射 =====================
SPECIAL_LOGO_MAPPING = {
    "CCTV-少儿": f"{RAW_LOGO_BASE}cctv-14.png",
    "CCTV-17": f"{RAW_LOGO_BASE}cctv-17.png",
    "CCTV-5＋": f"{RAW_LOGO_BASE}cctv-5plus.png",
    "CGTN英语": f"{RAW_LOGO_BASE}cgtn.png",
    "四川卫视": f"{RAW_LOGO_BASE}sichuan.png",
    "湖南卫视": f"{RAW_LOGO_BASE}hunan.png",
    "江苏卫视": f"{RAW_LOGO_BASE}jiangsu.png",
    "浙江卫视": f"{RAW_LOGO_BASE}zhejiang.png",
    "东方卫视": f"{RAW_LOGO_BASE}dragon-tv.png",
    "北京卫视": f"{RAW_LOGO_BASE}beijing.png",
    "广东卫视": f"{RAW_LOGO_BASE}guangdong.png",
    "深圳卫视": f"{RAW_LOGO_BASE}shenzhen.png",
    "天津卫视": f"{RAW_LOGO_BASE}tianjin.png",
    "山东卫视": f"{RAW_LOGO_BASE}shandong.png",
    "安徽卫视": f"{RAW_LOGO_BASE}anhui.png",
    "辽宁卫视": f"{RAW_LOGO_BASE}liaoning.png",
    "黑龙江卫视": f"{RAW_LOGO_BASE}heilongjiang.png",
    "吉林卫视": f"{RAW_LOGO_BASE}jilin.png",
    "河南卫视": f"{RAW_LOGO_BASE}henan.png",
    "湖北卫视": f"{RAW_LOGO_BASE}hubei.png",
    "江西卫视": f"{RAW_LOGO_BASE}jiangxi.png",
    "广西卫视": f"{RAW_LOGO_BASE}guangxi.png",
    "云南卫视": f"{RAW_LOGO_BASE}yunnan.png",
    "贵州卫视": f"{RAW_LOGO_BASE}guizhou.png",
    "山西卫视": f"{RAW_LOGO_BASE}shanxi.png",
    "陕西卫视": f"{RAW_LOGO_BASE}shaanxi.png",
    "青海卫视": f"{RAW_LOGO_BASE}qinghai.png",
    "宁夏卫视": f"{RAW_LOGO_BASE}ningxia.png",
    "内蒙古卫视": f"{RAW_LOGO_BASE}neimenggu.png",
    "西藏卫视": f"{RAW_LOGO_BASE}tibet.png",
    "新疆卫视": f"{RAW_LOGO_BASE}xinjiang.png",
    "甘肃卫视": f"{RAW_LOGO_BASE}gansu.png",
    "海南卫视": f"{RAW_LOGO_BASE}hainan.png",
    "兵团卫视": f"{RAW_LOGO_BASE}bingtuan.png",
    "东南卫视": f"{RAW_LOGO_BASE}fujian.png",
    "延边卫视": f"{RAW_LOGO_BASE}yanbian.png",
    "康巴卫视": f"{RAW_LOGO_BASE}kangba.png",
    "CDTV-1": f"{RAW_LOGO_BASE}chengdu.png"
}

# ===================== 功能函数 =====================
def get_channel_group(channel_name):
    """频道分组逻辑"""
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

def get_channel_logo(channel_name):
    """获取带代理的台标URL"""
    if channel_name in SPECIAL_LOGO_MAPPING:
        raw_logo_url = SPECIAL_LOGO_MAPPING[channel_name]
        return GITHUB_PROXY + raw_logo_url
    
    clean_name = channel_name.replace("高清", "").replace("4K", "").replace("＋", "plus").strip()
    if clean_name.startswith("CCTV"):
        logo_name = clean_name.lower()
    else:
        logo_name = clean_name.lower().replace(" ", "-")
    
    raw_logo_url = f"{RAW_LOGO_BASE}{logo_name}.png"
    return GITHUB_PROXY + raw_logo_url

def generate_playback_url(multicast_ip, multicast_port):
    """生成回放地址（核心新增）"""
    # 通用回放URL格式：回放服务器 + 组播IP + 端口（可根据实际规则调整）
    # 示例1：http://回放服务器/playback?ip=239.94.0.31&port=5140
    # 示例2：http://回放服务器/239.94.0.31:5140/playback
    encoded_ip = quote(multicast_ip)
    encoded_port = quote(multicast_port)
    playback_url = f"{PLAYBACK_BASE_URL}?ip={encoded_ip}&port={encoded_port}"
    return playback_url

def parse_multicast_table(html_content):
    """解析数据源，过滤画中画频道"""
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
        
        # 解析组播IP和端口
        multicast_parts = multicast_addr.split(":")
        if len(multicast_parts) != 2:
            print(f"⚠️  跳过无效组播地址 {multicast_addr}（频道：{channel_name}）")
            continue
        multicast_ip, multicast_port = multicast_parts
        
        # 基础数据
        logo = get_channel_logo(channel_name)
        tvg_id = channel_name.replace('高清', '').replace('＋', 'plus').replace('-', '').replace('4K', '').lower()
        group = get_channel_group(channel_name)
        
        channels.append({
            'name': channel_name,
            'multicast_ip': multicast_ip,
            'multicast_port': multicast_port,
            'logo': logo,
            'tvg_id': tvg_id,
            'group': group
        })
    
    print(f"✅ 解析完成：共识别 {len(channels) + filtered_count} 个频道，过滤 {filtered_count} 个画中画频道，保留 {len(channels)} 个有效频道")
    return channels

def generate_live_m3u8(channels, udpxy_url, output_file):
    """生成直播m3u8（原有逻辑，优化格式）"""
    m3u8_header = f"""#EXTM3U x-tvg-url="{EPG_URL}"
"""
    m3u8_lines = [m3u8_header]

    # 分组归类
    grouped_channels = {}
    for channel in channels:
        group = channel['group']
        if group not in grouped_channels:
            grouped_channels[group] = []
        grouped_channels[group].append(channel)
    
    # 分组顺序
    group_order = ["央视", "省级卫视", "地方台-四川", "4K专区", "其他频道"]
    for group in grouped_channels.keys():
        if group not in group_order:
            group_order.append(group)
    
    # 生成内容
    for group in group_order:
        if group not in grouped_channels or len(grouped_channels[group]) == 0:
            continue
        m3u8_lines.append(f"#EXTGRP:{group}")
        for channel in grouped_channels[group]:
            name = channel['name']
            ip = channel['multicast_ip']
            port = channel['multicast_port']
            logo = channel['logo']
            tvg_id = channel['tvg_id']
            
            udpxy_play_url = f"{udpxy_url.rstrip('/')}/udp/{ip}:{port}"
            channel_line = f"#EXTINF:-1 tvg-id=\"{tvg_id}\" tvg-logo=\"{logo}\",{name}\n{udpxy_play_url}"
            m3u8_lines.append(channel_line)
        m3u8_lines.append("")
    
    # 保存文件
    final_content = "\n".join(m3u8_lines)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    group_stats = {g:len(c) for g,c in grouped_channels.items()}
    print(f"\n📄 生成直播文件：{output_file}（udpxy：{udpxy_url}）")
    print(f"📊 分组统计：{group_stats}")
    return output_file

def generate_playback_m3u8(channels, output_file="iptv-playback.m3u8"):
    """生成回放m3u8（核心新增）"""
    m3u8_header = f"""#EXTM3U x-tvg-url="{EPG_URL}"
"""
    m3u8_lines = [m3u8_header]

    # 分组归类（回放分组在原有基础上加“回放”标识）
    grouped_channels = {}
    for channel in channels:
        group = f"{channel['group']}-回放"  # 分组名加“回放”，区分直播
        if group not in grouped_channels:
            grouped_channels[group] = []
        grouped_channels[group].append(channel)
    
    # 分组顺序
    group_order = ["央视-回放", "省级卫视-回放", "地方台-四川-回放", "4K专区-回放", "其他频道-回放"]
    for group in grouped_channels.keys():
        if group not in group_order:
            group_order.append(group)
    
    # 生成回放内容
    for group in group_order:
        if group not in grouped_channels or len(grouped_channels[group]) == 0:
            continue
        m3u8_lines.append(f"#EXTGRP:{group}")
        for channel in grouped_channels[group]:
            # 频道名加回放后缀
            name = f"{channel['name']}{PLAYBACK_NAME_SUFFIX}"
            ip = channel['multicast_ip']
            port = channel['multicast_port']
            logo = channel['logo']
            tvg_id = f"{channel['tvg_id']}_playback"  # tvg-id加后缀，避免冲突
            
            # 生成回放地址
            playback_url = generate_playback_url(ip, port)
            channel_line = f"#EXTINF:-1 tvg-id=\"{tvg_id}\" tvg-logo=\"{logo}\",{name}\n{playback_url}"
            m3u8_lines.append(channel_line)
        m3u8_lines.append("")
    
    # 保存回放文件
    final_content = "\n".join(m3u8_lines)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    group_stats = {g:len(c) for g,c in grouped_channels.items()}
    print(f"\n📄 生成回放文件：{output_file}")
    print(f"📊 回放分组统计：{group_stats}")
    print(f"🔗 回放服务器地址：{PLAYBACK_BASE_URL}")
    return output_file

def main():
    """主函数：生成直播+回放m3u8"""
    try:
        # 1. 获取并解析数据源
        print(f"🔍 开始获取数据源：{SOURCE_URL}")
        html_content = requests.get(SOURCE_URL, verify=False, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }).text
        html_content = html_content.encode('utf-8').decode('utf-8')  # 编码兼容
        channels = parse_multicast_table(html_content)
        
        if not channels:
            raise ValueError("❌ 未解析到任何有效频道数据")
        
        # 2. 生成直播m3u8（原有功能）
        print("\n🚀 开始生成直播m3u8文件：")
        print(f"🖼️  台标代理地址：{GITHUB_PROXY}")
        generated_live_files = []
        for config in UDPXY_CONFIGS:
            udpxy_url = config["udpxy_url"]
            output_file = config["output_file"]
            generated_file = generate_live_m3u8(channels, udpxy_url, output_file)
            generated_live_files.append(generated_file)
        
        # 3. 生成回放m3u8（核心新增）
        print("\n🎬 开始生成回放m3u8文件：")
        generated_playback_file = generate_playback_m3u8(channels)
        
        # 4. 输出最终结果
        print(f"\n🎉 所有文件生成完成！")
        print(f"📁 生成的文件列表：")
        for file in generated_live_files:
            print(f"  - 直播：{file}")
        print(f"  - 回放：{generated_playback_file}")
        print(f"📡 EPG源地址：{EPG_URL}")
        print(f"🖼️  台标源：iptv-org公开库（代理：{GITHUB_PROXY}）")
        print(f"🔗 回放服务器：{PLAYBACK_BASE_URL}")
    
    except Exception as e:
        print(f"\n❌ 程序执行失败：{str(e)}")
        # 生成兜底文件
        for config in UDPXY_CONFIGS:
            with open(config["output_file"], "w", encoding="utf-8") as f:
                f.write(f"#EXTM3U\n# 生成失败：{str(e)}\n")
        with open("iptv-playback.m3u8", "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n# 回放文件生成失败：{str(e)}\n")
        raise

if __name__ == "__main__":
    main()
