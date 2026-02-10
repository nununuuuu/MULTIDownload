import customtkinter as ctk
import webbrowser
from constants import APP_VERSION, GITHUB_REPO
from ui.tooltip import CTkToolTip

class AdvancedSettingsMixin:
    """
    負責進階設定 (Advanced Tab -> Settings / Cookie / Network) 的 UI 建構與互動邏輯
    這裡包含整個「設定」分頁的邏輯，因為它實際上包含了 Cookie, Network, Performance 等多個子區塊
    """
    def setup_settings_ui(self):
        """設定分頁 - 只包含外觀與行為設定"""
        # Main Scrollable
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.pack(fill="both", expand=True)

        # Helper: Section Card
        def create_section_card(parent, title, icon):
            card = ctk.CTkFrame(parent, fg_color=("gray95", "#454545"), corner_radius=12)
            card.pack(fill="x", padx=20, pady=15)
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=25, pady=(20, 10))
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 20)).pack(side="left", padx=(0, 15))
            ctk.CTkLabel(header, text=title, font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=25, pady=(0, 25))
            return content

        # Main Container
        scroll_container = self.settings_scroll # Alias for clarity

        # --- 外觀與行為 (Appearance & Behavior) ---
        app_card = create_section_card(scroll_container, "外觀與行為設定 (Appearance & Behavior)", icon="🎨")
        
        # Theme Row
        theme_box = ctk.CTkFrame(app_card, fg_color="transparent")
        theme_box.pack(fill="x", pady=5)
        
        ctk.CTkLabel(theme_box, text="主題模式 (Theme)", font=self.font_title).pack(side="left")
        
        theme_seg_bg = ctk.CTkFrame(theme_box, fg_color=("gray90", "#1C1C1C"), corner_radius=10, height=40) 
        theme_seg_bg.pack(side="right")
        
        self.theme_opts = [
            ("跟隨系統", "System", "💻"), 
            ("淺色", "Light", "☀"), 
            ("深色", "Dark", "☾")
        ]
        self.theme_btns = {}

        def on_theme_click(mode_name):
            ctk.set_appearance_mode(mode_name) # Call CTk directly
            self.user_selected_theme = mode_name
            
            # Manually update visuals
            for code, btn in self.theme_btns.items():
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
        
        current_mode = getattr(self, 'user_selected_theme', 'System')
        
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
            btn.grid(row=0, column=i, padx=4, pady=4)
            self.theme_btns[code] = btn
            
            # Check for initial match
            if code == current_mode:
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

        # Toggles
        # Init Variables
        if not hasattr(self, 'var_clipboard'): self.var_clipboard = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_notification'): self.var_notification = ctk.BooleanVar(value=True)
        if not hasattr(self, 'var_auto_start'): self.var_auto_start = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_auto_update'): self.var_auto_update = ctk.BooleanVar(value=True)
        
        def _save(): 
             if hasattr(self, 'save_config'): self.save_config()

        def _add_switch(title, var, desc):
            f = ctk.CTkFrame(app_card, fg_color="transparent")
            f.pack(fill="x", pady=(15, 0))
            
            r1 = ctk.CTkFrame(f, fg_color="transparent")
            r1.pack(fill="x")
            
            ctk.CTkLabel(r1, text=title, font=(self.font_family, 15, "bold")).pack(side="left")
            
            sw = ctk.CTkSwitch(r1, text="", variable=var, command=_save, progress_color="#2CC985", button_hover_color="#20A068", width=40)
            sw.pack(side="right")
            
            ctk.CTkLabel(f, text=desc, font=(self.font_family, 12), text_color=("gray50", "gray60"), wraplength=500, justify="left").pack(anchor="w", pady=(2,0))

        # Search Limit Slider
        if not hasattr(self, 'var_search_limit'): self.var_search_limit = ctk.IntVar(value=20)

        def _update_limit_label(value):
            limit_lbl.configure(text=f"各平台搜尋結果數量：{int(value)}")
            if hasattr(self, 'save_config'): self.save_config()

        limit_frame = ctk.CTkFrame(app_card, fg_color="transparent")
        limit_frame.pack(fill="x", pady=(15, 0))
        
        limit_top = ctk.CTkFrame(limit_frame, fg_color="transparent")
        limit_top.pack(fill="x")
        
        limit_lbl = ctk.CTkLabel(limit_top, text=f"各平台搜尋結果數量：{self.var_search_limit.get()}", font=(self.font_family, 15, "bold"))
        limit_lbl.pack(side="left")
        
        slider = ctk.CTkSlider(limit_frame, from_=5, to=50, number_of_steps=9, variable=self.var_search_limit, command=_update_limit_label, 
                               progress_color=("#1F6AA5", "#88C0D0"), button_color=("#1F6AA5", "#88C0D0"), button_hover_color=("#1565a0", "#6bb0c0"))
        slider.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(limit_frame, text="設定各平台 (YouTube + Bilibili) 分別搜尋的數量。", font=(self.font_family, 12), text_color=("gray50", "gray60")).pack(anchor="w")

        _add_switch("監聽剪貼簿", self.var_clipboard, "若啟用，會自動檢測並搜尋剪貼簿中的影片連結。")
        _add_switch("通知系統", self.var_notification, "若啟用，下載完成時會發送系統通知。")
        _add_switch("自動開始下載", self.var_auto_start, "若啟用，新增任務後會自動開始下載。")
        _add_switch("自動檢查更新", self.var_auto_update, "啟動時檢查更新。")

        # Reset Button
        ctk.CTkFrame(scroll_container, height=1, fg_color=("gray90", "#404040")).pack(fill="x", pady=20)
        
        reset_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        reset_frame.pack(fill="x", padx=30, pady=(0, 30))
        ctk.CTkButton(
            reset_frame, 
            text="重置設定",
            font=("Microsoft JhengHei UI", 15, "bold"), 
            fg_color="transparent", 
            border_width=1,
            border_color="#D93025",
            text_color="#D93025",
            hover_color="#FEE2E2",
            height=35,
            command=self.clear_cache_and_reset
        ).pack(fill="x")

    def setup_advanced_ui(self):
        """進階設定頁面 - 包含 Cookie、效能、網路設定"""
        # 建立捲動區域以容納更多設定
        scroll_container = ctk.CTkScrollableFrame(self.tab_adv, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Helper: Section Card ---
        def create_section_card(parent, title, icon="⚙️"):
            frame = ctk.CTkFrame(parent, fg_color=("gray95", "#454545"), corner_radius=15)
            frame.pack(fill="x", pady=10, padx=10)
            
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray10", "gray90")).pack(side="left")
            
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=(0, 20))
            return content

        # --- 1. Cookie 來源 (Cookies) ---
        cookie_card = create_section_card(scroll_container, "帳號授權與 Cookie (Account)", icon="🍪")
        
        if not hasattr(self, 'var_cookie_mode'):
            self.var_cookie_mode = ctk.StringVar(value="none")
        
        # 統一按鈕樣式定義
        SELECTED_STYLE = {
            "fg_color": ("#1F6AA5", "#88C0D0"),
            "text_color": ("white", "#1A1A1A"),
            "border_width": 0,
            "hover_color": ("#144870", "#6bb0c0")
        }
        UNSELECTED_STYLE = {
            "fg_color": ("white", "#2B2B2B"),
            "text_color": ("gray20", "gray80"),
            "border_width": 1,
            "border_color": ("gray70", "gray50"),
            "hover_color": ("#E5E5E5", "#404040")
        }
        
        # 建立視覺更新函數
        def update_browser_visuals(*args):
            if not hasattr(self, 'browser_btns'): return
            current = self.var_cookie_mode.get()
            
            for val, btn in self.browser_btns.items():
                if val == current:
                    btn.configure(**SELECTED_STYLE)
                else:
                    btn.configure(**UNSELECTED_STYLE)
        
        # 儲存為實例方法以供外部調用
        self._update_browser_visuals = update_browser_visuals

        # 核心：監聽變數變動
        self.var_cookie_mode.trace_add("write", update_browser_visuals)
        
        # Sub-section: Browser
        b_header = ctk.CTkFrame(cookie_card, fg_color="transparent")
        b_header.pack(fill="x", pady=(5, 10))
        ctk.CTkLabel(b_header, text="從瀏覽器讀取", font=("Microsoft JhengHei UI", 14, "bold"), text_color="gray").pack(side="left")
        
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

        for i, (text, val) in enumerate(browsers):
            btn = ctk.CTkButton(
                browser_grid, 
                text=text, 
                height=32,
                font=self.font_text,
                corner_radius=16,
                command=lambda v=val: on_browser_click(v),
                **UNSELECTED_STYLE
            )
            btn.grid(row=i//4, column=i%4, padx=6, pady=6, sticky="ew")
            self.browser_btns[val] = btn
            browser_grid.grid_columnconfigure(i%4, weight=1)

        CTkToolTip(browser_grid, "自動讀取瀏覽器登入狀態 (例如 YouTube Premium 會員)。\n執行前建議完全關閉瀏覽器以避免讀取鎖定。")

        # Sub-section: File
        ctk.CTkFrame(cookie_card, height=2, fg_color=("gray85", "gray30")).pack(fill="x", pady=20)
        
        f_header = ctk.CTkFrame(cookie_card, fg_color="transparent")
        f_header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_header, text="使用 cookies.txt 或直接貼上 cookies (穩定)", font=("Microsoft JhengHei UI", 14, "bold"), text_color="gray").pack(side="left")
        
        lbl_f_help = ctk.CTkLabel(f_header, text="❓", cursor="hand2", font=self.font_small)
        lbl_f_help.pack(side="left", padx=5)
        CTkToolTip(lbl_f_help, "【如何取得 cookies.txt ?】\n建議點擊右側連結安裝「Get cookies.txt LOCALLY」擴充功能。\n安裝後：到 YouTube 首頁登入 -> 點擊擴充功能圖示 -> \"Export\" -> 下載")
        
        # Links
        link_box = ctk.CTkFrame(f_header, fg_color="transparent")
        link_box.pack(side="right")
        
        def make_link(parent, text, url):
            lbl = ctk.CTkLabel(parent, text=text, text_color=("#1F6AA5", "#88C0D0"), cursor="hand2", font=self.font_small)
            lbl.pack(side="left", padx=5)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            lbl.bind("<Enter>", lambda e: lbl.configure(text_color=("#144870", "#6bb0c0")))
            lbl.bind("<Leave>", lambda e: lbl.configure(text_color=("#1F6AA5", "#88C0D0")))
            
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
            command=on_file_mode_click,
            **UNSELECTED_STYLE
        )
        btn_file_mode.pack(side="left", padx=(0, 10))
        self.browser_btns['file'] = btn_file_mode 

        self.entry_cookie_path = ctk.CTkEntry(f_input_box, placeholder_text="請選擇 cookies.txt...", state="disabled", height=35)
        self.entry_cookie_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_cookie_browse = ctk.CTkButton(f_input_box, text="瀏覽", width=80, height=35, state="disabled", fg_color="#555555", command=self.browse_cookie_file)
        self.btn_cookie_browse.pack(side="left")

        # --- 貼上模式區塊 ---
        paste_input_box = ctk.CTkFrame(cookie_card, fg_color="transparent")
        paste_input_box.pack(fill="x", padx=10, pady=(10, 0))
        
        def on_paste_mode_click():
            self.var_cookie_mode.set("paste")
            self.on_cookie_mode_change()
            update_browser_visuals()
            if hasattr(self, 'save_config'): self.save_config()
            
        btn_paste_mode = ctk.CTkButton(
            paste_input_box, text="貼上模式", width=100, height=32, corner_radius=16,
            command=on_paste_mode_click,
            **UNSELECTED_STYLE
        )
        btn_paste_mode.pack(side="left", padx=(0, 10))
        self.browser_btns['paste'] = btn_paste_mode
        
        # 貼上狀態指示
        self.lbl_paste_status = ctk.CTkLabel(
            paste_input_box, 
            text="尚未貼上 Cookie", 
            font=self.font_small,
            text_color=("gray50", "gray60")
        )
        self.lbl_paste_status.pack(side="left", padx=(0, 10))
        
        # 編輯/貼上按鈕
        self.btn_cookie_paste = ctk.CTkButton(
            paste_input_box, text="📋 貼上 Cookie", width=120, height=35, 
            state="disabled", fg_color="#555555", 
            command=self.open_cookie_paste_dialog
        )
        self.btn_cookie_paste.pack(side="right")
        


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
        # 使用與 SELECTED_STYLE 相同的顏色
        ACTIVE_COLOR = ("#1F6AA5", "#88C0D0")
        ACTIVE_TEXT = ("white", "#1A1A1A")  # 淺色模式白字，深色模式黑字
        ACTIVE_HOVER = ("#144870", "#6bb0c0")  # hover 變深
        DISABLED_COLOR = "#555555"
        DISABLED_TEXT = ("gray60", "gray60")
        
        if mode == "file":
            self.entry_cookie_path.configure(state="normal")
            self.btn_cookie_browse.configure(state="normal", fg_color=ACTIVE_COLOR, text_color=ACTIVE_TEXT, hover_color=ACTIVE_HOVER)
            self.btn_cookie_paste.configure(state="disabled", fg_color=DISABLED_COLOR, text_color=DISABLED_TEXT)
            self.log("[設定變更] Cookie 來源切換為: 檔案 (cookies.txt)")
            self.show_toast("Cookie 來源: 檔案")
        elif mode == "paste":
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color=DISABLED_COLOR, text_color=DISABLED_TEXT)
            self.btn_cookie_paste.configure(state="normal", fg_color=ACTIVE_COLOR, text_color=ACTIVE_TEXT, hover_color=ACTIVE_HOVER)
            self.log("[設定變更] Cookie 來源切換為: 貼上模式")
            self.show_toast("Cookie 來源: 貼上模式")
            # 更新狀態標籤
            self._update_paste_status()
        else:
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color=DISABLED_COLOR, text_color=DISABLED_TEXT)
            self.btn_cookie_paste.configure(state="disabled", fg_color=DISABLED_COLOR, text_color=DISABLED_TEXT)
            
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
        from tkinter import filedialog
        p = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if p:
            self.entry_cookie_path.delete(0, "end")
            self.entry_cookie_path.insert(0, p)

    def _get_pasted_cookie_path(self):
        """取得貼上 Cookie 的儲存路徑"""
        import os
        data_dir = getattr(self, 'data_dir', None)
        if not data_dir:
            # Fallback: 使用 app_path
            if hasattr(self, 'config_file'):
                data_dir = os.path.dirname(self.config_file)
            else:
                data_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(data_dir, "pasted_cookies.txt")
    
    def _update_paste_status(self):
        """更新貼上 Cookie 狀態標籤"""
        import os
        cookie_path = self._get_pasted_cookie_path()
        if os.path.exists(cookie_path):
            # 顯示檔案大小
            size = os.path.getsize(cookie_path)
            if size > 0:
                self.lbl_paste_status.configure(
                    text=f"✓ 已貼上 ({size} bytes)",
                    text_color=("#01814A", "#2CC985")
                )
            else:
                self.lbl_paste_status.configure(
                    text="尚未貼上 Cookie",
                    text_color=("gray50", "gray60")
                )
        else:
            self.lbl_paste_status.configure(
                text="尚未貼上 Cookie",
                text_color=("gray50", "gray60")
            )
    
    def _convert_header_string_to_netscape(self, content):
        """將 HTTP Header String 格式轉換為 Netscape 格式
        
        輸入範例: PREF=tz=Asia.Taipei;HSID=abc123;SID=xyz789
        輸出範例:
        # Netscape HTTP Cookie File
        .youtube.com	TRUE	/	FALSE	1739180400	PREF	tz=Asia.Taipei
        .youtube.com	TRUE	/	FALSE	1739180400	HSID	abc123
        """
        import time
        content = content.strip()
        
        # 清理可能包含的 Header 前綴
        if content.lower().startswith("cookie:"):
            content = content[7:].strip()
        elif content.lower().startswith("set-cookie:"):
            content = content[11:].strip()
            
        # 檢查是否已經是 Netscape 格式 (以 # 開頭或包含 Tab 分隔)
        if content.startswith("#") or "\t" in content:
            return content  # 不需要轉換
        
        # 檢查是否是 Header String 格式 (NAME=value;NAME2=value2...)
        if "=" in content and (";" in content or content.count("=") == 1):
            netscape_lines = ["# Netscape HTTP Cookie File", "# Converted from Header String format by MULTIDownload", ""]
            
            # 設定過期時間為一年後 (避免 expiration=0 導致 cookie 被視為無效)
            expire_ts = str(int(time.time()) + 365 * 24 * 3600)
            
            # 需要同時寫入 .google.com 的 cookie 名稱 (YouTube 認證必備)
            google_auth_cookies = {
                'SAPISID', '__Secure-1PAPISID', '__Secure-3PAPISID',
                'SID', '__Secure-1PSID', '__Secure-3PSID',
                'SSID', 'HSID', 'APISID',
                '__Secure-1PSIDTS', '__Secure-3PSIDTS',
                'SIDCC', '__Secure-1PSIDCC', '__Secure-3PSIDCC',
                'NID', 'LOGIN_INFO', 'VISITOR_PRIVACY_METADATA'
            }
            
            # 分割各個 cookie
            # [Fix] 處理可能存在的換行
            content = content.replace("\n", "").replace("\r", "")
            cookies = content.split(";")
            
            count = 0
            for cookie in cookies:
                cookie = cookie.strip()
                if not cookie or "=" not in cookie:
                    continue
                
                # 分割 name 和 value (只在第一個 = 處分割)
                eq_pos = cookie.find("=")
                name = cookie[:eq_pos].strip()
                value = cookie[eq_pos+1:].strip()
                
                if not name:
                    continue
                
                # 判斷 secure flag
                secure = "TRUE" if name.startswith("__Secure-") else "FALSE"
                
                # 產生 Netscape 格式行
                # 格式: domain	flag	path	secure	expiration	name	value
                line = f".youtube.com\tTRUE\t/\t{secure}\t{expire_ts}\t{name}\t{value}"
                netscape_lines.append(line)
                count += 1
                
                # 若為 Google 認證 cookie，同時寫入 .google.com 域名
                if name in google_auth_cookies:
                    line_google = f".google.com\tTRUE\t/\t{secure}\t{expire_ts}\t{name}\t{value}"
                    netscape_lines.append(line_google)
            
            if count > 0:  # 有成功轉換至少一個 cookie
                self.log(f"[Cookie] 識別格式：Header String 格式 → 正在轉換為 Netscape 格式...")
                self.log(f"[Cookie] 轉換完成！共 {count} 個 Cookie")
                return "\n".join(netscape_lines)
            
            if len(netscape_lines) > 3:  # 有成功轉換至少一個 cookie
                self.log(f"[Cookie] 已自動將 Header String 格式轉換為 Netscape 格式 ({len(netscape_lines) - 3} 個 cookie)")
                return "\n".join(netscape_lines)
        
        # 無法識別的格式，原樣返回
        return content

    def open_cookie_paste_dialog(self):
        """開啟貼上 Cookie 對話框"""
        import os
        from ui.dialogs import CookiePasteDialog
        
        cookie_path = self._get_pasted_cookie_path()
        current_content = ""
        
        # 讀取現有內容 (如果有)
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, "r", encoding="utf-8") as f:
                    current_content = f.read()
            except:
                pass
        
        dlg = CookiePasteDialog(self, current_content)
        self.wait_window(dlg)
        
        if dlg.result is not None:
            # 儲存到檔案
            try:
                # 確保目錄存在
                os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
                
                # [New] 自動轉換格式
                converted_content = self._convert_header_string_to_netscape(dlg.result)
                
                with open(cookie_path, "w", encoding="utf-8") as f:
                    f.write(converted_content)
                
                self.log("[設定變更] Cookie 內容已儲存")
                self.show_toast("Cookie 已儲存！", color="#01814A")
                self._update_paste_status()
                
                # 儲存設定
                if hasattr(self, 'save_config'): 
                    self.save_config()
                    
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("錯誤", f"儲存 Cookie 失敗：\n{e}")
            
    def clear_cache_and_reset(self):
        """重置設定頁面"""
        try:
             import tkinter.messagebox as messagebox
             if messagebox.askyesno("重置設定", "確定要重置此頁面的所有設定嗎？\n(包含主題與功能開關)"):
                # 1. 重置變數
                if hasattr(self, 'var_clipboard'): self.var_clipboard.set(False)
                if hasattr(self, 'var_notification'): self.var_notification.set(True)
                if hasattr(self, 'var_auto_start'): self.var_auto_start.set(False)
                if hasattr(self, 'var_auto_update'): self.var_auto_update.set(True)
                if hasattr(self, 'attributes'): self.attributes("-topmost", False)

                # 2. 重置主題
                self.user_selected_theme = "System"
                ctk.set_appearance_mode("System")
                
                # 更新按鈕樣式
                if hasattr(self, 'theme_btns'):
                    for code, btn in self.theme_btns.items():
                        if code == "System":
                           btn.configure(fg_color=("white", "#5A5A5A"), text_color=("#1F6AA5", "#88C0D0"), border_color=("#1F6AA5", "#88C0D0"), border_width=1)
                        else:
                           btn.configure(fg_color=("gray90", "gray30"), text_color=("gray10", "gray90"), border_color="transparent", border_width=0)

                # 3. 儲存
                if hasattr(self, 'save_config'): self.save_config()
                
                self.update_idletasks()
                self.show_toast("設定已重置", duration=1500)
                
        except Exception as e:
             print(f"Reset config error: {e}")
