import QtQuick
import QtQuick.Controls
import "../theme"

// Makale Market sonuç kartı: başlık, yazar/yıl, atıf, dergi, rozetler (açık erişim / PDF /
// kütüphanede), açılır özet ve "Kaydet". `paper` `ui_qml/serializers.py::serialize_paper` çıktısıdır.
Rectangle {
    id: root

    property var paper: ({})
    property bool expanded: false
    property string discoveryKind: ""  // "" | references | citations | similar
    property bool selectable: false    // Toplu işlem için onay kutusu
    property bool selected: false

    readonly property bool inLibrary: paper.libraryResourceId > 0

    signal saveRequested()
    signal saveForLaterRequested()
    signal selectionToggled()
    signal authorRequested(string authorId, string authorName)

    function toggleDiscovery(kind) {
        root.discoveryKind = root.discoveryKind === kind ? "" : kind
        if (root.discoveryKind !== "")
            bridge.market.loadDiscovery(kind, root.paper.openalexId)
    }

    implicitHeight: content.implicitHeight + 24
    radius: Theme.radiusSm
    color: Theme.bgElevated
    border.width: 1
    border.color: Theme.borderSubtle

    Column {
        id: content
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 6

        Item {
            width: parent.width
            height: Math.max(titleText.implicitHeight, buttonRow.height)

            // Toplu seçim kutusu (kütüphanede olan makalede gösterilmez)
            Rectangle {
                id: checkBox
                visible: root.selectable && !root.inLibrary
                width: visible ? 18 : 0
                height: 18
                y: 2
                radius: 4
                color: root.selected ? Theme.accent : "transparent"
                border.width: 1
                border.color: root.selected ? Theme.accent : Theme.borderStrong

                AppIcon {
                    anchors.centerIn: parent
                    visible: root.selected
                    name: "fa5s.check"
                    size: 10
                    color: Theme.textOnAccent
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectionToggled()
                }
            }

            Text {
                id: titleText
                anchors.left: checkBox.right
                anchors.leftMargin: checkBox.visible ? 8 : 0
                anchors.right: buttonRow.left
                anchors.rightMargin: 8
                text: root.paper.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                wrapMode: Text.Wrap
            }

            Row {
                id: buttonRow
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 6

                AppIconButton {
                    visible: !root.inLibrary
                    iconName: "fa5s.bookmark"
                    iconSize: 12
                    tooltip: "Sonra oku (okuma-listesi etiketiyle kaydet)"
                    onClicked: root.saveForLaterRequested()
                }

                AppButton {
                    id: saveButton
                    text: root.inLibrary ? "Kütüphanede" : "Kaydet"
                    iconName: root.inLibrary ? "fa5s.check" : ""
                    variant: root.inLibrary ? "secondary" : "subtle"
                    enabledState: !root.inLibrary
                    onClicked: root.saveRequested()
                }
            }
        }

        Flow {
            width: parent.width
            spacing: 0

            Text {
                visible: root.paper.authors.length === 0
                text: "Yazar bilinmiyor"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }

            // Yazar adına tıklayınca o yazarın çalışmaları listelenir.
            Repeater {
                model: Math.min(root.paper.authors.length, 5)

                delegate: Text {
                    required property int index
                    readonly property string authorId: root.paper.authorIds[index] || ""
                    text: root.paper.authors[index] + (index < Math.min(root.paper.authors.length, 5) - 1 ? ", " : "")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.underline: authorMouse.containsMouse && authorId !== ""
                    color: authorMouse.containsMouse && authorId !== "" ? Theme.accentText : Theme.textMuted

                    MouseArea {
                        id: authorMouse
                        anchors.fill: parent
                        enabled: parent.authorId !== ""
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.authorRequested(parent.authorId, root.paper.authors[parent.index])
                    }
                }
            }

            Text {
                visible: root.paper.authors.length > 5
                text: " ve ark."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }

            Text {
                text: root.paper.year ? "  ·  " + root.paper.year + "  ·  " : "  ·  "
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }

            Text {
                text: root.paper.citationCount + " atıf"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Medium
                color: Theme.textSecondary
            }
        }

        // Dergi / konferans · DOI
        Text {
            width: parent.width
            visible: text.length > 0
            text: [root.paper.venue, root.paper.doi ? "DOI: " + root.paper.doi : ""]
                  .filter(function(part) { return part && part.length > 0 }).join("  ·  ")
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            font.italic: true
            color: Theme.textMuted
            elide: Text.ElideRight
        }

        // "Okumadığın ortak referans" önerilerinde: kütüphaneden kaç makale bu esere atıf yapıyor
        Text {
            width: parent.width
            visible: root.paper.citedByLibrary > 0
            text: "Kütüphanendeki " + root.paper.citedByLibrary + " makale bu esere atıf yapıyor"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            font.weight: Font.Medium
            color: Theme.accentText
        }

        Row {
            spacing: 6
            visible: root.paper.isOpenAccess || root.paper.hasPdf

            AppBadge {
                visible: root.paper.isOpenAccess
                text: "Açık erişim"
                iconName: "fa5s.unlock"
                badgeColor: Theme.statusCompletedBg
                textColor: Theme.statusCompleted
                borderColor: "transparent"
            }

            AppBadge {
                visible: root.paper.hasPdf
                text: "PDF var"
                iconName: "fa5s.file-pdf"
                badgeColor: Theme.statusPlannedBg
                textColor: Theme.statusPlanned
                borderColor: "transparent"
            }
        }

        Text {
            id: abstractText
            width: parent.width
            text: root.paper.abstract
            visible: root.paper.abstract.length > 0
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            maximumLineCount: root.expanded ? 1000 : 3
            elide: Text.ElideRight
        }

        Text {
            visible: root.paper.abstract.length > 0 && (root.expanded || abstractText.truncated)
            text: root.expanded ? "Daralt" : "Devamını oku"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.accentText

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
            }
        }

        // Keşif: referanslar / atıf yapanlar / benzer makaleler (OpenAlex kimliği varsa)
        Row {
            spacing: 14
            visible: root.paper.openalexId !== ""

            Repeater {
                model: [
                    { kind: "references", label: "Referanslar" },
                    { kind: "citations", label: "Atıf yapanlar" },
                    { kind: "similar", label: "Benzer makaleler" }
                ]

                delegate: Text {
                    required property var modelData
                    text: modelData.label
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: root.discoveryKind === modelData.kind ? Font.DemiBold : Font.Normal
                    font.underline: kindMouse.containsMouse
                    color: root.discoveryKind === modelData.kind ? Theme.accentText : Theme.textMuted

                    MouseArea {
                        id: kindMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleDiscovery(parent.modelData.kind)
                    }
                }
            }
        }

        Column {
            id: discoveryPanel
            width: parent.width
            spacing: 6
            visible: root.discoveryKind !== ""

            readonly property var panel: root.discoveryKind !== ""
                ? bridge.market.marketDiscovery[root.discoveryKind + ":" + root.paper.openalexId] : undefined

            Text {
                width: parent.width
                visible: !discoveryPanel.panel || discoveryPanel.panel.items.length === 0
                text: !discoveryPanel.panel || discoveryPanel.panel.loading ? "Yükleniyor..."
                      : (discoveryPanel.panel.error !== "" ? discoveryPanel.panel.error
                         : "OpenAlex'te bu liste için kayıt bulunamadı.")
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: discoveryPanel.panel && discoveryPanel.panel.error !== "" ? Theme.dangerText : Theme.textMuted
            }

            Repeater {
                model: discoveryPanel.panel ? discoveryPanel.panel.items : []

                delegate: PaperListItem {
                    required property var modelData
                    width: discoveryPanel.width
                    paper: modelData
                    color: Theme.bgSurface
                    onSaveRequested: bridge.market.saveMarketResult(modelData)
                }
            }
        }
    }
}
