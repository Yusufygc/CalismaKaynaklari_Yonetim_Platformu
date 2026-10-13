import QtQuick
import QtQuick.Controls
import "../theme"

// Bilgi Havuzu > Metinde Ara sekmesi: PDF'lerin içindeki metinde arama. Sonuçlar kaynağa göre gruplu (başlık + sayfa
// eşleşmeleri); sonuca tıklamak okuyucuyu o sayfada açar. Üstte dizinleme durumu (arka planda sürerken ilerleme).
// Arama kutusu üst çubuktadır (KnowledgePoolView); sorgu `bridge.contentSearch.search` ile gelir.
Item {
    id: root

    readonly property var status: bridge.contentSearch.indexStatus
    readonly property bool indexing: status.state === "running"

    Rectangle {
        id: statusBar
        objectName: "indexStatusBar"
        width: parent.width
        height: 36
        color: "transparent"

        Text {
            objectName: "indexStatusText"
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: root.status.state === "unavailable" ? Theme.danger : Theme.textMuted
            text: {
                if (root.status.state === "unavailable") return "Bu sistemde tam metin araması kullanılamıyor."
                if (root.indexing) return "PDF'ler dizinleniyor: " + root.status.done + "/" + root.status.total + " — bitenlerde arama şimdiden çalışır."
                return "Arama, PDF'lerin içindeki metinde çalışır (taranmış / metin katmanı olmayan PDF'ler hariç)."
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Theme.borderSubtle
        }
    }

    // Boş durumlar
    Text {
        objectName: "contentSearchEmpty"
        anchors.centerIn: parent
        visible: resultsList.count === 0 && root.status.state !== "unavailable"
        horizontalAlignment: Text.AlignHCenter
        width: parent.width - 96
        wrapMode: Text.Wrap
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        color: Theme.textMuted
        text: bridge.contentSearch.searched ? "Eşleşme bulunamadı." : "Yukarıdaki kutuya yazarak PDF'lerin içinde ara."
    }

    ListView {
        id: resultsList
        objectName: "contentResults"
        anchors.top: statusBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        anchors.topMargin: 12
        spacing: 12
        clip: true
        model: bridge.contentSearch.groups

        delegate: Rectangle {
            id: groupCard
            required property var modelData
            width: resultsList.width - 24
            implicitHeight: groupColumn.implicitHeight + 24
            radius: Theme.radiusSm
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.borderSubtle

            Column {
                id: groupColumn
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Row {
                    spacing: 8
                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "fa5s.book-open"
                        size: 12
                        color: Theme.accent
                    }
                    Text {
                        objectName: "groupTitle"
                        anchors.verticalCenter: parent.verticalCenter
                        width: groupCard.width - 24 - 20
                        elide: Text.ElideRight
                        text: groupCard.modelData.title
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: bridge.contentSearch.openHit(groupCard.modelData.resourceId, groupCard.modelData.hits[0].page)
                        }
                    }
                }

                Repeater {
                    model: groupCard.modelData.hits

                    delegate: Rectangle {
                        id: hitRow
                        required property var modelData
                        objectName: "hitRow"
                        width: groupColumn.width
                        implicitHeight: hitText.implicitHeight + 12
                        radius: Theme.radiusXs
                        color: hitMouse.containsMouse ? Theme.bgHover : "transparent"

                        Row {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 10

                            Text {
                                width: 48
                                text: "s. " + (hitRow.modelData.page + 1)
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.DemiBold
                                color: Theme.accentText
                            }

                            Text {
                                id: hitText
                                objectName: "hitSnippet"
                                width: parent.width - 58
                                textFormat: Text.StyledText
                                wrapMode: Text.Wrap
                                text: hitRow.modelData.html
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                lineHeight: 1.25
                                color: Theme.textSecondary
                            }
                        }

                        MouseArea {
                            id: hitMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: bridge.contentSearch.openHit(groupCard.modelData.resourceId, hitRow.modelData.page)
                        }
                    }
                }

                Text {
                    objectName: "moreHits"
                    visible: groupCard.modelData.more > 0
                    text: groupCard.modelData.expanded
                          ? "+ " + groupCard.modelData.more + " sayfa daha (ilk " + groupCard.modelData.hits.length + " gösteriliyor)"
                          : "+ " + groupCard.modelData.more + " sayfa daha — tümünü göster"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.underline: !groupCard.modelData.expanded && moreMouse.containsMouse
                    color: groupCard.modelData.expanded ? Theme.textMuted : Theme.accentText

                    MouseArea {
                        id: moreMouse
                        anchors.fill: parent
                        enabled: !groupCard.modelData.expanded
                        hoverEnabled: true
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: bridge.contentSearch.expand(groupCard.modelData.resourceId)
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar { active: true }
    }
}
