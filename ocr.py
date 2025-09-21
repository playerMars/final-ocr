#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
كود OCR بسيط وجاهز للاستخدام
يدعم العربية والإنجليزية
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import sys
import re
import json
from datetime import datetime

def enhance_image(image):
    """تحسين جودة الصورة لـ OCR أفضل"""
    try:
        # تحويل إلى رمادي
        if image.mode != 'L':
            image = image.convert('L')
        
        # تحسين التباين
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # تحسين الحدة
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        # فلتر لتقليل التشويش
        image = image.filter(ImageFilter.MedianFilter())
        
        return image
    except Exception as e:
        print(f"تحذير: لا يمكن تحسين الصورة - {e}")
        return image

def extract_text_from_image(image_path, lang='ara+eng', enhance=True):
    """
    استخراج النص من صورة
    
    Args:
        image_path: مسار الصورة
        lang: اللغة (ara للعربية، eng للإنجليزية، ara+eng للاثنين)
        enhance: تحسين الصورة قبل المعالجة
    
    Returns:
        النص المستخرج
    """
    try:
        # التحقق من وجود الملف
        if not os.path.exists(image_path):
            return f"❌ الملف غير موجود: {image_path}"
        
        # فتح الصورة
        print(f"📖 جاري قراءة الصورة: {image_path}")
        image = Image.open(image_path)
        
        # تحسين الصورة (اختياري)
        if enhance:
            print("🔧 جاري تحسين جودة الصورة...")
            image = enhance_image(image)
        
        # استخراج النص
        print(f"🔍 جاري استخراج النص باللغة: {lang}")
        
        # إعدادات محسنة لـ tesseract
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzأبتثجحخدذرزسشصضطظعغفقكلمنهويء '
        
        # استخراج النص
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        
        # تنظيف النص
        text = text.strip()
        
        if not text:
            return "⚠️ لم يتم العثور على نص في الصورة"
        
        return text
        
    except Exception as e:
        return f"❌ خطأ في استخراج النص: {str(e)}"

