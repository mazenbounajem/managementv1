import os
import re
import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen.canvas import Canvas
import reportlab.lib.styles

def is_arabic(text):
    """Simple check if text contains Arabic characters"""
    if not isinstance(text, str):
        return False
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or \
           '\u08A0' <= char <= '\u08FF' or '\uFB50' <= char <= '\uFDFF' or \
           '\uFE70' <= char <= '\uFEFF':
            return True
    return False

def get_arabic_text(text):
    """Reshape and apply bidi algorithm to text if it contains Arabic, preserving HTML tags."""
    if isinstance(text, str) and is_arabic(text):
        try:
            # Split the string by HTML tags to prevent bidi from reversing tags
            parts = re.split(r'(<[^>]+>)', text)
            for i in range(len(parts)):
                if not parts[i].startswith('<') and is_arabic(parts[i]):
                    reshaped = arabic_reshaper.reshape(parts[i])
                    parts[i] = get_display(reshaped)
            return "".join(parts)
        except Exception as e:
            print(f"Error reshaping text: {e}")
            return text
    return text

def setup_arabic_support():
    """Configure ReportLab globally to support Arabic text via monkey patching."""
    
    # 1. Register Tahoma font (fallback to Arial)
    tahoma_path = r'C:\Windows\Fonts\tahoma.ttf'
    tahomabd_path = r'C:\Windows\Fonts\tahomabd.ttf'
    arial_path = r'C:\Windows\Fonts\arial.ttf'
    arialbd_path = r'C:\Windows\Fonts\arialbd.ttf'
    
    font_name = 'ArabicFont'
    bold_font_name = 'ArabicFont-Bold'
    
    if os.path.exists(tahoma_path):
        pdfmetrics.registerFont(TTFont(font_name, tahoma_path))
        if os.path.exists(tahomabd_path):
            pdfmetrics.registerFont(TTFont(bold_font_name, tahomabd_path))
        else:
            pdfmetrics.registerFont(TTFont(bold_font_name, tahoma_path))
    elif os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont(font_name, arial_path))
        if os.path.exists(arialbd_path):
            pdfmetrics.registerFont(TTFont(bold_font_name, arialbd_path))
        else:
            pdfmetrics.registerFont(TTFont(bold_font_name, arial_path))
    else:
        print("Warning: Neither Tahoma nor Arial fonts found in C:\\Windows\\Fonts\\.")
        return

    # 2. Patch getSampleStyleSheet to default to ArabicFont
    original_get_sample = reportlab.lib.styles.getSampleStyleSheet
    def patched_get_sample():
        styles = original_get_sample()
        for name, style in styles.byName.items():
            if hasattr(style, 'fontName'):
                if 'Bold' in style.fontName or 'Heading' in name or 'Title' in name:
                    style.fontName = bold_font_name
                else:
                    style.fontName = font_name
        return styles
    reportlab.lib.styles.getSampleStyleSheet = patched_get_sample

    # 3. Patch Paragraph to reshape text
    original_paragraph_init = Paragraph.__init__
    def patched_paragraph_init(self, text, *args, **kwargs):
        text = get_arabic_text(text)
        original_paragraph_init(self, text, *args, **kwargs)
    Paragraph.__init__ = patched_paragraph_init

    # 4. Patch Table to reshape string cells
    original_table_init = Table.__init__
    def patched_table_init(self, data, *args, **kwargs):
        new_data = []
        if data:
            for row in data:
                new_row = []
                for cell in row:
                    if isinstance(cell, str):
                        new_row.append(get_arabic_text(cell))
                    else:
                        new_row.append(cell)
                new_data.append(new_row)
        else:
            new_data = data
        original_table_init(self, new_data, *args, **kwargs)
    Table.__init__ = patched_table_init

    # 5. Patch TableStyle to use ArabicFont
    original_tablestyle_init = TableStyle.__init__
    original_tablestyle_add = TableStyle.add

    def fix_cmd(cmd):
        cmd_list = list(cmd)
        if cmd_list and (cmd_list[0] == 'FONTNAME' or cmd_list[0] == 'FONT'):
            if len(cmd_list) >= 4:
                if 'Bold' in str(cmd_list[3]) or 'bold' in str(cmd_list[3]):
                    cmd_list[3] = bold_font_name
                else:
                    cmd_list[3] = font_name
        return tuple(cmd_list)

    def patched_tablestyle_init(self, cmds=None, *args, **kwargs):
        if cmds is not None:
            cmds = [fix_cmd(cmd) for cmd in cmds]
        original_tablestyle_init(self, cmds, *args, **kwargs)

    def patched_tablestyle_add(self, *cmd):
        cmd = fix_cmd(cmd)
        original_tablestyle_add(self, *cmd)

    TableStyle.__init__ = patched_tablestyle_init
    TableStyle.add = patched_tablestyle_add

    # 6. Patch Canvas text drawing methods
    original_draw_string = Canvas.drawString
    original_draw_centred = Canvas.drawCentredString
    original_draw_right = Canvas.drawRightString

    def patched_draw_string(self, x, y, text, *args, **kwargs):
        text = get_arabic_text(text)
        original_draw_string(self, x, y, text, *args, **kwargs)

    def patched_draw_centred(self, x, y, text, *args, **kwargs):
        text = get_arabic_text(text)
        original_draw_centred(self, x, y, text, *args, **kwargs)

    def patched_draw_right(self, x, y, text, *args, **kwargs):
        text = get_arabic_text(text)
        original_draw_right(self, x, y, text, *args, **kwargs)

    Canvas.drawString = patched_draw_string
    Canvas.drawCentredString = patched_draw_centred
    Canvas.drawRightString = patched_draw_right

    # 7. Patch pdfmetrics.stringWidth
    original_string_width = pdfmetrics.stringWidth
    def patched_string_width(text, fontName, fontSize):
        text = get_arabic_text(text)
        return original_string_width(text, fontName, fontSize)
    pdfmetrics.stringWidth = patched_string_width
