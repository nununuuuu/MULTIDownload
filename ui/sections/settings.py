import customtkinter as ctk
from constants import APP_VERSION, GITHUB_REPO

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
        
        slider = ctk.CTkSlider(limit_frame, from_=5, to=50, number_of_steps=9, variable=self.var_search_limit, command=_update_limit_label, progress_color="#1F6AA5")
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

    def on_cookie_mode_change(self):
        mode = self.var_cookie_mode.get()
        if mode == "file":
            self.entry_cookie_path.configure(state="normal")
            self.btn_cookie_browse.configure(state="normal", fg_color="#1F6AA5")
            self.btn_cookie_paste.configure(state="disabled", fg_color="#555555")
            self.log("[設定變更] Cookie 來源切換為: 檔案 (cookies.txt)")
            self.show_toast("Cookie 來源: 檔案")
        elif mode == "paste":
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color="#555555")
            self.btn_cookie_paste.configure(state="normal", fg_color="#1F6AA5")
            self.log("[設定變更] Cookie 來源切換為: 貼上模式")
            self.show_toast("Cookie 來源: 貼上模式")
            # 更新狀態標籤
            self._update_paste_status()
        else:
            self.entry_cookie_path.configure(state="disabled")
            self.btn_cookie_browse.configure(state="disabled", fg_color="#555555")
            self.btn_cookie_paste.configure(state="disabled", fg_color="#555555")
            
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
                
                with open(cookie_path, "w", encoding="utf-8") as f:
                    f.write(dlg.result)
                
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
