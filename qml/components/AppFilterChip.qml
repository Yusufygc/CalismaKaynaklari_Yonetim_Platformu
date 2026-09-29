import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string iconName: ""
    property int count: -1
    property bool isSelected: false
    property color dotColor: "transparent"

    signal clicked()

    implicitWidth: row.implicitWidth + 18
    implicitHeight: 28
    radius: Theme.radiusSm

    color: {
        if (isSelected) return Theme.accentSubtle
        if (mouseArea.containsMouse) return Theme.bgHover
        return Theme.bgSurface
    }

    border.width: 1
    border.color: isSelected ? Theme.accent : Theme.borderSubtle

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        // Renkli nokta
        Rectangle {
            visible: root.dotColor.a > 0
            width: 7
            height: 7
            radius: 3.5
            anchors.verticalCenter: parent.verticalCenter
            color: root.dotColor
        }

        AppIcon {
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            name: root.iconName
            size: 12
            color: root.isSelected ? Theme.accentText : Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: root.isSelected ? Font.DemiBold : Font.Normal
            color: root.isSelected ? Theme.accentText : Theme.textPrimary
        }

        // Sayı rozeti
        Rectangle {
            visible: root.count >= 0
            implicitWidth: countText.implicitWidth + 8
            implicitHeight: 16
            radius: Theme.radiusPill
            anchors.verticalCenter: parent.verticalCenter
            color: root.isSelected ? Theme.accent : Theme.chipUnselectedBg

            Text {
                id: countText
                anchors.centerIn: parent
                text: root.count.toString()
                font.family: Theme.fontFamily
                font.pixelSize: 10
                font.weight: Font.Bold
                color: root.isSelected ? Theme.textOnAccent : Theme.textSecondary
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
