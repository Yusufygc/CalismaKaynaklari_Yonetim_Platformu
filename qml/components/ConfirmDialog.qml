import QtQuick
import QtQuick.Controls
import "../theme"

// Yıkıcı işlem onayı: başlık + mesaj + Vazgeç / onay düğmesi. Onayda `confirmed` yayılır ve pencere kapanır.
Popup {
    id: root

    property string title: ""
    property string message: ""
    property string confirmText: "Sil"

    signal confirmed()

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
            text: root.title
            font.family: Theme.fontHeading
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            color: Theme.textPrimary
        }

        Text {
            width: parent.width
            wrapMode: Text.Wrap
            text: root.message
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            color: Theme.textSecondary
        }

        Row {
            anchors.right: parent.right
            spacing: 8

            AppButton {
                objectName: "confirmCancelButton"
                text: "Vazgeç"
                variant: "ghost"
                onClicked: root.close()
            }

            AppButton {
                objectName: "confirmAcceptButton"
                text: root.confirmText
                iconName: "fa5s.trash"
                variant: "danger"
                onClicked: {
                    root.close()
                    root.confirmed()
                }
            }
        }
    }
}
