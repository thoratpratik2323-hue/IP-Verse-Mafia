"""
screenshot_ocr.py — Intelligent Screenshot OCR & Text Extraction

Extract text from screenshots and analyze content.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class ScreenshotOCR:
    """Extracts and analyzes text from screenshots."""
    
    def __init__(self):
        self.ocr_ready = self._check_ocr()
    
    def _check_ocr(self) -> bool:
        """Check if OCR libraries are available."""
        try:
            import pytesseract
            from PIL import Image
            return True
        except ImportError:
            return False
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image."""
        if not self.ocr_ready:
            return {"success": False, "error": "OCR not available. Install pytesseract and tesseract-ocr"}
        
        try:
            import pytesseract
            from PIL import Image
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            
            return {
                "success": True,
                "text": text,
                "file": image_path,
                "char_count": len(text),
                "line_count": len(text.split('\n'))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_structured_data(self, image_path: str) -> Dict[str, Any]:
        """Extract structured data from image (tables, forms, etc)."""
        if not self.ocr_ready:
            return {"success": False, "error": "OCR not available"}
        
        try:
            import pytesseract
            from PIL import Image
            import re
            
            img = Image.open(image_path)
            data = pytesseract.image_to_data(img, output_type='dict')
            
            # Group by lines
            lines = {}
            for i, text in enumerate(data['text']):
                if text.strip():
                    line_num = data['line_num'][i]
                    if line_num not in lines:
                        lines[line_num] = []
                    lines[line_num].append(text)
            
            structured = [" ".join(line) for line in lines.values()]
            
            return {
                "success": True,
                "structured_text": structured,
                "raw_data": data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """Analyze screenshot for content insights."""
        extraction = self.extract_text(image_path)
        
        if not extraction["success"]:
            return extraction
        
        text = extraction["text"]
        
        # Simple analysis
        analysis = {
            "file": image_path,
            "total_chars": len(text),
            "total_words": len(text.split()),
            "total_lines": len(text.split('\n')),
            "has_numbers": bool(__import__('re').search(r'\d', text)),
            "has_emails": bool(__import__('re').search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "has_urls": bool(__import__('re').search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)),
            "text_sample": text[:200]  # First 200 chars
        }
        
        return {
            "success": True,
            "analysis": analysis,
            "extracted_text": text
        }
    
    def batch_extract(self, folder_path: str) -> Dict[str, Any]:
        """Extract text from all images in folder."""
        results = []
        folder = Path(folder_path)
        
        for img_file in folder.glob("*.{png,jpg,jpeg,bmp,gif}"):
            result = self.extract_text(str(img_file))
            results.append({
                "file": str(img_file),
                "success": result.get("success"),
                "text": result.get("text") if result.get("success") else None
            })
        
        return {
            "success": True,
            "total_processed": len(results),
            "results": results
        }
    
    def save_extracted_text(self, image_path: str, output_file: str) -> bool:
        """Extract text and save to file."""
        try:
            result = self.extract_text(image_path)
            if result["success"]:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result["text"])
                return True
            return False
        except:
            return False


ocr = ScreenshotOCR()
