import QtQuick
import QtQuick.Controls
import "../theme"
import "../js/highlights.js" as Highlights

// PDF sayfasında metin seçilince beliren yüzen araç çubuğu (5 renkli alıntı kaydetme + "Kelime Havuzuna Ekle")
// ve kelime çevirisi popover'ı. Sayfa (`paper`) üzerine bindirilir; seçim `pdfSelection` (PdfSelection) ile gelir.
// Alıntı/kelime kaydı `bridge.reader.addPdfHighlight/addPdfVocabulary` ile yapılır (seçim page-point haritası).
Item {
    id: root

    property var pdfSelection      // PdfSelection (hold/text/from/to/clear())
    property Item paper            // Sayfa kâğıdı (pageScale, width, height)
    property int pageIndex: 0
    property var resource

    readonly property bool popoverVisible: newVocabPopover.visible
    function closeVocabulary() { newVocabPopover.visible = false }

    anchors.fill: parent
    z: 20

    // Yeni secim -> renkli highlight kaydetme (Kindle tarzi yuzen toolbar)
    // Secimin hemen ustunde/altinda konumlanir (sayfa altina sabit degil),
    // sayfa sinirlari disina tasmayacak sekilde kenarlara yaslanir.
    Rectangle {
        id: newHighlightToolbar
        objectName: "newHighlightToolbar"
        visible: root.pdfSelection.hold && root.pdfSelection.text.trim().length > 0
        z: 20
        implicitWidth: newHighlightRow.implicitWidth + 16
        implicitHeight: 36
        radius: Theme.radiusPill
        color: Theme.popoverBg
        border.width: 1
        border.color: Theme.borderStrong

        // Secim, araç çubuğundaki bir düğmeye tıklanırken (fare imleci
        // metnin üzerinden geçerken) DragHandler'ın kendisini bozup
        // root.pdfSelection.from/to'yu sıfırlamasına karşı: toolbar görünür
        // olduğu anda değerler burada dondurulur, düğmeler canlı
        // root.pdfSelection.* yerine bu sabit kopyaları kullanır (bkz.
        // "highlight çalışmıyor" hatası).
        property point capturedFrom: Qt.point(0, 0)
        property point capturedTo: Qt.point(0, 0)
        property string capturedText: ""
        onVisibleChanged: {
            if (visible) {
                capturedFrom = root.pdfSelection.from
                capturedTo = root.pdfSelection.to
                capturedText = root.pdfSelection.text
            }
        }

        // QPdfDocument.getSelection() PDF *nokta* (pt) uzayinda calisir; PdfSelection.from/to ise
        // ekrandaki piksel. Zoom %100 degilken piksel gonderilirse rastgele yer secilirdi.
        readonly property real safeScale: root.paper.pageScale > 0 ? root.paper.pageScale : 1
        readonly property point pointFrom: Qt.point(capturedFrom.x / safeScale, capturedFrom.y / safeScale)
        readonly property point pointTo: Qt.point(capturedTo.x / safeScale, capturedTo.y / safeScale)

        // bridge.reader.addPdfHighlight / addPdfVocabulary'nin bekledigi secim haritasi (page-point uzayinda)
        function selectionMap(page) {
            return { page: page, fromX: pointFrom.x, fromY: pointFrom.y, toX: pointTo.x, toY: pointTo.y }
        }

        property real selectionCenterX: (capturedFrom.x + capturedTo.x) / 2
        property real selectionTopY: Math.min(capturedFrom.y, capturedTo.y)
        property real selectionBottomY: Math.max(capturedFrom.y, capturedTo.y)
        property bool fitsAbove: selectionTopY - height - 10 >= 0

        x: Math.max(0, Math.min(selectionCenterX - width / 2, parent.width - width))
        y: {
            if (fitsAbove) return selectionTopY - height - 10
            return Math.min(selectionBottomY + 10, parent.height - height)
        }

        Row {
            id: newHighlightRow
            anchors.centerIn: parent
            spacing: 8

            Repeater {
                model: Theme.highlightPalette
                delegate: Rectangle {
                    required property string modelData
                    width: 22
                    height: 22
                    radius: 11
                    color: modelData
                    border.width: 1
                    border.color: Theme.swatchBorderLight

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        ToolTip.visible: containsMouse
                        ToolTip.text: Highlights.labelForColor(parent.modelData, bridge.reader.highlightLabels)
                        onClicked: {
                            if (newHighlightToolbar.capturedText.trim().length > 0 && root.resource) {
                                bridge.reader.addPdfHighlight(
                                    root.resource.id, root.resource.pdfFileUrl,
                                    newHighlightToolbar.selectionMap(root.pageIndex),
                                    parent.modelData
                                )
                            }
                            root.pdfSelection.clear()
                        }
                    }
                }
            }

            Rectangle {
                width: 1
                height: 18
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.borderSubtle
            }

            AppIconButton {
                anchors.verticalCenter: parent.verticalCenter
                iconName: "fa5s.language"
                iconSize: 13
                tooltip: "Kelime Havuzuna Ekle"
                onClicked: {
                    newVocabPopover.word = newHighlightToolbar.capturedText.trim()
                    newVocabPopover.translationText = ""
                    newVocabPopover.visible = true
                }
            }
        }
    }

    // Secili kelimeyi/ifadeyi Bilgi Havuzu'na (kelime listesi) ekleme
    // popover'i -- HTML okuyucudaki "Kelime Havuzuna Ekle" ozelligiyle
    // ayni: bridge.reader.addVocabulary(resourceId, word, translation).
    Rectangle {
        id: newVocabPopover
        objectName: "newVocabPopover"
        property string word: ""
        property string translationText: ""
        visible: false
        z: 21
        x: Math.max(0, Math.min(newHighlightToolbar.x, root.paper.width - width))
        y: Math.max(0, Math.min(newHighlightToolbar.y + newHighlightToolbar.height + 8, root.paper.height - height))
        width: 260
        implicitHeight: vocabCol.implicitHeight + 20
        radius: Theme.radiusMd
        color: Theme.popoverBg
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: vocabCol
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            Text {
                width: parent.width
                text: "Kelime: " + newVocabPopover.word
                elide: Text.ElideRight
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Rectangle {
                width: parent.width
                height: 32
                radius: Theme.radiusSm
                color: Theme.bgSurface
                border.width: 1
                border.color: Theme.borderSubtle

                TextInput {
                    id: vocabTranslationInput
                    objectName: "vocabTranslationInput"
                    anchors.fill: parent
                    anchors.margins: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    text: newVocabPopover.translationText
                    onTextChanged: newVocabPopover.translationText = text

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Türkçe anlamını girin..."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                        visible: !vocabTranslationInput.text
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                AppButton {
                    text: "Vazgeç"
                    variant: "ghost"
                    implicitHeight: 28
                    onClicked: {
                        newVocabPopover.visible = false
                        root.pdfSelection.clear()
                    }
                }

                AppButton {
                    text: "Kaydet"
                    variant: "primary"
                    implicitHeight: 28
                    enabledState: vocabTranslationInput.text.trim().length > 0
                    onClicked: {
                        if (root.resource) {
                            // Secim noktalariyla gonderilir: gectigi cumle baglam olarak da kaydedilir.
                            bridge.reader.addPdfVocabulary(
                                root.resource.id, root.resource.pdfFileUrl,
                                newHighlightToolbar.selectionMap(root.pageIndex),
                                vocabTranslationInput.text.trim()
                            )
                        }
                        newVocabPopover.visible = false
                        root.pdfSelection.clear()
                    }
                }
            }
        }
    }
}
