import os
import json
import base64
import hmac
import hashlib
from datetime import datetime
import requests
import oss2

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
        # 获取图片流
        response = requests.get(source_url, stream=True)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch image from {source_url}: {response.status_code}")

        # 上传到 OSS
        result = self.bucket.put_object(object_name, response.content)
        if result.status != 200:
            raise Exception(f"Failed to upload to OSS: {result.status}")

        return result

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
        raise Exception(f"Failed to send Telegram message: {response.status_code} {response.text}")

# 从URL提取文件名
def get_file_name(url):
    return url.split('/')[-1]

# 处理单个图片
def process_image(url, type, oss, processed_links):
    # 检查是否已经处理过这个URL
    if url in processed_links:
        return None

    file_name = get_file_name(url)
    object_name = f"pixiv/{type}/{file_name}"

    # 使用流式上传
    oss.put_object_from_url(url, object_name)

    # 记录到 processed_links
    processed_links[url] = datetime.now().isoformat()

    return object_name

# 主要处理逻辑
def handle_request():
    endpoints = {
        'm': 'https://pxrank-api.onani.cn/m',
        'w': 'https://pxrank-api.onani.cn/w',
        'd': 'https://pxrank-api.onani.cn/d',
        'n': 'https://pxrank-api.onani.cn/n'
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
        processed_links = {}
        send_telegram_message(bot_token, chat_id, '🔄 Monthly link cleanup completed')

    # 处理每个端点
    for type, endpoint in endpoints.items():
        try:
            # 获取URL列表
            response = requests.get(endpoint)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch URLs from {endpoint}: {response.status_code}")

            url_list = response.text.strip().split('\n')
            
            success_count = 0
            failure_count = 0
            failures = []

            # 处理每个URL
            for url in url_list:
                try:
                    result = process_image(url.strip(), type, oss, processed_links)
                    if result:
                        success_count += 1
                        # 每成功处理5张图片发送一次进度通知
                        if success_count % 5 == 0:
                            send_telegram_message(
                                bot_token,
                                chat_id,
                                f"📈 Progress update ({type}):\nProcessed: {success_count}/{len(url_list)}"
                            )
                except Exception as error:
                    failure_count += 1
                    failures.append({"url": url, "error": str(error)})
                    print(f"Error processing {url}: {error}")

            # 发送处理完成通知
            if success_count > 0 or failure_count > 0:
                message = f"📊 Summary for type: {type}\n" \
                         f"✅ Successful: {success_count}\n" \
                         f"❌ Failed: {failure_count}\n" \
                         f"📁 Type: {type}\n\n"
                
                if failures:
                    message += "Failed URLs:\n"
                    # 只显示前5个失败的URL，避免消息过长
                    for failure in failures[:5]:
                        message += f"{failure['url']}\nError: {failure['error']}\n\n"
                    if len(failures) > 5:
                        message += f"...and {len(failures) - 5} more failures\n"
                
                send_telegram_message(bot_token, chat_id, message)

        except Exception as error:
            print(f"Error processing endpoint {endpoint}: {error}")
            send_telegram_message(
                bot_token, 
                chat_id, 
                f"❌ Error processing endpoint {endpoint}: {error}"
            )

    # 保存已处理的链接
    with open('link.json', 'w') as f:
        json.dump(processed_links, f)

# 主函数
if __name__ == "__main__":
    handle_request()
