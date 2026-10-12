import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"

// Ayarlar > Obsidian: vault klasörü seçimi, eşitleme durumu ve elle eşitleme (bridge.vault).
// Alıntı/not/kelimeler `<vault>/Papers/<citekey>.md` dosyalarına yalnızca işaretli blok içinde yazılır.
Column {
    id: root
    spacing: 16

    readonly property var status: bridge.vault.status
    readonly property bool enabled: status.enabled === true
    readonly property color stateColor: status.state === "error" ? Theme.danger
                                      : status.state === "syncing" || status.state === "pending" ? Theme.statusInProgress
                                      : root.enabled ? Theme.statusCompleted : Theme.textMuted
    readonly property string stateText: {
        if (status.state === "syncing") return "Eşitleniyor…"
        if (status.state === "pending") return "Değişiklikler bekliyor…"
        if (status.state === "error") return status.message !== "" ? status.message : "Vault klasörü kullanılamıyor."
        if (!root.enabled) return "Eşitleme kapalı"
        return status.message !== "" ? status.message : "Hazır"
    }

    FolderDialog {
        id: folderDialog
        title: "Obsidian Vault Klasörünü Seç"
        onAccepted: bridge.vault.chooseVault(selectedFolder)
    }

    Text {
        text: "Obsidian Vault"
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.textPrimary
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "PDF alıntıların, notların ve kelimelerin seçtiğin klasöre Papers/<atıf anahtarı>.md olarak yazılır. "
              + "Uygulama yalnızca işaretli bloğu günceller; notlarındaki diğer her şeye ve kendi eklediğin etiketlere dokunmaz."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        color: Theme.textSecondary
    }

    Rectangle {
        width: parent.width
        implicitHeight: vaultCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: vaultCol
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Text {
                width: parent.width
                objectName: "vaultPathText"
                elide: Text.ElideMiddle
                text: root.status.path !== undefined && root.status.path !== "" ? root.status.path : "Klasör seçilmedi"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: root.status.path ? Theme.textPrimary : Theme.textMuted
            }

            Row {
                spacing: 8

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 4
                    color: root.stateColor
                }
                Text {
                    objectName: "vaultStateText"
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.stateText
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: root.status.state === "error" ? Theme.dangerText : Theme.textSecondary
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.status.lastSync !== undefined && root.status.lastSync !== ""
                    text: "· Son eşitleme: " + root.status.lastSync
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }
            }

            Row {
                spacing: 8

                AppButton {
                    objectName: "chooseVaultButton"
                    text: root.enabled ? "Klasörü Değiştir" : "Klasör Seç"
                    iconName: "fa5s.folder-open"
                    variant: "primary"
                    onClicked: folderDialog.open()
                }
                AppButton {
                    objectName: "syncVaultButton"
                    text: "Şimdi Eşitle"
                    iconName: "fa5s.sync"
                    variant: "secondary"
                    enabledState: root.enabled && root.status.state !== "syncing"
                    onClicked: bridge.vault.syncNow()
                }
                AppButton {
                    objectName: "clearVaultButton"
                    visible: root.status.path !== undefined && root.status.path !== ""
                    text: "Eşitlemeyi Kapat"
                    variant: "ghost"
                    onClicked: bridge.vault.clearVault()
                }
            }
        }
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "İpucu: Obsidian'da klasörü \"Vault olarak aç\" ile açtığından emin ol. Not içindeki sayfa numaraları "
              + "(s. 3) uygulamadaki PDF'e bağlanır; blok bağlantıları ([[atıf-anahtarı#^hl-…]]) alıntıya gider."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
    }
}
