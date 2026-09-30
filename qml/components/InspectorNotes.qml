import QtQuick
import QtQuick.Controls
import "../theme"

// Kişisel (Markdown) notlar alanı ve "Notu Kaydet". Genişliği kullanıldığı yerde verilir.
Column {
    id: root

    property var resource

    spacing: 8

    Item {
        width: parent.width
        height: Math.max(notesHeaderLabel.implicitHeight, saveNotesButton.height)

        Text {
            id: notesHeaderLabel
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "KİŞİSEL NOTLAR"
            font.family: Theme.fontFamily
            font.pixelSize: 10
            font.weight: Font.Bold
            color: Theme.textMuted
        }

        AppButton {
            id: saveNotesButton
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: "Notu Kaydet"
            iconName: "fa5s.check"
            variant: "subtle"
            implicitHeight: 26
            onClicked: {
                if (root.resource) {
                    bridge.library.updateResourceNotes(root.resource.id, notesArea.text)
                }
            }
        }
    }

    Rectangle {
        width: parent.width
        height: 180
        radius: Theme.radiusSm
        color: Theme.bgSurface
        border.width: 1
        border.color: notesArea.activeFocus ? Theme.borderFocus : Theme.borderSubtle

        Flickable {
            anchors.fill: parent
            anchors.margins: 10
            contentWidth: width
            contentHeight: notesArea.implicitHeight
            clip: true

            TextArea.flickable: TextArea {
                id: notesArea
                width: parent.width
                text: root.resource && root.resource.content ? root.resource.content : ""
                placeholderText: "Markdown notlarını buraya yaz..."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                color: Theme.textPrimary
                wrapMode: TextEdit.Wrap
                background: null
                padding: 0
            }
        }
    }
}
