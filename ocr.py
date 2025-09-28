import re
import pandas as pd
from typing import Dict, List, Any, Optional
import pytesseract
from PIL import Image
import cv2
import numpy as np

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Preprocess image to improve OCR accuracy
    """
    # Read image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Apply threshold to get image with only black and white
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Dilate to connect text components
    kernel = np.ones((1,1), np.uint8)
    processed = cv2.dilate(thresh, kernel, iterations=1)
    
    return processed

def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using OCR
    """
    try:
        # Preprocess image
        processed_img = preprocess_image(image_path)
        
        # Configure OCR
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:/%-$()[]|! '
        
        # Extract text
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        return text
        
    except Exception as e:
        print(f"Error during OCR: {e}")
        # Fallback: try with original image
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e2:
            print(f"Fallback OCR also failed: {e2}")
            return ""

def extract_invoice_info_from_image(image_path: str) -> Dict[str, Any]:
    """
    Extract invoice information from image file
    """
    # Extract text from image
    print(f"Extracting text from image: {image_path}")
    text = extract_text_from_image(image_path)
    
    if not text.strip():
        print("No text extracted from image")
        return {}
    
    print("Text extracted successfully. Processing...")
    print("="*50)
    print("EXTRACTED TEXT:")
    print(text)
    print("="*50)
    
    # Process the extracted text
    return extract_invoice_info_to_dataframe(text)

