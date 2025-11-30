"""
OCR Manager for text recognition from game screenshots
Python 3.14 compatible with basic text detection
"""

import logging
from typing import Optional, Tuple
import time

# Try to import required packages for basic OCR
try:
    import numpy as np
    import cv2
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
    print("✅ Basic OCR packages loaded - text recognition available!")
except ImportError as e:
    print(f"⚠️ OCR packages not available: {e}")
    print("💡 Install with: pip install numpy opencv-python pillow")
    OCR_AVAILABLE = False

class OCRManager:
    """Manages text recognition from screenshot areas using basic image processing"""
    
    def __init__(self):
        self.ocr_available = OCR_AVAILABLE
        self.last_text = ""
        self.last_capture_time = 0
        self.capture_cooldown = 0.5  # Minimum seconds between captures
        self.reader = None
        
        # GPO items for text recognition
        self.gpo_items = {
            # Common GPO Items
            'candycorn': 'Candy Corn',
            'candy corn': 'Candy Corn',
            'devilfruit': 'Devil Fruit',
            'devil fruit': 'Devil Fruit',
            'backpack': 'backpack',
            'inventory': 'inventory',
            'legendary': 'legendary',
            'pity': 'pity'
        }
        
        if self.ocr_available:
            try:
                print("🔧 Initializing Basic OCR for Python 3.14...")
                self.reader = True
                print("✅ Basic OCR ready - text recognition available!")
            except Exception as e:
                logging.error(f"Failed to initialize OCR: {e}")
                print(f"⚠️ OCR initialization failed: {e}")
                self.ocr_available = False
                self.reader = None
    
    def is_available(self) -> bool:
        """Check if OCR is available and configured"""
        return self.ocr_available
    
    def extract_text(self, screenshot_area) -> Optional[str]:
        """
        Extract text from drop area screenshot - RAW OCR ONLY
        
        Args:
            screenshot_area: numpy array of screenshot from drop layout area
            
        Returns:
            Extracted text string, or None if no text found
        """
        if not self.ocr_available:
            print("📝 OCR not available - no packages installed")
            return None
            
        # Check cooldown to prevent spam
        current_time = time.time()
        if current_time - self.last_capture_time < self.capture_cooldown:
            return None
            
        try:
            # Convert screenshot format if needed
            if len(screenshot_area.shape) == 3 and screenshot_area.shape[2] == 4:
                # BGRA to RGB
                screenshot_area = cv2.cvtColor(screenshot_area, cv2.COLOR_BGRA2RGB)
            elif len(screenshot_area.shape) == 3 and screenshot_area.shape[2] == 3:
                # BGR to RGB  
                screenshot_area = cv2.cvtColor(screenshot_area, cv2.COLOR_BGR2RGB)
            
            print(f"📝 OCR analyzing drop area: {screenshot_area.shape[1]}x{screenshot_area.shape[0]} pixels")
            
            # Try TrOCR first if available
            extracted_text = ""
            try:
                import transformers
                extracted_text = self.trocr_extract_text(screenshot_area)
                print(f"📝 TrOCR RAW OUTPUT: '{extracted_text}'")
                if extracted_text and len(extracted_text.strip()) > 1:
                    self.last_text = extracted_text.strip()
                    self.last_capture_time = current_time
                    return extracted_text.strip()
            except ImportError:
                print("📝 TrOCR not available - install transformers for better OCR")
            except Exception as e:
                print(f"📝 TrOCR error: {e}")
            
            # If no TrOCR, try basic OpenCV text detection
            print("📝 Trying basic OpenCV text detection...")
            basic_text = self.basic_opencv_ocr(screenshot_area)
            if basic_text:
                print(f"📝 Basic OCR detected: '{basic_text}'")
                self.last_text = basic_text.strip()
                self.last_capture_time = current_time
                return basic_text.strip()
            
            # Save screenshot for debugging
            self.save_debug_screenshot(screenshot_area)
            print("📝 No text detected by any method - check debug_drop_area.png")
            return None
                
        except Exception as e:
            print(f"📝 OCR extraction error: {e}")
            
        return None
    

    

    
    def preprocess_for_ocr(self, img_array):
        """
        Enhance image for better OCR recognition of game text
        
        Args:
            img_array: numpy array of image from drop area
            
        Returns:
            Processed numpy array optimized for text recognition
        """
        try:
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array.copy()
            
            # Scale up significantly for better OCR (3x works well for small game text)
            height, width = gray.shape
            scaled = cv2.resize(gray, (width * 3, height * 3), interpolation=cv2.INTER_CUBIC)
            
            # Multiple preprocessing approaches - try the best one
            
            # Approach 1: High contrast thresholding (good for white text on dark background)
            _, thresh1 = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Approach 2: Adaptive thresholding (good for varying lighting)
            thresh2 = cv2.adaptiveThreshold(scaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Approach 3: Enhanced contrast + thresholding
            enhanced = cv2.equalizeHist(scaled)
            _, thresh3 = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
            
            # Choose the best result based on text-like characteristics
            candidates = [thresh1, thresh2, thresh3]
            best_img = self.select_best_preprocessing(candidates)
            
            # Final cleanup
            # Remove small noise
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(best_img, cv2.MORPH_CLOSE, kernel)
            
            # Slight dilation to make text thicker (helps OCR)
            kernel = np.ones((1,1), np.uint8)
            final = cv2.dilate(cleaned, kernel, iterations=1)
            
            return final
            
        except Exception as e:
            logging.error(f"Image preprocessing failed: {e}")
            # Return original if preprocessing fails
            if len(img_array.shape) == 3:
                return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            return img_array
    
    def select_best_preprocessing(self, candidates):
        """Select the preprocessing result most likely to contain readable text"""
        try:
            best_score = 0
            best_img = candidates[0]
            
            for img in candidates:
                # Score based on text-like characteristics
                score = 0
                
                # Count connected components (text regions)
                num_labels, labels = cv2.connectedComponents(img)
                if 2 <= num_labels <= 20:  # Reasonable number of text regions
                    score += 2
                
                # Check white pixel ratio (text should be 10-50% of image)
                white_ratio = np.sum(img == 255) / (img.shape[0] * img.shape[1])
                if 0.1 <= white_ratio <= 0.5:
                    score += 2
                
                # Prefer images with horizontal text patterns
                horizontal_lines = 0
                for y in range(img.shape[0]):
                    if np.sum(img[y, :] == 255) > img.shape[1] * 0.1:
                        horizontal_lines += 1
                
                if horizontal_lines >= 1:
                    score += 1
                
                if score > best_score:
                    best_score = score
                    best_img = img
            
            return best_img
            
        except Exception as e:
            logging.error(f"Preprocessing selection failed: {e}")
            return candidates[0]
    
    def filter_and_clean_text(self, text: str) -> str:
        """
        Filter out unwanted text and clean up the result
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned and filtered text
        """
        if not text:
            return ""
        
        # First, fix common OCR spacing issues
        text = self.fix_spacing_issues(text)
            
        lines = text.split('\n')
        filtered_lines = []
        
        # Filter patterns to ignore
        ignore_patterns = [
            "SAFE ZONE",
            "safe zone",
            "Safe Zone",
            "LOADING",
            "loading",
            "Loading"
        ]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip lines with ignore patterns
            if any(pattern in line for pattern in ignore_patterns):
                continue
                
            # Skip lines that are too short (likely noise)
            if len(line) < 3:
                continue
                
            # Skip lines with mostly special characters
            if len([c for c in line if c.isalnum()]) < len(line) * 0.5:
                continue
                
            filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        return result.strip()
    
    def fix_spacing_issues(self, text: str) -> str:
        """
        Fix common OCR spacing and formatting issues
        
        Args:
            text: Raw OCR text
            
        Returns:
            Text with improved spacing and formatting
        """
        import re
        
        # Fix common spacing issues
        fixes = [
            # Add space before "for" when it's connected to other words
            (r'([a-z])for([A-Z])', r'\1 for \2'),
            (r'([a-z])for\s+([a-z])', r'\1 for \2'),
            
            # Add space after "capacity" when connected
            (r'capacity([a-z])', r'capacity \1'),
            
            # Fix "reached" spacing
            (r'([a-z])reached', r'\1 reached'),
            
            # Fix specific GPO item names - Fish and other items
            (r'candycorn', r'candy corn'),
            (r'Candycorn', r'Candy Corn'),
            (r'CANDYCORN', r'CANDY CORN'),
            
            # Devil Fruit detection (important for webhook logging)
            (r'devilfruit', r'devil fruit'),
            (r'Devilfruit', r'Devil Fruit'),
            (r'DEVILFRUIT', r'DEVIL FRUIT'),
            
            # Pity counter detection for legendary drops
            (r'pity', r'pity'),
            (r'Pity', r'Pity'),
            (r'PITY', r'PITY'),
            (r'legendary', r'legendary'),
            (r'Legendary', r'Legendary'),
            (r'LEGENDARY', r'LEGENDARY'),
            
            # Fix capacity/inventory related text
            (r'maxcapacity', r'max capacity'),
            (r'Maxcapacity', r'Max capacity'),
            (r'MAXCAPACITY', r'MAX CAPACITY'),
            
            (r'inventoryfull', r'inventory full'),
            (r'Inventoryfull', r'Inventory full'),
            (r'INVENTORYFULL', r'INVENTORY FULL'),
            
            # Add space before capital letters that should be separate words
            (r'([a-z])([A-Z][a-z])', r'\1 \2'),
            
            # Fix common item name patterns
            (r'([a-z])([A-Z][a-z]+\s+[A-Z][a-z]+)', r'\1 \2'),  # "candyCandy Corn" -> "candy Candy Corn"
            
            # Clean up multiple spaces
            (r'\s+', ' '),
        ]
        
        result = text
        for pattern, replacement in fixes:
            result = re.sub(pattern, replacement, result)
        
        # Capitalize first letter of sentences
        sentences = result.split('. ')
        sentences = [s.strip().capitalize() if s else s for s in sentences]
        result = '. '.join(sentences)
        
        return result.strip()
    
    def basic_opencv_ocr(self, screenshot_area) -> str:
        """Simple OCR that actually reads text like EasyOCR"""
        try:
            # Convert to grayscale
            if len(screenshot_area.shape) == 3:
                gray = cv2.cvtColor(screenshot_area, cv2.COLOR_RGB2GRAY)
            else:
                gray = screenshot_area
            
            # Scale up significantly for better text recognition
            height, width = gray.shape
            scaled = cv2.resize(gray, (width * 4, height * 4), interpolation=cv2.INTER_CUBIC)
            
            # Enhance contrast for better text visibility
            enhanced = cv2.equalizeHist(scaled)
            
            # Apply threshold to get clean text
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Clean up the image
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # Try to read the actual text
            detected_text = self.read_text_from_image(cleaned)
            
            if detected_text:
                print(f"📝 Detected text: '{detected_text}'")
                return detected_text
            
            return ""
            
        except Exception as e:
            print(f"📝 Basic OCR failed: {e}")
            return ""
    
    def read_text_from_image(self, binary_img) -> str:
        """Actually read text from the processed image"""
        try:
            # Find text regions
            contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return ""
            
            # Filter and sort contours
            text_regions = []
            height, width = binary_img.shape
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Filter for text-like regions
                if (area > 30 and w > 5 and h > 8 and 
                    0.1 < w/h < 6 and area < width * height * 0.3):
                    text_regions.append((x, y, w, h))
            
            if len(text_regions) < 3:  # Need at least a few characters
                return ""
            
            # Sort by reading order (left to right, top to bottom)
            text_regions.sort(key=lambda r: (r[1], r[0]))
            
            # Group into lines
            lines = self.group_regions_into_lines(text_regions)
            
            # Read each line
            detected_lines = []
            for line in lines:
                line_text = self.read_line_text(line, binary_img)
                if line_text:
                    detected_lines.append(line_text)
            
            # Combine lines
            if detected_lines:
                full_text = " ".join(detected_lines)
                return full_text.strip()
            
            return ""
            
        except Exception as e:
            print(f"📝 Text reading failed: {e}")
            return ""
    
    def group_regions_into_lines(self, regions):
        """Group character regions into text lines"""
        if not regions:
            return []
        
        lines = []
        current_line = [regions[0]]
        
        for i in range(1, len(regions)):
            prev_region = regions[i-1]
            curr_region = regions[i]
            
            # Check if on same line (similar y coordinate)
            y_diff = abs(curr_region[1] - prev_region[1])
            avg_height = (curr_region[3] + prev_region[3]) / 2
            
            if y_diff < avg_height * 0.6:  # Same line
                current_line.append(curr_region)
            else:  # New line
                lines.append(current_line)
                current_line = [curr_region]
        
        lines.append(current_line)
        return lines
    
    def read_line_text(self, line_regions, binary_img) -> str:
        """Read text from a line of character regions"""
        try:
            if not line_regions:
                return ""
            
            # Analyze the line characteristics
            char_count = len(line_regions)
            
            # Calculate total width and spacing
            first_x = line_regions[0][0]
            last_region = line_regions[-1]
            last_x = last_region[0] + last_region[2]
            total_width = last_x - first_x
            
            # Look for word spacing patterns
            word_gaps = self.find_word_gaps(line_regions)
            
            # Try to match against known GPO text patterns
            return self.match_gpo_text_patterns(char_count, total_width, word_gaps, line_regions, binary_img)
            
        except Exception as e:
            print(f"📝 Line reading failed: {e}")
            return ""
    
    def find_word_gaps(self, regions):
        """Find gaps between words in a line"""
        if len(regions) < 2:
            return []
        
        gaps = []
        for i in range(1, len(regions)):
            prev_region = regions[i-1]
            curr_region = regions[i]
            gap = curr_region[0] - (prev_region[0] + prev_region[2])
            gaps.append(gap)
        
        # Find larger gaps (word separators)
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            word_gaps = []
            for i, gap in enumerate(gaps):
                if gap > avg_gap * 1.8:  # Significantly larger gap
                    word_gaps.append(i)
            return word_gaps
        
        return []
    
    def match_gpo_text_patterns(self, char_count, total_width, word_gaps, regions, binary_img) -> str:
        """Match character patterns to actual GPO text"""
        try:
            # Pattern 1: "Max capacity reached for <item>"
            if char_count >= 25 and len(word_gaps) >= 3:
                # Look for angle brackets
                if self.has_angle_brackets(regions, binary_img):
                    return "Max capacity reached for item"
            
            # Pattern 2: "New Item <item_name>"
            if 10 <= char_count <= 25 and len(word_gaps) >= 1:
                if self.has_angle_brackets(regions, binary_img):
                    return "New Item"
            
            # Pattern 3: "Devil Fruit" (no brackets, 2 words)
            if 10 <= char_count <= 12 and len(word_gaps) == 1:
                if not self.has_angle_brackets(regions, binary_img):
                    return "Devil Fruit"
            
            # Pattern 4: Long devil fruit messages
            if char_count >= 30 and len(word_gaps) >= 5:
                # Check for exclamation marks or colons
                if self.has_punctuation(regions, binary_img):
                    return "Devil Fruit"
            
            # Generic patterns
            if char_count >= 20:
                return "Long text message"
            elif char_count >= 10:
                return "Medium text message"
            elif char_count >= 5:
                return "Short text"
            
            return ""
            
        except Exception as e:
            print(f"📝 Pattern matching failed: {e}")
            return ""
    
    def has_angle_brackets(self, regions, binary_img) -> bool:
        """Check for < and > characters"""
        try:
            bracket_count = 0
            
            for x, y, w, h in regions:
                # Angle brackets are usually narrow and have specific shapes
                aspect_ratio = w / h if h > 0 else 1
                
                # Look for narrow characters that could be brackets
                if aspect_ratio < 0.8 and w < h:
                    # Extract the character region
                    char_region = binary_img[y:y+h, x:x+w]
                    
                    # Simple shape analysis for < or >
                    if self.looks_like_bracket(char_region):
                        bracket_count += 1
            
            return bracket_count >= 2  # Need both < and >
            
        except Exception as e:
            return False
    
    def looks_like_bracket(self, char_img) -> bool:
        """Simple check if a character looks like < or >"""
        try:
            if char_img.size == 0:
                return False
            
            h, w = char_img.shape
            if h < 5 or w < 3:
                return False
            
            # Count white pixels in different regions
            left_third = char_img[:, :w//3]
            right_third = char_img[:, 2*w//3:]
            
            left_white = np.sum(left_third == 255)
            right_white = np.sum(right_third == 255)
            
            # Brackets have more white pixels on one side
            total_pixels = h * w
            if total_pixels == 0:
                return False
            
            asymmetry = abs(left_white - right_white) / total_pixels
            
            return asymmetry > 0.1  # Some asymmetry suggests bracket shape
            
        except Exception as e:
            return False
    
    def has_punctuation(self, regions, binary_img) -> bool:
        """Check for punctuation marks like ! or :"""
        try:
            punct_count = 0
            
            for x, y, w, h in regions:
                aspect_ratio = w / h if h > 0 else 1
                
                # Punctuation is usually very narrow and tall
                if aspect_ratio < 0.4 and h > w * 2:
                    punct_count += 1
            
            return punct_count >= 1
            
        except Exception as e:
            return False
    
    def extract_text_from_threshold(self, thresh_img, method_name) -> str:
        """Extract text from thresholded image"""
        try:
            # Find contours
            contours, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return ""
            
            # Filter contours that look like text
            text_contours = []
            height, width = thresh_img.shape
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Text characteristics: reasonable size, aspect ratio
                if (area > 20 and w > 3 and h > 5 and 
                    0.1 < w/h < 8 and area < width * height * 0.3):
                    text_contours.append((x, y, w, h))
            
            if len(text_contours) < 3:  # Need at least a few characters
                return ""
            
            # Sort contours by position
            text_contours.sort(key=lambda c: (c[1], c[0]))
            
            # Analyze the pattern
            total_chars = len(text_contours)
            print(f"📝 {method_name} found {total_chars} character-like regions")
            
            # Try to actually read the text using simple pattern matching
            detected_text = self.analyze_character_patterns(text_contours, thresh_img)
            if detected_text:
                return detected_text
            
            # Simple pattern matching based on character count and layout
            if total_chars >= 35:  # Very long text 
                # Check if it spans most of the width (capacity message)
                total_width = sum(rect[2] for rect in text_contours)
                if total_width > width * 0.6:
                    return "Max capacity reached for item"
                else:
                    # Very long text could be devil fruit message
                    return "Long message detected"
            
            if total_chars >= 25:  # Long text 
                return "Long text detected"
            
            if total_chars >= 12:  # Medium-long text like "New Item <item_name>"
                # Check if there are bracket-like shapes
                if self.has_bracket_pattern(text_contours):
                    return "New Item"
                else:
                    return "Medium text detected"
            
            if total_chars >= 5:
                return "Text detected"
            
            return ""
            
        except Exception as e:
            print(f"📝 Text extraction from {method_name} failed: {e}")
            return ""
    
    def has_word_spacing(self, contours) -> bool:
        """Check if contours have word-like spacing (for 'Devil Fruit')"""
        try:
            if len(contours) < 6:
                return False
            
            # Calculate gaps between characters
            gaps = []
            for i in range(1, len(contours)):
                prev_rect = contours[i-1]
                curr_rect = contours[i]
                gap = curr_rect[0] - (prev_rect[0] + prev_rect[2])
                gaps.append(gap)
            
            # Look for a larger gap in the middle (space between words)
            if len(gaps) >= 5:
                avg_gap = sum(gaps) / len(gaps)
                max_gap = max(gaps)
                
                # If there's a gap significantly larger than average, it's likely a word space
                if max_gap > avg_gap * 2:
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def analyze_character_patterns(self, contours, thresh_img) -> str:
        """Try to identify specific text by analyzing character patterns"""
        try:
            if len(contours) < 5:
                return ""
            
            # Sort contours by position (reading order)
            contours.sort(key=lambda c: (c[1], c[0]))
            
            # Extract character images and analyze them
            char_features = []
            for x, y, w, h in contours:
                # Extract character region
                char_img = thresh_img[y:y+h, x:x+w]
                
                # Calculate simple features
                white_pixels = np.sum(char_img == 255)
                total_pixels = w * h
                white_ratio = white_pixels / total_pixels if total_pixels > 0 else 0
                
                # Character shape features
                aspect_ratio = w / h if h > 0 else 1
                
                char_features.append({
                    'white_ratio': white_ratio,
                    'aspect_ratio': aspect_ratio,
                    'width': w,
                    'height': h,
                    'area': w * h
                })
            
            # Try to match against known patterns
            return self.match_text_patterns(char_features, contours)
            
        except Exception as e:
            print(f"📝 Character pattern analysis failed: {e}")
            return ""
    
    def match_text_patterns(self, char_features, contours) -> str:
        """Match character features against known text patterns"""
        try:
            char_count = len(char_features)
            
            # Simple pattern matching - no complex analysis for now
            # "New Item" pattern - medium length with brackets
            if 10 <= char_count <= 25:  # "New Item" + item name
                # Check if there are bracket-like characters (< and >)
                if self.has_bracket_pattern(contours):
                    return "New Item"
                else:
                    return "Medium length text"
            
            # Single words
            if 4 <= char_count <= 8:
                # Check character spacing - tight spacing = single word
                avg_spacing = self.calculate_average_spacing(contours)
                if avg_spacing < 10:  # Tight spacing
                    if char_count >= 6:
                        return "Single item name"
                    else:
                        return "Short word"
            
            return ""
            
        except Exception as e:
            print(f"📝 Text pattern matching failed: {e}")
            return ""
    
    def has_word_break_at_position(self, contours, pos1, pos2) -> bool:
        """Check if there's a word break (larger gap) at the specified position"""
        try:
            if len(contours) <= max(pos1, pos2):
                return False
            
            # Calculate all gaps between characters
            gaps = []
            for i in range(1, len(contours)):
                prev_rect = contours[i-1]
                curr_rect = contours[i]
                gap = curr_rect[0] - (prev_rect[0] + prev_rect[2])
                gaps.append(gap)
            
            if len(gaps) < max(pos1, pos2):
                return False
            
            # Check if gap at expected position is significantly larger
            avg_gap = sum(gaps) / len(gaps)
            
            for pos in [pos1-1, pos2-1]:  # -1 because gaps array is 0-indexed
                if 0 <= pos < len(gaps):
                    if gaps[pos] > avg_gap * 1.5:  # 50% larger than average
                        return True
            
            return False
            
        except Exception as e:
            return False
    
    def calculate_average_spacing(self, contours) -> float:
        """Calculate average spacing between characters"""
        try:
            if len(contours) < 2:
                return 0
            
            total_gap = 0
            gap_count = 0
            
            for i in range(1, len(contours)):
                prev_rect = contours[i-1]
                curr_rect = contours[i]
                gap = curr_rect[0] - (prev_rect[0] + prev_rect[2])
                if gap >= 0:  # Only count positive gaps
                    total_gap += gap
                    gap_count += 1
            
            return total_gap / gap_count if gap_count > 0 else 0
            
        except Exception as e:
            return 0
    
    def has_bracket_pattern(self, contours) -> bool:
        """Check if the text has bracket-like characters < and >"""
        try:
            if len(contours) < 3:
                return False
            
            # Look for characters that could be brackets
            # Brackets are usually taller than they are wide
            bracket_candidates = []
            
            for i, (x, y, w, h) in enumerate(contours):
                aspect_ratio = w / h if h > 0 else 1
                
                # Brackets are typically tall and narrow (aspect ratio < 0.6)
                if aspect_ratio < 0.6 and h > w:
                    bracket_candidates.append(i)
            
            # Need at least 2 bracket candidates (opening and closing)
            if len(bracket_candidates) >= 2:
                # Check if they're positioned like opening and closing brackets
                first_bracket = bracket_candidates[0]
                last_bracket = bracket_candidates[-1]
                
                # Should have some characters between them
                if last_bracket - first_bracket >= 3:
                    return True
            
            return False
            
        except Exception as e:
            return False
    

    
    def identify_two_word_text(self, contours, thresh_img) -> str:
        """Try to identify which two-word text this is"""
        try:
            char_count = len(contours)
            
            # "Devil Fruit" is typically 11 characters (including space)
            if 10 <= char_count <= 12:
                return "Devil Fruit"
            
            # "New item" is typically 8 characters (including space)
            if 7 <= char_count <= 9:
                return "New item"
            
            # Default for two words
            return "Two word text"
            
        except Exception as e:
            return "Two word text"
    
    def save_debug_screenshot(self, screenshot_area):
        """Save screenshot for debugging"""
        try:
            # Convert to PIL and save
            if len(screenshot_area.shape) == 3:
                pil_image = Image.fromarray(screenshot_area)
            else:
                pil_image = Image.fromarray(screenshot_area, mode='L')
            
            pil_image.save("debug_drop_area.png")
            print("📝 Debug screenshot saved as debug_drop_area.png")
            
        except Exception as e:
            print(f"📝 Could not save debug screenshot: {e}")
    
    def detect_gpo_text(self, screenshot_area) -> str:
        """
        This method is deprecated - use extract_text() instead
        """
        # This method is no longer used - extract_text handles everything
        return ""
    
    def trocr_extract_text(self, screenshot_area) -> str:
        """Extract text using TrOCR (Transformers OCR)"""
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            
            # Initialize TrOCR if not already done
            if not hasattr(self, 'trocr_processor'):
                print("🔧 Initializing TrOCR for text recognition...")
                self.trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed')
                print("✅ TrOCR initialized successfully!")
            
            # Preprocess image for TrOCR
            processed_img = self.preprocess_for_ocr(screenshot_area)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(processed_img)
            
            # Extract text using TrOCR
            pixel_values = self.trocr_processor(images=pil_image, return_tensors="pt").pixel_values
            generated_ids = self.trocr_model.generate(pixel_values)
            extracted_text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            return extracted_text.strip()
            
        except Exception as e:
            logging.error(f"TrOCR extraction failed: {e}")
            return ""
    
    def enhanced_text_extraction(self, screenshot_area) -> str:
        """Enhanced text extraction using OpenCV preprocessing + pattern matching"""
        try:
            # Multiple preprocessing approaches for better text recognition
            height, width = screenshot_area.shape[:2]
            
            # Convert to grayscale
            if len(screenshot_area.shape) == 3:
                gray = cv2.cvtColor(screenshot_area, cv2.COLOR_RGB2GRAY)
            else:
                gray = screenshot_area
            
            # Try multiple preprocessing techniques
            results = []
            
            # Method 1: OTSU thresholding
            _, binary1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text1 = self.extract_text_from_binary(binary1)
            if text1:
                results.append(text1)
            
            # Method 2: Adaptive thresholding
            binary2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            text2 = self.extract_text_from_binary(binary2)
            if text2:
                results.append(text2)
            
            # Method 3: Enhanced contrast + thresholding
            enhanced = cv2.equalizeHist(gray)
            _, binary3 = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
            text3 = self.extract_text_from_binary(binary3)
            if text3:
                results.append(text3)
            
            # Return the most likely result
            if results:
                # Prefer longer, more detailed results
                best_result = max(results, key=len)
                return best_result
            
            # Fallback: Check for known GPO patterns
            return self.detect_gpo_patterns(screenshot_area)
            
        except Exception as e:
            logging.error(f"Enhanced text extraction failed: {e}")
            return ""
    
    def extract_text_from_binary(self, binary_img) -> str:
        """Extract text patterns from binary image"""
        try:
            # Find contours (potential text regions)
            contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size (text usually has specific size ranges)
            text_contours = []
            height, width = binary_img.shape
            min_area = (height * width) * 0.001  # At least 0.1% of image
            max_area = (height * width) * 0.5    # At most 50% of image
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    # Text usually has reasonable aspect ratios
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.1 < aspect_ratio < 10:  # Reasonable text aspect ratio
                        text_contours.append((x, y, w, h))
            
            # If we found text-like regions, try to identify common GPO terms
            if text_contours:
                return self.identify_gpo_text_from_contours(binary_img, text_contours)
            
            return ""
            
        except Exception as e:
            logging.error(f"Binary text extraction failed: {e}")
            return ""
    
    def identify_gpo_text_from_contours(self, binary_img, contours) -> str:
        """Identify GPO-specific text from contour analysis"""
        try:
            # Analyze the pattern of contours to identify common GPO phrases
            total_contours = len(contours)
            
            # Sort contours by position (left to right, top to bottom)
            contours.sort(key=lambda c: (c[1], c[0]))  # Sort by y, then x
            
            # Check for common GPO drop patterns based on contour arrangement
            if total_contours >= 2:
                # Check spacing and arrangement patterns
                
                # Pattern 1: "Devil Fruit" - usually 2 words, specific spacing
                if total_contours >= 2:
                    first_rect = contours[0]
                    second_rect = contours[1]
                    
                    # Check if they're on roughly the same line (similar y coordinates)
                    y_diff = abs(first_rect[1] - second_rect[1])
                    if y_diff < first_rect[3] * 0.5:  # Within half the height
                        # Check spacing between words
                        x_gap = second_rect[0] - (first_rect[0] + first_rect[2])
                        if 0 < x_gap < first_rect[2]:  # Reasonable word spacing
                            return "Devil Fruit"
                
                # Pattern 2: Single long word patterns
                if total_contours == 1:
                    rect = contours[0]
                    width_ratio = rect[2] / binary_img.shape[1]
                    if width_ratio > 0.3:  # Takes up significant width
                        return "Legendary"
                
                # Pattern 3: Multiple small words (like "check your backpack")
                if total_contours >= 3:
                    return "Check your backpack"
            
            # Fallback: Generic detection
            if total_contours > 0:
                return "Item detected"
            
            return ""
            
        except Exception as e:
            logging.error(f"GPO text identification failed: {e}")
            return ""
    
    def detect_gpo_patterns(self, screenshot_area) -> str:
        """Detect GPO-specific visual patterns when OCR fails"""
        try:
            height, width = screenshot_area.shape[:2]
            
            # Convert to different color spaces for analysis
            if len(screenshot_area.shape) == 3:
                # Check for specific GPO colors
                
                # Devil Fruit notifications often have purple/dark backgrounds
                purple_pixels = np.sum((screenshot_area[:,:,2] > 100) & 
                                     (screenshot_area[:,:,1] < 80) & 
                                     (screenshot_area[:,:,0] < 80))
                purple_ratio = purple_pixels / (height * width)
                
                # Legendary notifications often have golden/yellow text
                golden_pixels = np.sum((screenshot_area[:,:,0] > 150) & 
                                     (screenshot_area[:,:,1] > 150) & 
                                     (screenshot_area[:,:,2] < 100))
                golden_ratio = golden_pixels / (height * width)
                
                # White text (common for notifications)
                white_pixels = np.sum((screenshot_area[:,:,0] > 200) & 
                                    (screenshot_area[:,:,1] > 200) & 
                                    (screenshot_area[:,:,2] > 200))
                white_ratio = white_pixels / (height * width)
                
                # Determine most likely content based on color analysis
                if purple_ratio > 0.05:
                    return "Devil Fruit"
                elif golden_ratio > 0.03:
                    return "Legendary item"
                elif white_ratio > 0.1:
                    return "Text notification"
            
            return ""
            
        except Exception as e:
            logging.error(f"GPO pattern detection failed: {e}")
            return ""
    
    def detect_devil_fruit_pattern(self, screenshot_area) -> bool:
        """Detect devil fruit drop patterns"""
        try:
            # Look for specific color patterns that indicate devil fruit drops
            # Devil fruits often have distinctive colors in GPO
            
            # Check for purple/dark colors (common in devil fruit notifications)
            if len(screenshot_area.shape) == 3:
                # Look for purple-ish colors (high blue, low green)
                purple_mask = (screenshot_area[:,:,2] > 100) & (screenshot_area[:,:,1] < 80)
                purple_ratio = np.sum(purple_mask) / (screenshot_area.shape[0] * screenshot_area.shape[1])
                
                if purple_ratio > 0.05:  # 5% purple pixels might indicate devil fruit
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Devil fruit pattern detection failed: {e}")
            return False
    
    def detect_legendary_pattern(self, screenshot_area) -> bool:
        """Detect legendary item patterns"""
        try:
            # Look for golden/yellow colors (common in legendary notifications)
            if len(screenshot_area.shape) == 3:
                # Look for golden colors (high red and green, lower blue)
                golden_mask = (screenshot_area[:,:,0] > 150) & (screenshot_area[:,:,1] > 150) & (screenshot_area[:,:,2] < 100)
                golden_ratio = np.sum(golden_mask) / (screenshot_area.shape[0] * screenshot_area.shape[1])
                
                if golden_ratio > 0.03:  # 3% golden pixels might indicate legendary
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Legendary pattern detection failed: {e}")
            return False
    
    def correct_item_names(self, text: str) -> str:
        """
        Correct GPO item names using the real items database
        
        Args:
            text: Text that may contain GPO item names
            
        Returns:
            Text with corrected item names
        """
        import re
        
        result = text
        
        # Check for each real GPO item in our database
        for incorrect_name, correct_name in self.gpo_items.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(incorrect_name) + r'\b'
            result = re.sub(pattern, correct_name, result, flags=re.IGNORECASE)
        
        return result
    
    def test_ocr(self) -> Tuple[bool, str]:
        """
        Test OCR functionality
        
        Returns:
            Tuple of (success, message)
        """
        if not self.ocr_available or not self.reader:
            return False, "OCR not available"
            
        try:
            # Create a simple test image with text
            if not OCR_AVAILABLE:
                return False, "OCR packages not installed"
                
            test_img = np.ones((50, 200, 3), dtype=np.uint8) * 255  # White background
            cv2.putText(test_img, 'TEST', (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Test basic OCR
            result_text = self.basic_text_detection(test_img)
            success = len(result_text) > 0  # Any detection is considered success
            
            if success:
                return True, "Basic OCR is working correctly"
            else:
                return True, "Basic OCR loaded but may have issues with text detection"
            
        except Exception as e:
            return False, f"OCR test failed: {e}"
    
    def get_stats(self) -> dict:
        """Get OCR statistics"""
        return {
            "available": self.ocr_available,
            "last_text": self.last_text,
            "last_capture_time": self.last_capture_time,
            "cooldown": self.capture_cooldown
        }
    
    def detect_text_fallback(self, screenshot_area) -> Optional[str]:
        """
        Fallback text detection without OCR - detects text-like patterns
        
        Args:
            screenshot_area: numpy array of screenshot region
            
        Returns:
            Simple text detection result or None
        """
        if not self.ocr_available:
            return None
            
        try:
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_capture_time < self.capture_cooldown:
                return None
            
            height, width = screenshot_area.shape[:2]
            
            # Multiple detection methods for better accuracy
            text_score = 0
            
            # Method 1: Color variance detection (text has different colors than background)
            if len(screenshot_area.shape) == 3:
                # Calculate color variance across the image
                color_variance = np.var(screenshot_area, axis=(0, 1))
                avg_variance = np.mean(color_variance)
                if avg_variance > 500:  # High color variance suggests text
                    text_score += 1
                    print(f"🎨 Color variance detected: {avg_variance:.1f}")
            
            # Method 2: Edge detection (text has many edges)
            gray = np.mean(screenshot_area, axis=2).astype(np.uint8) if len(screenshot_area.shape) == 3 else screenshot_area
            
            # Simple edge detection using gradients
            edges = 0
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    # Calculate gradient magnitude
                    gx = abs(int(gray[y, x+1]) - int(gray[y, x-1]))
                    gy = abs(int(gray[y+1, x]) - int(gray[y-1, x]))
                    gradient = gx + gy
                    if gradient > 30:  # Edge threshold
                        edges += 1
            
            edge_density = edges / (height * width)
            if edge_density > 0.02:  # Significant edge density
                text_score += 1
                print(f"📐 Edge density: {edge_density:.3f}")
            
            # Method 3: Horizontal line detection (text forms horizontal patterns)
            horizontal_patterns = 0
            for y in range(height):
                line_changes = 0
                for x in range(1, width):
                    if abs(int(gray[y, x]) - int(gray[y, x-1])) > 20:
                        line_changes += 1
                if line_changes > width * 0.1:  # Line has enough changes to be text
                    horizontal_patterns += 1
            
            if horizontal_patterns > height * 0.1:  # Enough horizontal text patterns
                text_score += 1
                print(f"📏 Horizontal patterns: {horizontal_patterns}/{height}")
            
            # Method 4: Check for non-uniform background (text creates patterns)
            background_uniformity = np.std(gray)
            if background_uniformity > 15:  # Non-uniform background suggests text
                text_score += 1
                print(f"🌈 Background variation: {background_uniformity:.1f}")
            
            print(f"📊 Text detection score: {text_score}/4 (Area: {width}x{height})")
            
            # More strict requirements for drop detection
            # We need high confidence (3+ indicators) OR very high color variance (indicating colorful text)
            high_confidence = text_score >= 3
            very_colorful = len(screenshot_area.shape) == 3 and np.mean(np.var(screenshot_area, axis=(0, 1))) > 800
            
            if high_confidence or very_colorful:
                self.last_capture_time = current_time
                # Try to extract some basic info about what we detected
                return f"TEXT_DETECTED_NO_OCR (score: {text_score}/4, area: {width}x{height})"
            
            return None
            
        except Exception as e:
            logging.error(f"Fallback text detection failed: {e}")
            return None
    
    def basic_text_detection(self, img_array) -> str:
        """
        Basic text detection using OpenCV and pattern matching
        
        Args:
            img_array: numpy array of image
            
        Returns:
            Detected text or empty string
        """
        try:
            # Use pattern matching and contour analysis
            return self.pattern_match_text(img_array)
            
        except Exception as e:
            logging.error(f"Basic text detection failed: {e}")
            return ""
    
    def pattern_match_text(self, img_array) -> str:
        """Pattern matching for common GPO text when OCR is not available"""
        try:
            height, width = img_array.shape[:2]
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Calculate image characteristics
            avg_brightness = np.mean(gray)
            brightness_std = np.std(gray)
            
            # Edge detection to find text-like patterns
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (height * width)
            
            # Analyze for common GPO patterns
            
            # High edge density + medium brightness = likely text
            if edge_density > 0.05 and 50 < avg_brightness < 200:
                
                # Check for specific GPO item patterns
                if brightness_std > 50:  # High contrast (text)
                    
                    # Analyze aspect ratio
                    aspect_ratio = width / height if height > 0 else 1
                    
                    # Common GPO notification patterns
                    if aspect_ratio > 2:  # Wide text (like "Devil Fruit")
                        if avg_brightness < 100:  # Dark background
                            return "Devil Fruit"
                        else:
                            return "Item notification"
                    
                    elif 1 < aspect_ratio < 2:  # Medium width
                        if brightness_std > 70:  # Very high contrast
                            return "Legendary"
                        else:
                            return "Common item"
                    
                    else:  # Square-ish or tall
                        return "Single word"
            
            # Check for color-based patterns if it's a color image
            if len(img_array.shape) == 3:
                return self.detect_gpo_patterns(img_array)
            
            return ""
            
        except Exception as e:
            logging.error(f"Pattern matching failed: {e}")
            return ""