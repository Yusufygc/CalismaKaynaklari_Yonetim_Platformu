import QtQuick
import "../theme"

// Kategori rengi seçici: Theme.categoryPalette üzerinde tek seçim.
Row {
    id: root

    property string selectedColor: ""
    signal colorPicked(string color)

    spacing: 6

    Repeater {
        model: Theme.categoryPalette

        Rectangle {
            objectName: "colorSwatch"
            readonly property bool selected: String(root.selectedColor).toLowerCase() === String(modelData).toLowerCase()
            width: 22
            height: 22
            radius: 11
            color: modelData
            border.width: selected ? 2 : 0
            border.color: Theme.textOnAccent

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.colorPicked(String(modelData))
            }
        }
    }
}
