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
        onHeightChanged: forceLayout()
        onWidthChanged: forceLayout()
        property size firstPagePointSize: root.document?.status === PdfDocument.Ready ? root.document.pagePointSize(0) : Qt.size(1, 1)
        property real pageHolderWidth: Math.max(root.width, ((rot90 ? root.document?.maxPageHeight : root.document?.maxPageWidth) ?? 0) * root.renderScale)
        columnWidthProvider: function(col) { return root.document ? pageHolderWidth + vscroll.width + 2 : 0 }
        rowHeightProvider: function(row) { return (rot90 ? root.document.pagePointSize(row).width : root.document.pagePointSize(row).height) * root.renderScale }

        property int pendingRow: -1
        property point pendingLocation
        property real pendingZoom: -1
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
                color: Theme.bgSurface

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
                    Instantiator {
                        model: root.pageHighlights(pageHolder.index)
                        delegate: ShapePath {
                            id: highlightShapePath
                            required property var modelData
                            property color baseColor: modelData.color
                            strokeWidth: -1
                            // Fosforlu kalem efekti icin yari saydam -- opak renk
                            // altindaki metni tamamen kapatiyordu (kullanicidan gelen bulgu).
                            fillColor: Qt.rgba(baseColor.r, baseColor.g, baseColor.b, 0.35)
                            scale: Qt.size(paper.pageScale, paper.pageScale)
                            PathMultiline {
                                paths: root.polygonsFromPoints(highlightShapePath.modelData.boundsPolygons)
                            }
                        }
                        onObjectAdded: (index, object) => persistedHighlightsShape.data.push(object)
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
                        if (!root.noteMode) return
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
                Rectangle {
                    id: newHighlightToolbar
                    visible: selection.hold && selection.text.trim().length > 0
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 16
                    z: 20
                    implicitWidth: newHighlightRow.implicitWidth + 16
                    implicitHeight: 36
                    radius: Theme.radiusPill
                    color: Theme.isDark ? "#1A1E2F" : "#FFFFFF"
                    border.width: 1
                    border.color: Theme.borderStrong

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
                                border.color: "#FFFFFF44"

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (selection.text.trim().length > 0 && root.resource) {
                                            bridge.addPdfHighlight(
                                                root.resource.id, root.resource.url, pageHolder.index,
                                                selection.from.x, selection.from.y,
                                                selection.to.x, selection.to.y,
                                                parent.modelData
                                            )
                                        }
                                        selection.clear()
                                    }
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
                        TapHandler {
                            acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus | PointerDevice.TouchScreen
                            onTapped: {
                                editHighlightPopover.highlightId = highlightHitArea.modelData.id
                                editHighlightPopover.x = Math.max(0, Math.min(
                                    highlightHitArea.x, paper.width - editHighlightPopover.implicitWidth))
                                editHighlightPopover.y = Math.max(0, Math.min(
                                    highlightHitArea.y + highlightHitArea.height + 4,
                                    paper.height - editHighlightPopover.implicitHeight))
                                editHighlightPopover.visible = true
                            }
                        }
                    }
                }

                // Var olan highlight duzenleme popover'i (renk degistir / sil)
                Rectangle {
                    id: editHighlightPopover
                    property int highlightId: -1
                    visible: false
                    z: 30
                    implicitWidth: editHighlightRow.implicitWidth + 16
                    implicitHeight: 36
                    radius: Theme.radiusPill
                    color: Theme.isDark ? "#1A1E2F" : "#FFFFFF"
                    border.width: 1
                    border.color: Theme.borderStrong

                    Row {
                        id: editHighlightRow
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
                                border.color: "#FFFFFF44"

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        bridge.updateHighlightColor(editHighlightPopover.highlightId, parent.modelData)
                                        editHighlightPopover.visible = false
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: 1
                            height: 18
                            color: Theme.borderSubtle
                            anchors.verticalCenter: parent.verticalCenter
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
                        border.color: "#FFFFFF66"
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
                    color: Theme.isDark ? "#1A1E2F" : "#FFFFFF"
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
                    color: Theme.isDark ? "#1A1E2F" : "#FFFFFF"
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
                    }
                    enabled: editHighlightPopover.visible || editNotePopover.visible
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
            onActiveChanged: if (!active) {
                const cell = tableView.cellAtPos(root.width / 2, root.height / 2)
                const currentItem = tableView.itemAtCell(cell)
                const currentLocation = currentItem
                                      ? Qt.point((tableView.contentX - currentItem.x + tableView.jumpLocationMargin.x) / root.renderScale,
                                                 (tableView.contentY - currentItem.y + tableView.jumpLocationMargin.y) / root.renderScale)
                                      : Qt.point(0, 0)
                pageNavigator.update(cell.y, currentLocation, root.renderScale)
            }
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
