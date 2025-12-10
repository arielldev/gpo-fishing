"""
OCR Manager for text recognition from game screenshots
Supports multiple OCR engines with graceful fallbacks
"""

import logging
from typing import Optional, Tuple
import time
import warnings

# Suppress PyTorch warnings about GPU acceleration
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch.*")

# Always import numpy and cv2 for fallback detection
try:
    import numpy as np
    import cv2
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False
    print("⚠️ NumPy/OpenCV not available - text detection disabled")

# Try OCR engines - prioritize EasyOCR since it's more commonly installed
try:
    # Try EasyOCR first
    import easyocr
    from PIL import Image, ImageEnhance
    OCR_AVAILABLE = True
    OCR_ENGINE = "easy"
    print("✅ EasyOCR loaded successfully - text recognition available!")
except ImportError as e:
    print(f"🔍 EasyOCR import failed: {e}")
    try:
        # Fallback to PaddleOCR
        import paddleocr
        from PIL import Image, ImageEnhance
        OCR_AVAILABLE = True
        OCR_ENGINE = "paddle"
        print("✅ PaddleOCR loaded successfully - lightweight text recognition!")
    except ImportError as e2:
        print(f"🔍 PaddleOCR import failed: {e2}")
        OCR_AVAILABLE = False
        OCR_ENGINE = None
        # Create dummy classes for type hints when OCR not available
        class DummyImage:
            Image = object
            LANCZOS = 1
        class DummyEnhance:
            pass
        
        Image = DummyImage()
        ImageEnhance = DummyEnhance()
        if FALLBACK_AVAILABLE:
            print("⚠️ No OCR engine available - using fallback text detection")
        else:
            print("❌ No text detection available - install numpy and opencv-python")

