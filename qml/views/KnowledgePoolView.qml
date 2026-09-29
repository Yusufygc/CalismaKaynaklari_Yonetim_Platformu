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

    // Alıntılar: toplu silme için seçim (id -> true; değişince yeniden atanır ki bağlamalar tazelensin)
    property var selectedIds: ({})
    readonly property int selectedCount: Object.keys(selectedIds).length

    function toggleSelected(id) {
        const next = Object.assign({}, root.selectedIds)
        if (next[id]) delete next[id]
        else next[id] = true
        root.selectedIds = next
    }

    function selectAllVisible() {
        const next = {}
        const list = highlightsList.model
        for (let i = 0; i < list.length; i++) next[list[i].id] = true
        root.selectedIds = next
    }

    function clearSelection() {
        root.selectedIds = ({})
    }

    function deleteSelected() {
        bridge.reader.deleteHighlights(Object.keys(root.selectedIds).map(Number))
        root.clearSelection()
    }

    // Görünmeyen (filtre/arama/sekme dışı) alıntı yanlışlıkla silinmesin: görünüm değişince seçimi bırak.
    onLabelFilterChanged: clearSelection()
    onSearchQueryChanged: clearSelection()
    onActiveTabChanged: clearSelection()

    Popup {
        id: confirmDeletePopup
        anchors.centerIn: Overlay.overlay
        width: 360
        padding: 20
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.popoverBg
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderStrong
        }

        contentItem: Column {
            spacing: 14

            Text {
                text: "Alıntıları Sil"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: root.selectedCount + " alıntı kalıcı olarak silinecek. Bu işlem geri alınamaz."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                AppButton {
                    text: "Vazgeç"
                    variant: "ghost"
                    onClicked: confirmDeletePopup.close()
                }

                AppButton {
                    text: "Sil (" + root.selectedCount + ")"
                    iconName: "fa5s.trash"
                    variant: "danger"
                    onClicked: {
                        confirmDeletePopup.close()
                        root.deleteSelected()
                    }
                }
            }
        }
    }

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

        // 2. İçerik Listeleri (Alıntılar veya Kelimeler)
        Item {
            width: parent.width
            height: parent.height - 64

            // --- SEKME 0: ALINTILAR ---
            // Toplu seçim çubuğu
            Item {
                id: selectionBar
                visible: root.activeTab === 0 && bridge.reader.highlights.length > 0
                width: parent.width
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
                        onClicked: root.selectAllVisible()
                    }

                    AppButton {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.selectedCount > 0
                        text: "Seçimi temizle"
                        variant: "ghost"
                        implicitHeight: 28
                        onClicked: root.clearSelection()
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.selectedCount > 0
                        text: root.selectedCount + " seçili"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }

                AppButton {
                    anchors.right: parent.right
                    anchors.rightMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Seçilenleri Sil (" + root.selectedCount + ")"
                    iconName: "fa5s.trash"
                    variant: "danger"
                    implicitHeight: 28
                    enabledState: root.selectedCount > 0
                    onClicked: confirmDeletePopup.open()
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.borderSubtle
                }
            }

            ListView {
                id: highlightsList
                visible: root.activeTab === 0
                anchors.top: selectionBar.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 24
                anchors.topMargin: 12
                spacing: 12
                clip: true

                model: {
                    var all = bridge.reader.highlights
                    return all.filter(function(h) {
                        if (root.labelFilter !== "" && h.label !== root.labelFilter) return false
                        if (!root.searchQuery) return true
                        return TextUtils.foldTr(h.content).indexOf(root.searchQuery) !== -1 ||
                               TextUtils.foldTr(h.resource_title).indexOf(root.searchQuery) !== -1 ||
                               TextUtils.foldTr(h.comment).indexOf(root.searchQuery) !== -1
                    })
                }

                // Akademik anlam etiketine göre filtre (Yöntem, Bulgu / Sonuç, ...)
                header: Flow {
                    width: highlightsList.width - 24
                    spacing: 8
                    bottomPadding: 12

                    AppFilterChip {
                        text: "Tümü"
                        isSelected: root.labelFilter === ""
                        onClicked: root.labelFilter = ""
                    }

                    Repeater {
                        model: bridge.reader.highlightLabels
                        delegate: AppFilterChip {
                            required property var modelData
                            text: modelData.label
                            dotColor: modelData.color
                            isSelected: root.labelFilter === modelData.label
                            onClicked: root.labelFilter = (root.labelFilter === modelData.label ? "" : modelData.label)
                        }
                    }
                }

                delegate: Rectangle {
                    width: highlightsList.width - 24
                    implicitHeight: hlCardCol.implicitHeight + 24
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    // Sol Renk Çizgisi
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 4
                        radius: 2
                        color: modelData.color || Theme.accent
                    }

                    // Toplu silme seçim kutusu
                    Rectangle {
                        id: hlCheckBox
                        readonly property bool checked: root.selectedIds[modelData.id] === true
                        x: 16
                        y: 14
                        width: 18
                        height: 18
                        radius: 4
                        color: checked ? Theme.accent : "transparent"
                        border.width: 1
                        border.color: checked ? Theme.accent : Theme.borderStrong

                        AppIcon {
                            anchors.centerIn: parent
                            visible: hlCheckBox.checked
                            name: "fa5s.check"
                            size: 10
                            color: Theme.textOnAccent
                        }

                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -4
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleSelected(modelData.id)
                        }
                    }

                    Column {
                        id: hlCardCol
                        anchors.fill: parent
                        anchors.leftMargin: 44
                        anchors.rightMargin: 16
                        anchors.topMargin: 12
                        anchors.bottomMargin: 12
                        spacing: 8

                        // Alıntı Metni
                        Text {
                            width: parent.width - 50
                            text: "“" + modelData.content + "”"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.italic: true
                            lineHeight: 1.3
                            color: Theme.textPrimary
                            wrapMode: Text.Wrap
                        }

                        // Anlam etiketi + sayfa
                        Text {
                            text: modelData.label + (modelData.page >= 0 ? " · Sayfa " + (modelData.page + 1) : "")
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: Theme.textMuted
                        }

                        // Kullanıcının yorumu
                        Text {
                            width: parent.width - 50
                            visible: modelData.comment !== ""
                            text: "Yorum: " + modelData.comment
                            wrapMode: Text.Wrap
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.italic: true
                            color: Theme.accentText
                        }

                        // Alt Bilgi: Kaynak Başlığı & Sil
                        Item {
                            width: parent.width
                            height: Math.max(hlFooterRow.implicitHeight, hlDeleteButton.height)

                            Row {
                                id: hlFooterRow
                                anchors.left: parent.left
                                anchors.right: hlDeleteButton.left
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8

                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "fa5s.book-open"
                                    size: 11
                                    color: Theme.accent
                                }

                                // Kaynak Bağlantısı (Tıklandığında okuyucuyu açar)
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.resource_title
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Medium
                                    color: Theme.accentText

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: bridge.reader.openReader(modelData.resource_id)
                                    }
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "• " + modelData.created_at
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }
                            }

                            AppIconButton {
                                id: hlDeleteButton
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                iconName: "fa5s.trash"
                                iconSize: 11
                                tooltip: "Alıntıyı Sil"
                                onClicked: bridge.reader.deleteHighlight(modelData.id)
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }

            // --- SEKME 1: KELİMELER ---
            ListView {
                id: vocabList
                visible: root.activeTab === 1
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                clip: true

                model: {
                    var all = bridge.reader.vocabulary
                    if (!root.searchQuery) return all
                    return all.filter(function(v) {
                        return TextUtils.foldTr(v.word).indexOf(root.searchQuery) !== -1 ||
                               TextUtils.foldTr(v.translation).indexOf(root.searchQuery) !== -1
                    })
                }

                delegate: Rectangle {
                    width: vocabList.width - 24
                    implicitHeight: vocabCol.implicitHeight + 20
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        id: vocabCol
                        anchors.left: parent.left
                        anchors.right: vocabDeleteButton.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 16

                        // Kelime
                        Column {
                            width: 200
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Text {
                                text: modelData.word
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontMd
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: modelData.resource_title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.accentText
                                elide: Text.ElideRight
                                width: parent.width

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: bridge.reader.openReader(modelData.resource_id)
                                }
                            }
                        }

                        // Anlamı (Çeviri)
                        Text {
                            width: parent.width - 320
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.translation
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Medium
                            color: Theme.textSecondary
                            wrapMode: Text.Wrap
                        }

                    }

                    AppIconButton {
                        id: vocabDeleteButton
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        iconName: "fa5s.trash"
                        iconSize: 11
                        tooltip: "Kelimeyi Sil"
                        onClicked: bridge.reader.deleteVocabulary(modelData.id)
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }
        }
    }
}
