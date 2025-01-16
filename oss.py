import oss2
import httpx
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm
from functools import partial

class OSSUploader:
    def __init__(self):
        # 从环境变量中获取 OSS 配置信息
        access_key_id = os.getenv('ACCESS_KEY_ID')
        access_key_secret = os.getenv('ACCESS_KEY_SECRET')
        endpoint = os.getenv('OSS_ENDPOINT', 'oss-cn-hongkong.aliyuncs.com')  # 提供默认值
        region = os.getenv('OSS_REGION', 'cn-hongkong')  # 提供默认值
        self.bucket_name = os.getenv('OSS_BUCKET', 'acofork-hk')  # 提供默认值

        # 检查必要的环境变量是否存在
        if not access_key_id or not access_key_secret:
            raise ValueError("ACCESS_KEY_ID and ACCESS_KEY_SECRET must be set as environment variables.")

        # 存储到实例变量
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.region = region

        print(f"Initialized OSSUploader with bucket: {self.bucket_name}, endpoint: {self.endpoint}")      # OSS配置

        
        # 创建认证对象
        auth = oss2.Auth(access_key_id, access_key_secret)
        
        # 创建存储桶对象
        self.bucket = oss2.Bucket(auth, endpoint, self.bucket_name, region=region)
        
        # 创建连接池
        self.client = httpx.Client(
            verify=False,
            follow_redirects=True,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=20)
        )
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=24)
        self.pbar = None

    def download_image(self, url, retries=3):
        """下载图片到内存，带重试"""
        headers = {
            'Referer': 'https://www.pixiv.net/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for attempt in range(retries):
            try:
                response = self.client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.content
            except Exception as e:
                if attempt == retries - 1:
                    print(f"\n下载失败 {url}: {str(e)}")
                    return None
                continue
        return None

    def calculate_progress(self, consumed_bytes, total_bytes):
        """使用tqdm显示进度"""
        if total_bytes and not self.pbar:
            self.pbar = tqdm(
                total=total_bytes,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="上传进度"
            )
        if self.pbar:
            self.pbar.n = consumed_bytes
            self.pbar.refresh()
            if consumed_bytes == total_bytes:
                self.pbar.close()
                self.pbar = None

    def upload_to_oss(self, image_data, object_name):
        """上传到OSS"""
        headers = {
            'x-oss-forbid-overwrite': 'true'
        }
        try:
            if self.pbar:
                self.pbar.close()
            self.pbar = None
            
            # 添加上传描述
            desc = f"上传 {object_name.split('/')[-1]}"
            
            self.pbar = tqdm(
                desc=desc,
                total=len(image_data),
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False,
                position=1
            )
            
            result = self.bucket.put_object(
                object_name,
                image_data,
                headers=headers,
                progress_callback=self.calculate_progress
            )
            return True
            
        except oss2.exceptions.OssError as e:
            if self.pbar:
                self.pbar.close()
            self.pbar = None
            
            error_code = getattr(e, 'code', '')
            if error_code == 'FileAlreadyExists':
                print(f"\n文件已存在: {object_name}")
                return True
            print(f"\n上传失败 {object_name}: {str(e)}")
            return False

    def process_json_file(self, json_file):
        """处理单个JSON文件，区分三种状态"""
        print(f"\n处理文件: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        # 统计初始状态
        json_skip_count = len([item for item in items if item['status'] == 1])
        pending_items = [item for item in items if item['status'] != 1]
        
        if not pending_items:
            print(f"所有文件已处理完成，跳过: {json_skip_count}")
            return 0, json_skip_count, 0, 0  # 新增一个返回值表示OSS已存在数
        
        # 创建任务列表
        tasks = []
        for item in pending_items:
            url = item['url']
            filename = url.split('/')[-1]
            object_name = f'pixiv/{filename}'
            tasks.append((url, object_name, item))
        
        batch_size = 24
        success_count = 0
        oss_exists_count = 0  # 新增：OSS中已存在的计数
        fail_count = 0
        
        with tqdm(total=len(tasks), desc="总进度", position=0) as pbar:
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                
                with ThreadPoolExecutor(max_workers=24) as executor:
                    futures = {
                        executor.submit(self.process_single_item, url, obj_name): (url, obj_name, item)
                        for url, obj_name, item in batch
                    }
                    
                    for future in as_completed(futures):
                        url, obj_name, item = futures[future]
                        try:
                            result = future.result()
                            if result == "success":
                                item['status'] = 1
                                success_count += 1
                            elif result == "exists":
                                item['status'] = 1
                                oss_exists_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            print(f"\n处理失败 {url}: {str(e)}")
                            fail_count += 1
                        finally:
                            pbar.update(1)
                
                # 每批次保存进度
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
        
        return success_count, json_skip_count, fail_count, oss_exists_count

    def process_single_item(self, url, object_name, pbar=None):
        """处理单个文件，返回具体状态"""
        try:
            image_data = self.download_image(url)
            if not image_data:
                return "fail"
                
            try:
                self.bucket.put_object(
                    object_name,
                    image_data,
                    headers={'x-oss-forbid-overwrite': 'true'}
                )
                return "success"
            except oss2.exceptions.OssError as e:
                error_code = getattr(e, 'code', '')
                if error_code == 'FileAlreadyExists':
                    return "exists"
                raise e
                
        except Exception as e:
            print(f"\n处理失败 {url}: {str(e)}")
            return "fail"

    def process_all_files(self):
        """处理所有JSON文件"""
        print(f"开始上传 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        
        total_success = 0
        total_json_skip = 0
        total_oss_exists = 0
        total_fail = 0
        
        img_dir = 'img'
        for filename in os.listdir(img_dir):
            if filename.endswith('.json'):
                json_file = os.path.join(img_dir, filename)
                success, json_skip, fail, oss_exists = self.process_json_file(json_file)
                total_success += success
                total_json_skip += json_skip
                total_fail += fail
                total_oss_exists += oss_exists
        
        print(f"\n上传完成 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"总统计:")
        print(f"  - 成功上传: {total_success}")
        print(f"  - JSON已存在: {total_json_skip}")
        print(f"  - OSS已存在: {total_oss_exists}")
        print(f"  - 处理失败: {total_fail}")
        print(f"  - 总计处理: {total_success + total_json_skip + total_oss_exists + total_fail}")

def main():
    import urllib3
    urllib3.disable_warnings()
    
    uploader = OSSUploader()
    uploader.process_all_files()

if __name__ == '__main__':
    main()
