import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# 配置：扩展版台标映射（覆盖更多频道）
LOGO_MAPPING = {
    # CCTV系列
    "CCTV-1": "https://epg.51zmt.top:8001/logos/cctv1.png",
    "CCTV-1高清": "https://epg.51zmt.top:8001/logos/cctv1.png",
    "CCTV-2": "https://epg.51zmt.top:8001/logos/cctv2.png",
    "CCTV-2高清": "https://epg.51zmt.top:8001/logos/cctv2.png",
    "CCTV-3": "https://epg.51zmt.top:8001/logos/cctv3.png",
    "CCTV-3高清": "https://epg.51zmt.top:8001/logos/cctv3.png",
    "CCTV-4": "https://epg.51zmt.top:8001/logos/cctv4.png",
    "CCTV-4高清": "https://epg.51zmt.top:8001/logos/cctv4.png",
    "CCTV-5": "https://epg.51zmt.top:8001/logos/cctv5.png",
    "CCTV-5高清": "https://epg.51zmt.top:8001/logos/cctv5.png",
    "CCTV-5＋": "https://epg.51zmt.top:8001/logos/cctv5plus.png",
    "CCTV-5＋高清": "https://epg.51zmt.top:8001/logos/cctv5plus.png",
    "CCTV-6": "https://epg.51zmt.top:8001/logos/cctv6.png",
    "CCTV-6高清": "https://epg.51zmt.top:8001/logos/cctv6.png",
    "CCTV-7": "https://epg.51zmt.top:8001/logos/cctv7.png",
    "CCTV-7高清": "https://epg.51zmt.top:8001/logos/cctv7.png",
    "CCTV-8": "https://epg.51zmt.top:8001/logos/cctv8.png",
    "CCTV-8高清": "https://epg.51zmt.top:8001/logos/cctv8.png",
    "CCTV-9": "https://epg.51zmt.top:8001/logos/cctv9.png",
    "CCTV-9高清": "https://epg.51zmt.top:8001/logos/cctv9.png",
    "CCTV-10": "https://epg.51zmt.top:8001/logos/cctv10.png",
    "CCTV-10高清": "https://epg.51zmt.top:8001/logos/cctv10.png",
    "CCTV-11": "https://epg.51zmt.top:8001/logos/cctv11.png",
    "CCTV-11高清": "https://epg.51zmt.top:8001/logos/cctv11.png",
    "CCTV-12": "https://epg.51zmt.top:8001/logos/cctv12.png",
    "CCTV-12高清": "https://epg.51zmt.top:8001/logos/cctv12.png",
    "CCTV-13": "https://epg.51zmt.top:8001/logos/cctv13.png",
    "CCTV-13高清": "https://epg.51zmt.top:8001/logos/cctv13.png",
    "CCTV-少儿": "https://epg.51zmt.top:8001/logos/cctv14.png",
    "CCTV-少儿高清": "https://epg.51zmt.top:8001/logos/cctv14.png",
    "CCTV-15": "https://epg.51zmt.top:8001/logos/cctv15.png",
    "CCTV-15高清": "https://epg.51zmt.top:8001/logos/cctv15.png",
    "CCTV-17": "https://epg.51zmt.top:8001/logos/cctv17.png",
    "CCTV-17高清": "https://epg.51zmt.top:8001/logos/cctv17.png",
    "CCTV-4K": "https://epg.51zmt.top:8001/logos/cctv4k.png",
    
    # 省级卫视
    "四川卫视": "https://epg.51zmt.top:8001/logos/sctv1.png",
    "四川卫视高清": "https://epg.51zmt.top:8001/logos/sctv1.png",
    "四川卫视4K": "https://epg.51zmt.top:8001/logos/sctv4k.png",
    "湖南卫视": "https://epg.51zmt.top:8001/logos/hntv.png",
    "湖南卫视高清": "https://epg.51zmt.top:8001/logos/hntv.png",
    "湖南卫视4K": "https://epg.51zmt.top:8001/logos/hntv4k.png",
    "江苏卫视": "https://epg.51zmt.top:8001/logos/jstv.png",
    "江苏卫视高清": "https://epg.51zmt.top:8001/logos/jstv.png",
    "江苏卫视4K": "https://epg.51zmt.top:8001/logos/jstv4k.png",
    "浙江卫视": "https://epg.51zmt.top:8001/logos/zjstv.png",
    "浙江卫视高清": "https://epg.51zmt.top:8001/logos/zjstv.png",
    "浙江卫视4K": "https://epg.51zmt.top:8001/logos/zjstv4k.png",
    "东方卫视": "https://epg.51zmt.top:8001/logos/dftv.png",
    "东方卫视高清": "https://epg.51zmt.top:8001/logos/dftv.png",
    "东方卫视4K": "https://epg.51zmt.top:8001/logos/dftv4k.png",
    "北京卫视": "https://epg.51zmt.top:8001/logos/bjtv.png",
    "北京卫视高清": "https://epg.51zmt.top:8001/logos/bjtv.png",
    "北京卫视4K": "https://epg.51zmt.top:8001/logos/bjtv4k.png",
    "深圳卫视": "https://epg.51zmt.top:8001/logos/sztv.png",
    "深圳卫视高清": "https://epg.51zmt.top:8001/logos/sztv.png",
    "深圳卫视4K": "https://epg.51zmt.top:8001/logos/sztv4k.png",
    "广东卫视": "https://epg.51zmt.top:8001/logos/gdtv.png",
    "广东卫视高清": "https://epg.51zmt.top:8001/logos/gdtv.png",
    "广东卫视4K": "https://epg.51zmt.top:8001/logos/gdtv4k.png",
    "天津卫视": "https://epg.51zmt.top:8001/logos/tjtv.png",
    "天津卫视高清": "https://epg.51zmt.top:8001/logos/tjtv.png",
    "山东卫视": "https://epg.51zmt.top:8001/logos/sdtv.png",
    "山东卫视高清": "https://epg.51zmt.top:8001/logos/sdtv.png",
    "山东卫视4K": "https://epg.51zmt.top:8001/logos/sdtv4k.png",
    "江西卫视": "https://epg.51zmt.top:8001/logos/jxtv.png",
    "江西卫视高清": "https://epg.51zmt.top:8001/logos/jxtv.png",
    "东南卫视": "https://epg.51zmt.top:8001/logos/dntv.png",
    "东南卫视高清": "https://epg.51zmt.top:8001/logos/dntv.png",
    "黑龙江卫视": "https://epg.51zmt.top:8001/logos/hljtv.png",
    "黑龙江卫视高清": "https://epg.51zmt.top:8001/logos/hljtv.png",
    "贵州卫视": "https://epg.51zmt.top:8001/logos/gztv.png",
    "贵州卫视高清": "https://epg.51zmt.top:8001/logos/gztv.png",
    "湖北卫视": "https://epg.51zmt.top:8001/logos/hbtv.png",
    "湖北卫视高清": "https://epg.51zmt.top:8001/logos/hbtv.png",
    "安徽卫视": "https://epg.51zmt.top:8001/logos/ahtv.png",
    "安徽卫视高清": "https://epg.51zmt.top:8001/logos/ahtv.png",
    "河北卫视": "https://epg.51zmt.top:8001/logos/hbtv.png",
    "河北卫视高清": "https://epg.51zmt.top:8001/logos/hbtv.png",
    "河南卫视": "https://epg.51zmt.top:8001/logos/hatv.png",
    "河南卫视高清": "https://epg.51zmt.top:8001/logos/hatv.png",
    "广西卫视": "https://epg.51zmt.top:8001/logos/gxtv.png",
    "广西卫视高清": "https://epg.51zmt.top:8001/logos/gxtv.png",
    "云南卫视": "https://epg.51zmt.top:8001/logos/yntv.png",
    "云南卫视高清": "https://epg.51zmt.top:8001/logos/yntv.png",
    "吉林卫视": "https://epg.51zmt.top:8001/logos/jltv.png",
    "吉林卫视高清": "https://epg.51zmt.top:8001/logos/jltv.png",
    "陕西卫视": "https://epg.51zmt.top:8001/logos/sxtv.png",
    "陕西卫视高清": "https://epg.51zmt.top:8001/logos/sxtv.png",
    "山西卫视": "https://epg.51zmt.top:8001/logos/sxtv.png",
    "山西卫视高清": "https://epg.51zmt.top:8001/logos/sxtv.png",
    "内蒙古卫视": "https://epg.51zmt.top:8001/logos/nmgtv.png",
    "内蒙古卫视高清": "https://epg.51zmt.top:8001/logos/nmgtv.png",
    "青海卫视": "https://epg.51zmt.top:8001/logos/qhtv.png",
    "青海卫视高清": "https://epg.51zmt.top:8001/logos/qhtv.png",
    "宁夏卫视": "https://epg.51zmt.top:8001/logos/nxtv.png",
    "宁夏卫视高清": "https://epg.51zmt.top:8001/logos/nxtv.png",
    "西藏卫视": "https://epg.51zmt.top:8001/logos/xztv.png",
    "西藏卫视高清": "https://epg.51zmt.top:8001/logos/xztv.png",
    "新疆卫视": "https://epg.51zmt.top:8001/logos/xjtv.png",
    "新疆卫视高清": "https://epg.51zmt.top:8001/logos/xjtv.png",
    "甘肃卫视": "https://epg.51zmt.top:8001/logos/gstv.png",
    "甘肃卫视高清": "https://epg.51zmt.top:8001/logos/gstv.png",
    "海南卫视": "https://epg.51zmt.top:8001/logos/hntv.png",
    "海南卫视高清": "https://epg.51zmt.top:8001/logos/hntv.png",
    "辽宁卫视": "https://epg.51zmt.top:8001/logos/lntv.png",
    "辽宁卫视高清": "https://epg.51zmt.top:8001/logos/lntv.png",
    "兵团卫视": "https://epg.51zmt.top:8001/logos/bttv.png",
    "兵团卫视高清": "https://epg.51zmt.top:8001/logos/bttv.png",
    "厦门卫视": "https://epg.51zmt.top:8001/logos/xmtv.png",
    "厦门卫视高清": "https://epg.51zmt.top:8001/logos/xmtv.png",
    "三沙卫视": "https://epg.51zmt.top:8001/logos/sstv.png",
    "三沙卫视高清": "https://epg.51zmt.top:8001/logos/sstv.png",
    
    # 地方台（四川）
    "SCTV-2": "https://epg.51zmt.top:8001/logos/sctv2.png",
    "SCTV-2高清": "https://epg.51zmt.top:8001/logos/sctv2.png",
    "SCTV-3": "https://epg.51zmt.top:8001/logos/sctv3.png",
    "SCTV-3高清": "https://epg.51zmt.top:8001/logos/sctv3.png",
    "SCTV-4": "https://epg.51zmt.top:8001/logos/sctv4.png",
    "SCTV-4高清": "https://epg.51zmt.top:8001/logos/sctv4.png",
    "SCTV-5": "https://epg.51zmt.top:8001/logos/sctv5.png",
    "SCTV-5高清": "https://epg.51zmt.top:8001/logos/sctv5.png",
    "SCTV-6": "https://epg.51zmt.top:8001/logos/sctv6.png",
    "SCTV-6高清": "https://epg.51zmt.top:8001/logos/sctv6.png",
    "SCTV-7": "https://epg.51zmt.top:8001/logos/sctv7.png",
    "SCTV-7高清": "https://epg.51zmt.top:8001/logos/sctv7.png",
    "SCTV-科教": "https://epg.51zmt.top:8001/logos/sctv8.png",
    "SCTV-科教高清": "https://epg.51zmt.top:8001/logos/sctv8.png",
    "四川乡村": "https://epg.51zmt.top:8001/logos/sctv9.png",
    "四川乡村高清": "https://epg.51zmt.top:8001/logos/sctv9.png",
    "康巴卫视": "https://epg.51zmt.top:8001/logos/kangba.png",
    "康巴卫视高清": "https://epg.51zmt.top:8001/logos/kangba.png",
    "峨眉电影": "https://epg.51zmt.top:8001/logos/emdy.png",
    "峨眉电影高清": "https://epg.51zmt.top:8001/logos/emdy.png",
    "CDTV-1": "https://epg.51zmt.top:8001/logos/cdtv1.png",
    "CDTV-1高清": "https://epg.51zmt.top:8001/logos/cdtv1.png",
    
    # 其他频道
    "中国交通": "https://epg.51zmt.top:8001/logos/zhongjiaotv.png",
    "中国交通高清": "https://epg.51zmt.top:8001/logos/zhongjiaotv.png",
    "山东教育卫视": "https://epg.51zmt.top:8001/logos/sdjytv.png",
    "山东教育卫视高清": "https://epg.51zmt.top:8001/logos/sdjytv.png",
    "延边卫视": "https://epg.51zmt.top:8001/logos/ybstv.png",
    "延边卫视高清": "https://epg.51zmt.top:8001/logos/ybstv.png",
    "北京纪实科教": "https://epg.51zmt.top:8001/logos/bjjskj.png",
    "北京纪实科教高清": "https://epg.51zmt.top:8001/logos/bjjskj.png",
    "爱上4K专区": "https://epg.51zmt.top:8001/logos/4kzone.png",
    "CGTN英语": "https://epg.51zmt.top:8001/logos/cgtn.png",
    "精彩导视": "https://epg.51zmt.top:8001/logos/guide.png",
    
    # 通用台标（最后兜底）
    "default": "https://epg.51zmt.top:8001/logos/default.png"
}

