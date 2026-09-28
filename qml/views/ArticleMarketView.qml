import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property int activeTab: 0 // 0: En Güncel, 1: En Popüler, 2: En Çok Atıf Alan
    property bool hasSearched: false

    function runSearch() {
        if (topicInput.text.trim().length === 0) return
        root.hasSearched = true
        bridge.searchArticles(topicInput.text.trim())
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Arama + Sekmeler
        Item {
            width: parent.width
            height: 64

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16

                // Konu Arama Kutusu (AppSearchBar YENİDEN KULLANILMIYOR:
                // o bileşen her tuş vuruşunda searchChanged fırlatıyor, burada
                // uzak bir API'ye (rate-limitli) sadece Enter/Ara ile gidilmeli.)
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 320
                    height: 36
                    radius: Theme.radiusSm
                    color: topicInput.activeFocus ? Theme.bgSurface : Theme.bgElevated
                    border.width: 1
                    border.color: topicInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 8
                        spacing: 8

                        AppIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "fa5s.search"
                            size: 13
                            color: topicInput.activeFocus ? Theme.accent : Theme.textMuted
                        }

                        TextInput {
                            id: topicInput
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 24
                            clip: true
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            selectionColor: Theme.accentSubtle
                            selectedTextColor: Theme.textPrimary
                            onAccepted: root.runSearch()

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "Bir konu ara (örn. transformer neural network)..."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                color: Theme.textMuted
                                visible: !topicInput.text && !topicInput.activeFocus
                            }
                        }
                    }
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Ara"
                    iconName: "fa5s.search"
                    variant: "primary"
                    enabledState: !bridge.marketSearchLoading
                    onClicked: root.runSearch()
                }

                BusyIndicator {
                    anchors.verticalCenter: parent.verticalCenter
                    running: bridge.marketSearchLoading
                    visible: bridge.marketSearchLoading
                    width: 24
                    height: 24
                }

            }

            // Sekme Butonları (Pill Bar) — 3 segment, sağa hizalı
            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                width: 380
                height: 36
                radius: Theme.radiusSm
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle

                Row {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 4

                    Repeater {
                        model: [
                            { icon: "fa5s.clock", label: "En Güncel" },
                            { icon: "fa5s.fire", label: "En Popüler" },
                            { icon: "fa5s.quote-right", label: "En Çok Atıf Alan" }
                        ]

                        Rectangle {
                            width: (380 - 6 - 8) / 3
                            height: 30
                            radius: Theme.radiusXs
                            color: root.activeTab === index ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === index ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: modelData.icon
                                    size: 11
                                    color: root.activeTab === index ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: root.activeTab === index ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === index ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = index
                            }
                        }
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // 2. İçerik: 3 sonuç listesi
        Item {
            width: parent.width
            height: parent.height - 64

            property var currentList: {
                if (root.activeTab === 0) return bridge.marketResults.recent
                if (root.activeTab === 1) return bridge.marketResults.popular
                return bridge.marketResults.cited
            }

            // Boş durumlar
            Column {
                anchors.centerIn: parent
                spacing: 8
                visible: !bridge.marketSearchLoading && parent.currentList.length === 0

                AppIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    name: root.hasSearched ? "fa5s.folder-open" : "fa5s.search"
                    size: 28
                    color: Theme.textMuted
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.hasSearched ? "Sonuç bulunamadı." : "Bir konu arayarak makale keşfetmeye başlayın."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }

            ListView {
                id: resultsList
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                clip: true
                model: parent.currentList

                delegate: Rectangle {
                    width: resultsList.width - 24
                    implicitHeight: paperCol.implicitHeight + 24
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    property bool saved: false

                    Column {
                        id: paperCol
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        anchors.topMargin: 12
                        anchors.bottomMargin: 12
                        spacing: 6

                        Row {
                            width: parent.width
                            spacing: 8

                            Text {
                                width: parent.width - 100
                                text: modelData.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontMd
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                                wrapMode: Text.Wrap
                            }

                            Item { width: 1; height: 1; Layout.fillWidth: true }

                            AppButton {
                                text: saved ? "Kaydedildi" : "Kaydet"
                                variant: saved ? "secondary" : "subtle"
                                enabledState: !saved
                                onClicked: {
                                    bridge.saveMarketResult(modelData)
                                    saved = true
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            Text {
                                text: (modelData.authors.length > 0 ? modelData.authors.join(", ") : "Yazar bilinmiyor") +
                                      (modelData.year ? " · " + modelData.year : "")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                                elide: Text.ElideRight
                                width: Math.min(implicitWidth, 500)
                            }

                            Rectangle {
                                radius: Theme.radiusPill
                                color: Theme.bgSurface
                                border.width: 1
                                border.color: Theme.borderSubtle
                                width: citationText.implicitWidth + 16
                                height: 18
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    id: citationText
                                    anchors.centerIn: parent
                                    text: modelData.citationCount + " atıf"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: Theme.textSecondary
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            text: modelData.abstract
                            visible: modelData.abstract.length > 0
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            wrapMode: Text.Wrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }
        }
    }
}
