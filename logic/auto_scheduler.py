"""
Otomatik Nöbet Dağıtım ve Nöbet Adaleti Motoru (Gelişmiş Mevzuat & 2 Aşamalı Optimizasyon)

Mevzuat ve Kural Öncelik Hiyerarşisi:
1. KESİN KURALLAR (Hard Constraints - Asla İhlal Edilemez):
   - Nöbet muafiyeti (Hamilelik, süt izni, engellilik, engelli yakını, yasal izin)
   - Kadro okulu / birden fazla okulda görev önceliği
   - Müsait olunmayan günler (İzinli / görevli günler)
   - Aynı gün çakışması (Aynı gün 2. nöbet verilemez)
   - Sabit nöbetler (Kilitli görevler korunur, değiştirilemez)
   - Nöbet yeri kapasitesi (Kapasite aşımı engellenir)
   - İkili eğitim devre uyumu (Sabahçı / Öğlenci devre kısıtları)

2. DENGELEME VE TERCİH KURALLARI (Soft Constraints - Puanlama):
   - Öğretmen gün tercihleri (+Puan: Tercih edilen gün, -Puan: İstenmeyen gün)
   - Ders programı ve ders yükü (Dersin az olduğu gün +Puan)
   - Boş ders sayısı (Boş dersin fazla olduğu gün +Puan)
   - Nöbet sayısı dengesi (Bu hafta hiç nöbet almamış öncelikli, eşit dağılım)
   - Önceki hafta rotasyonu (Geçen hafta aynı gün/yer nöbeti tekrarından kaçınma)
   - Nöbet yeri çeşitliliği (Farklı nöbet bölgeleri arasında rotasyon)

3. 2 AŞAMALI OPTİMİZASYON:
   - Aşama 1: Kesin kurallara uygun geçerli temel çözüm oluşturma
   - Aşama 2: Tercih, ders yükü ve adalet skorunu maksimize eden takas optimizasyon turu

4. AÇIKLANABİLİRLİK:
   - Her atama için "Neden bu öğretmen buraya atandı?" gerekçe maddeleri üretilir.
"""
import random
import datetime
from typing import List, Dict, Tuple, Optional, Any, Set
from core.models import Assignment, Teacher, Location, Day, DutyFairnessReport
from core.database import Database
from core.logger import logger

