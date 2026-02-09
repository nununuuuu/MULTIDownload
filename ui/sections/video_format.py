import customtkinter as ctk
from ui.tooltip import CTkToolTip

class VideoFormatMixin:
    """
    負責格式設定 (Format Tab) 的 UI 建構與互動邏輯
    包括：影片/音訊格式選擇、SponsorBlock 設定、後處理選項
    """
    def setup_format_ui(self):
        # 初始化變數
        if not hasattr(self, 'var_download_mode'): self.var_download_mode = ctk.StringVar(value="video")
        if not hasattr(self, 'var_video_res'): self.var_video_res = ctk.StringVar(value="Best (最高畫質)")
        if not hasattr(self, 'var_video_codec_select'): self.var_video_codec_select = ctk.StringVar(value="Auto (預設)")
        if not hasattr(self, 'var_audio_qual'): self.var_audio_qual = ctk.StringVar(value="Best (來源預設)")
        if not hasattr(self, 'var_audio_codec'): self.var_audio_codec = ctk.StringVar(value="Auto (預設)")
        if not hasattr(self, 'var_video_format'): self.var_video_format = ctk.StringVar(value="mp4")
        if not hasattr(self, 'var_audio_format'): self.var_audio_format = ctk.StringVar(value="mp3")
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
        for widget in self.tab_format.winfo_children():
            widget.destroy()

        self.tab_format.pack_propagate(False)
        
        # 建立主捲動容器
        scroll_container = ctk.CTkScrollableFrame(self.tab_format, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ========== 模式選擇器 (Mode Selector) ==========
        mode_frame = ctk.CTkFrame(scroll_container, fg_color=("gray95", "#454545"), corner_radius=15)
        mode_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        mode_inner = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_inner.pack(fill="x", pady=20, padx=20)
        mode_inner.grid_columnconfigure(0, weight=1)  # 左側空白
        mode_inner.grid_columnconfigure(1, weight=0)  # 中間內容
        mode_inner.grid_columnconfigure(2, weight=1)  # 右側空白
        
        # 中間區域 (標籤 + 按鈕)
        center_frame = ctk.CTkFrame(mode_inner, fg_color="transparent")
        center_frame.grid(row=0, column=1)
        
        ctk.CTkLabel(center_frame, text="下載模式", font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).pack(side="left", padx=(0, 20))
        
        mode_btn_frame = ctk.CTkFrame(center_frame, fg_color=("gray90", "#1C1C1C"), corner_radius=10)
        mode_btn_frame.pack(side="left")
        
        self.mode_btns = {}
        
        def on_mode_change(mode):
            self.var_download_mode.set(mode)
            # 更新按鈕樣式
            for m, btn in self.mode_btns.items():
                if m == mode:
                    btn.configure(fg_color=("white", "#5A5A5A"), text_color=("#1F6AA5", "#88C0D0"), border_color=("#1F6AA5", "#88C0D0"), border_width=1)
                else:
                    btn.configure(fg_color="transparent", text_color=("gray10", "gray70"), border_width=0)
            # 切換顯示的設定區塊 (only if frames exist)
            if hasattr(self, 'post_frame'):
                self._toggle_format_mode(mode)
        
        for i, (mode_val, mode_label) in enumerate([("video", "影片模式"), ("audio", "音訊模式")]):
            btn = ctk.CTkButton(
                mode_btn_frame,
                text=mode_label,
                font=(self.font_family, 14, "bold"),
                width=140, height=36,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray70"),  # 確保未選中狀態也可見
                hover_color=("white", "#404040"),
                command=lambda m=mode_val: on_mode_change(m)
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
            self.mode_btns[mode_val] = btn
        
        # 初始化按鈕樣式 (只更新樣式，不切換模式)
        self.mode_btns["video"].configure(fg_color=("white", "#5A5A5A"), text_color=("#1F6AA5", "#88C0D0"), border_color=("#1F6AA5", "#88C0D0"), border_width=1)
        
        # 相容性最佳開關
        self.var_compat_mode = ctk.BooleanVar(value=False)
        
        def on_compat_toggle():
            if self.var_compat_mode.get():
                # 開啟相容性模式
                mode = self.var_download_mode.get()
                if mode == "video":
                    # 影片模式：H.264 + AAC
                    self.var_video_codec_select.set("H.264 - 舊裝置/車機")
                    self.combo_video_codec_select.configure(state="disabled")
                    self.combo_audio_codec.set("AAC/m4a - 車機/蘋果")
                    self.combo_audio_codec.configure(state="disabled")
                else:
                    # 音訊模式：MP3
                    self.var_audio_format.set("MP3 - 萬用格式")
                    self.combo_audio_format.configure(state="disabled")
            else:
                # 關閉相容性模式
                mode = self.var_download_mode.get()
                if mode == "video":
                    self.combo_video_codec_select.configure(state="normal")
                    self.combo_audio_codec.configure(state="normal")
                    self.var_video_codec_select.set("Auto (預設)")
                else:
                    self.combo_audio_format.configure(state="normal")
            self.update_dynamic_hint()
        
        self.sw_compat_mode = ctk.CTkSwitch(
            mode_inner, 
            text="相容性最佳", 
            variable=self.var_compat_mode,
            font=(self.font_family, 13),
            progress_color="#2CC985",
            button_hover_color="#20A068",
            command=on_compat_toggle
        )
        self.sw_compat_mode.grid(row=0, column=2, sticky="e")
        CTkToolTip(self.sw_compat_mode, "開啟後確保所有裝置都能播放\n影片模式：H.264 + AAC\n音訊模式：MP3")

        # ========== 影片模式設定區 ==========
        self.video_settings_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        self.video_settings_frame.pack(fill="x", padx=0, pady=0)
        
        # 使用 grid 布局讓兩個卡片並排
        self.video_settings_frame.grid_columnconfigure(0, weight=1, uniform="vcols")
        self.video_settings_frame.grid_columnconfigure(1, weight=1, uniform="vcols")
        
        # Helper: Create Card
        def create_card(parent, title, icon, row, col, columnspan=1, use_grid=True):
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "#454545"), corner_radius=15)
            if use_grid:
                frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10, columnspan=columnspan)
            else:
                frame.pack(fill="x", padx=10, pady=10)
            
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            header.grid_columnconfigure(1, weight=1)
            
            # 使用 grid 確保垂直對齊，並用 pady 微調 icon 位置
            icon_lbl = ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 16))
            icon_lbl.grid(row=0, column=0, padx=(0, 8), pady=(0, 5), sticky="w")
            title_lbl = ctk.CTkLabel(header, text=title, font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90"))
            title_lbl.grid(row=0, column=1, sticky="w")
            
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            return content

        # --- Video Card 1: 影片設定 ---
        video_content = create_card(self.video_settings_frame, "影片設定 (Video)", "🎬", row=0, col=0)
        
        ctk.CTkLabel(video_content, text="輸出容器 (Container)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_video_container = ctk.CTkOptionMenu(video_content, values=["mp4", "mkv", "webm"], 
                                              variable=self.var_video_format, width=200, **opt_style)
        self.combo_video_container.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(video_content, text="影片畫質 (Resolution)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_video_res = ctk.CTkOptionMenu(video_content, values=["Best (最高畫質)", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"], 
                                                 variable=self.var_video_res, width=200, **opt_style)
        self.combo_video_res.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(video_content, text="視訊編碼 (Video Codec)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_video_codec_select = ctk.CTkOptionMenu(video_content, values=[
            "Auto (預設)", 
            "H.264 - 舊裝置/車機", 
            "H.265 - 省空間/蘋果", 
            "VP9 - Android/舊電腦4K", 
            "AV1 - 極致畫質"
        ], variable=self.var_video_codec_select, width=200, command=self.update_dynamic_hint, **opt_style)
        self.combo_video_codec_select.pack(fill="x", pady=(0, 15))
        CTkToolTip(self.combo_video_codec_select, "Auto: 下載原生最佳畫質。\nH.264: 限 1080p，車機/舊電視最穩。\nH.265: 轉檔後檔案極小。\nVP9: 舊電腦看 4K。\nAV1: 極致畫質但吃效能。")

        # --- Video Card 2: 音訊設定 ---
        audio_content = create_card(self.video_settings_frame, "音訊設定 (Audio)", "🎵", row=0, col=1)
        
        ctk.CTkLabel(audio_content, text="音訊音質 (Bitrate)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_quality = ctk.CTkOptionMenu(audio_content, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps", "64 kbps"], 
                                                     variable=self.var_audio_qual, command=lambda _: self.update_dynamic_hint(), width=200, **opt_style)
        self.combo_audio_quality.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(audio_content, text="音訊編碼 (Codec)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_codec = ctk.CTkOptionMenu(audio_content, values=["Auto (預設)", "Opus - 音質優先", "AAC/m4a - 車機/蘋果", "MP3 - 萬用格式", "FLAC - 無損", "WAV - 無損原始"], 
                                                   variable=self.var_audio_codec, command=lambda _: self.update_dynamic_hint(), width=200, **opt_style)
        self.combo_audio_codec.pack(fill="x", pady=(0, 15))
        
        self.lbl_format_hint = ctk.CTkLabel(audio_content, text="提示：若車用音響無聲音，請選擇 AAC 或 MP3", font=(self.font_family, 12), text_color=("#1F6AA5", "#88C0D0"), wraplength=250)
        self.lbl_format_hint.pack(pady=(10, 0))

        # ========== 音訊模式設定區 ==========
        self.audio_settings_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        # 預設隱藏
        
        audio_only_content = create_card(self.audio_settings_frame, "純音訊設定 (Audio Only)", "🎵", row=0, col=0, use_grid=False)
        
        ctk.CTkLabel(audio_only_content, text="輸出格式 (Format)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_format = ctk.CTkOptionMenu(audio_only_content, values=["MP3 - 萬用格式", "AAC/m4a - 車機/蘋果", "FLAC - 無損", "WAV - 無損原始"], 
                                              variable=self.var_audio_format, width=200, **opt_style)
        self.combo_audio_format.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(audio_only_content, text="音質 (Bitrate)", font=self.font_title, text_color="gray").pack(anchor="w", pady=(5, 5))
        self.combo_audio_only_quality = ctk.CTkOptionMenu(audio_only_content, values=["Best (來源預設)", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps", "64 kbps"], 
                                                     variable=self.var_audio_qual, width=200, **opt_style)
        self.combo_audio_only_quality.pack(fill="x", pady=(0, 15))
        
        self.lbl_audio_hint = ctk.CTkLabel(audio_only_content, text="提示：純音訊模式將只下載音軌，不含影像。", font=(self.font_family, 12), text_color=("#1F6AA5", "#88C0D0"), wraplength=350)
        self.lbl_audio_hint.pack(pady=(10, 0))

        # ========== 後處理選項 (共用) ==========
        self.post_frame = ctk.CTkFrame(scroll_container, fg_color=("gray95", "#454545"), corner_radius=15)
        self.post_frame.pack(fill="x", padx=10, pady=10)
        
        post_header = ctk.CTkFrame(self.post_frame, fg_color="transparent")
        post_header.pack(fill="x", padx=20, pady=(15, 10))
        post_header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(post_header, text="🔧", font=("Segoe UI Emoji", 16)).grid(row=0, column=0, padx=(0, 8), pady=(0, 5), sticky="w")
        ctk.CTkLabel(post_header, text="下載與後處理選項 (Post-Processing)", font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).grid(row=0, column=1, sticky="w")
        
        post_content = ctk.CTkFrame(self.post_frame, fg_color="transparent")
        post_content.pack(fill="x", padx=20, pady=(0, 20))
        post_content.grid_columnconfigure(0, weight=1)
        post_content.grid_columnconfigure(1, weight=1)
        
        def create_switch(parent, text, var, r, c, tooltip=None):
            sw = ctk.CTkSwitch(parent, text=text, variable=var, font=(self.font_family, 13), 
                               progress_color="#2CC985", button_hover_color="#20A068")
            sw.grid(row=r, column=c, sticky="w", padx=20, pady=12)
            if tooltip: CTkToolTip(sw, tooltip)
            return sw

        self.sw_embed_thumb = create_switch(post_content, "內嵌影片縮圖 (Thumbnail)", self.var_embed_thumb, 0, 0, "將封面圖寫入檔案中")
        self.sw_embed_subs = create_switch(post_content, "內嵌字幕檔案 (Embed Subs)", self.var_embed_subs, 0, 1, "將字幕封裝進影片 (Softsubs)")
        create_switch(post_content, "寫入中繼資料 (Metadata)", self.var_metadata, 1, 0, "寫入標題、作者、日期等資訊")

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
            
            x = self.winfo_x() + (self.winfo_width() // 2) - 200
            y = self.winfo_y() + (self.winfo_height() // 2) - 300
            top.geometry(f"+{x}+{y}")
            
            ctk.CTkLabel(top, text="請勾選要【刪除】的片段類型", font=(self.font_family, 14, "bold"), text_color=("#1F6AA5", "#88C0D0")).pack(pady=15)
            
            chk_frame = ctk.CTkScrollableFrame(top, fg_color="transparent") 
            chk_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            sb_descriptions = {
                'sponsor': "廠商付費的業配內容 (如 VPN、手遊廣告)",
                'selfpromo': "創作者推銷自己的周邊、課程或會員",
                'interaction': "請求按讚、訂閱、分享的互動提醒",
                'intro': "固定的開場動畫、Logo 或主題曲",
                'outro': "片尾名單、結尾畫面或推薦卡片",
                'preview': "影片開頭的精彩預告或前情提要",
                'music_offtopic': "MV 中間的演戲、對話等非音樂部分",
                'filler': "離題閒聊、拖時間或無實質內容片段"
            }
            
            for key, text in self.sb_labels.items():
                var = self.sb_vars[key]
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
        
        on_sb_toggle()
        CTkToolTip(sb_sw, "自動移除影片中的特定片段 (如廣告、片頭等)。\n點擊右側按鈕可自定義要刪除的類別。")


    def _toggle_format_mode(self, mode):
        """切換影片模式/音訊模式的顯示"""
        is_compat = self.var_compat_mode.get() if hasattr(self, 'var_compat_mode') else False
        
        if mode == "video":
            self.video_settings_frame.pack(fill="x", padx=0, pady=0, before=self.post_frame)
            self.audio_settings_frame.pack_forget()
            # 啟用影片相關的後處理選項
            if hasattr(self, 'sw_embed_thumb'): self.sw_embed_thumb.configure(state="normal")
            if hasattr(self, 'sw_embed_subs'): self.sw_embed_subs.configure(state="normal")
            # 解鎖音訊格式 (音訊模式的)
            if hasattr(self, 'combo_audio_format'): self.combo_audio_format.configure(state="normal")
            
            # 應用相容性模式
            if is_compat:
                self.var_video_codec_select.set("H.264 - 舊裝置/車機")
                self.combo_video_codec_select.configure(state="disabled")
                self.combo_audio_codec.set("AAC/m4a - 車機/蘋果")
                self.combo_audio_codec.configure(state="disabled")
        else:
            self.video_settings_frame.pack_forget()
            self.audio_settings_frame.pack(fill="x", padx=0, pady=0, before=self.post_frame)
            # 禁用影片相關的後處理選項
            if hasattr(self, 'sw_embed_thumb'): self.sw_embed_thumb.configure(state="disabled")
            if hasattr(self, 'sw_embed_subs'): self.sw_embed_subs.configure(state="disabled")
            # 解鎖影片編碼
            if hasattr(self, 'combo_video_codec_select'): self.combo_video_codec_select.configure(state="normal")
            if hasattr(self, 'combo_audio_codec'): self.combo_audio_codec.configure(state="normal")
            
            # 應用相容性模式
            if is_compat:
                self.var_audio_format.set("MP3 - 萬用格式")
                self.combo_audio_format.configure(state="disabled")
        
        self.update_dynamic_hint()

    def update_dynamic_hint(self, *args):
        """更新格式提示文字"""
        mode = self.var_download_mode.get() if hasattr(self, 'var_download_mode') else "video"
        v_codec = self.var_video_codec_select.get() if hasattr(self, 'var_video_codec_select') else "Auto"
        a_codec = self.var_audio_codec.get() if hasattr(self, 'combo_audio_codec') else "Auto"
        is_compat = self.var_compat_mode.get() if hasattr(self, 'var_compat_mode') else False
        
        # 連動邏輯：H.264 強制搭配 AAC (若非相容性模式才處理，相容性模式已在開關中處理)
        if mode == "video" and not is_compat:
            if "H.264" in v_codec:
                current = self.combo_audio_codec.get()
                if "AAC" not in current:
                    self.combo_audio_codec.set("AAC/m4a - 車機/蘋果")
                self.combo_audio_codec.configure(state="disabled")
            else:
                self.combo_audio_codec.configure(state="normal")
        
        # 產生提示文字
        if mode == "audio":
            audio_fmt = self.var_audio_format.get() if hasattr(self, 'var_audio_format') else "mp3"
            if is_compat:
                hint = "提示：相容性最佳模式\n將下載 MP3 格式，所有裝置都能播放"
            elif "FLAC" in audio_fmt or "WAV" in audio_fmt:
                hint = "提示：無損格式將保留原始音質\n(注意：YouTube 來源多為有損，轉成無損不會提升品質)"
            else:
                hint = f"提示：將下載 {audio_fmt.split(' ')[0]} 格式的純音訊"
        else:
            # 影片模式
            container = self.var_video_format.get() if hasattr(self, 'var_video_format') else "mp4"
            
            if is_compat:
                hint = "提示：相容性最佳模式 (H.264 + AAC)\n所有裝置都能播放，車機、舊電視、手機最穩"
            elif "H.264" in v_codec:
                hint = "提示：H.264 模式 (1080p + AAC)\n確保老舊裝置皆可播放"
            elif "H.265" in v_codec:
                hint = "提示：H.265 模式 (HEVC)\n需下載後重新轉檔，檔案極小"
            elif "VP9" in v_codec:
                hint = "提示：VP9 模式\nGoogle 的 4K 標準，舊電腦也能看"
            elif "AV1" in v_codec:
                hint = "提示：AV1 模式\n極致畫質但較吃效能"
            elif "AAC" in a_codec:
                hint = "提示：AAC 音訊編碼\n車機、蘋果裝置相容性佳"
            elif "MP3" in a_codec:
                hint = "提示：MP3 音訊編碼\n所有裝置都能播放 (需轉檔)"
            elif "Opus" in a_codec:
                hint = "提示：Opus 音訊編碼\n音質最好、檔案最小"
            else:
                hint = f"提示：將下載 {container} 格式 (自動最佳品質)"
        
        # 更新 Label
        if hasattr(self, 'lbl_format_hint'):
            self.lbl_format_hint.configure(text=hint, text_color=("#1F6AA5", "#88C0D0"))

