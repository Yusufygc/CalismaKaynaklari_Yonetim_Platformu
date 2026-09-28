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

            Row {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 12

                // Arama Kutusu
                AppSearchBar {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 320
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

                // Yatay Kaydırılabilir Kategori Filtreleri
                Flickable {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 320 - 150 - 24
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

                Item { Layout.fillWidth: true }

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
                cellHeight: 305
                model: bridge.resourcesModel

                delegate: AppCard {
                    cardWidth: 274
                    cardHeight: 290
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
