import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
import threading
import webbrowser
import sys
import os
import time
import subprocess
import random
import re


try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from constants import APP_VERSION, GITHUB_REPO, DEFAULT_APPEARANCE_MODE, CODE_TO_NAME
from ui.tooltip import CTkToolTip

class AppLayoutMixin:


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
    """
    將 UI 佈局相關的程式碼從 main.py 抽離至此 Mixin。
    前提：主類別 (App) 已初始化基本字體屬性 (self.font_*) 與資料結構 (self.frames 等)。
    """

    def setup_sidebar(self):
        # Navigation Buttons & Indicators
        self.nav_btns = {}
        self.nav_indicators = {}
        
        # Configure columns: 0 is for the strip indicator, 1 is for the button
        self.sidebar_frame.grid_columnconfigure(0, minsize=5) 
        self.sidebar_frame.grid_columnconfigure(1, weight=1)
        
        self.sidebar_items = {
            "Basic": ("home.png", "基本選項", "⌂"),      
            "Format": ("video.png", "格式/畫質", "🎞"),
            "Live": ("live.png", "直播設定", "📡"),
            "Sub": ("sub.png", "字幕設定", "🔡"),
            "Output": ("time.png", "裁切/預約", "⏰"),
            "Adv": ("adv.png", "進階選項", "🛠"),
            "Tasks": ("tasks.png", "任務列表", "📥"),
            "Log": ("log.png", "系統日誌", "⏱"),
            "Settings": ("settings.png", "設定", "⚙"),
            "About": ("about.png", "關於", "ⓘ")
        }
        
        # 上方按鈕
        top_items = ["Basic", "Format", "Live", "Sub", "Output", "Adv", "Tasks"]
        for i, key in enumerate(top_items):
            if key not in self.sidebar_items: continue
            self._create_sidebar_item(key, i)

        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # 下方按鈕 (Log, Settings, About)
        bottom_items = ["Log", "Settings", "About"]
        for i, key in enumerate(bottom_items):
             if key not in self.sidebar_items: continue
             self._create_sidebar_item(key, 11+i)
             
    def _load_icon(self, filename):
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = os.path.join(sys._MEIPASS, "icon")
            else:
                base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon")
                
            path = os.path.join(base_path, filename)
            if os.path.exists(path):
                img_white = Image.open(path).convert("RGBA")
                
                r, g, b, a = img_white.split()
                img_black = Image.merge("RGBA", (r.point(lambda _: 0), g.point(lambda _: 0), b.point(lambda _: 0), a))
                
                return ctk.CTkImage(light_image=img_black, dark_image=img_white, size=(24, 24))
        except: pass
        return None

    def _create_sidebar_item(self, key, row_idx):
        filename, tooltip_text, fallback_char = self.sidebar_items.get(key, ("", "", "?"))
        
        # 1. Indicator Strip (Left)
        indicator = ctk.CTkFrame(self.sidebar_frame, width=4, height=40, corner_radius=2, fg_color="transparent")
        indicator.grid(row=row_idx, column=0, pady=5, sticky="e") 
        self.nav_indicators[key] = indicator
        
        # 2. Icon Button
        icon_img = self._load_icon(filename)
        
        btn_kwargs = {
            "text": "",
            "image": icon_img,
            "anchor": "center",
            "fg_color": "transparent",
            "hover_color": ("gray90", "gray25"),
            "height": 50,
            "width": 50,
            "corner_radius": 10,
            "command": lambda k=key: self.select_frame(k)
        }
        
        if not icon_img:
            btn_kwargs["text"] = fallback_char
            btn_kwargs["font"] = self.font_sidebar_icon
            btn_kwargs["text_color"] = ("gray50", "gray70")
            del btn_kwargs["image"]

        btn = ctk.CTkButton(self.sidebar_frame, **btn_kwargs)
        btn.grid(row=row_idx, column=1, sticky="nsew", pady=2, padx=(5, 10))
        self.nav_btns[key] = btn
        CTkToolTip(btn, tooltip_text)

    def show_nav_badge(self, key):
        """在指定的導航按鈕上顯示紅點提醒"""
        if key not in self.nav_btns: return
        
        # 避免重複添加
        if hasattr(self, f"badge_{key}"): return

        btn = self.nav_btns[key]
        
        # 建立紅點
        badge = ctk.CTkFrame(self.sidebar_frame, width=12, height=12, corner_radius=6, fg_color="#FF3B30", border_width=2, border_color="#2b2b2b")
        

        badge.place(in_=btn, relx=0.75, rely=0.2, anchor="center")
        
        setattr(self, f"badge_{key}", badge)

    def show_widget_badge(self, widget, badge_id):
        """在任意 Widget 上顯示紅點"""
        if not widget: return
        if hasattr(self, f"badge_widget_{badge_id}"): return

        try:
            badge = ctk.CTkFrame(widget.master, width=12, height=12, corner_radius=6, fg_color="#FF3B30", border_width=2, border_color="#2b2b2b")
            badge.place(in_=widget, relx=0.98, rely=0.02, anchor="center")
            
            setattr(self, f"badge_widget_{badge_id}", badge)
        except Exception: pass

    def select_frame(self, name):
        # Update Nav
        for key in self.nav_btns:
            self.nav_btns[key].configure(text_color=("gray50", "gray70"))
            if key in self.nav_indicators:
                self.nav_indicators[key].configure(fg_color="transparent")
        
        if name in self.nav_btns:
            self.nav_btns[name].configure(text_color="#1F6AA5")
            if name in self.nav_indicators:
                self.nav_indicators[name].configure(fg_color="#1F6AA5")
        
        # Switch Frame using Stacking (Lift)
        if name in self.frames:
            # Ensure it is managed by grid (idempotent)
            self.frames[name].grid(row=0, column=0, sticky="nsew")
            self.frames[name].tkraise()
            
    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    
    def safe_open_path(self, path):
        try:
            if not os.path.exists(path): return
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.call(('xdg-open', path))
        except: pass

    # ================= UI 建構區 =================

    def setup_bottom_controls(self):
        # 底部控制區放在 main_view 的第二列 (row=1)
        self.bottom_frame = ctk.CTkFrame(self.main_view, fg_color="transparent", height=60)
        self.bottom_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=15)
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
            self.bottom_frame, text="快速下載", width=100, height=35, font=self.font_btn, 
            fg_color="#01814A", hover_color="#006030", command=self.on_start_download
        )
        self.btn_download.grid(row=0, column=3, padx=(5, 5))

        # 加入任務按鈕 (僅加入排程)
        self.btn_add = ctk.CTkButton(
            self.bottom_frame, text="加入任務", width=100, height=35, font=self.font_btn, 
            fg_color="#1F6AA5", hover_color="#144870", command=self.on_add_task
        )
        self.btn_add.grid(row=0, column=4, padx=(5, 0))

    def create_about_page(self):
        if not hasattr(self, 'about_frame'):
            self.about_frame = ctk.CTkFrame(self.frames["About"], fg_color="transparent")
            self.about_frame.pack(fill="both", expand=True, padx=20, pady=20)

        btn_check_update = ctk.CTkButton(
            self.about_frame, text="檢查更新", command=self.check_app_update,
            width=120, height=32, corner_radius=16, font=self.font_btn 
        )
        btn_check_update.pack(pady=10)
        
        # [New] 查看更新日誌按鈕
        btn_changelog = ctk.CTkButton(
            self.about_frame, text="查看更新日誌", command=self.show_changelog,
            width=120, height=32, corner_radius=16, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray70", "gray30")
        )
        btn_changelog.pack(pady=5)
        



    def setup_basic_ui(self):
        if not hasattr(self, 'var_hardware_accel'): self.var_hardware_accel = ctk.BooleanVar(value=False)
        
        hw_frame = ctk.CTkFrame(self.tab_basic, fg_color="transparent")
        hw_frame.grid(row=0, column=0, sticky="nw", padx=20, pady=20)
        
        def on_hw_toggle():
            if self.var_hardware_accel.get():
                msg = (
                    "開啟後可能出現『檔案畫質略差、體積大』及『轉檔時會佔用顯卡資源 (影響遊戲效能)』等問題。\n"
                    "確定要啟用嗎？"
                )
                try:
                    import tkinter.messagebox as messagebox
                    if not messagebox.askyesno("硬體加速", msg, icon="warning"):
                        self.var_hardware_accel.set(False) 
                except: pass
            
            if hasattr(self, 'save_config'): self.save_config()

        self.switch_hw = ctk.CTkSwitch(hw_frame, text="硬體加速:偵測中...", variable=self.var_hardware_accel,
                                       font=(self.font_family, 12, "bold"), text_color="gray60",
                                       progress_color="#2CC985", button_hover_color="#20A068",
                                       state="disabled", command=on_hw_toggle)
        self.switch_hw.pack(anchor="w")
        CTkToolTip(self.switch_hw, "使用顯示卡 GPU 加速合併與轉檔過程。\n自動偵測: NVIDIA, Intel, AMD, Apple (Mac)。")

        # --- Absolute Vertical Centering Layout ---
        self.tab_basic.grid_rowconfigure(0, weight=1)
        self.tab_basic.grid_rowconfigure(1, weight=0) 
        self.tab_basic.grid_rowconfigure(2, weight=1)
        self.tab_basic.grid_columnconfigure(0, weight=1)
        
        # Main Container (The Island) 
        island_frame = ctk.CTkFrame(self.tab_basic, fg_color="transparent")
        island_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Spacer to enforce consistent width (720px)
        ctk.CTkFrame(island_frame, width=720, height=0, fg_color="transparent").pack()
        
        # --- Thumbnail Preview Card (Above Search) ---
        self.preview_card = ctk.CTkFrame(island_frame, fg_color=("white", "#2B2B2B"), corner_radius=12, border_width=1, border_color=("#1F6AA5", "#1F6AA5"))
        
        # Inner Layout
        self.preview_card.grid_columnconfigure(1, weight=1)
        
        # 1. Image (Left) - Placeholder
        self.lbl_thumb_img = ctk.CTkLabel(self.preview_card, text="", width=120, height=68, corner_radius=8, fg_color="gray20") # Aspect~ 16:9
        self.lbl_thumb_img.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        
        # 2. Info (Right)
        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=10, padx=(0, 10))
        
        self.lbl_preview_title = ctk.CTkLabel(self.info_frame, text="標題載入中...", font=(self.font_family, 14, "bold"), anchor="w", justify="left", wraplength=500, text_color=("#1F6AA5", "#3B8ED0"))
        self.lbl_preview_title.pack(fill="x")
        
        self.lbl_preview_meta = ctk.CTkLabel(self.info_frame, text="--:-- • --", font=(self.font_family, 12), text_color="gray", anchor="w")
        self.lbl_preview_meta.pack(fill="x", pady=(2, 0))

        # --- 1. Search Section ---
        search_section = ctk.CTkFrame(island_frame, fg_color="transparent")
        search_section.pack(fill="x", pady=(0, 0)) 
        
        # Input Bar
        input_bar = ctk.CTkFrame(search_section, fg_color=("white", "#2b2b2b"), corner_radius=25, border_width=2, border_color=("#B0B0B0", "#484848"))
        input_bar.pack(fill="x", ipady=5)

 
        
        
        # 2. Paste Button (Left of Analyze)
        def paste_url():
            try:
                self.entry_url.delete(0, 'end')
                self.entry_url.insert(0, self.clipboard_get())
                if hasattr(self, 'on_fetch_info'):
                    self.after(200, self.on_fetch_info) 
            except: pass
            
        btn_paste = ctk.CTkButton(input_bar, text="📋", width=50, height=50, fg_color="transparent", hover_color=("gray90", "#3a3a3a"), 
                                  text_color=("gray50", "gray80"), font=("Segoe UI Emoji", 22), command=paste_url, corner_radius=25)
        btn_paste.pack(side="right", padx=(5, 5))
        CTkToolTip(btn_paste, "貼上並自動分析網址")

        # 3. URL Entry (Fills remaining space)
        self.entry_url = ctk.CTkEntry(input_bar, width=450, height=50, font=(self.font_family, 16), 
                                      placeholder_text="貼上影片連結...", 
                                      fg_color="transparent", border_width=0, text_color=("gray20", "white"))
        self.entry_url.pack(side="left", padx=15, fill="x", expand=True)
        # Bind Enter key
        if hasattr(self, 'on_fetch_info'):
             self.entry_url.bind('<Return>', lambda event: self.on_fetch_info())
        
        
        # Restore Logic Variable (Hidden)
        self.var_playlist = ctk.BooleanVar(value=False)


        # --- 2. Settings Section (Modern Card) ---
        settings_card = ctk.CTkFrame(island_frame, fg_color=("white", "#232323"), corner_radius=15, border_width=1, border_color=("#E5E5E5", "#333333"))
        settings_card.pack(fill="x", pady=(10, 10))
        
        # Settings Content
        s_content = ctk.CTkFrame(settings_card, fg_color="transparent")
        s_content.pack(fill="x", padx=30, pady=25)
        s_content.grid_columnconfigure(1, weight=1)
        
        # Header - With decorative accent
        header_frame = ctk.CTkFrame(s_content, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        ctk.CTkFrame(header_frame, width=4, height=18, fg_color="#1F6AA5", corner_radius=2).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_frame, text="快速設定 (Quick Settings)", font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")

        # Timestamp Switch (Header Right)
        if not hasattr(self, 'var_add_timestamp'): self.var_add_timestamp = ctk.BooleanVar(value=False)
        
        self.switch_timestamp = ctk.CTkSwitch(header_frame, text="", variable=self.var_add_timestamp, 
                                              progress_color="#2CC985", button_hover_color="#20A068", height=24, width=40)
        self.switch_timestamp.pack(side="right", padx=(5, 0))
        
        lbl_ts = ctk.CTkLabel(header_frame, text="防止覆寫", font=("Microsoft JhengHei UI", 12), text_color=("gray40", "gray60"))
        lbl_ts.pack(side="right")
        
        ts_hint = "啟用後會自動在檔名後方加入時間戳記，\n確保每次下載的檔名都是唯一的，避免舊檔案被覆寫。"
        CTkToolTip(lbl_ts, ts_hint)
        CTkToolTip(self.switch_timestamp, ts_hint)

        # Path (Row 1)
        ctk.CTkLabel(s_content, text="儲存位置", font=("Microsoft JhengHei UI", 13), text_color=("gray40", "gray60")).grid(row=1, column=0, sticky="w", pady=5)
        
        path_box = ctk.CTkFrame(s_content, fg_color="transparent")
        path_box.grid(row=1, column=1, sticky="ew", padx=(15, 0), pady=5)
        
        self.entry_path = ctk.CTkEntry(path_box, height=30, font=("Microsoft JhengHei UI", 13), placeholder_text="預設為當前目錄", 
                                       fg_color=("#F0F0F0", "#3E3E3E"), border_width=0, corner_radius=8) 
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(path_box, text="瀏覽", width=70, height=30, fg_color=("#1F6AA5", "#1F6AA5"), hover_color=("#144870", "#144870"), 
                      text_color="white", font=("Microsoft JhengHei UI", 12), corner_radius=8, command=self.browse_folder).pack(side="left")

        # Filename (Row 2)
        ctk.CTkLabel(s_content, text="檔案名稱", font=("Microsoft JhengHei UI", 13), text_color=("gray40", "gray60")).grid(row=2, column=0, sticky="w", pady=5)
        
        self.entry_filename = ctk.CTkEntry(s_content, height=30, font=("Microsoft JhengHei UI", 13), placeholder_text="預設為影片原標題",
                                           fg_color=("#F0F0F0", "#3E3E3E"), border_width=0, corner_radius=8)
        self.entry_filename.grid(row=2, column=1, sticky="ew", padx=(15, 0), pady=10)
        
        # 初始化顯示
        self.update_queue_ui()

    def on_playlist_toggle(self):
        """歌單模式時禁用不相關選項"""
        state = "disabled" if self.var_playlist.get() else "normal"
        
        if hasattr(self, 'entry_filename'):
            self.entry_filename.configure(state=state)
            if state == "disabled": self.entry_filename.configure(placeholder_text="播放清單模式下將自動命名")
            else: self.entry_filename.configure(placeholder_text="預設為原標題")
        
        
        if hasattr(self, 'chk_cut'):
             self.chk_cut.configure(state=state)
             if state == "disabled":
                  self.chk_cut.deselect()
                  if hasattr(self, 'entry_start'): self.entry_start.configure(state="disabled")
                  if hasattr(self, 'entry_end'): self.entry_end.configure(state="disabled")
        
        if hasattr(self, 'rb_live_now'): self.rb_live_now.configure(state=state)
        if hasattr(self, 'rb_live_start'): self.rb_live_start.configure(state=state)

    def browse_folder(self):
        filename = filedialog.askdirectory()
        if filename:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, filename)
            if hasattr(self, 'save_config'): self.save_config()



    def setup_format_ui(self):
        if not hasattr(self, 'var_video_res'): self.var_video_res = ctk.StringVar(value="Best (最高畫質)")
        if not hasattr(self, 'var_video_legacy'): self.var_video_legacy = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_audio_only'): self.var_audio_only = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_audio_qual'): self.var_audio_qual = ctk.StringVar(value="Best (來源預設)")
        if not hasattr(self, 'var_audio_codec'): self.var_audio_codec = ctk.StringVar(value="Auto (預設/Opus)")
        if not hasattr(self, 'var_embed_thumb'): self.var_embed_thumb = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_embed_subs'): self.var_embed_subs = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_metadata'): self.var_metadata = ctk.BooleanVar(value=False)

        opt_style = {
            "height": 40, "corner_radius": 8,
            "fg_color": ("gray90", "gray30"), 
            "button_color": ("gray80", "gray40"), "button_hover_color": ("gray75", "gray35"),
            "dropdown_fg_color": ("gray95", "gray25"), "dropdown_hover_color": ("gray85", "gray35"), "dropdown_text_color": ("black", "white"),
            "font": self.font_text, "dropdown_font": self.font_text, "text_color": ("black", "white")
        }

        # --- Layout Setup ---
        # 清空舊有元件
        for widget in self.tab_format.winfo_children():
            widget.destroy()

        self.tab_format.pack_propagate(False)
        
        # 建立主捲動容器
        scroll_container = ctk.CTkScrollableFrame(self.tab_format, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        scroll_container.grid_columnconfigure(0, weight=1, uniform="cols")
        scroll_container.grid_columnconfigure(1, weight=1, uniform="cols")

        # Helper: Create Card
        def create_card(parent, title, icon, row, col, columnspan=1):
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "gray20"), corner_radius=15)
            frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10, columnspan=columnspan)
            
            # Header
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 20)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            return content

        # --- Card 1: Video Settings ---
        video_content = create_card(scroll_container, "影片設定 (Video)", "🎬", row=0, col=0)
        
        ctk.CTkLabel(video_content, text="輸出格式 (Format)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.format_options = ["mp4 (影片+音訊)", "mkv (影片+音訊)", "webm (影片+音訊)", "mp3 (純音訊)", "m4a (純音訊)", "flac (無損音訊)", "wav (無損音訊)"]
        self.combo_format = ctk.CTkOptionMenu(video_content, values=self.format_options, command=self.on_format_change, 
                                              width=200, **opt_style)
        self.combo_format.set("mp4 (影片+音訊)")
        self.combo_format.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(video_content, text="影片畫質 (Resolution)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_video_res = ctk.CTkOptionMenu(video_content, values=["Best (最高畫質)", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"], 
                                                 variable=self.var_video_res, width=200, **opt_style)
        self.combo_video_res.pack(fill="x", pady=(0, 15))
        
        self.chk_legacy = ctk.CTkSwitch(video_content, text="使用 H.264 編碼 (高相容性)", variable=self.var_video_legacy, 
                                        font=(self.font_family, 13), progress_color="#2CC985", button_hover_color="#20A068", command=self.update_dynamic_hint)
        self.chk_legacy.pack(anchor="w", pady=(5, 15))
        CTkToolTip(self.chk_legacy, "若您的播放裝置較舊，請開啟此選項。\n注意：最高畫質通常限制為 1080p。")

        # --- Card 2: Audio Settings ---
        audio_content = create_card(scroll_container, "音訊設定 (Audio)", "🎵", row=0, col=1)
        
        ctk.CTkLabel(audio_content, text="音訊音質 (Bitrate)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_quality = ctk.CTkOptionMenu(audio_content, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps (標準)(yt最佳)", "96 kbps (較低)", "64 kbps (省空間)"], 
                                                     variable=self.var_audio_qual, command=lambda _: self.update_dynamic_hint(), width=200, **opt_style)
        self.combo_audio_quality.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(audio_content, text="音訊編碼 (Codec)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_codec = ctk.CTkOptionMenu(audio_content, values=["Auto (預設/Opus)", "AAC (車用/相容性高)"], 
                                                   variable=self.var_audio_codec, command=lambda _: self.update_dynamic_hint(), width=200, **opt_style)
        self.combo_audio_codec.pack(fill="x", pady=(0, 15))
        
        self.lbl_format_hint = ctk.CTkLabel(audio_content, text="提示：若車用音響無聲音，請在「音訊編碼」選擇 AAC", font=(self.font_family, 12), text_color="#1F6AA5", wraplength=250)
        self.lbl_format_hint.pack(pady=(10, 0))

        # --- Card 3: Post Processing ---
        post_content = create_card(scroll_container, "下載與後處理選項 (Post-Processing)", "🔧", row=1, col=0, columnspan=2)
        post_content.grid_columnconfigure(0, weight=1)
        post_content.grid_columnconfigure(1, weight=1)
        
        def create_switch(parent, text, var, r, c, tooltip=None):
            # 使用 CTkSwitch 取代 CheckBox
            sw = ctk.CTkSwitch(parent, text=text, variable=var, font=(self.font_family, 13), 
                               progress_color="#2CC985", button_hover_color="#20A068")
            sw.grid(row=r, column=c, sticky="w", padx=20, pady=12)
            if tooltip: CTkToolTip(sw, tooltip)
            return sw

        create_switch(post_content, "內嵌影片縮圖 (Thumbnail)", self.var_embed_thumb, 0, 0, "將 YouTube 封面圖寫入影片檔案中")
        create_switch(post_content, "內嵌字幕檔案 (Embed Subs)", self.var_embed_subs, 0, 1, "將下載的字幕檔直接封裝進影片 (Softsubs)")
        create_switch(post_content, "寫入中繼資料 (Metadata)", self.var_metadata, 1, 0, "寫入標題、作者、日期等詳細資訊")
        
        # SponsorBlock with Options
        if not hasattr(self, 'var_sponsorblock'): self.var_sponsorblock = ctk.BooleanVar(value=False)
        
        # 定義所有可用類別與預設狀態
        if not hasattr(self, 'sb_vars'):
            self.sb_vars = {
                'sponsor': ctk.BooleanVar(value=True),
                'selfpromo': ctk.BooleanVar(value=True),
                'interaction': ctk.BooleanVar(value=True),
                'intro': ctk.BooleanVar(value=True),
                'outro': ctk.BooleanVar(value=True),
                'preview': ctk.BooleanVar(value=True),
                'music_offtopic': ctk.BooleanVar(value=True),
                'filler': ctk.BooleanVar(value=True)
            }
            # 為了顯示名稱的映射
            self.sb_labels = {
                'sponsor': "贊助商廣告 (Sponsor)",
                'selfpromo': "自我推銷 (Self-Promo)",
                'interaction': "互動提醒 (Interaction)",
                'intro': "片頭 (Intro)",
                'outro': "片尾 (Outro)",
                'preview': "預告/回顧 (Preview)",
                'music_offtopic': "MV 無關片段 (Music Only)",
                'filler': "無內容片段 (Filler)"
            }

        sb_frame = ctk.CTkFrame(post_content, fg_color="transparent")
        sb_frame.grid(row=1, column=1, sticky="w", padx=20, pady=12)

        def open_sb_settings():
            top = ctk.CTkToplevel(self)
            top.title("SponsorBlock 過濾設定")
            top.geometry("400x600")
            top.resizable(False, False)
            top.attributes("-topmost", True)
            
            # Center
            x = self.winfo_x() + (self.winfo_width() // 2) - 200
            y = self.winfo_y() + (self.winfo_height() // 2) - 300
            top.geometry(f"+{x}+{y}")
            
            ctk.CTkLabel(top, text="請勾選要【刪除】的片段類型", font=(self.font_family, 14, "bold"), text_color="#1F6AA5").pack(pady=15)
            
            chk_frame = ctk.CTkScrollableFrame(top, fg_color="transparent") 
            chk_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            sb_descriptions = {
                'sponsor': "廠商付費的業配內容 (如 VPN、手遊廣告)",
                'selfpromo': "創作者推銷自己的周邊、課程或會員",
                'interaction': "請求按讚、訂閱、分享的互動提醒",
                'intro': "固定的開場動畫、Logo 或主題曲",
                'outro': "片尾名單、結尾畫面或推薦卡片",
                'preview': "影片開頭的精彩預告或前情提要",
                'music_offtopic': "MV 中間的演戲、對話等非音樂部分，專用於音樂錄影帶 (MV)",
                'filler': "離題閒聊、拖時間或無實質內容片段"
            }
            
            for key, text in self.sb_labels.items():
                var = self.sb_vars[key]
                
                # Item Container
                item_frame = ctk.CTkFrame(chk_frame, fg_color="transparent")
                item_frame.pack(fill="x", pady=8)
                
                cb = ctk.CTkCheckBox(item_frame, text=text, variable=var, font=(self.font_family, 13, "bold"))
                cb.pack(anchor="w")
                
                desc = sb_descriptions.get(key, "")
                ctk.CTkLabel(item_frame, text=desc, font=(self.font_family, 11), text_color=("gray50", "gray70")).pack(anchor="w", padx=(30, 0))
                
            ctk.CTkButton(top, text="確定", command=top.destroy, width=120, height=35).pack(pady=10)

        def on_sb_toggle():
            state = "normal" if self.var_sponsorblock.get() else "disabled"
            self.btn_sb_config.configure(state=state)

        sb_sw = ctk.CTkSwitch(sb_frame, text="啟用 SponsorBlock", variable=self.var_sponsorblock, 
                              font=(self.font_family, 13), progress_color="#2CC985", button_hover_color="#20A068",
                              command=on_sb_toggle)
        sb_sw.pack(side="left")

        self.btn_sb_config = ctk.CTkButton(sb_frame, text="⚙ 設定過濾類別", 
                                           width=140, height=28,
                                           font=(self.font_family, 12),
                                           fg_color=("#3E3E3E", "gray30"), 
                                           hover_color=("#505050", "gray40"),
                                           command=open_sb_settings)
        self.btn_sb_config.pack(side="left", padx=(10, 0))
        
        # Init state
        on_sb_toggle()

        CTkToolTip(sb_sw, "自動移除影片中的特定片段 (如廣告、片頭等)。\n點擊右側按鈕可自定義要刪除的類別。")



        self.on_format_change(None)

    def setup_live_ui(self):
        self.tab_live = self.frames["Live"]
        
        # Grid Configuration
        self.tab_live.grid_columnconfigure(0, weight=1)
        self.tab_live.grid_rowconfigure(0, weight=1) 
        
        center_box = ctk.CTkFrame(self.tab_live, fg_color="transparent")
        center_box.grid(row=0, column=0, sticky="ew", padx=40)
        center_box.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(center_box, text="直播錄製設定 (Live Stream Settings)", font=(self.font_family, 18, "bold"), text_color=("gray20", "gray80")).pack(pady=(0, 25))

        # --- Helper for Cards (Standard Style) ---
        def create_live_card(parent, title, icon="⚙️"):
            card = ctk.CTkFrame(parent, fg_color=("gray95", "gray20"), corner_radius=15)
            card.pack(fill="x", pady=10)
            
            # Header
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            # Icon & Title
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
            # Content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=(0, 20))
            return content

        # Init Variables
        if not hasattr(self, 'var_live_wait'): self.var_live_wait = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_live_from_start'): self.var_live_from_start = ctk.BooleanVar(value=True)

        # --- Card 1: 智慧等待 ---
        wait_content = create_live_card(center_box, "智慧等待 (Smart Wait)", icon="📡")
        
        s_wait = ctk.CTkSwitch(wait_content, text="啟用等待開台 (Wait for Stream)", variable=self.var_live_wait, 
                               font=(self.font_family, 13, "bold"), progress_color="#2CC985", height=32)
        s_wait.pack(anchor="w", padx=10, pady=8)
        CTkToolTip(s_wait, "僅對直播連結有效。\n若直播尚未開始，程式將持續監控直到開播。")
        
        # --- Card 2: 錄製策略 ---
        rec_content = create_live_card(center_box, "錄製策略 (Recording Strategy)", icon="📼")
        
        s_rec = ctk.CTkSwitch(rec_content, text="嘗試從頭下載 (Live from Start)", variable=self.var_live_from_start,
                              font=(self.font_family, 13, "bold"), progress_color="#2CC985", button_hover_color="#20A068", height=32)
        s_rec.pack(anchor="w", padx=10, pady=8)
        CTkToolTip(s_rec, "僅對直播連結有效。\n若您在直播中途才開始錄製，嘗試抓取錯過的開頭片段。")

        # --- Note ---
        note_box = ctk.CTkFrame(center_box, fg_color="transparent")
        note_box.pack(pady=20)
        ctk.CTkLabel(note_box, text="提示：開啟「等待開台」後，任務狀態會顯示為「下載中」，但在開播前沒有進度條變化屬正常現象。", 
                     text_color=("#1F6AA5", "#88C0D0"), font=(self.font_family, 12)).pack()

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
                 if "純音訊" in choice or "影片" in choice:
                      self.combo_audio_codec.configure(state="normal")

        hint = f"提示：將下載 {choice.split(' ')[0]} 格式"

        if "純音訊" in choice:
             hint = f"提示：已選擇 {choice.split(' ')[0]} 格式，若需車用相容性可手動指定 AAC"
        elif "無損" in choice:
             hint = "提示：無損模式下不建議進行額外編碼轉換"
        else:
            if self.var_video_legacy.get():
                hint = "提示：相容模式已開啟 (H.264 + AAC)\n確保所有裝置皆可播放"
            elif self.combo_audio_codec.get().startswith("AAC"):
                hint = "提示：將優先使用 AAC 音訊編碼 (提升車用與舊裝置相容性)"
            else:
                hint = f"提示：將下載 {choice.split(' ')[0]} 格式 (自動最佳品質)"
        
        qual = self.combo_audio_quality.get()
        if "Best" not in qual and "無損" not in choice:
             hint += "\n(注意：在無更高品質時，強制設定位元率只會增加檔案大小無法提升原始音質)"

        self.lbl_format_hint.configure(text=hint,text_color=("#1F6AA5", "#88C0D0"))

    def on_format_change(self, choice):
        # 1. 無損音訊 (flac/wav) -> 鎖定畫質與編碼 (不建議轉碼)
        if choice and "無損" in choice:
            self.combo_video_res.set("N/A")
            self.combo_video_res.configure(state="disabled")
            
            # 鎖定 H.264 (影片專用)
            self.chk_legacy.deselect()
            self.chk_legacy.configure(state="disabled")

            self.combo_audio_codec.set("Auto (預設/Opus)")
            self.combo_audio_codec.configure(state="disabled")

        # 2. 一般純音訊 (mp3/m4a) -> 鎖定畫質，但開放編碼 (允許強制轉 AAC)
        elif choice and "純音訊" in choice:
            self.combo_video_res.set("N/A")
            self.combo_video_res.configure(state="disabled")
            
            # 鎖定 H.264 (影片專用)
            self.chk_legacy.deselect()
            self.chk_legacy.configure(state="disabled")
            
            self.combo_audio_codec.configure(state="normal")

        # 3. 影片模式 -> 全部開放
        else:
            self.combo_video_res.configure(state="normal")
            if "Best" not in self.combo_video_res.get():
                 pass 
            
            # 開放 H.264
            self.chk_legacy.configure(state="normal")
            self.combo_audio_codec.configure(state="normal")
            
        self.update_dynamic_hint()
    
    def setup_subtitle_ui(self):
        # 1. Search & Filter Bar (Top)
        filter_frame = ctk.CTkFrame(self.tab_sub, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        # Search Icon/Label
        ctk.CTkLabel(filter_frame, text="🔍", font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 5))
        
        # Search Entry
        self.var_sub_search = ctk.StringVar()
        self.var_sub_search.trace("w", self._on_sub_search_change)
        
        self.entry_sub_search = ctk.CTkEntry(filter_frame, placeholder_text="搜尋語言或代碼 (如: 繁體, en, zh-TW)...", placeholder_text_color="gray", height=35, font=self.font_text)
        self.entry_sub_search.bind("<KeyRelease>", self._on_sub_search_change)
        self.entry_sub_search.pack(side="left", fill="x", expand=True)
        
        # Hint (Right side)
        ctk.CTkLabel(filter_frame, text="(*請先分析網址)", text_color="gray", font=self.font_small).pack(side="left", padx=(10, 0))

        # 2. Scrollable List for Subtitles
        self.scroll_subs = ctk.CTkScrollableFrame(self.tab_sub, label_text=None, fg_color=("gray95", "gray16"))
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Grid Configuration for 2 columns
        self.scroll_subs.grid_columnconfigure(0, weight=1)
        self.scroll_subs.grid_columnconfigure(1, weight=1)

        self.sub_checkboxes = {} 
        self.current_sub_data = [] 

        # 3. Manual Settings (Bottom)
        ctk.CTkFrame(self.tab_sub, height=2, fg_color=("gray85", "gray30")).pack(fill="x", padx=20, pady=10)

        manual_frame = ctk.CTkFrame(self.tab_sub, fg_color="transparent")
        manual_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Title
        ctk.CTkLabel(manual_frame, text="通用字幕設定 (若無分析/播放清單)", font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray20", "gray90")).pack(anchor="w", pady=(5, 10))

        self.pl_sub_vars = {
            'zh-TW': ctk.BooleanVar(value=False),
            'zh-Hans': ctk.BooleanVar(value=False),
            'en': ctk.BooleanVar(value=False),
            'ja': ctk.BooleanVar(value=False),
            'ko': ctk.BooleanVar(value=False)
        }
        
        # Common Languages Row
        chk_font = ("Microsoft JhengHei UI", 14)
        
        row1 = ctk.CTkFrame(manual_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkCheckBox(row1, text="繁體中文", variable=self.pl_sub_vars['zh-TW'], font=chk_font).pack(side="left", padx=(10, 20))
        ctk.CTkCheckBox(row1, text="簡體中文", variable=self.pl_sub_vars['zh-Hans'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="英文", variable=self.pl_sub_vars['en'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="日文", variable=self.pl_sub_vars['ja'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="韓文", variable=self.pl_sub_vars['ko'], font=chk_font).pack(side="left", padx=20)
        
        CTkToolTip(manual_frame, "適用於播放清單下載：\n將依照「由左至右」的優先順序嘗試下載勾選的字幕。\n若影片包含該字幕則下載，否則跳過。")
        
        # Manual Entry Row
        manual_bg = ctk.CTkFrame(manual_frame, fg_color="transparent")
        manual_bg.pack(anchor="w", pady=(15, 0))
        
        self.var_sub_manual = ctk.BooleanVar()
        def toggle_manual_entry():
            self.entry_sub_manual.configure(state="normal" if self.var_sub_manual.get() else "disabled")
            
        ctk.CTkCheckBox(manual_bg, text="其他", variable=self.var_sub_manual, command=toggle_manual_entry, font=self.font_text).pack(side="left", padx=(10, 2))
        
        self.entry_sub_manual = ctk.CTkEntry(manual_bg, width=120, placeholder_text="代碼 (如: th, vi)", state="disabled")
        self.entry_sub_manual.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(manual_bg, text="用逗號或空白分隔", text_color=("#1F6AA5", "#88C0D0"), font=self.font_small).pack(side="left", padx=5)
        
        ctk.CTkButton(manual_bg, text="查詢代碼表", width=80, height=24, fg_color="#555555", font=("Microsoft JhengHei UI", 12), command=self.open_lang_table).pack(side="left", padx=10)

    def _on_sub_search_change(self, *args):
        query = self.entry_sub_search.get()
        self._refresh_subtitle_view(query)

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

    def clear_subtitle_ui(self):
        """Reset subtitle UI to initial state"""
        self.current_sub_data = []
        self.sub_checkboxes = {}
        if hasattr(self, 'entry_sub_search'): self.entry_sub_search.delete(0, "end")
        if hasattr(self, 'var_sub_search'): self.var_sub_search.set("")
        
        if hasattr(self, 'scroll_subs'):
            for w in self.scroll_subs.winfo_children():
                w.destroy()
            
            ctk.CTkLabel(self.scroll_subs, text="(請先分析網址)", text_color="gray", font=("Microsoft JhengHei UI", 16)).pack(pady=40)

    def update_subtitle_list_ui(self, info_dict):
        """Prepare subtitle data and refresh UI"""
        self.current_sub_data = [] 
        self.sub_checkboxes = {} 
        
        subtitles = info_dict.get('subtitles', {})
        if isinstance(subtitles, list):
            new_subs = {}
            for item in subtitles:
                if isinstance(item, str): new_subs[item] = []
                elif isinstance(item, dict):
                    code = item.get('code') or item.get('lang') or item.get('language')
                    if code: new_subs[code] = [item]
            subtitles = new_subs

        automatic_captions = info_dict.get('automatic_captions', {})
        if isinstance(automatic_captions, list): 
             new_auto = {}
             for item in automatic_captions:
                if isinstance(item, str): new_auto[item] = []
                elif isinstance(item, dict):
                    code = item.get('code') or item.get('lang') or item.get('language')
                    if code: new_auto[code] = [item]
             automatic_captions = new_auto
        
        # 1. Official Subtitles
        if subtitles:
            for code, sub_info in subtitles.items():
                name = code
                if sub_info and 'name' in sub_info[0]:
                    name = f"{sub_info[0]['name']} ({code})"
                else: 
                     lang_name = CODE_TO_NAME.get(code)
                     if lang_name: name = f"[{code}] {lang_name}"
                
                self.current_sub_data.append({
                    "code": code, "name": name, "type": "official"
                })
        
        # 2. Auto Captions
        if automatic_captions:
            for code in automatic_captions.keys():
                lang_name = CODE_TO_NAME.get(code, code)
                name = f"[自動] {lang_name} ({code})"
                
                self.current_sub_data.append({
                    "code": code, "name": name, "type": "auto"
                })

        # Initial Render
        self._refresh_subtitle_view("")
        
        if not self.current_sub_data:
             if hasattr(self, 'lbl_sub_hint'): self.lbl_sub_hint.configure(text="分析完成：無字幕")
        else:
             if hasattr(self, 'lbl_sub_hint'): self.lbl_sub_hint.configure(text="分析完成：請勾選要下載的字幕軌")

    def _refresh_subtitle_view(self, query=""):
        # Clear existing
        for widget in self.scroll_subs.winfo_children():
            widget.destroy()
            
        if not self.current_sub_data:
            ctk.CTkLabel(self.scroll_subs, text="無可用字幕 (請先執行分析)", text_color="gray").pack(pady=20)
            return

        query = query.lower().strip()
        filtered = []
        for item in self.current_sub_data:
            if not query or query in item['code'].lower() or query in item['name'].lower():
                filtered.append(item)
        
        if not filtered:
             ctk.CTkLabel(self.scroll_subs, text="找不到符合的語言", text_color="gray").pack(pady=20)
             return

        # Grouping Logic
        fav_codes = ['zh-tw', 'zh-hant', 'zh-hans', 'zh-cn', 'en', 'en-us', 'ja', 'ko']
        
        # Define Regions (Prefix based)
        asia_codes = ['zh', 'ja', 'ko', 'vi', 'th', 'id', 'ms', 'hi', 'bn', 'my', 'tl', 'lo', 'km', 'mn', 'ne', 'si', 'ur', 'pa']
        eu_codes = ['fr', 'de', 'it', 'es', 'pt', 'ru', 'uk', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'el', 'tr', 'cs', 'hu', 'ro', 'bg', 'hr', 'sr', 'sk', 'sl', 'et', 'lv', 'lt']
        
        groups = {
            "🌟 常用語言 (Favorites)": [],
            "🌏 亞洲地區 (Asia)": [],
            "🌍 歐美與其他地區 (Europe / Americas / Others)": [],
            "🤖 自動生成 (Auto-generated)": []
        }
        
        for item in filtered:
            code = item['code'].lower()
            base_code = code.split('-')[0]
            
            if item['type'] == 'auto':
                groups["🤖 自動生成 (Auto-generated)"].append(item)
            elif code in fav_codes:
                groups["🌟 常用語言 (Favorites)"].append(item)
            elif base_code in asia_codes:
                groups["🌏 亞洲地區 (Asia)"].append(item)
            else:
                groups["🌍 歐美與其他地區 (Europe / Americas / Others)"].append(item)

        # Render Groups
        row_idx = 0
        
        def create_group_section(title, items):
            nonlocal row_idx
            if not items: return
            
            # Header (Span 2 cols)
            header = ctk.CTkLabel(self.scroll_subs, text=title, font=("Microsoft JhengHei UI", 13, "bold"), text_color=("#1F6AA5", "#88C0D0"))
            header.grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(10, 5), padx=5)
            row_idx += 1
            
            # Sub-grid layout for items
            for i, item in enumerate(items):
                code = item['code']
                
                # Create/Retrieve Variable
                if code not in self.sub_checkboxes:
                    var = ctk.BooleanVar(value=False)
                    # Auto select logic removed
                    self.sub_checkboxes[code] = var
                else:
                    var = self.sub_checkboxes[code]
                
                # Checkbox
                chk = ctk.CTkCheckBox(self.scroll_subs, text=item['name'], variable=var, font=self.font_text)
                
                r = row_idx + (i // 2)
                c = i % 2
                chk.grid(row=r, column=c, sticky="w", padx=10, pady=2)
            
            # Update row_idx for next group
            row_idx += (len(items) + 1) // 2

        create_group_section("🌟 常用語言 (Favorites)", groups["🌟 常用語言 (Favorites)"])
        create_group_section("🌏 亞洲地區 (Asia)", groups["🌏 亞洲地區 (Asia)"])
        create_group_section("🌍 歐美與其他地區 (Europe / Americas / Others)", groups["🌍 歐美與其他地區 (Europe / Americas / Others)"])
        create_group_section("🤖 自動生成 (Auto-generated)", groups["🤖 自動生成 (Auto-generated)"])

    def _old_refresh_subtitle_view(self, query=""):
        # Clear existing
        for widget in self.scroll_subs.winfo_children():
            widget.destroy()
            
        if not self.current_sub_data:
            ctk.CTkLabel(self.scroll_subs, text="無可用字幕", text_color="gray").pack(pady=20)
            return

        query = query.lower().strip()
        filtered = []
        for item in self.current_sub_data:
            # Simple fuzzy match
            if not query or query in item['code'].lower() or query in item['name'].lower():
                filtered.append(item)
        
        if not filtered:
             ctk.CTkLabel(self.scroll_subs, text="找不到符合的語言", text_color="gray").pack(pady=20)
             return

        fav_codes = ['zh-tw', 'zh-hant', 'zh-hans', 'zh-cn', 'en', 'en-us', 'ja', 'ko']
        
        groups = {
            "🌟 常用語言 (Favorites)": [],
            "🌏 其他語言 (Others)": [],
            "🤖 自動生成 (Auto-generated)": []
        }
        
        for item in filtered:
            code_lower = item['code'].lower()
            if item['type'] == 'auto':
                groups["🤖 自動生成 (Auto-generated)"].append(item)
            elif code_lower in fav_codes:
                groups["🌟 常用語言 (Favorites)"].append(item)
            else:
                groups["🌏 其他語言 (Others)"].append(item)

        # Render Groups
        row_idx = 0
        
        def create_group_section(title, items):
            nonlocal row_idx
            if not items: return
            
            # Header (Span 2 cols)
            header = ctk.CTkLabel(self.scroll_subs, text=title, font=("Microsoft JhengHei UI", 13, "bold"), text_color="#1F6AA5")
            header.grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(10, 5), padx=5)
            row_idx += 1
            
            # Sub-grid layout for items
            for i, item in enumerate(items):
                code = item['code']
                
                # Create/Retrieve Variable
                if code not in self.sub_checkboxes:
                    var = ctk.BooleanVar(value=False)
                    if code.lower() == 'zh-tw' and item['type'] == 'official': 
                        var.set(True) 
                    self.sub_checkboxes[code] = var
                else:
                    var = self.sub_checkboxes[code]
                
                # Checkbox
                chk = ctk.CTkCheckBox(self.scroll_subs, text=item['name'], variable=var, font=self.font_text)
                
                r = row_idx + (i // 2)
                c = i % 2
                chk.grid(row=r, column=c, sticky="w", padx=10, pady=2)
            
            # Update row_idx for next group
            row_idx += (len(items) + 1) // 2

        create_group_section("🌟 常用/推薦 (Recommended)", groups["🌟 常用語言 (Favorites)"])
        create_group_section("🌏 其他官方字幕 (Official)", groups["🌏 其他語言 (Others)"])
        create_group_section("🤖 自動翻譯/生成 (Auto-generated)", groups["🤖 自動生成 (Auto-generated)"])

    def _deprecated_update_subtitle_list_ui(self, info_dict):
        """(Old Version) 根據 ytdlp 資訊，動態更新字幕列表 Checkbox"""
        # 清空
        for widget in self.scroll_subs.winfo_children():
            widget.destroy()
        self.sub_checkboxes = {}
        
        subtitles = info_dict.get('subtitles', {})
        automatic_captions = info_dict.get('automatic_captions', {})
        
        has_any = False
        
        # 1. 創作者上傳字幕 (Subtitles)
        if subtitles:
            has_any = True
            row_idx = 0
            ctk.CTkLabel(self.scroll_subs, text="【官方/CC 字幕】", font=("Microsoft JhengHei UI", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", pady=(5, 0))
            
            for code, sub_info in subtitles.items():
                # 找出名稱
                display_name = code
                if sub_info and 'name' in sub_info[0]:
                    display_name = f"{sub_info[0]['name']} ({code})"
                else: 

                     lang_name = CODE_TO_NAME.get(code)
                     if lang_name: display_name = f"[{code}] {lang_name}"

                var = ctk.BooleanVar(value=False)
                if code == 'zh-TW': var.set(True) 
                self.sub_checkboxes[code] = var
                
                chk = ctk.CTkCheckBox(self.scroll_subs, text=display_name, variable=var, font=self.font_text)
                chk.pack(anchor="w", padx=10, pady=2)

        # 2. 自動生成字幕 (Auto-subs)
        if automatic_captions:
            has_any = True
            ctk.CTkLabel(self.scroll_subs, text="【自動翻譯/生成字幕】 (可能不準確)", font=("Microsoft JhengHei UI", 12, "bold"), text_color="#E0aaff").pack(anchor="w", pady=(15, 0))
            
            # 常見語言優先排序
            priority = ['zh-Hant', 'zh-Hans', 'en', 'ja', 'ko']
            sorted_keys = sorted(automatic_captions.keys(), key=lambda x: (priority.index(x) if x in priority else 999, x))
            
            for code in sorted_keys:
                display_name = f"自動生成 - {code}"
                
                var = ctk.BooleanVar(value=False)
                self.sub_checkboxes[f"auto-{code}"] = var
                
                chk = ctk.CTkCheckBox(self.scroll_subs, text=display_name, variable=var, font=self.font_text)
                chk.pack(anchor="w", padx=10, pady=2)
                
        if not has_any:
            ctk.CTkLabel(self.scroll_subs, text="找不到任何字幕", text_color="red").pack(pady=20)
            self.lbl_sub_hint.configure(text="分析完成：無字幕")
        else:
            self.lbl_sub_hint.configure(text="分析完成：請勾選要下載的字幕軌")

    def setup_output_ui(self):
        # 建立捲動區域
        scroll_container = ctk.CTkScrollableFrame(self.tab_output, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Helper: Section Card ---
        def create_section_card(parent, title, icon="⚙️"):
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "gray20"), corner_radius=15)
            frame.pack(fill="x", pady=10, padx=10)
            
            # Header
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
            # Content Container
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=(0, 20))
            return content

        # --- 1. 時間剪輯 (Time Cut) ---
        cut_card = create_section_card(scroll_container, "剪輯與裁剪 (Trim & Cut)", icon="✂️")

        self.var_cut = ctk.BooleanVar(value=False)
        
        def reset_time_range():
            self.entry_start.delete(0, "end")
            self.entry_end.delete(0, "end")
            
        def toggle_cut():
             is_on = self.var_cut.get()
             state = "normal" if is_on else "disabled"
             self.entry_start.configure(state=state)
             self.entry_end.configure(state=state)
             self.btn_reset_time.configure(state=state)
             self.lbl_arrow.configure(text_color="#1F6AA5" if is_on else "gray")
             
             if is_on:
                 self.entry_start.configure(placeholder_text="000000")
                 self.entry_end.configure(placeholder_text="000500")
             
        self.chk_cut = ctk.CTkCheckBox(cut_card, text="啟用時間裁切 (下載部分片段)", font=("Microsoft JhengHei UI", 14, "bold"), variable=self.var_cut, command=toggle_cut)
        self.chk_cut.pack(anchor="w", pady=(5, 15))
        CTkToolTip(self.chk_cut, "僅下載影片的指定時間範圍，格式為 HHMMSS，例如 000130")
        
        # Time Inputs (New Style)
        time_box = ctk.CTkFrame(cut_card, fg_color=("gray90", "#2B2B2B"), corner_radius=8)
        time_box.pack(fill="x", padx=10, pady=5)
        
        inner = ctk.CTkFrame(time_box, fg_color="transparent")
        inner.pack(padx=15, pady=15)
        
        # Start
        self.entry_start = ctk.CTkEntry(inner, width=110, placeholder_text="000000", height=38, 
                                        font=("Consolas", 15, "bold"), justify="center", state="disabled")
        self.entry_start.pack(side="left")
        
        # Arrow
        self.lbl_arrow = ctk.CTkLabel(inner, text="➔", font=("Arial", 20), text_color="gray")
        self.lbl_arrow.pack(side="left", padx=15)
        
        # End
        self.entry_end = ctk.CTkEntry(inner, width=110, placeholder_text="000500", height=38,
                                      font=("Consolas", 15, "bold"), justify="center", state="disabled")
        self.entry_end.pack(side="left")
        
        # Reset Button (Circular Style)
        self.btn_reset_time = ctk.CTkButton(inner, text="↺", width=38, height=38, 
                                            fg_color=("gray85", "gray30"), hover_color=("gray75", "gray40"),
                                            text_color=("gray20", "gray90"),
                                            font=("Microsoft JhengHei UI", 20, "bold"),
                                            corner_radius=19, state="disabled", command=reset_time_range)
        self.btn_reset_time.pack(side="left", padx=(20, 0))
        CTkToolTip(self.btn_reset_time, "重設為預設值")

        # --- 2. 排程下載 (Scheduler) ---
        sched_card = create_section_card(scroll_container, "預約排程下載 (Scheduler)", icon="🕒")
        
        if not hasattr(self, 'var_schedule_enable'): self.var_schedule_enable = ctk.BooleanVar(value=False)
        
        # Row 1: Switch
        s_sched = ctk.CTkSwitch(sched_card, text="啟用指定時間下載 (離峰下載)", variable=self.var_schedule_enable, 
                                font=("Microsoft JhengHei UI", 13, "bold"), progress_color="#2CC985", button_hover_color="#20A068", height=32)
        s_sched.pack(anchor="w", padx=20, pady=5)
        CTkToolTip(s_sched, "開啟後，新增的任務會暫停，直到指定時間才開始下載。\n適合掛機下載大型清單。")
        
        # Row 2: Time Input
        t_frame = ctk.CTkFrame(sched_card, fg_color="transparent")
        t_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(t_frame, text="每日啟動時間 :", font=("Microsoft JhengHei UI", 12)).pack(side="left")
        
        self.entry_schedule_time = ctk.CTkEntry(t_frame, width=100, placeholder_text="2330", 
                                                font=("Consolas", 14, "bold"), justify="center")
        self.entry_schedule_time.pack(side="left", padx=10)
        self.entry_schedule_time.insert(0, "0000")
        
        
        ctk.CTkLabel(t_frame, text="(24小時制 HHMM)", text_color="gray", font=("Microsoft JhengHei UI", 11)).pack(side="left")

        # --- 3. 任務完成後 (After Completion) ---
        after_card = create_section_card(scroll_container, "任務完成後動作 (When Finished)", icon="🏁")
        
        if not hasattr(self, 'var_after_completion'): self.var_after_completion = ctk.StringVar(value="none")
        
        # Custom Segmented Control Container
        seg_bg = ctk.CTkFrame(after_card, fg_color=("gray90", "#1C1C1C"), corner_radius=12)
        seg_bg.pack(fill="x", padx=20, pady=10)
        
        # Options Data: (Title, Value, Icon)
        self.after_opts = [
            ("保持開啟", "none", "☀"), 
            ("進入睡眠", "sleep", "🌙"), 
            ("自動關機", "shutdown", "🔌")
        ]
        
        self.after_btns = {}

        def update_after_visuals():
            current = self.var_after_completion.get()
            for title, code, icon in self.after_opts:
                btn = self.after_btns.get(code)
                if not btn: continue
                
                if code == current:
                    # Selected: "Floating" look (White/Lighter bg + Color Text)
                    btn.configure(
                        fg_color=("white", "#5A5A5A"), 
                        text_color=("#1F6AA5", "#88C0D0"),
                        border_color=("#1F6AA5", "#88C0D0"),
                        border_width=2
                    )
                else:
                    # Unselected: Flat Transparent
                    btn.configure(
                        fg_color="transparent", 
                        text_color=("gray50", "gray70"),
                        border_width=0
                    )

        def on_after_click(code):
            self.var_after_completion.set(code)
            update_after_visuals()
            
            # Update Hint
            hint = "執行完畢後保持電腦開啟"
            if code == "sleep": hint = "所有任務完成後 (佇列清空)，倒數 60 秒進入睡眠模式"
            elif code == "shutdown": hint = "所有任務完成後 (佇列清空)，倒數 60 秒自動關機"
            
            self.lbl_after_hint.configure(text=f"{hint}", text_color=("#1F6AA5", "#88C0D0"))
            if hasattr(self, 'check_queue'): self.check_queue()

        # Create Buttons Grid
        seg_bg.grid_columnconfigure(0, weight=1)
        seg_bg.grid_columnconfigure(1, weight=1)
        seg_bg.grid_columnconfigure(2, weight=1)
        
        for i, (title, code, icon) in enumerate(self.after_opts):
            # Using \n for vertical stacking of Icon and Text
            btn_text = f"{icon}\n{title}"
            
            btn = ctk.CTkButton(
                seg_bg, 
                text=btn_text,
                font=("Microsoft JhengHei UI", 13, "bold"),
                width=100, height=50,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("white", "#404040"),
                command=lambda c=code: on_after_click(c)
            )
            btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            
            # Tweak font for the Icon line if possible (TKinter limitation: one font per widget). 
            # We'll stick to a robust font size.
            
            self.after_btns[code] = btn

        # Hint Label
        self.lbl_after_hint = ctk.CTkLabel(after_card, text="執行完畢後保持電腦開啟。", text_color=("#1F6AA5", "#88C0D0"), font=("Microsoft JhengHei UI", 12))
        self.lbl_after_hint.pack(padx=20, pady=(0, 15), anchor="w")
        
        # Init State
        # Ensure default valid
        if self.var_after_completion.get() not in [x[1] for x in self.after_opts]:
             self.var_after_completion.set("none")
             
        on_after_click(self.var_after_completion.get())

    def setup_advanced_ui(self):
        # 建立捲動區域以容納更多設定
        scroll_container = ctk.CTkScrollableFrame(self.tab_adv, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Helper: Section Card ---
        def create_section_card(parent, title, icon="⚙️"):
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "gray20"), corner_radius=15)
            frame.pack(fill="x", pady=10, padx=10)
            
            # Header
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray10", "gray90")).pack(side="left") # Standard Text
            
            # Content Container
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=(0, 20))
            return content

        # --- 1. Cookie 來源 (Cookies) ---
        cookie_card = create_section_card(scroll_container, "帳號授權與 Cookie (Account)", icon="🍪")
        
        self.var_cookie_mode = ctk.StringVar(value="none")
        
        # Sub-section: Browser
        b_header = ctk.CTkFrame(cookie_card, fg_color="transparent")
        b_header.pack(fill="x", pady=(5, 10))
        ctk.CTkLabel(b_header, text="從瀏覽器讀取 (推薦)", font=("Microsoft JhengHei UI", 14, "bold"), text_color="gray").pack(side="left")
        
        lbl_b_help = ctk.CTkLabel(b_header, text="❓", cursor="hand2", font=self.font_small)
        lbl_b_help.pack(side="left", padx=5)
        CTkToolTip(lbl_b_help, "【說明】\n程式會自動讀取您選擇的瀏覽器中 YouTube 的登入狀態。\n無需手動匯出檔案，設定與更新最方便，但穩定度低。\n若無法使用，建議使用下方cookies.txt方式。\n注意：執行下載時建議先將該瀏覽器「完全關閉」，以免讀取失敗。")
        
        # Browser Grid (Chips/Pills Style)
        browser_grid = ctk.CTkFrame(cookie_card, fg_color="transparent")
        browser_grid.pack(fill="x", pady=5)
        
        browsers = [
            ("不使用", "none"), ("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox"),
            ("Opera", "opera"), ("Brave", "brave"), ("Vivaldi", "vivaldi"), ("Chromium", "chromium")
        ]
        
        self.browser_btns = {}

        def on_browser_click(val):
            self.var_cookie_mode.set(val)
            self.on_cookie_mode_change()
            update_browser_visuals()
            if hasattr(self, 'save_config'): self.save_config()

        def update_browser_visuals():
            current = self.var_cookie_mode.get()
            for val, btn in self.browser_btns.items():
                if val == current:
                    btn.configure(
                        fg_color="#1F6AA5", 
                        text_color="white", 
                        border_width=0,
                        hover_color="#144870" 
                    )
                else:
                    btn.configure(
                        fg_color=("white", "#333333"), 
                        text_color=("gray20", "gray80"), 
                        border_width=1, 
                        border_color=("gray70", "gray50"),
                        hover_color=("gray90", "#404040") 
                    )

        for i, (text, val) in enumerate(browsers):
            btn = ctk.CTkButton(
                browser_grid, 
                text=text, 
                height=32,
                font=self.font_text,
                corner_radius=16,
                fg_color=("white", "#333333"), 
                border_width=1,
                border_color=("gray70", "gray50"),
                text_color=("gray20", "gray80"),
                hover_color=("gray90", "#404040"), 
                command=lambda v=val: on_browser_click(v)
            )
            btn.grid(row=i//4, column=i%4, padx=6, pady=6, sticky="ew")
            self.browser_btns[val] = btn
            browser_grid.grid_columnconfigure(i%4, weight=1)

        update_browser_visuals()

        CTkToolTip(browser_grid, "自動讀取瀏覽器登入狀態 (例如 YouTube Premium 會員)。\n執行前建議完全關閉瀏覽器以避免讀取鎖定。")

        # Sub-section: File
        ctk.CTkFrame(cookie_card, height=2, fg_color=("gray85", "gray30")).pack(fill="x", pady=20) # Divider
        
        f_header = ctk.CTkFrame(cookie_card, fg_color="transparent")
        f_header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_header, text="使用 cookies.txt (穩定)", font=("Microsoft JhengHei UI", 14, "bold"), text_color="gray").pack(side="left")
        
        lbl_f_help = ctk.CTkLabel(f_header, text="❓", cursor="hand2", font=self.font_small)
        lbl_f_help.pack(side="left", padx=5)
        CTkToolTip(lbl_f_help, "【如何取得 cookies.txt ?】\n建議點擊右側連結安裝「Get cookies.txt LOCALLY」擴充功能。\n安裝後：到 YouTube 首頁登入 -> 點擊擴充功能圖示 -> \"Export\" -> 下載")
        
        # Links
        link_box = ctk.CTkFrame(f_header, fg_color="transparent")
        link_box.pack(side="right")
        
        def make_link(parent, text, url):
            lbl = ctk.CTkLabel(parent, text=text, text_color="#3B8ED0", cursor="hand2", font=self.font_small)
            lbl.pack(side="left", padx=5)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            lbl.bind("<Enter>", lambda e: lbl.configure(text_color="#1F6AA5"))
            lbl.bind("<Leave>", lambda e: lbl.configure(text_color="#3B8ED0"))
            
        make_link(link_box, "[Chrome/Edge 擴充]", "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
        make_link(link_box, "[Firefox 擴充]", "https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/")
        

        
        f_input_box = ctk.CTkFrame(cookie_card, fg_color="transparent")
        f_input_box.pack(fill="x", padx=10)
        
        def on_file_mode_click():
            self.var_cookie_mode.set("file")
            self.on_cookie_mode_change()
            update_browser_visuals()
            if hasattr(self, 'save_config'): self.save_config()
            
        btn_file_mode = ctk.CTkButton(
            f_input_box, text="檔案模式", width=100, height=32, corner_radius=16,
            fg_color="transparent", border_width=1, border_color=("gray70", "gray50"), text_color=("gray20", "gray80"),
            hover_color=("#D0E0F0", "#3A3A3A"),
            command=on_file_mode_click
        )
        btn_file_mode.pack(side="left", padx=(0, 10))
        self.browser_btns['file'] = btn_file_mode 

        self.entry_cookie_path = ctk.CTkEntry(f_input_box, placeholder_text="請選擇 cookies.txt...", state="disabled", height=35)
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_cookie_browse = ctk.CTkButton(f_input_box, text="瀏覽", width=80, height=35, state="disabled", fg_color="#555555", command=self.browse_cookie_file)
        self.btn_cookie_browse.pack(side="left")

        # --- 2. 效能設定 (Performance) ---
        perf_card = create_section_card(scroll_container, "效能設定 (Performance)", icon="🚀")
        
        ctk.CTkLabel(perf_card, text="最大同時下載數", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        
        perf_box = ctk.CTkFrame(perf_card, fg_color="transparent")
        perf_box.pack(fill="x", pady=5)
        
        concurrent_values = [str(i) for i in range(1, 11)]
        self.combo_concurrent = ctk.CTkOptionMenu(perf_box, values=concurrent_values, width=120, height=35, command=self.update_concurrent_label, 
                                                  fg_color=("gray90", "gray30"), text_color=("black", "white"),
                                                  button_color=("gray80", "gray40"), button_hover_color=("gray75", "gray35"))
        self.combo_concurrent.pack(side="left")
        self.combo_concurrent.set("1")
        
        ctk.CTkLabel(perf_box, text="(建議值: 1~3)", text_color="gray", font=self.font_small).pack(side="left", padx=15)

        # --- 3. 網路設定 (Network) ---
        net_card = create_section_card(scroll_container, "網路連接設定 (Network)", icon="🌐")
        
        # UA
        ctk.CTkLabel(net_card, text="User Agent (偽裝瀏覽器)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.entry_ua = ctk.CTkEntry(net_card, height=35, placeholder_text="預設 (自動隨機)", border_color=("gray70", "gray40"))
        self.entry_ua.pack(fill="x", pady=5)
        CTkToolTip(self.entry_ua, "若遇網站阻擋，可填入特定瀏覽器的 UA 字串。")
        
        # Proxy
        proxy_header = ctk.CTkFrame(net_card, fg_color="transparent")
        proxy_header.pack(fill="x", pady=(15, 5))
        
        ctk.CTkLabel(proxy_header, text="Proxy 代理伺服器", font=self.font_title, text_color="gray").pack(side="left")
        
        self.var_remember_proxy = ctk.BooleanVar(value=False)
        def on_proxy_toggle():
             if hasattr(self, 'save_config'): self.save_config()
             
        self.chk_remember_proxy = ctk.CTkSwitch(
            proxy_header, text="記住設定", variable=self.var_remember_proxy, 
            font=self.font_small, width=80, height=20,
            command=on_proxy_toggle, progress_color="#2CC985", button_hover_color="#20A068"
        )
        self.chk_remember_proxy.pack(side="right")

        self.entry_proxy = ctk.CTkEntry(net_card, height=35, placeholder_text="http://user:pass@host:port", border_color=("gray70", "gray40"))
        self.entry_proxy.pack(fill="x", pady=5)
        CTkToolTip(self.entry_proxy, "若需翻牆或隱藏 IP，請輸入 Proxy (支援 http/https/socks5)。")

        # --- Event Bindings for Immediate Feedback ---
        self.last_ua = ""
        self.last_proxy = ""

        def on_net_change(event=None):
            # Check UA
            curr_ua = self.entry_ua.get().strip()
            if curr_ua != self.last_ua:
                self.last_ua = curr_ua
                if curr_ua:
                    self.log(f"[設定變更] User Agent 已更新")
                    self.show_toast("User Agent 已更新")
                if hasattr(self, 'save_config'): self.save_config()
            
            # Check Proxy
            curr_proxy = self.entry_proxy.get().strip()
            if curr_proxy != self.last_proxy:
                self.last_proxy = curr_proxy
                if curr_proxy:
                    self.log(f"[設定變更] Proxy 已更新")
                    self.show_toast("Proxy 已更新")

        self.entry_ua.bind("<FocusOut>", on_net_change)
        self.entry_ua.bind("<Return>", on_net_change)
        self.entry_proxy.bind("<FocusOut>", on_net_change)
        self.entry_proxy.bind("<Return>", on_net_change)
        
    def on_cookie_mode_change(self):
        mode = self.var_cookie_mode.get()
        if mode == "file":
            self.entry_cookie_path.configure(state="normal")
            self.btn_cookie_browse.configure(state="normal", fg_color="#1F6AA5")
            self.log("[設定變更] Cookie 來源切換為: 檔案 (cookies.txt)")
            self.show_toast("Cookie 來源: 檔案")
        else:
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color="#555555")
            
            if mode == 'none':
                 pass
            else:
                 self.log(f"[設定變更] Cookie 來源切換為: 瀏覽器 ({mode})")
                 self.show_toast(f"Cookie 來源: {mode}")

    def update_concurrent_label(self, value):
        self.max_concurrent_downloads = int(value)
        self.log(f"[設定變更] 最大同時下載數: {value}")
        self.show_toast(f"最大同時下載數: {value}")
        if hasattr(self, 'save_config'): self.save_config()
            
    def browse_cookie_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if p:
            self.entry_cookie_path.delete(0, "end")
            self.entry_cookie_path.insert(0, p)

    # --- Changelog Viewer ---
    def show_changelog(self):
        """讀取並顯示 CHANGELOG.md (最近 1 次更新)"""
        try:
            import sys
            import re
            import os
            import tkinter as tk 
            import textwrap 
            
            # --- Changelog Loading Logic ---
            # 1. 優先嘗試匯入由 build_onedir.py 生成的靜態檔案 (打包版)
            try:
                from .changelog_gen import CHANGELOG_TEXT
            except ImportError:
                # 2. 開發模式：動態讀取專案根目錄的 CHANGELOG.md
                CHANGELOG_TEXT = ""
                try:
                    import sys
                    if getattr(sys, 'frozen', False):
                        base = os.path.dirname(sys.executable)
                    else:
                        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
                    
                    log_file = os.path.join(base, "CHANGELOG.md")
                    if os.path.exists(log_file):
                        with open(log_file, "r", encoding="utf-8") as f:
                            CHANGELOG_TEXT = f.read()
                    else:
                        CHANGELOG_TEXT = "## [Dev]\n目前為開發模式，未偵測到 CHANGELOG.md。"
                except Exception as e:
                    CHANGELOG_TEXT = f"Error loading changelog: {e}"

            content = textwrap.dedent(CHANGELOG_TEXT).strip()
            
            # 2. 簡易解析：只取最新版本
            parts = re.split(r'(^## \[)', content, flags=re.MULTILINE)
            display_text = parts[0] 
            count = 0
            for i in range(1, len(parts), 2):
                if count >= 1: break
                if i+1 < len(parts):
                    display_text += parts[i] + parts[i+1]
                    count += 1
            content = display_text.strip()
            
            # 3. 顯示視窗
            top = ctk.CTkToplevel(self)
            top.title("本次更新內容")
            top.geometry("500x350")
            
            # Center window
            x = self.winfo_x() + (self.winfo_width() // 2) - 250
            y = self.winfo_y() + (self.winfo_height() // 2) - 175
            top.geometry(f"+{x}+{y}")
            top.attributes("-topmost", True)
            
            # --- Markdown Formatter ---
            def format_markdown(text):
                lines = text.split('\n')
                formatted = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        formatted.append("")
                        continue
                    
                    # 處理標題 (## V1.0.0) -> [V1.0.0]
                    if line.startswith('## '):
                        # 擷取版本號 (移除 ## 與前後空白)
                        ver_txt = line.replace('## ', '').strip()
                        formatted.append(f"\n━━━ {ver_txt} ━━━")
                    
                    # 處理小標題 (### Added) -> Added
                    elif line.startswith('### '):
                        sub_cat = line.replace('### ', '').strip()
                        formatted.append(f"\n[{sub_cat}]")
                        
                    # 處理列表 (- Item) -> • Item
                    elif line.startswith('- '):
                        item = line[2:] 
                        # 移除粗體記號
                        item = item.replace('**', '') 
                        formatted.append(f"  • {item}")
                    
                    # 其他文字
                    else:
                        # 移除 # 
                        clean_line = line.lstrip('#').strip()
                        if clean_line: formatted.append(clean_line)
                
                return "\n".join(formatted)
            # --------------------------------
            
            pretty_content = format_markdown(content)

            textbox = ctk.CTkTextbox(top, font=("Microsoft JhengHei UI", 14), wrap="word", height=400)
            textbox.pack(fill="both", expand=True, padx=15, pady=15)
            
            # 設定 Tag 樣式不一定對所有字體生效，主要靠排版
            textbox.insert("1.0", pretty_content)
            textbox.configure(state="disabled") 
            
        except Exception as e:
            if hasattr(self, 'show_toast'):
                self.show_toast("錯誤", f"無法讀取日誌: {e}")
            else:
                tk.messagebox.showerror("Error", str(e))


    def setup_log_ui(self):
        # 1. 工具列 (Toolbar)
        toolbar = ctk.CTkFrame(self.tab_log, fg_color="transparent", height=40)
        toolbar.pack(fill="x", padx=10, pady=(15, 5))
        
        # Title with Icon
        ctk.CTkLabel(toolbar, text="💻 運行日誌 (Console)", font=("Microsoft JhengHei UI", 14, "bold"), text_color=("#1F6AA5", "#88C0D0")).pack(side="left", padx=5)
        
        # Helper functions
        def copy_logs():
            if hasattr(self, 'txt_log'):
                self.clipboard_clear()
                self.clipboard_append(self.txt_log.get("1.0", "end"))
                if hasattr(self, 'show_toast'): self.show_toast("已複製日誌內容")

        def clear_logs_action():
            if hasattr(self, 'txt_log'):
                self.txt_log.configure(state="normal")
                self.txt_log.delete("1.0", "end")
                self.txt_log.configure(state="disabled")

        # Buttons (Clean Style)
        ctk.CTkButton(
            toolbar, text="🗑 清空", width=80, height=30, 
            fg_color="transparent", border_width=1, border_color="#DB3E39", text_color="#DB3E39",
            hover_color=("#FEE", "#400"), 
            font=self.font_small, command=clear_logs_action
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            toolbar, text="📋 複製全部", width=90, height=30, 
            fg_color="#1F6AA5", hover_color="#144870", 
            font=self.font_small, command=copy_logs
        ).pack(side="right", padx=5)

        # 2. Log Console (Dark Theme Terminal)
        self.console_container = ctk.CTkFrame(self.tab_log, fg_color="#1E1E1E", corner_radius=8, border_width=1, border_color="#333333")
        self.console_container.pack(fill="both", expand=True, padx=10, pady=(5, 15))
        
        # Textbox (Terminal Style)
        self.txt_log = ctk.CTkTextbox(
            self.console_container,
            font=("Consolas", 13), 
            text_color="#E0E0E0",  
            fg_color="#1E1E1E",    
            scrollbar_button_color="#333333",
            scrollbar_button_hover_color="#444444",
            border_width=0,
            activate_scrollbars=True
        )
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt_log.configure(state="disabled") 

    def clear_log(self):
        if hasattr(self, 'txt_log'):
             self.txt_log.configure(state="normal")
             self.txt_log.delete("1.0", "end")
             self.txt_log.configure(state="disabled")
        
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}\n"
        
        tag = "info"
        if any(x in msg for x in ["[錯誤]", "Error", "失敗", "系統錯誤"]):
            tag = "error"
        elif any(x in msg for x in ["[警告]", "Warning", "無效"]):
            tag = "warning"
        elif any(x in msg for x in ["成功", "完成", "啟動下載"]):
            tag = "success"
            
        try:
            self.txt_log.configure(state="normal")
            
            self.txt_log.tag_config("error", foreground="#FF5555")   
            self.txt_log.tag_config("warning", foreground="#FFB86C") 
            self.txt_log.tag_config("success", foreground="#50FA7B")
            self.txt_log.tag_config("info", foreground="#E0E0E0")    
            
            self.txt_log.insert("end", full_msg, tag)
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except: pass
        print(full_msg.strip())

    def setup_settings_ui(self):
        """設定分頁 (List Style - Refined)"""
        # Main Scrollable
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.pack(fill="both", expand=True)

        # Main Container
        container = ctk.CTkFrame(self.settings_scroll, fg_color=("gray95", "gray20"), corner_radius=12)
        container.pack(fill="x", padx=20, pady=20)
        
        # --- 1. Top Section ---
        top_frame = ctk.CTkFrame(container, fg_color="transparent")
        top_frame.pack(fill="x", padx=30, pady=20)
        top_frame.grid_columnconfigure(1, weight=1)
        
        # Theme Row
        ctk.CTkLabel(top_frame, text="🌗", font=("Segoe UI Emoji", 18)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ctk.CTkLabel(top_frame, text="主題設定", font=("Microsoft JhengHei UI", 15, "bold")).grid(row=0, column=0, sticky="w", padx=(35, 0))
        
        # Theme Custom Segmented Control
        theme_seg_bg = ctk.CTkFrame(top_frame, fg_color=("gray90", "#1C1C1C"), corner_radius=10, height=45) 
        theme_seg_bg.grid(row=0, column=1, sticky="e")
        
        self.theme_opts = [
            ("跟隨系統", "System", "💻"), 
            ("淺色", "Light", "☀"), 
            ("深色", "Dark", "☾")
        ]
        self.theme_btns = {}

        def update_theme_visuals():
            current = ctk.get_appearance_mode() 
            pass

        def on_theme_click(mode_name):
            self.change_appearance_mode_event(mode_name)
            # Manually update visuals
            for title, code, icon in self.theme_opts:
                btn = self.theme_btns.get(code)
                if not btn: continue
                
                if code == mode_name:
                    btn.configure(
                        fg_color=("white", "#5A5A5A"), 
                        text_color=("#1F6AA5", "#88C0D0"),
                        border_color=("#1F6AA5", "#88C0D0"),
                        border_width=1
                    )
                else:
                    btn.configure(
                        fg_color="transparent", 
                        text_color=("gray30", "gray70"),
                        border_width=0
                    )
            # Save config if needed
            if hasattr(self, 'save_config'): self.save_config()

        # Build Theme Buttons
        theme_seg_bg.grid_columnconfigure(0, weight=1)
        theme_seg_bg.grid_columnconfigure(1, weight=1)
        theme_seg_bg.grid_columnconfigure(2, weight=1)
        
        current_mode = ctk.get_appearance_mode()
        
        for i, (title, code, icon) in enumerate(self.theme_opts):
            btn = ctk.CTkButton(
                theme_seg_bg, 
                text=f"{icon} {title}",
                font=("Microsoft JhengHei UI", 12, "bold"),
                width=90, height=35,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("white", "#404040"),
                command=lambda c=code: on_theme_click(c)
            )
            btn.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            self.theme_btns[code] = btn
            
            # Check for initial match (approximate)
            if code == current_mode:
                btn.configure(
                    fg_color=("white", "#5A5A5A"), 
                    text_color=("#1F6AA5", "#88C0D0"),
                    border_color=("#1F6AA5", "#88C0D0"),
                    border_width=1
                )
            elif code == "System" and current_mode not in ["Light", "Dark"]:
                 # Just in case
                 pass

        # Divider
        ctk.CTkFrame(container, height=1, fg_color=("gray90", "#404040")).pack(fill="x")
        
        # --- 2. Toggles Section ---
        toggles_frame = ctk.CTkFrame(container, fg_color="transparent")
        toggles_frame.pack(fill="x", padx=30, pady=20)
        
        # Init Variables
        if not hasattr(self, 'var_clipboard'): self.var_clipboard = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_notification'): self.var_notification = ctk.BooleanVar(value=True)
        if not hasattr(self, 'var_auto_start'): self.var_auto_start = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_auto_update'): self.var_auto_update = ctk.BooleanVar(value=True)
        if not hasattr(self, 'var_always_on_top'): self.var_always_on_top = ctk.BooleanVar(value=False)
        # Fix HW Accel var persistence just in case
        if not hasattr(self, 'var_hardware_accel'): self.var_hardware_accel = ctk.BooleanVar(value=False)

        def _save(): 
             # Apply Always on Top immediately
             if hasattr(self, 'var_always_on_top'):
                 self.attributes("-topmost", self.var_always_on_top.get())
             
             if hasattr(self, 'save_config'): self.save_config()

        def _add_item(icon, title, var, desc):
            f = ctk.CTkFrame(toggles_frame, fg_color="transparent")
            f.pack(fill="x", pady=(0, 20))
            
            # Row 1: Icon | Title | Switch
            r1 = ctk.CTkFrame(f, fg_color="transparent")
            r1.pack(fill="x")
            
            ctk.CTkLabel(r1, text=icon, font=("Segoe UI Emoji", 18), width=30).pack(side="left")
            ctk.CTkLabel(r1, text=title, font=(self.font_family, 15, "bold")).pack(side="left", padx=5)
            
            sw = ctk.CTkSwitch(r1, text="", variable=var, command=_save, progress_color="#2CC985", button_hover_color="#20A068", width=40)
            sw.pack(side="right")
            
            # Row 2: Desc
            ctk.CTkLabel(f, text=desc, font=(self.font_family, 12), text_color=("gray50", "gray60"), wraplength=500, justify="left").pack(anchor="w", padx=(40, 0), pady=(5,0))

        _add_item("📋", "監聽剪貼簿", self.var_clipboard, "若啟用，會自動檢測並搜尋剪貼簿中的影片連結。")
        _add_item("🔔", "通知系統", self.var_notification, "若啟用，下載完成時會發送系統通知。")
        _add_item("⬇", "自動開始下載", self.var_auto_start, "若啟用，新增任務後會自動開始下載。")
        _add_item("🔄", "自動檢查更新", self.var_auto_update, "啟動時檢查更新。")

        # Bottom Divider
        ctk.CTkFrame(container, height=1, fg_color=("gray90", "#404040")).pack(fill="x")

        # Clear Cache
        reset_frame = ctk.CTkFrame(container, fg_color="transparent")
        reset_frame.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(
            reset_frame, 
            text="清理暫存與重置",
            font=("Microsoft JhengHei UI", 15, "bold"), 
            fg_color="transparent", 
            border_width=1,
            border_color="#D93025",
            text_color="#D93025",
            hover_color="#FEE2E2",
            height=35,
            command=self.clear_cache_and_reset
        ).pack(fill="x")

    def clear_cache_and_reset(self):
        """清理暫存並重啟"""
        try:
             import tkinter.messagebox as messagebox
             if messagebox.askyesno("確認", "確定要刪除設定檔與暫存並重啟嗎？\n(所有偏好設定將會流失)"):
                if os.path.exists(self.config_file):
                    os.remove(self.config_file)
                try:
                    self.show_toast("正在重啟...", duration=2000)
                    self.after(1000, lambda: self.restart_app())
                except: pass
        except Exception as e:
             print(f"Clear cache error: {e}")

    def restart_app(self):
        """重新啟動應用程式"""
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def setup_about_ui(self):
        # 主容器 (用於垂直置中)
        main_container = ctk.CTkFrame(self.tab_about, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        
        # --- 1. 資訊小卡 (Info Card) ---
        info_card = ctk.CTkFrame(main_container, fg_color=("gray95", "gray20"), corner_radius=20, border_width=0)
        info_card.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.7)
        
        # (A) 標題區
        title_label = ctk.CTkLabel(info_card, text="MULTIDownload", font=("Microsoft YaHei UI", 36, "bold"), text_color=("#1F6AA5", "#3B8ED0"))
        title_label.pack(pady=(40, 5))
        
        version_label = ctk.CTkLabel(info_card, text=f"Version {APP_VERSION}", font=("Consolas", 12), text_color="gray")
        version_label.pack(pady=(0, 20))
        
        quotes = [
            "這裡沒有 Bug，只有還沒被發現的 Feature 🐛",
            "程式碼寫得爛，但至少能動 ",
            "如果不 work，請嘗試重新開機 ",
            "由 10% 的技術和 90% 的咖啡驅動 ☕",
            "這不是卡住，是在思考人生 ",
            "不要問我為什麼，它就是能跑 🏃",
            "警告：可能包含少量人工智慧 (和大量人工智障) ",
            "如果 run不了，至少還能 walk",
            "只要 Code 能跑，Bug 就是種裝飾",
            "程式碼與我，只有一個能動",
            "只要心態不崩，程式就不算崩",
            "明明不是猴子卻一直在抓 Bug",
            "昨天解決一個 Bug，現在我有八個 Bug",
            "過程全是 Bug，至少還能 Run",
            "點擊這裡並沒有彩蛋 (真的沒有) 🥚",
            "5 mins Coding + 8 hours Debugging = still not moving",
            "99% 人工智障 + 1% 新鮮的肝 = 動不了的垃圾",
            "程式碼不動，是因為它在沉思人生",
        ]
        
        def change_quote(event=None):
            desc_label.configure(text=random.choice(quotes))

        desc_label = ctk.CTkLabel(info_card, text="圖形化多功能影音下載工具", font=("Microsoft JhengHei UI", 14), text_color=("gray40", "gray80"))
        desc_label.pack(pady=(0, 30))
        desc_label.bind("<Button-1>", change_quote)
        
        # (B) 核心功能區 (更新按鈕)
        btn_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        self.btn_update_ytdlp = ctk.CTkButton(
            btn_frame, 
            text="↻ 更新核心組件 (yt-dlp)", 
            font=("Microsoft JhengHei UI", 13, "bold"), 
            fg_color="#1F6AA5", hover_color="#144870", 
            height=40, width=200, corner_radius=20,
            command=self.check_for_updates 
        )
        self.btn_update_ytdlp.grid(row=0, column=0, padx=10, pady=10)
        
        self.btn_update_app = ctk.CTkButton(
            btn_frame, 
            text="☁ 檢查軟體更新", 
            font=("Microsoft JhengHei UI", 13, "bold"), 
            fg_color="transparent", border_width=2, border_color="#1F6AA5", 
            text_color=("#1F6AA5", "#3B8ED0"), hover_color=("gray90", "gray30"),
            height=40, width=200, corner_radius=20,
            command=lambda: threading.Thread(target=self.check_app_update, daemon=True).start()
        )
        self.btn_update_app.grid(row=0, column=1, padx=10, pady=10)

        # [New] 查看更新日誌按鈕
        self.btn_changelog = ctk.CTkButton(
            btn_frame, 
            text="📃 查看更新日誌", 
            font=("Microsoft JhengHei UI", 13), 
            fg_color="transparent", border_width=1, text_color=("gray40", "gray60"),
            hover_color=("gray90", "gray30"),
            height=32, width=150, corner_radius=16,
            command=self.show_changelog
        )
        self.btn_changelog.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        # (C) 連結區 (小型按鈕)
        link_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        link_frame.pack(pady=(20, 40))
        
        def open_github(event=None): webbrowser.open(f"https://github.com/{GITHUB_REPO}")
        def open_issues(event=None): webbrowser.open(f"https://github.com/{GITHUB_REPO}/issues")

        # GitHub (Icon + Text)
        btn_gh = ctk.CTkButton(link_frame, text="★ Star on GitHub", font=("Consolas", 12), 
                               fg_color="transparent", text_color="gray", hover_color=("gray90", "gray25"),
                               height=30, width=120, command=open_github)
        btn_gh.pack(side="left", padx=5)

        # Issue
        btn_bug = ctk.CTkButton(link_frame, text="🐛 Report Issue", font=("Consolas", 12), 
                                fg_color="transparent", text_color="gray", hover_color=("gray90", "gray25"),
                                height=30, width=120, command=open_issues)
        btn_bug.pack(side="left", padx=5)

        # (D) 版權資訊 (卡片內底部)
        copyright_label = ctk.CTkLabel(
            info_card,
            text="Copyright © 2025 nununuuuu.",
            font=("Microsoft JhengHei UI", 10), text_color="gray60"
        )
        copyright_label.pack(side="bottom", pady=(10, 20))


        # --- 2. 底部版權區 (Footer) ---
        footer_frame = ctk.CTkFrame(self.tab_about, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=20)
        
        try:
             import yt_dlp
             v_text = f"yt-dlp 版本: {yt_dlp.version.__version__}"
        except: 
             v_text = "yt-dlp 版本: Unknown"
        
        ctk.CTkLabel(footer_frame, text=v_text, text_color="gray", font=("Consolas", 10)).pack(pady=(0, 10))

        disclaimer = (
            "免責聲明：本軟體僅供技術研究與個人學習使用，請勿用於商業用途。\n"
            "因使用本項目而產生的任何後果均由使用者個人承擔，與開發者無關，概不負責。"
        )
        ctk.CTkLabel(footer_frame, text=disclaimer, text_color="gray", font=("Microsoft JhengHei UI", 10), justify="center").pack()

    def check_for_updates(self):
        """檢查並自動更新 yt-dlp"""
        self.btn_update_ytdlp.configure(state="disabled", text="檢查中...")
        
        def run_check():
            try:
                import json
                import urllib.request
                
                # 1. 取得 PyPI 最新版本資訊
                url = "https://pypi.org/pypi/yt-dlp/json"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data['info']['version']
                
                current_version = yt_dlp.version.__version__ if yt_dlp else "0.0.0"
                
                def parse_version(v_str):
                    try:
                        return tuple(map(int, v_str.split('.')))
                    except:
                        return (0, 0, 0)

                if parse_version(latest_version) <= parse_version(current_version):
                    self.after(0, lambda: messagebox.showinfo("檢查更新", f"版本已為最新版本 ({current_version})"))
                    self.after(0, lambda: self.btn_update_ytdlp.configure(state="normal", text="↻ 更新核心組件 (yt-dlp)"))
                    return

                # 詢問並執行更新
                def ask_and_update():
                    if messagebox.askyesno("發現新版本", f"現有版本: {current_version}\n最新版本: {latest_version}\n\n是否立即下載並更新？"):
                        self.btn_update_ytdlp.configure(text=f"下載新版本 {latest_version}...")
                        threading.Thread(target=run_download, args=(data,), daemon=True).start()
                    else:
                        self.btn_update_ytdlp.configure(state="normal", text="↻ 更新核心組件 (yt-dlp)")
                
                self.after(0, ask_and_update)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("更新失敗", f"更新錯誤: {str(e)}"))
                self.after(0, lambda: self.btn_update_ytdlp.configure(state="normal", text="↻ 更新核心組件 (yt-dlp)"))

        def run_download(data):
            try:
                import zipfile
                import urllib.request
                from io import BytesIO
                
                download_url = None
                for file_info in data['urls']:
                    if file_info['packagetype'] == 'bdist_wheel':
                        download_url = file_info['url']
                        break
                
                if not download_url:
                    raise Exception("找不到可用的更新檔案 (.whl)")

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
                    for member in zip_ref.namelist():
                        if member.startswith('yt_dlp/'):
                            zip_ref.extract(member, lib_dir)
                
                def on_success():
                    messagebox.showinfo("更新成功", f"yt-dlp 已更新，點擊確定將重啟程式。")
                    import subprocess
                    current_file = sys.executable if getattr(sys, 'frozen', False) else __file__
                    if getattr(sys, 'frozen', False):
                        subprocess.Popen([sys.executable])
                    else:
                        subprocess.Popen([sys.executable, current_file])
                    os._exit(0)

                self.after(0, on_success)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("更新失敗", str(e)))
                self.after(0, lambda: self.btn_update_ytdlp.configure(state="normal", text="↻ 更新核心組件 (yt-dlp)"))

        threading.Thread(target=run_check, daemon=True).start()

