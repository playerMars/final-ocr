import cv2import cv2

import pytesseractimport pytesseract

import numpy as npimport numpy as np

import pandas as pdimport re

import refrom typing import Dict, List

import osimport pandas as pd

import jsonimport json

import globimport os

from datetime import datetimefrom datetime import datetime

from typing import Dict, List, Any, Optional, Tuple

from PIL import Imageclass InvoiceParser:

    def __init__(self):

class InvoiceParser:        self.invoice_data = {

    """A class to parse invoice images and extract structured data"""            'invoice_number': [],

                'date': [],

    def __init__(self):            'total': [],

        # Pre-compile regex patterns for better performance            'seller_name': [],

        self.invoice_patterns = [            'seller_address': [],

            r'Invoice\s*no[:.]\s*(\d+)',            'seller_phone': [],

            r'Invoice\s*number[:.]\s*(\d+)',            'product_names': [],

            r'Invoice\s*#[:.]\s*(\d+)',            'quantities': [],

            r'Invoice[:.]\s*(\d+)',            'unit_prices': [],

            r'[\n\r](\d{8,})'            'vat': [],

        ]            'discount': [],

                    'total_per_item': []

        self.date_patterns = [        }

            r'Date\s*(?:of\s*issue)?[:.]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',    

            r'(?:Issue|Invoice)\s*date[:.]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',    def preprocess_image(self, image_path: str) -> np.ndarray:

            r'[\n\r](\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'        """

        ]        Preprocess the image to improve OCR accuracy

                """

        self.item_patterns = [        # Verify file exists and is accessible

            r'^(?:\d+\.)?\s*([^0-9]+?)\s+(\d+(?:[.,]\d+)?)\s+(?:each\s+)?(\d+(?:[.,]\d+)?)\s+(\d+)%?\s+(\d+(?:[.,]\d+)?)',        if not os.path.exists(image_path):

            r'^(?:\d+\.)?\s*([^0-9]+?)\s+(\d+(?:[.,]\d+)?)\s+(?:each\s+)?(?:[\$€]?\s*(\d+(?:[.,]\d+)?))?'            raise ValueError(f"Image file does not exist: {image_path}")

        ]            

        # Read image

