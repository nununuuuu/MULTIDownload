import customtkinter as ctk
from constants import CODE_TO_NAME
from ui.tooltip import CTkToolTip

class SubtitleMixin:
    """
    負責字幕設定 (Subtitle Tab) 的 UI 建構與互動邏輯
    包括：字幕搜尋、過濾列表、手動下載設定
    """
    def setup_subtitle_ui(self):
        # 1. Search & Filter Bar (Top)
        filter_frame = ctk.CTkFrame(self.tab_sub, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        # Search Icon/Label
        ctk.CTkLabel(filter_frame, text="🔍", font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 5))
        
        # Search Entry
        self.var_sub_search = ctk.StringVar()
        self.var_sub_search.trace("w", self._on_sub_search_change)
        
        self.entry_sub_search = ctk.CTkEntry(filter_frame, placeholder_text="搜尋語言或代碼 (如: 繁體, en, zh-TW)...", placeholder_text_color="gray", height=35, font=self.font_text)
        self.entry_sub_search.bind("<KeyRelease>", self._on_sub_search_change)
        self.entry_sub_search.pack(side="left", fill="x", expand=True)
        
        # Hint (Right side)
        ctk.CTkLabel(filter_frame, text="(*請先分析網址)", text_color="gray", font=self.font_small).pack(side="left", padx=(10, 0))

        # 2. Scrollable List for Subtitles
        self.scroll_subs = ctk.CTkScrollableFrame(self.tab_sub, label_text=None, fg_color=("gray95", "gray16"))
        self.scroll_subs.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Grid Configuration for 2 columns
        self.scroll_subs.grid_columnconfigure(0, weight=1)
        self.scroll_subs.grid_columnconfigure(1, weight=1)

        self.sub_checkboxes = {} 
        self.current_sub_data = [] 

        # 3. Manual Settings (Bottom)
        ctk.CTkFrame(self.tab_sub, height=2, fg_color=("gray85", "gray30")).pack(fill="x", padx=20, pady=10)

        manual_frame = ctk.CTkFrame(self.tab_sub, fg_color="transparent")
        manual_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Title
        ctk.CTkLabel(manual_frame, text="通用字幕設定 (若無分析/播放清單)", font=("Microsoft JhengHei UI", 16, "bold"), text_color=("gray20", "gray90")).pack(anchor="w", pady=(5, 10))

        self.pl_sub_vars = {
            'zh-TW': ctk.BooleanVar(value=False),
            'zh-Hans': ctk.BooleanVar(value=False),
            'en': ctk.BooleanVar(value=False),
            'ja': ctk.BooleanVar(value=False),
            'ko': ctk.BooleanVar(value=False)
        }
        
        # Common Languages Row
        chk_font = ("Microsoft JhengHei UI", 14)
        
        row1 = ctk.CTkFrame(manual_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkCheckBox(row1, text="繁體中文", variable=self.pl_sub_vars['zh-TW'], font=chk_font).pack(side="left", padx=(10, 20))
        ctk.CTkCheckBox(row1, text="簡體中文", variable=self.pl_sub_vars['zh-Hans'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="英文", variable=self.pl_sub_vars['en'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="日文", variable=self.pl_sub_vars['ja'], font=chk_font).pack(side="left", padx=20)
        ctk.CTkCheckBox(row1, text="韓文", variable=self.pl_sub_vars['ko'], font=chk_font).pack(side="left", padx=20)
        
        CTkToolTip(manual_frame, "適用於播放清單下載：\n將依照「由左至右」的優先順序嘗試下載勾選的字幕。\n若影片包含該字幕則下載，否則跳過。")
        
        # Manual Entry Row
        manual_bg = ctk.CTkFrame(manual_frame, fg_color="transparent")
        manual_bg.pack(anchor="w", pady=(15, 0))
        
        self.var_sub_manual = ctk.BooleanVar()
        def toggle_manual_entry():
            self.entry_sub_manual.configure(state="normal" if self.var_sub_manual.get() else "disabled")
            
        ctk.CTkCheckBox(manual_bg, text="其他", variable=self.var_sub_manual, command=toggle_manual_entry, font=self.font_text).pack(side="left", padx=(10, 2))
        
        self.entry_sub_manual = ctk.CTkEntry(manual_bg, width=120, placeholder_text="代碼 (如: th, vi)", state="disabled")
        self.entry_sub_manual.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(manual_bg, text="用逗號或空白分隔", text_color=("#1F6AA5", "#88C0D0"), font=self.font_small).pack(side="left", padx=5)
        
        ctk.CTkButton(manual_bg, text="查詢代碼表", width=80, height=24, fg_color="#555555", font=("Microsoft JhengHei UI", 12), command=self.open_lang_table).pack(side="left", padx=10)

    def _on_sub_search_change(self, *args):
        query = self.entry_sub_search.get()
        self._refresh_subtitle_view(query)

    def open_lang_table(self):
        top = ctk.CTkToplevel(self)
        top.title("語言代碼對照表")
        top.geometry("400x600")
        
        top.transient(self)
        
        ctk.CTkLabel(top, text="支援的語言代碼", font=("Microsoft JhengHei UI", 14, "bold")).pack(pady=10)
        
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        sorted_langs = sorted(CODE_TO_NAME.items(), key=lambda x: x[0])
        
        for code, name in sorted_langs:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=code, width=60, anchor="w", font=("Consolas", 11, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", padx=5)

    def clear_subtitle_ui(self):
        """Reset subtitle UI to initial state"""
        self.current_sub_data = []
        self.sub_checkboxes = {}
        if hasattr(self, 'entry_sub_search'): self.entry_sub_search.delete(0, "end")
        if hasattr(self, 'var_sub_search'): self.var_sub_search.set("")
        
        if hasattr(self, 'scroll_subs'):
            for w in self.scroll_subs.winfo_children():
                w.destroy()
            
            ctk.CTkLabel(self.scroll_subs, text="(請先分析網址)", text_color="gray", font=("Microsoft JhengHei UI", 16)).pack(pady=40)

    def update_subtitle_list_ui(self, info_dict):
        """Prepare subtitle data and refresh UI"""
        self.current_sub_data = [] 
        self.sub_checkboxes = {} 
        
        subtitles = info_dict.get('subtitles', {})
        if isinstance(subtitles, list):
            new_subs = {}
            for item in subtitles:
                if isinstance(item, str): new_subs[item] = []
                elif isinstance(item, dict):
                    code = item.get('code') or item.get('lang') or item.get('language')
                    if code: new_subs[code] = [item]
            subtitles = new_subs

        automatic_captions = info_dict.get('automatic_captions', {})
        if isinstance(automatic_captions, list): 
             new_auto = {}
             for item in automatic_captions:
                if isinstance(item, str): new_auto[item] = []
                elif isinstance(item, dict):
                    code = item.get('code') or item.get('lang') or item.get('language')
                    if code: new_auto[code] = [item]
             automatic_captions = new_auto
        
        # 1. Official Subtitles
        if subtitles:
            for code, sub_info in subtitles.items():
                name = code
                if sub_info and 'name' in sub_info[0]:
                    name = f"{sub_info[0]['name']} ({code})"
                else: 
                     lang_name = CODE_TO_NAME.get(code)
                     if lang_name: name = f"[{code}] {lang_name}"
                
                self.current_sub_data.append({
                    "code": code, "name": name, "type": "official"
                })
        
        # 2. Auto Captions
        if automatic_captions:
            for code in automatic_captions.keys():
                lang_name = CODE_TO_NAME.get(code, code)
                name = f"[自動] {lang_name} ({code})"
                
                self.current_sub_data.append({
                    "code": code, "name": name, "type": "auto"
                })

        # Initial Render
        self._refresh_subtitle_view("")
        
        if not self.current_sub_data:
             if hasattr(self, 'lbl_sub_hint'): self.lbl_sub_hint.configure(text="分析完成：無字幕")
        else:
             if hasattr(self, 'lbl_sub_hint'): self.lbl_sub_hint.configure(text="分析完成：請勾選要下載的字幕軌")

    def _refresh_subtitle_view(self, query=""):
        # Clear existing
        for widget in self.scroll_subs.winfo_children():
            widget.destroy()
            
        if not self.current_sub_data:
            ctk.CTkLabel(self.scroll_subs, text="無可用字幕 (請先執行分析)", text_color="gray").pack(pady=20)
            return

        query = query.lower().strip()
        filtered = []
        for item in self.current_sub_data:
            if not query or query in item['code'].lower() or query in item['name'].lower():
                filtered.append(item)
        
        if not filtered:
             ctk.CTkLabel(self.scroll_subs, text="找不到符合的語言", text_color="gray").pack(pady=20)
             return

        # Grouping Logic
        fav_codes = ['zh-tw', 'zh-hant', 'zh-hans', 'zh-cn', 'en', 'en-us', 'ja', 'ko']
        
        # Define Regions (Prefix based)
        asia_codes = ['zh', 'ja', 'ko', 'vi', 'th', 'id', 'ms', 'hi', 'bn', 'my', 'tl', 'lo', 'km', 'mn', 'ne', 'si', 'ur', 'pa']
        eu_codes = ['fr', 'de', 'it', 'es', 'pt', 'ru', 'uk', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'el', 'tr', 'cs', 'hu', 'ro', 'bg', 'hr', 'sr', 'sk', 'sl', 'et', 'lv', 'lt']
        
        groups = {
            "🌟 常用語言 (Favorites)": [],
            "🌏 亞洲地區 (Asia)": [],
            "🌍 歐美與其他地區 (Europe / Americas / Others)": [],
            "🤖 自動生成 (Auto-generated)": []
        }
        
        for item in filtered:
            code = item['code'].lower()
            base_code = code.split('-')[0]
            
            if item['type'] == 'auto':
                groups["🤖 自動生成 (Auto-generated)"].append(item)
            elif code in fav_codes:
                groups["🌟 常用語言 (Favorites)"].append(item)
            elif base_code in asia_codes:
                groups["🌏 亞洲地區 (Asia)"].append(item)
            else:
                groups["🌍 歐美與其他地區 (Europe / Americas / Others)"].append(item)

        # Render Groups
        row_idx = 0
        
        def create_group_section(title, items):
            nonlocal row_idx
            if not items: return
            
            # Header (Span 2 cols)
            header = ctk.CTkLabel(self.scroll_subs, text=title, font=("Microsoft JhengHei UI", 13, "bold"), text_color=("#1F6AA5", "#88C0D0"))
            header.grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(10, 5), padx=5)
            row_idx += 1
            
            # Sub-grid layout for items
            for i, item in enumerate(items):
                code = item['code']
                
                # Create/Retrieve Variable
                if code not in self.sub_checkboxes:
                    var = ctk.BooleanVar(value=False)
                    # Auto select logic removed
                    self.sub_checkboxes[code] = var
                else:
                    var = self.sub_checkboxes[code]
                
                # Checkbox
                chk = ctk.CTkCheckBox(self.scroll_subs, text=item['name'], variable=var, font=self.font_text)
                
                r = row_idx + (i // 2)
                c = i % 2
                chk.grid(row=r, column=c, sticky="w", padx=10, pady=2)
            
            # Update row_idx for next group
            row_idx += (len(items) + 1) // 2

        create_group_section("🌟 常用語言 (Favorites)", groups["🌟 常用語言 (Favorites)"])
        create_group_section("🌏 亞洲地區 (Asia)", groups["🌏 亞洲地區 (Asia)"])
        create_group_section("🌍 歐美與其他地區 (Europe / Americas / Others)", groups["🌍 歐美與其他地區 (Europe / Americas / Others)"])
        create_group_section("🤖 自動生成 (Auto-generated)", groups["🤖 自動生成 (Auto-generated)"])
