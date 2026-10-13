.pragma library

// Renk temaları. Her tema 5 temel renkten (primary, accent, highlight, paper, ink) iki mod için (açık/koyu) bütün arayüz
// renklerini türetir; metin ve vurgu renkleri zemine göre WCAG AA (>= 4.5:1) olacak şekilde otomatik düzeltilir, bu
// yüzden yeni bir tema eklemek yalnızca bir `palettes` girdisi eklemektir. `build(id, isDark)` düz bir nesne döner
// ({bgBase: "#RRGGBB", ...}); Theme.qml bunu özelliklere bağlar. Aynı kod testlerde (QJSEngine) denetlenir.
//
// Girdiler: primary = baskın koyu ton (kenar çubuğu tonu, koyu modun zemini), accent = etkileşim rengi (düğme, bağlantı),
// highlight = ikincil vurgu (iğne, odak), paper = açık mod kâğıt zemini, ink = açık mod metin rengi.
// swatches = ayarlar sayfasındaki 5'li renk örneği.

var palettes = [
    {
        id: "akademik-mavi",
        name: "Akademik Mavi",
        description: "Mürekkep laciverti ve akademik mavi; sıcak kâğıt zemin. Varsayılan.",
        primary: "#14213D", accent: "#1E4FA8", highlight: "#B08D2E", paper: "#F4F1E9", ink: "#14213D",
        swatches: ["#14213D", "#1E4FA8", "#B08D2E", "#F4F1E9", "#3A4561"]
    },
    {
        id: "klasik-akademik",
        name: "Klasik Akademik",
        description: "Lacivert ve bordo, krem kâğıt, antik altın. Üniversite, hukuk, tarih.",
        primary: "#1B2A4A", accent: "#7B2D3B", highlight: "#C9A227", paper: "#F5F0E6", ink: "#3A3A3A",
        swatches: ["#1B2A4A", "#7B2D3B", "#F5F0E6", "#C9A227", "#3A3A3A"]
    },
    {
        id: "modern-akademik",
        name: "Modern Akademik",
        description: "Antrasit, füme ve açık gri; vurgu mavi. Makale, tez, sunum.",
        primary: "#2E2E2E", accent: "#3B6EA5", highlight: "#5C5C5C", paper: "#FAFAFA", ink: "#2E2E2E",
        swatches: ["#2E2E2E", "#5C5C5C", "#E8E8E8", "#FAFAFA", "#3B6EA5"]
    },
    {
        id: "kutuphane-vintage",
        name: "Kütüphane (Vintage)",
        description: "Koyu yeşil, hardal, kiremit, krem kağıt, kahve. Edebiyat, felsefe, sanat tarihi.",
        primary: "#2F4F3E", accent: "#A0522D", highlight: "#D4A24C", paper: "#F4EBD9", ink: "#4A3728",
        swatches: ["#2F4F3E", "#D4A24C", "#A0522D", "#F4EBD9", "#4A3728"]
    },
    {
        id: "bilimsel-teknik",
        name: "Bilimsel / Teknik",
        description: "Petrol mavisi ve turkuaz, açık mavi zemin. Mühendislik, tıp, fen bilimleri.",
        primary: "#1F4E5F", accent: "#2B7A78", highlight: "#3FA7A0", paper: "#EEF4F5", ink: "#333333",
        swatches: ["#1F4E5F", "#3FA7A0", "#DCE9EC", "#333333", "#FFFFFF"]
    },
    {
        id: "prestijli-universite",
        name: "Prestijli Üniversite",
        description: "Koyu lacivert, açık mavi, altın, krem; Oxford/Cambridge havası.",
        primary: "#002147", accent: "#0A3D7A", highlight: "#B8860B", paper: "#F8F5EE", ink: "#111111",
        swatches: ["#002147", "#A3C1D9", "#B8860B", "#F8F5EE", "#111111"]
    }
]

var defaultId = "akademik-mavi"

