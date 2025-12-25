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
        # 設定 Grid 佈局：左側內容(重)，右側導航(輕)
        self.tab_tasks.grid_columnconfigure(0, weight=1)
        self.tab_tasks.grid_columnconfigure(1, weight=0)
        self.tab_tasks.grid_rowconfigure(0, weight=1)

        # 1. 內容區域 (左與中)
        self.task_content_container = ctk.CTkFrame(self.tab_tasks, fg_color="transparent")
        self.task_content_container.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # 2. 右側導航欄
        self.task_right_bar = ctk.CTkFrame(self.tab_tasks, width=110, corner_radius=10)
        self.task_right_bar.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.task_right_bar.grid_propagate(False) # 禁止被內容撐大
        self.task_right_bar.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.task_right_bar, text="任務視圖", font=self.font_small, text_color="gray").pack(pady=(15, 5))

        # 定義導航按鈕
        self.task_nav_buttons = {}
        nav_items = [("等待中", " ⏳"), ("進行中", "▶️"), ("已完成", "✔️")]
        
        for i, (name, icon) in enumerate(nav_items):
            btn = ctk.CTkButton(self.task_right_bar, text=f" {name}  {icon}", 
                                font=self.font_text, 
                                fg_color="transparent", 
                                text_color=("gray10", "gray90"),
                                hover_color=("gray75", "gray25"),
                                anchor="e", 
                                height=32,
                                command=lambda n=name: self.switch_task_view(n))
            btn.pack(fill="x", pady=2, padx=5)
            self.task_nav_buttons[name] = btn

        # 3. 建立各個視圖 (初始隱藏，掛載在 content_container 下)
        
        # Waiting View
        self.view_waiting = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        self.lbl_waiting_empty = ctk.CTkLabel(self.view_waiting, text="目前沒有等待中的任務", text_color="gray", font=self.font_text)
        self.lbl_waiting_empty.pack(pady=20)
        
        # Active View
        self.view_active = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        self.lbl_active_empty = ctk.CTkLabel(self.view_active, text="目前沒有執行中的任務", text_color="gray", font=self.font_text)
        self.lbl_active_empty.pack(pady=20)

        # Finished View
        self.view_finished = ctk.CTkScrollableFrame(self.task_content_container, fg_color="transparent")
        self.lbl_finished_empty = ctk.CTkLabel(self.view_finished, text="目前沒有已完成的紀錄", text_color="gray", font=self.font_text)
        self.lbl_finished_empty.pack(pady=20)
        
        self.btn_clear_history = ctk.CTkButton(self.tab_tasks, text="清除歷史紀錄", fg_color="gray", font=self.font_btn, command=self.clear_history)

        # 創建右側欄的「清除紀錄」按鈕 (初始隱藏)
        self.btn_clear_history_in_bar = ctk.CTkButton(self.task_right_bar, text="清除紀錄", fg_color="gray", font=self.font_small, command=self.clear_history)

        # 為了相容舊代碼 (segmented button 變數)
        self.task_segmented = type('obj', (object,), {'set': self.switch_task_view, 'get': lambda: self.current_task_view})
        self.current_task_view = "進行中" 
        
        # 初始顯示
        self.switch_task_view("進行中")

    def switch_task_view(self, value):
        self.current_task_view = value
        
        # 1. 更新按鈕樣式 (Highlight 當前選中)
        for name, btn in self.task_nav_buttons.items():
            if name == value:
                btn.configure(fg_color=("gray85", "gray20"), text_color=("#1F6AA5", "#3B8ED0")) # Highlight
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # 2. 切換內容顯示
        self.view_waiting.pack_forget()
        self.view_active.pack_forget()
        self.view_finished.pack_forget()
        self.btn_clear_history.place_forget() 
        self.btn_clear_history_in_bar.pack_forget()

        if value == "等待中":
            self.view_waiting.pack(fill="both", expand=True)
        elif value == "進行中":
            self.view_active.pack(fill="both", expand=True)
        elif value == "已完成":
            self.view_finished.pack(fill="both", expand=True)
            # 顯示右側欄底部的清除按鈕
            self.btn_clear_history_in_bar.pack(side="bottom", pady=20, padx=5)

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

    def create_active_task_widget(self, task_id, config, initial_status="準備中..."):
        row = ctk.CTkFrame(self.view_active)
        row.pack(fill="x", pady=5, padx=5)
        
        self.lbl_active_empty.pack_forget()
        self.active_task_widgets[task_id] = {'frame': row}

        # Info
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        
        # Determine Title (Priority: Filename > Default Title > URL)
        title = config.get('filename')
        if not title: title = config.get('default_title')
        if not title or title == "尚未分析": title = config.get('url')
        
        if len(title) > 50: title = title[:47] + "..."
        
        lbl_title = ctk.CTkLabel(info_frame, text=title, font=("Microsoft JhengHei UI", 12, "bold"), anchor="w")
        lbl_title.pack(fill="x")
        self.active_task_widgets[task_id]['title_label'] = lbl_title
        
        # URL Label
        url_text = config.get('url', '')
        if url_text and url_text != title:
            if len(url_text) > 60: url_text_disp = url_text[:57] + "..."
            else: url_text_disp = url_text
            
            lbl_url = ctk.CTkLabel(info_frame, text=url_text_disp, text_color="gray", font=("Consolas", 10), anchor="w")
            lbl_url.pack(fill="x")
        
        # Status & Progress Container
        status_frame = ctk.CTkFrame(row, fg_color="transparent")
        status_frame.pack(side="right", padx=10)
        
        # Status Text (Green)
        # Use a nice vibrant green for dark mode, maybe a bit darker for light mode if supported, 
        # but #24A36C is a good standard "Success/Active" green.
        lbl_stat = ctk.CTkLabel(status_frame, text=initial_status, font=self.font_text, width=120, anchor="e", text_color="#24A36C")
        lbl_stat.pack(side="top", anchor="e")
        self.active_task_widgets[task_id]['status_label'] = lbl_stat
        
        prog = ctk.CTkProgressBar(status_frame, width=150, height=10)
        prog.set(0)
        prog.pack(side="top", pady=5)
        self.active_task_widgets[task_id]['progress_bar'] = prog
        
        # Speed & ETA (Green)
        meta_lbl = ctk.CTkLabel(status_frame, text="-- MB/s | --:--", font=self.font_small, text_color="#24A36C")
        meta_lbl.pack(side="top", anchor="e")
        self.active_task_widgets[task_id]['meta_label'] = meta_lbl
        
        # Cancel Button
        btn_cancel = ctk.CTkButton(row, text="✕", width=30, height=30, fg_color="transparent", text_color="red", hover_color="#500000",
                                   command=lambda: self.cancel_task(task_id))
        btn_cancel.pack(side="right", padx=5)
        
        # Double-click to Pause/Resume
        def on_double_click(event):
            self.toggle_pause_task(task_id)
            
        row.bind("<Double-Button-1>", on_double_click)
        info_frame.bind("<Double-Button-1>", on_double_click)
        for child in info_frame.winfo_children():
            child.bind("<Double-Button-1>", on_double_click)
        
        # 暫存上次更新時間 (避免 UI 更新太頻繁)
        self.task_last_update_time[task_id] = 0

    def remove_active_task_widget(self, task_id):
        if task_id in self.active_task_widgets:
            frame = self.active_task_widgets[task_id]['frame']
            frame.destroy()
            del self.active_task_widgets[task_id]
            
            if not self.active_task_widgets:
                self.lbl_active_empty.pack(pady=20)

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
            if widget != self.lbl_finished_empty:
                widget.destroy()
        self.history_data = [] 
        self.lbl_finished_empty.pack(pady=20)

    def add_history_item(self, config, success, msg):
        if not hasattr(self, 'history_data'): self.history_data = []
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
