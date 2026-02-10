import threading
import os
import re
import time
from datetime import datetime
import sys
import glob
import shutil
import subprocess

_scripts_dir = os.path.join(os.path.dirname(sys.executable), '')
if _scripts_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = _scripts_dir + os.pathsep + os.environ.get('PATH', '')

# Constants
SUPPORTED_BROWSERS = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave', 'vivaldi', 'chromium']
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class YtDlpCore:
    def __init__(self):
        self.is_downloading = False
        self.stop_signal = False
        # [Fix] 程式啟動時，在背景嘗試更新一次解密組件
        threading.Thread(target=self._initial_update_check, daemon=True).start()

    def _initial_update_check(self):
        """背景執行一次最小更新檢查，確保 ejs 組件是最新的"""
        try:
            import yt_dlp
            # 僅初始化 YoutubeDL 即可觸發 remote_components 下載，不需要解析任何影片
            with yt_dlp.YoutubeDL({
                'quiet': True, 'no_warnings': True,
                'remote_components': ['ejs:github'],
            }) as ydl:
                pass
        except: 
            pass

    def fetch_video_info(self, url, cookie_type='none', cookie_path='', user_agent=None, proxy=None):
        try:
            import yt_dlp
        except ImportError as e:
            return {'error': f"核心載入失敗: {e}"}
        ydl_opts = {
            'skip_download': True, 
            'quiet': True, 
            'no_warnings': True,
            'noplaylist': True,
            'format': 'best',  # [Fix] 避免帶 Cookie 時 YouTube SABR 格式匹配失敗
            'ignore_no_formats_error': True,  # [Fix] 分析階段不應因格式問題中斷
            'remote_components': ['ejs:github'],  # [Fix] 自動下載最新 JS challenge solver
        }
        if user_agent: ydl_opts['user_agent'] = user_agent
        if proxy: ydl_opts['proxy'] = proxy

        # 支援多種瀏覽器 Cookie 讀取
        has_cookies = False
        if cookie_type in SUPPORTED_BROWSERS:
            ydl_opts['cookiesfrombrowser'] = (cookie_type, )
            has_cookies = True
        elif cookie_type == 'file' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True
        elif cookie_type == 'paste' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True

        # [Fix] 根據 Cookie 狀態選擇 player_client (ios/android 不支援 Cookie)
        if has_cookies:
            clients = ['web', 'web_embedded']
        else:
            clients = ['ios', 'android', 'web_embedded', 'web']
        ydl_opts['extractor_args'] = {
            'youtube': {'player_client': clients, 'player_skip_subscribe_check': True}
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb = info.get('thumbnail')
                if not thumb and info.get('thumbnails'):
                    try: thumb = info['thumbnails'][-1].get('url')
                    except: pass

                return {
                    'title': info.get('title', '未知標題'),
                    'thumbnail': thumb,
                    'duration': info.get('duration_string'),
                    'uploader': info.get('uploader'),
                    'is_live': info.get('is_live', False),
                    'subtitles': list(set(list(info.get('subtitles', {}).keys()) + list(info.get('automatic_captions', {}).keys()))),
                    'http_headers': info.get('http_headers', {})
                }
        except Exception as e:
            return {'error': f"分析失敗: {str(e) or repr(e)}"}

    def fetch_playlist_info(self, url, cookie_type='none', cookie_path='', user_agent=None, proxy=None):
        try:
            import yt_dlp
        except ImportError as e:
            return {'error': f"核心載入失敗: {e}"}
        
        ydl_opts = {
            'skip_download': True, 
            'quiet': True, 
            'no_warnings': True,
            'extract_flat': False, # Disable flat extraction to ensure we get full metadata (titles)
            'noplaylist': False,
            'ignoreerrors': True,
        }
        if user_agent: ydl_opts['user_agent'] = user_agent
        if proxy: ydl_opts['proxy'] = proxy

        has_cookies = False
        if cookie_type in SUPPORTED_BROWSERS:
            ydl_opts['cookiesfrombrowser'] = (cookie_type, )
            has_cookies = True
        elif cookie_type == 'file' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True
        elif cookie_type == 'paste' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True

        # [Fix] 根據 Cookie 狀態選擇 player_client
        if has_cookies:
            clients = ['web', 'web_embedded']
        else:
            clients = ['ios', 'android', 'web_embedded', 'web']
        ydl_opts['extractor_args'] = {
            'youtube': {'player_client': clients, 'player_skip_subscribe_check': True}
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("無法有效獲取清單資訊 (info is None)")
                    
                entries_data = []
                if 'entries' in info:
                    for idx, entry in enumerate(info['entries']):
                        if entry:
                            title = entry.get('title', '未知標題')
                            # 嘗試獲取 URL，若無則用 ID 組建
                            url = entry.get('url')
                            if not url and entry.get('id'):
                                url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            
                            entries_data.append({'index': idx + 1, 'title': title, 'url': url})
                
                count = len(entries_data)
                if not count and info.get('playlist_count'): count = info.get('playlist_count')
                
                # Try to get playlist thumbnail
                thumb = info.get('thumbnail')
                if not thumb and info.get('thumbnails'):
                    try: thumb = info['thumbnails'][-1].get('url')
                    except: pass
                
                # Fallback: Take first video's thumbnail if accessible
                if not thumb and entries_data:
                    first_entry = info['entries'][0] if info.get('entries') else None
                    if first_entry:
                        thumb = first_entry.get('thumbnail')

                return {
                    'title': info.get('title', '未知播放清單'),
                    'thumbnail': thumb,
                    'count': count,
                    'items': entries_data,
                    'http_headers': info.get('http_headers', {})
                }
        except Exception as e:
            return {'error': f"播放清單分析失敗: {str(e) or repr(e)}"}

    def search_videos(self, query, max_results=10, cookie_type='none', cookie_path='', user_agent=None, proxy=None, log_callback=None):
        """同時搜尋 YouTube 和 Bilibili 影片"""
        try:
            import yt_dlp
        except ImportError as e:
            return {'error': f"核心載入失敗: {e}"}

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'ignoreerrors': True,
        }
        
        if user_agent: ydl_opts['user_agent'] = user_agent
        if proxy: ydl_opts['proxy'] = proxy

        has_cookies = False
        if cookie_type in SUPPORTED_BROWSERS:
            ydl_opts['cookiesfrombrowser'] = (cookie_type, )
            has_cookies = True
        elif cookie_type == 'file' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True
        elif cookie_type == 'paste' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
                has_cookies = True

        # [Fix] 根據 Cookie 狀態選擇 player_client
        if has_cookies:
            clients = ['web', 'web_embedded']
        else:
            clients = ['ios', 'android', 'web_embedded', 'web']
        ydl_opts['extractor_args'] = {
            'youtube': {'player_client': clients}
        }

        # 每個平台各抓 max_results 筆 (多抓幾筆以補足過濾)
        per_platform = max_results + 5
        
        all_results = []
        
        # 搜尋 YouTube
        yt_results = []
        yt_failed = False
        try:
            yt_url = f"ytsearch{per_platform}:{query}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(yt_url, download=False)
                if info and 'entries' in info:
                    for entry in info.get('entries', []):
                        parsed = self._parse_search_entry(entry, 'youtube')
                        if parsed:
                            yt_results.append(parsed)
            if not yt_results: yt_failed = True # 無結果也視為失敗
        except Exception:
            yt_failed = True
            if log_callback: log_callback("[警告] YouTube 搜尋錯誤")
        
        # 截取 YouTube 前 max_results 筆
        all_results.extend(yt_results[:max_results])
        
        # 搜尋 Bilibili (使用官方 API)
        bili_results = []
        bili_failed = False
        try:
            bili_results = self._search_bilibili_api(query, max_results)
            if not bili_results: bili_failed = True
        except Exception:
            bili_failed = True
            if log_callback: log_callback("[警告] Bilibili 搜尋錯誤")
        
        all_results.extend(bili_results)

        if yt_failed and bili_failed:
             if log_callback: log_callback("[錯誤] 搜尋暫時無法使用")

        # 排序由 UI 彈窗處理
        return {'results': all_results}

    def _search_bilibili_api(self, query, max_results=20):
        """使用 Bilibili 官方 API 搜尋影片"""
        import requests
        import urllib.parse
        
        results = []
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            session.headers.update(headers)
            
            # 1. 先訪問首頁獲取必要的 Cookie (buvid3, b_nut 等)
            session.get('https://www.bilibili.com/', timeout=5)
            
            # 2. 搜尋 API (使用舊版非 WBI API)
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={encoded_query}&page=1&page_size={max_results}"
            
            search_headers = {
                'Referer': f'https://search.bilibili.com/all?keyword={encoded_query}',
                'Origin': 'https://search.bilibili.com',
            }
            
            resp = session.get(api_url, headers=search_headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 檢查回傳格式
                result_list = None
                if data.get('code') == 0:
                    if data.get('data', {}).get('result'):
                        result_list = data['data']['result']
                
                if result_list:
                    for item in result_list[:max_results]:
                        duration_str = item.get('duration', '--:--')
                        
                        # 清理標題中的 <em> 標籤
                        title = item.get('title', '未知標題')
                        title = title.replace('<em class="keyword">', '').replace('</em>', '')
                        
                        thumbnail = item.get('pic', '')
                        if thumbnail and not thumbnail.startswith('http'):
                            thumbnail = 'https:' + thumbnail
                        
                        results.append({
                            'title': title,
                            'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                            'thumbnail': thumbnail,
                            'duration': duration_str,
                            'uploader': item.get('author', '未知頻道'),
                            'view_count': item.get('play'),
                            'timestamp': item.get('pubdate'),  # Bilibili 的上傳時間戳
                            'platform': 'bilibili',
                        })
        except Exception as e:
            print(f"Bilibili API 搜尋錯誤: {e}")
        
        return results

    def _parse_search_entry(self, entry, platform):
        """解析單筆搜尋結果"""
        if not entry:
            return None
        
        duration = entry.get('duration')
        entry_url = entry.get('url') or ''
        entry_id = entry.get('id') or ''
        
        # YouTube 過濾
        if platform == 'youtube':
            if not duration:
                return None
            if '/channel/' in entry_url or '/@' in entry_url or entry_url.startswith('https://www.youtube.com/c/'):
                return None
            if 'list=' in entry_url and 'watch?v=' not in entry_url:
                return None
        
        # Bilibili 過濾 (放寬條件，Bilibili 有時不回傳 duration)
        # if platform == 'bilibili':
        #     if not duration:
        #         return None
        
        # 組建 URL
        video_url = entry_url
        if not video_url and entry_id:
            if platform == 'youtube':
                video_url = f"https://www.youtube.com/watch?v={entry_id}"
            elif platform == 'bilibili':
                video_url = f"https://www.bilibili.com/video/{entry_id}"
        
        # 格式化時長
        if duration:
            mins, secs = divmod(int(duration), 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                duration_str = f"{hours}:{mins:02d}:{secs:02d}"
            else:
                duration_str = f"{mins}:{secs:02d}"
        else:
            duration_str = "--:--"
        
        return {
            'title': entry.get('title', '未知標題'),
            'url': video_url,
            'thumbnail': entry.get('thumbnail') or (entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None),
            'duration': duration_str,
            'uploader': entry.get('uploader') or entry.get('channel') or '未知頻道',
            'view_count': entry.get('view_count'),
            'timestamp': entry.get('timestamp'),  # Unix timestamp
            'upload_date': entry.get('upload_date'),  # YYYYMMDD 格式
            'platform': platform,
        }


    def get_available_hw_accel(self):
        """偵測可用的硬體加速器 (NVIDIA, Intel, AMD)"""
        accel_types = []
        try:
            # [Fix] 確保 ffmpeg_path 在所有分支下都有值
            ffmpeg_path = shutil.which("ffmpeg")
            
            # 若系統 PATH 找不到，嘗試本地目錄
            if not ffmpeg_path:
                try: 
                    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                    local_ffmpeg = os.path.join(base_dir, "ffmpeg.exe") 
                    if os.path.exists(local_ffmpeg): 
                        ffmpeg_path = local_ffmpeg
                    else: 
                        local_ffmpeg_bin = os.path.join(base_dir, "bin", "ffmpeg.exe")
                        if os.path.exists(local_ffmpeg_bin): 
                            ffmpeg_path = local_ffmpeg_bin
                except: 
                    pass
            
            # 若仍找不到 ffmpeg，直接返回空列表
            if not ffmpeg_path:
                return accel_types
            
            # 執行偵測
            cmd = [ffmpeg_path, "-hide_banner", "-encoders"]
            # Windows 隱藏視窗
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
            output = result.stdout
            
            if "nvenc" in output: accel_types.append("NVIDIA")
            if "qsv" in output: accel_types.append("Intel")
            if "amf" in output: accel_types.append("AMD")
            if "videotoolbox" in output: accel_types.append("Apple")
            
        except Exception:
            pass 
            
        return accel_types


    def stop_download(self):
        self.stop_signal = True
        # [Refinement] 移除強制殺死線程的邏輯
        # 強制在此處使用 SystemExit 會導致檔案控制代碼 (File Handle) 未正確釋放
        # 進而導致暫停後恢復時出現 WinError 32 (檔案被佔用)
        # yt-dlp 會在 progress_hook 中檢查 stop_signal 並優雅退出
        pass

    def start_download_thread(self, config, progress_callback, log_callback, finish_callback, title_callback=None):
        if self.is_downloading: return
        self.stop_signal = False
        self.is_downloading = True
        
        # [Fix] 保存 Thread 參照以便強制作業
        self.download_thread = threading.Thread(target=self._run_download, args=(config, progress_callback, log_callback, finish_callback, title_callback))
        self.download_thread.daemon = True
        self.download_thread.start()

    def _remove_ansi(self, text):
        return ANSI_ESCAPE.sub('', text)

    def _progress_hook(self, d, progress_callback, log_callback, title_callback=None):
        try:
            import yt_dlp
        except ImportError:
            return 

        if self.stop_signal: raise yt_dlp.utils.DownloadError("使用者手動停止下載")
        
        if d['status'] == 'downloading':
            if title_callback:
                try:
                    full_path = d.get('filename', '')
                    base = os.path.basename(full_path)
                    if base.endswith('.part'): base = base[:-5]
                    root, _ = os.path.splitext(base)
                    
                    root = re.sub(r'\.f[0-9]{2,}(?:\.[a-z0-9]+)?$', '', root)
                    
                    if root: title_callback(root)
                except: pass

            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                
                # 直播判斷 (total 為 None)
                if total is None:
                    downloaded_mb = downloaded / 1024 / 1024
                    speed = self._remove_ansi(d.get('_speed_str', 'N/A'))
                    
                    # 區分 直播 vs 普通不定長度下載
                    status_text = f"直播錄製中: {downloaded_mb:.1f}MB" if d.get('is_live') else f"下載中: {downloaded_mb:.1f}MB"
                    if progress_callback: progress_callback(-1, status_text, speed, "Live")
                else:
                    progress = downloaded / total
                    speed = self._remove_ansi(d.get('_speed_str', 'N/A'))
                    eta = self._remove_ansi(d.get('_eta_str', 'N/A'))
                    percent_str = f"{int(progress * 100)}%"
                    if progress_callback: progress_callback(progress, f"下載中: {percent_str}", speed, eta)
            except: 
                if progress_callback: progress_callback(0, "下載中...")
        
        elif d['status'] == 'finished':
            if progress_callback: progress_callback(0.99, "合併轉檔中 (修復音訊)...") 

    def _run_download(self, config, progress_callback, log_callback, finish_callback, title_callback=None):
        try:
            import yt_dlp
        except ImportError:
            self.is_downloading = False
            if finish_callback: finish_callback(False, "核心遺失: 未安裝 yt-dlp，請至設定頁面執行更新。")
            return

        # 鎖定程式所在目錄尋找 ffmpeg (優先順序: 當前目錄 -> bin 子目錄 -> 系統環境變數)
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))

        ffmpeg_loc = None
        
        # 優先檢查 bin/ 子目錄 (較為整潔的配置)
        if os.path.exists(os.path.join(script_dir, 'bin', 'ffmpeg.exe')) or os.path.exists(os.path.join(script_dir, 'bin', 'ffmpeg')):
            ffmpeg_loc = os.path.join(script_dir, 'bin')
        # 其次檢查根目錄
        elif os.path.exists(os.path.join(script_dir, 'ffmpeg.exe')) or os.path.exists(os.path.join(script_dir, 'ffmpeg')):
            ffmpeg_loc = script_dir
            
        # --- FFmpeg 狀態診斷與回報 ---
        check_path = None
        if ffmpeg_loc:
            check_path = os.path.join(ffmpeg_loc, 'ffmpeg.exe')
            if not os.path.exists(check_path): check_path = os.path.join(ffmpeg_loc, 'ffmpeg')
        else:
            check_path = "ffmpeg" 

        try:
            # 嘗試執行 -version 確保可用
            cmd = [check_path, "-version"]
            # Windows 下隱藏視窗
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, startupinfo=startupinfo)
            
            # Determine source info
            source_desc = "系統環境變數"
            path_desc = "系統預設"
            
            if ffmpeg_loc:
                if ffmpeg_loc.endswith("bin"): source_desc = "本地 (bin 子目錄)"
                else: source_desc = "本地 (程式根目錄)"
                path_desc = ffmpeg_loc
            else:
                sys_p = shutil.which("ffmpeg")
                if sys_p: path_desc = sys_p

            if log_callback: 
                log_callback(f"[系統] 偵測到 FFmpeg:來源: {source_desc} | 路徑: {path_desc}")
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            if ffmpeg_loc:
                if log_callback: log_callback(f"[嚴重錯誤] 發現 FFmpeg 但無法執行！請檢查檔案是否損毀或被防毒攔截。\n路徑: {check_path}")
            else:
                if log_callback: log_callback(f"[嚴重警告] 未偵測到 FFmpeg！\n高畫質下載 (1080p+) 需要合併影像與聲音，將導致失敗。\n請確認已將 ffmpeg.exe 放入程式資料夾。")
            
        except Exception as e:
            if log_callback: log_callback(f"[系統錯誤] 檢查 FFmpeg 時發生例外: {e}")
        # ----------------------------------
        
        # 3. Else: remains None (yt-dlp will use system PATH)
        
        if not config.get('save_path'): config['save_path'] = os.getcwd()

        class MyLogger:
            def debug(self, msg):
                if "[Merger]" in msg or "Merging formats" in msg:
                     if log_callback: log_callback("分段下載完畢 (Video/Audio)，準備合併...")
            def info(self, msg): pass
            def warning(self, msg):
                # [Filter] 
                # 允許顯示更新進度，這讓使用者能知道正在下載新組件
                if "Downloading remote component" in msg or "Updated remote component" in msg:
                    if log_callback: log_callback(f"[系統] {msg}")
                    return
                
                # 過濾掉不會導致核心失敗的技術性警告
                ignore_keywords = [
                    "JavaScript runtime", "SABR streaming", 
                    "solver lib script", "solver core script", 
                    "Remote components", "PO Token", "GVS PO Token",
                    "Skipping unsupported client"
                ]
                if any(k in msg for k in ignore_keywords):
                    return
                if log_callback: log_callback(f"[警告] {self._clean(msg)}")
            def error(self, msg):
                if log_callback: log_callback(f"[錯誤] {self._clean(msg)}")
            def _clean(self, msg):
                return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', msg)

        filename_tmpl = f"{config['filename']}" if config.get('filename') else "%(title)s"
        
        if config.get('add_timestamp'):
            ts_str = datetime.now().strftime("_%Y%m%d_%H%M%S")
            filename_tmpl += ts_str
            
        opts = {
            'outtmpl': os.path.join(config['save_path'], f"{filename_tmpl}.%(ext)s"),
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback, log_callback, title_callback)],
            'noplaylist': not config.get('playlist_mode', False), 
            'continuedl': True, 'overwrites': True,
            'ffmpeg_location': ffmpeg_loc,
            'windowsfilenames': True, 'trim_file_name': 200,     
            'quiet': True, 'no_warnings': True,
            'logger': MyLogger(),
            'remote_components': ['ejs:github'],  # [Fix] 自動下載最新 JS challenge solver
            'file_access_retries': 10,  # [Fix] 增加檔案存取重試次數 (防毒軟體鎖檔)
            'retries': 5,  # 網路重試
            'referer': 'https://www.youtube.com/',
        }
        
        if config.get('proxy'): opts['proxy'] = config['proxy']
        
        if config.get('user_agent'): 
            opts['user_agent'] = config['user_agent']
            # 若手動指定 UA，則不使用 impersonate 以免衝突 (impersonate 會自帶 UA)
            opts.pop('impersonate', None)
        
        if not config.get('user_agent'):
             opts.pop('user_agent', None) 
        
        # [Fix] Metadata 映射 (不包含日期，日期由 mutagen 在下載後修正)
        opts['parse_metadata'] = [
            'video:uploader:%(artist)s',
            'video:description:%(comment)s',
        ]
        
        # [Fix] 防止 FFmpegMetadata 寫入錯誤的 date (YYYYMMDD 會被解讀成亂碼年份)
        opts.setdefault('postprocessor_args', {})
        opts['postprocessor_args'].setdefault('FFmpegMetadata', [])
        opts['postprocessor_args']['FFmpegMetadata'].extend(['-metadata', 'date='])
        
        # Post-Processing Options
        # [FIX] 初始化 Post-Processors 列表
        # 改為完全手動管理 PP，確保縮圖先嵌入，再寫入 Metadata
        opts.setdefault('postprocessors', [])

        if config.get('embed_thumbnail'): 
            opts['writethumbnail'] = True # 下載封面
            opts['postprocessors'].append({
                'key': 'EmbedThumbnail',
            })
        
        if config.get('add_metadata'):
            opts['postprocessors'].append({
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            })


        if config.get('sponsorblock'): 
            # 直接使用使用者勾選的類別列表
            sb_list = config.get('sponsor_cats_list', ['all'])
            if not sb_list: sb_list = ['all'] # 防呆
            
            opts['sponsorblock_remove'] = sb_list
            opts['force_keyframes_at_cuts'] = True 

        # Hardware Acceleration
        hw_mode = config.get('hardware_accel', '')
        pp_args = []
        if "NVIDIA" in hw_mode: pp_args = ['-hwaccel', 'cuda']
        elif "Intel" in hw_mode: pp_args = ['-hwaccel', 'auto']
        elif "AMD" in hw_mode: pp_args = ['-hwaccel', 'auto'] 
        elif "Apple" in hw_mode: pp_args = ['-hwaccel', 'videotoolbox']
        elif "自動" in hw_mode: pp_args = ['-hwaccel', 'auto']
        
        if pp_args:
             if log_callback: log_callback(f"[系統] 已啟用硬體加速: {hw_mode}")
             opts['postprocessor_args'].setdefault('Merger', [])
             opts['postprocessor_args']['Merger'].extend(pp_args)
             opts['postprocessor_args'].setdefault('VideoConvertor', [])
             opts['postprocessor_args']['VideoConvertor'].extend(pp_args)


        # Live Stream Logic
        if config.get('live_wait'):
            opts['wait_for_video'] = (2, 10) 
            if log_callback: log_callback("[直播] 已啟用智慧等待: 正在監控開台訊號...")
            
        if config.get('live_from_start'):
            opts['live_from_start'] = True


        # Cookie 設定
        has_cookies = False
        if config['cookie_type'] in SUPPORTED_BROWSERS:
            opts['cookiesfrombrowser'] = (config['cookie_type'], )
            has_cookies = True
        elif config['cookie_type'] == 'file' and config['cookie_path']:
            opts['cookiefile'] = config['cookie_path']
            has_cookies = True
        elif config['cookie_type'] == 'paste' and config['cookie_path']:
            opts['cookiefile'] = config['cookie_path']
            has_cookies = True

        # [Fix] 根據 Cookie 狀態選擇 player_client (ios/android 不支援 Cookie)
        if has_cookies:
            clients = ['web', 'web_embedded']
        else:
            clients = ['ios', 'android', 'web_embedded', 'web']
        opts['extractor_args'] = {
            'youtube': {'player_client': clients, 'player_skip_subscribe_check': True}
        }

        # 1. 解析目標 Bitrate
        target_bitrate = None
        if config['audio_qual'] != 'Best (來源預設)':
            target_bitrate = config['audio_qual'].split(' ')[0]

        # 2. 模式判斷
        if config['is_audio_only']:
            # --- 純音訊模式 ---
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': config['ext'], 
            }]
            
            # 無損格式 (FLAC/WAV) 不設定 bitrate
            if config['ext'] in ['flac', 'wav']:
                pass 
            else:
                # 有損格式設定 bitrate
                if target_bitrate: opts['postprocessors'][0]['preferredquality'] = target_bitrate
                else: opts['postprocessors'][0]['preferredquality'] = '192'

        else:
            # --- 影片模式 ---
            res_constraint = ""
            if "Best" not in config['video_res']:
                try:
                     r = config['video_res'].split('p')[0]
                     res_constraint = f"[height<={r}]"
                except: pass

            v_codecs = []
            
            # 取得 UI 選項的編碼
            # "Auto (預設)", "H.264 - 舊裝置/車機", "H.265 - 省空間/蘋果", "VP9 - Android/舊電腦4K", "AV1 - 極致畫質"
            sel_codec = config.get('video_codec', 'Auto')
            
            is_h264_mode = "H.264" in sel_codec or config.get('use_h264_legacy', False)
            is_h265_mode = "H.265" in sel_codec
            is_vp9_mode = "VP9" in sel_codec
            is_av1_mode = "AV1" in sel_codec

            if is_h264_mode:
                v_codecs.append(f"bestvideo{res_constraint}[vcodec^=avc1]")
            elif is_vp9_mode:
                v_codecs.append(f"bestvideo{res_constraint}[vcodec^=vp9]")
            elif is_av1_mode:
                v_codecs.append(f"bestvideo{res_constraint}[vcodec^=av01]")
            
            # 若為 Auto 或 H.265(需事後轉檔)，則先下載畫質最好的 (通常是 av1/vp9)
            v_codecs.append(f"bestvideo{res_constraint}")
            
            a_codecs = []
            # 解析音訊編碼選擇
            # "Auto (預設)", "Opus - 音質優先", "AAC - 車機/蘋果", "MP3 - 萬用格式", "FLAC - 無損", "WAV - 無損原始"
            audio_codec_sel = config.get('audio_codec', 'Auto')
            is_aac_mode = "AAC" in audio_codec_sel
            is_mp3_mode = "MP3" in audio_codec_sel
            is_opus_mode = "Opus" in audio_codec_sel
            is_flac_mode = "FLAC" in audio_codec_sel
            is_wav_mode = "WAV" in audio_codec_sel
            
            # H.264 模式強制 AAC (for compatibility)
            if is_aac_mode or is_mp3_mode or is_h264_mode:
                a_codecs.append("bestaudio[ext=m4a]")
            elif is_opus_mode:
                a_codecs.append("bestaudio[ext=webm]")
            a_codecs.append("bestaudio")

            fmt_options = []
            for v in v_codecs:
                for a in a_codecs:
                    fmt_options.append(f"{v}+{a}")
            
            fmt_options.append("best")
            
            opts['format'] = "/".join(fmt_options)
            opts['merge_output_format'] = config['ext']

            # Post-Processing Args for Merger/Converter
            merger_args = []
            
            # 1. 裁剪模式：強制重編碼 (最高優先級)
            if config['use_time_range']:
                if 'postprocessor_args' not in opts: opts['postprocessor_args'] = {}
                if 'Merger' not in opts['postprocessor_args']: opts['postprocessor_args']['Merger'] = []
                
                # 使用 libx264 快速裁剪 (兼顧速度與相容性)
                opts['postprocessor_args']['Merger'].extend([
                    '-c:v', 'libx264', '-preset', 'ultrafast', 
                    '-c:a', 'aac', '-b:a', '192k'
                ])
                
            # 2. H.265 轉檔模式 (若未啟用裁剪)
            elif is_h265_mode:
                # 偵測硬體加速
                enc_cmd = ['-c:v', 'libx265', '-crf', '28', '-preset', 'medium', '-tag:v', 'hvc1']
                hw_type = config.get('hardware_accel', '')
                
                if "NVIDIA" in hw_type:
                    enc_cmd = ['-c:v', 'hevc_nvenc', '-preset', 'p4', '-tag:v', 'hvc1']
                elif "Intel" in hw_type:
                     enc_cmd = ['-c:v', 'hevc_qsv', '-load_plugin', 'hevc_hw', '-tag:v', 'hvc1']
                elif "AMD" in hw_type:
                     enc_cmd = ['-c:v', 'hevc_amf', '-tag:v', 'hvc1']
                elif "Apple" in hw_type:
                     enc_cmd = ['-c:v', 'hevc_videotoolbox', '-tag:v', 'hvc1']

                merger_args = enc_cmd + ['-c:a', 'copy']
                
                if 'postprocessor_args' not in opts: opts['postprocessor_args'] = {}
                if 'Merger' not in opts['postprocessor_args']: opts['postprocessor_args']['Merger'] = []
                opts['postprocessor_args']['Merger'].extend(merger_args)

            # 3. 一般模式 (Stream Copy or Audio Re-encode)
            else:
                if is_aac_mode or is_h264_mode:
                    merger_args = ['-c:v', 'copy', '-c:a', 'aac']
                    if target_bitrate and target_bitrate.isdigit():
                         merger_args.extend(['-b:a', f'{target_bitrate}k'])
                elif is_mp3_mode:
                    # MP3 需要重新編碼
                    merger_args = ['-c:v', 'copy', '-c:a', 'libmp3lame']
                    if target_bitrate and target_bitrate.isdigit():
                         merger_args.extend(['-b:a', f'{target_bitrate}k'])
                    else:
                         merger_args.extend(['-b:a', '192k'])  # MP3 預設 192kbps
                elif is_opus_mode:
                    merger_args = ['-c:v', 'copy', '-c:a', 'libopus']
                    if target_bitrate and target_bitrate.isdigit():
                         merger_args.extend(['-b:a', f'{target_bitrate}k'])
                elif is_flac_mode:
                    # FLAC 無損編碼
                    merger_args = ['-c:v', 'copy', '-c:a', 'flac']
                elif is_wav_mode:
                    # WAV 無損編碼 (PCM)
                    merger_args = ['-c:v', 'copy', '-c:a', 'pcm_s16le']
                elif target_bitrate:
                    # Auto mode with custom bitrate
                    merger_args = ['-c:v', 'copy', '-c:a', 'libopus', '-b:a', f'{target_bitrate}k']
                else:
                    # 完全不轉碼 (Video Copy / Audio Copy)
                    pass

                if merger_args:
                    if 'postprocessor_args' not in opts: opts['postprocessor_args'] = {}
                    if 'Merger' not in opts['postprocessor_args']: opts['postprocessor_args']['Merger'] = []
                    opts['postprocessor_args']['Merger'].extend(merger_args)

        # 3. 其他功能 (裁剪/字幕/直播)
        if config['use_time_range']:
            opts['download_ranges'] = yt_dlp.utils.download_range_func(
                None, [(self._parse_time(config['start_time']), self._parse_time(config['end_time']))]
            )
            # 關閉強制關鍵影格切割 (配合上述全重編碼，不需要此選項，且此選項常導致 Bug)
            opts['force_keyframes_at_cuts'] = False

        if config['sub_langs']:
            should_write = not config.get('embed_subs', False)
            opts['writesubtitles'] = should_write
            opts['writeautomaticsub'] = should_write
            opts['subtitleslangs'] = config['sub_langs']

        if config['is_live']: opts['live_from_start'] = config['live_from_start']

        success = False
        message = ""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    if log_callback: log_callback(f"啟動下載: {config['url']}")
                else:
                    if log_callback: log_callback(f"檔案被佔用或下載失敗，等待系統釋放資源 ({attempt}/{max_retries})...")
                    time.sleep(5) # [UPGRADE] 延長等待時間至 5秒，讓 Antivirus 有時間掃描完釋放
                    
                    # 嘗試清理可能殘留的暫存檔 (雖難以精確預測檔名，但可依賴 yt-dlp 的 overwrites)

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(config['url'], download=True)
                
                # [Fix] 下載成功後，用 mutagen 修正 MP4/M4A 的日期標籤
                if info and config.get('add_metadata'):
                    try:
                        upload_date = info.get('upload_date', '')
                        # 將 YYYYMMDD 格式化為 YYYY-MM-DD
                        if upload_date and len(upload_date) >= 8:
                            date_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                        elif upload_date and len(upload_date) >= 4:
                            date_str = upload_date[:4]
                        else:
                            date_str = ''
                        if date_str:
                            # 取得最終輸出檔案路徑
                            filepath = info.get('filepath') or info.get('requested_downloads', [{}])[0].get('filepath', '')
                            if filepath and os.path.exists(filepath):
                                ext = os.path.splitext(filepath)[1].lower()
                                if ext in ('.mp4', '.m4a', '.m4v'):
                                    from mutagen.mp4 import MP4
                                    audio = MP4(filepath)
                                    audio.tags['\xa9day'] = [date_str]  # ©day = YYYY-MM-DD
                                    audio.save()
                                elif ext == '.mp3':
                                    from mutagen.mp3 import MP3
                                    from mutagen.id3 import TDRC
                                    audio = MP3(filepath)
                                    audio.tags.add(TDRC(encoding=3, text=[date_str]))
                                    audio.save()
                    except Exception as meta_e:
                        if log_callback: log_callback(f"[警告] 日期修正失敗: {meta_e}")

                success = True
                message = "下載成功！"
                if progress_callback: progress_callback(1.0, "下載完成 100%")
                break 
            except (SystemExit, KeyboardInterrupt):
                message = "下載已取消 (強制中止)"
                
                # [Fix] 強制中止後主動清理殘檔，避免 WinError 32
                try:
                    time.sleep(1) # 等待 I/O 釋放
                    base_path = os.path.join(config['save_path'], filename_tmpl)
                    # 尋找所有可能的暫存檔 (例如 .part, .ytdl, .mp4, .webm...)
                    # 使用 glob 模糊搜尋檔名開頭相符的檔案
                    for f in glob.glob(f"{glob.escape(base_path)}*"):
                        try: 
                            if os.path.exists(f): 
                                os.remove(f)
                                if log_callback: log_callback(f"[系統] 已清理殘檔: {os.path.basename(f)}")
                        except: pass
                except: pass
                
                break
            except yt_dlp.utils.DownloadError as e:
                # 優先檢查停止訊號
                if self.stop_signal:
                    message = "下載已暫停"
                    break

                err_msg = str(e)
                if "使用者手動停止" in err_msg: 
                    message = "下載已取消"
                    break
                elif "requested format is not available" in err_msg.lower():
                    # [Fix] YouTube SABR 格式問題：自動降級為最寬鬆的格式重試
                    if opts.get('format') != 'best':
                        if log_callback: log_callback(f"[警告] 指定格式不可用 (可能是 YouTube SABR 串流限制)，自動降級為最佳可用格式重試...")
                        opts['format'] = 'best'
                        # 移除可能衝突的合併格式設定
                        opts.pop('merge_output_format', None)
                        continue
                    else:
                        message = f"下載錯誤: 無可用格式 ({err_msg})"
                        break
                elif "416" in err_msg or "requested range not satisfiable" in err_msg.lower():
                    # [Fix] HTTP 416: 殘留的 .part 檔案導致續傳範圍無效
                    if log_callback: log_callback(f"[警告] HTTP 416: 暫存檔與伺服器不一致，正在清理殘檔並重新下載...")
                    # 清理所有可能的暫存檔
                    try:
                        save_dir = config.get('save_path', os.getcwd())
                        for f in glob.glob(os.path.join(save_dir, "*.part")):
                            try: os.remove(f); 
                            except: pass
                        for f in glob.glob(os.path.join(save_dir, "*.ytdl")):
                            try: os.remove(f); 
                            except: pass
                    except: pass
                    # 關閉續傳模式，強制全新下載
                    opts['continuedl'] = False
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        message = f"下載錯誤: 暫存檔衝突無法修復 (HTTP 416)"
                        break
                elif "WinError 32" in err_msg:
                    # [Fix] 終極通用版 WinError 32 修復：處理所有臨時檔案改名
                    if log_callback: log_callback(f"[警告] 檔案鎖定衝突 (WinError 32)。防毒軟體正在掃描，嘗試手動修復...")
                    
                    rename_success = False
                    import re as _re
                    # [優化] 通用匹配邏輯：抓取任何 A -> B 的改名路徑
                    match = _re.search(r"'(.+?)'\s*->\s*'(.+?)'", err_msg)
                    if match:
                        src_path = match.group(1)
                        dst_path = match.group(2)
                        
                        # 如果是常見的臨時檔案後綴，且確實存在
                        if os.path.exists(src_path):
                            for retry in range(15):
                                try:
                                    time.sleep(2)
                                    # 防呆：如果目標檔案已存在且不等於來源，先移除它
                                    if os.path.exists(dst_path) and os.path.abspath(src_path) != os.path.abspath(dst_path):
                                        try: os.remove(dst_path)
                                        except: pass
                                    
                                    os.rename(src_path, dst_path)
                                    rename_success = True
                                    if log_callback: log_callback(f"[修復] 改名成功！(於等待 {(retry+1)*2} 秒後解決鎖定)")
                                    break
                                except OSError:
                                    if log_callback and retry % 3 == 0: 
                                        log_callback(f"[等待] 防毒軟體掃描中... ({retry+1}/15)")
                    
                    if rename_success:
                        # [Cleanup] 手動重命名成功後，清理 yt-dlp 遺留的片段文件
                        # 等待防毒軟體釋放檔案鎖定
                        time.sleep(3)
                        try:
                            base_name = os.path.splitext(dst_path)[0]
                            save_dir = os.path.dirname(dst_path)
                            video_stem = os.path.basename(base_name)
                            # 搜尋同目錄下所有同名的分段檔 (如 .f401.mp4, .f251.webm)
                            for f in os.listdir(save_dir):
                                f_path = os.path.join(save_dir, f)
                                if f_path == os.path.abspath(dst_path):
                                    continue
                                if f.startswith(video_stem) and f != os.path.basename(dst_path):
                                    try:
                                        os.remove(f_path)
                                        if log_callback: log_callback(f"[清理] 已移除殘留分段檔: {f}")
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        
                        success = True
                        message = "下載成功！"
                        break
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(5)
                            continue
                elif "video unavailable" in err_msg.lower() or "is not available" in err_msg.lower():
                    # [Fix] YouTube "Video unavailable" 自動修復策略
                    # 根據 Cookie 狀態選擇適合的 player_client 重試
                    has_ck = 'cookiesfrombrowser' in opts or 'cookiefile' in opts
                    if attempt == 0:
                        # 策略 1: 切換至不同的 player_client 組合
                        if has_ck:
                            # 有 Cookie → 只用支援 Cookie 的 client
                            retry_clients = ['mweb', 'web', 'web_embedded']
                        else:
                            # 無 Cookie → 嘗試不同的 client 組合
                            retry_clients = ['mweb', 'ios', 'android']
                        if log_callback: log_callback(f"[警告] 影片不可用，正在切換播放器介面重試...")
                        opts['extractor_args'] = {
                            'youtube': {
                                'player_client': retry_clients,
                                'player_skip_subscribe_check': True
                            }
                        }
                        time.sleep(2)
                        continue
                    elif attempt == 1:
                        # 策略 2: 切換 Cookie 狀態
                        if has_ck:
                            # 有 Cookie → 移除 Cookie，改用無 Cookie 的 client
                            if log_callback: log_callback(f"[警告] 嘗試移除 Cookie 並以訪客模式重試...")
                            opts.pop('cookiesfrombrowser', None)
                            opts.pop('cookiefile', None)
                            retry_clients = ['ios', 'android', 'web_embedded']
                        else:
                            if log_callback: log_callback(f"[警告] 訪客模式無法存取，嘗試最後一組播放器組合...")
                            retry_clients = ['web', 'web_embedded']
                        opts['extractor_args'] = {
                            'youtube': {
                                'player_client': retry_clients,
                                'player_skip_subscribe_check': True
                            }
                        }
                        time.sleep(2)
                        continue
                    else:
                        # 所有策略都失敗
                        if not config.get('cookie_type') or config['cookie_type'] == 'none':
                            hint = "\n💡 提示: 此影片可能需要登入才能觀看，請至設定頁面啟用瀏覽器 Cookie。"
                        else:
                            hint = "\n💡 提示: 此影片可能有地區限制或已被刪除，請嘗試使用 VPN 或確認連結是否正確。"
                        message = f"影片不可用: YouTube 拒絕存取此影片。{hint}"
                        break
                elif ("could not find" in err_msg.lower() or "cookie database" in err_msg.lower() or "copy" in err_msg.lower()) and "cookie" in err_msg.lower():
                    if 'cookiesfrombrowser' in opts:
                        if log_callback: log_callback(f"[警告] 無法讀取瀏覽器 Cookie (或是瀏覽器開啟中)，將自動切換為訪客模式重試...")
                        del opts['cookiesfrombrowser']
                        continue
                else: 
                    message = f"下載錯誤: {e}"
                    break

            except Exception as e:
                # 優先檢查停止訊號
                if self.stop_signal:
                    message = "下載已暫停"
                    break
                    
                err_str = str(e)
                # 處理通用 WinError 32 (PermissionError 等)
                if "WinError 32" in err_str or "Permission denied" in err_str:
                     if log_callback: log_callback(f"[警告] 檔案鎖定衝突 (WinError 32)。防毒軟體正在掃描，嘗試手動修復...")
                     import re as _re
                     match = _re.search(r"'(.+?)'\s*->\s*'(.+?)'", err_str)
                     if match:
                         src_path = match.group(1)
                         dst_path = match.group(2)
                         if os.path.exists(src_path):
                             for retry in range(15):
                                 try:
                                     time.sleep(2)
                                     if os.path.exists(dst_path) and os.path.abspath(src_path) != os.path.abspath(dst_path):
                                         try: os.remove(dst_path)
                                         except: pass
                                     os.rename(src_path, dst_path)
                                     success = True
                                     message = "下載成功！"
                                     if log_callback: log_callback(f"[修復] 改名成功！(等待了 {(retry+1)*2} 秒)")
                                     break
                                 except OSError:
                                     pass
                             if success: break
                     
                     if attempt < max_retries - 1:
                         time.sleep(7)
                         continue # Retry
                
                # 若非可重試錯誤或已達最大重試次數
                message = f"系統錯誤: {e}"
                break
        
        self.is_downloading = False
        if finish_callback: finish_callback(success, message)

    def _parse_time(self, time_str):
        if not time_str: return 0
        try:
            time_str = str(time_str).strip()
            
            if ':' in time_str:
                parts = list(map(float, time_str.split(':')))
                if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
                elif len(parts) == 2: return parts[0]*60 + parts[1]
                return parts[0]
            
            if '.' in time_str:
                return float(time_str)
                
         
            if time_str.isdigit():
                val = int(time_str)
                s = val % 100
                m = (val // 100) % 100
                h = val // 10000
                return h*3600 + m*60 + s

            return float(time_str)
        except: return 0