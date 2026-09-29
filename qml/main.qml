import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "theme"
import "components"
import "views"

ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    minimumWidth: 960
    minimumHeight: 600
    title: "PKM — Kaynak Yönetim Platformu"
    color: Theme.bgBase

    // Bridge'den tema durumunu reaktif senkronize et
    Connections {
        target: bridge
        function onIsDarkThemeChanged(isDark) {
            Theme.isDark = isDark
        }
    }

    Component.onCompleted: {
        Theme.isDark = bridge.isDarkTheme

        // Pencere konumu hic kaydedilmiyor (QSettings yok) -- her acilis sifirdan.
        // Qt/Windows'un varsayilan yerlestirmesi coklu-ekran/DPI degisikliginde
        // ekran disina dusebiliyor; acilista birincil ekrana gore elle ortala.
        x = Screen.width / 2 - width / 2
        y = Screen.height / 2 - height / 2
    }

    // Klavye Kısayolları
    Shortcut {
        sequence: "Esc"
        onActivated: {
            if (formModal.isOpen) {
                formModal.closeModal()
            } else if (bridge.library.isDrawerOpen) {
                bridge.library.closeDrawer()
            }
        }
    }

    Item {
        anchors.fill: parent

        // Ana Gövde Düzeni (Sol Sidebar + Çalışma Alanı)
        Row {
            anchors.fill: parent
            spacing: 0

            // 1. Sol Sidebar
            AppSidebar {
                id: sidebar
                height: parent.height
                onNavSelected: function(viewName) {
                    bridge.setCurrentView(viewName)
                }
                onFilterSelected: function(statusKey, isFav) {
                    showcaseView.selectedStatus = statusKey
                    showcaseView.favoriteOnly = isFav
                    showcaseView.updateFilters()
                }
            }

            // 2. Ana Çalışma Alanı (Workspace)
            Item {
                id: workspace
                width: parent.width - sidebar.width
                height: parent.height
                clip: true

                // Sayfa 1: Bağlantı Vitrini
                ShowcaseView {
                    id: showcaseView
                    anchors.fill: parent
                    visible: bridge.currentView === "showcase"
                    onNewResourceRequested: formModal.openForNew()
                }

                // Sayfa 2: Okuyucu Görünümü
                ReaderView {
                    id: readerView
                    anchors.fill: parent
                    visible: bridge.currentView === "reader"
                }

                // Sayfa 3: Bilgi Havuzu
                KnowledgePoolView {
                    id: knowledgeView
                    anchors.fill: parent
                    visible: bridge.currentView === "knowledge"
                }

                // Sayfa 4: Ayarlar
                SettingsView {
                    id: settingsView
                    anchors.fill: parent
                    visible: bridge.currentView === "settings"
                }

                // Sayfa 5: Makale Market
                ArticleMarketView {
                    id: articleMarketView
                    anchors.fill: parent
                    visible: bridge.currentView === "articleMarket"
                }

                // Sayfa 6: Native PDF Okuyucu
                PdfReaderView {
                    id: pdfReaderView
                    anchors.fill: parent
                    visible: bridge.currentView === "pdfReader"
                }
            }
        }

        // 3. Sağdan Açılan Inspector Drawer (Detay & Notlar)
        InspectorDrawer {
            id: inspectorDrawer
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            onEditRequested: function(res) {
                formModal.openForEdit(res)
            }
        }

        // 4. Yeni / Düzenle Kaynak Modalı
        ResourceFormModal {
            id: formModal
        }

        // 5. Toast Bildirim Rozeti (Sağ Altta Modern Bildirim)
        Rectangle {
            id: toast
            property string message: ""
            property string toastType: "info"

            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 24
            z: 9999
            implicitWidth: toastRow.implicitWidth + 24
            implicitHeight: 38
            radius: Theme.radiusSm
            color: Theme.tooltipBg
            border.width: 1
            border.color: toastType === "error" ? Theme.danger : Theme.accent
            opacity: 0

            Behavior on opacity { NumberAnimation { duration: Theme.animFast } }

            Row {
                id: toastRow
                anchors.centerIn: parent
                spacing: 8

                AppIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    name: toast.toastType === "error" ? "fa5s.exclamation-circle" : "fa5s.check-circle"
                    size: 14
                    color: toast.toastType === "error" ? Theme.danger : Theme.accent
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: toast.message
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    color: Theme.textOnAccent
                }
            }

            Timer {
                id: toastTimer
                interval: 3000
                onTriggered: toast.opacity = 0
            }

            function show(type, msg) {
                toastType = type
                message = msg
                opacity = 1
                toastTimer.restart()
            }
        }

        Connections {
            target: bridge
            function onNotificationEmitted(type, msg) {
                toast.show(type, msg)
            }
        }

        // 6. Yerel PDF Sürükle-Bırak
        DropArea {
            id: pdfDropArea
            anchors.fill: parent
            onDropped: function(drop) {
                if (!drop.hasUrls) return
                for (var i = 0; i < drop.urls.length; i++) {
                    var u = drop.urls[i].toString()
                    if (u.toLowerCase().endsWith(".pdf")) {
                        bridge.library.importLocalPdf(u)
                    }
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            visible: pdfDropArea.containsDrag
            z: 1000
            color: Theme.accentSubtle
            opacity: 0.94
            border.width: 2
            border.color: Theme.accent

            Column {
                anchors.centerIn: parent
                spacing: 12

                AppIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    name: "fa5s.file-pdf"
                    size: 40
                    color: Theme.accent
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "PDF'i buraya bırak"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.DemiBold
                    color: Theme.accentText
                }
            }
        }
    }
}
