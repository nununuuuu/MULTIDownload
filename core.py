import threading
import os
import re
import time

class YtDlpCore:
    def __init__(self):
        self.is_downloading = False
        self.stop_signal = False

    def fetch_video_info(self, url, cookie_type='none', cookie_path=''):
        try:
            import yt_dlp
        except ImportError as e:
            return {'error': f"核心載入失敗: {e}"}
        ydl_opts = {
            'skip_download': True, 
            'quiet': True, 
            'no_warnings': True,
            'noplaylist': True,
        }

        # 支援多種瀏覽器 Cookie 讀取
        supported_browsers = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave', 'vivaldi']
        if cookie_type in supported_browsers:
            ydl_opts['cookiesfrombrowser'] = (cookie_type, )
        elif cookie_type == 'file' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', '未知標題'),
                    'is_live': info.get('is_live', False),
                    'subtitles': list(set(list(info.get('subtitles', {}).keys()) + list(info.get('automatic_captions', {}).keys())))
                }
        except Exception as e:
            return {'error': str(e)}

    def fetch_playlist_info(self, url, cookie_type='none', cookie_path=''):
        try:
            import yt_dlp
        except ImportError as e:
            return {'error': f"核心載入失敗: {e}"}
        
        ydl_opts = {
            'skip_download': True, 
            'quiet': True, 
            'no_warnings': True,
            'extract_flat': True, # Key: Fast extraction
            'noplaylist': False,
        }

        # Cookie Setup (Reuse logic)
        supported_browsers = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave', 'vivaldi']
        if cookie_type in supported_browsers:
            ydl_opts['cookiesfrombrowser'] = (cookie_type, )
        elif cookie_type == 'file' and cookie_path:
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # Process entries for selection dialog
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
                
                return {
                    'title': info.get('title', '未知播放清單'),
                    'count': count,
                    'items': entries_data
                }
        except Exception as e:
            return {'error': str(e)}

    def stop_download(self):
        self.stop_signal = True

    def start_download_thread(self, config, progress_callback, log_callback, finish_callback, title_callback=None):
        if self.is_downloading: return
        self.stop_signal = False
        self.is_downloading = True
        thread = threading.Thread(target=self._run_download, args=(config, progress_callback, log_callback, finish_callback, title_callback))
        thread.daemon = True
        thread.start()

    def _remove_ansi(self, text):
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _progress_hook(self, d, progress_callback, log_callback, title_callback=None):
        try:
            import yt_dlp
        except ImportError:
            return 

        if self.stop_signal: raise yt_dlp.utils.DownloadError("使用者手動停止下載")
        
        if d['status'] == 'downloading':
            # Try to report title if available (and not done yet)
            if title_callback:
                # Extract filename without path and extension as the "Title"
                try:
                    full_path = d.get('filename', '')
                    base = os.path.basename(full_path)
                    # Remove .part
                    if base.endswith('.part'): base = base[:-5]
                    # Remove extension
                    root, _ = os.path.splitext(base)
                    # Remove Typical yt-dlp format suffix like .f137, .f251 using Regex
                    # Pattern: .f followed by digits, optionally followed by another extension part
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
                    # 傳送 -1 代表直播模式
                    if progress_callback: progress_callback(-1, f"直播錄製中 | 已錄: {downloaded_mb:.1f}MB | 速度: {speed}")
                else:
                    progress = downloaded / total
                    speed = self._remove_ansi(d.get('_speed_str', 'N/A'))
                    eta = self._remove_ansi(d.get('_eta_str', 'N/A'))
                    percent_str = f"{int(progress * 100)}%"
                    if progress_callback: progress_callback(progress, f"下載中: {percent_str} | 速度: {speed} | 剩餘: {eta}")
            except: 
                if progress_callback: progress_callback(0, "下載中...")
        
        elif d['status'] == 'finished':
            if progress_callback: progress_callback(0.99, "合併轉檔中 (修復音訊)...") 
            if log_callback: log_callback(f"檔案下載完畢，正在執行 FFmpeg 處理...")

    def _run_download(self, config, progress_callback, log_callback, finish_callback, title_callback=None):
        try:
            import yt_dlp
        except ImportError:
            self.is_downloading = False
            if finish_callback: finish_callback(False, "核心遺失: 未安裝 yt-dlp，請至設定頁面執行更新。")
            return

        # 鎖定程式所在目錄尋找 ffmpeg
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_loc = None
        if os.path.exists(os.path.join(script_dir, 'ffmpeg.exe')): ffmpeg_loc = script_dir
        elif os.path.exists(os.path.join(script_dir, 'ffmpeg')): ffmpeg_loc = script_dir
        
        # Ensure config has save_path
        if not config.get('save_path'): config['save_path'] = os.getcwd()

        opts = {
            'outtmpl': os.path.join(config['save_path'], f"{config['filename']}.%(ext)s" if config['filename'] else "%(title)s.%(ext)s"),
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback, log_callback, title_callback)],
            'noplaylist': not config.get('playlist_mode', False), 
            'continuedl': True, 'overwrites': True,
            'ffmpeg_location': ffmpeg_loc,
            'windowsfilenames': True, 'trim_file_name': 200,     
            'quiet': True, 'no_warnings': True,
        }



        # Cookie 設定
        supported_browsers = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave', 'vivaldi']
        if config['cookie_type'] in supported_browsers:
            opts['cookiesfrombrowser'] = (config['cookie_type'], )
        elif config['cookie_type'] == 'file' and config['cookie_path']:
            opts['cookiefile'] = config['cookie_path']

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
            # Determine Resolution Constraint
            res_constraint = ""
            if "Best" not in config['video_res']:
                try:
                     r = config['video_res'].split('p')[0]
                     res_constraint = f"[height<={r}]"
                except: pass

            # Generate Video Preferences
            v_codecs = []
            if config.get('use_h264_legacy', False):
                v_codecs.append(f"bestvideo{res_constraint}[vcodec^=avc1]")
            v_codecs.append(f"bestvideo{res_constraint}")
            
            # Generate Audio Preferences
            a_codecs = []
            wanted_audio = config.get('audio_codec', 'Auto').split(' ')[0]
            # If user wants AAC or Legacy Mode, prefer m4a source
            if wanted_audio == 'AAC' or config.get('use_h264_legacy', False):
                a_codecs.append("bestaudio[ext=m4a]")
            a_codecs.append("bestaudio")

            # Generate ALL Combinations: V1+A1 / V1+A2 / V2+A1 / V2+A2
            # This prevents the "slash issue" where yt-dlp picks video-only format.
            fmt_options = []
            for v in v_codecs:
                for a in a_codecs:
                    fmt_options.append(f"{v}+{a}")
            
            # Add fallback 'best' at the end
            fmt_options.append("best")
            
            opts['format'] = "/".join(fmt_options)
            opts['merge_output_format'] = config['ext']

            # 判斷是否強制轉碼 AAC (車用模式) 確保相容性
            # 並且應用使用者設定的 Bitrate (例如 192k, 320k)
            # 注意: 如果來源是 128k AAC，轉成 192k 不會變好，但至少符合使用者設定的參數
            if "AAC" in config.get('audio_codec', ''):
                cmd_args = ['-c:v', 'copy', '-c:a', 'aac']
                
                # 解析目標 Bitrate
                # 只有當使用者明確指定數字 (如 320, 192) 時才強制指定
                # 若為 Best (None)，則不加 -b:a，讓 ffmpeg 自動判斷或維持 VBR，不強制灌水
                if target_bitrate and target_bitrate.isdigit():
                     cmd_args.extend(['-b:a', f'{target_bitrate}k'])

                opts['postprocessor_args'] = {'merger': cmd_args}
            else:
                # Auto/Opus 模式
                # 如果使用者有指定 bitrate，我們也應該嘗試應用 (若需轉檔)
                # 簡單起見，非 AAC 模式下我們暫不強制轉檔，就讓 yt-dlp 選最佳
                pass
                if target_bitrate:
                     opts['postprocessor_args'] = {'merger': ['-c:v', 'copy', '-c:a', 'libopus', '-b:a', f'{target_bitrate}k']}

        # 3. 其他功能 (裁剪/字幕/直播)
        if config['use_time_range']:
            opts['download_ranges'] = yt_dlp.utils.download_range_func(
                None, [(self._parse_time(config['start_time']), self._parse_time(config['end_time']))]
            )
            opts['force_keyframes_at_cuts'] = True

        if config['sub_langs']:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = True
            opts['subtitleslangs'] = config['sub_langs']

        if config['is_live']: opts['live_from_start'] = config['live_from_start']

        success = False
        message = ""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    if log_callback: log_callback(f"啟動下載: {config['url']}")
                else:
                    if log_callback: log_callback(f"檔案被佔用，正在重試 ({attempt}/{max_retries})...")
                    time.sleep(2) # 等待檔案釋放

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([config['url']])
                
                success = True
                message = "下載成功！"
                if progress_callback: progress_callback(1.0, "下載完成 100%")
                break # 成功則跳出迴圈

            except yt_dlp.utils.DownloadError as e:
                err_msg = str(e)
                if "使用者手動停止" in err_msg: 
                    message = "下載已取消"
                    break
                elif "WinError 32" in err_msg:
                    # 如果是最後一次嘗試，則報錯
                    if attempt == max_retries - 1:
                        message = "檔案被佔用 (WinError 32)\n請關閉防毒軟體或檢查檔案是否被開啟。"
                    continue # 繼續下一次重試
                else: 
                    message = f"下載錯誤: {e}"
                    break
            except Exception as e:
                message = f"系統錯誤: {e}"
                break
        
        # Finally block logic moved here ensuring it runs after loop
        self.is_downloading = False
        if finish_callback: finish_callback(success, message)

    def _parse_time(self, time_str):
        try:
            parts = list(map(int, time_str.split(':')))
            if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
            elif len(parts) == 2: return parts[0]*60 + parts[1]
            return parts[0]
        except: return 0