"""pdfkit: PDF okuma ve calisma modulu (belge deposu, alintilar, kelimeler, Obsidian ciktisi).

Bagimsiz pakettir; uygulamanin geri kalani yalnizca `pdfkit.api` uzerinden kullanir. Paket `services/`,
`controllers/` ve `ui_qml/` import etmez; dis dunya ile baglantilari `pdfkit.app.ports` arayuzleri ve olaylardir.
Paylasilan cekirdek (`core`) ve ortak SQLAlchemy `Base`'i (`models.base`) kullanmasi bilincli istisnadir.
Plan: docs/plans/pdfkit-plan-2026-10-12.md
"""
