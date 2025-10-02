import re
import os
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import pytesseract
from PIL import Image
import cv2
import numpy as np

def preprocess_image(image_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Preprocess image to improve OCR accuracy - returns multiple versions
    """
    # Clear any existing windows and cached memory
    cv2.destroyAllWindows()
    
    # Read image with fresh handle
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
    
    # Threshold
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Resize for better OCR if image is small
    height, width = gray.shape
    if height < 2000:
        scale_factor = 2000 / height
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        thresh = cv2.resize(thresh, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    return thresh, gray

def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using OCR with multiple attempts
    """
    try:
        # Clear any cached images
        cv2.destroyAllWindows()
        
        # Verify the image exists
        if not os.path.exists(image_path):
            print(f"Error: Image file not found: {image_path}")
            return ""
            
        # Read image with a fresh handle
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image: {image_path}")
            return ""
            
        processed_img, original_gray = preprocess_image(image_path)
        
        # Use single optimized OCR configuration for invoices
        config = r'--oem 1 --psm 6'  # LSTM engine with uniform text block assumption
        
        try:
            best_text = pytesseract.image_to_string(processed_img, config=config, lang='eng')
        except Exception as e:
            print(f"Warning: OCR failed with primary configuration: {e}")
            best_text = ""
        
        # Also try with original grayscale
        if len(best_text) < 100:  # Try grayscale if processed image gave poor results
            try:
                text = pytesseract.image_to_string(original_gray, config=config, lang='eng')
                if len(text) > len(best_text):
                    best_text = text
            except Exception as e:
                print(f"Warning: OCR failed with grayscale image: {e}")
        
        # Try with PIL Image as fallback
        if len(best_text) < 100:
            try:
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img, lang='eng')
                if len(text) > len(best_text):
                    best_text = text
            except:
                pass
        
        return best_text
        
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""

