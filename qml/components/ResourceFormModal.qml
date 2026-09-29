import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    objectName: "resourceFormModal"

    property bool isOpen: false
    property int resourceId: 0
    property string initialUrl: ""
    property string initialTitle: ""
    property int initialCategoryId: 0
    property string initialStatus: "INBOX"
    property int initialPriority: 2
    property var selectedTagIds: []
    property bool isScraping: false

    signal closed()

    anchors.fill: parent
    visible: opacity > 0
    opacity: isOpen ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.animFast } }

    function openForNew() {
        resourceId = 0
        urlInput.text = ""
        titleInput.text = ""
        categoryCombo.currentIndex = 0
        statusCombo.currentIndex = 0
        priorityCombo.currentIndex = 1
        selectedTagIds = []
        isScraping = false
        isOpen = true
    }

    function openForEdit(res) {
        resourceId = res.id
        urlInput.text = res.url || ""
        titleInput.text = res.title || ""
        
        // Kategori index bul
        var catIndex = 0
        for (var i = 0; i < bridge.categories.length; i++) {
            if (bridge.categories[i].id === res.categoryId) {
                catIndex = i + 1
                break
            }
        }
        categoryCombo.currentIndex = catIndex

        // Durum index bul
        var statuses = ["INBOX", "PLANNED", "IN_PROGRESS", "COMPLETED"]
        var sIdx = statuses.indexOf(res.status)
        statusCombo.currentIndex = sIdx >= 0 ? sIdx : 0

        priorityCombo.currentIndex = Math.max(0, Math.min(3, (res.priority || 2) - 1))
        selectedTagIds = res.tags ? res.tags.map(function(t) { return t.id }) : []
        isScraping = false
        isOpen = true
    }

    FileDialog {
        id: pdfFileDialog
        title: "PDF Dosyası Seç"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["PDF dosyaları (*.pdf)"]
        onAccepted: {
            root.importsInFlight = selectedFiles.length
            root.importsSucceeded = 0
            for (const file of selectedFiles)
                bridge.importLocalPdf(file)
        }
    }

    // Kopyalama arka planda: her dosya için bridge.pdfImportFinished(ok) gelir; en az biri başarılıysa kapan.
    property int importsInFlight: 0
    property int importsSucceeded: 0

    Connections {
        target: bridge
        function onPdfImportFinished(ok) {
            if (root.importsInFlight === 0) return  // Sürükle-bırakla gelen içe aktarma: pencereyi etkilemez
            root.importsInFlight--
            if (ok) root.importsSucceeded++
            if (root.importsInFlight === 0 && root.importsSucceeded > 0)
                root.closeModal()
        }
    }

    // Karartma Perdesi
    Rectangle {
        anchors.fill: parent
        color: Theme.overlayBg
        MouseArea {
            anchors.fill: parent
            onClicked: root.closeModal()
        }
    }

    // Modal Pencere Kutusu
    Rectangle {
        id: dialogBox
        width: 520
        implicitHeight: dialogCol.implicitHeight + 40
        anchors.centerIn: parent
        radius: Theme.radiusLg
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: dialogCol
            width: parent.width
            padding: 24
            spacing: 16

            // Başlık & Kapat
            Item {
                width: parent.width - 48
                height: Math.max(titleText.implicitHeight, closeButton.height)

                Text {
                    id: titleText
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.resourceId > 0 ? "Kaynağı Düzenle" : "Yeni Kaynak Ekle"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }

                AppIconButton {
                    id: closeButton
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    iconName: "fa5s.times"
                    iconSize: 13
                    onClicked: root.closeModal()
                }
            }

            Rectangle {
                width: parent.width - 48
                height: 1
                color: Theme.borderSubtle
            }

            // 1. URL ve Otomatik Tarama Butonu
            Column {
                width: parent.width - 48
                spacing: 6

                Text {
                    text: "BAĞLANTI / URL"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }

                Row {
                    width: parent.width
                    spacing: 8

                    Rectangle {
                        width: parent.width - 128
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.bgSurface
                        border.width: 1
                        border.color: urlInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                        TextInput {
                            id: urlInput
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            clip: true

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "https://ornek.com/makale"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                color: Theme.textMuted
                                visible: !urlInput.text && !urlInput.activeFocus
                            }
                        }
                    }

                    AppButton {
                        text: root.isScraping ? "Çekiliyor..." : "Bilgi Çek"
                        iconName: "fa5s.magic"
                        variant: "subtle"
                        implicitHeight: 36
                        enabledState: !root.isScraping && urlInput.text.length > 5
                        onClicked: {
                            root.isScraping = true
                            bridge.scrapeUrl(urlInput.text)
                        }
                    }
                }

                // Yeni kaynakta: bilgisayardan bir veya birden fazla PDF seç (kopyalanıp
                // uygulama depolamasına alınır, native okuyucuda açılır).
                AppButton {
                    visible: root.resourceId === 0
                    text: "Bilgisayardan PDF Yükle"
                    iconName: "fa5s.file-pdf"
                    variant: "subtle"
                    implicitHeight: 32
                    onClicked: pdfFileDialog.open()
                }
            }

            // 2. Başlık
            Column {
                width: parent.width - 48
                spacing: 6

                Text {
                    text: "BAŞLIK *"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }

                Rectangle {
                    width: parent.width
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: titleInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    TextInput {
                        id: titleInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        clip: true

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Kaynak başlığı girin..."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textMuted
                            visible: !titleInput.text && !titleInput.activeFocus
                        }
                    }
                }
            }

            // 3. Kategori & Durum & Öncelik
            Row {
                width: parent.width - 48
                spacing: 12

                // Kategori Seçici
                Column {
                    width: (parent.width - 24) / 3
                    spacing: 6

                    Text {
                        text: "KATEGORİ"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    AppComboBox {
                        id: categoryCombo
                        width: parent.width
                        model: {
                            var list = ["Kategorisiz"]
                            for (var i = 0; i < bridge.categories.length; i++) {
                                list.push(bridge.categories[i].name)
                            }
                            return list
                        }
                    }
                }

                // Durum Seçici
                Column {
                    width: (parent.width - 24) / 3
                    spacing: 6

                    Text {
                        text: "DURUM"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    AppComboBox {
                        id: statusCombo
                        width: parent.width
                        model: ["Gelen Kutusu", "Planlandı", "Devam Eden", "Tamamlandı"]
                    }
                }

                // Öncelik
                Column {
                    width: (parent.width - 24) / 3
                    spacing: 6

                    Text {
                        text: "ÖNCELİK"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: Theme.textMuted
                    }

                    AppComboBox {
                        id: priorityCombo
                        width: parent.width
                        model: ["1 - Düşük", "2 - Normal", "3 - Yüksek", "4 - Acil"]
                    }
                }
            }

            // 4. Butonlar (Vazgeç & Kaydet) - ortalanmış
            Item {
                width: parent.width - 48
                height: actionButtonsRow.implicitHeight

                Row {
                    id: actionButtonsRow
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 10

                    AppButton {
                        text: "Vazgeç"
                        variant: "danger"
                        onClicked: root.closeModal()
                    }

                    AppButton {
                        text: root.resourceId > 0 ? "Güncellemeleri Kaydet" : "Kaydet ve Ekle"
                        iconName: "fa5s.check"
                        variant: "primary"
                        enabledState: titleInput.text.trim().length > 0
                        onClicked: root.submitForm()
                    }
                }
            }
        }
    }

    Connections {
        target: bridge
        function onUrlScraped(metadata) {
            root.isScraping = false
            if (metadata && metadata.title && !titleInput.text) {
                titleInput.text = metadata.title
            }
        }
    }

    function closeModal() {
        isOpen = false
        closed()
    }

    function submitForm() {
        var statuses = ["INBOX", "PLANNED", "IN_PROGRESS", "COMPLETED"]
        var selectedStatus = statuses[statusCombo.currentIndex]

        var catId = 0
        if (categoryCombo.currentIndex > 0 && categoryCombo.currentIndex <= bridge.categories.length) {
            catId = bridge.categories[categoryCombo.currentIndex - 1].id
        }

        var data = {
            "title": titleInput.text.trim(),
            "url": urlInput.text.trim(),
            "category_id": catId,
            "status": selectedStatus,
            "priority": priorityCombo.currentIndex + 1,
            "tag_ids": root.selectedTagIds
        }

        if (root.resourceId > 0) {
            data["id"] = root.resourceId
        }

        bridge.saveResource(data)
        closeModal()
    }
}
