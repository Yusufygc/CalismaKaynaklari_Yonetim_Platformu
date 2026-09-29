import QtQuick
import "../theme"

// Makale Market filtre çubuğu: yıl aralığı, tür, dil, açık erişim, yazar çipi, "Kütüphaneden Öneriler".
// Alanların değerleri burada durur (`filters()`); açık erişim / yazar / öneri modu durumu kökten gelir.
Item {
    id: root

    property bool openAccessOnly: false
    property bool suggestMode: false
    property string authorId: ""
    property string authorName: ""

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

    signal filtersEdited()        // Yıl/tür/dil değişti (aramayı yenile)
    signal openAccessToggled()
    signal authorCleared()
    signal suggestionsToggled()

    width: parent ? parent.width : 0
    height: 48

    // Bu çubuğun sahip olduğu alanlar (root: açık erişim + yazar ekler)
    function filters() {
        return {
            yearFrom: yearFromInput.text.trim(),
            yearTo: yearToInput.text.trim(),
            workType: workTypeOptions[workTypeBox.currentIndex].value,
            language: languageOptions[languageBox.currentIndex].value
        }
    }

    function indexOfValue(options, value) {
        for (let i = 0; i < options.length; i++)
            if (options[i].value === value) return i
        return 0
    }

    // Kayıtlı arama çalıştırılırken alanları onunla eşitle
    function apply(saved) {
        yearFromInput.text = saved.yearFrom || ""
        yearToInput.text = saved.yearTo || ""
        workTypeBox.currentIndex = indexOfValue(workTypeOptions, saved.workType || "")
        languageBox.currentIndex = indexOfValue(languageOptions, saved.language || "")
    }


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
                onEditingFinished: root.filtersEdited()

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
                onEditingFinished: root.filtersEdited()

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
            onActivated: root.filtersEdited()
        }

        AppComboBox {
            id: languageBox
            anchors.verticalCenter: parent.verticalCenter
            width: 130
            implicitHeight: 30
            model: root.languageOptions.map(function(o) { return o.label })
            onActivated: root.filtersEdited()
        }

        AppFilterChip {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.authorId !== ""
            text: "Yazar: " + (root.authorName.length > 16 ? root.authorName.substring(0, 15) + "…" : root.authorName) + "  ✕"
            iconName: "fa5s.user"
            isSelected: true
            onClicked: root.authorCleared()
        }

        AppFilterChip {
            anchors.verticalCenter: parent.verticalCenter
            text: "Sadece açık erişim"
            iconName: "fa5s.unlock"
            isSelected: root.openAccessOnly
            onClicked: root.openAccessToggled()
        }
    }

    AppFilterChip {
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        text: "Kütüphaneden Öneriler"
        iconName: "fa5s.lightbulb"
        isSelected: root.suggestMode
        onClicked: root.suggestionsToggled()
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.borderSubtle
    }
}
