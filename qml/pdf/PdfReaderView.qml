import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Pdf
import "../components"
import "../theme"

Item {
    id: root
    objectName: "pdfReaderView"

    property var resource: bridge.reader.currentReaderResource
    // Okuyucu kapaninca resource bosalir; source'u "" yapmak Qt'de "Cannot open" uyarisi
    // basiyor. Son gecerli dosya URL'si tutulur, yalnizca yeni gecerli URL gelince degisir.
    property url lastPdfUrl: ""
    onResourceChanged: {
        if (resource && resource.pdfFileUrl)
            lastPdfUrl = resource.pdfFileUrl
    }

    // pdfkit belge oturumu: okuyucu kaynağı değişince açılır, kaynak boşalınca (okuyucu kapanınca) kapanır.
    // Alıntı/not/kelime modelleri `bridge.pdf` üzerinden gelir; kaynak sözlüğü yalnız başlık/durum içindir.
    readonly property int resourceId: resource && resource.id ? resource.id : 0
    readonly property string resourcePdfUrl: resource && resource.pdfFileUrl ? resource.pdfFileUrl : ""
    function syncDocument() {
        if (resourceId > 0 && resourcePdfUrl !== "")
            bridge.pdf.openDocument(resourceId)
        else
            bridge.pdf.closeDocument()
    }
    onResourceIdChanged: {
        relinkTargetId = 0
        pageArea.flushViewState()  // onceki belgenin son konumu (oturum henuz eski belgede)
        pageArea.trackView = false
        if (resourceId === 0)
            restoredResourceId = 0
        syncDocument()
    }
    onResourcePdfUrlChanged: syncDocument()
    Component.onCompleted: syncDocument()

    // Kaldığı yerden devam: belge hazır olunca (QML belgesi + pdfkit oturumu) kayıtlı sayfa/konum/zoom'a gidilir.
    // Geri yükleme bitip yerleşene kadar konum kaydı kapalıdır (eski kayıt sayfa 0 ile ezilmesin).
    property int restoredResourceId: 0
    property int appliedJumpToken: 0

    // Derin baglanti (pkm://open?...) hedefi: belge hazir ve kaldigi yer geri yuklenmisse hedef sayfa/konuma gidilir
    // (kayitli okuma durumundan once gelir). `bridge.pdf.jumpTarget` her istekte yeni `token` tasir.
    function applyJump() {
        const target = bridge.pdf.jumpTarget
        if (target.token === undefined || target.token === appliedJumpToken)
            return
        if (pdfDoc.status !== PdfDocument.Ready || restoredResourceId !== resourceId || resourceId === 0)
            return
        appliedJumpToken = target.token
        if (target.find) {
            // Tam metin aramasi sonucu: arama cubugu aranan sozcukle acilir (sayfadaki eslesmeler boyanir). Cubugun
            // acilmasi sayfa alaninin yuksekligini degistirdigi icin atlama yerlesim oturduktan sonra yapilir.
            root.searchOpen = true
            searchInput.text = target.find
            deferredJump = target
            findJumpTimer.restart()
            return
        }
        pageArea.goToLocation(target.page, Qt.point(target.x, target.y), 0)
    }
    property var deferredJump: null
    Timer {
        id: findJumpTimer
        interval: 120
        onTriggered: {
            if (root.deferredJump)
                pageArea.goToLocation(root.deferredJump.page, Qt.point(root.deferredJump.x, root.deferredJump.y), 0)
            root.deferredJump = null
        }
    }
    property bool textLayerBannerDismissed: false

    // Yetim alintiyi yeniden baglama: yan panelden baslar, sayfada yeni metin secilince biter (bkz. PdfSelectionOverlay).
    property int relinkTargetId: 0
    property string relinkQuote: ""
    // Son acilan belgenin metin katmani durumu. Okuyucu kapanirken oturum basligi bosalir; bandin yuksekligi o anda
    // degisirse sayfa alani kapanista yeniden yerlesir (Qt TableView cokmesi gozlendi), bu yuzden deger yalniz yeni
    // belge acilinca guncellenir.
    property bool textLayerMissing: false
    function tryRestore() {
        if (resourceId === 0 || restoredResourceId === resourceId || pdfDoc.status !== PdfDocument.Ready)
            return
        if (bridge.pdf.currentDocument.resourceId !== resourceId)
            return
        restoredResourceId = resourceId
        const state = bridge.pdf.readingState
        // Bekleyen derin baglanti hedefi varsa kayitli konuma hic gidilmez: iki atlama ust uste binerse sayfa alani
        // yerlesimi (asenkron) ikincisini bozuyor.
        const jump = bridge.pdf.jumpTarget
        const jumpPending = jump.token !== undefined && jump.token !== appliedJumpToken
        if (state.hasState && !jumpPending)
            pageArea.restoreView(state.page, state.x, state.y, state.zoom)
        trackSettleTimer.restart()
        applyJump()
    }
    Timer {
        id: trackSettleTimer
        interval: 700
        onTriggered: pageArea.trackView = root.restoredResourceId === root.resourceId && root.resourceId > 0
    }
    Connections {
        target: pdfDoc
        function onStatusChanged() { root.tryRestore() }
    }
    Connections {
        target: bridge.pdf
        function onJumpTargetChanged() { root.applyJump() }
        function onCurrentDocumentChanged() {
            const document = bridge.pdf.currentDocument
            if (document.documentId !== undefined) {
                root.textLayerMissing = document.hasTextLayer === false
                root.textLayerBannerDismissed = false  // her belge acilisinda bant yeniden gorunur
            }
            root.tryRestore()
        }
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
        onAccepted: if (root.resource) bridge.reader.exportResourceMarkdown(root.resource.id, selectedFile)
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
                    onClicked: bridge.reader.closeReader()
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

        // Metin katmanı uyarısı: taranmış (görüntü) PDF'lerde seçim, alıntı, kelime ve arama çalışmaz.
        Item {
            id: textLayerBanner
            objectName: "noTextLayerBanner"
            readonly property bool shown: root.textLayerMissing && !root.textLayerBannerDismissed
            width: parent.width
            height: shown ? 40 : 0
            visible: shown
            clip: true

            Rectangle {
                anchors.fill: parent
                color: Theme.statusInProgressBg
            }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.right: dismissBannerButton.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                AppIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    name: "fa5s.exclamation-triangle"
                    size: 13
                    color: Theme.statusInProgress
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 23
                    elide: Text.ElideRight
                    text: "Metin katmanı yok (taranmış PDF): seçim, alıntı ve arama çalışmaz. Sayfa notu eklenebilir."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                }
            }

            AppButton {
                id: dismissBannerButton
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: "Gizle"
                variant: "ghost"
                onClicked: root.textLayerBannerDismissed = true
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
            height: parent.height - 56 - searchBar.height - textLayerBanner.height

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
                onRelinkRequested: (annotationId, quote) => {
                    root.relinkTargetId = annotationId
                    root.relinkQuote = quote
                }
            }

            PdfPageArea {
                id: pageArea
                objectName: "pageArea"
                anchors.left: sidePanel.right
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                document: pdfDoc
                relinkTargetId: root.relinkTargetId
                onRelinkCompleted: root.relinkTargetId = 0
                onViewStateChanged: (page, x, y, zoom, seenPage) => bridge.pdf.saveReadingState(page, x, y, zoom, seenPage)
            }

            // Yeniden baglama bilgisi: sayfa alaninin ustunde yuzer (yerlesimi etkilemez; okuyucu kapanirken yukseklik
            // degisimi sayfa alanini yeniden yerlestirip cokmeye yol aciyordu).
            Rectangle {
                id: relinkBanner
                objectName: "relinkBanner"
                visible: root.relinkTargetId > 0
                z: 60
                anchors.top: parent.top
                anchors.topMargin: 10
                anchors.horizontalCenter: pageArea.horizontalCenter
                width: Math.min(pageArea.width - 40, relinkRow.implicitWidth + 24)
                height: 40
                radius: Theme.radiusPill
                color: Theme.popoverBg
                border.width: 1
                border.color: Theme.accent

                Row {
                    id: relinkRow
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(420, implicitWidth)
                        elide: Text.ElideRight
                        text: "Sayfada yeni metni seç: “" + root.relinkQuote + "”"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                    }

                    AppButton {
                        objectName: "cancelRelinkButton"
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Vazgeç"
                        variant: "ghost"
                        implicitHeight: 28
                        onClicked: root.relinkTargetId = 0
                    }
                }
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
                    onClicked: if (root.resource) bridge.reader.openTextReader(root.resource.id)
                }
            }
        }
    }
}
