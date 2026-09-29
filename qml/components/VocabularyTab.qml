import QtQuick
import QtQuick.Controls
import "../theme"
import "../js/text.js" as TextUtils

// Bilgi Havuzu > Kelimeler sekmesi: arama filtreli kelime listesi (çeviri, kaynak bağlantısı, silme).
Item {
    id: root

    property string searchQuery: ""

    ListView {
        id: vocabList
        anchors.fill: parent
        anchors.margins: 24
        spacing: 12
        clip: true

        model: {
            var all = bridge.reader.vocabulary
            if (!root.searchQuery) return all
            return all.filter(function(v) {
                return TextUtils.foldTr(v.word).indexOf(root.searchQuery) !== -1 ||
                       TextUtils.foldTr(v.translation).indexOf(root.searchQuery) !== -1
            })
        }

        delegate: Rectangle {
            width: vocabList.width - 24
            implicitHeight: vocabCol.implicitHeight + 20
            radius: Theme.radiusSm
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.borderSubtle

            Row {
                id: vocabCol
                anchors.left: parent.left
                anchors.right: vocabDeleteButton.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 16

                // Kelime
                Column {
                    width: 200
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    Text {
                        text: modelData.word
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Text {
                        text: modelData.resource_title
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.accentText
                        elide: Text.ElideRight
                        width: parent.width

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: bridge.reader.openReader(modelData.resource_id)
                        }
                    }
                }

                // Anlamı (Çeviri)
                Text {
                    width: parent.width - 320
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.translation
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Medium
                    color: Theme.textSecondary
                    wrapMode: Text.Wrap
                }

            }

            AppIconButton {
                id: vocabDeleteButton
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                iconName: "fa5s.trash"
                iconSize: 11
                tooltip: "Kelimeyi Sil"
                onClicked: bridge.reader.deleteVocabulary(modelData.id)
            }
        }

        ScrollBar.vertical: ScrollBar { active: true }
    }
}