function find(id) {
    for (var i = 0; i < palettes.length; i++) {
        if (palettes[i].id === id)
            return palettes[i]
    }
    return palettes[0]
}

function ids() {
    return palettes.map(function (p) { return p.id })
}

// ---- Renk matematiği ----

function parse(hex) {
    return [parseInt(hex.substr(1, 2), 16), parseInt(hex.substr(3, 2), 16), parseInt(hex.substr(5, 2), 16)]
}

function toHex(rgb) {
    var out = "#"
    for (var i = 0; i < 3; i++) {
        var v = Math.max(0, Math.min(255, Math.round(rgb[i])))
        out += (v < 16 ? "0" : "") + v.toString(16)
    }
    return out.toUpperCase()
}

// a ile b'yi karıştırır; t = b'nin payı (0..1)
function mix(a, b, t) {
    var x = parse(a), y = parse(b)
    return toHex([x[0] + (y[0] - x[0]) * t, x[1] + (y[1] - x[1]) * t, x[2] + (y[2] - x[2]) * t])
}

function luminance(hex) {
    var c = parse(hex).map(function (v) {
        var s = v / 255
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
    })
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}

function contrast(a, b) {
    var la = luminance(a), lb = luminance(b)
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

function worstContrast(fg, backgrounds) {
    var worst = 1000
    for (var i = 0; i < backgrounds.length; i++)
        worst = Math.min(worst, contrast(fg, backgrounds[i]))
    return worst
}

// fg'yi (açık modda siyaha, koyu modda beyaza doğru) tüm zeminlere karşı en az `minimum` kontrast olana dek kaydırır.
function ensure(fg, minimum, backgrounds, dark) {
    var target = dark ? "#FFFFFF" : "#000000"
    var color = fg
    for (var step = 0; step <= 40 && worstContrast(color, backgrounds) < minimum; step++)
        color = mix(fg, target, (step + 1) * 0.025)
    return color
}

// Beyaz yazının üstünde en az `minimum` kontrast verecek şekilde rengi koyulaştırır (düğme zemini).
function ensureWithWhite(color, minimum) {
    var result = color
    for (var step = 0; step <= 40 && contrast("#FFFFFF", result) < minimum; step++)
        result = mix(color, "#000000", (step + 1) * 0.025)
    return result
}

// ---- Tema türetme ----

var STATUS = {
    light: { inbox: "#6D3FC4", planned: "#0B6FA8", progress: "#9A5208", completed: "#08704E" },
    dark: { inbox: "#B99CF7", planned: "#5CC3F5", progress: "#F5B83D", completed: "#3DD6A0" }
}

function build(id, isDark) {
    var p = find(id)
    var t = {}
    var white = "#FFFFFF", black = "#000000"

    if (!isDark) {
        t.bgBase = p.paper
        t.bgSurface = mix(p.paper, white, 0.55)
        t.bgElevated = mix(p.paper, white, 0.85)
        t.bgSidebar = mix(p.paper, p.primary, 0.07)
        t.bgHover = mix(p.paper, p.primary, 0.12)
        t.bgActive = mix(p.paper, p.primary, 0.2)
        t.borderSubtle = mix(p.paper, p.primary, 0.16)
        t.borderStrong = mix(p.paper, p.primary, 0.34)
    } else {
        var base = mix(p.primary, black, 0.72)
        var tint = mix(p.primary, p.paper, 0.16)  // koyu primary'lerde de katmanlar ve kenarlıklar ayırt edilsin
        t.bgBase = base
        t.bgSidebar = mix(base, tint, 0.14)
        t.bgSurface = mix(base, tint, 0.26)
        t.bgElevated = mix(base, tint, 0.38)
        t.bgHover = mix(base, tint, 0.52)
        t.bgActive = mix(base, tint, 0.66)
        t.borderSubtle = mix(base, tint, 0.45)
        t.borderStrong = mix(base, tint, 0.9)
    }
    var surfaces = [t.bgBase, t.bgSidebar, t.bgSurface, t.bgElevated, t.bgHover]

    // Metinler
    if (!isDark) {
        t.textPrimary = ensure(p.ink, 8, surfaces, false)
        t.textSecondary = ensure(mix(p.ink, p.paper, 0.28), 5.5, surfaces, false)
        t.textMuted = ensure(mix(p.ink, p.paper, 0.42), 4.6, surfaces, false)
    } else {
        t.textPrimary = ensure(mix(p.paper, white, 0.35), 9, surfaces, true)
        t.textSecondary = ensure(mix(p.paper, t.bgBase, 0.28), 6, surfaces, true)
        t.textMuted = ensure(mix(p.paper, t.bgBase, 0.45), 4.6, surfaces, true)
    }
    t.textOnAccent = white

    // Vurgu
    var accentSource = isDark ? mix(p.accent, white, 0.16) : p.accent
    t.accent = ensureWithWhite(accentSource, 4.6)
    t.accentHover = isDark ? mix(t.accent, white, 0.12) : mix(t.accent, black, 0.12)
    if (isDark && contrast(white, t.accentHover) < 4.5)
        t.accentHover = t.accent
    t.accentSubtle = isDark ? mix(t.bgBase, t.accent, 0.3) : mix(p.paper, t.accent, 0.12)
    var accentSurfaces = surfaces.concat([t.accentSubtle, t.bgActive])
    t.accentText = ensure(isDark ? mix(t.accent, p.paper, 0.6) : t.accent, 4.8, accentSurfaces, isDark)
    t.borderFocus = isDark ? t.accentText : t.accent

    // Durum renkleri: kendi zeminlerinde ve yüzeylerde okunur
    var status = isDark ? STATUS.dark : STATUS.light
    var keys = [["Inbox", "inbox"], ["Planned", "planned"], ["InProgress", "progress"], ["Completed", "completed"]]
    for (var i = 0; i < keys.length; i++) {
        var raw = status[keys[i][1]]
        var bg = isDark ? mix(t.bgSurface, raw, 0.2) : mix(t.bgSurface, raw, 0.16)
        t["status" + keys[i][0] + "Bg"] = bg
        t["status" + keys[i][0]] = ensure(raw, 4.6, surfaces.concat([bg]), isDark)
    }

    // Aksiyon renkleri
    t.danger = isDark ? "#F0645F" : "#C62828"
    t.dangerHover = isDark ? "#F47E7A" : "#A61F1F"
    t.dangerSubtle = isDark ? mix(t.bgSurface, "#F0645F", 0.2) : mix(t.bgSurface, "#C62828", 0.12)
    t.dangerText = ensure(isDark ? "#FFB4B0" : "#9B1C1C", 4.6, surfaces.concat([t.dangerSubtle]), isDark)
    t.favorite = isDark ? "#F472A8" : "#B8195F"
    t.favoriteSubtle = isDark ? mix(t.bgSurface, "#F472A8", 0.2) : mix(t.bgSurface, "#B8195F", 0.12)
    t.pin = ensure(isDark ? mix(p.highlight, white, 0.3) : p.highlight, 3, [t.bgSurface, t.bgBase], isDark)

    // Diğer
    t.tooltipBg = isDark ? t.bgElevated : mix(p.ink, p.primary, 0.5)
    t.chipUnselectedBg = isDark ? mix(t.bgBase, p.primary, 0.5) : mix(p.paper, p.primary, 0.1)
    t.gradientHeaderStart = t.accentSubtle
    t.popoverBg = isDark ? mix(t.bgBase, p.primary, 0.3) : t.bgElevated
    t.fallbackCategoryColor = t.textMuted
    // Gölge/kaplama renkleri saydamdır; Theme.qml'de sabit tutulur, burada yalnızca temaya bağlı olanlar:
    t.shadowTint = isDark ? "#000000" : p.primary
    t.badgeBase = t.bgSidebar
    return t
}
