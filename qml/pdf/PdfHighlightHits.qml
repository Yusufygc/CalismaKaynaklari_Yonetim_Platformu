import QtQuick
import QtQuick.Controls
import "../components"
import "../theme"

// Kalıcı alıntılara tıklama alanları (yorum köşe işareti dahil) ve tıklanınca açılan düzenleme popover'ı
// (renk/anlam değiştir, yorum, sil). Sayfa (`paper`) üzerine bindirilir.
Item {
    id: root

    property Item paper            // Sayfa kâğıdı (pageScale, width, height)
    property int pageIndex: 0
    property var highlightModel    // bridge.pdf.pageModel(pageIndex): bu sayfanın alıntıları (artımlı)

    readonly property bool popoverVisible: editHighlightPopover.visible
    function closeAll() { editHighlightPopover.visible = false }

    // Her popover açılışında artar; sayfa-dismiss işleyicisi tıklamayla yeni açılanı kapatmasın diye kullanır.
    property int openCount: 0

    anchors.fill: parent
    z: 30

    // Kalici highlight'lara tiklama -> renk degistir / sil popover'i
    // TapHandler kullanilir (MouseArea degil) -- MouseArea, ustune
    // geldigi metinde yeni bir surukle-secim baslatilmasini engelleyip
    // "highlight bir kere calisiyor, ikincisi calismiyor" hatasina
    // yol aciyordu (MouseArea eski girdi sistemi, DragHandler ile
    // ayni alanda oncelik/grab catismasi yaratabiliyor).
    Repeater {
        model: root.highlightModel
        delegate: Item {
            id: highlightHitArea
            objectName: "highlightHitArea"
            required property int annotationId
            required property var boundingRect
            required property string comment
            required property string label
            visible: boundingRect.length === 4
            x: visible ? boundingRect[0] * root.paper.pageScale : 0
            y: visible ? boundingRect[1] * root.paper.pageScale : 0
            width: visible ? boundingRect[2] * root.paper.pageScale : 0
            height: visible ? boundingRect[3] * root.paper.pageScale : 0

            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }

            // Yorumu olan alintilarin kose isareti
            Rectangle {
                visible: highlightHitArea.comment !== ""
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
                    editHighlightPopover.highlightId = highlightHitArea.annotationId
                    editHighlightPopover.label = highlightHitArea.label
                    editCommentInput.text = highlightHitArea.comment
                    editHighlightPopover.x = Math.max(0, Math.min(
                        highlightHitArea.x, root.paper.width - editHighlightPopover.width))
                    editHighlightPopover.y = Math.max(0, Math.min(
                        highlightHitArea.y + highlightHitArea.height + 4,
                        root.paper.height - editHighlightPopover.implicitHeight))
                    editHighlightPopover.visible = true
                    root.openCount++
                }
            }
        }
    }

    // Var olan highlight duzenleme popover'i (renk/anlam, yorum, sil)
    Rectangle {
        id: editHighlightPopover
        objectName: "editHighlightPopover"
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
                    model: bridge.pdf.labels
                    delegate: Rectangle {
                        required property var modelData
                        width: 22
                        height: 22
                        radius: 11
                        color: modelData.color
                        border.width: 1
                        border.color: Theme.swatchBorderLight

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            ToolTip.visible: containsMouse
                            ToolTip.text: parent.modelData.name
                            onClicked: {
                                bridge.pdf.setLabel(editHighlightPopover.highlightId, parent.modelData.key)
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
                            bridge.pdf.deleteAnnotation(editHighlightPopover.highlightId)
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
                    objectName: "editCommentInput"
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
                        bridge.pdf.setComment(editHighlightPopover.highlightId, editCommentInput.text)
                        editHighlightPopover.visible = false
                    }
                }
            }
        }
    }
}
