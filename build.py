import os

def read_links(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def generate_image_items(links):
    items = []
    for link in links:
        items.append(f'  <div class="grid-item">\n    <img src="{link}"  loading="lazy">\n  </div>')
    return '\n'.join(items)

def update_html(template_path, output_path, image_items):
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到图片部分的开始和结束位置
    start_marker = '<div class="grid-sizer"></div>'
    end_marker = '</div>\n\n<!-- External JS Libraries'
    
    # 分割内容
    start_part = content.split(start_marker)[0] + start_marker + '\n'
    end_part = content.split(end_marker)[1]
    
    # 组合新的内容
    new_content = start_part + image_items + '\n' + end_marker + end_part
    
    # 写入新文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    # 设置文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    links_path = os.path.join(current_dir, 'static', 'oss_link.txt')
    template_path = os.path.join(current_dir, 'static', 'ori.html')
    output_path = os.path.join(current_dir, 'static', 'index.html')
    
    # 读取链接
    links = read_links(links_path)
    
    # 生成图片项
    image_items = generate_image_items(links)
    
    # 更新HTML文件
    update_html(template_path, output_path, image_items)
    
    print(f"已成功生成新的HTML文件: {output_path}")

if __name__ == '__main__':
    main()
