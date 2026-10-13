"""
Nöbet İş Mantığı Servisi
Hücre taşıma, takas, sabitleme, atama, rotasyon/kaydırma ve Undo/Redo komutları.
"""
from typing import List, Optional, Tuple, Dict, Any
from core.models import Assignment, Teacher, Location, Day, SchoolInfo
from core.database import Database
from core.undo_manager import UndoManager, Command
from core.logger import logger
import copy
import unicodedata
import pymupdf
from data.reference_data import NAME_ALIASES
from logic.matching_service import MatchingService

class MoveOrSwapCommand(Command):
    def __init__(
        self,
        db: Database,
        week_start: str,
        source_day_id: str,
        source_loc_id: str,
        source_slot: int,
        target_day_id: str,
        target_loc_id: str,
        target_slot: int
    ):
        self.db = db
        self.week_start = week_start
        self.src_day = source_day_id
        self.src_loc = source_loc_id
        self.src_slot = source_slot
        self.tgt_day = target_day_id
        self.tgt_loc = target_loc_id
        self.tgt_slot = target_slot

        self.old_src_assign: Optional[Assignment] = None
        self.old_tgt_assign: Optional[Assignment] = None
        self.is_swap = False
        self.description = "Nöbet Taşıma"

    def execute(self) -> bool:
        assignments = self.db.get_assignments_for_week(self.week_start)
        
        # Kaynak atamayı bul
        src_assign = None
        for a in assignments:
            if a.day_id == self.src_day and a.location_id == self.src_loc and a.slot_index == self.src_slot:
                src_assign = a
                break

        if not src_assign or not src_assign.teacher_id:
            return False

        if src_assign.fixed:
            logger.warning("Sabit nöbet taşınamaz (önce kilidi kaldırın).")
            return False

        # Hedef atamayı bul
        tgt_assign = None
        for a in assignments:
            if a.day_id == self.tgt_day and a.location_id == self.tgt_loc and a.slot_index == self.tgt_slot:
                tgt_assign = a
                break

        if tgt_assign and tgt_assign.fixed:
            logger.warning("Hedef hücredeki nöbet sabitlenmiştir, takas yapılamaz.")
            return False

        # Çakışma kontrolü (Aynı gün 2. nöbet engeli)
        days_map = {d.id: d.name for d in self.db.get_days()}
        src_teacher_obj = self.db.get_teacher_by_id(src_assign.teacher_id)
        src_teacher_name = src_teacher_obj.name if src_teacher_obj else "Öğretmen"

        # Eğer gün değişiyorsa: kaynak öğretmen hedef günde başka bir nöbette mi?
        if self.src_day != self.tgt_day:
            tgt_day_name = days_map.get(self.tgt_day, "bu")
            src_other_on_tgt_day = [
                a for a in assignments
                if a.day_id == self.tgt_day and a.teacher_id == src_assign.teacher_id and not (a.location_id == self.tgt_loc and a.slot_index == self.tgt_slot)
            ]
            if src_other_on_tgt_day:
                self.error_message = f"{src_teacher_name} {tgt_day_name} günü başka bir nöbette görevli olduğu için buraya atanamaz."
                logger.warning(self.error_message)
                return False

            # Katı Kural (Seçenek B): Öğretmenin hedef günde hiç dersi yoksa nöbet taşınamaz
            src_all_lessons = self.db.get_teacher_lessons(src_assign.teacher_id)
            if src_all_lessons:
                src_day_lessons = [l for l in src_all_lessons if l.day_name == tgt_day_name and not l.is_free]
                if not src_day_lessons:
                    self.error_message = f"{src_teacher_name} {tgt_day_name} günü hiç dersi bulunmadığı için nöbete atanamaz."
                    logger.warning(self.error_message)
                    return False

        # Eğer takas yapılıyorsa ve günler farklıysa: hedef öğretmen kaynak günde başka bir nöbette mi?
        if tgt_assign and tgt_assign.teacher_id and self.src_day != self.tgt_day:
            tgt_teacher_obj = self.db.get_teacher_by_id(tgt_assign.teacher_id)
            tgt_teacher_name = tgt_teacher_obj.name if tgt_teacher_obj else "Öğretmen"
            src_day_name = days_map.get(self.src_day, "bu")
            tgt_other_on_src_day = [
                a for a in assignments
                if a.day_id == self.src_day and a.teacher_id == tgt_assign.teacher_id and not (a.location_id == self.src_loc and a.slot_index == self.src_slot)
            ]
            if tgt_other_on_src_day:
                self.error_message = f"{tgt_teacher_name} {src_day_name} günü başka bir nöbette görevli olduğu için takas yapılamaz."
                logger.warning(self.error_message)
                return False

            # Katı Kural (Seçenek B): Takas edilen öğretmenin kaynak günde hiç dersi yoksa takas yapılamaz
            tgt_all_lessons = self.db.get_teacher_lessons(tgt_assign.teacher_id)
            if tgt_all_lessons:
                tgt_day_lessons = [l for l in tgt_all_lessons if l.day_name == src_day_name and not l.is_free]
                if not tgt_day_lessons:
                    self.error_message = f"{tgt_teacher_name} {src_day_name} günü hiç dersi bulunmadığı için takas yapılamaz."
                    logger.warning(self.error_message)
                    return False

        # Aynı hücre mi?
        if (self.src_day == self.tgt_day and 
            self.src_loc == self.tgt_loc and 
            self.src_slot == self.tgt_slot):
            return True  # No-op

        # Durumları yedekle
        self.old_src_assign = copy.deepcopy(src_assign)
        self.old_tgt_assign = copy.deepcopy(tgt_assign) if tgt_assign else None

        if tgt_assign and tgt_assign.teacher_id:
            # Dolu hücreye taşıma = TAKAS (SWAP)
            self.is_swap = True
            self.description = "Nöbet Takası"
            temp_teacher = tgt_assign.teacher_id
            tgt_assign.teacher_id = src_assign.teacher_id
            src_assign.teacher_id = temp_teacher
            self.db.save_assignment(src_assign)
            self.db.save_assignment(tgt_assign)
        else:
            # Boş hücreye taşıma
            self.is_swap = False
            self.description = "Nöbet Taşıma"
            if not tgt_assign:
                tgt_assign = Assignment(
                    week_start=self.week_start,
                    day_id=self.tgt_day,
                    location_id=self.tgt_loc,
                    slot_index=self.tgt_slot,
                    teacher_id=src_assign.teacher_id
                )
            else:
                tgt_assign.teacher_id = src_assign.teacher_id
            
            src_assign.teacher_id = None
            self.db.save_assignment(src_assign)
            self.db.save_assignment(tgt_assign)

        return True

    def undo(self) -> bool:
        if self.old_src_assign:
            self.db.save_assignment(self.old_src_assign)
        if self.old_tgt_assign:
            self.db.save_assignment(self.old_tgt_assign)
        else:
            assignments = self.db.get_assignments_for_week(self.week_start)
            for a in assignments:
                if a.day_id == self.tgt_day and a.location_id == self.tgt_loc and a.slot_index == self.tgt_slot:
                    a.teacher_id = None
                    self.db.save_assignment(a)
                    break
        return True


