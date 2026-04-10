from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, Match, Team

matches_bp = Blueprint('matches', __name__)


@matches_bp.route('/matches')
@login_required
def matches_list():
    """صفحة إدارة المباريات"""
    matches = Match.query.order_by(Match.day, Match.match_order).all()
    return render_template('matches.html', matches=matches)


@matches_bp.route('/api/matches', methods=['GET'])
@login_required
def api_get_matches():
    """API: قائمة المباريات"""
    day = request.args.get('day', type=int)
    query = Match.query.order_by(Match.day, Match.match_order)
    if day:
        query = query.filter_by(day=day)
    matches = query.all()
    return jsonify([m.to_dict() for m in matches])


@matches_bp.route('/api/matches', methods=['POST'])
@login_required
def api_create_match():
    """API: إضافة مباراة جديدة"""
    data = request.get_json()
    name = data.get('name', '').strip()
    day = data.get('day')
    period = data.get('period', 'morning')
    match_order = data.get('match_order')
    time_label = data.get('time_label', '').strip()

    if not name or not day or not match_order:
        return jsonify({'error': 'الاسم واليوم والترتيب مطلوبة'}), 400

    if day not in [1, 2]:
        return jsonify({'error': 'اليوم غير صالح'}), 400

    if period not in ['morning', 'evening']:
        return jsonify({'error': 'الفترة غير صالحة'}), 400

    match = Match(
        name=name,
        day=day,
        period=period,
        match_order=match_order,
        time_label=time_label or None
    )
    db.session.add(match)
    db.session.commit()

    return jsonify({
        'message': 'تمت إضافة المباراة بنجاح',
        'match': match.to_dict()
    }), 201


@matches_bp.route('/api/matches/<int:id>', methods=['PUT'])
@login_required
def api_update_match(id):
    """API: تعديل مباراة"""
    match = Match.query.get_or_404(id)
    data = request.get_json()

    name = data.get('name', '').strip()
    day = data.get('day', match.day)
    period = data.get('period', match.period)
    match_order = data.get('match_order', match.match_order)
    time_label = data.get('time_label', '').strip()

    if not name:
        return jsonify({'error': 'اسم المباراة مطلوب'}), 400

    match.name = name
    match.day = day
    match.period = period
    match.match_order = match_order
    match.time_label = time_label or None
    db.session.commit()

    return jsonify({'message': 'تم تحديث المباراة بنجاح', 'match': match.to_dict()})


@matches_bp.route('/api/matches/<int:id>', methods=['DELETE'])
@login_required
def api_delete_match(id):
    """API: حذف مباراة"""
    match = Match.query.get_or_404(id)
    match.teams = []  # إزالة العلاقات
    db.session.delete(match)
    db.session.commit()
    return jsonify({'message': 'تم حذف المباراة بنجاح'})


@matches_bp.route('/api/matches/<int:id>/teams', methods=['POST'])
@login_required
def api_assign_team_to_match(id):
    """API: تعيين فريق لمباراة"""
    match = Match.query.get_or_404(id)
    data = request.get_json()
    team_id = data.get('team_id')

    if not team_id:
        return jsonify({'error': 'معرف الفريق مطلوب'}), 400

    team = Team.query.get_or_404(team_id)

    if team in match.teams:
        return jsonify({'error': 'الفريق موجود بالفعل في هذه المباراة'}), 400

    match.teams.append(team)
    db.session.commit()

    return jsonify({
        'message': f'تم تعيين الفريق للمباراة',
        'match': match.to_dict()
    })


@matches_bp.route('/api/matches/<int:id>/teams/<int:team_id>', methods=['DELETE'])
@login_required
def api_remove_team_from_match(id, team_id):
    """API: إزالة فريق من مباراة"""
    match = Match.query.get_or_404(id)
    team = Team.query.get_or_404(team_id)

    if team not in match.teams:
        return jsonify({'error': 'الفريق غير موجود في هذه المباراة'}), 400

    match.teams.remove(team)
    db.session.commit()

    return jsonify({
        'message': 'تم إزالة الفريق من المباراة',
        'match': match.to_dict()
    })


@matches_bp.route('/api/teams/<int:team_id>/matches', methods=['GET'])
@login_required
def api_get_team_matches(team_id):
    """API: مباريات فريق معين"""
    team = Team.query.get_or_404(team_id)
    day = request.args.get('day', type=int)

    matches = team.matches
    if day:
        matches = [m for m in matches if m.day == day]

    return jsonify([m.to_dict() for m in matches])
