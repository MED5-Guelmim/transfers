"""
خوارزمية توزيع النقل اللوجستي — نسخة المباريات (v4)
================================
المبادئ الأساسية:
1. التوزيع يتم حسب المباريات مرتبة بالترتيب (match_order).
2. كل مباراة لها رحلات خاصة بتوقيتها.
3. ★ قيد الفندق: جميع الفرق في نفس الرحلة يجب أن تكون من نفس الفندق.
4. ★ لا يمكن لشاحنة أن تعمل رحلتين في نفس الوقت.
5. ★ توزيع متوازن: الشاحنة الأقل رحلات لها الأولوية.
6. ★ الأولوية: العربة الخاصة بأكاديمية الفريق أولاً.
7. ★ رحلات الإياب تتبع نفس تخصيص رحلات الذهاب.
8. منطق الجنس: محاولة وضع الذكور مع الذكور والإناث مع الإناث.
"""

from collections import defaultdict
from models import db, Team, Vehicle, Trip, trip_teams, Academy, Match


def _get_team_hotel_id(team):
    """الحصول على hotel_id الخاص بفريق عبر أكاديميته"""
    if team.academy:
        return team.academy.hotel_id
    return None


def _get_time_slot(match):
    """فترة زمنية فريدة للمباراة"""
    if match.time_label:
        return f"{match.period}_{match.time_label}"
    return f"match_{match.id}"


def _group_matches_by_period(matches):
    """تجميع المباريات حسب الفترة"""
    groups = defaultdict(list)
    for match in matches:
        groups[match.period].append(match)
    for period in groups:
        groups[period].sort(key=lambda m: m.match_order)
    return groups


