import sys
import os
import webbrowser
import threading
import time
from backend.main import app
import uvicorn

def open_browser():
    """等待服务器启动后打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open('http://localhost:8000')

def main():
    # 设置工作目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        os.chdir(os.path.dirname(sys.executable))
    else:
        # 如果是直接运行 Python 脚本
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 启动浏览器线程
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main() 