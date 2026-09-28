import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
    }

    // Klavye Kısayolları
    Shortcut {
        sequence: "Esc"
        onActivated: {
            if (formModal.isOpen) {
                formModal.closeModal()
            } else if (bridge.isDrawerOpen) {
                bridge.closeDrawer()
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
                onStatusFilterSelected: function(statusKey) {
                    showcaseView.selectedStatus = statusKey
                    showcaseView.updateFilters()
                }
                onFavoriteFilterSelected: function(isFav) {
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
    }
}
