import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property var resource: bridge.selectedResource
    property bool isOpen: bridge.isDrawerOpen
    property int drawerWidth: 420
    property bool confirmDelete: false

    signal editRequested(var res)

    width: drawerWidth
    height: parent.height
    x: isOpen ? (parent.width - width) : parent.width
    color: Theme.bgElevated
    border.width: 1
    border.color: Theme.borderSubtle
    clip: true

    Behavior on x { NumberAnimation { duration: Theme.animBase; easing.type: Easing.OutCubic } }

    // Dışarı tıklama / Karartma gölgesi
    Rectangle {
        visible: root.isOpen
        anchors.right: parent.left
        width: 16
        height: parent.height
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: Theme.shadowColor }
        }
    }

    // Ana İçerik
    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar (Kapat Butonu & Hızlı Aksiyonlar)
        Item {
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
                        if (root.resource) bridge.togglePin(root.resource.id)
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
                        if (root.resource) bridge.toggleFavorite(root.resource.id)
                    }
                }

                AppIconButton {
                    iconName: "fa5s.times"
                    iconSize: 14
                    tooltip: "Kapat (Esc)"
                    tooltipPosition: "bottom"
                    onClicked: {
                        root.confirmDelete = false
                        bridge.closeDrawer()
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

        // 2. Kaydırılabilir Detay Alanı
        Flickable {
            width: parent.width
            height: parent.height - 52
            contentHeight: contentCol.implicitHeight + 40
            clip: true

            Column {
                id: contentCol
                width: parent.width
                padding: 20
                spacing: 16

                // Başlık
                Text {
                    width: parent.width - 40
                    text: root.resource && root.resource.title ? root.resource.title : "İsimsiz Kaynak"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    wrapMode: Text.Wrap
                }

                // Kategori ve Okuma Süresi
                Row {
                    spacing: 8
                    width: parent.width - 40

                    AppBadge {
                        visible: Boolean(root.resource && root.resource.categoryName)
                        text: (root.resource && root.resource.categoryName) || ""
                        dotColor: (root.resource && root.resource.categoryColor) || "transparent"
                        badgeColor: Theme.bgSurface
                        borderColor: Theme.borderSubtle
                        textColor: Theme.textPrimary
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: (root.resource && root.resource.readingMinutes > 0) ? ("• " + root.resource.readingMinutes + " dk okuma") : ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: (root.resource && root.resource.createdAt) ? ("• " + root.resource.createdAt) : ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }

                // Durum Seçici (Pill Bar)
                Column {
                    spacing: 6
                    width: parent.width - 40

                    Text {
                        text: "DURUM"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    Row {
                        spacing: 6
                        width: parent.width

                        StatusPill {
                            text: "Gelen Kutusu"
                            statusKey: "INBOX"
                            dotColor: Theme.statusInbox
                            isSelected: root.resource && root.resource.status === "INBOX"
                            onClicked: bridge.updateResourceStatus(root.resource.id, "INBOX")
                        }

                        StatusPill {
                            text: "Planlandı"
                            statusKey: "PLANNED"
                            dotColor: Theme.statusPlanned
                            isSelected: root.resource && root.resource.status === "PLANNED"
                            onClicked: bridge.updateResourceStatus(root.resource.id, "PLANNED")
                        }

                        StatusPill {
                            text: "Devam"
                            statusKey: "IN_PROGRESS"
                            dotColor: Theme.statusInProgress
                            isSelected: root.resource && root.resource.status === "IN_PROGRESS"
                            onClicked: bridge.updateResourceStatus(root.resource.id, "IN_PROGRESS")
                        }

                        StatusPill {
                            text: "Bitti"
                            statusKey: "COMPLETED"
                            dotColor: Theme.statusCompleted
                            isSelected: root.resource && root.resource.status === "COMPLETED"
                            onClicked: bridge.updateResourceStatus(root.resource.id, "COMPLETED")
                        }
                    }
                }

                // Etiketler
                Column {
                    visible: Boolean(root.resource && root.resource.tags && root.resource.tags.length > 0)
                    spacing: 6
                    width: parent.width - 40

                    Text {
                        text: "ETİKETLER"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    Flow {
                        width: parent.width
                        spacing: 6

                        Repeater {
                            model: root.resource ? root.resource.tags : []
                            AppBadge {
                                text: "#" + modelData.name
                                badgeColor: Theme.bgSurface
                                borderColor: Theme.borderSubtle
                                textColor: Theme.textSecondary
                            }
                        }
                    }
                }

                // Ana Aksiyonlar (Oku, Düzenle, Sil)
                Row {
                    width: parent.width - 40
                    spacing: 8

                    AppButton {
                        text: "Okuyucuda Aç"
                        iconName: "fa5s.book-open"
                        variant: "primary"
                        Layout.fillWidth: true
                        onClicked: {
                            if (root.resource) bridge.openReader(root.resource.id)
                        }
                    }

                    AppButton {
                        text: "Düzenle"
                        iconName: "fa5s.edit"
                        variant: "secondary"
                        onClicked: {
                            if (root.resource) root.editRequested(root.resource)
                        }
                    }

                    AppButton {
                        text: root.confirmDelete ? "Emin misin?" : "Sil"
                        iconName: "fa5s.trash"
                        variant: root.confirmDelete ? "danger" : "secondary"
                        onClicked: {
                            if (root.confirmDelete) {
                                root.confirmDelete = false
                                if (root.resource) bridge.deleteResource(root.resource.id)
                            } else {
                                root.confirmDelete = true
                            }
                        }
                    }
                }

                // Ayraç
                Rectangle {
                    width: parent.width - 40
                    height: 1
                    color: Theme.borderSubtle
                }

                // Notlar Alanı
                Column {
                    width: parent.width - 40
                    spacing: 8

                    Row {
                        width: parent.width
                        Text {
                            text: "KİŞİSEL NOTLAR"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: Theme.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { Layout.fillWidth: true }

                        AppButton {
                            text: "Notu Kaydet"
                            iconName: "fa5s.check"
                            variant: "subtle"
                            implicitHeight: 26
                            onClicked: {
                                if (root.resource) {
                                    bridge.updateResourceNotes(root.resource.id, notesArea.text)
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

                // Alıntılar Özeti (Varsa)
                Column {
                    visible: Boolean(root.resource && root.resource.highlights && root.resource.highlights.length > 0)
                    width: parent.width - 40
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
            }
        }
    }

    // Durum Seçici Pill Bileşeni
    component StatusPill : Rectangle {
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
}
