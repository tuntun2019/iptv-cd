import os
import json
import requests
from urllib.parse import quote

def get_multicast_data(url):
    """获取组播源数据，增加调试和异常处理"""
    try:
        # 禁用 SSL 验证（因源地址是自签名证书）
        # 添加请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(
            url, 
            verify=False, 
            timeout=30,
            headers=headers
        )
        response.raise_for_status()
        
        # 打印调试信息：查看返回的状态码和前500个字符
        print(f"请求状态码: {response.status_code}")
        print(f"返回内容（前500字符）: {response.text[:500]}")
        
        # 尝试解析JSON
        try:
            return response.json()
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"完整返回内容: {response.text}")
            # 尝试修复可能的JSON格式问题（比如BOM头、多余字符）
            cleaned_text = response.text.strip().lstrip('\ufeff')
            if cleaned_text:
                try:
                    return json.loads(cleaned_text)
                except:
                    raise
            raise
    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        raise
    except Exception as e:
        print(f"获取组播数据失败: {e}")
        raise

def generate_m3u8(multicast_data, udpxy_proxy):
    """生成带udpxy、台标、EPG的m3u8内容"""
    m3u8_header = """#EXTM3U x-tvg-url="https://epg.51zmt.top:8001/epg/epg.xml"
"""
    m3u8_lines = [m3u8_header]

    # 检查数据是否有效
    if not isinstance(multicast_data, list):
        print(f"无效的组播数据格式，期望列表，实际: {type(multicast_data)}")
        return m3u8_header

    for channel in multicast_data:
        # 提取频道基础信息（增加默认值，避免KeyError）
        name = channel.get("name", "未知频道")
        multicast = channel.get("multicast", "")
        logo = channel.get("logo", "")
        tvg_id = channel.get("tvg_id", "")
        
        if not multicast:
            print(f"跳过无组播地址的频道: {name}")
            continue

        # 解析组播地址（格式：239.255.1.1:1234）
        multicast_parts = multicast.split(":")
        if len(multicast_parts) != 2:
            print(f"无效的组播地址格式: {multicast} (频道: {name})")
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
    
    final_content = "".join(m3u8_lines)
    print(f"共生成 {len(m3u8_lines)-1} 个频道")
    return final_content

def main():
    # 从环境变量获取udpxy代理地址，默认值为指定地址
    udpxy_proxy = os.getenv("UDPXY_PROXY", "http://192.168.16.254:8866")
    # 数据源地址
    source_url = "https://epg.51zmt.top:8001/multicast/"
    # 生成的m3u8文件保存路径
    output_file = "iptv.m3u8"

    try:
        # 1. 获取组播数据
        print(f"开始请求组播数据源: {source_url}")
        multicast_data = get_multicast_data(source_url)
        print(f"成功获取组播数据，共 {len(multicast_data)} 条记录")
        
        # 2. 生成m3u8内容
        m3u8_content = generate_m3u8(multicast_data, udpxy_proxy)
        
        # 3. 保存到文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u8_content)
        
        print(f"\n✅ m3u8文件生成完成")
        print(f"📄 文件路径：{output_file}")
        print(f"🔌 使用的udpxy代理地址：{udpxy_proxy}")
        print(f"📺 频道数量：{len(m3u8_content.split('#EXTINF:-1')) - 1}")
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        # 生成一个空的m3u8文件，避免Action因文件不存在而提交失败
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# 数据获取失败，请检查数据源地址\n")
        # 抛出异常，让Action标记为失败
        raise

if __name__ == "__main__":
    main()
