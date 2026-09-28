pragma Singleton
import QtQuick

QtObject {
    id: root

    // Tema durumu (Bridge'e bağlı)
    property bool isDark: true

    // Arka planlar (Notion / Linear tarzı katmanlar)
    readonly property color bgBase: isDark ? "#0D0F17" : "#F8F9FA"
    readonly property color bgSidebar: isDark ? "#121520" : "#FFFFFF"
    readonly property color bgSurface: isDark ? "#181B28" : "#FFFFFF"
    readonly property color bgElevated: isDark ? "#1F2335" : "#FFFFFF"
    readonly property color bgHover: isDark ? "#262C42" : "#F3F4F6"
    readonly property color bgActive: isDark ? "#2F3652" : "#E5E7EB"

    // Kenarlıklar (Subtle 1px borders)
    readonly property color borderSubtle: isDark ? "#22273A" : "#E5E7EB"
    readonly property color borderStrong: isDark ? "#353D5A" : "#D1D5DB"
    readonly property color borderFocus: isDark ? "#6366F1" : "#4F46E5"

    // Metinler
    readonly property color textPrimary: isDark ? "#F9FAFB" : "#111827"
    readonly property color textSecondary: isDark ? "#9CA3AF" : "#4B5563"
    readonly property color textMuted: isDark ? "#64748B" : "#9CA3AF"
    readonly property color textOnAccent: "#FFFFFF"

    // Vurgu (Accent - Indigo / Electric Sky)
    readonly property color accent: isDark ? "#6366F1" : "#4F46E5"
    readonly property color accentHover: isDark ? "#818CF8" : "#6366F1"
    readonly property color accentSubtle: isDark ? "#1E223D" : "#EEF2FF"
    readonly property color accentText: isDark ? "#A5B4FC" : "#4338CA"

    // Durum Renkleri
    readonly property color statusInbox: "#A855F7"
    readonly property color statusPlanned: "#38BDF8"
    readonly property color statusInProgress: "#F59E0B"
    readonly property color statusCompleted: "#10B981"

    readonly property color statusInboxBg: isDark ? "#281738" : "#F3E8FF"
    readonly property color statusPlannedBg: isDark ? "#13273D" : "#E0F2FE"
    readonly property color statusInProgressBg: isDark ? "#332210" : "#FEF3C7"
    readonly property color statusCompletedBg: isDark ? "#122E23" : "#D1FAE5"

    // Aksiyon Renkleri
    readonly property color danger: "#EF4444"
    readonly property color dangerHover: "#DC2626"
    readonly property color dangerSubtle: isDark ? "#32161A" : "#FEE2E2"
    readonly property color dangerText: isDark ? "#FCA5A5" : "#B91C1C"

    readonly property color favorite: "#EC4899"
    readonly property color favoriteSubtle: isDark ? "#331627" : "#FCE7F3"

    readonly property color pin: "#F59E0B"

    // Gölgeler ve Karartma
    readonly property color shadowColor: isDark ? "#00000088" : "#00000018"
    readonly property color overlayBg: "#00000077"
    readonly property color backdropSubtle: "#00000055"
    readonly property color tooltipBg: isDark ? "#1E2235" : "#1F2937"
    readonly property color chipUnselectedBg: isDark ? "#2A2F45" : "#E2E8F0"
    readonly property color badgeOverlay: isDark ? "#141724DD" : "#FFFFFFEE"
    readonly property color gradientHeaderStart: isDark ? "#1A2238" : "#EEF2FF"
    readonly property color fallbackCategoryColor: "#64748B"

    // Renk Paletleri
    readonly property var categoryPalette: [
        "#6366F1",
        "#38BDF8",
        "#10B981",
        "#F59E0B",
        "#EF4444",
        "#EC4899",
        "#8B5CF6"
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

    // Tipografi
    readonly property string fontFamily: "Inter, Segoe UI, sans-serif"
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
