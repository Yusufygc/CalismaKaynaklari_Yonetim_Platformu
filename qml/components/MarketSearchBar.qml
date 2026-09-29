import QtQuick
import QtQuick.Controls
import "../theme"

// Makale Market üst çubuğu: konu arama kutusu (son aramalar açılır listesiyle), "Ara" butonu ve sekme kapsülü.
// Arama yalnızca Enter/"Ara" ile tetiklenir (AppSearchBar bilinçli kullanılmadı: her tuşta sinyal atar, API rate-limitli).
Item {
    id: root

    property int activeTab: 0
    property alias text: topicInput.text

    signal searchRequested()
    signal tabSelected(int index)

    width: parent ? parent.width : 0
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
            id: searchBox
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
                objectName: "topicInput"
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 24
                    clip: true
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    selectionColor: Theme.accentSubtle
                    selectedTextColor: Theme.textPrimary
                    onAccepted: {
                        historyPopup.close()
                        root.searchRequested()
                    }
                    onActiveFocusChanged: {
                        if (activeFocus && text.length === 0 && bridge.market.marketSearchHistory.length > 0)
                            historyPopup.open()
                    }
                    onTextChanged: if (text.length > 0) historyPopup.close()

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

            // Son aramalar (oturum boyunca)
            Popup {
                id: historyPopup
                y: searchBox.height + 4
                width: searchBox.width
                padding: 4
                focus: false
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                background: Rectangle {
                    color: Theme.bgElevated
                    radius: Theme.radiusSm
                    border.width: 1
                    border.color: Theme.borderStrong
                }

                contentItem: Column {
                    spacing: 2

                    Item {
                        width: parent.width
                        height: 24

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Son aramalar"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }

                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Temizle"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.accentText

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    bridge.market.clearMarketHistory()
                                    historyPopup.close()
                                }
                            }
                        }
                    }

                    Repeater {
                        model: bridge.market.marketSearchHistory

                        delegate: Rectangle {
                            required property string modelData
                            width: parent.width
                            height: 30
                            radius: Theme.radiusXs
                            color: historyMouse.containsMouse ? Theme.bgHover : "transparent"

                            Text {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                text: parent.modelData
                                elide: Text.ElideRight
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textPrimary
                            }

                            MouseArea {
                                id: historyMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    topicInput.text = parent.modelData
                                    historyPopup.close()
                                    root.searchRequested()
                                }
                            }
                        }
                    }
                }
            }
        }

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            text: "Ara"
            iconName: "fa5s.search"
            variant: "primary"
            enabledState: !bridge.market.marketSearchLoading
            onClicked: root.searchRequested()
        }

        BusyIndicator {
            anchors.verticalCenter: parent.verticalCenter
            running: bridge.market.marketSearchLoading
            visible: bridge.market.marketSearchLoading
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
                    color: root.activeTab === index ? Theme.accentSubtle : "transparent"
                    border.width: root.activeTab === index ? 1 : 0
                    border.color: Theme.accent

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
                            color: root.activeTab === index ? Theme.accentText : Theme.textSecondary
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.tabSelected(index)
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
