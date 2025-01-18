import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup
import oss2
from telegram.ext import Application
from io import BytesIO

# Telegram bot 设置
async def send_telegram_message(bot_token, chat_id, message):
    application = Application.builder().token(bot_token).build()
    await application.bot.send_message(chat_id=chat_id, text=message)

# 设置OSS客户端
auth = oss2.Auth(os.getenv('ACCESS_KEY_ID'), os.getenv('ACCESS_KEY_SECRET'))
bucket = oss2.Bucket(auth, os.getenv('OSS_ENDPOINT'), os.getenv('OSS_BUCKET'))

# Pixiv ranking页面
RANKING_URLS = [
    'https://www.pixiv.net/ranking.php?mode=daily',
    'https://www.pixiv.net/ranking.php?mode=weekly',
    'https://www.pixiv.net/ranking.php?mode=monthly',
    'https://www.pixiv.net/ranking.php?mode=rookie',
    'https://www.pixiv.net/ranking.php?mode=original',
    'https://www.pixiv.net/ranking.php?mode=daily_ai'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.pixiv.net'
}

async def main():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    processed_urls = set()
    uploaded_files = []

    # 发送开始消息
    await send_telegram_message(bot_token, chat_id, "开始处理Pixiv图片...")

    for ranking_url in RANKING_URLS:
        try:
            response = requests.get(ranking_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有图片URL
            img_urls = soup.find_all('img', src=lambda x: x and 'img-master/img/' in x)
            
            for img in img_urls:
                src = img['src']
                if 'c/240x480/' in src:
                    original_url = src.replace('c/240x480/', '')
                    if original_url in processed_urls:
                        continue
                        
                    processed_urls.add(original_url)
                    
                    try:
                        # 下载图片
                        img_response = requests.get(original_url, headers=headers)
                        if img_response.status_code == 200:
                            # 准备上传到OSS
                            img_data = BytesIO(img_response.content)
                            file_name = f"pixiv/{original_url.split('/')[-1]}"
                            
                            # 检查文件是否已存在
                            headers = {'x-oss-forbid-overwrite': 'true'}
                            bucket.put_object(file_name, img_data, headers=headers)
                            
                            uploaded_files.append(f"https://aliyun-oss.onani.cn/{file_name}")
                            
                            # 发送进度消息
                            await send_telegram_message(bot_token, chat_id, 
                                f"成功上传: {file_name}")
                            
                    except Exception as e:
                        await send_telegram_message(bot_token, chat_id,
                            f"处理图片时出错: {str(e)}")
                        
        except Exception as e:
            await send_telegram_message(bot_token, chat_id,
                f"处理排行榜页面出错: {str(e)}")

    # 将所有URL保存到json文件
    with open('oss_url.json', 'w', encoding='utf-8') as f:
        json.dump(uploaded_files, f, ensure_ascii=False, indent=2)

    # 发送完成消息
    await send_telegram_message(bot_token, chat_id,
        f"处理完成！共上传 {len(uploaded_files)} 个文件")

if __name__ == "__main__":
    asyncio.run(main())