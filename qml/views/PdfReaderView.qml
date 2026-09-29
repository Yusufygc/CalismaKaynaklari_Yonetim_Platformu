import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Pdf
import "../components"
import "../theme"

Item {
    id: root
    objectName: "pdfReaderView"

    property var resource: bridge.currentReaderResource
    // Okuyucu kapaninca resource bosalir; source'u "" yapmak Qt'de "Cannot open" uyarisi
    // basiyor. Son gecerli dosya URL'si tutulur, yalnizca yeni gecerli URL gelince degisir.
    property url lastPdfUrl: ""
    onResourceChanged: {
        if (resource && resource.pdfFileUrl)
            lastPdfUrl = resource.pdfFileUrl
    }
    property bool sidePanelOpen: false
    property bool searchOpen: false

    function openSearch() {
        root.searchOpen = true
        searchInput.forceActiveFocus()
        searchInput.selectAll()
    }

    function closeSearch() {
        root.searchOpen = false
        searchInput.text = ""
        pageArea.searchString = ""
    }

    Shortcut {
        sequences: [StandardKey.Find]
        enabled: root.visible
        onActivated: root.openSearch()
    }

    PaperInfoPopup {
        id: paperInfoPopup
        objectName: "paperInfoPopup"
        anchors.centerIn: Overlay.overlay
        resource: root.resource ?? ({})
    }

    FileDialog {
        id: exportDialog
        title: "Alıntı ve Notları Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Markdown (*.md)"]
        defaultSuffix: "md"
        onAccepted: if (root.resource) bridge.exportResourceMarkdown(root.resource.id, selectedFile)
    }

    PdfDocument {
        id: pdfDoc
        objectName: "pdfDoc"
        source: root.lastPdfUrl
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // Üst Bar
        Item {
            id: topBar
            width: parent.width
            height: 56

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                AppButton {
                    text: "Vitrine Dön"
                    iconName: "fa5s.arrow-left"
                    variant: "ghost"
                    onClicked: bridge.closeReader()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.resource && root.resource.title ? root.resource.title : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    // Sag butonlarla (sayfa sayaci, zoom, ...) ust uste binmesin.
                    width: Math.max(60, Math.min(implicitWidth, topBar.width - topRightRow.width - 250))
                }
            }

            Row {
                id: topRightRow
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                AppIconButton {
                    iconName: "fa5s.columns"
                    iconSize: 12
                    tooltip: "Sayfalar / Anahat / Notlarım"
                    isActive: root.sidePanelOpen
                    onClicked: root.sidePanelOpen = !root.sidePanelOpen
                }

                AppIconButton {
                    iconName: "fa5s.search"
                    iconSize: 12
                    tooltip: "Metinde Ara (Ctrl+F)"
                    isActive: root.searchOpen
                    onClicked: root.searchOpen ? root.closeSearch() : root.openSearch()
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: pdfDoc.status === PdfDocument.Ready
                          ? (pageArea.currentPage + 1) + " / " + pdfDoc.pageCount
                          : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppButton {
                    text: "Not Ekle"
                    iconName: "fa5s.comment-alt"
                    variant: pageArea.noteMode ? "primary" : "ghost"
                    onClicked: pageArea.noteMode = !pageArea.noteMode
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppIconButton {
                    iconName: "fa5s.search-minus"
                    iconSize: 12
                    tooltip: "Uzaklaştır"
                    onClicked: pageArea.zoomOut()
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Math.round(pageArea.renderScale * 100) + "%"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppIconButton {
                    iconName: "fa5s.search-plus"
                    iconSize: 12
                    tooltip: "Yakınlaştır"
                    onClicked: pageArea.zoomIn()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppIconButton {
                    iconName: "fa5s.quote-left"
                    iconSize: 12
                    tooltip: "Atıf / Kaynak Bilgisi"
                    onClicked: paperInfoPopup.open()
                }

                AppIconButton {
                    iconName: "fa5s.file-export"
                    iconSize: 12
                    tooltip: "Alıntı ve Notları Markdown Olarak Dışa Aktar"
                    onClicked: exportDialog.open()
                }

                AppIconButton {
                    iconName: "fa5s.external-link-alt"
                    iconSize: 12
                    tooltip: "Sistem Görüntüleyicisinde Aç"
                    onClicked: {
                        if (root.resource && root.resource.url) {
                            Qt.openUrlExternally(root.resource.url)
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

        // Arama Çubuğu (Ctrl+F)
        Item {
            id: searchBar
            width: parent.width
            height: root.searchOpen ? 44 : 0
            visible: root.searchOpen
            clip: true

            // Sonuc sayisi icin gorunmez sayac (PdfSearchModel'de count property'si yok).
            Instantiator {
                id: searchCounter
                model: pageArea.searchModel
                delegate: QtObject {}
            }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    width: 320
                    height: 30
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: searchInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    TextInput {
                        id: searchInput
                        objectName: "searchInput"
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        clip: true
                        onTextChanged: pageArea.searchString = text
                        onAccepted: pageArea.searchForward()
                        Keys.onEscapePressed: root.closeSearch()

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Metinde ara..."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textMuted
                            visible: !searchInput.text
                        }
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: searchInput.text.length > 0
                    text: searchCounter.count > 0
                          ? (pageArea.searchModel.currentResult + 1) + " / " + searchCounter.count
                          : "Sonuç yok"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppIconButton {
                    iconName: "fa5s.chevron-up"
                    iconSize: 11
                    tooltip: "Önceki sonuç"
                    onClicked: pageArea.searchBack()
                }

                AppIconButton {
                    iconName: "fa5s.chevron-down"
                    iconSize: 11
                    tooltip: "Sonraki sonuç (Enter)"
                    onClicked: pageArea.searchForward()
                }

                AppIconButton {
                    iconName: "fa5s.times"
                    iconSize: 11
                    tooltip: "Aramayı kapat (Esc)"
                    onClicked: root.closeSearch()
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // PDF Gövdesi (yan panel + sayfalar)
        Item {
            clip: true
            width: parent.width
            height: parent.height - 56 - searchBar.height

            PdfSidePanel {
                id: sidePanel
                objectName: "sidePanel"
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: root.sidePanelOpen ? 300 : 0
                visible: root.sidePanelOpen
                document: pdfDoc
                resource: root.resource ?? ({})
                currentPage: pageArea.currentPage
                onPageRequested: (page, location) => pageArea.goToLocation(page, location, 0)
            }

            PdfPageArea {
                id: pageArea
                objectName: "pageArea"
                anchors.left: sidePanel.right
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                document: pdfDoc
                resource: root.resource ?? ({})
            }

            Column {
                anchors.centerIn: parent
                spacing: 8
                visible: pdfDoc.status !== PdfDocument.Ready

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: {
                        if (pdfDoc.status === PdfDocument.Error)
                            return "PDF açılamadı: " + pdfDoc.error
                        if (root.resource && root.resource.pdfState === "downloading")
                            return "PDF indiriliyor..."
                        return "PDF yükleniyor..."
                    }
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }

                AppButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: pdfDoc.status === PdfDocument.Error
                             || (root.resource && root.resource.pdfState === "downloading")
                    text: "Metin Okuyucusunda Aç"
                    variant: "subtle"
                    onClicked: if (root.resource) bridge.openTextReader(root.resource.id)
                }
            }
        }
    }
}