# 过滤关键词：包含这些关键词的频道会被移除（画中画相关）
FILTER_KEYWORDS = ["画中画", "PIP", "pip", "画中", "中画"]

# 分组规则
def get_channel_group(channel_name):
    """根据频道名称判断所属分组"""
    # 央视分组
    if channel_name.startswith("CCTV") or channel_name.startswith("CGTN"):
        return "央视"
    # 地方台（四川）
    elif any(prefix in channel_name for prefix in ["SCTV", "CDTV", "康巴卫视", "峨眉电影", "四川乡村"]):
        return "地方台-四川"
    # 卫视分组
    elif any(suffix in channel_name for suffix in ["卫视", "湖南卫视", "江苏卫视", "浙江卫视", "东方卫视", "北京卫视"]):
        return "省级卫视"
    # 4K专区
    elif "4K" in channel_name or "专区" in channel_name:
        return "4K专区"
    # 其他频道
    else:
        return "其他频道"

def get_multicast_html(url):
    """获取组播源的HTML页面"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # 禁用SSL验证
        response = requests.get(url, verify=False, timeout=30, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'  # 确保中文编码正确
        return response.text
    except Exception as e:
        print(f"获取HTML页面失败: {e}")
        raise

def parse_multicast_table(html_content):
    """解析HTML中的组播表格，提取频道名称和组播地址，过滤画中画频道"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 找到频道表格（根据页面结构定位）
    table = soup.find('table')
    if not table:
        raise ValueError("未找到频道表格")
    
    channels = []
    filtered_count = 0
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue  # 跳过无效行
        
        # 提取数据：第2列是频道名称，第3列是组播地址
        channel_name = cells[1].text.strip()
        multicast_addr = cells[2].text.strip()
        
        # 过滤画中画频道
        if any(keyword in channel_name for keyword in FILTER_KEYWORDS):
            filtered_count += 1
            print(f"过滤画中画频道: {channel_name}")
            continue
        
        if not channel_name or not multicast_addr:
            continue
        
        # 优化台标匹配逻辑：优先精确匹配，没有则用默认
        logo = LOGO_MAPPING.get(channel_name, LOGO_MAPPING['default'])
        # 生成tvg-id（用于EPG匹配）
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
    # M3U8头部（gz格式的EPG源地址）
    m3u8_header = """#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml.gz"
"""
    m3u8_lines = [m3u8_header]

    # 按分组归类频道
    grouped_channels = {}
    for channel in channels:
        group = channel['group']
        if group not in grouped_channels:
            grouped_channels[group] = []
        grouped_channels[group].append(channel)
    
    # 按指定顺序生成分组（控制显示顺序）
    group_order = ["央视", "省级卫视", "地方台-四川", "4K专区", "其他频道"]
    # 补充未在预设顺序中的分组
    all_groups = list(grouped_channels.keys())
    for group in all_groups:
        if group not in group_order:
            group_order.append(group)
    
    # 生成每个分组的频道
    for group in group_order:
        if group not in grouped_channels:
            continue
        
        group_channels = grouped_channels[group]
        # 添加分组标签
        m3u8_lines.append(f"#EXTGRP:{group}")
        m3u8_lines.append("")  # 空行分隔，提升可读性
        
        for channel in group_channels:
            name = channel['name']
            multicast = channel['multicast']
            logo = channel['logo']
            tvg_id = channel['tvg_id']
            
            # 解析组播地址（格式：239.255.1.1:1234）
            multicast_parts = multicast.split(":")
            if len(multicast_parts) != 2:
                print(f"跳过无效组播地址: {multicast} (频道: {name})")
                continue
            
            ip = multicast_parts[0]
            port = multicast_parts[1]
            
            # 拼接udpxy转单播地址
            udpxy_url = f"{udpxy_proxy.rstrip('/')}/udp/{ip}:{port}"
            
            # 构建频道条目
            channel_line = f"""#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}",{name}
{udpxy_url}
"""
            m3u8_lines.append(channel_line)
    
    return "".join(m3u8_lines)

