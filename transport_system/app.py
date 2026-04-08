import os
import sys
from flask import Flask, render_template, jsonify
from models import db, Academy, Team, Vehicle, Trip, Hotel


def create_app():
    app = Flask(__name__)

    # إعدادات التطبيق
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'transport.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'basketball-transport-2026'
    app.config['JSON_AS_ASCII'] = False

    # تهيئة قاعدة البيانات
    db.init_app(app)

    with app.app_context():
        # تسجيل Blueprints
        from routes.academies import academies_bp
        from routes.vehicles import vehicles_bp
        from routes.distribution import distribution_bp
        from routes.reports import reports_bp
        from routes.hotels import hotels_bp

        app.register_blueprint(academies_bp)
        app.register_blueprint(vehicles_bp)
        app.register_blueprint(distribution_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(hotels_bp)

        # إنشاء الجداول
        db.create_all()

    # الصفحة الرئيسية — لوحة التحكم
    @app.route('/')
    def dashboard():
        academies_count = Academy.query.count()
        teams_active_d1 = Team.query.filter_by(day1_status='active').count()
        teams_active_d2 = Team.query.filter_by(day2_status='active').count()
        teams_total = Team.query.count()
        vehicles_count = Vehicle.query.count()
        vehicles_public = Vehicle.query.filter_by(ownership='public').count()
        vehicles_private = Vehicle.query.filter_by(ownership='academy').count()
        trips_d1 = Trip.query.filter_by(day=1).count()
        trips_d2 = Trip.query.filter_by(day=2).count()

        return render_template('dashboard.html',
                               academies_count=academies_count,
                               teams_active_d1=teams_active_d1,
                               teams_active_d2=teams_active_d2,
                               teams_total=teams_total,
                               vehicles_count=vehicles_count,
                               vehicles_public=vehicles_public,
                               vehicles_private=vehicles_private,
                               trips_d1=trips_d1,
                               trips_d2=trips_d2)

    # API لإحصائيات لوحة التحكم
    @app.route('/api/stats')
    def api_stats():
        return jsonify({
            'academies': Academy.query.count(),
            'teams_total': Team.query.count(),
            'teams_active_d1': Team.query.filter_by(day1_status='active').count(),
            'teams_active_d2': Team.query.filter_by(day2_status='active').count(),
            'vehicles': Vehicle.query.count(),
            'vehicles_public': Vehicle.query.filter_by(ownership='public').count(),
            'vehicles_private': Vehicle.query.filter_by(ownership='academy').count()
        })

    return app


# ═══════════════════════════════════════
# إنشاء التطبيق على مستوى الوحدة (مطلوب لـ PythonAnywhere)
# ═══════════════════════════════════════
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

