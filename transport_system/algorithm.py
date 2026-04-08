"""
خوارزمية توزيع النقل اللوجستي المحسنة
================================
المبادئ الأساسية:
1. الأولوية القصوى: كل أكاديمية تستخدم عربتها الخاصة لفرقها أولاً.
2. أولوية الفندق: عند ملء الفراغات، فرق نفس الفندق لها الأولوية.
3. منطق الفصل: محاولة وضع الذكور مع الذكور والإناث مع الإناث قدر الإمكان عند دمج الفرق.
4. العربات العامة: تحمل فرق من نفس الفندق قدر الإمكان.
5. ملء الفراغات: استغلال السعة المتبقية في العربات الخاصة ثم العامة.
6. الرحلات الإضافية: في حال وجود فائض، يتم إنشاء رحلات ثانية مع أولوية العربات العامة.
"""

from collections import defaultdict
from models import db, Team, Vehicle, Trip, trip_teams, Academy


def get_active_teams(day):
    """جلب الفرق المشاركة بناءً على حالة النشاط في اليوم المحدد"""
    if day == 1:
        return Team.query.filter_by(day1_status='active').all()
    else:
        return Team.query.filter_by(day2_status='active').all()


def _get_team_hotel_id(team):
    """الحصول على hotel_id الخاص بفريق عبر أكاديميته"""
    if team.academy:
        return team.academy.hotel_id
    return None


def _pick_teams_by_hotel(teams_pool, hotel_id, cap, gender_hint=None):
    """
    اختيار فرق من نفس الفندق مع مراعاة الجنس
    - hotel_id: الفندق المستهدف
    - cap: الحد الأقصى للفرق
    - gender_hint: الجنس المفضل (اختياري)
    """
    selected = []

    if hotel_id:
        # أولاً: فرق من نفس الفندق ونفس الجنس
        if gender_hint:
            same_hotel_same_gender = [
                t for t in teams_pool
                if _get_team_hotel_id(t) == hotel_id and t.gender == gender_hint
            ]
            selected.extend(same_hotel_same_gender[:cap])

        # ثانياً: فرق من نفس الفندق (أي جنس) إذا بقيت سعة
        if len(selected) < cap:
            remaining = cap - len(selected)
            same_hotel = [
                t for t in teams_pool
                if _get_team_hotel_id(t) == hotel_id and t not in selected
            ]
            selected.extend(same_hotel[:remaining])

    # ثالثاً: إذا لم تمتلئ، فرق من نفس الجنس من أي فندق
    if len(selected) < cap and gender_hint:
        remaining = cap - len(selected)
        same_gender = [
            t for t in teams_pool
            if t.gender == gender_hint and t not in selected
        ]
        selected.extend(same_gender[:remaining])

    # أخيراً: أي فرق متاحة لملء الباقي
    if len(selected) < cap:
        remaining = cap - len(selected)
        others = [t for t in teams_pool if t not in selected]
        selected.extend(others[:remaining])

    return selected