def extract_invoice_info_to_dataframe(text: str) -> Dict[str, Any]:
    """
    Extract invoice information and store in structured format
    """
    
    # Clean text
    text = re.sub(r'\n\s*\n', '\n', text)
    lines = text.split('\n')
    
    invoice_data = {
        'invoice_number': [],
        'date': [],
        'total': [],
        'seller_name': [],
        'seller_address': [],
        'seller_tax_id': [],
        'client_name': [],
        'client_address': [],
        'client_tax_id': [],
        'product_names': [],
        'quantities': [],
        'unit_prices': [],
        'net_worth': [],
        'vat_percentage': [],
        'gross_worth': [],
        'discount': []
    }
    
    # 1. Invoice Number
    invoice_patterns = [
        r'Invoice\s+no:?\s*(\d+)',
        r'Invoice\s+number:?\s*(\d+)',
        r'Invoice\s*#\s*(\d+)',
        r'INV\s*-?\s*(\d+)'
    ]
    
    for pattern in invoice_patterns:
        invoice_match = re.search(pattern, text, re.IGNORECASE)
        if invoice_match:
            invoice_data['invoice_number'].append(invoice_match.group(1))
            break
    
    # 2. Date - Multiple patterns to handle OCR variations
    date_patterns = [
        r'Date\s+of\s+issue:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
        r'Date:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
        r'Issue\s+date:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            invoice_data['date'].append(date_match.group(1))
            break
    
    # 3. Seller Information
    seller_patterns = [
        r'Seller:?\s*(.*?)(?=Client:|ITEMS|Items)',
        r'From:?\s*(.*?)(?=To:|Bill\s+to:|ITEMS|Items)',
        r'Vendor:?\s*(.*?)(?=Customer:|ITEMS|Items)'
    ]
    
    for pattern in seller_patterns:
        seller_section = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if seller_section:
            seller_text = seller_section.group(1).strip()
            seller_lines = [line.strip() for line in seller_text.split('\n') if line.strip()]
            
            if seller_lines:
                # Seller name (first line)
                invoice_data['seller_name'].append(seller_lines[0])
                
                # Process remaining lines for address and tax ID
                address_parts = []
                for line in seller_lines[1:]:
                    if re.search(r'Tax\s+Id:?\s*([\d\-]+)', line, re.IGNORECASE):
                        tax_id = re.search(r'Tax\s+Id:?\s*([\d\-]+)', line, re.IGNORECASE)
                        if tax_id:
                            invoice_data['seller_tax_id'].append(tax_id.group(1))
                    elif not re.search(r'IBAN|Phone|Email', line, re.IGNORECASE):
                        address_parts.append(line)
                
                if address_parts:
                    invoice_data['seller_address'].append(', '.join(address_parts))
            break
    
    # 4. Client Information
    client_patterns = [
        r'Client:?\s*(.*?)(?=ITEMS|Items|Tax\s+Id)',
        r'To:?\s*(.*?)(?=ITEMS|Items)',
        r'Bill\s+to:?\s*(.*?)(?=ITEMS|Items)',
        r'Customer:?\s*(.*?)(?=ITEMS|Items)'
    ]
    
    for pattern in client_patterns:
        client_section = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if client_section:
            client_text = client_section.group(1).strip()
            client_lines = [line.strip() for line in client_text.split('\n') 
                          if line.strip() and not re.search(r'Tax\s+Id', line, re.IGNORECASE)]
            
            if client_lines:
                # Client name
                invoice_data['client_name'].append(client_lines[0])
                
                # Client address
                address_parts = [line for line in client_lines[1:] 
                               if not re.search(r'IBAN|Phone|Email', line, re.IGNORECASE)]
                if address_parts:
                    invoice_data['client_address'].append(', '.join(address_parts))
            break
    
    # Client Tax ID
    client_tax_patterns = [
        r'Client:.*?Tax\s+Id:?\s*([\d\-]+)',
        r'Tax\s+Id:?\s*([\d\-]+)(?=\s|$)',
    ]
    
    for pattern in client_tax_patterns:
        client_tax = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if client_tax:
            invoice_data['client_tax_id'].append(client_tax.group(1))
            break
    
    # 5. Extract Items - Enhanced for OCR variations
    items_patterns = [
        r'ITEMS(.*?)SUMMARY',
        r'Items(.*?)Summary',
        r'ITEMS(.*?)Total',
        r'Items(.*?)Total'
    ]
    
    for pattern in items_patterns:
        items_section = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if items_section:
            items_text = items_section.group(1)
            
            # Process items
            item_lines = []
            current_item = ""
            
            for line in items_text.split('\n'):
                line = line.strip()
                if not line or re.match(r'^(No\.|Description|Qty|UM|Net|VAT|Gross)', line, re.IGNORECASE):
                    continue
                if line.startswith('---'):
                    continue
                
                # New item starts with number and dot
                if re.match(r'^\d+\.', line):
                    if current_item:
                        item_lines.append(current_item.strip())
                    current_item = line
                else:
                    # Add to current item
                    current_item += " " + line
            
            # Add last item
            if current_item:
                item_lines.append(current_item.strip())
            
            # Process each item line
            for item_line in item_lines:
                # Extract numbers (price, quantity, totals)
                numbers = re.findall(r'\d+[.,]\d+|\d+%|\b\d+\b', item_line)
                if len(numbers) >= 5:
                    # Extract description
                    desc_match = re.match(r'^(\d+)\.\s+(.+?)\s+(?=\d)', item_line)
                    if desc_match:
                        description = desc_match.group(2).strip()
                        # Clean description by removing trailing numbers
                        description = re.sub(r'\s+\d+[.,]?\d*\s*$', '', description)
                        invoice_data['product_names'].append(description)
                        
                        # Parse numbers more carefully
                        try:
                            qty_idx = 0
                            for i, num in enumerate(numbers):
                                if not '%' in num and float(num.replace(',', '.')) > 0:
                                    qty_idx = i
                                    break
                            
                            if qty_idx < len(numbers):
                                invoice_data['quantities'].append(float(numbers[qty_idx].replace(',', '.')))
                                
                                # Next should be unit price
                                if qty_idx + 1 < len(numbers):
                                    invoice_data['unit_prices'].append(float(numbers[qty_idx + 1].replace(',', '.')))
                                
                                # Net worth
                                if qty_idx + 2 < len(numbers):
                                    invoice_data['net_worth'].append(float(numbers[qty_idx + 2].replace(',', '.')))
                                
                                # VAT percentage
                                vat_pct = next((num for num in numbers if '%' in num), '10%')
                                invoice_data['vat_percentage'].append(vat_pct)
                                
                                # Gross worth (last number without %)
                                gross_nums = [num for num in numbers if '%' not in num]
                                if gross_nums:
                                    invoice_data['gross_worth'].append(float(gross_nums[-1].replace(',', '.')))
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing item numbers: {e}")
                            continue
            break
    
    # 6. Total
    total_patterns = [
        r'Total\s+.*?\$\s*(\d+\s*\d*[.,]?\d*)',
        r'Total:?\s*\$?\s*(\d+[.,]?\d*)',
        r'Grand\s+total:?\s*\$?\s*(\d+[.,]?\d*)',
        r'\$\s*(\d+[.,]?\d+)(?=\s*$)'
    ]
    
    for pattern in total_patterns:
        total_match = re.search(pattern, text, re.IGNORECASE)
        if total_match:
            try:
                total_value = float(total_match.group(1).replace(' ', '').replace(',', '.'))
                invoice_data['total'].append(total_value)
                break
            except ValueError:
                continue
    
    return invoice_data

def create_invoice_dataframes(data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Create structured DataFrames from extracted invoice data
    """
    
    # Invoice Header Information
    header_data = {
        'Field': ['Invoice Number', 'Date', 'Total Amount', 'Seller Name', 'Seller Address', 'Seller Tax ID', 
                  'Client Name', 'Client Address', 'Client Tax ID'],
        'Value': [
            data['invoice_number'][0] if data['invoice_number'] else None,
            data['date'][0] if data['date'] else None,
            data['total'][0] if data['total'] else None,
            data['seller_name'][0] if data['seller_name'] else None,
            data['seller_address'][0] if data['seller_address'] else None,
            data['seller_tax_id'][0] if data['seller_tax_id'] else None,
            data['client_name'][0] if data['client_name'] else None,
            data['client_address'][0] if data['client_address'] else None,
            data['client_tax_id'][0] if data['client_tax_id'] else None
        ]
    }
    
    header_df = pd.DataFrame(header_data)
    
    # Items DataFrame
    if data['product_names']:
        items_data = {
            'Item_No': list(range(1, len(data['product_names']) + 1)),
            'Product_Name': data['product_names'],
            'Quantity': data['quantities'] if data['quantities'] else [0] * len(data['product_names']),
            'Unit_Price': data['unit_prices'] if data['unit_prices'] else [0] * len(data['product_names']),
            'Net_Worth': data['net_worth'] if data['net_worth'] else [0] * len(data['product_names']),
            'VAT_Percentage': data['vat_percentage'] if data['vat_percentage'] else ['10%'] * len(data['product_names']),
            'Gross_Worth': data['gross_worth'] if data['gross_worth'] else [0] * len(data['product_names'])
        }
    else:
        items_data = {
            'Item_No': [],
            'Product_Name': [],
            'Quantity': [],
            'Unit_Price': [],
            'Net_Worth': [],
            'VAT_Percentage': [],
            'Gross_Worth': []
        }
    
    items_df = pd.DataFrame(items_data)
    
    # Summary DataFrame
    if items_df.empty or items_df['Net_Worth'].empty:
        summary_data = {
            'Metric': ['Total Net Worth', 'Total VAT', 'Total Gross Worth'],
            'Value': [0, 0, 0]
        }
    else:
        total_net = items_df['Net_Worth'].sum()
        total_gross = items_df['Gross_Worth'].sum()
        total_vat = total_gross - total_net
        
        summary_data = {
            'Metric': ['Total Net Worth', 'Total VAT', 'Total Gross Worth'],
            'Value': [total_net, total_vat, total_gross]
        }
    
    summary_df = pd.DataFrame(summary_data)
    
    return {
        'header': header_df,
        'items': items_df,
        'summary': summary_df
    }

def display_dataframes(dataframes: Dict[str, pd.DataFrame]):
    """
    Display all DataFrames in a formatted way
    """
    print("\nINVOICE HEADER INFORMATION")
    print("=" * 50)
    print(dataframes['header'].to_string(index=False))
    
    print("\n\nINVOICE ITEMS")
    print("=" * 80)
    if not dataframes['items'].empty:
        print(dataframes['items'].to_string(index=False))
    else:
        print("No items extracted")
    
    print("\n\nINVOICE SUMMARY")
    print("=" * 30)
    print(dataframes['summary'].to_string(index=False))

def save_to_excel(dataframes: Dict[str, pd.DataFrame], filename: str = 'invoice_data.xlsx'):
    """
    Save all DataFrames to Excel file with separate sheets
    """
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        dataframes['header'].to_excel(writer, sheet_name='Header', index=False)
        dataframes['items'].to_excel(writer, sheet_name='Items', index=False)
        dataframes['summary'].to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"Data saved to {filename}")

def save_to_csv(dataframes: Dict[str, pd.DataFrame], prefix: str = 'invoice'):
    """
    Save DataFrames to separate CSV files
    """
    dataframes['header'].to_csv(f'{prefix}_header.csv', index=False)
    dataframes['items'].to_csv(f'{prefix}_items.csv', index=False)
    dataframes['summary'].to_csv(f'{prefix}_summary.csv', index=False)
    
    print(f"Data saved to CSV files: {prefix}_header.csv, {prefix}_items.csv, {prefix}_summary.csv")

def process_invoice_image(image_path: str, save_excel: bool = False, save_csv: bool = False):
    """
    Complete pipeline to process invoice image
    """
    try:
        # Extract data from image
        print(f"Processing invoice image: {image_path}")
        extracted_data = extract_invoice_info_from_image(image_path)
        
        if not extracted_data:
            print("No data could be extracted from the image")
            return None
        
        # Create DataFrames
        print("Creating DataFrames...")
        dataframes = create_invoice_dataframes(extracted_data)
        
        # Display results
        display_dataframes(dataframes)
        
        # Save if requested
        if save_excel:
            invoice_num = extracted_data.get('invoice_number', ['unknown'])[0]
            save_to_excel(dataframes, f'invoice_{invoice_num}.xlsx')
        
        if save_csv:
            invoice_num = extracted_data.get('invoice_number', ['unknown'])[0]
            save_to_csv(dataframes, f'invoice_{invoice_num}')
        
        print("\n\nDataFrames created successfully!")
        print("Available DataFrames:")
        print("- dataframes['header']: Invoice header information")
        print("- dataframes['items']: Product details")
        print("- dataframes['summary']: Financial summary")
        
        return dataframes
        
    except Exception as e:
        print(f"Error processing invoice: {e}")
        return None

# Example usage:
if __name__ == "__main__":
    # Replace with your image path
    image_path = r"C:\Users\user\Desktop\final ocr\batch1-0001.jpg"  # or .jpg, .jpeg, etc.
    
    # Process the invoice image
    dataframes = process_invoice_image(
        image_path=image_path,
        save_excel=True,  # Set to True to save Excel file
        save_csv=False    # Set to True to save CSV files
    )
    
    # You can also access individual dataframes:
    if dataframes:
        header_df = dataframes['header']
        items_df = dataframes['items']
        summary_df = dataframes['summary']