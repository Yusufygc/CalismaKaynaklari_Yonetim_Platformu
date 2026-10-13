.pragma library

// Yazı tipi çiftleri (başlık + gövde + okuma). Her rol için sıralı aday listesi vardır; makinede kurulu ilk aday seçilir,
// hiçbiri yoksa son aday (Windows'ta her zaman bulunan bir yazı tipi) kullanılır. Böylece Google Fonts yazı tipleri
// (EB Garamond, Inter, Playfair Display...) kuruluysa kullanılır, değilse benzer bir Windows yazı tipine düşülür.
// Bu dosya yazı tipi DOSYASI paketlemez.

var pairs = [
    {
        id: "varsayilan",
        name: "Akademik Varsayılan",
        description: "Sitka başlıklar, Segoe UI arayüz. Dengeli, modern.",
        heading: ["Sitka Heading", "Georgia"],
        body: ["Segoe UI Variable Text", "Segoe UI"],
        reading: ["Sitka Text", "Georgia"]
    },
    {
        id: "klasik-kitap",
        name: "Klasik Kitap",
        description: "EB Garamond + Lato: makale ve kitap hissi.",
        heading: ["EB Garamond", "Garamond", "Palatino Linotype", "Georgia"],
        body: ["Lato", "Candara", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["EB Garamond", "Garamond", "Georgia"]
    },
    {
        id: "tez-kapagi",
        name: "Tez Kapağı",
        description: "Playfair Display + Source Sans: yüksek kontrastlı başlık, nötr gövde.",
        heading: ["Playfair Display", "Sitka Display", "Book Antiqua", "Georgia"],
        body: ["Source Sans 3", "Source Sans Pro", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["Source Serif 4", "Source Serif Pro", "Cambria", "Georgia"]
    },
    {
        id: "modern-sade",
        name: "Modern Sade",
        description: "Inter: ekranda net, tek ailede sade görünüm.",
        heading: ["Inter", "Segoe UI Variable Display", "Segoe UI"],
        body: ["Inter", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["Inter", "Segoe UI Variable Text", "Segoe UI"]
    },
    {
        id: "prestijli",
        name: "Prestijli",
        description: "Cormorant Garamond + Inter: ince, şık başlık.",
        heading: ["Cormorant Garamond", "Garamond", "Palatino Linotype", "Georgia"],
        body: ["Inter", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["Garamond", "Palatino Linotype", "Georgia"]
    },
    {
        id: "bilimsel",
        name: "Bilimsel",
        description: "IBM Plex: teknik yayınlar için tasarlanmış ikili.",
        heading: ["IBM Plex Serif", "Cambria", "Georgia"],
        body: ["IBM Plex Sans", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["IBM Plex Serif", "Merriweather", "Cambria", "Georgia"]
    },
    {
        id: "poster",
        name: "Poster",
        description: "Montserrat + Merriweather: güçlü geometrik başlık, rahat okuma.",
        heading: ["Montserrat", "Bahnschrift", "Segoe UI Semibold", "Segoe UI"],
        body: ["Source Sans 3", "Source Sans Pro", "Segoe UI Variable Text", "Segoe UI"],
        reading: ["Merriweather", "Georgia"]
    }
]

var defaultId = "varsayilan"

function find(id) {
    for (var i = 0; i < pairs.length; i++) {
        if (pairs[i].id === id)
            return pairs[i]
    }
    return pairs[0]
}

function ids() {
    return pairs.map(function (p) { return p.id })
}

// `candidates` içinden `available` listesinde bulunan ilk adı döner; yoksa son aday.
function pick(candidates, available) {
    for (var i = 0; i < candidates.length; i++) {
        if (available.indexOf(candidates[i]) !== -1)
            return candidates[i]
    }
    return candidates[candidates.length - 1]
}

// {heading, body, reading, installed: {heading: bool, body: bool, reading: bool}}
function resolve(id, available) {
    var p = find(id)
    var result = {
        heading: pick(p.heading, available),
        body: pick(p.body, available),
        reading: pick(p.reading, available)
    }
    result.installed = {
        heading: available.indexOf(p.heading[0]) !== -1,
        body: available.indexOf(p.body[0]) !== -1,
        reading: available.indexOf(p.reading[0]) !== -1
    }
    return result
}
