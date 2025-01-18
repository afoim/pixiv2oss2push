import os
import oss2
import json
import logging
from datetime import datetime, timedelta

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

def cleanup_old_files():
    # 获取OSS配置
    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    oss_endpoint = os.getenv('OSS_ENDPOINT')
    oss_bucket_name = os.getenv('OSS_BUCKET')
    
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    
    # 计算35天前的时间戳
    cutoff_date = datetime.now() - timedelta(days=35)
    
    # 获取所有文件并检查最后修改时间
    deleted_files = []
    marker = ''
    while True:
        object_list = bucket.list_objects(prefix='pixiv/', marker=marker, max_keys=1000)
        for obj in object_list.object_list:
            # 获取文件的最后修改时间
            last_modified = obj.last_modified
            if datetime.fromtimestamp(last_modified) < cutoff_date:
                # 删除超过35天的文件
                bucket.delete_object(obj.key)
                file_url = f'https://aliyun-oss.onani.cn/{obj.key}'
                deleted_files.append(file_url)
                logging.info(f'Deleted old file: {obj.key}')
        
        if len(object_list.object_list) < 1000:
            break
        marker = object_list.next_marker
    
    # 更新url_status.json
    if deleted_files:
        url_status = load_url_status()
        for url in deleted_files:
            if url in url_status:
                url_status[url] = 0
        save_url_status(url_status)
    
    logging.info(f'Cleanup completed. Deleted {len(deleted_files)} files.')

if __name__ == "__main__":
    cleanup_old_files() 