import sys
import os
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox
from core import YtDlpCore
import threading
import uuid
import time 
import webbrowser
import json




# --- Load Language Map from External JSON ---
CODE_TO_NAME = {}
try:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    lang_file = os.path.join(base_path, 'languages.json')
    
    if os.path.exists(lang_file):
        with open(lang_file, 'r', encoding='utf-8') as f:
            CODE_TO_NAME = json.load(f)
    else:
        CODE_TO_NAME = {'zh-TW': '繁體中文 (預設)', 'en': 'English'}
except Exception:
    CODE_TO_NAME = {'zh-TW': '繁體中文 (預設)', 'en': 'English'} 
# --- 支援外部 Library 覆蓋 ---
if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

lib_path = os.path.join(app_path, 'lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None 


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
            self.tooltip_window = ctk.CTkToplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.attributes("-topmost", True) 
            
            bg_color = "#FFFFDD" if ctk.get_appearance_mode() == "Light" else "#333333"
            fg_color = "#000000" if ctk.get_appearance_mode() == "Light" else "#FFFFFF"
            
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
            
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            self.tooltip_window.geometry(f"+{x}+{y}")

    def hide(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ==========================================
# 播放清單選擇視窗 (嵌入)
# ==========================================
class PlaylistSelectionDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, items):
        super().__init__(parent)
        self.title("選取下載項目")
        self.geometry("500x600")
        self.result = None
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Title
        ctk.CTkLabel(self, text=f"清單: {title}", font=("Microsoft JhengHei UI", 14, "bold"), wraplength=450).pack(pady=10)
        ctk.CTkLabel(self, text="請勾選要下載的項目 (預設全選)", text_color="gray").pack()
        
        # Scrollable List
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.vars = {}
        for item in items:
            idx = item['index']
            t = item['title']
            if len(t) > 40: t = t[:38] + ".."
            
            var = ctk.BooleanVar(value=True)
            self.vars[idx] = var
            chk = ctk.CTkCheckBox(self.scroll, text=f"{idx}. {t}", variable=var, font=("Microsoft JhengHei UI", 12))
            chk.pack(anchor="w", pady=2)
            
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="全選", width=80, command=self.select_all).pack(side="left")
        ctk.CTkButton(btn_frame, text="全取消", width=80, command=self.deselect_all).pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="確定", fg_color="#01814A", hover_color="#006030", command=self.on_confirm).pack(side="right")
        
    def select_all(self):
        for var in self.vars.values(): var.set(True)
        
    def deselect_all(self):
        for var in self.vars.values(): var.set(False)
        
    def on_confirm(self):
        selected_indices = [idx for idx, var in self.vars.items() if var.get()]
        if not selected_indices:
            messagebox.showwarning("警告", "請至少選擇一個項目")
            return
        self.result = selected_indices
        self.destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MULTIDownload")
        self.geometry("800x780") 
        
        try:
            if hasattr(sys, '_MEIPASS'):
                 # PyInstaller 打包後的暫存路徑
                 icon_path = os.path.join(sys._MEIPASS, "1.ico")
            else:
                 # 開發環境路徑
                 icon_path = r"C:\mypython\MULTIDownload\icon\1.ico"
            
            if os.path.exists(icon_path):
                 self.iconbitmap(icon_path)
        except Exception: pass 
        
        ctk.set_appearance_mode(DEFAULT_APPEARANCE_MODE)
        
        self.font_family = "Microsoft JhengHei UI" if sys.platform.startswith("win") else "PingFang TC"
        self.font_title = (self.font_family, 14, "bold")
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

        # --- 1. 建立分頁系統 ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(padx=10, pady=(10, 0), fill="both", expand=True)
        self.tab_view._segmented_button.configure(font=self.font_btn)

        self.tab_basic = self.tab_view.add("基本選項")
        self.tab_format = self.tab_view.add("格式/畫質")
        self.tab_sub = self.tab_view.add("字幕")
        self.tab_output = self.tab_view.add("時間裁剪")
        self.tab_adv = self.tab_view.add("進階選項")
        self.tab_tasks = self.tab_view.add("任務列表")
        self.tab_log = self.tab_view.add("系統日誌")
        self.tab_settings = self.tab_view.add("設定")

        self.history_data = [] 
        self.active_task_widgets = {}
        self.selected_playlist_data = [] 
        self.pending_playlist_info = None 

        self.setup_tasks_ui() 


        self.setup_basic_ui()
        
        # Throttling
        self.task_last_update_time = {}
        self.setup_format_ui()
        self.setup_subtitle_ui()
        self.setup_output_ui()
        self.setup_advanced_ui()
        self.setup_log_ui()
        self.setup_settings_ui()

        # --- 2. 建立底部控制區 ---
        self.setup_bottom_controls()
        

        
        # Default tab
        self.tab_view.set("基本選項")

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
        CTkToolTip(self.chk_independent, "勾選後，將不加入排程，直接在背景獨立開始下載。\n適合需要長時間下載的任務(如直播)或臨時想插隊下載一個檔案。")

        # 下載按鈕 (直接開始 - 加入並執行)
        self.btn_download = ctk.CTkButton(
            self.bottom_frame, text="開始下載", width=100, height=35, font=self.font_btn, 
            fg_color="#01814A", hover_color="#006030", command=self.on_start_download
        )
        self.btn_download.grid(row=0, column=3, padx=(5, 5))

        # 加入任務按鈕 (僅加入排程)
        self.btn_add = ctk.CTkButton(
            self.bottom_frame, text="加入任務", width=100, height=35, font=self.font_btn, 
            fg_color="#1F6AA5", hover_color="#144870", command=self.on_add_task
        )
        self.btn_add.grid(row=0, column=4, padx=(5, 0))
        
    def chk_independent_check(self):
        # Helper to update status label
        count = len(self.download_queue)
        msg = f"下載中... (排程等待: {count})" if self.downloading else "準備就緒"
        if not self.downloading and count > 0: msg = f"準備就緒 (排程等待: {count})"
        self.lbl_status.configure(text=msg)

    def setup_basic_ui(self):
        # URL
        ctk.CTkLabel(self.tab_basic, text="影片網址 (URL)", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_url = ctk.CTkEntry(self.tab_basic, width=600, font=self.font_text, placeholder_text="請在此貼上連結...")
        self.entry_url.pack(padx=20, pady=5)
        

        
        # 提示文字移至輸入框下方
        ctk.CTkLabel(self.tab_basic, text="提示：直播影片推薦勾選「獨立執行」，可於背景下載避免卡住排程", font=self.font_small, text_color="#1F6AA5").pack(anchor="w", padx=25, pady=(0, 5))
        
        self.btn_analyze = ctk.CTkButton(self.tab_basic, text="分析網址 (獲取字幕)", font=self.font_btn, command=self.on_fetch_info)
        self.btn_analyze.pack(padx=20, pady=5)
        
        # Playlist Checkbox
        self.var_playlist = ctk.BooleanVar(value=False)
        self.chk_playlist = ctk.CTkCheckBox(self.tab_basic, text="下載完整播放清單 (Playlist)", font=self.font_small, variable=self.var_playlist, command=self.on_playlist_toggle)
        self.chk_playlist.pack(padx=20, pady=5)

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
        
        # 初始化顯示
        self.update_queue_ui()

    def update_queue_ui(self):
        """更新等待中(排程)介面"""
        # 清空目前等待區
        for widget in self.view_waiting.winfo_children():
            widget.destroy()

        # Reset variables
        self.queue_vars = []

        if not self.download_queue:
            ctk.CTkLabel(self.view_waiting, text="目前沒有等待中的任務", text_color="gray", font=self.font_text).pack(pady=20)
        else:
            # Control Frame
            ctrl_frame = ctk.CTkFrame(self.view_waiting, fg_color="transparent")
            ctrl_frame.pack(fill="x", padx=5, pady=(0, 10))
            
            # Select All Checkbox
            self.var_select_all = ctk.BooleanVar(value=False)
            chk_all = ctk.CTkCheckBox(ctrl_frame, text="全選", font=self.font_small, width=60, 
                                      variable=self.var_select_all, command=self.toggle_select_all)
            chk_all.pack(side="left", padx=5)
            
            # Download Selected Button
            ctk.CTkButton(
                ctrl_frame, text="下載選取項目", fg_color="#01814A", hover_color="#006030", font=self.font_btn,
                command=self.start_selected_queue
            ).pack(side="left", fill="x", expand=True, padx=5)
        
        for i, config in enumerate(self.download_queue):
            row = ctk.CTkFrame(self.view_waiting, fg_color=("gray85", "gray25"))
            row.pack(fill="x", pady=2, padx=5)
            
            # Checkbox
            var = ctk.BooleanVar(value=False)
            self.queue_vars.append(var)
            ctk.CTkCheckBox(row, text="", width=24, variable=var, command=self.update_select_all_state).pack(side="left", padx=(10, 0), anchor="n", pady=5)
            
            # Index
            ctk.CTkLabel(row, text=f"{i+1}.", font=self.font_text, width=30).pack(side="left", padx=0, anchor="n", pady=5)
            
            # Info Frame
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=2)
            
            # Determine Display Name & Mode
            display_name = config.get('filename')
            is_using_url_as_title = False
            
            if not display_name:
                default_t = config.get('default_title', '')
                if default_t and default_t not in ["尚未分析", "分析中...", ""]:
                    display_name = default_t
                else:
                    display_name = config['url']
                    is_using_url_as_title = True
            
            if len(display_name) > 50: display_name = display_name[:47] + "..."
            
            # Title
            ctk.CTkLabel(info_frame, text=display_name, font=("Microsoft JhengHei UI", 12, "bold"), anchor="w").pack(fill="x")
            
            # URL (Show only if different from display_name AND didn't fallback to URL)
            if config['url'] != display_name and not is_using_url_as_title:
                url_text = config['url']
                if len(url_text) > 60: url_text = url_text[:57] + "..."
                ctk.CTkLabel(info_frame, text=url_text, text_color="gray", font=("Consolas", 10), anchor="w").pack(fill="x")
            
            # Task Details (Format, Subs, Cut)
            meta_parts = []
            ext = config['ext']
            if config.get('is_audio_only'):
                # Audio: mp3 (320kbps)
                 qual = config.get('audio_qual', 'Best').split(' ')[0]
                 codec = config.get('audio_codec', 'Auto').split(' ')[0]
                 meta = f"{ext} ({qual})"
                 if codec and codec != "Auto": meta += f" [{codec}]"
                 meta_parts.append(meta)
            else:
                # Video: mp4 (1080p) [H.264] + Audio (192kbps) [AAC]
                res = config.get('video_res', 'Best').split(' ')[0]
                
                # Video part
                v_meta = f"{ext} ({res})"
                if config.get('use_h264_legacy'): v_meta += " [H.264]"
                
                # Audio part (for video downloads)
                a_qual = config.get('audio_qual', 'Best').split(' ')[0]
                a_codec = config.get('audio_codec', 'Auto').split(' ')[0]
                
                a_meta = ""
                is_default_audio = (a_qual == "Best" and a_codec == "Auto")
                
                if not is_default_audio:
                    a_meta = f" + ({a_qual})"
                    if a_codec != "Auto": a_meta += f" [{a_codec}]"
                
                meta_parts.append(v_meta + a_meta)
            
            # 2. Tags
            if config.get('sub_langs'): meta_parts.append("字幕")
            if config.get('use_time_range'): meta_parts.append("時間裁剪")
            
            details_text = " | ".join(meta_parts)
            ctk.CTkLabel(info_frame, text=details_text, text_color="#888888", font=self.font_small, anchor="w").pack(fill="x")


            ctk.CTkButton(
                row, text="✕", width=30, height=20, fg_color="transparent", hover_color="#8B0000", text_color="red", 
                command=lambda idx=i: self.remove_from_queue(idx)
            ).pack(side="right", padx=10)


        
    def toggle_select_all(self):
        val = self.var_select_all.get()
        for var in self.queue_vars:
            var.set(val)

    def update_select_all_state(self):
        if not self.queue_vars: return
        all_checked = all(var.get() for var in self.queue_vars)
        self.var_select_all.set(all_checked)

    def start_selected_queue(self):
        indices = [i for i, var in enumerate(self.queue_vars) if var.get()]
        if not indices:
            return messagebox.showwarning("提示", "請先勾選要下載的任務")
            
        indices.sort(reverse=True)
        
        for i in indices:
            if i < len(self.download_queue):
                config = self.download_queue.pop(i)
                self._start_core_download(config)
        
        self.update_queue_ui()

    def remove_from_queue(self, index):
        """從排程中移除任務"""
        if 0 <= index < len(self.download_queue):
            removed = self.download_queue.pop(index)
            self.log(f"已移除排程: {removed['url']}")
            self.update_queue_ui()
            self.chk_independent_check()

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
        
        # 畫質與相容性組合
        res_frame = ctk.CTkFrame(self.tab_format, fg_color="transparent")
        res_frame.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        
        self.combo_video_res = ctk.CTkOptionMenu(res_frame, values=["Best (最高畫質)", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"], **option_style)
        self.combo_video_res.pack(side="left", fill="x", expand=True)
        
        # 新增 H.264 開關
        self.var_video_legacy = ctk.BooleanVar(value=False)
        self.chk_legacy = ctk.CTkCheckBox(res_frame, text="H.264 (相容模式)", font=self.font_small, variable=self.var_video_legacy, command=self.update_dynamic_hint)
        self.chk_legacy.pack(side="right", padx=(10, 0))
        
        # 加入 Tooltip 解釋
        CTkToolTip(self.chk_legacy, "勾選後，將強制優先下載 H.264 編碼的影片(最高1080p)，\n以確保在 Windows 內建播放器能直接播放。\n若不勾選，可能會下載 AV1/VP9 (高畫質)，在舊電腦可能無法播放。")

        ctk.CTkLabel(self.tab_format, text="音訊品質", font=self.font_title).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.combo_audio_quality = ctk.CTkOptionMenu(self.tab_format, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps (標準)(yt最佳)", "96 kbps (較低)", "64 kbps (省空間)"], command=lambda _: self.update_dynamic_hint(), **option_style)
        self.combo_audio_quality.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.tab_format, text="音訊編碼", font=self.font_title).grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.combo_audio_codec = ctk.CTkOptionMenu(self.tab_format, values=["Auto (預設/Opus)", "AAC (車用/相容性高)"], command=lambda _: self.update_dynamic_hint(), **option_style)
        self.combo_audio_codec.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        self.lbl_format_hint = ctk.CTkLabel(self.tab_format, text="提示：若車用音響無聲音，請在「音訊編碼」選擇 AAC", font=self.font_small, text_color="#1F6AA5")
        self.lbl_format_hint.grid(row=5, column=0, columnspan=2, padx=20, pady=20)

    def on_format_change(self, choice):
        # 1. 無損音訊 (flac/wav) -> 鎖定畫質與編碼 (不建議轉碼)
        if "無損" in choice:
            self.combo_video_res.set("N/A")
            self.combo_video_res.configure(state="disabled")
            
            # 鎖定 H.264 (影片專用)
            self.chk_legacy.deselect()
            self.chk_legacy.configure(state="disabled")

            self.combo_audio_codec.set("Auto (來源預設)")

        
        # 2. 一般純音訊 (mp3/m4a) -> 鎖定畫質，但開放編碼 (允許強制轉 AAC)
        elif "純音訊" in choice:
            self.combo_video_res.set("N/A")
            self.combo_video_res.configure(state="disabled")
            
            # 鎖定 H.264 (影片專用)
            self.chk_legacy.deselect()
            self.chk_legacy.configure(state="disabled")
            


        # 3. 影片模式 -> 全部開放
        else:
            self.combo_video_res.configure(state="normal")
            self.combo_video_res.set("Best (最高畫質)")
            
            # 開放 H.264
            self.chk_legacy.configure(state="normal")

            
            self.update_dynamic_hint()

    def update_dynamic_hint(self):
        choice = self.combo_format.get()
        
        if self.var_video_legacy.get():
             current = self.combo_audio_codec.get()
             if not current.startswith("AAC"):
                 self.combo_audio_codec.set("AAC (車用/相容性高)")
             self.combo_audio_codec.configure(state="disabled")
        else:
             if "無損" in choice:
                 self.combo_audio_codec.configure(state="disabled")
             else:
                 self.combo_audio_codec.configure(state="normal")

        hint = f"提示：將下載 {choice.split(' ')[0]} 格式"

        if "純音訊" in choice:
             hint = f"提示：已選擇 {choice.split(' ')[0]} 格式，若需車用相容性可手動指定 AAC"
        elif "無損" in choice:
             hint = "提示：無損模式下不建議進行額外編碼轉換"
        else:
            if self.var_video_legacy.get():
                hint = "提示：相容模式已開啟 (H.264 + AAC)，確保所有裝置皆可播放"
            elif self.combo_audio_codec.get().startswith("AAC"):
                hint = "提示：將優先使用 AAC 音訊編碼 (提升車用與舊裝置相容性)"
            else:
                hint = f"提示：將下載 {choice.split(' ')[0]} 格式 (自動最佳品質)"
        
        
        qual = self.combo_audio_quality.get()
        if "Best" not in qual and "無損" not in choice:
             hint += "\n(注意：在無更高品質時，強制設定位元率只會增加檔案大小無法提升原始音質)"

        self.lbl_format_hint.configure(text=hint)

    def setup_subtitle_ui(self):
        self.lbl_sub_hint = ctk.CTkLabel(self.tab_sub, text="請先在［基本選項］點擊「分析網址」以載入字幕列表", font=self.font_small, text_color="gray")
        self.lbl_sub_hint.pack(pady=10)
        self.scroll_subs = ctk.CTkScrollableFrame(self.tab_sub, label_text=None)
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=10)
        self.sub_checkboxes = {}

        manual_frame = ctk.CTkFrame(self.tab_sub, fg_color="transparent")
        manual_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(manual_frame, text="歌單/通用字幕設定 (若無分析):", font=self.font_title).pack(anchor="w", pady=(5,5))
        
        self.pl_sub_vars = {
            'zh-TW': ctk.BooleanVar(value=False),
            'zh-Hans': ctk.BooleanVar(value=False),
            'en': ctk.BooleanVar(value=False),
            'ja': ctk.BooleanVar(value=False),
            'ko': ctk.BooleanVar(value=False)
        }
        
        chk_frame = ctk.CTkFrame(manual_frame, fg_color="transparent")
        chk_frame.pack(anchor="w", padx=10)
        
        ctk.CTkCheckBox(chk_frame, text="繁體中文", variable=self.pl_sub_vars['zh-TW'], width=80, font=self.font_text).pack(side="left", padx=5)
        ctk.CTkCheckBox(chk_frame, text="簡體中文", variable=self.pl_sub_vars['zh-Hans'], width=80, font=self.font_text).pack(side="left", padx=5)
        ctk.CTkCheckBox(chk_frame, text="英文", variable=self.pl_sub_vars['en'], width=60, font=self.font_text).pack(side="left", padx=5)
        ctk.CTkCheckBox(chk_frame, text="日文", variable=self.pl_sub_vars['ja'], width=60, font=self.font_text).pack(side="left", padx=5)
        ctk.CTkCheckBox(chk_frame, text="韓文", variable=self.pl_sub_vars['ko'], width=60, font=self.font_text).pack(side="left", padx=5)
        
        CTkToolTip(chk_frame, "當下載「播放清單」或未執行分析時，將嘗試下載此處勾選的語言。\n(若該影片有此語言則下載，沒有則跳過)")
        
        manual_bg = ctk.CTkFrame(manual_frame, fg_color="transparent")
        manual_bg.pack(anchor="w", padx=10, pady=(5,0))
        
        self.var_sub_manual = ctk.BooleanVar()
        def toggle_manual_entry():
            self.entry_sub_manual.configure(state="normal" if self.var_sub_manual.get() else "disabled")
            
        ctk.CTkCheckBox(manual_bg, text="其他 (自訂):", variable=self.var_sub_manual, command=toggle_manual_entry, width=100, font=self.font_text).pack(side="left", padx=5)
        
        self.entry_sub_manual = ctk.CTkEntry(manual_bg, width=120, placeholder_text="代碼 (如: th, vi)", state="disabled")
        self.entry_sub_manual.pack(side="left", padx=5)
        
        ctk.CTkButton(manual_bg, text="查詢代碼表", width=80, height=24, fg_color="#555555", command=self.open_lang_table).pack(side="left", padx=10)

    def open_lang_table(self):
        top = ctk.CTkToplevel(self)
        top.title("語言代碼對照表")
        top.geometry("400x600")
        
        top.transient(self)
        
        ctk.CTkLabel(top, text="支援的語言代碼", font=("Microsoft JhengHei UI", 14, "bold")).pack(pady=10)
        
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        sorted_langs = sorted(CODE_TO_NAME.items(), key=lambda x: x[0])
        
        for code, name in sorted_langs:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=code, width=60, anchor="w", font=("Consolas", 11, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", padx=5)

    def setup_output_ui(self):
        self.var_cut = ctk.BooleanVar(value=False)
        self.chk_cut = ctk.CTkCheckBox(self.tab_output, text="啟用時間裁剪", font=self.font_title, variable=self.var_cut, command=self.toggle_time_inputs)
        self.chk_cut.pack(anchor="w", padx=20, pady=20)
        
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
        self.rb_live_now = ctk.CTkRadioButton(self.tab_output, text="從現在開始", font=self.font_text, variable=self.var_live_mode, value="now")
        self.rb_live_now.pack(anchor="w", padx=40, pady=5)
        self.rb_live_start = ctk.CTkRadioButton(self.tab_output, text="從頭開始", font=self.font_text, variable=self.var_live_mode, value="start")
        self.rb_live_start.pack(anchor="w", padx=40, pady=5)

    def on_playlist_toggle(self):
        """歌單模式時禁用不相關選項"""
        state = "disabled" if self.var_playlist.get() else "normal"
        
        # 1. Filename (Playlist uses auto naming)
        self.entry_filename.configure(state=state)
        if state == "disabled": self.entry_filename.configure(placeholder_text="播放清單模式下將自動命名")
        else: self.entry_filename.configure(placeholder_text="例如: MyVideo (無需輸入副檔名)")
        
        # 2. Time Cut
        self.chk_cut.configure(state=state)
        if state == "disabled": 
            self.chk_cut.deselect()
            self.toggle_time_inputs() 
            
        # 3. Live Options
        self.rb_live_now.configure(state=state)
        self.rb_live_start.configure(state=state)

        # 4. Start Download Button & Independent Checkbox
        self.btn_start.configure(state=state, fg_color="gray" if state == "disabled" else "#01814A")
        
        if hasattr(self, 'chk_independent'):
            self.chk_independent.configure(state=state)
            if state == "disabled": self.var_independent.set(False)

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
            webbrowser.open("https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
            
        lbl_link = ctk.CTkLabel(file_title_frame, text="[下載 Chrome/Edge 擴充]", text_color="#3B8ED0", cursor="hand2", font=self.font_small)
        lbl_link.pack(side="left", padx=5)
        lbl_link.bind("<Button-1>", open_ext_link)
        lbl_link.bind("<Enter>", lambda e: lbl_link.configure(text_color="#1F6AA5")) 
        lbl_link.bind("<Leave>", lambda e: lbl_link.configure(text_color="#3B8ED0"))
        
        def open_firefox_link(event=None):
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
        ctk.CTkRadioButton(file_frame, text="檔案路徑", font=self.font_text, variable=self.var_cookie, value="file").pack(side="left", padx=(20, 10))
        self.entry_cookie_path = ctk.CTkEntry(file_frame, font=self.font_text, placeholder_text="請選擇 cookies.txt...")
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=10)
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(file_frame, text="瀏覽", width=80, font=self.font_btn, command=self.browse_cookie_file).pack(side="right")



        # Max Concurrent Settings
        ctk.CTkLabel(self.tab_adv, text="最大同時下載任務數", font=self.font_title).pack(anchor="w", padx=20, pady=(20, 10))
        
        # 定義統一樣式 (參考 setup_format_ui)
        option_style = {
            "fg_color": "#3E3E3E", "button_color": "#505050", "button_hover_color": "#606060",
            "dropdown_fg_color": "#2B2B2B", "dropdown_hover_color": "#1F6AA5", "dropdown_text_color": "#FFFFFF",
            "font": self.font_btn, "dropdown_font": self.font_btn, "text_color": "#FFFFFF", 
        }

        # 改用下拉選單 (Combobox)
        concurrent_options = [str(i) for i in range(1, 11)]
        self.combo_concurrent = ctk.CTkOptionMenu(
            self.tab_adv, 
            values=concurrent_options, 
            command=self.on_concurrent_change,
            width=200, 
            **option_style
        )
        self.combo_concurrent.set("1") 
        self.combo_concurrent.pack(anchor="w", padx=20, pady=5)

    def on_concurrent_change(self, value):
        self.max_concurrent_downloads = int(value)
        self.check_queue()

    # --- 任務整合介面 (Setup Tasks UI) ---
    def setup_tasks_ui(self):
        # 1. Segmented Control for tabs
        self.task_view_mode = ctk.StringVar(value="active")
        self.task_segmented = ctk.CTkSegmentedButton(
            self.tab_tasks, 
            values=["等待中", "進行中", "已完成"], 
            variable=self.task_view_mode,
            command=self.switch_task_view,
            font=self.font_btn
        )
        self.task_segmented.pack(pady=10, padx=10, fill="x")
        self.task_segmented.set("進行中") 

        # 2. Waiting View (排程等待) - Default Hidden
        self.view_waiting = ctk.CTkScrollableFrame(self.tab_tasks, fg_color="transparent")
        
        # 3. Active View (執行中) - Default Visible
        self.view_active = ctk.CTkScrollableFrame(self.tab_tasks, fg_color="transparent")
        self.lbl_active_empty = ctk.CTkLabel(self.view_active, text="目前沒有執行中的任務", text_color="gray", font=self.font_text)
        self.lbl_active_empty.pack(pady=20)
        self.view_active.pack(fill="both", expand=True, padx=10, pady=10)

        # 4. Finished View (已完成) - Default Hidden
        self.view_finished = ctk.CTkScrollableFrame(self.tab_tasks, fg_color="transparent")
        self.lbl_finished_empty = ctk.CTkLabel(self.view_finished, text="目前沒有已完成的紀錄", text_color="gray", font=self.font_text)
        self.lbl_finished_empty.pack(pady=20)
        
        self.btn_clear_history = ctk.CTkButton(self.tab_tasks, text="清除歷史紀錄", fg_color="gray", font=self.font_btn, command=self.clear_history)

    def switch_task_view(self, value):
        self.view_waiting.pack_forget()
        self.view_active.pack_forget()
        self.view_finished.pack_forget()
        self.btn_clear_history.pack_forget()

        if value == "等待中":
            self.view_waiting.pack(fill="both", expand=True, padx=10, pady=5)
        elif value == "進行中":
            self.view_active.pack(fill="both", expand=True, padx=10, pady=5)
        elif value == "已完成":
            self.view_finished.pack(fill="both", expand=True, padx=10, pady=5)
            self.btn_clear_history.pack(pady=10)

    def create_active_task_widget(self, task_id, config, initial_status="準備中..."):
        row = ctk.CTkFrame(self.view_active)
        row.pack(fill="x", pady=5, padx=5)

    
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=5)

        btn_cancel = ctk.CTkButton(btn_frame, text="中止", width=50, fg_color="#DB3E39", hover_color="#8B0000", 
                                   command=lambda: self.cancel_task(task_id))
        btn_cancel.pack(side="left", padx=2)

        progress = ctk.CTkProgressBar(row, height=12, width=150) 
        progress.pack(side="right", padx=10, pady=15)
        progress.set(0)

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        
        display_name = config.get('filename')
        is_using_url_as_title = False
        
        if not display_name:
            default_t = config.get('default_title', '')
            if default_t and default_t not in ["尚未分析", "分析中...", ""]:
                display_name = default_t
            else:
                display_name = config['url']
                is_using_url_as_title = True
        
        if len(display_name) > 60: display_name = display_name[:57] + "..."
        
        lbl_title = ctk.CTkLabel(info_frame, text=display_name, font=("Microsoft JhengHei UI", 13, "bold"), anchor="w")
        lbl_title.pack(fill="x")
        
        if config['url'] != display_name and not is_using_url_as_title:
            url_text = config['url']
            if len(url_text) > 70: url_text = url_text[:67] + "..."
            lbl_url = ctk.CTkLabel(info_frame, text=url_text, text_color="gray", font=("Consolas", 10), anchor="w")
            lbl_url.pack(fill="x")
            
            lbl_url.bind("<Double-Button-1>", lambda e: self.toggle_pause_task(task_id))
        else:
             lbl_url = None 
        
        lbl_status = ctk.CTkLabel(info_frame, text=initial_status, text_color="#2CC985", font=("Consolas", 12), anchor="w")
        lbl_status.pack(fill="x")
    
        def on_double_click(event):
            self.toggle_pause_task(task_id)
            
        widgets_to_bind = [row, info_frame, lbl_title, lbl_status]
        
        for widget in widgets_to_bind:
            widget.bind("<Double-Button-1>", on_double_click)

        self.active_task_widgets[task_id] = {
            'row': row,
            'lbl_status': lbl_status,
            'progress': progress,
            'btn_cancel': btn_cancel,
            'lbl_title': lbl_title,
            'lbl_url': lbl_url
        }

    def _update_task_buttons(self, task_id, state):
        if task_id not in self.active_task_widgets: 
            return
        w = self.active_task_widgets[task_id]
        
        if state == "paused":
            w['progress'].configure(mode="determinate")

    def toggle_pause_task(self, task_id):
        # 排程任務
        if task_id in self.active_queue_tasks:
            task_info = self.active_queue_tasks[task_id]
            if task_info['status'] == 'running':
                task_info['status'] = 'paused'
                self.log(f"暫停任務: {task_info['config']['url']}")
                try: 
                    task_info['core'].stop_download()
                except: pass

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
                 w = self.active_task_widgets[task_id]
                 w['lbl_status'].configure(text="正在中止...", text_color="#DB3E39")
                 w['btn_cancel'].configure(state="disabled", text="...")
             except: pass

        if task_id in self.active_queue_tasks:
             self.active_queue_tasks[task_id]['status'] = 'cancelled'
             try: 
                self.active_queue_tasks[task_id]['core'].stop_download()
             except: pass
        elif task_id in self.bg_tasks:
             self.stop_background_task(task_id)
        
    
    def remove_active_task_widget(self, task_id):
        if task_id in self.active_task_widgets:
            self.active_task_widgets[task_id]['row'].destroy()
            del self.active_task_widgets[task_id]
            
        if not self.active_task_widgets:
            self.lbl_active_empty.pack(pady=20)

    def update_task_widget(self, task_id, percent, msg):
        def _update():
            if task_id in self.active_task_widgets:
                w = self.active_task_widgets[task_id]
                try:
                    if not w['lbl_status'].winfo_exists(): return
                    
                    w['lbl_status'].configure(text=msg)
                    if percent == -1:
                        w['progress'].configure(mode="indeterminate")
                        w['progress'].start()
                    else:
                        w['progress'].configure(mode="determinate")
                        try: w['progress'].stop()
                        except: pass
                        w['progress'].set(percent)
                except Exception as e:
                    print(f"UI Update Error: {e}")
        
        self.after(0, _update)

    def add_history_item(self, config, success, msg):
        self.history_data.append({'config': config, 'success': success, 'msg': msg})
        self.render_history_item(config, success, msg)

    def render_history_item(self, config, success, msg):
        self.lbl_finished_empty.pack_forget()
        
        row = ctk.CTkFrame(self.view_finished, fg_color=("gray90", "gray20"))
        row.pack(fill="x", pady=2, padx=5)
        
        status_color = "#01814A" if success else "#DB3E39"
        status_text = "✔" if success else "✗"
        ctk.CTkLabel(row, text=status_text, text_color=status_color, width=50, font=("Yes", 12, "bold")).pack(side="left", padx=5, anchor="n", pady=5)
        
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=2)
        
        display_name = config.get('filename')
        is_using_url_as_title = False
        
        if not display_name:
            default_t = config.get('default_title', '')
            if default_t and default_t not in ["尚未分析", "分析中...", ""]:
                display_name = default_t
            else:
                display_name = config['url']
                is_using_url_as_title = True

        trunc_name = (display_name[:50] + '..') if len(display_name) > 50 else display_name
        ctk.CTkLabel(info_frame, text=trunc_name, font=("Microsoft JhengHei UI", 12, "bold"), anchor="w").pack(anchor="w", fill="x")
        
        if config['url'] != display_name and not is_using_url_as_title:
            trunc_url = config['url']
            if len(trunc_url) > 60: trunc_url = trunc_url[:57] + ".."
            ctk.CTkLabel(info_frame, text=trunc_url, text_color="gray", font=("Consolas", 10), anchor="w").pack(anchor="w", fill="x")

        meta_parts = []
        ext = config['ext']
        if config.get('is_audio_only'):
             # Audio: mp3 (320kbps)
             qual = config.get('audio_qual', 'Best').split(' ')[0]
             codec = config.get('audio_codec', 'Auto').split(' ')[0]
             meta = f"{ext} ({qual})"
             if codec and codec != "Auto": meta += f" [{codec}]"
             meta_parts.append(meta)
        else:
            # Video: mp4 (1080p) [H.264] + Audio (192kbps) [AAC]
            res = config.get('video_res', 'Best').split(' ')[0]
            
            # Video part
            v_meta = f"{ext} ({res})"
            if config.get('use_h264_legacy'): v_meta += " [H.264]"
            
            # Audio part (for video downloads)
            a_qual = config.get('audio_qual', 'Best').split(' ')[0]
            a_codec = config.get('audio_codec', 'Auto').split(' ')[0]
            
            a_meta = ""
            # Only show audio details if user selected specific settings (not default Best/Auto)
            is_default_audio = (a_qual == "Best" and a_codec == "Auto")
            
            if not is_default_audio:
                a_meta = f" + ({a_qual})"
                if a_codec != "Auto": a_meta += f" [{a_codec}]"
            
            meta_parts.append(v_meta + a_meta)
        
        if config.get('sub_langs'): meta_parts.append("字幕")
        if config.get('use_time_range'): meta_parts.append("時間裁剪")

        final_msg = msg
        if success:
             final_msg = " | ".join(meta_parts)
             
        trunc_msg = (final_msg[:80] + '..') if len(final_msg) > 80 else final_msg
        
        msg_color = "#888888" if success else "#DB3E39"
        ctk.CTkLabel(info_frame, text=trunc_msg, text_color=msg_color, font=self.font_small, anchor="w").pack(anchor="w", fill="x")

        action_frame = ctk.CTkFrame(row, fg_color="transparent")
        action_frame.pack(side="right", padx=5)

        save_path = config.get('save_path', '')
        if success and save_path:
             ctk.CTkButton(action_frame, text="開啟", width=50, height=25, font=self.font_small, 
                           command=lambda p=save_path: self.safe_open_path(p)).pack(side="right", padx=2)
        
        ctk.CTkButton(action_frame, text="✕", width=25, height=25, fg_color="transparent", text_color="gray", 
                      command=lambda w=row: w.destroy()).pack(side="right", padx=2)

    def clear_history(self):
        for widget in self.view_finished.winfo_children():
            if widget != self.lbl_finished_empty:
                widget.destroy()
        self.lbl_finished_empty.pack(pady=20)
        self.history_data = []

    def safe_open_path(self, path):
         if os.path.exists(path): os.startfile(path)
         else: messagebox.showerror("錯誤", f"找不到路徑:\n{path}")

    def stop_background_task(self, task_id):
        if task_id in self.bg_tasks:
            try: self.bg_tasks[task_id]['core'].stop_download()
            except: pass
            self.bg_tasks.pop(task_id)
            self.log(f"已手動停止背景任務: {task_id}")
            self.remove_active_task_widget(task_id)

    def setup_log_ui(self):
        self.textbox_log = ctk.CTkTextbox(self.tab_log, state="disabled", font=("Consolas", 12))
        self.textbox_log.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        btn_clear = ctk.CTkButton(self.tab_log, text="清空日誌", width=100, height=30, 
                                  fg_color="gray", hover_color="#555555", font=self.font_btn,
                                  command=self.clear_log)
        btn_clear.pack(pady=(0, 10), anchor="e", padx=10)

    def clear_log(self):
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.configure(state="disabled")

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
        
        # Playlist Detection
        if "list=" in url:
            is_playlist = messagebox.askyesno("播放清單偵測", "偵測到此網址包含播放清單\n\n是否要下載『整張歌單』\n(選擇「否」將僅下載此影片)")
            self.var_playlist.set(is_playlist)
            
            if is_playlist:
                 self.show_toast("清單讀取中... ", duration=3000, color="#BEBEBE")
                 self.log(f"正在分析播放清單: {url}")
                 self.selected_playlist_data = []
                 c_type = self.var_cookie.get()
                 c_path = self.entry_cookie_path.get().strip()
                 threading.Thread(target=self._run_playlist_check, args=(url, c_type, c_path), daemon=True).start()
                 return

        c_type = self.var_cookie.get()
        c_path = self.entry_cookie_path.get().strip()
        self.show_toast("正在分析字幕...", color="#BEBEBE")
        self.log(f"正在分析: {url}")
        threading.Thread(target=self._run_fetch, args=(url, c_type, c_path), daemon=True).start()

    def _run_playlist_check(self, url, c_type, c_path):
        # 快速分析清單 (不抓詳細字幕)
        info = self.core.fetch_playlist_info(url, cookie_type=c_type, cookie_path=c_path)
        
        def _update_pl_ui():
            if 'error' in info:
                self.show_toast("清單分析失敗", color="#FF2D2D")
                self.log(f"清單錯誤: {info['error']}")
            else:
                title = info.get('title', '未知清單')
                count = info.get('count', '?')
                self.show_toast(f"清單分析完成 ({count} 部影片)")
                self.log(f"已獲取清單: {title} (共 {count} 部)")
                
                
                if 'items' in info and info['items']:
                    self.pending_playlist_info = info
                    self.show_toast("清單已就緒！\n設定格式後->「加入任務」", duration=4000)
                    self.log(f"清單分析完成，等待使用者加入任務...")
                else:
                    self.pending_playlist_info = None
                    messagebox.showinfo("歌單模式", f"已讀取清單：{title}\n\n注意：此清單無法解析內容，將預設下載全部。")
        
        self.after(0, _update_pl_ui)

    def _run_fetch(self, url, c_type, c_path):
        info = self.core.fetch_video_info(url, cookie_type=c_type, cookie_path=c_path)
        
        def _update_ui():
            if 'error' in info:
                self.show_toast("分析失敗", color="#FF2D2D")
                err_msg = info['error']
                self.log(f"錯誤: {err_msg}")
                
                if err_msg == "CORE_MISSING":
                    messagebox.showerror("核心遺失", "未安裝 yt-dlp 核心組件！\n無法進行分析或下載。\n\n請稍後在「設定」頁面點擊「檢查並更新」安裝。")
                    self.tab_view.set("設定")
                    
                elif "Sign in" in err_msg: messagebox.showwarning("驗證失敗", "YouTube 拒絕連線。\n請到 [高級選項] 勾選瀏覽器後再試一次。")
            else:
                if info['subtitles']:
                    self.show_toast("分析完成！")
                else:
                    self.show_toast("分析完成 (無字幕)")
                
                self.log(f"已獲取資訊: {info['title']}")
                self.after(50, lambda: self.update_subtitles_ui(info['subtitles']))
        
        self.after(0, _update_ui)

    def update_subtitles_ui(self, sub_list):
        self.last_loaded_subtitles = sorted(sub_list) if sub_list else []

        for widget in self.scroll_subs.winfo_children(): widget.destroy()
        self.sub_checkboxes.clear()
        
        # Scenario 1: No subtitles found
        if not sub_list: 
             self.scroll_subs.pack_forget()
             
             if hasattr(self, 'lbl_sub_hint') and self.lbl_sub_hint.winfo_exists():
                 self.lbl_sub_hint.configure(text="此影片未提供字幕 (或無法獲取)", text_color="#FF5555")
                 self.lbl_sub_hint.pack(pady=10)
             return

        # Scenario 2: Has subtitles -> Hide the hint label, show scroll
        if hasattr(self, 'lbl_sub_hint') and self.lbl_sub_hint.winfo_exists():
            self.lbl_sub_hint.pack_forget()
        
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=10)

        PRIORITY_LANGS = ['zh-TW', 'zh-Hant', 'zh-HK', 'zh-Hans', 'zh-CN', 'en', 'en-US', 'en-GB', 'ja', 'ko']
        priority_matches = []
        other_matches = []
        for code in sub_list:
            if code in PRIORITY_LANGS: priority_matches.append(code)
            else: other_matches.append(code)
        
        priority_matches.sort(key=lambda x: PRIORITY_LANGS.index(x))
        other_matches.sort()

        def create_chk(parent, code):
            lang_name = CODE_TO_NAME.get(code)
            display_text = f"★ [{code}] {lang_name}" if lang_name and code in PRIORITY_LANGS else (f"[{code}] {lang_name}" if lang_name else f"[{code}] (未知語言)")
            if len(display_text) > 20: display_text = display_text[:18] + ".."
            
            var = ctk.BooleanVar()
            self.sub_checkboxes[code] = var
            return ctk.CTkCheckBox(parent, text=display_text, variable=var, font=self.font_text, width=20) 

        if priority_matches:
            ctk.CTkLabel(self.scroll_subs, text="推薦", text_color="#1F6AA5", font=self.font_small).pack(anchor="w", padx=10, pady=(5,0))
            for code in priority_matches:
                create_chk(self.scroll_subs, code).pack(anchor="w", padx=10, pady=2)

        # Divider
        if priority_matches and other_matches: 
            ctk.CTkFrame(self.scroll_subs, height=2, fg_color="#555555").pack(fill="x", padx=10, pady=10)

        # Add Other Subs (Grid Layout)
        if other_matches:
            if priority_matches: 
                ctk.CTkLabel(self.scroll_subs, text="其他", text_color="#1F6AA5", font=self.font_small).pack(anchor="w", padx=10, pady=(5,0))
            
            cols = 4
            current_row_frame = None
            
            for i, code in enumerate(other_matches):
                if i % cols == 0:
                    current_row_frame = ctk.CTkFrame(self.scroll_subs, fg_color="transparent")
                    current_row_frame.pack(fill="x", padx=5, pady=2)
                
                cell_frame = ctk.CTkFrame(current_row_frame, width=170, height=30, fg_color="transparent")
                cell_frame.pack_propagate(False) 
                cell_frame.pack(side="left", padx=5)
                
                chk = create_chk(cell_frame, code)
                chk.pack(side="left", anchor="w")


        # 6. Finally, switch the view atomically
        pass 
        
    def get_selected_subs(self):
        selected = [lang for lang, var in self.sub_checkboxes.items() if var.get()]
        
        if hasattr(self, 'pl_sub_vars'):
             for code, var in self.pl_sub_vars.items():
                 if var.get(): selected.append(code)

        if hasattr(self, 'var_sub_manual') and self.var_sub_manual.get():
            txt = self.entry_sub_manual.get().strip()
            if txt:
                parts = txt.replace(',', ' ').split()
                for p in parts:
                    clean_code = p.strip()
                    if clean_code: selected.append(clean_code)
        
        seen = set()
        unique_selected = []
        for x in selected:
            if x not in seen:
                unique_selected.append(x)
                seen.add(x)
        selected = unique_selected
        
        PRIORITY_LANGS = ['zh-TW', 'zh-Hant', 'zh-Hans', 'zh-CN', 'en', 'en-US', 'en-GB', 'ja', 'ko']
        
        def sort_key(lang):
            if lang in PRIORITY_LANGS:
                return PRIORITY_LANGS.index(lang)
            return 999 
            
        selected.sort(key=sort_key) 
        
        return selected

    def get_config_from_ui(self):
        url = self.entry_url.get().strip()
        if not url: 
            messagebox.showwarning("提示", "網址不能為空")
            return None

        raw_path = self.entry_path.get().strip()
        final_save_path = raw_path if raw_path else app_path

        raw_format = self.combo_format.get() 
        selected_ext = raw_format.split(' ')[0]
        is_audio_only = selected_ext in ['mp3', 'm4a', 'wav', 'flac']
        
        config = {
            'url': url,
            'save_path': final_save_path,
            'filename': self.entry_filename.get().strip(),
            'ext': self.combo_format.get().split(' ')[0],
            'is_audio_only': is_audio_only,
            'video_res': self.combo_video_res.get(),
            'audio_qual': self.combo_audio_quality.get(),
            'audio_codec': self.combo_audio_codec.get(),
            'use_time_range': self.var_cut.get(),
            'start_time': self.entry_start.get().strip(),
            'end_time': self.entry_end.get().strip(),
            'use_h264_legacy': self.var_video_legacy.get(), 
            'playlist_mode': self.var_playlist.get(),       
            'sub_langs': self.get_selected_subs(),
            'cookie_type': self.var_cookie.get(),
            'cookie_path': self.entry_cookie_path.get().strip(),
            'is_live': False,
            'live_from_start': (self.var_live_mode.get() == 'start'),
        }
        return config

    def on_add_task(self):
        base_config = self.get_config_from_ui()
        if not base_config: return
        
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
                
                self.download_queue.append(task_config)
            
            self.log(f"已加入 {count} 個任務至排程")
            
            self.selected_playlist_data = []
            
            self.entry_url.delete(0, "end")
            self.entry_filename.delete(0, "end")
            self.var_playlist.set(False) 
            self.on_playlist_toggle() 
            
            self.update_queue_ui()
            
            self.tab_view.set("任務列表")
            self.task_segmented.set("等待中")
            self.switch_task_view("等待中")
            
            return

        current_def_title = base_config.get('default_title', '')
        if not base_config.get('filename') and (not current_def_title or current_def_title in ["尚未分析", "分析中..."]):
             base_config['default_title'] = "正在獲取標題..." 
             threading.Thread(target=self._auto_fetch_title, args=(base_config,), daemon=True).start()

        # 加入佇列
        self.download_queue.append(base_config)
        self.log(f"已加入排程: {base_config['url']}")
        self.update_queue_ui()
        
        # Show Toast
        self.show_toast("任務加入成功")
        
        # 清空輸入與重置分析狀態
        self.entry_url.delete(0, "end")
        self.entry_filename.delete(0, "end")
        self.update_subtitles_ui([]) 

    def _auto_fetch_title(self, config):
        """Background thread to fetch title for waiting tasks"""
        core = YtDlpCore()
        try:
            info = core.fetch_video_info(config['url'], config['cookie_type'], config['cookie_path'])
            
            if info and 'title' in info and info['title'] != '未知標題':
                config['default_title'] = info['title']
            else:
                config['default_title'] = "" 
            
            self.after(0, self.update_queue_ui)
        except: 
            config['default_title'] = ""
            self.after(0, self.update_queue_ui)

    def show_toast(self, message, duration=2000, color="#01814A"):
        if hasattr(self, 'current_toast') and self.current_toast:
            try: self.current_toast.destroy()
            except: pass
            
        toast = ctk.CTkToplevel(self)
        self.current_toast = toast 
        
        toast.overrideredirect(True) 
        
        x = self.winfo_x() + self.winfo_width() - 220
        y = self.winfo_y() + 85
        toast.geometry(f"200x50+{x}+{y}")
        toast.attributes("-alpha", 1.0)
        toast.attributes("-topmost", True)
        
        frame = ctk.CTkFrame(toast, fg_color=color, corner_radius=10)
        frame.pack(fill="both", expand=True)
        
        label = ctk.CTkLabel(frame, text=message, text_color="white", font=("Microsoft JhengHei UI", 14, "bold"))
        label.pack(expand=True)
        
        toast.update_idletasks()
        
        def close_toast():
            try: toast.destroy()
            except: pass
            
        self.after(duration, close_toast)

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
            self.entry_url.delete(0, "end")
            self.entry_filename.delete(0, "end")
            
            self.tab_view.set("任務列表")
            self.task_segmented.set("進行中")
            self.switch_task_view("進行中")
            return

        # --- 一般排程邏輯 ---
        self.download_queue.append(config)
        self.log(f"已加入排程並開始: {config['url']}")
        self.update_queue_ui()
        self.check_queue() 
        
        # 提示切換
        self.tab_view.set("任務列表")
        self.task_segmented.set("進行中")
        self.switch_task_view("進行中")
        
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
            self.lbl_status.configure(text=msg)
        elif active_count == 0 and queue_count == 0:
            if self.downloading:
                self.downloading = False
                self.btn_download.configure(state="normal", text="開始下載")
                self.lbl_status.configure(text="所有任務已完成！")
                self.progress_bar.set(0)


        # 啟動新任務
        while len(self.active_queue_tasks) < self.max_concurrent_downloads and self.download_queue:
            next_config = self.download_queue.pop(0)
            self.update_queue_ui()
            self._start_core_download(next_config)

    def _start_core_download(self, config, task_id=None):
        if not task_id: task_id = str(uuid.uuid4())
        
        is_resume = task_id in self.active_task_widgets
        
        last_percent = 0
        if task_id in self.active_queue_tasks:
             last_percent = self.active_queue_tasks[task_id].get('last_percent', 0)

        core = YtDlpCore()
        
        self.active_queue_tasks[task_id] = {
            'core': core,
            'config': config,
            'status': 'running',
            'last_percent': last_percent
        }
        
        if not is_resume:
            self.create_active_task_widget(task_id, config, "排程任務啟動中...")
        else:
             msg = "恢復下載中..."
             if last_percent > 0: msg = f"恢復下載中 ({int(last_percent*100)}%)..."
             self.update_task_widget(task_id, last_percent if last_percent > 0 else 0, msg)
             self._update_task_buttons(task_id, "running")

        if self.tab_view.get() == "任務列表" and self.task_segmented.get() != "進行中":
             self.task_segmented.set("進行中")
             self.switch_task_view("進行中")
        
        self.log(f"啟動排程任務: {config['url']}")
        
        def update_title_callback(real_title):
            if not config.get('filename'):
                self.active_queue_tasks[task_id]['config']['default_title'] = real_title
                config['default_title'] = real_title
                
                def _update_ui():
                    if task_id in self.active_task_widgets:
                        if len(real_title) > 60: real_title_disp = real_title[:57] + "..."
                        else: real_title_disp = real_title
                        
                        if 'lbl_title' in self.active_task_widgets[task_id]:
                             self.active_task_widgets[task_id]['lbl_title'].configure(text=real_title_disp)
                
                self.after(0, _update_ui)

        core.start_download_thread(
            config, 
            progress_callback=lambda p, m: self.update_progress(p, m, task_id), 
            log_callback=self.log,
            finish_callback=lambda s, m: self.on_download_finished(s, m, task_id, config),
            title_callback=update_title_callback
        )

    def update_background_progress(self, task_id, percent, msg):
        if task_id in self.bg_tasks:
            self.bg_tasks[task_id]['status'] = msg
            if task_id not in self.active_task_widgets:
                 pass 
            self.update_task_widget(task_id, percent, msg)

    def on_stop_download(self):
        if messagebox.askyesno("確認", "確定要停止所有排程任務嗎？\n(背景獨立任務不會被停止)"):
            self.log("正在停止所有排程任務...")
            # 停止所有正在執行的
            for t_id, info in list(self.active_queue_tasks.items()):
                try: 
                    info['status'] = 'cancelled'
                    info['core'].stop_download()
                except: pass
            # 清空等待隊列 
            if self.download_queue:
                if messagebox.askyesno("確認", "是否同時清空等待中的排程清單？"):
                    self.download_queue.clear()
                    self.update_queue_ui()
            self.check_queue()

    def update_progress(self, percent, msg, task_id):
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
            self.update_task_widget(task_id, percent, msg)

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
                    else: self.lbl_status.configure(text=f"下載中：{int(percent * 100)}%")
        except: pass

    def on_download_finished(self, success, msg, task_id, config):
        current_status = 'unknown'
        if task_id in self.active_queue_tasks:
            current_status = self.active_queue_tasks[task_id].get('status', 'finished')

        if current_status == 'paused':
            self.log(f"[已暫停] {msg}")
            
            last_p = self.active_queue_tasks[task_id].get('last_percent', 0)
            if last_p < 0: last_p = 0
            self.update_task_widget(task_id, last_p, "已暫停 (雙擊繼續)")
            
            self._update_task_buttons(task_id, 'paused')
            return

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
                
                if yt_dlp:
                     current_version = yt_dlp.version.__version__
                else:
                     current_version = "0.0.0" 
                
                # 版本號比對函數
                def parse_version(v_str):
                    try:
                        return tuple(map(int, v_str.split('.')))
                    except:
                        return (0, 0, 0)

                if parse_version(latest_version) <= parse_version(current_version):
                    self.after(0, lambda: messagebox.showinfo("檢查更新", f"版本已為最新版本 ({current_version})"))
                    self.after(0, lambda: self.btn_update.configure(state="normal", text="檢查更新yt-dlp",hover_color="#555555"))
                    return

                # 詢問是否更新
                should_update = [False]
                def ask_user():
                    should_update[0] = messagebox.askyesno("發現新版本", f"現有版本: {current_version}\n最新版本: {latest_version}\n\n是否立即下載並更新？")
                
                
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
                    import subprocess
                    current_file = sys.executable if getattr(sys, 'frozen', False) else __file__
                    # 啟動新進程
                    subprocess.Popen([sys.executable, current_file] if not getattr(sys, 'frozen', False) else [current_file])
                    # 強制結束目前進程 (避免清理時報錯)
                    os._exit(0)

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
                
                # 2. 替換設定變數 
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

        # 自動更新
        self.btn_update = ctk.CTkButton(settings_frame, text="檢查並更新yt-dlp", font=self.font_btn, fg_color="gray", hover_color="#555555", command=self.check_for_updates)
        self.btn_update.pack(pady=(0, 20))


        def open_releases(event=None):
            webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases")
            
        lbl_release = ctk.CTkLabel(settings_frame, text="手動更新 yt-dlp", font=self.font_small, text_color="#3B8ED0", cursor="hand2")
        lbl_release.pack(side="bottom", pady=(0, 20)) 
        lbl_release.bind("<Button-1>", open_releases)
        lbl_release.bind("<Enter>", lambda e: lbl_release.configure(text_color="#1F6AA5"))
        lbl_release.bind("<Leave>", lambda e: lbl_release.configure(text_color="#3B8ED0"))

        try:
            if yt_dlp:
                 version_text = f"yt-dlp版本 - {yt_dlp.version.__version__}"
            else:
                 version_text = "yt-dlp版本 - 未安裝 (請點擊上方按鈕安裝)"
        except:
            version_text = "yt-dlp版本 - 未知"
            
        ctk.CTkLabel(settings_frame, text=version_text, font=self.font_small, text_color="gray").pack(side="bottom", pady=(5, 0))



if __name__ == "__main__":
    app = App()
    app.mainloop()