import os
import json
import requests
import oss2
from datetime import datetime
import sys
import time

# 阿里云 OSS 客户端
class AliyunOSS:
    def __init__(self, access_key_id, access_key_secret, endpoint, bucket):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.bucket_name = bucket
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket)

    def put_object_from_url(self, source_url, object_name):
        """从 URL 上传文件到 OSS，禁止覆盖同名文件"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.pixiv.net/',
            'x-oss-forbid-overwrite': 'true'  # 禁止覆盖同名文件
        }
        response = requests.get(source_url, headers=headers, stream=True)
        if response.status_code != 200:
            print(f"从 {source_url} 获取图片失败：")
            print(f"状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            print(f"响应体: {response.text}")
            sys.exit(1)

        # 上传到 OSS
        try:
            result = self.bucket.put_object(object_name, response.content, headers=headers)
            if result.status != 200:
                print(f"上传到 OSS 失败：")
                print(f"状态码: {result.status}")
                print(f"响应头: {result.headers}")
                print(f"响应体: {result.resp.read()}")
                sys.exit(1)
            return result
        except oss2.exceptions.OssError as e:
            if e.status == 409:  # 409 表示文件已存在
                print(f"文件 {object_name} 已存在于 OSS，跳过。")
                return None
            else:
                print(f"上传到 OSS 失败: {e}")
                sys.exit(1)

# Telegram 通知功能
def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"发送 Telegram 消息失败：")
        print(f"状态码: {response.status_code}")
        print(f"响应体: {response.text}")
        sys.exit(1)

# 从URL提取文件名
def get_file_name(url):
    return url.split('/')[-1]

# 处理单个图片
def process_image(url, type, oss, processed_links):
    """处理单个图片，确保本地 JSON 中未记录该文件"""
    file_name = get_file_name(url)
    object_name = f"pixiv/{type}/{file_name}"

    # 检查本地 JSON 中是否已记录该文件
    if url in processed_links:
        print(f"文件 {url} 已处理，跳过。")
        return None

    # 上传到 OSS
    result = oss.put_object_from_url(url, object_name)
    if result is None:  # 文件已存在，跳过
        return None

    # 记录到 processed_links
    processed_links[url] = datetime.now().isoformat()

    return object_name

# 主要处理逻辑
def handle_request():
    endpoints = {
        '每月': 'https://pxrank-api.onani.cn/m',
        '每周': 'https://pxrank-api.onani.cn/w',
        '每日': 'https://pxrank-api.onani.cn/d',
        '新人': 'https://pxrank-api.onani.cn/n'
    }

    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')

    oss = AliyunOSS(
        access_key_id,
        access_key_secret,
        'oss-cn-hongkong.aliyuncs.com',
        'acofork-hk'
    )

    # 读取已处理的链接
    if os.path.exists('link.json'):
        with open('link.json', 'r') as f:
            processed_links = json.load(f)
    else:
        processed_links = {}

    # 检查是否是月初，如果是则清空 processed_links
    now = datetime.now()
    if now.day == 1:
        print(f"当前时间为 {now.year} 年 {now.month} 月 1 日，尝试清空 link.json...")
        processed_links = {}
        with open('link.json', 'w') as f:
            json.dump(processed_links, f)
        print("清空 link.json 成功。")
        send_telegram_message(bot_token, chat_id, f"🔄 {now.year} 年 {now.month} 月 1 日，已清空 link.json。")

    # 发送开始运行通知
    start_time = time.time()
    send_telegram_message(bot_token, chat_id, "🚀 Github Action - Run Pixiv Image Uploader 开始运行...")

    # 处理每个端点
    for type, endpoint in endpoints.items():
        try:
            # 获取URL列表
            response = requests.get(endpoint)
            if response.status_code != 200:
                print(f"从 {endpoint} 获取 URL 列表失败：")
                print(f"状态码: {response.status_code}")
                print(f"响应头: {response.headers}")
                print(f"响应体: {response.text}")
                sys.exit(1)

            url_list = response.text.strip().split('\n')
            
            success_count = 0
            skip_count = 0
            failures = []

            # 处理每个URL
            for url in url_list:
                try:
                    result = process_image(url.strip(), type, oss, processed_links)
                    if result:
                        success_count += 1
                    else:
                        skip_count += 1
                except Exception as error:
                    failures.append({"url": url, "error": str(error)})
                    print(f"处理 {url} 失败: {error}")
                    sys.exit(1)

            # 发送处理完成通知
            if success_count > 0:
                message = f"📊 {type}排行榜同步完成：\n" \
                         f"✅ 成功上传: {success_count} 张\n" \
                         f"⏩ 跳过: {skip_count} 张\n" \
                         f"📁 类型: {type}"
                send_telegram_message(bot_token, chat_id, message)
            else:
                print(f"暂未发现 {type}排行榜有新增内容（本次检查的所有内容都已经在 link.json 中），跳过。")

        except Exception as error:
            print(f"处理 {type}排行榜失败: {error}")
            send_telegram_message(
                bot_token, 
                chat_id, 
                f"❌ 处理 {type}排行榜失败: {error}"
            )
            sys.exit(1)

    # 保存已处理的链接
    with open('link.json', 'w') as f:
        json.dump(processed_links, f)

    # 发送运行结束通知
    end_time = time.time()
    total_time = int(end_time - start_time)
    total_success = sum(1 for url in processed_links if url.startswith('http'))
    send_telegram_message(
        bot_token,
        chat_id,
        f"🏁 Github Action - Run Pixiv Image Uploader 运行结束，本次共同步 {total_success} 张图片，耗时 {total_time} 秒。"
    )

# 主函数
if __name__ == "__main__":
    handle_request()
