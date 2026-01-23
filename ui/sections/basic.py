import customtkinter as ctk
from PIL import Image
import requests
import io
import threading
from ui.tooltip import CTkToolTip
from tkinter import messagebox

class BasicTabMixin:
    """
    負責基本選項 (Basic Tab) 的 UI 建構與互動邏輯
    包含：硬體加速偵測顯示、連結貼上、縮圖預覽
    """
    
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
        
        # Reset Params Button (Top Right)
        btn_reset = ctk.CTkButton(self.tab_basic, text="⟲", width=36, height=36, 
                                  font=("Arial", 16, "bold"),
                                  fg_color=("gray85", "#2B2B2B"), 
                                  text_color=("gray10", "gray90"), 
                                  hover_color=("gray75", "#3A3A3A"),
                                  border_width=2,
                                  border_color=("gray60", "#484848"),
                                  command=self.reset_parameters)
        btn_reset.place(relx=0.97, rely=0.02, anchor="ne")

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
        self.preview_card = ctk.CTkFrame(island_frame, fg_color=("white", "#454545"), corner_radius=12, border_width=1, border_color=("#1F6AA5", "#1F6AA5"))
        
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
        settings_card = ctk.CTkFrame(island_frame, fg_color=("white", "#454545"), corner_radius=15, border_width=1, border_color=("#E5E5E5", "#333333"))
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
    
    # ----------------------------------------------------
    #  Moved from main.py: Logic related to Basic Tab
    # ----------------------------------------------------

    def update_thumbnail(self, info):
        """非同步下載並顯示縮圖與資訊"""
        if not hasattr(self, 'preview_card'): return
        
        # Reset if no info
        if not info:
             self.preview_card.pack_forget()
             return

        # [Fix] 防止「分析完成」比「加入任務」晚發生，導致已清空的介面又跳出舊縮圖
        # 如果輸入框已經被清空，就忽略這次的縮圖更新
        if not self.entry_url.get().strip():
            return

        url = info.get('thumbnail')
        title = info.get('title', 'Unknown')
        duration = info.get('duration') # e.g. "3:45"
        uploader = info.get('uploader')
        
        # Reset Thumbnail first (to avoid stale image if new one fails)
        if hasattr(self, 'lbl_thumb_img'):
            self.lbl_thumb_img.configure(image=None, text="") 
            # Force update to clear immediate visual
            self.lbl_thumb_img.update_idletasks()

        # Update Text Info immediately (Auto wrap handle by UI)
        self.lbl_preview_title.configure(text=title)
        
        meta_parts = []
        if uploader: meta_parts.append(uploader)
        if duration: meta_parts.append(duration)
        if not meta_parts: meta_parts.append("Ready")
        self.lbl_preview_meta.configure(text=" • ".join(meta_parts))

        # Show Card
        self.preview_card.pack(side="top", pady=(0, 10), fill="x", padx=10, before=self.entry_url.master.master)

        if not url: return

        def _fetch():
            try:
                # Use headers from yt-dlp info as base
                headers = info.get('http_headers', {}).copy()
                
                # Default UA if missing
                if 'User-Agent' not in headers:
                    headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

                # Bilibili Special Handling for Thumbnails (hdslb.com)
                if "bilibili" in url or "hdslb" in url:
                    headers['Referer'] = "https://www.bilibili.com/"
                elif 'Referer' not in headers:
                     headers['Referer'] = "https://www.youtube.com/" if "youtube" in url else ""

                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = io.BytesIO(resp.content)
                    pil_img = Image.open(data)
                    
                    # Fixed target: height 68
                    base_height = 68
                    w_percent = (base_height / float(pil_img.size[1]))
                    w_size = int((float(pil_img.size[0]) * float(w_percent)))
                    
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w_size, base_height))
                    
                    def _ui():
                        if hasattr(self, 'lbl_thumb_img'):
                             self.lbl_thumb_img.configure(image=ctk_img, text="", width=w_size)
                             self.lbl_thumb_img.image = ctk_img # Keep reference
                    self.after(0, _ui)
            except Exception as e:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_hw_ui(self, accels):
        """更新硬體加速開關的狀態"""
        if not hasattr(self, 'switch_hw'): return
        
        if accels:
             best = accels[0]
             self.detected_gpu = best
             self.switch_hw.configure(state="normal", text=f"啟用硬體加速 ({best})")
        else:
             self.detected_gpu = None
             self.switch_hw.configure(state="disabled", text="未偵測到相容 GPU (硬體加速不可用)")
             self.var_hardware_accel.set(False)

