import re
import pandas as pd
from typing import Dict, List, Any, Optional

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
    invoice_match = re.search(r'Invoice\s+no:\s*(\d+)', text, re.IGNORECASE)
    if invoice_match:
        invoice_data['invoice_number'].append(invoice_match.group(1))
    
    # 2. Date
    date_match = re.search(r'Date\s+of\s+issue:\s*(\d{2}/\d{2}/\d{4})', text)
    if date_match:
        invoice_data['date'].append(date_match.group(1))
    
    # 3. Seller Information
    seller_section = re.search(r'Seller:(.*?)(?=Client:|ITEMS)', text, re.DOTALL | re.IGNORECASE)
    if seller_section:
        seller_text = seller_section.group(1).strip()
        seller_lines = [line.strip() for line in seller_text.split('\n') if line.strip()]
        
        if seller_lines:
            # Seller name (first line)
            invoice_data['seller_name'].append(seller_lines[0])
            
            # Address
            for line in seller_lines[1:]:
                if re.match(r'\d+.*[A-Z]{2}\s+\d+', line):
                    invoice_data['seller_address'].append(line)
                elif 'Tax Id:' in line:
                    tax_id = re.search(r'Tax\s+Id:\s*([\d\-]+)', line)
                    if tax_id:
                        invoice_data['seller_tax_id'].append(tax_id.group(1))
    
    # 4. Client Information
    client_section = re.search(r'Client:(.*?)(?=ITEMS|Tax Id)', text, re.DOTALL)
    if client_section:
        client_text = client_section.group(1).strip()
        client_lines = [line.strip() for line in client_text.split('\n') if line.strip() and 'Tax Id:' not in line]
        
        if client_lines:
            # Client name
            invoice_data['client_name'].append(client_lines[0])
            
            # Client address
            for line in client_lines[1:]:
                if re.match(r'.*[A-Z]{2}\s+\d+', line):
                    invoice_data['client_address'].append(line)
    
    # Client Tax ID
    client_tax = re.search(r'Client:.*?Tax\s+Id:\s*([\d\-]+)', text, re.DOTALL)
    if client_tax:
        invoice_data['client_tax_id'].append(client_tax.group(1))
    
    # 5. Extract Items
    items_section = re.search(r'ITEMS(.*?)SUMMARY', text, re.DOTALL)
    if items_section:
        items_text = items_section.group(1)
        
        item_lines = []
        current_item = ""
        
        for line in items_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('No.') or line.startswith('---'):
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
            # Extract numbers from the end
            numbers = re.findall(r'\d+[.,]\d+|\d+%', item_line)
            if len(numbers) >= 5:
                # Extract description (everything before numbers)
                desc_match = re.match(r'^(\d+)\.\s+(.+?)\s+(?=\d+[.,]\d+\s+each)', item_line)
                if desc_match:
                    description = desc_match.group(2).strip()
                    invoice_data['product_names'].append(description)
                    
                    # Extract numbers in order
                    invoice_data['quantities'].append(float(numbers[0].replace(',', '.')))
                    invoice_data['unit_prices'].append(float(numbers[1].replace(',', '.')))
                    invoice_data['net_worth'].append(float(numbers[2].replace(',', '.')))
                    
                    # VAT percentage
                    vat_pct = next((num for num in numbers if '%' in num), '10%')
                    invoice_data['vat_percentage'].append(vat_pct)
                    
                    # Gross worth (last number)
                    invoice_data['gross_worth'].append(float(numbers[-1].replace(',', '.')))
    
    # 6. Total
    summary_section = re.search(r'SUMMARY(.*?)$', text, re.DOTALL)
    if summary_section:
        summary_text = summary_section.group(1)
        total_match = re.search(r'Total\s+.*?\$\s*(\d+\s*\d+[.,]\d+)', summary_text)
        if total_match:
            total_value = float(total_match.group(1).replace(' ', '').replace(',', '.'))
            invoice_data['total'].append(total_value)
    
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
    items_data = {
        'Item_No': list(range(1, len(data['product_names']) + 1)),
        'Product_Name': data['product_names'],
        'Quantity': data['quantities'],
        'Unit_Price': data['unit_prices'],
        'Net_Worth': data['net_worth'],
        'VAT_Percentage': data['vat_percentage'],
        'Gross_Worth': data['gross_worth']
    }
    
    items_df = pd.DataFrame(items_data)
    
    # Summary DataFrame
    if items_df.empty:
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
    print("INVOICE HEADER INFORMATION")
    print("=" * 50)
    print(dataframes['header'].to_string(index=False))
    
    print("\n\nINVOICE ITEMS")
    print("=" * 80)
    print(dataframes['items'].to_string(index=False))
    
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

# Invoice text from the image
invoice_text = """
Invoice no: 51109338

Date of issue: 04/13/2013

Seller:                                    Client:
Andrews, Kirby and Valdez                  Becker Ltd
58861 Gonzalez Prairie                     8012 Stewart Summit Apt. 455
Lake Daniellefurt, IN 57228               North Douglas, AZ 95355

Tax Id: 945-82-2137                       Tax Id: 942-80-0517
IBAN: GB75MCRL06841367619257

ITEMS

No.    Description                         Qty    UM     Net price    Net worth    VAT [%]    Gross worth

1.     CLEARANCE! Fast Dell Desktop        3.00   each   209.00       627.00       10%        689.70
       Computer PC DUAL CORE
       WINDOWS 10 4/8/16GB RAM

2.     HP T520 Thin Client Computer        5.00   each   37.75        188.75       10%        207.63
       AMD GX-212JC 1.2GHz 4GB RAM
       TESTED !IREAD BELOW!!

3.     gaming pc desktop computer          1.00   each   400.00       400.00       10%        440.00

4.     12-Core Gaming Computer             3.00   each   464.89       1394.67      10%        1534.14
       Desktop PC Tower Affordable
       GAMING PC 8GB AMD Vega RGB

5.     Custom Build Dell Optiplex 9020    5.00   each   221.99       1109.95      10%        1220.95
       MT i5-4570 3.20GHz Desktop
       Computer PC

6.     Dell Optiplex 990 MT Computer       4.00   each   269.95       1079.80      10%        1187.78
       PC Quad Core i7 3.4GHz 16GB
       2TB HD Windows 10 Pro

7.     Dell Core 2 Duo Desktop            5.00   each   168.00       840.00       10%        924.00
       Computer | Windows XP Pro |
       4GB | 500GB

SUMMARY

                                          VAT [%]    Net worth    VAT      Gross worth
                                          10%        5640.17      564.02   6204.19

Total                                               $ 5640.17    $ 564.02  $ 6204.19
"""

# Extract data and create DataFrames
print("Extracting invoice data...")
extracted_data = extract_invoice_info_to_dataframe(invoice_text)

print("Creating DataFrames...")
dataframes = create_invoice_dataframes(extracted_data)

# Display results
display_dataframes(dataframes)

# Uncomment to save data
# save_to_excel(dataframes, 'invoice_51109338.xlsx')
# save_to_csv(dataframes, 'invoice_51109338')

print("\n\nDataFrames created successfully!")
print("Available DataFrames:")
print("- dataframes['header']: Invoice header information")
print("- dataframes['items']: Product details")
print("- dataframes['summary']: Financial summary")