def generate_distribution(day):
    """
    توليد توزيع النقل — v4
    ★ الإصلاحات:
    - العربة الخاصة لا تُعطى لفرق أكاديمية أخرى عندما فرق أكاديميتها موجودة
    - رحلات الإياب تتبع نفس العربة التي ذهب بها الفريق
    - لا خلط فنادق مختلفة في نفس الرحلة
    - توزيع متوازن بين العربات
    """
    # ═══ 1. تنظيف ═══
    old_trips = Trip.query.filter_by(day=day).all()
    for trip in old_trips:
        trip.teams = []
        db.session.delete(trip)
    db.session.commit()

    # ═══ 2. جلب المباريات ═══
    matches = Match.query.filter_by(day=day).order_by(Match.match_order).all()
    if not matches:
        return {'message': 'لا توجد مباريات لهذا اليوم', 'vehicles': {}}

    # ═══ 3. تحضير العربات ═══
    all_vehicles = Vehicle.query.all()
    capacity_map = {'small': 2, 'large': 5}

    # ═══ 4. متتبعات ═══
    vehicle_trip_count = defaultdict(int)
    vehicle_busy_times = defaultdict(set)  # v_id → set of time_slot strings

    period_groups = _group_matches_by_period(matches)
    all_trips_data = []
    total_distributed = 0
    total_unassigned = 0

    for period in ['morning', 'evening']:
        if period not in period_groups:
            continue

        period_matches = period_groups[period]

        # ─── بناء خريطة الفريق ↔ المباريات ───
        team_match_map = defaultdict(list)
        team_obj_map = {}

        for match in period_matches:
            for team in match.teams:
                team_match_map[team.id].append(match)
                team_obj_map[team.id] = team

        # ─── تحديد مباراة الذهاب والإياب لكل فريق ───
        team_go_match = {}
        team_return_match = {}

        for team_id, team_matches in team_match_map.items():
            team_go_match[team_id] = team_matches[0]
            team_return_match[team_id] = team_matches[-1]

        # ═══════════════════════════════════════
        # ★ الخطوة الأولى: رحلات الذهاب
        # ═══════════════════════════════════════
        # نحفظ تخصيص فريق → عربة لاستخدامه في الإياب
        team_vehicle_assignment = {}  # team_id → vehicle_id (لربط الإياب بالذهاب)

        for match in period_matches:
            teams_for_go = [
                team_obj_map[tid] for tid, go_m in team_go_match.items()
                if go_m.id == match.id
            ]
            if not teams_for_go:
                continue

            time_slot = _get_time_slot(match)

            # تجميع الفرق حسب الفندق
            hotel_groups = defaultdict(list)
            for team in teams_for_go:
                h_id = _get_team_hotel_id(team)
                hotel_groups[h_id].append(team)

            # ★ ترتيب مجموعات الفنادق:
            # الفنادق التي فرقها لها عربات خاصة تُعالج أولاً
            def _hotel_has_private_vehicles(hotel_id, teams):
                acad_ids = set(t.academy_id for t in teams)
                return any(
                    v.ownership == 'academy' and v.academy_id in acad_ids
                    for v in all_vehicles
                )

            sorted_hotel_ids = sorted(
                hotel_groups.keys(),
                key=lambda hid: (0 if _hotel_has_private_vehicles(hid, hotel_groups[hid]) else 1, hid or 0)
            )

            # ★ حساب العربات المحجوزة: عربات خاصة لأكاديميات لها فرق في هذه المباراة
            # هذه العربات لا يجب أن تُعطى لفرق أكاديميات أخرى
            reserved_vehicle_ids = set()
            for hotel_id in sorted_hotel_ids:
                acad_ids = set(t.academy_id for t in hotel_groups[hotel_id])
                for v in all_vehicles:
                    if (v.ownership == 'academy'
                            and v.academy_id in acad_ids
                            and time_slot not in vehicle_busy_times[v.id]
                            and (v.can_return or vehicle_trip_count[v.id] == 0)):
                        reserved_vehicle_ids.add(v.id)

            for hotel_id in sorted_hotel_ids:
                hotel_teams = hotel_groups[hotel_id]
                remaining = list(hotel_teams)

                # ═══ المرحلة أ: العربات الخاصة بأكاديميات الفرق أولاً ═══
                academy_ids_with_teams = set(t.academy_id for t in remaining)
                private_for_these = [
                    v for v in all_vehicles
                    if v.ownership == 'academy'
                    and v.academy_id in academy_ids_with_teams
                    and time_slot not in vehicle_busy_times[v.id]
                    and (v.can_return or vehicle_trip_count[v.id] == 0)
                ]
                private_for_these.sort(key=lambda v: vehicle_trip_count[v.id])

                for v in private_for_these:
                    if not remaining:
                        break
                    if time_slot in vehicle_busy_times[v.id]:
                        continue

                    cap = capacity_map.get(v.type, 2)

                    own_teams = [t for t in remaining if t.academy_id == v.academy_id]
                    batch = []

                    if own_teams:
                        gender_hint = own_teams[0].gender
                        same_g = [t for t in own_teams if t.gender == gender_hint]
                        diff_g = [t for t in own_teams if t.gender != gender_hint]
                        batch = same_g[:cap]
                        if len(batch) < cap:
                            batch.extend(diff_g[:cap - len(batch)])

                        if len(batch) < cap:
                            others = [t for t in remaining if t not in batch]
                            same_g_others = [t for t in others if t.gender == gender_hint]
                            diff_g_others = [t for t in others if t.gender != gender_hint]
                            needed = cap - len(batch)
                            batch.extend(same_g_others[:needed])
                            needed = cap - len(batch)
                            if needed > 0:
                                batch.extend(diff_g_others[:needed])

                    if batch:
                        all_trips_data.append((v.id, match.id, 'go', batch))
                        vehicle_trip_count[v.id] += 1
                        vehicle_busy_times[v.id].add(time_slot)
                        total_distributed += len(batch)
                        # إزالة من المحجوزات بعد الاستخدام
                        reserved_vehicle_ids.discard(v.id)
                        for t in batch:
                            team_vehicle_assignment[t.id] = v.id
                            remaining.remove(t)

                # ★ إلغاء حجز العربات التي لم تُستخدم من هذه المجموعة
                # (أكاديمياتها لم تعد بحاجة لنقل في هذا الوقت)
                for v in private_for_these:
                    if v.id in reserved_vehicle_ids and time_slot not in vehicle_busy_times[v.id]:
                        reserved_vehicle_ids.discard(v.id)

                # ═══ المرحلة ب: العربات الأخرى (مع تجنب المحجوزة) ═══
                while remaining:
                    vehicle = _find_available_vehicle(
                        remaining, time_slot, all_vehicles,
                        vehicle_trip_count, vehicle_busy_times, capacity_map,
                        excluded_vehicle_ids=reserved_vehicle_ids
                    )
                    if vehicle is None:
                        total_unassigned += len(remaining)
                        break

                    cap = capacity_map.get(vehicle.type, 2)
                    batch = _select_batch_simple(remaining, cap)

                    if not batch:
                        break

                    all_trips_data.append((vehicle.id, match.id, 'go', batch))
                    vehicle_trip_count[vehicle.id] += 1
                    vehicle_busy_times[vehicle.id].add(time_slot)
                    total_distributed += len(batch)
                    for t in batch:
                        team_vehicle_assignment[t.id] = vehicle.id
                        remaining.remove(t)

        # ═══════════════════════════════════════
        # ★ الخطوة الثانية: رحلات الإياب
        # ★ نفس العربة التي ذهب بها الفريق تعيده
        # ═══════════════════════════════════════
        for match in period_matches:
            teams_for_return = [
                team_obj_map[tid] for tid, ret_m in team_return_match.items()
                if ret_m.id == match.id
            ]
            if not teams_for_return:
                continue

            time_slot = _get_time_slot(match) + "_return"

            # تجميع الفرق حسب العربة التي ذهبوا بها
            vehicle_return_groups = defaultdict(list)
            unassigned_return = []

            for team in teams_for_return:
                assigned_v = team_vehicle_assignment.get(team.id)
                if assigned_v:
                    vehicle_return_groups[assigned_v].append(team)
                else:
                    unassigned_return.append(team)

            # إنشاء رحلات إياب — نفس العربة
            for v_id, return_teams in vehicle_return_groups.items():
                vehicle = Vehicle.query.get(v_id)
                if not vehicle.can_return:
                    # العربة لا تعود — نحتاج عربة بديلة
                    unassigned_return.extend(return_teams)
                    continue

                # قد نحتاج لتقسيم إذا زاد العدد عن السعة
                cap = capacity_map.get(vehicle.type, 2)
                remaining_return = list(return_teams)

                while remaining_return:
                    batch = remaining_return[:cap]
                    remaining_return = remaining_return[cap:]

                    all_trips_data.append((v_id, match.id, 'return', batch))
                    vehicle_trip_count[v_id] += 1
                    vehicle_busy_times[v_id].add(time_slot)

            # فرق لم يكن لها تخصيص ذهاب — نبحث عن عربة
            if unassigned_return:
                hotel_groups_ret = defaultdict(list)
                for team in unassigned_return:
                    h_id = _get_team_hotel_id(team)
                    hotel_groups_ret[h_id].append(team)

                for hotel_id, hotel_teams in hotel_groups_ret.items():
                    remaining = list(hotel_teams)
                    while remaining:
                        vehicle = _find_available_vehicle(
                            remaining, time_slot, all_vehicles,
                            vehicle_trip_count, vehicle_busy_times, capacity_map,
                            require_can_return=True
                        )
                        if vehicle is None:
                            break
                        cap = capacity_map.get(vehicle.type, 2)
                        batch = _select_batch_simple(remaining, cap)
                        if not batch:
                            break
                        all_trips_data.append((vehicle.id, match.id, 'return', batch))
                        vehicle_trip_count[vehicle.id] += 1
                        vehicle_busy_times[vehicle.id].add(time_slot)
                        for t in batch:
                            remaining.remove(t)

    # ═══ 5. حفظ في قاعدة البيانات ═══
    final_result = {}
    order_counter = defaultdict(int)

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

    period_count = len(period_groups)
    msg = f"تم توزيع {total_distributed} فريق على {len(matches)} مباراة ({period_count} فترة)."
    if total_unassigned > 0:
        msg += f" تنبيه: {total_unassigned} فريق لم يجدوا مكاناً."

    return {'message': msg, 'vehicles': final_result}


