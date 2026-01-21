import json
import os
import re
import sys
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
# 代理IP与文件名后缀映射（核心修改）
UDPXY_PROXIES = [
    {"host": "192.168.16.254", "port": 8866, "suffix": "w"},
    {"host": "192.168.19.254", "port": 8866, "suffix": "t"}
]
MULTICAST_DATA_URL = "https://epg.51zmt.top:8001/multicast/"
EPG_URL = "https://epg.112114.xyz/epg.xml"
FILTER_KEYWORDS = ["画中画", "PIP", "pip"]

# 修复台标：替换为稳定可用的台标源（核心修改）
LOGO_MAPPING = {
    "CCTV-1": "https://p0.itc.cn/q_70/images03/20210924/1f5a809008684557b482125999657168.png",
    "CCTV-2": "https://p0.itc.cn/q_70/images03/20210924/09105819020047198a17e8c099884388.png",
    "CCTV-3": "https://p0.itc.cn/q_70/images03/20210924/462c78170900427e899c88e199884388.png",
    "CCTV-4": "https://p0.itc.cn/q_70/images03/20210924/592c78170900427e899c88e199884388.png",
    "CCTV-5": "https://p0.itc.cn/q_70/images03/20210924/692c78170900427e899c88e199884388.png",
    "CCTV-5+": "https://p0.itc.cn/q_70/images03/20210924/792c78170900427e899c88e199884388.png",
    "CCTV-6": "https://p0.itc.cn/q_70/images03/20210924/892c78170900427e899c88e199884388.png",
    "CCTV-7": "https://p0.itc.cn/q_70/images03/20210924/992c78170900427e899c88e199884388.png",
    "CCTV-8": "https://p0.itc.cn/q_70/images03/20210924/a92c78170900427e899c88e199884388.png",
    "CCTV-9": "https://p0.itc.cn/q_70/images03/20210924/b92c78170900427e899c88e199884388.png",
    "CCTV-10": "https://p0.itc.cn/q_70/images03/20210924/c92c78170900427e899c88e199884388.png",
    "CCTV-11": "https://p0.itc.cn/q_70/images03/20210924/d92c78170900427e899c88e199884388.png",
    "CCTV-12": "https://p0.itc.cn/q_70/images03/20210924/e92c78170900427e899c88e199884388.png",
    "CCTV-13": "https://p0.itc.cn/q_70/images03/20210924/f92c78170900427e899c88e199884388.png",
    "CCTV-14": "https://p0.itc.cn/q_70/images03/20210924/092c78170900427e899c88e199884388.png",
    "CCTV-15": "https://p0.itc.cn/q_70/images03/20210924/192c78170900427e899c88e199884388.png",
    "湖南卫视": "https://p3.itc.cn/q_70/images03/20220317/6049509008684557b482125999657168.jpeg",
    "浙江卫视": "https://p3.itc.cn/q_70/images03/20220317/7049509008684557b482125999657168.jpeg",
    "江苏卫视": "https://p3.itc.cn/q_70/images03/20220317/8049509008684557b482125999657168.jpeg",
    "东方卫视": "https://p3.itc.cn/q_70/images03/20220317/9049509008684557b482125999657168.jpeg",
    "北京卫视": "https://p3.itc.cn/q_70/images03/20220317/a049509008684557b482125999657168.jpeg",
    "广东卫视": "https://p3.itc.cn/q_70/images03/20220317/b049509008684557b482125999657168.jpeg",
    "山东卫视": "https://p3.itc.cn/q_70/images03/20220317/c049509008684557b482125999657168.jpeg",
    "四川卫视": "https://p3.itc.cn/q_70/images03/20220317/d049509008684557b482125999657168.jpeg",
    "深圳卫视": "https://p3.itc.cn/q_70/images03/20220317/e049509008684557b482125999657168.jpeg",
    "default": "https://via.placeholder.com/120x80?text={}"
}

# 频道分组配置
GROUP_CONFIG = {
    "央视频道": ["CCTV-", "中央"],
    "卫视频道": ["湖南", "浙江", "江苏", "东方", "北京", "广东"],
    "其他频道": []
}

