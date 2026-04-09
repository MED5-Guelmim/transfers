"""
سكريبت ترحيل قاعدة البيانات
يستعيد البيانات القديمة ويضيف الجداول الجديدة (match, match_teams, match_id في trip)
"""
import os
import shutil
import sqlite3

basedir = os.path.abspath(os.path.dirname(__file__))
OLD_DB = os.path.join(os.path.dirname(basedir), 'save', 'transport (1).db')
NEW_DB = os.path.join(basedir, 'transport.db')


def migrate():
    print(f'[1] Old DB: {OLD_DB}')
    print(f'    New DB: {NEW_DB}')

    if not os.path.exists(OLD_DB):
        print('[ERROR] Old database not found!')
        return

    # 1. نسخ الملف القديم كملف جديد
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)
        print('[2] Removed existing new DB')

    shutil.copy2(OLD_DB, NEW_DB)
    print('[3] Copied old DB as new DB')

    # 2. فتح قاعدة البيانات وإضافة الجداول الجديدة
    conn = sqlite3.connect(NEW_DB)
    cursor = conn.cursor()

    # التحقق من الجداول الموجودة
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [r[0] for r in cursor.fetchall()]
    print(f'[4] Existing tables: {existing_tables}')

    # إنشاء جدول المباريات
    if 'match' not in existing_tables:
        cursor.execute('''
            CREATE TABLE match (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                day INTEGER NOT NULL,
                period VARCHAR(10) NOT NULL,
                match_order INTEGER NOT NULL,
                time_label VARCHAR(50)
            )
        ''')
        print('[5] Created "match" table')
    else:
        print('[5] "match" table already exists')

    # إنشاء جدول وسيط المباراة-الفريق
    if 'match_teams' not in existing_tables:
        cursor.execute('''
            CREATE TABLE match_teams (
                match_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                PRIMARY KEY (match_id, team_id),
                FOREIGN KEY (match_id) REFERENCES match(id),
                FOREIGN KEY (team_id) REFERENCES team(id)
            )
        ''')
        print('[6] Created "match_teams" table')
    else:
        print('[6] "match_teams" table already exists')

    # إضافة عمود match_id لجدول الرحلات
    cursor.execute("PRAGMA table_info(trip)")
    trip_columns = [r[1] for r in cursor.fetchall()]

    if 'match_id' not in trip_columns:
        cursor.execute('ALTER TABLE trip ADD COLUMN match_id INTEGER REFERENCES match(id)')
        print('[7] Added "match_id" column to trip table')
    else:
        print('[7] "match_id" column already exists in trip')

    # إزالة أعمدة الإقصاء القديمة من الفرق (SQLite لا يدعم DROP COLUMN مباشرة)
    # لذلك سنتركها — النموذج الجديد لا يقرأها فلا مشكلة
    cursor.execute("PRAGMA table_info(team)")
    team_columns = [r[1] for r in cursor.fetchall()]
    print(f'[8] Team columns: {team_columns}')
    if 'day1_status' in team_columns:
        print('    -> day1_status/day2_status still in DB (ignored by new code, no issue)')

    # التحقق من وجود جدول المستخدمين
    if 'user' not in existing_tables:
        cursor.execute('''
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) NOT NULL UNIQUE,
                display_name VARCHAR(120) NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                plain_password VARCHAR(120),
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active_user BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('[9] Created "user" table')
    else:
        print('[9] "user" table already exists')

    conn.commit()
    conn.close()

    print('')
    print('=== Migration completed successfully! ===')
    print('Start the app with: python app.py')


if __name__ == '__main__':
    migrate()