    def preprocess_image(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:        try:

        """Preprocess image for better OCR accuracy"""            img = cv2.imread(image_path)

        # Clear any existing windows            if img is None:

        cv2.destroyAllWindows()                raise ValueError(f"Could not read image: {image_path}")

                except Exception as e:

        # Read image            raise ValueError(f"Error reading image {image_path}: {str(e)}")

        img = cv2.imread(image_path)            

        if img is None:        # Convert to grayscale

            raise ValueError(f"Failed to load image: {image_path}")        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                

        # Convert to grayscale        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

                enhanced = clahe.apply(gray)

        # Enhance contrast        

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))        # Denoise

        enhanced = clahe.apply(gray)        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

                

        # Denoise        # Thresholding

        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                

        # Adaptive threshold        # Check if image is too small

        thresh = cv2.adaptiveThreshold(        height, width = thresh.shape

            denoised,         if height < 2000:  # Resize if image is small

            255,             scale = 2000 / height

            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,            thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            cv2.THRESH_BINARY_INV,        

            11,        return thresh

            2

        )    def extract_text(self, image_path: str) -> str:

                """

        # Resize if image is too small        Extract text from image using multiple OCR attempts

        height = thresh.shape[0]        """

        if height < 2000:        # Preprocess image

            scale = 2000 / height        processed_img = self.preprocess_image(image_path)

            thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)        

                # Multiple OCR configurations

        return thresh, gray        configs = [

            r'--oem 3 --psm 6',  # Assume uniform block of text

    def extract_text(self, image: np.ndarray) -> str:            r'--oem 3 --psm 1',  # Automatic page segmentation

        """Extract text from image using multiple OCR configurations"""            r'--oem 1 --psm 6',  # Legacy engine

        configs = [        ]

            '--oem 3 --psm 6',  # Assume uniform block of text        

            '--oem 3 --psm 1',  # Automatic page segmentation        best_text = ""

            '--oem 1 --psm 6'   # Legacy engine with uniform text        max_length = 0

        ]        

                for config in configs:

        best_text = ""            try:

        max_length = 0                text = pytesseract.image_to_string(processed_img, config=config, lang='eng')

                        if len(text) > max_length:

        for config in configs:                    best_text = text

            try:                    max_length = len(text)

                text = pytesseract.image_to_string(image, config=config, lang='eng')            except Exception as e:

                if len(text) > max_length:                print(f"OCR error with config {config}: {str(e)}")

                    best_text = text                continue

                    max_length = len(text)        

            except Exception as e:        return best_text

                print(f"OCR error with config {config}: {str(e)}")

                continue    def clean_number(self, num_str: str) -> float:

                """

        return self._clean_text(best_text)        Clean and convert number strings to float

        """

    def _clean_text(self, text: str) -> str:        try:

        """Clean OCR output text"""            # Remove any non-numeric characters except . and ,

        replacements = {            num_str = re.sub(r'[^\d,.]', '', num_str.strip())

            'Deil': 'Dell',            

            'De11': 'Dell',            if not num_str:

            'HPT520': 'HP T520',                return 0.0

            'C1ient': 'Client',            

            'Bui1d': 'Build',            # Handle different number formats

            'Optip1ex': 'Optiplex',            if ',' in num_str and '.' in num_str:

            '|': 'I',                if num_str.index(',') > num_str.index('.'):

            '\n\n': '\n'                    # Format: 1.234,56

        }                    num_str = num_str.replace('.', '').replace(',', '.')

                        else:

        for old, new in replacements.items():                    # Format: 1,234.56

            text = text.replace(old, new)                    num_str = num_str.replace(',', '')

                    elif ',' in num_str:

        return text.strip()                # If comma is close to end, treat as decimal

                if len(num_str.split(',')[1]) <= 2:

    def extract_invoice_number(self, text: str) -> str:                    num_str = num_str.replace(',', '.')

        """Extract invoice number using multiple patterns"""                else:

        for pattern in self.invoice_patterns:                    num_str = num_str.replace(',', '')

            match = re.search(pattern, text, re.IGNORECASE)            

            if match:            return float(num_str)

                return match.group(1)        except:

        return ""            return 0.0



    def extract_date(self, text: str) -> str:    def extract_invoice_number(self, text: str) -> str:

        """Extract invoice date using multiple patterns"""        """Extract invoice number"""

        for pattern in self.date_patterns:        patterns = [

            match = re.search(pattern, text, re.IGNORECASE)            r'Invoice\s*(?:no|number|#)?\s*[:]?\s*(\d+)',

            if match:            r'Invoice\s*#\s*(\d+)',

                return match.group(1)            r'Invoice\s*:\s*(\d+)',

        return ""            r'INV[.-]?(\d+)',

        ]

    def extract_party_info(self, text: str, party_type: str) -> Dict[str, str]:        

        """Extract seller or client information"""        for pattern in patterns:

        section_pattern = f"{party_type}:(.*?)(?=Client:|ITEMS|$)" if party_type == "Seller" else r"Client:(.*?)(?=ITEMS|$)"            match = re.search(pattern, text, re.IGNORECASE)

        tax_pattern = r"Tax\s*Id:?\s*([\d\-]+)"            if match:

                        return match.group(1)

        info = {}        return ""

        

        # Extract main section    def extract_date(self, text: str) -> str:

        section_match = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)        """Extract invoice date"""

        if section_match:        patterns = [

            lines = [line.strip() for line in section_match.group(1).split('\n') if line.strip()]            r'Date\s*(?:of\s*issue)?[:\s]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',

            if lines:            r'Date[:\s]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',

                info['name'] = lines[0]            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',

                info['address'] = ' '.join(lines[1:]) if len(lines) > 1 else ""        ]

                

        # Extract tax ID        for pattern in patterns:

        tax_match = re.search(tax_pattern, text)            match = re.search(pattern, text, re.IGNORECASE)

        if tax_match:            if match:

            info['tax_id'] = tax_match.group(1)                date_str = match.group(1)

                        # Try to parse and standardize date format

        return info                try:

                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y']:

    def extract_items(self, text: str) -> List[Dict[str, Any]]:                        try:

        """Extract item details from invoice"""                            date_obj = datetime.strptime(date_str, fmt)

        items = []                            return date_obj.strftime('%Y-%m-%d')

                                except:

        # Find items section                            continue

        items_section = re.search(r'ITEMS(.*?)(?=SUMMARY|$)', text, re.IGNORECASE | re.DOTALL)                except:

        if not items_section:                    return date_str

            return items        return ""

            

        lines = items_section.group(1).split('\n')    def extract_seller_info(self, text: str) -> tuple:

                """Extract seller information"""

        for line in lines:        seller_section = ""

            line = line.strip()        seller_name = ""

            if not line or re.match(r'^(No\.|Description|Qty)', line, re.IGNORECASE):        seller_address = ""

                continue        seller_phone = ""

                    

            # Try to match item details        # Try to find seller section

            for pattern in self.item_patterns:        patterns = [

                match = re.search(pattern, line)            r'Seller[\s:]+(.+?)(?=Client|Customer|Bill to|Ship to|ITEMS)',

                if match:            r'From[\s:]+(.+?)(?=To|ITEMS)',

                    groups = match.groups()        ]

                    item = {        

                        'description': groups[0].strip(),        for pattern in patterns:

                        'quantity': self._parse_number(groups[1]),            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

                        'unit_price': self._parse_number(groups[2]) if len(groups) > 2 and groups[2] else 0.0,            if match:

                        'vat': groups[3] if len(groups) > 3 and groups[3] else "10",                seller_section = match.group(1).strip()

                        'total': self._parse_number(groups[4]) if len(groups) > 4 and groups[4] else 0.0                break

                    }        

                            if seller_section:

                    # Calculate missing values            lines = seller_section.split('\n')

                    if item['total'] == 0.0:            lines = [line.strip() for line in lines if line.strip()]

                        item['total'] = item['quantity'] * item['unit_price']            

                                if lines:

                    items.append(item)                # First line is usually the name

                    break                seller_name = lines[0]

                        

        return items                # Look for phone number

                phone_pattern = r'(?:Phone|Tel|Mobile)[:\s]*([+\d\s\-()]+)'

    def _parse_number(self, text: str) -> float:                for line in lines:

        """Convert string to float, handling different number formats"""                    phone_match = re.search(phone_pattern, line, re.IGNORECASE)

        if not text:                    if phone_match:

            return 0.0                        seller_phone = phone_match.group(1).strip()

                                lines.remove(line)

        # Remove currency symbols and spaces                        break

        text = re.sub(r'[^\d,.-]', '', text)                

                        # Remaining lines (excluding tax ID and IBAN) are address

        # Handle different number formats                address_lines = []

        if ',' in text and '.' in text:                for line in lines[1:]:

            if text.index(',') > text.index('.'):                    if not any(x in line.lower() for x in ['tax', 'iban', 'phone', 'tel']):

                text = text.replace('.', '').replace(',', '.')                        address_lines.append(line)

            else:                seller_address = ' '.join(address_lines)

                text = text.replace(',', '')        

        elif ',' in text:        return seller_name, seller_address, seller_phone

            text = text.replace(',', '.')

            def extract_items(self, text: str) -> tuple:

        try:        """Extract item information"""

            return float(text)        items_section = ""

        except:        patterns = [

            return 0.0            r'ITEMS(.*?)(?=SUMMARY|Total)',

            r'Description(.*?)(?=SUMMARY|Total)',

    def extract_totals(self, text: str, items: List[Dict[str, Any]]) -> Dict[str, float]:        ]

        """Extract or calculate invoice totals"""        

        summary_section = re.search(r'SUMMARY(.*?)$', text, re.IGNORECASE | re.DOTALL)        for pattern in patterns:

        if summary_section:            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

            # Try to find totals in summary            if match:

            total_match = re.search(r'Total\s*\$?\s*([\d,.]+)\s*\$?\s*([\d,.]+)\s*\$?\s*([\d,.]+)',                 items_section = match.group(1).strip()

                                  summary_section.group(1))                break

                    

            if total_match:        if not items_section:

                return {            return [], [], [], [], [], []

                    'net_worth': self._parse_number(total_match.group(1)),        

                    'vat': self._parse_number(total_match.group(2)),        # Split into lines and process each item

                    'gross_worth': self._parse_number(total_match.group(3))        lines = items_section.split('\n')

                }        current_item = []

                items = []

        # Calculate totals from items if summary not found        

        if items:        for line in lines:

            total_net = sum(item['total'] for item in items)            line = line.strip()

            total_vat = sum(item['total'] * float(item['vat']) / 100 for item in items)            if not line:

            total_gross = total_net + total_vat                continue

                            

            return {            # If line starts with number, it's a new item

                'net_worth': round(total_net, 2),            if re.match(r'^\d+\.?\s+', line):

                'vat': round(total_vat, 2),                if current_item:

                'gross_worth': round(total_gross, 2)                    items.append(' '.join(current_item))

            }                current_item = [re.sub(r'^\d+\.?\s+', '', line)]

                    else:

        return {'net_worth': 0.0, 'vat': 0.0, 'gross_worth': 0.0}                if current_item and not re.search(r'\d+[.,]\d+', line):

                    current_item.append(line)

    def process_invoice(self, image_path: str) -> Dict[str, Any]:        

        """Process a single invoice image and extract all information"""        if current_item:

        try:            items.append(' '.join(current_item))

            # Preprocess image and extract text        

            processed_img, gray_img = self.preprocess_image(image_path)        # Extract quantities, prices, and totals

            text = self.extract_text(processed_img)        quantities = []

                    unit_prices = []

            # Parse invoice data        total_per_item = []

            invoice_data = {        vat_values = []

                'invoice_number': self.extract_invoice_number(text),        discounts = []

                'date': self.extract_date(text)        

            }        for item in items:

                        # Look for quantity

            # Extract party information            qty_match = re.search(r'(\d+[.,]?\d*)\s*(?:each|pc|pcs|units?)', item)

            seller_info = self.extract_party_info(text, 'Seller')            quantities.append(self.clean_number(qty_match.group(1)) if qty_match else 1.0)

            client_info = self.extract_party_info(text, 'Client')            

                        # Look for unit price

            invoice_data.update({            price_match = re.search(r'(?:price|@)\s*(\d+[.,]?\d*)', item)

                'seller_name': seller_info.get('name', ''),            if not price_match:

                'seller_address': seller_info.get('address', ''),                price_match = re.search(r'(\d+[.,]?\d*)(?=\s*(?:each|pc|pcs|units?))', item)

                'seller_tax_id': seller_info.get('tax_id', ''),            unit_prices.append(self.clean_number(price_match.group(1)) if price_match else 0.0)

                'client_name': client_info.get('name', ''),            

                'client_address': client_info.get('address', ''),            # Look for total

                'client_tax_id': client_info.get('tax_id', '')            total_match = re.search(r'(?:total|worth|amount)\s*[\$\€]?\s*(\d+[.,]?\d*)', item)

            })            total_per_item.append(self.clean_number(total_match.group(1)) if total_match else 0.0)

                        

            # Extract items and totals            # Look for VAT

            items = self.extract_items(text)            vat_match = re.search(r'(\d+)%', item)

            invoice_data['items'] = items            vat_values.append(vat_match.group(1) if vat_match else "0")

            invoice_data['totals'] = self.extract_totals(text, items)            

                        # Look for discount

            return invoice_data            discount_match = re.search(r'discount\s*[\$\€]?\s*(\d+[.,]?\d*)', item, re.IGNORECASE)

                        discounts.append(self.clean_number(discount_match.group(1)) if discount_match else 0.0)

        except Exception as e:        

            print(f"Error processing invoice {image_path}: {str(e)}")        # Clean product names by removing numeric and special characters

            return {}        product_names = []

        for item in items:

