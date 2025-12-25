import customtkinter as ctk

class CTkToolTip(ctk.CTkToplevel):
    def __init__(self, widget, text, delay=200):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id = None
        self._tip_window = None
        
        self.widget.bind("<Enter>", self._schedule, add="+")
        self.widget.bind("<Leave>", self._unschedule, add="+")
        self.widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, event=None):
        self._unschedule()
        self._after_id = self.widget.after(self.delay, self._show)

    def _unschedule(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_window or not self.text:
            return
            
        x, y, cx, cy = self.widget.bbox("insert")
        
        button_x = self.widget.winfo_rootx()
        button_y = self.widget.winfo_rooty()
        button_w = self.widget.winfo_width()
        button_h = self.widget.winfo_height()
        
        target_x = button_x + button_w + 5
        target_y = button_y + (button_h // 2) - 15 
        
        self._tip_window = ctk.CTkToplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{target_x}+{target_y}")
        
        self._tip_window.lift()
        self._tip_window.attributes('-topmost', True)

        label = ctk.CTkLabel(self._tip_window, text=self.text, corner_radius=6, 
                             fg_color=("#1A1A1A", "#F8F9FA"), 
                             text_color=("#FFFFFF", "#1A1A1A"), 
                             padx=10, pady=5,
                             font=("Microsoft YaHei UI", 14, "bold"))
        label.pack()

    def _hide(self, event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None
