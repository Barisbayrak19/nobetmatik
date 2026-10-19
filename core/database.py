"""
SQLite Veritabanı Yöneticisi ve Repository Katmanı
"""
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from core.config import DB_PATH
from core.models import (
    SchoolInfo, Teacher, Location, Day, Assignment,
    TeacherLesson, SubstitutionAssignment, AttendanceRecord
)
from core.logger import logger

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            custom_path = self._detect_custom_db_path()
            self.db_path = Path(custom_path) if custom_path else DB_PATH
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _detect_custom_db_path(self) -> Optional[str]:
        try:
            if DB_PATH.exists():
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                r = conn.execute("SELECT value FROM app_settings WHERE key = 'custom_db_path'").fetchone()
                conn.close()
                if r and r["value"] and Path(r["value"]).exists():
                    return r["value"]
        except Exception:
            pass
        return None

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
        except Exception:
            pass
        try:
            yield conn
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
        except Exception:
            pass
        return conn

    def init_db(self):
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS school_info (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT,
                district TEXT,
                academic_year TEXT,
                principal_name TEXT,
                duty_rules TEXT,
                installed INTEGER DEFAULT 0
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                branch TEXT,
                is_active INTEGER DEFAULT 1,
                unavailable_days TEXT DEFAULT '[]',
                notes TEXT,
                created_at TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                capacity INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS days (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                week_start TEXT NOT NULL,
                day_id TEXT NOT NULL,
                location_id TEXT NOT NULL,
                slot_index INTEGER DEFAULT 0,
                teacher_id TEXT,
                fixed INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE(week_start, day_id, location_id, slot_index),
                FOREIGN KEY(day_id) REFERENCES days(id) ON DELETE CASCADE,
                FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE,
                FOREIGN KEY(teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_timetables (
                id TEXT PRIMARY KEY,
                teacher_id TEXT NOT NULL,
                day_name TEXT NOT NULL,
                period INTEGER NOT NULL,
                class_name TEXT,
                subject_code TEXT,
                is_free INTEGER DEFAULT 0,
                UNIQUE(teacher_id, day_name, period),
                FOREIGN KEY(teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS substitution_assignments (
                id TEXT PRIMARY KEY,
                date_str TEXT NOT NULL,
                period INTEGER NOT NULL,
                absent_teacher_id TEXT NOT NULL,
                class_name TEXT,
                subject_code TEXT,
                duty_teacher_id TEXT,
                notes TEXT,
                is_ek_ders INTEGER DEFAULT 0,
                FOREIGN KEY(absent_teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY(duty_teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            );
            """)

            try:
                cursor.execute("ALTER TABLE substitution_assignments ADD COLUMN is_ek_ders INTEGER DEFAULT 0;")
            except Exception:
                pass

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_records (
                id TEXT PRIMARY KEY,
                date_str TEXT NOT NULL,
                teacher_id TEXT,
                teacher_name TEXT NOT NULL,
                branch TEXT,
                status TEXT NOT NULL,
                periods_missed TEXT,
                lessons_missed TEXT,
                slip_path TEXT,
                notes TEXT,
                created_at TEXT
            );
            """)

            try:
                cursor.execute("ALTER TABLE attendance_records ADD COLUMN lessons_missed TEXT DEFAULT '';")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE attendance_records ADD COLUMN slip_path TEXT DEFAULT '';")
            except Exception:
                pass

            # Migrations: Okul kademesi, ikili eğitim ve öğretmen telefon/devre
            for col, col_def in [
                ("school_level", "TEXT DEFAULT 'Ortaokul'"),
                ("education_type", "TEXT DEFAULT 'Normal (Tekli)'"),
                ("daily_periods", "INTEGER DEFAULT 7")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE school_info ADD COLUMN {col} {col_def};")
                except Exception:
                    pass

            for col, col_def in [
                ("phone", "TEXT DEFAULT ''"),
                ("shift_group", "TEXT DEFAULT 'Tümü'"),
                ("is_exempt", "INTEGER DEFAULT 0"),
                ("exemption_reason", "TEXT DEFAULT ''"),
                ("seniority_years", "INTEGER DEFAULT 0"),
                ("exemption_requested", "INTEGER DEFAULT 0"),
                ("preferred_days", "TEXT DEFAULT '[]'"),
                ("avoided_days", "TEXT DEFAULT '[]'"),
                ("is_primary_school", "INTEGER DEFAULT 1")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE teachers ADD COLUMN {col} {col_def};")
                except Exception:
                    pass

            try:
                cursor.execute("ALTER TABLE locations ADD COLUMN shift_group TEXT DEFAULT 'Tümü';")
            except Exception:
                pass

            conn.commit()

    # --- School Info ---
    def get_school_info(self) -> SchoolInfo:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM school_info LIMIT 1").fetchone()
            if row:
                return SchoolInfo(
                    id=row["id"],
                    name=row["name"],
                    city=row["city"] or "",
                    district=row["district"] or "",
                    academic_year=row["academic_year"] or "",
                    principal_name=row["principal_name"] or "",
                    duty_rules=row["duty_rules"] or "",
                    installed=bool(row["installed"]),
                    school_level=row["school_level"] if "school_level" in row.keys() and row["school_level"] else "Ortaokul",
                    education_type=row["education_type"] if "education_type" in row.keys() and row["education_type"] else "Normal (Tekli)",
                    daily_periods=row["daily_periods"] if "daily_periods" in row.keys() and row["daily_periods"] else 7
                )
            return SchoolInfo()

    def save_school_info(self, info: SchoolInfo):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO school_info (id, name, city, district, academic_year, principal_name, duty_rules, installed, school_level, education_type, daily_periods)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                city=excluded.city,
                district=excluded.district,
                academic_year=excluded.academic_year,
                principal_name=excluded.principal_name,
                duty_rules=excluded.duty_rules,
                installed=excluded.installed,
                school_level=excluded.school_level,
                education_type=excluded.education_type,
                daily_periods=excluded.daily_periods;
            """, (info.id, info.name, info.city, info.district, info.academic_year,
                  info.principal_name, info.duty_rules, 1 if info.installed else 0,
                  info.school_level, info.education_type, info.daily_periods))
            conn.commit()

    def get_days(self, active_only: bool = False) -> List[Day]:
        with self.connection() as conn:
            query = "SELECT * FROM days"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY order_num ASC"
            rows = conn.execute(query).fetchall()
            return [Day(id=r["id"], name=r["name"], order_num=r["order_num"], is_active=bool(r["is_active"])) for r in rows]

    def save_day(self, day: Day):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO days (id, name, order_num, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                order_num=excluded.order_num,
                is_active=excluded.is_active;
            """, (day.id, day.name, day.order_num, 1 if day.is_active else 0))
            conn.commit()

    # --- Locations ---
    def get_locations(self, active_only: bool = False) -> List[Location]:
        with self.connection() as conn:
            query = "SELECT * FROM locations"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY order_num ASC"
            rows = conn.execute(query).fetchall()
            return [Location(id=r["id"], name=r["name"], order_num=r["order_num"],
                             capacity=r["capacity"],
                             shift_group=r["shift_group"] if "shift_group" in r.keys() and r["shift_group"] else "Tümü",
                             is_active=bool(r["is_active"])) for r in rows]

    def get_location_by_id(self, loc_id: str) -> Optional[Location]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM locations WHERE id = ?", (loc_id,)).fetchone()
            if row:
                return Location(id=row["id"], name=row["name"], order_num=row["order_num"],
                                capacity=row["capacity"],
                                shift_group=row["shift_group"] if "shift_group" in row.keys() and row["shift_group"] else "Tümü",
                                is_active=bool(row["is_active"]))
            return None

    def save_location(self, loc: Location):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO locations (id, name, order_num, capacity, is_active, shift_group)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                order_num=excluded.order_num,
                capacity=excluded.capacity,
                is_active=excluded.is_active,
                shift_group=excluded.shift_group;
            """, (loc.id, loc.name, loc.order_num, loc.capacity, 1 if loc.is_active else 0, loc.shift_group))
            conn.commit()

    def delete_location(self, loc_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
            conn.commit()

    # --- Teachers ---
    def get_teachers(self, active_only: bool = False) -> List[Teacher]:
        with self.connection() as conn:
            query = "SELECT * FROM teachers"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name COLLATE NOCASE ASC"
            rows = conn.execute(query).fetchall()
            result = []
            for r in rows:
                unavail = json.loads(r["unavailable_days"]) if r["unavailable_days"] else []
                pref_days = json.loads(r["preferred_days"]) if "preferred_days" in r.keys() and r["preferred_days"] else []
                avoid_days = json.loads(r["avoided_days"]) if "avoided_days" in r.keys() and r["avoided_days"] else []
                result.append(Teacher(
                    id=r["id"],
                    name=r["name"],
                    branch=r["branch"] or "",
                    phone=r["phone"] if "phone" in r.keys() and r["phone"] else "",
                    shift_group=r["shift_group"] if "shift_group" in r.keys() and r["shift_group"] else "Tümü",
                    is_active=bool(r["is_active"]),
                    unavailable_days=unavail,
                    notes=r["notes"] or "",
                    created_at=r["created_at"] or "",
                    is_exempt=bool(r["is_exempt"]) if "is_exempt" in r.keys() and r["is_exempt"] is not None else False,
                    exemption_reason=r["exemption_reason"] if "exemption_reason" in r.keys() and r["exemption_reason"] else "",
                    seniority_years=int(r["seniority_years"]) if "seniority_years" in r.keys() and r["seniority_years"] is not None else 0,
                    exemption_requested=bool(r["exemption_requested"]) if "exemption_requested" in r.keys() and r["exemption_requested"] is not None else False,
                    preferred_days=pref_days,
                    avoided_days=avoid_days,
                    is_primary_school=bool(r["is_primary_school"]) if "is_primary_school" in r.keys() and r["is_primary_school"] is not None else True
                ))
            return result

    def get_teacher_by_id(self, teacher_id: str) -> Optional[Teacher]:
        with self.connection() as conn:
            r = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
            if r:
                unavail = json.loads(r["unavailable_days"]) if r["unavailable_days"] else []
                pref_days = json.loads(r["preferred_days"]) if "preferred_days" in r.keys() and r["preferred_days"] else []
                avoid_days = json.loads(r["avoided_days"]) if "avoided_days" in r.keys() and r["avoided_days"] else []
                return Teacher(
                    id=r["id"],
                    name=r["name"],
                    branch=r["branch"] or "",
                    phone=r["phone"] if "phone" in r.keys() and r["phone"] else "",
                    shift_group=r["shift_group"] if "shift_group" in r.keys() and r["shift_group"] else "Tümü",
                    is_active=bool(r["is_active"]),
                    unavailable_days=unavail,
                    notes=r["notes"] or "",
                    created_at=r["created_at"] or "",
                    is_exempt=bool(r["is_exempt"]) if "is_exempt" in r.keys() and r["is_exempt"] is not None else False,
                    exemption_reason=r["exemption_reason"] if "exemption_reason" in r.keys() and r["exemption_reason"] else "",
                    seniority_years=int(r["seniority_years"]) if "seniority_years" in r.keys() and r["seniority_years"] is not None else 0,
                    exemption_requested=bool(r["exemption_requested"]) if "exemption_requested" in r.keys() and r["exemption_requested"] is not None else False,
                    preferred_days=pref_days,
                    avoided_days=avoid_days,
                    is_primary_school=bool(r["is_primary_school"]) if "is_primary_school" in r.keys() and r["is_primary_school"] is not None else True
                )
            return None

    get_teacher = get_teacher_by_id

    def save_teacher(self, teacher: Teacher):
        with self.connection() as conn:
            unavail_json = json.dumps(teacher.unavailable_days, ensure_ascii=False)
            pref_json = json.dumps(teacher.preferred_days, ensure_ascii=False)
            avoid_json = json.dumps(teacher.avoided_days, ensure_ascii=False)
            conn.execute("""
            INSERT INTO teachers (id, name, branch, is_active, unavailable_days, notes, created_at, phone, shift_group,
                                  is_exempt, exemption_reason, seniority_years, exemption_requested, preferred_days, avoided_days, is_primary_school)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                branch=excluded.branch,
                is_active=excluded.is_active,
                unavailable_days=excluded.unavailable_days,
                notes=excluded.notes,
                phone=excluded.phone,
                shift_group=excluded.shift_group,
                is_exempt=excluded.is_exempt,
                exemption_reason=excluded.exemption_reason,
                seniority_years=excluded.seniority_years,
                exemption_requested=excluded.exemption_requested,
                preferred_days=excluded.preferred_days,
                avoided_days=excluded.avoided_days,
                is_primary_school=excluded.is_primary_school;
            """, (teacher.id, teacher.name, teacher.branch, 1 if teacher.is_active else 0,
                  unavail_json, teacher.notes, teacher.created_at, teacher.phone, teacher.shift_group,
                  1 if teacher.is_exempt else 0, teacher.exemption_reason, teacher.seniority_years,
                  1 if teacher.exemption_requested else 0, pref_json, avoid_json, 1 if teacher.is_primary_school else 0))
            conn.commit()

    add_teacher = save_teacher

    def delete_teacher(self, teacher_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
            conn.commit()

    # --- Assignments ---
    def get_assignments_for_week(self, week_start: str) -> List[Assignment]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM assignments WHERE week_start = ?", (week_start,)
            ).fetchall()
            return [
                Assignment(
                    id=r["id"],
                    week_start=r["week_start"],
                    day_id=r["day_id"],
                    location_id=r["location_id"],
                    slot_index=r["slot_index"],
                    teacher_id=r["teacher_id"],
                    fixed=bool(r["fixed"]),
                    notes=r["notes"] or ""
                ) for r in rows
            ]

    def get_assignments_for_teacher(self, teacher_id: str) -> List[Assignment]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM assignments WHERE teacher_id = ? ORDER BY week_start DESC",
                (teacher_id,)
            ).fetchall()
            return [
                Assignment(
                    id=r["id"],
                    week_start=r["week_start"],
                    day_id=r["day_id"],
                    location_id=r["location_id"],
                    slot_index=r["slot_index"],
                    teacher_id=r["teacher_id"],
                    fixed=bool(r["fixed"]),
                    notes=r["notes"] or ""
                ) for r in rows
            ]

    def get_assignment_by_id(self, assign_id: str) -> Optional[Assignment]:
        with self.connection() as conn:
            r = conn.execute("SELECT * FROM assignments WHERE id = ?", (assign_id,)).fetchone()
            if r:
                return Assignment(
                    id=r["id"],
                    week_start=r["week_start"],
                    day_id=r["day_id"],
                    location_id=r["location_id"],
                    slot_index=r["slot_index"],
                    teacher_id=r["teacher_id"],
                    fixed=bool(r["fixed"]),
                    notes=r["notes"] or ""
                )
            return None

    def save_assignment(self, a: Assignment):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO assignments (id, week_start, day_id, location_id, slot_index, teacher_id, fixed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, day_id, location_id, slot_index) DO UPDATE SET
                teacher_id=excluded.teacher_id,
                fixed=excluded.fixed,
                notes=excluded.notes;
            """, (a.id, a.week_start, a.day_id, a.location_id, a.slot_index,
                  a.teacher_id, 1 if a.fixed else 0, a.notes))
            conn.commit()

    def delete_assignment(self, assign_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM assignments WHERE id = ?", (assign_id,))
            conn.commit()

    def clear_week_assignments(self, week_start: str, preserve_fixed: bool = True):
        with self.connection() as conn:
            if preserve_fixed:
                conn.execute(
                    "DELETE FROM assignments WHERE week_start = ? AND fixed = 0",
                    (week_start,)
                )
            else:
                conn.execute(
                    "DELETE FROM assignments WHERE week_start = ?",
                    (week_start,)
                )
            conn.commit()

    def clear_assignments(self, week_start: str, preserve_fixed: bool = False):
        self.clear_week_assignments(week_start, preserve_fixed=preserve_fixed)

    def has_assigned_duties_for_week(self, week_start: str) -> bool:
        """Belirtilen haftada atanmış en az bir öğretmen nöbeti olup olmadığını kontrol eder."""
        with self.connection() as conn:
            r = conn.execute(
                "SELECT COUNT(*) as c FROM assignments WHERE week_start = ? AND teacher_id IS NOT NULL AND teacher_id != ''",
                (week_start,)
            ).fetchone()
            return (r["c"] > 0) if r else False

    # --- Settings ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.connection() as conn:
            r = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return r["value"] if r else default

    def set_setting(self, key: str, value: str):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (key, value))
            conn.commit()

    # --- Timetables ---
    def save_teacher_lesson(self, lesson: TeacherLesson):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO teacher_timetables (id, teacher_id, day_name, period, class_name, subject_code, is_free)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(teacher_id, day_name, period) DO UPDATE SET
                class_name=excluded.class_name,
                subject_code=excluded.subject_code,
                is_free=excluded.is_free;
            """, (lesson.id, lesson.teacher_id, lesson.day_name, lesson.period,
                  lesson.class_name, lesson.subject_code, 1 if lesson.is_free else 0))
            conn.commit()

    def save_teacher_lessons_batch(self, lessons: List[TeacherLesson]):
        with self.connection() as conn:
            data = [
                (l.id, l.teacher_id, l.day_name, l.period, l.class_name, l.subject_code, 1 if l.is_free else 0)
                for l in lessons
            ]
            conn.executemany("""
            INSERT INTO teacher_timetables (id, teacher_id, day_name, period, class_name, subject_code, is_free)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(teacher_id, day_name, period) DO UPDATE SET
                class_name=excluded.class_name,
                subject_code=excluded.subject_code,
                is_free=excluded.is_free;
            """, data)
            conn.commit()

    save_teacher_lessons = save_teacher_lessons_batch

    def get_teacher_lessons(self, teacher_id: str, day_name: Optional[str] = None) -> List[TeacherLesson]:
        with self.connection() as conn:
            query = "SELECT * FROM teacher_timetables WHERE teacher_id = ?"
            params = [teacher_id]
            if day_name:
                query += " AND day_name = ?"
                params.append(day_name)
            query += " ORDER BY period ASC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                TeacherLesson(
                    id=r["id"],
                    teacher_id=r["teacher_id"],
                    day_name=r["day_name"],
                    period=r["period"],
                    class_name=r["class_name"] or "",
                    subject_code=r["subject_code"] or "",
                    is_free=bool(r["is_free"])
                ) for r in rows
            ]

    def clear_teacher_lessons(self, teacher_id: Optional[str] = None):
        with self.connection() as conn:
            if teacher_id:
                conn.execute("DELETE FROM teacher_timetables WHERE teacher_id = ?", (teacher_id,))
            else:
                conn.execute("DELETE FROM teacher_timetables")
            conn.commit()

    def get_all_teacher_lessons(self) -> List[TeacherLesson]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM teacher_timetables ORDER BY teacher_id, day_name, period").fetchall()
            return [
                TeacherLesson(
                    id=r["id"],
                    teacher_id=r["teacher_id"],
                    day_name=r["day_name"],
                    period=r["period"],
                    class_name=r["class_name"] or "",
                    subject_code=r["subject_code"] or "",
                    is_free=bool(r["is_free"])
                ) for r in rows
            ]

    def get_distinct_classes(self) -> List[str]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT class_name FROM teacher_timetables WHERE class_name IS NOT NULL AND class_name != '' ORDER BY class_name"
            ).fetchall()
            return [r["class_name"] for r in rows]

    def get_class_lessons(self, class_name: str) -> List[TeacherLesson]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM teacher_timetables WHERE class_name = ? ORDER BY day_name, period",
                (class_name,)
            ).fetchall()
            return [
                TeacherLesson(
                    id=r["id"],
                    teacher_id=r["teacher_id"],
                    day_name=r["day_name"],
                    period=r["period"],
                    class_name=r["class_name"] or "",
                    subject_code=r["subject_code"] or "",
                    is_free=bool(r["is_free"])
                ) for r in rows
            ]

    def has_timetable_data(self) -> bool:
        with self.connection() as conn:
            row = conn.execute("SELECT count(*) as cnt FROM teacher_timetables WHERE is_free = 0").fetchone()
            return (row["cnt"] > 0) if row else False

    # --- Substitution Assignments ---
    def save_substitution(self, sub: SubstitutionAssignment):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO substitution_assignments (id, date_str, period, absent_teacher_id, class_name, subject_code, duty_teacher_id, notes, is_ek_ders)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                date_str=excluded.date_str,
                period=excluded.period,
                absent_teacher_id=excluded.absent_teacher_id,
                class_name=excluded.class_name,
                subject_code=excluded.subject_code,
                duty_teacher_id=excluded.duty_teacher_id,
                notes=excluded.notes,
                is_ek_ders=excluded.is_ek_ders;
            """, (sub.id, sub.date_str, sub.period, sub.absent_teacher_id,
                  sub.class_name, sub.subject_code, sub.duty_teacher_id, sub.notes,
                  1 if sub.is_ek_ders else 0))
            conn.commit()

    def get_substitutions_for_date(self, date_str: str) -> List[SubstitutionAssignment]:
        return self.get_substitutions(date_str=date_str)

    def get_substitutions(
        self,
        date_str: Optional[str] = None,
        month_str: Optional[str] = None,
        duty_teacher_id: Optional[str] = None,
        absent_teacher_id: Optional[str] = None
    ) -> List[SubstitutionAssignment]:
        with self.connection() as conn:
            query = "SELECT * FROM substitution_assignments WHERE 1=1"
            params = []
            if date_str:
                query += " AND date_str = ?"
                params.append(date_str)
            if month_str:
                query += " AND date_str LIKE ? || '%'"
                params.append(month_str)
            if duty_teacher_id:
                query += " AND duty_teacher_id = ?"
                params.append(duty_teacher_id)
            if absent_teacher_id:
                query += " AND absent_teacher_id = ?"
                params.append(absent_teacher_id)
            query += " ORDER BY date_str ASC, period ASC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                SubstitutionAssignment(
                    id=r["id"],
                    date_str=r["date_str"],
                    period=r["period"],
                    absent_teacher_id=r["absent_teacher_id"],
                    class_name=r["class_name"] or "",
                    subject_code=r["subject_code"] or "",
                    duty_teacher_id=r["duty_teacher_id"],
                    notes=r["notes"] or "",
                    is_ek_ders=bool(r["is_ek_ders"]) if "is_ek_ders" in r.keys() else False
                ) for r in rows
            ]

    def delete_substitution(self, sub_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM substitution_assignments WHERE id = ?", (sub_id,))
            conn.commit()

    # --- App Settings (Key-Value Store) ---
    def get_setting(self, key: str, default: str = "") -> str:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (key, value))
            conn.commit()

    # --- Personel Devam Takip (Attendance Records) ---
    def save_attendance_record(self, record: AttendanceRecord):
        with self.connection() as conn:
            conn.execute("""
            INSERT INTO attendance_records (id, date_str, teacher_id, teacher_name, branch, status, periods_missed, lessons_missed, slip_path, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                date_str=excluded.date_str,
                teacher_id=excluded.teacher_id,
                teacher_name=excluded.teacher_name,
                branch=excluded.branch,
                status=excluded.status,
                periods_missed=excluded.periods_missed,
                lessons_missed=excluded.lessons_missed,
                slip_path=excluded.slip_path,
                notes=excluded.notes;
            """, (record.id, record.date_str, record.teacher_id, record.teacher_name,
                  record.branch, record.status, record.periods_missed, record.lessons_missed,
                  record.slip_path, record.notes, record.created_at))
            conn.commit()

    def get_attendance_records(
        self,
        date_str: Optional[str] = None,
        month_str: Optional[str] = None,
        teacher_id: Optional[str] = None
    ) -> List[AttendanceRecord]:
        with self.connection() as conn:
            query = "SELECT * FROM attendance_records WHERE 1=1"
            params = []
            if date_str:
                query += " AND date_str = ?"
                params.append(date_str)
            if month_str:
                query += " AND date_str LIKE ?"
                params.append(f"{month_str}%")
            if teacher_id:
                query += " AND teacher_id = ?"
                params.append(teacher_id)
            query += " ORDER BY date_str DESC, teacher_name ASC"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                AttendanceRecord(
                    id=r["id"],
                    date_str=r["date_str"],
                    teacher_id=r["teacher_id"],
                    teacher_name=r["teacher_name"],
                    branch=r["branch"] or "",
                    status=r["status"] or "Raporlu",
                    periods_missed=r["periods_missed"] or "Tüm Gün",
                    lessons_missed=r["lessons_missed"] if "lessons_missed" in r.keys() and r["lessons_missed"] else "",
                    slip_path=r["slip_path"] if "slip_path" in r.keys() and r["slip_path"] else "",
                    notes=r["notes"] or "",
                    created_at=r["created_at"] or ""
                ) for r in rows
            ]

    def delete_attendance_record(self, record_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM attendance_records WHERE id = ?", (record_id,))
            conn.commit()

    def delete_attendance_for_teacher_date(self, teacher_id: str, date_str: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM attendance_records WHERE teacher_id = ? AND date_str = ?", (teacher_id, date_str))
            conn.commit()

    def reset_timetables(self):
        """Tüm ders programı kayıtlarını tamamen siler."""
        with self.connection() as conn:
            conn.execute("DELETE FROM teacher_timetables")
            conn.commit()

    def reset_all_data(self, keep_school_info: bool = True, keep_locations: bool = True):
        """
        Sistemi sıfırlar (temiz başlangıç). İsteğe bağlı olarak okul künyesini ve nöbet yerlerini korur.
        """
        with self.connection() as conn:
            conn.execute("DELETE FROM teacher_timetables")
            conn.execute("DELETE FROM substitution_assignments")
            conn.execute("DELETE FROM attendance_records")
            conn.execute("DELETE FROM assignments")
            conn.execute("DELETE FROM teachers")
            if not keep_locations:
                conn.execute("DELETE FROM locations")
            if not keep_school_info:
                conn.execute("DELETE FROM school_info")
                conn.execute("DELETE FROM app_settings")
            conn.commit()

    # --- Güvenlik, Şifre ve Ağ Yönetimi ---
    def is_password_protected(self) -> bool:
        pwd_hash = self.get_setting("admin_password_hash", "")
        return bool(pwd_hash and pwd_hash.strip())

    def set_admin_password(self, password: str):
        if not password or not password.strip():
            self.set_setting("admin_password_hash", "")
        else:
            import hashlib
            h = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()
            self.set_setting("admin_password_hash", h)

    def verify_admin_password(self, password: str) -> bool:
        saved_hash = self.get_setting("admin_password_hash", "")
        if not saved_hash or not saved_hash.strip():
            return True
        import hashlib
        h = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()
        return h == saved_hash.strip()

