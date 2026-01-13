import os
import json
import requests
from urllib.parse import quote

def get_multicast_data(url):
    """获取组播源数据"""
    try:
        # 禁用 SSL 验证（因源地址是自签名证书）
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取组播数据失败: {e}")
        raise

def generate_m3u8(multicast_data, udpxy_proxy):
    """生成带udpxy、台标、EPG的m3u8内容"""
    m3u8_header = """#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml.gz"
"""
    m3u8_lines = [m3u8_header]

    for channel in multicast_data:
        # 提取频道基础信息
        name = channel.get("name", "未知频道")
        multicast = channel.get("multicast", "")
        logo = channel.get("logo", "")
        tvg_id = channel.get("tvg_id", "")
        
        if not multicast:
            continue

        # 解析组播地址（格式：239.255.1.1:1234）
        multicast_parts = multicast.split(":")
        if len(multicast_parts) != 2:
            continue
        
        ip = multicast_parts[0]
        port = multicast_parts[1]
        
        # 拼接udpxy转单播地址：http://代理地址/udp/组播IP:端口
        udpxy_url = f"{udpxy_proxy.rstrip('/')}/udp/{ip}:{port}"
        
        # 构建m3u8频道条目（包含台标、EPG、udpxy链接）
        channel_line = f"""#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}",{name}
{udpxy_url}
"""
        m3u8_lines.append(channel_line)
    
    return "".join(m3u8_lines)

def main():
    # 从环境变量获取udpxy代理地址，默认值为指定地址
    udpxy_proxy = os.getenv("UDPXY_PROXY", "http://192.168.16.254:8866")
    # 数据源地址
    source_url = "https://epg.51zmt.top:8001/multicast/"
    # 生成的m3u8文件保存路径
    output_file = "iptv.m3u8"

    # 1. 获取组播数据
    multicast_data = get_multicast_data(source_url)
    
    # 2. 生成m3u8内容
    m3u8_content = generate_m3u8(multicast_data, udpxy_proxy)
    
    # 3. 保存到文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    
    print(f"m3u8文件生成完成，保存路径：{output_file}")
    print(f"使用的udpxy代理地址：{udpxy_proxy}")

if __name__ == "__main__":
    main()
