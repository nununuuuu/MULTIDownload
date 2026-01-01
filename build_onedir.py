import os
import subprocess
import shutil
import sys

def build():
    # 強制設定 stdout/stderr 為 UTF-8，避免 GitHub Actions Windows Runner 編碼錯誤
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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

    # --- [New] 生成暫存日誌檔案 ui/changelog_gen.py ---
    print("Generating temporary log file: ui/changelog_gen.py ...")
    changelog_path = os.path.join(project_root, "CHANGELOG.md")
    gen_py_path = os.path.join(project_root, "ui", "changelog_gen.py")
    
    generated_file_created = False
    
    if os.path.exists(changelog_path):
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Escape triple quotes just in case
            content = content.replace('"""', r'\"\"\"')
            
            py_content = f'CHANGELOG_TEXT = """\n{content}\n"""'
            
            with open(gen_py_path, "w", encoding="utf-8") as f:
                f.write(py_content)
                
            generated_file_created = True
            print(f"★ Generated {gen_py_path} successfully.")
            
        except Exception as e:
            print(f"⚠ Error generating log file: {e}")
    else:
        print("⚠ Warning: CHANGELOG.md not found.")
    # ----------------------------------------------------

    print(f"專案根目錄: {project_root}")
    print(f"圖示目錄: {icon_dir}")

    # 1. 確保 PyInstaller 已安裝
    try:
        import PyInstaller
    except ImportError:
        print("未偵測到 PyInstaller，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    try:
        # 2. 定義 PyInstaller 指令
        hidden_imports = [
            "mutagen", "brotli", "certifi", "requests", "urllib3", "websockets", "sqlite3", "optparse", "email", "http.client", "http.cookies", "http.cookiejar",
            "xml.etree.ElementTree", "pycryptodomex", "Cryptodome", "ctypes", "curl_cffi", "hmac", "html", "html.entities", "html.parser", "http.server", "mimetypes",
            "typing", "fileinput", "inspect", "platform", "shlex", "textwrap", "difflib", "threading", "subprocess", "yt_dlp_ejs", "yt_dlp_ejs.yt", "yt_dlp_ejs.yt.solver", "secretstorage",
            "PIL", "PIL.Image", "PIL.ImageTk"
        ]
        
        cmd = [
            sys.executable, "-m", "PyInstaller", # Use full path to be safe
            "--noconfirm",
            "--onedir", # 資料夾模式
            "--windowed",
            "--clean",
            "--name", "MULTIDownload",
            "--exclude-module", "yt_dlp", # 核心排除
            
            # 資源打包
            f"--icon={app_icon}",
            f"--add-data={icon_dir};icon", 
            
            main_script
        ]

        # 添加 Hidden Imports
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])

        print(f"正在執行打包指令: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
    finally:
        # --- [Cleanup] 刪除暫存檔 ---
        if generated_file_created and os.path.exists(gen_py_path):
            try:
                os.remove(gen_py_path)
                print(f"★ Cleaned up temporary file: {gen_py_path}")
            except Exception as e:
                print(f"⚠ Failed to clean up temp file: {e}")
        # ----------------------------

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
    # [Fix] 來源改為 data/languages.json
    lang_file = os.path.join(project_root, "data", "languages.json")
    if os.path.exists(lang_file):
        data_dir = os.path.join(exe_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        shutil.copy(lang_file, data_dir)
        print(f"已複製: languages.json 到 dist/MULTIDownload/data/")
    else:
        print(f"⚠ 警告: 找不到 languages.json (路徑: {lang_file})")

    
    # [New] 自動複製 FFmpeg / FFprobe 到 bin 資料夾
    bin_dir = os.path.join(exe_dir, "bin")
    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)
        
    for bin_file in ["ffmpeg.exe", "ffprobe.exe"]:
        # [Fix] 來源改為 bin/ 資料夾
        src = os.path.join(project_root, "bin", bin_file)
        dst = os.path.join(bin_dir, bin_file)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"已複製: {bin_file} -> bin/")
        else:
            print(f"⚠ 警告: 找不到 {bin_file} (路徑: {src})")
    
    # 5. 完成提示
    print("\n" + "="*60)
    print(f"建置成功 (資料夾模式)！")
    print(f"程式資料夾: {exe_dir}")
    print(f"可執行檔: {exe_path}")
    print("-" * 60)
    print("請注意：")
    print("1. 此版本為 onedir 模式 (資料夾)，發布時需打包整個 'MULTIDownload' 資料夾。")
    print("2. 確保 ffmpeg.exe, ffprobe.exe 在 bin 資料夾中，與 languages.json 在 data 資料夾中。")
    print("3. yt-dlp 核心程式會在首次執行時下載至該資料夾。")
    print("="*60)

if __name__ == "__main__":
    build()
