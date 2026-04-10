import os
import sys
from flask import Flask, render_template, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from models import db, Academy, Team, Vehicle, Trip, Hotel, User, Match


def create_app():
    app = Flask(__name__)

    # إعدادات التطبيق
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'transport.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'basketball-transport-2026-secret'
    app.config['JSON_AS_ASCII'] = False

    # تهيئة قاعدة البيانات
    db.init_app(app)

    # ═══════════════════════════════════════
    # تهيئة Flask-Login
    # ═══════════════════════════════════════
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # تسجيل Blueprints
        from routes.academies import academies_bp
        from routes.vehicles import vehicles_bp
        from routes.distribution import distribution_bp
        from routes.reports import reports_bp
        from routes.hotels import hotels_bp
        from routes.auth import auth_bp
        from routes.users import users_bp
        from routes.matches import matches_bp

        app.register_blueprint(academies_bp)
        app.register_blueprint(vehicles_bp)
        app.register_blueprint(distribution_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(hotels_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(users_bp)
        app.register_blueprint(matches_bp)

        # إنشاء الجداول
        db.create_all()

        # ═══════════════════════════════════════
        # إنشاء مستخدم admin افتراضي
        # ═══════════════════════════════════════
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                display_name='المدير العام',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('[OK] Default user created: admin / admin123')

        # ═══════════════════════════════════════
        # ترحيل: إزالة أعمدة الإقصاء القديمة إن وُجدت
        # ═══════════════════════════════════════
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            team_columns = [c['name'] for c in inspector.get_columns('team')]
            if 'day1_status' in team_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE team DROP COLUMN day1_status'))
                    conn.execute(db.text('ALTER TABLE team DROP COLUMN day2_status'))
                    conn.commit()
                print('[OK] Migrated: removed day1_status, day2_status from team table')
        except Exception:
            pass  # SQLite قد لا يدعم DROP COLUMN في النسخ القديمة

    # الصفحة الرئيسية — لوحة التحكم
    @app.route('/')
    @login_required
    def dashboard():
        academies_count = Academy.query.count()
        teams_total = Team.query.count()
        vehicles_count = Vehicle.query.count()
        vehicles_public = Vehicle.query.filter_by(ownership='public').count()
        vehicles_private = Vehicle.query.filter_by(ownership='academy').count()
        trips_d1 = Trip.query.filter_by(day=1).count()
        trips_d2 = Trip.query.filter_by(day=2).count()
        matches_d1 = Match.query.filter_by(day=1).count()
        matches_d2 = Match.query.filter_by(day=2).count()

        return render_template('dashboard.html',
                               academies_count=academies_count,
                               teams_total=teams_total,
                               vehicles_count=vehicles_count,
                               vehicles_public=vehicles_public,
                               vehicles_private=vehicles_private,
                               trips_d1=trips_d1,
                               trips_d2=trips_d2,
                               matches_d1=matches_d1,
                               matches_d2=matches_d2)

    # API لإحصائيات لوحة التحكم
    @app.route('/api/stats')
    @login_required
    def api_stats():
        return jsonify({
            'academies': Academy.query.count(),
            'teams_total': Team.query.count(),
            'vehicles': Vehicle.query.count(),
            'vehicles_public': Vehicle.query.filter_by(ownership='public').count(),
            'vehicles_private': Vehicle.query.filter_by(ownership='academy').count(),
            'matches_d1': Match.query.filter_by(day=1).count(),
            'matches_d2': Match.query.filter_by(day=2).count()
        })

    return app


# ═══════════════════════════════════════
# إنشاء التطبيق على مستوى الوحدة (مطلوب لـ PythonAnywhere)
# ═══════════════════════════════════════
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
