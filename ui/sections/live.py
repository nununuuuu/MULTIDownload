import customtkinter as ctk
from ui.tooltip import CTkToolTip

class LiveStreamMixin:
    """
    負責直播設定 (Live Tab) 的 UI 建構
    包括：智慧等待、錄製策略 (DVR)、定時停止
    """
    def setup_live_ui(self):
        self.tab_live = self.frames["Live"]
        
        # Grid Configuration
        self.tab_live.grid_columnconfigure(0, weight=1)
        self.tab_live.grid_rowconfigure(0, weight=1) 
        
        center_box = ctk.CTkFrame(self.tab_live, fg_color="transparent")
        center_box.grid(row=0, column=0, sticky="ew", padx=40)
        center_box.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(center_box, text="直播錄製設定 (Live Stream Settings)", font=(self.font_family, 18, "bold"), text_color=("gray20", "gray80")).pack(pady=(0, 25))

        # --- Helper for Cards (Standard Style) ---
        def create_live_card(parent, title, icon="⚙️"):
            card = ctk.CTkFrame(parent, fg_color=("gray95", "#454545"), corner_radius=15)
            card.pack(fill="x", pady=10)
            
            # Header
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(15, 10))
            
            # Icon & Title
            ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(header, text=title, font=(self.font_family, 16, "bold"), text_color=("gray20", "gray90")).pack(side="left")
            
            # Content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=(0, 20))
            return content

        # Init Variables
        if not hasattr(self, 'var_live_wait'): self.var_live_wait = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_live_from_start'): self.var_live_from_start = ctk.BooleanVar(value=True)
        if not hasattr(self, 'var_live_autostop'): self.var_live_autostop = ctk.BooleanVar(value=False)
        if not hasattr(self, 'var_live_stop_min'): self.var_live_stop_min = ctk.StringVar(value="60")

        # --- Card 1: 智慧等待 ---
        wait_content = create_live_card(center_box, "智慧等待 (Smart Wait)", icon="📡")
        
        s_wait = ctk.CTkSwitch(wait_content, text="啟用等待開台 (Wait for Stream)", variable=self.var_live_wait, 
                               font=(self.font_family, 13, "bold"), progress_color="#2CC985", height=32)
        s_wait.pack(anchor="w", padx=10, pady=8)
        CTkToolTip(s_wait, "僅對直播連結有效。\n若直播尚未開始，程式將持續監控直到開播。")
        
        # --- Card 2: 錄製策略 ---
        rec_content = create_live_card(center_box, "錄製策略 (Recording Strategy)", icon="📼")
        
        s_rec = ctk.CTkSwitch(rec_content, text="嘗試從頭下載 (Live from Start)", variable=self.var_live_from_start,
                              font=(self.font_family, 13, "bold"), progress_color="#2CC985", button_hover_color="#20A068", height=32)
        s_rec.pack(anchor="w", padx=10, pady=8)
        CTkToolTip(s_rec, "僅對直播連結有效。\n若您在直播中途才開始錄製，嘗試抓取錯過的開頭片段。")

        # --- Sub-feature: Auto Stop ---
        stop_frame = ctk.CTkFrame(rec_content, fg_color="transparent")
        stop_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        def toggle_stop_entry():
             state = "normal" if self.var_live_autostop.get() else "disabled"
             self.entry_live_stop.configure(state=state)
             
        s_stop = ctk.CTkSwitch(stop_frame, text="啟用定時停止 (Auto Stop)", variable=self.var_live_autostop, 
                               font=(self.font_family, 13, "bold"), progress_color="#2CC985", button_hover_color="#20A068",
                               command=toggle_stop_entry, height=32)
        s_stop.pack(side="left")
        
        self.entry_live_stop = ctk.CTkEntry(stop_frame, textvariable=self.var_live_stop_min, width=60, height=28, state="disabled")
        self.entry_live_stop.pack(side="left", padx=10)
        
        ctk.CTkLabel(stop_frame, text="分鐘後停止", font=(self.font_family, 12), text_color="gray").pack(side="left")

        # --- Note ---
        note_box = ctk.CTkFrame(center_box, fg_color="transparent")
        note_box.pack(pady=20)
        ctk.CTkLabel(note_box, text="提示：開啟「等待開台」後，任務狀態會顯示為「下載中」，但在開播前沒有進度條變化屬正常現象。", 
                     text_color=("#1F6AA5", "#88C0D0"), font=(self.font_family, 12)).pack()
