import QtQuick
import "../components"
import "../theme"

Column {
    id: root
    spacing: 16

    signal openUpdateDialogRequested()

    Text {
        text: "Uygulama Güncellemeleri"
        font.family: Theme.fontHeading
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.textPrimary
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "GitHub Releases üzerinden yeni sürümleri denetler; kurulum dosyasının SHA-256 özetini doğrulayarak sessizce günceller."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        color: Theme.textSecondary
    }

    // 1. Kart: Sürüm Bilgisi ve Şimdi Denetle
    Rectangle {
        width: parent.width
        implicitHeight: versionCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: versionCol
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Row {
                spacing: 12
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 32
                    height: 32
                    radius: Theme.radiusSm
                    color: Theme.accentSubtle
                    AppIcon {
                        anchors.centerIn: parent
                        name: "fa5s.code-branch"
                        size: 15
                        color: Theme.accent
                    }
                }
                Column {
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: "Kurulu Sürüm: v" + bridge.update.currentVersion
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "Son denetim: " + bridge.update.lastCheckedText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textSecondary
                    }
                }
            }

            Row {
                spacing: 8

                AppButton {
                    text: bridge.update.isChecking ? "Denetleniyor..." : "Şimdi Denetle"
                    iconName: "fa5s.sync-alt"
                    variant: "primary"
                    enabledState: !bridge.update.isChecking && !bridge.update.isDownloading
                    onClicked: bridge.update.checkForUpdates(true)
                }

                AppButton {
                    visible: bridge.update.updateAvailable
                    text: "Yeni Sürüm Var (v" + bridge.update.latestVersion + ")"
                    iconName: "fa5s.arrow-circle-up"
                    variant: "subtle"
                    onClicked: bridge.update.requestUpdateDialog()
                }

                AppButton {
                    text: "Sürüm Geçmişi"
                    iconName: "fa5s.external-link-alt"
                    variant: "ghost"
                    onClicked: bridge.update.openReleasePage()
                }
            }
        }
    }

    // 2. Kart: Açılışta Otomatik Denetle
    Rectangle {
        width: parent.width
        implicitHeight: autoCheckCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: autoCheckCol
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Row {
                spacing: 8
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 4
                    color: bridge.update.autoCheckEnabled ? Theme.statusCompleted : Theme.textMuted
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: bridge.update.autoCheckEnabled ? "Açılışta Otomatik Denetim Açık" : "Açılışta Otomatik Denetim Kapalı"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Açıkken, uygulama penceresi açıldıktan 3 saniye sonra arka planda GitHub'da yeni sürüm arar. Ağ bağlantısı yoksa sessizce pas geçer."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textSecondary
            }

            Row {
                spacing: 8

                AppButton {
                    text: bridge.update.autoCheckEnabled ? "Otomatik Denetimi Kapat" : "Otomatik Denetimi Etkinleştir"
                    variant: bridge.update.autoCheckEnabled ? "secondary" : "primary"
                    onClicked: bridge.update.setAutoCheckEnabled(!bridge.update.autoCheckEnabled)
                }

                AppButton {
                    text: "Atlanan Sürümü Sıfırla"
                    variant: "ghost"
                    onClicked: bridge.update.resetSkippedVersion()
                }
            }
        }
    }

    // Bilgilendirme Notu
    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "Güvenlik: İndirilen kurulum dosyaları strictly doğrulanır (yalnızca github.com deposu, SHA-256 sağlama toplamı eşleşmesi ve 400 MB boyut sınırı). Özet uyuşmazlığında dosya derhal silinir. Kişisel hiçbir veri gönderilmez."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
    }
}
