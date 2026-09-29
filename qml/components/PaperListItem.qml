import QtQuick
import "../theme"

// Kompakt makale satırı (Kaynakça sekmesi, Market kartı altındaki keşif listeleri, öneriler).
// `paper` bridge._serialize_paper çıktısıdır.
Rectangle {
    id: root

    property var paper: ({})
    property string extraInfo: ""  // örn. "Kütüphanendeki 3 makale atıf yapıyor"

    readonly property bool inLibrary: paper.libraryResourceId > 0

    signal saveRequested()

    implicitHeight: column.implicitHeight + 16
    radius: Theme.radiusSm
    color: Theme.bgElevated
    border.width: 1
    border.color: Theme.borderSubtle

    Column {
        id: column
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Text {
            width: parent.width
            text: root.paper.title
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }

        Text {
            width: parent.width
            text: (root.paper.authors.length > 0
                   ? root.paper.authors.slice(0, 3).join(", ")
                     + (root.paper.authors.length > 3 ? " ve ark." : "")
                   : "Yazar bilinmiyor")
                  + (root.paper.year ? " · " + root.paper.year : "")
                  + " · " + root.paper.citationCount + " atıf"
            elide: Text.ElideRight
            font.family: Theme.fontFamily
            font.pixelSize: 10
            color: Theme.textMuted
        }

        Text {
            width: parent.width
            visible: root.extraInfo.length > 0
            text: root.extraInfo
            wrapMode: Text.Wrap
            font.family: Theme.fontFamily
            font.pixelSize: 10
            color: Theme.accentText
        }

        Item {
            width: parent.width
            height: saveButton.height

            AppButton {
                id: saveButton
                anchors.right: parent.right
                text: root.inLibrary ? "Kütüphanede" : "Kaydet"
                iconName: root.inLibrary ? "fa5s.check" : "fa5s.plus"
                variant: root.inLibrary ? "secondary" : "subtle"
                enabledState: !root.inLibrary
                implicitHeight: 24
                onClicked: root.saveRequested()
            }
        }
    }
}