class AssignTeacherCommand(Command):
    def __init__(self, db: Database, assignment: Assignment, new_teacher_id: Optional[str]):
        self.db = db
        self.assignment_id = assignment.id
        self.old_teacher_id = assignment.teacher_id
        self.new_teacher_id = new_teacher_id
        self.error_message: Optional[str] = None
        self.description = "Öğretmen Atama" if new_teacher_id else "Atama Kaldırma"

    def execute(self) -> bool:
        assign = self.db.get_assignment_by_id(self.assignment_id)
        if not assign:
            return False
        if assign.fixed:
            logger.warning("Sabitlenmiş nöbet değiştirilemez.")
            return False

        if self.new_teacher_id:
            days_map = {d.id: d.name for d in self.db.get_days()}
            d_name = days_map.get(assign.day_id, "")
            t_obj = self.db.get_teacher_by_id(self.new_teacher_id)
            t_name = t_obj.name if t_obj else "Öğretmen"

            # Katı Kural (Seçenek B): O gün hiç dersi yoksa nöbet atanamaz
            t_all_lessons = self.db.get_teacher_lessons(self.new_teacher_id)
            if t_all_lessons:
                t_day_lessons = [l for l in t_all_lessons if l.day_name == d_name and not l.is_free]
                if not t_day_lessons:
                    self.error_message = f"{t_name} {d_name} günü hiç dersi bulunmadığı için nöbete atanamaz."
                    logger.warning(self.error_message)
                    return False

            assignments = self.db.get_assignments_for_week(assign.week_start)
            same_day_assigns = [
                a for a in assignments
                if a.day_id == assign.day_id and a.teacher_id == self.new_teacher_id and a.id != assign.id
            ]
            if same_day_assigns:
                self.error_message = f"{t_name} {d_name} günü zaten başka bir nöbete atanmıştır."
                logger.warning(self.error_message)
                return False

        assign.teacher_id = self.new_teacher_id
        self.db.save_assignment(assign)
        return True

    def undo(self) -> bool:
        assign = self.db.get_assignment_by_id(self.assignment_id)
        if not assign:
            return False
        assign.teacher_id = self.old_teacher_id
        self.db.save_assignment(assign)
        return True


