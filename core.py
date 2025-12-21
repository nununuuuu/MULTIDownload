import threading
import os
import re
import time

class YtDlpCore:
    def __init__(self):
        self.is_downloading = False
        self.stop_signal = False

    def fetch_video_info(self, url, cookie_type='none', cookie_path=''):
        import yt_dlp
        ydl_opts = {
            'skip_download': True, 
            'quiet': True, 
            'no_warnings': True,
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
        import yt_dlp
        if self.stop_signal: raise yt_dlp.utils.DownloadError("使用者手動停止下載")
        
        if d['status'] == 'downloading':
            # Try to report title if available (and not done yet)
            if title_callback:
                # Extract filename without path and extension as the "Title"
                try:
                    full_path = d.get('filename', '')
                    base = os.path.basename(full_path)
                    root, _ = os.path.splitext(base)
                    # If using part file, remove .part (rarely needed if we just take root)
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
                    if progress_callback: progress_callback(-1, f"🔴 直播錄製中 | 已錄: {downloaded_mb:.1f}MB | 速度: {speed}")
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
        import yt_dlp
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
            'noplaylist': True, 'continuedl': True, 'overwrites': True,
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
            video_fmt = "bestvideo"
            if "Best" not in config['video_res']:
                try:
                    res = config['video_res'].split('p')[0]
                    video_fmt = f"bestvideo[height<={res}]"
                except: pass

            opts['format'] = f"{video_fmt}+bestaudio/best"
            opts['merge_output_format'] = config['ext']

            # 判斷是否強制轉碼 AAC (車用模式)
            if "AAC" in config.get('audio_codec', ''):
                opts['postprocessor_args'] = {'merger': ['-c:v', 'copy', '-c:a', 'aac']}
                if target_bitrate: opts['postprocessor_args']['merger'].extend(['-b:a', f'{target_bitrate}k'])
            else:
                # Auto/Opus 模式
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