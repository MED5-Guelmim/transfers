from flask import Blueprint, render_template, request, jsonify
from models import db, Vehicle, Academy

vehicles_bp = Blueprint('vehicles', __name__)


@vehicles_bp.route('/vehicles')
def vehicles_list():
    """صفحة إدارة وسائل النقل"""
    vehicles = Vehicle.query.order_by(Vehicle.name).all()
    academies = Academy.query.order_by(Academy.name).all()
    return render_template('vehicles.html', vehicles=vehicles, academies=academies)


@vehicles_bp.route('/api/vehicles', methods=['GET'])
def api_get_vehicles():
    """API: الحصول على كل وسائل النقل"""
    vehicles = Vehicle.query.order_by(Vehicle.name).all()
    return jsonify([v.to_dict() for v in vehicles])


@vehicles_bp.route('/api/vehicles', methods=['POST'])
def api_create_vehicle():
    """API: إضافة وسيلة نقل جديدة"""
    data = request.get_json()
    name = data.get('name', '').strip()
    v_type = data.get('type', 'small')
    ownership = data.get('ownership', 'public')
    academy_id = data.get('academy_id')
    can_return = data.get('can_return', True)

    if not name:
        return jsonify({'error': 'اسم العربة مطلوب'}), 400

    if v_type not in ['small', 'large']:
        return jsonify({'error': 'نوع العربة غير صالح'}), 400

    if ownership == 'academy' and not academy_id:
        return jsonify({'error': 'يجب اختيار الأكاديمية للعربة الخاصة'}), 400

    if ownership == 'public':
        academy_id = None

    vehicle = Vehicle(
        name=name,
        type=v_type,
        ownership=ownership,
        academy_id=academy_id,
        can_return=can_return
    )
    db.session.add(vehicle)
    db.session.commit()

    return jsonify({'message': 'تمت إضافة العربة بنجاح', 'vehicle': vehicle.to_dict()}), 201


@vehicles_bp.route('/api/vehicles/<int:id>', methods=['PUT'])
def api_update_vehicle(id):
    """API: تعديل وسيلة نقل"""
    vehicle = Vehicle.query.get_or_404(id)
    data = request.get_json()

    name = data.get('name', '').strip()
    v_type = data.get('type', vehicle.type)
    ownership = data.get('ownership', vehicle.ownership)
    academy_id = data.get('academy_id')
    can_return = data.get('can_return', vehicle.can_return)

    if not name:
        return jsonify({'error': 'اسم العربة مطلوب'}), 400

    if ownership == 'academy' and not academy_id:
        return jsonify({'error': 'يجب اختيار الأكاديمية للعربة الخاصة'}), 400

    if ownership == 'public':
        academy_id = None

    vehicle.name = name
    vehicle.type = v_type
    vehicle.ownership = ownership
    vehicle.academy_id = academy_id
    vehicle.can_return = can_return
    db.session.commit()

    return jsonify({'message': 'تم تحديث العربة بنجاح', 'vehicle': vehicle.to_dict()})


@vehicles_bp.route('/api/vehicles/<int:id>', methods=['DELETE'])
def api_delete_vehicle(id):
    """API: حذف وسيلة نقل"""
    vehicle = Vehicle.query.get_or_404(id)
    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({'message': 'تم حذف العربة بنجاح'})
