import os
import json
import asyncio
import httpx
from bs4 import BeautifulSoup
import oss2
from telegram.ext import Application
from io import BytesIO
import sys

# 验证必需的环境变量
required_env_vars = {
    'ACCESS_KEY_ID': os.getenv('ACCESS_KEY_ID'),
    'ACCESS_KEY_SECRET': os.getenv('ACCESS_KEY_SECRET'),
    'OSS_ENDPOINT': os.getenv('OSS_ENDPOINT'),
    'OSS_BUCKET': os.getenv('OSS_BUCKET'),
    'BOT_TOKEN': os.getenv('BOT_TOKEN'),
    'CHAT_ID': os.getenv('CHAT_ID')
}

# 检查环境变量
missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    print(f"错误: 以下环境变量未设置: {', '.join(missing_vars)}")
    sys.exit(1)

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.pixiv.net'
}

# Pixiv ranking页面
RANKING_URLS = [
    'https://www.pixiv.net/ranking.php?mode=daily',
    'https://www.pixiv.net/ranking.php?mode=weekly',
    'https://www.pixiv.net/ranking.php?mode=monthly',
    'https://www.pixiv.net/ranking.php?mode=rookie',
    'https://www.pixiv.net/ranking.php?mode=original',
    'https://www.pixiv.net/ranking.php?mode=daily_ai'
]

# Telegram bot 设置
async def send_telegram_message(bot_token, chat_id, message):
    try:
        application = Application.builder().token(bot_token).build()
        await application.bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"发送 Telegram 消息时出错: {str(e)}")

# 设置OSS客户端
try:
    auth = oss2.Auth(required_env_vars['ACCESS_KEY_ID'], required_env_vars['ACCESS_KEY_SECRET'])
    bucket = oss2.Bucket(auth, required_env_vars['OSS_ENDPOINT'], required_env_vars['OSS_BUCKET'])
except Exception as e:
    print(f"初始化 OSS 客户端时出错: {str(e)}")
    sys.exit(1)

async def fetch_ranking_page(client, url):
    try:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        print(f"获取排行榜页面出错 {url}: {str(e)}")
        return None

async def download_image(client, url):
    try:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.content
    except httpx.HTTPError as e:
        print(f"下载图片出错 {url}: {str(e)}")
        return None

async def main():
    bot_token = required_env_vars['BOT_TOKEN']
    chat_id = required_env_vars['CHAT_ID']
    processed_urls = set()
    uploaded_files = []

    print("开始处理Pixiv图片...")
    await send_telegram_message(bot_token, chat_id, "开始处理Pixiv图片...")

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        for ranking_url in RANKING_URLS:
            try:
                html_content = await fetch_ranking_page(client, ranking_url)
                if not html_content:
                    continue

                soup = BeautifulSoup(html_content, 'html.parser')
                img_urls = soup.find_all('img', src=lambda x: x and 'img-master/img/' in x)

                for img in img_urls:
                    src = img['src']
                    if 'c/240x480/' in src:
                        original_url = src.replace('c/240x480/', '')
                        if original_url in processed_urls:
                            continue

                        processed_urls.add(original_url)

                        img_content = await download_image(client, original_url)
                        if img_content:
                            try:
                                # 准备上传到OSS
                                img_data = BytesIO(img_content)
                                file_name = f"pixiv/{original_url.split('/')[-1]}"

                                # 检查文件是否已存在
                                headers = {'x-oss-forbid-overwrite': 'true'}
                                bucket.put_object(file_name, img_data, headers=headers)

                                uploaded_files.append(f"https://aliyun-oss.onani.cn/{file_name}")

                                # 发送进度消息
                                print(f"成功上传: {file_name}")
                                await send_telegram_message(bot_token, chat_id, f"成功上传: {file_name}")

                            except Exception as e:
                                print(f"上传到OSS时出错: {str(e)}")
                                await send_telegram_message(bot_token, chat_id, f"上传文件时出错: {str(e)}")

            except Exception as e:
                error_msg = f"处理排行榜页面出错: {str(e)}"
                print(error_msg)
                await send_telegram_message(bot_token, chat_id, error_msg)

    # 将所有URL保存到json文件
    try:
        with open('oss_url.json', 'w', encoding='utf-8') as f:
            json.dump(uploaded_files, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存json文件时出错: {str(e)}")

    # 发送完成消息
    final_msg = f"处理完成！共上传 {len(uploaded_files)} 个文件"
    print(final_msg)
    await send_telegram_message(bot_token, chat_id, final_msg)

if __name__ == "__main__":
    asyncio.run(main())