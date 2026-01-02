
import importlib
import sys

hidden_imports = [
    "mutagen", "brotli", "certifi", "requests", "urllib3", "websockets", "sqlite3", "optparse", "email", "http.client", "http.cookies", "http.cookiejar",
    "xml.etree.ElementTree", "pycryptodomex", "ctypes", "curl_cffi", "hmac", "html", "html.entities", "html.parser", "http.server", "mimetypes",
    "typing", "fileinput", "inspect", "platform", "shlex", "textwrap", "difflib", "threading", "subprocess", "yt_dlp_ejs", "yt_dlp_ejs.yt", "yt_dlp_ejs.yt.solver", "secretstorage",
    "PIL", "PIL.Image", "PIL.ImageTk"
]

print(f"{'Module Name':<30} | {'Status':<10}")
print("-" * 45)

missing_count = 0
for module_name in hidden_imports:
    # 特殊處理: Cryptodome 實際上是 pycryptodomex (import Cryptodome)
    # pytube 也是可能有別名，但這裡依照 list 檢查
    
    check_name = module_name
    if module_name == "pycryptodomex":
        check_name = "Cryptodome" # 實際 import 名稱
        
    try:
        importlib.import_module(check_name)
        status = "✅ OK"
    except ImportError:
        status = "❌ Missing"
        missing_count += 1
    
    print(f"{module_name:<30} | {status}")

print("-" * 45)
if missing_count == 0:
    print("★ 所有 Hidden Imports 皆已安裝！")
else:
    print(f"⚠ 發現 {missing_count} 個模組缺失，請檢查。")
    print("注意：sqlite3, email, http... 等為內建模組，理論上不應缺失 (除非 Python 直譯器異常)。")
