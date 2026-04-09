"""
خوارزمية توزيع النقل اللوجستي — نسخة المباريات
================================
المبادئ الأساسية:
1. التوزيع يتم حسب المباريات مرتبة بالترتيب (match_order).
2. فرق المباراة الأولى تُنقل أولاً، ثم فرق المباراة الثانية، وهكذا.
3. الأولوية القصوى: كل أكاديمية تستخدم عربتها الخاصة لفرقها أولاً.
4. أولوية الفندق: عند ملء الفراغات، فرق نفس الفندق لها الأولوية.
5. منطق الفصل: محاولة وضع الذكور مع الذكور والإناث مع الإناث.
6. العربات العامة: تحمل فرق من نفس الفندق قدر الإمكان.
7. الرحلات تحمل وقت المباراة بدل رقم تسلسلي.
"""

from collections import defaultdict
from models import db, Team, Vehicle, Trip, trip_teams, Academy, Match


def get_teams_for_match(match):
    """جلب الفرق المعينة لمباراة معينة"""
    return list(match.teams)


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


def _distribute_teams_for_match(match, teams_needing_transport, private_vehicles, public_vehicles, capacity_map):
    """
    توزيع فرق مباراة واحدة على العربات المتاحة.
    يعيد قائمة من (vehicle_id, [teams]) لرحلات الذهاب.
    """
    go_batches = []  # [(vehicle_id, [teams])]

    if not teams_needing_transport:
        return go_batches

    teams_pool = list(teams_needing_transport)

    # ═══════════ الخطوة 1: عربات خاصة — فرق أكاديميتها أولاً ═══════════
    for v in private_vehicles:
        if not teams_pool:
            break
        cap = capacity_map.get(v.type, 2)
        my_teams = [t for t in teams_pool if t.academy_id == v.academy_id]
        selected = my_teams[:cap]
        if selected:
            go_batches.append((v.id, selected))
            for t in selected:
                teams_pool.remove(t)

    # ═══════════ الخطوة 2: ملء الفراغات في العربات الخاصة ═══════════
    for i, (v_id, batch) in enumerate(go_batches):
        if not teams_pool:
            break
        v = Vehicle.query.get(v_id)
        cap = capacity_map.get(v.type, 2)
        if len(batch) < cap:
            needed = cap - len(batch)
            target_gender = batch[0].gender if batch else None
            vehicle_hotel_id = v.academy.hotel_id if v.academy else None
            fillers = _pick_teams_by_hotel(teams_pool, vehicle_hotel_id, needed, target_gender)
            batch.extend(fillers)
            for t in fillers:
                teams_pool.remove(t)

    # ═══════════ الخطوة 3: عربات عامة ═══════════
    for v in public_vehicles:
        if not teams_pool:
            break
        cap = capacity_map.get(v.type, 2)
        first_team = teams_pool[0]
        target_hotel_id = _get_team_hotel_id(first_team)
        target_gender = first_team.gender
        trip_batch = _pick_teams_by_hotel(teams_pool, target_hotel_id, cap, target_gender)
        if trip_batch:
            go_batches.append((v.id, trip_batch))
            for t in trip_batch:
                teams_pool.remove(t)

    # ═══════════ الخطوة 4: رحلات إضافية (عربات يمكنها العودة) ═══════════
    while teams_pool:
        made_progress = False
        all_avail = public_vehicles + private_vehicles
        for v in all_avail:
            if not teams_pool:
                break
            if v.can_return:
                cap = capacity_map.get(v.type, 2)
                first_team = teams_pool[0]
                target_hotel_id = _get_team_hotel_id(first_team)
                target_gender = first_team.gender
                trip_batch = _pick_teams_by_hotel(teams_pool, target_hotel_id, cap, target_gender)
                if trip_batch:
                    go_batches.append((v.id, trip_batch))
                    for t in trip_batch:
                        teams_pool.remove(t)
                    made_progress = True
        if not made_progress:
            break

    return go_batches


def generate_distribution(day):
    """
    توليد توزيع النقل بناءً على المباريات المرتبة.
    - المباراة الأولى → رحلاتها أولاً
    - المباراة الثانية → رحلاتها ثانياً
    - وهكذا...
    """
    # 1. تنظيف التوزيعات السابقة
    old_trips = Trip.query.filter_by(day=day).all()
    for trip in old_trips:
        trip.teams = []
        db.session.delete(trip)
    db.session.commit()

    # 2. جلب المباريات مرتبة
    matches = Match.query.filter_by(day=day).order_by(Match.match_order).all()
    if not matches:
        return {'message': 'لا توجد مباريات لهذا اليوم', 'vehicles': {}}

    # 3. تحضير العربات
    all_vehicles = Vehicle.query.all()
    private_vehicles = [v for v in all_vehicles if v.ownership == 'academy']
    public_vehicles = [v for v in all_vehicles if v.ownership == 'public']
    capacity_map = {'small': 2, 'large': 5}

    # 4. تتبع الفرق التي تم توزيعها لكل مباراة
    #    (فريق واحد يمكن أن يكون في أكثر من مباراة)
    all_trips_data = []  # [(vehicle_id, match_id, direction, [teams])]
    total_teams_distributed = 0
    total_unassigned = 0

    for match in matches:
        match_teams_list = get_teams_for_match(match)
        if not match_teams_list:
            continue

        # توزيع فرق هذه المباراة
        go_batches = _distribute_teams_for_match(
            match, match_teams_list, private_vehicles, public_vehicles, capacity_map
        )

        distributed_in_match = sum(len(batch) for _, batch in go_batches)
        unassigned_in_match = len(match_teams_list) - distributed_in_match
        total_teams_distributed += distributed_in_match
        total_unassigned += unassigned_in_match

        # رحلات الذهاب
        for v_id, batch in go_batches:
            all_trips_data.append((v_id, match.id, 'go', batch))

        # رحلات الإياب
        for v_id, batch in go_batches:
            vehicle = Vehicle.query.get(v_id)
            if vehicle.can_return:
                all_trips_data.append((v_id, match.id, 'return', batch))

    # 5. حفظ في قاعدة البيانات
    final_result = {}
    order_counter = defaultdict(int)  # عداد لكل عربة

    for v_id, match_id, direction, batch in all_trips_data:
        order_counter[v_id] += 1
        new_trip = Trip(
            vehicle_id=v_id,
            day=day,
            direction=direction,
            trip_order=order_counter[v_id],
            match_id=match_id
        )
        db.session.add(new_trip)
        db.session.flush()
        new_trip.teams = batch

        if v_id not in final_result:
            vehicle = Vehicle.query.get(v_id)
            final_result[v_id] = {'vehicle': vehicle.to_dict(), 'trips': []}
        final_result[v_id]['trips'].append(new_trip.to_dict())

    db.session.commit()

    msg = f"تم توزيع {total_teams_distributed} فريق على {len(matches)} مباراة."
    if total_unassigned > 0:
        msg += f" تنبيه: {total_unassigned} فريق لم يجدوا مكانا."

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