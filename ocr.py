import re
import pandas as pd
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
from PIL import Image
import pytesseract
import os

def preprocess_image(image_path: str) -> np.ndarray:
    """
    تحسين جودة الصورة قبل استخراج النص
    """
    # قراءة الصورة
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"لا يمكن قراءة الصورة من المسار: {image_path}")
    
    # تحويل إلى اللون الرمادي
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # تطبيق فلتر لتقليل الضوضاء
    denoised = cv2.medianBlur(gray, 3)
    
    # تحسين التباين
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # تطبيق threshold لتحسين وضوح النص
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh

def extract_text_from_image(image_path: str) -> str:
    """
    استخراج النص من الصورة باستخدام OCR
    """
    try:
        # تحسين الصورة
        processed_image = preprocess_image(image_path)
        
        # تحويل إلى PIL Image
        pil_image = Image.fromarray(processed_image)
        
        # إعدادات OCR محسنة للفواتير
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/$%:-()\n '
        
        # استخراج النص
        text = pytesseract.image_to_string(pil_image, config=custom_config)
        
        return text.strip()
    
    except Exception as e:
        print(f"خطأ في استخراج النص من الصورة: {e}")
        return ""

def extract_invoice_info_to_dataframe(text: str) -> Dict[str, Any]:
    """
    استخراج معلومات الفاتورة وتخزينها في تنسيق منظم
    """
    
    # تنظيف النص
    text = re.sub(r'\n\s*\n', '\n', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
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
    
    # 1. رقم الفاتورة - تحسين البحث
    invoice_patterns = [
        r'Invoiceno[:\s]*(\d+)',
        r'Invoice\s*no[:\s]*(\d+)',
        r'Invoice\s*Number[:\s]*(\d+)'
    ]
    for pattern in invoice_patterns:
        invoice_match = re.search(pattern, text, re.IGNORECASE)
        if invoice_match:
            invoice_data['invoice_number'].append(invoice_match.group(1))
            break
    
    # 2. التاريخ - تحسين البحث
    date_patterns = [
        r'Dateofissue[:\s]*(\d{2}/\d{2}/\d{4})',
        r'Date\s*of\s*issue[:\s]*(\d{2}/\d{2}/\d{4})',
        r'Date[:\s]*(\d{2}/\d{2}/\d{4})'
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            invoice_data['date'].append(date_match.group(1))
            break
    
    # 3. معلومات البائع والعميل - تحسين الاستخراج
    # البحث عن معلومات البائع والعميل في نفس السطر أو أسطر متتالية
    seller_client_pattern = r'Seller:\s*Client:\s*(.+?)(?=TaxId:|IBAN:|ITEMS)'
    seller_client_match = re.search(seller_client_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if seller_client_match:
        seller_client_text = seller_client_match.group(1).strip()
        # تقسيم النص إلى كلمات وتجميع المعلومات
        words = seller_client_text.split()
        
        # البحث عن أسماء الشركات (عادة تحتوي على حروف كبيرة متتالية)
        company_names = []
        addresses = []
        
        current_name = []
        current_address = []
        
        for word in words:
            # إذا كان الكلمة تحتوي على حروف وأرقام وفاصلات (عنوان)
            if re.match(r'.*\d+.*', word) and (',' in word or len(word) > 10):
                if current_name:
                    company_names.append(' '.join(current_name))
                    current_name = []
                current_address.append(word)
            # إذا كانت كلمة تبدأ بحرف كبير (اسم شركة)
            elif word[0].isupper() and not re.match(r'.*\d+.*', word):
                if current_address:
                    addresses.append(' '.join(current_address))
                    current_address = []
                current_name.append(word)
            else:
                if current_name:
                    current_name.append(word)
                elif current_address:
                    current_address.append(word)
        
        # إضافة آخر اسم وعنوان
        if current_name:
            company_names.append(' '.join(current_name))
        if current_address:
            addresses.append(' '.join(current_address))
        
        # تخصيص الأسماء للبائع والعميل
        if len(company_names) >= 2:
            invoice_data['seller_name'].append(company_names[0])
            invoice_data['client_name'].append(company_names[1])
        elif len(company_names) == 1:
            invoice_data['seller_name'].append(company_names[0])
        
        # تخصيص العناوين
        if len(addresses) >= 2:
            invoice_data['seller_address'].append(addresses[0])
            invoice_data['client_address'].append(addresses[1])
        elif len(addresses) == 1:
            invoice_data['seller_address'].append(addresses[0])
    
    # استخراج Tax IDs
    tax_ids = re.findall(r'TaxId[:\s]*(\d{3}-\d{2}-\d{4})', text, re.IGNORECASE)
    if len(tax_ids) >= 2:
        invoice_data['seller_tax_id'].append(tax_ids[0])
        invoice_data['client_tax_id'].append(tax_ids[1])
    elif len(tax_ids) == 1:
        invoice_data['seller_tax_id'].append(tax_ids[0])
    
    # 5. استخراج المواد - تحسين كبير
    items_section = re.search(r'ITEMS(.*?)SUMMARY', text, re.DOTALL)
    if items_section:
        items_text = items_section.group(1)
        
        # تنظيف النص وتقسيمه إلى أسطر
        item_lines = []
        lines = items_text.split('\n')
        current_item = ""
        
        for line in lines:
            line = line.strip()
            if not line or 'No.' in line or 'Description' in line or line.startswith('---') or line == 'worth':
                continue
            
            # إذا بدأ السطر برقم ونقطة، فهو مادة جديدة
            if re.match(r'^\d+\s', line):
                if current_item:
                    item_lines.append(current_item.strip())
                current_item = line
            else:
                # إضافة للمادة الحالية
                current_item += " " + line
        
        # إضافة المادة الأخيرة
        if current_item:
            item_lines.append(current_item.strip())
        
        # معالجة كل مادة
        for item_line in item_lines:
            # البحث عن الأرقام في السطر
            # نمط للبحث عن: رقم المادة، الكمية، السعر، القيمة الصافية، VAT، القيمة الإجمالية
            numbers = re.findall(r'\d+[,.]?\d*', item_line)
            
            if len(numbers) >= 6:  # على الأقل 6 أرقام (رقم المادة، كمية، سعر، صافي، vat، إجمالي)
                # استخراج الوصف (النص بين رقم المادة والكمية)
                desc_match = re.search(r'^\d+\s+(.+?)\s+\d+[,.]?\d*\s+each', item_line)
                if not desc_match:
                    # محاولة أخرى للعثور على الوصف
                    desc_match = re.search(r'^\d+\s+(.+?)\s+(?=\d+[,.]?\d*)', item_line)
                
                if desc_match:
                    description = desc_match.group(1).strip()
                    # تنظيف الوصف من الكلمات الزائدة
                    description = re.sub(r'\s+', ' ', description)
                    
                    invoice_data['product_names'].append(description)
                    
                    # استخراج الأرقام بالترتيب
                    try:
                        # تخطي رقم المادة والبحث عن الكمية والأسعار
                        qty_idx = 1  # الكمية عادة الرقم الثاني
                        price_idx = 2  # السعر الثالث
                        net_idx = 3   # القيمة الصافية الرابعة
                        gross_idx = -1  # القيمة الإجمالية آخر رقم
                        
                        invoice_data['quantities'].append(float(numbers[qty_idx].replace(',', '.')))
                        invoice_data['unit_prices'].append(float(numbers[price_idx].replace(',', '.')))
                        invoice_data['net_worth'].append(float(numbers[net_idx].replace(',', '.')))
                        
                        # البحث عن نسبة VAT
                        vat_match = re.search(r'(\d+)%', item_line)
                        vat_pct = vat_match.group(1) + '%' if vat_match else '10%'
                        invoice_data['vat_percentage'].append(vat_pct)
                        
                        # القيمة الإجمالية
                        invoice_data['gross_worth'].append(float(numbers[gross_idx].replace(',', '.')))
                    except (ValueError, IndexError) as e:
                        print(f"خطأ في معالجة المادة: {item_line}")
                        continue
    
    # 6. المجموع - تحسين البحث
    total_patterns = [
        r'Total\s+\$\s*(\d+[,.]?\d*)',
        r'Total\s+.*?\$\s*(\d+[,.]?\d*)',
        r'Total.*?(\d+[,.]?\d*)'
    ]
    
    for pattern in total_patterns:
        total_match = re.search(pattern, text)
        if total_match:
            try:
                total_value = float(total_match.group(1).replace(',', '.'))
                invoice_data['total'].append(total_value)
                break
            except ValueError:
                continue
    
    return invoice_data

def create_invoice_dataframes(data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    إنشاء DataFrames منظمة من بيانات الفاتورة المستخرجة
    """
    
    # معلومات رأس الفاتورة
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
    
    # DataFrame للمواد
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
    
    # DataFrame للملخص
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
    عرض جميع DataFrames بتنسيق مرتب
    """
    print("\n" + "="*60)
    print("معلومات رأس الفاتورة")
    print("="*60)
    print(dataframes['header'].to_string(index=False))
    
    print("\n" + "="*80)
    print("مواد الفاتورة")
    print("="*80)
    if not dataframes['items'].empty:
        print(dataframes['items'].to_string(index=False))
    else:
        print("لا توجد مواد مستخرجة")
    
    print("\n" + "="*40)
    print("ملخص الفاتورة")
    print("="*40)
    print(dataframes['summary'].to_string(index=False))

def save_to_excel(dataframes: Dict[str, pd.DataFrame], filename: str = 'invoice_data.xlsx'):
    """
    حفظ جميع DataFrames في ملف Excel مع صفحات منفصلة
    """
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        dataframes['header'].to_excel(writer, sheet_name='Header', index=False)
        dataframes['items'].to_excel(writer, sheet_name='Items', index=False)
        dataframes['summary'].to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"تم حفظ البيانات في {filename}")

def save_to_csv(dataframes: Dict[str, pd.DataFrame], prefix: str = 'invoice'):
    """
    حفظ DataFrames في ملفات CSV منفصلة
    """
    dataframes['header'].to_csv(f'{prefix}_header.csv', index=False)
    dataframes['items'].to_csv(f'{prefix}_items.csv', index=False)
    dataframes['summary'].to_csv(f'{prefix}_summary.csv', index=False)
    
    print(f"تم حفظ البيانات في ملفات CSV: {prefix}_header.csv, {prefix}_items.csv, {prefix}_summary.csv")

def process_invoice_from_image(image_path: str):
    """
    الوظيفة الرئيسية لمعالجة الفاتورة من الصورة
    """
    if not os.path.exists(image_path):
        print(f"الملف غير موجود: {image_path}")
        return None
    
    print("استخراج النص من الصورة...")
    invoice_text = extract_text_from_image(image_path)
    
    if not invoice_text:
        print("فشل في استخراج النص من الصورة")
        return None
    
    print("النص المستخرج:")
    print("-" * 50)
    print(invoice_text)
    print("-" * 50)
    
    print("\nاستخراج بيانات الفاتورة...")
    extracted_data = extract_invoice_info_to_dataframe(invoice_text)
    
    print("إنشاء DataFrames...")
    dataframes = create_invoice_dataframes(extracted_data)
    
    # عرض النتائج
    display_dataframes(dataframes)
    
    return {
        'invoice_text': invoice_text,
        'extracted_data': extracted_data,
        'dataframes': dataframes
    }

# مثال للاستخدام
if __name__ == "__main__":
    # يمكنك أيضاً اختبار البرنامج مع النص المعطى مباشرة
    test_text = """Invoiceno:51109338
Dateofissue: 04/13/2013
Seller: Client:
Andrews,KirbyandValdez BeckerLtd
58861GonzalezPrairie 8012StewartSummitApt.455
LakeDaniellefurt,IN57228 NorthDouglas,AZ95355
TaxId:945-82-2137 TaxId:942-80-0517
IBAN:GB75MCRL06841367619257
ITEMS
No. Description Qty UM Netprice Networth VAT(%) Gross
worth
1 CLEARANCEFastDellDesktop 3,00 each 209,00 627,00 10% 689,70
ComputerPCDUALCORE
WINDOWS104/8/16GBRAM
2 HPT520ThinClientComputer 5,00 each 37,75 188,75 10% 207,63
AMDGX-212JC1.2GHz4GBRAM
TESTEDREADBELOW
3 gamingpcdesktopcomputer 1,00 each 400,00 400,00 10% 440,00
4 12-CoreGamingComputer 3,00 each 464,89 1394,67 10% 1534,14
DesktopPCTowerAffordable
GAMINGPC8GBAMDVegaRGB
5 CustomBuildDellOptiplex9020 5,00 each 221,99 1109,95 10% 1220,95
MTi5-45703.20GHzDesktop
ComputerPC
6 DellOptiplex990MTComputer 4,00 each 269,95 1079,80 10% 1187,78
PCQuadCorei73.4GHz16GB
2TBHDWindows10Pro
7 DellCore2DuoDesktop 5,00 each 168,00 840,00 10% 924,00
ComputerWindowsXPPro
4GB500GB
SUMMARY
VAT(%) Networth VAT Grossworth
10% 5640,17 564,02 6204,19
Total $5640,17 $564,02 $6204,19"""

    print("اختبار البرنامج مع النص المعطى:")
    print("-" * 60)
    
    # استخراج البيانات
    extracted_data = extract_invoice_info_to_dataframe(test_text)
    
    # إنشاء DataFrames
    dataframes = create_invoice_dataframes(extracted_data)
    
    # عرض النتائج
    display_dataframes(dataframes)
    
    # اختبار مع صورة (اختياري)
    print("\n" + "="*60)
    print("لاختبار البرنامج مع صورة، ضع مسار الصورة هنا:")
    image_path = r"C:\Users\user\Desktop\final ocr\batch1-0001.jpg"  
    
    # معالجة الفاتورة من صورة (إذا كان المسار موجود)
    if os.path.exists(image_path):
        result = process_invoice_from_image(image_path)
        
        if result:
            print(f"\n\nنتائج معالجة الصورة من {image_path}:")
            display_dataframes(result['dataframes'])
    else:
        print(f"الصورة غير موجودة في المسار: {image_path}")
        print("للاختبار مع صورة، ضع مسار صورة الفاتورة في متغير image_path")
    
    print("\n\nتم إكمال الاختبار!")