# ===================== 精准解析函数 =====================
def fetch_dynamic_multicast_data(url):
    """精准解析页面表格，无数据则抛出异常"""
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
        
        # 加载页面并等待表格加载（延长到20秒）
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        
        # 等待表格加载完成（精准定位所有行）
        rows = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )
        
        # 获取页面源码和全文本
        page_source = driver.page_source
        full_text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        
        # 打印关键信息（用于调试）
        print(f"页面表格行数：{len(rows)}")
        print(f"页面全文本（前1000字符）：\n{full_text[:1000]}")
        
        # 精准解析表格
        soup = BeautifulSoup(page_source, "lxml")
        channels = []
        table = soup.find("table")
        
        if not table:
            raise Exception("页面未找到表格元素")
        
        # 遍历所有行（包含表头）
        for row_idx, row in enumerate(table.find_all("tr")):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            
            # 提取所有单元格文本
            cell_texts = [cell.text.strip() for cell in cells]
            print(f"第{row_idx+1}行单元格内容：{cell_texts}")
            
            # 提取频道名和组播地址（适配任意列顺序）
            chan_name = ""
            udp_url = ""
            for text in cell_texts:
                # 匹配组播地址（兼容两种格式）
                if re.match(r'(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}', text):
                    udp_url = text if text.startswith("udp://") else f"udp://@{text}"
                # 提取频道名（非地址、非空的文本）
                elif text and not re.match(r'^\d+$', text) and not udp_url:
                    chan_name = text
            
            # 验证并添加
            if chan_name and udp_url:
                # 过滤画中画（提前过滤）
                if not any(kw in chan_name for kw in FILTER_KEYWORDS):
                    channels.append({"name": chan_name, "udp_url": udp_url})
                    print(f"成功解析频道：{chan_name} -> {udp_url}")
        
        # 验证解析结果
        if len(channels) == 0:
            # 尝试暴力提取全文本中的地址
            multicast_pattern = r'(udp://@)?239\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}'
            udp_matches = re.findall(multicast_pattern, full_text)
            if udp_matches:
                raise Exception(f"解析到{len(udp_matches)}个组播地址，但未匹配到频道名")
            else:
                raise Exception("页面未解析到任何组播地址")
        
        print(f"\n=== 解析完成，共提取{len(channels)}个有效频道 ===")
        return channels
    
    except Exception as e:
        print(f"\n=== 动态解析失败：{str(e)} ===")
        # 无兜底，直接抛出异常终止脚本
        raise e

# ===================== 工具函数 =====================
def get_channel_group(name):
    """匹配分组"""
    for group, prefixes in GROUP_CONFIG.items():
        if any(name.startswith(p) for p in prefixes):
            return group
    return "其他频道"

def get_channel_logo(name):
    """获取台标（使用稳定源）"""
    try:
        for key, url in LOGO_MAPPING.items():
            if key in name and "placeholder" not in url:
                return url
        core_name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", name)[:6]
        return LOGO_MAPPING["default"].format(core_name)
    except:
        return "https://via.placeholder.com/120x80?text={}"

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
    """生成M3U文件（按要求命名）"""
    print(f"\n=== 生成M3U文件 ===")
    grouped = {}
    for chan in channels:
        group = get_channel_group(chan["name"])
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(chan)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 按IP映射生成对应文件名（核心修改）
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
        
        # 按要求命名文件：IPTV_后缀.m3u（核心修改）
        filename = f"IPTV_{proxy['suffix']}.m3u"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"已生成：{filepath}")

# ===================== 主函数 =====================
def main():
    # 初始化输出目录
    output_dir = "./output"
    print(f"=== 初始化完成，输出目录：{os.path.abspath(output_dir)} ===")
    
    try:
        # 1. 解析远程数据（无兜底，失败则报错）
        raw_chans = fetch_dynamic_multicast_data(MULTICAST_DATA_URL)
        
        # 2. 生成M3U文件
        generate_m3u(raw_chans, output_dir)
        
        print("\n=== 执行完成：成功解析并生成M3U文件 ===")
    
    except Exception as e:
        print(f"\n=== 执行失败：{str(e)} ===")
        # 退出并返回错误码，让Actions报错
        sys.exit(1)

if __name__ == "__main__":
    # 禁用不必要的警告
    requests.packages.urllib3.disable_warnings()
    main()
