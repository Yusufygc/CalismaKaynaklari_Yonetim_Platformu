// Qt'nin QtQuick.Pdf modülündeki PdfMultiPageView.qml temel alınıp
// tema (Theme.qml) + highlight/not overlay noktalarıyla uyarlandı.
// Kaynak: .venv/Lib/site-packages/PySide6/qml/QtQuick/Pdf/PdfMultiPageView.qml
// (Qt dokümantasyonu bu dosyayı kopyala-değiştir başlangıç noktası olarak öneriyor.)

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Pdf
import QtQuick.Shapes
import "../theme"

Item {
    id: root
    // Sayfalar kaydirilirken alanin disina (ust cubuga) tasmasin.
    clip: true

    required property PdfDocument document
    required property var resource

    property string selectedText
    property bool noteMode: false

    // Bu sayfaya ait kalici highlight'lar (page/startIndex/length dolu olanlar).
    function pageHighlights(page) {
        if (!root.resource || !root.resource.highlights) return []
        return root.resource.highlights.filter(function(h) {
            return h.page === page && h.startIndex >= 0 && h.length > 0 && h.boundsPolygons
        })
    }

    // Bridge'den gelen duz [[ [x,y], [x,y], ... ], ...] veriyi PathMultiline.paths
    // icin QPolygonF listesine (Qt.point dizileri) cevirir.
    function polygonsFromPoints(boundsPolygons) {
        if (!boundsPolygons) return []
        return boundsPolygons.map(function(poly) {
            return poly.map(function(pt) { return Qt.point(pt[0], pt[1]) })
        })
    }

    // Highlight renginin akademik anlami (bridge.highlightLabels: renk -> etiket).
    function labelForColor(color) {
        const wanted = String(color).toUpperCase()
        for (const entry of bridge.highlightLabels) {
            if (String(entry.color).toUpperCase() === wanted)
                return entry.label
        }
        return "Genel"
    }

    // Bu sayfaya ait PDF notlari.
    function pageNotes(page) {
        if (!root.resource || !root.resource.pdfNotes) return []
        return root.resource.pdfNotes.filter(function(n) { return n.page === page })
    }

    property alias currentPage: pageNavigator.currentPage
    property alias backEnabled: pageNavigator.backAvailable
    property alias forwardEnabled: pageNavigator.forwardAvailable

    function back() { pageNavigator.back() }
    function forward() { pageNavigator.forward() }

    function goToPage(page) {
        if (page === pageNavigator.currentPage)
            return
        goToLocation(page, Qt.point(-1, -1), 0)
    }

    function goToLocation(page, location, zoom) {
        if (tableView.rows === 0) {
            tableView.pendingRow = page
            tableView.pendingLocation = location
            tableView.pendingZoom = zoom
            return
        }
        if (zoom > 0) {
            pageNavigator.jumping = true
            root.renderScale = zoom
            pageNavigator.jumping = false
        }
        pageNavigator.jump(page, location, zoom)
    }

    property int currentPageRenderingStatus: Image.Null

    property real renderScale: 1
    property real pageRotation: 0

    function resetScale() { root.renderScale = 1 }

    function zoomIn() { root.renderScale = Math.min(tableView.maxScale, root.renderScale * 1.2) }
    function zoomOut() { root.renderScale = Math.max(tableView.minScale, root.renderScale / 1.2) }

    // Gorunumun ortasindaki sayfayi navigator'a bildirir (sayfa sayaci icin). Fare tekerlegi /
    // dokunmatik kaydirmada ScrollBar aktiflesmeyebildigi icin contentY degisiminden de cagrilir.
    function syncCurrentPage() {
        const cell = tableView.cellAtPos(root.width / 2, root.height / 2)
        if (cell.y < 0)
            return
        const currentItem = tableView.itemAtCell(cell)
        const currentLocation = currentItem
                              ? Qt.point((tableView.contentX - currentItem.x + tableView.jumpLocationMargin.x) / root.renderScale,
                                         (tableView.contentY - currentItem.y + tableView.jumpLocationMargin.y) / root.renderScale)
                              : Qt.point(0, 0)
        pageNavigator.update(cell.y, currentLocation, root.renderScale)
    }

    Timer {
        id: pageSyncTimer
        interval: 120
        onTriggered: root.syncCurrentPage()
    }

    function scaleToWidth(width, height) {
        root.renderScale = width / (tableView.rot90 ? tableView.firstPagePointSize.height : tableView.firstPagePointSize.width)
    }

    property alias searchModel: searchModel
    property alias searchString: searchModel.searchString
    function searchBack() { --searchModel.currentResult }
    function searchForward() { ++searchModel.currentResult }


    PdfStyle {
        id: style
        selectionColor: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35)
        pageSearchResultsColor: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35)
        currentSearchResultStrokeColor: Theme.accent
        currentSearchResultStrokeWidth: 2
    }

    TableView {
        id: tableView
        property real minScale: 0.1
        property real maxScale: 10
        property point jumpLocationMargin: Qt.point(10, 10)
        anchors.fill: parent
        anchors.leftMargin: 2
        model: root.document ? root.document.pageCount : 0
        rowSpacing: 8
        property real rotationNorm: Math.round((360 + (root.pageRotation % 360)) % 360)
        property bool rot90: rotationNorm == 90 || rotationNorm == 270
        onRot90Changed: forceLayout()
        onContentYChanged: if (!pageNavigator.jumping) pageSyncTimer.restart()
        onHeightChanged: forceLayout()
        onWidthChanged: forceLayout()
        property size firstPagePointSize: root.document?.status === PdfDocument.Ready ? root.document.pagePointSize(0) : Qt.size(1, 1)
        property real pageHolderWidth: Math.max(root.width, ((rot90 ? root.document?.maxPageHeight : root.document?.maxPageWidth) ?? 0) * root.renderScale)
        columnWidthProvider: function(col) { return root.document ? pageHolderWidth + vscroll.width + 2 : 0 }
        rowHeightProvider: function(row) { return (rot90 ? root.document.pagePointSize(row).width : root.document.pagePointSize(row).height) * root.renderScale }

        property int pendingRow: -1
        property point pendingLocation
        property real pendingZoom: -1

        // Ctrl+tekerlek: yakinlastir/uzaklastir. Ctrl basili degilken bu
        // handler hicbir sey yapmaz, olay normal sekilde TableView'in
        // kendi kaydirmasina gecer.
        WheelHandler {
            target: null
            acceptedModifiers: Qt.ControlModifier
            onWheel: (event) => {
                if (event.angleDelta.y > 0)
                    root.zoomIn()
                else if (event.angleDelta.y < 0)
                    root.zoomOut()
            }
        }

        onRowsChanged: {
            if (rows > 0 && tableView.pendingRow >= 0) {
                root.goToLocation(tableView.pendingRow, tableView.pendingLocation, tableView.pendingZoom)
                tableView.pendingRow = -1
                tableView.pendingLocation = Qt.point(-1, -1)
                tableView.pendingZoom = -1
            }
        }

        delegate: Rectangle {
            id: pageHolder
            required property int index
            color: "transparent"
            property alias selection: selection

            Rectangle {
                id: paper
                width: image.width
                height: image.height
                rotation: root.pageRotation
                anchors.centerIn: pinch.active ? undefined : parent
                property size pagePointSize: root.document.pagePointSize(pageHolder.index)
                property real pageScale: image.paintedWidth / pagePointSize.width
                // PDF sayfasi fiziksel olarak her zaman beyaz kagit -- uygulama
                // koyu temasindan bagimsiz olmali (Theme.bgSurface koyu temada
                // sayfanin etrafinda/altinda koyu sizinti yapiyordu).
                color: "white"

                PdfPageImage {
                    id: image
                    document: root.document
                    currentFrame: pageHolder.index
                    asynchronous: true
                    fillMode: Image.PreserveAspectFit
                    width: paper.pagePointSize.width * root.renderScale
                    height: paper.pagePointSize.height * root.renderScale
                    property real renderScale: root.renderScale
                    onRenderScaleChanged: {
                        image.sourceSize.width = paper.pagePointSize.width * renderScale * Screen.devicePixelRatio
                        image.sourceSize.height = 0
                        paper.scale = 1
                        searchHighlights.update()
                    }
                    onStatusChanged: {
                        if (pageHolder.index === pageNavigator.currentPage)
                            root.currentPageRenderingStatus = status
                    }
                }

                // Kalici highlight'lar: her biri kendi Shape'i. Onceden Instantiator + Shape.data.push(object)
                // kullaniliyordu; nesneler Shape'e devredildikten sonra Instantiator tarafindan yikilinca
                // sarkan isaretci kaliyor, currentReaderResourceChanged sirasinda native cokme (segfault)
                // olusuyordu (fare simulasyonuyla yeniden uretildi).
                Repeater {
                    model: root.pageHighlights(pageHolder.index)
                    delegate: Shape {
                        id: highlightShape
                        required property var modelData
                        readonly property color baseColor: modelData.color
                        anchors.fill: parent
                        visible: image.status === Image.Ready

                        ShapePath {
                            strokeWidth: -1
                            // Fosforlu kalem efekti icin yari saydam -- opak renk altindaki metni kapatiyordu.
                            fillColor: Qt.rgba(highlightShape.baseColor.r, highlightShape.baseColor.g,
                                               highlightShape.baseColor.b, 0.35)
                            scale: Qt.size(paper.pageScale, paper.pageScale)
                            PathMultiline {
                                paths: root.polygonsFromPoints(highlightShape.modelData.boundsPolygons)
                            }
                        }
                    }
                }

                Shape {
                    id: persistedHighlightsShape
                    anchors.fill: parent
                    visible: image.status === Image.Ready
                    onVisibleChanged: searchHighlights.update()
                    ShapePath {
                        strokeWidth: -1
                        fillColor: style.pageSearchResultsColor
                        scale: Qt.size(paper.pageScale, paper.pageScale)
                        PathMultiline {
                            id: searchHighlights
                            function update() {
                                paths = searchModel.boundingPolygonsOnPage(pageHolder.index)
                            }
                        }
                    }
                    Connections {
                        target: searchModel
                        function onCurrentPageBoundingPolygonsChanged() { searchHighlights.update() }
                    }
                    ShapePath {
                        strokeWidth: -1
                        fillColor: style.selectionColor
                        scale: Qt.size(paper.pageScale, paper.pageScale)
                        PathMultiline {
                            paths: selection.geometry
                        }
                    }
                }

                Shape {
                    anchors.fill: parent
                    visible: image.status === Image.Ready && searchModel.currentPage === pageHolder.index
                    ShapePath {
                        strokeWidth: style.currentSearchResultStrokeWidth
                        strokeColor: style.currentSearchResultStrokeColor
                        fillColor: "transparent"
                        scale: Qt.size(paper.pageScale, paper.pageScale)
                        PathMultiline {
                            paths: searchModel.currentResultBoundingPolygons
                        }
                    }
                }

                PinchHandler {
                    id: pinch
                    minimumScale: tableView.minScale / root.renderScale
                    maximumScale: Math.max(1, tableView.maxScale / root.renderScale)
                    minimumRotation: root.pageRotation
                    maximumRotation: root.pageRotation
                    onActiveChanged:
                        if (active) {
                            paper.z = 10
                        } else {
                            paper.z = 0
                            const centroidInPoints = Qt.point(pinch.centroid.position.x / root.renderScale,
                                                            pinch.centroid.position.y / root.renderScale)
                            const centroidInFlickable = tableView.mapFromItem(paper, pinch.centroid.position.x, pinch.centroid.position.y)
                            const newSourceWidth = image.sourceSize.width * paper.scale
                            const ratio = newSourceWidth / image.sourceSize.width
                            if (ratio > 1.1 || ratio < 0.9) {
                                const centroidOnPage = Qt.point(centroidInPoints.x * root.renderScale * ratio, centroidInPoints.y * root.renderScale * ratio)
                                paper.scale = 1
                                pinch.persistentScale = 1
                                paper.x = 0
                                paper.y = 0
                                root.renderScale *= ratio
                                tableView.forceLayout()
                                if (tableView.rotationNorm == 0) {
                                    tableView.contentX = pageHolder.x + tableView.originX + centroidOnPage.x - centroidInFlickable.x
                                    tableView.contentY = pageHolder.y + tableView.originY + centroidOnPage.y - centroidInFlickable.y
                                } else if (tableView.rotationNorm == 90) {
                                    tableView.contentX = pageHolder.x + tableView.originX + image.height - centroidOnPage.y - centroidInFlickable.x
                                    tableView.contentY = pageHolder.y + tableView.originY + centroidOnPage.x - centroidInFlickable.y
                                } else if (tableView.rotationNorm == 180) {
                                    tableView.contentX = pageHolder.x + tableView.originX + image.width - centroidOnPage.x - centroidInFlickable.x
                                    tableView.contentY = pageHolder.y + tableView.originY + image.height - centroidOnPage.y - centroidInFlickable.y
                                } else if (tableView.rotationNorm == 270) {
                                    tableView.contentX = pageHolder.x + tableView.originX + centroidOnPage.y - centroidInFlickable.x
                                    tableView.contentY = pageHolder.y + tableView.originY + image.width - centroidOnPage.x - centroidInFlickable.y
                                }
                                tableView.returnToBounds()
                            }
                        }
                    grabPermissions: PointerHandler.CanTakeOverFromAnything
                }

                DragHandler {
                    id: textSelectionDrag
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
                    target: null
                }
                TapHandler {
                    id: mouseClickHandler
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
                    onTapped: {
                        if (!root.noteMode) {
                            if (selection.hold && selection.text.trim().length > 0) {
                                selection.clear()
                            }
                            return
                        }
                        const pos = mouseClickHandler.point.position
                        newNotePopover.pendingPage = pageHolder.index
                        newNotePopover.pendingX = pos.x / paper.pageScale
                        newNotePopover.pendingY = pos.y / paper.pageScale
                        newNotePopover.x = Math.max(0, Math.min(pos.x, paper.width - newNotePopover.width))
                        newNotePopover.y = Math.max(0, Math.min(pos.y, paper.height - newNotePopover.height))
                        newNotePopover.noteText = ""
                        newNotePopover.visible = true
                    }
                }
                TapHandler {
                    id: touchTapHandler
                    acceptedDevices: PointerDevice.TouchScreen
                    onTapped: {
                        selection.clear()
                        selection.forceActiveFocus()
                    }
                }

                Repeater {
                    model: PdfLinkModel {
                        id: linkModel
                        document: root.document
                        page: image.currentFrame
                    }
                    delegate: PdfLinkDelegate {
                        x: rectangle.x * paper.pageScale
                        y: rectangle.y * paper.pageScale
                        width: rectangle.width * paper.pageScale
                        height: rectangle.height * paper.pageScale
                        visible: image.status === Image.Ready
                        onTapped:
                            (link) => {
                                if (link.page >= 0)
                                    root.goToLocation(link.page, link.location, link.zoom)
                                else
                                    Qt.openUrlExternally(url)
                            }
                    }
                }

                PdfSelection {
                    id: selection
                    anchors.fill: parent
                    document: root.document
                    page: image.currentFrame
                    renderScale: image.renderScale
                    from: textSelectionDrag.centroid.pressPosition
                    to: textSelectionDrag.centroid.position
                    hold: !textSelectionDrag.active && !mouseClickHandler.pressed
                    onTextChanged: root.selectedText = text
                    focus: true
                }

                // Yeni secim -> renkli highlight kaydetme (Kindle tarzi yuzen toolbar)
                // Secimin hemen ustunde/altinda konumlanir (sayfa altina sabit degil),
                // sayfa sinirlari disina tasmayacak sekilde kenarlara yaslanir.
                Rectangle {
                    id: newHighlightToolbar
                    objectName: "newHighlightToolbar"
                    visible: selection.hold && selection.text.trim().length > 0
                    z: 20
                    implicitWidth: newHighlightRow.implicitWidth + 16
                    implicitHeight: 36
                    radius: Theme.radiusPill
                    color: Theme.popoverBg
                    border.width: 1
                    border.color: Theme.borderStrong

                    // Secim, araç çubuğundaki bir düğmeye tıklanırken (fare imleci
                    // metnin üzerinden geçerken) DragHandler'ın kendisini bozup
                    // selection.from/to'yu sıfırlamasına karşı: toolbar görünür
                    // olduğu anda değerler burada dondurulur, düğmeler canlı
                    // selection.* yerine bu sabit kopyaları kullanır (bkz.
                    // "highlight çalışmıyor" hatası).
                    property point capturedFrom: Qt.point(0, 0)
                    property point capturedTo: Qt.point(0, 0)
                    property string capturedText: ""
                    onVisibleChanged: {
                        if (visible) {
                            capturedFrom = selection.from
                            capturedTo = selection.to
                            capturedText = selection.text
                        }
                    }

                    // QPdfDocument.getSelection() PDF *nokta* (pt) uzayinda calisir; PdfSelection.from/to ise
                    // ekrandaki piksel. Zoom %100 degilken piksel gonderilirse rastgele yer secilirdi.
                    readonly property real safeScale: paper.pageScale > 0 ? paper.pageScale : 1
                    readonly property point pointFrom: Qt.point(capturedFrom.x / safeScale, capturedFrom.y / safeScale)
                    readonly property point pointTo: Qt.point(capturedTo.x / safeScale, capturedTo.y / safeScale)

                    property real selectionCenterX: (capturedFrom.x + capturedTo.x) / 2
                    property real selectionTopY: Math.min(capturedFrom.y, capturedTo.y)
                    property real selectionBottomY: Math.max(capturedFrom.y, capturedTo.y)
                    property bool fitsAbove: selectionTopY - height - 10 >= 0

                    x: Math.max(0, Math.min(selectionCenterX - width / 2, parent.width - width))
                    y: {
                        if (fitsAbove) return selectionTopY - height - 10
                        return Math.min(selectionBottomY + 10, parent.height - height)
                    }

                    Row {
                        id: newHighlightRow
                        anchors.centerIn: parent
                        spacing: 8

                        Repeater {
                            model: Theme.highlightPalette
                            delegate: Rectangle {
                                required property string modelData
                                width: 22
                                height: 22
                                radius: 11
                                color: modelData
                                border.width: 1
                                border.color: Theme.swatchBorderLight

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    ToolTip.visible: containsMouse
                                    ToolTip.text: root.labelForColor(parent.modelData)
                                    onClicked: {
                                        if (newHighlightToolbar.capturedText.trim().length > 0 && root.resource) {
                                            bridge.addPdfHighlight(
                                                root.resource.id, root.resource.pdfFileUrl, pageHolder.index,
                                                newHighlightToolbar.pointFrom.x, newHighlightToolbar.pointFrom.y,
                                                newHighlightToolbar.pointTo.x, newHighlightToolbar.pointTo.y,
                                                parent.modelData
                                            )
                                        }
                                        selection.clear()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: 1
                            height: 18
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.borderSubtle
                        }

                        AppIconButton {
                            anchors.verticalCenter: parent.verticalCenter
                            iconName: "fa5s.language"
                            iconSize: 13
                            tooltip: "Kelime Havuzuna Ekle"
                            onClicked: {
                                newVocabPopover.word = newHighlightToolbar.capturedText.trim()
                                newVocabPopover.translationText = ""
                                newVocabPopover.visible = true
                            }
                        }
                    }
                }

                // Secili kelimeyi/ifadeyi Bilgi Havuzu'na (kelime listesi) ekleme
                // popover'i -- HTML okuyucudaki "Kelime Havuzuna Ekle" ozelligiyle
                // ayni: bridge.addVocabulary(resourceId, word, translation).
                Rectangle {
                    id: newVocabPopover
                    property string word: ""
                    property string translationText: ""
                    visible: false
                    z: 21
                    x: Math.max(0, Math.min(newHighlightToolbar.x, paper.width - width))
                    y: Math.max(0, Math.min(newHighlightToolbar.y + newHighlightToolbar.height + 8, paper.height - height))
                    width: 260
                    implicitHeight: vocabCol.implicitHeight + 20
                    radius: Theme.radiusMd
                    color: Theme.popoverBg
                    border.width: 1
                    border.color: Theme.borderStrong

                    Column {
                        id: vocabCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Text {
                            width: parent.width
                            text: "Kelime: " + newVocabPopover.word
                            elide: Text.ElideRight
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }

                        Rectangle {
                            width: parent.width
                            height: 32
                            radius: Theme.radiusSm
                            color: Theme.bgSurface
                            border.width: 1
                            border.color: Theme.borderSubtle

                            TextInput {
                                id: vocabTranslationInput
                                anchors.fill: parent
                                anchors.margins: 8
                                verticalAlignment: TextInput.AlignVCenter
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                text: newVocabPopover.translationText
                                onTextChanged: newVocabPopover.translationText = text

                                Text {
                                    anchors.fill: parent
                                    verticalAlignment: Text.AlignVCenter
                                    text: "Türkçe anlamını girin..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textMuted
                                    visible: !vocabTranslationInput.text
                                }
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            spacing: 8

                            AppButton {
                                text: "Vazgeç"
                                variant: "ghost"
                                implicitHeight: 28
                                onClicked: {
                                    newVocabPopover.visible = false
                                    selection.clear()
                                }
                            }

                            AppButton {
                                text: "Kaydet"
                                variant: "primary"
                                implicitHeight: 28
                                enabledState: vocabTranslationInput.text.trim().length > 0
                                onClicked: {
                                    if (root.resource) {
                                        // Secim noktalariyla gonderilir: gectigi cumle baglam olarak da kaydedilir.
                                        bridge.addPdfVocabulary(
                                            root.resource.id, root.resource.pdfFileUrl, pageHolder.index,
                                            newHighlightToolbar.pointFrom.x, newHighlightToolbar.pointFrom.y,
                                            newHighlightToolbar.pointTo.x, newHighlightToolbar.pointTo.y,
                                            vocabTranslationInput.text.trim()
                                        )
                                    }
                                    newVocabPopover.visible = false
                                    selection.clear()
                                }
                            }
                        }
                    }
                }

                // Kalici highlight'lara tiklama -> renk degistir / sil popover'i
                // TapHandler kullanilir (MouseArea degil) -- MouseArea, ustune
                // geldigi metinde yeni bir surukle-secim baslatilmasini engelleyip
                // "highlight bir kere calisiyor, ikincisi calismiyor" hatasina
                // yol aciyordu (MouseArea eski girdi sistemi, DragHandler ile
                // ayni alanda oncelik/grab catismasi yaratabiliyor).
                Repeater {
                    model: root.pageHighlights(pageHolder.index)
                    delegate: Item {
                        id: highlightHitArea
                        required property var modelData
                        x: modelData.boundingRect ? modelData.boundingRect[0] * paper.pageScale : 0
                        y: modelData.boundingRect ? modelData.boundingRect[1] * paper.pageScale : 0
                        width: modelData.boundingRect ? modelData.boundingRect[2] * paper.pageScale : 0
                        height: modelData.boundingRect ? modelData.boundingRect[3] * paper.pageScale : 0

                        HoverHandler {
                            cursorShape: Qt.PointingHandCursor
                        }

                        // Yorumu olan alintilarin kose isareti
                        Rectangle {
                            visible: highlightHitArea.modelData.comment !== ""
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.topMargin: -6
                            width: 14
                            height: 14
                            radius: 7
                            color: Theme.accent
                            AppIcon {
                                anchors.centerIn: parent
                                name: "fa5s.comment-dots"
                                size: 8
                                color: Theme.textOnAccent
                            }
                        }

                        TapHandler {
                            acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus | PointerDevice.TouchScreen
                            onTapped: {
                                editHighlightPopover.highlightId = highlightHitArea.modelData.id
                                editHighlightPopover.label = highlightHitArea.modelData.label
                                editCommentInput.text = highlightHitArea.modelData.comment
                                editHighlightPopover.x = Math.max(0, Math.min(
                                    highlightHitArea.x, paper.width - editHighlightPopover.width))
                                editHighlightPopover.y = Math.max(0, Math.min(
                                    highlightHitArea.y + highlightHitArea.height + 4,
                                    paper.height - editHighlightPopover.implicitHeight))
                                editHighlightPopover.visible = true
                            }
                        }
                    }
                }

                // Var olan highlight duzenleme popover'i (renk/anlam, yorum, sil)
                Rectangle {
                    id: editHighlightPopover
                    property int highlightId: -1
                    property string label: ""
                    visible: false
                    z: 30
                    width: 264
                    implicitHeight: editHighlightCol.implicitHeight + 20
                    height: implicitHeight
                    radius: Theme.radiusMd
                    color: Theme.popoverBg
                    border.width: 1
                    border.color: Theme.borderStrong

                    Column {
                        id: editHighlightCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Row {
                            id: editHighlightRow
                            spacing: 8

                            Repeater {
                                model: Theme.highlightPalette
                                delegate: Rectangle {
                                    required property string modelData
                                    width: 22
                                    height: 22
                                    radius: 11
                                    color: modelData
                                    border.width: 1
                                    border.color: Theme.swatchBorderLight

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        ToolTip.visible: containsMouse
                                        ToolTip.text: root.labelForColor(parent.modelData)
                                        onClicked: {
                                            bridge.updateHighlightColor(editHighlightPopover.highlightId, parent.modelData)
                                            editHighlightPopover.visible = false
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: 26
                                height: 26
                                radius: 13
                                color: Theme.dangerSubtle
                                AppIcon {
                                    anchors.centerIn: parent
                                    name: "fa5s.trash"
                                    size: 11
                                    color: Theme.dangerText
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        bridge.deleteHighlight(editHighlightPopover.highlightId)
                                        editHighlightPopover.visible = false
                                    }
                                }
                            }
                        }

                        Text {
                            text: editHighlightPopover.label
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            color: Theme.textSecondary
                        }

                        Rectangle {
                            width: parent.width
                            height: 54
                            radius: Theme.radiusXs
                            color: Theme.bgSurface
                            border.width: 1
                            border.color: editCommentInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                            TextInput {
                                id: editCommentInput
                                anchors.fill: parent
                                anchors.margins: 6
                                wrapMode: TextInput.Wrap
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm

                                Text {
                                    anchors.fill: parent
                                    text: "Yorum ekle..."
                                    font: editCommentInput.font
                                    color: Theme.textMuted
                                    visible: !editCommentInput.text && !editCommentInput.activeFocus
                                }
                            }
                        }

                        Item {
                            width: parent.width
                            height: saveCommentButton.height

                            AppButton {
                                id: saveCommentButton
                                anchors.right: parent.right
                                text: "Yorumu Kaydet"
                                variant: "primary"
                                implicitHeight: 28
                                onClicked: {
                                    bridge.updateHighlightComment(editHighlightPopover.highlightId, editCommentInput.text)
                                    editHighlightPopover.visible = false
                                }
                            }
                        }
                    }
                }

                // Kalici notlar -- sayfadaki ufak ikon, tiklaninca duzenleme popover'i
                Repeater {
                    model: root.pageNotes(pageHolder.index)
                    delegate: Rectangle {
                        required property var modelData
                        x: modelData.x * paper.pageScale - 10
                        y: modelData.y * paper.pageScale - 10
                        width: 20
                        height: 20
                        radius: 10
                        color: Theme.accent
                        border.width: 1
                        border.color: Theme.markerBorderLight
                        z: 15

                        AppIcon {
                            anchors.centerIn: parent
                            name: "fa5s.comment-alt"
                            size: 10
                            color: Theme.textOnAccent
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                editNotePopover.noteId = modelData.id
                                editNotePopover.noteText = modelData.text
                                editNotePopover.x = Math.max(0, Math.min(
                                    parent.x, paper.width - editNotePopover.width))
                                editNotePopover.y = Math.max(0, Math.min(
                                    parent.y + parent.height + 4, paper.height - editNotePopover.height))
                                editNotePopover.visible = true
                            }
                        }
                    }
                }

                // Yeni not olusturma popover'i (Not Ekle modunda sayfaya tiklaninca)
                Rectangle {
                    id: newNotePopover
                    property int pendingPage: 0
                    property real pendingX: 0
                    property real pendingY: 0
                    property alias noteText: newNoteInput.text
                    visible: false
                    z: 30
                    width: 220
                    height: 96
                    radius: Theme.radiusSm
                    color: Theme.popoverBg
                    border.width: 1
                    border.color: Theme.borderStrong

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        Rectangle {
                            width: parent.width
                            height: 50
                            radius: Theme.radiusXs
                            color: Theme.bgSurface
                            border.width: 1
                            border.color: Theme.borderSubtle

                            TextInput {
                                id: newNoteInput
                                anchors.fill: parent
                                anchors.margins: 6
                                wrapMode: TextInput.Wrap
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            spacing: 6

                            AppButton {
                                text: "İptal"
                                variant: "ghost"
                                onClicked: newNotePopover.visible = false
                            }
                            AppButton {
                                text: "Kaydet"
                                variant: "primary"
                                onClicked: {
                                    if (newNoteInput.text.trim().length > 0 && root.resource) {
                                        bridge.addPdfNote(root.resource.id, newNotePopover.pendingPage,
                                                           newNotePopover.pendingX, newNotePopover.pendingY,
                                                           newNoteInput.text.trim())
                                    }
                                    newNotePopover.visible = false
                                }
                            }
                        }
                    }
                }

                // Var olan not duzenleme popover'i
                Rectangle {
                    id: editNotePopover
                    property int noteId: -1
                    property alias noteText: editNoteInput.text
                    visible: false
                    z: 30
                    width: 220
                    height: 96
                    radius: Theme.radiusSm
                    color: Theme.popoverBg
                    border.width: 1
                    border.color: Theme.borderStrong

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        Rectangle {
                            width: parent.width
                            height: 50
                            radius: Theme.radiusXs
                            color: Theme.bgSurface
                            border.width: 1
                            border.color: Theme.borderSubtle

                            TextInput {
                                id: editNoteInput
                                anchors.fill: parent
                                anchors.margins: 6
                                wrapMode: TextInput.Wrap
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            spacing: 6

                            Rectangle {
                                width: 26
                                height: 26
                                radius: 13
                                color: Theme.dangerSubtle
                                AppIcon {
                                    anchors.centerIn: parent
                                    name: "fa5s.trash"
                                    size: 11
                                    color: Theme.dangerText
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        bridge.deletePdfNote(editNotePopover.noteId)
                                        editNotePopover.visible = false
                                    }
                                }
                            }
                            AppButton {
                                text: "Kaydet"
                                variant: "primary"
                                onClicked: {
                                    if (editNoteInput.text.trim().length > 0) {
                                        bridge.updatePdfNote(editNotePopover.noteId, editNoteInput.text.trim())
                                    }
                                    editNotePopover.visible = false
                                }
                            }
                        }
                    }
                }

                TapHandler {
                    id: dismissPopoverHandler
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
                    onTapped: {
                        editHighlightPopover.visible = false
                        editNotePopover.visible = false
                        newVocabPopover.visible = false
                    }
                    enabled: editHighlightPopover.visible || editNotePopover.visible || newVocabPopover.visible
                }
            }
        }
        ScrollBar.vertical: ScrollBar {
            id: vscroll
            onPressedChanged: if (pressed) {
                const cell = tableView.cellAtPos(root.width / 2, root.height / 2)
                const currentItem = tableView.itemAtCell(cell)
                const currentLocation = currentItem
                                      ? Qt.point((tableView.contentX - currentItem.x + tableView.jumpLocationMargin.x) / root.renderScale,
                                                 (tableView.contentY - currentItem.y + tableView.jumpLocationMargin.y) / root.renderScale)
                                      : Qt.point(0, 0)
                pageNavigator.jump(cell.y, currentLocation, root.renderScale)
            }
            onActiveChanged: if (!active) root.syncCurrentPage()
        }
        ScrollBar.horizontal: ScrollBar { }
    }

    onRenderScaleChanged: {
        if (pageNavigator.jumping)
            return
        tableView.forceLayout()
        const cell = tableView.cellAtPos(root.width / 2, root.height / 2)
        const currentItem = tableView.itemAtCell(cell)
        if (currentItem) {
            const currentLocation = Qt.point((tableView.contentX - currentItem.x + tableView.jumpLocationMargin.x) / root.renderScale,
                                             (tableView.contentY - currentItem.y + tableView.jumpLocationMargin.y) / root.renderScale)
            pageNavigator.update(cell.y, currentLocation, renderScale)
        }
    }

    PdfPageNavigator {
        id: pageNavigator
        property bool jumping: false
        property int previousPage: 0
        onJumped: function(current) {
            jumping = true
            if (current.zoom > 0)
                root.renderScale = current.zoom
            const pageSize = root.document.pagePointSize(current.page)
            if (current.location.y < 0) {
                const previousPageDelegate = tableView.itemAtCell(0, previousPage)
                const currentYOffset = previousPageDelegate
                                     ? tableView.contentY - previousPageDelegate.y
                                     : 0
                tableView.positionViewAtRow(current.page, Qt.AlignTop, currentYOffset)
            } else if (current.rectangles.length > 0) {
                pageSize.width *= root.renderScale
                pageSize.height *= root.renderScale
                const rectPts = current.rectangles[0]
                const rectPx = Qt.rect(rectPts.x * root.renderScale - tableView.jumpLocationMargin.x,
                                       rectPts.y * root.renderScale - tableView.jumpLocationMargin.y,
                                       rectPts.width * root.renderScale + tableView.jumpLocationMargin.x * 2,
                                       rectPts.height * root.renderScale + tableView.jumpLocationMargin.y * 2)
                tableView.positionViewAtCell(0, current.page, TableView.Contain, Qt.point(0, 0), rectPx)
            } else {
                pageSize.width *= root.renderScale
                pageSize.height *= root.renderScale
                const rectPx = Qt.rect(current.location.x * root.renderScale - tableView.jumpLocationMargin.x,
                                       current.location.y * root.renderScale - tableView.jumpLocationMargin.y,
                                       tableView.jumpLocationMargin.x * 2, tableView.jumpLocationMargin.y * 2)
                tableView.positionViewAtCell(0, current.page, TableView.AlignLeft | TableView.AlignTop, Qt.point(0, 0), rectPx)
            }
            jumping = false
            previousPage = current.page
        }

        property url documentSource: root.document.source
        onDocumentSourceChanged: {
            pageNavigator.clear()
            root.resetScale()
            tableView.contentX = 0
            tableView.contentY = 0
        }
    }

    PdfSearchModel {
        id: searchModel
        document: root.document === undefined ? null : root.document
        onCurrentResultChanged: pageNavigator.jump(currentResultLink)
    }
}
