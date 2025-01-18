import os
import oss2
import json
import logging

logging.basicConfig(level=logging.INFO)

def load_url_status():
    try:
        with open('url_status.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_url_status(status_dict):
    with open('url_status.json', 'w') as f:
        json.dump(status_dict, f, indent=2)

def sync_oss_status():
    # 获取OSS配置
    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    oss_endpoint = os.getenv('OSS_ENDPOINT')
    oss_bucket_name = os.getenv('OSS_BUCKET')
    
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    
    # 获取当前OSS中的所有文件
    oss_files = set()
    marker = ''
    while True:
        object_list = bucket.list_objects(prefix='pixiv/', marker=marker, max_keys=1000)
        for obj in object_list.object_list:
            file_url = f'https://aliyun-oss.onani.cn/{obj.key}'
            oss_files.add(file_url)
        if len(object_list.object_list) < 1000:
            break
        marker = object_list.next_marker
    
    # 加载当前的URL状态
    url_status = load_url_status()
    
    # 更新状态
    for url in list(url_status.keys()):
        if url not in oss_files and url_status[url] == 1:
            # 如果文件在OSS中已被删除，将状态设为0
            logging.info(f'File deleted from OSS, resetting status: {url}')
            url_status[url] = 0
    
    # 保存更新后的状态
    save_url_status(url_status)
    logging.info('OSS status sync completed')

if __name__ == "__main__":
    sync_oss_status() 