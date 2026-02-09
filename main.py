import sys
import os

# ====================================================================
# [Priority] 優先使用 lib 資料夾內的套件版本
# 必須在所有其他導入之前執行，確保 yt_dlp 等核心套件使用正確版本
# ====================================================================
if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

lib_path = os.path.join(app_path, "lib")
if os.path.isdir(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)
    print(f"[Lib] 優先使用 lib 資料夾: {lib_path}")

# ====================================================================
# 標準導入
# ====================================================================
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from core import YtDlpCore
import threading
import uuid
import time 
from datetime import datetime, timedelta
import webbrowser
import requests 
import io
import zipfile
import shutil
from PIL import Image

import json
from tkinterdnd2 import TkinterDnD, DND_ALL

# Refactored Imports
from constants import APP_VERSION, GITHUB_REPO, DEFAULT_APPEARANCE_MODE, CODE_TO_NAME
from ui.layout import AppLayoutMixin
from ui.tasks import TaskLayoutMixin
from ui.tooltip import CTkToolTip
from ui.custom_titlebar import setup_custom_titlebar # [UI] Import Title Bar Logic

ctk.set_default_color_theme("blue")

# 嘗試載入 yt_dlp (應該已經從 lib 優先載入)
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from ui.dialogs import PlaylistSelectionDialog

