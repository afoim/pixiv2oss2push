import os
import httpx
import oss2
import json
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)

new_count = 0
existing_count = 0
error_count = 0
skipped_count = 0

def load_url_status():
    try:
        with open('url_status.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_url_status(status_dict):
    with open('url_status.json', 'w') as f:
        json.dump(status_dict, f, indent=2)

def upload_to_oss(url):
    global new_count, existing_count, error_count, skipped_count
    
    url = url.strip()
    url_status = load_url_status()
    
    # 如果URL已经成功上传过，跳过
    if url_status.get(url) == 1:
        logging.info(f'Already processed, skipping: {url}')
        skipped_count += 1
        return
    
    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    oss_endpoint = os.getenv('OSS_ENDPOINT')
    oss_bucket_name = os.getenv('OSS_BUCKET')
    
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    
    headers = {'Referer': 'https://www.pixiv.net'}
    
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        object_name = f'pixiv/{os.path.basename(url)}'
        try:
            bucket.put_object(object_name, response.content, headers={'x-oss-forbid-overwrite': 'true'})
            logging.info(f'Successfully uploaded: {object_name}')
            new_count += 1
            # 标记为已处理
            url_status[url] = 1
            save_url_status(url_status)
        except oss2.exceptions.OssError as e:
            if e.status == 409:
                logging.info(f'File already exists, skipping: {object_name}')
                existing_count += 1
                # 标记为已处理
                url_status[url] = 1
                save_url_status(url_status)
            else:
                logging.error(f'Failed to upload {object_name}: {e}')
                error_count += 1

def main():
    with open('link.txt', 'r') as file:
        urls = file.readlines()
    
    # 使用较小的线程数以避免频繁的文件读写冲突
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(upload_to_oss, urls)
    
    logging.info(f'New images: {new_count}')
    logging.info(f'Existing images: {existing_count}')
    logging.info(f'Skipped images: {skipped_count}')
    logging.info(f'Errors: {error_count}')

if __name__ == "__main__":
    main()
