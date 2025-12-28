import customtkinter as ctk
import time
from tkinter import messagebox
from ui.tooltip import CTkToolTip

class TaskLayoutMixin:
    """
    負責任務列表 (Tasks) 相關的 UI 邏輯
    """
    
    # --- 任務整合介面 (Setup Tasks UI) ---
    def setup_tasks_ui(self):
        # 1. 佈局基礎 (Rows: 0=Nav, 1=Content)
        self.tab_tasks.grid_columnconfigure(0, weight=1)
        self.tab_tasks.grid_columnconfigure(1, weight=0) # Remove old col config
        self.tab_tasks.grid_rowconfigure(0, weight=0) # Nav
        self.tab_tasks.grid_rowconfigure(1, weight=1) # Content

        # 2. 頂部導航欄 (Top Navigation)
        self.nav_frame = ctk.CTkFrame(self.tab_tasks, fg_color="transparent") # Remove fixed height
        self.nav_frame.grid(row=0, column=0, sticky="ew", pady=(20, 15), padx=20, columnspan=2)
        
        # Segmented Control - Modern Capsule Style
        self.seg_tasks = ctk.CTkSegmentedButton(
            self.nav_frame, 
            values=["等待中", "進行中", "已完成"], 
            command=self.switch_task_view,
            font=("Microsoft JhengHei UI", 14, "bold"),
            height=42, # Taller
            width=520, # Wider to breathe
            corner_radius=21, # Capsule shape
            selected_color="#1F6AA5", selected_hover_color="#144870",
            # unselected_color/hover defaults are usually fine, but adding fg_color gives it a track
            fg_color=("gray85", "gray30") 
        )
        self.seg_tasks.pack(side="top") 
        self.seg_tasks.set("進行中")
        
        # 清除紀錄按鈕 (Clear History) - 絕對定位於右上角
        self.btn_clear_history = ctk.CTkButton(
            self.nav_frame, text="🗑 清除紀錄", width=100, height=32,
            fg_color="transparent", border_width=1, border_color=("gray70", "gray50"), 
            text_color=("gray20", "gray80"), hover_color=("gray90", "gray30"), 
            font=("Microsoft JhengHei UI", 13, "bold"), command=self.clear_history
        )
        
        # 3. 內容容器 (Content Container)
        self.task_content_container = ctk.CTkFrame(self.tab_tasks, fg_color="transparent")
        self.task_content_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=0, columnspan=2)
        
        # --- Views (Scrollable) ---
        self.view_waiting = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        self.view_active = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        self.view_finished = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        
        # --- Empty State Labels (Overlay on Container) ---
        # 這些標籤直接掛載在 container 上，使用 place 絕對置中，避免受 ScrollableFrame 內部高度影響
        self.lbl_waiting_empty = ctk.CTkLabel(self.task_content_container, text="目前沒有等待中的任務", text_color="gray", font=self.font_text)
        self.lbl_active_empty = ctk.CTkLabel(self.task_content_container, text="目前沒有執行中的任務", text_color="gray", font=self.font_text)
        self.lbl_finished_empty = ctk.CTkLabel(self.task_content_container, text="目前沒有已完成的紀錄", text_color="gray", font=self.font_text)
        
        # 初始化顯示
        self.current_task_view = "進行中"
        self.switch_task_view("進行中")

    def _generate_meta_text(self, config):
        parts = []
        # 1. 輸出格式
        parts.append(config.get('ext', ''))
        
        # 2. 影片畫質 (若非純音訊模式)
        if not config.get('is_audio_only'):
            res = config.get('video_res', 'Best')
            res_str = res.split(' ')[0]
            if config.get('use_h264_legacy'):
                res_str += " (H.264)"
            parts.append(res_str)
            
        # 3. 音訊音質
        qual = config.get('audio_qual', 'Best')
        parts.append(qual.split(' ')[0])
        
        # 4. 音訊編碼
        codec = config.get('audio_codec', 'Auto')
        parts.append(codec.split(' ')[0])
        
        # 5. 影片縮圖
        if config.get('embed_thumbnail'): parts.append("影片縮圖")
        
        # 6. 字幕檔案 (內嵌)
        if config.get('embed_subs'): parts.append("字幕檔案")
        
        # 7. 中繼資料
        if config.get('add_metadata'): parts.append("中繼資料")
        
        # 8. 字幕 (下載)
        if config.get('sub_langs'): parts.append("字幕")
        
        # 9. 時間裁剪
        if config.get('use_time_range'): parts.append("時間裁剪")
        
        # 10. 直播模式
        if config.get('is_live'):
            mode = "現在開始"
            if config.get('live_from_start'): mode = "從頭追溯"
            parts.append(mode)

        return " | ".join(parts)

    def switch_task_view(self, value):
        self.current_task_view = value
        
        # 隱藏所有視圖 & 按鈕
        self.view_waiting.pack_forget()
        self.view_active.pack_forget()
        self.view_finished.pack_forget()
        self.btn_clear_history.place_forget()
        
        # 隱藏所有空狀態標籤 (預設)
        self.lbl_waiting_empty.place_forget()
        self.lbl_active_empty.place_forget()
        self.lbl_finished_empty.place_forget()
        
        # 顯示選定視圖，並檢查該視圖是否為空以顯示標籤
        if value == "等待中":
            self.view_waiting.pack(fill="both", expand=True)
            if not self.download_queue: 
                self.lbl_waiting_empty.place(relx=0.5, rely=0.4, anchor="center")
                
        elif value == "進行中":
            self.view_active.pack(fill="both", expand=True)
            if not getattr(self, 'active_task_widgets', {}): 
                self.lbl_active_empty.place(relx=0.5, rely=0.4, anchor="center")
                
        elif value == "已完成":
            self.view_finished.pack(fill="both", expand=True)
            self.btn_clear_history.place(relx=1.0, rely=0.5, anchor="e")
            if not getattr(self, 'history_data', []): 
                self.lbl_finished_empty.place(relx=0.5, rely=0.4, anchor="center")

    def update_queue_ui(self):
        """更新等待中(排程)介面"""
        # view_waiting 只包含任務列表卡片，直接清空
        if hasattr(self, 'view_waiting'):
            for widget in self.view_waiting.winfo_children():
                widget.destroy()

        self.queue_vars = []

        if not self.download_queue:
            # 若目前在等待分頁，顯示空狀態
            if self.current_task_view == "等待中":
                self.lbl_waiting_empty.place(relx=0.5, rely=0.4, anchor="center")
            else:
                self.lbl_waiting_empty.place_forget()
        else:
            # 隱藏空狀態
            self.lbl_waiting_empty.place_forget()
            
            # Control Frame
            ctrl_frame = ctk.CTkFrame(self.view_waiting, fg_color="transparent")
            ctrl_frame.pack(fill="x", padx=10, pady=(0, 15))
            
            # Select All Checkbox
            self.var_select_all = ctk.BooleanVar(value=False)
            chk_all = ctk.CTkCheckBox(ctrl_frame, text="全選", font=self.font_small, width=60, 
                                      variable=self.var_select_all, command=self.toggle_select_all)
            chk_all.pack(side="left", padx=5)
            
            # Download Selected Button
            ctk.CTkButton(
                ctrl_frame, text="開始下載選取項目", fg_color="#01814A", hover_color="#006030", font=self.font_btn,
                height=32, corner_radius=16,
                command=self.start_selected_queue
            ).pack(side="right", padx=5)
        
        for i, config in enumerate(self.download_queue):
            # Card Style
            row = ctk.CTkFrame(self.view_waiting, fg_color=("white", "#2B2B2B"), corner_radius=12,
                               border_width=1, border_color=("gray85", "#3A3A3A"))
            row.pack(fill="x", pady=6, padx=10)
            
            # Checkbox
            var = ctk.BooleanVar(value=False)
            self.queue_vars.append(var)
            chk = ctk.CTkCheckBox(row, text="", width=24, variable=var, command=self.update_select_all_state)
            chk.pack(side="left", padx=(15, 10), anchor="center")
            
            # Info Frame
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=12)
            
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
            
            if len(display_name) > 60: display_name = display_name[:57] + "..."
            
            # Title
            ctk.CTkLabel(info_frame, text=display_name, font=("Microsoft JhengHei UI", 13, "bold"), anchor="w", text_color=("#1F6AA5", "#3B8ED0")).pack(fill="x")
            
            # URL (Show only if different from display_name AND didn't fallback to URL)
            if config['url'] != display_name and not is_using_url_as_title:
                url_text = config['url']
                if len(url_text) > 80: url_text = url_text[:77] + "..."
                ctk.CTkLabel(info_frame, text=url_text, text_color="gray", font=("Consolas", 11), anchor="w").pack(fill="x", pady=(2, 0))
            
            # Meta Badges
            details_text = self._generate_meta_text(config)
            ctk.CTkLabel(info_frame, text=details_text, text_color=("gray40", "gray60"), font=self.font_small, anchor="w").pack(fill="x", pady=(5, 0))

            # Remove Button
            ctk.CTkButton(
                row, text="✕", width=36, height=36, fg_color="transparent", hover_color=("#FFEEEE", "#440000"), text_color="red", 
                font=("Arial", 16), corner_radius=18,
                command=lambda idx=i: self.remove_from_queue(idx)
            ).pack(side="right", padx=15)

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

    def create_active_task_widget(self, task_id, config, initial_status="準備中..."):
        # Card style
        row = ctk.CTkFrame(self.view_active, fg_color=("white", "#2B2B2B"), corner_radius=12,
                           border_width=1, border_color=("gray85", "#3A3A3A"))
        row.pack(fill="x", pady=6, padx=10)
        
        self.lbl_active_empty.place_forget()
        self.active_task_widgets[task_id] = {'frame': row}

        self.active_task_widgets[task_id] = {'frame': row}

        # 1. Right Side: Cancel Button (Fixed)
        btn_cancel = ctk.CTkButton(row, text="✕", width=36, height=36, fg_color="transparent", text_color="red", hover_color=("#FFEEEE", "#440000"),
                                   font=("Arial", 16), corner_radius=18,
                                   command=lambda: self.cancel_task(task_id))
        btn_cancel.pack(side="right", padx=(5, 10))

        # 2. Right Side: Status & Speed (Fixed width to prevent jitter, but packed before main info)
        status_frame = ctk.CTkFrame(row, fg_color="transparent")
        status_frame.pack(side="right", padx=5, pady=12)
        
        # Status Text
        # Removed fixed width to allow natural sizing, or use a smaller min-width logic if needed. 
        # For now, natural size prevents empty space issues, but might cause slight jitter. 
        # To fix jitter without fixed width, we can rely on right-alignment.
        lbl_stat = ctk.CTkLabel(status_frame, text=initial_status, font=("Microsoft JhengHei UI", 14, "bold"), text_color="#24A36C", anchor="e")
        lbl_stat.pack(anchor="e")
        self.active_task_widgets[task_id]['status_label'] = lbl_stat
        
        # Speed & ETA
        meta_lbl = ctk.CTkLabel(status_frame, text="-- MB/s  |  --:--", font=("Consolas", 11), text_color=("gray50", "gray70"), anchor="e")
        meta_lbl.pack(anchor="e", pady=(2, 0))
        self.active_task_widgets[task_id]['meta_label'] = meta_lbl

        # 3. Main Info (Left - Expands to fill remaining space)
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=12)
        
        # Determine Title
        title = config.get('filename')
        if not title: title = config.get('default_title')
        if not title or title == "尚未分析": title = config.get('url')
        if len(title) > 55: title = title[:52] + "..."
        
        # Title Label
        lbl_title = ctk.CTkLabel(info_frame, text=title, font=("Microsoft JhengHei UI", 13, "bold"), anchor="w", text_color=("#1F6AA5", "#3B8ED0"))
        lbl_title.pack(fill="x")
        self.active_task_widgets[task_id]['title_label'] = lbl_title
        
        # Format Badge
        meta_text = self._generate_meta_text(config)
        ctk.CTkLabel(info_frame, text=meta_text, text_color=("gray50", "gray70"), font=self.font_small, anchor="w").pack(fill="x", pady=(2, 0))
        
        # Progress Bar
        prog = ctk.CTkProgressBar(info_frame, height=8, corner_radius=4)
        prog.set(0)
        prog.pack(fill="x", pady=(8, 0))
        self.active_task_widgets[task_id]['progress_bar'] = prog
        
        # Double-click to Pause/Resume
        def on_double_click(event):
            self.toggle_pause_task(task_id)
            
        def bind_recursive(widget):
            try:
                widget.bind("<Double-Button-1>", on_double_click)
                for child in widget.winfo_children():
                    bind_recursive(child)
            except: pass
            
        bind_recursive(row)
        
        # 暫存上次更新時間 (避免 UI 更新太頻繁)
        self.task_last_update_time[task_id] = 0

    def remove_active_task_widget(self, task_id):
        if task_id in self.active_task_widgets:
            frame = self.active_task_widgets[task_id]['frame']
            frame.destroy()
            del self.active_task_widgets[task_id]
            
            if not self.active_task_widgets:
                if self.current_task_view == "進行中":
                    self.lbl_active_empty.place(relx=0.5, rely=0.4, anchor="center")

    def _update_task_buttons(self, task_id, state):
        """更新單一任務的按鈕圖示 (已改為雙擊暫停，此函式保留相容性)"""
        pass

    def update_task_widget(self, task_id, percent, status_text=None, speed=None, eta=None):
        if task_id not in self.active_task_widgets: return
        
        # Throttling is handled by main.py content update loop to avoid race conditions
        # (main.py updates the timestamp before calling us)

        widgets = self.active_task_widgets[task_id]
        
        if percent >= 0:
            widgets['progress_bar'].set(percent)
        
        if status_text:
            widgets['status_label'].configure(text=status_text)
            
        if speed and eta:
            widgets['meta_label'].configure(text=f"{speed} | {eta}")


    def clear_history(self):
        for widget in self.view_finished.winfo_children():
             widget.destroy()
        self.history_data = [] 
        if self.current_task_view == "已完成":
            self.lbl_finished_empty.place(relx=0.5, rely=0.4, anchor="center")

    def add_history_item(self, config, success, msg):
        if not hasattr(self, 'history_data'): self.history_data = []
        self.history_data.append({'config': config, 'success': success, 'msg': msg})
        self.render_history_item(config, success, msg)

    def render_history_item(self, config, success, msg):
        self.lbl_finished_empty.place_forget()
        
        # Card
        row = ctk.CTkFrame(self.view_finished, fg_color=("white", "#2B2B2B"), corner_radius=12,
                           border_width=1, border_color=("gray85", "#3A3A3A"))
        row.pack(fill="x", pady=6, padx=10)
        
        # Determine Color
        status_color = "#01814A" if success else "#DB3E39"
        
        # Status Indicator Strip (Left)
        strip = ctk.CTkFrame(row, width=6, fg_color=status_color, corner_radius=0, height=60) # height to ensure min height
        strip.pack(side="left", fill="y", padx=(0, 10))
        
        # Info
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=12)
        
        # Title
        display_name = config.get('filename')
        if not display_name:
            default_t = config.get('default_title', '')
            if default_t and default_t not in ["尚未分析", "分析中...", ""]: display_name = default_t
            else: display_name = config['url']
        
        if len(display_name) > 60: display_name = display_name[:57] + "..."
        ctk.CTkLabel(info_frame, text=display_name, font=("Microsoft JhengHei UI", 13, "bold"), anchor="w").pack(fill="x")
        
        # URL
        if config['url'] != display_name:
            url_text = config['url']
            if len(url_text) > 80: url_text = url_text[:77] + "..."
            ctk.CTkLabel(info_frame, text=url_text, text_color="gray", font=("Consolas", 11), anchor="w").pack(fill="x", pady=(2, 0))

        # Details / Error Msg
        if success:
             details_text = self._generate_meta_text(config)
        else:
             details_text = f"❌ {msg}"

        # Use simple color for details, red for error if fail
        detail_color = ("gray50", "gray70") if success else "#DB3E39"
        ctk.CTkLabel(info_frame, text=details_text, text_color=detail_color, font=self.font_small, anchor="w").pack(fill="x", pady=(5, 0))

        # Action Buttons
        action_frame = ctk.CTkFrame(row, fg_color="transparent")
        action_frame.pack(side="right", padx=15)

        save_path = config.get('save_path', '')
        if success and save_path:
             ctk.CTkButton(action_frame, text="開啟", width=60, height=30, font=self.font_small, fg_color=("gray90", "gray30"), text_color=("black", "white"), hover_color=("gray80", "gray40"),
                           command=lambda p=save_path: self.safe_open_path(p)).pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="✕", width=30, height=30, fg_color="transparent", text_color="gray", hover_color=("#FFEEEE", "#440000"),
                      command=lambda w=row: w.destroy()).pack(side="left", padx=5)
