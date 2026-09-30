import QtQuick
import "../theme"

// Ayarlar > Etiket hapı: görünüm modunda "#ad (sayı)", kalem ile satır içi yeniden adlandırma, çarpı ile silme talebi.
// Başarılı kayıtta köprü `tags` listesini yeniler, hap yeniden oluşur ve görünüm moduna döner;
// hata (yinelenen ad vb.) durumunda düzenleme açık kalır.
Rectangle {
    id: root

    property var tag: ({})
    property bool editing: false

    signal deleteRequested(int tagId, string tagName)

    function startEdit() {
        nameInput.text = tag.name
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
        if (name.toLowerCase() === String(tag.name).toLowerCase()) {
            cancelEdit()
            return
        }
        bridge.settings.updateTag(tag.id, name)
    }

    implicitWidth: (editing ? editRow.implicitWidth : viewRow.implicitWidth) + 20
    implicitHeight: 32
    radius: Theme.radiusPill
    color: Theme.bgElevated
    border.width: 1
    border.color: editing ? Theme.borderFocus : Theme.borderSubtle

    Row {
        id: viewRow
        visible: !root.editing
        anchors.centerIn: parent
        spacing: 8

        Text {
            objectName: "tagNameText"
            anchors.verticalCenter: parent.verticalCenter
            text: "#" + root.tag.name
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.weight: Font.Medium
            color: Theme.textPrimary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "(" + root.tag.resource_count + ")"
            font.family: Theme.fontFamily
            font.pixelSize: 10
            color: Theme.textMuted
        }

        AppIconButton {
            objectName: "tagEditButton"
            anchors.verticalCenter: parent.verticalCenter
            iconName: "fa5s.pen"
            iconSize: 10
            implicitWidth: 18
            implicitHeight: 18
            tooltip: "Etiketi Düzenle"
            onClicked: root.startEdit()
        }

        AppIconButton {
            objectName: "tagDeleteButton"
            anchors.verticalCenter: parent.verticalCenter
            iconName: "fa5s.times"
            iconSize: 10
            implicitWidth: 18
            implicitHeight: 18
            tooltip: "Etiketi Sil"
            onClicked: root.deleteRequested(root.tag.id, root.tag.name)
        }
    }

    Row {
        id: editRow
        visible: root.editing
        anchors.centerIn: parent
        spacing: 8

        TextInput {
            id: nameInput
            objectName: "tagNameEdit"
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(80, implicitWidth)
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            selectByMouse: true
            Keys.onReturnPressed: root.save()
            Keys.onEnterPressed: root.save()
            // Ana pencerenin genel Esc kisayolu (cekmece/modal kapatma) yerine bu alan Esc'i yakalasin
            Keys.onShortcutOverride: (event) => event.accepted = (event.key === Qt.Key_Escape)
            Keys.onEscapePressed: root.cancelEdit()
        }

        AppIconButton {
            objectName: "tagSaveButton"
            anchors.verticalCenter: parent.verticalCenter
            iconName: "fa5s.check"
            iconSize: 10
            implicitWidth: 18
            implicitHeight: 18
            tooltip: "Kaydet"
            onClicked: root.save()
        }

        AppIconButton {
            objectName: "tagCancelButton"
            anchors.verticalCenter: parent.verticalCenter
            iconName: "fa5s.times"
            iconSize: 10
            implicitWidth: 18
            implicitHeight: 18
            tooltip: "İptal"
            onClicked: root.cancelEdit()
        }
    }
}
