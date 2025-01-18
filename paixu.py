import re
import sys

def sort_urls(file_path):
    with open(file_path, 'r') as file:
        urls = file.readlines()

    # 删除 URL 中的 /c/240x480
    urls = [url.strip().replace('/c/240x480', '') for url in urls]

    # 对 URL 进行排序
    def sort_key(url):
        match = re.search(r'img/(\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2})/(\d+)_p(\d+)_master1200\.jpg', url)
        if match:
            date, id, page = match.groups()
            return (date, int(id), int(page))
        return url

    urls.sort(key=sort_key)

    # 将排序后的 URL 写回文件
    with open(file_path, 'w') as file:
        for url in urls:
            file.write(url + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python paixu.py <file_path>")
    else:
        sort_urls(sys.argv[1])
