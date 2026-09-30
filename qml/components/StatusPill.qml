import QtQuick
import QtQuick.Controls
import "../theme"

// Durum seçici hapı (Gelen Kutusu / Planlandı / Devam / Bitti).
Rectangle {
    property string text: ""
    property string statusKey: ""
    property color dotColor: "transparent"
    property bool isSelected: false
    signal clicked()

    implicitWidth: pillRow.implicitWidth + 14
    implicitHeight: 26
    radius: Theme.radiusPill

    color: isSelected ? Qt.alpha(dotColor, 0.2) : Theme.bgSurface
    border.width: 1
    border.color: isSelected ? dotColor : Theme.borderSubtle

    Row {
        id: pillRow
        anchors.centerIn: parent
        spacing: 5

        Rectangle {
            width: 6
            height: 6
            radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: dotColor
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: parent.parent.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            font.weight: isSelected ? Font.DemiBold : Font.Normal
            color: isSelected ? Theme.textPrimary : Theme.textSecondary
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: parent.clicked()
    }
}