def _find_available_vehicle(teams, time_slot, all_vehicles,
                            vehicle_trip_count, vehicle_busy_times, capacity_map,
                            require_can_return=False,
                            excluded_vehicle_ids=None):
    """
    إيجاد عربة متاحة:
    1. ليست مشغولة في هذا الوقت
    2. ليست في قائمة المحجوزة (reserved)
    3. الأقل رحلات أولاً (توزيع متوازن)
    4. العامة أولاً ثم الخاصة
    """
    if excluded_vehicle_ids is None:
        excluded_vehicle_ids = set()

    team_academy_ids = {t.academy_id for t in teams}
    candidates = []

    for v in all_vehicles:
        if v.id in excluded_vehicle_ids:
            continue  # ★ محجوزة لأكاديميتها
        if time_slot in vehicle_busy_times[v.id]:
            continue
        if require_can_return and not v.can_return:
            continue
        if not v.can_return and vehicle_trip_count[v.id] > 0:
            continue

        # الأولوية: عامة > خاصة بأكاديمية أخرى
        if v.ownership == 'public':
            priority = 0
        elif v.ownership == 'academy' and v.academy_id not in team_academy_ids:
            priority = 1
        else:
            priority = 2

        candidates.append((priority, vehicle_trip_count[v.id], v.id, v))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return candidates[0][3]


def _select_batch_simple(teams_pool, cap):
    """اختيار دفعة بسيطة — نفس الجنس أولاً"""
    if not teams_pool:
        return []

    gender_hint = teams_pool[0].gender
    same_g = [t for t in teams_pool if t.gender == gender_hint]
    diff_g = [t for t in teams_pool if t.gender != gender_hint]

    batch = same_g[:cap]
    if len(batch) < cap:
        batch.extend(diff_g[:cap - len(batch)])
    return batch


def get_distribution(day):
    """استرجاع التوزيع المخزن مسبقاً"""
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