import customtkinter as ctk
import sys

def setup_custom_titlebar(self):
    """建立自定義標題列"""
    # [Theme] 設定標題列背景色：(淺色模式, 深色模式)

    # --- 嘗試移除原生標題列並應用自定義樣式 (Windows Only) ---
    def apply_frameless_style():
        if sys.platform == "win32":
            try:
                # [Important] 為了保留原生最小化動畫與 DWM 特性，必須設為 False
                self.overrideredirect(False)
                
                from ctypes import windll, byref, c_int, sizeof
                hwnd = windll.user32.GetParent(self.winfo_id())
                
                # 1. 去除標題列 (WS_CAPTION)
                GWL_STYLE = -16
                WS_CAPTION = 0x00C00000
                WS_SYSMENU = 0x00080000
                
                style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
                
                # [Animation Fix] 為了找回原生的「縮放彈出」動畫，必須保留這些樣式
                # WS_SYSMENU + WS_MINIMIZEBOX/MAXIMIZEBOX 是觸發 Windows DWM 動畫的關鍵
                WS_SYSMENU = 0x00080000
                WS_MINIMIZEBOX = 0x00020000
                WS_MAXIMIZEBOX = 0x00010000
                WS_POPUP = 0x80000000 # [Animation Fix] 加上 POPUP 屬性通常能恢復無標題列視窗的動畫
                
                # 移除標題列(WS_CAPTION) 但強制加回動畫控制屬性 與 POPUP
                new_style = (style & ~WS_CAPTION) | WS_POPUP | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
                
                windll.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                
                # 3. 修正頂部白條：啟用 DWM 深色模式 (Immersive Dark Mode)
                # 這會將殘留的視窗邊框渲染為深色
                try:
                    from ctypes import c_int, byref, sizeof, Structure
                    
                    class MARGINS(Structure):
                        _fields_ = [("cxLeftWidth", c_int),
                                    ("cxRightWidth", c_int),
                                    ("cyTopHeight", c_int),
                                    ("cyBottomHeight", c_int)]
                                    
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    DWMWA_BORDER_COLOR = 34    # [New] 控制視窗周圍邊框顏色
                    DWMWA_CAPTION_COLOR = 35   # 控制頂部標題列顏色
                    
                    # 偵測當前主題模式
                    mode = ctk.get_appearance_mode()
                    
                    if mode == "Light":
                        use_dark_mode = 0
                        # gray90 (#E5E5E5) -> 0x00E5E5E5
                        color = 0x00E5E5E5
                    else:
                        use_dark_mode = 1
                        # #2B2B2B -> 0x002B2B2B (RGB和BGR相同)
                        color = 0x002B2B2B
                    
                    # 1. 設定 DWM 深色/淺色模式優先權
                    windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(c_int(use_dark_mode)), sizeof(c_int))
                    
                    # 2. [Color Fix] 指定標題列區域顏色
                    windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(c_int(color)), sizeof(c_int))

                    # 3. [Border Fix] 指定視窗邊框顏色 (讓周圍那圈細線也變色)
                    windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, byref(c_int(color)), sizeof(c_int))

                    # [Critical] 擴展邊框至原來標題列的位置
                    # 配合上述顏色修正，這 1px 邊框將與標題列融為一體
                    margins = MARGINS(0, 0, 1, 0) 
                    windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))
                    
                except Exception as e:
                    print(f"DWM Effect Error: {e}")

                # 2. 強制刷新
                windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27) # SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOMOVE | SWP_NOSIZE
                
                # 3. 確保任務列顯示圖示
                try:
                    GWL_EXSTYLE = -20
                    WS_EX_APPWINDOW = 0x00040000
                    WS_EX_TOOLWINDOW = 0x00000080
                    
                    ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    ex_style = ex_style & ~WS_EX_TOOLWINDOW  # 移除工具視窗樣式
                    ex_style = ex_style | WS_EX_APPWINDOW     # 強制任務列圖示
                    windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
                except Exception as e:
                    print(f"Taskbar Icon Error: {e}")
                
            except Exception as e:
                print(f"Apply Style Error: {e}")
                self.overrideredirect(True) # Fallback

    # 延遲執行樣式修改，確保視窗已建立並覆蓋可能的重置
    self.after(200, apply_frameless_style)

    
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