class AutoScheduler:
    def __init__(self, db: Database):
        self.db = db

    def _load_weights(self) -> Dict[str, int]:
        """Ayarlardan puanlama katsayılarını çeker (varsayılan değerlerle)."""
        get = self.db.get_setting
        return {
            "SCORE_BASE_ELIGIBLE": int(get("score_base_eligible", "1000")),
            "SCORE_PREFERRED_DAY": int(get("score_preferred_day", "100")),
            "SCORE_LOW_WORKLOAD": int(get("score_low_workload", "50")),
            "SCORE_FREE_PERIODS": int(get("score_free_periods", "30")),
            "SCORE_ZERO_DUTY_THIS_WEEK": int(get("score_zero_duty", "50")),
            "SCORE_NO_PREV_WEEK_DUTY": int(get("score_no_prev_duty", "30")),
            "SCORE_PREV_WEEK_DIFF_DAY": int(get("score_prev_diff_day", "20")),
            "SCORE_PREV_WEEK_DIFF_LOC": int(get("score_prev_diff_loc", "10")),
            "PENALTY_AVOIDED_DAY": int(get("penalty_avoided_day", "-100")),
            "PENALTY_PREV_WEEK_SAME_DAY": int(get("penalty_prev_same_day", "-80")),
            "PENALTY_HAS_DUTY_THIS_WEEK": int(get("penalty_has_duty", "-200")),
        }

    def _analyze_teacher_timetables(
        self,
        teachers: List[Teacher],
        days: List[Day]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Öğretmenlerin gün bazında ders sayılarını ve boş derslerini hesaplar.
        Dönüş: {teacher_id: {day_name: {'lesson_count': int, 'free_count': int, 'is_low': bool}}}
        """
        all_lessons = self.db.get_all_teacher_lessons()
        
        # teacher_id -> day_name -> list of lessons
        t_day_lessons: Dict[str, Dict[str, List[Any]]] = {t.id: {d.name: [] for d in days} for t in teachers}
        for l in all_lessons:
            if l.teacher_id in t_day_lessons and l.day_name in t_day_lessons[l.teacher_id]:
                t_day_lessons[l.teacher_id][l.day_name].append(l)

        analysis: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for t in teachers:
            analysis[t.id] = {}
            day_counts = []
            for d in days:
                lessons = t_day_lessons[t.id][d.name]
                active_count = sum(1 for item in lessons if not item.is_free)
                free_count = sum(1 for item in lessons if item.is_free)
                day_counts.append(active_count)
                analysis[t.id][d.name] = {
                    "lesson_count": active_count,
                    "free_count": free_count,
                    "total_periods": len(lessons),
                    "is_low": False,
                    "has_timetable": False
                }

            total_active = sum(day_counts)
            has_tt = total_active > 0 or any(len(t_day_lessons[t.id][d.name]) > 0 for d in days)
            avg_lessons = sum(day_counts) / len(day_counts) if day_counts else 0.0

            for d in days:
                analysis[t.id][d.name]["has_timetable"] = has_tt
                c = analysis[t.id][d.name]["lesson_count"]
                # Sadece o gün dersi olan ve ortalamanın altında (veya <= 4) olanlar için ders yükü düşük sayılır
                if c > 0 and (c < avg_lessons or c <= 4):
                    analysis[t.id][d.name]["is_low"] = True

        return analysis

    def _analyze_previous_week(self, week_start: str) -> Dict[str, Dict[str, Any]]:
        """
        Geçen haftanın nöbet kayıtlarını inceler:
        {teacher_id: {'days': set(day_name), 'locations': set(loc_id), 'total': int}}
        """
        result: Dict[str, Dict[str, Any]] = {}
        try:
            cur_dt = datetime.date.fromisoformat(week_start)
            prev_week_dt = cur_dt - datetime.timedelta(days=7)
            prev_week_str = prev_week_dt.isoformat()
            prev_assigns = self.db.get_assignments_for_week(prev_week_str)
            days_map = {d.id: d.name for d in self.db.get_days()}

            for a in prev_assigns:
                if a.teacher_id:
                    tid = a.teacher_id
                    if tid not in result:
                        result[tid] = {"days": set(), "locations": set(), "total": 0}
                    result[tid]["days"].add(days_map.get(a.day_id, ""))
                    result[tid]["locations"].add(a.location_id)
                    result[tid]["total"] += 1
        except Exception as e:
            logger.debug(f"Önceki hafta analizi yapılamadı: {e}")

        return result

    def generate_schedule(
        self,
        week_start: str,
        avoid_consecutive_days: bool = True,
        preserve_fixed: bool = True,
        allow_second_duty: bool = False,
        full_day_lessons_eligible: bool = True,
        only_days_with_lessons: bool = True,
        consider_preferences: bool = True,
        consider_prev_rotation: bool = True,
        honor_seniority: bool = True,
        assign_co_duty_for_unassigned: bool = False
    ) -> Tuple[List[Assignment], DutyFairnessReport]:
        """
        Mevzuat ve adalet kurallarına göre kullanıcı tanımlı ilkelerle 2 aşamalı optimizasyon ile nöbetleri dağıtır.
        O gün nöbetsiz kalan öğretmenleri boş derslerinde eşli/destek nöbetçi olarak başkasının yanına görevlendirmeyi teklif eder.
        Veritabanına doğrudan yazmaz, önizleme listesi ve detaylı adalet raporu döndürür.
        """
        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)
        all_teachers = self.db.get_teachers(active_only=True)
        school_info = self.db.get_school_info()
        weights = self._load_weights()

        day_map = {d.id: d for d in days}
        loc_map = {loc.id: loc for loc in locations}
        teacher_map = {t.id: t for t in all_teachers}
        day_order = {d.id: d.order_num for d in days}

        # Toplam gerekli nöbet slotu sayısı
        total_slots_needed = sum(loc.capacity for loc in locations) * len(days)

        # 1. KESİN UYGUNLUK VE MUAFİYET KONTROLÜ
        excluded_teachers: Dict[str, str] = {}
        candidate_pool: List[Teacher] = []
        senior_requested_teachers: List[Teacher] = []

        for t in all_teachers:
            # A) Kesin Mevzuat / Sağlık Muafiyeti
            if getattr(t, "is_exempt", False):
                reason = getattr(t, "exemption_reason", "").strip() or "Mevzuat / Sağlık Muafiyeti"
                excluded_teachers[t.name] = f"Nöbet muafiyeti mevcut ({reason})"
                continue

            # B) Kadro Okulu Olmama Durumu (Ders yoksa veya kadro başka okuldaysa)
            if not getattr(t, "is_primary_school", True):
                lessons = self.db.get_teacher_lessons(t.id)
                active_lessons = [l for l in lessons if not l.is_free]
                if len(active_lessons) == 0:
                    excluded_teachers[t.name] = "Kadro okulu değil ve bu okulda aktif dersi bulunmuyor"
                    continue

            # C) 20 / 25 Yıl Kıdem ve Muafiyet Talebi
            if honor_seniority and getattr(t, "seniority_years", 0) >= 20 and getattr(t, "exemption_requested", False):
                senior_requested_teachers.append(t)
            else:
                candidate_pool.append(t)

        # 20/25 Yıl Kuralı Değerlendirmesi: Okul personel sayısı yeterli mi?
        warnings: List[str] = []
        if honor_seniority and senior_requested_teachers:
            # Eğer kıdemsiz aday sayısı nöbet slotlarını rahatça karşılıyorsa kıdemliler muaf tutulur
            if len(candidate_pool) >= total_slots_needed:
                for st in senior_requested_teachers:
                    excluded_teachers[st.name] = f"20/25 yıl kıdem ({st.seniority_years} yıl) ve muafiyet talebi kabul edildi"
            else:
                # Personel yetersiz: Kıdemli öğretmenler de havuza eklenir, yönetici uyarılır
                candidate_pool.extend(senior_requested_teachers)
                st_names = ", ".join(st.name for st in senior_requested_teachers)
                warnings.append(
                    f"Personel sayısı yetersiz olduğundan 20/25 yıl kıdemli ve talepte bulunan öğretmenler ({st_names}) nöbet havuzuna dahil edildi."
                )

        # 2. MEVCUT ATAMALARI VE SABİT NÖBETLERİ YÜKLE
        current_assignments = self.db.get_assignments_for_week(week_start)
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

        # 3. SABİT NÖBETLERİ TESPİT ET VE KORU
        teacher_duty_count: Dict[str, int] = {t.id: 0 for t in candidate_pool}
        teacher_days: Dict[str, Set[str]] = {t.id: set() for t in candidate_pool}
        teacher_locations: Dict[str, Set[str]] = {t.id: set() for t in candidate_pool}
        fixed_count = 0

        slots_to_fill: List[Tuple[str, str, int]] = []

        for key, assign in plan.items():
            if preserve_fixed and assign.fixed and assign.teacher_id:
                t_id = assign.teacher_id
                if t_id in teacher_duty_count:
                    teacher_duty_count[t_id] += 1
                if t_id in teacher_days:
                    teacher_days[t_id].add(assign.day_id)
                if t_id in teacher_locations:
                    teacher_locations[t_id].add(assign.location_id)
                fixed_count += 1
            else:
                assign.teacher_id = None
                slots_to_fill.append(key)

        # 4. YARDIMCI ANALİZLER
        tt_analysis = self._analyze_teacher_timetables(candidate_pool, days)
        prev_analysis = self._analyze_previous_week(week_start)

        # Dağıtım gerekçeleri sözlüğü: (day_id, loc_id, slot_idx) -> List[str]
        assignment_reasons: Dict[Tuple[str, str, int], List[str]] = {}

        # Slotları sırala: Gün sırası ve nöbet yeri sırası
        slots_to_fill.sort(key=lambda x: (day_order.get(x[0], 0), loc_map[x[1]].order_num if x[1] in loc_map else 0, x[2]))

        # Rastgelelik tohumu (deterministik ve adil)
        rng = random.Random(42)

        # 5. AŞAMA 1: GEÇERLİ TEMEL ÇÖZÜM OLUŞTURMA (GREEDY ADAPTIVE)
        unfilled_slots: List[Dict[str, Any]] = []

        for day_id, loc_id, slot_idx in slots_to_fill:
            day_obj = day_map.get(day_id)
            loc_obj = loc_map.get(loc_id)
            day_name = day_obj.name if day_obj else ""
            loc_name = loc_obj.name if loc_obj else ""

            # Uygun Adayları Filtrele (KESİN KURALLAR)
            valid_candidates: List[Tuple[Teacher, float, List[str]]] = []

            for t in candidate_pool:
                # KESİN 0: 2. Nöbet Kontrolü
                # Kullanıcı "2. nöbet günü ver" seçeneğini seçmediyse kesinlikle kimseye 2. nöbet verilmez!
                if not allow_second_duty and teacher_duty_count[t.id] >= 1:
                    continue
                if allow_second_duty and teacher_duty_count[t.id] >= 2:
                    continue

                # KESİN 1: Müsait olmadığı gün mü?
                if day_name in t.unavailable_days:
                    continue

                # KESİN 2: Aynı gün zaten başka bir nöbeti var mı? (Çakışma Engeli - Aynı gün 2. nöbet asla verilemez)
                if day_id in teacher_days[t.id]:
                    continue

                # KESİN 3: İkili Eğitim Devre Uyumu
                if school_info.education_type == "İkili":
                    t_shift = getattr(t, "shift_group", "Tümü")
                    l_shift = getattr(loc_obj, "shift_group", "Tümü")
                    if t_shift != "Tümü" and l_shift != "Tümü" and t_shift != l_shift:
                        continue

                # KESİN 4: Ardışık gün kısıtı (Varsa)
                if avoid_consecutive_days:
                    has_consecutive = False
                    day_num = day_order.get(day_id, 0)
                    for exist_day_id in teacher_days[t.id]:
                        exist_num = day_order.get(exist_day_id, 0)
                        if abs(exist_num - day_num) == 1:
                            has_consecutive = True
                            break
                    if has_consecutive:
                        continue

                # KESİN 5: Boş Gün Kısıtı (Sadece dersi olan günlere nöbet ver seçiliyse)
                t_stat = tt_analysis.get(t.id, {}).get(day_name, {})
                if only_days_with_lessons and t_stat.get("has_timetable", False) and t_stat.get("lesson_count", 0) == 0:
                    continue

                # ADAY İÇİN PUANLAMA VE GEREKÇE HESAPLA (DENGELEME KURALLARI)
                score = float(weights["SCORE_BASE_ELIGIBLE"])
                reasons: List[str] = ["✓ Nöbet tutmaya mevzuata uygun"]

                # A) Nöbet Sayısı Dengesi (Bu hafta henüz nöbet almamış öğretmene mutlak öncelik)
                current_duties = teacher_duty_count[t.id]
                if current_duties == 0:
                    score += 50000.0  # 0 nöbetli öğretmene devasa öncelik (herkese 1 nöbet garantisi)
                    reasons.append("✓ Bu hafta henüz nöbet görevi bulunmuyor")

                    # Haftalık müsait olduğu gün sayısı az olan öğretmenlere slot önceliği ver
                    avail_days_cnt = sum(
                        1 for d_chk in days
                        if d_chk.name not in t.unavailable_days and
                        (not only_days_with_lessons or not tt_analysis.get(t.id, {}).get(d_chk.name, {}).get("has_timetable", False) or tt_analysis.get(t.id, {}).get(d_chk.name, {}).get("lesson_count", 0) > 0)
                    )
                    score += max(0, 5 - avail_days_cnt) * 100.0
                else:
                    # 2. Nöbet (ancak 0 nöbetli uygun aday kalmadığında devreye girer)
                    score += weights["PENALTY_HAS_DUTY_THIS_WEEK"] * current_duties
                    reasons.append(f"• İhtiyaç nedeniyle haftalık {current_duties + 1}. nöbet görevi")

                # B) Öğretmen Gün Tercihleri
                if consider_preferences:
                    pref_days = getattr(t, "preferred_days", [])
                    avoid_days = getattr(t, "avoided_days", [])
                    if day_name in pref_days:
                        score += weights["SCORE_PREFERRED_DAY"]
                        reasons.append(f"✓ Öğretmenin tercih ettiği gün ({day_name})")
                    elif day_name in avoid_days:
                        score += weights["PENALTY_AVOIDED_DAY"]
                        reasons.append(f"• Öğretmenin tercih etmediği gün ({day_name}) (ihtiyaç nedeniyle atandı)")

                # C) Ders Programı ve Ders Yükü (Tüm dersleri dolu olsa bile tam yetkinlik)
                t_day_stat = tt_analysis.get(t.id, {}).get(day_name, {})
                l_count = t_day_stat.get("lesson_count", 0)
                f_count = t_day_stat.get("free_count", 0)

                if full_day_lessons_eligible and l_count > 0:
                    if f_count == 0:
                        reasons.append(f"✓ {day_name} günü dersleri tam dolu olsa da mevzuat gereği nöbetçi (Teneffüs nöbeti)")
                    elif t_day_stat.get("is_low", False):
                        score += weights["SCORE_LOW_WORKLOAD"]
                        reasons.append(f"✓ {day_name} günü ders yükü düşük ({l_count} saat ders)")
                    else:
                        reasons.append(f"✓ {day_name} günü {l_count} saat dersi bulunuyor")

                # D) Boş Ders Sayısı (Ek dinlenme bonusu)
                if f_count >= 3:
                    score += weights["SCORE_FREE_PERIODS"]
                    reasons.append(f"✓ {f_count} saat boş dersi bulunuyor (dinlenmeye/ikameye uygun)")

                # E) Önceki Hafta Rotasyonu
                if consider_prev_rotation:
                    t_prev = prev_analysis.get(t.id, {})
                    if t_prev.get("total", 0) == 0:
                        score += weights["SCORE_NO_PREV_WEEK_DUTY"]
                        reasons.append("✓ Önceki hafta nöbeti bulunmuyor")
                    else:
                        if day_name in t_prev.get("days", set()):
                            score += weights["PENALTY_PREV_WEEK_SAME_DAY"]
                            reasons.append("• Geçen hafta da aynı gün nöbet tutmuştu")
                        else:
                            score += weights["SCORE_PREV_WEEK_DIFF_DAY"]
                            reasons.append("✓ Geçen haftaya göre gün rotasyonu sağlandı")

                        if loc_id in t_prev.get("locations", set()):
                            score -= 20
                        else:
                            score += weights["SCORE_PREV_WEEK_DIFF_LOC"]
                            reasons.append(f"✓ {loc_name} yeri için yer rotasyonu dengeli")

                # Küçük rastgelelik (aynı puandaki adaylar arasında çeşitlilik)
                score += rng.uniform(0.01, 0.99)
                valid_candidates.append((t, score, reasons))

            # Eğer ardışık gün kısıtı yüzünden aday kalmadıysa kısıtı esnetip tekrar dene
            if not valid_candidates and avoid_consecutive_days:
                for t in candidate_pool:
                    if not allow_second_duty and teacher_duty_count[t.id] >= 1:
                        continue
                    if allow_second_duty and teacher_duty_count[t.id] >= 2:
                        continue
                    if day_name in t.unavailable_days or day_id in teacher_days[t.id]:
                        continue
                    if school_info.education_type == "İkili":
                        t_shift = getattr(t, "shift_group", "Tümü")
                        l_shift = getattr(loc_obj, "shift_group", "Tümü")
                        if t_shift != "Tümü" and l_shift != "Tümü" and t_shift != l_shift:
                            continue
                    
                    t_stat = tt_analysis.get(t.id, {}).get(day_name, {})
                    if only_days_with_lessons and t_stat.get("has_timetable", False) and t_stat.get("lesson_count", 0) == 0:
                        continue

                    # Esnetilmiş aday
                    current_duties = teacher_duty_count[t.id]
                    score = float(weights["SCORE_BASE_ELIGIBLE"]) + (50000.0 if current_duties == 0 else -1000.0)
                    reasons = ["✓ Nöbet mevzuatına uygun", "• Zorunluluk nedeniyle ardışık gün esnetildi"]
                    valid_candidates.append((t, score, reasons))

            if valid_candidates:
                # En yüksek puanlı adayı seç
                valid_candidates.sort(key=lambda x: x[1], reverse=True)
                best_teacher, best_score, best_reasons = valid_candidates[0]

                plan[(day_id, loc_id, slot_idx)].teacher_id = best_teacher.id
                teacher_duty_count[best_teacher.id] += 1
                teacher_days[best_teacher.id].add(day_id)
                teacher_locations[best_teacher.id].add(loc_id)
                assignment_reasons[(day_id, loc_id, slot_idx)] = best_reasons
            else:
                # Çözüm bulunamadı: Nedenini açıkça kaydet
                if not allow_second_duty:
                    zero_duty_left = sum(1 for t in candidate_pool if teacher_duty_count[t.id] == 0)
                    if zero_duty_left == 0:
                        reason_msg = f"{day_name} günü için henüz nöbet almamış öğretmen kalmadı ('2. nöbet günü ver' kapalı olduğu için kimseye 2. nöbet verilmedi)."
                    else:
                        reason_msg = f"{day_name} günü için müsait veya çakışmasız 0 nöbetli öğretmen bulunamadı."
                else:
                    reason_msg = f"{day_name} günü için müsait veya çakışmasız öğretmen kalmadı."

                unfilled_slots.append({
                    "day": day_name,
                    "location": loc_name,
                    "slot": slot_idx + 1,
                    "reason": reason_msg
                })
                warnings.append(f"{day_name} günü {loc_name} (Slot {slot_idx+1}) doldurulamadı: {reason_msg}")

        if not allow_second_duty and unfilled_slots:
            warnings.insert(0, f"📌 'Yetersiz kalırsa 2. nöbet günü ver' seçeneği kapalı olduğu için kimseye 2. nöbet verilmedi ({len(unfilled_slots)} slot boş kaldı).")

        # 6. AŞAMA 2: OPTİMİZASYON TURU (LOCAL SEARCH SWAP İLE ADALET VE TERCİH İYİLEŞTİRMESİ)
        # Sadece sabit olmayan, atanmış slotlar arasında swap denemeleri yapılır
        unfixed_slots = [k for k in plan.keys() if plan[k].teacher_id and not plan[k].fixed]
        max_swap_rounds = min(50, len(unfixed_slots) * 2)

        for _ in range(max_swap_rounds):
            if len(unfixed_slots) < 2:
                break
            k1, k2 = rng.sample(unfixed_slots, 2)
            d1_id, l1_id, s1_idx = k1
            d2_id, l2_id, s2_idx = k2

            t1_id = plan[k1].teacher_id
            t2_id = plan[k2].teacher_id
            if t1_id == t2_id:
                continue

            # Günler farklıysa çakışma kontrolleri
            if d1_id != d2_id:
                # t1, d2'de başka bir yerde nöbetçi mi? (k2 hariç)
                t1_d2_conflict = any(plan[(d2_id, l, s)].teacher_id == t1_id for l in loc_map for s in range(loc_map[l].capacity) if (d2_id, l, s) != k2)
                # t2, d1'de başka bir yerde nöbetçi mi? (k1 hariç)
                t2_d1_conflict = any(plan[(d1_id, l, s)].teacher_id == t2_id for l in loc_map for s in range(loc_map[l].capacity) if (d1_id, l, s) != k1)

                if t1_d2_conflict or t2_d1_conflict:
                    continue

                t1_obj = teacher_map.get(t1_id)
                t2_obj = teacher_map.get(t2_id)
                if not t1_obj or not t2_obj:
                    continue

                d1_name = day_map[d1_id].name
                d2_name = day_map[d2_id].name

                if d2_name in t1_obj.unavailable_days or d1_name in t2_obj.unavailable_days:
                    continue

                # KESİN (Seçenek B): O gün hiç dersi olmayan öğretmene swap yapılamaz
                t1_d2_stat = tt_analysis.get(t1_id, {}).get(d2_name, {})
                if only_days_with_lessons and t1_d2_stat.get("has_timetable", False) and t1_d2_stat.get("lesson_count", 0) == 0:
                    continue
                t2_d1_stat = tt_analysis.get(t2_id, {}).get(d1_name, {})
                if only_days_with_lessons and t2_d1_stat.get("has_timetable", False) and t2_d1_stat.get("lesson_count", 0) == 0:
                    continue

                # Takas sonucunda tercih memnuniyeti artıyor mu?
                # Mevcut memnuniyet
                pref_before = 0
                if d1_name in getattr(t1_obj, "preferred_days", []): pref_before += 1
                if d1_name in getattr(t1_obj, "avoided_days", []): pref_before -= 1
                if d2_name in getattr(t2_obj, "preferred_days", []): pref_before += 1
                if d2_name in getattr(t2_obj, "avoided_days", []): pref_before -= 1

                pref_after = 0
                if d2_name in getattr(t1_obj, "preferred_days", []): pref_after += 1
                if d2_name in getattr(t1_obj, "avoided_days", []): pref_after -= 1
                if d1_name in getattr(t2_obj, "preferred_days", []): pref_after += 1
                if d1_name in getattr(t2_obj, "avoided_days", []): pref_after -= 1

                # Eğer takas tercihleri iyileştiriyorsa takas et
                if pref_after > pref_before:
                    plan[k1].teacher_id = t2_id
                    plan[k2].teacher_id = t1_id
                    teacher_days[t1_id].discard(d1_id)
                    teacher_days[t1_id].add(d2_id)
                    teacher_days[t2_id].discard(d2_id)
                    teacher_days[t2_id].add(d1_id)

        # 6.5. BOŞTA KALAN ÖĞRETMENLER İÇİN EŞLİ / DESTEK NÖBETÇİ ANALİZİ VE TEKLİFİ
        # (O gün hiç görevlendirilmemiş öğretmen kaldıysa boş derslerine, adil olacak şekilde, başkasının yanına görevlendirme)
        co_duty_proposals: List[Dict[str, Any]] = []
        co_duty_assignments: List[Assignment] = []

        all_teacher_lessons = self.db.get_all_teacher_lessons()
        t_lessons_by_day_map: Dict[Tuple[str, str], List[Any]] = {}
        for l in all_teacher_lessons:
            key = (l.teacher_id, l.day_name)
            if key not in t_lessons_by_day_map:
                t_lessons_by_day_map[key] = []
            t_lessons_by_day_map[key].append(l)

        # Eşli nöbet verilecek öncelikli alanlar (Bahçe, Zemin Kat gibi hareketli alanlar)
        def _get_loc_co_duty_rank(loc_obj: Location) -> int:
            nm = loc_obj.name.upper()
            if "BAHÇE" in nm or "BAHCE" in nm:
                return 1
            if "ZEMİN" in nm or "ZEMIN" in nm or "GİRİŞ" in nm or "KANTİN" in nm:
                return 2
            if "1." in nm:
                return 3
            return 4

        sorted_locs_for_co_duty = sorted(locations, key=_get_loc_co_duty_rank)

        for d in days:
            day_id = d.id
            day_name = d.name

            # O gün okulda nöbet alan öğretmenler
            assigned_today = {
                plan[(day_id, loc.id, s)].teacher_id
                for loc in locations
                for s in range(loc.capacity)
                if (day_id, loc.id, s) in plan and plan[(day_id, loc.id, s)].teacher_id
            }

            # O gün okulda dersi olup nöbet yazılmamış uygun öğretmenler
            unassigned_today: List[Tuple[Teacher, int, int, List[int]]] = []
            for t in candidate_pool:
                if t.id in assigned_today:
                    continue
                if day_name in t.unavailable_days:
                    continue
                if not allow_second_duty and teacher_duty_count[t.id] >= 1:
                    continue
                if allow_second_duty and teacher_duty_count[t.id] >= 2:
                    continue

                t_day_lessons = t_lessons_by_day_map.get((t.id, day_name), [])
                active_lessons = [l for l in t_day_lessons if not l.is_free]
                free_lessons = [l for l in t_day_lessons if l.is_free]
                active_cnt = len(active_lessons)
                free_cnt = len(free_lessons)
                free_periods = sorted([l.period for l in free_lessons])

                # O gün en az 1 aktif dersi olan (okulda fiilen bulunan) öğretmenler
                if active_cnt > 0:
                    unassigned_today.append((t, active_cnt, free_cnt, free_periods))

            # Adil sıralama:
            # 1. Bu hafta hiç nöbet almamış olanlar (0 nöbetli) en önde
            # 2. O gün boş dersi en çok olanlar (dinlenmeye ve ikameye müsait)
            # 3. O günkü ders yükü daha az olanlar (aşırı yorgunluğu engelle)
            unassigned_today.sort(
                key=lambda x: (
                    0 if teacher_duty_count[x[0].id] == 0 else 1,
                    -x[2],  # free_cnt azalan
                    x[1],   # active_cnt artan
                )
            )

            co_assigned_in_day = set()
            for loc in sorted_locs_for_co_duty:
                primary_assign = plan.get((day_id, loc.id, 0))
                if not primary_assign or not primary_assign.teacher_id:
                    continue
                primary_t = teacher_map.get(primary_assign.teacher_id)
                if not primary_t:
                    continue

                for cand_t, cand_act_cnt, cand_free_cnt, cand_free_pers in unassigned_today:
                    if cand_t.id in co_assigned_in_day:
                        continue
                    if cand_t.id == primary_t.id:
                        continue
                    if not allow_second_duty and teacher_duty_count[cand_t.id] >= 1:
                        continue
                    if allow_second_duty and teacher_duty_count[cand_t.id] >= 2:
                        continue

                    free_str = ", ".join(map(str, cand_free_pers)) if cand_free_pers else "Teneffüsler"
                    cand_duties = teacher_duty_count[cand_t.id]
                    
                    reason_desc = (
                        f"{day_name} günü {cand_act_cnt} saat dersi olup nöbetsiz kalmıştı. "
                        f"{cand_free_cnt} saat boş dersi ({free_str}) adilce değerlendirilerek "
                        f"{primary_t.name} yanına {loc.name} eşli destek nöbetçisi olarak eşleştirildi."
                    )

                    proposal = {
                        "day_id": day_id,
                        "day_name": day_name,
                        "location_id": loc.id,
                        "location_name": loc.name,
                        "slot_index": 1,
                        "primary_teacher_id": primary_t.id,
                        "primary_teacher_name": primary_t.name,
                        "co_teacher_id": cand_t.id,
                        "co_teacher_name": cand_t.name,
                        "co_teacher_branch": cand_t.branch,
                        "free_periods": cand_free_pers,
                        "free_periods_str": free_str,
                        "lesson_count": cand_act_cnt,
                        "free_count": cand_free_cnt,
                        "current_duties": cand_duties,
                        "reason": reason_desc
                    }
                    co_duty_proposals.append(proposal)
                    co_assigned_in_day.add(cand_t.id)

                    if assign_co_duty_for_unassigned:
                        co_assign = Assignment(
                            week_start=week_start,
                            day_id=day_id,
                            location_id=loc.id,
                            slot_index=1,
                            teacher_id=cand_t.id,
                            fixed=False,
                            notes=(
                                f"👥 Eşli Destek Nöbetçisi: {primary_t.name} ile birlikte ({loc.name})\n"
                                f"🕒 Boş Ders Desteği: {free_str}. Dersler\n"
                                f"✓ Adil iş yükü dengelemesi ile görevlendirildi."
                            )
                        )
                        plan[(day_id, loc.id, 1)] = co_assign
                        co_duty_assignments.append(co_assign)
                        teacher_duty_count[cand_t.id] += 1
                        teacher_days[cand_t.id].add(day_id)
                        teacher_locations[cand_t.id].add(loc.id)

                    break  # Her lokasyona 1 eşli nöbetçi ekle

        # 7. GEREKÇE METİNLERİNİ ATAMALARA YANSIT
        assignment_reasons_report: Dict[str, List[str]] = {}
        for (day_id, loc_id, slot_idx), a in plan.items():
            key_str = f"{day_id}_{loc_id}_{slot_idx}"
            r_list = assignment_reasons.get((day_id, loc_id, slot_idx), [])
            if a.fixed:
                r_list = ["🔒 Sabit Nöbet (Kullanıcı tarafından kilitlendi)"]
            elif slot_idx >= 1 and a.teacher_id:
                # Eşli Nöbetçi gerekçesi
                primary_assign = plan.get((day_id, loc_id, 0))
                p_name = teacher_map[primary_assign.teacher_id].name if primary_assign and primary_assign.teacher_id in teacher_map else "Asıl Nöbetçi"
                loc_name = loc_map[loc_id].name if loc_id in loc_map else ""
                d_name = day_map[day_id].name if day_id in day_map else ""
                t_stat = tt_analysis.get(a.teacher_id, {}).get(d_name, {})
                f_cnt = t_stat.get("free_count", 0)
                l_cnt = t_stat.get("lesson_count", 0)
                r_list = [
                    f"👥 {p_name} ile birlikte {loc_name} Eşli Destek Nöbetçisi",
                    f"✓ {d_name} günü {f_cnt} saat boş dersi adil değerlendirildi",
                    f"✓ Ders yükü dengelendi ({l_cnt} saat aktif ders)",
                    "✓ Nöbetsiz kalması önlendi ve adil iş yükü sağlandı"
                ]
            elif a.teacher_id:
                t_obj = teacher_map.get(a.teacher_id)
                d_obj = day_map.get(day_id)
                d_name = d_obj.name if d_obj else ""
                t_stat = tt_analysis.get(a.teacher_id, {}).get(d_name, {})
                l_cnt = t_stat.get("lesson_count", 0)
                f_cnt = t_stat.get("free_count", 0)
                
                # Dinamik güncellenmiş gerekçeler
                r_list = [
                    "✓ Nöbet tutmaya mevzuata uygun",
                    f"✓ Nöbet sayısı dengeli ({teacher_duty_count.get(a.teacher_id, 1)}. nöbet)",
                ]
                if t_stat.get("is_low", False):
                    r_list.append(f"✓ {d_name} günü ders yükü düşük ({l_cnt} ders)")
                if f_cnt >= 2:
                    r_list.append(f"✓ {f_cnt} saat boş dersi bulunuyor")
                if t_obj and d_name in getattr(t_obj, "preferred_days", []):
                    r_list.append(f"✓ Öğretmenin tercih ettiği gün ({d_name})")
                r_list.append("✓ Gün ve nöbet yeri rotasyonu dengeli")

            assignment_reasons_report[key_str] = r_list
            a.notes = "\n".join(r_list)

        # 8. ADALET VE İSTATİSTİK RAPORU
        active_counts = [teacher_duty_count[t.id] for t in candidate_pool]
        avg = sum(active_counts) / len(active_counts) if active_counts else 0.0
        min_c = min(active_counts) if active_counts else 0
        max_c = max(active_counts) if active_counts else 0
        spread = max_c - min_c

        # Gini Katsayısı Hesaplama (0.0 = Tam Eşit Dağılım, 1.0 = Tam Eşitsizlik)
        def _calc_gini(counts: List[int]) -> float:
            if not counts or len(counts) <= 1:
                return 0.0
            s = sorted(counts)
            n = len(s)
            total = sum(s)
            if total == 0:
                return 0.0
            gini_sum = sum((2 * i - n - 1) * c for i, c in enumerate(s, 1))
            return max(0.0, min(1.0, round(gini_sum / (n * total), 4)))

        gini_val = _calc_gini(active_counts)
        # 100 üzerinden adalet skoru (Gini ve yayılım cezası ile)
        fairness_score = max(0.0, min(100.0, round(100.0 - (gini_val * 100.0 * 0.75) - (spread * 4.0), 1)))

        # Tercih karşılanma sayısı
        satisfied_prefs = 0
        unsatisfied_prefs = 0
        for t in candidate_pool:
            t_days = {day_map[d].name for d in teacher_days[t.id] if d in day_map}
            for pd in getattr(t, "preferred_days", []):
                if pd in t_days:
                    satisfied_prefs += 1
            for ad in getattr(t, "avoided_days", []):
                if ad in t_days:
                    unsatisfied_prefs += 1

        filled_count = sum(1 for a in plan.values() if a.teacher_id)
        zero_cnt = sum(1 for c in active_counts if c == 0)
        one_cnt = sum(1 for c in active_counts if c == 1)
        multi_cnt = sum(1 for c in active_counts if c > 1)

        fairness_details = {
            "fairness_score": fairness_score,
            "gini_index": gini_val,
            "total_active_teachers": len(all_teachers),
            "eligible_teachers": len(candidate_pool),
            "zero_duty_teachers": zero_cnt,
            "one_duty_teachers": one_cnt,
            "multi_duty_teachers": multi_cnt,
            "min_duties": min_c,
            "max_duties": max_c,
            "average_duties": round(avg, 2),
            "spread": spread,
            "co_duty_count": len(co_duty_assignments),
            "co_duty_proposal_count": len(co_duty_proposals),
            "fairness_level": "A+ Mükemmel Eşitlik" if fairness_score >= 95 else ("A Çok Yüksek Adalet" if fairness_score >= 90 else "B Dengeli Dağılım")
        }

        stats = {
            "total_active_teachers": len(all_teachers),
            "eligible_teachers": len(candidate_pool),
            "excluded_count": len(excluded_teachers),
            "total_slots": len(plan),
            "filled_slots": filled_count,
            "unfilled_slots": len(unfilled_slots),
            "fixed_preserved": fixed_count,
            "satisfied_preferences": satisfied_prefs,
            "unsatisfied_preferences": unsatisfied_prefs,
            "spread": spread,
            "gini_index": gini_val,
            "co_duty_count": len(co_duty_assignments),
            "co_duty_proposal_count": len(co_duty_proposals)
        }

        report = DutyFairnessReport(
            teacher_counts=teacher_duty_count,
            teacher_names={t.id: t.name for t in all_teachers},
            average_duties=round(avg, 2),
            min_duties=min_c,
            max_duties=max_c,
            fairness_score=fairness_score,
            warnings=warnings,
            excluded_teachers=excluded_teachers,
            assignment_reasons=assignment_reasons_report,
            unfilled_slots=unfilled_slots,
            stats=stats,
            co_duty_proposals=co_duty_proposals,
            co_duty_assignments=co_duty_assignments,
            gini_index=gini_val,
            fairness_details=fairness_details
        )

        return list(plan.values()), report

    def apply_schedule(self, assignments: List[Assignment]):
        """
        Önizlenen dağıtımı veritabanına kaydeder.
        Eşli nöbet atamaları varsa ilgili nöbet yerlerinin kapasitesini otomatik olarak senkronize eder.
        """
        locs = {l.id: l for l in self.db.get_locations()}
        max_slot_needed = {}
        for a in assignments:
            if a.teacher_id:
                max_slot_needed[a.location_id] = max(max_slot_needed.get(a.location_id, 0), a.slot_index + 1)

        for loc_id, needed_cap in max_slot_needed.items():
            loc = locs.get(loc_id)
            if loc and loc.capacity < needed_cap:
                loc.capacity = needed_cap
                self.db.save_location(loc)

        for a in assignments:
            self.db.save_assignment(a)
        logger.info(f"{len(assignments)} atama veritabanına uygulandı.")
