import os
import httpx
import oss2
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)

new_count = 0
existing_count = 0
error_count = 0

def upload_to_oss(url):
    global new_count, existing_count, error_count
    
    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    oss_endpoint = os.getenv('OSS_ENDPOINT')
    oss_bucket_name = os.getenv('OSS_BUCKET')
    
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    
    headers = {'Referer': 'https://www.pixiv.net'}
    
    url = url.strip()
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        object_name = f'pixiv/{os.path.basename(url)}'
        try:
            bucket.put_object(object_name, response.content, headers={'x-oss-forbid-overwrite': 'true'})
            logging.info(f'Successfully uploaded: {object_name}')
            new_count += 1
        except oss2.exceptions.OssError as e:
            if e.status == 409:
                logging.info(f'File already exists, skipping: {object_name}')
                existing_count += 1
            else:
                logging.error(f'Failed to upload {object_name}: {e}')
                error_count += 1

def main():
    with open('link.txt', 'r') as file:
        urls = file.readlines()
    
    with ThreadPoolExecutor(max_workers=24) as executor:
        executor.map(upload_to_oss, urls)
    
    logging.info(f'New images: {new_count}')
    logging.info(f'Existing images: {existing_count}')
    logging.info(f'Errors: {error_count}')

if __name__ == "__main__":
    main()