def save_text_to_file(text, output_file='extracted_text.txt'):
    """حفظ النص في ملف"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✅ تم حفظ النص في: {output_file}")
        return True
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")
        return False

def extract_invoice_data(text):
    """
    استخراج بيانات الفاتورة المحددة مع التعامل مع الأسماء المختلفة
    """
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
    
    # أنماط رقم الفاتورة - متعددة اللغات والصيغ
    invoice_patterns = [
        # العربية
        r'(?:رقم\s*الفاتورة|فاتورة\s*رقم|رقم\s*الفاتورة|فاتورة)\s*[:#]?\s*([A-Z0-9\-/]+)',
        r'(?:Invoice\s*No|Invoice\s*Number|Invoice\s*#|Bill\s*No)\s*[:#]?\s*([A-Z0-9\-/]+)',
        r'(?:INV|INVOICE|Bill)\s*[:#\-]?\s*([A-Z0-9\-/]+)',
        r'(?:رقم|#)\s*([A-Z0-9\-/]{3,})',
    ]
    
    # أنماط التاريخ - صيغ متنوعة
    date_patterns = [
        # التواريخ العربية والإنجليزية
        r'(?:تاريخ\s*الفاتورة|تاريخ|Date|Invoice\s*Date)\s*[:#]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(?:تاريخ\s*الفاتورة|تاريخ|Date|Invoice\s*Date)\s*[:#]?\s*(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
        r'(?:تاريخ\s*الفاتورة|تاريخ|Date)\s*[:#]?\s*(\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{4})',
        r'(?:Date|Invoice\s*Date)\s*[:#]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',  # تاريخ منفرد
        r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',   # تاريخ ISO
    ]
    
    # أنماط الإجمالي
    total_patterns = [
        r'(?:الإجمالي|المجموع|Total|Grand\s*Total|Final\s*Total)\s*[:#]?\s*([\d,]+\.?\d*)\s*(?:ريال|درهم|دينار|جنيه|SR|AED|USD|\$)?',
        r'(?:الإجمالي|Total)\s*[:#]?\s*(?:ريال|درهم|SR|AED|USD|\$)?\s*([\d,]+\.?\d*)',
        r'(?:المبلغ\s*الكلي|المبلغ\s*الإجمالي)\s*[:#]?\s*([\d,]+\.?\d*)',
        r'(?:Amount\s*Due|Total\s*Amount)\s*[:#]?\s*(?:\$|SR|AED)?\s*([\d,]+\.?\d*)',
    ]
    
    # أنماط اسم البائع/الشركة
    seller_name_patterns = [
        r'(?:اسم\s*الشركة|الشركة|اسم\s*البائع|Company\s*Name|Seller|Vendor)\s*[:#]?\s*([^\n\r]+?)(?:\n|$)',
        r'(?:مؤسسة|شركة|مكتب)\s+([^\n\r]+?)(?:\n|$)',
        r'(?:Company|Corporation|LLC|Ltd|Inc)\s*:?\s*([^\n\r]+?)(?:\n|$)',
        r'^([^\n\r]+?(?:مؤسسة|شركة|Company|Corp|LLC|Ltd))',
    ]
    
    # أنماط عنوان البائع
    seller_address_patterns = [
        r'(?:العنوان|عنوان|Address)\s*[:#]?\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=(?:هاتف|رقم\s*الهاتف|الهاتف|Phone|Tel)|$)',
        r'(?:ص\.ب|P\.O\.\s*Box|صندوق\s*بريد)\s*[:#]?\s*([^\n\r]+)',
        r'(?:المدينة|City)\s*[:#]?\s*([^\n\r]+)',
        r'(?:الرمز\s*البريدي|Postal\s*Code|ZIP)\s*[:#]?\s*([^\n\r]+)',
    ]
    
    # أنماط رقم هاتف البائع
    seller_phone_patterns = [
        r'(?:هاتف|رقم\s*الهاتف|الهاتف|Phone|Tel|Mobile)\s*[:#]?\s*(\+?\d{1,4}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4})',
        r'(\+966\s*\d{2}\s*\d{3}\s*\d{4})',  # سعودي
        r'(\+971\s*\d{2}\s*\d{3}\s*\d{4})',  # إماراتي  
        r'(\+962\s*\d{1}\s*\d{3}\s*\d{4})',  # أردني
        r'(\+20\s*\d{2}\s*\d{3}\s*\d{4})',   # مصري
        r'(\d{4}\s*\d{3}\s*\d{3})',          # محلي
    ]
    
    # أنماط أسماء المنتجات
    product_patterns = [
        r'(?:المنتج|السلعة|الصنف|Product|Item|Description)\s*[:#]?\s*([^\n\r\t]+?)(?=(?:الكمية|Qty|Quantity|السعر|Price)|\d+|\n|$)',
        # نمط للجداول - البحث عن صفوف المنتجات
        r'^(?:\d+[.\)]?\s+)?([^0-9\n\r]{3,50})\s+(?:\d+)\s+(?:[\d,]+\.?\d*)',  # نمط جدول بسيط
    ]
    
    # أنماط الكمية
    quantity_patterns = [
        r'(?:الكمية|عدد|Qty|Quantity)\s*[:#]?\s*(\d+)',
        r'(?:x|\*)\s*(\d+)',  # نمط الضرب
        r'(\d+)\s*(?:قطعة|وحدة|pcs|units?)',
        # في الجداول
        r'(?:^|\t|\s{2,})(\d+)(?:\s|$)',  # رقم منفرد في بداية أو بعد مسافات
    ]
    
    # أنماط سعر الوحدة
    unit_price_patterns = [
        r'(?:سعر\s*الوحدة|السعر|Unit\s*Price|Price)\s*[:#]?\s*([\d,]+\.?\d*)',
        r'(?:@|each)\s*([\d,]+\.?\d*)',
        # في الجداول
        r'(?:ريال|SR|AED|USD|\$)\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:ريال|SR|AED|USD)',
    ]
    
    # أنماط الضريبة VAT
    vat_patterns = [
        r'(?:ضريبة\s*القيمة\s*المضافة|الضريبة|VAT|Tax)\s*[:#]?\s*(%?\s*[\d,]+\.?\d*%?)',
        r'(?:VAT|Tax)\s*(?:@|Rate)?\s*(\d+(?:\.\d+)?%)',
        r'(\d+(?:\.\d+)?%)\s*(?:ضريبة|VAT|Tax)',
        r'(?:ضريبة|Tax)\s*[:#]?\s*([\d,]+\.?\d*)',
    ]
    
    # أنماط الخصم
    discount_patterns = [
        r'(?:خصم|تخفيض|Discount)\s*[:#]?\s*(%?\s*[\d,]+\.?\d*%?)',
        r'(?:Discount|Off)\s*[:#]?\s*(\d+(?:\.\d+)?%)',
        r'(\d+(?:\.\d+)?%)\s*(?:خصم|Discount)',
        r'(?:خصم|Discount)\s*[:#]?\s*([\d,]+\.?\d*)',
        r'(?:\-|\()\s*([\d,]+\.?\d*)\s*(?:\)|$)',  # مبالغ بعلامة سالبة
    ]
    
    # أنماط الإجمالي لكل صنف
    total_per_item_patterns = [
        r'(?:المجموع|الإجمالي|Total|Amount)\s*[:#]?\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:ريال|SR|AED|USD)(?:\s|$)',
        # في نهاية صف الجدول
        r'(?:^|\s)([\d,]+\.?\d*)(?:\s*$|\n)',
    ]
    
    # تطبيق الأنماط
    patterns_map = {
        'invoice_number': invoice_patterns,
        'date': date_patterns, 
        'total': total_patterns,
        'seller_name': seller_name_patterns,
        'seller_address': seller_address_patterns,
        'seller_phone': seller_phone_patterns,
        'product_names': product_patterns,
        'quantities': quantity_patterns,
        'unit_prices': unit_price_patterns,
        'vat': vat_patterns,
        'discount': discount_patterns,
        'total_per_item': total_per_item_patterns
    }
    
    # استخراج البيانات لكل فئة
    for field, patterns in patterns_map.items():
        all_matches = []
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # تنظيف النتائج
                    cleaned_matches = []
                    for match in matches:
                        if isinstance(match, tuple):
                            match = next((m for m in match if m), match[0])
                        
                        cleaned = str(match).strip()
                        if len(cleaned) > 0:
                            cleaned_matches.append(cleaned)
                    
                    all_matches.extend(cleaned_matches)
            except re.error:
                continue
        
        # إزالة التكرارات والفلترة
        unique_matches = []
        seen = set()
        for match in all_matches:
            if match not in seen:
                seen.add(match)
                # فلترة إضافية حسب النوع
                if field in ['quantities', 'unit_prices', 'vat', 'discount', 'total_per_item', 'total']:
                    # التأكد من وجود أرقام
                    if re.search(r'\d', match):
                        unique_matches.append(match)
                elif field in ['seller_phone']:
                    # التأكد من صحة رقم الهاتف
                    if len(re.sub(r'\D', '', match)) >= 7:
                        unique_matches.append(match)
                else:
                    if len(match.strip()) >= 2:
                        unique_matches.append(match)
        
        invoice_data[field] = unique_matches
    
    return invoice_data

def parse_invoice_table(text):
    """
    استخراج بيانات الجدول من الفاتورة (المنتجات والأسعار)
    """
    table_data = []
    
    # تقسيم النص إلى أسطر
    lines = text.split('\n')
    
    # البحث عن أسطر تحتوي على بيانات منتجات
    # نمط: اسم_منتج + كمية + سعر + إجمالي
    table_pattern = r'^(.+?)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)(?:\s+([\d,]+\.?\d*))?'
    
    current_products = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # البحث عن صفوف الجدول
        match = re.match(table_pattern, line)
        if match:
            product_data = {
                'product_name': match.group(1).strip(),
                'quantity': match.group(2).strip(),
                'unit_price': match.group(3).strip(),
                'total_price': match.group(4).strip(),
                'vat_amount': match.group(5).strip() if match.group(5) else ''
            }
            current_products.append(product_data)
        else:
            # محاولة أخرى بنمط مختلف - الفصل بالمسافات المتعددة
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                # محاولة تحديد الأعمدة
                numbers = []
                text_parts = []
                
                for part in parts:
                    part = part.strip()
                    # التحقق من كون الجزء رقم (مع دعم الفواصل والنقاط العشرية)
                    if re.match(r'^[\d,]+\.?\d*$', part) and part:
                        numbers.append(part)
                    elif part and not part.isspace():
                        text_parts.append(part)
                
                if len(numbers) >= 2 and len(text_parts) >= 1:
                    product_data = {
                        'product_name': ' '.join(text_parts),
                        'quantity': numbers[0] if len(numbers) > 0 else '',
                        'unit_price': numbers[1] if len(numbers) > 1 else '',
                        'total_price': numbers[2] if len(numbers) > 2 else '',
                        'vat_amount': numbers[3] if len(numbers) > 3 else ''
                    }
                    current_products.append(product_data)
    
    return current_products

def validate_invoice_data(invoice_data):
    """
    التحقق من صحة بيانات الفاتورة وتنظيفها
    """
    validated = {}
    
    for field, values in invoice_data.items():
        if not values:
            validated[field] = []
            continue
        
        if field == 'invoice_number':
            # أخذ أول رقم فاتورة صحيح
            for val in values:
                if len(val) >= 3 and any(c.isalnum() for c in val):
                    validated[field] = [val]
                    break
            else:
                validated[field] = values[:1]  # أول قيمة
        
        elif field == 'date':
            # البحث عن أول تاريخ صحيح
            for val in values:
                if re.search(r'\d{1,4}[/\-]\d{1,2}[/\-]\d{1,4}', val):
                    validated[field] = [val]
                    break
            else:
                validated[field] = values[:1]
        
        elif field == 'total':
            # البحث عن أكبر مبلغ (عادة يكون الإجمالي)
            numeric_totals = []
            for val in values:
                num = re.sub(r'[^\d.]', '', val)
                if num and '.' in num:
                    try:
                        numeric_totals.append((float(num), val))
                    except:
                        pass
                elif num:
                    try:
                        numeric_totals.append((float(num), val))
                    except:
                        pass
            
            if numeric_totals:
                # ترتيب حسب القيمة وأخذ الأكبر
                numeric_totals.sort(key=lambda x: x[0], reverse=True)
                validated[field] = [numeric_totals[0][1]]
            else:
                validated[field] = values[:1]
        
        elif field in ['seller_name', 'seller_address']:
            # أخذ أول قيمة غير فارغة ومعقولة
            for val in values:
                if len(val.strip()) >= 3:
                    validated[field] = [val.strip()]
                    break
            else:
                validated[field] = []
        
        elif field == 'seller_phone':
            # أخذ أول رقم هاتف صحيح
            for val in values:
                cleaned_phone = re.sub(r'\D', '', val)
                if len(cleaned_phone) >= 7:
                    validated[field] = [val]
                    break
            else:
                validated[field] = []
        
        else:
            # للمنتجات والكميات والأسعار، الاحتفاظ بجميع القيم
            validated[field] = values
    
    return validated

def format_invoice_report(invoice_data, table_data=None, format_type='text'):
    """
    تنسيق تقرير الفاتورة للعرض
    """
    if format_type == 'json':
        report = {
            'invoice_info': invoice_data,
            'table_data': table_data or []
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    elif format_type == 'text':
        report = []
        report.append("=" * 60)
        report.append("🧾 تقرير تحليل الفاتورة")
        report.append("=" * 60)
        
        # معلومات الفاتورة الأساسية
        report.append("\n📋 معلومات الفاتورة:")
        report.append("-" * 30)
        
        field_names = {
            'invoice_number': '🔢 رقم الفاتورة',
            'date': '📅 التاريخ', 
            'total': '💰 الإجمالي',
            'seller_name': '🏢 اسم البائع',
            'seller_address': '📍 عنوان البائع',
            'seller_phone': '📞 هاتف البائع',
            'vat': '📊 الضريبة',
            'discount': '🎯 الخصم'
        }
        
        for field, display_name in field_names.items():
            values = invoice_data.get(field, [])
            if values:
                report.append(f"{display_name}: {values[0]}")
        
        # بيانات المنتجات
        if any([invoice_data.get('product_names'), 
                invoice_data.get('quantities'), 
                invoice_data.get('unit_prices')]):
            
            report.append("\n🛍️ بيانات المنتجات:")
            report.append("-" * 30)
            
            products = invoice_data.get('product_names', [])
            quantities = invoice_data.get('quantities', [])
            unit_prices = invoice_data.get('unit_prices', [])
            totals = invoice_data.get('total_per_item', [])
            
            max_items = max(len(products), len(quantities), len(unit_prices))
            
            for i in range(max_items):
                product = products[i] if i < len(products) else 'غير محدد'
                qty = quantities[i] if i < len(quantities) else 'غير محدد'
                price = unit_prices[i] if i < len(unit_prices) else 'غير محدد'
                total = totals[i] if i < len(totals) else 'غير محدد'
                
                report.append(f"{i+1}. المنتج: {product}")
                report.append(f"   الكمية: {qty} | السعر: {price} | الإجمالي: {total}")
        
        # بيانات الجدول المستخرجة
        if table_data:
            report.append(f"\n📊 جدول المنتجات المستخرج ({len(table_data)} صنف):")
            report.append("-" * 30)
            
            for i, item in enumerate(table_data, 1):
                report.append(f"{i}. {item.get('product_name', 'غير محدد')}")
                report.append(f"   الكمية: {item.get('quantity', 'N/A')}")
                report.append(f"   سعر الوحدة: {item.get('unit_price', 'N/A')}")
                report.append(f"   الإجمالي: {item.get('total_price', 'N/A')}")
                if item.get('vat_amount'):
                    report.append(f"   الضريبة: {item.get('vat_amount')}")
        
        return '\n'.join(report)
    
    return str(invoice_data)

def get_text_stats(text):
    """إحصائيات النص"""
    lines = text.split('\n')
    words = text.split()
    chars = len(text)
    
    print(f"""