class ToggleFixedCommand(Command):
    def __init__(self, db: Database, assignment_id: str):
        self.db = db
        self.assignment_id = assignment_id
        self.old_fixed = False
        self.description = "Nöbet Sabitleme"

    def execute(self) -> bool:
        assign = self.db.get_assignment_by_id(self.assignment_id)
        if not assign:
            return False
        self.old_fixed = assign.fixed
        assign.fixed = not assign.fixed
        self.description = "Nöbet Sabitlendi" if assign.fixed else "Nöbet Sabiti Kaldırıldı"
        self.db.save_assignment(assign)
        return True

    def undo(self) -> bool:
        assign = self.db.get_assignment_by_id(self.assignment_id)
        if not assign:
            return False
        assign.fixed = self.old_fixed
        self.db.save_assignment(assign)
        return True


class ShiftScheduleCommand(Command):
    """
    Haftalık nöbet çizelgesini manuel olarak gün veya yer bazında kaydıran (rotasyon yapan) komut.
    """
    def __init__(
        self,
        db: Database,
        week_start: str,
        shift_type: str = "day",  # "day" veya "location"
        steps: int = 1,          # 1: ileri, -1: geri
        preserve_fixed: bool = True
    ):
        self.db = db
        self.week_start = week_start
        self.shift_type = shift_type
        self.steps = steps
        self.preserve_fixed = preserve_fixed
        self.old_assignments: List[Assignment] = []
        dir_text = "İleri" if steps > 0 else "Geri"
        self.description = f"Nöbetleri {'Güne' if shift_type == 'day' else 'Yere'} Göre {dir_text} Kaydır"

    def execute(self) -> bool:
        assignments = self.db.get_assignments_for_week(self.week_start)
        if not assignments:
            return False

        self.old_assignments = [copy.deepcopy(a) for a in assignments]
        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)

        assign_map = {(a.day_id, a.location_id, a.slot_index): a for a in assignments}
        new_teacher_map: Dict[Tuple[str, str, int], Optional[str]] = {}

        if self.shift_type == "day":
            # Gün bazlı kaydırma: Her yer ve slot için günler arasında rotasyon
            for loc in locations:
                for slot in range(loc.capacity):
                    if self.preserve_fixed:
                        # Sabit olmayan günleri belirle; döngüyü sadece bunlar arasında kur
                        unfixed_days = [
                            d for d in days
                            if (d.id, loc.id, slot) in assign_map and not assign_map[(d.id, loc.id, slot)].fixed
                        ]
                        teachers = [assign_map[(d.id, loc.id, slot)].teacher_id for d in unfixed_days]
                        num_unfixed = len(unfixed_days)
                        if num_unfixed > 1:
                            for i, d in enumerate(unfixed_days):
                                src_i = (i - self.steps) % num_unfixed
                                new_teacher_map[(d.id, loc.id, slot)] = teachers[src_i]
                    else:
                        # Sabit gözetilmeksizin tüm günler rotasyona girer
                        valid_days = [d for d in days if (d.id, loc.id, slot) in assign_map]
                        teachers = [assign_map[(d.id, loc.id, slot)].teacher_id for d in valid_days]
                        num_days = len(valid_days)
                        if num_days > 1:
                            for i, d in enumerate(valid_days):
                                src_i = (i - self.steps) % num_days
                                new_teacher_map[(d.id, loc.id, slot)] = teachers[src_i]

        elif self.shift_type == "location":
            # Yer bazlı kaydırma: Her gün için nöbet yerleri arasında rotasyon
            for d in days:
                slots_on_day = []
                for loc in locations:
                    for slot in range(loc.capacity):
                        key = (d.id, loc.id, slot)
                        if key in assign_map:
                            slots_on_day.append((loc.id, slot))

                if self.preserve_fixed:
                    # Sabit olmayan yerleri belirle; döngüyü sadece bunlar arasında kur
                    unfixed_slots = [
                        (l_id, s) for l_id, s in slots_on_day
                        if not assign_map[(d.id, l_id, s)].fixed
                    ]
                    teachers = [assign_map[(d.id, l_id, s)].teacher_id for l_id, s in unfixed_slots]
                    num_unfixed = len(unfixed_slots)
                    if num_unfixed > 1:
                        for i, (l_id, s) in enumerate(unfixed_slots):
                            src_i = (i - self.steps) % num_unfixed
                            new_teacher_map[(d.id, l_id, s)] = teachers[src_i]
                else:
                    teachers = [assign_map[(d.id, l_id, s)].teacher_id for l_id, s in slots_on_day]
                    num_slots = len(slots_on_day)
                    if num_slots > 1:
                        for i, (l_id, s) in enumerate(slots_on_day):
                            src_i = (i - self.steps) % num_slots
                            new_teacher_map[(d.id, l_id, s)] = teachers[src_i]

        # Yeni atamaları uygula
        for (d_id, loc_id, slot), t_id in new_teacher_map.items():
            assign = assign_map.get((d_id, loc_id, slot))
            if assign and (not self.preserve_fixed or not assign.fixed):
                assign.teacher_id = t_id
                self.db.save_assignment(assign)

        return True

    def undo(self) -> bool:
        for a in self.old_assignments:
            self.db.save_assignment(a)
        return True


