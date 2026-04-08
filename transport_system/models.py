from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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

# جدول وسيط بين الرحلة والفريق (Many-to-Many)
trip_teams = db.Table(
    'trip_teams',
    db.Column('trip_id', db.Integer, db.ForeignKey('trip.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)


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
    STATUS_CHOICES = ['active', 'eliminated']

    id = db.Column(db.Integer, primary_key=True)
    academy_id = db.Column(db.Integer, db.ForeignKey('academy.id'), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    day1_status = db.Column(db.String(15), nullable=False, default='active')
    day2_status = db.Column(db.String(15), nullable=False, default='active')

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
            'display_name': self.display_name,
            'day1_status': self.day1_status,
            'day2_status': self.day2_status
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

    # العلاقة Many-to-Many مع الفرق
    teams = db.relationship('Team', secondary=trip_teams, lazy='subquery',
                            backref=db.backref('trips', lazy=True))

    def __repr__(self):
        return f'<Trip {self.vehicle.name} - Day{self.day} - {self.direction}>'

    @property
    def direction_label(self):
        return self.DIRECTION_LABELS.get(self.direction, self.direction)

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'vehicle_name': self.vehicle.name if self.vehicle else '',
            'day': self.day,
            'direction': self.direction,
            'direction_label': self.direction_label,
            'trip_order': self.trip_order,
            'teams': [t.to_dict() for t in self.teams]
        }
