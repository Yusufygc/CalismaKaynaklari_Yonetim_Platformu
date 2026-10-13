import QtQuick
import "../theme"
import "../theme/palettes.js" as Palettes
import "../theme/fonts.js" as Fonts

// Ayarlar > Görünüm: açık/koyu mod, renk teması ve yazı tipi çifti. Seçim anında uygulanır ve kaydedilir
// (bridge.appearance; mod: bridge.isDarkTheme). Tema ve yazı tipi tanımları qml/theme/palettes.js ve fonts.js'tedir.
Column {
    id: root
    spacing: 20

    readonly property var installedFonts: Qt.fontFamilies()

    Text {
        text: "Görünüm"
        font.family: Theme.fontHeading
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.textPrimary
    }

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "Renk temasını, açık/koyu modu ve yazı tiplerini buradan seçersin. Değişiklik hemen uygulanır ve bir sonraki açılışta hatırlanır."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        color: Theme.textSecondary
    }

    // ---- Mod ----
    Column {
        width: parent.width
        spacing: 8

        Text {
            text: "Mod"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }

        Row {
            spacing: 8
            AppButton {
                objectName: "lightModeButton"
                text: "Açık"
                iconName: "fa5s.sun"
                variant: !bridge.isDarkTheme ? "primary" : "secondary"
                onClicked: if (bridge.isDarkTheme) bridge.toggleTheme()
            }
            AppButton {
                objectName: "darkModeButton"
                text: "Koyu"
                iconName: "fa5s.moon"
                variant: bridge.isDarkTheme ? "primary" : "secondary"
                onClicked: if (!bridge.isDarkTheme) bridge.toggleTheme()
            }
        }
    }

    // ---- Renk teması ----
    Column {
        width: parent.width
        spacing: 8

        Text {
            text: "Renk teması"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }

        Flow {
            width: parent.width
            spacing: 12

            Repeater {
                model: Palettes.palettes

                delegate: Rectangle {
                    id: paletteCard
                    required property var modelData
                    objectName: "paletteCard"
                    readonly property bool selected: bridge.appearance.paletteId === modelData.id
                    width: (parent.width - 12) / 2
                    height: cardColumn.implicitHeight + 24
                    radius: Theme.radiusMd
                    color: selected ? Theme.accentSubtle : Theme.bgElevated
                    border.width: selected ? 2 : 1
                    border.color: selected ? Theme.accent : Theme.borderSubtle

                    Column {
                        id: cardColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Row {
                            spacing: 6
                            Repeater {
                                model: paletteCard.modelData.swatches
                                delegate: Rectangle {
                                    required property string modelData
                                    width: 24
                                    height: 24
                                    radius: 12
                                    color: modelData
                                    border.width: 1
                                    border.color: Theme.borderStrong
                                }
                            }
                        }

                        Row {
                            spacing: 8
                            Text {
                                text: paletteCard.modelData.name
                                font.family: Theme.fontHeading
                                font.pixelSize: Theme.fontBase + 1
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                            AppIcon {
                                visible: paletteCard.selected
                                anchors.verticalCenter: parent.verticalCenter
                                name: "fa5s.check-circle"
                                size: 13
                                color: Theme.accentText
                            }
                        }

                        Text {
                            width: parent.width
                            wrapMode: Text.Wrap
                            text: paletteCard.modelData.description
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.appearance.setPalette(paletteCard.modelData.id)
                    }
                }
            }
        }
    }

    // ---- Yazı tipi ----
    Column {
        width: parent.width
        spacing: 8

        Text {
            text: "Yazı tipi"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }

        Text {
            width: parent.width
            wrapMode: Text.Wrap
            text: "Başlık, arayüz ve alıntı yazı tipleri bir çift olarak seçilir. Yazı tiplerinin çoğu uygulamayla birlikte gelir; bulunamayan olursa benzeri kullanılır."
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }

        Repeater {
            model: Fonts.pairs

            delegate: Rectangle {
                id: fontCard
                required property var modelData
                objectName: "fontCard"
                readonly property var resolved: Fonts.resolve(modelData.id, root.installedFonts)
                readonly property bool selected: bridge.appearance.fontPairId === modelData.id
                readonly property bool allInstalled: resolved.installed.heading && resolved.installed.body && resolved.installed.reading
                width: root.width
                height: fontColumn.implicitHeight + 24
                radius: Theme.radiusMd
                color: selected ? Theme.accentSubtle : Theme.bgElevated
                border.width: selected ? 2 : 1
                border.color: selected ? Theme.accent : Theme.borderSubtle

                Column {
                    id: fontColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4

                    Row {
                        spacing: 8
                        Text {
                            text: fontCard.modelData.name
                            font.family: fontCard.resolved.heading
                            font.pixelSize: Theme.fontMd
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                        AppIcon {
                            visible: fontCard.selected
                            anchors.verticalCenter: parent.verticalCenter
                            name: "fa5s.check-circle"
                            size: 13
                            color: Theme.accentText
                        }
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "Kaynakları okumak, işaretlemek ve karşılaştırmak için sade bir arayüz."
                        font.family: fontCard.resolved.body
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "“Derin öğrenme yöntemleri, geleneksel yaklaşımlara göre belirgin biçimde daha yüksek doğruluk sağlamaktadır.”"
                        font.family: fontCard.resolved.reading
                        font.pixelSize: Theme.fontBase
                        font.italic: true
                        color: Theme.textSecondary
                    }

                    Text {
                        objectName: "fontCardInfo"
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: fontCard.modelData.description + "  ·  Kullanılan: " + fontCard.resolved.heading + " / "
                              + fontCard.resolved.body + " / " + fontCard.resolved.reading
                              + (fontCard.allInstalled ? "" : "  (bazıları kurulu değil, benzeri kullanılıyor)")
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.appearance.setFontPair(fontCard.modelData.id)
                }
            }
        }
    }

    AppButton {
        objectName: "resetAppearanceButton"
        text: "Varsayılana dön"
        variant: "ghost"
        onClicked: bridge.appearance.reset()
    }
}
