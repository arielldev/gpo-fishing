import os
import sys
import time
import threading
import tkinter.messagebox as msgbox

class UpdateManager:
    def __init__(self, app):
        self.app = app
        self.current_version = "1.5"
        self.repo_url = "https://api.github.com/repos/arielldev/gpo-fishing/commits/main"
        self.last_check = 0
        self.check_interval = 300  # 5 minutes
        self.pending_update = None
        self.installed_commit = self._get_installed_commit()  # Track what's actually installed
        
    def check_for_updates(self):
        """Check for updates from GitHub repository"""
        # Don't check for updates while main loop is running
        if self.app.main_loop_active:
            return
        
        try:
            import requests
            
            current_time = time.time()
            if current_time - self.last_check < self.check_interval:
                return  # Don't check too frequently
            
            self.last_check = current_time
            
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                commit_hash = commit_data['sha'][:7]
                commit_message = commit_data['commit']['message'].split('\n')[0]
                
                if self.should_update(commit_hash):
                    self.app.root.after(0, lambda: self.prompt_update(commit_hash, commit_message))
                else:
                    self.app.root.after(0, lambda: self.app.update_status('Up to date!', 'success', '✅'))
            else:
                self.app.root.after(0, lambda: self.app.update_status('Update check failed', 'error', '❌'))
                
        except Exception as e:
            self.app.root.after(0, lambda: self.app.update_status(f'Update check error: {str(e)[:30]}...', 'error', '❌'))

    def _get_installed_commit(self):
        """Get the currently installed commit hash"""
        try:
            import json
            # Try to read from installed_version.json in project root
            version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'installed_version.json')
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    return data.get('commit_hash')
            else:
                # File doesn't exist - automatically create it with current latest commit
                print("🔄 First run detected - marking current version as installed...")
                if self._auto_create_installed_version():
                    # Try reading again after creation
                    with open(version_file, 'r') as f:
                        data = json.load(f)
                        return data.get('commit_hash')
        except Exception as e:
            print(f"Error reading installed version: {e}")
        return None  # Unknown version
    
    def _save_installed_commit_data(self, commit_data):
        """Save the complete commit data when user actually updates"""
        try:
            import json
            # Save in the project root directory
            version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'installed_version.json')
            
            # Save complete commit info
            save_data = {
                'commit_hash': commit_data['sha'][:7],
                'full_hash': commit_data['sha'],
                'message': commit_data['commit']['message'].split('\n')[0],
                'date': commit_data['commit']['committer']['date'],
                'updated_at': time.time()
            }
            
            with open(version_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            self.installed_commit = save_data['commit_hash']
            print(f"✅ Saved installed version: {save_data['commit_hash']} - {save_data['message']}")
            
        except Exception as e:
            print(f"Error saving installed version: {e}")

    def mark_current_as_installed(self):
        """Mark the current latest commit as installed (stops nagging)"""
        try:
            import requests
            import json
            
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                self._save_installed_commit_data(commit_data)
                return True
        except Exception as e:
            print(f"Error marking current version as installed: {e}")
        return False

    def _auto_create_installed_version(self):
        """Automatically create installed_version.json on first run"""
        try:
            import requests
            import json
            
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                self._save_installed_commit_data(commit_data)
                print("✅ Automatically marked current version as installed!")
                return True
        except Exception as e:
            print(f"Error auto-creating installed version: {e}")
        return False

    def should_update(self, commit_hash):
        """Check if we should update - only if it's a different commit than installed"""
        # If we don't know what's installed, don't spam with updates
        if not self.installed_commit:
            return False
        
        # Only update if it's actually a different commit
        return commit_hash != self.installed_commit

    def prompt_update(self, commit_hash, commit_message):
        """Prompt user about available update"""
        # Don't show update dialog while main loop is running
        if self.app.main_loop_active:
            # Store the update info to show later
            self.pending_update = {'commit_hash': commit_hash, 'commit_message': commit_message}
            self.app.update_status('Update available - will prompt when fishing stops', 'info', '🔄')
            return
        
        message = f"New update available!\\n\\nLatest commit: {commit_hash}\\nChanges: {commit_message}\\n\\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download_update()
        else:
            self.app.update_status('Update skipped', 'warning', '⏭️')

    def show_pending_update(self):
        """Show the pending update dialog that was delayed during fishing"""
        if not self.pending_update:
            return
            
        commit_hash = self.pending_update['commit_hash']
        commit_message = self.pending_update['commit_message']
        
        message = f"Update available (found while fishing)!\\n\\nLatest commit: {commit_hash}\\nChanges: {commit_message}\\n\\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download_update()
        else:
            self.app.update_status('Update skipped', 'warning', '⏭️')
        
        self.pending_update = None

    def startup_update_check(self):
        """Check for updates immediately on startup (bypasses interval check)"""
        if not hasattr(self.app, 'auto_update_enabled') or not self.app.auto_update_enabled or self.app.main_loop_active:
            return
            
        # Reset the last check time to force immediate check
        self.last_check = 0
        threading.Thread(target=self.immediate_update_check, daemon=True).start()

    def immediate_update_check(self):
        """Perform update check without interval restrictions"""
        try:
            import requests
            
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                commit_hash = commit_data['sha'][:7]
                commit_message = commit_data['commit']['message'].split('\n')[0]
                
                if self.should_update(commit_hash):
                    self.app.root.after(0, lambda: self.prompt_update(commit_hash, commit_message))
                else:
                    self.app.root.after(0, lambda: self.app.update_status('Up to date!', 'success', '✅'))
            else:
                self.app.root.after(0, lambda: self.app.update_status('Update check failed', 'error', '❌'))
                
        except Exception as e:
            self.app.root.after(0, lambda: self.app.update_status(f'Update check error: {str(e)[:30]}...', 'error', '❌'))

    def download_update(self):
        """Download and apply update automatically while preserving user settings"""
        try:
            import requests
            import zipfile
            import tempfile
            import shutil
            from datetime import datetime
            
            self.app.update_status('Downloading update...', 'info', '⬇️')
            
            # First, get the latest commit info to save after successful update
            commit_response = requests.get(self.repo_url, timeout=10)
            latest_commit_data = None
            if commit_response.status_code == 200:
                latest_commit_data = commit_response.json()
            
            # Download the latest version
            zip_url = "https://github.com/arielldev/gpo-fishing/archive/refs/heads/main.zip"
            response = requests.get(zip_url, timeout=60)
            
            if response.status_code == 200:
                # Create temporary directory for extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "update.zip")
                    
                    # Save the zip file
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find the extracted folder
                    extracted_folder = None
                    for item in os.listdir(temp_dir):
                        if os.path.isdir(os.path.join(temp_dir, item)) and 'gpo-fishing' in item:
                            extracted_folder = os.path.join(temp_dir, item)
                            break
                    
                    if not extracted_folder:
                        self.app.update_status('Update extraction failed', 'error', '❌')
                        return
                    
                    # Files to preserve during update
                    preserve_files = ['default_settings.json', 'presets/', '.git/', '.gitignore']
                    
                    # Create backup of current version
                    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    backup_dir = os.path.join(current_dir, f"backup_{backup_timestamp}")
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    # Backup current files
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
                    
                    # Check if requirements.txt will be updated
                    requirements_updated = False
                    old_requirements_path = os.path.join(current_dir, 'requirements.txt')
                    new_requirements_path = os.path.join(extracted_folder, 'requirements.txt')
                    
                    if os.path.exists(old_requirements_path) and os.path.exists(new_requirements_path):
                        with open(old_requirements_path, 'r') as f:
                            old_requirements = f.read()
                        with open(new_requirements_path, 'r') as f:
                            new_requirements = f.read()
                        requirements_updated = old_requirements != new_requirements
                    
                    # Copy new files, preserving specified files
                    for item in os.listdir(extracted_folder):
                        src = os.path.join(extracted_folder, item)
                        dst = os.path.join(current_dir, item)
                        
                        # Skip preserved files
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
                    
                    # Update requirements if they changed
                    if requirements_updated:
                        self.app.update_status('Updating dependencies...', 'info', '📦')
                        self._update_requirements()
                    
                    # Save the complete commit data so we never ask for this update again
                    if latest_commit_data:
                        self._save_installed_commit_data(latest_commit_data)
                    
                    self.app.update_status('Update installed! Restarting...', 'success', '✅')
                    self.app.root.after(2000, self._restart)
                    
            else:
                self.app.update_status('Download failed', 'error', '❌')
                
        except Exception as e:
            self.app.update_status(f'Update error: {str(e)[:30]}...', 'error', '❌')

    def _update_requirements(self):
        """Update Python packages from requirements.txt"""
        try:
            import subprocess
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_path = os.path.join(current_dir, 'requirements.txt')
            
            if os.path.exists(requirements_path):
                # Try to update requirements
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', requirements_path, '--upgrade'
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("Requirements updated successfully")
                else:
                    print(f"Requirements update failed: {result.stderr}")
            
        except Exception as e:
            print(f"Error updating requirements: {e}")

    def _restart(self):
        """Restart the application"""
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

    def start_auto_update_loop(self):
        """Start the auto-update checking loop"""
        if hasattr(self.app, 'auto_update_enabled') and self.app.auto_update_enabled and not self.app.main_loop_active:
            threading.Thread(target=self.check_for_updates, daemon=True).start()
        
        # Schedule next check
        if hasattr(self.app, 'auto_update_enabled') and self.app.auto_update_enabled:
            self.app.root.after(self.check_interval * 1000, self.start_auto_update_loop)