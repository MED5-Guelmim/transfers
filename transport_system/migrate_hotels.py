"""
سكريبت ترحيل قاعدة البيانات
============================
ينقل بيانات الفنادق من عمود hotel النصي في جدول academy
إلى جدول hotel جديد مع ربطها بـ hotel_id
"""
import os
import sqlite3

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'transport.db')

print(f"[*] ترحيل قاعدة البيانات: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# الخطوة 1: إنشاء جدول hotel إذا لم يكن موجوداً
print("[1] إنشاء جدول hotel...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS hotel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL UNIQUE,
        address VARCHAR(300)
    )
''')

# الخطوة 2: التحقق من وجود عمود hotel النصي في جدول academy
cursor.execute("PRAGMA table_info(academy)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

has_old_hotel = 'hotel' in column_names
has_hotel_id = 'hotel_id' in column_names

if has_old_hotel and not has_hotel_id:
    print("[2] نقل بيانات الفنادق من عمود hotel إلى جدول hotel...")
    
    # استخراج أسماء الفنادق الفريدة
    cursor.execute("SELECT DISTINCT hotel FROM academy WHERE hotel IS NOT NULL AND hotel != ''")
    hotel_names = cursor.fetchall()
    
    for (name,) in hotel_names:
        cursor.execute("INSERT OR IGNORE INTO hotel (name) VALUES (?)", (name.strip(),))
    
    print(f"   تم إضافة {len(hotel_names)} فندق")
    
    # الخطوة 3: إضافة عمود hotel_id
    print("[3] إضافة عمود hotel_id...")
    cursor.execute("ALTER TABLE academy ADD COLUMN hotel_id INTEGER REFERENCES hotel(id)")
    
    # الخطوة 4: ربط الأكاديميات بالفنادق
    print("[4] ربط الأكاديميات بالفنادق...")
    cursor.execute("SELECT id, hotel FROM academy")
    academies = cursor.fetchall()
    
    for (acad_id, hotel_name) in academies:
        if hotel_name:
            cursor.execute("SELECT id FROM hotel WHERE name = ?", (hotel_name.strip(),))
            hotel_row = cursor.fetchone()
            if hotel_row:
                cursor.execute("UPDATE academy SET hotel_id = ? WHERE id = ?", (hotel_row[0], acad_id))
    
    print(f"   تم ربط {len(academies)} أكاديمية")
    
    # الخطوة 5: حذف العمود القديم (SQLite لا يدعم DROP COLUMN مباشرة في الإصدارات القديمة)
    # نقوم بإعادة إنشاء الجدول
    print("[5] إعادة هيكلة جدول academy...")
    
    # حفظ البيانات
    cursor.execute("""
        SELECT id, name, hotel_id FROM academy
    """)
    academy_data = cursor.fetchall()
    
    # حفظ بيانات الجداول المرتبطة
    cursor.execute("SELECT id, academy_id, gender, category, day1_status, day2_status FROM team")
    team_data = cursor.fetchall()
    
    cursor.execute("SELECT id, name, type, ownership, academy_id, can_return FROM vehicle")
    vehicle_data = cursor.fetchall()
    
    # حذف الجداول المعتمدة مؤقتاً 
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    cursor.execute("DROP TABLE IF EXISTS academy")
    cursor.execute('''
        CREATE TABLE academy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            hotel_id INTEGER REFERENCES hotel(id)
        )
    ''')
    
    for row in academy_data:
        cursor.execute("INSERT INTO academy (id, name, hotel_id) VALUES (?, ?, ?)", row)
    
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("   تم بنجاح!")

elif has_hotel_id:
    print("[*] الترحيل تم مسبقاً - عمود hotel_id موجود بالفعل")
else:
    print("[*] لا يوجد عمود hotel قديم ولا hotel_id - إعداد جديد")
    # فقط تأكد من وجود hotel_id
    if 'hotel_id' not in column_names:
        cursor.execute("ALTER TABLE academy ADD COLUMN hotel_id INTEGER REFERENCES hotel(id)")

conn.commit()
conn.close()

print("\n[✓] اكتمل الترحيل بنجاح!")
