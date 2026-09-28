import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../theme"

Item {
    id: root

    property string searchQuery: ""
    property int selectedCategoryId: 0
    property string selectedStatus: "ALL"
    property bool favoriteOnly: false

    signal newResourceRequested()
    signal cardSelected(int resourceId)

    function updateFilters() {
        bridge.applyFilter(
            searchQuery,
            selectedCategoryId.toString(),
            "0",
            selectedStatus,
            favoriteOnly
        )
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Arama, Hızlı Kategori Seçimi & Yeni Ekle
        Item {
            width: parent.width
            height: 64

            // Sol Taraf: Arama Kutusu
            AppSearchBar {
                id: searchBar
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                width: 280
                placeholder: "Kaynaklarda ara (başlık, not veya URL)..."
                onSearchChanged: function(q) {
                    root.searchQuery = q
                    root.updateFilters()
                }
                onSearchCleared: {
                    root.searchQuery = ""
                    root.updateFilters()
                }
            }

            // Sağ Taraf: Görünüm Seçici & Yeni Ekle Aksiyonları
            Row {
                id: rightActionsRow
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                // Görünüm Modu Seçici (Zengin / Sade Görünüm Kapsülü)
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    height: 32
                    width: 68
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.centerIn: parent
                        spacing: 2

                        AppIconButton {
                            iconName: "fa5s.th-large"
                            iconSize: 12
                            implicitWidth: 30
                            implicitHeight: 26
                            tooltip: "Zengin Görünüm"
                            tooltipPosition: "bottom"
                            isActive: !bridge.isSimpleMode
                            activeBgColor: Theme.accentSubtle
                            iconColor: !bridge.isSimpleMode ? Theme.accent : Theme.textSecondary
                            onClicked: bridge.setSimpleMode(false)
                        }

                        AppIconButton {
                            iconName: "fa5s.th-list"
                            iconSize: 12
                            implicitWidth: 30
                            implicitHeight: 26
                            tooltip: "Sade Görünüm"
                            tooltipPosition: "bottom"
                            isActive: bridge.isSimpleMode
                            activeBgColor: Theme.accentSubtle
                            iconColor: bridge.isSimpleMode ? Theme.accent : Theme.textSecondary
                            onClicked: bridge.setSimpleMode(true)
                        }
                    }
                }

                // Yeni Kaynak Ekle Butonu
                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Yeni Ekle"
                    iconName: "fa5s.plus"
                    variant: "primary"
                    implicitHeight: 36
                    onClicked: root.newResourceRequested()
                }
            }

            // Orta Alan: Yatay Kaydırılabilir Kategori Filtreleri
            Flickable {
                id: catFlickable
                anchors.left: searchBar.right
                anchors.leftMargin: 12
                anchors.right: rightActionsRow.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                height: 32
                contentWidth: catRow.implicitWidth
                clip: true

                Row {
                    id: catRow
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    AppFilterChip {
                        text: "Tüm Kategoriler"
                        isSelected: root.selectedCategoryId === 0
                        onClicked: {
                            root.selectedCategoryId = 0
                            root.updateFilters()
                        }
                    }

                    Repeater {
                        model: bridge.categories
                        AppFilterChip {
                            text: modelData.name
                            dotColor: modelData.color_hex || Theme.fallbackCategoryColor
                            count: modelData.resource_count
                            isSelected: root.selectedCategoryId === modelData.id
                            onClicked: {
                                if (root.selectedCategoryId === modelData.id) {
                                    root.selectedCategoryId = 0
                                } else {
                                    root.selectedCategoryId = modelData.id
                                }
                                root.updateFilters()
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

        // 2. Kart Grid Alanı (Showcase)
        Item {
            width: parent.width
            height: parent.height - 64

            // Boş Durum
            Column {
                anchors.centerIn: parent
                spacing: 12
                visible: bridge.resourcesModel.rowCount() === 0

                Rectangle {
                    width: 64
                    height: 64
                    radius: Theme.radiusMd
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle
                    anchors.horizontalCenter: parent.horizontalCenter

                    AppIcon {
                        anchors.centerIn: parent
                        name: "fa5s.bookmark"
                        size: 26
                        color: Theme.textMuted
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Henüz kriterlere uygun kaynak yok"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Yeni bir web bağlantısı veya not ekleyerek başlayın."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }

                AppButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "İlk Kaynağı Ekle"
                    iconName: "fa5s.plus"
                    variant: "subtle"
                    onClicked: root.newResourceRequested()
                }
            }

            // Kartlar GridView
            GridView {
                id: grid
                anchors.fill: parent
                anchors.margins: 24
                visible: bridge.resourcesModel.rowCount() > 0
                clip: true

                cellWidth: 290
                cellHeight: bridge.isSimpleMode ? 148 : 305
                model: bridge.resourcesModel

                delegate: AppCard {
                    isSimple: bridge.isSimpleMode
                    cardWidth: 274
                    cardHeight: bridge.isSimpleMode ? 136 : 290
                    onClicked: {
                        bridge.selectResource(model.id)
                        root.cardSelected(model.id)
                    }
                    onPinToggled: bridge.togglePin(model.id)
                    onFavoriteToggled: bridge.toggleFavorite(model.id)
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }
        }
    }
}
