import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isCollapsed: false
    property string activeNav: bridge.currentView
    property string activeStatusFilter: "ALL"
    property bool isFavoriteFilter: false

    signal navSelected(string viewName)
    signal statusFilterSelected(string statusName)
    signal favoriteFilterSelected(bool isFav)
    signal filterSelected(string statusName, bool isFav)

    width: isCollapsed ? 64 : 230
    color: Theme.bgSidebar
    border.width: 1
    border.color: Theme.borderSubtle

    Behavior on width { NumberAnimation { duration: Theme.animBase; easing.type: Easing.OutCubic } }

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Logo & Başlık Barı
        Item {
            width: parent.width
            height: 56

            Row {
                anchors.left: parent.left
                anchors.leftMargin: root.isCollapsed ? 18 : 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                // Logo İkon Kutusu
                Rectangle {
                    width: 32
                    height: 32
                    radius: Theme.radiusSm
                    color: Theme.accentSubtle
                    border.width: 1
                    border.color: Theme.accent

                    AppIcon {
                        anchors.centerIn: parent
                        name: "fa5s.bookmark"
                        size: 14
                        color: Theme.accent
                    }
                }

                // Başlık
                Column {
                    visible: !root.isCollapsed
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        text: "Kaynak Yönetim"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Text {
                        text: "Kişisel Bilgi Tabanı"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        color: Theme.textMuted
                    }
                }
            }

            // Katlama / Açma Butonu (Sağda)
            AppIconButton {
                visible: !root.isCollapsed
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                iconName: "fa5s.chevron-left"
                iconSize: 11
                tooltip: "Menüyü Daralt"
                tooltipPosition: "bottom"
                onClicked: root.isCollapsed = true
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // Açma Butonu (Daraltılmış Modda Üstte)
        Item {
            visible: root.isCollapsed
            width: parent.width
            height: 36

            AppIconButton {
                anchors.centerIn: parent
                iconName: "fa5s.chevron-right"
                iconSize: 11
                tooltip: "Menüyü Genişlet"
                tooltipPosition: "bottom"
                onClicked: root.isCollapsed = false
            }
        }

        // 2. Navigasyon Listesi
        Flickable {
            width: parent.width
            height: parent.height - 56 - 54 - (root.isCollapsed ? 36 : 0)
            contentHeight: navColumn.implicitHeight + 20
            clip: true

            Column {
                id: navColumn
                width: parent.width
                padding: 8
                spacing: 4

                // Bölüm: Görünümler
                Text {
                    visible: !root.isCollapsed
                    text: "ÇALIŞMA ALANI"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.textMuted
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    topPadding: 6
                    bottomPadding: 4
                }

                // Nav: Vitrin
                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.th-large"
                    title: "Bağlantı Vitrini"
                    badgeText: bridge.stats.total ? bridge.stats.total.toString() : "0"
                    isActive: root.activeNav === "showcase" && root.activeStatusFilter === "ALL" && !root.isFavoriteFilter
                    onClicked: {
                        root.activeStatusFilter = "ALL"
                        root.isFavoriteFilter = false
                        root.filterSelected("ALL", false)
                        root.statusFilterSelected("ALL")
                        root.favoriteFilterSelected(false)
                        root.navSelected("showcase")
                    }
                }

                // Nav: Bilgi Havuzu
                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.quote-right"
                    title: "Bilgi Havuzu"
                    badgeText: (bridge.highlights.length + bridge.vocabulary.length).toString()
                    isActive: root.activeNav === "knowledge"
                    onClicked: root.navSelected("knowledge")
                }

                // Nav: Makale Market
                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.search"
                    title: "Makale Market"
                    isActive: root.activeNav === "articleMarket"
                    onClicked: root.navSelected("articleMarket")
                }

                // Nav: Ayarlar
                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.sliders-h"
                    title: "Ayarlar"
                    isActive: root.activeNav === "settings"
                    onClicked: root.navSelected("settings")
                }

                // Ayraç
                Item {
                    width: parent.width
                    height: 16
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width - 16
                        height: 1
                        color: Theme.borderSubtle
                    }
                }

                // Bölüm: Durum Filtreleri
                Text {
                    visible: !root.isCollapsed
                    text: "DURUMLAR"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.textMuted
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    topPadding: 6
                    bottomPadding: 4
                }

                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.inbox"
                    title: "Gelen Kutusu"
                    badgeText: bridge.stats.inbox ? bridge.stats.inbox.toString() : "0"
                    dotColor: Theme.statusInbox
                    isActive: root.activeNav === "showcase" && root.activeStatusFilter === "INBOX"
                    onClicked: {
                        root.activeStatusFilter = "INBOX"
                        root.isFavoriteFilter = false
                        root.filterSelected("INBOX", false)
                        root.statusFilterSelected("INBOX")
                        root.favoriteFilterSelected(false)
                        root.navSelected("showcase")
                    }
                }

                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.calendar-alt"
                    title: "Planlananlar"
                    badgeText: bridge.stats.planned ? bridge.stats.planned.toString() : "0"
                    dotColor: Theme.statusPlanned
                    isActive: root.activeNav === "showcase" && root.activeStatusFilter === "PLANNED"
                    onClicked: {
                        root.activeStatusFilter = "PLANNED"
                        root.isFavoriteFilter = false
                        root.filterSelected("PLANNED", false)
                        root.statusFilterSelected("PLANNED")
                        root.favoriteFilterSelected(false)
                        root.navSelected("showcase")
                    }
                }

                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.spinner"
                    title: "Devam Edenler"
                    badgeText: bridge.stats.in_progress ? bridge.stats.in_progress.toString() : "0"
                    dotColor: Theme.statusInProgress
                    isActive: root.activeNav === "showcase" && root.activeStatusFilter === "IN_PROGRESS"
                    onClicked: {
                        root.activeStatusFilter = "IN_PROGRESS"
                        root.isFavoriteFilter = false
                        root.filterSelected("IN_PROGRESS", false)
                        root.statusFilterSelected("IN_PROGRESS")
                        root.favoriteFilterSelected(false)
                        root.navSelected("showcase")
                    }
                }

                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.check-circle"
                    title: "Tamamlananlar"
                    badgeText: bridge.stats.completed ? bridge.stats.completed.toString() : "0"
                    dotColor: Theme.statusCompleted
                    isActive: root.activeNav === "showcase" && root.activeStatusFilter === "COMPLETED"
                    onClicked: {
                        root.activeStatusFilter = "COMPLETED"
                        root.isFavoriteFilter = false
                        root.filterSelected("COMPLETED", false)
                        root.statusFilterSelected("COMPLETED")
                        root.favoriteFilterSelected(false)
                        root.navSelected("showcase")
                    }
                }

                // Ayraç
                Item {
                    width: parent.width
                    height: 16
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width - 16
                        height: 1
                        color: Theme.borderSubtle
                    }
                }

                // Favoriler
                SidebarItem {
                    isCollapsed: root.isCollapsed
                    iconName: "fa5s.heart"
                    title: "Favoriler"
                    badgeText: bridge.stats.favorites ? bridge.stats.favorites.toString() : "0"
                    dotColor: Theme.favorite
                    isActive: root.activeNav === "showcase" && root.isFavoriteFilter
                    onClicked: {
                        root.isFavoriteFilter = true
                        root.activeStatusFilter = "ALL"
                        root.filterSelected("ALL", true)
                        root.statusFilterSelected("ALL")
                        root.favoriteFilterSelected(true)
                        root.navSelected("showcase")
                    }
                }
            }
        }

        // 3. Alt Bar: Tema Değiştirme Butonu
        Item {
            width: parent.width
            height: 54

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }

            Rectangle {
                anchors.centerIn: parent
                width: parent.width - 16
                height: 38
                radius: Theme.radiusSm
                color: themeMouse.containsMouse ? Theme.bgHover : "transparent"

                Row {
                    anchors.centerIn: parent
                    spacing: 10

                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: bridge.isDarkTheme ? "fa5s.moon" : "fa5s.sun"
                        size: 15
                        color: Theme.pin
                    }

                    Text {
                        visible: !root.isCollapsed
                        anchors.verticalCenter: parent.verticalCenter
                        text: bridge.isDarkTheme ? "Koyu Tema" : "Açık Tema"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Medium
                        color: Theme.textPrimary
                    }
                }

                MouseArea {
                    id: themeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.toggleTheme()
                }
            }
        }
    }

    // Dahili Sidebar Öğesi Bileşeni
    component SidebarItem : Rectangle {
        property bool isCollapsed: false
        property string iconName: ""
        property string title: ""
        property string badgeText: ""
        property color dotColor: "transparent"
        property bool isActive: false

        signal clicked()

        width: parent.width - 16
        height: 34
        anchors.horizontalCenter: parent.horizontalCenter
        radius: Theme.radiusSm

        color: {
            if (isActive) return Theme.accentSubtle
            if (itemMouse.containsMouse) return Theme.bgHover
            if (isCollapsed) return Theme.bgElevated
            return "transparent"
        }

        border.width: (isActive || isCollapsed) ? 1 : 0
        border.color: isActive ? Theme.accent : Theme.borderSubtle

        Behavior on color { ColorAnimation { duration: Theme.animFast } }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: root.isCollapsed ? (parent.width - 20) / 2 : 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            AppIcon {
                anchors.verticalCenter: parent.verticalCenter
                name: iconName
                size: 14
                color: isActive ? Theme.accentText : (dotColor.a > 0 ? dotColor : Theme.textPrimary)
            }

            Text {
                visible: !root.isCollapsed
                anchors.verticalCenter: parent.verticalCenter
                text: title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: isActive ? Font.DemiBold : Font.Normal
                color: isActive ? Theme.accentText : Theme.textPrimary
            }
        }

        // Sayı Rozeti
        Rectangle {
            visible: !root.isCollapsed && badgeText !== "" && badgeText !== "0"
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: badgeLabel.implicitWidth + 8
            implicitHeight: 18
            radius: Theme.radiusPill
            color: isActive ? Theme.accent : Theme.bgElevated

            Text {
                id: badgeLabel
                anchors.centerIn: parent
                text: badgeText
                font.family: Theme.fontFamily
                font.pixelSize: 10
                font.weight: Font.Bold
                color: isActive ? Theme.textOnAccent : Theme.textMuted
            }
        }

        MouseArea {
            id: itemMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }

        ToolTip {
            visible: isCollapsed && title !== "" && itemMouse.containsMouse
            text: title
            delay: 300
            x: parent.width + 6
            y: (parent.height - height) / 2

            contentItem: Text {
                text: title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textOnAccent
            }

            background: Rectangle {
                color: Theme.tooltipBg
                border.color: Theme.borderStrong
                border.width: 1
                radius: Theme.radiusXs
            }
        }
    }
}
