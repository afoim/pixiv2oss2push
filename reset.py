import json
import os

def reset_status():
    """重置所有JSON文件中的status值为0"""
    img_dir = 'img'
    if not os.path.exists(img_dir):
        print("img目录不存在")
        return
        
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(img_dir) if f.endswith('.json')]
    if not json_files:
        print("没有找到JSON文件")
        return
        
    total_reset = 0
    
    print("开始重置状态...")
    for json_file in json_files:
        file_path = os.path.join(img_dir, json_file)
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
            
        reset_count = 0
        # 重置所有status为0
        for item in items:
            if item['status'] != 0:
                item['status'] = 0
                reset_count += 1
                
        # 保存修改
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            
        total_reset += reset_count
        print(f"重置 {json_file}: {reset_count} 个状态")
    
    print(f"\n完成重置")
    print(f"总计重置: {total_reset} 个状态")

if __name__ == "__main__":
    reset_status()
