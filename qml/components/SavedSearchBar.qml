import QtQuick
import QtQuick.Controls
import "../theme"

// Kayıtlı aramalar çubuğu (yeni yayın rozetiyle). Yalnızca bridge.market ile konuşur.
Item {
    width: parent ? parent.width : 0
    height: visible ? 44 : 0
    visible: bridge.market.savedSearches.length > 0


    Text {
        id: savedLabel
        anchors.left: parent.left
        anchors.leftMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        text: "Kayıtlı aramalar"
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
    }

    Flickable {
        anchors.left: savedLabel.right
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        height: 30
        contentWidth: savedRow.implicitWidth
        contentHeight: height
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Row {
            id: savedRow
            spacing: 8

            Repeater {
                model: bridge.market.savedSearches

                delegate: Row {
                    required property var modelData
                    spacing: 2

                    AppFilterChip {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label + (modelData.newCount > 0 ? "  ·  " + modelData.newCount + " yeni" : "")
                        iconName: "fa5s.bookmark"
                        dotColor: modelData.newCount > 0 ? Theme.statusInProgress : "transparent"
                        isSelected: bridge.market.activeSavedSearchId === modelData.id
                        onClicked: bridge.market.runSavedSearch(modelData.id)
                    }

                    AppIconButton {
                        anchors.verticalCenter: parent.verticalCenter
                        iconName: "fa5s.times"
                        iconSize: 10
                        tooltip: "Kayıtlı aramayı sil"
                        onClicked: bridge.market.deleteSavedSearch(modelData.id)
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
