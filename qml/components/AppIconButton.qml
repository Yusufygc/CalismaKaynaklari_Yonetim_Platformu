import QtQuick
import QtQuick.Controls
import QtQuick.Window
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
    property string tooltipPosition: "auto" // "auto", "bottom", "top", "left", "right"

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

    // Modern QtQuick.Controls ToolTip (Pencere seviyesinde kayan overlay popup)
    ToolTip {
        id: tooltipPopup
        visible: root.tooltip !== "" && mouseArea.containsMouse
        text: root.tooltip
        delay: 350
        timeout: 5000

        // Yatay Konumlandırma (Pencere kenarlarından taşmayı engelle)
        x: {
            if (root.tooltipPosition === "right") return root.width + 6
            if (root.tooltipPosition === "left") return -width - 6

            var idealX = Math.round((root.width - width) / 2)
            var pt = root.mapToItem(null, 0, 0)
            if (!pt) return idealX

            var winX = pt.x + idealX
            if (winX < 8) {
                idealX += (8 - winX)
            }
            var winW = root.Window.width
            if (winW > 0 && (winX + width > winW - 8)) {
                idealX -= (winX + width - (winW - 8))
            }
            return idealX
        }

        // Dikey Konumlandırma (Üst çubuk veya üstteki logolarla çakışmayı engelle)
        y: {
            if (root.tooltipPosition === "bottom") return root.height + 6
            if (root.tooltipPosition === "top") return -height - 6
            if (root.tooltipPosition === "left" || root.tooltipPosition === "right") {
                return Math.round((root.height - height) / 2)
            }

            // "auto" modu:
            // Butonun pencere dikey konumu üst 100px içindeyse (başlık, üst çubuk, daraltılmış logo altı),
            // yukarıdaki öğelerle çakışmaması için daima butonun altında aç
            var pt = root.mapToItem(null, 0, 0)
            if (!pt || pt.y < 100) {
                return root.height + 6
            }
            return -height - 6
        }

        contentItem: Text {
            text: tooltipPopup.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textOnAccent
        }

        background: Rectangle {
            color: Theme.tooltipBg
            border.color: Theme.borderStrong
            border.width: 1
            radius: Theme.radiusXs
        }
    }
}

