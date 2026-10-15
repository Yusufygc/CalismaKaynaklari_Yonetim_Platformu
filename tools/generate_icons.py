"""Kaynak Yönetim Platformu çoklu çözünürlüklü uygulama ikonu üreticisi.

PySide6 QPainter vektörel çizim motoru ve Pillow ile Windows standardında
(16, 24, 32, 48, 64, 128, 256) çok boyutlu `.ico` ve yüksek çözünürlüklü `.png` üretir.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)


def render_master_icon(size: int = 1024) -> QImage:
    """1024x1024 piksel üstün kaliteli ana ikon görselini çizer."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # 1. Taban Squircle (Windows 11 / Modern Masaüstü Geometrisi)
    pad = 60.0
    rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
    radius = 215.0

    # Çok katmanlı yumuşak gölge
    for offset, alpha in [(14, 55), (28, 45), (52, 25)]:
        s_path = QPainterPath()
        s_path.addRoundedRect(QRectF(pad, pad + offset, size - 2 * pad, size - 2 * pad), radius, radius)
        p.fillPath(s_path, QColor(0, 0, 0, alpha))

    # Taban gradyanı: Akademik Mürekkep Laciverti -> Gece Yarısı Obsidiyen
    bg_path = QPainterPath()
    bg_path.addRoundedRect(rect, radius, radius)

    bg_grad = QLinearGradient(pad, pad, size - pad, size - pad)
    bg_grad.setColorAt(0.0, QColor("#1E2A4A"))  # Derin Akademik Mavi
    bg_grad.setColorAt(0.4, QColor("#0F172A"))  # Koyu arduvaz
    bg_grad.setColorAt(1.0, QColor("#030712"))  # Gece yarısı siyahı
    p.fillPath(bg_path, bg_grad)

    # İnce radyal cam ışıması (Cyan/Royal)
    glow = QRadialGradient(512, 490, 480)
    glow.setColorAt(0.0, QColor(56, 189, 248, 60))
    glow.setColorAt(0.5, QColor(37, 99, 235, 25))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillPath(bg_path, glow)

    # Kenar cam vurgusu (1px mikro-border)
    rim_grad = QLinearGradient(pad, pad, pad, size - pad)
    rim_grad.setColorAt(0.0, QColor(255, 255, 255, 130))
    rim_grad.setColorAt(0.3, QColor(56, 189, 248, 90))
    rim_grad.setColorAt(0.7, QColor(30, 58, 138, 45))
    rim_grad.setColorAt(1.0, QColor(255, 255, 255, 20))
    p.strokePath(bg_path, QPen(QBrush(rim_grad), 4.5))

    # 2. Açık Bilgi Defteri / Kitap Figürü
    cx = 512.0
    spine_top = 280.0
    spine_bot = 760.0
    page_w = 370.0

    # Kitap altı gölgesi
    book_sh = QPainterPath()
    book_sh.addEllipse(QPointF(cx, spine_bot + 25), 400.0, 60.0)
    p.fillPath(book_sh, QColor(0, 0, 0, 110))

    # Sert Cilt Tabanı (Lacivert deri kapak)
    hc = QPainterPath()
    hc.moveTo(cx, spine_bot + 35)
    hc.cubicTo(cx - 140, spine_bot + 25, cx - 260, spine_bot + 35, cx - page_w - 20, spine_bot - 15)
    hc.lineTo(cx - page_w - 20, spine_top + 60)
    hc.cubicTo(cx - 260, spine_top - 5, cx - 140, spine_top + 5, cx, spine_top + 20)
    hc.cubicTo(cx + 140, spine_top + 5, cx + 260, spine_top - 5, cx + page_w + 20, spine_top + 60)
    hc.lineTo(cx + page_w + 20, spine_bot - 15)
    hc.cubicTo(cx + 260, spine_bot + 35, cx + 140, spine_bot + 25, cx, spine_bot + 35)
    hc.closeSubpath()

    hc_grad = QLinearGradient(cx, spine_top, cx, spine_bot + 40)
    hc_grad.setColorAt(0.0, QColor("#0F172A"))
    hc_grad.setColorAt(0.5, QColor("#1E293B"))
    hc_grad.setColorAt(1.0, QColor("#020617"))
    p.fillPath(hc, hc_grad)
    p.strokePath(hc, QPen(QColor(56, 189, 248, 85), 3.5))

    # Yelpaze Sayfa Kenarları (Fanned Under-Pages)
    fanned_l = QPainterPath()
    fanned_l.moveTo(cx, spine_bot + 10)
    fanned_l.cubicTo(cx - 130, spine_bot + 5, cx - 250, spine_bot + 10, cx - page_w + 5, spine_bot - 35)
    fanned_l.lineTo(cx - page_w + 5, spine_top + 45)
    fanned_l.cubicTo(cx - 250, spine_top + 10, cx - 130, spine_top + 15, cx, spine_top + 25)
    fanned_l.closeSubpath()
    p.fillPath(fanned_l, QColor("#94A3B8"))

    fanned_r = QPainterPath()
    fanned_r.moveTo(cx, spine_bot + 10)
    fanned_r.cubicTo(cx + 130, spine_bot + 5, cx + 250, spine_bot + 10, cx + page_w - 5, spine_bot - 35)
    fanned_r.lineTo(cx + page_w - 5, spine_top + 45)
    fanned_r.cubicTo(cx + 250, spine_top + 10, cx + 130, spine_top + 15, cx, spine_top + 25)
    fanned_r.closeSubpath()
    p.fillPath(fanned_r, QColor("#94A3B8"))

    # Ana Sayfalar (Sol ve Sağ)
    lp = QPainterPath()
    lp.moveTo(cx, spine_bot - 5)
    lp.cubicTo(cx - 120, spine_bot - 15, cx - 230, spine_bot - 10, cx - page_w + 20, spine_bot - 55)
    lp.cubicTo(cx - page_w + 10, spine_bot - 65, cx - page_w + 10, spine_top + 45, cx - page_w + 20, spine_top + 35)
    lp.cubicTo(cx - 230, spine_top, cx - 120, spine_top + 20, cx, spine_top + 32)
    lp.closeSubpath()

    lp_grad = QLinearGradient(cx - page_w, spine_top, cx, spine_bot)
    lp_grad.setColorAt(0.0, QColor("#FFFFFF"))
    lp_grad.setColorAt(0.7, QColor("#F8FAFC"))
    lp_grad.setColorAt(1.0, QColor("#E2E8F0"))
    p.fillPath(lp, lp_grad)
    p.strokePath(lp, QPen(QColor("#CBD5E1"), 2.0))

    rp = QPainterPath()
    rp.moveTo(cx, spine_bot - 5)
    rp.cubicTo(cx + 120, spine_bot - 15, cx + 230, spine_bot - 10, cx + page_w - 20, spine_bot - 55)
    rp.cubicTo(cx + page_w - 10, spine_bot - 65, cx + page_w - 10, spine_top + 45, cx + page_w - 20, spine_top + 35)
    rp.cubicTo(cx + 230, spine_top, cx + 120, spine_top + 20, cx, spine_top + 32)
    rp.closeSubpath()

    rp_grad = QLinearGradient(cx, spine_top, cx + page_w, spine_bot)
    rp_grad.setColorAt(0.0, QColor("#F1F5F9"))
    rp_grad.setColorAt(0.4, QColor("#FFFFFF"))
    rp_grad.setColorAt(1.0, QColor("#E2E8F0"))
    p.fillPath(rp, rp_grad)
    p.strokePath(rp, QPen(QColor("#CBD5E1"), 2.0))

    # Orta omurga oluk gölgesi
    spine_groove = QPainterPath()
    spine_groove.moveTo(cx - 14, spine_top + 28)
    spine_groove.lineTo(cx + 14, spine_top + 28)
    spine_groove.lineTo(cx + 18, spine_bot - 5)
    spine_groove.lineTo(cx - 18, spine_bot - 5)
    spine_groove.closeSubpath()
    sg_grad = QLinearGradient(cx - 18, 0, cx + 18, 0)
    sg_grad.setColorAt(0.0, QColor(15, 23, 42, 0))
    sg_grad.setColorAt(0.5, QColor(15, 23, 42, 100))
    sg_grad.setColorAt(1.0, QColor(15, 23, 42, 0))
    p.fillPath(spine_groove, sg_grad)

    # Sayfa üzerindeki kaynak/metin satırları
    p.setPen(QPen(QColor("#94A3B8"), 13.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for dy in [105, 175, 245, 315]:
        p.drawLine(QPointF(cx - page_w + 75, spine_top + dy - 15), QPointF(cx - 70, spine_top + dy + 18))
    for dy in [105, 175, 245, 315]:
        p.drawLine(QPointF(cx + 70, spine_top + dy + 18), QPointF(cx + page_w - 75, spine_top + dy - 15))

    # 3. İpeksi Altın Ayraç Şeridi (Antique Gold Bookmark)
    rw = 66.0
    r_top = spine_top + 10
    r_bot = 660.0

    # Ayraç altı derinlik gölgesi
    r_sh = QPainterPath()
    r_sh.moveTo(cx - rw / 2 + 8, r_top + 8)
    r_sh.lineTo(cx + rw / 2 + 8, r_top + 8)
    r_sh.lineTo(cx + rw / 2 + 8, r_bot + 8)
    r_sh.lineTo(cx + 8, r_bot - 24)
    r_sh.lineTo(cx - rw / 2 + 8, r_bot + 8)
    r_sh.closeSubpath()
    p.fillPath(r_sh, QColor(0, 0, 0, 70))

    # Ayraç gövdesi ve çatal kuyruk
    ribbon = QPainterPath()
    ribbon.moveTo(cx - rw / 2, r_top)
    ribbon.lineTo(cx + rw / 2, r_top)
    ribbon.lineTo(cx + rw / 2, r_bot)
    ribbon.lineTo(cx, r_bot - 30)
    ribbon.lineTo(cx - rw / 2, r_bot)
    ribbon.closeSubpath()

    r_grad = QLinearGradient(cx - rw / 2, r_top, cx + rw / 2, r_bot)
    r_grad.setColorAt(0.0, QColor("#FEF08A"))  # İpeksi altın parıltısı
    r_grad.setColorAt(0.3, QColor("#F59E0B"))  # Sıcak amber
    r_grad.setColorAt(0.75, QColor("#D97706"))  # Doygun altın
    r_grad.setColorAt(1.0, QColor("#92400E"))  # Antik bronz
    p.fillPath(ribbon, r_grad)
    p.strokePath(ribbon, QPen(QColor("#78350F"), 2.5))

    # Dikiş çizgisi
    stitch_pen = QPen(QColor(255, 255, 255, 130), 2.0, Qt.PenStyle.DotLine)
    p.setPen(stitch_pen)
    p.drawLine(QPointF(cx - rw / 2 + 7, r_top + 8), QPointF(cx - rw / 2 + 7, r_bot - 36))
    p.drawLine(QPointF(cx + rw / 2 - 7, r_top + 8), QPointF(cx + rw / 2 - 7, r_bot - 36))

    # 4. Safir Bilgi Prizması (Apex Jewel / Nexus)
    nx, ny = cx, spine_top + 10
    prism = QPainterPath()
    p_w, p_h = 36.0, 48.0
    prism.moveTo(nx, ny - p_h)
    prism.lineTo(nx + p_w, ny)
    prism.lineTo(nx, ny + p_h)
    prism.lineTo(nx - p_w, ny)
    prism.closeSubpath()

    p_sh = QPainterPath()
    p_sh.moveTo(nx + 6, ny - p_h + 8)
    p_sh.lineTo(nx + p_w + 6, ny + 8)
    p_sh.lineTo(nx + 6, ny + p_h + 8)
    p_sh.lineTo(nx - p_w + 6, ny + 8)
    p_sh.closeSubpath()
    p.fillPath(p_sh, QColor(0, 0, 0, 75))

    pr_grad = QLinearGradient(nx - p_w, ny - p_h, nx + p_w, ny + p_h)
    pr_grad.setColorAt(0.0, QColor("#7DD3FC"))
    pr_grad.setColorAt(0.35, QColor("#38BDF8"))
    pr_grad.setColorAt(0.75, QColor("#2563EB"))
    pr_grad.setColorAt(1.0, QColor("#1D4ED8"))
    p.fillPath(prism, pr_grad)
    p.strokePath(prism, QPen(QColor("#FFFFFF"), 3.5))

    facet = QPainterPath()
    facet.moveTo(nx, ny - p_h)
    facet.lineTo(nx + p_w, ny)
    facet.lineTo(nx, ny)
    facet.closeSubpath()
    p.fillPath(facet, QColor(255, 255, 255, 90))

    p.end()
    return img


def generate_all_icons(assets_dir: Path | None = None) -> None:
    """Tüm çözünürlüklerdeki PNG ve çok katmanlı ICO dosyasını oluşturur."""
    if assets_dir is None:
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    master_qimg = render_master_icon(1024)
    master_png_path = assets_dir / "icon_master_1024.png"
    master_qimg.save(str(master_png_path))

    pil_master = Image.open(master_png_path)

    # Windows standart çözünürlükleri
    sizes = [16, 24, 32, 48, 64, 128, 256]
    for s in sizes:
        resized = pil_master.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(assets_dir / f"icon_{s}.png")

    # Çok katmanlı Windows ICO dosyası
    ico_path = assets_dir / "icon.ico"
    pil_master.save(str(ico_path), format="ICO", sizes=[(s, s) for s in sizes])

    # Uygulama içi (QML / PySide6 WindowIcon) ana PNG (512x512 ve 256x256)
    png_path = assets_dir / "icon.png"
    pil_master.resize((512, 512), Image.Resampling.LANCZOS).save(str(png_path))

    # Geçici dosyayı temizle
    master_png_path.unlink(missing_ok=True)
    print(f"[OK] Uygulama ikonları üretildi: {ico_path} ({len(sizes)} boyut) ve {png_path}")


if __name__ == "__main__":
    generate_all_icons()
