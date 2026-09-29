import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    implicitHeight: 36
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBase

    contentItem: Text {
        leftPadding: 10
        rightPadding: control.indicator.width + 8
        text: control.displayText
        font: control.font
        color: Theme.textPrimary
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: AppIcon {
        x: control.width - width - 10
        y: control.height / 2 - height / 2
        name: "fa5s.chevron-down"
        size: 11
        color: Theme.textMuted
    }

    background: Rectangle {
        implicitHeight: 36
        radius: Theme.radiusSm
        color: Theme.bgSurface
        border.width: 1
        border.color: control.activeFocus || control.popup.visible ? Theme.borderFocus : Theme.borderSubtle
        Behavior on border.color { ColorAnimation { duration: Theme.animFast } }
    }

    delegate: ItemDelegate {
        id: delegateItem
        required property var modelData
        required property int index

        width: control.width
        implicitHeight: 34

        contentItem: Text {
            text: delegateItem.modelData
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            color: delegateItem.highlighted ? Theme.accentText : Theme.textPrimary
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10
        }

        background: Rectangle {
            color: delegateItem.highlighted ? Theme.bgHover : "transparent"
        }

        highlighted: control.highlightedIndex === index
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + topPadding + bottomPadding, 220)
        padding: 4

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }

        background: Rectangle {
            color: Theme.bgElevated
            radius: Theme.radiusSm
            border.width: 1
            border.color: Theme.borderStrong
        }
    }
}
