import customtkinter as ctk
import sys

def setup_custom_titlebar(self):
    """建立自定義標題列"""
    # [Theme] 設定標題列背景色：(淺色模式, 深色模式)

    # --- 移除原生標題列 (使用無邊框模式) ---
    def apply_frameless_style():
        if sys.platform == "win32":
            try:
                # 1. 啟用無邊框模式 (這會直接移除標題列)
                self.overrideredirect(True)
                
                # 2. 關於工作列圖示 (overrideredirect=True 會導致從工作列消失)
                # 必須重設 GWL_EXSTYLE 為 WS_EX_APPWINDOW
                import ctypes
                from ctypes import windll
                
                # 讓 Windows 知道這是一個獨立的 App
                myappid = 'mycompany.multidownload.app.2.0'
                try:
                    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except: pass

                def _force_icon():
                    try:
                        hwnd = windll.user32.GetParent(self.winfo_id())
                        if not hwnd: hwnd = self.winfo_id() # Fallback
                        
                        # A. 處理延伸樣式 (ExStyle) - 確保顯示在工作列
                        GWL_EXSTYLE = -20
                        WS_EX_APPWINDOW = 0x00040000
                        WS_EX_TOOLWINDOW = 0x00000080
                        
                        ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                        ex_style = (ex_style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

                        # B. 處理基本樣式 (Style) - 確保工作列點擊有反應 (縮小/還原)
                        # 雖然是無邊框，但必須騙 Windows 說我們有最小化按鈕
                        GWL_STYLE = -16
                        WS_SYSMENU = 0x00080000
                        WS_MINIMIZEBOX = 0x00020000
                        
                        style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
                        style = style | WS_SYSMENU | WS_MINIMIZEBOX
                        windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
                        
                        # C. 強制刷新
                        # SWP_NOSIZE|SWP_NOMOVE|SWP_NOZORDER|SWP_FRAMECHANGED
                        windll.user32.SetWindowPos(hwnd, 0, 0,0,0,0, 0x0001|0x0002|0x0004|0x0020)
                    except Exception as e:
                        print(f"Force Icon Error: {e}")

                # 延遲執行，確保視窗建立完成
                self.after(200, _force_icon)
                
            except Exception as e:
                print(f"Apply Frameless Error: {e}")

    # 延遲執行
    self.after(100, apply_frameless_style)

    
    # [UI] 標題列 UI (跟之前一樣，放在 Row 0)
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
        """最小化（恢復時會有淡入動畫）"""
        try:
            self.iconify()
        except:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6)
        
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
