import os
import sys
import time
import threading
import tkinter.messagebox as msgbox

class UpdateManager:
    def __init__(self, app):
        self.app = app
        self.current_version = "1.4.4"
        self.repo_url = "https://api.github.com/repos/arielldev/gpo-fishing/commits/main"
        self.last_check = 0
        self.check_interval = 300
        self.pending_update = None
    
    def check(self):
        if self.app.main_loop_active:
            return
            
        try:
            import requests
            
            current_time = time.time()
            if current_time - self.last_check < self.check_interval:
                return
            
            self.last_check = current_time
            
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                latest_commit = commit_data['sha'][:7]
                commit_message = commit_data['commit']['message'].split('\n')[0]
                commit_date = commit_data['commit']['committer']['date']
                
                if self._should_update(commit_date):
                    self.app.root.after(0, lambda: self._prompt_update(latest_commit, commit_message))
                else:
                    self.app.root.after(0, lambda: self.app.update_status('Up to date!', 'success', '✅'))
            else:
                self.app.root.after(0, lambda: self.app.update_status('Update check failed', 'error', '❌'))
                
        except Exception as e:
            self.app.root.after(0, lambda: self.app.update_status(f'Update check error: {str(e)[:30]}...', 'error', '❌'))
    
    def _should_update(self, commit_date):
        try:
            from datetime import datetime
            
            current_file_time = os.path.getmtime(__file__)
            commit_time = datetime.fromisoformat(commit_date.replace('Z', '+00:00')).timestamp()
            
            return commit_time > current_file_time
        except:
            return False
    
    def _prompt_update(self, commit_hash, commit_message):
        if self.app.main_loop_active:
            self.pending_update = {'commit_hash': commit_hash, 'commit_message': commit_message}
            self.app.update_status('Update available - will prompt when fishing stops', 'info', '🔄')
            return
        
        message = f"New update available!\n\nLatest commit: {commit_hash}\nChanges: {commit_message}\n\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download()
        else:
            self.app.update_status('Update skipped', 'warning', '⏭️')
    
    def show_pending(self):
        if not self.pending_update:
            return
            
        commit_hash = self.pending_update['commit_hash']
        commit_message = self.pending_update['commit_message']
        
        message = f"Update available (found while fishing)!\n\nLatest commit: {commit_hash}\nChanges: {commit_message}\n\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download()
        else:
            self.app.update_status('Update skipped', 'warning', '⏭️')
        
        self.pending_update = None
    
    def download(self):
        try:
            import requests
            import zipfile
            import tempfile
            import shutil
            from datetime import datetime
            
            self.app.update_status('Downloading update...', 'info', '⬇️')
            
            zip_url = "https://github.com/arielldev/gpo-fishing/archive/refs/heads/main.zip"
            response = requests.get(zip_url, timeout=60)
            
            if response.status_code == 200:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "update.zip")
                    
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    extracted_folder = None
                    for item in os.listdir(temp_dir):
                        if os.path.isdir(os.path.join(temp_dir, item)) and 'gpo-fishing' in item:
                            extracted_folder = os.path.join(temp_dir, item)
                            break
                    
                    if not extracted_folder:
                        self.app.update_status('Update extraction failed', 'error', '❌')
                        return
                    
                    preserve_files = ['default_settings.json', 'presets/', '.git/', '.gitignore']
                    
                    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    backup_dir = os.path.join(current_dir, f"backup_{backup_timestamp}")
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    for item in os.listdir(current_dir):
                        if item.startswith('backup_'):
                            continue
                        src = os.path.join(current_dir, item)
                        dst = os.path.join(backup_dir, item)
                        try:
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        except:
                            pass
                    
                    self.app.update_status('Installing update...', 'info', '⚙️')
                    
                    for item in os.listdir(extracted_folder):
                        src = os.path.join(extracted_folder, item)
                        dst = os.path.join(current_dir, item)
                        
                        if any(item.startswith(preserve.rstrip('/')) for preserve in preserve_files):
                            continue
                        
                        try:
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        except Exception as e:
                            print(f"Error updating {item}: {e}")
                    
                    self.app.update_status('Update installed! Restarting...', 'success', '✅')
                    self.app.root.after(2000, self._restart)
                    
            else:
                self.app.update_status('Download failed', 'error', '❌')
                
        except Exception as e:
            self.app.update_status(f'Update error: {str(e)[:30]}...', 'error', '❌')
    
    def _restart(self):
        try:
            import subprocess
            
            script_path = os.path.abspath(__file__)
            self.app.root.quit()
            self.app.root.destroy()
            
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable, script_path])
            
            sys.exit(0)
            
        except Exception as e:
            print(f"Restart failed: {e}")
            sys.exit(1)
    
    def start_loop(self):
        if self.app.auto_update_enabled and not self.app.main_loop_active:
            threading.Thread(target=self.check, daemon=True).start()
        
        if self.app.auto_update_enabled:
            self.app.root.after(self.check_interval * 1000, self.start_loop)
