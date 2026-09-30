import QtQuick
import "../theme"

// Ayarlar > Kategori satırı: görünüm modu (renk noktası, ad, kaynak sayısı, düzenle/sil) ve
// satır içi düzenleme modu (ad + renk paleti + Kaydet/İptal).
// Başarılı kayıtta köprü `categories` listesini yeniler, satır yeniden oluşur ve görünüm moduna döner;
// hata (yinelenen ad vb.) durumunda düzenleme açık kalır ve hata bildirimi köprüden gelir.
Rectangle {
    id: root

    property var category: ({})
    property bool editing: false
    property string draftColor: ""
    readonly property string categoryColor: category.color_hex || Theme.fallbackCategoryColor

    signal deleteRequested(int categoryId, string categoryName)

    function startEdit() {
        nameInput.text = category.name
        draftColor = categoryColor
        editing = true
        nameInput.forceActiveFocus()
        nameInput.selectAll()
    }

    function cancelEdit() {
        editing = false
    }

    function save() {
        const name = nameInput.text.trim()
        if (name.length === 0)
            return
        const unchanged = name === category.name && draftColor.toLowerCase() === categoryColor.toLowerCase()
        if (unchanged) {
            cancelEdit()
            return
        }
        bridge.settings.updateCategory(category.id, name, draftColor, category.icon || "")
    }

    width: parent ? parent.width : 0
    implicitHeight: editing ? editColumn.implicitHeight + 24 : 44
    radius: Theme.radiusSm
    color: Theme.bgElevated
    border.width: 1
    border.color: editing ? Theme.borderFocus : Theme.borderSubtle

    // --- Görünüm modu ---
    Row {
        visible: !root.editing
        anchors.left: parent.left
        anchors.right: actions.left
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 16
        anchors.rightMargin: 12
        spacing: 12

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 10
            height: 10
            radius: 5
            color: root.categoryColor
        }

        Text {
            objectName: "categoryNameText"
            anchors.verticalCenter: parent.verticalCenter
            text: root.category.name
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            font.weight: Font.Medium
            color: Theme.textPrimary
        }

        AppBadge {
            anchors.verticalCenter: parent.verticalCenter
            text: root.category.resource_count + " kaynak"
            badgeColor: Theme.bgSurface
            borderColor: Theme.borderSubtle
            textColor: Theme.textMuted
        }
    }

    Row {
        id: actions
        visible: !root.editing
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        AppIconButton {
            objectName: "categoryEditButton"
            iconName: "fa5s.pen"
            iconSize: 12
            tooltip: "Kategoriyi Düzenle"
            onClicked: root.startEdit()
        }

        AppIconButton {
            objectName: "categoryDeleteButton"
            iconName: "fa5s.trash"
            iconSize: 12
            tooltip: "Kategoriyi Sil"
            onClicked: root.deleteRequested(root.category.id, root.category.name)
        }
    }

    // --- Düzenleme modu ---
    Column {
        id: editColumn
        visible: root.editing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 12

        Rectangle {
            width: Math.min(parent.width, 320)
            height: 36
            radius: Theme.radiusSm
            color: Theme.bgSurface
            border.width: 1
            border.color: nameInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle

            TextInput {
                id: nameInput
                objectName: "categoryNameEdit"
                anchors.fill: parent
                anchors.margins: 8
                verticalAlignment: TextInput.AlignVCenter
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                selectByMouse: true
                Keys.onReturnPressed: root.save()
                Keys.onEnterPressed: root.save()
                // Ana pencerenin genel Esc kisayolu (cekmece/modal kapatma) yerine bu alan Esc'i yakalasin
                Keys.onShortcutOverride: (event) => event.accepted = (event.key === Qt.Key_Escape)
                Keys.onEscapePressed: root.cancelEdit()
            }
        }

        ColorPalette {
            selectedColor: root.draftColor
            onColorPicked: (color) => root.draftColor = color
        }

        Row {
            spacing: 8

            AppButton {
                objectName: "categorySaveButton"
                text: "Kaydet"
                iconName: "fa5s.check"
                variant: "primary"
                enabledState: nameInput.text.trim().length > 0
                onClicked: root.save()
            }

            AppButton {
                objectName: "categoryCancelButton"
                text: "İptal"
                variant: "ghost"
                onClicked: root.cancelEdit()
            }
        }
    }
}
