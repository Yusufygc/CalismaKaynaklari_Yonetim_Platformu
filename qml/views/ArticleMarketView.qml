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
    readonly property var activeMeta: bridge.market.marketMeta[activeKind]
    property bool openAccessOnly: false
    property bool suggestMode: false   // "Kütüphaneden Öneriler" görünümü
    property string authorId: ""       // Yazar filtresi (kartta yazar adına tıklanınca)
    property string authorName: ""
    // Toplu seçim: anahtar -> makale (JS nesnesi; değişince yeniden atanır ki bağlamalar tazelensin)
    property var selection: ({})
    // Çalışan kayıtlı arama (varsa): koleksiyon etiketi ipucu için
    readonly property var activeSaved: {
        const list = bridge.market.savedSearches
        for (let i = 0; i < list.length; i++)
            if (list[i].id === bridge.market.activeSavedSearchId) return list[i]
        return null
    }
    readonly property int selectionCount: Object.keys(selection).length

    onActiveTabChanged: resultsList.restorePending = false

    // Arama bağlamı: filtre çubuğunun alanları + kökün tuttuğu açık erişim / yazar durumu
    function currentFilters() {
        return Object.assign({}, filterBar.filters(), {
            openAccess: root.openAccessOnly,
            authorId: root.authorId,
            authorName: root.authorName
        })
    }

    // Kayıtlı arama çalıştırılırken form alanlarını onunla eşitle (bridge.market.savedSearchApplied)
    function applySavedSearch(topic, filters) {
        searchBar.text = topic
        filterBar.apply(filters)
        root.openAccessOnly = !!filters.openAccess
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
        if (root.suggestMode) return bridge.market.marketSuggestions.items
        return bridge.market.marketResults[root.activeKind]
    }

    // Dışa aktarılacaklar: seçim varsa seçilenler, yoksa görünen tüm liste
    function exportPapers() {
        return root.selectionCount > 0 ? Object.values(root.selection) : root.bridgeList()
    }

    function saveSelected() {
        bridge.market.saveMarketResults(Object.values(root.selection))
        root.clearSelection()
    }

    function runSearch() {
        if (searchBar.text.trim().length === 0 && root.authorId === "") return
        root.suggestMode = false
        root.hasSearched = true
        root.clearSelection()
        bridge.market.searchArticles(searchBar.text.trim(), root.currentFilters())
    }

    function searchAuthor(id, name) {
        root.authorId = id
        root.authorName = name
        searchBar.text = ""
        root.runSearch()
    }

    function clearAuthor() {
        root.authorId = ""
        root.authorName = ""
        if (searchBar.text.trim().length > 0) {
            root.runSearch()
        } else {
            root.hasSearched = false
            bridge.market.resetMarketResults()
        }
    }

    function toggleSuggestions() {
        root.suggestMode = !root.suggestMode
        if (root.suggestMode) bridge.market.loadLibrarySuggestions()
    }

    // Filtre değişince, önceden arama yapılmışsa sonuçları yenile.
    function refreshIfSearched() {
        if (root.hasSearched) root.runSearch()
    }

    Component.onCompleted: bridge.market.checkSavedSearches()
    onVisibleChanged: if (visible) bridge.market.checkSavedSearches()

    Connections {
        target: bridge.market
        function onSavedSearchApplied(topic, filters) { root.applySavedSearch(topic, filters) }
    }

    // Aramayı kaydet: isteğe bağlı koleksiyon etiketi
    SaveSearchPopup {
        id: saveSearchPopup
        anchors.centerIn: Overlay.overlay
        onSaveRequested: (tag) => bridge.market.saveSearch(searchBar.text.trim(), root.currentFilters(), tag)
    }

    FileDialog {
        id: bibtexDialog
        title: "Sonuçları BibTeX Olarak Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["BibTeX (*.bib)"]
        defaultSuffix: "bib"
        onAccepted: bridge.market.exportMarketResults("bibtex", selectedFile, root.exportPapers())
    }

    FileDialog {
        id: csvDialog
        title: "Sonuçları CSV Olarak Dışa Aktar"
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV (*.csv)"]
        defaultSuffix: "csv"
        onAccepted: bridge.market.exportMarketResults("csv", selectedFile, root.exportPapers())
    }

    Column {
        anchors.fill: parent
        spacing: 0

        MarketSearchBar {
            id: searchBar
            activeTab: root.activeTab
            onSearchRequested: root.runSearch()
            onTabSelected: (index) => {
                root.suggestMode = false
                root.activeTab = index
            }
        }

        MarketFilterBar {
            id: filterBar
            openAccessOnly: root.openAccessOnly
            suggestMode: root.suggestMode
            authorId: root.authorId
            authorName: root.authorName
            onFiltersEdited: root.refreshIfSearched()
            onOpenAccessToggled: {
                root.openAccessOnly = !root.openAccessOnly
                root.refreshIfSearched()
            }
            onAuthorCleared: root.clearAuthor()
            onSuggestionsToggled: root.toggleSuggestions()
        }

        SavedSearchBar { id: savedBar }

        MarketResultsToolbar {
            id: resultsToolbar
            visible: bridge.market.marketSearchLoading === false && root.bridgeList().length > 0
            selectionCount: root.selectionCount
            canSaveSearch: root.hasSearched && !root.suggestMode && bridge.market.activeSavedSearchId === 0
            collectionTag: root.activeSaved ? root.activeSaved.tag : ""
            countLabel: root.selectionCount > 0 ? root.selectionCount + " seçili"
                        : (bridge.market.marketMeta[root.activeKind].total > 0 && !root.suggestMode
                           ? bridge.market.marketMeta[root.activeKind].total + " sonuç" : "")
            onSelectAllRequested: root.selectAllVisible()
            onClearSelectionRequested: root.clearSelection()
            onSaveSearchRequested: saveSearchPopup.open()
            onBibtexRequested: bibtexDialog.open()
            onCsvRequested: csvDialog.open()
            onSaveSelectedRequested: root.saveSelected()
        }

            // 5. İçerik: 3 sonuç listesi
            Item {
                width: parent.width
                height: parent.height - searchBar.height - filterBar.height - savedBar.height - resultsToolbar.height

                property var currentList: {
                    if (root.suggestMode) return bridge.market.marketSuggestions.items
                    if (root.activeTab === 0) return bridge.market.marketResults.recent
                    if (root.activeTab === 1) return bridge.market.marketResults.popular
                    return bridge.market.marketResults.cited
                }

                // Boş / hata durumları (z: sonradan tanımlanan, ekranı kaplayan ListView tıklamaları yutmasın)
                Column {
                    anchors.centerIn: parent
                    spacing: 8
                    z: 1
                    visible: !bridge.market.marketSearchLoading && !bridge.market.marketSuggestions.loading
                             && parent.currentList.length === 0

                    readonly property var suggestions: bridge.market.marketSuggestions
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
                        onClicked: root.suggestMode ? bridge.market.loadLibrarySuggestions() : root.runSearch()
                    }
                }

                BusyIndicator {
                    anchors.centerIn: parent
                    running: visible
                    visible: root.suggestMode && bridge.market.marketSuggestions.loading
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
                        onSaveRequested: bridge.market.saveMarketResult(modelData)
                        onSaveForLaterRequested: bridge.market.saveMarketResultForLater(modelData)
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
                                    bridge.market.loadMoreArticles(root.activeKind)
                                }
                            }
                        }
                    }

                    ScrollBar.vertical: ScrollBar { active: true }
                }
            }
    }
}
