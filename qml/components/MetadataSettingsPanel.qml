import QtQuick
import "../theme"

// Ayarlar > Künye: yeni eklenen PDF'in künyesini (yazar, yıl, dergi) OpenAlex'ten otomatik doldurma (bridge.metadata).
// Varsayılan açıktır (özellik zaten böyleydi): açıkken PDF'ten çıkarılan DOI (başka hiçbir şey değil) openalex.org'a gönderilir.
Column {
    id: root
    spacing: 16

    readonly property bool enabled: bridge.metadata.autoFill

    Text {
        text: "Künyeyi Otomatik Doldur"
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.textPrimary
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "DOI'si olan yeni bir PDF eklediğinde yazar, yıl ve dergi bilgisi OpenAlex'ten kendiliğinden getirilir; "
              + "atıf ve Obsidian notları bu bilgiyi kullanır."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        color: Theme.textSecondary
    }

    Rectangle {
        width: parent.width
        implicitHeight: metadataCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: metadataCol
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
                    color: root.enabled ? Theme.statusCompleted : Theme.textMuted
                }
                Text {
                    objectName: "autoMetadataStateText"
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.enabled ? "Açık" : "Kapalı"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }
            }

            AppButton {
                objectName: "autoMetadataButton"
                text: root.enabled ? "Kapat" : "Etkinleştir"
                variant: root.enabled ? "secondary" : "primary"
                onClicked: bridge.metadata.setAutoFill(!root.enabled)
            }
        }
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "Gizlilik: açıkken yalnızca PDF'ten okunan DOI openalex.org'a gönderilir; kapatırsan hiçbir şey gönderilmez. Zaten dolu olan hiçbir alan değiştirilmez; "
              + "bulunan makalenin başlığı PDF'in kendi başlığıyla açıkça çelişiyorsa (DOI başka bir makaleye ait olabilir) hiçbir şey yazılmaz. "
              + "Elle \"Akademik bilgi getir\" her zaman kullanılabilir."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
    }
}
