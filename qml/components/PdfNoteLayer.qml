import QtQuick
import QtQuick.Controls
import "../theme"

// Sayfadaki kalıcı not işaretleri, yeni not (Not Ekle modu) ve not düzenleme popover'ları.
// Sayfa (`paper`) üzerine bindirilir; yeni not `beginNewNote(position)` ile başlatılır.
Item {
    id: root

    property Item paper            // Sayfa kâğıdı (pageScale, width, height)
    property int pageIndex: 0
    property var resource

    readonly property var pageNotes: (!resource || !resource.pdfNotes) ? [] : resource.pdfNotes.filter(function(n) {
        return n.page === pageIndex
    })

    readonly property bool popoverVisible: newNotePopover.visible || editNotePopover.visible
    function closeAll() {
        newNotePopover.visible = false
        editNotePopover.visible = false
    }

    // Sayfaya tıklanan noktada (piksel) yeni not popover'ını açar; nokta page-point uzayında saklanır.
    function beginNewNote(pos) {
        newNotePopover.pendingPage = root.pageIndex
        newNotePopover.pendingX = pos.x / root.paper.pageScale
        newNotePopover.pendingY = pos.y / root.paper.pageScale
        newNotePopover.x = Math.max(0, Math.min(pos.x, root.paper.width - newNotePopover.width))
        newNotePopover.y = Math.max(0, Math.min(pos.y, root.paper.height - newNotePopover.height))
        newNotePopover.noteText = ""
        newNotePopover.visible = true
    }

    anchors.fill: parent
    z: 30

    // Kalici notlar -- sayfadaki ufak ikon, tiklaninca duzenleme popover'i
    Repeater {
        model: root.pageNotes
        delegate: Rectangle {
            required property var modelData
            x: modelData.x * root.paper.pageScale - 10
            y: modelData.y * root.paper.pageScale - 10
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
                        parent.x, root.paper.width - editNotePopover.width))
                    editNotePopover.y = Math.max(0, Math.min(
                        parent.y + parent.height + 4, root.paper.height - editNotePopover.height))
                    editNotePopover.visible = true
                }
            }
        }
    }

    // Yeni not olusturma popover'i (Not Ekle modunda sayfaya tiklaninca)
    Rectangle {
        id: newNotePopover
        objectName: "newNotePopover"
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
                    objectName: "newNoteInput"
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
                            bridge.reader.addPdfNote(root.resource.id, newNotePopover.pendingPage,
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
        objectName: "editNotePopover"
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
                            bridge.reader.deletePdfNote(editNotePopover.noteId)
                            editNotePopover.visible = false
                        }
                    }
                }
                AppButton {
                    text: "Kaydet"
                    variant: "primary"
                    onClicked: {
                        if (editNoteInput.text.trim().length > 0) {
                            bridge.reader.updatePdfNote(editNotePopover.noteId, editNoteInput.text.trim())
                        }
                        editNotePopover.visible = false
                    }
                }
            }
        }
    }
}
