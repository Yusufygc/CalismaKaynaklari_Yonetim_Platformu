pragma Singleton
import QtQuick

QtObject {
    id: root

    // Tema durumu (Bridge'e bağlı)
    property bool isDark: true

    // Akademik palet: mürekkep laciverti + kâğıt tonları. Açık temada sıcak "kâğıt" zemin (göz yormaz), koyu temada
    // derin lacivert zemin; metinler her iki temada da WCAG AA (≥ 4.5:1) kontrastın üstündedir.

    // Arka planlar (katmanlı yüzeyler)
    readonly property color bgBase: isDark ? "#0B1020" : "#F4F1E9"
    readonly property color bgSidebar: isDark ? "#0F1629" : "#ECE8DC"
    readonly property color bgSurface: isDark ? "#141C33" : "#FBFAF6"
    readonly property color bgElevated: isDark ? "#1B2542" : "#FFFFFF"
    readonly property color bgHover: isDark ? "#243154" : "#E7E2D3"
    readonly property color bgActive: isDark ? "#2E3E69" : "#DAD3BF"

    // Kenarlıklar
    readonly property color borderSubtle: isDark ? "#25314F" : "#DDD6C3"
    readonly property color borderStrong: isDark ? "#3A4B78" : "#BDB49B"
    readonly property color borderFocus: isDark ? "#7FA8FF" : "#1E4FA8"

    // Metinler
    readonly property color textPrimary: isDark ? "#F5F2EA" : "#14213D"
    readonly property color textSecondary: isDark ? "#C3CCE3" : "#3A4561"
    readonly property color textMuted: isDark ? "#9AA7C8" : "#525D7A"
    readonly property color textOnAccent: "#FFFFFF"

    // Vurgu (akademik mavi)
    readonly property color accent: isDark ? "#3866D6" : "#1E4FA8"
    readonly property color accentHover: isDark ? "#5E8CF0" : "#2A63C9"
    readonly property color accentSubtle: isDark ? "#182750" : "#E4EBF8"
    readonly property color accentText: isDark ? "#A9C2FF" : "#1B3F86"

    // Durum Renkleri (açık temada daha koyu, koyu temada daha parlak: iki yüzeyde de okunur)
    readonly property color statusInbox: isDark ? "#B99CF7" : "#6D3FC4"
    readonly property color statusPlanned: isDark ? "#5CC3F5" : "#0B6FA8"
    readonly property color statusInProgress: isDark ? "#F5B83D" : "#9A5208"
    readonly property color statusCompleted: isDark ? "#3DD6A0" : "#08704E"

    readonly property color statusInboxBg: isDark ? "#2A1D47" : "#EBE3FA"
    readonly property color statusPlannedBg: isDark ? "#10304A" : "#DCEEF9"
    readonly property color statusInProgressBg: isDark ? "#3A2A0F" : "#FAEBCF"
    readonly property color statusCompletedBg: isDark ? "#0F3328" : "#D5F0E3"

    // Aksiyon Renkleri
    readonly property color danger: isDark ? "#F0645F" : "#C62828"
    readonly property color dangerHover: isDark ? "#F47E7A" : "#A61F1F"
    readonly property color dangerSubtle: isDark ? "#3A1B20" : "#FBE3E1"
    readonly property color dangerText: isDark ? "#FFB4B0" : "#9B1C1C"

    readonly property color favorite: isDark ? "#F472A8" : "#B8195F"
    readonly property color favoriteSubtle: isDark ? "#3A1A2D" : "#FADCE9"

    readonly property color pin: isDark ? "#F2C04D" : "#A8730E"

    // Gölgeler ve Karartma
    readonly property color shadowColor: isDark ? "#00000099" : "#14213D22"
    readonly property color overlayBg: "#00000077"
    readonly property color backdropSubtle: "#00000055"
    readonly property color tooltipBg: isDark ? "#1B2542" : "#14213D"
    readonly property color chipUnselectedBg: isDark ? "#27345A" : "#E3DDCB"
    readonly property color badgeOverlay: isDark ? "#0F1629DD" : "#FBFAF6EE"
    readonly property color gradientHeaderStart: isDark ? "#16223F" : "#E4EBF8"
    readonly property color fallbackCategoryColor: "#5B6683"
    readonly property color popoverBg: isDark ? "#182140" : "#FFFFFF"
    readonly property color swatchBorderLight: "#FFFFFF44"
    readonly property color markerBorderLight: "#FFFFFF66"
    readonly property color thumbnailOverlay: "#00000045"

    // Renk Paletleri (kategori rengi seçici)
    readonly property var categoryPalette: [
        "#1E4FA8", // Oxford mavisi
        "#0F766E", // Çam yeşili-teal
        "#15803D", // Orman yeşili
        "#B35F0B", // Kehribar
        "#9F1239", // Bordo
        "#6D3FC4", // Mor
        "#475569"  // Arduvaz
    ]

    // Alıntı Fosforlu Renk Paleti
    readonly property var highlightPalette: [
        "#EAB308", // Sarı
        "#22C55E", // Yeşil
        "#06B6D4", // Camgöbeği
        "#A855F7", // Mor
        "#EC4899"  // Pembe
    ]

    // Radius Değerleri
    readonly property int radiusXs: 4
    readonly property int radiusSm: 6
    readonly property int radiusMd: 10
    readonly property int radiusLg: 14
    readonly property int radiusXl: 18
    readonly property int radiusPill: 999

    // Tipografi: arayüz Segoe UI Variable (modern, net), başlıklar Sitka Heading (akademik serif), okunacak metin
    // (alıntılar) Sitka Text. Kurulu değilse sıradaki aday seçilir (Georgia / Segoe UI hemen her Windows'ta vardır).
    function pickFamily(candidates, fallback) {
        const available = Qt.fontFamilies()
        for (let i = 0; i < candidates.length; i++) {
            if (available.indexOf(candidates[i]) !== -1)
                return candidates[i]
        }
        return fallback
    }
    readonly property string fontFamily: pickFamily(["Segoe UI Variable Text", "Segoe UI", "Inter"], "Segoe UI")
    readonly property string fontHeading: pickFamily(["Sitka Heading", "Georgia", "Cambria", "Palatino Linotype"], "Georgia")
    readonly property string fontReading: pickFamily(["Sitka Text", "Georgia", "Cambria", "Palatino Linotype"], "Georgia")
    readonly property int fontXs: 11
    readonly property int fontSm: 12
    readonly property int fontBase: 13
    readonly property int fontMd: 15
    readonly property int fontLg: 18
    readonly property int fontXl: 22
    readonly property int font2Xl: 28

    // Animasyon Süreleri
    readonly property int animFast: 150
    readonly property int animBase: 250
    readonly property int animSlow: 350
}