class CopyWeekCommand(Command):
    """
    Bir haftanın nöbetlerini diğer bir haftaya kopyalayan (isteğe bağlı gün veya yer kaydırma ile) komut.
    """
    def __init__(
        self,
        db: Database,
        source_week: str,
        target_week: str,
        shift_days: int = 0,
        shift_mode: str = "same",  # "same", "shift_day", "shift_loc"
        shift_steps: int = 1,
        preserve_fixed: bool = True
    ):
        self.db = db
        self.source_week = source_week
        self.target_week = target_week
        if shift_days != 0 and shift_mode == "same":
            self.shift_mode = "shift_day"
            self.shift_steps = shift_days
        else:
            self.shift_mode = shift_mode
            self.shift_steps = shift_steps
        self.preserve_fixed = preserve_fixed
        self.old_target_assignments: List[Assignment] = []
        
        mode_desc = {
            "same": "Aynısını Aktar",
            "shift_day": f"Günleri {self.shift_steps} Gün Kaydırarak Aktar",
            "shift_loc": f"Yerleri {self.shift_steps} Sıra Kaydırarak Aktar"
        }.get(self.shift_mode, "Aktar")
        self.description = f"Nöbetleri Sonraki Haftaya ({mode_desc})"

    def execute(self) -> bool:
        self.old_target_assignments = [copy.deepcopy(a) for a in self.db.get_assignments_for_week(self.target_week)]
        src_assignments = self.db.get_assignments_for_week(self.source_week)
        if not src_assignments:
            return False

        # Önce kaynak haftanın atamalarını hedef haftaya birebir aktar
        self.db.clear_week_assignments(self.target_week, preserve_fixed=False)
        for a in src_assignments:
            new_assign = Assignment(
                week_start=self.target_week,
                day_id=a.day_id,
                location_id=a.location_id,
                slot_index=a.slot_index,
                teacher_id=a.teacher_id,
                fixed=a.fixed,
                notes=a.notes
            )
            self.db.save_assignment(new_assign)

        # Eğer gün kaydırma (rotasyon) istenmişse:
        if self.shift_mode == "shift_day" and self.shift_steps != 0:
            shifter = ShiftScheduleCommand(
                db=self.db,
                week_start=self.target_week,
                shift_type="day",
                steps=self.shift_steps,
                preserve_fixed=self.preserve_fixed
            )
            shifter.execute()

        # Eğer nöbet yeri kaydırma istenmişse:
        elif self.shift_mode == "shift_loc" and self.shift_steps != 0:
            shifter = ShiftScheduleCommand(
                db=self.db,
                week_start=self.target_week,
                shift_type="location",
                steps=self.shift_steps,
                preserve_fixed=self.preserve_fixed
            )
            shifter.execute()

        return True

    def undo(self) -> bool:
        self.db.clear_week_assignments(self.target_week, preserve_fixed=False)
        for a in self.old_target_assignments:
            self.db.save_assignment(a)
        return True


