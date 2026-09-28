import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string iconName: ""
    property int iconSize: 15
    property string variant: "secondary" // "primary", "secondary", "ghost", "danger", "subtle"
    property bool enabledState: true

    signal clicked()

    implicitWidth: contentRow.implicitWidth + 24
    implicitHeight: 34
    radius: Theme.radiusSm

    color: {
        if (!enabledState) return Theme.borderSubtle
        if (mouseArea.pressed) {
            if (variant === "primary") return Qt.darker(Theme.accent, 1.15)
            if (variant === "danger") return Qt.darker(Theme.danger, 1.15)
            return Theme.bgActive
        }
        if (mouseArea.containsMouse) {
            if (variant === "primary") return Theme.accentHover
            if (variant === "danger") return Theme.dangerHover
            if (variant === "ghost") return Theme.bgHover
            if (variant === "subtle") return Qt.lighter(Theme.accentSubtle, 1.05)
            return Theme.bgHover
        }
        if (variant === "primary") return Theme.accent
        if (variant === "danger") return Theme.dangerSubtle
        if (variant === "ghost") return "transparent"
        if (variant === "subtle") return Theme.accentSubtle
        return Theme.bgSurface
    }

    border.width: (variant === "secondary" || (variant === "ghost" && mouseArea.containsMouse)) ? 1 : 0
    border.color: mouseArea.containsMouse ? Theme.borderStrong : Theme.borderSubtle

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 8

        AppIcon {
            id: btnIcon
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            name: root.iconName
            size: root.iconSize
            color: root.textColor
        }

        Text {
            id: btnText
            visible: root.text !== ""
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: root.variant === "primary" ? Font.DemiBold : Font.Medium
            color: root.textColor
        }
    }

    readonly property color textColor: {
        if (!enabledState) return Theme.textMuted
        if (variant === "primary") return Theme.textOnAccent
        if (variant === "danger") return mouseArea.containsMouse ? Theme.textOnAccent : Theme.dangerText
        if (variant === "subtle") return Theme.accentText
        return Theme.textPrimary
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabledState
        cursorShape: root.enabledState ? Qt.PointingHandCursor : Qt.ArrowCursor
        enabled: root.enabledState
        onClicked: root.clicked()
    }
}
