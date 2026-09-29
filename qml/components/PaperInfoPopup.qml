import QtQuick
import QtQuick.Controls
import "../theme"

// Kaynağın akademik bilgileri + APA / IEEE / BibTeX atıfları (tek tıkla kopyala).
Popup {
    id: root

    property var resource: ({})
    readonly property var paper: (resource && resource.paper) ? resource.paper : ({})
    readonly property bool hasPaperInfo: (paper.authors && paper.authors.length > 0) || !!paper.year || !!paper.doi

    width: 480
    padding: 16
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.popoverBg
        radius: Theme.radiusMd
        border.width: 1
        border.color: Theme.borderStrong
    }

    contentItem: Column {
        spacing: 12

        Row {
            width: parent.width
            spacing: 8

            Text {
                width: parent.width - fetchButton.width - 8
                anchors.verticalCenter: parent.verticalCenter
                text: "Atıf ve Kaynak Bilgisi"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            AppButton {
                id: fetchButton
                text: "OpenAlex'ten Getir"
                iconName: "fa5s.cloud-download-alt"
                variant: "subtle"
                implicitHeight: 28
                onClicked: if (root.resource && root.resource.id) bridge.fetchPaperMetadata(root.resource.id)
            }
        }

        Column {
            width: parent.width
            spacing: 3

            Text {
                width: parent.width
                text: root.resource && root.resource.title ? root.resource.title : ""
                wrapMode: Text.Wrap
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                visible: root.hasPaperInfo
                text: {
                    const parts = []
                    if (root.paper.authors && root.paper.authors.length > 0)
                        parts.push(root.paper.authors.slice(0, 6).join(", ")
                                   + (root.paper.authors.length > 6 ? " ve ark." : ""))
                    if (root.paper.year) parts.push(String(root.paper.year))
                    if (root.paper.venue) parts.push(root.paper.venue)
                    if (root.paper.doi) parts.push("DOI: " + root.paper.doi)
                    if (root.paper.citationCount > 0) parts.push(root.paper.citationCount + " atıf")
                    return parts.join(" · ")
                }
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textSecondary
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                visible: !root.hasPaperInfo
                text: "Yazar/yıl/DOI bilgisi yok. \"OpenAlex'ten Getir\" ile otomatik doldurabilirsin; atıflar bu bilgilerle üretilir."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
        }

        Repeater {
            model: [
                { style: "apa", label: "APA" },
                { style: "ieee", label: "IEEE" },
                { style: "bibtex", label: "BibTeX" }
            ]

            delegate: Column {
                id: citationBlock
                required property var modelData
                width: root.contentItem.width
                spacing: 4

                Item {
                    width: parent.width
                    height: copyButton.height

                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: citationBlock.modelData.label
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    AppButton {
                        id: copyButton
                        anchors.right: parent.right
                        text: "Kopyala"
                        iconName: "fa5s.copy"
                        variant: "ghost"
                        implicitHeight: 26
                        onClicked: bridge.copyCitation(root.resource.id, citationBlock.modelData.style)
                    }
                }

                Rectangle {
                    width: parent.width
                    height: citationText.implicitHeight + 16
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: Theme.borderSubtle

                    TextEdit {
                        id: citationText
                        anchors.fill: parent
                        anchors.margins: 8
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        text: root.resource && root.resource.id
                              ? bridge.citationText(root.resource.id, citationBlock.modelData.style) : ""
                        font.family: citationBlock.modelData.style === "bibtex" ? "Consolas" : Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        selectionColor: Theme.accent
                    }
                }
            }
        }
    }
}
