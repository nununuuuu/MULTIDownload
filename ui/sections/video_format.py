import customtkinter as ctk
from ui.tooltip import CTkToolTip

class VideoFormatMixin:
    """
    負責格式設定 (Format Tab) 的 UI 建構與互動邏輯
    包括：影片/音訊格式選擇、SponsorBlock 設定、後處理選項
    """
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
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "#454545"), corner_radius=15)
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
