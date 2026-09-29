import QtQuick
import QtQuick.Controls
import "../theme"

// Aramayı kaydet: isteğe bağlı koleksiyon etiketi. Kaydet'e basınca `saveRequested(tag)` yayar.
Popup {
    id: root

    signal saveRequested(string tag)  // Kaydet'e basılınca (boş etiket = koleksiyon yok)

    anchors.centerIn: Overlay.overlay
    width: 380
    padding: 20
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    onOpened: {
        tagInput.text = ""
        tagInput.forceActiveFocus()
    }

    background: Rectangle {
        color: Theme.popoverBg
        radius: Theme.radiusMd
        border.width: 1
        border.color: Theme.borderStrong
    }

    contentItem: Column {
        spacing: 12

        Text {
            text: "Aramayı Kaydet"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            color: Theme.textPrimary
        }

        Text {
            width: parent.width
            wrapMode: Text.Wrap
            text: "Yeni yayın çıkınca kayıtlı aramanda \"yeni\" rozeti görürsün. İstersen bu aramadan kaydettiğin makalelere otomatik bir etiket (koleksiyon) eklenir."
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            color: Theme.textSecondary
        }

        Rectangle {
            width: parent.width
            height: 34
            radius: Theme.radiusSm
            color: Theme.bgSurface
            border.width: 1
            border.color: tagInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

            TextInput {
                id: tagInput
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: TextInput.AlignVCenter
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                clip: true
                onAccepted: saveSearchButton.clicked()

                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    text: "Koleksiyon etiketi (isteğe bağlı)"
                    font: parent.font
                    color: Theme.textMuted
                    visible: !parent.text
                }
            }
        }

        Row {
            anchors.right: parent.right
            spacing: 8

            AppButton {
                text: "Vazgeç"
                variant: "ghost"
                onClicked: root.close()
            }

            AppButton {
                id: saveSearchButton
                text: "Kaydet"
                variant: "primary"
                onClicked: {
                    root.saveRequested(tagInput.text.trim())
                    root.close()
                }
            }
        }
    }
}
