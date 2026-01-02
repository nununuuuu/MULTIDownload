import customtkinter as ctk
import sys

def setup_custom_titlebar(self):
    """建立自定義標題列"""
    # [Theme] 設定標題列背景色：(淺色模式, 深色模式)

    # --- 移除原生標題列 (Native Frameless Strategy) ---
    def apply_native_frameless():
        import sys
        if sys.platform == "win32":
            try:
                # 1. 確保 OverrideRedirect 為 False (標準視窗模式)
                self.overrideredirect(False)
                
                # 2. 定義 Windows API 常數
                GWL_STYLE = -16
                WS_CAPTION = 0x00C00000  # 標題列
                WS_THICKFRAME = 0x00040000 # 可調整大小的邊框 (保留此項以允許縮放)
                
                import ctypes
                from ctypes import windll
                
                def _remove_caption():
                    hwnd = windll.user32.GetParent(self.winfo_id())
                    if not hwnd: hwnd = self.winfo_id()
                    
                    # 取得當前樣式
                    old_style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
                    
                    # 移除標題列 (Caption) 但保留邊框 (ThickFrame) 以供縮放
                    # 這樣系統仍視其為標準視窗，但沒有上方白條
                    new_style = old_style & ~WS_CAPTION
                    
                    windll.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                    
                    # 強制刷新樣式
                    SWP_NOZORDER = 0x0004
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    SWP_FRAMECHANGED = 0x0020
                    SWP_SHOWWINDOW = 0x0040
                    
                    windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                              SWP_NOZORDER | SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                
                # 在視窗建立後執行 (延遲確保 HWND 準備好)
                self.after(100, _remove_caption)
                
                # 綁定 Map 事件以防樣式跑掉 (但只執行一次即可，比較安全)
                self._frameless_applied = False
                def on_map(e):
                    if e.widget == self and not self._frameless_applied:
                        self._frameless_applied = True
                        self.after(50, _remove_caption)
                
                self.bind("<Map>", on_map, add="+")
                
            except Exception as e:
                print(f"Native Frameless Error: {e}")

    # 執行新策略
    apply_native_frameless()
    
    # [UI] 標題列 UI
    self.title_bar_frame = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=("gray90", "#2B2B2B"))
    self.title_bar_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    self.title_bar_frame.grid_propagate(False) # 固定高度
    
    # 應用程式圖示
    try:
        from PIL import Image
        import os
        import sys
        
        # 使用與窗口圖標相同的路徑邏輯
        icon_path = None
        if hasattr(sys, '_MEIPASS'):
            icon_candidates = [
                os.path.join(sys._MEIPASS, "icon", "1.ico"),
                os.path.join(sys._MEIPASS, "1.ico")
            ]
        else:
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_candidates = [
                os.path.join(exe_dir, "icon", "1.ico"),
                os.path.join(exe_dir, "1.ico"),
                os.path.join(os.path.dirname(__file__), "..", "icon", "1.ico")
            ]
        
        for path in icon_candidates:
            if os.path.exists(path):
                icon_path = path
                break
        
        if icon_path:
            icon_image = Image.open(icon_path)
            icon_image = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
            icon_photo = ctk.CTkImage(light_image=icon_image, dark_image=icon_image, size=(16, 16))
            
            lbl_icon = ctk.CTkLabel(self.title_bar_frame, image=icon_photo, text="")
            lbl_icon.pack(side="left", padx=(8, 5))
    except Exception as e:
        print(f"Icon Load Error: {e}")
    
    # 標題文字
    self.lbl_title = ctk.CTkLabel(
        self.title_bar_frame, 
        text=f"MULTIDownload", 
        font=("Microsoft JhengHei UI", 11, "bold"), 
        text_color=("gray20", "gray80")
    )
    self.lbl_title.pack(side="left", padx=(0, 15))
    

    def move_window(event):
        try:
            from ctypes import windll
            hwnd = windll.user32.GetParent(self.winfo_id())
            windll.user32.ReleaseCapture()
            windll.user32.PostMessageW(hwnd, 0xA1, 2, 0)
        except Exception as e:
            print(f"Drag Error: {e}")

    # 綁定 Press 事件即可，不需要 Motion logic
    self.lbl_title.bind("<Button-1>", move_window)
    self.title_bar_frame.bind("<Button-1>", move_window)
    
    # --- 右側按鈕區 ---
    btn_frame = ctk.CTkFrame(self.title_bar_frame, fg_color="transparent")
    btn_frame.pack(side="right", padx=0, fill="y")
    
    # 1. Pin Button
    self.is_pinned = False
    def toggle_pin():
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        if self.is_pinned:
            self.btn_pin_tb.configure(text_color="#0078D4") 
        else:
            self.btn_pin_tb.configure(text_color=("gray60", "gray70"))
        if hasattr(self, 'var_always_on_top'):
            self.var_always_on_top.set(self.is_pinned)

    self.btn_pin_tb = ctk.CTkButton(
        btn_frame, text="🖈", width=40, height=32, corner_radius=0,
        fg_color="transparent", text_color=("gray60", "gray70"), hover_color=("gray80", "#3A3A3A"),
        font=("Microsoft JhengHei UI", 18, "bold"), command=toggle_pin
    )
    self.btn_pin_tb.pack(side="left")
    
    # 2. Minimize
    def minimize():
        """最小化（標準方式）"""
        try:
            # Native Frameless 下，直接使用標準 iconify 即可
            self.iconify() 
        except Exception as e:
            print(f"Minimize Error: {e}")
        
    btn_min = ctk.CTkButton(
        btn_frame, text="─", width=45, height=30, corner_radius=0,
        fg_color="transparent", text_color=("gray20", "gray80"), hover_color=("gray80", "#3A3A3A"),
        font=("Microsoft JhengHei UI", 12, "bold"), command=minimize
    )
    btn_min.pack(side="left")
    
    # 2.5 Maximize (標準視窗最大化)
    self.is_maximized = False
    def toggle_maximize():
        """最大化/還原（先隱藏避免看到黑色重繪）"""
        def do_maximize():
            if not self.is_maximized:
                try:
                    self.state('zoomed') 
                except:
                    screen_width = self.winfo_screenwidth()
                    screen_height = self.winfo_screenheight()
                    self.geometry(f"{screen_width}x{screen_height}+0+0")
                
                self.is_maximized = True
                btn_max.configure(text="❐") # Restore
            else:
                try:
                    self.state('normal') 
                except: pass
                
                self.is_maximized = False
                btn_max.configure(text="◻") # Maximize
            
            # 完成狀態切換後，需要充足時間確保渲染完全完成
            def show_after_render():
                try:
                    # 多次強制渲染以確保所有內容都已繪製
                    self.update_idletasks()
                    self.update()
                    
                    # 再次確認並開始淡入
                    def start_fade_in():
                        self.update_idletasks()
                        if hasattr(self, '_fade_in_window'):
                            self._fade_in_window(alpha=0.0)
                        else:
                            self.attributes("-alpha", 1.0)
                    
                    self.after(50, start_fade_in)
                except:
                    pass
                finally:
                    # 動畫完成後清除標記
                    self.after(250, lambda: setattr(self, '_is_maximizing', False))
            
            # 增加延遲以確保視窗大小調整完全完成
            self.after(150, show_after_render)
        
        # 設置標記，告訴 _handle_window_restore 不要干預
        self._is_maximizing = True
        
        # 先設置透明，避免看到黑色背景
        try:
            self.attributes("-alpha", 0.0)
        except:
            pass
        
        # 延遲一點再執行最大化，讓透明度生效
        self.after(10, do_maximize)

    btn_max = ctk.CTkButton(
        btn_frame, text="□", width=45, height=32, corner_radius=0,
        fg_color="transparent", text_color=("gray20", "gray80"), hover_color=("gray80", "#3A3A3A"),
        font=("Microsoft JhengHei UI", 12, "bold"), command=toggle_maximize
    )
    btn_max.pack(side="left")

    
    # 3. Close
    def close_app():
        if hasattr(self, 'on_closing'):
            self.on_closing()
        else:
            self.destroy()
            sys.exit(0)
        
    btn_close = ctk.CTkButton(
        btn_frame, text="✕", width=45, height=32, corner_radius=0,
        fg_color="transparent", text_color=("gray20", "gray80"), hover_color="#E81123",
        font=("Microsoft JhengHei UI", 12), command=close_app
    )
    btn_close.pack(side="left")

def force_taskbar_icon(self):
    """強制在工作列顯示圖示 (解決 overrideredirect 問題)"""
    try:
        import ctypes
        from ctypes import windll
        
        # 1. Set App ID
        myappid = 'mycompany.multidownload.app.2.0'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        # 2. Modify Window Style
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        
        hwnd = windll.user32.GetParent(self.winfo_id())
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception as e:
        print(f"Taskbar Icon Error: {e}")

from ui.tooltip import CTkToolTip
