import customtkinter as ctk
from tkinter import filedialog, messagebox
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
        
        # (Icon, TooltipText)
        self.sidebar_items = {
            "Basic": ("⌂", "基本選項"),      
            "Format": ("🎞", "格式/畫質"),
            "Sub": ("🔡", "字幕設定"),
            "Output": ("✂", "時間裁切"),
            "Adv": ("🛠", "進階選項"),
            "Tasks": ("📥", "任務列表"),
            "Log": ("⏱", "系統日誌"),
            "Settings": ("⚙", "設定"),
            "About": ("ⓘ", "關於")
        }
        
        # 上方按鈕
        top_items = ["Basic", "Format", "Sub", "Output", "Adv", "Tasks"]
        for i, key in enumerate(top_items):
            if key not in self.sidebar_items: continue
            self._create_sidebar_item(key, i)

        # 設定 Spacer (彈簧)，將第 10 列設為可伸縮，把後面的按鈕推到底部
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # 下方按鈕 (Log, Settings, About)
        bottom_items = ["Log", "Settings", "About"]
        for i, key in enumerate(bottom_items):
             if key not in self.sidebar_items: continue
             self._create_sidebar_item(key, 11+i)

    def _create_sidebar_item(self, key, row_idx):
        icon, tooltip_text = self.sidebar_items.get(key, ("?", ""))
        
        # 1. Indicator Strip (Left)
        indicator = ctk.CTkFrame(self.sidebar_frame, width=4, height=40, corner_radius=2, fg_color="transparent")
        indicator.grid(row=row_idx, column=0, pady=5, sticky="e") # Right align in col 0 to touch button
        self.nav_indicators[key] = indicator
        
        # 2. Icon Button
        # hover_color="transparent" to avoid the blocky background, or use a very subtle gray if needed
        btn = ctk.CTkButton(self.sidebar_frame, text=icon, anchor="center", 
                            fg_color="transparent", text_color=("gray50", "gray70"), 
                            hover_color=("gray90", "gray25"),
                            font=self.font_sidebar_icon, height=50, corner_radius=10,
                            width=50,
                            command=lambda k=key: self.select_frame(k))
        btn.grid(row=row_idx, column=1, sticky="nsew", pady=2, padx=(5, 10))
        self.nav_btns[key] = btn
        CTkToolTip(btn, tooltip_text)

    def select_frame(self, name):
        # Hide all frames
        for frame in self.frames.values():
            frame.grid_forget()
        
        # Update Sidebar Styling (Indicator Logic)
        for key in self.nav_btns:
            # Reset to inactive state
            self.nav_btns[key].configure(text_color=("gray50", "gray70"))
            if key in self.nav_indicators:
                self.nav_indicators[key].configure(fg_color="transparent")
        
        # Set Active State
        if name in self.nav_btns:
            self.nav_btns[name].configure(text_color="#1F6AA5")
            if name in self.nav_indicators:
                self.nav_indicators[name].configure(fg_color="#1F6AA5")
        
        # Show selected frame
        if name in self.frames:
            self.frames[name].grid(row=0, column=0, sticky="nsew")
            
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

    def setup_basic_ui(self):
        # --- Absolute Vertical Centering Layout ---
        # Grid: Row 0 (Spacer), Row 1 (Content), Row 2 (Spacer)
        self.tab_basic.grid_rowconfigure(0, weight=1)
        self.tab_basic.grid_rowconfigure(1, weight=0) # Content row, no expansion
        self.tab_basic.grid_rowconfigure(2, weight=1)
        self.tab_basic.grid_columnconfigure(0, weight=1)
        
        # Main Container (The Island)
        island_frame = ctk.CTkFrame(self.tab_basic, fg_color="transparent")
        island_frame.grid(row=1, column=0, sticky="n") # Centered content
        
        # --- 1. Search Section ---
        search_section = ctk.CTkFrame(island_frame, fg_color="transparent")
        search_section.pack(pady=(0, 20)) # Removed fill="x" to center the bar naturally
        
        # Input Bar (Pill Shape)
        input_bar = ctk.CTkFrame(search_section, fg_color=("white", "#2d3436"), corner_radius=30, border_width=1, border_color=("#E5E5E5", "gray30"))
        input_bar.pack(ipady=5) # Removed fill="x", it will now hug the content
        
        # Paste Button
        def paste_url():
            try:
                self.entry_url.delete(0, 'end')
                self.entry_url.insert(0, self.clipboard_get())
            except: pass
            
        btn_paste = ctk.CTkButton(input_bar, text="📋", width=45, height=45, fg_color="transparent", hover_color=("gray90", "gray40"), 
                                  text_color=("gray50", "gray80"), font=("Segoe UI Emoji", 20), command=paste_url, corner_radius=22)
        btn_paste.pack(side="left", padx=(10, 0))
        CTkToolTip(btn_paste, "貼上網址")

        # URL Entry
        self.entry_url = ctk.CTkEntry(input_bar, width=420, height=50, font=("Microsoft JhengHei UI", 16), 
                                      placeholder_text="在此貼上 YouTube / Twitch 連結...", 
                                      fg_color="transparent", border_width=0, text_color=("gray20", "white"))
        self.entry_url.pack(side="left", padx=10)
        
        # Analyze Button
        self.btn_analyze = ctk.CTkButton(input_bar, text="分析網址", height=45, width=120, font=("Microsoft JhengHei UI", 15, "bold"), 
                                         fg_color="#1F6AA5", hover_color="#144870", corner_radius=22, command=self.on_fetch_info,
                                         text_color="white")
        self.btn_analyze.pack(side="right", padx=10)
        
        # sub_row for Hints
        sub_row = ctk.CTkFrame(search_section, fg_color="transparent")
        sub_row.pack(fill="x", pady=(15, 0))

        # Restore Logic Variable (Hidden)
        self.var_playlist = ctk.BooleanVar(value=False)

        # Hint text
        hint_text = "提示：若網址為歌單或需要下載字幕請先分析網址，其餘皆可『直接下載』或『加入任務』等待下載"
        # Center the hint since it's the only item
        hint_label = ctk.CTkLabel(sub_row, text=hint_text, font=("Microsoft JhengHei UI", 12), text_color="#1F6AA5")
        hint_label.pack(side="top", anchor="center")


        # --- 2. Settings Section (Compact Attached) ---
        settings_card = ctk.CTkFrame(island_frame, fg_color=("white", "#2d3436"), corner_radius=12, border_width=1, border_color=("#E5E5E5", "gray30"))
        settings_card.pack(fill="x")
        
        # Settings Content
        s_content = ctk.CTkFrame(settings_card, fg_color="transparent")
        s_content.pack(fill="x", padx=25, pady=20)
        s_content.grid_columnconfigure(1, weight=1)
        
        # Header
        ctk.CTkLabel(s_content, text="⚙️ 下載設定", font=("Microsoft JhengHei UI", 14, "bold"), text_color=("gray40", "gray80")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Path
        ctk.CTkLabel(s_content, text="儲存位置", font=("Microsoft JhengHei UI", 13), text_color=("gray40", "gray60")).grid(row=1, column=0, sticky="w", pady=5)
        
        path_box = ctk.CTkFrame(s_content, fg_color="transparent")
        path_box.grid(row=1, column=1, sticky="ew", padx=(15, 0), pady=5)
        
        self.entry_path = ctk.CTkEntry(path_box, height=30, font=("Microsoft JhengHei UI", 13), placeholder_text="預設為當前目錄", 
                                       fg_color=("#F0F0F0", "#3E3E3E"), border_width=0, corner_radius=8) 
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(path_box, text="瀏覽", width=70, height=30, fg_color=("#1F6AA5", "#1F6AA5"), hover_color=("#144870", "#144870"), 
                      text_color="white", font=("Microsoft JhengHei UI", 12), corner_radius=8, command=self.browse_folder).pack(side="left")

        # Filename
        ctk.CTkLabel(s_content, text="檔案名稱", font=("Microsoft JhengHei UI", 13), text_color=("gray40", "gray60")).grid(row=2, column=0, sticky="w", pady=5)
        
        self.entry_filename = ctk.CTkEntry(s_content, height=30, font=("Microsoft JhengHei UI", 13), placeholder_text="預設為影片原標題",
                                           fg_color=("#F0F0F0", "#3E3E3E"), border_width=0, corner_radius=8)
        self.entry_filename.grid(row=2, column=1, sticky="ew", padx=(15, 0), pady=10)
        
        # 初始化顯示
        self.update_queue_ui()

    def on_playlist_toggle(self):
        """歌單模式時禁用不相關選項"""
        state = "disabled" if self.var_playlist.get() else "normal"
        
        # 1. Filename (Playlist uses auto naming)
        if hasattr(self, 'entry_filename'):
            self.entry_filename.configure(state=state)
            if state == "disabled": self.entry_filename.configure(placeholder_text="播放清單模式下將自動命名")
            else: self.entry_filename.configure(placeholder_text="預設為原標題")
        
        # 2. Start Download Button (Single download mostly) - actually Queue handles execution
        
        # 3. Time Cut (Usually not applied to whole playlist)
        if hasattr(self, 'chk_cut'):
             self.chk_cut.configure(state=state)
             if state == "disabled":
                  self.chk_cut.deselect()
                  # We need to manually trigger the toggle effect or call command?
                  # Since toggle_cut is internal function in setup_output_ui, we can't call it directly.
                  # But var_cut is shared. If we deselect, var_cut becomes False.
                  # We can assume UI setup made entry_start/end follow var_cut if we could trigger it.
                  # BUT toggle_cut is bound to command. Deselecting programmatically DOES NOT trigger command in CTk usually.
                  # We should handle entry state here manually.
                  if hasattr(self, 'entry_start'): self.entry_start.configure(state="disabled")
                  if hasattr(self, 'entry_end'): self.entry_end.configure(state="disabled")
        
        # 4. Live Options (Not for playlists)
        if hasattr(self, 'rb_live_now'): self.rb_live_now.configure(state=state)
        if hasattr(self, 'rb_live_start'): self.rb_live_start.configure(state=state)

    def browse_folder(self):
        filename = filedialog.askdirectory()
        if filename:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, filename)

    def update_queue_ui(self):
        """更新等待中(排程)介面"""
        # 清空目前等待區 (但不刪除 lbl_waiting_empty)
        if hasattr(self, 'view_waiting'):
            for widget in self.view_waiting.winfo_children():
                if hasattr(self, 'lbl_waiting_empty') and widget == self.lbl_waiting_empty:
                     continue
                widget.destroy()

        # Reset variables
        self.queue_vars = []

        if not self.download_queue:
            if hasattr(self, 'lbl_waiting_empty'):
                 self.lbl_waiting_empty.pack(pady=20)
            else:
                 ctk.CTkLabel(self.view_waiting, text="目前沒有等待中的任務", text_color="gray", font=self.font_text).pack(pady=20)
        else:
            if hasattr(self, 'lbl_waiting_empty'):
                 self.lbl_waiting_empty.pack_forget()
            ctrl_frame = ctk.CTkFrame(self.view_waiting, fg_color="transparent")
            ctrl_frame.pack(fill="x", padx=5, pady=(0, 10))
            
            self.var_select_all = ctk.BooleanVar(value=False)
            chk_all = ctk.CTkCheckBox(ctrl_frame, text="全選", font=self.font_small, width=60, 
                                      variable=self.var_select_all, command=self.toggle_select_all)
            chk_all.pack(side="left", padx=5)
            
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

    def setup_format_ui(self):
        # 使用 pack 對齊，避免 grid 造成的混亂
        self.tab_format.pack_propagate(False) 
        
        main_scroll = ctk.CTkFrame(self.tab_format, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Common Styles
        title_font = ("Microsoft JhengHei UI", 16, "bold")
        sub_font = ("Microsoft JhengHei UI", 14)
        opt_style = {
            "height": 40, "corner_radius": 8,
            "fg_color": "#3E3E3E", 
            "button_color": "#505050", "button_hover_color": "#606060",
            "dropdown_fg_color": "#F0F0F0", "dropdown_hover_color": "#CCCCCC", "dropdown_text_color": "#000000",
            "font": self.font_text, "dropdown_font": self.font_text, "text_color": "#FFFFFF"
        }

        # --- 1. 主要格式選擇 (Primary Format) ---
        fmt_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        fmt_frame.pack(fill="x", pady=(0, 30))
        
        ctk.CTkLabel(fmt_frame, text="選擇輸出格式 (Output Format)", font=title_font, text_color=("gray20", "gray90")).pack(anchor="w", pady=(0, 10))
        
        self.format_options = ["mp4 (影片+音訊)", "mkv (影片+音訊)", "webm (影片+音訊)", "mp3 (純音訊)", "m4a (純音訊)", "flac (無損音訊)", "wav (無損音訊)"]
        self.combo_format = ctk.CTkOptionMenu(fmt_frame, values=self.format_options, command=self.on_format_change, **opt_style)
        self.combo_format.set("mp4 (影片+音訊)")
        self.combo_format.pack(fill="x")

        # --- 2. 詳細品質設定 (Quality Details) ---
        detail_container = ctk.CTkFrame(main_scroll, fg_color=("gray90", "gray16"), corner_radius=12)
        detail_container.pack(fill="x", pady=(0, 30))
        
        # 內部 Grid 配置 (左右分欄)
        detail_container.grid_columnconfigure(1, weight=1)
        
        # Row 1: Video Resolution
        ctk.CTkLabel(detail_container, text="影片畫質", font=sub_font, text_color="gray").grid(row=0, column=0, padx=30, pady=(25, 15), sticky="w")
        
        v_res_box = ctk.CTkFrame(detail_container, fg_color="transparent")
        v_res_box.grid(row=0, column=1, padx=30, pady=(25, 15), sticky="ew")
        
        self.combo_video_res = ctk.CTkOptionMenu(v_res_box, values=["Best (最高畫質)", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"], width=180, **opt_style)
        self.combo_video_res.pack(side="left", fill="x", expand=True)

        self.var_video_legacy = ctk.BooleanVar(value=False)
        self.chk_legacy = ctk.CTkCheckBox(v_res_box, text="H.264 (相容模式)", font=self.font_small, variable=self.var_video_legacy, command=self.update_dynamic_hint)
        self.chk_legacy.pack(side="right", padx=(10, 0))
        CTkToolTip(self.chk_legacy, "勾選後，將強制優先下載 H.264 編碼的影片(最高1080p)。\n適合舊電腦或需要在 Windows 內建播放器直接播放的情況。")

        # Row 2: Audio Quality
        ctk.CTkLabel(detail_container, text="音訊品質", font=sub_font, text_color="gray").grid(row=1, column=0, padx=30, pady=15, sticky="w")
        self.combo_audio_quality = ctk.CTkOptionMenu(detail_container, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps (標準)(yt最佳)", "96 kbps (較低)", "64 kbps (省空間)"], command=lambda _: self.update_dynamic_hint(), **opt_style)
        self.combo_audio_quality.grid(row=1, column=1, padx=30, pady=15, sticky="ew")

        # Row 3: Audio Codec
        ctk.CTkLabel(detail_container, text="音訊編碼", font=sub_font, text_color="gray").grid(row=2, column=0, padx=30, pady=(15, 25), sticky="w")
        self.combo_audio_codec = ctk.CTkOptionMenu(detail_container, values=["Auto (預設/Opus)", "AAC (車用/相容性高)"], command=lambda _: self.update_dynamic_hint(), **opt_style)
        self.combo_audio_codec.grid(row=2, column=1, padx=30, pady=(15, 25), sticky="ew")

        # Hint Label
        self.lbl_format_hint = ctk.CTkLabel(main_scroll, text="提示：若車用音響無聲音，請在「音訊編碼」選擇 AAC", font=("Microsoft JhengHei UI", 12), text_color="#1F6AA5")
        self.lbl_format_hint.pack(pady=(0, 20))

        # --- 3. 後期處理 (Post-Processing) ---
        ctk.CTkLabel(main_scroll, text="後期處理選項", font=sub_font, text_color="gray").pack(anchor="w", pady=(10, 5))
        
        pp_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        pp_frame.pack(fill="x", pady=(0, 20))
        
        self.var_embed_thumb = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(pp_frame, text="嵌入縮圖", variable=self.var_embed_thumb, font=self.font_text, corner_radius=20).pack(side="left", padx=(0, 20))
        
        self.var_embed_subs = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(pp_frame, text="嵌入字幕 (mkv/mp4)", variable=self.var_embed_subs, font=self.font_text, corner_radius=20).pack(side="left", padx=20)
        
        self.var_metadata = ctk.BooleanVar(value=False)
        chk_meta = ctk.CTkCheckBox(pp_frame, text="寫入中繼資料", variable=self.var_metadata, font=self.font_text, corner_radius=20)
        chk_meta.pack(side="left", padx=20)
        CTkToolTip(chk_meta, "將影片資訊 (如標題、作者、日期、章節等) 寫入檔案中。\n部分播放器可顯示章節與詳細資訊。")

        self.on_format_change(None)

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
                hint = "提示：相容模式已開啟 (H.264 + AAC)，確保所有裝置皆可播放"
            elif self.combo_audio_codec.get().startswith("AAC"):
                hint = "提示：將優先使用 AAC 音訊編碼 (提升車用與舊裝置相容性)"
            else:
                hint = f"提示：將下載 {choice.split(' ')[0]} 格式 (自動最佳品質)"
        
        qual = self.combo_audio_quality.get()
        if "Best" not in qual and "無損" not in choice:
             hint += "\n(注意：在無更高品質時，強制設定位元率只會增加檔案大小無法提升原始音質)"

        self.lbl_format_hint.configure(text=hint)

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
        # 1. Hint Label
        self.lbl_sub_hint = ctk.CTkLabel(self.tab_sub, text="請先在［基本選項］點擊「分析網址」以載入字幕列表", font=("Microsoft JhengHei UI", 12), text_color="gray")
        self.lbl_sub_hint.pack(pady=(15, 5))
        
        # 2. Scrollable List for Analysis Results
        self.scroll_subs = ctk.CTkScrollableFrame(self.tab_sub, label_text=None, fg_color=("gray95", "gray16"))
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=10)
        self.sub_checkboxes = {}

        # 3. Manual Settings (Clean Layout)
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
        
        CTkToolTip(manual_frame, "當下載「播放清單」或未執行分析時，將嘗試下載此處勾選的語言。\n(若該影片有此語言則下載，沒有則跳過)")
        
        # Manual Entry Row
        manual_bg = ctk.CTkFrame(manual_frame, fg_color="transparent")
        manual_bg.pack(anchor="w", pady=(15, 0))
        
        self.var_sub_manual = ctk.BooleanVar()
        def toggle_manual_entry():
            self.entry_sub_manual.configure(state="normal" if self.var_sub_manual.get() else "disabled")
            
        ctk.CTkCheckBox(manual_bg, text="其他", variable=self.var_sub_manual, command=toggle_manual_entry, font=self.font_text).pack(side="left", padx=(10, 2))
        
        self.entry_sub_manual = ctk.CTkEntry(manual_bg, width=120, placeholder_text="代碼 (如: th, vi)", state="disabled")
        self.entry_sub_manual.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(manual_bg, text="用逗號或空白分隔", text_color="#1F6AA5", font=self.font_small).pack(side="left", padx=5)
        
        ctk.CTkButton(manual_bg, text="查詢代碼表", width=80, height=24, fg_color="#555555", font=("Microsoft JhengHei UI", 12), command=self.open_lang_table).pack(side="left", padx=10)

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

    def update_subtitle_list_ui(self, info_dict):
        """根據 ytdlp 資訊，動態更新字幕列表 Checkbox"""
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
        def toggle_cut():
             state = "normal" if self.var_cut.get() else "disabled"
             self.entry_start.configure(state=state)
             self.entry_end.configure(state=state)
             self.lbl_start.configure(text_color="#1F6AA5" if self.var_cut.get() else "gray")
             self.lbl_end.configure(text_color="#1F6AA5" if self.var_cut.get() else "gray")
             
        self.chk_cut = ctk.CTkCheckBox(cut_card, text="啟用時間裁切 (下載部分片段)", font=("Microsoft JhengHei UI", 14, "bold"), variable=self.var_cut, command=toggle_cut)
        self.chk_cut.pack(anchor="w", pady=(5, 15))
        CTkToolTip(self.chk_cut, "僅下載影片的指定時間範圍，格式為 HH:MM:SS，例如 00:01:30")
        
        # Time Inputs
        time_frame = ctk.CTkFrame(cut_card, fg_color="transparent")
        time_frame.pack(fill="x", padx=20)
        
        self.lbl_start = ctk.CTkLabel(time_frame, text="開始時間 (Start):", font=self.font_text, text_color="gray")
        self.lbl_start.pack(side="left")
        
        self.entry_start = ctk.CTkEntry(time_frame, width=100, state="disabled", placeholder_text="00:00:00", height=35)
        self.entry_start.pack(side="left", padx=10)
        
        self.lbl_end = ctk.CTkLabel(time_frame, text="結束時間 (End):", font=self.font_text, text_color="gray")
        self.lbl_end.pack(side="left", padx=(20, 0))
        
        self.entry_end = ctk.CTkEntry(time_frame, width=100, state="disabled", placeholder_text="00:05:00", height=35)
        self.entry_end.pack(side="left", padx=10)

        # --- 2. 直播模式 (Live) --- 
        live_card = create_section_card(scroll_container, "直播錄製模式 (Live Stream)", icon="🔴")
        
        self.var_live_mode = ctk.StringVar(value="now")
        
        bg_live = ctk.CTkFrame(live_card, fg_color="transparent")
        bg_live.pack(fill="x", pady=5)
        
        self.rb_live_now = ctk.CTkRadioButton(bg_live, text="從現在開始錄製 (Live Now)", variable=self.var_live_mode, value="now", font=self.font_text, fg_color="#E74C3C", hover_color="#C0392B")
        self.rb_live_now.pack(anchor="w", pady=8)
        
        self.rb_live_start = ctk.CTkRadioButton(bg_live, text="從開頭追溯 (Live From Start)", variable=self.var_live_mode, value="start", font=self.font_text, fg_color="#E74C3C", hover_color="#C0392B")
        self.rb_live_start.pack(anchor="w", pady=8)
        CTkToolTip(self.rb_live_start, "嘗試下載直播緩衝區，從直播開始處抓取。\n(注意：部分直播可能不支援，取決於 YouTube 緩衝)")

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
            ctk.CTkLabel(header, text=title, font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
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
        ctk.CTkLabel(b_header, text="從瀏覽器讀取 (推薦)", font=("Microsoft JhengHei UI", 14, "bold"), text_color="#1F6AA5").pack(side="left")
        
        lbl_b_help = ctk.CTkLabel(b_header, text="❓", cursor="hand2", font=self.font_small)
        lbl_b_help.pack(side="left", padx=5)
        CTkToolTip(lbl_b_help, "【說明】\n程式會自動讀取您選擇的瀏覽器中 YouTube 的登入狀態。\n無需手動匯出檔案，設定與更新最方便。\n若無法使用，建議使用下方cookies.txt方式。\n注意：執行下載時建議先將該瀏覽器「完全關閉」，以免讀取失敗。")
        
        # Browser Grid
        browser_grid = ctk.CTkFrame(cookie_card, fg_color="transparent")
        browser_grid.pack(fill="x", pady=5)
        
        browsers = [
            ("不使用 (None)", "none"), ("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox"),
            ("Opera", "opera"), ("Brave", "brave"), ("Vivaldi", "vivaldi"), ("Chromium", "chromium")
        ]
        
        for i, (text, val) in enumerate(browsers):
            rb = ctk.CTkRadioButton(
                browser_grid, text=text, variable=self.var_cookie_mode, value=val,
                font=self.font_text, command=self.on_cookie_mode_change,
                fg_color="#1F6AA5", hover_color="#144870"
            )
            rb.grid(row=i//4, column=i%4, padx=10, pady=8, sticky="w")
            
        CTkToolTip(browser_grid, "自動讀取瀏覽器登入狀態 (例如 YouTube Premium 會員)。\n執行前建議完全關閉瀏覽器以避免讀取鎖定。")

        # Sub-section: File
        ctk.CTkFrame(cookie_card, height=2, fg_color=("gray85", "gray30")).pack(fill="x", pady=20) # Divider
        
        f_header = ctk.CTkFrame(cookie_card, fg_color="transparent")
        f_header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_header, text="使用 cookies.txt 檔案", font=("Microsoft JhengHei UI", 14, "bold"), text_color="#1F6AA5").pack(side="left")
        
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

        # File Input Area
        f_input_box = ctk.CTkFrame(cookie_card, fg_color="transparent")
        f_input_box.pack(fill="x", padx=10)
        
        ctk.CTkRadioButton(f_input_box, text="檔案路徑:", variable=self.var_cookie_mode, value="file", 
                           font=self.font_text, command=self.on_cookie_mode_change, fg_color="#1F6AA5").pack(side="left", padx=(0, 10))
        
        self.entry_cookie_path = ctk.CTkEntry(f_input_box, placeholder_text="請選擇 cookies.txt...", state="disabled", height=35)
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_cookie_browse = ctk.CTkButton(f_input_box, text="瀏覽", width=80, height=35, state="disabled", fg_color="#555555", command=self.browse_cookie_file)
        self.btn_cookie_browse.pack(side="left")

        # --- 2. 效能設定 (Performance) ---
        perf_card = create_section_card(scroll_container, "效能設定 (Performance)", icon="🚀")
        
        ctk.CTkLabel(perf_card, text="最大同時下載數 (Concurrent Downloads)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        
        perf_box = ctk.CTkFrame(perf_card, fg_color="transparent")
        perf_box.pack(fill="x", pady=5)
        
        concurrent_values = [str(i) for i in range(1, 11)]
        self.combo_concurrent = ctk.CTkOptionMenu(perf_box, values=concurrent_values, width=120, height=35, command=self.update_concurrent_label, fg_color="#3E3E3E", button_color="#505050")
        self.combo_concurrent.pack(side="left")
        self.combo_concurrent.set("1")
        
        ctk.CTkLabel(perf_box, text="(建議值: 1~3，過多可能導致被 YouTube 暫時封鎖)", text_color="gray", font=self.font_small).pack(side="left", padx=15)

        # --- 3. 網路設定 (Network) ---
        net_card = create_section_card(scroll_container, "網路連接設定 (Network)", icon="🌐")
        
        # UA
        ctk.CTkLabel(net_card, text="User Agent (偽裝瀏覽器字串)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.entry_ua = ctk.CTkEntry(net_card, height=35, placeholder_text="預設 (自動隨機)", border_color=("gray70", "gray40"))
        self.entry_ua.pack(fill="x", pady=5)
        CTkToolTip(self.entry_ua, "若遇網站阻擋，可填入特定瀏覽器的 UA 字串。留空則使用程式內建預設值。")
        
        # Proxy
        ctk.CTkLabel(net_card, text="Proxy 代理伺服器", font=self.font_title, text_color="gray").pack(anchor="w", pady=(15, 5))
        self.entry_proxy = ctk.CTkEntry(net_card, height=35, placeholder_text="http://user:pass@host:port", border_color=("gray70", "gray40"))
        self.entry_proxy.pack(fill="x", pady=5)
        CTkToolTip(self.entry_proxy, "若需翻牆或隱藏 IP，請輸入 Proxy (支援 http/https/socks5)。")
        
    def on_cookie_mode_change(self):
        if self.var_cookie_mode.get() == "file":
            self.entry_cookie_path.configure(state="normal")
            self.btn_cookie_browse.configure(state="normal", fg_color="#1F6AA5")
        else:
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color="#555555")

    def update_concurrent_label(self, value):
        self.max_concurrent_downloads = int(value)
            
    def browse_cookie_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if p:
            self.entry_cookie_path.delete(0, "end")
            self.entry_cookie_path.insert(0, p)



    def setup_log_ui(self):
        self.txt_log = ctk.CTkTextbox(self.tab_log, font=("Consolas", 12))
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=10)
        
        btn_clear = ctk.CTkButton(self.tab_log, text="清空日誌", font=self.font_btn, height=35, fg_color="#555555", hover_color="#333333", command=self.clear_log)
        btn_clear.pack(pady=(0, 10))

    def clear_log(self):
        self.txt_log.delete("1.0", "end")
        
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}\n"
        try:
            self.txt_log.insert("end", full_msg)
            self.txt_log.see("end")
        except: pass
        print(full_msg.strip())

    def setup_settings_ui(self):
        """設定分頁介面 (修改 constants.py)"""
        # 1. 外層容器 (負責置中)
        settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        settings_frame.pack(fill="both", expand=True)
        
        # 2. 中央內容區塊
        center_box = ctk.CTkFrame(settings_frame, fg_color=("gray95", "gray20"), corner_radius=20) # 修正顏色以配合 About 頁面
        center_box.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.7)
        
        # 標題
        ctk.CTkLabel(center_box, text="外觀主題 (Appearance)", font=("Microsoft JhengHei UI", 18, "bold"), text_color=("gray20", "gray80")).pack(pady=(40, 30), padx=50)
        
        # --- 卡片式選單 (Grid Layout) ---
        self.theme_grid = ctk.CTkFrame(center_box, fg_color="transparent")
        self.theme_grid.pack(pady=(0, 30), padx=40, fill="x")
        
        self.theme_grid.grid_columnconfigure(0, weight=1)
        self.theme_grid.grid_columnconfigure(1, weight=1)
        self.theme_grid.grid_columnconfigure(2, weight=1)
        
        # Mapping: Display -> Value
        self.theme_value_map = {
            "System": "System",
            "Light": "Light",
            "Dark": "Dark"
        }
        
        # UI Definition: Key -> (Icon, Label)
        self.theme_ui_data = {
            "System": ("🖥️", "系統預設"),
            "Light": ("☀️", "淺色模式"),
            "Dark": ("🌙", "深色模式")
        }
        
        self.current_theme_selection = DEFAULT_APPEARANCE_MODE
        self.theme_cards = {}

        def set_theme_selection(mode_key):
            self.current_theme_selection = mode_key
            update_card_visuals()

        def on_enter(card_key):
            if card_key != self.current_theme_selection:
                self.theme_cards[card_key]["frame"].configure(fg_color=("#E0E0E0", "#2B2B2B"))

        def on_leave(card_key):
            if card_key != self.current_theme_selection:
                self.theme_cards[card_key]["frame"].configure(fg_color="transparent")

        def update_card_visuals():
            for key, items in self.theme_cards.items():
                frame = items["frame"]
                icon_lbl = items["icon"]
                text_lbl = items["text"]
                
                if key == self.current_theme_selection:
                    frame.configure(
                        fg_color=("#D0E0F0", "#252526"), 
                        border_color="#1F6AA5",           
                        border_width=2
                    )
                    icon_lbl.configure(text_color="#1F6AA5")
                    text_lbl.configure(text_color="#1F6AA5")
                else:
                    frame.configure(
                        fg_color="transparent",
                        border_color=("gray70", "gray40"),
                        border_width=1
                    )
                    icon_lbl.configure(text_color=("gray20", "gray80"))
                    text_lbl.configure(text_color=("gray20", "gray80"))

        # Create Card Frames
        keys = ["System", "Light", "Dark"]
        for i, key in enumerate(keys):
            icon_char, label_text = self.theme_ui_data[key]
            
            card = ctk.CTkFrame(
                self.theme_grid, 
                height=140, 
                corner_radius=15,
                fg_color="transparent",
                border_width=1,
                border_color="gray50",
                cursor="hand2"
            )
            card.grid(row=0, column=i, padx=10, sticky="ew")
            
            lbl_icon = ctk.CTkLabel(card, text=icon_char, font=("Segoe UI Emoji", 22), text_color="gray")
            lbl_icon.place(relx=0.5, rely=0.4, anchor="center")
            
            lbl_text = ctk.CTkLabel(card, text=label_text, font=("Microsoft JhengHei UI", 15, "bold"), text_color="gray")
            lbl_text.place(relx=0.5, rely=0.75, anchor="center")
            
            for widget in [card, lbl_icon, lbl_text]:
                widget.bind("<Button-1>", lambda e, k=key: set_theme_selection(k))
                widget.bind("<Enter>", lambda e, k=key: on_enter(k))
                widget.bind("<Leave>", lambda e, k=key: on_leave(k))
            
            self.theme_cards[key] = {
                "frame": card,
                "icon": lbl_icon,
                "text": lbl_text
            }
            
        update_card_visuals() 

        # --- 底部操作區 ---
        
        # 警示文字 (移至按鈕上方，縮小並柔和化)
        warn_box = ctk.CTkFrame(center_box, fg_color="transparent")
        warn_box.pack(pady=(0, 10))
        ctk.CTkLabel(warn_box, text="⚠️ 設定更改將於應用程式重啟後生效", text_color="#E67E22", font=("Microsoft JhengHei UI", 12)).pack()

        def on_apply_click():
            value = self.current_theme_selection
            if value and value != DEFAULT_APPEARANCE_MODE:
                apply_theme_logic(value)
            else:
                 self.show_toast("設定未變更")

        self.btn_apply = ctk.CTkButton(center_box, text="套用並重啟", 
                                       font=("Microsoft JhengHei UI", 14, "bold"),
                                       height=45,
                                       corner_radius=12,
                                       fg_color="#1F6AA5", hover_color="#144870",
                                       command=on_apply_click)
        self.btn_apply.pack(pady=(0, 40), padx=50, fill="x")

        def apply_theme_logic(selected_mode):
            try:
                # 1. 讀取 constants.py
                import constants
                target_file = constants.__file__
                
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 2. Regex 替換 (確保安全)
                new_line = f'DEFAULT_APPEARANCE_MODE = "{selected_mode}"'
                # 尋找 DEFAULT_APPEARANCE_MODE = "..." 或 '...'
                if re.search(r'DEFAULT_APPEARANCE_MODE\s*=\s*["\'].*?["\']', content):
                    new_content = re.sub(r'DEFAULT_APPEARANCE_MODE\s*=\s*["\'].*?["\']', new_line, content, count=1)
                    
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(new_content)
                                        
                    # 3. 重啟
                    self.after(1000, lambda: self.restart_app())
                else:
                    self.show_toast("寫入設定失敗", color="red")
                    
            except Exception as e:
                self.show_toast(f"設定失敗: {e}", color="red")
                print(e)

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
            "程式碼寫得很爛，但至少能動 ",
            "如果不 work，請嘗試重新開機 ",
            "由 10% 的技術和 90% 的咖啡驅動 ☕",
            "這不是卡住，是在思考人生 ",
            "不要問我為什麼，它就是能跑 🏃",
            "警告：可能包含少量人工智慧 (和大量人工智障) ",
            "如果run不了，至少還能walk",
            "只要 Code 能跑，Bug 就是種裝飾",
            "程式碼與我，只有一個能動",
            "只要心態不崩，程式就不算崩",
            "明明不是猴子卻一直在抓 Bug",
            "昨天解決一個 Bug，現在我有八個 Bug",
            "過程全是 Bug，至少還能 Run",
            "點擊這裡並沒有彩蛋 (真的沒有) 🥚"
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
        self.btn_update_app.grid(row=1, column=0, padx=10, pady=10)

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
            "Copyright © 2025 nununuuuu. Powered by yt-dlp & CustomTkinter."
        )
        ctk.CTkLabel(footer_frame, text=disclaimer, text_color="gray", font=("Microsoft JhengHei UI", 10), justify="center").pack()

