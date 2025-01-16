import httpx
import re
import json
import os
from datetime import datetime

def get_html(url, headers):
    try:
        client = httpx.Client(verify=False, follow_redirects=True)
        response = client.get(url, headers=headers)
        return response.text
    finally:
        client.close()

def extract_image_urls(html_text):
    # 先匹配完整的URL
    pattern = r'https://i\.pximg\.net/c/240x480/img-master/img/[^"\']+\.jpg'
    urls = re.findall(pattern, html_text)
    
    # 处理URL格式，移除 c/240x480/ 并添加参数
    cleaned_urls = []
    for url in urls:
        cleaned_url = url.replace('/c/240x480/', '/')
        cleaned_urls.append({"url": cleaned_url, "status": 0})
    
    return cleaned_urls

def merge_urls(existing_urls, new_urls):
    """合并新旧URL列表，保留已存在URL的status值，并返回统计信息"""
    existing_dict = {item['url']: item['status'] for item in existing_urls} if existing_urls else {}
    
    merged = []
    existing_count = 0
    new_count = 0
    
    for item in new_urls:
        if item['url'] in existing_dict:
            item['status'] = existing_dict[item['url']]
            existing_count += 1
        else:
            new_count += 1
        merged.append(item)
    
    return merged, existing_count, new_count

def get_all_rankings():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.pixiv.net/',
    }
    
    # 定义排行榜类型和对应的URL
    ranking_types = {
        'daily': 'https://www.pixiv.net/ranking.php?mode=daily',
        'weekly': 'https://www.pixiv.net/ranking.php?mode=weekly',
        'monthly': 'https://www.pixiv.net/ranking.php?mode=monthly',
        'rookie': 'https://www.pixiv.net/ranking.php?mode=rookie',
        'original': 'https://www.pixiv.net/ranking.php?mode=original',
        'daily_ai': 'https://www.pixiv.net/ranking.php?mode=daily_ai'
    }
    
    print(f"开始更新 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    # 确保img目录存在
    if not os.path.exists('img'):
        os.makedirs('img')
        print("创建img目录")
    
    total_new = 0
    total_existing = 0
    
    # 获取并保存每个类型的数据
    for rank_type, url in ranking_types.items():
        print(f"\n处理 {rank_type} 排行榜...")
        
        # 读取现有数据
        output_file = f'img/{rank_type}.json'
        existing_urls = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                try:
                    existing_urls = json.load(f)
                except json.JSONDecodeError:
                    print(f"警告: {output_file} 格式错误，将作为新文件处理")

        # 获取新数据
        html = get_html(url, headers)
        new_urls = extract_image_urls(html)
        
        # 合并数据并获取统计信息
        merged_urls, existing_count, new_count = merge_urls(existing_urls, new_urls)
        total_new += new_count
        total_existing += existing_count
        
        # 保存更新后的数据
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_urls, f, ensure_ascii=False, indent=2)
        
        print(f"完成 {rank_type}:")
        print(f"  - 新增: {new_count} 个URLs")
        print(f"  - 已存在: {existing_count} 个URLs")
        print(f"  - 总计: {len(merged_urls)} 个URLs")
    
    print(f"\n更新完成 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"总统计:")
    print(f"  - 总新增: {total_new} 个URLs")
    print(f"  - 总已存在: {total_existing} 个URLs")
    print(f"  - 总计: {total_new + total_existing} 个URLs")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    
    get_all_rankings()
