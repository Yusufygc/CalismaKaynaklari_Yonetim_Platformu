import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"
import "../theme"
import "../js/text.js" as TextUtils

Item {
    id: root

    property int activeTab: 0 // 0: Alıntılar, 1: Kelimeler
    property string searchQuery: ""
    property string labelFilter: "" // Alıntılar: akademik anlam etiketi ("" = tümü)

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Sekmeler ve Arama
        Item {
            width: parent.width
            height: 64

            Row {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 16

                // Sekme Butonları (Pill Bar)
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 280
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 4

                        // Alıntılar Sekmesi
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
                                    name: "fa5s.quote-right"
                                    size: 11
                                    color: root.activeTab === 0 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Alıntılar (" + bridge.reader.highlights.length + ")"
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

                        // Kelime Dağarcığı Sekmesi
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
                                    name: "fa5s.language"
                                    size: 12
                                    color: root.activeTab === 1 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Kelimeler (" + bridge.reader.vocabulary.length + ")"
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

                // Arama Kutusu
                AppSearchBar {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 280
                    placeholder: root.activeTab === 0 ? "Alıntılarda ara..." : "Kelimelerde ara..."
                    onSearchChanged: function(q) { root.searchQuery = TextUtils.foldTr(q) }
                    onSearchCleared: { root.searchQuery = "" }
                }
            }

            // Tüm kütüphanenin alıntı/not/kelimelerini tek Markdown'a aktar (literatür taraması)
            AppButton {
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                text: "Tümünü Dışa Aktar (.md)"
                iconName: "fa5s.file-export"
                variant: "subtle"
                onClicked: libraryExportDialog.open()
            }

            FileDialog {
                id: libraryExportDialog
                title: "Literatür Notlarını Dışa Aktar"
                fileMode: FileDialog.SaveFile
                nameFilters: ["Markdown (*.md)"]
                defaultSuffix: "md"
                onAccepted: bridge.reader.exportLibraryMarkdown(selectedFile)
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // 2. İçerik: Alıntılar / Kelimeler sekmeleri
        Item {
            width: parent.width
            height: parent.height - 64

            HighlightsTab {
                anchors.fill: parent
                visible: root.activeTab === 0
                searchQuery: root.searchQuery
                labelFilter: root.labelFilter
                onLabelFilterRequested: (label) => root.labelFilter = label
            }

            VocabularyTab {
                anchors.fill: parent
                visible: root.activeTab === 1
                searchQuery: root.searchQuery
            }
        }
    }
}
