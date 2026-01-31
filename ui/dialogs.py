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
            
        # 基本驗證：檢查是否包含 cookies.txt 的典型格式
        # (Netscape HTTP Cookie File 格式通常以 # 開頭的註解或網域開始)
        lines = content.split('\n')
        valid_lines = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # cookies.txt 格式：domain, flag, path, secure, expiry, name, value (tab 分隔)
            parts = line.split('\t')
            if len(parts) >= 6:
                valid_lines += 1
                
        if valid_lines == 0:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "格式警告", 
                "此內容可能不是有效的 cookies.txt 格式。\n\n"
                "是否仍要儲存？"
            ):
                return
        
        self.result = content
        self.destroy()
