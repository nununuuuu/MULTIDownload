import os
import subprocess
import shutil
import sys

def build():
    # 1. 確保 PyInstaller 已安裝
    try:
        import PyInstaller
    except ImportError:
        print("未偵測到 PyInstaller，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 定義 PyInstaller 指令
    # --onefile: 單一 EXE
    # --windowed: 無黑窗 (GUI)
    # --clean: 清理緩存
    # --exclude-module yt_dlp: 排除 yt-dlp (讓使用者自己下載)
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--clean",
        "--name", "MULTIDownload",
        "--exclude-module", "yt_dlp", # 排除內建 yt-dlp
        
        # 強制包含 yt-dlp 的依賴套件 (避免 exclude yt_dlp 後連帶遺失這些)
        "--hidden-import", "mutagen",
        "--hidden-import", "brotli",
        "--hidden-import", "certifi",
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "websockets",
        "--hidden-import", "sqlite3",
        "--hidden-import", "optparse",
        "--hidden-import", "email",
        "--hidden-import", "http.client",
        "--hidden-import", "http.cookies",
        "--hidden-import", "http.cookiejar",
        "--hidden-import", "xml.etree.ElementTree",
        "--hidden-import", "pycryptodomex",
        "--hidden-import", "Cryptodome",
        "--hidden-import", "ctypes",
        "--hidden-import", "curl_cffi",
        "--hidden-import", "hmac",
        "--hidden-import", "html",
        "--hidden-import", "html.entities",
        "--hidden-import", "html.parser",
        "--hidden-import", "http.server",
        "--hidden-import", "mimetypes",
        "--hidden-import", "typing",
        "--hidden-import", "fileinput",
        "--hidden-import", "inspect",
        "--hidden-import", "platform",
        "--hidden-import", "shlex",
        "--hidden-import", "textwrap",
        "--hidden-import", "difflib",
        "--hidden-import", "threading",
        "--hidden-import", "subprocess",
        "--hidden-import", "yt_dlp_ejs",
        "--hidden-import", "yt_dlp_ejs.yt",
        "--hidden-import", "yt_dlp_ejs.yt.solver", # Patch deeper nest
        "--hidden-import", "secretstorage",
        
        "--icon", r"C:\mypython\MULTIDownload\icon\1.ico",
        "--add-data", r"C:\mypython\MULTIDownload\icon\1.ico;.",
        # 排除 ffmpeg (雖然通常不會自動包進去，但明確排除也好，或只是不加入 binary)
        "main.py"
    ]

    print(f"正在執行打包指令: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("打包完成！")
    
    # 3. 整理輸出檔案
    dist_dir = "dist"
    # 在 onedir 模式下，EXE 位於 dist/MULTIDownload/MULTIDownload.exe
    exe_dir = os.path.join(dist_dir, "MULTIDownload") 
    exe_path = os.path.join(exe_dir, "MULTIDownload.exe")
    
    if not os.path.exists(exe_path):
        print(f"錯誤：EXE 檔案未生成 (路徑: {exe_path})")
        return

    # 4. 複製必要外部檔案 (languages.json)
    # 複製到 exe 所在的資料夾
    files_to_copy = ["languages.json"]
    
    for f in files_to_copy:
        if os.path.exists(f):
            shutil.copy(f, exe_dir)
            print(f"已複製: {f} 到 {exe_dir}")

    # 5. 提示使用者
    print("\n" + "="*50)
    print(f"建置成功！程式位於: {os.path.abspath(exe_dir)}")
    print("請注意：")
    print("1. ffmpeg.exe 與 ffprobe.exe 需手動放入該資料夾 (或確認環境變數)")
    print("2. 首次執行程式時，請至「設定」頁面點擊「檢查並更新 yt-dlp」以安裝下載核心")
    print("="*50)

if __name__ == "__main__":
    build()