📊 إحصائيات النص:
   📝 عدد الأحرف: {chars}
   🔤 عدد الكلمات: {len(words)}
   📄 عدد الأسطر: {len(lines)}
   📏 متوسط الكلمات في السطر: {len(words)/len(lines):.1f}
    """)

def advanced_invoice_analysis(image_path, lang='ara+eng'):
    """
    تحليل فاتورة متقدم مخصص لاستخراج البيانات المطلوبة
    """
    try:
        # استخراج النص الأساسي
        print("📖 جاري قراءة الفاتورة...")
        text = extract_text_from_image(image_path, lang, enhance=True)
        
        if "❌" in text or "⚠️" in text:
            return {
                'success': False,
                'error': text,
                'text': text
            }
        
        print("🔍 جاري تحليل بيانات الفاتورة...")
        
        # استخراج بيانات الفاتورة
        invoice_data = extract_invoice_data(text)
        
        # التحقق من صحة البيانات
        validated_data = validate_invoice_data(invoice_data)
        
        # استخراج جدول المنتجات
        table_data = parse_invoice_table(text)
        
        # إنشاء ملخص التحليل
        analysis_summary = {
            'found_invoice_number': len(validated_data['invoice_number']) > 0,
            'found_date': len(validated_data['date']) > 0,
            'found_total': len(validated_data['total']) > 0,
            'found_seller_info': len(validated_data['seller_name']) > 0,
            'found_products': len(validated_data['product_names']) > 0,
            'found_table': len(table_data) > 0,
            'total_products_detected': max(
                len(validated_data['product_names']),
                len(table_data)
            ),
            'completeness_score': 0
        }
        
        # حساب درجة اكتمال البيانات
        required_fields = ['invoice_number', 'date', 'total', 'seller_name']
        found_fields = sum(1 for field in required_fields if len(validated_data[field]) > 0)
        analysis_summary['completeness_score'] = round((found_fields / len(required_fields)) * 100)
        
        return {
            'success': True,
            'text': text,
            'invoice_data': validated_data,
            'table_data': table_data,
            'analysis_summary': analysis_summary,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"خطأ في تحليل الفاتورة: {str(e)}",
            'text': ''
        }

def save_invoice_report(analysis_result, output_file='invoice_analysis'):
    """
    حفظ تقرير تحليل الفاتورة
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if not analysis_result['success']:
            print(f"❌ فشل التحليل: {analysis_result['error']}")
            return False
        
        # حفظ التقرير النصي
        text_file = f"{output_file}_{timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(format_invoice_report(
                analysis_result['invoice_data'], 
                analysis_result['table_data'], 
                'text'
            ))
            
            # إضافة ملخص التحليل
            f.write(f"\n\n📊 ملخص التحليل:")
            f.write(f"\n{'='*30}")
            summary = analysis_result['analysis_summary']
            f.write(f"\n✅ رقم الفاتورة: {'نعم' if summary['found_invoice_number'] else 'لا'}")
            f.write(f"\n✅ التاريخ: {'نعم' if summary['found_date'] else 'لا'}")
            f.write(f"\n✅ الإجمالي: {'نعم' if summary['found_total'] else 'لا'}")
            f.write(f"\n✅ معلومات البائع: {'نعم' if summary['found_seller_info'] else 'لا'}")
            f.write(f"\n✅ المنتجات: {'نعم' if summary['found_products'] else 'لا'}")
            f.write(f"\n✅ جدول المنتجات: {'نعم' if summary['found_table'] else 'لا'}")
            f.write(f"\n📈 درجة الاكتمال: {summary['completeness_score']}%")
            f.write(f"\n🛍️ إجمالي المنتجات المكتشفة: {summary['total_products_detected']}")
            
            # إضافة النص الخام
            f.write(f"\n\n📄 النص الخام:")
            f.write(f"\n{'='*30}")
            f.write(f"\n{analysis_result['text']}")
        
        # حفظ البيانات كـ JSON
        json_file = f"{output_file}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        # حفظ CSV للمنتجات إذا وجدت
        if analysis_result['table_data']:
            csv_file = f"{output_file}_products_{timestamp}.csv"
            import csv
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if analysis_result['table_data']:
                    writer = csv.DictWriter(f, fieldnames=['product_name', 'quantity', 'unit_price', 'total_price', 'vat_amount'])
                    writer.writeheader()
                    writer.writerows(analysis_result['table_data'])
        
        print(f"✅ تم حفظ تقرير تحليل الفاتورة:")
        print(f"   📄 التقرير النصي: {text_file}")
        print(f"   🗂️  بيانات JSON: {json_file}")
        if analysis_result['table_data']:
            print(f"   📊 جدول المنتجات: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في حفظ التقرير: {e}")
        return False

