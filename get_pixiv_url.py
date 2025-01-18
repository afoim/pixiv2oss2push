import httpx
import re
import logging
import concurrent.futures

# 配置 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局带 Referer 的请求头
headers = {
    'Referer': 'https://www.pixiv.net'
}

# 请求 Pixiv 排行榜页面
logger.info('Requesting Pixiv ranking page...')
response = httpx.get('https://www.pixiv.net/ranking.php?mode=daily', headers=headers)
html_content = response.text

# 查找所有图片 URL
logger.info('Parsing image URLs...')
image_urls = re.findall(r'https://i\.pximg\.net/c/240x480/img-master/img/[\d/]+/[\d]+_p\d+_master1200\.jpg', html_content)

valid_urls = []

def fetch_url(url):
    index = 0
    while True:
        test_url = url.replace('_p0_', f'_p{index}_')
        logger.debug(f'Testing URL: {test_url}')
        response = httpx.get(test_url, headers=headers)
        if '404 Not Found' in response.text:
            logger.debug(f'404 Not Found for URL: {test_url}')
            break
        valid_urls.append(test_url)
        index += 1

# 使用多线程访问 URL
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    executor.map(fetch_url, image_urls)

# 删除 URL 中的 /c/240x480
valid_urls = [url.replace('/c/240x480', '') for url in valid_urls]

# 将所有有效 URL 存入 link.txt
logger.info('Writing valid URLs to link.txt...')
with open('link.txt', 'w') as file:
    for url in valid_urls:
        file.write(url + '\n')
logger.info('Finished writing URLs.')
