"""
خوارزمية توزيع النقل اللوجستي
================================
توزع الفرق النشطة على وسائل النقل المتاحة مع مراعاة:
1. أولوية النقل الخاص (عربات الأكاديمية لفرقها أولاً)
2. توزيع الفائض على العربات العامة والخاصة ذات السعة المتبقية
3. جميع الفرق يجب أن تذهب أولاً، ثم الإياب بعد ذلك
4. لا يجب أن يبقى أي فريق بدون نقل
"""

from collections import defaultdict
from models import db, Team, Vehicle, Trip, trip_teams, Academy


def get_active_teams(day):
    """الحصول على الفرق النشطة في يوم معين"""
    if day == 1:
        return Team.query.filter_by(day1_status='active').all()
    else:
        return Team.query.filter_by(day2_status='active').all()


def group_teams_by_academy(teams):
    """تجميع الفرق حسب الأكاديمية"""
    academy_teams = defaultdict(list)
    for team in teams:
        academy_teams[team.academy_id].append(team)
    return academy_teams


def generate_distribution(day):
    """
    الخوارزمية الرئيسية لتوزيع النقل
    
    المبدأ:
    - المرحلة 1: كل الفرق تذهب (رحلات الذهاب)
    - المرحلة 2: كل الفرق تعود (رحلات الإياب)
    - العربات يمكنها القيام برحلات متعددة (ذهاب، عودة، ذهاب مرة ثانية...)
    - لا فريق يبقى بدون نقل
    """
    # حذف التوزيع السابق لهذا اليوم
    old_trips = Trip.query.filter_by(day=day).all()
    for trip in old_trips:
        trip.teams = []
        db.session.delete(trip)
    db.session.commit()

    # الخطوة 1: جمع الفرق النشطة
    active_teams = get_active_teams(day)
    if not active_teams:
        return {'message': 'لا توجد فرق نشطة في هذا اليوم', 'vehicles': {}}

    # الخطوة 2: تجميع حسب الأكاديمية
    academy_teams = group_teams_by_academy(active_teams)

    # الخطوة 3: تحضير العربات
    all_vehicles = Vehicle.query.all()
    private_vehicles = [v for v in all_vehicles if v.ownership == 'academy']
    public_vehicles = [v for v in all_vehicles if v.ownership == 'public']

    capacity_map = {'small': 2, 'large': 5}

    # ═══════════════════════════════════════
    # المرحلة الأولى: توزيع رحلات الذهاب
    # ═══════════════════════════════════════
    
    # قائمة كل الفرق التي تحتاج نقل (ذهاب)
    teams_needing_go = list(active_teams)
    
    # هيكل لتخزين التوزيع: {vehicle_id: [[teams_trip1], [teams_trip2], ...]}
    go_distribution = defaultdict(list)

    # الخطوة 3أ: توزيع النقل الخاص أولاً
    for v in private_vehicles:
        if not teams_needing_go:
            break
        academy_id = v.academy_id
        # فرق هذه الأكاديمية التي لم تُنقل بعد
        my_teams = [t for t in teams_needing_go if t.academy_id == academy_id]
        cap = capacity_map.get(v.type, 2)

        # الرحلة الأولى: فرق الأكاديمية أولاً
        trip_teams_list = my_teams[:cap]
        # إذا بقيت سعة، أضف فرق أخرى
        remaining_cap = cap - len(trip_teams_list)
        if remaining_cap > 0:
            others = [t for t in teams_needing_go if t not in trip_teams_list]
            trip_teams_list.extend(others[:remaining_cap])

        if trip_teams_list:
            go_distribution[v.id].append(trip_teams_list)
            for t in trip_teams_list:
                if t in teams_needing_go:
                    teams_needing_go.remove(t)

    # الخطوة 3ب: توزيع على العربات العامة
    for v in public_vehicles:
        if not teams_needing_go:
            break
        cap = capacity_map.get(v.type, 2)
        trip_teams_list = teams_needing_go[:cap]
        if trip_teams_list:
            go_distribution[v.id].append(trip_teams_list)
            for t in trip_teams_list:
                teams_needing_go.remove(t)

    # الخطوة 3ج: إذا بقيت فرق - رحلات إضافية (العربات تعود وتذهب مرة أخرى)
    round_number = 1
    while teams_needing_go:
        round_number += 1
        made_progress = False
        
        # كل العربات التي تستطيع العودة يمكنها القيام برحلة ذهاب إضافية
        for v in all_vehicles:
            if not teams_needing_go:
                break
            if not v.can_return:
                continue
            cap = capacity_map.get(v.type, 2)
            trip_teams_list = teams_needing_go[:cap]
            if trip_teams_list:
                go_distribution[v.id].append(trip_teams_list)
                for t in trip_teams_list:
                    teams_needing_go.remove(t)
                made_progress = True

        if not made_progress:
            break  # لا يمكننا نقل المزيد (لا عربات متاحة)

    # ═══════════════════════════════════════
    # المرحلة الثانية: توليد الرحلات
    # ═══════════════════════════════════════
    # المنطق: لكل عربة:
    #   - رحلة ذهاب 1 (order=1)
    #   - رحلة ذهاب 2 إن وجدت (order=2)
    #   - ...
    #   - ثم رحلات الإياب بنفس الترتيب

    result = {}
    trip_order_global = 1

    for v_id, trip_batches in go_distribution.items():
        vehicle = Vehicle.query.get(v_id)
        trips_list = []
        trip_order = 1

        # إنشاء رحلات الذهاب
        for batch in trip_batches:
            go_trip = Trip(
                vehicle_id=v_id,
                day=day,
                direction='go',
                trip_order=trip_order
            )
            db.session.add(go_trip)
            db.session.flush()
            go_trip.teams = batch
            trips_list.append(go_trip)
            trip_order += 1

        # إنشاء رحلات الإياب (بنفس الترتيب) إذا كانت العربة تستطيع
        if vehicle.can_return:
            for batch in trip_batches:
                return_trip = Trip(
                    vehicle_id=v_id,
                    day=day,
                    direction='return',
                    trip_order=trip_order
                )
                db.session.add(return_trip)
                db.session.flush()
                return_trip.teams = batch
                trips_list.append(return_trip)
                trip_order += 1

        result[v_id] = {
            'vehicle': vehicle.to_dict(),
            'trips': [t.to_dict() for t in trips_list]
        }

    db.session.commit()

    unassigned_count = len(teams_needing_go)
    total_transported = len(active_teams) - unassigned_count

    message = f'تم توزيع {total_transported} فريق على {len(result)} عربة'
    if unassigned_count > 0:
        message += f' — تنبيه: {unassigned_count} فريق لم يتم نقلهم (سعة غير كافية)'

    return {
        'message': message,
        'vehicles': result,
        'unassigned_count': unassigned_count
    }


def get_distribution(day):
    """الحصول على التوزيع الحالي لليوم المحدد"""
    trips = Trip.query.filter_by(day=day).order_by(Trip.vehicle_id, Trip.trip_order).all()

    if not trips:
        return {'message': 'لا يوجد توزيع لهذا اليوم', 'vehicles': {}}

    result = {}
    for trip in trips:
        v_id = trip.vehicle_id
        if v_id not in result:
            result[v_id] = {
                'vehicle': trip.vehicle.to_dict(),
                'trips': []
            }
        result[v_id]['trips'].append(trip.to_dict())

    return {
        'message': f'التوزيع الحالي: {len(result)} عربة',
        'vehicles': result
    }