def generate_distribution(day):
    """
    توليد توزيع النقل بناءً على القواعد الذكية المحددة
    """
    # 1. تنظيف التوزيعات السابقة لتجنب التكرار
    old_trips = Trip.query.filter_by(day=day).all()
    for trip in old_trips:
        trip.teams = []
        db.session.delete(trip)
    db.session.commit()

    # 2. تحضير البيانات
    active_teams = get_active_teams(day)
    if not active_teams:
        return {'message': 'لا توجد فرق نشطة لهذا اليوم', 'vehicles': {}}

    all_vehicles = Vehicle.query.all()
    private_vehicles = [v for v in all_vehicles if v.ownership == 'academy']
    public_vehicles = [v for v in all_vehicles if v.ownership == 'public']

    capacity_map = {'small': 2, 'large': 5}
    teams_needing_go = list(active_teams)
    go_distribution = defaultdict(list)

    # ═══════════════════════════════════════
    # الخطوة 1: الأولوية للأكاديمية (رحلة أولى خاصة)
    # ═══════════════════════════════════════
    for v in private_vehicles:
        if not teams_needing_go:
            break

        cap = capacity_map.get(v.type, 2)
        # جلب الفرق التي تنتمي لنفس أكاديمية العربة
        my_teams = [t for t in teams_needing_go if t.academy_id == v.academy_id]

        selected = my_teams[:cap]
        if selected:
            go_distribution[v.id].append(selected)
            for t in selected:
                teams_needing_go.remove(t)

    # ═══════════════════════════════════════
    # الخطوة 2: ملء الفراغات في العربات الخاصة مع أولوية نفس الفندق
    # ═══════════════════════════════════════
    for v in private_vehicles:
        if not teams_needing_go:
            break

        cap = capacity_map.get(v.type, 2)

        # إذا لم تحصل العربة على رحلة في الخطوة 1، ننشئ لها مكاناً فارغاً
        if not go_distribution[v.id]:
            go_distribution[v.id].append([])

        current_trip = go_distribution[v.id][0]

        if len(current_trip) < cap:
            needed = cap - len(current_trip)

            # تحديد الجنس والفندق الموجود حالياً في العربة
            target_gender = current_trip[0].gender if current_trip else None
            # الحصول على فندق أكاديمية العربة
            vehicle_hotel_id = None
            if v.academy:
                vehicle_hotel_id = v.academy.hotel_id

            # اختيار فرق مع أولوية نفس الفندق
            fillers = _pick_teams_by_hotel(
                teams_needing_go, vehicle_hotel_id, needed, target_gender
            )

            current_trip.extend(fillers)
            for t in fillers:
                teams_needing_go.remove(t)

        # تنظيف الرحلات التي بقيت فارغة تماماً
        if not go_distribution[v.id][0]:
            go_distribution[v.id].pop(0)

    # ═══════════════════════════════════════
    # الخطوة 3: العربات العامة - تجميع حسب الفندق
    # ═══════════════════════════════════════
    for v in public_vehicles:
        if not teams_needing_go:
            break

        cap = capacity_map.get(v.type, 2)

        # نختار أول فريق ونستخدم فندقه كأساس للتجميع
        first_team = teams_needing_go[0]
        target_hotel_id = _get_team_hotel_id(first_team)
        target_gender = first_team.gender

        # اختيار فرق من نفس الفندق مع مراعاة الجنس
        trip_teams_list = _pick_teams_by_hotel(
            teams_needing_go, target_hotel_id, cap, target_gender
        )

        if trip_teams_list:
            go_distribution[v.id].append(trip_teams_list)
            for t in trip_teams_list:
                teams_needing_go.remove(t)

    # ═══════════════════════════════════════
    # الخطوة 4: الرحلات الإضافية (Round 2+)
    # ═══════════════════════════════════════
    while teams_needing_go:
        made_progress = False

        # الأولوية للعربات العامة في الرحلات الإضافية لتخفيف العبء عن الأكاديميات
        all_avail_vehicles = public_vehicles + private_vehicles

        for v in all_avail_vehicles:
            if not teams_needing_go:
                break

            if v.can_return:  # العربة قادرة على القيام برحلة ثانية
                cap = capacity_map.get(v.type, 2)

                # اختيار الفرق مع أولوية الفندق والجنس
                first_team = teams_needing_go[0]
                target_hotel_id = _get_team_hotel_id(first_team)
                target_gender = first_team.gender

                trip_batch = _pick_teams_by_hotel(
                    teams_needing_go, target_hotel_id, cap, target_gender
                )

                if trip_batch:
                    go_distribution[v.id].append(trip_batch)
                    for t in trip_batch:
                        teams_needing_go.remove(t)
                    made_progress = True

        if not made_progress:
            break  # لا توجد عربات متاحة لمزيد من الرحلات

    # ═══════════════════════════════════════
    # حفظ النتائج في قاعدة البيانات
    # ═══════════════════════════════════════
    final_result = {}

    for v_id, batches in go_distribution.items():
        vehicle = Vehicle.query.get(v_id)
        current_trips = []
        order_counter = 1

        # إنشاء رحلات الذهاب
        for batch in batches:
            new_trip = Trip(vehicle_id=v_id, day=day, direction='go', trip_order=order_counter)
            db.session.add(new_trip)
            db.session.flush()
            new_trip.teams = batch
            current_trips.append(new_trip)
            order_counter += 1

        # إنشاء رحلات الإياب (نفس الفرق، ترتيب معاكس أو متوازي)
        if vehicle.can_return:
            for batch in batches:
                new_trip = Trip(vehicle_id=v_id, day=day, direction='return', trip_order=order_counter)
                db.session.add(new_trip)
                db.session.flush()
                new_trip.teams = batch
                current_trips.append(new_trip)
                order_counter += 1

        final_result[v_id] = {
            'vehicle': vehicle.to_dict(),
            'trips': [t.to_dict() for t in current_trips]
        }

    db.session.commit()

    unassigned = len(teams_needing_go)
    msg = f"تم توزيع {len(active_teams) - unassigned} فريق."
    if unassigned > 0:
        msg += f" تنبيه: {unassigned} فريق لم يجدوا مكاناً."

    return {'message': msg, 'vehicles': final_result}


def get_distribution(day):
    """استرجاع التوزيع المخزن مسبقاً لعرضه"""
    trips = Trip.query.filter_by(day=day).order_by(Trip.vehicle_id, Trip.trip_order).all()
    if not trips:
        return {'message': 'لا يوجد توزيع حالي', 'vehicles': {}}

    result = {}
    for trip in trips:
        v_id = trip.vehicle_id
        if v_id not in result:
            result[v_id] = {'vehicle': trip.vehicle.to_dict(), 'trips': []}
        result[v_id]['trips'].append(trip.to_dict())

    return {'message': 'تم تحميل التوزيع', 'vehicles': result}