import QtQuick
import "../theme"

Rectangle {
    id: root

    property alias text: textInput.text
    property string placeholder: "Kaynaklarda ara (başlık, etiket, not)..."

    signal searchChanged(string query)
    signal searchCleared()

    implicitWidth: 320
    implicitHeight: 36
    radius: Theme.radiusSm

    color: textInput.activeFocus ? Theme.bgSurface : Theme.bgElevated
    border.width: 1
    border.color: textInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }
    Behavior on color { ColorAnimation { duration: Theme.animFast } }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 8
        spacing: 8

        AppIcon {
            anchors.verticalCenter: parent.verticalCenter
            name: "fa5s.search"
            size: 13
            color: textInput.activeFocus ? Theme.accent : Theme.textMuted
            Behavior on color { ColorAnimation { duration: Theme.animFast } }
        }

        Item {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 64
            height: parent.height

            TextInput {
                id: textInput
                anchors.fill: parent
                verticalAlignment: TextInput.AlignVCenter
                clip: true
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                selectionColor: Theme.accentSubtle
                selectedTextColor: Theme.textPrimary

                onTextChanged: root.searchChanged(text)
                onAccepted: root.searchChanged(text)

                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    text: root.placeholder
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    color: Theme.textMuted
                    visible: !textInput.text && !textInput.activeFocus
                }
            }
        }

        // Temizle Butonu
        AppIconButton {
            visible: textInput.text.length > 0
            anchors.verticalCenter: parent.verticalCenter
            iconName: "fa5s.times"
            iconSize: 12
            implicitWidth: 22
            implicitHeight: 22
            tooltip: "Temizle"
            tooltipPosition: "bottom"
            onClicked: {
                textInput.text = ""
                root.searchCleared()
            }
        }
    }
}