class OCRManager:
    """Manages text recognition from screenshot areas using EasyOCR"""
    
    def __init__(self, app=None):
        self.app = app  # Reference to main app for accessing layout manager
        self.ocr_available = OCR_AVAILABLE
        self.last_text = ""
        self.last_capture_time = 0
        self.capture_cooldown = 2.0  # Increased cooldown to reduce CPU load
        self.reader = None
        
        # Performance optimization settings - will be configured based on performance mode
        self.performance_mode = "fast"  # Default to fast mode
        self.configure_performance_settings()
        
        # Caching for repeated similar images
        self.image_cache = {}
        self.cache_max_size = 10
        self.cache_similarity_threshold = 0.95
        
        # Devil fruit names for spawn detection
        self.devil_fruits = [
            'Tori', 'Mochi', 'Ope', 'Venom', 'Buddha', 'Pteranodon',
            'Smoke', 'Goru', 'Yuki', 'Yami', 'Pika', 'Magu',
            'Kage', 'Mera', 'Paw', 'Goro', 'Ito', 'Hie',
            'Suna', 'Gura', 'Zushi', 'Kira', 'Spring', 'Yomi',
            'Bomb', 'Gomu', 'Horo', 'Mero', 'Bari', 'Heal',
            'Spin', 'Suke', 'Kilo'
        ]
        
        # Create lowercase mapping for fuzzy matching
        self.devil_fruits_lower = [f.lower() for f in self.devil_fruits]
    
    def configure_performance_settings(self):
        """Configure OCR performance settings based on performance mode"""
        # Get drop layout dimensions if available
        drop_width = None
        drop_height = None
        if self.app and hasattr(self.app, 'layout_manager'):
            drop_area = self.app.layout_manager.get_layout_area('drop')
            if drop_area:
                drop_width = drop_area['width']
                drop_height = drop_area['height']
        
        # Use drop layout size if available, otherwise use None (no resizing)
        if drop_width and drop_height:
            max_size = (drop_width, drop_height)
        else:
            max_size = (999, 999)  # Effectively no limit if drop layout not set
        
        if self.performance_mode == "fast":
            # Fastest mode - minimal processing, maximum performance
            self.max_image_size = max_size
            self.skip_preprocessing = True
            self.capture_cooldown = 3.0  # Longer cooldown
            self.cache_max_size = 15
            print(f"🚀 OCR configured for FAST mode - max size: {max_size}")
            
        elif self.performance_mode == "balanced":
            # Balanced mode - moderate processing, good performance
            self.max_image_size = max_size
            self.skip_preprocessing = False
            self.capture_cooldown = 2.0
            self.cache_max_size = 10
            print(f"⚖️ OCR configured for BALANCED mode - max size: {max_size}")
            
        elif self.performance_mode == "quality":
            # Quality mode - better processing, slower performance
            self.max_image_size = max_size
            self.skip_preprocessing = False
            self.capture_cooldown = 1.5
            self.cache_max_size = 5
            print(f"🎯 OCR configured for QUALITY mode - max size: {max_size}")
        
        else:
            # Default to fast mode if unknown setting
            self.performance_mode = "fast"
            self.configure_performance_settings()
    
    def set_performance_mode(self, mode: str):
        """Set OCR performance mode and reconfigure settings"""
        if mode in ["fast", "balanced", "quality"]:
            self.performance_mode = mode
            self.configure_performance_settings()
            # Clear cache when changing modes
            self.image_cache.clear()
        else:
            print(f"⚠️ Unknown OCR performance mode: {mode}. Using 'fast' mode.")
        
        # Only real GPO items for better recognition
        self.gpo_items = {
            # Real GPO Items from fishing
            'candycorn': 'Candy Corn',
            'candy corn': 'Candy Corn',
            
            # Devil Fruits (important for webhook logging)
            'devilfruit': 'Devil Fruit',
            'devil fruit': 'Devil Fruit',
        }
        
        if self.ocr_available:
            try:
                if OCR_ENGINE == "easy":
                    print("🔧 Initializing EasyOCR with CPU optimization...")
                    # Initialize EasyOCR with only compatible parameters
                    self.reader = easyocr.Reader(
                        ['en'], 
                        gpu=False,  # Force CPU usage
                        verbose=False,
                        download_enabled=True
                    )
                    print("✅ EasyOCR ready with CPU optimization - text recognition available!")
                elif OCR_ENGINE == "paddle":
                    print("🔧 Initializing PaddleOCR (lightweight engine)...")
                    # Initialize PaddleOCR with English language
                    self.reader = paddleocr.PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                    print("✅ PaddleOCR ready - lightweight text recognition!")
            except Exception as e:
                logging.error(f"Failed to initialize {OCR_ENGINE}OCR: {e}")
                self.ocr_available = False
                self.reader = None
    
    def is_available(self) -> bool:
        """Check if OCR is available and configured"""
        return self.ocr_available
    
    def extract_text(self, screenshot_area=None) -> Optional[str]:
        """
        Extract text from drop layout area using available OCR engine
        Always uses the configured drop layout area, ignoring screenshot_area parameter
        
        Args:
            screenshot_area: IGNORED - always uses drop layout area
            
        Returns:
            Extracted and filtered text, or None if no text found
        """
        # Always capture from drop layout area
        screenshot_area = self.capture_drop_area()
        if screenshot_area is None:
            print("❌ Could not capture drop layout area")
            return None
        
        if not self.ocr_available or not self.reader:
            # Fallback: Basic text detection without OCR
            if FALLBACK_AVAILABLE:
                return self.detect_text_fallback(screenshot_area)
            else:
                return None
            
        # Check cooldown to prevent spam
        current_time = time.time()
        if current_time - self.last_capture_time < self.capture_cooldown:
            return None
        
        # Check image cache for similar images to avoid reprocessing
        cached_result = self.check_image_cache(screenshot_area)
        if cached_result is not None:
            print(f"📋 Using cached OCR result: {cached_result}")
            return cached_result
            
        try:
            # Convert BGR to RGB if needed
            if len(screenshot_area.shape) == 3:
                screenshot_area = cv2.cvtColor(screenshot_area, cv2.COLOR_BGR2RGB)
            
            # Preprocess image for better recognition
            processed_img = self.preprocess_for_easyocr(screenshot_area)
            
            # Use appropriate OCR engine
            if OCR_ENGINE == "paddle":
                # PaddleOCR returns different format: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, confidence]
                results = self.reader.ocr(processed_img, cls=True)
                if results and results[0]:
                    texts = [item[1][0] for item in results[0] if item[1][1] > 0.5]  # confidence > 0.5
                    raw_text = ' '.join(texts)
                else:
                    raw_text = ""
            else:
                # EasyOCR format
                results = self.reader.readtext(processed_img, detail=0, paragraph=True)
                raw_text = ' '.join(results) if results else ""
            
            # Filter and clean text
            if raw_text:
                filtered_text = self.filter_and_clean_text(raw_text)
                
                # Apply item name corrections
                if filtered_text:
                    corrected_text = self.correct_item_names(filtered_text)
                    
                    if corrected_text and corrected_text != self.last_text:
                        self.last_text = corrected_text
                        self.last_capture_time = current_time
                        
                        # Cache the result for similar future images
                        self.cache_image_result(screenshot_area, corrected_text)
                        
                        print(f"📝 {OCR_ENGINE.title()}OCR extracted: {corrected_text}")
                        return corrected_text
                
        except Exception as e:
            logging.error(f"{OCR_ENGINE.title() if OCR_ENGINE else 'OCR'} extraction failed: {e}")
            # Fall back to basic text detection if OCR fails
            if FALLBACK_AVAILABLE:
                return self.detect_text_fallback(screenshot_area)
            else:
                return None
            
        return None
    
    def preprocess_for_easyocr(self, img_array):
        """
        Lightweight image enhancement for better EasyOCR recognition with minimal CPU impact
        
        Args:
            img_array: numpy array of image
            
        Returns:
            Processed numpy array
        """
        try:
            # Limit image size to reduce processing time
            height, width = img_array.shape[:2]
            if width > self.max_image_size[0] or height > self.max_image_size[1]:
                scale_factor = min(self.max_image_size[0] / width, self.max_image_size[1] / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            # Skip heavy preprocessing if enabled
            if self.skip_preprocessing:
                return img_array
            
            # Convert to grayscale if needed (faster processing)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Minimal enhancement - just basic contrast adjustment
            # Skip expensive operations like CLAHE, denoising, and sharpening
            img_array = cv2.convertScaleAbs(img_array, alpha=1.2, beta=10)
            
            return img_array
            
        except Exception as e:
            logging.error(f"Image preprocessing failed: {e}")
            return img_array
    
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
        Test OCR functionality using drop layout area
        
        Returns:
            Tuple of (success, message)
        """
        if not self.ocr_available or not self.reader:
            return False, f"{OCR_ENGINE or 'OCR'} not available"
        
        if not self.app or not hasattr(self.app, 'layout_manager'):
            return False, "No app reference - cannot access drop layout area"
            
        try:
            # Test by trying to capture and process the actual drop area
            drop_area = self.capture_drop_area()
            if drop_area is None:
                return False, "Could not capture drop layout area for testing"
            
            # Try to process the drop area (even if no text is present)
            processed_img = self.preprocess_for_easyocr(drop_area)
            
            # Try to extract text based on engine
            if OCR_ENGINE == "paddle":
                results = self.reader.ocr(processed_img, cls=True)
                success = True  # If no exception, OCR is working
            else:
                results = self.reader.readtext(processed_img, detail=0)
                success = True  # If no exception, OCR is working
            
            return True, f"{OCR_ENGINE.title()}OCR is working correctly with drop layout area"
            
        except Exception as e:
            return False, f"{OCR_ENGINE.title()}OCR test failed: {e}"
    
    def detect_fruit_spawn(self, text: str) -> Optional[str]:
        """
        Detect devil fruit spawn from OCR text
        Matches against known GPO fruit names using fuzzy matching
        
        Args:
            text: OCR extracted text
            
        Returns:
            Fruit name if detected, None otherwise
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Look for spawn keywords first
        spawn_keywords = ['spawned', 'has spawned', 'spawn']
        has_spawn_keyword = any(keyword in text_lower for keyword in spawn_keywords)
        
        if not has_spawn_keyword:
            return None
        
        # Try to find fruit name using fuzzy matching
        for i, fruit_lower in enumerate(self.devil_fruits_lower):
            # Direct match
            if fruit_lower in text_lower:
                return self.devil_fruits[i]
            
            # Fuzzy match - allow for OCR errors (1-2 character differences)
            if len(fruit_lower) >= 3:
                # Check if most characters match in sequence
                for word in text_lower.split():
                    if len(word) >= 3:
                        # Calculate similarity
                        matches = sum(1 for a, b in zip(fruit_lower, word) if a == b)
                        similarity = matches / max(len(fruit_lower), len(word))
                        
                        # Accept if 70%+ similarity
                        if similarity >= 0.7:
                            return self.devil_fruits[i]
        
        return None
    
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
        Fallback text detection without OCR - detects text-like patterns in drop layout area
        
        Args:
            screenshot_area: numpy array of drop area screenshot
            
        Returns:
            Simple text detection result or None
        """
        if not FALLBACK_AVAILABLE:
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
    
    def check_image_cache(self, img_array) -> Optional[str]:
        """
        Check if we have a cached result for a similar image
        
        Args:
            img_array: numpy array of image
            
        Returns:
            Cached text result or None
        """
        try:
            # Create a simple hash of the image for comparison
            img_hash = self.simple_image_hash(img_array)
            
            # Check cache for similar images
            for cached_hash, cached_text in self.image_cache.items():
                similarity = self.hash_similarity(img_hash, cached_hash)
                if similarity > self.cache_similarity_threshold:
                    return cached_text
            
            return None
            
        except Exception as e:
            logging.error(f"Cache check failed: {e}")
            return None
    
    def cache_image_result(self, img_array, text_result: str):
        """
        Cache the OCR result for this image
        
        Args:
            img_array: numpy array of image
            text_result: OCR text result
        """
        try:
            # Clean cache if it's getting too large
            if len(self.image_cache) >= self.cache_max_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.image_cache))
                del self.image_cache[oldest_key]
            
            # Add new result to cache
            img_hash = self.simple_image_hash(img_array)
            self.image_cache[img_hash] = text_result
            
        except Exception as e:
            logging.error(f"Cache storage failed: {e}")
    
    def simple_image_hash(self, img_array) -> str:
        """
        Create a simple hash of the image for caching
        
        Args:
            img_array: numpy array of image
            
        Returns:
            Simple hash string
        """
        try:
            # Resize to small size for fast hashing
            small_img = cv2.resize(img_array, (16, 16), interpolation=cv2.INTER_LINEAR)
            
            # Convert to grayscale if needed
            if len(small_img.shape) == 3:
                small_img = cv2.cvtColor(small_img, cv2.COLOR_RGB2GRAY)
            
            # Create hash from pixel values
            return str(hash(small_img.tobytes()))
            
        except Exception as e:
            logging.error(f"Image hashing failed: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def hash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calculate similarity between two image hashes
        
        Args:
            hash1: First hash
            hash2: Second hash
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            # Simple string similarity for now
            if hash1 == hash2:
                return 1.0
            
            # For more sophisticated similarity, we could use Hamming distance
            # For now, exact match only
            return 0.0
            
        except Exception as e:
            logging.error(f"Hash similarity calculation failed: {e}")
            return 0.0
    
    def capture_drop_area(self):
        """
        Capture screenshot from the configured drop layout area
        
        Returns:
            numpy array of drop area screenshot or None if failed
        """
        try:
            if not self.app or not hasattr(self.app, 'layout_manager'):
                print("❌ No app or layout manager available for drop area capture")
                return None
            
            # Get drop layout area coordinates
            drop_area = self.app.layout_manager.get_layout_area('drop')
            if not drop_area:
                print("❌ Drop layout area not configured")
                return None
            
            # Capture screenshot of drop area
            import mss
            with mss.mss() as sct:
                monitor = {
                    'left': drop_area['x'],
                    'top': drop_area['y'],
                    'width': drop_area['width'],
                    'height': drop_area['height']
                }
                screenshot = sct.grab(monitor)
                screenshot_array = np.array(screenshot)
                
                print(f"📸 Captured drop area: {drop_area['width']}x{drop_area['height']} at ({drop_area['x']}, {drop_area['y']})")
                return screenshot_array
                
        except Exception as e:
            logging.error(f"Drop area capture failed: {e}")
            return None