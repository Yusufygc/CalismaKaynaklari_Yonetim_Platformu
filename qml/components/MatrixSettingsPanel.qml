import QtQuick
import "../theme"

// Ayarlar > Matris: literatür matrisinin sütun sırası (Bilgi Havuzu > Matris'te ve dışa aktarmada), Obsidian'daki
// `Papers/_Matris.md` dosyasına hangi sütunların yazılacağı ve o dosyada hücre başına en çok kaç alıntı olacağı
// (bridge.synthesis). Uygulama içindeki matrisin hücrelerinde sınır yoktur; sınır yalnızca Obsidian dosyasını küçük tutar.
Column {
    id: root
    spacing: 16

    readonly property var limitChoices: [
        { "label": "Hepsi", "value": 0 }, { "label": "3", "value": 3 }, { "label": "5", "value": 5 },
        { "label": "10", "value": 10 }, { "label": "20", "value": 20 }
    ]

    Text {
        text: "Literatür Matrisi"
        font.family: Theme.fontHeading
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.textPrimary
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "Matris, her makaleyi bir satırda ve her anlam etiketini bir sütunda gösterir. Sütunların sırasını buradan değiştirebilirsin; "
              + "Bilgi Havuzu'ndaki matris, dışa aktarılan dosya ve Obsidian notu aynı sırayı kullanır."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        color: Theme.textSecondary
    }

    Rectangle {
        width: parent.width
        implicitHeight: columnsCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: columnsCol
            anchors.fill: parent
            anchors.margins: 14
            spacing: 6

            Row {
                width: parent.width
                Text {
                    width: parent.width - 150
                    text: "Sütun"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }
                Text {
                    width: 90
                    text: "Obsidian'da yaz"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }
                Text {
                    width: 60
                    text: "Sıra"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }
            }

            Repeater {
                model: bridge.synthesis.columnSettings

                delegate: Rectangle {
                    id: columnRow
                    required property var modelData
                    required property int index
                    objectName: "matrixColumnRow"
                    width: columnsCol.width
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        spacing: 0

                        Row {
                            width: parent.width - 160
                            height: parent.height
                            spacing: 8
                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 8
                                height: 8
                                radius: 4
                                color: columnRow.modelData.color !== "" ? columnRow.modelData.color : Theme.textMuted
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: columnRow.modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textPrimary
                            }
                        }

                        Item {
                            width: 90
                            height: parent.height

                            Rectangle {
                                objectName: "vaultColumnToggle"
                                anchors.verticalCenter: parent.verticalCenter
                                width: 18
                                height: 18
                                radius: 4
                                color: columnRow.modelData.vault ? Theme.accent : "transparent"
                                border.width: 1
                                border.color: columnRow.modelData.vault ? Theme.accent : Theme.borderStrong

                                AppIcon {
                                    visible: columnRow.modelData.vault
                                    anchors.centerIn: parent
                                    name: "fa5s.check"
                                    size: 10
                                    color: Theme.textOnAccent
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: bridge.synthesis.setVaultColumn(columnRow.modelData.key, !columnRow.modelData.vault)
                                }
                            }
                        }

                        Row {
                            width: 70
                            height: parent.height
                            spacing: 2
                            AppIconButton {
                                objectName: "moveColumnUp"
                                anchors.verticalCenter: parent.verticalCenter
                                iconName: "fa5s.chevron-up"
                                iconSize: 11
                                implicitWidth: 28
                                implicitHeight: 28
                                tooltip: "Yukarı taşı"
                                opacity: columnRow.index > 0 ? 1 : 0.3
                                onClicked: bridge.synthesis.moveColumn(columnRow.modelData.key, -1)
                            }
                            AppIconButton {
                                objectName: "moveColumnDown"
                                anchors.verticalCenter: parent.verticalCenter
                                iconName: "fa5s.chevron-down"
                                iconSize: 11
                                implicitWidth: 28
                                implicitHeight: 28
                                tooltip: "Aşağı taşı"
                                opacity: columnRow.index < bridge.synthesis.columnSettings.length - 1 ? 1 : 0.3
                                onClicked: bridge.synthesis.moveColumn(columnRow.modelData.key, 1)
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        width: parent.width
        implicitHeight: limitCol.implicitHeight + 28
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderSubtle

        Column {
            id: limitCol
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10

            Text {
                text: "Obsidian'da hücre başına en çok alıntı"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Flow {
                width: parent.width
                spacing: 8
                Repeater {
                    model: root.limitChoices
                    delegate: AppFilterChip {
                        required property var modelData
                        objectName: "cellLimitChip"
                        text: modelData.label
                        isSelected: bridge.synthesis.cellLimit === modelData.value
                        onClicked: bridge.synthesis.setCellLimit(modelData.value)
                    }
                }
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Fazlası, Obsidian dosyasında \"… ve N alıntı daha (uygulamada)\" satırıyla belirtilir. Bilgi Havuzu'ndaki matriste hücreler ilk 3 alıntıyı gösterir, "
                      + "gerisi \"alıntı daha\" bağlantısıyla açılır; dışa aktarma ve panoya kopyalama her zaman tüm alıntıları içerir."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
        }
    }

    AppButton {
        objectName: "resetMatrixOptionsButton"
        text: "Varsayılana dön"
        variant: "ghost"
        onClicked: bridge.synthesis.resetOptions()
    }
}
