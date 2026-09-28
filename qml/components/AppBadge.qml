import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property color dotColor: "transparent"
    property bool showDot: dotColor !== "transparent"
    property color badgeColor: Theme.bgSurface
    property color textColor: Theme.textSecondary
    property color borderColor: Theme.borderSubtle
    property string iconName: ""
    property bool clickable: false

    signal clicked()

    implicitWidth: row.implicitWidth + (clickable ? 16 : 12)
    implicitHeight: 22
    radius: Theme.radiusPill

    color: clickable && mouseArea.containsMouse ? Qt.lighter(badgeColor, 1.1) : badgeColor
    border.width: 1
    border.color: borderColor

    Behavior on color { ColorAnimation { duration: Theme.animFast } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 5

        // İsteğe bağlı renkli nokta (status dot)
        Rectangle {
            visible: root.showDot
            width: 6
            height: 6
            radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: root.dotColor
        }

        AppIcon {
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            name: root.iconName
            size: 11
            color: root.textColor
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            font.weight: Font.Medium
            color: root.textColor
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.clickable
        hoverEnabled: root.clickable
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
