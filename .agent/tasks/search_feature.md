# 實作計畫：YouTube 搜尋與選取下載功能

## 1. 目標描述

讓使用者能直接在 `MULTIDownload` 介面中輸入關鍵字搜尋影片，顯示搜尋結果後點選即可自動填入網址並分析，實現類似 YouTube 網頁的搜尋體驗。

## 2. 待辦事項 (Task List)

### 核心功能 (Backend - `core.py`)

- [ ] **新增 `search_videos` 方法**：
  - 使用 `ytsearchN:` 語法（預設抓取 10-20 筆結果）。
  - 啟用 `extract_flat=True` 以在不讀取詳細資訊的情況下快速獲取標題與網址。
  - 處理搜尋過程中的錯誤（如網路問題、核心遺失）。

### 介面設計 (UI - `ui/dialogs.py` & `ui/sections/basic.py`)

- [ ] **建立 `SearchResultDialog` (彈窗式搜尋結果)**：
  - 採用清單列表，顯示影片縮圖、標題、上傳者與長度。
  - 實作「滑過效果」提高互動感。
  - 點選結果後回傳 URL。
- [ ] **優化 `BasicTab` (搜尋輸入區)**：
  - 將 `entry_url` 的 Placeholder 改為「貼上連結或輸入關鍵字搜尋...」。
  - 在輸入框右側新增一個搜尋按鈕 (🔍)。
  - 修改 Enter 鍵邏輯：偵測到非 URL 字串時自動觸發搜尋而非分析。

### 邏輯串接 (Integration - `main.py`)

- [ ] **新增 `on_search_triggered` 處理函式**：
  - 判斷輸入內容是「URL」還是「關鍵字」。
  - 若為關鍵字，啟動背景執行緒執行搜尋。
  - 搜尋完成後彈出 `SearchResultDialog`。
  - 接收使用者點選的網址，自動填入 `entry_url` 並呼叫現有的 `on_fetch_info`。

### 視覺與體驗優化 (Polish)

- [ ] **搜尋中狀態顯示**：搜尋時顯示 Toast 或在按鈕上顯示載入動畫。
- [ ] **搜尋失敗處理**：若找不到結果，給予親切的提示。

## 3. 技術要點

- **搜尋速度**：`extract_flat` 是關鍵，能確保搜尋在 1 秒內回傳基本標題。
- **異步處理**：所有網路請求必須在 `threading.Thread` 中執行，避免 GUI 凍結。
- **UI 一致性**：搜尋結果彈窗必須符合現有的深色/淺色主題。
