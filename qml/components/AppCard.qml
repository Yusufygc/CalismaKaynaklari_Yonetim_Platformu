import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import "../theme"

Item {
    id: root

    property int cardWidth: 280
    property int cardHeight: 290

    // Modelden gelen property'ler
    property int resourceId: model ? model.id : 0
    property string title: model ? model.title : ""
    property string url: model ? model.url : ""
    property string domain: model ? model.domain : ""
    property string categoryName: model ? model.categoryName : ""
    property string categoryColor: model ? model.categoryColor : Theme.fallbackCategoryColor
    property string status: model ? model.status : "INBOX"
    property string statusLabel: model ? model.statusLabel : ""
    property bool isPinned: model ? model.isPinned : false
    property bool isFavorite: model ? model.isFavorite : false
    property string description: model ? model.description : ""
    property string thumbnailUrl: model ? model.thumbnailUrl : ""
    property int readingMinutes: model ? model.readingMinutes : 0
    property var tags: model ? model.tags : []

    signal clicked()
    signal pinToggled()
    signal favoriteToggled()

    width: cardWidth
    height: cardHeight

    // Kart Gövdesi (Hover animasyonlu)
    Rectangle {
        id: cardBody
        anchors.fill: parent
        anchors.topMargin: mouseArea.containsMouse ? 0 : 3
        anchors.bottomMargin: mouseArea.containsMouse ? 3 : 0
        radius: Theme.radiusMd
        color: mouseArea.containsMouse ? Theme.bgElevated : Theme.bgSurface
        border.width: 1
        border.color: mouseArea.containsMouse ? Theme.borderStrong : Theme.borderSubtle
        clip: true

        Behavior on anchors.topMargin { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutCubic } }
        Behavior on anchors.bottomMargin { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

        Column {
            anchors.fill: parent
            spacing: 0

            // 1. Üst Görsel / Banner Alanı
            Item {
                width: parent.width
                height: 120
                clip: true

                // Küçük Resim Varsa
                Image {
                    id: thumbnailImg
                    anchors.fill: parent
                    source: root.thumbnailUrl
                    fillMode: Image.PreserveAspectCrop
                    visible: root.thumbnailUrl !== ""
                    smooth: true
                    cache: true
                }

                // Küçük Resim Yoksa Şık Gradyan Banner
                Rectangle {
                    anchors.fill: parent
                    visible: root.thumbnailUrl === ""
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.gradientHeaderStart }
                        GradientStop { position: 1.0; color: Qt.alpha(root.categoryColor, Theme.isDark ? 0.25 : 0.15) }
                    }

                    // Arka plan filigran ikonu
                    AppIcon {
                        anchors.centerIn: parent
                        name: "fa5s.globe"
                        size: 38
                        color: Qt.alpha(Theme.textMuted, 0.25)
                    }
                }

                // Banner Alt Karartması (Görsel üstü metin okunurluğu için)
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.27) }
                    }
                }

                // Sol Üst: Kategori Rozeti
                AppBadge {
                    visible: root.categoryName !== ""
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 10
                    text: root.categoryName
                    dotColor: root.categoryColor
                    badgeColor: Theme.badgeOverlay
                    borderColor: Qt.alpha(root.categoryColor, 0.4)
                    textColor: Theme.textPrimary
                }

                // Sağ Üst: Pin & Favori Aksiyonları
                Row {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 8
                    spacing: 4

                    // Pin Butonu
                    Rectangle {
                        width: 26
                        height: 26
                        radius: Theme.radiusPill
                        color: root.isPinned ? Qt.alpha(Theme.pin, 0.25) : Theme.backdropSubtle
                        border.width: 1
                        border.color: root.isPinned ? Theme.pin : "transparent"

                        AppIcon {
                            anchors.centerIn: parent
                            name: "fa5s.thumbtack"
                            size: 11
                            color: root.isPinned ? Theme.pin : Theme.textOnAccent
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                mouse.accepted = true
                                root.pinToggled()
                            }
                        }
                    }

                    // Favori Butonu
                    Rectangle {
                        width: 26
                        height: 26
                        radius: Theme.radiusPill
                        color: root.isFavorite ? Qt.alpha(Theme.favorite, 0.25) : Theme.backdropSubtle
                        border.width: 1
                        border.color: root.isFavorite ? Theme.favorite : "transparent"

                        AppIcon {
                            anchors.centerIn: parent
                            name: "fa5s.heart"
                            size: 12
                            color: root.isFavorite ? Theme.favorite : Theme.textOnAccent
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                mouse.accepted = true
                                root.favoriteToggled()
                            }
                        }
                    }
                }
            }

            // 2. Kart İçerik Alanı
            Column {
                width: parent.width
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                padding: 12
                spacing: 6

                // Alan Adı ve Okuma Süresi
                Row {
                    spacing: 6
                    width: parent.width

                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "fa5s.link"
                        size: 10
                        color: Theme.accent
                        visible: root.domain !== ""
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.domain ? root.domain : "Yerel Not"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                        color: Theme.accentText
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, 140)
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.readingMinutes > 0
                        text: "• " + root.readingMinutes + " dk okuma"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }

                // Başlık
                Text {
                    width: parent.width
                    text: root.title
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase + 1
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                    lineHeight: 1.25
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                    elide: Text.ElideRight
                }

                // Kısa Açıklama
                Text {
                    width: parent.width
                    visible: root.description !== ""
                    text: root.description
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textSecondary
                    lineHeight: 1.2
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                    elide: Text.ElideRight
                }
            }

            Item { Layout.fillHeight: true }

            // 3. Kart Alt Barı (Durum ve Etiketler)
            Item {
                width: parent.width
                height: 38

                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: 1
                    color: Theme.borderSubtle
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 6

                    // Durum Rozeti
                    AppBadge {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.statusLabel
                        dotColor: {
                            if (root.status === "COMPLETED") return Theme.statusCompleted
                            if (root.status === "IN_PROGRESS") return Theme.statusInProgress
                            if (root.status === "PLANNED") return Theme.statusPlanned
                            return Theme.statusInbox
                        }
                        badgeColor: {
                            if (root.status === "COMPLETED") return Theme.statusCompletedBg
                            if (root.status === "IN_PROGRESS") return Theme.statusInProgressBg
                            if (root.status === "PLANNED") return Theme.statusPlannedBg
                            return Theme.statusInboxBg
                        }
                        textColor: Theme.textPrimary
                        borderColor: "transparent"
                    }

                    // İlk etiket (varsa)
                    AppBadge {
                        visible: root.tags && root.tags.length > 0
                        anchors.verticalCenter: parent.verticalCenter
                        text: (root.tags && root.tags.length > 0) ? ("#" + root.tags[0].name) : ""
                        badgeColor: Theme.bgHover
                        borderColor: Theme.borderSubtle
                        textColor: Theme.textSecondary
                    }

                    // Ek etiket sayısı rozeti (+2)
                    AppBadge {
                        visible: root.tags && root.tags.length > 1
                        anchors.verticalCenter: parent.verticalCenter
                        text: "+" + (root.tags.length - 1)
                        badgeColor: Theme.bgHover
                        borderColor: Theme.borderSubtle
                        textColor: Theme.textMuted
                    }
                }
            }
        }

        // Kart Tıklama
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }
    }
}