def main():
    # 从环境变量获取udpxy代理地址
    udpxy_proxy = os.getenv("UDPXY_PROXY", "http://192.168.16.254:8866")
    # 数据源地址
    source_url = "https://epg.51zmt.top:8001/multicast/"
    # 输出文件
    output_file = "iptv.m3u8"

    try:
        # 1. 获取HTML页面
        print(f"开始请求组播数据源: {source_url}")
        html_content = get_multicast_html(source_url)
        
        # 2. 解析表格数据（过滤画中画频道）
        channels = parse_multicast_table(html_content)
        
        if not channels:
            raise ValueError("未解析到任何频道数据")
        
        # 3. 生成带分组的m3u8内容
        m3u8_content = generate_m3u8(channels, udpxy_proxy)
        
        # 4. 保存文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u8_content)
        
        # 打印分组统计
        print(f"\n✅ m3u8文件生成完成")
        print(f"📄 文件路径：{output_file}")
        print(f"🔌 使用的udpxy代理地址：{udpxy_proxy}")
        print(f"📡 EPG源地址：http://epg.51zmt.top:8000/e.xml.gz")
        print(f"\n📊 频道分组统计：")
        group_stats = {}
        for channel in channels:
            group = channel['group']
            group_stats[group] = group_stats.get(group, 0) + 1
        for group, count in group_stats.items():
            print(f"  - {group}: {count} 个频道")
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        # 生成备用m3u8文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# 数据获取失败，请检查数据源地址或网络\n")
        raise

if __name__ == "__main__":
    main()