def interactive_invoice_mode():
    """
    وضع تفاعلي مخصص لتحليل الفواتير
    """
    print("""
🧾 مرحباً بك في محلل الفواتير الذكي!
    
الميزات:
✅ استخراج رقم الفاتورة والتاريخ
✅ استخراج إجمالي المبلغ
✅ معلومات البائع (الاسم، العنوان، الهاتف)
✅ تفاصيل المنتجات (الاسم، الكمية، السعر)
✅ الضريبة والخصومات
✅ تصدير البيانات (نص، JSON، CSV)

الأوامر:
1️⃣  تحليل فاتورة واحدة
2️⃣  معالجة مجموعة فواتير
3️⃣  عرض آخر تحليل
4️⃣  تغيير إعدادات اللغة
5️⃣  خروج
    """)
    
    current_lang = 'ara+eng'
    last_analysis = None
    
    while True:
        try:
            choice = input("\n🔸 اختر رقم الأمر: ").strip()
            
            if choice == '1':
                # تحليل فاتورة واحدة
                image_path = input("📁 أدخل مسار الفاتورة: ").strip().strip('"')
                
                if not os.path.exists(image_path):
                    print("❌ الملف غير موجود!")
                    continue
                
                print("\n🚀 بدء تحليل الفاتورة...")
                analysis = advanced_invoice_analysis(image_path, current_lang)
                last_analysis = analysis
                
                if analysis['success']:
                    # عرض الملخص السريع
                    summary = analysis['analysis_summary']
                    print(f"\n✅ تم تحليل الفاتورة بنجاح!")
                    print(f"📊 درجة اكتمال البيانات: {summary['completeness_score']}%")
                    print(f"🛍️ المنتجات المكتشفة: {summary['total_products_detected']}")
                    
                    # عرض النتائج الرئيسية
                    invoice_data = analysis['invoice_data']
                    
                    print("\n🔍 البيانات المستخرجة:")
                    print("-" * 40)
                    
                    if invoice_data['invoice_number']:
                        print(f"🔢 رقم الفاتورة: {invoice_data['invoice_number'][0]}")
                    
                    if invoice_data['date']:
                        print(f"📅 التاريخ: {invoice_data['date'][0]}")
                    
                    if invoice_data['total']:
                        print(f"💰 الإجمالي: {invoice_data['total'][0]}")
                    
                    if invoice_data['seller_name']:
                        print(f"🏢 البائع: {invoice_data['seller_name'][0]}")
                    
                    if invoice_data['seller_phone']:
                        print(f"📞 الهاتف: {invoice_data['seller_phone'][0]}")
                    
                    # عرض المنتجات
                    if analysis['table_data']:
                        print(f"\n🛍️ المنتجات ({len(analysis['table_data'])}):")
                        print("-" * 40)
                        for i, product in enumerate(analysis['table_data'][:5], 1):  # أول 5 منتجات
                            print(f"{i}. {product['product_name']}")
                            print(f"   الكمية: {product['quantity']} | السعر: {product['unit_price']} | الإجمالي: {product['total_price']}")
                        
                        if len(analysis['table_data']) > 5:
                            print(f"   ... و {len(analysis['table_data']) - 5} منتج آخر")
                    
                    elif invoice_data['product_names']:
                        print(f"\n🛍️ المنتجات المكتشفة:")
                        for i, product in enumerate(invoice_data['product_names'][:3], 1):
                            print(f"{i}. {product}")
                    
                    # خيارات الحفظ
                    print(f"\n💾 خيارات الحفظ:")
                    save_choice = input("حفظ التقرير؟ (y/n): ").lower().strip()
                    
                    if save_choice in ['y', 'yes', 'نعم']:
                        save_invoice_report(analysis)
                
                else:
                    print(f"❌ فشل في تحليل الفاتورة: {analysis['error']}")
            
            elif choice == '2':
                # معالجة مجموعة فواتير
                folder_path = input("📁 أدخل مسار مجلد الفواتير: ").strip().strip('"')
                
                if not os.path.exists(folder_path):
                    print("❌ المجلد غير موجود!")
                    continue
                
                supported_formats = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
                files = [f for f in os.listdir(folder_path) 
                        if f.lower().endswith(supported_formats)]
                
                if not files:
                    print("❌ لا توجد صور في المجلد")
                    continue
                
                print(f"🔄 معالجة {len(files)} فاتورة...")
                
                batch_results = []
                successful = 0
                failed = 0
                
                for i, filename in enumerate(files, 1):
                    image_path = os.path.join(folder_path, filename)
                    print(f"\n[{i}/{len(files)}] معالجة: {filename}")
                    
                    analysis = advanced_invoice_analysis(image_path, current_lang)
                    batch_results.append({
                        'filename': filename,
                        'analysis': analysis
                    })
                    
                    if analysis['success']:
                        successful += 1
                        summary = analysis['analysis_summary']
                        print(f"✅ نجح - اكتمال البيانات: {summary['completeness_score']}%")
                        
                        # حفظ تلقائي للتقرير
                        base_name = os.path.splitext(filename)[0]
                        save_invoice_report(analysis, f"invoice_{base_name}")
                    else:
                        failed += 1
                        print(f"❌ فشل: {analysis.get('error', 'خطأ غير معروف')}")
                
                # ملخص المعالجة المجمعة
                print(f"\n📊 ملخص المعالجة المجمعة:")
                print(f"✅ نجح: {successful}")
                print(f"❌ فشل: {failed}")
                print(f"📈 معدل النجاح: {(successful/len(files)*100):.1f}%")
                
                # حفظ ملخص شامل
                summary_file = f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'batch_info': {
                            'total_files': len(files),
                            'successful': successful,
                            'failed': failed,
                            'success_rate': successful/len(files)*100
                        },
                        'results': batch_results
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"💾 تم حفظ ملخص شامل في: {summary_file}")
            
            elif choice == '3':
                # عرض آخر تحليل
                if last_analysis and last_analysis['success']:
                    print("\n📋 آخر تحليل:")
                    print(format_invoice_report(
                        last_analysis['invoice_data'], 
                        last_analysis['table_data'], 
                        'text'
                    ))
                else:
                    print("❌ لا يوجد تحليل سابق أو فشل آخر تحليل")
            
            elif choice == '4':
                # تغيير اللغة
                print("\n🌐 خيارات اللغة:")
                print("1. العربية فقط (ara)")
                print("2. الإنجليزية فقط (eng)")
                print("3. العربية والإنجليزية (ara+eng) - مُستحسن")
                print("4. لغة مخصصة")
                
                lang_choice = input("اختر: ").strip()
                
                if lang_choice == '1':
                    current_lang = 'ara'
                elif lang_choice == '2':
                    current_lang = 'eng'
                elif lang_choice == '3':
                    current_lang = 'ara+eng'
                elif lang_choice == '4':
                    current_lang = input("أدخل رمز اللغة: ").strip()
                
                print(f"✅ تم تغيير اللغة إلى: {current_lang}")
            
            elif choice == '5':
                print("👋 شكراً لاستخدام محلل الفواتير!")
                break
            
            else:
                print("❌ اختيار غير صحيح!")
                
        except KeyboardInterrupt:
            print("\n👋 تم إيقاف المحلل")
            break
        except Exception as e:
            print(f"❌ خطأ: {e}")

