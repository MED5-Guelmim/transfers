from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """نموذج المستخدم"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    plain_password = db.Column(db.String(120), nullable=True)  # للعرض من طرف المدير فقط
    role = db.Column(db.String(20), nullable=False, default='user')  # admin / user
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plain_password = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return self.is_active_user

    @property
    def role_label(self):
        return 'مدير' if self.role == 'admin' else 'مستخدم'

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self, include_password=False):
        data = {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'role_label': self.role_label,
            'is_active': self.is_active_user,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
        if include_password:
            data['plain_password'] = self.plain_password or '***'
        return data


class Hotel(db.Model):
    """نموذج الفندق"""
    __tablename__ = 'hotel'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    address = db.Column(db.String(300), nullable=True)

    # العلاقة مع الأكاديميات
    academies = db.relationship('Academy', backref='hotel_ref', lazy=True)

    def __repr__(self):
        return f'<Hotel {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address or '',
            'academies_count': len(self.academies)
        }


# ═══════════════════════════════════════
# جدول وسيط: المباراة ↔ الفريق (Many-to-Many)
# ═══════════════════════════════════════
match_teams = db.Table(
    'match_teams',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

# جدول وسيط بين الرحلة والفريق (Many-to-Many)
trip_teams = db.Table(
    'trip_teams',
    db.Column('trip_id', db.Integer, db.ForeignKey('trip.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)


class Match(db.Model):
    """نموذج المباراة"""
    __tablename__ = 'match'

    PERIOD_CHOICES = ['morning', 'evening']
    PERIOD_LABELS = {'morning': 'صباحاً', 'evening': 'مساءً'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)           # "مباراة 1", "مباراة 2"
    day = db.Column(db.Integer, nullable=False)                  # 1 أو 2
    period = db.Column(db.String(10), nullable=False)            # 'morning' أو 'evening'
    match_order = db.Column(db.Integer, nullable=False)          # ترتيب المباراة في اليوم
    time_label = db.Column(db.String(50), nullable=True)         # "09:00" - يظهر في التوزيع

    # العلاقة مع الفرق
    teams = db.relationship('Team', secondary=match_teams, lazy='subquery',
                            backref=db.backref('matches', lazy=True))

    # العلاقة مع الرحلات
    trips = db.relationship('Trip', backref='match', lazy=True)

    def __repr__(self):
        return f'<Match {self.name} - Day{self.day}>'

    @property
    def period_label(self):
        return self.PERIOD_LABELS.get(self.period, self.period)

    @property
    def display_time(self):
        """الوقت المعروض: الساعة إن وُجدت أو الفترة"""
        if self.time_label:
            return self.time_label
        return self.period_label

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'day': self.day,
            'period': self.period,
            'period_label': self.period_label,
            'match_order': self.match_order,
            'time_label': self.time_label or '',
            'display_time': self.display_time,
            'teams_count': len(self.teams),
            'teams': [t.to_dict() for t in self.teams]
        }


class Academy(db.Model):
    """نموذج الأكاديمية"""
    __tablename__ = 'academy'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=True)

    # العلاقات
    teams = db.relationship('Team', backref='academy', lazy=True, cascade='all, delete-orphan')
    vehicles = db.relationship('Vehicle', backref='academy', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Academy {self.name}>'

    @property
    def hotel_name(self):
        return self.hotel_ref.name if self.hotel_ref else '—'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'hotel_id': self.hotel_id,
            'hotel': self.hotel_name,
            'teams_count': len(self.teams),
            'vehicles_count': len([v for v in self.vehicles])
        }


class Team(db.Model):
    """نموذج الفريق"""
    __tablename__ = 'team'

    GENDER_CHOICES = ['ذكور', 'إناث']
    CATEGORY_CHOICES = ['U18', 'U15', 'U18_sport_study', 'U15_sport_study']
    CATEGORY_LABELS = {
        'U18': 'أقل من 18 غير منتمي',
        'U15': 'أقل من 15 غير منتمي',
        'U18_sport_study': 'أقل من 18 رياضة ودراسة',
        'U15_sport_study': 'أقل من 15 رياضة ودراسة'
    }

    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(30), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('academy_id', 'gender', 'category', name='uq_team_academy_gender_category'),
    )

    def __repr__(self):
        return f'<Team {self.academy.name} - {self.gender} {self.category}>'

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category)

    @property
    def display_name(self):
        return f'{self.gender} - {self.category_label}'

    def to_dict(self):
        return {
            'id': self.id,
            'academy_id': self.academy_id,
            'academy_name': self.academy.name if self.academy else '',
            'gender': self.gender,
            'category': self.category,
            'category_label': self.category_label,
            'display_name': self.display_name
        }


class Vehicle(db.Model):
    """نموذج وسيلة النقل"""
    __tablename__ = 'vehicle'

    TYPE_CHOICES = ['small', 'large']
    TYPE_LABELS = {'small': 'صغيرة (فريقان)', 'large': 'كبيرة (5 فرق)'}
    TYPE_CAPACITY = {'small': 2, 'large': 5}
    OWNERSHIP_CHOICES = ['academy', 'public']
    OWNERSHIP_LABELS = {'academy': 'خاصة بأكاديمية', 'public': 'عامة'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(10), nullable=False, default='small')
    ownership = db.Column(db.String(10), nullable=False, default='public')
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=True)
    can_return = db.Column(db.Boolean, nullable=False, default=True)

    # العلاقات
    trips = db.relationship('Trip', backref='vehicle', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Vehicle {self.name}>'

    @property
    def capacity(self):
        return self.TYPE_CAPACITY.get(self.type, 2)

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.type, self.type)

    @property
    def ownership_label(self):
        return self.OWNERSHIP_LABELS.get(self.ownership, self.ownership)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'type_label': self.type_label,
            'capacity': self.capacity,
            'ownership': self.ownership,
            'ownership_label': self.ownership_label,
            'academy_id': self.academy_id,
            'academy_name': self.academy.name if self.academy else '',
            'can_return': self.can_return
        }


class Trip(db.Model):
    """نموذج الرحلة"""
    __tablename__ = 'trip'

    DIRECTION_CHOICES = ['go', 'return']
    DIRECTION_LABELS = {'go': 'ذهاب', 'return': 'إياب'}

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    trip_order = db.Column(db.Integer, nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)

    # العلاقة Many-to-Many مع الفرق
    teams = db.relationship('Team', secondary=trip_teams, lazy='subquery',
                            backref=db.backref('trips', lazy=True))

    def __repr__(self):
        return f'<Trip {self.vehicle.name} - Day{self.day} - {self.direction}>'

    @property
    def direction_label(self):
        return self.DIRECTION_LABELS.get(self.direction, self.direction)

    @property
    def time_display(self):
        """وقت الرحلة من المباراة المرتبطة"""
        if self.match:
            return self.match.display_time
        return ''

    @property
    def match_name(self):
        """اسم المباراة المرتبطة"""
        if self.match:
            return self.match.name
        return ''

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'vehicle_name': self.vehicle.name if self.vehicle else '',
            'day': self.day,
            'direction': self.direction,
            'direction_label': self.direction_label,
            'trip_order': self.trip_order,
            'match_id': self.match_id,
            'match_name': self.match_name,
            'time_display': self.time_display,
            'teams': [t.to_dict() for t in self.teams]
        }