def process_invoices(directory: str):            # Remove price, quantity, and other numeric information

    """Process all invoice images in a directory"""            name = re.sub(r'\d+[.,]?\d*\s*(?:each|pc|pcs|units?|€|\$|%)', '', item)

    parser = InvoiceParser()            name = re.sub(r'(?:price|amount|total|worth|vat|tax|discount).*', '', name, flags=re.IGNORECASE)

    all_data = []            product_names.append(' '.join(name.split()))

            

    # Get all image files        return product_names, quantities, unit_prices, vat_values, discounts, total_per_item

    image_files = []

    for ext in ['*.jpg', '*.jpeg', '*.png', '*.tiff']:    def extract_total(self, text: str) -> float:

        image_files.extend(glob.glob(os.path.join(directory, ext)))        """Extract total amount"""

            patterns = [

    if not image_files:            r'Total\s*(?:amount)?[:\s]\s*[\$\€]?\s*(\d+[.,]?\d*)',

        print(f"No image files found in {directory}")            r'Grand\s*total[:\s]\s*[\$\€]?\s*(\d+[.,]?\d*)',

        return            r'Amount\s*due[:\s]\s*[\$\€]?\s*(\d+[.,]?\d*)',

            ]

    # Process each invoice        

    for image_file in image_files:        for pattern in patterns:

        print(f"\nProcessing: {os.path.basename(image_file)}")            match = re.search(pattern, text, re.IGNORECASE)

        data = parser.process_invoice(image_file)            if match:

        if data:                return self.clean_number(match.group(1))

            all_data.append(data)        return 0.0

    

    if all_data:    def parse_invoice(self, image_path: str) -> Dict:

        # Save results        """

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")        Main function to parse invoice

                """

        # Save to Excel        # Reset invoice data

        excel_path = os.path.join(directory, f'invoice_analysis_{timestamp}.xlsx')        self.invoice_data = {key: [] for key in self.invoice_data.keys()}

                

        # Create DataFrames        # Extract text from image

        headers = []        text = self.extract_text(image_path)

        items = []        if not text:

                    return self.invoice_data

        for invoice in all_data:        

            # Add header information        # Extract items information first to get the number of items

            headers.append({        product_names, quantities, unit_prices, vat_values, discounts, totals = self.extract_items(text)

                'Invoice Number': invoice['invoice_number'],        num_items = len(product_names)

                'Date': invoice['date'],        

                'Seller Name': invoice['seller_name'],        # Extract single-value information and repeat for each item

                'Seller Address': invoice['seller_address'],        invoice_number = self.extract_invoice_number(text)

                'Seller Tax ID': invoice['seller_tax_id'],        date = self.extract_date(text)

                'Client Name': invoice['client_name'],        total = self.extract_total(text)

                'Client Address': invoice['client_address'],        seller_name, seller_address, seller_phone = self.extract_seller_info(text)

                'Client Tax ID': invoice['client_tax_id'],        

                'Total Net': invoice['totals']['net_worth'],        # Fill arrays with repeated values

                'Total VAT': invoice['totals']['vat'],        self.invoice_data['invoice_number'] = [invoice_number] * num_items if num_items > 0 else [invoice_number]

                'Total Gross': invoice['totals']['gross_worth']        self.invoice_data['date'] = [date] * num_items if num_items > 0 else [date]

            })        self.invoice_data['total'] = [total] * num_items if num_items > 0 else [total]

                    self.invoice_data['seller_name'] = [seller_name] * num_items if num_items > 0 else [seller_name]

            # Add items        self.invoice_data['seller_address'] = [seller_address] * num_items if num_items > 0 else [seller_address]

            for item in invoice['items']:        self.invoice_data['seller_phone'] = [seller_phone] * num_items if num_items > 0 else [seller_phone]

                items.append({        

                    'Invoice Number': invoice['invoice_number'],        # Fill arrays with item-specific values

                    'Description': item['description'],        self.invoice_data['product_names'] = product_names if product_names else [""]

                    'Quantity': item['quantity'],        self.invoice_data['quantities'] = quantities if quantities else [0]

                    'Unit Price': item['unit_price'],        self.invoice_data['unit_prices'] = unit_prices if unit_prices else [0]

                    'VAT %': item['vat'],        self.invoice_data['vat'] = vat_values if vat_values else ["0"]

                    'Total': item['total']        self.invoice_data['discount'] = discounts if discounts else [0]

                })        self.invoice_data['total_per_item'] = totals if totals else [0]

                

        # Create Excel writer        # Ensure all arrays have the same length

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:        max_length = max(len(arr) for arr in self.invoice_data.values())

            pd.DataFrame(headers).to_excel(writer, sheet_name='Invoices', index=False)        for key in self.invoice_data:

            pd.DataFrame(items).to_excel(writer, sheet_name='Items', index=False)            while len(self.invoice_data[key]) < max_length:

                        if isinstance(self.invoice_data[key][0], str):

        print(f"\nProcessed {len(all_data)} invoices")                    self.invoice_data[key].append("")

        print(f"Results saved to: {excel_path}")                else:

                            self.invoice_data[key].append(0)

        return all_data        

        return self.invoice_data

if __name__ == "__main__":

    directory = os.path.dirname(os.path.abspath(__file__))    def save_to_json(self, output_file: str):

    print(f"Processing invoices in: {directory}")        """Save extracted data to JSON file"""

    results = process_invoices(directory)        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.invoice_data, f, ensure_ascii=False, indent=4)

    def save_to_excel(self, output_file: str):
        """Save extracted data to Excel file"""
        df = pd.DataFrame(self.invoice_data)
        df.to_excel(output_file, index=False)

def main():
    # Initialize parser
    parser = InvoiceParser()
    
    # Process invoice
    image_path = input(r"C:\Users\user\Desktop\final ocr\batch1-0001.jpg")
    try:
        invoice_data = parser.parse_invoice(image_path)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parser.save_to_json(f'invoice_analysis_{timestamp}.json')
        parser.save_to_excel(f'invoice_analysis_{timestamp}.xlsx')
        
        print("\nExtracted Data:")
        print("==============")
        for key, value in invoice_data.items():
            print(f"{key}: {value}")
        
        print("\nResults have been saved to JSON and Excel files")
        
    except Exception as e:
        print(f"Error processing invoice: {str(e)}")

if __name__ == "__main__":
    main()
