# MULTIDownload - 圖形化下載工具

這是一個基於強大開源專案 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 與現代化介面庫 [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 打造的桌面下載工具。

它旨在解決複雜的指令操作痛點，提供一個美觀、直覺且功能強大的圖形化介面，支援高畫質影片下載、會員限定內容存取、直播錄製以及多工排程處理。

---

## 核心特色

### 強大下載能力
- **支援多平台**：除 YouTube 外，亦支援 yt-dlp 所涵蓋的數千個影音網站。
- **高畫質支援**：最高支援 8K 解析度下載，並可自由選擇影片編碼 (H.264, AV1, VP9)。
- **音訊轉檔**：支援提取純音訊並轉換為 MP3, M4A, FLAC, WAV 等格式，可自訂位元率 (Bitrate)。
- **字幕下載**：分析影片後自動列出所有可用字幕，支援多選並嵌入影片中。

### 進階功能
- **會員/限制內容存取**：
    - **瀏覽器直讀**：內建 Chrome, Edge, Firefox 等瀏覽器 Cookie 讀取功能，無需手動匯出檔案。
    - **cookies.txt 支援**：亦支援載入 Netscape 格式的 Cookie 檔案。
- **直播錄製**：支援從現在開始錄製，或嘗試從直播開頭追溯下載 (Live from start)。
- **時間裁剪**：可指定「開始時間」與「結束時間」，僅下載影片的精華片段。
- **多工排程**：
    - 支援加入下載隊列 (Queue)。
    - 可設定「最大同時下載數」，依序處理任務。
    - 支援背景獨立執行模式，避免卡住主要排程。

### 現代化體驗
- **外觀自訂**：內建深色 (Dark) 與淺色 (Light) 模式，可於設定分頁中切換 (自動重啟生效)。
- **系統日誌**：內建詳細的執行日誌視窗，方便追蹤進度與排除錯誤。
- **自動重試**：針對 Windows 檔案佔用 (WinError 32) 加入自動重試機制，提高轉檔成功率。
- **核心熱更新**：內建自動更新檢測，一鍵下載最新版 yt-dlp 核心，無需重新下載整個軟體，即可對抗 YouTube 演算法更新。

---

## 安裝與使用

### 一般使用者 (推薦)
1. 下載最新發布的壓縮包 (ZIP)。
2. 解壓縮至任意資料夾。
3. 雙擊執行 `MULTIDownload.exe` 即可使用。
   * *軟體包內已附帶穩定版 FFmpeg，無需額外安裝。若需更新 FFmpeg，僅需下載新版 `ffmpeg.exe` 覆蓋即可。*

### 開發者 (Python 原始碼)
若您想自行修改程式碼或透過 Python 執行：

1. **安裝依賴套件 (推薦使用 uv)**：
   ```bash
   uv pip install yt-dlp customtkinter
   ```
   *(若使用 pip: `pip install yt-dlp customtkinter`)*

2. **準備 FFmpeg**：
   需安裝 FFmpeg 並設定環境變數，或將 `ffmpeg.exe` 與 `ffprobe.exe` 放置於專案根目錄。

3. **啟動程式**：
   ```bash
   uv run python main.py
   ```
   *(或使用 pip: `python main.py`)*

---

## 操作指南

### 步驟一：基本設定
1. 在 **[影片網址]** 欄位貼上連結。
2. 點擊 **[分析網址]** 按鈕。
   - 程式會抓取影片標題、封面以及可用的字幕列表。
   - 若顯示「尚未分析」，請檢查網址是否正確。
3. 設定 **[下載位置]** (預設為當前目錄)。

### 步驟二：選擇格式
- 到 **[格式/畫質]** 分頁選擇您要下載 **影片 (Video)** 還是 **純音訊 (Audio)**。
- 選擇目標解析度 (如 1080p, 4K) 與附檔名 (mp4, mkv, mp3...)。

### 步驟三：進階選項 (Cookie 設定)
若下載會員限定影片或遇到 403 錯誤，請至 **[進階選項]**：
- **推薦方法**：勾選您的瀏覽器 (如 Chrome / Edge)，程式會自動讀取登入資訊。
  - *注意：下載時建議關閉該瀏覽器以避免權限衝突。*
- **替代方法**：使用 `cookies.txt` 檔案匯入。
  - Chrome / Edge: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
  - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

### 步驟四：開始下載
- 回到下方控制列，點擊 **[開始下載]**。
- 您可以在 **[排程任務]** 區域查看等待中的任務，或在底部的進度條查看當前進度。

---

## 常見問題 (FAQ)

**Q: 下載到一半出現 "WinError 32" 錯誤？**
A: 這通常是因為檔案被防毒軟體掃描或佔用。本程式已內建自動重試機制，通常等待幾秒後會自動解決。若持續失敗，請嘗試暫時關閉防毒軟體。

**Q: 如何下載會員限定影片？**
A: 請在瀏覽器上登入 YouTube 帳號，然後在程式的 [進階選項] 中勾選對應的瀏覽器 (例如 Chrome)。

**Q: 淺色模式下字體看不清楚？**
A: 請確認您已更新至最新版本，程式已針對標題與提示文字進行了深淺色模式的自動適配。

---

## License
本專案僅供學習與個人使用。使用時請務必遵守目標網站的服務條款與版權規範。
核心下載功能由 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 提供。
