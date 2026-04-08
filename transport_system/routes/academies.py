from flask import Blueprint, render_template, request, jsonify
from models import db, Academy, Team, Vehicle, Hotel

academies_bp = Blueprint('academies', __name__)


@academies_bp.route('/academies')
def academies_list():
    """صفحة إدارة الأكاديميات"""
    academies = Academy.query.order_by(Academy.name).all()
    hotels = Hotel.query.order_by(Hotel.name).all()
    return render_template('academies.html', academies=academies, hotels=hotels)


@academies_bp.route('/api/academies', methods=['GET'])
def api_get_academies():
    """API: الحصول على كل الأكاديميات"""
    academies = Academy.query.order_by(Academy.name).all()
    return jsonify([a.to_dict() for a in academies])


@academies_bp.route('/api/academies', methods=['POST'])
def api_create_academy():
    """API: إضافة أكاديمية جديدة"""
    data = request.get_json()
    name = data.get('name', '').strip()
    hotel_id = data.get('hotel_id')

    if not name or not hotel_id:
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400

    # تحقق من وجود الفندق
    hotel = Hotel.query.get(hotel_id)
    if not hotel:
        return jsonify({'error': 'الفندق المحدد غير موجود'}), 400

    # تحقق من عدم التكرار
    existing = Academy.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'هذه الأكاديمية موجودة بالفعل'}), 400

    academy = Academy(name=name, hotel_id=hotel_id)
    db.session.add(academy)
    db.session.commit()

    return jsonify({
        'message': 'تمت إضافة الأكاديمية بنجاح',
        'academy': academy.to_dict(),
        'redirect_url': f'/academy/{academy.id}'
    }), 201


@academies_bp.route('/api/academies/<int:id>', methods=['PUT'])
def api_update_academy(id):
    """API: تعديل أكاديمية"""
    academy = Academy.query.get_or_404(id)
    data = request.get_json()

    name = data.get('name', '').strip()
    hotel_id = data.get('hotel_id')

    if not name or not hotel_id:
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400

    # تحقق من وجود الفندق
    hotel = Hotel.query.get(hotel_id)
    if not hotel:
        return jsonify({'error': 'الفندق المحدد غير موجود'}), 400

    academy.name = name
    academy.hotel_id = hotel_id
    db.session.commit()

    return jsonify({'message': 'تم تحديث الأكاديمية بنجاح', 'academy': academy.to_dict()})


@academies_bp.route('/api/academies/<int:id>', methods=['DELETE'])
def api_delete_academy(id):
    """API: حذف أكاديمية"""
    academy = Academy.query.get_or_404(id)
    db.session.delete(academy)
    db.session.commit()
    return jsonify({'message': 'تم حذف الأكاديمية بنجاح'})


# ─── صفحة تفاصيل الأكاديمية ───

@academies_bp.route('/academy/<int:id>')
def academy_detail(id):
    """صفحة تفاصيل الأكاديمية وفرقها"""
    academy = Academy.query.get_or_404(id)
    teams = Team.query.filter_by(academy_id=id).all()
    vehicles = Vehicle.query.filter_by(academy_id=id).all()

    # تنظيم الفرق حسب الجنس والفئة
    teams_map = {}
    for team in teams:
        teams_map[(team.gender, team.category)] = team

    return render_template('academy_detail.html',
                           academy=academy,
                           teams=teams,
                           teams_map=teams_map,
                           vehicles=vehicles,
                           genders=Team.GENDER_CHOICES,
                           categories=Team.CATEGORY_CHOICES,
                           category_labels=Team.CATEGORY_LABELS)


# ─── API: إدارة الفرق ───

@academies_bp.route('/api/teams', methods=['POST'])
def api_create_team():
    """API: إضافة فريق"""
    data = request.get_json()
    academy_id = data.get('academy_id')
    gender = data.get('gender')
    category = data.get('category')

    if not all([academy_id, gender, category]):
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400

    # التحقق من عدم وجود فريق مكرر
    existing = Team.query.filter_by(
        academy_id=academy_id, gender=gender, category=category
    ).first()
    if existing:
        return jsonify({'error': 'هذا الفريق موجود بالفعل'}), 400

    team = Team(
        academy_id=academy_id,
        gender=gender,
        category=category,
        day1_status='active',
        day2_status='active'
    )
    db.session.add(team)
    db.session.commit()

    return jsonify({'message': 'تمت إضافة الفريق بنجاح', 'team': team.to_dict()}), 201


@academies_bp.route('/api/teams/<int:id>/toggle', methods=['POST'])
def api_toggle_team_status(id):
    """API: تبديل حالة الفريق"""
    team = Team.query.get_or_404(id)
    data = request.get_json()
    day = data.get('day')

    if day not in [1, 2]:
        return jsonify({'error': 'يوم غير صالح'}), 400

    if day == 1:
        team.day1_status = 'eliminated' if team.day1_status == 'active' else 'active'
    else:
        team.day2_status = 'eliminated' if team.day2_status == 'active' else 'active'

    db.session.commit()
    return jsonify({'message': 'تم تحديث حالة الفريق', 'team': team.to_dict()})


@academies_bp.route('/api/teams/<int:id>', methods=['DELETE'])
def api_delete_team(id):
    """API: حذف فريق"""
    team = Team.query.get_or_404(id)
    db.session.delete(team)
    db.session.commit()
    return jsonify({'message': 'تم حذف الفريق بنجاح'})