def batch_ocr(folder_path, lang='ara+eng'):
    """معالجة مجموعة من الصور"""
    supported_formats = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
    
    if not os.path.exists(folder_path):
        print(f"❌ المجلد غير موجود: {folder_path}")
        return
    
    files = [f for f in os.listdir(folder_path) 
             if f.lower().endswith(supported_formats)]
    
    if not files:
        print("❌ لا توجد صور مدعومة في المجلد")
        return
    
    print(f"🔄 معالجة {len(files)} صورة...")
    
    results = {}
    for i, filename in enumerate(files, 1):
        image_path = os.path.join(folder_path, filename)
        print(f"\n[{i}/{len(files)}] معالجة: {filename}")
        
        text = extract_text_from_image(image_path, lang)
        results[filename] = text
        
        # حفظ النتيجة
        output_file = f"text_{os.path.splitext(filename)[0]}.txt"
        save_text_to_file(text, output_file)
    
    print(f"\n✅ تمت معالجة {len(files)} صورة بنجاح!")
    return results

def check_tesseract():
    """التحقق من تثبيت tesseract"""
    try:
        version = pytesseract.get_tesseract_version()
        langs = pytesseract.get_languages()
        
        print(f"✅ Tesseract مثبت - الإصدار: {version}")
        print(f"🌐 اللغات المدعومة: {', '.join(langs)}")
        
        if 'ara' not in langs:
            print("⚠️ تحذير: اللغة العربية غير مثبتة")
            print("لتثبيت العربية:")
            print("- Windows: تأكد من تحديد Arabic في التثبيت")
            print("- Ubuntu: sudo apt install tesseract-ocr-ara")
            print("- Mac: brew install tesseract-lang")
        
        return True
    except Exception as e:
        print(f"❌ Tesseract غير مثبت: {e}")
        print("يرجى تثبيت Tesseract-OCR:")
        print("- Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("- Ubuntu: sudo apt install tesseract-ocr")
        print("- Mac: brew install tesseract")
        return False

def main():
    """الدالة الرئيسية المحسنة للفواتير"""
    print("🧾 محلل الفواتير الذكي - استخراج البيانات من الفواتير")
    print("="*65)
    
    # فحص النظام
    if not check_tesseract():
        return
    
    # التحقق من المعاملات
    if len(sys.argv) > 1:
        if '--invoice' in sys.argv or '-i' in sys.argv:
            # وضع الفاتورة المباشر
            try:
                invoice_index = sys.argv.index('--invoice') if '--invoice' in sys.argv else sys.argv.index('-i')
                if invoice_index + 1 < len(sys.argv):
                    image_path = sys.argv[invoice_index + 1]
                    
                    if os.path.exists(image_path):
                        print(f"\n🧾 تحليل فاتورة: {image_path}")
                        
                        lang = 'ara+eng'
                        if len(sys.argv) > invoice_index + 2:
                            lang = sys.argv[invoice_index + 2]
                        
                        analysis = advanced_invoice_analysis(image_path, lang)
                        
                        if analysis['success']:
                            print("\n✅ تم تحليل الفاتورة بنجاح!")
                            
                            # عرض تقرير مفصل
                            print(format_invoice_report(
                                analysis['invoice_data'], 
                                analysis['table_data'], 
                                'text'
                            ))
                            
                            # حفظ التقرير
                            save_invoice_report(analysis)
                        else:
                            print(f"❌ فشل في تحليل الفاتورة: {analysis['error']}")
                    else:
                        print(f"❌ الملف غير موجود: {image_path}")
                else:
                    print("❌ يرجى تحديد مسار الفاتورة بعد --invoice")
            except ValueError:
                print("❌ خطأ في المعاملات")
        
        elif '--help' in sys.argv or '-h' in sys.argv:
            print_invoice_help()
        
        elif '--demo' in sys.argv:
            demo_invoice_patterns()
        
        else:
            # الوضع العادي القديم
            image_path = sys.argv[1]
            lang = sys.argv[2] if len(sys.argv) > 2 else 'ara+eng'
            
            if os.path.exists(image_path):
                text = extract_text_from_image(image_path, lang)
                print(f"\n📋 النص المستخرج:\n{'-'*50}")
                print(text)
                print('-'*50)
                get_text_stats(text)
                save_text_to_file(text, 'extracted_text.txt')
            else:
                print(f"❌ الملف غير موجود: {image_path}")
    else:
        # الوضع التفاعلي للفواتير
        interactive_invoice_mode()

def print_invoice_help():
    """طباعة تعليمات استخدام محلل الفواتير"""
    print("""
🧾 محلل الفواتير الذكي - تعليمات الاستخدام

الاستخدام:
    python ocr.py                                    # الوضع التفاعلي للفواتير
    python ocr.py --invoice invoice.jpg              # تحليل فاتورة واحدة
    python ocr.py -i receipt.png ara+eng             # تحليل بلغة محددة
    python ocr.py --demo                             # عرض أمثلة الأنماط
    python ocr.py --help                             # هذه المساعدة

البيانات المستخرجة:
📊 معلومات أساسية:
   • رقم الفاتورة (Invoice Number)
   • التاريخ (Date) 
   • الإجمالي (Total Amount)
   
🏢 معلومات البائع:
   • اسم البائع/الشركة (Seller Name)
   • العنوان (Address)
   • رقم الهاتف (Phone Number)
   
🛍️ تفاصيل المنتجات:
   • أسماء المنتجات (Product Names)
   • الكميات (Quantities)
   • أسعار الوحدة (Unit Prices)
   • الإجماليات الفرعية (Total per Item)
   
💰 المعلومات المالية:
   • الضريبة المضافة (VAT)
   • الخصومات (Discounts)

الصيغ المدعومة:
✅ الفواتير العربية والإنجليزية
✅ تنسيقات مختلفة للأرقام والتواريخ
✅ جداول المنتجات المعقدة
✅ عملات متنوعة (ريال، درهم، دولار، إلخ)

المخرجات:
📄 تقرير نصي مفصل
🗂️ بيانات JSON للمعالجة البرمجية  
📊 جدول CSV للمنتجات
📈 درجة اكتمال البيانات

أمثلة:
    python ocr.py --invoice "فاتورة_شراء.jpg"
    python ocr.py -i receipt.png eng
    """)

def demo_invoice_patterns():
    """عرض أمثلة على أنماط الفواتير المدعومة"""
    print("""
🧾 أمثلة على البيانات المدعومة في الفواتير:

🔢 أرقام الفواتير:
   • رقم الفاتورة: INV-2023-001
   • Invoice No: 12345
   • فاتورة رقم 2023/456
   • Bill #789

📅 التواريخ:
   • 15/03/2023
   • 2023-12-25
   • 10 مارس 2023  
   • 5 January 2023
   • تاريخ الفاتورة: 01/01/2024

💰 الأسعار والمبالغ:
   • الإجمالي: 1,250.50 ريال
   • Total: $99.99
   • المجموع: 500 درهم
   • Grand Total: 1500 SR

🏢 معلومات البائع:
   • شركة المثال التجارية
   • Example Trading Company
   • العنوان: الرياض، شارع الملك فهد
   • Address: Dubai, Sheikh Zayed Road
   • هاتف: +966 50 123 4567

🛍️ بيانات المنتجات:
   • لابتوب ديل انسبايرون    2    2500.00    5000.00
   • Dell Laptop              1    $999.99    $999.99
   • المنتج: هاتف ذكي | الكمية: 3 | السعر: 800

💸 الضرائب والخصومات:
   • ضريبة القيمة المضافة: 15%
   • VAT: 5%
   • خصم: 10%
   • Discount: $50

يدعم المحلل تنسيقات وأساليب مختلفة للفواتير!
    """)

# تحديث نمط الاستدعاء
if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        print_invoice_help()
    elif '--demo' in sys.argv:
        demo_invoice_patterns()
    else:
        main()