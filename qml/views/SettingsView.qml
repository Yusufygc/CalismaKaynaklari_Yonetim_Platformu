import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property int activeTab: 0 // 0: Kategoriler, 1: Etiketler
    property string newCategoryColor: Theme.accent

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
                    width: 260
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
                            width: (parent.width - 4) / 2
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
                            width: (parent.width - 4) / 2
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

                            // Renk Paleti Seçimi
                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Repeater {
                                    model: Theme.categoryPalette
                                    Rectangle {
                                        width: 22
                                        height: 22
                                        radius: 11
                                        color: modelData
                                        border.width: String(root.newCategoryColor).toLowerCase() === String(modelData).toLowerCase() ? 2 : 0
                                        border.color: Theme.textOnAccent

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.newCategoryColor = modelData
                                        }
                                    }
                                }
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
                            Rectangle {
                                width: parent.width
                                height: 44
                                radius: Theme.radiusSm
                                color: Theme.bgElevated
                                border.width: 1
                                border.color: Theme.borderSubtle

                                Row {
                                    anchors.left: parent.left
                                    anchors.right: deleteCategoryButton.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 12
                                    spacing: 12

                                    Rectangle {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 10
                                        height: 10
                                        radius: 5
                                        color: modelData.color_hex || Theme.fallbackCategoryColor
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.name
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Medium
                                        color: Theme.textPrimary
                                    }

                                    AppBadge {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.resource_count + " kaynak"
                                        badgeColor: Theme.bgSurface
                                        borderColor: Theme.borderSubtle
                                        textColor: Theme.textMuted
                                    }
                                }

                                AppIconButton {
                                    id: deleteCategoryButton
                                    anchors.right: parent.right
                                    anchors.rightMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    iconName: "fa5s.trash"
                                    iconSize: 12
                                    tooltip: "Kategoriyi Sil"
                                    onClicked: bridge.settings.deleteCategory(modelData.id)
                                }
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
                            Rectangle {
                                implicitWidth: tagRow.implicitWidth + 20
                                implicitHeight: 32
                                radius: Theme.radiusPill
                                color: Theme.bgElevated
                                border.width: 1
                                border.color: Theme.borderSubtle

                                Row {
                                    id: tagRow
                                    anchors.centerIn: parent
                                    spacing: 8

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "#" + modelData.name
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Medium
                                        color: Theme.textPrimary
                                    }

                                    // Kaynak sayısı
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "(" + modelData.resource_count + ")"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        color: Theme.textMuted
                                    }

                                    AppIconButton {
                                        anchors.verticalCenter: parent.verticalCenter
                                        iconName: "fa5s.times"
                                        iconSize: 10
                                        implicitWidth: 18
                                        implicitHeight: 18
                                        tooltip: "Etiketi Sil"
                                        onClicked: bridge.settings.deleteTag(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ScrollBar.vertical: ScrollBar { active: true }
        }
    }
}
