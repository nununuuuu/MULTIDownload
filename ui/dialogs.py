import customtkinter as ctk

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
        pass # To be overridden or bound? Actually the logic is:
        # We need to access self.vars here.
        selected_indices = [idx for idx, var in self.vars.items() if var.get()]
        if not selected_indices:
             # We need messagebox. Imported locally?
             from tkinter import messagebox
             messagebox.showwarning("警告", "請至少選擇一個項目")
             return
        self.result = selected_indices
        self.destroy()

class CookiePasteDialog(ctk.CTkToplevel):
    """對話框：讓使用者直接貼上 cookies.txt 內容"""
    def __init__(self, parent, current_content=""):
        super().__init__(parent)
        self.title("貼上 Cookie 內容")
        self.geometry("600x500")
        self.result = None
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # 置中視窗
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 300
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 250
        self.geometry(f"+{x}+{y}")
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            header, 
            text="🍪 貼上 Cookie 內容", 
            font=("Microsoft JhengHei UI", 16, "bold")
        ).pack(side="left")
        
        # Description
        desc_frame = ctk.CTkFrame(self, fg_color=("gray95", "#2B2B2B"), corner_radius=8)
        desc_frame.pack(fill="x", padx=20, pady=10)
        
        desc_text = (
            "請將 cookies.txt 的完整內容貼到下方文字框中。\n\n"
            "取得方式：\n"
            "1. 安裝瀏覽器擴充「Get cookies.txt LOCALLY」\n"
            "2. 到 YouTube 首頁並登入帳號\n"
            "3. 點擊擴充圖示 → Export → 複製全部內容"
        )
        ctk.CTkLabel(
            desc_frame, 
            text=desc_text, 
            font=("Microsoft JhengHei UI", 12),
            text_color=("gray40", "gray70"),
            justify="left",
            wraplength=540
        ).pack(padx=15, pady=12, anchor="w")
        
        # Text Area
        self.textbox = ctk.CTkTextbox(
            self, 
            font=("Consolas", 12),
            fg_color=("white", "#1E1E1E"),
            border_width=1,
            border_color=("gray70", "gray40"),
            wrap="none"
        )
        self.textbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 載入現有內容
        if current_content:
            self.textbox.insert("1.0", current_content)
        
        # Button Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        # Clear Button
        ctk.CTkButton(
            btn_frame, 
            text="清空", 
            width=80, 
            height=35,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray50"),
            text_color=("gray30", "gray80"),
            hover_color=("gray90", "#3A3A3A"),
            command=self.clear_content
        ).pack(side="left")
        
        # Paste from Clipboard Button
        ctk.CTkButton(
            btn_frame, 
            text="📋 從剪貼簿貼上", 
            width=130, 
            height=35,
            fg_color=("gray85", "#3A3A3A"),
            text_color=("gray20", "gray90"),
            hover_color=("gray75", "#4A4A4A"),
            command=self.paste_from_clipboard
        ).pack(side="left", padx=10)
        
        # Cancel Button
        ctk.CTkButton(
            btn_frame, 
            text="取消", 
            width=80, 
            height=35,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray50"),
            text_color=("gray30", "gray80"),
            hover_color=("gray90", "#3A3A3A"),
            command=self.destroy
        ).pack(side="right")
        
        # Confirm Button
        ctk.CTkButton(
            btn_frame, 
            text="確定儲存", 
            width=100, 
            height=35,
            fg_color="#01814A",
            hover_color="#006030",
            command=self.on_confirm
        ).pack(side="right", padx=10)
        
        # Focus on textbox
        self.after(100, self.textbox.focus_set)
        
    def clear_content(self):
        self.textbox.delete("1.0", "end")
        
    def paste_from_clipboard(self):
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content:
                self.textbox.delete("1.0", "end")
                self.textbox.insert("1.0", clipboard_content)
        except:
            pass
        
    def on_confirm(self):
        content = self.textbox.get("1.0", "end").strip()
        
        if not content:
            from tkinter import messagebox
            messagebox.showwarning("警告", "Cookie 內容不能為空！")
            return
        
        # 格式識別
        detected_format = self._detect_cookie_format(content)
        
        # 如果識別為「不支援」的格式，顯示提示
        if detected_format == "unsupported":
            from tkinter import messagebox
            messagebox.showinfo(
                "格式識別結果", 
                "⚠️ 無法識別 Cookie 格式\n\n"
                "【支援的格式】\n"
                "1. Netscape 格式 (cookies.txt)\n"
                "   - 由「Get cookies.txt LOCALLY」擴充匯出\n"
                "   - 每行以 Tab 分隔，包含 domain、path、name、value 等欄位\n\n"
                "2. Header String 格式\n"
                "   - 由瀏覽器 F12 開發者工具複製\n"
                "   - 格式：NAME=value;NAME2=value2;...\n\n"
                "【建議】\n"
                "使用 Chrome/Edge 擴充「Get cookies.txt LOCALLY」\n"
                "點擊 Export → Copy to clipboard，然後貼上。"
            )
            return
            
        # 顯示識別結果並進行必要的轉換
        format_names = {
            "netscape": "Netscape 格式 ✓ (完美) ",
            "header_string": "Header String 格式 → 正在轉換為 Netscape 格式..."
        }
        
        # 記錄到 log (透過 parent)
        if hasattr(self.master, 'log'):
            self.master.log(f"[Cookie] 識別格式：{format_names.get(detected_format, detected_format)}")
        
        # 如果是 Header String 格式，進行轉換
        if detected_format == "header_string":
            content = self._convert_header_to_netscape(content)
            if hasattr(self.master, 'log'):
                cookie_count = len([l for l in content.split('\n') if l.strip() and not l.startswith('#')])
                self.master.log(f"[Cookie] 轉換完成！共 {cookie_count} 個 Cookie")
        
        self.result = content
        self.destroy()
    
    def _convert_header_to_netscape(self, content):
        """將 HTTP Header String 格式轉換為 Netscape 格式"""
        import time
        content = content.strip()
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
            'NID', 'LOGIN_INFO'
        }
        
        # 分割各個 cookie
        cookies = content.split(";")
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
            
            # 判斷 secure flag (以 __Secure- 開頭的 cookie 需要 secure)
            secure = "TRUE" if name.startswith("__Secure-") else "FALSE"
            
            # 產生 Netscape 格式行
            # 格式: domain	flag	path	secure	expiration	name	value
            line = f".youtube.com\tTRUE\t/\t{secure}\t{expire_ts}\t{name}\t{value}"
            netscape_lines.append(line)
            
            # 若為 Google 認證 cookie，同時寫入 .google.com 域名
            if name in google_auth_cookies:
                line_google = f".google.com\tTRUE\t/\t{secure}\t{expire_ts}\t{name}\t{value}"
                netscape_lines.append(line_google)
        
        return "\n".join(netscape_lines)
    
    def _detect_cookie_format(self, content):
        """識別 Cookie 內容的格式"""
        content = content.strip()
        lines = content.split('\n')
        
        # 檢查 Netscape 格式
        # 特徵：以 # 開頭的註解，或 Tab 分隔的行（至少 6 個欄位）
        netscape_lines = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 6:
                netscape_lines += 1
        
        if netscape_lines > 0:
            return "netscape"
        
        # 檢查 Header String 格式
        # 特徵：NAME=value;NAME2=value2... (無換行，有多個 ; 和 =)
        if len(lines) == 1 or (len(lines) <= 3 and all(';' in l or '=' in l for l in lines if l.strip())):
            first_line = lines[0].strip()
            if '=' in first_line and ';' in first_line:
                return "header_string"
            # 單個 cookie 的情況
            if '=' in first_line and first_line.count('=') >= 1:
                return "header_string"
        
        return "unsupported"


