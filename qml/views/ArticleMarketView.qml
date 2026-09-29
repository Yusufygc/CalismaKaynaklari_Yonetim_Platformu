import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../theme"

Item {
    id: root
    objectName: "articleMarketView"

    property int activeTab: 0 // 0: En Güncel, 1: En Popüler, 2: En Çok Atıf Alan
    property bool hasSearched: false

    readonly property var tabKinds: ["recent", "popular", "cited"]
    readonly property string activeKind: tabKinds[activeTab]
    readonly property var activeMeta: bridge.marketMeta[activeKind]
    readonly property var workTypeOptions: [
        { label: "Tüm türler", value: "" },
        { label: "Makale", value: "article" },
        { label: "Derleme", value: "review" },
        { label: "Ön baskı", value: "preprint" }
    ]
    readonly property var languageOptions: [
        { label: "Tüm diller", value: "" },
        { label: "Türkçe", value: "tr" },
        { label: "İngilizce", value: "en" }
    ]
    property bool openAccessOnly: false
    property bool suggestMode: false   // "Kütüphaneden Öneriler" görünümü
    property string authorId: ""       // Yazar filtresi (kartta yazar adına tıklanınca)
    property string authorName: ""
    // Toplu seçim: anahtar -> makale (JS nesnesi; değişince yeniden atanır ki bağlamalar tazelensin)
    property var selection: ({})
    // Çalışan kayıtlı arama (varsa): koleksiyon etiketi ipucu için
    readonly property var activeSaved: {
        const list = bridge.savedSearches
        for (let i = 0; i < list.length; i++)
            if (list[i].id === bridge.activeSavedSearchId) return list[i]
        return null
    }
    readonly property int selectionCount: Object.keys(selection).length

    onActiveTabChanged: resultsList.restorePending = false

    function currentFilters() {
        return {
            yearFrom: yearFromInput.text.trim(),
            yearTo: yearToInput.text.trim(),
            openAccess: root.openAccessOnly,
            workType: workTypeOptions[workTypeBox.currentIndex].value,
            language: languageOptions[languageBox.currentIndex].value,
            authorId: root.authorId,
            authorName: root.authorName
        }
    }

    function indexOfValue(options, value) {
        for (let i = 0; i < options.length; i++)
            if (options[i].value === value) return i
        return 0
    }

    // Kayıtlı arama çalıştırılırken form alanlarını onunla eşitle (bridge.savedSearchApplied)
    function applySavedSearch(topic, filters) {
        topicInput.text = topic
        yearFromInput.text = filters.yearFrom || ""
        yearToInput.text = filters.yearTo || ""
        root.openAccessOnly = !!filters.openAccess
        workTypeBox.currentIndex = root.indexOfValue(root.workTypeOptions, filters.workType || "")
        languageBox.currentIndex = root.indexOfValue(root.languageOptions, filters.language || "")
        root.authorId = filters.authorId || ""
        root.authorName = filters.authorName || ""
        root.suggestMode = false
        root.hasSearched = true
        root.clearSelection()
    }

    function paperKey(paper) {
        return paper.openalexId || paper.doi || paper.url || paper.title
    }

    function toggleSelected(paper) {
        const next = Object.assign({}, root.selection)
        const key = root.paperKey(paper)
        if (next[key] !== undefined) delete next[key]
        else next[key] = paper
        root.selection = next
    }

    function selectAllVisible() {
        const next = Object.assign({}, root.selection)
        const list = bridgeList()
        for (let i = 0; i < list.length; i++) {
            if (list[i].libraryResourceId === 0) next[root.paperKey(list[i])] = list[i]
        }
        root.selection = next
    }

    function clearSelection() {
        root.selection = ({})
    }

    // Görünen liste (öneri modunda öneriler, aksi halde etkin sekme)
    function bridgeList() {
        if (root.suggestMode) return bridge.marketSuggestions.items
        return bridge.marketResults[root.activeKind]
    }

    // Dışa aktarılacaklar: seçim varsa seçilenler, yoksa görünen tüm liste
    function exportPapers() {
        return root.selectionCount > 0 ? Object.values(root.selection) : root.bridgeList()
    }

    function saveSelected() {
        bridge.saveMarketResults(Object.values(root.selection))
        root.clearSelection()
    }

    function runSearch() {
        if (topicInput.text.trim().length === 0 && root.authorId === "") return
        root.suggestMode = false
        root.hasSearched = true
        root.clearSelection()
        bridge.searchArticles(topicInput.text.trim(), root.currentFilters())
    }

    function searchAuthor(id, name) {
        root.authorId = id
        root.authorName = name
        topicInput.text = ""
        root.runSearch()
    }

    function clearAuthor() {
        root.authorId = ""
        root.authorName = ""
        if (topicInput.text.trim().length > 0) {
            root.runSearch()
        } else {
            root.hasSearched = false
            bridge.resetMarketResults()
        }
    }

    function toggleSuggestions() {
        root.suggestMode = !root.suggestMode
        if (root.suggestMode) bridge.loadLibrarySuggestions()
    }

    // Filtre değişince, önceden arama yapılmışsa sonuçları yenile.
    function refreshIfSearched() {
        if (root.hasSearched) root.runSearch()
    }

    Component.onCompleted: bridge.checkSavedSearches()
    onVisibleChanged: if (visible) bridge.checkSavedSearches()

    Connections {
        target: bridge
        function onSavedSearchApplied(topic, filters) { root.applySavedSearch(topic, filters) }
    }

    // Aramayı kaydet: isteğe bağlı koleksiyon etiketi
    Popup {
        id: saveSearchPopup
        anchors.centerIn: Overlay.overlay
        width: 380
        padding: 20
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onOpened: {
            tagInput.text = ""
            tagInput.forceActiveFocus()
        }

        background: Rectangle {
            color: Theme.popoverBg
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderStrong
        }

        contentItem: Column {
            spacing: 12

            Text {
                text: "Aramayı Kaydet"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Yeni yayın çıkınca kayıtlı aramanda \"yeni\" rozeti görürsün. İstersen bu aramadan kaydettiğin makalelere otomatik bir etiket (koleksiyon) eklenir."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
            }

            Rectangle {
                width: parent.width
                height: 34
                radius: Theme.radiusSm
                color: Theme.bgSurface
                border.width: 1
                border.color: tagInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                TextInput {
                    id: tagInput
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    clip: true
                    onAccepted: saveSearchButton.clicked()

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Koleksiyon etiketi (isteğe bağlı)"
                        font: parent.font
                        color: Theme.textMuted
                        visible: !parent.text
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                AppButton {
                    text: "Vazgeç"
                    variant: "ghost"
                    onClicked: saveSearchPopup.close()
                }

                AppButton {
                    id: saveSearchButton
                    text: "Kaydet"
                    variant: "primary"
                    onClicked: {
                        bridge.saveSearch(topicInput.text.trim(), root.currentFilters(), tagInput.text.trim())
                        saveSearchPopup.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: bibtexDialog
        title: "Sonuçları BibTeX Olarak Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["BibTeX (*.bib)"]
        defaultSuffix: "bib"
        onAccepted: bridge.exportMarketResults("bibtex", selectedFile, root.exportPapers())
    }

    FileDialog {
        id: csvDialog
        title: "Sonuçları CSV Olarak Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV (*.csv)"]
        defaultSuffix: "csv"
        onAccepted: bridge.exportMarketResults("csv", selectedFile, root.exportPapers())
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // 1. Üst Bar: Arama + Sekmeler
        Item {
            width: parent.width
            height: 64

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16

                // Konu Arama Kutusu (AppSearchBar YENİDEN KULLANILMIYOR:
                // o bileşen her tuş vuruşunda searchChanged fırlatıyor, burada
                // uzak bir API'ye (rate-limitli) sadece Enter/Ara ile gidilmeli.)
                Rectangle {
                    id: searchBox
                    anchors.verticalCenter: parent.verticalCenter
                    width: 320
                    height: 36
                    radius: Theme.radiusSm
                    color: topicInput.activeFocus ? Theme.bgSurface : Theme.bgElevated
                    border.width: 1
                    border.color: topicInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 8
                        spacing: 8

                        AppIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "fa5s.search"
                            size: 13
                            color: topicInput.activeFocus ? Theme.accent : Theme.textMuted
                        }

                        TextInput {
                            id: topicInput
                        objectName: "topicInput"
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 24
                            clip: true
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            selectionColor: Theme.accentSubtle
                            selectedTextColor: Theme.textPrimary
                            onAccepted: {
                                historyPopup.close()
                                root.runSearch()
                            }
                            onActiveFocusChanged: {
                                if (activeFocus && text.length === 0 && bridge.marketSearchHistory.length > 0)
                                    historyPopup.open()
                            }
                            onTextChanged: if (text.length > 0) historyPopup.close()

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "Bir konu ara (örn. transformer neural network)..."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                color: Theme.textMuted
                                visible: !topicInput.text && !topicInput.activeFocus
                            }
                        }
                    }

                    // Son aramalar (oturum boyunca)
                    Popup {
                        id: historyPopup
                        y: searchBox.height + 4
                        width: searchBox.width
                        padding: 4
                        focus: false
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                        background: Rectangle {
                            color: Theme.bgElevated
                            radius: Theme.radiusSm
                            border.width: 1
                            border.color: Theme.borderStrong
                        }

                        contentItem: Column {
                            spacing: 2

                            Item {
                                width: parent.width
                                height: 24

                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Son aramalar"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Temizle"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.accentText

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            bridge.clearMarketHistory()
                                            historyPopup.close()
                                        }
                                    }
                                }
                            }

                            Repeater {
                                model: bridge.marketSearchHistory

                                delegate: Rectangle {
                                    required property string modelData
                                    width: parent.width
                                    height: 30
                                    radius: Theme.radiusXs
                                    color: historyMouse.containsMouse ? Theme.bgHover : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: parent.modelData
                                        elide: Text.ElideRight
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        color: Theme.textPrimary
                                    }

                                    MouseArea {
                                        id: historyMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            topicInput.text = parent.modelData
                                            historyPopup.close()
                                            root.runSearch()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Ara"
                    iconName: "fa5s.search"
                    variant: "primary"
                    enabledState: !bridge.marketSearchLoading
                    onClicked: root.runSearch()
                }

                BusyIndicator {
                    anchors.verticalCenter: parent.verticalCenter
                    running: bridge.marketSearchLoading
                    visible: bridge.marketSearchLoading
                    width: 24
                    height: 24
                }

            }

            // Sekme Butonları (Pill Bar) — 3 segment, sağa hizalı
            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                width: 380
                height: 36
                radius: Theme.radiusSm
                color: Theme.bgElevated
                border.width: 1
                border.color: Theme.borderSubtle

                Row {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 4

                    Repeater {
                        model: [
                            { icon: "fa5s.clock", label: "En Güncel" },
                            { icon: "fa5s.fire", label: "En Popüler" },
                            { icon: "fa5s.quote-right", label: "En Çok Atıf Alan" }
                        ]

                        Rectangle {
                            width: (380 - 6 - 8) / 3
                            height: 30
                            radius: Theme.radiusXs
                            color: root.activeTab === index ? Theme.accentSubtle : "transparent"
                            border.width: root.activeTab === index ? 1 : 0
                            border.color: Theme.accent

                            Row {
                                anchors.centerIn: parent
                                spacing: 6
                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: modelData.icon
                                    size: 11
                                    color: root.activeTab === index ? Theme.accentText : Theme.textSecondary
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: root.activeTab === index ? Font.DemiBold : Font.Normal
                                    color: root.activeTab === index ? Theme.accentText : Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.suggestMode = false
                                    root.activeTab = index
                                }
                            }
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

        // 2. Filtre çubuğu: yıl aralığı, tür, dil, açık erişim
        Item {
            id: filterBar
            width: parent.width
            height: 48

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Yıl"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    height: 30
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: yearFromInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    TextInput {
                        id: yearFromInput
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        maximumLength: 4
                        inputMethodHints: Qt.ImhDigitsOnly
                        validator: IntValidator { bottom: 1000; top: 3000 }
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        onEditingFinished: root.refreshIfSearched()

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "başlangıç"
                            font: parent.font
                            color: Theme.textMuted
                            visible: !parent.text && !parent.activeFocus
                        }
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "–"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    height: 30
                    radius: Theme.radiusSm
                    color: Theme.bgSurface
                    border.width: 1
                    border.color: yearToInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

                    TextInput {
                        id: yearToInput
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        maximumLength: 4
                        inputMethodHints: Qt.ImhDigitsOnly
                        validator: IntValidator { bottom: 1000; top: 3000 }
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        onEditingFinished: root.refreshIfSearched()

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "bitiş"
                            font: parent.font
                            color: Theme.textMuted
                            visible: !parent.text && !parent.activeFocus
                        }
                    }
                }

                AppComboBox {
                    id: workTypeBox
                    anchors.verticalCenter: parent.verticalCenter
                    width: 130
                    implicitHeight: 30
                    model: root.workTypeOptions.map(function(o) { return o.label })
                    onActivated: root.refreshIfSearched()
                }

                AppComboBox {
                    id: languageBox
                    anchors.verticalCenter: parent.verticalCenter
                    width: 130
                    implicitHeight: 30
                    model: root.languageOptions.map(function(o) { return o.label })
                    onActivated: root.refreshIfSearched()
                }

                AppFilterChip {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.authorId !== ""
                    text: "Yazar: " + (root.authorName.length > 16 ? root.authorName.substring(0, 15) + "…" : root.authorName) + "  ✕"
                    iconName: "fa5s.user"
                    isSelected: true
                    onClicked: root.clearAuthor()
                }

                AppFilterChip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Sadece açık erişim"
                    iconName: "fa5s.unlock"
                    isSelected: root.openAccessOnly
                    onClicked: {
                        root.openAccessOnly = !root.openAccessOnly
                        root.refreshIfSearched()
                    }
                }
            }

            AppFilterChip {
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                text: "Kütüphaneden Öneriler"
                iconName: "fa5s.lightbulb"
                isSelected: root.suggestMode
                onClicked: root.toggleSuggestions()
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // 3. Kayıtlı aramalar (yeni yayın rozetiyle)
        Item {
            id: savedBar
            width: parent.width
            height: visible ? 44 : 0
            visible: bridge.savedSearches.length > 0

            Text {
                id: savedLabel
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                text: "Kayıtlı aramalar"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }

            Flickable {
                anchors.left: savedLabel.right
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                height: 30
                contentWidth: savedRow.implicitWidth
                contentHeight: height
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Row {
                    id: savedRow
                    spacing: 8

                    Repeater {
                        model: bridge.savedSearches

                        delegate: Row {
                            required property var modelData
                            spacing: 2

                            AppFilterChip {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.label + (modelData.newCount > 0 ? "  ·  " + modelData.newCount + " yeni" : "")
                                iconName: "fa5s.bookmark"
                                dotColor: modelData.newCount > 0 ? Theme.statusInProgress : "transparent"
                                isSelected: bridge.activeSavedSearchId === modelData.id
                                onClicked: bridge.runSavedSearch(modelData.id)
                            }

                            AppIconButton {
                                anchors.verticalCenter: parent.verticalCenter
                                iconName: "fa5s.times"
                                iconSize: 10
                                tooltip: "Kayıtlı aramayı sil"
                                onClicked: bridge.deleteSavedSearch(modelData.id)
                            }
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

        // 4. Sonuç araç çubuğu: toplu seçim, toplu kaydet, dışa aktar
        Item {
            id: resultsToolbar
            width: parent.width
            height: visible ? 44 : 0
            visible: bridge.marketSearchLoading === false && root.bridgeList().length > 0

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Tümünü seç"
                    variant: "ghost"
                    implicitHeight: 28
                    onClicked: root.selectAllVisible()
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.selectionCount > 0
                    text: "Seçimi temizle"
                    variant: "ghost"
                    implicitHeight: 28
                    onClicked: root.clearSelection()
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.hasSearched && !root.suggestMode && bridge.activeSavedSearchId === 0
                    text: "Aramayı kaydet"
                    iconName: "fa5s.bookmark"
                    variant: "ghost"
                    implicitHeight: 28
                    onClicked: saveSearchPopup.open()
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.activeSaved !== null && root.activeSaved.tag !== ""
                    text: "Kaydedilenler #" + (root.activeSaved ? root.activeSaved.tag : "") + " etiketiyle eklenir"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.accentText
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.selectionCount > 0 ? root.selectionCount + " seçili"
                          : bridge.marketMeta[root.activeKind].total > 0 && !root.suggestMode
                            ? bridge.marketMeta[root.activeKind].total + " sonuç" : ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "BibTeX"
                    iconName: "fa5s.file-export"
                    variant: "subtle"
                    implicitHeight: 28
                    onClicked: bibtexDialog.open()
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "CSV"
                    iconName: "fa5s.file-csv"
                    variant: "subtle"
                    implicitHeight: 28
                    onClicked: csvDialog.open()
                }

                AppButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Seçilenleri Kaydet (" + root.selectionCount + ")"
                    iconName: "fa5s.plus"
                    variant: "primary"
                    implicitHeight: 28
                    enabledState: root.selectionCount > 0
                    onClicked: root.saveSelected()
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.borderSubtle
            }
        }

        // 5. İçerik: 3 sonuç listesi
        Item {
            width: parent.width
            height: parent.height - 64 - filterBar.height - savedBar.height - resultsToolbar.height

            property var currentList: {
                if (root.suggestMode) return bridge.marketSuggestions.items
                if (root.activeTab === 0) return bridge.marketResults.recent
                if (root.activeTab === 1) return bridge.marketResults.popular
                return bridge.marketResults.cited
            }

            // Boş / hata durumları (z: sonradan tanımlanan, ekranı kaplayan ListView tıklamaları yutmasın)
            Column {
                anchors.centerIn: parent
                spacing: 8
                z: 1
                visible: !bridge.marketSearchLoading && !bridge.marketSuggestions.loading
                         && parent.currentList.length === 0

                readonly property var suggestions: bridge.marketSuggestions
                readonly property bool failed: root.suggestMode ? suggestions.error !== ""
                                               : (root.hasSearched && root.activeMeta.error !== "")

                AppIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    name: parent.failed ? "fa5s.exclamation-triangle"
                          : (root.hasSearched ? "fa5s.folder-open" : "fa5s.search")
                    size: 28
                    color: parent.failed ? Theme.dangerText : Theme.textMuted
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.suggestMode
                          ? (parent.failed ? "Öneriler alınamadı. Bağlantını kontrol edip tekrar dene."
                             : (parent.suggestions.sourceCount === 0
                                ? "Kütüphanende OpenAlex kaydı olan makale yok. Market'ten kaydet ya da okuyucuda OpenAlex'ten Getir'i kullan."
                                : "Ortak referans bulunamadı."))
                          : (parent.failed ? "Sonuçlar alınamadı. Bağlantını kontrol edip tekrar dene."
                             : (root.hasSearched ? "Sonuç bulunamadı." : "Bir konu arayarak makale keşfetmeye başlayın."))
                    width: Math.min(implicitWidth, 560)
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: parent.failed ? Theme.dangerText : Theme.textMuted
                }

                AppButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: parent.failed
                    text: "Tekrar dene"
                    iconName: "fa5s.redo"
                    variant: "subtle"
                    onClicked: root.suggestMode ? bridge.loadLibrarySuggestions() : root.runSearch()
                }
            }

            BusyIndicator {
                anchors.centerIn: parent
                running: visible
                visible: root.suggestMode && bridge.marketSuggestions.loading
            }

            ListView {
                id: resultsList
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                clip: true
                model: parent.currentList

                // "Daha fazla yükle" listeyi yeniden atar (ListView başa sarar) — konumu koru.
                property real restoreY: 0
                property bool restorePending: false
                onCountChanged: {
                    if (!restorePending) return
                    restorePending = false
                    Qt.callLater(function() {
                        resultsList.contentY = Math.min(resultsList.restoreY,
                                                        Math.max(0, resultsList.contentHeight - resultsList.height))
                    })
                }

                delegate: PaperCard {
                    required property var modelData
                    width: resultsList.width - 24
                    paper: modelData
                    selectable: true
                    selected: root.selection[root.paperKey(modelData)] !== undefined
                    onSelectionToggled: root.toggleSelected(modelData)
                    onSaveRequested: bridge.saveMarketResult(modelData)
                    onSaveForLaterRequested: bridge.saveMarketResultForLater(modelData)
                    onAuthorRequested: (id, name) => root.searchAuthor(id, name)
                }

                footer: Item {
                    width: resultsList.width - 24
                    height: !root.suggestMode && (root.activeMeta.hasMore || root.activeMeta.error !== "") && resultsList.count > 0 ? 56 : 0
                    visible: height > 0

                    Column {
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            visible: root.activeMeta.error !== ""
                            text: "Sonraki sayfa alınamadı."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.dangerText
                        }

                        AppButton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: root.activeMeta.loadingMore ? "Yükleniyor..."
                                  : (root.activeMeta.error !== "" ? "Tekrar dene"
                                     : "Daha fazla yükle (" + resultsList.count + " / " + root.activeMeta.total + ")")
                            variant: "subtle"
                            enabledState: !root.activeMeta.loadingMore
                            onClicked: {
                                resultsList.restoreY = resultsList.contentY
                                resultsList.restorePending = true
                                bridge.loadMoreArticles(root.activeKind)
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar { active: true }
            }
        }
    }
}
