from functools import wraps
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, User

users_bp = Blueprint('users', __name__)


def admin_required(f):
    """Decorator: يسمح فقط للمدير"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'ليس لديك صلاحية للوصول'}), 403
        return f(*args, **kwargs)
    return decorated_function


@users_bp.route('/users')
@login_required
def users_list():
    """صفحة إدارة المستخدمين — admin فقط"""
    if not current_user.is_admin:
        return jsonify({'error': 'ليس لديك صلاحية'}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)


@users_bp.route('/api/users', methods=['GET'])
@admin_required
def api_get_users():
    """API: قائمة المستخدمين (مع كلمات المرور للمدير)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict(include_password=True) for u in users])


@users_bp.route('/api/users', methods=['POST'])
@admin_required
def api_create_user():
    """API: إضافة مستخدم جديد"""
    data = request.get_json()
    username = data.get('username', '').strip()
    display_name = data.get('display_name', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')

    if not username or not display_name or not password:
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400

    if len(password) < 4:
        return jsonify({'error': 'كلمة المرور قصيرة جداً (4 أحرف على الأقل)'}), 400

    if role not in ['admin', 'user']:
        return jsonify({'error': 'الدور غير صالح'}), 400

    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({'error': 'اسم المستخدم مستخدم بالفعل'}), 400

    user = User(
        username=username,
        display_name=display_name,
        role=role
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'تم إضافة المستخدم بنجاح',
        'user': user.to_dict(include_password=True)
    }), 201


@users_bp.route('/api/users/<int:id>', methods=['PUT'])
@admin_required
def api_update_user(id):
    """API: تعديل مستخدم"""
    user = User.query.get_or_404(id)
    data = request.get_json()

    display_name = data.get('display_name', '').strip()
    role = data.get('role', user.role)
    new_password = data.get('password', '').strip()

    if not display_name:
        return jsonify({'error': 'الاسم المعروض مطلوب'}), 400

    if role not in ['admin', 'user']:
        return jsonify({'error': 'الدور غير صالح'}), 400

    user.display_name = display_name
    user.role = role

    if new_password:
        if len(new_password) < 4:
            return jsonify({'error': 'كلمة المرور قصيرة جداً (4 أحرف على الأقل)'}), 400
        user.set_password(new_password)

    db.session.commit()

    return jsonify({
        'message': 'تم تحديث المستخدم بنجاح',
        'user': user.to_dict(include_password=True)
    })


@users_bp.route('/api/users/<int:id>', methods=['DELETE'])
@admin_required
def api_delete_user(id):
    """API: حذف مستخدم"""
    user = User.query.get_or_404(id)

    # لا يمكن حذف نفسك
    if user.id == current_user.id:
        return jsonify({'error': 'لا يمكنك حذف حسابك الخاص'}), 400

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'تم حذف المستخدم بنجاح'})


@users_bp.route('/api/users/<int:id>/toggle', methods=['POST'])
@admin_required
def api_toggle_user(id):
    """API: تفعيل/تعطيل مستخدم"""
    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        return jsonify({'error': 'لا يمكنك تعطيل حسابك الخاص'}), 400

    user.is_active_user = not user.is_active_user
    db.session.commit()

    status = 'مفعّل' if user.is_active_user else 'معطّل'
    return jsonify({
        'message': f'تم تغيير حالة المستخدم إلى {status}',
        'user': user.to_dict(include_password=True)
    })
