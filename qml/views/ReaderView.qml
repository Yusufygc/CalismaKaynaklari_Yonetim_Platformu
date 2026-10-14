import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property var resource: bridge.reader.currentReaderResource
    property int baseFontSize: 16
    property int zoomLevel: 0

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Okuma Barı
        Item {
            width: parent.width
            height: 56

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                // Geri Butonu
                AppButton {
                    text: "Vitrine Dön"
                    iconName: "fa5s.arrow-left"
                    variant: "ghost"
                    onClicked: bridge.reader.closeReader()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Makale Başlığı ve Meta
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    width: Math.min(parent.parent.width - 320, 500)

                    Text {
                        width: parent.width
                        text: root.resource && root.resource.title ? root.resource.title : ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        elide: Text.ElideRight
                    }

                    Text {
                        text: (root.resource && root.resource.domain ? root.resource.domain : "") +
                              (root.resource && root.resource.readingMinutes ? " • " + root.resource.readingMinutes + " dk okuma" : "")
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }
            }

            // Sağ Taraf: Yazı Tipi Boyutu (Zoom) & Tarayıcıda Aç
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                AppIconButton {
                    iconName: "fa5s.minus"
                    iconSize: 11
                    tooltip: "Yazı Boyutunu Küçült"
                    tooltipPosition: "bottom"
                    onClicked: {
                        if (root.zoomLevel > -3) root.zoomLevel--
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: (100 + root.zoomLevel * 15) + "%"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppIconButton {
                    iconName: "fa5s.plus"
                    iconSize: 11
                    tooltip: "Yazı Boyutunu Büyüt"
                    tooltipPosition: "bottom"
                    onClicked: {
                        if (root.zoomLevel < 5) root.zoomLevel++
                    }
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppIconButton {
                    iconName: "fa5s.external-link-alt"
                    iconSize: 12
                    tooltip: "Orijinal Sayfayı Tarayıcıda Aç"
                    tooltipPosition: "bottom"
                    onClicked: {
                        if (root.resource && root.resource.url) {
                            Qt.openUrlExternally(root.resource.url)
                        }
                    }
                }
            }

            // Okuma İlerleme Çubuğu (En Altta)
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 2
                color: Theme.borderSubtle

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: {
                        var maxScroll = flickable.contentHeight - flickable.height
                        if (maxScroll <= 0) return parent.width
                        var ratio = Math.max(0, Math.min(1, flickable.contentY / maxScroll))
                        return parent.width * ratio
                    }
                    color: Theme.accent
                }
            }
        }

        // 2. Okuma Gövdesi (Ortalanmış 760px Sütun)
        Item {
            width: parent.width
            height: parent.height - 56

            Flickable {
                id: flickable
                anchors.fill: parent
                contentWidth: width
                contentHeight: articleCol.implicitHeight + 80
                clip: true

                Column {
                    id: articleCol
                    width: Math.min(parent.width - 40, 760)
                    anchors.horizontalCenter: parent.horizontalCenter
                    topPadding: 32
                    bottomPadding: 60
                    spacing: 20

                    // Büyük Makale Başlığı
                    Text {
                        width: parent.width
                        text: root.resource && root.resource.title ? root.resource.title : ""
                        font.family: Theme.fontFamily
                        font.pixelSize: (root.baseFontSize + root.zoomLevel * 2) + 10
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        wrapMode: Text.Wrap
                        lineHeight: 1.25
                    }

                    // Kaynak URL Bilgisi
                    Row {
                        spacing: 8
                        visible: Boolean(root.resource && root.resource.url)

                        AppIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: (root.resource && root.resource.url && root.resource.url.startsWith("file://")) ? "fa5s.file-pdf" : "fa5s.globe"
                            size: 13
                            color: Theme.accent
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: {
                                if (!root.resource || !root.resource.url) return ""
                                if (root.resource.url.startsWith("file://")) return "Yerel PDF dosyası"
                                return root.resource.url
                            }
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.accentText
                            elide: Text.ElideRight
                            width: Math.min(implicitWidth, 680)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.borderSubtle
                    }

                    // Makale İçeriği (HTML / RichText Destekli)
                    // Metin henüz yokken: çekiliyor mu, bulunamadı mı? (aksiyonlarla)
                    Column {
                        id: statusPanel
                        objectName: "readerStatusPanel"
                        visible: bridge.reader.extractionState !== "ready"
                        width: parent.width
                        spacing: 12
                        topPadding: 8

                        readonly property string phase: bridge.reader.extractionState
                        readonly property bool busy: phase === "pending" || phase === "searching"

                        Row {
                            spacing: 10
                            BusyIndicator {
                                running: statusPanel.busy
                                visible: statusPanel.busy
                                width: 22
                                height: 22
                            }
                            AppIcon {
                                visible: !statusPanel.busy
                                anchors.verticalCenter: parent.verticalCenter
                                name: "fa5s.exclamation-circle"
                                size: 16
                                color: Theme.textMuted
                            }
                            Text {
                                objectName: "readerStatusText"
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: Theme.fontHeading
                                font.pixelSize: Theme.fontMd
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                                text: {
                                    switch (statusPanel.phase) {
                                    case "pending": return "İçerik çekiliyor…"
                                    case "searching": return "Açık erişimli PDF aranıyor…"
                                    case "noOpenAccess": return "Bu makalenin açık erişimli bir kopyası bulunamadı"
                                    case "failed": return "Sayfanın metni alınamadı"
                                    default: return "Henüz metin yok"
                                    }
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            wrapMode: Text.Wrap
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            visible: !statusPanel.busy
                            text: {
                                if (statusPanel.phase === "noOpenAccess")
                                    return "Yayıncı sayfası otomatik okumaya kapalı ve ücretsiz bir PDF bulunamadı. Makaleyi tarayıcıda açıp kendi PDF'ini indirebilir, sonra \"Bilgisayardan PDF Yükle\" ile ekleyebilirsin."
                                if (bridge.reader.canFindOpenAccess)
                                    return "Yayıncı sayfaları (örneğin Elsevier, Springer) robotların okumasına izin vermeyebilir. Makalenin ücretsiz (açık erişimli) bir PDF kopyasını arayabilirsin."
                                return "Site otomatik okumaya izin vermiyor olabilir ya da sayfada okunacak makale metni yok. Tekrar deneyebilir ya da sayfayı tarayıcıda açabilirsin."
                            }
                        }

                        Row {
                            spacing: 8
                            visible: !statusPanel.busy
                            AppButton {
                                objectName: "findOpenAccessButton"
                                visible: bridge.reader.canFindOpenAccess && statusPanel.phase !== "noOpenAccess"
                                text: "Açık erişimli PDF ara"
                                iconName: "fa5s.file-pdf"
                                variant: "primary"
                                onClicked: bridge.reader.findOpenAccessPdf()
                            }
                            AppButton {
                                objectName: "retryExtractionButton"
                                text: "Yeniden dene"
                                iconName: "fa5s.redo"
                                variant: "secondary"
                                onClicked: bridge.reader.retryExtraction()
                            }
                            AppButton {
                                objectName: "openInBrowserButton"
                                text: "Tarayıcıda aç"
                                iconName: "fa5s.external-link-alt"
                                variant: "ghost"
                                onClicked: if (root.resource && root.resource.url) Qt.openUrlExternally(root.resource.url)
                            }
                        }
                    }

                    TextEdit {
                        id: textContent
                        objectName: "readerText"
                        visible: bridge.reader.extractionState === "ready"
                        width: parent.width
                        textFormat: TextEdit.RichText
                        text: bridge.reader.readerHtml
                        persistentSelection: true  // renk düğmesine basılırken seçim kaybolmasın
                        font.family: Theme.fontFamily
                        font.pixelSize: root.baseFontSize + root.zoomLevel * 2
                        color: Theme.textPrimary
                        wrapMode: TextEdit.Wrap
                        readOnly: true
                        selectByMouse: true
                        selectionColor: Theme.accentSubtle
                        selectedTextColor: Theme.textPrimary
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }

            // 3. Kindle/Notion Tarzı Yüzen Seçim Araç Çubuğu (Selection Bar)
            Rectangle {
                id: selectionBar
                objectName: "selectionBar"
                // Seçili metnin hemen üstünde (yer yoksa altında) durur; kaydırınca seçimle birlikte hareket eder.
                readonly property bool hasSelection: textContent.visible && textContent.selectedText.trim().length > 0
                // Seçim yokken selectionStart/End geçersizdir (-1): o konumda hesaplanmaz.
                readonly property rect startRect: hasSelection ? textContent.positionToRectangle(textContent.selectionStart) : Qt.rect(0, 0, 0, 0)
                readonly property rect endRect: hasSelection ? textContent.positionToRectangle(textContent.selectionEnd) : Qt.rect(0, 0, 0, 0)
                readonly property point startPoint: { flickable.contentY; return textContent.mapToItem(parent, startRect.x, startRect.y) }
                readonly property point endPoint: { flickable.contentY; return textContent.mapToItem(parent, endRect.x, endRect.y) }
                readonly property real aboveY: startPoint.y - height - 8
                visible: hasSelection && endPoint.y + endRect.height > 0 && startPoint.y < parent.height
                implicitWidth: selRow.implicitWidth + 24
                implicitHeight: 44
                width: implicitWidth
                height: implicitHeight
                x: Math.max(8, Math.min(parent.width - width - 8, startPoint.x))
                y: Math.max(8, Math.min(parent.height - height - 8, aboveY >= 8 ? aboveY : endPoint.y + endRect.height + 8))
                z: 5
                radius: Theme.radiusPill
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderStrong

                // Çubuğun boş yerlerine basmak seçimi kaldırmasın
                MouseArea {
                    anchors.fill: parent
                }

                Row {
                    id: selRow
                    anchors.centerIn: parent
                    height: parent.height
                    spacing: 8

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Vurgula:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                        color: Theme.textSecondary
                    }

                    // 5 Fosforlu Renk Yuvarlağı
                    Repeater {
                        model: Theme.highlightPalette
                        Item {
                            id: colorCell
                            required property string modelData
                            width: 22
                            height: selRow.height

                            Rectangle {
                                objectName: "highlightColorDot"
                                anchors.centerIn: parent
                                width: 22
                                height: 22
                                radius: 11
                                color: colorCell.modelData
                                border.width: 1
                                border.color: Qt.alpha(Theme.textOnAccent, 0.27)

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.resource) {
                                            bridge.annotations.addHighlight(root.resource.id, textContent.selectedText, colorCell.modelData)
                                            textContent.deselect()
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: 1
                        height: 18
                        color: Theme.borderSubtle
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Kelime Olarak Ekle Butonu
                    AppButton {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Kelime Havuzuna Ekle"
                        iconName: "fa5s.language"
                        variant: "subtle"
                        implicitHeight: 28
                        onClicked: {
                            vocabModal.word = textContent.selectedText
                            vocabModal.open()
                        }
                    }
                }
            }
        }
    }

    // Kelime Havuzuna Ekleme Mini Popover/Dialog
    Dialog {
        id: vocabModal
        property string word: ""
        anchors.centerIn: parent
        width: 380
        title: "Kelime Havuzuna Ekle"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        Column {
            spacing: 12
            width: parent.width

            Text {
                text: "Kelime: " + vocabModal.word
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Rectangle {
                width: parent.width
                height: 36
                radius: Theme.radiusSm
                color: Theme.bgSurface
                border.width: 1
                border.color: Theme.borderSubtle

                TextInput {
                    id: translationInput
                    anchors.fill: parent
                    anchors.margins: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Türkçe anlamını girin..."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textMuted
                        visible: !translationInput.text
                    }
                }
            }
        }

        onAccepted: {
            if (root.resource && translationInput.text.trim()) {
                bridge.annotations.addVocabulary(root.resource.id, vocabModal.word, translationInput.text.trim())
                translationInput.text = ""
                textContent.deselect()
            }
        }
    }
}
