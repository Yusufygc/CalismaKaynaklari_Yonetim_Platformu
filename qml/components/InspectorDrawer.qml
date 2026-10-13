import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property var resource: bridge.library.selectedResource
    property bool isOpen: bridge.library.isDrawerOpen
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
        InspectorTopBar {
            width: parent.width
            resource: root.resource
            onCloseRequested: root.confirmDelete = false
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
                            onClicked: bridge.library.updateResourceStatus(root.resource.id, "INBOX")
                        }

                        StatusPill {
                            text: "Planlandı"
                            statusKey: "PLANNED"
                            dotColor: Theme.statusPlanned
                            isSelected: root.resource && root.resource.status === "PLANNED"
                            onClicked: bridge.library.updateResourceStatus(root.resource.id, "PLANNED")
                        }

                        StatusPill {
                            text: "Devam"
                            statusKey: "IN_PROGRESS"
                            dotColor: Theme.statusInProgress
                            isSelected: root.resource && root.resource.status === "IN_PROGRESS"
                            onClicked: bridge.library.updateResourceStatus(root.resource.id, "IN_PROGRESS")
                        }

                        StatusPill {
                            text: "Bitti"
                            statusKey: "COMPLETED"
                            dotColor: Theme.statusCompleted
                            isSelected: root.resource && root.resource.status === "COMPLETED"
                            onClicked: bridge.library.updateResourceStatus(root.resource.id, "COMPLETED")
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
                    id: drawerActionsRow
                    width: parent.width - 40
                    spacing: 8

                    AppButton {
                        objectName: "openReaderButton"
                        text: (root.resource && root.resource.isVideo) ? "Videoyu Aç" : "Okuyucuda Aç"
                        iconName: (root.resource && root.resource.isVideo) ? "fa5s.play" : "fa5s.book-open"
                        variant: "primary"
                        // Row, RowLayout degil -- Layout.fillWidth no-op'tu, bu
                        // yuzden kalan genislik elle hesaplaniyor.
                        width: drawerActionsRow.width - editButton.width - deleteButton.width - drawerActionsRow.spacing * 2
                        onClicked: {
                            if (root.resource) bridge.reader.openReader(root.resource.id)
                        }
                    }

                    AppButton {
                        id: editButton
                        text: "Düzenle"
                        iconName: "fa5s.edit"
                        variant: "secondary"
                        onClicked: {
                            if (root.resource) root.editRequested(root.resource)
                        }
                    }

                    AppButton {
                        id: deleteButton
                        text: root.confirmDelete ? "Emin misin?" : "Sil"
                        iconName: "fa5s.trash"
                        variant: root.confirmDelete ? "danger" : "secondary"
                        onClicked: {
                            if (root.confirmDelete) {
                                root.confirmDelete = false
                                if (root.resource) bridge.library.deleteResource(root.resource.id)
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
                InspectorNotes {
                    width: parent.width - 40
                    resource: root.resource
                }

                // Alıntılar Özeti (Varsa)
                InspectorHighlights {
                    width: parent.width - 40
                    resource: root.resource
                }
            }
        }
    }
}
