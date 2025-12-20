import sys
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from core import YtDlpCore 
import threading
import uuid
from LANGUAGE_MAP import CODE_TO_NAME 
import yt_dlp # 用於顯示版本號

# --- [高階技巧] 支援外部 Library 覆蓋 (用於 exe 更新 yt-dlp) ---
# 若在 exe 旁建立 'lib' 資料夾並放入新版 yt_dlp，程式將優先載入該版本
if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

lib_path = os.path.join(app_path, 'lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)


# --- 設定：預設外觀模式 (請勿手動修改格式，程式會自動更新此行) ---
DEFAULT_APPEARANCE_MODE = "Dark"

ctk.set_default_color_theme("blue")

class CTkToolTip:
    """
    通用工具提示 (Tooltip) 類別
    當滑鼠停留在 widget 上時顯示文字框
    """
    def __init__(self, widget, text, delay=200):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<ButtonPress>", self.on_leave)

    def on_enter(self, event=None):
        self.schedule()

    def on_leave(self, event=None):
        self.unschedule()
        self.hide()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show(self):
        if not self.tooltip_window:
            # 建立無邊框視窗
            self.tooltip_window = ctk.CTkToplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.attributes("-topmost", True) # 確保在最上層
            
            # 設定顏色 (跟隨主題)
            bg_color = "#FFFFDD" if ctk.get_appearance_mode() == "Light" else "#333333"
            fg_color = "#000000" if ctk.get_appearance_mode() == "Light" else "#FFFFFF"
            
            # 內容標籤
            label = ctk.CTkLabel(
                self.tooltip_window, 
                text=self.text, 
                text_color=fg_color,
                fg_color=bg_color,
                corner_radius=6,
                font=("Microsoft JhengHei UI", 12),
                padx=10, 
                pady=5
            )
            label.pack()
            
            # 計算位置 (跟隨滑鼠下方)
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            self.tooltip_window.geometry(f"+{x}+{y}")

    def hide(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MULTIDownload")
        self.geometry("800x780") 
        
        # 設定外觀
        ctk.set_appearance_mode(DEFAULT_APPEARANCE_MODE)
        
        # --- 字型設定 ---
        self.font_family = "Microsoft JhengHei UI" if sys.platform.startswith("win") else "PingFang TC"
        self.font_title = (self.font_family, 14, "bold")
        self.font_text = (self.font_family, 12)
        self.font_btn = (self.font_family, 14, "bold")
        self.font_small = (self.font_family, 11)
        
        # 初始化
        self.core = YtDlpCore()
        self.downloading = False # 保留此變數作為 UI 狀態與簡易判斷
        self.download_queue = [] 
        self.active_queue_tasks = {} # 用於追蹤排程中正在執行的任務 {uuid: core}
        self.max_concurrent_downloads = 1 # 預設最大同時下載數
        self.bg_tasks = {}       

        # --- 1. 建立分頁系統 ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(padx=10, pady=(10, 0), fill="both", expand=True)
        self.tab_view._segmented_button.configure(font=self.font_btn)

        self.tab_basic = self.tab_view.add("基本選項")
        self.tab_format = self.tab_view.add("格式/畫質")
        self.tab_sub = self.tab_view.add("字幕")
        self.tab_output = self.tab_view.add("輸出/裁剪")
        self.tab_adv = self.tab_view.add("進階選項")
        self.tab_bg = self.tab_view.add("背景任務")
        self.tab_log = self.tab_view.add("系統日誌")
        self.tab_settings = self.tab_view.add("設定") # 新增設定分頁

        self.setup_basic_ui()
        self.setup_format_ui()
        self.setup_subtitle_ui()
        self.setup_output_ui()
        self.setup_advanced_ui()
        self.setup_background_ui()
        self.setup_log_ui()
        self.setup_settings_ui() # 初始化設定介面

        # --- 2. 建立底部控制區 ---
        self.setup_bottom_controls()
        
        # --- 3. 啟動背景刷新 ---
        self.refresh_background_tab()

    # ================= UI 建構區 =================


    def setup_bottom_controls(self):
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.bottom_frame.pack(side="bottom", fill="x", padx=15, pady=15)
        self.bottom_frame.grid_columnconfigure(1, weight=1)

        # 狀態文字
        self.lbl_status = ctk.CTkLabel(self.bottom_frame, text="準備就緒", font=self.font_title, width=80, anchor="w")
        self.lbl_status.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # 進度條
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, height=15)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=10, sticky="ew")

        # 獨立執行 Checkbox
        self.var_independent = ctk.BooleanVar(value=False)
        self.chk_independent = ctk.CTkCheckBox(
            self.bottom_frame, text="獨立執行", font=self.font_small, width=20, variable=self.var_independent
        )
        self.chk_independent.grid(row=0, column=2, padx=(10, 5))

        # 下載按鈕
        self.btn_download = ctk.CTkButton(
            self.bottom_frame, text="開始下載", width=100, height=35, font=self.font_btn, 
            fg_color="#009100", hover_color="#007500", command=self.on_start_download
        )
        self.btn_download.grid(row=0, column=3, padx=(5, 5))

        # 停止按鈕
        self.btn_stop = ctk.CTkButton(
            self.bottom_frame, text="停止", width=80, height=35, font=self.font_btn, 
            fg_color="#DB3E39", hover_color="#8B0000", state="disabled", command=self.on_stop_download
        )
        self.btn_stop.grid(row=0, column=4, padx=(5, 0))

    def setup_basic_ui(self):
        # URL
        ctk.CTkLabel(self.tab_basic, text="影片網址 (URL)", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_url = ctk.CTkEntry(self.tab_basic, width=600, font=self.font_text, placeholder_text="請在此貼上連結...")
        self.entry_url.pack(padx=20, pady=5)
        
        # 提示文字移至輸入框下方
        ctk.CTkLabel(self.tab_basic, text="Tip：直播影片推薦勾選「獨立執行」，可於背景下載避免卡住排程", font=self.font_small, text_color="gray").pack(anchor="w", padx=25, pady=(0, 5))
        
        btn_fetch = ctk.CTkButton(self.tab_basic, text="分析網址 (獲取標題/字幕)", font=self.font_btn, command=self.on_fetch_info)
        btn_fetch.pack(padx=20, pady=5)

        self.lbl_title = ctk.CTkLabel(self.tab_basic, text="尚未分析", font=self.font_text, text_color=("gray20", "gray80"))
        self.lbl_title.pack(padx=20, pady=5)

        # Path
        ctk.CTkLabel(self.tab_basic, text="下載位置", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 5))
        path_frame = ctk.CTkFrame(self.tab_basic, fg_color="transparent")
        path_frame.pack(fill="x", padx=20)
        self.entry_path = ctk.CTkEntry(path_frame, font=self.font_text, placeholder_text="預設為當前目錄")
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(path_frame, text="選擇", font=self.font_btn, width=80, command=self.browse_folder).pack(side="right")

        # Filename
        ctk.CTkLabel(self.tab_basic, text="檔名", font=self.font_title).pack(anchor="w", padx=20, pady=(10, 5))
        self.entry_filename = ctk.CTkEntry(self.tab_basic, font=self.font_text, width=400, placeholder_text="預設為原標題")
        self.entry_filename.pack(anchor="w", padx=20)


        # --- [新增] 下載排程顯示區 ---
        ctk.CTkLabel(self.tab_basic, text="排程任務", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 5))
        
        # 使用 ScrollableFrame 來顯示清單
        self.queue_scroll_frame = ctk.CTkScrollableFrame(self.tab_basic, height=150)
        self.queue_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(5, 10))
        
        # 初始化顯示
        self.update_queue_ui()

    def update_queue_ui(self):
        """[新增] 更新排程介面"""
        # 清空目前顯示
        for widget in self.queue_scroll_frame.winfo_children():
            widget.destroy()

        if not self.download_queue:
            ctk.CTkLabel(self.queue_scroll_frame, text="目前沒有排程任務", text_color="gray", font=self.font_text).pack(pady=20)
            return

        for i, config in enumerate(self.download_queue):
            # 每一行是一個 Frame
            row = ctk.CTkFrame(self.queue_scroll_frame, fg_color=("gray85", "gray25"))
            row.pack(fill="x", pady=2, padx=5)
            
            # 顯示標題或網址
            display_text = config['filename'] if config['filename'] else config['url']
            if len(display_text) > 40: display_text = display_text[:37] + "..."
            
            # 序號 + 標題
            ctk.CTkLabel(row, text=f"{i+1}. {display_text}", font=self.font_text, anchor="w").pack(side="left", padx=10, pady=5)
            
            # 格式資訊
            fmt_info = f"[{config['ext']}]"
            ctk.CTkLabel(row, text=fmt_info, text_color="gray", font=self.font_small).pack(side="left", padx=5)

            # 移除按鈕 (X)
            btn_remove = ctk.CTkButton(
                row, text="✕", width=30, height=20, fg_color="transparent", hover_color="#8B0000", text_color="red", font=("Arial", 12, "bold"),
                command=lambda idx=i: self.remove_from_queue(idx)
            )
            btn_remove.pack(side="right", padx=10)

    def remove_from_queue(self, index):
        """[新增] 從排程中移除任務"""
        if 0 <= index < len(self.download_queue):
            removed = self.download_queue.pop(index)
            self.log(f"已移除排程: {removed['url']}")
            self.update_queue_ui()
            # 更新底部狀態文字
            self.lbl_status.configure(text=f"下載中... (排程等待: {len(self.download_queue)})" if self.downloading else "準備就緒")

    def setup_format_ui(self):
        self.tab_format.grid_columnconfigure(1, weight=1)
        option_style = {
            "width": 220, "height": 35, "corner_radius": 5,
            "fg_color": "#3E3E3E", "button_color": "#505050", "button_hover_color": "#606060",
            "dropdown_fg_color": "#2B2B2B", "dropdown_hover_color": "#1F6AA5", "dropdown_text_color": "#FFFFFF",
            "font": self.font_text, "dropdown_font": self.font_text, "text_color": "#FFFFFF"
        }

        ctk.CTkLabel(self.tab_format, text="輸出格式", font=self.font_title).grid(row=0, column=0, padx=20, pady=20, sticky="w")
        self.format_options = ["mp4 (影片+音訊)", "mkv (影片+音訊)", "webm (影片+音訊)", "mp3 (純音訊)", "m4a (純音訊)", "flac (無損音訊)", "wav (無損音訊)"]
        self.combo_format = ctk.CTkOptionMenu(self.tab_format, values=self.format_options, command=self.on_format_change, **option_style)
        self.combo_format.set("mp4 (影片+音訊)")
        self.combo_format.grid(row=0, column=1, padx=20, pady=20, sticky="ew")

        ctk.CTkFrame(self.tab_format, height=2, fg_color="gray").grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.tab_format, text="影片畫質", font=self.font_title).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.combo_video_res = ctk.CTkOptionMenu(self.tab_format, values=["Best (最高畫質)", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"], **option_style)
        self.combo_video_res.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.tab_format, text="音訊品質", font=self.font_title).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.combo_audio_quality = ctk.CTkOptionMenu(self.tab_format, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps (標準)", "96 kbps (較低)", "64 kbps (省空間)"], **option_style)
        self.combo_audio_quality.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.tab_format, text="音訊編碼", font=self.font_title).grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.combo_audio_codec = ctk.CTkOptionMenu(self.tab_format, values=["Auto (預設/Opus)", "AAC (車用/相容性高)"], **option_style)
        self.combo_audio_codec.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        self.lbl_format_hint = ctk.CTkLabel(self.tab_format, text="Tip：若車用音響無聲音，請在「音訊編碼」選擇 AAC", font=self.font_small, text_color="gray")
        self.lbl_format_hint.grid(row=5, column=0, columnspan=2, padx=20, pady=20)

    def on_format_change(self, choice):
        if "純音訊" in choice or "無損" in choice:
            self.combo_video_res.set("N/A")
            self.combo_video_res.configure(state="disabled")
            self.combo_audio_codec.set("Auto (預設/Opus)")
            self.combo_audio_codec.configure(state="disabled")
            self.lbl_format_hint.configure(text="提示：已選擇純音訊/無損模式，畫質與編碼選項已自動調整")
        else:
            self.combo_video_res.configure(state="normal")
            self.combo_video_res.set("Best (最高畫質)")
            self.combo_audio_codec.configure(state="normal")
            self.lbl_format_hint.configure(text=f"提示：將下載 {choice.split(' ')[0]} 格式")

    def setup_subtitle_ui(self):
        ctk.CTkLabel(self.tab_sub, text="請先在［基本選項］點擊「分析網址」以載入字幕列表", font=self.font_small, text_color="gray").pack(pady=10)
        self.scroll_subs = ctk.CTkScrollableFrame(self.tab_sub, label_text="可用字幕語言")
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=10)
        self.sub_checkboxes = {}

    def setup_output_ui(self):
        self.var_cut = ctk.BooleanVar(value=False)
        chk_cut = ctk.CTkCheckBox(self.tab_output, text="啟用時間裁剪", font=self.font_title, variable=self.var_cut, command=self.toggle_time_inputs)
        chk_cut.pack(anchor="w", padx=20, pady=20)
        
        time_frame = ctk.CTkFrame(self.tab_output)
        time_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(time_frame, text="開始 (HH:MM:SS)", font=self.font_title).pack(side="left", padx=10)
        self.entry_start = ctk.CTkEntry(time_frame, width=100, font=self.font_text, placeholder_text="00:00:00")
        self.entry_start.pack(side="left", padx=10)
        ctk.CTkLabel(time_frame, text="至", font=self.font_title).pack(side="left", padx=5)
        self.entry_end = ctk.CTkEntry(time_frame, width=100, font=self.font_text, placeholder_text="00:01:30")
        self.entry_end.pack(side="left", padx=10)
        self.toggle_time_inputs()
        
        ctk.CTkLabel(self.tab_output, text="直播錄製選項:", font=self.font_title).pack(anchor="w", padx=20, pady=(30, 10))
        self.var_live_mode = ctk.StringVar(value="now")
        ctk.CTkRadioButton(self.tab_output, text="從現在開始", font=self.font_text, variable=self.var_live_mode, value="now").pack(anchor="w", padx=40, pady=5)
        ctk.CTkRadioButton(self.tab_output, text="從頭開始", font=self.font_text, variable=self.var_live_mode, value="start").pack(anchor="w", padx=40, pady=5)

    def setup_advanced_ui(self):
        # 瀏覽器 Cookie 標題區塊 (含 Tooltip)
        browser_title_frame = ctk.CTkFrame(self.tab_adv, fg_color="transparent")
        browser_title_frame.pack(anchor="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(browser_title_frame, text="使用瀏覽器 Cookie (推薦)", font=self.font_title).pack(side="left")
        
        lbl_browser_help = ctk.CTkLabel(browser_title_frame, text="❓", cursor="hand2", font=self.font_small)
        lbl_browser_help.pack(side="left", padx=5)
        
        # 設定 Tooltip 內容
        browser_help_text = (
            "【說明】\n"
            "程式會自動讀取您選擇的瀏覽器中 YouTube 的登入狀態。\n"
            "無需手動匯出檔案，設定與更新最方便。\n"
            "若無法使用，建議使用下方cookies.txt方式。\n"
            "注意：執行下載時建議先將該瀏覽器「完全關閉」，以免讀取失敗。"
        )
        CTkToolTip(lbl_browser_help, browser_help_text)
        
        self.var_cookie = ctk.StringVar(value="none")

        browser_frame = ctk.CTkFrame(self.tab_adv, fg_color="transparent")
        browser_frame.pack(anchor="w", padx=20)
        ctk.CTkRadioButton(browser_frame, text="不使用", font=self.font_text, variable=self.var_cookie, value="none").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkRadioButton(browser_frame, text="Chrome", font=self.font_text, variable=self.var_cookie, value="chrome").grid(row=0, column=1, padx=20, pady=10, sticky="w")
        ctk.CTkRadioButton(browser_frame, text="Firefox", font=self.font_text, variable=self.var_cookie, value="firefox").grid(row=0, column=2, padx=20, pady=10, sticky="w")
        ctk.CTkRadioButton(browser_frame, text="Edge", font=self.font_text, variable=self.var_cookie, value="edge").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkRadioButton(browser_frame, text="Safari", font=self.font_text, variable=self.var_cookie, value="safari").grid(row=1, column=1, padx=20, pady=10, sticky="w")
        
        # 檔案標題區塊 (含 Tooltip)
        file_title_frame = ctk.CTkFrame(self.tab_adv, fg_color="transparent")
        file_title_frame.pack(anchor="w", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(file_title_frame, text="使用 cookies.txt 檔案", font=self.font_title).pack(side="left")
        
        # 幫助圖示
        lbl_help = ctk.CTkLabel(file_title_frame, text="❓", cursor="hand2", font=self.font_small)
        lbl_help.pack(side="left", padx=5)
        
        # 可點擊的下載連結
        def open_ext_link(event=None):
            import webbrowser
            webbrowser.open("https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
            
        lbl_link = ctk.CTkLabel(file_title_frame, text="[下載 Chrome/Edge 擴充]", text_color="#3B8ED0", cursor="hand2", font=self.font_small)
        lbl_link.pack(side="left", padx=5)
        lbl_link.bind("<Button-1>", open_ext_link)
        lbl_link.bind("<Enter>", lambda e: lbl_link.configure(text_color="#1F6AA5")) # Hover effect
        lbl_link.bind("<Leave>", lambda e: lbl_link.configure(text_color="#3B8ED0"))
        
        def open_firefox_link(event=None):
            import webbrowser
            webbrowser.open("https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/")

        lbl_link_firefox = ctk.CTkLabel(file_title_frame, text="[下載 Firefox 擴充]", text_color="#3B8ED0", cursor="hand2", font=self.font_small)
        lbl_link_firefox.pack(side="left", padx=5)
        lbl_link_firefox.bind("<Button-1>", open_firefox_link)
        lbl_link_firefox.bind("<Enter>", lambda e: lbl_link_firefox.configure(text_color="#1F6AA5")) 
        lbl_link_firefox.bind("<Leave>", lambda e: lbl_link_firefox.configure(text_color="#3B8ED0"))
        
        # 設定 Tooltip 內容
        help_text = (
            "【如何取得 cookies.txt ?】\n"
            "建議點擊右側連結安裝「Get cookies.txt LOCALLY」擴充功能。\n"
            "安裝後：到 YouTube 首頁登入 -> 點擊擴充功能圖示 -> \"Export\" -> 下載"
        )
        CTkToolTip(lbl_help, help_text)
        file_frame = ctk.CTkFrame(self.tab_adv, fg_color="transparent")
        file_frame.pack(fill="x", padx=20)
        ctk.CTkRadioButton(file_frame, text="檔案路徑:", font=self.font_text, variable=self.var_cookie, value="file").pack(side="left", padx=(20, 10))
        self.entry_cookie_path = ctk.CTkEntry(file_frame, font=self.font_text, placeholder_text="請選擇 cookies.txt...")
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=10)
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(file_frame, text="瀏覽", width=60, font=self.font_text, command=self.browse_cookie_file).pack(side="right")



        # Max Concurrent Settings
        ctk.CTkLabel(self.tab_adv, text="最大同時下載任務數", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 10))
        
        # 定義統一樣式 (參考 setup_format_ui)
        option_style = {
            "fg_color": "#3E3E3E", "button_color": "#505050", "button_hover_color": "#606060",
            "dropdown_fg_color": "#2B2B2B", "dropdown_hover_color": "#1F6AA5", "dropdown_text_color": "#FFFFFF",
            "font": self.font_btn, "dropdown_font": self.font_btn, "text_color": "#FFFFFF", # 將下拉選單字體加大 (使用 font_btn: 14pt bold)
        }

        # 改用下拉選單 (Combobox)
        concurrent_options = [str(i) for i in range(1, 11)] # 1 到 10
        self.combo_concurrent = ctk.CTkOptionMenu(
            self.tab_adv, 
            values=concurrent_options, 
            command=self.on_concurrent_change,
            width=200, # 加寬選單
            **option_style
        )
        self.combo_concurrent.set("1") # 預設值
        self.combo_concurrent.pack(anchor="w", padx=20, pady=5)

    def on_concurrent_change(self, value):
        self.max_concurrent_downloads = int(value)
        # 如果調大數值，嘗試檢查隊列
        self.check_queue()

    def setup_background_ui(self):
        ctk.CTkLabel(self.tab_bg, text="正在執行的獨立任務", font=self.font_title).pack(pady=10)
        self.bg_scroll_frame = ctk.CTkScrollableFrame(self.tab_bg)
        self.bg_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_background_tab(self):
        for widget in self.bg_scroll_frame.winfo_children(): widget.destroy()
        if not self.bg_tasks:
            ctk.CTkLabel(self.bg_scroll_frame, text="目前沒有執行中的獨立任務", text_color="gray", font=self.font_text).pack(pady=20)
        else:
            for t_id, info in list(self.bg_tasks.items()):
                row_frame = ctk.CTkFrame(self.bg_scroll_frame)
                row_frame.pack(fill="x", pady=5)
                url_short = info['url']
                if len(url_short) > 50: url_short = url_short[:47] + "..."
                info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                info_frame.pack(side="left", padx=10, fill="x", expand=True)
                ctk.CTkLabel(info_frame, text=url_short, font=self.font_text, anchor="w").pack(anchor="w")
                status = info.get('status', '執行中')
                status_color = "#2CC985" if "下載中" in status else ("#FFA500" if "直播" in status else "gray")
                ctk.CTkLabel(info_frame, text=status, text_color=status_color, font=self.font_small, anchor="w").pack(anchor="w")
                btn_kill = ctk.CTkButton(row_frame, text="停止/移除", width=80, height=30, fg_color="#DB3E39", hover_color="#8B0000", command=lambda i=t_id: self.stop_background_task(i))
                btn_kill.pack(side="right", padx=10, pady=10)
        self.after(1000, self.refresh_background_tab)

    def stop_background_task(self, task_id):
        if task_id in self.bg_tasks:
            try: self.bg_tasks[task_id]['core'].stop_download()
            except: pass
            self.bg_tasks.pop(task_id)
            self.log(f"已手動停止背景任務: {task_id}")

    def setup_log_ui(self):
        self.textbox_log = ctk.CTkTextbox(self.tab_log, state="disabled", font=("Consolas", 12))
        self.textbox_log.pack(fill="both", expand=True, padx=10, pady=10)

    # --- 邏輯功能 ---
    def log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", f"{message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def toggle_time_inputs(self):
        state = "normal" if self.var_cut.get() else "disabled"
        self.entry_start.configure(state=state)
        self.entry_end.configure(state=state)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, folder)
    
    def browse_cookie_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            self.entry_cookie_path.delete(0, "end")
            self.entry_cookie_path.insert(0, filename)
            self.var_cookie.set("file")

    def on_fetch_info(self):
        url = self.entry_url.get().strip()
        if not url: return messagebox.showerror("錯誤", "請輸入網址")
        c_type = self.var_cookie.get()
        c_path = self.entry_cookie_path.get().strip()
        self.lbl_title.configure(text="分析中...")
        self.log(f"正在分析: {url}")
        threading.Thread(target=self._run_fetch, args=(url, c_type, c_path), daemon=True).start()

    def _run_fetch(self, url, c_type, c_path):
        info = self.core.fetch_video_info(url, cookie_type=c_type, cookie_path=c_path)
        if 'error' in info:
            self.lbl_title.configure(text="分析失敗", text_color="red")
            self.log(f"錯誤: {info['error']}")
            if "Sign in" in info['error']: messagebox.showwarning("驗證失敗", "YouTube 拒絕連線。\n請到 [高級選項] 勾選瀏覽器後再試一次。")
        else:
            self.lbl_title.configure(text=f"{info['title']}", text_color=("black", "white"))
            self.log(f"已獲取資訊: {info['title']}")
            self.after(0, lambda: self.update_subtitles_ui(info['subtitles']))

    def update_subtitles_ui(self, sub_list):
        for widget in self.scroll_subs.winfo_children(): widget.destroy()
        self.sub_checkboxes.clear()
        if not sub_list: 
            ctk.CTkLabel(self.scroll_subs, text="無可用字幕", font=self.font_text).pack()
            return
        PRIORITY_LANGS = ['zh-TW', 'zh-Hant', 'zh-HK', 'zh-Hans', 'zh-CN', 'en', 'en-US', 'en-GB', 'ja', 'ko']
        priority_matches = []
        other_matches = []
        for code in sub_list:
            if code in PRIORITY_LANGS: priority_matches.append(code)
            else: other_matches.append(code)
        priority_matches.sort(key=lambda x: PRIORITY_LANGS.index(x))
        other_matches.sort()
        def add_checkbox(code):
            lang_name = CODE_TO_NAME.get(code)
            display_text = f"★ [{code}] {lang_name}" if lang_name and code in PRIORITY_LANGS else (f"[{code}] {lang_name}" if lang_name else f"[{code}] (未知語言)")
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(self.scroll_subs, text=display_text, variable=var, font=self.font_text)
            chk.pack(anchor="w", padx=10, pady=2)
            self.sub_checkboxes[code] = var
        if priority_matches:
            ctk.CTkLabel(self.scroll_subs, text="--- 推薦語言 ---", text_color="gray", font=self.font_small).pack(anchor="w", padx=10, pady=(5,0))
            for code in priority_matches: add_checkbox(code)
        if priority_matches and other_matches: ctk.CTkFrame(self.scroll_subs, height=2, fg_color="#555555").pack(fill="x", padx=10, pady=10)
        if other_matches:
            if priority_matches: ctk.CTkLabel(self.scroll_subs, text="--- 其他語言 ---", text_color="gray", font=self.font_small).pack(anchor="w", padx=10, pady=(5,0))
            for code in other_matches: add_checkbox(code)

    def get_selected_subs(self):
        return [lang for lang, var in self.sub_checkboxes.items() if var.get()]

    def on_start_download(self):
        url = self.entry_url.get().strip()
        if not url: return messagebox.showwarning("提示", "網址不能為空")

        raw_path = self.entry_path.get().strip()
        final_save_path = raw_path if raw_path else os.path.dirname(os.path.abspath(__file__))

        raw_format = self.combo_format.get() 
        selected_ext = raw_format.split(' ')[0]
        is_audio_only = selected_ext in ['mp3', 'm4a', 'wav', 'flac']
        
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
            'sub_langs': self.get_selected_subs(),
            'cookie_type': self.var_cookie.get(),
            'cookie_path': self.entry_cookie_path.get().strip(),
            'is_live': False,
            'live_from_start': (self.var_live_mode.get() == 'start')
        }

        # --- 獨立任務邏輯 ---
        if self.var_independent.get():
            self.log(f"★ 啟動獨立背景任務: {url}")
            messagebox.showinfo("背景任務", "任務已啟動！\n請至「背景任務」分頁查看進度或停止。")
            task_id = str(uuid.uuid4())
            bg_core = YtDlpCore()
            self.bg_tasks[task_id] = {'core': bg_core, 'url': url, 'status': '執行中'}
            
            def on_bg_finish(success, msg):
                self.log(f"[背景任務結束] {msg}")
                if task_id in self.bg_tasks: self.bg_tasks.pop(task_id)

            bg_core.start_download_thread(
                config, 
                progress_callback=lambda p, m: self.update_background_progress(task_id, m), 
                log_callback=self.log,
                finish_callback=on_bg_finish
            )
            self.entry_url.delete(0, "end")
            self.entry_filename.delete(0, "end")
            
            # 自動切換到背景任務分頁
            self.tab_view.set("背景任務")
            return

        # --- 一般排程邏輯 ---
        # 加入佇列
        self.download_queue.append(config)
        self.log(f"已加入排程: {url}")
        self.update_queue_ui()
        self.check_queue() # 檢查是否可以開始下載
        
        # 清空輸入
        self.entry_url.delete(0, "end")
        self.entry_filename.delete(0, "end")

    def check_queue(self):
        """檢查並啟動排程任務"""
        # 更新 UI 狀態
        active_count = len(self.active_queue_tasks)
        queue_count = len(self.download_queue)
        
        msg = f"下載中 ({active_count}/{self.max_concurrent_downloads}) | 等待中: {queue_count}"
        if active_count > 0:
            self.downloading = True
            self.btn_download.configure(state="disabled", text="下載中...")
            self.btn_stop.configure(state="normal")
            self.lbl_status.configure(text=msg)
        elif active_count == 0 and queue_count == 0:
             # 只有當原本是下載中狀態，才顯示完成
            if self.downloading:
                self.downloading = False
                self.btn_download.configure(state="normal", text="開始下載")
                self.btn_stop.configure(state="disabled")
                self.lbl_status.configure(text="所有任務已完成！")
                self.progress_bar.set(0)
                if self.active_queue_tasks: messagebox.showinfo("完成", "所有排程任務已完成！") # 這裡其實不會被觸發，因為 active_count 已經是 0

        # 啟動新任務
        while len(self.active_queue_tasks) < self.max_concurrent_downloads and self.download_queue:
            next_config = self.download_queue.pop(0)
            self.update_queue_ui()
            self._start_core_download(next_config)

    def _start_core_download(self, config):
        task_id = str(uuid.uuid4())
        core = YtDlpCore()
        self.active_queue_tasks[task_id] = core
        
        self.log(f"啟動排程任務: {config['url']}")
        core.start_download_thread(
            config, 
            progress_callback=lambda p, m: self.update_progress(p, m, task_id), 
            log_callback=self.log,
            finish_callback=lambda s, m: self.on_download_finished(s, m, task_id)
        )

    def update_background_progress(self, task_id, msg):
        if task_id in self.bg_tasks:
            status_text = msg
            if "直播" in msg: status_text = "直播錄製中..."
            elif "下載中" in msg: status_text = "下載中..."
            self.bg_tasks[task_id]['status'] = status_text

    def on_stop_download(self):
        if messagebox.askyesno("確認", "確定要停止所有排程任務嗎？\n(背景獨立任務不會被停止)"):
            self.log("正在停止所有排程任務...")
            # 停止所有正在執行的
            for t_id, core in list(self.active_queue_tasks.items()):
                try: core.stop_download()
                except: pass
            # 清空等待隊列 (可選，這裡假設使用者想清空)
            if self.download_queue:
                if messagebox.askyesno("確認", "是否同時清空等待中的排程清單？"):
                    self.download_queue.clear()
                    self.update_queue_ui()
            self.check_queue()

    def update_progress(self, percent, msg, task_id):
        # 多任務時，進度條顯示最近活動的任務，或者保持忙碌狀態
        try:
            if len(self.active_queue_tasks) > 1:
                # 多任務時顯示文字，進度條設為 indeterminate 比較好
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
                self.lbl_status.configure(text=f"下載中 ({len(self.active_queue_tasks)} 個任務執行中...)")
            else:
                # 單任務依舊顯示精確進度
                if percent == -1:
                    self.progress_bar.configure(mode="indeterminate")
                    self.progress_bar.start()
                else:
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.stop()
                    self.progress_bar.set(percent)
                
                # 狀態文字只在單任務時更新詳細資訊，避免跳動
                if len(self.active_queue_tasks) <= 1:
                    if "合併" in msg or "轉檔" in msg: self.lbl_status.configure(text="合併轉檔中...")
                    else: self.lbl_status.configure(text=f"下載中: {int(percent * 100)}%")
        except: pass

    def on_download_finished(self, success, msg, task_id):
        status_prefix = "成功" if success else "失敗"
        self.log(f"[{status_prefix}] {msg}")
        
        # 移除已完成任務
        if task_id in self.active_queue_tasks:
            self.active_queue_tasks.pop(task_id)
            
        if not success:
             self.log(f"排程任務錯誤: {msg}") # 不彈窗以免中斷後續任務

        # 觸發檢查隊列，看是否需要啟動下一個
        self.after(500, self.check_queue)
        
        if not self.active_queue_tasks and not self.download_queue:
            if success: messagebox.showinfo("完成", "所有排程任務已完成！")


    def check_for_updates(self):
        """檢查並自動更新 yt-dlp (針對 exe/lib 架構)"""
        self.btn_update.configure(state="disabled", text="檢查中...")
        
        def run_update():
            try:
                import json
                import urllib.request
                import zipfile
                import shutil
                from io import BytesIO
                
                # 1. 取得 PyPI 最新版本資訊
                url = "https://pypi.org/pypi/yt-dlp/json"
                # 需要 User-Agent 避免被擋
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data['info']['version']
                
                current_version = yt_dlp.version.__version__
                
                # 版本號比對函數
                def parse_version(v_str):
                    try:
                        return tuple(map(int, v_str.split('.')))
                    except:
                        return (0, 0, 0)

                if parse_version(latest_version) <= parse_version(current_version):
                    self.after(0, lambda: messagebox.showinfo("檢查更新", f"版本已為最新版本 ({current_version})"))
                    self.after(0, lambda: self.btn_update.configure(state="normal", text="檢查並更新yt-dlp"))
                    return

                # 詢問是否更新
                should_update = [False]
                def ask_user():
                    should_update[0] = messagebox.askyesno("發現新版本", f"現有版本: {current_version}\n最新版本: {latest_version}\n\n是否立即下載並更新？")
                
                # 為了避免在線程中直接彈窗卡住，我們使用同步方式 (在這種簡單場景下通常可接受)
                # 或者我們略過詢問直接下載 (根據使用者的意圖"檢查並更新")，這裡我們假設使用者點了按鈕就是想更新
                
                self.after(0, lambda: self.btn_update.configure(text=f"下載新版本 {latest_version}..."))

                # 2. 尋找 .whl 下載連結
                download_url = None
                for file_info in data['urls']:
                    if file_info['packagetype'] == 'bdist_wheel':
                        download_url = file_info['url']
                        break
                
                if not download_url:
                    raise Exception("找不到可用的更新檔案 (.whl)")

                # 3. 下載並解壓縮
                # 判斷路徑
                if getattr(sys, 'frozen', False):
                    base_path = os.path.dirname(sys.executable)
                else:
                    base_path = os.path.dirname(os.path.abspath(__file__))
                    
                lib_dir = os.path.join(base_path, 'lib')
                if not os.path.exists(lib_dir):
                    os.makedirs(lib_dir)

                with urllib.request.urlopen(download_url, timeout=60) as response:
                    whl_data = response.read()
                    
                with zipfile.ZipFile(BytesIO(whl_data)) as zip_ref:
                    # 只解壓 yt_dlp 資料夾
                    for member in zip_ref.namelist():
                        if member.startswith('yt_dlp/'):
                            zip_ref.extract(member, lib_dir)
                
                # 更新成功後的處理
                def on_success():
                    messagebox.showinfo("更新成功", f"yt-dlp 已更新至 {latest_version}！\n\n點擊確定將自動重啟應用程式以生效。")
                    # 重啟應用程式
                    self.destroy()
                    import subprocess
                    current_file = sys.executable if getattr(sys, 'frozen', False) else __file__
                    subprocess.Popen([sys.executable, current_file] if not getattr(sys, 'frozen', False) else [current_file])
                    sys.exit(0)

                self.after(0, on_success)

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("更新失敗", f"更新錯誤: {err_msg}"))
                self.after(0, lambda: self.btn_update.configure(state="normal", text="檢查並更新yt-dlp"))

        threading.Thread(target=run_update, daemon=True).start()

    def setup_settings_ui(self):
        """設定分頁介面 (取代舊的彈窗)"""
        # 使用一個 Frame 來置中內容
        settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        settings_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(settings_frame, text="外觀主題設定", font=self.font_title).pack(pady=(20, 10))
        ctk.CTkLabel(settings_frame, text="WARNING：更改後將自動重啟應用程式", font=self.font_small, text_color="red").pack(pady=(0, 20))
        
        # 取得當前設定值
        var_mode = ctk.StringVar(value=DEFAULT_APPEARANCE_MODE)
        
        modes = [("系統預設 (System)", "System"), ("淺色模式 (Light)", "Light"), ("深色模式 (Dark)", "Dark")]
        
        for text, mode in modes:
            ctk.CTkRadioButton(settings_frame, text=text, variable=var_mode, value=mode, font=self.font_text).pack(anchor="center", pady=10)
            
        def apply_theme():
            selected = var_mode.get()
            if selected == DEFAULT_APPEARANCE_MODE:
                return

            # 直接執行重啟
            try:
                # 1. 讀取自身程式碼
                import re
                current_file = __file__
                with open(current_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 2. 替換設定變數 (使用正則表達式精確替換)
                new_line = f'DEFAULT_APPEARANCE_MODE = "{selected}"'
                new_content = re.sub(r'DEFAULT_APPEARANCE_MODE = ".*?"', new_line, content, count=1)
                
                # 3. 寫回檔案
                with open(current_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # 4. 強制重啟
                self.destroy() 
                import sys
                import subprocess
                subprocess.Popen([sys.executable, current_file])
                sys.exit(0)
                
            except Exception as e:
                messagebox.showerror("錯誤", f"無法更新設定: {e}")
            
        ctk.CTkButton(settings_frame, text="套用並重啟", font=self.font_btn, height=40, command=apply_theme).pack(pady=(40, 20))

        # 自動更新按鈕
        self.btn_update = ctk.CTkButton(settings_frame, text="檢查並更新yt-dlp", font=self.font_text, fg_color="#555555", hover_color="#333333", command=self.check_for_updates)
        self.btn_update.pack(pady=(0, 20))


        # 先 Pack 連結，讓它沉在最底下
        def open_releases(event=None):
            import webbrowser
            webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases")
            
        lbl_release = ctk.CTkLabel(settings_frame, text="手動更新 yt-dlp", font=self.font_small, text_color="#3B8ED0", cursor="hand2")
        lbl_release.pack(side="bottom", pady=(0, 20)) # 底部留白多一點
        lbl_release.bind("<Button-1>", open_releases)
        lbl_release.bind("<Enter>", lambda e: lbl_release.configure(text_color="#1F6AA5"))
        lbl_release.bind("<Leave>", lambda e: lbl_release.configure(text_color="#3B8ED0"))

        # 再 Pack 版本號，它會疊在連結上面
        try:
            version_text = f"yt-dlp版本: {yt_dlp.version.__version__}"
        except:
            version_text = "版本: 未知"
            
        ctk.CTkLabel(settings_frame, text=version_text, font=self.font_small, text_color="gray").pack(side="bottom", pady=(5, 0))



if __name__ == "__main__":
    app = App()
    app.mainloop()