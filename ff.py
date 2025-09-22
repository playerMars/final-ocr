import re
from typing import Dict, List, Any

def extract_invoice_info(text: str) -> Dict[str, Any]:
    """
    استخراج معلومات الفاتورة باستخدام Regular Expressions
    """
    
    # تنظيف النص من الأسطر الفارغة والمسافات الزائدة
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    
    invoice_data = {
        'invoice_number': [],
        'date': [],
        'total': [],
        'seller_name': [],
        'seller_address': [],
        'seller_phone': [],
        'product_names': [],
        'quantities': [],
        'unit_prices': [],
        'vat': [],
        'discount': [],
        'total_per_item': []
    }
    
    # 1. رقم الفاتورة
    invoice_number_pattern = r'Invoice\s+no[:\s]*(\d+)'
    invoice_match = re.search(invoice_number_pattern, text, re.IGNORECASE)
    if invoice_match:
        invoice_data['invoice_number'].append(invoice_match.group(1))
    
    # 2. تاريخ الفاتورة
    date_pattern = r'Date\s+of\s+issue[:\s]*(\d{2}\/\d{2}\/\d{4})'
    date_match = re.search(date_pattern, text, re.IGNORECASE)
    if date_match:
        invoice_data['date'].append(date_match.group(1))
    
    # 3. إجمالي المبلغ
    total_pattern = r'Total\s+.*?\$\s*(\d+\s*\d+[.,]\d+)'
    total_match = re.search(total_pattern, text, re.IGNORECASE | re.DOTALL)
    if total_match:
        invoice_data['total'].append(total_match.group(1).replace(' ', ''))
    
    # 4. اسم البائع
    seller_name_pattern = r'Seller[:\s]*([A-Za-z\s,]+?)(?=\d|\n|Tax)'
    seller_match = re.search(seller_name_pattern, text, re.IGNORECASE)
    if seller_match:
        invoice_data['seller_name'].append(seller_match.group(1).strip())
    
    # 5. عنوان البائع
    seller_address_pattern = r'(\d+\s+[A-Za-z\s]+(?:Lake|Street|Ave|Road|Blvd)[A-Za-z\s,]*[A-Z]{2}\s+\d+)'
    seller_address_match = re.search(seller_address_pattern, text)
    if seller_address_match:
        invoice_data['seller_address'].append(seller_address_match.group(1))
    
    # 6. هاتف البائع (Tax ID في هذه الحالة)
    phone_pattern = r'Tax\s+Id[:\s]*(\d{3}-\d{2}-\d{4})'
    phone_match = re.search(phone_pattern, text, re.IGNORECASE)
    if phone_match:
        invoice_data['seller_phone'].append(phone_match.group(1))
    
    # 7. أسماء المنتجات
    product_pattern = r'^\d+\.\s+([A-Za-z\s!]+?)(?=\s+\d+[.,]\d+\s+each|\s+each)'
    products = re.findall(product_pattern, text, re.MULTILINE)
    # تنظيف أسماء المنتجات
    cleaned_products = []
    for product in products:
        # إزالة المواصفات التقنية
        clean_product = re.sub(r'[A-Z]{2,}\s+[A-Z]{2}[-\d]+[A-Z]*.*$', '', product)
        clean_product = re.sub(r'\b(?:PC|Computer|Desktop|WINDOWS|AMD|DUAL|CORE|RAM|HD|Pro|MT|GHz|GB|TB)\b.*$', '', clean_product, flags=re.IGNORECASE)
        clean_product = clean_product.strip()
        if clean_product:
            cleaned_products.append(clean_product)
    invoice_data['product_names'] = cleaned_products
    
    # 8. الكميات
    quantity_pattern = r'^\d+\.\s+.*?\s+(\d+[.,]\d+)\s+each'
    quantities = re.findall(quantity_pattern, text, re.MULTILINE)
    invoice_data['quantities'] = quantities
    
    # 9. أسعار الوحدة
    unit_price_pattern = r'each\s+(\d+[.,]\d+)'
    unit_prices = re.findall(unit_price_pattern, text)
    invoice_data['unit_prices'] = unit_prices
    
    # 10. ضريبة القيمة المضافة
    vat_pattern = r'VAT\s+\[%\]\s+(\d+%)'
    vat_matches = re.findall(vat_pattern, text)
    if vat_matches:
        invoice_data['vat'] = list(set(vat_matches))  # إزالة التكرار
    
    # 11. الخصم (غير موجود في هذه الفاتورة)
    discount_pattern = r'[Dd]iscount[:\s]*(\d+[.,]\d+)'
    discount_matches = re.findall(discount_pattern, text)
    invoice_data['discount'] = discount_matches
    
    # 12. إجمالي لكل عنصر
    total_per_item_pattern = r'(\d+\s*\d+[.,]\d+)(?=\s*$|\s*10%)'
    total_per_item = re.findall(total_per_item_pattern, text, re.MULTILINE)
    # تنظيف وتحويل الأرقام
    cleaned_totals = []
    for total in total_per_item:
        clean_total = total.replace(' ', '')
        if re.match(r'\d+[.,]\d+$', clean_total):
            cleaned_totals.append(clean_total)
    invoice_data['total_per_item'] = cleaned_totals
    
    return invoice_data

# مثال على الاستخدام
sample_text = """
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

# تشغيل الاستخراج
result = extract_invoice_info(sample_text)

# طباعة النتائج
print("=== معلومات الفاتورة المستخرجة ===\n")
for key, value in result.items():
    if value:  # طباعة فقط الحقول التي تحتوي على بيانات
        print(f"{key}: {value}")

# دالة لعرض النتائج بشكل منظم
def display_results(data):
    print("\n=== تفاصيل مفصلة ===")
    print(f"رقم الفاتورة: {data['invoice_number'][0] if data['invoice_number'] else 'غير موجود'}")
    print(f"التاريخ: {data['date'][0] if data['date'] else 'غير موجود'}")
    print(f"اسم البائع: {data['seller_name'][0] if data['seller_name'] else 'غير موجود'}")
    print(f"عنوان البائع: {data['seller_address'][0] if data['seller_address'] else 'غير موجود'}")
    print(f"هاتف البائع: {data['seller_phone'][0] if data['seller_phone'] else 'غير موجود'}")
    print(f"المجموع الكلي: {data['total'][0] if data['total'] else 'غير موجود'}")
    print(f"ضريبة القيمة المضافة: {', '.join(data['vat']) if data['vat'] else 'غير موجود'}")
    
    print("\n=== المنتجات ===")
    for i, product in enumerate(data['product_names']):
        qty = data['quantities'][i] if i < len(data['quantities']) else 'غير محدد'
        price = data['unit_prices'][i] if i < len(data['unit_prices']) else 'غير محدد'
        total = data['total_per_item'][i] if i < len(data['total_per_item']) else 'غير محدد'
        print(f"{i+1}. {product}")
        print(f"   الكمية: {qty} | السعر: {price} | الإجمالي: {total}")

display_results(result)