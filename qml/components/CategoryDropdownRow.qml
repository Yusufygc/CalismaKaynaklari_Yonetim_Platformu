import QtQuick
import "../theme"

Rectangle {
    id: root

    property string label: ""
    property color dotColor: "transparent"
    property int count: -1
    property bool isSelected: false

    signal clicked()

    height: 34
    radius: Theme.radiusXs
    color: isSelected ? Theme.accentSubtle : (mouseArea.containsMouse ? Theme.bgHover : "transparent")

    Behavior on color { ColorAnimation { duration: Theme.animFast } }

    Row {
        anchors.left: parent.left
        anchors.right: countBadge.visible ? countBadge.left : parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        Rectangle {
            visible: root.dotColor.a > 0
            anchors.verticalCenter: parent.verticalCenter
            width: 7
            height: 7
            radius: 3.5
            color: root.dotColor
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            elide: Text.ElideRight
            width: parent.width - (root.dotColor.a > 0 ? 15 : 0)
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: root.isSelected ? Font.DemiBold : Font.Normal
            color: root.isSelected ? Theme.accentText : Theme.textPrimary
        }
    }

    Rectangle {
        id: countBadge
        visible: root.count >= 0
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        implicitWidth: countText.implicitWidth + 8
        implicitHeight: 16
        radius: Theme.radiusPill
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

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