class SearchResultDialog(ctk.CTkToplevel):
    """YouTube + Bilibili 搜尋結果選擇彈窗"""
    def __init__(self, parent, query, results):
        super().__init__(parent)
        self.title(f"搜尋結果：{query}")
        # self.geometry("620x650") # Removed to avoid conflict
        self.result = None  # 選中的 URL
        self.all_results = results  # 儲存完整結果
        self.current_filter = "all"  # 當前篩選
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # 置中視窗
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 375
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 360
        self.geometry(f"+{x}+{y}")
        self.geometry("750x680")
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            header, 
            text=f"🔍 搜尋：{query}", 
            font=("Microsoft JhengHei UI", 16, "bold")
        ).pack(side="left")
        
        # 結果計數標籤 (會動態更新)
        self.lbl_count = ctk.CTkLabel(
            header, 
            text=f"共 {len(results)} 筆結果", 
            font=("Microsoft JhengHei UI", 12),
            text_color="gray"
        )
        self.lbl_count.pack(side="right")
        
        # 篩選與排序區
        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # 左側：平台篩選按鈕
        filter_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        filter_frame.pack(side="left")
        
        # 計算各平台數量
        yt_count = len([r for r in results if r.get('platform') == 'youtube'])
        bili_count = len([r for r in results if r.get('platform') == 'bilibili'])
        
        self.filter_btns = {}
        filter_options = [
            ("all", f"全部 ({len(results)})"),
            ("youtube", f"YouTube ({yt_count})"),
            ("bilibili", f"Bilibili ({bili_count})")
        ]
        
        for code, text in filter_options:
            btn = ctk.CTkButton(
                filter_frame,
                text=text,
                width=110,
                height=30,
                corner_radius=15,
                font=("Microsoft JhengHei UI", 11),
                fg_color=("#1F6AA5", "#1F6AA5") if code == "all" else "transparent",
                text_color="white" if code == "all" else ("gray50", "gray70"),
                hover_color=("#144870", "#144870"),
                border_width=1 if code != "all" else 0,
                border_color=("gray60", "gray50"),
                command=lambda c=code: self._on_filter_change(c)
            )
            btn.pack(side="left", padx=2)
            self.filter_btns[code] = btn
        
        # 右側：排序選項
        sort_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        sort_frame.pack(side="right")
        
        ctk.CTkLabel(sort_frame, text="排序:", font=("Microsoft JhengHei UI", 11), text_color="gray").pack(side="left", padx=(0, 5))
        
        self.sort_var = ctk.StringVar(value="views_desc")
        self.sort_menu = ctk.CTkOptionMenu(
            sort_frame,
            variable=self.sort_var,
            values=["觀看次數↓", "觀看次數↑", "上傳時間↓", "上傳時間↑"],
            width=150,
            height=28,
            font=("Microsoft JhengHei UI", 11),
            dropdown_font=("Microsoft JhengHei UI", 11),
            dynamic_resizing=False,
            command=self._on_sort_change
        )
        self.sort_menu.pack(side="left")
        self.sort_menu.set("觀看次數↓")
        
        # 結果列表容器
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=10)
        
        # 渲染結果 (預設按觀看數降序)
        self._apply_sort_and_render()
        
        # 底部按鈕
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkButton(
            btn_frame, 
            text="取消", 
            width=100, 
            height=35,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray50"),
            text_color=("gray30", "gray80"),
            hover_color=("gray90", "#3A3A3A"),
            command=self.destroy
        ).pack(side="right")

    def _on_filter_change(self, filter_code):
        """切換平台篩選"""
        self.current_filter = filter_code
        
        # 更新按鈕樣式
        for code, btn in self.filter_btns.items():
            if code == filter_code:
                btn.configure(
                    fg_color=("#1F6AA5", "#1F6AA5"),
                    text_color="white",
                    border_width=0
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray50", "gray70"),
                    border_width=1
                )
        
        # 過濾結果
        if filter_code == "all":
            filtered = self.all_results
        else:
            filtered = [r for r in self.all_results if r.get('platform') == filter_code]
        
        # 更新計數
        self.lbl_count.configure(text=f"共 {len(filtered)} 筆結果")
        
        # 重新排序並渲染
        self._apply_sort_and_render()

    def _on_sort_change(self, value):
        """切換排序方式"""
        self._apply_sort_and_render()

    def _apply_sort_and_render(self):
        """根據當前篩選和排序設定渲染結果"""
        # 1. 先進行平台篩選
        if self.current_filter == "all":
            filtered = self.all_results.copy()
        else:
            filtered = [r for r in self.all_results if r.get('platform') == self.current_filter]
        
        # 2. 進行排序
        sort_value = self.sort_menu.get()
        reverse = "↓" in sort_value
        
        def get_view_count(item):
            vc = item.get('view_count')
            if vc is None:
                return 0
            if isinstance(vc, str):
                vc = vc.replace(',', '').replace('萬', '0000').replace('億', '00000000')
                try:
                    return int(float(vc))
                except:
                    return 0
            return int(vc)
        
        def get_upload_time(item):
            # 優先使用 timestamp，否則嘗試解析日期字串
            ts = item.get('timestamp') or item.get('upload_date') or item.get('pubdate') or 0
            if isinstance(ts, str):
                try:
                    # YYYYMMDD 格式
                    return int(ts.replace('-', '').replace('/', '')[:8])
                except:
                    return 0
            return int(ts) if ts else 0
        
        if "觀看" in sort_value:
            filtered.sort(key=get_view_count, reverse=reverse)
        elif "日期" in sort_value:
            filtered.sort(key=get_upload_time, reverse=reverse)
        
        # 3. 渲染
        self._render_results(filtered)

    def _render_results(self, results):
        """渲染結果列表"""
        # 清空現有內容
        for widget in self.scroll.winfo_children():
            widget.destroy()
        
        if not results:
            ctk.CTkLabel(
                self.scroll, 
                text="找不到相關影片，請嘗試其他關鍵字。", 
                text_color="gray",
                font=("Microsoft JhengHei UI", 14)
            ).pack(pady=50)
        else:
            for item in results:
                self._create_result_row(item)


    def _create_result_row(self, item):
        """建立單筆搜尋結果的 UI 列"""
        row = ctk.CTkFrame(
            self.scroll, 
            fg_color=("white", "#3A3A3A"), 
            corner_radius=10,
            cursor="hand2"
        )
        row.pack(fill="x", pady=5, padx=5)
        row.grid_columnconfigure(1, weight=1)
        
        # 儲存 URL 到 row 物件
        row.video_url = item.get('url')
        
        # 縮圖區域 (Placeholder)
        thumb_frame = ctk.CTkFrame(row, width=160, height=90, fg_color=("gray85", "gray25"), corner_radius=6)
        thumb_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        thumb_frame.grid_propagate(False)
        
        # 縮圖載入 (異步)
        thumb_url = item.get('thumbnail')
        if thumb_url:
            self._load_thumbnail_async(thumb_frame, thumb_url)
        else:
            ctk.CTkLabel(thumb_frame, text="🎬", font=("Segoe UI Emoji", 24), text_color="gray").place(relx=0.5, rely=0.5, anchor="center")
        
        # 標題
        title = item.get('title', '未知標題')
        if len(title) > 55:
            title = title[:53] + "..."
        
        lbl_title = ctk.CTkLabel(
            row, 
            text=title, 
            font=("Microsoft JhengHei UI", 13, "bold"),
            anchor="w",
            text_color=("gray10", "gray95")
        )
        lbl_title.grid(row=0, column=1, sticky="sw", padx=(0, 10), pady=(10, 0))
        
        # 頻道 + 時長 + 平台標籤
        platform = item.get('platform', 'youtube')
        platform_icon = "▶" if platform == 'youtube' else "📺"
        platform_color = "#FF0000" if platform == 'youtube' else "#00A1D6"
        
        meta_frame = ctk.CTkFrame(row, fg_color="transparent")
        meta_frame.grid(row=1, column=1, sticky="nw", padx=(0, 10), pady=(0, 10))
        
        # 平台標籤
        lbl_platform = ctk.CTkLabel(
            meta_frame, 
            text=platform_icon,
            font=("Segoe UI Emoji", 10),
            text_color=platform_color,
            width=16
        )
        lbl_platform.pack(side="left")
        
        meta = f"{item.get('uploader', '未知頻道')} • {item.get('duration', '--:--')}"
        lbl_meta = ctk.CTkLabel(
            meta_frame, 
            text=meta, 
            font=("Microsoft JhengHei UI", 11),
            anchor="w",
            text_color="gray"
        )
        lbl_meta.pack(side="left")
        
        # 綁定點擊事件
        def on_click(event, url=item.get('url')):
            self.result = url
            self.destroy()
        
        # 綁定到所有子元件
        for widget in [row, lbl_title, lbl_meta, thumb_frame, meta_frame, lbl_platform]:
            widget.bind("<Button-1>", on_click)
        
        # Hover 效果
        def on_enter(event):
            row.configure(fg_color=("gray90", "#4A4A4A"))
        def on_leave(event):
            row.configure(fg_color=("white", "#3A3A3A"))
        
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

    def _load_thumbnail_async(self, frame, url):
        """異步載入縮圖"""
        import threading
        
        def _load():
            try:
                import requests
                from PIL import Image
                from io import BytesIO
                
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    img = Image.open(BytesIO(resp.content))
                    img = img.resize((160, 90), Image.Resampling.LANCZOS)
                    
                    # 回到主線程更新 UI
                    def _update():
                        try:
                            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
                            lbl = ctk.CTkLabel(frame, image=ctk_img, text="")
                            lbl.place(relx=0.5, rely=0.5, anchor="center")
                            # 重新綁定點擊事件
                            lbl.bind("<Button-1>", lambda e: None)  # 將在父層處理
                        except:
                            pass
                    
                    self.after(0, _update)
            except:
                pass
        
        threading.Thread(target=_load, daemon=True).start()
