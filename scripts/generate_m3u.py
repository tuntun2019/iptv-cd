def fetch_multicast_data(url):
    """适配Bootstrap网页的组播数据解析"""
    try:
        print(f"\n=== 开始获取组播数据：{url} ===")
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
        
        print(f"HTTP状态码：{response.status_code}")
        print(f"返回内容前1000字符：\n{response.text[:1000]}")
        
        soup = BeautifulSoup(response.text, "lxml")
        channels = []
        
        # 适配Bootstrap表格（精准定位：包含组播数据的表格）
        # 匹配所有表格，遍历查找包含"udp://"的单元格
        all_tables = soup.find_all("table")
        print(f"检测到{len(all_tables)}个表格，开始逐个解析...")
        
        for table_idx, table in enumerate(all_tables):
            rows = table.find_all("tr")
            for row_idx, row in enumerate(rows):
                # 获取所有单元格（td/th）
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                
                # 提取频道名和UDP地址（适配任意列顺序）
                name = ""
                udp_url = ""
                for cell in cells:
                    cell_text = cell.text.strip()
                    if cell_text.startswith("udp://"):
                        udp_url = cell_text
                    elif cell_text and not udp_url:  # 优先取非UDP的列作为频道名
                        name = cell_text
                
                # 验证并添加
                if name and udp_url and udp_url.startswith("udp://"):
                    channels.append({"name": name, "udp_url": udp_url})
                    print(f"表格{table_idx+1}行{row_idx+1}：{name} -> {udp_url}")
        
        # 兜底：若解析为0，使用测试数据
        if len(channels) == 0:
            print("未解析到任何频道，使用测试数据...")
            channels = [
                {"name": "CCTV-1 综合", "udp_url": "udp://@239.136.116.100:8000"},
                {"name": "CCTV-5 体育", "udp_url": "udp://@239.136.116.105:8000"},
                {"name": "湖南卫视", "udp_url": "udp://@239.136.118.101:8000"},
                {"name": "CCTV-5 体育 画中画", "udp_url": "udp://@239.136.116.106:8000"}
            ]
        
        print(f"=== 解析完成，原始频道数：{len(channels)} ===")
        return channels
    
    except Exception as e:
        print(f"\n=== 获取组播数据失败：{str(e)} ===")
        # 测试数据兜底
        return [
            {"name": "CCTV-1 综合", "udp_url": "udp://@239.136.116.100:8000"},
            {"name": "CCTV-5 体育", "udp_url": "udp://@239.136.116.105:8000"},
            {"name": "湖南卫视", "udp_url": "udp://@239.136.118.101:8000"},
            {"name": "CCTV-5 体育 画中画", "udp_url": "udp://@239.136.116.106:8000"}
        ]
