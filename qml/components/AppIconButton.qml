import QtQuick
import "../theme"

Rectangle {
    id: root

    property string iconName: ""
    property int iconSize: 16
    property color iconColor: Theme.textSecondary
    property color iconHoverColor: Theme.textPrimary
    property color activeBgColor: Theme.bgHover
    property bool isActive: false
    property string tooltip: ""

    signal clicked()

    implicitWidth: 30
    implicitHeight: 30
    radius: Theme.radiusSm

    color: {
        if (mouseArea.pressed) return Theme.bgActive
        if (mouseArea.containsMouse || isActive) return activeBgColor
        return "transparent"
    }

    border.width: mouseArea.containsMouse && !isActive ? 1 : 0
    border.color: Theme.borderSubtle

    Behavior on color { ColorAnimation { duration: Theme.animFast } }

    AppIcon {
        anchors.centerIn: parent
        name: root.iconName
        size: root.iconSize
        color: mouseArea.containsMouse ? root.iconHoverColor : root.iconColor
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    // Basit şık tooltip
    Rectangle {
        id: tooltipRect
        visible: root.tooltip !== "" && mouseArea.containsMouse
        z: 999
        anchors.bottom: parent.top
        anchors.bottomMargin: 6
        anchors.horizontalCenter: parent.horizontalCenter
        width: tipText.implicitWidth + 12
        height: tipText.implicitHeight + 6
        radius: Theme.radiusXs
        color: Theme.tooltipBg
        border.width: 1
        border.color: Theme.borderStrong

        Text {
            id: tipText
            anchors.centerIn: parent
            text: root.tooltip
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textOnAccent
        }
    }
}
