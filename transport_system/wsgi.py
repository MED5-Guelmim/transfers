"""
ملف WSGI لنشر التطبيق على PythonAnywhere
==========================================
في إعدادات PythonAnywhere:
- Source code: /home/USERNAME/transport_system
- Working directory: /home/USERNAME/transport_system
- WSGI configuration file: أنسخ محتوى هذا الملف هناك

أو اضبط مسار WSGI في إعدادات PythonAnywhere ليشير إلى:
/home/USERNAME/transport_system/wsgi.py
"""

import sys
import os

# ═══════════════════════════════════════
# ضبط مسار المشروع — غيّر USERNAME إلى اسم المستخدم الخاص بك
# ═══════════════════════════════════════
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# استيراد التطبيق
from app import app as application
