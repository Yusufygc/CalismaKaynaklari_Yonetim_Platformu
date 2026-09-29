import QtQuick
import QtQuick.Controls
import QtQuick.Pdf
import "../theme"

// Native PDF okuyucunun sol paneli: sayfa küçük resimleri, anahat (içindekiler)
// ve kullanıcının alıntı/notları (etikete göre filtrelenebilir).
Rectangle {
    id: root

    required property PdfDocument document
    property var resource: ({})
    property int currentPage: 0

    signal pageRequested(int page, point location)

    color: Theme.bgSidebar
    property int activeTab: 0 // 0: Sayfalar, 1: Anahat, 2: Notlarım, 3: Kaynakça
    property string labelFilter: ""
    property string relatedKind: "references" // Kaynakça sekmesi: references | citations

    readonly property string paperOpenAlexId: (resource && resource.paper) ? resource.paper.openalexId : ""

    // Kaynakça sekmesi açıkken (ve makalenin OpenAlex kimliği varsa) referans / atıf listelerini yükle.
    function ensureRelatedLoaded() {
        if (activeTab !== 3 || !resource || !resource.id || paperOpenAlexId === "")
            return
        if (bridge.relatedPapers.openalexId !== paperOpenAlexId)
            bridge.loadRelatedPapers(resource.id)
    }
    onActiveTabChanged: ensureRelatedLoaded()
    onResourceChanged: ensureRelatedLoaded()

    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Theme.borderSubtle
    }

    Column {
        anchors.fill: parent
        anchors.rightMargin: 1
        spacing: 0

        Row {
            id: tabRow
            width: parent.width
            height: 40
            padding: 6
            spacing: 4

            Repeater {
                model: ["Sayfalar", "Anahat", "Notlarım", "Kaynakça"]
                delegate: Rectangle {
                    required property string modelData
                    required property int index
                    width: (tabRow.width - 12 - 12) / 4
                    height: 28
                    radius: Theme.radiusXs
                    color: root.activeTab === index ? Theme.accentSubtle : "transparent"
                    border.width: root.activeTab === index ? 1 : 0
                    border.color: Theme.accent

                    Text {
                        anchors.centerIn: parent
                        text: parent.modelData
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: root.activeTab === parent.index ? Font.DemiBold : Font.Normal
                        color: root.activeTab === parent.index ? Theme.accentText : Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.activeTab = parent.index
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.borderSubtle
        }

        Item {
            width: parent.width
            height: parent.height - tabRow.height - 1

            // --- Sayfalar (küçük resimler) ---
            ListView {
                id: thumbList
                anchors.fill: parent
                visible: root.activeTab === 0
                clip: true
                spacing: 10
                topMargin: 10
                bottomMargin: 10
                model: root.document ? root.document.pageCount : 0
                currentIndex: root.currentPage
                ScrollBar.vertical: ScrollBar {}

                delegate: Item {
                    id: thumbDelegate
                    required property int index
                    readonly property size pageSize: root.document.pagePointSize(index)
                    width: thumbList.width
                    height: thumbFrame.height + 18

                    Rectangle {
                        id: thumbFrame
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 128
                        height: thumbDelegate.pageSize.width > 0
                                ? 128 * thumbDelegate.pageSize.height / thumbDelegate.pageSize.width
                                : 170
                        color: "white"
                        border.width: thumbDelegate.index === root.currentPage ? 2 : 1
                        border.color: thumbDelegate.index === root.currentPage ? Theme.accent : Theme.borderStrong

                        PdfPageImage {
                            anchors.fill: parent
                            anchors.margins: 1
                            document: root.document
                            currentFrame: thumbDelegate.index
                            asynchronous: true
                            fillMode: Image.PreserveAspectFit
                            sourceSize.width: 256
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.pageRequested(thumbDelegate.index, Qt.point(-1, -1))
                        }
                    }

                    Text {
                        anchors.top: thumbFrame.bottom
                        anchors.topMargin: 2
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: thumbDelegate.index + 1
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: thumbDelegate.index === root.currentPage ? Theme.accentText : Theme.textMuted
                    }
                }
            }

            // --- Anahat (içindekiler) ---
            // Doğrulanmış düz liste (bridge.pdfOutline): PdfBookmarkModel'in QML'e doğrudan
            // bağlanması geçersiz yer imli PDF'lerde çökme riski taşıyordu.
            Item {
                anchors.fill: parent
                visible: root.activeTab === 1

                ListView {
                    id: outlineList
                    anchors.fill: parent
                    clip: true
                    model: root.resource && root.resource.pdfFileUrl
                           ? bridge.pdfOutline(root.resource.pdfFileUrl) : []
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                        id: outlineItem
                        required property var modelData
                        width: outlineList.width
                        height: 32
                        color: outlineMouse.containsMouse ? Theme.bgHover : "transparent"

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 12 + outlineItem.modelData.level * 14
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: outlineItem.modelData.title
                            elide: Text.ElideRight
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: outlineItem.modelData.level === 0 ? Font.DemiBold : Font.Normal
                            color: Theme.textPrimary
                        }

                        MouseArea {
                            id: outlineMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.pageRequested(outlineItem.modelData.page, Qt.point(-1, -1))
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 32
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    visible: outlineList.count === 0
                    text: "Bu PDF'te anahat (içindekiler) bilgisi yok."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }

            // --- Notlarım (alıntılar + notlar) ---
            Item {
                anchors.fill: parent
                visible: root.activeTab === 2

                Flow {
                    id: labelChips
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 8
                    spacing: 6

                    AppFilterChip {
                        text: "Tümü"
                        isSelected: root.labelFilter === ""
                        onClicked: root.labelFilter = ""
                    }

                    Repeater {
                        model: bridge.highlightLabels
                        AppFilterChip {
                            required property var modelData
                            text: modelData.label
                            dotColor: modelData.color
                            isSelected: root.labelFilter === modelData.label
                            onClicked: root.labelFilter = (root.labelFilter === modelData.label ? "" : modelData.label)
                        }
                    }
                }

                ListView {
                    id: notesList
                    anchors.top: labelChips.bottom
                    anchors.topMargin: 6
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    clip: true
                    spacing: 6
                    ScrollBar.vertical: ScrollBar {}

                    model: {
                        const items = []
                        const highlights = (root.resource && root.resource.highlights) ? root.resource.highlights : []
                        for (const h of highlights) {
                            if (root.labelFilter !== "" && h.label !== root.labelFilter)
                                continue
                            const rect = h.boundingRect
                            items.push({
                                kind: "highlight", page: h.page, color: h.color, label: h.label,
                                text: h.content, comment: h.comment,
                                x: rect ? rect[0] : -1, y: rect ? rect[1] : -1
                            })
                        }
                        if (root.labelFilter === "") {
                            const notes = (root.resource && root.resource.pdfNotes) ? root.resource.pdfNotes : []
                            for (const n of notes) {
                                items.push({
                                    kind: "note", page: n.page, color: Theme.accent, label: "Not",
                                    text: n.text, comment: "", x: n.x, y: n.y
                                })
                            }
                        }
                        items.sort(function(a, b) { return a.page - b.page || a.y - b.y })
                        return items
                    }

                    delegate: Rectangle {
                        id: noteItem
                        required property var modelData
                        width: notesList.width - 16
                        x: 8
                        implicitHeight: noteCol.implicitHeight + 16
                        radius: Theme.radiusSm
                        color: noteMouse.containsMouse ? Theme.bgHover : Theme.bgElevated
                        border.width: 1
                        border.color: Theme.borderSubtle

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 3
                            color: noteItem.modelData.color
                        }

                        Column {
                            id: noteCol
                            anchors.fill: parent
                            anchors.margins: 8
                            anchors.leftMargin: 12
                            spacing: 3

                            Text {
                                text: noteItem.modelData.label + " · Sayfa " + (noteItem.modelData.page + 1)
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                color: Theme.textMuted
                            }
                            Text {
                                width: parent.width
                                text: noteItem.modelData.text
                                maximumLineCount: 3
                                wrapMode: Text.Wrap
                                elide: Text.ElideRight
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textPrimary
                            }
                            Text {
                                width: parent.width
                                visible: noteItem.modelData.comment !== ""
                                text: "Yorum: " + noteItem.modelData.comment
                                wrapMode: Text.Wrap
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.italic: true
                                color: Theme.accentText
                            }
                        }

                        MouseArea {
                            id: noteMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.pageRequested(
                                noteItem.modelData.page,
                                Qt.point(Math.max(0, noteItem.modelData.x), Math.max(0, noteItem.modelData.y)))
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 32
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    visible: notesList.count === 0
                    text: "Henüz alıntı veya not yok. Metin seçip renk seçerek alıntı ekleyebilirsin."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }

            // --- Kaynakça (referanslar + atıf yapanlar, OpenAlex) ---
            Item {
                id: relatedTab
                anchors.fill: parent
                visible: root.activeTab === 3

                readonly property var related: bridge.relatedPapers
                readonly property var current: related[root.relatedKind]

                // OpenAlex kimliği yoksa: önce bilgi getirilmeli
                Column {
                    anchors.centerIn: parent
                    width: parent.width - 32
                    spacing: 10
                    visible: root.paperOpenAlexId === ""

                    Text {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        text: "Referans ve atıf listesi için makalenin OpenAlex kaydı gerekir."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }

                    AppButton {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "OpenAlex'ten Getir"
                        iconName: "fa5s.cloud-download-alt"
                        variant: "primary"
                        onClicked: if (root.resource && root.resource.id) bridge.fetchPaperMetadata(root.resource.id)
                    }
                }

                Item {
                    anchors.fill: parent
                    visible: root.paperOpenAlexId !== ""

                    Row {
                        id: relatedSwitch
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: 8
                        spacing: 6

                        Repeater {
                            model: [
                                { kind: "references", label: "Referanslar" },
                                { kind: "citations", label: "Atıf Yapanlar" }
                            ]
                            delegate: AppFilterChip {
                                required property var modelData
                                text: modelData.label
                                count: relatedTab.related[modelData.kind].items.length
                                isSelected: root.relatedKind === modelData.kind
                                onClicked: root.relatedKind = modelData.kind
                            }
                        }
                    }

                    ListView {
                        id: relatedList
                        anchors.top: relatedSwitch.bottom
                        anchors.topMargin: 8
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        clip: true
                        spacing: 6
                        model: relatedTab.current.items
                        ScrollBar.vertical: ScrollBar {}

                        delegate: PaperListItem {
                            required property var modelData
                            width: relatedList.width - 16
                            x: 8
                            paper: modelData
                            onSaveRequested: bridge.saveMarketResult(modelData)
                        }
                    }

                    Text {
                        anchors.centerIn: relatedList
                        width: parent.width - 32
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        visible: relatedList.count === 0
                        text: relatedTab.current.loading ? "Yükleniyor..."
                              : (relatedTab.current.error !== "" ? relatedTab.current.error
                                 : "OpenAlex'te bu liste için kayıt bulunamadı.")
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: relatedTab.current.error !== "" ? Theme.dangerText : Theme.textMuted
                    }
                }
            }
        }
    }
}
