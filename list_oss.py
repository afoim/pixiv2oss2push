import os
import oss2

def list_oss_files():
    access_key_id = os.getenv('ACCESS_KEY_ID')
    access_key_secret = os.getenv('ACCESS_KEY_SECRET')
    oss_endpoint = os.getenv('OSS_ENDPOINT')
    oss_bucket_name = os.getenv('OSS_BUCKET')
    
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    
    oss_url_prefix = 'https://aliyun-oss.onani.cn/pixiv/'
    
    urls = []
    marker = ''
    while True:
        object_list = bucket.list_objects(prefix='pixiv/', marker=marker, max_keys=1000)
        for obj in object_list.object_list:
            file_url = oss_url_prefix + obj.key[len('pixiv/'):]
            urls.append(file_url)
        if len(object_list.object_list) < 1000:
            break
        marker = object_list.next_marker
    
    os.makedirs('static', exist_ok=True)
    with open('static/oss_link.txt', 'w') as file:
        for url in reversed(urls):
            file.write(url + '\n')

if __name__ == "__main__":
    list_oss_files()
