import QtQuick
import "../theme"

// Sonuç araç çubuğu: toplu seçim, aramayı kaydet, dışa aktar, toplu kaydet. Durum kökten gelir, eylemler sinyalle döner.
Item {
    id: root

    property int selectionCount: 0
    property bool canSaveSearch: false     // Arama yapıldı, öneri modunda değil ve henüz kayıtlı değil
    property string collectionTag: ""      // Çalışan kayıtlı aramanın koleksiyon etiketi ("" = yok)
    property string countLabel: ""         // "3 seçili" / "42 sonuç"

    signal selectAllRequested()
    signal clearSelectionRequested()
    signal saveSearchRequested()
    signal bibtexRequested()
    signal csvRequested()
    signal saveSelectedRequested()

    width: parent ? parent.width : 0
    height: visible ? 44 : 0


    Row {
        anchors.left: parent.left
        anchors.leftMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            text: "Tümünü seç"
            variant: "ghost"
            implicitHeight: 28
            onClicked: root.selectAllRequested()
        }

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.selectionCount > 0
            text: "Seçimi temizle"
            variant: "ghost"
            implicitHeight: 28
            onClicked: root.clearSelectionRequested()
        }

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.canSaveSearch
            text: "Aramayı kaydet"
            iconName: "fa5s.bookmark"
            variant: "ghost"
            implicitHeight: 28
            onClicked: root.saveSearchRequested()
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.collectionTag !== ""
            text: "Kaydedilenler #" + root.collectionTag + " etiketiyle eklenir"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.accentText
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.countLabel
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            text: "BibTeX"
            iconName: "fa5s.file-export"
            variant: "subtle"
            implicitHeight: 28
            onClicked: root.bibtexRequested()
        }

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            text: "CSV"
            iconName: "fa5s.file-csv"
            variant: "subtle"
            implicitHeight: 28
            onClicked: root.csvRequested()
        }

        AppButton {
            anchors.verticalCenter: parent.verticalCenter
            text: "Seçilenleri Kaydet (" + root.selectionCount + ")"
            iconName: "fa5s.plus"
            variant: "primary"
            implicitHeight: 28
            enabledState: root.selectionCount > 0
            onClicked: root.saveSelectedRequested()
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.borderSubtle
    }
}
