"""
Otomatik Nöbet Dağıtım ve Nöbet Adaleti Motoru
"""
import random
from typing import List, Dict, Tuple, Optional, Any
from core.models import Assignment, Teacher, Location, Day, DutyFairnessReport
from core.database import Database
from core.logger import logger

class AutoScheduler:
    def __init__(self, db: Database):
        self.db = db

    def generate_schedule(
        self,
        week_start: str,
        avoid_consecutive_days: bool = True
    ) -> Tuple[List[Assignment], DutyFairnessReport]:
        """
        Nöbetleri kısıtlara göre dağıtır ve bir önizleme listesi ile adalet raporu döndürür.
        Veritabanına doğrudan yazmaz!
        """
        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)
        teachers = self.db.get_teachers(active_only=True)
        current_assignments = self.db.get_assignments_for_week(week_start)

        # Hızlı erişim haritaları
        day_map = {d.id: d for d in days}
        loc_map = {loc.id: loc for loc in locations}
        teacher_map = {t.id: t for t in teachers}

        # Mevcut atamaları kopyala
        plan: Dict[Tuple[str, str, int], Assignment] = {}
        for a in current_assignments:
            plan[(a.day_id, a.location_id, a.slot_index)] = Assignment(
                id=a.id,
                week_start=a.week_start,
                day_id=a.day_id,
                location_id=a.location_id,
                slot_index=a.slot_index,
                teacher_id=a.teacher_id,
                fixed=a.fixed,
                notes=a.notes
            )

        # Eksik slotları oluştur
        for d in days:
            for loc in locations:
                for slot in range(loc.capacity):
                    key = (d.id, loc.id, slot)
                    if key not in plan:
                        plan[key] = Assignment(
                            week_start=week_start,
                            day_id=d.id,
                            location_id=loc.id,
                            slot_index=slot,
                            teacher_id=None,
                            fixed=False
                        )

        # Sabit atamaları tespit et ve sayaçları başlat
        teacher_duty_count: Dict[str, int] = {t.id: 0 for t in teachers}
        # Öğretmenin hangi gün nöbeti var: teacher_id -> set of day_id
        teacher_days: Dict[str, set] = {t.id: set() for t in teachers}

        slots_to_fill: List[Tuple[str, str, int]] = []

        for key, assign in plan.items():
            if assign.fixed and assign.teacher_id:
                t_id = assign.teacher_id
                if t_id in teacher_duty_count:
                    teacher_duty_count[t_id] += 1
                if t_id in teacher_days:
                    teacher_days[t_id].add(assign.day_id)
            else:
                # Dağıtılacak slot
                assign.teacher_id = None
                slots_to_fill.append(key)

        # Gün sırasına göre sıralı slot listesi
        day_order = {d.id: d.order_num for d in days}
        slots_to_fill.sort(key=lambda x: (day_order.get(x[0], 0), x[1], x[2]))

        # Rastgelelik için öğretmen havuzunu karıştır
        candidate_pool = list(teachers)
        random.seed(42)  # Deterministik / tekrarlanabilir dağıtım

        warnings: List[str] = []

        for day_id, loc_id, slot_idx in slots_to_fill:
            day_obj = day_map.get(day_id)
            day_name = day_obj.name if day_obj else ""
            day_num = day_obj.order_num if day_obj else 0

            # Uygun adayları filtrele
            valid_candidates = []
            for t in candidate_pool:
                # 1. Müsait olmadığı gün mü?
                if day_name in t.unavailable_days:
                    continue
                # 2. Aynı gün zaten nöbeti var mı?
                if day_id in teacher_days[t.id]:
                    continue
                # 3. Ardışık gün kontrolü
                if avoid_consecutive_days:
                    has_consecutive = False
                    for existing_day_id in teacher_days[t.id]:
                        exist_num = day_order.get(existing_day_id, 0)
                        if abs(exist_num - day_num) == 1:
                            has_consecutive = True
                            break
                    if has_consecutive:
                        continue
                valid_candidates.append(t)

            # Eğer ardışık gün yüzünden kimse kalmadıysa kısıtı esnet
            if not valid_candidates and avoid_consecutive_days:
                for t in candidate_pool:
                    if day_name in t.unavailable_days or day_id in teacher_days[t.id]:
                        continue
                    valid_candidates.append(t)

            if valid_candidates:
                # En az nöbet tutmuş olanı seç (Nöbet Adaleti)
                valid_candidates.sort(key=lambda t: (teacher_duty_count[t.id], random.random()))
                chosen = valid_candidates[0]
                plan[(day_id, loc_id, slot_idx)].teacher_id = chosen.id
                teacher_duty_count[chosen.id] += 1
                teacher_days[chosen.id].add(day_id)
            else:
                loc_name = loc_map.get(loc_id).name if loc_id in loc_map else ""
                warnings.append(f"{day_name} günü {loc_name} (Slot {slot_idx+1}) için uygun öğretmen bulunamadı.")

        # Adalet raporunu hesapla
        active_counts = [teacher_duty_count[t.id] for t in teachers]
        avg = sum(active_counts) / len(active_counts) if active_counts else 0.0
        min_c = min(active_counts) if active_counts else 0
        max_c = max(active_counts) if active_counts else 0
        spread = max_c - min_c
        fairness_score = max(0.0, round(100.0 - (spread * 15.0), 1))

        report = DutyFairnessReport(
            teacher_counts=teacher_duty_count,
            teacher_names={t.id: t.name for t in teachers},
            average_duties=round(avg, 2),
            min_duties=min_c,
            max_duties=max_c,
            fairness_score=fairness_score,
            warnings=warnings
        )

        return list(plan.values()), report

    def apply_schedule(self, assignments: List[Assignment]):
        """
        Önizlenen dağıtımı veritabanına kaydeder.
        """
        for a in assignments:
            self.db.save_assignment(a)
        logger.info(f"{len(assignments)} atama veritabanına uygulandı.")
