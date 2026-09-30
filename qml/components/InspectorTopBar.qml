import QtQuick
import QtQuick.Controls
import "../theme"

// Çekmece üst çubuğu: harici bağlantı, sabitle, favori, kapat. Kapatma `closeRequested` ile de bildirilir
// (üst bileşen onay durumunu sıfırlar).
Item {
    id: root

    property var resource
    signal closeRequested()

    width: parent.width
    height: 52

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        // Harici URL Butonu
        Rectangle {
            visible: Boolean(root.resource && root.resource.url)
            implicitWidth: urlRow.implicitWidth + 16
            implicitHeight: 28
            radius: Theme.radiusPill
            color: Theme.bgSurface
            border.width: 1
            border.color: Theme.borderSubtle

            Row {
                id: urlRow
                anchors.centerIn: parent
                spacing: 6

                AppIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    name: "fa5s.external-link-alt"
                    size: 11
                    color: Theme.accent
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.resource && root.resource.domain ? root.resource.domain : "Bağlantıyı Aç"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Medium
                    color: Theme.accentText
                }
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.resource && root.resource.url) {
                        Qt.openUrlExternally(root.resource.url)
                    }
                }
            }
        }
    }

    // Sağ Taraf: Pin, Favori, Kapat
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        AppIconButton {
            iconName: "fa5s.thumbtack"
            iconSize: 13
            isActive: Boolean(root.resource && root.resource.isPinned)
            iconColor: (root.resource && root.resource.isPinned) ? Theme.pin : Theme.textSecondary
            tooltip: "Sabitle"
            tooltipPosition: "bottom"
            onClicked: {
                if (root.resource) bridge.library.togglePin(root.resource.id)
            }
        }

        AppIconButton {
            iconName: "fa5s.heart"
            iconSize: 13
            isActive: Boolean(root.resource && root.resource.isFavorite)
            iconColor: (root.resource && root.resource.isFavorite) ? Theme.favorite : Theme.textSecondary
            tooltip: (root.resource && root.resource.isFavorite) ? "Favorilerden Çıkar" : "Favorilere Ekle"
            tooltipPosition: "bottom"
            onClicked: {
                if (root.resource) bridge.library.toggleFavorite(root.resource.id)
            }
        }

        AppIconButton {
            iconName: "fa5s.times"
            iconSize: 14
            tooltip: "Kapat (Esc)"
            tooltipPosition: "bottom"
            onClicked: {
                root.closeRequested()
                bridge.library.closeDrawer()
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.borderSubtle
    }
}