class DutyService:
    def __init__(self, db: Database, undo_manager: Optional[UndoManager] = None):
        self.db = db
        self.undo_manager = undo_manager or UndoManager()
        self.last_error: Optional[str] = None

    def get_grid_matrix(self, week_start: str) -> Dict[str, Any]:
        """
        Arayüz tablosunun kolayca render edilmesi için gün, yer ve atamaları matris haline getirir.
        """
        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)
        assignments = self.db.get_assignments_for_week(week_start)
        teachers = {t.id: t for t in self.db.get_teachers()}

        assign_map: Dict[Tuple[str, str, int], Assignment] = {}
        for a in assignments:
            assign_map[(a.day_id, a.location_id, a.slot_index)] = a

        # Eksik slotlar varsa otomatik oluştur
        for d in days:
            for loc in locations:
                for slot in range(loc.capacity):
                    key = (d.id, loc.id, slot)
                    if key not in assign_map:
                        new_assign = Assignment(
                            week_start=week_start,
                            day_id=d.id,
                            location_id=loc.id,
                            slot_index=slot,
                            teacher_id=None
                        )
                        self.db.save_assignment(new_assign)
                        assign_map[key] = new_assign

        return {
            "days": days,
            "locations": locations,
            "assignments": assign_map,
            "teachers": teachers
        }

    def move_or_swap(
        self,
        week_start: str,
        source_day_id: str,
        source_loc_id: str,
        source_slot: int,
        target_day_id: str,
        target_loc_id: str,
        target_slot: int
    ) -> bool:
        self.last_error = None
        cmd = MoveOrSwapCommand(
            self.db,
            week_start,
            source_day_id,
            source_loc_id,
            source_slot,
            target_day_id,
            target_loc_id,
            target_slot
        )
        success = self.undo_manager.execute_command(cmd)
        if not success:
            self.last_error = getattr(cmd, "error_message", None)
        return success

    def assign_teacher(self, assignment: Assignment, teacher_id: Optional[str]) -> bool:
        self.last_error = None
        cmd = AssignTeacherCommand(self.db, assignment, teacher_id)
        success = self.undo_manager.execute_command(cmd)
        if not success:
            self.last_error = getattr(cmd, "error_message", None)
        return success

    def toggle_fixed(self, assignment_id: str) -> bool:
        cmd = ToggleFixedCommand(self.db, assignment_id)
        return self.undo_manager.execute_command(cmd)

    def shift_schedule(
        self,
        week_start: str,
        shift_type: str = "day",
        steps: int = 1,
        preserve_fixed: bool = True
    ) -> bool:
        cmd = ShiftScheduleCommand(
            self.db,
            week_start=week_start,
            shift_type=shift_type,
            steps=steps,
            preserve_fixed=preserve_fixed
        )
        return self.undo_manager.execute_command(cmd)

    def copy_week_to_next(
        self,
        source_week: str,
        target_week: str,
        shift_days: int = 0,
        shift_mode: str = "same",
        shift_steps: int = 1,
        preserve_fixed: bool = True
    ) -> bool:
        cmd = CopyWeekCommand(
            self.db,
            source_week=source_week,
            target_week=target_week,
            shift_days=shift_days,
            shift_mode=shift_mode,
            shift_steps=shift_steps,
            preserve_fixed=preserve_fixed
        )
        return self.undo_manager.execute_command(cmd)

    def parse_duty_table_pdf(self, pdf_path: str, target_week: str) -> List[Assignment]:
        """
        PDF formatındaki haftalık nöbet çizelgesini (resmi MEB tablosu veya sistem çıktısı)
        ayrıştırır ve hedef hafta için Assignment listesi üretir.
        Hem standart (satırlar Günler, sütunlar Yerler) hem de devrik (satırlar Yerler, sütunlar Günler)
        tablo formatlarını ve çoklu öğretmen hücrelerini destekler.
        """
        days = self.db.get_days()
        locations = self.db.get_locations()
        teachers = self.db.get_teachers()

        day_map = {unicodedata.normalize('NFC', d.name).upper(): d for d in days}
        loc_map = {unicodedata.normalize('NFC', l.name).upper(): l for l in locations}
        t_map = {unicodedata.normalize('NFC', t.name).upper(): t for t in teachers}
        t_names = list(t_map.keys())

        def clean_pdf_text(s: Any) -> str:
            if not s:
                return ""
            s = unicodedata.normalize("NFC", str(s))
            return " ".join(s.split()).strip()

        def match_teacher(name_text: str) -> Optional[Teacher]:
            if not name_text:
                return None
            cleaned = clean_pdf_text(name_text)
            canon = NAME_ALIASES.get(cleaned, cleaned).upper()
            if canon in t_map:
                return t_map[canon]
            for t_upper, t_obj in t_map.items():
                if t_upper == canon or t_obj.name.upper() == canon:
                    return t_obj
            matches = MatchingService.find_best_matches(canon, t_names, threshold=0.6)
            if matches:
                return t_map[matches[0][0]]
            return None

        assignments: List[Assignment] = []
        doc = pymupdf.open(pdf_path)
        day_names_upper = set(day_map.keys())

        for page in doc:
            tabs = page.find_tables()
            if not tabs:
                continue
            table = tabs[0].extract()
            if not table or len(table) < 2:
                continue

            header_row_idx = None
            for r_idx, row in enumerate(table):
                non_empty = [clean_pdf_text(c).upper() for c in row if c]
                if any('KAT' in c or 'BAHÇE' in c or 'ZEMİN' in c for c in non_empty) or any(any(dn in c for dn in day_names_upper) for c in non_empty):
                    header_row_idx = r_idx
                    break
            if header_row_idx is None:
                header_row_idx = 0

            header_cols = [clean_pdf_text(c).upper() for c in table[header_row_idx]]
            header_day_count = sum(1 for c in header_cols if any(dn in c for dn in day_names_upper))
            is_transposed = header_day_count >= 3

            if not is_transposed:
                for row in table[header_row_idx + 1:]:
                    if not row or not any(row):
                        continue
                    first_col = clean_pdf_text(row[0]).upper()
                    matched_day = None
                    for d_name, d_obj in day_map.items():
                        if d_name in first_col or first_col in d_name:
                            matched_day = d_obj
                            break
                    if not matched_day:
                        continue

                    for c_idx in range(1, len(row)):
                        if c_idx >= len(header_cols):
                            break
                        col_header = header_cols[c_idx]
                        raw_cell = row[c_idx]
                        if not raw_cell:
                            continue
                        lines = [clean_pdf_text(l) for l in str(raw_cell).split('\n') if clean_pdf_text(l)]
                        if not lines:
                            continue

                        target_locs = []
                        if col_header == 'BAHÇE' and 'BAHÇE 1' in loc_map and 'BAHÇE 2' in loc_map:
                            target_locs = [loc_map['BAHÇE 1'], loc_map['BAHÇE 2']]
                        else:
                            for l_name, l_obj in loc_map.items():
                                if l_name in col_header or col_header in l_name:
                                    target_locs = [l_obj]
                                    break
                        if not target_locs:
                            continue

                        if len(target_locs) == 1 and target_locs[0].capacity == 1 and len(lines) > 1:
                            whole_name = ' '.join(lines)
                            m_whole = match_teacher(whole_name)
                            if m_whole:
                                lines = [whole_name]

                        for l_idx, line in enumerate(lines):
                            matched_t = match_teacher(line)
                            t_id = matched_t.id if matched_t else None
                            if len(target_locs) > 1:
                                loc = target_locs[l_idx] if l_idx < len(target_locs) else target_locs[-1]
                                slot = 0
                            else:
                                loc = target_locs[0]
                                slot = l_idx if loc.capacity > 1 else 0

                            assignments.append(Assignment(
                                week_start=target_week,
                                day_id=matched_day.id,
                                location_id=loc.id,
                                slot_index=slot,
                                teacher_id=t_id
                            ))
            else:
                for row in table[header_row_idx + 1:]:
                    if not row or not any(row):
                        continue
                    first_col = clean_pdf_text(row[0]).upper()
                    target_locs = []
                    if first_col == 'BAHÇE' and 'BAHÇE 1' in loc_map and 'BAHÇE 2' in loc_map:
                        target_locs = [loc_map['BAHÇE 1'], loc_map['BAHÇE 2']]
                    else:
                        for l_name, l_obj in loc_map.items():
                            if l_name in first_col or first_col in l_name:
                                target_locs = [l_obj]
                                break
                    if not target_locs:
                        continue

                    for c_idx in range(1, len(row)):
                        if c_idx >= len(header_cols):
                            break
                        day_col_header = header_cols[c_idx]
                        matched_day = None
                        for d_name, d_obj in day_map.items():
                            if d_name in day_col_header or day_col_header in d_name:
                                matched_day = d_obj
                                break
                        if not matched_day:
                            continue

                        raw_cell = row[c_idx]
                        if not raw_cell:
                            continue
                        lines = [clean_pdf_text(l) for l in str(raw_cell).split('\n') if clean_pdf_text(l)]
                        if not lines:
                            continue

                        if len(target_locs) == 1 and target_locs[0].capacity == 1 and len(lines) > 1:
                            whole_name = ' '.join(lines)
                            m_whole = match_teacher(whole_name)
                            if m_whole:
                                lines = [whole_name]

                        for l_idx, line in enumerate(lines):
                            matched_t = match_teacher(line)
                            t_id = matched_t.id if matched_t else None
                            if len(target_locs) > 1:
                                loc = target_locs[l_idx] if l_idx < len(target_locs) else target_locs[-1]
                                slot = 0
                            else:
                                loc = target_locs[0]
                                slot = l_idx if loc.capacity > 1 else 0

                            assignments.append(Assignment(
                                week_start=target_week,
                                day_id=matched_day.id,
                                location_id=loc.id,
                                slot_index=slot,
                                teacher_id=t_id
                            ))

        return assignments
