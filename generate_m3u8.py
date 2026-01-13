import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# ===================== 台标配置（适配GitHub代理） =====================
# GitHub代理地址
GITHUB_PROXY = "https://ghfast.top/"
# 原始台标仓库地址
RAW_LOGO_BASE = "https://github.com/iptv-org/logos/raw/master/logos/"
# 带代理的台标基础地址
BASE_LOGO_URL = GITHUB_PROXY + RAW_LOGO_BASE
# 默认台标（带代理）
DEFAULT_LOGO = GITHUB_PROXY + "https://github.com/iptv-org/logos/raw/master/logos/default.png"

# 特殊频道台标映射（自动适配代理）
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

# ===================== 核心配置项 =====================
# 1. 过滤画中画频道的关键词
FILTER_KEYWORDS = ["画中画", "PIP", "pip", "画中", "中画"]

# 2. udpxy地址与输出文件的映射
UDPXY_CONFIGS = [
    {"udpxy_url": "http://192.168.16.254:8866", "output_file": "iptv.m3u8"},
    {"udpxy_url": "http://192.168.19.254:8866", "output_file": "iptv-t.m3u8"}
]

# 3. 数据源和EPG配置
SOURCE_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "http://epg.51zmt.top:8000/e.xml.gz"

# ===================== 功能函数 =====================
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

def get_channel_logo(channel_name):
    """根据频道名获取带代理的台标URL"""
    # 1. 优先匹配特殊频道映射（拼接代理）
    if channel_name in SPECIAL_LOGO_MAPPING:
        raw_logo_url = SPECIAL_LOGO_MAPPING[channel_name]
        return GITHUB_PROXY + raw_logo_url
    
    # 2. 通用匹配：去除后缀，转小写，拼接代理
    clean_name = channel_name.replace("高清", "").replace("4K", "").replace("＋", "plus").strip()
    if clean_name.startswith("CCTV"):
        logo_name = clean_name.lower()
    else:
        logo_name = clean_name.lower().replace(" ", "-")
    
    # 3. 拼接原始URL + 代理
    raw_logo_url = f"{RAW_LOGO_BASE}{logo_name}.png"
    proxy_logo_url = GITHUB_PROXY + raw_logo_url
    
    # 4. 兜底：返回带代理的默认台标
    return proxy_logo_url

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
    """解析HTML中的组播表格，过滤画中画频道"""
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
        
        logo = get_channel_logo(channel_name)
        tvg_id = channel_name.replace('高清', '').replace('＋', 'plus').replace('-', '').replace('4K', '').lower()
        group = get_channel_group(channel_name)
        
        channels.append({
            'name': channel_name,
            'multicast': multicast_addr,
            'logo': logo,
            'tvg_id': tvg_id,
            'group': group
        })
    
    print(f"✅ 解析完成：共识别 {len(channels) + filtered_count} 个频道，过滤 {filtered_count} 个画中画频道，保留 {len(channels)} 个有效频道")
    return channels

def generate_m3u8(channels, udpxy_url, output_file):
    """生成单个m3u8文件"""
    # M3U8头部（含正确的EPG地址）
    m3u8_header = f"""#EXTM3U x-tvg-url="{EPG_URL}"
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
                print(f"⚠️  跳过无效地址 {multicast}（频道：{name}）")
                continue
            ip, port = multicast_parts
            udpxy_play_url = f"{udpxy_url.rstrip('/')}/udp/{ip}:{port}"
            
            channel_line = f"""#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}",{name}
{udpxy_play_url}
"""
            m3u8_lines.append(channel_line)
    
    # 保存文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(m3u8_lines))
    
    # 统计分组信息
    group_stats = {g:len(c) for g,c in grouped_channels.items()}
    print(f"\n📄 生成文件：{output_file}（udpxy：{udpxy_url}）")
    print(f"📊 分组统计：{group_stats}")
    return output_file

def main():
    """主函数：批量生成多udpxy地址的m3u8文件"""
    try:
        # 1. 获取并解析数据源（只解析一次，复用频道数据）
        print(f"🔍 开始获取数据源：{SOURCE_URL}")
        html_content = get_multicast_html(SOURCE_URL)
        channels = parse_multicast_table(html_content)
        
        if not channels:
            raise ValueError("❌ 未解析到任何有效频道数据")
        
        # 2. 循环生成每个udpxy对应的文件
        print("\n🚀 开始生成m3u8文件：")
        print(f"🖼️  台标代理地址：{GITHUB_PROXY}")
        generated_files = []
        for config in UDPXY_CONFIGS:
            udpxy_url = config["udpxy_url"]
            output_file = config["output_file"]
            generated_file = generate_m3u8(channels, udpxy_url, output_file)
            generated_files.append(generated_file)
        
        # 3. 输出最终结果
        print(f"\n🎉 所有文件生成完成！")
        print(f"📁 生成的文件列表：")
        for file in generated_files:
            print(f"  - {file}")
        print(f"📡 EPG源地址：{EPG_URL}")
        print(f"🖼️  台标源：iptv-org公开库（代理：{GITHUB_PROXY}）")
    
    except Exception as e:
        print(f"\n❌ 程序执行失败：{str(e)}")
        # 生成错误兜底文件
        for config in UDPXY_CONFIGS:
            with open(config["output_file"], "w", encoding="utf-8") as f:
                f.write(f"#EXTM3U\n# 生成失败：{str(e)}\n")
        raise

if __name__ == "__main__":
    main()
