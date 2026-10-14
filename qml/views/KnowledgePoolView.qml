import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"
import "../theme"
import "../js/text.js" as TextUtils

Item {
    id: root

    property int activeTab: 0 // 0: Alıntılar, 1: Kelimeler, 2: Metinde Ara (PDF içeriği), 3: Matris (literatür matrisi)
    property string searchQuery: ""
    property string rawQuery: "" // katlanmamış arama metni (Metinde Ara: tırnaklı ifade, özgün yazım)
    property string labelFilter: "" // Alıntılar: akademik anlam etiketi ("" = tümü)
    property string tagFilter: "" // Alıntılar: serbest etiket ("" = tümü)

    // Metinde Ara sekmesi açıkken sorgu (ya da sekme) değişince PDF içeriğinde arar; bekletme köprüdedir.
    function syncContentSearch() {
        bridge.contentSearch.search(root.activeTab === 2 ? root.rawQuery : "")
        bridge.synthesis.setTitleQuery(root.activeTab === 3 ? root.rawQuery : "")  // Matris: kaynak süzgeci
    }
    onRawQueryChanged: syncContentSearch()
    onActiveTabChanged: syncContentSearch()

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Sekmeler, Arama ve dışa aktarma. Dar pencerede sekmeler ve arama küçülür, dışa aktarma düğmesi
        // yalnız simgeye iner; böylece hiçbiri üst üste binmez (en küçük pencere 960 px).
        Item {
            id: topBar
            width: parent.width
            height: 64
            readonly property bool compactExport: width < 1100
            readonly property int exportWidth: compactExport ? 36 : exportButton.implicitWidth
            readonly property int available: width - 48 - exportWidth - 32  // iki boşluk (16) ve sağdaki düğme payı
            readonly property int tabsWidth: Math.round(Math.min(540, available * 0.66))
            readonly property int searchWidth: Math.max(150, Math.min(280, available - tabsWidth))

            Row {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 24
                spacing: 16

                // Sekme Butonları (Pill Bar)
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: topBar.tabsWidth
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
                                    name: "fa5s.quote-right"
                                    size: 11
                                    color: root.activeTab === 0 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Alıntılar (" + bridge.annotations.highlights.length + ")"
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
                                    name: "fa5s.language"
                                    size: 12
                                    color: root.activeTab === 1 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Kelimeler (" + bridge.annotations.vocabulary.length + ")"
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

                        // Metinde Ara Sekmesi (PDF içeriği)
                        Rectangle {
                            objectName: "contentSearchTab"
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
                                    name: "fa5s.search"
                                    size: 11
                                    color: root.activeTab === 2 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Metinde Ara"
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

                        // Matris Sekmesi (literatür matrisi: kaynak x anlam etiketi)
                        Rectangle {
                            objectName: "matrixTab"
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
                                    name: "fa5s.th"
                                    size: 11
                                    color: root.activeTab === 3 ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Matris"
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

                // Arama Kutusu
                AppSearchBar {
                    anchors.verticalCenter: parent.verticalCenter
                    width: topBar.searchWidth
                    placeholder: root.activeTab === 0 ? "Alıntılarda ara..." : (root.activeTab === 1 ? "Kelimelerde ara..." : (root.activeTab === 2 ? "PDF'lerin içinde ara..." : "Kaynak ara (başlık, atıf anahtarı)..."))
                    onSearchChanged: function(q) { root.searchQuery = TextUtils.foldTr(q); root.rawQuery = q }
                    onSearchCleared: { root.searchQuery = ""; root.rawQuery = "" }
                }
            }

            // Tüm kütüphanenin alıntı/not/kelimelerini tek Markdown'a aktar (literatür taraması)
            AppButton {
                id: exportButton
                objectName: "libraryExportButton"
                visible: !topBar.compactExport
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                text: "Tümünü Dışa Aktar (.md)"
                iconName: "fa5s.file-export"
                variant: "subtle"
                onClicked: libraryExportDialog.open()
            }

            AppIconButton {
                objectName: "libraryExportIconButton"
                visible: topBar.compactExport
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                iconName: "fa5s.file-export"
                iconSize: 14
                implicitWidth: 36
                implicitHeight: 36
                tooltip: "Tümünü Dışa Aktar (.md)"
                tooltipPosition: "bottom"
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
                tagFilter: root.tagFilter
                onTagFilterRequested: (tag) => root.tagFilter = tag
            }

            VocabularyTab {
                anchors.fill: parent
                visible: root.activeTab === 1
                searchQuery: root.searchQuery
            }

            ContentSearchTab {
                anchors.fill: parent
                visible: root.activeTab === 2
            }

            MatrixTab {
                anchors.fill: parent
                visible: root.activeTab === 3
            }
        }
    }
}
