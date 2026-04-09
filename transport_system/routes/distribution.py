from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, Academy, Team
from algorithm import generate_distribution, get_distribution

distribution_bp = Blueprint('distribution', __name__)


@distribution_bp.route('/distribution')
@login_required
def distribution_page():
    """صفحة توزيع النقل"""
    return render_template('distribution.html')


@distribution_bp.route('/api/distribution/generate', methods=['POST'])
@login_required
def api_generate_distribution():
    """API: توليد التوزيع تلقائياً"""
    data = request.get_json()
    day = data.get('day', 1)

    if day not in [1, 2]:
        return jsonify({'error': 'يوم غير صالح'}), 400

    try:
        result = generate_distribution(day)
        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500


@distribution_bp.route('/api/distribution/<int:day>', methods=['GET'])
@login_required
def api_get_distribution(day):
    """API: الحصول على التوزيع الحالي"""
    if day not in [1, 2]:
        return jsonify({'error': 'يوم غير صالح'}), 400

    result = get_distribution(day)
    return jsonify(result)


# ─── صفحة حالة الفرق ───

@distribution_bp.route('/teams_status')
@login_required
def teams_status_page():
    """صفحة إدارة الفرق"""
    academies = Academy.query.order_by(Academy.name).all()
    # تجميع كل معرّفات الفرق لاستخدامها في الجافاسكربت
    team_ids = [t.id for a in academies for t in a.teams]
    return render_template('teams_status.html', academies=academies, team_ids=team_ids)


@distribution_bp.route('/api/teams_status', methods=['GET'])
@login_required
def api_teams_status():
    """API: الحصول على حالة كل الفرق"""
    academies = Academy.query.order_by(Academy.name).all()
    result = []
    for academy in academies:
        teams = Team.query.filter_by(academy_id=academy.id).all()
        result.append({
            'academy': academy.to_dict(),
            'teams': [t.to_dict() for t in teams]
        })
    return jsonify(result)
