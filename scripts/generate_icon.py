"""
Nöbet Yönetim Sistemi - Uygulama Simgesi (Icon) Üretici
Yüksek çözünürlüklü (256x256, 128, 64, 48, 32, 16 px) profesyonel .ico ve .png simge üretir.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_app_icon():
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Arka plan: Yuvarlatılmış Kalkan / Kart (Lacivert - Mavi degraded hissi)
    # Dış gölge
    draw.rounded_rectangle([14, 18, 242, 246], radius=52, fill=(15, 23, 42, 70))
    # Ana arka plan (Deep Navy / MEB Mavisi)
    draw.rounded_rectangle([12, 12, 244, 244], radius=48, fill=(26, 54, 93, 255), outline=(66, 153, 225, 255), width=4)

    # 2. Üst Dekoratif Başlık Bandı (Turkuaz / Altın ton)
    draw.rounded_rectangle([20, 20, 236, 80], radius=38, fill=(43, 108, 176, 255))
    # Üst köşeler yuvarlak kalsın, altını düzleştir
    draw.rectangle([20, 50, 236, 80], fill=(43, 108, 176, 255))

    # 3. Takvim / Nöbet Çizelgesi Kartı
    draw.rounded_rectangle([44, 52, 212, 218], radius=24, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=3)
    # Takvim başlık şeridi (Kırmızı / Bordo MEB kırmızısı)
    draw.rounded_rectangle([44, 52, 212, 92], radius=24, fill=(197, 48, 48, 255))
    draw.rectangle([44, 76, 212, 92], fill=(197, 48, 48, 255))

    # Takvim asma halkaları (metalik gri)
    draw.rounded_rectangle([72, 40, 88, 62], radius=6, fill=(203, 213, 225, 255), outline=(71, 85, 105, 255), width=2)
    draw.rounded_rectangle([168, 40, 184, 62], radius=6, fill=(203, 213, 225, 255), outline=(71, 85, 105, 255), width=2)

    # 4. Takvim İçi Nöbet / Saat Çizgileri
    # Hücre ızgarası (Grid noktaları)
    for x in [72, 108, 144, 180]:
        for y in [112, 140, 168]:
            draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(226, 232, 240, 255))

    # Nöbet rozeti / Onay tiki rozeti (Altın Sarı / Amber)
    draw.ellipse([132, 132, 222, 222], fill=(214, 158, 46, 255), outline=(255, 255, 255, 255), width=4)
    # Rozet içi iç daire
    draw.ellipse([140, 140, 214, 214], fill=(236, 201, 75, 255))

    # Altın rozet içine beyaz kalın nöbet onay onay işareti (Checkmark)
    check_coords = [(154, 174), (168, 192), (200, 154)]
    draw.line(check_coords, fill=(255, 255, 255, 255), width=7, joint="curve")

    # Çift katmanlı çizgiler
    draw.line([(68, 120), (120, 120)], fill=(74, 85, 104, 255), width=6)
    draw.line([(68, 148), (116, 148)], fill=(160, 174, 192, 255), width=5)
    draw.line([(68, 176), (110, 176)], fill=(160, 174, 192, 255), width=5)

    # PNG Kaydet
    png_path = assets_dir / "app_icon.png"
    img.save(png_path, format="PNG")
    print(f"[OK] PNG simge olusturuldu: {png_path}")

    # Çok katmanlı ICO Kaydet
    ico_path = assets_dir / "app_icon.ico"
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"[OK] Cok boyutlu ICO simge olusturuldu: {ico_path}")

if __name__ == "__main__":
    generate_app_icon()
