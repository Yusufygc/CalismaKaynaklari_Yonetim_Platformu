import QtQuick
import QtQuick.Controls
import "../components"
import "../theme"

Popup {
    id: root

    anchors.centerIn: Overlay.overlay
    width: 480
    padding: 24
    modal: true
    focus: true
    closePolicy: bridge.update.isDownloading ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)

    background: Rectangle {
        color: Theme.popoverBg
        radius: Theme.radiusMd
        border.width: 1
        border.color: Theme.borderStrong
    }

    contentItem: Column {
        spacing: 16
        width: parent.width

        // 1. Durum: Windows Akıllı Uygulama Denetimi (SAC) Bekleme Döngüsü
        Column {
            width: parent.width
            spacing: 14
            visible: bridge.update.isWaitingWindows

            Row {
                spacing: 12
                AppIcon {
                    name: "fa5s.shield-alt"
                    size: 22
                    color: Theme.statusInProgress
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "Windows Güvenlik İncelemesi"
                    font.family: Theme.fontHeading
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Windows Akıllı Uygulama Denetimi kurulum dosyasını inceliyor. Engel kalktığında kurulum otomatik olarak başlayacaktır."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
                lineHeight: 1.3
            }

            Rectangle {
                width: parent.width
                height: 40
                radius: Theme.radiusSm
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle

                Row {
                    anchors.centerIn: parent
                    spacing: 8
                    AppIcon {
                        name: "fa5s.clock"
                        size: 13
                        color: Theme.accent
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "Otomatik deneniyor... (" + bridge.update.waitAttemptsLeft + " deneme kaldı)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8
                AppButton {
                    text: "Beklemeyi Bırak"
                    variant: "secondary"
                    iconName: "fa5s.times"
                    onClicked: bridge.update.cancelWait()
                }
            }
        }

        // 2. Durum: Windows Tarafından Engellendi (Gezgin Fallback)
        Column {
            width: parent.width
            spacing: 14
            visible: bridge.update.isBlockedByWindows && !bridge.update.isWaitingWindows

            Row {
                spacing: 12
                AppIcon {
                    name: "fa5s.info-circle"
                    size: 22
                    color: Theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "Kurulum Dosyası Hazır"
                    font.family: Theme.fontHeading
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Windows otomatik başlatmayı şimdilik engelledi. Kurulum dosyasını klasöründe açıp çift tıklayarak hemen kurabilirsiniz (veya birkaç dakika sonra yeniden deneyebilirsiniz)."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
                lineHeight: 1.3
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                AppButton {
                    text: "Kapat"
                    variant: "ghost"
                    onClicked: root.close()
                }

                AppButton {
                    text: "Sürüm Sayfası"
                    variant: "secondary"
                    iconName: "fa5s.external-link-alt"
                    onClicked: bridge.update.openReleasePage()
                }

                AppButton {
                    text: "Dosyayı Göster"
                    variant: "primary"
                    iconName: "fa5s.folder-open"
                    onClicked: bridge.update.openDownloadFolder()
                }
            }
        }

        // 3. Durum: İndirme Sürüyor
        Column {
            width: parent.width
            spacing: 14
            visible: bridge.update.isDownloading

            Row {
                spacing: 12
                AppIcon {
                    name: "fa5s.cloud-download-alt"
                    size: 22
                    color: Theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "Güncelleme İndiriliyor..."
                    font.family: Theme.fontHeading
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // İlerleme Çubuğu
            Rectangle {
                width: parent.width
                height: 10
                radius: 5
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle
                clip: true

                Rectangle {
                    width: parent.width * (bridge.update.downloadProgress / 100.0)
                    height: parent.height
                    radius: 5
                    color: Theme.accent

                    Behavior on width { NumberAnimation { duration: 150 } }
                }
            }

            Item {
                width: parent.width
                height: 18
                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "%" + bridge.update.downloadProgress + " tamamlandı"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }
                Text {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: "SHA-256 doğrulanıyor..."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textSecondary
                }
            }
        }

        // 4. Durum: Normal Yeni Sürüm Bildirimi
        Column {
            width: parent.width
            spacing: 14
            visible: !bridge.update.isDownloading && !bridge.update.isWaitingWindows && !bridge.update.isBlockedByWindows

            Row {
                spacing: 12
                AppIcon {
                    name: "fa5s.rocket"
                    size: 22
                    color: Theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                }
                Column {
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: "Yeni Sürüm Mevcut: v" + bridge.update.latestVersion
                        font.family: Theme.fontHeading
                        font.pixelSize: Theme.fontLg
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "Mevcut sürüm: v" + bridge.update.currentVersion + (bridge.update.downloadSizeMb ? " • " + bridge.update.downloadSizeMb : "")
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textSecondary
                    }
                }
            }

            // Sürüm Notları Kutusu
            Rectangle {
                width: parent.width
                height: Math.min(180, Math.max(80, notesText.implicitHeight + 20))
                radius: Theme.radiusSm
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle

                Flickable {
                    id: flick
                    anchors.fill: parent
                    anchors.margins: 12
                    contentWidth: width
                    contentHeight: notesText.implicitHeight
                    clip: true

                    Text {
                        id: notesText
                        width: flick.width
                        wrapMode: Text.Wrap
                        text: bridge.update.releaseNotes || "Bu sürüm için detaylı not bulunmuyor."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                        lineHeight: 1.25
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                AppButton {
                    text: "Bu Sürümü Atla"
                    variant: "ghost"
                    onClicked: {
                        bridge.update.skipCurrentVersion()
                        root.close()
                    }
                }

                AppButton {
                    text: "Daha Sonra"
                    variant: "secondary"
                    onClicked: root.close()
                }

                AppButton {
                    text: "Şimdi Güncelle"
                    variant: "primary"
                    iconName: "fa5s.download"
                    onClicked: bridge.update.startDownload()
                }
            }
        }
    }
}
