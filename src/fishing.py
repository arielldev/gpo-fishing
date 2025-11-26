import threading
import time
import mss
import numpy as np
import win32api
import win32con
import keyboard

class FishingBot:
    def __init__(self, app):
        self.app = app
        self.recovery_in_progress = False
        self.watchdog_active = False
        self.watchdog_thread = None
        self.last_loop_heartbeat = time.time()
        self.force_stop_flag = False
    
    def check_recovery_needed(self):
        """Smart recovery check - detects genuinely stuck states"""
        if not self.app.recovery_enabled or not self.app.main_loop_active or self.recovery_in_progress:
            return False
            
        current_time = time.time()
        
        # Check every 20 seconds
        if current_time - self.app.last_smart_check < 20.0:
            return False
            
        self.app.last_smart_check = current_time
        
        # Check if current state has been running too long
        state_duration = current_time - self.app.state_start_time
        
        # Reasonable timeouts for each state
        max_durations = {
            "idle": 45.0,           # Between fishing cycles
            "fishing": 90.0,        # Active fishing with fish control
            "casting": 20.0,        # Casting the line
            "menu_opening": 15.0,   # Opening purchase menu
            "typing": 10.0,         # Typing purchase amount
            "clicking": 8.0,        # Individual clicks
            "purchasing": 60.0      # Full purchase sequence
        }
        
        max_duration = max_durations.get(self.app.current_state, 60.0)
        
        if state_duration > max_duration:
            self.app.log(f'🚨 State "{self.app.current_state}" stuck for {state_duration:.0f}s (max: {max_duration}s)', "error")
            return True
            
        # Check for complete activity freeze
        time_since_activity = current_time - self.app.last_activity_time
        if time_since_activity > 120:  # 2 minutes of no activity
            self.app.log(f'⚠️ No activity for {time_since_activity:.0f}s - loop may be frozen', "error")
            return True
            
        return False
    
    def start_watchdog(self):
        """Start aggressive watchdog that monitors from OUTSIDE the main loop"""
        if self.watchdog_active:
            return
            
        self.watchdog_active = True
        self.last_loop_heartbeat = time.time()
        self.watchdog_thread = threading.Thread(target=self._watchdog_monitor, daemon=True)
        self.watchdog_thread.start()
        self.app.log('🐕 Watchdog started - monitoring for stuck states', "verbose")
    
    def stop_watchdog(self):
        """Stop the watchdog"""
        self.watchdog_active = False
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=2.0)
    
    def _watchdog_monitor(self):
        """Smart watchdog that monitors for stuck states and restarts the loop"""
        while self.watchdog_active and self.app.main_loop_active:
            try:
                current_time = time.time()
                
                # Check heartbeat from main loop
                heartbeat_age = current_time - self.last_loop_heartbeat
                
                # Trigger recovery if no heartbeat for 30 seconds
                if heartbeat_age > 30.0:
                    self.app.log(f'🚨 WATCHDOG: No heartbeat for {heartbeat_age:.0f}s - Loop appears stuck', "error")
                    self._restart_fishing_loop()
                    break
                
                # Check for stuck states
                if self.check_recovery_needed():
                    self.app.log('🚨 WATCHDOG: Stuck state detected - Restarting loop', "error")
                    self._restart_fishing_loop()
                    break
                
                time.sleep(10.0)  # Check every 10 seconds
                
            except Exception as e:
                self.app.log(f'⚠️ Watchdog error: {e}', "error")
                time.sleep(10.0)
        
        self.app.log('🐕 Watchdog stopped', "verbose")
    
    def update_heartbeat(self):
        """Update heartbeat from main loop"""
        self.last_loop_heartbeat = time.time()
    
    def _restart_fishing_loop(self):
        """Restart the fishing loop when it gets stuck"""
        if self.recovery_in_progress:
            return
            
        current_time = time.time()
        
        # Limit restart attempts
        if self.app.recovery_count >= 5:
            self.app.log(f'🛑 TOO MANY RESTARTS: {self.app.recovery_count} attempts. Stopping fishing.', "error")
            self.app.main_loop_active = False
            self.watchdog_active = False
            return
        
        self.recovery_in_progress = True
        self.app.recovery_count += 1
        self.app.last_recovery_time = current_time
        
        self.app.log(f'🔄 RESTARTING LOOP #{self.app.recovery_count}/5 - Fishing got stuck', "important")
        
        # Clean up mouse state immediately
        try:
            if self.app.is_clicking:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.app.is_clicking = False
        except:
            pass
        
        # Set force stop flag to exit current loop
        self.force_stop_flag = True
        
        # Reset state
        self.app.last_activity_time = current_time
        self.app.last_fish_time = current_time
        self.app.set_recovery_state("idle", {"action": "loop_restart"})
        
        # Wait a moment for current loop to exit
        time.sleep(2.0)
        
        # Reset flags and restart
        self.force_stop_flag = False
        self.last_loop_heartbeat = time.time()
        
        # Start fresh loop
        self.app.log('🎣 Starting fresh fishing loop...', "important")
        self.app.main_loop_thread = threading.Thread(target=self.run_main_loop, daemon=True)
        self.app.main_loop_thread.start()
        
        self.recovery_in_progress = False

    def _force_recovery(self):
        """NUCLEAR OPTION: Force recovery when system is truly stuck"""
        if self.recovery_in_progress:
            return
            
        current_time = time.time()
        
        # Recovery limit
        if self.app.recovery_count >= 3:
            self.app.log(f'🛑 RECOVERY LIMIT REACHED: {self.app.recovery_count} attempts failed. STOPPING EVERYTHING.', "error")
            self.app.main_loop_active = False
            self.watchdog_active = False
            return
        
        self.recovery_in_progress = True
        self.app.recovery_count += 1
        self.app.last_recovery_time = current_time
        
        self.app.log(f'💥 FORCE RECOVERY #{self.app.recovery_count}/3 - NUKING EVERYTHING', "error")
        
        # Send webhook
        if hasattr(self.app, 'webhook_manager'):
            recovery_info = {
                "recovery_number": self.app.recovery_count,
                "stuck_state": self.app.current_state,
                "timestamp": current_time,
                "recovery_type": "FORCE_RECOVERY"
            }
            self.app.webhook_manager.send_recovery(recovery_info)
        
        # FORCE stop everything
        self.force_stop_flag = True
        self.app.main_loop_active = False
        
        # Release mouse IMMEDIATELY
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.app.is_clicking = False
        except:
            pass
        
        # Reset ALL state
        self.app.last_activity_time = current_time
        self.app.last_fish_time = current_time
        self.app.set_recovery_state("idle", {"action": "force_recovery_reset"})
        
        # AGGRESSIVE thread cleanup - don't wait nicely
        self.app.log('💥 FORCE KILLING main loop thread...', "verbose")
        time.sleep(1.0)  # Brief pause for force_stop_flag to take effect
        
        # Try to join thread, but don't wait forever
        try:
            if hasattr(self.app, 'main_loop_thread') and self.app.main_loop_thread and self.app.main_loop_thread.is_alive():
                self.app.main_loop_thread.join(timeout=3.0)
                if self.app.main_loop_thread.is_alive():
                    self.app.log('⚠️ Thread refused to die - continuing anyway', "error")
        except:
            pass
        
        # RESTART FROM SCRATCH
        if self.app.recovery_count < 3:
            self.app.log('💥 RESTARTING FROM SCRATCH...', "important")
            
            # Reset flags
            self.force_stop_flag = False
            self.last_loop_heartbeat = time.time()
            
            # Start fresh
            self.app.main_loop_active = True
            self.app.main_loop_thread = threading.Thread(target=self.run_main_loop, daemon=True)
            self.app.main_loop_thread.start()
            
            self.app.log('✅ FORCE RECOVERY COMPLETE - Fresh start initiated', "important")
        
        self.recovery_in_progress = False
    
    def perform_recovery(self):
        """Legacy recovery method - now just calls force recovery"""
        self._force_recovery()
    
    def cast_line(self):
        """Cast fishing line"""
        self.app.cast_line()
    
    def check_and_purchase(self):
        """Check if auto-purchase is needed"""
        if getattr(self.app, 'auto_purchase_var', None) and self.app.auto_purchase_var.get():
            self.app.purchase_counter += 1
            loops_needed = int(getattr(self.app, 'loops_per_purchase', 1)) if getattr(self.app, 'loops_per_purchase', None) is not None else 1
            print(f'🛒 Purchase counter: {self.app.purchase_counter}/{loops_needed}')
            if self.app.purchase_counter >= max(1, loops_needed):
                try:
                    print('🛒 Performing auto-purchase...')
                    self.perform_auto_purchase()
                    self.app.purchase_counter = 0
                    print('🛒 Auto-purchase complete')
                except Exception as e:
                    print(f'❌ AUTO-PURCHASE ERROR: {e}')
    
    def perform_auto_purchase(self):
        """Perform auto-purchase sequence"""
        pts = self.app.point_coords
        
        # Convert points to tuples if they're lists (from JSON)
        for key in [1, 2, 3, 4]:
            if key in pts and pts[key] and isinstance(pts[key], list):
                pts[key] = tuple(pts[key])
        
        if not pts or not pts.get(1) or not pts.get(2) or not pts.get(3) or not pts.get(4):
            return
        
        if not self.app.main_loop_active:
            return
        
        amount = str(self.app.auto_purchase_amount)
        
        # Purchase sequence with state tracking
        self.app.set_recovery_state("menu_opening", {"action": "pressing_e_key"})
        keyboard.press_and_release('e')
        time.sleep(self.app.purchase_delay_after_key)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_1"})
        self._click_at(pts[1])
        time.sleep(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_2"})
        self._click_at(pts[2])
        time.sleep(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        # Double-click point 2 to ensure field is focused and selected
        self._click_at(pts[2])
        time.sleep(0.1)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("typing", {"action": "typing_amount"})
        # Type the amount
        keyboard.write(amount)
        # Extra delay to ensure typing is complete
        time.sleep(self.app.purchase_after_type_delay + 0.5)
        
        if not self.app.main_loop_active:
            return
        
        # Continue purchase sequence
        self.app.set_recovery_state("clicking", {"action": "click_point_1_confirm"})
        self._click_at(pts[1])
        time.sleep(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_3"})
        self._click_at(pts[3])
        time.sleep(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_2_final"})
        self._click_at(pts[2])
        time.sleep(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "right_click_point_4"})
        self._right_click_at(pts[4])
        time.sleep(self.app.purchase_click_delay)
        
        if hasattr(self.app, 'webhook_manager'):
            self.app.webhook_manager.send_purchase(amount)
        print()
    
    def _click_at(self, coords):
        """Click at coordinates"""
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception as e:
            pass
    
    def _right_click_at(self, coords):
        """Right click at coordinates"""
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
            threading.Event().wait(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            threading.Event().wait(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        except Exception as e:
            pass
    
    def run_main_loop(self):
        """Main fishing loop with aggressive monitoring"""
        print('🎣 Main loop started with watchdog protection')
        target_color = (85, 170, 255)
        dark_color = (25, 25, 25)
        white_color = (255, 255, 255)
        
        # Start watchdog for stuck state detection
        if not self.watchdog_active:
            self.start_watchdog()
        
        # Reset recovery count on fresh start
        if not self.recovery_in_progress:
            self.app.recovery_count = 0
        
        try:
            with mss.mss() as sct:
                # Auto-purchase at start if enabled
                if getattr(self.app, 'auto_purchase_var', None) and self.app.auto_purchase_var.get():
                    self.app.set_recovery_state("purchasing", {"sequence": "auto_purchase"})
                    self.perform_auto_purchase()
                
                # Main fishing loop
                # Main fishing loop
                while self.app.main_loop_active and not self.force_stop_flag:
                    # Update heartbeat for watchdog
                    self.update_heartbeat()
                    
                    # Check if loop should continue
                    if not self.app.main_loop_active:
                        print('🛑 Main loop stopped - main_loop_active is False')
                        break
                    if self.force_stop_flag:
                        print('🛑 Main loop stopped - force_stop_flag is True')
                        break
                    
                    try:
                        print(f'🎣 Fishing cycle #{self.app.fish_count + 1}')
                        
                        # Cast line
                        self.app.set_recovery_state("casting", {"action": "initial_cast"})
                        self.cast_line()
                        cast_time = time.time()
                        
                        # Enter detection phase
                        self.app.set_recovery_state("fishing", {"action": "blue_bar_detection"})
                        detected = False
                        was_detecting = False
                        print('Scanning for blue fishing bar...')
                        
                        detection_start_time = time.time()
                        while self.app.main_loop_active and not self.force_stop_flag:
                            # Update heartbeat frequently during detection
                            self.update_heartbeat()
                            
                            # Timeout check - if no fish detected for too long, recast
                            current_time = time.time()
                            if current_time - detection_start_time > self.app.scan_timeout:
                                if not detected:
                                    print(f'⏰ No fish detected after {self.app.scan_timeout}s, recasting...')
                                    break
                                elif current_time - detection_start_time > self.app.scan_timeout + 15:
                                    print(f'⏰ Fish control timeout after {self.app.scan_timeout + 15}s, recasting...')
                                    # Clean up mouse state before recasting
                                    if self.app.is_clicking:
                                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                        self.app.is_clicking = False
                                    break
                            
                            # Get screenshot with error handling
                            try:
                                x = self.app.overlay_area['x']
                                y = self.app.overlay_area['y']
                                width = self.app.overlay_area['width']
                                height = self.app.overlay_area['height']
                                monitor = {'left': x, 'top': y, 'width': width, 'height': height}
                                screenshot = sct.grab(monitor)
                                img = np.array(screenshot)
                            except Exception as screenshot_error:
                                print(f'❌ Screenshot error: {screenshot_error}')
                                time.sleep(0.1)
                                continue
                            
                            # Look for blue bar (target color) with error handling
                            try:
                                point1_x = None
                                point1_y = None
                                found_first = False
                                for row_idx in range(height):
                                    for col_idx in range(width):
                                        b, g, r = img[row_idx, col_idx, 0:3]
                                        if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                                            point1_x = x + col_idx
                                            point1_y = y + row_idx
                                            found_first = True
                                            break
                                    if found_first:
                                        break
                            except Exception as detection_error:
                                print(f'❌ Blue bar detection error: {detection_error}')
                                time.sleep(0.1)
                                continue
                            
                            if found_first:
                                detected = True
                            else:
                                # No blue bar found
                                if not detected and time.time() - cast_time > self.app.scan_timeout:
                                    print(f'Cast timeout after {self.app.scan_timeout}s, recasting...')
                                    break
                                
                                if was_detecting:
                                    print('Fish caught! Processing...')
                                    
                                    # Clean up mouse state immediately
                                    if self.app.is_clicking:
                                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                        self.app.is_clicking = False
                                    
                                    # Increment fish counter when fish is actually caught
                                    self.app.increment_fish_counter()
                                    time.sleep(self.app.wait_after_loss)
                                    was_detecting = False
                                    self.check_and_purchase()
                                    # Continue to next fishing cycle
                                    print('🐟 Fish processing complete')
                                    break
                                
                                time.sleep(0.1)
                                continue
                            
                            # Find right edge of blue bar
                            point2_x = None
                            row_idx = point1_y - y
                            for col_idx in range(width - 1, -1, -1):
                                b, g, r = img[row_idx, col_idx, 0:3]
                                if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                                    point2_x = x + col_idx
                                    break
                            
                            if point2_x is None:
                                time.sleep(0.1)
                                continue
                            
                            # Get the fishing bar area
                            temp_area_x = point1_x
                            temp_area_width = point2_x - point1_x + 1
                            temp_monitor = {'left': temp_area_x, 'top': y, 'width': temp_area_width, 'height': height}
                            temp_screenshot = sct.grab(temp_monitor)
                            temp_img = np.array(temp_screenshot)
                            
                            # Find top and bottom of dark area
                            top_y = None
                            for row_idx in range(height):
                                found_dark = False
                                for col_idx in range(temp_area_width):
                                    b, g, r = temp_img[row_idx, col_idx, 0:3]
                                    if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                        top_y = y + row_idx
                                        found_dark = True
                                        break
                                if found_dark:
                                    break
                            
                            bottom_y = None
                            for row_idx in range(height - 1, -1, -1):
                                found_dark = False
                                for col_idx in range(temp_area_width):
                                    b, g, r = temp_img[row_idx, col_idx, 0:3]
                                    if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                        bottom_y = y + row_idx
                                        found_dark = True
                                        break
                                if found_dark:
                                    break
                            
                            if top_y is None or bottom_y is None:
                                time.sleep(0.1)
                                continue
                            
                            # Get the real fishing area
                            self.app.real_area = {'x': temp_area_x, 'y': top_y, 'width': temp_area_width, 'height': bottom_y - top_y + 1}
                            real_x = self.app.real_area['x']
                            real_y = self.app.real_area['y']
                            real_width = self.app.real_area['width']
                            real_height = self.app.real_area['height']
                            real_monitor = {'left': real_x, 'top': real_y, 'width': real_width, 'height': real_height}
                            real_screenshot = sct.grab(real_monitor)
                            real_img = np.array(real_screenshot)
                            
                            # Find white indicator
                            white_top_y = None
                            white_bottom_y = None
                            for row_idx in range(real_height):
                                for col_idx in range(real_width):
                                    b, g, r = real_img[row_idx, col_idx, 0:3]
                                    if r == white_color[0] and g == white_color[1] and b == white_color[2]:
                                        white_top_y = real_y + row_idx
                                        break
                                if white_top_y is not None:
                                    break
                            
                            for row_idx in range(real_height - 1, -1, -1):
                                for col_idx in range(real_width):
                                    b, g, r = real_img[row_idx, col_idx, 0:3]
                                    if r == white_color[0] and g == white_color[1] and b == white_color[2]:
                                        white_bottom_y = real_y + row_idx
                                        break
                                if white_bottom_y is not None:
                                    break
                            
                            if white_top_y is not None and white_bottom_y is not None:
                                white_height = white_bottom_y - white_top_y + 1
                                max_gap = white_height * 2
                            
                            # Find dark sections (fish position)
                            dark_sections = []
                            current_section_start = None
                            gap_counter = 0
                            for row_idx in range(real_height):
                                has_dark = False
                                for col_idx in range(real_width):
                                    b, g, r = real_img[row_idx, col_idx, 0:3]
                                    if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                        has_dark = True
                                        break
                                if has_dark:
                                    gap_counter = 0
                                    if current_section_start is None:
                                        current_section_start = real_y + row_idx
                                else:
                                    if current_section_start is not None:
                                        gap_counter += 1
                                        if gap_counter > max_gap:
                                            section_end = real_y + row_idx - gap_counter
                                            dark_sections.append({'start': current_section_start, 'end': section_end, 'middle': (current_section_start + section_end) // 2})
                                            current_section_start = None
                                            gap_counter = 0
                            
                            if current_section_start is not None:
                                section_end = real_y + real_height - 1 - gap_counter
                                dark_sections.append({'start': current_section_start, 'end': section_end, 'middle': (current_section_start + section_end) // 2})
                            
                            # Control the fishing
                            if dark_sections and white_top_y is not None:
                                if not was_detecting:
                                    # First time detecting fish - don't increment counter yet
                                    print('Fish detected! Starting control...')
                                    self.app.set_recovery_state("fishing", {"action": "fish_control_active"})
                                was_detecting = True
                                
                                # Calculate error and control
                                for section in dark_sections:
                                    section['size'] = section['end'] - section['start'] + 1
                                largest_section = max(dark_sections, key=lambda s: s['size'])
                                
                                raw_error = largest_section['middle'] - white_top_y
                                normalized_error = raw_error / real_height if real_height > 0 else raw_error
                                derivative = normalized_error - self.app.previous_error
                                self.app.previous_error = normalized_error
                                pd_output = self.app.kp * normalized_error + self.app.kd * derivative
                                
                                print(f'Error: {raw_error}px, PD: {pd_output:.2f}')
                                
                                # Control mouse
                                if pd_output > 0:
                                    if not self.app.is_clicking:
                                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                        self.app.is_clicking = True
                                else:
                                    if self.app.is_clicking:
                                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                        self.app.is_clicking = False
                            
                            time.sleep(0.1)
                        
                        self.app.set_recovery_state("idle", {"action": "detection_complete"})
                        
                    except Exception as e:
                        print(f'🚨 Main loop error: {e}')
                        import traceback
                        traceback.print_exc()
                        self.app.log(f'Main loop error: {e}', "error")
                        if not self.force_stop_flag:
                            time.sleep(1.0)
                        else:
                            break  # Exit immediately on force stop
        
        except Exception as e:
            self.app.log(f'🚨 Critical main loop error: {e}', "error")
        
        finally:
            # ALWAYS clean up
            print('🛑 Main loop stopped - cleaning up')
            
            # Stop watchdog
            self.stop_watchdog()
            
            # Clean up mouse state
            if self.app.is_clicking:
                try:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.app.is_clicking = False
                except:
                    pass