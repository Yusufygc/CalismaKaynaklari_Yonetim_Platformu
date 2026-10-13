import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../theme"

// Bilgi Havuzu > Matris: literatür matrisi. Satır = makale, sütun = anlam etiketi (Yöntem, Bulgu / Sonuç, ...), hücre =
// o makalenin o türdeki alıntıları. Etiket / serbest etiket süzgeçleri üstte, kaynak süzgeci üst çubuktaki arama
// kutusudur (KnowledgePoolView). Alıntıya tıklamak okuyucuyu o alıntıda açar. Süzülmüş matris Markdown olarak
// dışa aktarılır ya da panoya kopyalanır (Obsidian'a yapıştırılabilir).
Item {
    id: root

    readonly property var matrix: bridge.synthesis.matrix
    readonly property var activeLabels: bridge.synthesis.activeLabels
    readonly property int headerWidth: 220
    readonly property int columnWidth: 280
    readonly property int tableWidth: headerWidth + matrix.columns.length * columnWidth
    readonly property int collapsedQuotes: 3  // hücrede ilk bu kadar alıntı görünür, gerisi "daha fazla" ile açılır

    onVisibleChanged: bridge.synthesis.setActive(visible)
    Component.onCompleted: bridge.synthesis.setActive(visible)

    FileDialog {
        id: exportDialog
        title: "Literatür Matrisini Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Markdown (*.md)"]
        defaultSuffix: "md"
        onAccepted: bridge.synthesis.exportMarkdown(selectedFile)
    }

    // ---- Süzgeç çubuğu ----
    Column {
        id: filterBar
        width: parent.width
        topPadding: 12
        bottomPadding: 10
        spacing: 8

        Item {
            width: parent.width
            height: 28

            Flow {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.right: actionRow.left
                anchors.rightMargin: 12
                spacing: 8

                Repeater {
                    model: root.matrix.columns
                    delegate: AppFilterChip {
                        required property var modelData
                        objectName: "matrixLabelChip"
                        text: modelData.name
                        count: modelData.count
                        dotColor: modelData.color !== "" ? modelData.color : Theme.textMuted
                        isSelected: root.activeLabels.indexOf(modelData.key) !== -1
                        onClicked: bridge.synthesis.toggleLabel(modelData.key)
                    }
                }
            }

            Row {
                id: actionRow
                anchors.right: parent.right
                anchors.rightMargin: 24
                spacing: 8

                AppButton {
                    objectName: "clearMatrixFiltersButton"
                    visible: bridge.synthesis.filtered
                    text: "Süzgeçleri temizle"
                    variant: "ghost"
                    implicitHeight: 28
                    onClicked: bridge.synthesis.clearFilters()
                }
                AppButton {
                    objectName: "copyMatrixButton"
                    text: "Panoya kopyala"
                    iconName: "fa5s.copy"
                    variant: "subtle"
                    implicitHeight: 28
                    enabledState: root.matrix.rowCount > 0
                    onClicked: bridge.synthesis.copyMarkdown()
                }
                AppButton {
                    objectName: "exportMatrixButton"
                    text: "Markdown'a aktar"
                    iconName: "fa5s.file-export"
                    variant: "subtle"
                    implicitHeight: 28
                    enabledState: root.matrix.rowCount > 0
                    onClicked: exportDialog.open()
                }
            }
        }

        Flow {
            objectName: "matrixTagRow"
            x: 24
            width: parent.width - 48
            spacing: 8
            visible: bridge.synthesis.tags.length > 0

            Repeater {
                model: bridge.synthesis.tags
                delegate: AppFilterChip {
                    required property var modelData
                    objectName: "matrixTagChip"
                    text: "#" + modelData.name
                    count: modelData.count
                    isSelected: bridge.synthesis.tag === modelData.name
                    onClicked: bridge.synthesis.setTag(modelData.name)
                }
            }
        }

        Text {
            objectName: "matrixSummary"
            x: 24
            text: root.matrix.rowCount + " kaynak · " + root.matrix.annotationCount + " alıntı"
                  + (bridge.synthesis.filtered ? " (süzülmüş)" : "")
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }

    Rectangle {
        id: divider
        anchors.top: filterBar.bottom
        width: parent.width
        height: 1
        color: Theme.borderSubtle
    }

    Text {
        objectName: "matrixEmpty"
        anchors.centerIn: parent
        visible: root.matrix.rowCount === 0
        horizontalAlignment: Text.AlignHCenter
        width: parent.width - 96
        wrapMode: Text.Wrap
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        color: Theme.textMuted
        text: bridge.synthesis.filtered
              ? "Süzgeçlerle eşleşen alıntı yok."
              : "Henüz alıntı yok. PDF okurken metni seçip bir anlam etiketiyle vurgula; makaleler burada yan yana görünür."
    }

    // ---- Matris: yatay kaydırılır; satırlar dikey sanallaştırılır ----
    Flickable {
        id: gridFlick
        anchors.top: divider.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: root.matrix.rowCount > 0
        contentWidth: root.tableWidth + 48
        contentHeight: height
        flickableDirection: Flickable.HorizontalFlick
        clip: true
        ScrollBar.horizontal: ScrollBar { active: true }

        // Sütun başlıkları
        Row {
            id: headerRow
            x: 24
            height: 32

            Rectangle {
                width: root.headerWidth
                height: parent.height
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    x: 10
                    text: "Kaynak"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    color: Theme.textSecondary
                }
            }

            Repeater {
                model: root.matrix.columns
                delegate: Rectangle {
                    required property var modelData
                    width: root.columnWidth
                    height: headerRow.height
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 10
                        spacing: 6
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 8
                            height: 8
                            radius: 4
                            color: modelData.color !== "" ? modelData.color : Theme.textMuted
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name + " (" + modelData.count + ")"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Bold
                            color: Theme.textSecondary
                        }
                    }
                }
            }
        }

        ListView {
            id: rowsList
            objectName: "matrixRows"
            x: 24
            y: headerRow.height
            width: root.tableWidth
            height: gridFlick.height - headerRow.height
            clip: true
            model: root.matrix.rows
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { active: true }

            delegate: RowLayout {
                id: matrixRow
                required property var modelData
                objectName: "matrixRow"
                width: root.tableWidth
                spacing: 0

                // Satır başlığı: kaynak adı (tıklayınca okuyucu), atıf anahtarı, yıl
                Rectangle {
                    Layout.preferredWidth: root.headerWidth
                    Layout.fillHeight: true
                    implicitHeight: headerCol.implicitHeight + 20
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Column {
                        id: headerCol
                        x: 10
                        y: 10
                        width: parent.width - 20
                        spacing: 4

                        Text {
                            objectName: "matrixRowTitle"
                            width: parent.width
                            wrapMode: Text.Wrap
                            text: matrixRow.modelData.title
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: bridge.reader.openReader(matrixRow.modelData.resourceId)
                            }
                        }
                        Text {
                            objectName: "matrixRowKey"
                            readonly property string key: matrixRow.modelData.citekey !== ""
                                ? matrixRow.modelData.citekey
                                : (matrixRow.modelData.suggestedCitekey !== "" ? matrixRow.modelData.suggestedCitekey + " (öneri)" : "")
                            width: parent.width
                            elide: Text.ElideRight
                            text: key + (matrixRow.modelData.year > 0 ? (key !== "" ? " · " : "") + matrixRow.modelData.year : "")
                            visible: text !== ""
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.italic: matrixRow.modelData.citekey === ""
                            color: Theme.textMuted
                        }
                    }
                }

                Repeater {
                    model: matrixRow.modelData.cells

                    delegate: Rectangle {
                        id: cell
                        required property var modelData
                        required property int index
                        property bool expanded: false
                        readonly property bool collapsible: modelData.length > root.collapsedQuotes
                        objectName: "matrixCell"
                        Layout.preferredWidth: root.columnWidth
                        Layout.fillHeight: true
                        implicitHeight: cellCol.implicitHeight + 16
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.borderSubtle

                        Column {
                            id: cellCol
                            x: 8
                            y: 8
                            width: parent.width - 16
                            spacing: 6

                            Repeater {
                                model: cell.expanded ? cell.modelData : cell.modelData.slice(0, root.collapsedQuotes)

                                delegate: Rectangle {
                                    id: quoteItem
                                    required property var modelData
                                    objectName: "matrixQuote"
                                    width: cellCol.width
                                    implicitHeight: quoteCol.implicitHeight + 10
                                    radius: Theme.radiusXs
                                    color: quoteMouse.containsMouse ? Theme.bgHover : Theme.bgElevated

                                    Column {
                                        id: quoteCol
                                        x: 6
                                        y: 5
                                        width: parent.width - 12
                                        spacing: 2

                                        Text {
                                            width: parent.width
                                            wrapMode: Text.Wrap
                                            text: "“" + quoteItem.modelData.text + "”"
                                            font.family: Theme.fontReading
                                            font.pixelSize: Theme.fontSm
                                            font.italic: true
                                            lineHeight: 1.2
                                            color: Theme.textPrimary
                                        }
                                        Text {
                                            width: parent.width
                                            wrapMode: Text.Wrap
                                            visible: quoteItem.modelData.comment !== ""
                                            text: "Yorum: " + quoteItem.modelData.comment
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            color: Theme.accentText
                                        }
                                        Text {
                                            width: parent.width
                                            elide: Text.ElideRight
                                            text: (quoteItem.modelData.orphaned ? "konumu bulunamadı" : quoteItem.modelData.pageLabel)
                                                  + (quoteItem.modelData.tags.length > 0 ? "  " + quoteItem.modelData.tags.map(function(t) { return "#" + t }).join(" ") : "")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 10
                                            color: Theme.textMuted
                                        }
                                    }

                                    MouseArea {
                                        id: quoteMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: bridge.synthesis.openAnnotation(matrixRow.modelData.resourceId, quoteItem.modelData.page, quoteItem.modelData.uid)
                                    }
                                }
                            }

                            Text {
                                objectName: "matrixCellToggle"
                                visible: cell.collapsible
                                text: cell.expanded ? "Daha az göster" : "+ " + (cell.modelData.length - root.collapsedQuotes) + " alıntı daha"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.underline: toggleMouse.containsMouse
                                color: Theme.accentText

                                MouseArea {
                                    id: toggleMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: cell.expanded = !cell.expanded
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