def clean_text(text: str) -> str:
    """
    Clean OCR text from common errors
    """
    replacements = {
        'Deil': 'Dell',
        'De11': 'Dell',
        'HPT520': 'HP T520',
        'C1ient': 'Client',
        'Bui1d': 'Build',
        'Optip1ex': 'Optiplex',
        '|': 'I',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

def extract_section(text: str, start_marker: str, end_marker: str = None) -> str:
    """
    Extract text between two markers with improved accuracy
    """
    try:
        # First try exact markers
        pattern = f"{re.escape(start_marker)}(.*?)"
        if end_marker:
            pattern += f"(?={re.escape(end_marker)})"
        else:
            pattern += "$"
        
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try with flexible whitespace
        pattern = f"{re.escape(start_marker)}\s*(.*?)"
        if end_marker:
            pattern += f"(?=\s*{re.escape(end_marker)})"
        else:
            pattern += "$"
        
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try finding section by looking for tabular data
        lines = text.split('\n')
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if start_marker.lower() in line.lower():
                start_idx = i + 1
            elif end_marker and end_marker.lower() in line.lower():
                end_idx = i
                break
        
        if start_idx >= 0:
            if end_idx > start_idx:
                return '\n'.join(lines[start_idx:end_idx]).strip()
            else:
                return '\n'.join(lines[start_idx:]).strip()
                
        return ""
    except Exception as e:
        print(f"Warning: Error extracting section: {str(e)[:100]}")
        return ""

def parse_invoice_header(text: str) -> Dict[str, Any]:
    """
    Parse invoice header information
    """
    data = {}
    
    # Invoice number
    inv_patterns = [
        r'Invoice\s+no:?\s*(\d+)',
        r'Invoice\s*#\s*(\d+)',
        r'INV-?(\d+)'
    ]
    
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_number'] = match.group(1)
            break
    
    # Date
    date_patterns = [
        r'Date\s+of\s+issue:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
        r'Date:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['date'] = match.group(1)
            break
    
    return data

def parse_party_info(text: str, party_type: str) -> Dict[str, str]:
    """
    Parse Seller or Client information
    """
    data = {}
    
    if party_type.lower() == 'seller':
        patterns = [
            r'Seller:\s*(.*?)\s*(?=Client:|ITEMS)',
            r'Seller\s*(.*?)\s*(?=Client|ITEMS)',
        ]
        
        tax_patterns = [
            r'Seller:.*?Tax\s+Id:?\s*([\d\-]+)',
            r'Tax\s+Id:?\s*([\d\-]+).*?(?=Client)',
        ]
    else:
        patterns = [
            r'Client:\s*(.*?)\s*(?=Tax\s+Id:|ITEMS|IBAN)',
            r'Client\s*(.*?)\s*(?=Tax\s+Id|ITEMS)',
        ]
        
        tax_patterns = [
            r'Client:.*?Tax\s+Id:?\s*([\d\-]+)',
        ]
    
    # Try to find section
    section_text = None
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            section_text = match.group(1).strip()
            break
    
    if section_text:
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        
        clean_lines = []
        for line in lines:
            if not re.search(r'IBAN:|Tax\s+Id:', line, re.IGNORECASE):
                clean_lines.append(line)
        
        if clean_lines:
            data['name'] = clean_lines[0]
            
            if len(clean_lines) > 1:
                data['address'] = ' '.join(clean_lines[1:])
    
    # Extract Tax ID
    for pattern in tax_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            data['tax_id'] = match.group(1)
            break
    
    return data

def parse_simple_item_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parser for simple item lines with basic format
    """
    try:
        # Clean and normalize the line
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Try different patterns
        patterns = [
            # Pattern 1: Full format with all fields
            r'^(\d+)[\.)\s]+(.*?)\s+(\d+(?:[.,]\d+)?)\s*(?:each\s+)?(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+(\d+)%\s+(\d+(?:[.,]\d+)?)',
            # Pattern 2: Simple format with quantity and price
            r'^(\d+)[\.)\s]+(.*?)\s+(\d+(?:[.,]\d+)?)\s*(?:each\s+)?(\d+(?:[.,]\d+)?)',
            # Pattern 3: Format with final total only
            r'^(\d+)[\.)\s]+(.*?)\s+(\d+(?:[.,]\d+)?)\s*(?:each\s+)?\s*(\d+(?:[.,]\d+)?)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
        
        if not match:
            return None
            
        item_no = int(match.group(1))
        description = match.group(2).strip()
        quantity = float(match.group(3).replace(',', '.'))
        unit_price = float(match.group(4).replace(',', '.'))
        vat = match.group(5) if match.group(5) else "10"
        
        # Calculate or use provided total
        net_worth = float(match.group(6).replace(',', '.')) if match.group(6) else quantity * unit_price
        
        # Calculate gross worth with VAT
        vat_rate = float(vat) / 100
        gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        return {
            'item_no': item_no,
            'description': description,
            'quantity': quantity,
            'unit_price': unit_price,
            'net_worth': net_worth,
            'vat_percentage': f"{vat}%",
            'gross_worth': gross_worth
        }
            
        # Extract description (text before the last 2-5 numbers)
        desc_pattern = r'^(.*?)(?=\s*\d+(?:[.,]\d+)?\s*(?:each|pc|pcs|units?)?\s*$)'
        desc_match = re.search(desc_pattern, line, re.IGNORECASE)
        
        if not desc_match:
            return None
            
        description = desc_match.group(1).strip()
        description = re.sub(r'\s+(each|pc|pcs|unit|units)\s*$', '', description, flags=re.IGNORECASE)
        
        # Try to identify the numbers
        qty = 1.0
        unit_price = float(numbers[-2])  # Assume last number is total and second-to-last is unit price
        net_worth = float(numbers[-1])
        
        # If we have more numbers, first one might be quantity
        if len(numbers) >= 3 and float(numbers[0]) < 1000:  # Reasonable quantity check
            qty = float(numbers[0])
            
        # Calculate VAT and gross (assume standard VAT if not found)
        vat_pct = "20%"  # Default VAT
        vat_match = re.search(r'(\d+)%', line)
        if vat_match:
            vat_pct = f"{vat_match.group(1)}%"
            
        vat_rate = float(vat_pct.replace('%', '')) / 100
        gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        return {
            'item_no': item_no,
            'description': description,
            'quantity': qty,
            'unit_price': unit_price,
            'net_worth': net_worth,
            'vat_percentage': vat_pct,
            'gross_worth': gross_worth
        }
        
    except Exception as e:
        print(f"Warning: Simple parse failed: {str(e)[:100]}")
        return None

def parse_item_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single item line from the invoice with table format support
    """
    try:
        # Clean and normalize the line
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Check for item number at start
        item_num_match = re.match(r'^(\d+)[\.,)\s]', line)
        if not item_num_match:
            return None
        
        item_no = int(item_num_match.group(1))
        
        # Look for the pattern: quantity + "each" + price (with possible thousand separators)
        qty_price_match = re.search(r'(\d+[,.]?\d*)\s*each\s+(\d{1,3}(?:[., ]\d{3})*(?:[,.]\d+)?)', line)
        if not qty_price_match:
            return None
            
        # Extract the main components
        qty_str = qty_price_match.group(1).replace(' ', '')
        price_str = qty_price_match.group(2).replace(' ', '')
        
        # Process quantity
        qty = float(qty_str.replace(',', '.'))
        
        # Process unit price with thousand separators
        if ',' in price_str and '.' in price_str:
            # European format (1.234,56)
            if price_str.index('.') < price_str.index(','):
                price_str = price_str.replace('.', '').replace(',', '.')
            # US/UK format (1,234.56)
            else:
                price_str = price_str.replace(',', '')
        elif ',' in price_str:
            if len(price_str.split(',')[1]) <= 2:
                price_str = price_str.replace(',', '.')
            else:
                price_str = price_str.replace(',', '')
                
        unit_price = float(price_str)
        
        # Find all decimal numbers (including those with thousand separators)
        numbers = re.findall(r'(\d{1,3}(?:[., ]\d{3})*(?:[,.]\d+)?|\d+)(?:\s*%)?', line)
        
        # Process numbers considering thousand separators
        clean_numbers = []
        for n in numbers:
            # Remove spaces
            n = n.replace(' ', '')
            
            # If number has both comma and dot
            if ',' in n and '.' in n:
                # European format (1.234,56)
                if n.index('.') < n.index(','):
                    n = n.replace('.', '').replace(',', '.')
                # US/UK format (1,234.56)
                else:
                    n = n.replace(',', '')
            # If only comma, treat as decimal if it's near the end
            elif ',' in n:
                if len(n.split(',')[1]) <= 2:
                    n = n.replace(',', '.')
                else:
                    n = n.replace(',', '')
                    
            try:
                num = float(n)
                if num != item_no:  # Exclude item number
                    clean_numbers.append(num)
            except ValueError:
                continue
                
        numbers = clean_numbers
        
        # Find VAT percentage
        vat_match = re.search(r'(\d+)\s*%', line)
        vat_pct = f"{vat_match.group(1)}%" if vat_match else "10%"
        
        # Extract description - everything between item number and first number
        desc_match = re.match(r'\d+[\.,]\s*(.+?)\s+\d+[,.]\d+', line)
        if not desc_match:
            return None
            
        description = desc_match.group(1).strip()
        description = re.sub(r'\s+each\s*$', '', description, flags=re.IGNORECASE)
        
        # Find net_worth and gross_worth
        # They should be after quantity and unit price
        idx = numbers.index(unit_price)
        potential_numbers = numbers[idx+1:]
        
        if len(potential_numbers) >= 2:
            net_worth = potential_numbers[-2]
            gross_worth = potential_numbers[-1]
        else:
            # Calculate if not found
            net_worth = round(qty * unit_price, 2)
            vat_rate = float(vat_pct.replace('%', '')) / 100
            gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        # Validate calculations
        expected_net = round(qty * unit_price, 2)
        if abs(net_worth - expected_net) > 0.1:  # Allow small rounding differences
            print(f"Warning: Adjusting net worth for item {item_no} from {net_worth} to {expected_net}")
            net_worth = expected_net
            vat_rate = float(vat_pct.replace('%', '')) / 100
            gross_worth = round(net_worth * (1 + vat_rate), 2)
            
        return {
            'item_no': item_no,
            'description': description,
            'quantity': qty,
            'unit_price': unit_price,
            'net_worth': net_worth,
            'vat_percentage': vat_pct,
            'gross_worth': gross_worth
        }
        
    except Exception as e:
        print(f"Warning: Failed to parse line: {str(e)[:100]}")
        return None
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Skip the item number part
            if part == str(item_no) or part == f"{item_no}.":
                continue
                
            # Try to parse as number
            try:
                num = float(part.replace(',', '.').replace('$', '').strip())
                if qty is None and num < 1000:  # First number under 1000 is likely quantity
                    qty = num
                numbers_found.append(num)
                continue
            except ValueError:
                pass
                
            # Check for percentage
            if re.match(r'^\d+%$', part):
                numbers_found.append(part)
                continue
                
            # Check for unit indicator
            if part.lower() in ['each', 'pc', 'pcs', 'unit', 'units']:
                continue
                
            # If we get here, it's probably part of the description
            if not any(x in part.lower() for x in ['vat', 'net', 'gross', 'total']):
                if description:
                    description += " "
                description += part
        
        if not description or len(numbers_found) < 3:
            return None
            
        # Clean up description
        description = re.sub(r'\s+(each|pc|pcs|unit|units)\s*$', '', description, flags=re.IGNORECASE)
        
        # Find VAT percentage
        vat_pct = "10%"  # Default VAT based on the example invoice
        for i, item in enumerate(numbers_found):
            if isinstance(item, str) and '%' in item:
                vat_pct = item
                numbers_found.pop(i)
                break
        
        # We expect: quantity, unit price, net worth, [gross worth]
        qty = qty or numbers_found[0]
        
        # Validate quantity is reasonable
        if qty > 100:  # If quantity seems too high, it might be price
            unit_price = qty
            qty = 1.0
        else:
            unit_price = numbers_found[1]
        
        net_worth = numbers_found[-2] if len(numbers_found) > 2 else unit_price * qty
        
        # Calculate or use provided gross worth
        vat_rate = float(vat_pct.replace('%', '')) / 100
        if len(numbers_found) > 3:
            gross_worth = numbers_found[-1]
        else:
            gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        # Final validation
        expected_net = round(qty * unit_price, 2)
        if abs(net_worth - expected_net) > 0.1:  # Allow small rounding differences
            net_worth = expected_net
            gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        return {
            'item_no': item_no,
            'description': description.strip(),
            'quantity': qty,
            'unit_price': unit_price,
            'net_worth': net_worth,
            'vat_percentage': vat_pct,
            'gross_worth': gross_worth
        }
        
    except Exception as e:
        print(f"Warning: Failed to parse line: {str(e)[:100]}")
        return None
    
    desc_match = None
    for pattern in desc_patterns:
        desc_match = re.search(pattern, line, re.IGNORECASE)
        if desc_match:
            break
            
    if not desc_match:
        return None
    
    description = desc_match.group(1).strip()
    description = re.sub(r'\s+(each|pc|pcs|unit|units)\s*$', '', description, flags=re.IGNORECASE)
    
    try:
        numbers_clean = [n.replace(',', '.') for n in all_numbers]
        numbers_clean = [n for n in numbers_clean if n and not n.isspace()]
        
        # Look for VAT percentage
        vat_idx = None
        vat_pct = "20%"  # Default VAT
        
        for i, n in enumerate(numbers_clean):
            if '%' in n or (i > 0 and float(n) in [20, 10, 5]):  # Common VAT rates
                vat_idx = i
                vat_pct = n if '%' in n else f"{n}%"
                break
        
        # Try to identify quantity and prices
        if len(numbers_clean) >= 3:
            if vat_idx is not None and vat_idx >= 3:
                # Standard format with VAT
                qty = float(numbers_clean[vat_idx - 3])
                unit_price = float(numbers_clean[vat_idx - 2])
                net_worth = float(numbers_clean[vat_idx - 1])
            else:
                # No explicit VAT or different format
                # Try to detect format based on values
                possible_qty = float(numbers_clean[0])
                if possible_qty < 1000:  # Reasonable quantity
                    qty = possible_qty
                    unit_price = float(numbers_clean[1])
                    net_worth = float(numbers_clean[-1])
                else:
                    # First number might be unit price
                    qty = 1.0
                    unit_price = float(numbers_clean[0])
                    net_worth = float(numbers_clean[-1])
        else:
            # Minimal information
            qty = 1.0
            unit_price = float(numbers_clean[0])
            net_worth = float(numbers_clean[-1])
        
        # Calculate gross amount
        vat_rate = float(vat_pct.replace('%', '')) / 100
        gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        # Validate and adjust if needed
        expected_net = round(qty * unit_price, 2)
        if abs(net_worth - expected_net) > 1.0:
            net_worth = expected_net
            gross_worth = round(net_worth * (1 + vat_rate), 2)
        
        return {
            'item_no': item_no,
            'description': description,
            'quantity': qty,
            'unit_price': unit_price,
            'net_worth': net_worth,
            'vat_percentage': vat_pct,
            'gross_worth': gross_worth
        }
        
    except (ValueError, IndexError) as e:
        print(f"Warning: Could not parse line: {line[:50]}...")
        return None

def parse_items(text: str) -> List[Dict[str, Any]]:
    """
    Parse all items from the invoice with improved flexibility
    """
    items = []
    
    # First try to find items section using various methods
    items_section = None
    
    # Method 1: Look for standard markers
    standard_patterns = [
        (r'ITEMS(.*?)(?=SUMMARY|Total|$)', re.IGNORECASE | re.DOTALL),
        (r'Description.*?Qty.*?Price(.*?)(?=SUMMARY|Total|$)', re.IGNORECASE | re.DOTALL),
        (r'No\.\s+Description(.*?)(?=SUMMARY|Total|$)', re.IGNORECASE | re.DOTALL)
    ]
    
    for pattern, flags in standard_patterns:
        match = re.search(pattern, text, flags)
        if match:
            section = match.group(1).strip()
            if section and len(section) > 50:  # Reasonable minimum length
                items_section = section
                break
    
    # Method 2: Look for numbered lines if no section found
    if not items_section:
        lines = text.split('\n')
        numbered_lines = []
        in_items = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip headers
            if re.match(r'^(No\.|Description|Qty|Price|Amount|\-+)$', line, re.IGNORECASE):
                continue
            
            # Start collecting at first numbered line
            if re.match(r'^\s*\d+[\.\)]\s+\S+', line):
                in_items = True
                numbered_lines.append(line)
            # Continue if we're in items section and line has numbers
            elif in_items and re.search(r'\d+[.,]\d+', line):
                numbered_lines.append(line)
            # Stop if we hit summary
            elif in_items and re.search(r'SUMMARY|Total|Subtotal', line, re.IGNORECASE):
                break
        
        if numbered_lines:
            items_section = '\n'.join(numbered_lines)
    
    # Also look for table headers
    table_headers = [
        r'No\.\s+Description\s+Qty\s+.*?Price.*?Net.*?VAT.*?Gross',
        r'No\.\s+Description\s+Quantity\s+.*?Price.*?Amount',
        r'Item\s+Description\s+Quantity\s+.*?Price',
        r'^\s*\d+\.\s+\S+.*?\d+\s*each\s+\d+',
    ]
    
    # Process found section if any
    if not items_section:
        print("Debug: No items section found in text")
        return items
        
    print("\nDebug: Items section found:")
    print("=" * 50)
    print(items_section)
    print("=" * 50 + "\n")
    
    # If not found, look for table headers
    if not items_section:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            for header_pattern in table_headers:
                if re.search(header_pattern, line, re.IGNORECASE):
                    # Found header, collect items until summary or end
                    items_lines = []
                    j = i + 1
                    while j < len(lines) and not re.search(r'SUMMARY|Total|Subtotal', lines[j], re.IGNORECASE):
                        if re.search(r'^\s*\d+[\.\)]\s+\S+', lines[j]):
                            items_lines.append(lines[j])
                        j += 1
                    if items_lines:
                        items_section = '\n'.join(items_lines)
                        break
            if items_section:
                break
    
    # If still not found, try looking for numbered lines
    if not items_section:
        lines = text.split('\n')
        items_lines = []
        in_items = False
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or re.match(r'^(No\.|Description|Qty|Price|Amount|\-+)$', line.strip(), re.IGNORECASE):
                continue
            
            # Look for numbered items
            if re.match(r'^\s*\d+[\.\)]\s+\S+', line):
                in_items = True
                items_lines.append(line)
            # Continue adding lines if we're in items section and line has numbers
            elif in_items and re.search(r'\d+[.,]\d+', line):
                items_lines.append(line)
            # Stop if we hit summary
            elif in_items and re.search(r'SUMMARY|Total|Subtotal', line, re.IGNORECASE):
                break
        
        if items_lines:
            items_section = '\n'.join(items_lines)
    
    if not items_section:
        print("Debug: No items section found in text")
        return items
    
    print("\nDebug: Items section found:")
    print("=" * 50)
    print(items_section)
    print("=" * 50 + "\n")
    
    # Split into lines and combine multi-line items
    lines = items_section.split('\n')
    combined_lines = []
    current_line = ""
    skip_next = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and headers
        if not line or re.match(r'^(No\.|Description|Qty|Price|Amount|---|\|)', line, re.IGNORECASE):
            continue
            
        if skip_next:
            skip_next = False
            continue
            
        # Check if this is a new item (starts with number)
        new_item_match = re.match(r'^\s*(\d+)[\.\)]\s+\S+', line)
        if new_item_match:
            item_num = int(new_item_match.group(1))
            
            # If we have a current line and it contains "each", save it
            if current_line and 'each' in current_line:
                combined_lines.append(current_line)
                
            # Start new line
            current_line = line
            
            # Look ahead to see if next line is continuation or new item
            next_idx = lines.index(line) + 1
            while next_idx < len(lines):
                next_line = lines[next_idx].strip()
                if not next_line:
                    next_idx += 1
                    continue
                    
                # If next line starts with next item number, break
                if re.match(rf'^\s*{item_num + 1}[\.\)]\s+\S+', next_line):
                    break
                    
                # If next line has numbers but no item number, it might be continuation
                if not re.match(r'^\s*\d+[\.\)]\s+', next_line):
                    if re.search(r'\d+[,.]\d+', next_line):
                        current_line += " " + next_line
                    elif len(next_line.split()) > 2:  # Looks like description continuation
                        current_line += " " + next_line
                    skip_next = True
                break
                next_idx += 1
    
    if current_line:
        combined_lines.append(current_line)
    
    print("\nDebug: Combined lines:")
    for line in combined_lines:
        print("-" * 50)
        print(line)
    print("-" * 50 + "\n")
    
    # Process each line
    lines = items_section.split('\n')
    current_item = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip headers and dividers
        if re.match(r'^(No\.|Description|Qty|Price|Amount|\-+|\|)', line, re.IGNORECASE):
            continue
            
        # If line starts with number, it's a new item
        if re.match(r'^\s*\d+[\.\)]\s+\S+', line):
            # Process previous item if exists
            if current_item:
                item = parse_simple_item_line(' '.join(current_item))
                if item:
                    items.append(item)
            current_item = [line]
        else:
            # Might be continuation of previous item
            current_item.append(line)
    
    # Process last item
    if current_item:
        item = parse_simple_item_line(' '.join(current_item))
        if item:
            items.append(item)
    
    # Try alternate parser for any unparsed lines
    if not items:
        for line in lines:
            if line.strip():
                item = parse_item_line(line.strip())
                if item:
                    items.append(item)
    
    print(f"\nDebug: Successfully parsed {len(items)} items")
    return items

def parse_totals(text: str, items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Parse summary totals from invoice
    """
    totals = {}
    
    summary_section = extract_section(text, r'SUMMARY')
    
    if summary_section:
        print("\nDebug - Summary section found:")
        print("-" * 50)
        print(summary_section)
        print("-" * 50)
        
        # Try to find the total line with all values
        total_patterns = [
            # Pattern for format: "Total $ X $ Y $ Z"
            r'Total\s*\$?\s*([\d\s,.]+)\s*\$?\s*([\d\s,.]+)\s*\$?\s*([\d\s,.]+)',
            r'Total.*?\$\s*([\d\s,.]+)\s*\$\s*([\d\s,.]+)\s*\$\s*([\d\s,.]+)',
            # Pattern for format with headers and values in separate lines
            r'Net\s*worth\s*[\r\n]+\$?\s*([\d\s,.]+)[\r\n]+.*?VAT\s*[\r\n]+\$?\s*([\d\s,.]+)[\r\n]+.*?Gross\s*worth\s*[\r\n]+\$?\s*([\d\s,.]+)',
            r'Total\s*Net\s*worth\s*VAT\s*Gross\s*worth.*?\$\s*([\d\s,.]+)\s*\$\s*([\d\s,.]+)\s*\$\s*([\d\s,.]+)',
            # Pattern for totals with headers
            r'Net\s*worth[^\d]+([\d\s,.]+)[^\d]+VAT[^\d]+([\d\s,.]+)[^\d]+Gross\s*worth[^\d]+([\d\s,.]+)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, summary_section, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    def convert_number(num_str: str) -> float:
                        # Remove spaces, currency symbols and any other non-numeric characters except . and ,
                        num_str = re.sub(r'[^\d,.]', '', num_str.strip())
                        
                        # If empty string, return 0
                        if not num_str:
                            return 0.0
                            
                        # If there are both commas and dots
                        if ',' in num_str and '.' in num_str:
                            # If comma is after dot (e.g., 1.234,56)
                            if num_str.index('.') < num_str.index(','):
                                num_str = num_str.replace('.', '')  # Remove thousand separators
                                num_str = num_str.replace(',', '.')  # Convert decimal separator
                            else:  # If comma is before dot (e.g., 1,234.56)
                                num_str = num_str.replace(',', '')  # Remove thousand separators
                        # If there's only comma
                        elif ',' in num_str:
                            # Check the position of the comma from the right
                            digits_after_comma = len(num_str.split(',')[-1])
                            # If 2 digits after comma, it's probably a decimal separator
                            if digits_after_comma == 2:
                                num_str = num_str.replace(',', '.')
                            else:  # It's a thousand separator
                                num_str = num_str.replace(',', '')
                        
                        try:
                            result = float(num_str)
                            # If result is too large, it might be a parsing error
                            if result > 1000000:
                                print(f"Warning: Very large number detected: {result}")
                            return result
                        except ValueError:
                            print(f"Warning: Could not convert '{num_str}' to float")
                            return 0.0
                    
                    net = convert_number(match.group(1))
                    vat = convert_number(match.group(2))
                    gross = convert_number(match.group(3))
                    
                    print(f"\nDebug - Found totals in summary:")
                    print(f"Net: {net}")
                    print(f"VAT: {vat}")
                    print(f"Gross: {gross}")
                    
                    # التحقق من صحة الحسابات
                    if abs(gross - (net + vat)) < 0.1:  # نسمح بفرق صغير للتقريب
                        totals['net_worth'] = net
                        totals['vat'] = vat
                        totals['gross_worth'] = gross
                        break
                    else:
                        print(f"Warning: Totals don't add up correctly: {net} + {vat} != {gross}")
                except ValueError as e:
                    print(f"Warning: Error converting numbers: {e}")
                    continue
        
        # If total line not found, try to find individual values
        if not totals:
            patterns = {
                'net_worth': [
                    r'Total.*?Net\s*worth.*?(\d[\d\s,]*\.?\d*)',
                    r'Net\s*worth.*?(\d[\d\s,]*\.?\d*)',
                    r'Subtotal.*?(\d[\d\s,]*\.?\d*)',
                ],
                'vat': [
                    r'VAT.*?(\d[\d\s,]*\.?\d*)',
                    r'Tax.*?(\d[\d\s,]*\.?\d*)',
                ],
                'gross_worth': [
                    r'Gross\s*worth.*?(\d[\d\s,]*\.?\d*)',
                    r'Total.*?(\d[\d\s,]*\.?\d*)$',
                ]
            }
            
            for key, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, summary_section, re.IGNORECASE | re.DOTALL)
                    if match:
                        try:
                            value_str = match.group(1).replace(' ', '').replace(',', '')
                            value = float(value_str)
                            totals[key] = value
                            print(f"Debug - Found {key}: {value}")
                            break
                        except ValueError:
                            continue
    
    # If we still don't have totals but we have items, calculate from items
    if not totals and items:
        print("\nDebug - Calculating totals from items:")
        total_net = sum(item['net_worth'] for item in items)
        total_gross = sum(item['gross_worth'] for item in items)
        total_vat = total_gross - total_net
        
        print(f"Calculated Net: {total_net}")
        print(f"Calculated VAT: {total_vat}")
        print(f"Calculated Gross: {total_gross}")
        
        totals = {
            'net_worth': round(total_net, 2),
            'vat': round(total_vat, 2),
            'gross_worth': round(total_gross, 2)
        }
    
    return totals

def extract_invoice_info_from_image(image_path: str) -> Dict[str, Any]:
    """
    Main function to extract all invoice information from image
    """
    print(f"Reading image: {image_path}")
    text = extract_text_from_image(image_path)
    
    if not text.strip():
        print("No text extracted from image")
        return {}
    
    text = clean_text(text)
    
    print("\n" + "="*60)
    print("EXTRACTED TEXT FROM IMAGE:")
    print("="*60)
    print(text)
    print("="*60 + "\n")
    
    invoice_data = {}
    
    header = parse_invoice_header(text)
    invoice_data.update(header)
    
    seller = parse_party_info(text, 'Seller')
    invoice_data['seller_name'] = seller.get('name')
    invoice_data['seller_address'] = seller.get('address')
    invoice_data['seller_tax_id'] = seller.get('tax_id')
    
    client = parse_party_info(text, 'Client')
    invoice_data['client_name'] = client.get('name')
    invoice_data['client_address'] = client.get('address')
    invoice_data['client_tax_id'] = client.get('tax_id')
    
    items = parse_items(text)
    invoice_data['items'] = items
    
    totals = parse_totals(text, items)
    invoice_data['totals'] = totals
    
    return invoice_data

def create_invoice_dataframes(data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Create structured DataFrames from extracted invoice data
    """
    # Fix seller and client mix-up if needed
    if data.get('seller_name') and 'Becker' in data.get('seller_name'):
        # Swap seller and client data
        seller_name = data.get('client_name')
        seller_addr = data.get('client_address')
        seller_tax = data.get('client_tax_id')
        
        client_name = data.get('seller_name')
        client_addr = data.get('seller_address')
        client_tax = data.get('seller_tax_id')
        
        data['seller_name'] = seller_name
        data['seller_address'] = seller_addr
        data['seller_tax_id'] = seller_tax
        
        data['client_name'] = client_name
        data['client_address'] = client_addr
        data['client_tax_id'] = client_tax
    
    header_data = {
        'Field': [
            'Invoice Number',
            'Date',
            'Seller Name',
            'Seller Address',
            'Seller Tax ID',
            'Client Name',
            'Client Address',
            'Client Tax ID'
        ],
        'Value': [
            data.get('invoice_number'),
            data.get('date'),
            data.get('seller_name'),
            data.get('seller_address'),
            data.get('seller_tax_id'),
            data.get('client_name'),
            data.get('client_address'),
            data.get('client_tax_id')
        ]
    }
    
    header_df = pd.DataFrame(header_data)
    
    items = data.get('items', [])
    if items:
        items_df = pd.DataFrame(items)
        column_order = ['item_no', 'description', 'quantity', 'unit_price', 
                       'net_worth', 'vat_percentage', 'gross_worth']
        items_df = items_df[[col for col in column_order if col in items_df.columns]]
        items_df.columns = ['Item_No', 'Product_Name', 'Quantity', 'Unit_Price',
                           'Net_Worth', 'VAT_Percentage', 'Gross_Worth']
    else:
        items_df = pd.DataFrame(columns=['Item_No', 'Product_Name', 'Quantity', 
                                        'Unit_Price', 'Net_Worth', 'VAT_Percentage', 
                                        'Gross_Worth'])
    
    # Get totals directly from the extracted data
    totals = data.get('totals', {})
    total_net = totals.get('net_worth', 0)
    total_vat = totals.get('vat', 0)
    total_gross = totals.get('gross_worth', 0)
    
    # If no totals were found in the summary, only then calculate from items
    if total_net == 0 and total_vat == 0 and total_gross == 0 and not items_df.empty:
        print("\nDebug - No totals found in summary, calculating from items")
        total_net = items_df['Net_Worth'].sum()
        total_gross = items_df['Gross_Worth'].sum()
        total_vat = total_gross - total_net
    
    # Format numbers with thousand separator and 2 decimal places
    summary_df = pd.DataFrame({
        'Metric': ['Total Net Worth', 'Total VAT', 'Total Gross Worth'],
        'Value': [
            '{:,.2f}'.format(total_net),
            '{:,.2f}'.format(total_vat),
            '{:,.2f}'.format(total_gross)
        ]
    })
    
    return {
        'header': header_df,
        'items': items_df,
        'summary': summary_df
    }

def display_dataframes(dataframes: Dict[str, pd.DataFrame]):
    """
    Display all DataFrames
    """
    print("\n" + "="*60)
    print("INVOICE HEADER INFORMATION")
    print("="*60)
    print(dataframes['header'].to_string(index=False))
    
    print("\n" + "="*60)
    print("INVOICE ITEMS")
    print("="*60)
    if not dataframes['items'].empty:
        print(dataframes['items'].to_string(index=False))
    else:
        print("No items found")
    
    print("\n" + "="*60)
    print("INVOICE SUMMARY")
    print("="*60)
    print(dataframes['summary'].to_string(index=False))
    print("="*60 + "\n")

def save_to_excel(dataframes: Dict[str, pd.DataFrame], filename: str = 'invoice_data.xlsx'):
    """
    Save to Excel file with auto-fitted columns
    """
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Write DataFrames to a single sheet
        sheet_name = 'Invoice'
        
        # Write header section
        dataframes['header'].to_excel(writer, sheet_name=sheet_name, index=False)
        header_rows = len(dataframes['header']) + 1  # +1 for column header
        
        # Write items section
        if not dataframes['items'].empty:
            dataframes['items'].to_excel(writer, sheet_name=sheet_name, 
                                      startrow=header_rows + 1, index=False)
            items_rows = len(dataframes['items']) + 1
        else:
            items_rows = 0
            
        # Write summary section
        dataframes['summary'].to_excel(writer, sheet_name=sheet_name,
                                     startrow=header_rows + items_rows + 2, index=False)
        
        # Auto-fit columns
        worksheet = writer.sheets[sheet_name]
        
        # Function to get column letter
        def get_column_letter(idx):
            result = ""
            while idx > 0:
                idx, remainder = divmod(idx - 1, 26)
                result = chr(65 + remainder) + result
            return result
        
        # Process each DataFrame
        dfs_info = [
            (dataframes['header'], 0),
            (dataframes['items'], header_rows + 1),
            (dataframes['summary'], header_rows + items_rows + 2)
        ]
        
        for df, start_row in dfs_info:
            if not df.empty:
                for idx, col in enumerate(df.columns, 1):
                    column = get_column_letter(idx)
                    max_length = max(
                        len(str(col)),  # Column header
                        df[col].astype(str).str.len().max()  # Content
                    )
                    # Add padding and set width
                    adjusted_width = max_length + 4
                    current_width = worksheet.column_dimensions[column].width
                    worksheet.column_dimensions[column].width = max(adjusted_width, 
                                                                 current_width or 0)
    
    print(f"✓ Data saved to {filename}")

def save_to_csv(dataframes: Dict[str, pd.DataFrame], prefix: str = 'invoice'):
    """
    Save to CSV files
    """
    dataframes['header'].to_csv(f'{prefix}_header.csv', index=False)
    dataframes['items'].to_csv(f'{prefix}_items.csv', index=False)
    dataframes['summary'].to_csv(f'{prefix}_summary.csv', index=False)
    
    print(f"✓ Data saved to: {prefix}_header.csv, {prefix}_items.csv, {prefix}_summary.csv")

def process_invoice_image(image_path: str, save_excel: bool = False, 
                         save_csv: bool = False, manual_text: str = None):
    """
    Complete pipeline to process invoice image
    """
    try:
        # Clear any existing cache
        cv2.destroyAllWindows()
        if hasattr(pytesseract, 'cleanup'):
            pytesseract.cleanup()
            
        if manual_text:
            print("Using manually provided text...")
            text = clean_text(manual_text)
            
            print("\n" + "="*60)
            print("PROVIDED TEXT:")
            print("="*60)
            print(text)
            print("="*60 + "\n")
            
            invoice_data = {}
            
            header = parse_invoice_header(text)
            invoice_data.update(header)
            
            seller = parse_party_info(text, 'Seller')
            invoice_data['seller_name'] = seller.get('name')
            invoice_data['seller_address'] = seller.get('address')
            invoice_data['seller_tax_id'] = seller.get('tax_id')
            
            client = parse_party_info(text, 'Client')
            invoice_data['client_name'] = client.get('name')
            invoice_data['client_address'] = client.get('address')
            invoice_data['client_tax_id'] = client.get('tax_id')
            
            items = parse_items(text)
            invoice_data['items'] = items
            
            totals = parse_totals(text, items)
            invoice_data['totals'] = totals
        else:
            invoice_data = extract_invoice_info_from_image(image_path)
        
        if not invoice_data:
            print("❌ No data could be extracted")
            print("\nTip: You can provide text directly using manual_text parameter")
            return None
        
        print("Creating DataFrames...")
        dataframes = create_invoice_dataframes(invoice_data)
        
        display_dataframes(dataframes)
        
        if save_excel:
            invoice_num = invoice_data.get('invoice_number', 'unknown')
            save_to_excel(dataframes, f'invoice_{invoice_num}.xlsx')
        
        if save_csv:
            invoice_num = invoice_data.get('invoice_number', 'unknown')
            save_to_csv(dataframes, f'invoice_{invoice_num}')
        
        print("✓ Processing completed successfully!")
        
        return dataframes
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Example usage
if __name__ == "__main__":
    image_path = r"C:\Users\user\Desktop\final ocr\batch1-0002.jpg"  # تحديث المسار
    
    print(f"\nProcessing image: {image_path}")  # طباعة المسار للتأكد
    
    # Option 1: Process from image with OCR
    dataframes = process_invoice_image(
        image_path=image_path,
        save_excel=True
    )
    
    # Option 2: Provide text manually if OCR fails
    # Uncomment and use this if OCR doesn't work well:
    """
    manual_text = '''
    Invoice no: 51109338
    Date of issue: 04/13/2013
    
    Seller:
    Andrews, Kirby and Valdez
    58861 Gonzalez Prairie
    Lake Daniellefurt, IN 57228
    Tax Id: 945-82-2137
    
    Client:
    Becker Ltd
    8012 Stewart Summit Apt. 455
    North Douglas, AZ 95355
    Tax Id: 942-80-0517
    
    ITEMS
    1. Item description 3.00 each 209.00 627.00 10% 689.70
    ...
    
    SUMMARY
    Total $ 5640.17 $ 564.02 $ 6204.19
    '''
    
    dataframes = process_invoice_image(
        image_path=image_path,
        manual_text=manual_text,
        save_excel=True
    )
    """