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
