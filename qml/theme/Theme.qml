pragma Singleton
import QtQuick
import "palettes.js" as Palettes
import "fonts.js" as Fonts

QtObject {
    id: root

    // Tema durumu (Bridge'e bağlı)
    property bool isDark: true

    // Renkler `palettes.js`ten türetilir: seçili tema (paletteId) ve mod (isDark) değişince tüm renkler birlikte yenilenir.
    // Metin/vurgu çiftleri her temada WCAG AA'dır (tests/test_qml/test_theme_contrast.py bütün temaları denetler).
    property string paletteId: Palettes.defaultId
    readonly property var tokens: Palettes.build(paletteId, isDark)

    readonly property color bgBase: tokens.bgBase
    readonly property color bgSidebar: tokens.bgSidebar
    readonly property color bgSurface: tokens.bgSurface
    readonly property color bgElevated: tokens.bgElevated
    readonly property color bgHover: tokens.bgHover
    readonly property color bgActive: tokens.bgActive
    readonly property color borderSubtle: tokens.borderSubtle
    readonly property color borderStrong: tokens.borderStrong
    readonly property color borderFocus: tokens.borderFocus
    readonly property color textPrimary: tokens.textPrimary
    readonly property color textSecondary: tokens.textSecondary
    readonly property color textMuted: tokens.textMuted
    readonly property color textOnAccent: tokens.textOnAccent
    readonly property color accent: tokens.accent
    readonly property color accentHover: tokens.accentHover
    readonly property color accentSubtle: tokens.accentSubtle
    readonly property color accentText: tokens.accentText
    readonly property color statusInbox: tokens.statusInbox
    readonly property color statusPlanned: tokens.statusPlanned
    readonly property color statusInProgress: tokens.statusInProgress
    readonly property color statusCompleted: tokens.statusCompleted
    readonly property color statusInboxBg: tokens.statusInboxBg
    readonly property color statusPlannedBg: tokens.statusPlannedBg
    readonly property color statusInProgressBg: tokens.statusInProgressBg
    readonly property color statusCompletedBg: tokens.statusCompletedBg
    readonly property color danger: tokens.danger
    readonly property color dangerHover: tokens.dangerHover
    readonly property color dangerSubtle: tokens.dangerSubtle
    readonly property color dangerText: tokens.dangerText
    readonly property color favorite: tokens.favorite
    readonly property color favoriteSubtle: tokens.favoriteSubtle
    readonly property color pin: tokens.pin
    readonly property color tooltipBg: tokens.tooltipBg
    readonly property color chipUnselectedBg: tokens.chipUnselectedBg
    readonly property color gradientHeaderStart: tokens.gradientHeaderStart
    readonly property color fallbackCategoryColor: tokens.fallbackCategoryColor
    readonly property color popoverBg: tokens.popoverBg

    // Saydam kaplamalar ve gölgeler
    readonly property color shadowColor: isDark ? "#00000099" : Qt.alpha(tokens.shadowTint, 0.14)
    readonly property color overlayBg: "#00000077"
    readonly property color backdropSubtle: "#00000055"
    readonly property color badgeOverlay: Qt.alpha(tokens.badgeBase, 0.87)
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

    // Tipografi: yazı tipi çifti (fontPairId) `fonts.js`teki aday listelerinden, makinede kurulu olanlara göre çözülür.
    // fontFamily = arayüz gövdesi, fontHeading = başlıklar, fontReading = alıntı/okunacak metin.
    property string fontPairId: Fonts.defaultId
    readonly property var fontSet: Fonts.resolve(fontPairId, Qt.fontFamilies())
    readonly property string fontFamily: fontSet.body
    readonly property string fontHeading: fontSet.heading
    readonly property string fontReading: fontSet.reading
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
