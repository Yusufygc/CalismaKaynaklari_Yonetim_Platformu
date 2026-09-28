import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property var resource: bridge.currentReaderResource
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
                    onClicked: bridge.closeReader()
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
                    TextEdit {
                        id: textContent
                        width: parent.width
                        textFormat: TextEdit.RichText
                        text: {
                            if (!root.resource) return ""
                            if (root.resource.fullText) return root.resource.fullText
                            if (root.resource.content) return "<p>" + root.resource.content + "</p>"
                            return "<p><i>İçerik çekiliyor veya metin bulunamadı...</i></p>"
                        }
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
                visible: textContent.selectedText.trim().length > 0
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 24
                anchors.horizontalCenter: parent.horizontalCenter
                implicitWidth: selRow.implicitWidth + 20
                implicitHeight: 40
                radius: Theme.radiusPill
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderStrong

                Row {
                    id: selRow
                    anchors.centerIn: parent
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
                        Rectangle {
                            width: 22
                            height: 22
                            radius: 11
                            color: modelData
                            border.width: 1
                            border.color: Qt.alpha(Theme.textOnAccent, 0.27)

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (root.resource) {
                                        bridge.addHighlight(root.resource.id, textContent.selectedText, modelData, -1, -1, -1)
                                        textContent.deselect()
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
                bridge.addVocabulary(root.resource.id, vocabModal.word, translationInput.text.trim())
                translationInput.text = ""
                textContent.deselect()
            }
        }
    }
}
