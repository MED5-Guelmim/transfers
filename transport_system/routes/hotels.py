from flask import Blueprint, render_template, request, jsonify
from models import db, Hotel

hotels_bp = Blueprint('hotels', __name__)


@hotels_bp.route('/hotels')
def hotels_list():
    """صفحة إدارة الفنادق"""
    hotels = Hotel.query.order_by(Hotel.name).all()
    return render_template('hotels.html', hotels=hotels)


@hotels_bp.route('/api/hotels', methods=['GET'])
def api_get_hotels():
    """API: الحصول على كل الفنادق"""
    hotels = Hotel.query.order_by(Hotel.name).all()
    return jsonify([h.to_dict() for h in hotels])


@hotels_bp.route('/api/hotels', methods=['POST'])
def api_create_hotel():
    """API: إضافة فندق جديد"""
    data = request.get_json()
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()

    if not name:
        return jsonify({'error': 'اسم الفندق مطلوب'}), 400

    # تحقق من عدم التكرار
    existing = Hotel.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'هذا الفندق موجود بالفعل'}), 400

    hotel = Hotel(name=name, address=address or None)
    db.session.add(hotel)
    db.session.commit()

    return jsonify({
        'message': 'تمت إضافة الفندق بنجاح',
        'hotel': hotel.to_dict()
    }), 201


@hotels_bp.route('/api/hotels/<int:id>', methods=['PUT'])
def api_update_hotel(id):
    """API: تعديل فندق"""
    hotel = Hotel.query.get_or_404(id)
    data = request.get_json()

    name = data.get('name', '').strip()
    address = data.get('address', '').strip()

    if not name:
        return jsonify({'error': 'اسم الفندق مطلوب'}), 400

    # تحقق من عدم التكرار (مع استثناء الفندق الحالي)
    existing = Hotel.query.filter(Hotel.name == name, Hotel.id != id).first()
    if existing:
        return jsonify({'error': 'يوجد فندق آخر بنفس الاسم'}), 400

    hotel.name = name
    hotel.address = address or None
    db.session.commit()

    return jsonify({'message': 'تم تحديث الفندق بنجاح', 'hotel': hotel.to_dict()})


@hotels_bp.route('/api/hotels/<int:id>', methods=['DELETE'])
def api_delete_hotel(id):
    """API: حذف فندق"""
    hotel = Hotel.query.get_or_404(id)

    # التحقق من عدم وجود أكاديميات مرتبطة
    if hotel.academies:
        return jsonify({
            'error': f'لا يمكن حذف الفندق لأنه مرتبط بـ {len(hotel.academies)} أكاديمية'
        }), 400

    db.session.delete(hotel)
    db.session.commit()
    return jsonify({'message': 'تم حذف الفندق بنجاح'})
