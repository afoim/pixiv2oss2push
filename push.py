import json
import os
from bs4 import BeautifulSoup

class GalleryGenerator:
    def __init__(self):
        self.oss_domain = 'https://aliyun-oss.onani.cn'
        self.categories = ['monthly', 'weekly', 'daily', 'rookie', 'original', 'daily_ai']
        self.images_by_category = {}

    def convert_url(self, pixiv_url):
        """将Pixiv URL转换为OSS URL"""
        filename = pixiv_url.split('/')[-1]
        return f"{self.oss_domain}/pixiv/{filename}"

    def load_images(self):
        """从所有JSON文件加载图片，并按照ID倒序排序"""
        for category in self.categories:
            json_path = f'img/{category}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    urls = [self.convert_url(item['url']) 
                           for item in data if item['status'] == 1]
                    
                    # 提取ID并按照数字大小倒序排序（最新的ID最大）
                    def get_id(url):
                        # 从URL中提取ID数字
                        return int(url.split('/')[-1].split('_')[0])
                    
                    self.images_by_category[category] = sorted(urls, 
                                                             key=get_id, 
                                                             reverse=True)

    def generate_html(self):
        """基于模板生成HTML页面"""
        # 确保static目录存在
        os.makedirs('static', exist_ok=True)
        
        # 读取原始模板
        template_path = 'static/ori.html'
        if not os.path.exists(template_path):
            print("错误: 未找到模板文件 static/ori.html")
            return
            
        # 读取模板并创建新的index.html
        with open(template_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        # 为每个分类添加图片
        for category in self.categories:
            container = soup.find('div', id=category)
            if container:
                # 清空现有内容
                container.clear()
                
                # 添加新的图片
                for url in self.images_by_category.get(category, []):
                    img_div = soup.new_tag('div', attrs={'class': 'item'})
                    link = soup.new_tag('a', href=url, target='_blank')
                    img = soup.new_tag('img', src=url, alt='pixiv image', loading='lazy')
                    link.append(img)
                    img_div.append(link)
                    container.append(img_div)
        
        # 直接保存为index.html
        with open('static/index.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        
        print(f"生成完成: static/index.html")
        print(f"图片统计:")
        for category, images in self.images_by_category.items():
            print(f"  - {category}: {len(images)} 张")

def main():
    generator = GalleryGenerator()
    generator.load_images()
    generator.generate_html()

if __name__ == '__main__':
    main()
