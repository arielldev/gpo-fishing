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
    
    def check_recovery_needed(self):
        """smart recovery - detects specific stuck actions with detailed logging"""
        if not self.app.recovery_enabled or not self.app.main_loop_active:
            return False
            
        current_time = time.time()
        
        # Check more frequently for faster recovery (every 10 seconds instead of 15)
        if current_time - self.app.last_smart_check < 10.0:
            return False
            
        self.app.last_smart_check = current_time
        
        # Check if current state has been running too long
        state_duration = current_time - self.app.state_start_time
        max_duration = self.app.max_state_duration.get(self.app.current_state, 60.0)
        
        # More aggressive timeout for idle state (common stuck state)
        if self.app.current_state == "idle" and state_duration > 30.0:  # Reduced from 45s to 30s
            max_duration = 30.0
        
        if state_duration > max_duration:
            # Create detailed stuck action report
            stuck_info = {
                "action": self.app.current_state,
                "duration": state_duration,
                "max_allowed": max_duration,
                "details": self.app.state_details.copy(),
                "timestamp": current_time
            }
            self.app.stuck_actions.append(stuck_info)
            
            # Log with different levels based on action type
            if self.app.current_state == "fishing":
                # Blue bar detection rarely gets stuck, this is unusual
                self.app.log(f'🚨 UNUSUAL: Fishing state stuck for {state_duration:.0f}s (blue bar detection issue?)', "error")
            elif self.app.current_state == "purchasing":
                self.app.log(f'⚠️ Purchase sequence stuck for {state_duration:.0f}s - likely menu/UI issue', "error")
            elif self.app.current_state == "menu_opening":
                self.app.log(f'⚠️ Menu opening stuck for {state_duration:.0f}s - E key or game response issue', "error")
            elif self.app.current_state == "typing":
                self.app.log(f'⚠️ Typing stuck for {state_duration:.0f}s - input field or keyboard issue', "error")
            elif self.app.current_state == "clicking":
                self.app.log(f'⚠️ Click action stuck for {state_duration:.0f}s - UI element or mouse issue', "error")
            elif self.app.current_state == "idle":
                self.app.log(f'🚨 IDLE STUCK: System idle for {state_duration:.0f}s - main loop may be frozen', "error")
            else:
                self.app.log(f'⚠️ State "{self.app.current_state}" stuck for {state_duration:.0f}s (max: {max_duration}s)', "error")
            
            # Dev mode detailed logging
            if self.app.dev_mode or self.app.verbose_logging:
                self.app.log(f'🔍 DEV: Stuck action details: {stuck_info}', "verbose")
            
            return True
            
        # More aggressive check for completely frozen state (reduced from 2 minutes to 90 seconds)
        time_since_activity = current_time - self.app.last_activity_time
        if time_since_activity > 90:  # 90 seconds instead of 120
            self.app.log(f'⚠️ Complete freeze detected - no activity for {time_since_activity:.0f}s', "error")
            return True
            
        return False
    
    def perform_recovery(self):
        """smart recovery with detailed logging and webhook notifications"""
        if not self.app.main_loop_active:
            return
            
        current_time = time.time()
        
        # Prevent spam recovery (reduced from 15 to 10 seconds for faster response)
        if current_time - self.app.last_recovery_time < 10:
            return
            
        self.app.recovery_count += 1
        self.app.last_recovery_time = current_time
        
        # Create detailed recovery report
        recovery_info = {
            "recovery_number": self.app.recovery_count,
            "stuck_state": self.app.current_state,
            "stuck_duration": current_time - self.app.state_start_time,
            "state_details": self.app.state_details.copy(),
            "recent_stuck_actions": self.app.stuck_actions[-3:] if len(self.app.stuck_actions) > 0 else [],
            "timestamp": current_time
        }
        
        self.app.log(f'🔄 Smart Recovery #{self.app.recovery_count} - State: {self.app.current_state} - Restarting...', "error")
        
        # Dev mode detailed recovery logging
        if self.app.dev_mode or self.app.verbose_logging:
            self.app.log(f'🔍 DEV: Recovery details: {recovery_info}', "verbose")
        
        # Send webhook notification about recovery
        self.app.webhook_manager.send_recovery(recovery_info)
        
        # Force release mouse if stuck clicking
        if self.app.is_clicking:
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.app.is_clicking = False
                self.app.log('🔧 Released stuck mouse click', "verbose")
            except Exception as e:
                self.app.log(f'⚠️ Error releasing mouse: {e}', "error")
        
        # Reset all timers and state
        self.app.last_activity_time = current_time
        self.app.last_fish_time = current_time
        self.app.set_recovery_state("idle", {"action": "recovery_reset"})
        self.app.stuck_actions.clear()  # Clear stuck actions after recovery
        
        # Stop current loop
        self.app.main_loop_active = False
        
        # Wait a moment for cleanup
        threading.Event().wait(2.0)  # Increased wait time for better cleanup
        
        # Restart the loop with better error handling
        try:
            if hasattr(self.app, 'main_loop_thread') and self.app.main_loop_thread and self.app.main_loop_thread.is_alive():
                self.app.main_loop_thread.join(timeout=5.0)  # Increased timeout
        except Exception as e:
            self.app.log(f'⚠️ Error joining thread: {e}', "error")
        
        # Restart with fresh state
        self.app.main_loop_active = True
        self.app.main_loop_thread = threading.Thread(target=self.run_main_loop, daemon=True)
        self.app.main_loop_thread.start()
        
        self.app.log('✅ Smart Recovery complete - Enhanced monitoring active', "important")
    
    def cast_line(self):
        """Delegate to app's cast_line method"""
        self.app.cast_line()
    
    def check_and_purchase(self):
        if getattr(self.app, 'auto_purchase_var', None) and self.app.auto_purchase_var.get():
            self.app.purchase_counter += 1
            loops_needed = int(getattr(self.app, 'loops_per_purchase', 1)) if getattr(self.app, 'loops_per_purchase', None) is not None else 1
            print(f'🔄 Purchase counter: {self.app.purchase_counter}/{loops_needed}')
            if self.app.purchase_counter >= max(1, loops_needed):
                try:
                    self.perform_auto_purchase()
                    self.app.purchase_counter = 0
                except Exception as e:
                    print(f'❌ AUTO-PURCHASE ERROR: {e}')
    
    def perform_auto_purchase(self):
        pts = self.app.point_coords
        if not pts or not pts.get(1) or not pts.get(2) or not pts.get(3) or not pts.get(4):
            print('Auto purchase aborted: points not fully set (need points 1-4).')
            return
        
        if not self.app.main_loop_active:
            print('Auto purchase aborted: main loop stopped.')
            return
        
        amount = str(self.app.auto_purchase_amount)
        
        self.app.set_recovery_state("menu_opening", {"action": "pressing_e_key", "amount": amount})
        self.app.log('Pressing E key...', "verbose")
        keyboard.press_and_release('e')
        threading.Event().wait(self.app.purchase_delay_after_key)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_1", "point": pts[1]})
        self.app.log(f'Clicking Point 1: {pts[1]}', "verbose")
        self._click_at(pts[1])
        threading.Event().wait(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_2", "point": pts[2]})
        self.app.log(f'Clicking Point 2: {pts[2]}', "verbose")
        self._click_at(pts[2])
        threading.Event().wait(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("typing", {"action": "typing_amount", "amount": amount})
        self.app.log(f'Typing amount: {amount}', "verbose")
        keyboard.write(amount)
        threading.Event().wait(self.app.purchase_after_type_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_1_confirm", "point": pts[1]})
        print(f'Clicking Point 1: {pts[1]}')
        self._click_at(pts[1])
        threading.Event().wait(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_3", "point": pts[3]})
        print(f'Clicking Point 3: {pts[3]}')
        self._click_at(pts[3])
        threading.Event().wait(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "click_point_2_final", "point": pts[2]})
        print(f'Clicking Point 2: {pts[2]}')
        self._click_at(pts[2])
        threading.Event().wait(self.app.purchase_click_delay)
        
        if not self.app.main_loop_active:
            return
        
        self.app.set_recovery_state("clicking", {"action": "right_click_point_4_close", "point": pts[4]})
        print(f'Right-clicking Point 4: {pts[4]}')
        self._right_click_at(pts[4])
        threading.Event().wait(self.app.purchase_click_delay)
        
        self.app.webhook_manager.send_purchase(amount)
        print()
    
    def _click_at(self, coords):
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass
        except Exception as e:
            print(f'Error clicking at {coords}: {e}')
    
    def _right_click_at(self, coords):
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            except Exception:
                pass
        except Exception as e:
            print(f'Error right-clicking at {coords}: {e}')
    
    def run_main_loop(self):
        print('Main loop started')
        target_color = (85, 170, 255)
        dark_color = (25, 25, 25)
        white_color = (255, 255, 255)
        
        self.app.dev_mode = self.app.verbose_logging
        
        with mss.mss() as sct:
            if getattr(self.app, 'auto_purchase_var', None) and self.app.auto_purchase_var.get():
                self.app.set_recovery_state("purchasing", {"sequence": "auto_purchase", "loops_per_purchase": getattr(self.app, 'loops_per_purchase', 1)})
                self.perform_auto_purchase()
            
            while self.app.main_loop_active:
                try:
                    self.app.set_recovery_state("casting", {"action": "initial_cast"})
                    self.cast_line()
                    cast_time = time.time()
                    
                    self.app.set_recovery_state("fishing", {"action": "blue_bar_detection", "scan_timeout": self.app.scan_timeout})
                    detected = False
                    last_detection_time = time.time()
                    was_detecting = False
                    print('Entering main detection loop with smart monitoring...')
                    
                    detection_start_time = time.time()
                    while self.app.main_loop_active:
                        if self.check_recovery_needed():
                            self.perform_recovery()
                            return
                        
                        current_time = time.time()
                        if current_time - detection_start_time > self.app.scan_timeout + 10:
                            print(f'🚨 FORCE TIMEOUT: Detection loop exceeded {self.app.scan_timeout + 10}s, breaking...')
                            self.app.set_recovery_state("idle", {"action": "force_timeout_break"})
                            break
                        
                        x = self.app.overlay_area['x']
                        y = self.app.overlay_area['y']
                        width = self.app.overlay_area['width']
                        height = self.app.overlay_area['height']
                        monitor = {'left': x, 'top': y, 'width': width, 'height': height}
                        screenshot = sct.grab(monitor)
                        img = np.array(screenshot)
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
                        current_time = time.time()
                        
                        if found_first:
                            detected = True
                            last_detection_time = current_time
                        else:
                            if not detected and current_time - cast_time > self.app.scan_timeout:
                                print(f'Cast timeout after {self.app.scan_timeout}s, recasting...')
                                self.app.set_recovery_state("casting", {"action": "recast_after_timeout", "timeout_duration": self.app.scan_timeout})
                                break
                            
                            if was_detecting:
                                print('Lost detection, waiting...')
                                threading.Event().wait(self.app.wait_after_loss)
                                was_detecting = False
                                self.check_and_purchase()
                                self.app.set_recovery_state("idle", {"action": "fish_caught_processing"})
                                break
                            
                            threading.Event().wait(0.1)
                            continue
                        point2_x = None
                        row_idx = point1_y - y
                        for col_idx in range(width - 1, -1, -1):
                            b, g, r = img[row_idx, col_idx, 0:3]
                            if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                                point2_x = x + col_idx
                                break
                        if point2_x is None:
                            threading.Event().wait(0.1)
                            continue
                        temp_area_x = point1_x
                        temp_area_width = point2_x - point1_x + 1
                        temp_monitor = {'left': temp_area_x, 'top': y, 'width': temp_area_width, 'height': height}
                        temp_screenshot = sct.grab(temp_monitor)
                        temp_img = np.array(temp_screenshot)
                        dark_color = (25, 25, 25)
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
                            threading.Event().wait(0.1)
                            continue
                        self.app.real_area = {'x': temp_area_x, 'y': top_y, 'width': temp_area_width, 'height': bottom_y - top_y + 1}
                        real_x = self.app.real_area['x']
                        real_y = self.app.real_area['y']
                        real_width = self.app.real_area['width']
                        real_height = self.app.real_area['height']
                        real_monitor = {'left': real_x, 'top': real_y, 'width': real_width, 'height': real_height}
                        real_screenshot = sct.grab(real_monitor)
                        real_img = np.array(real_screenshot)
                        white_color = (255, 255, 255)
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
                        if dark_sections and white_top_y is not None:
                            if not was_detecting:
                                self.app.increment_fish_counter()
                                self.app.set_recovery_state("idle")
                            was_detecting = True
                            last_detection_time = time.time()
                            for section in dark_sections:
                                section['size'] = section['end'] - section['start'] + 1
                            largest_section = max(dark_sections, key=lambda s: s['size'])
                            print(f'y:{white_top_y}')
                            print(f"y:{largest_section['middle']}")
                            raw_error = largest_section['middle'] - white_top_y
                            normalized_error = raw_error / real_height if real_height > 0 else raw_error
                            derivative = normalized_error - self.app.previous_error
                            self.app.previous_error = normalized_error
                            pd_output = self.app.kp * normalized_error + self.app.kd * derivative
                            print(f'Error: {raw_error}px ({normalized_error:.3f} normalized), PD Output: {pd_output:.2f}')
                            
                            if pd_output > 0:
                                if not self.app.is_clicking:
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    self.app.is_clicking = True
                            else:
                                if self.app.is_clicking:
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                    self.app.is_clicking = False
                            
                            print()
                        threading.Event().wait(0.1)
                    
                    self.app.set_recovery_state("idle", {"action": "detection_loop_complete"})
                    
                except Exception as e:
                    print(f'🚨 Main loop error: {e}')
                    self.app.log(f'Main loop error: {e}', "error")
                    self.app.set_recovery_state("idle", {"action": "error_recovery", "error": str(e)})
                    threading.Event().wait(1.0)
                    
        print('Main loop stopped')
        
        if self.app.is_clicking:
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.app.is_clicking = False
            except:
                pass
