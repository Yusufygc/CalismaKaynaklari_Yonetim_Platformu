import QtQuick
import QtQuick.Controls
import QtQuick.Pdf
import "../components"
import "../theme"

Item {
    id: root

    property var resource: bridge.currentReaderResource

    PdfDocument {
        id: pdfDoc
        objectName: "pdfDoc"
        source: root.resource && root.resource.url ? root.resource.url : ""
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // Üst Bar
        Item {
            width: parent.width
            height: 56

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                AppButton {
                    text: "Vitrine Dön"
                    iconName: "fa5s.arrow-left"
                    variant: "ghost"
                    onClicked: bridge.closeReader()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.resource && root.resource.title ? root.resource.title : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    width: Math.min(implicitWidth, 420)
                }
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: pdfDoc.status === PdfDocument.Ready
                          ? (pageArea.currentPage + 1) + " / " + pdfDoc.pageCount
                          : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppButton {
                    text: "Not Ekle"
                    iconName: "fa5s.comment-alt"
                    variant: pageArea.noteMode ? "primary" : "ghost"
                    onClicked: pageArea.noteMode = !pageArea.noteMode
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppIconButton {
                    iconName: "fa5s.search-minus"
                    iconSize: 12
                    tooltip: "Uzaklaştır"
                    onClicked: pageArea.zoomOut()
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Math.round(pageArea.renderScale * 100) + "%"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                AppIconButton {
                    iconName: "fa5s.search-plus"
                    iconSize: 12
                    tooltip: "Yakınlaştır"
                    onClicked: pageArea.zoomIn()
                }

                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.borderSubtle
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppIconButton {
                    iconName: "fa5s.external-link-alt"
                    iconSize: 12
                    tooltip: "Sistem Görüntüleyicisinde Aç"
                    onClicked: {
                        if (root.resource && root.resource.url) {
                            Qt.openUrlExternally(root.resource.url)
                        }
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // PDF Gövdesi
        Item {
            width: parent.width
            height: parent.height - 56

            PdfPageArea {
                id: pageArea
                anchors.fill: parent
                document: pdfDoc
                resource: root.resource ?? ({})
            }

            Column {
                anchors.centerIn: parent
                spacing: 8
                visible: pdfDoc.status !== PdfDocument.Ready

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: pdfDoc.status === PdfDocument.Error
                          ? "PDF açılamadı: " + pdfDoc.error
                          : "PDF yükleniyor..."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }
        }
    }
}
