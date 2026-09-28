import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property int activeTab: 0 // 0: Alıntılar, 1: Kelimeler
    property string searchQuery: ""

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Sekmeler ve Arama
        Item {
            width: parent.width
            height: 64

            Row {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 16

                // Sekme Butonları (Pill Bar)
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 280
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 4

                        // Alıntılar Sekmesi
                        Rectangle {
                            width: (parent.width - 4) / 2
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 0 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 0 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.quote-right"
                                    size: 11
                                    color: root.activeTab === 0 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Alıntılar (" + bridge.highlights.length + ")"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 0 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 0 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 0
                            }
                        }

                        // Kelime Dağarcığı Sekmesi
                        Rectangle {
                            width: (parent.width - 4) / 2
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 1 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 1 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.language"
                                    size: 12
                                    color: root.activeTab === 1 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Kelimeler (" + bridge.vocabulary.length + ")"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 1 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 1 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 1
                            }
                        }
                    }
                }

                // Arama Kutusu
                AppSearchBar {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 280
                    placeholder: root.activeTab === 0 ? "Alıntılarda ara..." : "Kelimelerde ara..."
                    onSearchChanged: function(q) { root.searchQuery = q.toLowerCase() }
                    onSearchCleared: { root.searchQuery = "" }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // 2. İçerik Listeleri (Alıntılar veya Kelimeler)
        Item {
            width: parent.width
            height: parent.height - 64

            // --- SEKME 0: ALINTILAR ---
            ListView {
                id: highlightsList
                visible: root.activeTab === 0
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                clip: true

                model: {
                    var all = bridge.highlights
                    if (!root.searchQuery) return all
                    return all.filter(function(h) {
                        return h.content.toLowerCase().indexOf(root.searchQuery) !== -1 ||
                               h.resource_title.toLowerCase().indexOf(root.searchQuery) !== -1
                    })
                }

                delegate: Rectangle {
                    width: highlightsList.width - 24
                    implicitHeight: hlCardCol.implicitHeight + 24
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    // Sol Renk Çizgisi
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 4
                        radius: 2
                        color: modelData.color || Theme.accent
                    }

                    Column {
                        id: hlCardCol
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        anchors.topMargin: 12
                        anchors.bottomMargin: 12
                        spacing: 8

                        // Alıntı Metni
                        Text {
                            width: parent.width - 50
                            text: "“" + modelData.content + "”"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.italic: true
                            lineHeight: 1.3
                            color: Theme.textPrimary
                            wrapMode: Text.Wrap
                        }

                        // Alt Bilgi: Kaynak Başlığı & Sil
                        Row {
                            width: parent.width
                            spacing: 8

                            AppIcon {
                                anchors.verticalCenter: parent.verticalCenter
                                name: "fa5s.book-open"
                                size: 11
                                color: Theme.accent
                            }

                            // Kaynak Bağlantısı (Tıklandığında okuyucuyu açar)
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.resource_title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Medium
                                color: Theme.accentText

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: bridge.openReader(modelData.resource_id)
                                }
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "• " + modelData.created_at
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                            }

                            Item { Layout.fillWidth: true }

                            AppIconButton {
                                iconName: "fa5s.trash"
                                iconSize: 11
                                tooltip: "Alıntıyı Sil"
                                onClicked: bridge.deleteHighlight(modelData.id)
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }

            // --- SEKME 1: KELİMELER ---
            ListView {
                id: vocabList
                visible: root.activeTab === 1
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                clip: true

                model: {
                    var all = bridge.vocabulary
                    if (!root.searchQuery) return all
                    return all.filter(function(v) {
                        return v.word.toLowerCase().indexOf(root.searchQuery) !== -1 ||
                               v.translation.toLowerCase().indexOf(root.searchQuery) !== -1
                    })
                }

                delegate: Rectangle {
                    width: vocabList.width - 24
                    implicitHeight: vocabCol.implicitHeight + 20
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        id: vocabCol
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        anchors.topMargin: 10
                        anchors.bottomMargin: 10
                        spacing: 16

                        // Kelime
                        Column {
                            width: 200
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Text {
                                text: modelData.word
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontMd
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: modelData.resource_title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.accentText
                                elide: Text.ElideRight
                                width: parent.width

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: bridge.openReader(modelData.resource_id)
                                }
                            }
                        }

                        // Anlamı (Çeviri)
                        Text {
                            width: parent.width - 320
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.translation
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Medium
                            color: Theme.textSecondary
                            wrapMode: Text.Wrap
                        }

                        Item { Layout.fillWidth: true }

                        AppIconButton {
                            anchors.verticalCenter: parent.verticalCenter
                            iconName: "fa5s.trash"
                            iconSize: 11
                            tooltip: "Kelimeyi Sil"
                            onClicked: bridge.deleteVocabulary(modelData.id)
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }
        }
    }
}