class App(ctk.CTk, TkinterDnD.DnDWrapper, AppLayoutMixin, TaskLayoutMixin):
    setup_custom_titlebar = setup_custom_titlebar # [UI] Attach Method

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self) # Init TkinterDnD
        self.title("MULTIDownload")
        self.geometry("900x780") 
        
        # [Anti-Flicker] 啟動時完全透明，避免渲染過程被看見
        self.attributes("-alpha", 0.0) 
        
        # 設定應用程式圖示 (Runtime Icon)
        try:
            icon_candidates = []
            
            # 1. 打包後的內部資源 (_MEIPASS)
            if hasattr(sys, '_MEIPASS'):
                icon_candidates.append(os.path.join(sys._MEIPASS, "icon", "1.ico"))
                icon_candidates.append(os.path.join(sys._MEIPASS, "1.ico"))
            
            # 2. 執行檔所在目錄 (OneDir 模式)
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_candidates.append(os.path.join(exe_dir, "1.ico"))
            icon_candidates.append(os.path.join(exe_dir, "icon", "1.ico"))
            
            # 3. 開發環境絕對路徑
            icon_candidates.append(r"C:\mypython\MULTIDownload\icon\1.ico")
            
            final_icon_path = None
            for p in icon_candidates:
                if os.path.exists(p):
                    final_icon_path = p
                    break
                    
            if final_icon_path:
                self.iconbitmap(final_icon_path)
            else:
                print("Warning: Icon file not found.")
                
        except Exception as e: 
            print(f"Set Icon Error: {e}") 
        
        # --- Theme Initialization (Pre-read to avoid flicker) ---
        temp_theme = DEFAULT_APPEARANCE_MODE
        try:
            temp_data_dir = os.path.join(app_path, "data")
            temp_cfg = os.path.join(temp_data_dir, "config.json")
            if os.path.exists(temp_cfg):
                with open(temp_cfg, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if "theme" in saved:
                    temp_theme = saved["theme"]
        except: pass
    
        ctk.set_appearance_mode(temp_theme)
        
        self.font_family = "Microsoft JhengHei UI" if sys.platform.startswith("win") else "PingFang TC"
        self.font_title = (self.font_family, 14, "bold")
        self.font_sidebar_icon = (self.font_family, 18, "bold") 
        self.font_text = (self.font_family, 12)
        self.font_btn = (self.font_family, 14, "bold") 
        self.font_small = (self.font_family, 11)
        
        # 初始化
        self.core = YtDlpCore()
        self.downloading = False 
        self.download_queue = [] 
        self.active_queue_tasks = {}
        self.last_loaded_subtitles = None 
        self.max_concurrent_downloads = 1 
        self.bg_tasks = {}       

        # --- Layout Logic: 2 rows (TitleBar | Content), 2 cols (Static Sidebar | Content) ---
        self.grid_rowconfigure(0, weight=0) # Row 0: Title Bar
        self.grid_rowconfigure(1, weight=1) # Row 1: Content
        self.grid_columnconfigure(0, minsize=60) 
        self.grid_columnconfigure(1, weight=1)   

        # [UI] 建立自定義標題列
        self.setup_custom_titlebar()
        
        # [Anti-Flicker] 監聽視窗顯示/恢復事件，解決最小化還原時的白底閃爍
        self.bind("<Map>", self._handle_window_restore)
        # [Anti-Flicker] 監聽視窗隱藏事件（最小化前），預先設置透明度
        self.bind("<Unmap>", self._handle_window_hide)

        # 1. Sidebar Frame (Static) -> Row 1
        self.sidebar_frame = ctk.CTkFrame(self, width=60, corner_radius=0)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew") # Grid to Row 1
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # 2. Main Content Area -> Row 1
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=1, column=1, sticky="nsew", padx=10, pady=10) # Grid to Row 1
        self.main_view.grid_rowconfigure(0, weight=1)     
        self.main_view.grid_rowconfigure(1, weight=0)      
        self.main_view.grid_columnconfigure(0, weight=1)

        # 3. Content Container
        self.frames = {}
        for name in ["Basic", "Format", "Live", "Sub", "Output", "Adv", "Tasks", "Log", "Settings", "About"]:
             frame = ctk.CTkFrame(self.main_view, corner_radius=10, fg_color=None)
             self.frames[name] = frame
        
        self.tab_basic = self.frames["Basic"]
        self.tab_format = self.frames["Format"]
        self.tab_live = self.frames["Live"]
        self.tab_sub = self.frames["Sub"]
        self.tab_output = self.frames["Output"]
        self.tab_adv = self.frames["Adv"]
        self.tab_tasks = self.frames["Tasks"]
        self.tab_log = self.frames["Log"]
        self.tab_settings = self.frames["Settings"]
        self.tab_about = self.frames["About"]

        self.history_data = [] 
        self.active_task_widgets = {}
        self.selected_playlist_data = [] 
        self.pending_playlist_info = None 
        self.last_fetched_info = None 
        
        # 4. Initialize UI (From Mixins)
        self.setup_sidebar()

        # 5. Setup Content UI (From Mixins)
        self.setup_tasks_ui() 
        self.setup_basic_ui()
        self.task_last_update_time = {}
        self.setup_format_ui()
        self.setup_live_ui()
        self.setup_subtitle_ui()
        self.setup_output_ui()
        self.setup_advanced_ui()
        self.setup_log_ui()
        self.setup_settings_ui()
        self.setup_about_ui()

        # --- Pre-load ALL Layouts (Stacking Strategy) ---
        # 將所有頁面全部 grid 上去並疊加，解決切換閃爍
        for f_name, f_frame in self.frames.items():
            f_frame.grid(row=0, column=0, sticky="nsew")
        
        # 強制初始排版計算
        self.update_idletasks()

        # --- 6. 建立底部控制區 (From Mixin) ---
        self.setup_bottom_controls()
        
        # Default view (此時會將 Basic 移到最上層)
        self.select_frame("Basic")
        
        # Global Click Binding to dismiss focus
        self.bind("<Button-1>", self._bg_click_handler)
        
        # --- Drag & Drop ---
        self.drop_target_register(DND_ALL)
        self.dnd_bind('<<Drop>>', self._on_drop)
        

        self.data_dir = os.path.join(app_path, "data")
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
            except Exception as e:
                print(f"Error creating data dir: {e}")
        
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.load_config()
        
        self.after(1000, self.check_core_library)

        # 硬體加速偵測
        self.detected_gpu = None
        self.check_hardware_acceleration()

        # 啟動自動更新檢查 (延遲 2 秒，避免影響啟動速度)
        self.after(2000, lambda: self.check_app_update(silent=True))
        
        # 啟動核心組件 (yt-dlp) 背景更新檢查
        self.after(5000, self.check_core_update_silent)
        
        # 啟動監聽迴圈 (剪貼簿)
        self.last_clipboard_content = ""
        self.after(1000, self._monitoring_loop)

        # 啟動排程檢查
        self.after(3000, self._scheduler_loop)

        # [Anti-Flicker] 所有 UI 已構建完成，等待充足時間確保完全渲染後再啟動淡入動畫
        self.after(300, self._fade_in_window)

    def check_hardware_acceleration(self):
        def _task():
            # 使用 core 的靜態能力偵測
            accels = self.core.get_available_hw_accel()
            try:
                self.after(0, lambda: self._update_hw_ui(accels))
            except RuntimeError:
                # 視窗已關閉，忽略
                pass
        threading.Thread(target=_task, daemon=True).start()



    def load_config(self):
        """讀取設定檔並應用到 UI"""
        self.is_loading_config = True  # 暫時禁止 Toast
        
        default_config = {
            "save_path": "",
            "cookie_mode": "none",
            "user_agent": "",
            "max_concurrent": 1,
            "remember_proxy": False,  
            "proxy": ""               
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except: pass

        # 1. Path
        if default_config["save_path"] and os.path.exists(default_config["save_path"]):
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, default_config["save_path"])
        
        # 2. Cookie Mode
        mode = default_config["cookie_mode"]
        if hasattr(self, 'var_cookie_mode'):
            self.var_cookie_mode.set(mode)
            if hasattr(self, 'on_cookie_mode_change'): 
                self.on_cookie_mode_change()
                # 更新按鈕視覺狀態
                if hasattr(self, '_update_browser_visuals'):
                    self.after(100, self._update_browser_visuals)
                # 更新貼上模式狀態
                if mode == 'paste' and hasattr(self, '_update_paste_status'):
                    self.after(150, self._update_paste_status)

        # 3. User Agent
        ua = default_config["user_agent"]
        if ua and hasattr(self, 'entry_ua'):
            self.entry_ua.delete(0, "end")
            self.entry_ua.insert(0, ua)
            
        # 4. Concurrent
        conc = default_config["max_concurrent"]
        if hasattr(self, 'combo_concurrent'):
            self.combo_concurrent.set(str(conc))
            self.max_concurrent_downloads = int(conc)
            
        # 5. Proxy [New]
        if hasattr(self, 'var_remember_proxy'):
            should_remember = default_config["remember_proxy"]
            self.var_remember_proxy.set(should_remember)
            
            if should_remember and default_config["proxy"]:
                self.entry_proxy.delete(0, "end")
                self.entry_proxy.insert(0, default_config["proxy"])

        # 6. SponsorBlock
        if hasattr(self, 'var_sponsorblock'):
            self.var_sponsorblock.set(default_config.get("sponsorblock", False))
            
        if hasattr(self, 'sb_vars'):
            saved_cats = default_config.get("sponsor_cats_list", ["all"])
            is_legacy_all = 'all' in saved_cats
            for k, var in self.sb_vars.items():
                if is_legacy_all: var.set(True)
                else: var.set(k in saved_cats)

        # 7. Hardware Accel
        if hasattr(self, 'var_hardware_accel'):
             hw_val = default_config.get("hardware_accel", "不使用 (CPU)")
             should_enable = (hw_val != "不使用 (CPU)")
             self.var_hardware_accel.set(should_enable)
        
        # 8. Search Limit
        if hasattr(self, 'var_search_limit'):
             self.var_search_limit.set(default_config.get("search_limit", 20))

        # 9. Extra Settings
        if hasattr(self, 'var_auto_start'): self.var_auto_start.set(default_config.get("auto_start_tasks", False))
        if hasattr(self, 'var_clipboard'): self.var_clipboard.set(default_config.get("monitor_clipboard", False))
        if hasattr(self, 'var_notification'): self.var_notification.set(default_config.get("enable_notification", True))
        if hasattr(self, 'var_auto_update'): self.var_auto_update.set(default_config.get("auto_update", True))
        
        # Theme
        theme = default_config.get("theme", "System")
        self.user_selected_theme = theme
        ctk.set_appearance_mode(theme)
        
        self.after(500, lambda: setattr(self, 'is_loading_config', False))  # 延遲恢復 Toast 以確保 UI 穩定

    def save_config(self):
        """儲存當前設定到檔案"""
        try:
            # Proxy Logic
            proxy_val = ""
            remember_proxy = False
            if hasattr(self, 'var_remember_proxy'):
                remember_proxy = self.var_remember_proxy.get()
                if remember_proxy:
                    proxy_val = self.entry_proxy.get().strip()
            
            # SponsorBlock List
            sb_list = ['all']
            if hasattr(self, 'sb_vars'):
                sb_list = [k for k, v in self.sb_vars.items() if v.get()]
            
            # Hardware Accel
            hw_val = "不使用 (CPU)"
            if hasattr(self, 'var_hardware_accel') and self.var_hardware_accel.get():
                hw_val = self.detected_gpu if self.detected_gpu else "自動"

            data = {
                "save_path": self.entry_path.get().strip(),
                "cookie_mode": self.var_cookie_mode.get(),
                "user_agent": self.entry_ua.get().strip(),
                "max_concurrent": self.max_concurrent_downloads,
                "remember_proxy": remember_proxy,
                "proxy": proxy_val,
                "sponsorblock": self.var_sponsorblock.get() if hasattr(self, 'var_sponsorblock') else False,
                "sponsor_cats_list": sb_list,
                "hardware_accel": hw_val,
                "auto_start_tasks": self.var_auto_start.get() if hasattr(self, 'var_auto_start') else False,
                "monitor_clipboard": self.var_clipboard.get() if hasattr(self, 'var_clipboard') else False,
                "enable_notification": self.var_notification.get() if hasattr(self, 'var_notification') else True,
                "auto_update": self.var_auto_update.get() if hasattr(self, 'var_auto_update') else True,
                "search_limit": self.var_search_limit.get() if hasattr(self, 'var_search_limit') else 20,
                "theme": getattr(self, "user_selected_theme", "System")
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save Config Error: {e}")

    # Hook into update events to auto-save
    def on_path_change(self, event=None):
        self.save_config()
        
    def _bg_click_handler(self, event):
        """點擊空白處取消輸入框焦點"""
        # 如果點擊的是輸入框本身 (Entry/Text)，不做動作
        if isinstance(event.widget, (tk.Entry, tk.Text, ctk.CTkEntry)):
            return
        
        # 檢查 class name 字串 (因為 CTk 元件底層可能是 Entry)
        try:
            if hasattr(event.widget, 'winfo_class'):
                cls = event.widget.winfo_class()
                if "Entry" in cls or "Text" in cls:
                    return
        except: pass
            
        self.focus()

    def _on_drop(self, event):
        """處理拖曳事件 (Drop Handler)"""
        data = event.data
        if not data: return
        
        # 處理資料 (移除大括號 {}) - Windows DnD 有時會將內容包在大括號中
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
            
        # 預處理: 簡單修復缺少的 protocol
        def fix_url(text):
            text = text.strip()
            # 1. Special case for youtube.com (force www)
            if text.startswith("youtube.com"):
                return "https://www." + text
            
            # 2. General case: Add https:// if protocol is missing
            if not text.startswith("http://") and not text.startswith("https://"):
                return "https://" + text
            
            return text

        data = fix_url(data)

        # 簡單驗證是否為 URL
        if not (data.startswith("http://") or data.startswith("https://")):
            # 嘗試過濾 (例如拖曳多個檔案時取第一個非空白行?)
            lines = data.split('\n')
            found = False
            for line in lines:
               line = fix_url(line)
               if line.startswith("http://") or line.startswith("https://"):
                   data = line
                   found = True
                   break
            if not found:
                 self.show_toast("僅支援網址拖曳", duration=2000, color="gray30")
                 return
        
        self.log(f"[拖曳] 偵測到網址: {data}")
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, data)
        self.on_fetch_info() # 自動執行分析 (但不直接下載，讓使用者確認)

    def safe_open_path(self, path):
         if os.path.exists(path): os.startfile(path)
         else: messagebox.showerror("錯誤", f"找不到路徑:\n{path}")

    def _get_cookie_path_for_mode(self):
        """根據 Cookie 模式取得正確的路徑"""
        mode = self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none'
        
        if mode == 'file':
            return self.entry_cookie_path.get().strip()
        elif mode == 'paste':
            # 貼上模式使用 data 目錄下的固定檔案
            return os.path.join(self.data_dir, "pasted_cookies.txt")
        else:
            return ""

    def on_fetch_info(self):
        text = self.entry_url.get().strip()
        if not text: return messagebox.showerror("錯誤", "請輸入網址或關鍵字")
        
        # [New] 智能判斷：URL 或關鍵字
        url_indicators = ["http://", "https://", "youtu.be", "bilibili", "b23.tv", ".com/", ".tv/", "watch?v="]
        is_url = any(indicator in text.lower() for indicator in url_indicators)
        
        if not is_url:
            # 觸發 YouTube 搜尋
            self._trigger_search(text)
            return
        
        url = text
        
        # Get UA & Cookie & Proxy safely
        ua = self.entry_ua.get().strip() if hasattr(self, 'entry_ua') else None
        proxy = self.entry_proxy.get().strip() if hasattr(self, 'entry_proxy') else None
        
        c_type = self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none'
        c_path = self._get_cookie_path_for_mode()

        # Playlist Detection
        # Enhanced detection for YouTube (list=) and Bilibili (series, season, collection, cb, etc.)
        is_generic_list = "list=" in url
        is_bili_list = "bilibili" in url and any(x in url for x in ["series", "season", "collection", "cb", "favlist"])
        
        if is_generic_list or is_bili_list:
            is_playlist = messagebox.askyesno("播放清單偵測", "偵測到此網址包含播放清單\n\n是否要下載『整張歌單』\n(選擇「否」將僅下載此影片)")
            self.var_playlist.set(is_playlist)
            
            if is_playlist:
                 self.show_toast("清單讀取中... ", duration=3000, color="#505050")
                 self.log(f"正在分析播放清單: {url}")
                 self.selected_playlist_data = []
                 threading.Thread(target=self._run_playlist_check, args=(url, c_type, c_path, ua, proxy), daemon=True).start()
                 return

        self.show_toast("正在分析字幕...", color="#505050")
        self.log(f"正在分析: {url}")
        self.update_thumbnail(None) # Reset thumbnail
        threading.Thread(target=self._run_fetch, args=(url, c_type, c_path, ua, proxy), daemon=True).start()

    def _trigger_search(self, query):
        """觸發 YouTube 搜尋"""
        self.show_toast(f"正在搜尋：{query}...", duration=5000, color="#1F6AA5")
        self.log(f"搜尋 YouTube: {query}")
        
        # 取得設定
        ua = self.entry_ua.get().strip() if hasattr(self, 'entry_ua') else None
        proxy = self.entry_proxy.get().strip() if hasattr(self, 'entry_proxy') else None
        c_type = self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none'
        c_path = self._get_cookie_path_for_mode()
        
        threading.Thread(
            target=self._run_search, 
            args=(query, c_type, c_path, ua, proxy), 
            daemon=True
        ).start()

    def _run_search(self, query, c_type, c_path, ua, proxy):
        """背景執行搜尋"""
        limit = self.var_search_limit.get() if hasattr(self, 'var_search_limit') else 20
        result = self.core.search_videos(
            query, 
            max_results=limit, 
            cookie_type=c_type, 
            cookie_path=c_path,
            user_agent=ua, 
            proxy=proxy
        )
        
        # 回到主線程處理結果
        self.after(0, lambda: self._on_search_complete(query, result))

    def _on_search_complete(self, query, result):
        """搜尋完成後顯示彈窗"""
        if 'error' in result and result['error']:
            self.show_toast(f"搜尋失敗: {result['error']}", color="#D93025")
            self.log(f"搜尋錯誤: {result['error']}")
            return
        
        results = result.get('results', [])
        
        if not results:
            self.show_toast("找不到相關影片", color="#F29900")
            self.log(f"搜尋 '{query}' 無結果")
            return
        
        self.show_toast(f"找到 {len(results)} 筆結果", color="#01814A")
        
        # 顯示搜尋結果彈窗
        from ui.dialogs import SearchResultDialog
        dialog = SearchResultDialog(self, query, results)
        self.wait_window(dialog)
        
        # 使用者選擇了影片
        if dialog.result:
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, dialog.result)
            self.log(f"已選擇: {dialog.result}")
            # 自動觸發分析
            self.after(200, self.on_fetch_info)


    def _run_playlist_check(self, url, c_type, c_path, ua, proxy):
        # 快速分析清單 (不抓詳細字幕)
        info = self.core.fetch_playlist_info(url, cookie_type=c_type, cookie_path=c_path, user_agent=ua, proxy=proxy)
        
        def _update_pl_ui():
            if 'error' in info:
                self.show_toast("清單分析失敗", color="#D93025")
                err_msg = info['error']
                self.log(f"清單錯誤: {err_msg}")
                
                if "核心載入失敗" in err_msg or "CORE_MISSING" in err_msg:
                    messagebox.showerror("核心遺失", "未安裝 yt-dlp 核心組件！\n無法進行分析或下載。\n\n請稍後在「設定」頁面點擊「檢查並更新」安裝。")
                    self.tab_view.set("設定")
            else:
                title = info.get('title', '未知清單')
                count = info.get('count', '?')
                self.show_toast(f"清單分析完成 ({count} 部影片)")
                self.log(f"已獲取清單: {title} (共 {count} 部)")
                
                # Update thumbnail for playlist
                self.update_thumbnail(info)

                if 'items' in info and info['items']:
                    self.pending_playlist_info = info
                    self.show_toast("清單已就緒！\n設定格式後->「加入任務」", duration=4000)
                    self.log(f"清單分析完成，等待使用者加入任務...")
                else:
                    self.pending_playlist_info = None
                    messagebox.showinfo("清單模式", f"已讀取清單：{title}\n\n注意：此清單無法解析內容，將預設下載全部。")
        
        self.after(0, _update_pl_ui)

    def _run_fetch(self, url, c_type, c_path, ua, proxy):
        info = self.core.fetch_video_info(url, cookie_type=c_type, cookie_path=c_path, user_agent=ua, proxy=proxy)
        
        def _update_ui():
            if 'error' in info:
                self.show_toast("分析失敗", color="#D93025")
                err_msg = info['error']
                self.log(f"{err_msg}")
                
                if "核心載入失敗" in err_msg or "CORE_MISSING" in err_msg:
                    messagebox.showerror("核心遺失", "未安裝 yt-dlp 核心組件！\n無法進行分析或下載。\n\n請稍後在「設定」頁面點擊「檢查並更新」安裝。")
                    self.tab_view.set("設定")
                    
                elif "Sign in" in err_msg: messagebox.showwarning("驗證失敗", "YouTube 拒絕連線。\n請到 [高級選項] 勾選瀏覽器後再試一次。")
            else:
                self.last_fetched_info = info
                # Live Stream Detection Logic
                if info.get('is_live', False):
                    self.show_toast("偵測到直播", color="#1F6AA5")
                    # Use a slight delay to ensure toast is visible before modal dialog
                    self.after(100, lambda: self._check_live_settings_popup())
                
                # Update Thumbnail
                self.update_thumbnail(info)

                if info['subtitles']:
                    self.show_toast("分析完成 (有字幕)")
                else:
                    self.show_toast("分析完成 (無字幕)")
                
                self.log(f"已獲取資訊: {info['title']}")
                self.after(50, lambda: self.update_subtitle_list_ui(info))
        
        self.after(0, _update_ui)

    def _check_live_settings_popup(self):
        """彈出視窗詢問是否前往直播設定"""
        if messagebox.askyesno("直播偵測", "此連結為直播/首播影片。\n\n是否前往【直播設定】頁面檢查：\n1. 智慧等待 (Smart Wait)\n2. 錄製策略 (DVR)\n\n(若設定已確認可按「否」繼續)"):
            self.select_frame("Live")



    def get_config_from_ui(self):
        url = self.entry_url.get().strip()
        if not url: 
            messagebox.showwarning("提示", "網址不能為空")
            return None

        raw_path = self.entry_path.get().strip()
        final_save_path = raw_path if raw_path else app_path

        # Handle Format (Mode-based)
        download_mode = self.var_download_mode.get() if hasattr(self, 'var_download_mode') else "video"
        
        if download_mode == "audio":
            # 純音訊模式
            raw_format = self.var_audio_format.get() if hasattr(self, 'var_audio_format') else "MP3"
            # 解析新格式名稱到副檔名
            if "AAC" in raw_format or "m4a" in raw_format:
                selected_ext = "m4a"
            elif "Opus" in raw_format:
                selected_ext = "opus"
            elif "FLAC" in raw_format:
                selected_ext = "flac"
            elif "WAV" in raw_format:
                selected_ext = "wav"
            else:  # MP3 or default
                selected_ext = "mp3"
            is_audio_only = True
        else:
            # 影片模式
            selected_ext = self.var_video_format.get() if hasattr(self, 'var_video_format') else "mp4"
            is_audio_only = False


        config = {
            'url': url,
            'save_path': final_save_path,
            'filename': self.entry_filename.get().strip(),
            'ext': selected_ext,
            'is_audio_only': is_audio_only,
            'video_res': self.combo_video_res.get(),
            'audio_qual': self.combo_audio_quality.get(),
            'audio_codec': self.combo_audio_codec.get(),
            'use_time_range': self.var_cut.get(),
            'start_time': self.entry_start.get().strip(),
            'end_time': self.entry_end.get().strip(),
            'video_codec': self.var_video_codec_select.get() if hasattr(self, 'var_video_codec_select') else "Auto", 
            'playlist_mode': self.var_playlist.get(),       
            'sub_langs': self.get_selected_subs(), 
            'cookie_type': self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none',
            'cookie_path': self._get_cookie_path_for_mode(),
            'user_agent': self.entry_ua.get().strip() if hasattr(self, 'entry_ua') else None,
            'proxy': self.entry_proxy.get().strip() if hasattr(self, 'entry_proxy') else None,
            'add_timestamp': self.var_add_timestamp.get() if hasattr(self, 'var_add_timestamp') else False,
            'is_live': False,

            'embed_thumbnail': self.var_embed_thumb.get() if hasattr(self, 'var_embed_thumb') else True,
            'embed_subs': self.var_embed_subs.get() if hasattr(self, 'var_embed_subs') else True,
            'add_metadata': self.var_metadata.get() if hasattr(self, 'var_metadata') else True,
            'sponsorblock': self.var_sponsorblock.get() if hasattr(self, 'var_sponsorblock') else False, 
            'sponsor_cats_list': [k for k, v in self.sb_vars.items() if v.get()] if hasattr(self, 'sb_vars') else ['all'], 
            'hardware_accel': self.detected_gpu if (hasattr(self, 'var_hardware_accel') and self.var_hardware_accel.get() and self.detected_gpu) else "不使用 (CPU)",
            
            # Live Stream Settings
            'live_wait': self.var_live_wait.get() if hasattr(self, 'var_live_wait') else False,
            'live_from_start': self.var_live_from_start.get() if hasattr(self, 'var_live_from_start') else True,
            'live_autostop': self.var_live_autostop.get() if hasattr(self, 'var_live_autostop') else False,
            'live_stop_min': self.var_live_stop_min.get() if hasattr(self, 'var_live_stop_min') else "60",
            
            # Scheduler
            'schedule_enabled': self.var_schedule_enable.get() if hasattr(self, 'var_schedule_enable') else False,
            'schedule_time': self.entry_schedule_time.get().strip() if hasattr(self, 'entry_schedule_time') else "00:00",
        }

        # Try to attach cached info (Thumbnail, Title) if URL matches (ignoring query params)
        def _clean_url(u):
            if not u: return ""
            return u.split('?')[0].split('&')[0]

        clean_input_url = _clean_url(url)
        
        cached_match = False
        if self.last_fetched_info:
            if _clean_url(self.last_fetched_info.get('webpage_url')) == clean_input_url: cached_match = True
            elif _clean_url(self.last_fetched_info.get('original_url')) == clean_input_url: cached_match = True
        
        if cached_match:
             if 'title' in self.last_fetched_info and not config['filename']:
                 config['default_title'] = self.last_fetched_info['title']


        
        return config

    def on_add_task(self):
        base_config = self.get_config_from_ui()
        if not base_config: return
        
        # Schedule Logic
        if base_config.get('schedule_enabled'):
            try:
                raw_time = base_config.get('schedule_time', "0000").replace(":", "").strip()
                # 補零 (例: 930 -> 0930)
                if len(raw_time) == 3: raw_time = "0" + raw_time
                
                if len(raw_time) != 4 or not raw_time.isdigit():
                    raise ValueError("Invalid format")
                    
                hh = int(raw_time[0:2])
                mm = int(raw_time[2:4])
                
                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                     raise ValueError("Time out of range")

                now = datetime.now()
                target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                
                base_config['schedule_ts'] = target.timestamp()
                base_config['schedule_str'] = target.strftime('%Y-%m-%d %H:%M')
                
                self.log(f"[預約] 任務已排程於: {base_config['schedule_str']}")
                self.show_toast(f"預約成功: {base_config['schedule_str']}", duration=3000)
            except Exception as e:
                self.log(f"[預約錯誤] 時間格式錯誤: {e}", level="error")
                base_config['schedule_enabled'] = False # Disable on error
        
        if self.pending_playlist_info:
            info = self.pending_playlist_info
            
            self.show_toast("正在開啟清單選單...", duration=2000)
            self.update() 

            dlg = PlaylistSelectionDialog(self, info.get('title', 'Unknown'), info.get('items', []))
            self.wait_window(dlg)
            
            if dlg.result:
                selected_items = []
                for idx in dlg.result:
                     for item in info['items']:
                        if item['index'] == idx:
                            selected_items.append(item)
                            break
                self.selected_playlist_data = selected_items
                self.pending_playlist_info = None 
            else:
                 return

        if base_config['playlist_mode'] and self.selected_playlist_data:
            count = len(self.selected_playlist_data)
            self.log(f"正在將清單展開為 {count} 個單曲任務...")
            
            for item in self.selected_playlist_data:
                task_config = base_config.copy()
                task_config['url'] = item.get('url', base_config['url']) 
                task_config['default_title'] = item.get('title', '未知標題')
                task_config['playlist_mode'] = False 
                task_config['filename'] = "" 
                task_config['manual_start'] = True
                
                self.download_queue.append(task_config)
            
            self.log(f"已加入 {count} 個任務至排程")
            
            self.selected_playlist_data = []
            
            self.entry_url.delete(0, "end")
            self.entry_filename.delete(0, "end")
            
            self.clear_subtitle_ui()
            self.update_thumbnail(None) # Reset thumbnail for playlist too 
            
            self.var_playlist.set(False) 
            self.on_playlist_toggle() 
            
            # Explicitly defocus BEFORE switching view to ensure placeholder reappears
            self.focus_set()
            
            self.update_queue_ui()
            
            self.select_frame("Tasks")
            self.seg_tasks.set("等待中")
            self.switch_task_view("等待中") 
            
            return

        current_def_title = base_config.get('default_title', '')
        if not base_config.get('filename') and (not current_def_title or current_def_title in ["尚未分析", "分析中..."]):
             base_config['default_title'] = "正在獲取標題..." 
             threading.Thread(target=self._auto_fetch_title, args=(base_config,), daemon=True).start()

        # 加入佇列
        base_config['manual_start'] = not self.var_auto_start.get() 
        self.download_queue.append(base_config)
        self.log(f"已加入排程: {base_config['url']}")
        self.update_queue_ui()
        
        # Show Toast
        self.show_toast("任務加入成功")
        
        # 清空輸入與重置分析狀態
        self.entry_url.delete(0, "end")
        self.entry_filename.delete(0, "end")
        
        self.clear_subtitle_ui() 
        self.update_thumbnail(None)
        
        # 轉移焦點至主視窗 (立即執行，確保 Placeholder 重置)
        self.focus_set() 

    def _auto_fetch_title(self, config):
        """Background thread to fetch title for waiting tasks"""
        core = YtDlpCore()
        success = False
        
        # 1. Try with user settings (Cookies, Proxy, etc.)
        try:
            info = core.fetch_video_info(config['url'], cookie_type=config['cookie_type'], cookie_path=config['cookie_path'], user_agent=config.get('user_agent'), proxy=config.get('proxy'))
            
            if info and 'title' in info and info['title'] != '未知標題' and 'error' not in info:
                config['default_title'] = info['title']
                success = True
        except: pass
        
        # 2. Fallback: Try without Cookies (if first attempt failed)
        if not success:
            try:
                info = core.fetch_video_info(config['url'], cookie_type='none', user_agent=config.get('user_agent'), proxy=config.get('proxy'))
                if info and 'title' in info and info['title'] != '未知標題' and 'error' not in info:
                    config['default_title'] = info['title']
            except: 
                config['default_title'] = ""

        self.after(0, self.update_queue_ui)

    def show_toast(self, message, duration=2000, color="#01814A"):
        """顯示頂層懸浮通知 (使用 Toplevel + Transparent Color 實現真去背圓角)"""
        if getattr(self, 'is_loading_config', False): return  # 設定載入中不顯示通知
        # 銷毀舊的 toast
        if hasattr(self, 'current_toast') and self.current_toast:
            try: self.current_toast.destroy()
            except: pass

        # 1. 建立 Toplevel 視窗
        top = ctk.CTkToplevel(self)
        top.overrideredirect(True) # 無邊框
        top.attributes("-topmost", True) # 最上層
        
        # 避免搶走焦點
        top.attributes("-alpha", 0.0) # 先隱藏，定好位再顯示
        
        # 2. 設定透明色 (Windows 特有解法)
        # 改用接近黑色的去背色 (#000001)，這樣就算閃爍也比較不明顯
        transparent_color = "#000001"
        try:
            if os.name == 'nt':
                top.attributes("-transparentcolor", transparent_color)
                top.configure(fg_color=transparent_color) 
            else:
                # 非 Windows 系統退回一般透明
                top.configure(fg_color="gray10") 
        except: pass
        
        # 3. 建立圓角內容
        # 注意: bg_color 必須設為上述的 transparent_color
        toast_btn = ctk.CTkButton(
            top,
            text=message,
            fg_color=color,
            bg_color=transparent_color, 
            hover_color=color, # 禁用 hover
            corner_radius=22,
            width=240,
            height=45,
            font=(self.font_family, 13, "bold"),
            text_color="white",
            command=lambda: top.destroy()
        )
        toast_btn.pack(fill="both", expand=True)

        # 4. 計算顯示位置 (右上角)
        try:
            # 確保幾何數據最新
            self.update_idletasks()
            mw_x = self.winfo_x()
            mw_y = self.winfo_y()
            mw_w = self.winfo_width()
            
            # x = 主視窗X + 寬度 - Toast寬(240) - padding(20)
            # y = 主視窗Y + padding(60)
            tx = mw_x + mw_w - 260 
            ty = mw_y + 60
            
            top.geometry(f"240x45+{tx}+{ty}")
        except:
             top.geometry("240x45")

        # 顯示
        top.attributes("-alpha", 1.0)
        self.current_toast = top

        # 5. 自動關閉與淡出動畫
        def start_fade_out():
            try:
                if not top.winfo_exists(): return
                
                # 簡易淡出
                alpha = top.attributes("-alpha")
                if alpha > 0.0:
                    alpha -= 0.1
                    top.attributes("-alpha", alpha)
                    self.after(30, start_fade_out)
                else:
                    top.destroy()
                    if self.current_toast == top: self.current_toast = None
            except: pass
            
        self.after(duration, start_fade_out)

        # 6. [Update] 讓 Toast 跟隨主視窗移動 (Fixed to Window)
        def _sync_pos(event=None):
            if not top.winfo_exists(): return
            try:
                # 只有當移動的是主視窗本身才更新
                if event and event.widget != self: return
                
                mw_x = self.winfo_x()
                mw_y = self.winfo_y()
                mw_w = self.winfo_width()
                
                tx = mw_x + mw_w - 260 
                ty = mw_y + 60
                top.geometry(f"240x45+{tx}+{ty}")
            except: pass
        
        # Bind configure event to main window
        self.bind("<Configure>", _sync_pos, add="+")

    def on_start_download(self):
        config = self.get_config_from_ui()
        if not config: return

        # --- 獨立任務邏輯 ---
        if self.var_independent.get():
            self.log(f"★ 啟動獨立背景任務: {config['url']}")
            messagebox.showinfo("背景任務", "任務已啟動！\n請至「背景任務」分頁查看進度或停止。")
            task_id = str(uuid.uuid4())
            bg_core = YtDlpCore()
            self.bg_tasks[task_id] = {'core': bg_core, 'url': config['url'], 'status': '執行中'}
            
            self.create_active_task_widget(task_id, config, "獨立任務啟動中...")

            def on_bg_finish(success, msg):
                self.log(f"[背景任務結束] {msg}")
                if task_id in self.bg_tasks: self.bg_tasks.pop(task_id)
                self.remove_active_task_widget(task_id)
                self.add_history_item(config, success, msg)

            bg_core.start_download_thread(
                config, 
                progress_callback=lambda p, m: self.update_background_progress(task_id, p, m), 
                log_callback=self.log,
                finish_callback=on_bg_finish
            )
            # 清空輸入與重置分析狀態
            self.entry_url.delete(0, "end")
            self.entry_filename.delete(0, "end")
            self.clear_subtitle_ui()
            self.update_thumbnail(None)
            self.focus_set()
            
            self.select_frame("Tasks")
            self.seg_tasks.set("進行中")
            self.switch_task_view("進行中")
            return

        # --- 一般排程邏輯 ---
        self.download_queue.append(config)
        self.log(f"已加入排程並開始: {config['url']}")
        self.update_queue_ui()
        self.check_queue() 
        
        # 提示切換
        self.select_frame("Tasks")
        if hasattr(self, 'seg_tasks'): self.seg_tasks.set("進行中")
        self.switch_task_view("進行中")

        # 清空輸入與重置分析狀態 (與加入任務保持一致)
        self.entry_url.delete(0, "end")
        self.entry_filename.delete(0, "end")
        self.clear_subtitle_ui()
        self.update_thumbnail(None)
        self.focus_set()
        




    def check_and_perform_shutdown(self):
        """檢查是否需要執行關機/睡眠"""
        if not hasattr(self, 'var_after_completion'): return
        action = self.var_after_completion.get()
        if action == 'none': return
        
        action_name = "自動關機" if action == 'shutdown' else "進入睡眠"
        cmd = "shutdown /s /t 0" if action == 'shutdown' else "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
        
        # Create Countdown Window
        dialog = ctk.CTkToplevel(self)
        dialog.title("任務完成")
        dialog.geometry("400x250")
        dialog.attributes("-topmost", True)
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 125
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text=f"所有任務已完成！\n即將執行 {action_name}", font=("Microsoft JhengHei UI", 16, "bold"), text_color="orange").pack(pady=(20, 10))
        
        lbl_timer = ctk.CTkLabel(dialog, text="60", font=("Arial", 48, "bold"), text_color="#1F6AA5")
        lbl_timer.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        cancel_flag = False
        
        def cancel():
            nonlocal cancel_flag
            cancel_flag = True
            dialog.destroy()
            self.show_toast(f"已取消 {action_name}")
            
        def execute_now():
            nonlocal cancel_flag
            cancel_flag = True 
            dialog.destroy()
            self.log(f"正在執行 {action_name}...")
            os.system(cmd)
            
        ctk.CTkButton(btn_frame, text="取消 (Cancel)", command=cancel, fg_color="gray", hover_color="gray30").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="立即執行 (Now)", command=execute_now, fg_color="#D93025", hover_color="#B31412").pack(side="left", padx=10)
        
        # Countdown Loop
        def update_timer(seconds):
            if cancel_flag: return
            if seconds <= 0:
                execute_now()
                return
            
            lbl_timer.configure(text=str(seconds))
            dialog.after(1000, update_timer, seconds - 1)
            
        update_timer(60)

    def _fade_in_window(self, alpha=0.0, step=0, start_y=None, target_y=None):
        """滑入 + 淡入組合動畫：從下方滑入並淡入"""
        max_steps = 15  # 減少步數以加快動畫 (150ms)
        slide_distance = 20  # 減少滑動距離以更微妙
        
        # 第一次調用時，儲存當前位置作為目標位置
        if start_y is None:
            try:
                geometry = self.geometry()
                # 解析格式 "widthxheight+x+y"
                parts = geometry.replace('x', '+').split('+')
                target_y = int(parts[2])
                start_y = target_y + slide_distance  # 起始位置在下方
                # 設置起始位置
                current_x = int(parts[1].split('x')[0]) if 'x' in parts[1] else int(parts[1])
                width = int(parts[0])
                height = int(parts[1].split('x')[1]) if 'x' in parts[1] else int(parts[0].split('x')[1])
                self.geometry(f"{width}x{height}+{current_x}+{start_y}")
            except:
                # 如果獲取位置失敗，退回到純淡入
                target_y = None
                start_y = None
        
        if step < max_steps:
            # 計算當前步驟的進度 (0.0 到 1.0)
            progress = step / max_steps
            
            # 淡入：alpha 從 0 到 1
            alpha = progress
            
            try:
                self.attributes("-alpha", alpha)
                
                # 滑入：Y 位置從 start_y 到 target_y
                if start_y is not None and target_y is not None:
                    current_y = int(start_y + (target_y - start_y) * progress)
                    geometry = self.geometry()
                    parts = geometry.replace('x', '+').split('+')
                    current_x = int(parts[1].split('x')[0]) if 'x' in parts[1] else int(parts[1])
                    width = int(parts[0])
                    height = int(parts[1].split('x')[1]) if 'x' in parts[1] else int(parts[0].split('x')[1])
                    self.geometry(f"{width}x{height}+{current_x}+{current_y}")
                
                # 下一步
                self.after(10, lambda: self._fade_in_window(alpha, step + 1, start_y, target_y))
            except:
                pass
        else:
            # 動畫完成，確保最終狀態正確
            try:
                self.attributes("-alpha", 1.0)
                if target_y is not None:
                    geometry = self.geometry()
                    parts = geometry.replace('x', '+').split('+')
                    current_x = int(parts[1].split('x')[0]) if 'x' in parts[1] else int(parts[1])
                    width = int(parts[0])
                    height = int(parts[1].split('x')[1]) if 'x' in parts[1] else int(parts[0].split('x')[1])
                    self.geometry(f"{width}x{height}+{current_x}+{target_y}")
            except:
                pass

    def _fade_out_window(self, step=0, start_y=None, target_y=None, callback=None):
        """滑出 + 淡出組合動畫：向下滑出並淡出（最小化前）"""
        max_steps = 15  # 與淡入動畫同步
        slide_distance = 20  # 與淡入動畫同步
        
        # 第一次調用時，儲存當前位置作為起始位置
        if start_y is None:
            try:
                geometry = self.geometry()
                parts = geometry.replace('x', '+').split('+')
                start_y = int(parts[2])
                target_y = start_y + slide_distance  # 目標位置在下方
            except:
                # 如果獲取位置失敗，退回到純淡出
                target_y = None
                start_y = None
        
        if step < max_steps:
            # 計算當前步驟的進度 (0.0 到 1.0)
            progress = step / max_steps
            
            # 淡出：alpha 從 1 到 0
            alpha = 1.0 - progress
            
            try:
                self.attributes("-alpha", alpha)
                
                # 滑出：Y 位置從 start_y 到 target_y
                if start_y is not None and target_y is not None:
                    current_y = int(start_y + (target_y - start_y) * progress)
                    geometry = self.geometry()
                    parts = geometry.replace('x', '+').split('+')
                    current_x = int(parts[1].split('x')[0]) if 'x' in parts[1] else int(parts[1])
                    width = int(parts[0])
                    height = int(parts[1].split('x')[1]) if 'x' in parts[1] else int(parts[0].split('x')[1])
                    self.geometry(f"{width}x{height}+{current_x}+{current_y}")
                
                # 下一步
                self.after(10, lambda: self._fade_out_window(step + 1, start_y, target_y, callback))
            except:
                pass
        else:
            # 動畫完成，執行回調（最小化）
            if callback:
                callback()

    def _handle_window_hide(self, event):
        """當視窗即將隱藏（最小化）時，設置標記和透明度"""
        if event.widget == self:
            try:
                self.attributes("-alpha", 0.0)
                self._was_minimized = True  # 明確標記為最小化
            except:
                pass

    def _handle_window_restore(self, event):
        """當視窗顯示時，只有從最小化恢復才播放動畫"""
        if event.widget == self:
            # 如果正在執行最大化操作，不要干預
            if getattr(self, '_is_maximizing', False):
                return
            
            # 檢查是否是從最小化恢復
            if getattr(self, '_was_minimized', False):
                # 是從最小化恢復，播放淡入動畫
                self._was_minimized = False  # 清除標記
                try:
                    self.update_idletasks()
                except:
                    pass
                self.after(100, lambda: self._fade_in_window(alpha=0.0))
            else:
                # 不是從最小化恢復（可能是最大化等）
                # 先完成UI渲染，避免看到黑色背景
                try:
                    self.update_idletasks()
                    self.attributes("-alpha", 1.0)
                except:
                    pass

    def _force_refresh_ui(self):
        self.update_idletasks()

        try:
            current_alpha = self.attributes("-alpha")
            if current_alpha >= 1.0:
                self.attributes("-alpha", 0.99)
                self.after(10, lambda: self.attributes("-alpha", 1.0))
        except Exception:
            pass

    def _scheduler_loop(self):
        """定期檢查排程任務"""
        self.check_queue()
        # 每 5 秒檢查一次
        self.after(5000, self._scheduler_loop)

    def check_queue(self):
        """檢查並啟動排程任務"""
        # 更新 UI 狀態
        active_count = len(self.active_queue_tasks)
        queue_count = len(self.download_queue)
        
        # Prepare Status Suffix
        status_suffix = ""
        if hasattr(self, 'var_after_completion'):
            act = self.var_after_completion.get()
            if act == 'shutdown': status_suffix = " | 結束後關機"
            elif act == 'sleep': status_suffix = " | 結束後睡眠"

        msg = f"下載中 ({active_count}/{self.max_concurrent_downloads}) | 等待中: {queue_count}{status_suffix}"
            
        if active_count >= 1:
            self.downloading = True
            # [Refine] 允許隨時加入新任務 (Queue Mode)
            self.btn_download.configure(state="normal", text="快速下載")

            if active_count > 1:
                self.lbl_status.configure(text=msg)
            # elseif active_count == 1: Do not update lbl_status (keep update_progress percentage)

        elif active_count == 0 and queue_count == 0:
            idle_msg = f"準備就緒{status_suffix}"
            
            if self.downloading:
                self.downloading = False
                self.btn_download.configure(state="normal", text="開始下載")
                idle_msg = f"所有任務已完成！{status_suffix}"
                self.progress_bar.set(0)
                
                self.check_and_perform_shutdown()
            
            if not self.downloading and hasattr(self, 'lbl_status'):
                 self.lbl_status.configure(text=idle_msg)

        # 啟動新任務 (支援排程邏輯)
        while len(self.active_queue_tasks) < self.max_concurrent_downloads and self.download_queue:
            
            start_index = -1
            now_ts = datetime.now().timestamp()
            
            for i, config in enumerate(self.download_queue):
                if config.get('schedule_enabled') and config.get('schedule_ts'):
                    if now_ts < config['schedule_ts']:
                        continue 
                
                if config.get('manual_start'):
                    continue
                
                start_index = i
                break
            
            if start_index == -1:
                break
                
            next_config = self.download_queue.pop(start_index)
            self.update_queue_ui()
            self._start_core_download(next_config)

    def _start_core_download(self, config, task_id=None):
        if not task_id: task_id = str(uuid.uuid4())
        
        is_resume = task_id in self.active_task_widgets
        
        last_percent = 0
        if task_id in self.active_queue_tasks:
             last_percent = self.active_queue_tasks[task_id].get('last_percent', 0)

        # [Optimized] 使用獨立線程啟動下載，以便在續傳時能等待舊線程結束，避免 WinError 32
        def _launcher():
             # 1. 若為續傳，先等待舊線程完全釋放資源
             if task_id in self.active_queue_tasks:
                 old_core = self.active_queue_tasks[task_id].get('core')
                 if old_core:
                     old_core.stop_download() # 確保再次發送停止訊號
                     if hasattr(old_core, 'download_thread') and old_core.download_thread.is_alive():
                         print(f"[{task_id}] 正在等待舊下載線程結束...")
                         old_core.download_thread.join(timeout=5.0) # 等待最多 5 秒
             
             # 2. 建立新核心
             core = YtDlpCore()
             
             self.active_queue_tasks[task_id] = {
                'core': core,
                'config': config,
                'status': 'running',
                'last_percent': last_percent
             }
             
             # 3. 回調主線程更新 UI
             def _ui_logic():
                 if not is_resume:
                     self.create_active_task_widget(task_id, config, "排程任務啟動中...")
                 else:
                     self._update_task_buttons(task_id, "running")
                     
                 if self.frames["Tasks"].winfo_ismapped() and getattr(self, 'seg_tasks', None) and self.seg_tasks.get() != "進行中":
                      self.seg_tasks.set("進行中")
                      self.switch_task_view("進行中")
                 
                 self.log(f"啟動排程任務: {config['url']}")
                 
                 # Setup Auto Stop Timer
                 if config.get('live_autostop', False):
                     try:
                         mins = float(config.get('live_stop_min', 60))
                         delay_ms = int(mins * 60 * 1000)
                         if delay_ms > 0:
                             timer_id = self.after(delay_ms, lambda: self._perform_auto_stop(task_id))
                             self.active_queue_tasks[task_id]['autostop_timer'] = timer_id
                             self.log(f"[{task_id}] 已設定自動停止，將於 {mins} 分鐘後結束錄製。")
                     except Exception as e:
                         print(f"AutoStop Init Error: {e}")
             
             self.after(0, _ui_logic)
             
             # 4. 準備 Title Callback
             def update_title_callback(real_title):
                if not config.get('filename'):
                    # 更新字典 (需注意 thread-safety，不過 Python dict 操作通常是 atomic)
                    if task_id in self.active_queue_tasks:
                        self.active_queue_tasks[task_id]['config']['default_title'] = real_title
                    config['default_title'] = real_title
                    
                    def _update_ui_title():
                        if task_id in self.active_task_widgets:
                            if len(real_title) > 50: real_title_disp = real_title[:47] + "..."
                            else: real_title_disp = real_title
                            
                            widgets = self.active_task_widgets[task_id]
                            if 'title_label' in widgets:
                                widgets['title_label'].configure(text=real_title_disp) 
                    
                    self.after(0, _update_ui_title)

             # 5. 啟動下載
             core.start_download_thread(
                config, 
                progress_callback=lambda p, m, s=None, e=None: self.update_progress(p, m, task_id, s, e), 
                log_callback=self.log,
                finish_callback=lambda s, m: self.on_download_finished(s, m, task_id, config),
                title_callback=update_title_callback
            )

        threading.Thread(target=_launcher, daemon=True).start()
        # [End of _start_core_download]
        
        def update_title_callback(real_title):
            if not config.get('filename'):
                self.active_queue_tasks[task_id]['config']['default_title'] = real_title
                config['default_title'] = real_title
                


    def update_background_progress(self, task_id, percent, msg):
        if task_id in self.bg_tasks:
            self.bg_tasks[task_id]['status'] = msg
            if task_id not in self.active_task_widgets:
                 pass 
            self.update_task_widget(task_id, percent, msg)

    def on_stop_download(self):
        if messagebox.askyesno("確認", "確定要停止所有排程任務嗎？\n(背景獨立任務不會被停止)"):
            self.log("正在停止所有排程任務...")
            for t_id, info in list(self.active_queue_tasks.items()):
                try: 
                    info['status'] = 'cancelled'
                    info['core'].stop_download()
                except: pass
            if self.download_queue:
                if messagebox.askyesno("確認", "是否同時清空等待中的排程清單？"):
                    self.download_queue.clear()
                    self.update_queue_ui()
            self.check_queue()

    def update_progress(self, percent, msg, task_id, speed=None, eta=None):
        if task_id in self.active_queue_tasks:
             self.active_queue_tasks[task_id]['last_percent'] = percent

        current_time = time.time()
        last_time = self.task_last_update_time.get(task_id, 0)
        
        should_update = (
            (current_time - last_time > 0.1) or 
            percent == -1 or 
            percent >= 1.0 or
            "合併" in msg or 
            "轉檔" in msg
        )

        if should_update:
            self.task_last_update_time[task_id] = current_time
            self.update_task_widget(task_id, percent, msg, speed, eta)

        # 多任務時，進度條顯示最近活動的任務，或者保持忙碌狀態
        try:
            active_count = len(self.active_queue_tasks)
            
            # [Fix] 判定邏輯優化：只有當任務數 > 1 時才顯示 (N個任務執行中)
            # 並且避免與 check_queue 中的文字打架
            
            if active_count > 1:
                # 多任務: Indeterminate Bar + 總數狀態
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
                self.lbl_status.configure(text=f"下載中 ({active_count} 個任務執行中...)")
            
            elif active_count == 1:
                # 單任務: Determinate Bar + 精確百分比
                if percent == -1:
                    self.progress_bar.configure(mode="indeterminate")
                    self.progress_bar.start()
                else:
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.stop()
                    self.progress_bar.set(percent)
                
                # 更新狀態文字
                if "合併" in msg or "轉檔" in msg: 
                    self.lbl_status.configure(text="合併轉檔中... (請稍候)")
                elif percent == -1:
                    # 不確定的進度 (e.g. 直播或處理中)
                    self.lbl_status.configure(text=msg if msg else "處理中...")
                else: 
                    # 正常下載進度
                    self.lbl_status.configure(text=f"下載中 {int(percent * 100)}%")
                    
        except: pass

    def on_download_finished(self, success, msg, task_id, config):
        # [Fix] 如果任務已不再佇列中 (例如已強制取消)，忽略此回調以避免重複處理
        if task_id not in self.active_queue_tasks:
            return

        current_status = 'unknown'
        if task_id in self.active_queue_tasks:
            current_status = self.active_queue_tasks[task_id].get('status', 'finished')

        # Clean up Auto-Stop Timer if exists
        if task_id in self.active_queue_tasks:
            if 'autostop_timer' in self.active_queue_tasks[task_id]:
                try: self.after_cancel(self.active_queue_tasks[task_id]['autostop_timer'])
                except: pass

        if current_status == 'paused':
            self.log(f"[已暫停] {msg}")
            
            last_p = self.active_queue_tasks[task_id].get('last_percent', 0)
            if last_p < 0: last_p = 0
            self.update_task_widget(task_id, last_p, "已暫停 (雙擊繼續)")
            
            self._update_task_buttons(task_id, 'paused')
            return

        # 錯誤訊息增強提示
        if not success and current_status != 'cancelled':
            if "Permission denied" in msg or "WinError 32" in msg or "unable to open" in msg:
                msg += " (提示: 目標檔案可能已存在或正被佔用，請關閉相關程式)"

        status_prefix = "成功" if success else "失敗"
        if current_status == 'cancelled': status_prefix = "已取消"
        
        self.log(f"[{status_prefix}] {msg}")
        
        # 移除已完成任務
        if task_id in self.active_queue_tasks:
            self.active_queue_tasks.pop(task_id)
        
        # 移除 UI Widget
        self.remove_active_task_widget(task_id)
        
        # 加入歷史 
        final_msg = "已取消" if current_status == 'cancelled' else msg
        self.add_history_item(config, success, final_msg)
            
        if not success and current_status != 'cancelled':
             self.log(f"排程任務錯誤: {msg}") 

        # 觸發檢查隊列，看是否需要啟動下一個
        self.after(500, self.check_queue)
        
        if not self.active_queue_tasks and not self.download_queue:
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0) 
            self.lbl_status.configure(text="準備就緒")
            
            # Check notification setting
            should_notify = True
            if hasattr(self, 'var_notification'):
                should_notify = self.var_notification.get()
            
            if success and should_notify:
                messagebox.showinfo("完成", "所有排程任務已完成！")

    def toggle_pause_task(self, task_id):
        # 排程任務
        if task_id in self.active_queue_tasks:
            task_info = self.active_queue_tasks[task_id]
            if task_info['status'] == 'running':
                task_info['status'] = 'paused'
                self.log(f"暫停任務: {task_info['config']['url']}")
                try: 
                    # Cancel Auto-Stop Timer if exists
                    if 'autostop_timer' in task_info:
                        try: self.after_cancel(task_info['autostop_timer'])
                        except: pass
                    task_info['core'].stop_download()
                except: pass
                
                # [UI Fix] 立即更新 UI 顯示為暫停狀態
                self.update_task_widget(task_id, task_info.get('last_percent', 0), "暫停下載 (雙擊繼續)")

            elif task_info['status'] == 'paused':
                self.resume_task(task_id)

    def resume_task(self, task_id):
        if task_id in self.active_queue_tasks:
             info = self.active_queue_tasks[task_id]
             self.log(f"繼續任務: {info['config']['url']}")
             self._start_core_download(info['config'], task_id=task_id)

    def cancel_task(self, task_id):
        if task_id in self.active_task_widgets:
             try:
                 self.update_task_widget(task_id, -1, "正在中止...")
             except: pass

        if task_id in self.active_queue_tasks:
             info = self.active_queue_tasks[task_id]
             
             # Cancel Auto-Stop Timer if exists
             if 'autostop_timer' in info:
                 try: self.after_cancel(info['autostop_timer'])
                 except: pass

             # 如果任務已暫停或核心未在運行，直接清理
             if info.get('status') == 'paused' or not info['core'].is_downloading:
                 info['status'] = 'cancelled'
                 self.on_download_finished(False, "手動取消", task_id, info['config'])
                 return

             info['status'] = 'cancelled'
             try: 
                info['core'].stop_download()
             except: pass
             
             # [Optimization] 立即執行清理與 UI 移除，不必等待背景線程回應
             # 因為已標記 cancelled 且 stop 後，背景線程的回調會因為 active_queue_tasks 檢查而被忽略
             self.on_download_finished(False, "手動取消", task_id, info['config'])
        if task_id in self.bg_tasks:
             self.stop_background_task(task_id)

    def _perform_auto_stop(self, task_id):
        """定時停止任務的回調"""
        if task_id in self.active_queue_tasks:
            self.log(f"[{task_id}] 定時錄製時間已到，正在停止...")
            self.cancel_task(task_id)
            self.show_toast("定時錄製已結束", f"任務 {task_id[:4]}... 已依排程停止")
             
    def stop_background_task(self, task_id):
        if task_id in self.bg_tasks:
            try: self.bg_tasks[task_id]['core'].stop_download()
            except: pass
            self.bg_tasks.pop(task_id)
            self.log(f"已手動停止背景任務: {task_id}")
            self.remove_active_task_widget(task_id)

    def check_core_library(self):
        if yt_dlp is None:
            ans = tk.messagebox.askyesno("核心檢查", "未偵測到 yt-dlp  (或檔案已遺失)。\n這將導致無法解析或下載影片。\n是否立即安裝？\n(確定後請勿關閉程式並稍等幾秒)")
            if ans:
                threading.Thread(target=self.install_yt_dlp, daemon=True).start()
            else:
                 self.log("警告: 核心未安裝。功能將受限。", level="error")
                 self.show_toast("核心缺失", "下載功能無法使用", icon_color="red")

    def install_yt_dlp(self):
        # 建立進度視窗
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("核心安裝中")
        progress_win.geometry("300x120")
        progress_win.attributes("-topmost", True) 
        
        # 讓視窗居中
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 60
        progress_win.geometry(f"+{x}+{y}")
        
        # 進度標籤
        lbl_status = ctk.CTkLabel(progress_win, text="正在初始化...", font=("Microsoft JhengHei UI", 14))
        lbl_status.pack(pady=40, padx=20)
        
        # 禁止關閉視窗 (簡單防呆)
        progress_win.protocol("WM_DELETE_WINDOW", lambda: None)
        
        def update_status(text):
            self.after(0, lambda: lbl_status.configure(text=text))
            self.after(0, lambda: self.log(text))

        def close_progress():
            self.after(0, progress_win.destroy)

        try:
            
            update_status("連線中...")
            
            target_dir = os.path.join(app_path, "lib")
            
            # 定義安裝成功後的重啟邏輯
            def on_install_success(source_name):
                update_status(f"安裝成功！({source_name})")
                self.after(0, lambda: self.show_toast(f"{source_name} 安裝完成", "請重新啟動程式", icon_color="green"))
                close_progress()
                
                def ask_restart():
                    if tk.messagebox.askyesno("需重啟", f"核心 ({source_name}) 安裝完成！\n必須重新啟動程式才能生效。\n是否立即重啟？"):
                        subprocess.Popen([sys.executable] + sys.argv)
                        self.quit()
                        sys.exit()
                self.after(0, ask_restart)

            # --- 策略 1: PyPI (優先) ---
            try:
                update_status("正在檢查 PyPI 版本...")
                resp = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    version = data['info']['version']
                    update_status(f"發現版本: {version}")
                    
                    download_url = None
                    for url_info in data['urls']:
                        if url_info['filename'].endswith('.whl'):
                            download_url = url_info['url']
                            break
                    
                    if download_url:
                        update_status("下載 PyPI 核心中...")
                        whl_resp = requests.get(download_url, timeout=30)
                        
                        # 直接刪除整個 lib 資料夾再重建
                        if os.path.exists(target_dir):
                            try:
                                shutil.rmtree(target_dir)
                            except:
                                pass
                        os.makedirs(target_dir, exist_ok=True)
                        
                        update_status("解壓縮中...")
                        with zipfile.ZipFile(io.BytesIO(whl_resp.content)) as z:
                            z.extractall(target_dir)
                            
                        on_install_success("PyPI")
                        return 
                        
            except Exception as pypi_e:
                update_status(f"PyPI 失敗，切換 GitHub...")
                self.after(0, lambda: self.log(f"PyPI 安裝失敗 ({str(pypi_e)})，嘗試切換至 GitHub...", level="warning"))
            
            # --- 策略 2: GitHub Releases (備援) ---
            try:
                update_status("正在連接 GitHub...")
                # 使用 GitHub API 獲取最新 Release
                gh_resp = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=10)
                if gh_resp.status_code == 200:
                    gh_data = gh_resp.json()
                    tag_name = gh_data['tag_name']
                    zip_url = gh_data['zipball_url'] 
                    
                    update_status(f"GitHub 版本: {tag_name}")
                    
                    zip_resp = requests.get(zip_url, timeout=60, stream=True)
                    
                    # 解壓到暫存資料夾
                    temp_extract_dir = os.path.join(app_path, "_temp_yt_dlp")
                    if os.path.exists(temp_extract_dir):
                        try:
                            shutil.rmtree(temp_extract_dir)
                        except: pass

                    os.makedirs(temp_extract_dir)
                    
                    update_status("解壓原始碼...")
                    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                        z.extractall(temp_extract_dir)
                    
                    # GitHub 源碼結構通常是: Root-Folder/yt_dlp/...
                    found_pkg = False
                    for root, dirs, files in os.walk(temp_extract_dir):
                        if 'yt_dlp' in dirs:
                            src_pkg = os.path.join(root, 'yt_dlp')
                            # 確認裡面有 __init__.py 才算是套件
                            if '__init__.py' in os.listdir(src_pkg):
                                if not os.path.exists(target_dir): os.makedirs(target_dir)
                                # 如果目標已存在 yt_dlp，先移除
                                target_pkg = os.path.join(target_dir, 'yt_dlp')
                                if os.path.exists(target_pkg):
                                    try:
                                        shutil.rmtree(target_pkg)
                                    except: pass

                                
                                # 移動
                                shutil.move(src_pkg, target_dir)
                                found_pkg = True
                                break
                    
                    # 清理暫存
                    try:
                        shutil.rmtree(temp_extract_dir)
                    except: pass

                    
                    if found_pkg:
                        on_install_success("GitHub")
                        return
                    else:
                        raise Exception("在 GitHub 原始碼中找不到 yt_dlp 套件資料夾")
                else:
                    raise Exception(f"GitHub API Error: {gh_resp.status_code}")

            except Exception as gh_e:
                raise Exception(f"所有下載來源皆失敗。\nGitHub: {gh_e}")

        except Exception as e:
            close_progress()
            err_msg = str(e)
            self.after(0, lambda: self.log(f"核心安裝失敗: {err_msg}", level="error"))
            self.after(0, lambda: self.show_toast("安裝失敗", err_msg, icon_color="red"))
            self.after(0, lambda: tk.messagebox.showerror("錯誤", f"核心安裝失敗:\n{err_msg}"))

    def check_app_update(self, silent=False):
        """檢查 App 是否有新版本 (GitHub Releases, 支援 Zip 與 Exe 選擇)"""
        if silent and hasattr(self, 'var_auto_update') and not self.var_auto_update.get():
            return
        
        def _check_process():
            try:
                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                
                session = requests.Session()
                resp = session.get(api_url, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    latest_tag = data.get("tag_name", "Unknown")
                    
                    # --- 版本比對邏輯 ---
                    def parse_version(v_str):
                        import re
                        try:
                            # 使用正則表達式擷取所有數字序列，這允許靈活的版本號格式
                            # 例如: 2026.01.06-1, 2026.01.06_fix1, 2026.01.06.v2 都能正確解析
                            nums = re.findall(r'\d+', v_str)
                            return tuple(map(int, nums)) if nums else (0, 0, 0)
                        except:
                            return (0, 0, 0)

                    remote_ver = parse_version(latest_tag)
                    local_ver = parse_version(APP_VERSION)
                    
                    if remote_ver > local_ver:
                        zip_url = ""
                        exe_url = ""
                        
                        # 同時尋找兩種資源
                        for asset in data.get("assets", []):
                            name_lower = asset["name"].lower()
                            if "source code" in name_lower: continue
                            
                            if name_lower.endswith(".zip"):
                                if "multidownload" in name_lower or "update" in name_lower:
                                    zip_url = asset["browser_download_url"]
                            elif name_lower.endswith(".exe"):
                                if "multidownload" in name_lower:
                                    exe_url = asset["browser_download_url"]

                        # 回到主線程顯示 UI
                        self.after(0, lambda: self._handle_update_found(latest_tag, zip_url, exe_url))
                            
                    else:
                        if not silent:
                            self.after(0, lambda: tk.messagebox.showinfo("檢查完成", f"目前已是最新版本 ({APP_VERSION})。\n(雲端最新: {latest_tag})"))
                
                elif resp.status_code == 404:
                    if not silent:
                        self.after(0, lambda: tk.messagebox.showerror("檢查失敗", "找不到發布版本 (GitHub Repo 未發布 Release 或設為私有)。"))
                else:
                    if not silent:
                        val = resp.status_code
                        self.after(0, lambda: tk.messagebox.showerror("檢查失敗", f"無法連接伺服器 (Status: {val})。"))
                
            except Exception as e:
                err = str(e)
                if not silent:
                    self.after(0, lambda: tk.messagebox.showerror("檢查錯誤", f"檢查更新時發生錯誤:\n{err}"))

        threading.Thread(target=_check_process, daemon=True).start()

    def _handle_update_found(self, version, zip_url, exe_url):
        """處理更新UI邏輯 (Main Thread)"""
        # 顯示紅點提示 (即使使用者關閉彈窗，側邊欄也會有提示)
        if hasattr(self, 'show_nav_badge'): self.show_nav_badge("About")
        if hasattr(self, 'btn_update_app'): self.show_widget_badge(self.btn_update_app, 'app_update')
        
        if zip_url or exe_url:
            self.show_update_selection_dialog(version, zip_url, exe_url)
        else:
            tk.messagebox.showwarning("無法更新", f"發現新版本 {version}，但在發布文件中找不到 .zip 或 .exe 檔。")

    def show_update_selection_dialog(self, version, zip_url, exe_url):
        """顯示更新選擇視窗 (統一使用自定義 UI 以支援字體格式)"""
        
        # 如果已經有彈窗，先關閉
        if hasattr(self, 'update_win') and self.update_win.winfo_exists():
            self.update_win.destroy()
            
        top = ctk.CTkToplevel(self)
        top.title("發現新版本")
        top.geometry("420x300")
        top.attributes("-topmost", True)
        self.update_win = top
        
        # --- 視窗中心定位保持不變 ---
        x = self.winfo_x() + (self.winfo_width() // 2) - 210
        y = self.winfo_y() + (self.winfo_height() // 2) - 175
        top.geometry(f"+{x}+{y}")
        
        # 1. Title - 增加上方的留白，讓標題更顯眼
        ctk.CTkLabel(top, text="發現新版本", font=("Microsoft JhengHei UI", 22, "bold")).pack(pady=(35, 10))
        
        # 2. Version Diff - 創造層次感
        ver_frame = ctk.CTkFrame(top, fg_color="transparent")
        ver_frame.pack(pady=(0, 25))
        
        # 舊版本：字體縮小、顏色變淡
        ctk.CTkLabel(ver_frame, text=f"{APP_VERSION}", font=("Consolas", 13), text_color="#888888").pack(side="left", padx=5)
        # 箭頭：使用更纖細的符號
        ctk.CTkLabel(ver_frame, text="→", font=("Consolas", 14), text_color="#AAAAAA").pack(side="left")
        # 新版本：字體加大、粗體、深色（或系統預設顏色）
        ctk.CTkLabel(ver_frame, text=f"{version}", font=("Consolas", 20, "bold")).pack(side="left", padx=8)

        # Helper Actions
        def do_zip():
            top.destroy()
            self.perform_self_update(zip_url)
            
        def do_exe():
            top.destroy()
            self.perform_self_update(exe_url)
            
        def do_cancel():
            top.destroy()

        # 3. Dynamic Buttons & Descriptions
        # 優化點：將說明文字字體稍微調小，顏色調淡，讓它看起來像輔助資訊
        
        if zip_url and exe_url:
            ctk.CTkLabel(top, text="請選擇您偏好的更新方式", font=("Microsoft JhengHei UI", 13), text_color="#666666").pack(pady=(0, 10))
             
            # ZIP 按鈕
            ctk.CTkButton(top, text="完整更新 (.zip)\n推薦：包含資源檔更新", command=do_zip, 
                        width=280, height=55, font=("Microsoft JhengHei UI", 13), 
                        fg_color="#1F6AA5", hover_color="#144870", corner_radius=8).pack(pady=8)
             
            # EXE 按鈕 (次要按鈕使用深色或透明描邊)
            ctk.CTkButton(top, text="快速更新 (.exe)\n僅替換主程式", command=do_exe, 
                        width=280, height=55, font=("Microsoft JhengHei UI", 13), 
                        fg_color="#444444", hover_color="#333333", corner_radius=8).pack(pady=8)

        elif zip_url:
            # 單一更新時，說明文字稍微遠離標題，靠近按鈕
            ctk.CTkLabel(top, text="本次更新將包含完整的資源檔案 (.zip)", font=("Microsoft JhengHei UI", 12), text_color="gray").pack(pady=(0, 5))
            ctk.CTkButton(top, text="立即更新 (.zip)", command=do_zip, 
                        width=280, height=48, font=("Microsoft JhengHei UI", 15, "bold"), 
                        fg_color="#1F6AA5", hover_color="#144870", corner_radius=8).pack(pady=10)

        elif exe_url:
            ctk.CTkLabel(top, text="本次僅進行快速更新 (.exe)", font=("Microsoft JhengHei UI", 12), text_color="gray").pack(pady=(0, 5))
            ctk.CTkButton(top, text="立即更新 (.exe)", command=do_exe, 
                        width=280, height=48, font=("Microsoft JhengHei UI", 15, "bold"), 
                        fg_color="#1F6AA5", hover_color="#144870", corner_radius=8).pack(pady=10)
        
        # 4. Cancel - 增加下方邊距，並讓它看起來更像一個輕量的選項
        ctk.CTkButton(top, text="暫不更新", font=("Microsoft JhengHei UI", 12), command=do_cancel, 
                    width=100, height=30, fg_color="transparent", text_color="#777777", 
                    hover_color=("gray90", "gray25")).pack(side="bottom", pady=(0, 25))
    
    def perform_self_update(self, download_url):
        try:
            
            self.show_toast("系統更新: 正在下載新版本...", duration=5000, color="#1F6AA5")
            self.update_idletasks()
            
            # 判斷更新類型
            is_zip = download_url.endswith(".zip")
            filename = "update.zip" if is_zip else "MULTIDownload_Update.exe"
            
            # 下載檔案
            response = requests.get(download_url, stream=True)
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.show_toast("正在安裝更新，程式將自動重啟...", duration=5000, color="#1F6AA5")
            
            current_exe = os.path.basename(sys.executable)
            
            if is_zip:
                # 1. 解壓至暫存區
                extract_dir = "_update_temp"
                if os.path.exists(extract_dir):
                    # [Fix] 加入延遲重試機制，應對 Windows 檔案鎖定 (WinError 32)
                    for attempt in range(3):
                        try:
                            shutil.rmtree(extract_dir)
                            break
                        except Exception as e:
                            if attempt < 2:
                                import time
                                time.sleep(1)  # 等待 1 秒後重試
                            else:
                                print(f"Warning: Cleanup failed after 3 attempts: {e}")

                os.makedirs(extract_dir)

                
                with zipfile.ZipFile(filename, 'r') as z:
                    z.extractall(extract_dir)
                
                # 2. 尋找解壓後的根目錄 (處理 Zip 包多一層資料夾的情況)
                src_path = extract_dir
                items = os.listdir(extract_dir)
                if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                     src_path = os.path.join(extract_dir, items[0])
                
                # 3. 建構 CMD 指令 (覆蓋整個資料夾)
                
                cmd_command = (
                    f'timeout /t 2 /nobreak > NUL && '
                    f'xcopy "{src_path}\\*" "." /s /e /y /i && '
                    f'rmdir /s /q "{extract_dir}" && '
                    f'del /f /q "{filename}" && '
                    f'start "" "{current_exe}"'
                )
            else:
                # EXE 替換模式
                cmd_command = (
                    f'timeout /t 2 /nobreak > NUL && '
                    f'del /f /q "{current_exe}" && '
                    f'move /y "{filename}" "{current_exe}" && '
                    f'start "" "{current_exe}"'
                )
            
            # 在背景啟動 CMD
            subprocess.Popen(f'cmd /c "{cmd_command}"', shell=True)
            
            # 關閉主程式
            self.destroy()
            sys.exit(0)
            
        except Exception as e:
            tk.messagebox.showerror("更新錯誤", f"無法執行自動更新:\n{e}")

    def check_core_update_silent(self):
        """背景檢查 yt-dlp 是否有更新"""
        def _bg_check():
            try:
                # 1. 取得本地版本
                local_ver_str = "0"
                try:
                    import yt_dlp.version
                    local_ver_str = yt_dlp.version.__version__
                except:
                    return # 未安裝或無法讀取

                # 2. 取得遠端版本 (使用 GitHub API，與手動檢查源保持一致)
                resp = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=10)
                if resp.status_code != 200: return
                
                data = resp.json()
                remote_tag = data.get("tag_name", "0")
                
                # 3. 比對 (yt-dlp 使用 YYYY.MM.DD 格式)
                def parse(v):
                    try:
                        return tuple(map(int, v.lower().lstrip('v').split('.')))
                    except: return (0,0,0)
                
                if parse(remote_tag) > parse(local_ver_str):
                     # 有更新
                     self.after(0, lambda: self._on_core_update_found(remote_tag))
                     
            except Exception: pass
        
        threading.Thread(target=_bg_check, daemon=True).start()

    def _on_core_update_found(self, version):
        if hasattr(self, 'show_nav_badge'): self.show_nav_badge("About")
        if hasattr(self, 'btn_update_ytdlp'): self.show_widget_badge(self.btn_update_ytdlp, 'core_update')
        # self.log(f"發現 yt-dlp 新版本 {version}，請至「設定」更新。") # 保持日誌乾淨可不加





    def _monitoring_loop(self):
        """背景監聽迴圈 (剪貼簿與輸入監聽)"""
        try:
            # 1. 剪貼簿監聽
            if hasattr(self, 'var_clipboard') and self.var_clipboard.get():
                # [FIX] 增加焦點判斷：只有當程式有焦點(在使用中)時才偵測
                if self.focus_get():
                    try:
                        content = self.clipboard_get()
                        if content != self.last_clipboard_content:
                            self.last_clipboard_content = content
                            if any(x in content for x in ["http://", "https://", "youtu", "bilibili"]):
                                if content != self.entry_url.get():
                                    self.entry_url.delete(0, "end")
                                    self.entry_url.insert(0, content)
                                    self.show_toast("已偵測並填入剪貼簿連結")
                                    self.after(500, self.on_fetch_info)
                    except: pass

        except: pass
        
        # Loop
        self.after(1500, self._monitoring_loop)

if __name__ == "__main__":
    app = App()
    app.mainloop()