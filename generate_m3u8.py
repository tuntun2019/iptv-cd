import os
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# 配置：台标映射（可根据需要扩展）
LOGO_MAPPING = {
    "CCTV-1": "https://epg.51zmt.top:8001/logos/cctv1.png",
    "CCTV-2": "https://epg.51zmt.top:8001/logos/cctv2.png",
    "CCTV-3": "https://epg.51zmt.top:8001/logos/cctv3.png",
    "CCTV-4": "https://epg.51zmt.top:8001/logos/cctv4.png",
    "CCTV-5": "https://epg.51zmt.top:8001/logos/cctv5.png",
    "CCTV-6": "https://epg.51zmt.top:8001/logos/cctv6.png",
    "CCTV-7": "https://epg.51zmt.top:8001/logos/cctv7.png",
    "CCTV-8": "https://epg.51zmt.top:8001/logos/cctv8.png",
    "CCTV-9": "https://epg.51zmt.top:8001/logos/cctv9.png",
    "CCTV-10": "https://epg.51zmt.top:8001/logos/cctv10.png",
    "CCTV-11": "https://epg.51zmt.top:8001/logos/cctv11.png",
    "CCTV-12": "https://epg.51zmt.top:8001/logos/cctv12.png",
    "CCTV-13": "https://epg.51zmt.top:8001/logos/cctv13.png",
    "CCTV-14": "https://epg.51zmt.top:8001/logos/cctv14.png",
    "CCTV-15": "https://epg.51zmt.top:8001/logos/cctv15.png",
    "CCTV-17": "https://epg.51zmt.top:8001/logos/cctv17.png",
    "四川卫视": "https://epg.51zmt.top:8001/logos/sctv1.png",
    "湖南卫视": "https://epg.51zmt.top:8001/logos/hntv.png",
    "江苏卫视": "https://epg.51zmt.top:8001/logos/jstv.png",
    "浙江卫视": "https://epg.51zmt.top:8001/logos/zjstv.png",
    "东方卫视": "https://epg.51zmt.top:8001/logos/dftv.png",
    "北京卫视": "https://epg.51zmt.top:8001/logos/bjtv.png",
    # 通用台标（匹配不到时使用）
    "default": "https://epg.51zmt.top:8001/logos/default.png"
}

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
    """解析HTML中的组播表格，提取频道名称和组播地址"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 找到频道表格（根据页面结构定位）
    table = soup.find('table')
    if not table:
        raise ValueError("未找到频道表格")
    
    channels = []
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue  # 跳过无效行
        
        # 提取数据：第2列是频道名称，第3列是组播地址
        channel_name = cells[1].text.strip()
        multicast_addr = cells[2].text.strip()
        
        if not channel_name or not multicast_addr:
            continue
        
        # 匹配台标（优先精确匹配，没有则用默认）
        logo = LOGO_MAPPING.get(channel_name.split('高清')[0].strip(), LOGO_MAPPING['default'])
        # 生成tvg-id（用于EPG匹配）
        tvg_id = channel_name.replace('高清', '').replace('＋', 'plus').replace('-', '').lower()
        
        channels.append({
            'name': channel_name,
            'multicast': multicast_addr,
            'logo': logo,
            'tvg_id': tvg_id
        })
    
    print(f"成功解析到 {len(channels)} 个频道")
    return channels

def generate_m3u8(channels, udpxy_proxy):
    """生成带udpxy、台标、EPG的m3u8内容"""
    # M3U8头部（包含EPG源）
    m3u8_header = """#EXTM3U x-tvg-url="https://epg.51zmt.top:8001/epg/epg.xml"
"""
    m3u8_lines = [m3u8_header]

    for channel in channels:
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
        
        # 2. 解析表格数据
        channels = parse_multicast_table(html_content)
        
        if not channels:
            raise ValueError("未解析到任何频道数据")
        
        # 3. 生成m3u8内容
        m3u8_content = generate_m3u8(channels, udpxy_proxy)
        
        # 4. 保存文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u8_content)
        
        print(f"\n✅ m3u8文件生成完成")
        print(f"📄 文件路径：{output_file}")
        print(f"🔌 使用的udpxy代理地址：{udpxy_proxy}")
        print(f"📺 有效频道数量：{len(channels)}")
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        # 生成备用m3u8文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# 数据获取失败，请检查数据源地址或网络\n")
        raise

if __name__ == "__main__":
    main()
