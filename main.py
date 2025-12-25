import sys
import os
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from core import YtDlpCore
import threading
import uuid
import time 
import webbrowser
import json

# Refactored Imports
from constants import APP_VERSION, GITHUB_REPO, DEFAULT_APPEARANCE_MODE, CODE_TO_NAME
from ui.layout import AppLayoutMixin
from ui.tasks import TaskLayoutMixin
from ui.tooltip import CTkToolTip

ctk.set_default_color_theme("blue")

try:
    import yt_dlp
except ImportError:
    yt_dlp = None 

# 支援外部 Library 覆蓋 (保持原版邏輯)
if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

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

class App(ctk.CTk, AppLayoutMixin, TaskLayoutMixin):
    def __init__(self):
        super().__init__()
        self.title("MULTIDownload")
        self.geometry("900x780") 
        
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
        self.font_sidebar_icon = (self.font_family, 18, "bold") 
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

        # --- Layout Logic: 1 row, 2 cols (Static Sidebar | Content) ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, minsize=60) 
        self.grid_columnconfigure(1, weight=1)   

        # 1. Sidebar Frame (Static)
        self.sidebar_frame = ctk.CTkFrame(self, width=60, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # 2. Main Content Area
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_view.grid_rowconfigure(0, weight=1)     
        self.main_view.grid_rowconfigure(1, weight=0)      
        self.main_view.grid_columnconfigure(0, weight=1)

        # 3. Content Container
        self.frames = {}
        for name in ["Basic", "Format", "Sub", "Output", "Adv", "Tasks", "Log", "Settings", "About"]:
             frame = ctk.CTkFrame(self.main_view, corner_radius=10, fg_color=None)
             self.frames[name] = frame
        
        self.tab_basic = self.frames["Basic"]
        self.tab_format = self.frames["Format"]
        self.tab_sub = self.frames["Sub"]
        self.tab_output = self.frames["Output"]
        self.tab_adv = self.frames["Adv"]
        self.tab_tasks = self.frames["Tasks"]
        self.tab_log = self.frames["Log"]
        self.tab_settings = self.frames["Settings"]
        self.tab_about = self.frames["About"]

        self.history_data = [] 
        self.active_task_widgets = {}
        self.selected_playlist_data = [] 
        self.pending_playlist_info = None 
        
        # 4. Initialize UI (From Mixins)
        self.setup_sidebar()

        # 5. Setup Content UI (From Mixins)
        self.setup_tasks_ui() 
        self.setup_basic_ui()
        self.task_last_update_time = {}
        self.setup_format_ui()
        self.setup_subtitle_ui()
        self.setup_output_ui()
        self.setup_advanced_ui()
        self.setup_log_ui()
        self.setup_settings_ui()
        self.setup_about_ui()

        # --- 6. 建立底部控制區 (From Mixin) ---
        self.setup_bottom_controls()
        
        # Default view
        self.select_frame("Basic")
        
    def safe_open_path(self, path):
         if os.path.exists(path): os.startfile(path)
         else: messagebox.showerror("錯誤", f"找不到路徑:\n{path}")

    def on_fetch_info(self):
        url = self.entry_url.get().strip()
        if not url: return messagebox.showerror("錯誤", "請輸入網址")
        
        # Get UA & Cookie & Proxy safely
        ua = self.entry_ua.get().strip() if hasattr(self, 'entry_ua') else None
        proxy = self.entry_proxy.get().strip() if hasattr(self, 'entry_proxy') else None
        
        c_type = self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none'
        c_path = self.entry_cookie_path.get().strip()

        # Playlist Detection
        if "list=" in url:
            is_playlist = messagebox.askyesno("播放清單偵測", "偵測到此網址包含播放清單\n\n是否要下載『整張歌單』\n(選擇「否」將僅下載此影片)")
            self.var_playlist.set(is_playlist)
            
            if is_playlist:
                 self.show_toast("清單讀取中... ", duration=3000, color="#BEBEBE")
                 self.log(f"正在分析播放清單: {url}")
                 self.selected_playlist_data = []
                 threading.Thread(target=self._run_playlist_check, args=(url, c_type, c_path, ua, proxy), daemon=True).start()
                 return

        self.show_toast("正在分析字幕...", color="#BEBEBE")
        self.log(f"正在分析: {url}")
        threading.Thread(target=self._run_fetch, args=(url, c_type, c_path, ua, proxy), daemon=True).start()

    def _run_playlist_check(self, url, c_type, c_path, ua, proxy):
        # 快速分析清單 (不抓詳細字幕)
        info = self.core.fetch_playlist_info(url, cookie_type=c_type, cookie_path=c_path, user_agent=ua, proxy=proxy)
        
        def _update_pl_ui():
            if 'error' in info:
                self.show_toast("清單分析失敗", color="#FF2D2D")
                err_msg = info['error']
                self.log(f"清單錯誤: {err_msg}")
                
                if "核心載入失敗" in err_msg or "CORE_MISSING" in err_msg:
                    messagebox.showerror("核心遺失", "未安裝 yt-dlp 核心組件！\n無法進行分析或下載。\n\n請稍後在「設定」頁面點擊「檢查並更新」安裝。")
                    self.tab_view.set("設定")
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
                    messagebox.showinfo("清單模式", f"已讀取清單：{title}\n\n注意：此清單無法解析內容，將預設下載全部。")
        
        self.after(0, _update_pl_ui)

    def _run_fetch(self, url, c_type, c_path, ua, proxy):
        info = self.core.fetch_video_info(url, cookie_type=c_type, cookie_path=c_path, user_agent=ua, proxy=proxy)
        
        def _update_ui():
            if 'error' in info:
                self.show_toast("分析失敗", color="#FF2D2D")
                err_msg = info['error']
                self.log(f"{err_msg}")
                
                if "核心載入失敗" in err_msg or "CORE_MISSING" in err_msg:
                    messagebox.showerror("核心遺失", "未安裝 yt-dlp 核心組件！\n無法進行分析或下載。\n\n請稍後在「設定」頁面點擊「檢查並更新」安裝。")
                    self.tab_view.set("設定")
                    
                elif "Sign in" in err_msg: messagebox.showwarning("驗證失敗", "YouTube 拒絕連線。\n請到 [高級選項] 勾選瀏覽器後再試一次。")
            else:
                if info['subtitles']:
                    self.show_toast("分析完成 (有字幕)")
                else:
                    self.show_toast("分析完成 (無字幕)")
                
                self.log(f"已獲取資訊: {info['title']}")
                self.after(50, lambda: self.update_subtitles_ui(info['subtitles']))
        
        self.after(0, _update_ui)

    def get_config_from_ui(self):
        url = self.entry_url.get().strip()
        if not url: 
            messagebox.showwarning("提示", "網址不能為空")
            return None

        raw_path = self.entry_path.get().strip()
        final_save_path = raw_path if raw_path else app_path

        # Handle Format
        raw_format = self.combo_format.get() 
        selected_ext = raw_format.split(' ')[0]
        is_audio_only = selected_ext in ['mp3', 'm4a', 'wav', 'flac']

        # Handle Live Mode (Ensure var_live_mode exists)
        live_from_start = False
        if hasattr(self, 'var_live_mode'):
             live_from_start = (self.var_live_mode.get() == 'start')
        
        config = {
            'url': url,
            'save_path': final_save_path,
            'filename': self.entry_filename.get().strip(),
            'ext': selected_ext,
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
            'cookie_type': self.var_cookie_mode.get() if hasattr(self, 'var_cookie_mode') else 'none',
            'cookie_path': self.entry_cookie_path.get().strip(),
            'user_agent': self.entry_ua.get().strip() if hasattr(self, 'entry_ua') else None,
            'proxy': self.entry_proxy.get().strip() if hasattr(self, 'entry_proxy') else None,
            'is_live': False,
            'live_from_start': live_from_start,
            'embed_thumbnail': self.var_embed_thumb.get() if hasattr(self, 'var_embed_thumb') else True,
            'embed_subs': self.var_embed_subs.get() if hasattr(self, 'var_embed_subs') else True,
            'add_metadata': self.var_metadata.get() if hasattr(self, 'var_metadata') else True,
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
            
            self.select_frame("Tasks")
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
            info = core.fetch_video_info(config['url'], cookie_type=config['cookie_type'], cookie_path=config['cookie_path'], user_agent=config.get('user_agent'), proxy=config.get('proxy'))
            
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
        y = self.winfo_y() + 45
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
            
            self.select_frame("Tasks")
            self.task_segmented.set("進行中")
            self.switch_task_view("進行中")
            return

        # --- 一般排程邏輯 ---
        self.download_queue.append(config)
        self.log(f"已加入排程並開始: {config['url']}")
        self.update_queue_ui()
        self.check_queue() 
        
        # 提示切換
        self.select_frame("Tasks")
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

        if self.frames["Tasks"].winfo_ismapped() and self.task_segmented.get() != "進行中":
             self.task_segmented.set("進行中")
             self.switch_task_view("進行中")
        
        self.log(f"啟動排程任務: {config['url']}")
        
        def update_title_callback(real_title):
            if not config.get('filename'):
                self.active_queue_tasks[task_id]['config']['default_title'] = real_title
                config['default_title'] = real_title
                
                def _update_ui():
                    if task_id in self.active_task_widgets:
                        if len(real_title) > 50: real_title_disp = real_title[:47] + "..."
                        else: real_title_disp = real_title
                        
                        widgets = self.active_task_widgets[task_id]
                        if 'title_label' in widgets:
                            widgets['title_label'].configure(text=real_title_disp) 
                
                self.after(0, _update_ui)

        core.start_download_thread(
            config, 
            progress_callback=lambda p, m, s=None, e=None: self.update_progress(p, m, task_id, s, e), 
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

    def update_progress(self, percent, msg, task_id, speed=None, eta=None):
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
            self.update_task_widget(task_id, percent, msg, speed, eta)

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
                 self.update_task_widget(task_id, -1, "正在中止...")
             except: pass

        if task_id in self.active_queue_tasks:
             self.active_queue_tasks[task_id]['status'] = 'cancelled'
             try: 
                self.active_queue_tasks[task_id]['core'].stop_download()
             except: pass
        elif task_id in self.bg_tasks:
             self.stop_background_task(task_id)
             
    def stop_background_task(self, task_id):
        if task_id in self.bg_tasks:
            try: self.bg_tasks[task_id]['core'].stop_download()
            except: pass
            self.bg_tasks.pop(task_id)
            self.log(f"已手動停止背景任務: {task_id}")
            self.remove_active_task_widget(task_id)

    def check_for_updates(self):
        """檢查並自動更新 yt-dlp (針對 exe/lib 架構)"""
        self.btn_update_ytdlp.configure(state="disabled", text="檢查中...")
        
        def run_update():
            try:
                import json
                import urllib.request
                import zipfile
                from io import BytesIO
                
                url = "https://pypi.org/pypi/yt-dlp/json"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data['info']['version']
                
                if yt_dlp: current_version = yt_dlp.version.__version__
                else: current_version = "0.0.0" 
                
                def parse_version(v_str):
                    try: return tuple(map(int, v_str.split('.')))
                    except: return (0, 0, 0)

                if parse_version(latest_version) <= parse_version(current_version):
                    self.after(0, lambda: messagebox.showinfo("檢查更新", f"版本已為最新版本 ({current_version})"))
                    self.after(0, lambda: self.btn_update_ytdlp.configure(state="normal", text="檢查更新yt-dlp",hover_color="#555555"))
                    return

                should_update = [False]
                def ask_user():
                    should_update[0] = messagebox.askyesno("發現新版本", f"現有版本: {current_version}\n最新版本: {latest_version}\n\n是否立即下載並更新？")
                
                self.after(0, lambda: self.btn_update_ytdlp.configure(text=f"下載新版本 {latest_version}..."))

                download_url = None
                for file_info in data['urls']:
                    if file_info['packagetype'] == 'bdist_wheel':
                        download_url = file_info['url']
                        break
                
                if not download_url: raise Exception("找不到可用的更新檔案 (.whl)")

                if getattr(sys, 'frozen', False): base_path = os.path.dirname(sys.executable)
                else: base_path = os.path.dirname(os.path.abspath(__file__))
                    
                lib_dir = os.path.join(base_path, 'lib')
                if not os.path.exists(lib_dir): os.makedirs(lib_dir)

                with urllib.request.urlopen(download_url, timeout=60) as response:
                    whl_data = response.read()
                    
                with zipfile.ZipFile(BytesIO(whl_data)) as zip_ref:
                    for member in zip_ref.namelist():
                        if member.startswith('yt_dlp/'):
                            zip_ref.extract(member, lib_dir)
                
                def on_success():
                    messagebox.showinfo("更新成功", f"yt-dlp 已更新至 {latest_version}！\n\n點擊確定將自動重啟應用程式以生效。")
                    import subprocess
                    current_file = sys.executable if getattr(sys, 'frozen', False) else __file__
                    subprocess.Popen([sys.executable, current_file] if not getattr(sys, 'frozen', False) else [current_file])
                    os._exit(0)

                self.after(0, on_success)

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("更新失敗", f"更新錯誤: {err_msg}"))
                self.after(0, lambda: self.btn_update_ytdlp.configure(state="normal", text="檢查並更新yt-dlp"))

        threading.Thread(target=run_update, daemon=True).start()


    def check_app_update(self):
        """檢查 App 是否有新版本 (GitHub Releases)"""
        try:
            import requests
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            
            session = requests.Session()
            resp = session.get(api_url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "Unknown")
                
                if latest_tag != APP_VERSION:
                    download_url = ""
                    for asset in data.get("assets", []):
                        if asset["name"].endswith(".exe"):
                            download_url = asset["browser_download_url"]
                            break
                    
                    if download_url:
                        if tk.messagebox.askyesno("發現新版本", f"發現新版本 {latest_tag}！\n(目前版本: {APP_VERSION})\n\n是否立即更新並重啟？"):
                            self.perform_self_update(download_url)
                    else:
                         tk.messagebox.showwarning("無法更新", f"發現新版本 {latest_tag}，但在發布文件中找不到 .exe 檔。")
                else:
                    tk.messagebox.showinfo("檢查完成", f"目前已是最新版本 ({APP_VERSION})。")
            elif resp.status_code == 404:
                tk.messagebox.showerror("檢查失敗", "找不到發布版本 (GitHub Repo 未發布 Release 或設為私有)。")
            else:
                tk.messagebox.showerror("檢查失敗", f"無法連接伺服器 (Status: {resp.status_code})。")
            
        except Exception as e:
            tk.messagebox.showerror("檢查錯誤", f"檢查更新時發生錯誤:\n{str(e)}")

    def perform_self_update(self, download_url):
        try:
            import requests
            
            new_exe_name = "MULTIDownload_Update.exe"
            self.show_toast("系統更新", "正在下載新版本，請稍候...", icon_color="blue")
            self.update_idletasks()
            
            response = requests.get(download_url, stream=True)
            with open(new_exe_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.show_toast("系統更新", "下載完成，正在重啟...", icon_color="green")

            current_exe = os.path.basename(sys.executable)
            
            cmd_command = (
                f'timeout /t 2 /nobreak > NUL && '
                f'del /f /q "{current_exe}" && '
                f'move /y "{new_exe_name}" "{current_exe}" && '
                f'start "" "{current_exe}"'
            )
            
            subprocess.Popen(f'cmd /c "{cmd_command}"', shell=True)
            
            self.quit()
            sys.exit()
            
        except Exception as e:
            tk.messagebox.showerror("更新失敗", f"無法完成更新: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()