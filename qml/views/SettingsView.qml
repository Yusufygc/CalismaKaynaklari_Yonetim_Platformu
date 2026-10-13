import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property int activeTab: 0 // 0: Kategoriler, 1: Etiketler, 2: Obsidian, 3: Künye
    property string newCategoryColor: Theme.accent

    // Silme onayı bekleyen öğe: kind "category" | "tag"
    property string pendingKind: ""
    property int pendingId: 0
    property string pendingName: ""

    function askDelete(kind, id, name) {
        pendingKind = kind
        pendingId = id
        pendingName = name
        confirmDialog.open()
    }

    function confirmDelete() {
        if (pendingKind === "category")
            bridge.settings.deleteCategory(pendingId)
        else if (pendingKind === "tag")
            bridge.settings.deleteTag(pendingId)
    }

    ConfirmDialog {
        id: confirmDialog
        title: root.pendingKind === "category" ? "Kategoriyi Sil" : "Etiketi Sil"
        message: "\"" + root.pendingName + "\" kalıcı olarak silinecek. Bu işlem geri alınamaz."
        onConfirmed: root.confirmDelete()
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Sekmeler
        Item {
            width: parent.width
            height: 64

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16

                Rectangle {
                    width: 520
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 4

                        Rectangle {
                            width: (parent.width - 12) / 4
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 0 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 0 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.folder"
                                    size: 11
                                    color: root.activeTab === 0 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Kategoriler"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 0 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 0 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 0
                            }
                        }

                        Rectangle {
                            width: (parent.width - 12) / 4
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 1 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 1 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.tag"
                                    size: 11
                                    color: root.activeTab === 1 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Etiketler"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 1 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 1 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 1
                            }
                        }

                        Rectangle {
                            objectName: "vaultTab"
                            width: (parent.width - 12) / 4
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 2 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 2 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.gem"
                                    size: 11
                                    color: root.activeTab === 2 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Obsidian"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 2 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 2 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 2
                            }
                        }

                        Rectangle {
                            objectName: "metadataTab"
                            width: (parent.width - 12) / 4
                            height: parent.height
                            radius: Theme.radiusXs
                            color: root.activeTab === 3 ? Theme.bgSurface : "transparent"
                            border.width: root.activeTab === 3 ? 1 : 0
                            border.color: Theme.borderStrong

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.id-card"
                                    size: 11
                                    color: root.activeTab === 3 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Künye"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: root.activeTab === 3 ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === 3 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = 3
                            }
                        }
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

        // 2. İçerik Alanı
        Flickable {
            width: parent.width
            height: parent.height - 64
            contentHeight: contentCol.implicitHeight + 60
            clip: true

            Column {
                id: contentCol
                width: Math.min(parent.width - 48, 800)
                anchors.horizontalCenter: parent.horizontalCenter
                topPadding: 24
                bottomPadding: 40
                spacing: 24

                // --- OBSIDIAN PANELİ ---
                VaultSettingsPanel {
                    visible: root.activeTab === 2
                    width: parent.width
                }

                // --- KÜNYE PANELİ ---
                MetadataSettingsPanel {
                    visible: root.activeTab === 3
                    width: parent.width
                }

                // --- KATEGORİLER PANELİ ---
                Column {
                    visible: root.activeTab === 0
                    width: parent.width
                    spacing: 16

                    Text {
                        text: "Yeni Kategori Ekle"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }

                    // Yeni Kategori Ekleme Satırı
                    Rectangle {
                        width: parent.width
                        implicitHeight: addCatRow.implicitHeight + 20
                        radius: Theme.radiusMd
                        color: Theme.bgElevated
                        border.width: 1
                        border.color: Theme.borderSubtle

                        Row {
                            id: addCatRow
                            anchors.left: parent.left
                            anchors.right: addCategoryButton.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 10

                            // İsim Girişi
                            Rectangle {
                                width: 220
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.bgSurface
                                border.width: 1
                                border.color: catNameInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                                TextInput {
                                    id: catNameInput
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    verticalAlignment: TextInput.AlignVCenter
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase

                                    Text {
                                        anchors.fill: parent
                                        verticalAlignment: Text.AlignVCenter
                                        text: "Kategori adı..."
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        color: Theme.textMuted
                                        visible: !catNameInput.text
                                    }
                                }
                            }

                            ColorPalette {
                                anchors.verticalCenter: parent.verticalCenter
                                selectedColor: root.newCategoryColor
                                onColorPicked: (color) => root.newCategoryColor = color
                            }

                        }

                        AppButton {
                            id: addCategoryButton
                            anchors.right: parent.right
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Kategori Ekle"
                            iconName: "fa5s.plus"
                            variant: "primary"
                            enabledState: catNameInput.text.trim().length > 0
                            onClicked: {
                                bridge.settings.createCategory(catNameInput.text.trim(), root.newCategoryColor, "")
                                catNameInput.text = ""
                            }
                        }
                    }

                    Text {
                        text: "Mevcut Kategoriler (" + bridge.settings.categories.length + ")"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        topPadding: 8
                    }

                    // Kategori Listesi
                    Column {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: bridge.settings.categories
                            CategoryRow {
                                category: modelData
                                onDeleteRequested: (id, name) => root.askDelete("category", id, name)
                            }
                        }
                    }
                }

                // --- ETİKETLER PANELİ ---
                Column {
                    visible: root.activeTab === 1
                    width: parent.width
                    spacing: 16

                    Text {
                        text: "Yeni Etiket Ekle"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }

                    // Yeni Etiket Ekleme Satırı
                    Rectangle {
                        width: parent.width
                        height: 56
                        radius: Theme.radiusMd
                        color: Theme.bgElevated
                        border.width: 1
                        border.color: Theme.borderSubtle

                        Row {
                            anchors.left: parent.left
                            anchors.right: addTagButton.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 10

                            Rectangle {
                                width: 280
                                height: 36
                                radius: Theme.radiusSm
                                color: Theme.bgSurface
                                border.width: 1
                                border.color: tagNameInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                                TextInput {
                                    id: tagNameInput
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    verticalAlignment: TextInput.AlignVCenter
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase

                                    Text {
                                        anchors.fill: parent
                                        verticalAlignment: Text.AlignVCenter
                                        text: "Etiket adı (örn. yapay-zeka)..."
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        color: Theme.textMuted
                                        visible: !tagNameInput.text
                                    }
                                }
                            }

                        }

                        AppButton {
                            id: addTagButton
                            anchors.right: parent.right
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Etiket Ekle"
                            iconName: "fa5s.plus"
                            variant: "primary"
                            enabledState: tagNameInput.text.trim().length > 0
                            onClicked: {
                                bridge.settings.createTag(tagNameInput.text.trim())
                                tagNameInput.text = ""
                            }
                        }
                    }

                    Text {
                        text: "Mevcut Etiketler (" + bridge.settings.tags.length + ")"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        topPadding: 8
                    }

                    // Etiketler Flow Izgarası
                    Flow {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: bridge.settings.tags
                            TagPill {
                                tag: modelData
                                onDeleteRequested: (id, name) => root.askDelete("tag", id, name)
                            }
                        }
                    }
                }
            }

            ScrollBar.vertical: ScrollBar { active: true }
        }
    }
}
