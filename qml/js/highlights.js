.pragma library

// Alinti renginin akademik anlami (bridge.reader.highlightLabels: [{label, color}]): renk -> etiket, yoksa "Genel".
function labelForColor(color, labels) {
    const wanted = String(color).toUpperCase()
    for (const entry of labels) {
        if (String(entry.color).toUpperCase() === wanted)
            return entry.label
    }
    return "Genel"
}
