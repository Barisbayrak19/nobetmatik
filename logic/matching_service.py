"""
Akıllı İsim Eşleştirme ve Çelişki Çözücü
Türkçe karakter duyarlı, kısaltma ve benzerlik analizi.
"""
from typing import List, Tuple, Optional, Dict
import difflib

TURKISH_MAP = {
    'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö'
}

def tr_upper(s: str) -> str:
    if not s:
        return ""
    result = []
    for char in s:
        if char in TURKISH_MAP:
            result.append(TURKISH_MAP[char])
        else:
            result.append(char.upper())
    return "".join(result).strip()

def normalize_text(s: str) -> str:
    return " ".join(tr_upper(s).replace(".", " ").split())

class MatchingService:
    @staticmethod
    def calculate_similarity(name1: str, name2: str) -> float:
        n1 = normalize_text(name1)
        n2 = normalize_text(name2)
        if not n1 or not n2:
            return 0.0
        if n1 == n2:
            return 1.0

        parts1 = n1.split()
        parts2 = n2.split()

        # Kısaltma eşleşmesi kontrolü (Örn: M BEYDİLLİ vs MEHMET BEYDİLLİ)
        if len(parts1) >= 2 and len(parts2) >= 2:
            surname1 = parts1[-1]
            surname2 = parts2[-1]
            if surname1 == surname2:
                # Soyad aynı, ilk harf aynı mı?
                if parts1[0][0] == parts2[0][0]:
                    return 0.92

        # Biri diğerini içeriyor mu? (Örn: İLKNUR AKBAŞ vs İLKNUR AKBAŞ UZUN)
        if n1 in n2 or n2 in n1:
            return 0.88

        # Difflib benzerlik skoru
        ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
        return round(ratio, 2)

    @classmethod
    def find_best_matches(
        cls,
        candidate_name: str,
        existing_names: List[str],
        threshold: float = 0.60
    ) -> List[Tuple[str, float]]:
        scores = []
        for name in existing_names:
            sim = cls.calculate_similarity(candidate_name, name)
            if sim >= threshold:
                scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
