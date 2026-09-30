import QtQuick
import QtQuick.Controls
import "../theme"

// Kaynağa ait alıntıların özeti (yalnız alıntı varsa görünür). Genişliği kullanıldığı yerde verilir.
Column {
    id: root

    property var resource

    visible: Boolean(root.resource && root.resource.highlights && root.resource.highlights.length > 0)
    spacing: 8

    Text {
        text: "BU KAYNAKTAKİ ALINTILAR (" + (root.resource && root.resource.highlights ? root.resource.highlights.length : 0) + ")"
        font.family: Theme.fontFamily
        font.pixelSize: 10
        font.weight: Font.Bold
        color: Theme.textMuted
    }

    Repeater {
        model: root.resource ? root.resource.highlights : []
        Rectangle {
            width: parent.width
            implicitHeight: hlCol.implicitHeight + 16
            radius: Theme.radiusSm
            color: Theme.bgSurface
            border.width: 1
            border.color: Theme.borderSubtle

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 3
                radius: 1
                color: modelData.color || Theme.accent
            }

            Column {
                id: hlCol
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 10
                anchors.topMargin: 8
                anchors.bottomMargin: 8
                spacing: 4

                Text {
                    width: parent.width
                    text: "“" + modelData.content + "”"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.italic: true
                    color: Theme.textPrimary
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
