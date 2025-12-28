import os
import subprocess
import shutil
import sys

def build():
    # 0. 環境準備
    project_root = os.path.dirname(os.path.abspath(__file__))
    icon_dir = os.path.join(project_root, "icon")
    main_script = os.path.join(project_root, "main.py")
    app_icon = os.path.join(icon_dir, "1.ico")
    
    # --- [New] 自動更新版本號 ---
    import datetime
    import re
    
    new_ver = datetime.datetime.now().strftime("%Y.%m.%d")
    const_file = os.path.join(project_root, "constants.py")
    
    if os.path.exists(const_file):
        try:
            with open(const_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 尋找 APP_VERSION = "..." 並替換
            new_content = re.sub(r'APP_VERSION\s*=\s*["\'].*?["\']', f'APP_VERSION = "{new_ver}"', content)
            
            if content != new_content:
                with open(const_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"★ 已自動更新版本號為: {new_ver}")
            else:
                print(f"版本號已是最新: {new_ver}")
        except Exception as e:
            print(f"⚠ 更新版本號失敗: {e}")
    # ----------------------------

    # --- [New] 自動注入 CHANGELOG 到 ui/layout.py ---
    print("Injecting CHANGELOG.md into ui/layout.py...")
    changelog_path = os.path.join(project_root, "CHANGELOG.md")
    layout_path = os.path.join(project_root, "ui", "layout.py")
    
    if os.path.exists(changelog_path) and os.path.exists(layout_path):
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_content = f.read()
            
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_code = f.read()
            
            # 定義標記
            start_marker = "# <CHANGELOG_INJECTION_START>"
            end_marker = "# <CHANGELOG_INJECTION_END>"
            
            # 尋找位置並替換
            # 使用 Regex 進行非貪婪匹配，將標記之間的內容替換為新的 CHANGELOG 字串
            pattern_str = f"({re.escape(start_marker)}).*?({re.escape(end_marker)})"
            
            # 準備替換內容：
            # 為了保持 Python 代碼美觀，我們給每一行加上 12 空格的縮排 (配合 layout.py 中的縮排層級)
            indent = "            "
            escaped_content = changelog_content.replace('"""', r'\"\"\"') 
            indented_content = "\n".join([indent + line for line in escaped_content.splitlines()])
            
            # 替換的目標字串：Start標記 + 換行 + 縮排的賦值語句 + 換行 + 縮排 + End標記
            replacement = (
                f"\\1\n"
                f"{indent}CHANGELOG_TEXT = \"\"\"\n"
                f"{indented_content}\n"
                f"{indent}\"\"\"\n"
                f"{indent}\\2"
            )
            
            # 執行正則替換
            new_layout_code, count = re.subn(pattern_str, replacement, layout_code, flags=re.DOTALL)
            
            if count > 0:
                with open(layout_path, "w", encoding="utf-8") as f:
                    f.write(new_layout_code)
                print("★ Successfully injected CHANGELOG into ui/layout.py source code.")
            else:
                print("⚠ Warning: Injection markers not found in layout.py. Skipping injection.")
                
        except Exception as e:
            print(f"⚠ Error injecting changelog: {e}")
    else:
        print("⚠ Warning: CHANGELOG.md or ui/layout.py not found.")
    # ----------------------------------------------------



    print(f"專案根目錄: {project_root}")
    print(f"圖示目錄: {icon_dir}")

    # 1. 確保 PyInstaller 已安裝
    try:
        import PyInstaller
    except ImportError:
        print("未偵測到 PyInstaller，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 定義 PyInstaller 指令
    hidden_imports = [
        "mutagen", "brotli", "certifi", "requests", "urllib3", "websockets", "sqlite3", "optparse", "email", "http.client", "http.cookies", "http.cookiejar",
        "xml.etree.ElementTree", "pycryptodomex", "Cryptodome", "ctypes", "curl_cffi", "hmac", "html", "html.entities", "html.parser", "http.server", "mimetypes",
        "typing", "fileinput", "inspect", "platform", "shlex", "textwrap", "difflib", "threading", "subprocess", "yt_dlp_ejs", "yt_dlp_ejs.yt", "yt_dlp_ejs.yt.solver", "secretstorage",
        "PIL", "PIL.Image", "PIL.ImageTk"
    ]

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir", # 資料夾模式
        "--windowed",
        "--clean",
        "--name", "MULTIDownload",
        "--exclude-module", "yt_dlp", # 核心排除
        
        # 資源打包
        f"--icon={app_icon}",
        f"--add-data={icon_dir};icon", # 將 icon 資料夾完整打包至輸出目錄的 icon 資料夾
        
        main_script
    ]

    # 添加 Hidden Imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    print(f"正在執行打包指令: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("PyInstaller 打包完成！開始後處理...")
    
    # 3. 整理輸出檔案
    dist_dir = os.path.join(project_root, "dist")
    exe_dir = os.path.join(dist_dir, "MULTIDownload") # onedir 模式下，這是主資料夾
    exe_path = os.path.join(exe_dir, "MULTIDownload.exe")
    
    if not os.path.exists(exe_path):
        print(f"錯誤：EXE 檔案未生成 (路徑: {exe_path})")
        return

    # 4. 複製必要外部檔案
    # 4. 複製必要外部檔案
    # languages.json -> data/languages.json
    lang_file = os.path.join(project_root, "languages.json")
    if os.path.exists(lang_file):
        data_dir = os.path.join(exe_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        shutil.copy(lang_file, data_dir)
        print(f"已複製: languages.json 到 dist/MULTIDownload/data/")

    
    # [New] 自動複製 FFmpeg / FFprobe 到 bin 資料夾
    bin_dir = os.path.join(exe_dir, "bin")
    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)
        
    for bin_file in ["ffmpeg.exe", "ffprobe.exe"]:
        src = os.path.join(project_root, bin_file)
        dst = os.path.join(bin_dir, bin_file)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"已複製: {bin_file} -> bin/")
        else:
            print(f"⚠ 警告: 找不到 {bin_file} (建議手動補入 bin 資料夾)")
    
    # 5. 完成提示
    print("\n" + "="*60)
    print(f"建置成功 (資料夾模式)！")
    print(f"程式資料夾: {exe_dir}")
    print(f"可執行檔: {exe_path}")
    print("-" * 60)
    print("請注意：")
    print("1. 此版本為 onedir 模式 (資料夾)，發布時需打包整個 'MULTIDownload' 資料夾。")
    print("2. 確保 ffmpeg.exe, ffprobe.exe在bin資料夾中，與 languages.json 在此目錄中。")
    print("3. yt-dlp 核心程式會在首次執行時下載至該資料夾。")
    print("="*60)

if __name__ == "__main__":
    build()
