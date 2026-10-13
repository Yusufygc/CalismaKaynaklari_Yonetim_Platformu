import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../js/guide.js" as GuideData

// Kullanım Kılavuzu: son kullanıcıya uygulamayı adım adım anlatan, görselli sayfa. İçerik `js/guide.js`tedir; görseller
// `assets/guide/*.png` (scripts/guide_screenshots.py ile üretilir). Solda içindekiler, sağda kaydırılan bölümler.
Item {
    id: root

    readonly property var sections: GuideData.sections
    property int currentIndex: 0
    readonly property int contentWidth: Math.min(flick.width - 64, 820)

    function scrollTo(index) {
        const item = sectionRepeater.itemAt(index)
        if (item === null)
            return
        currentIndex = index
        scrollAnimation.stop()
        scrollAnimation.from = flick.contentY
        scrollAnimation.to = Math.max(0, Math.min(item.y, flick.contentHeight - flick.height))
        scrollAnimation.start()
    }

    // Kaydırırken içindekiler listesinde görünen bölümü vurgular
    function syncCurrent() {
        if (scrollAnimation.running)
            return
        let found = 0
        for (let i = 0; i < sectionRepeater.count; i++) {
            const item = sectionRepeater.itemAt(i)
            if (item !== null && item.y <= flick.contentY + 80)
                found = i
        }
        currentIndex = found
    }

    // ---- İçindekiler ----
    Rectangle {
        id: toc
        objectName: "guideToc"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 270
        color: Theme.bgSurface

        Rectangle {
            anchors.right: parent.right
            width: 1
            height: parent.height
            color: Theme.borderSubtle
        }

        Column {
            anchors.fill: parent
            anchors.rightMargin: 1

            Item {
                width: parent.width
                height: 64

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    text: "İçindekiler"
                    font.family: Theme.fontHeading
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.borderSubtle
                }
            }

            ListView {
                id: tocList
                width: parent.width
                height: parent.height - 64
                clip: true
                model: root.sections
                spacing: 2
                topMargin: 8

                delegate: Rectangle {
                    id: tocItem
                    required property var modelData
                    required property int index
                    objectName: "guideTocItem"
                    width: tocList.width - 16
                    x: 8
                    height: 36
                    radius: Theme.radiusSm
                    color: root.currentIndex === index ? Theme.accentSubtle : (tocMouse.containsMouse ? Theme.bgHover : "transparent")

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 8
                        spacing: 10

                        AppIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: tocItem.modelData.icon
                            size: 13
                            color: root.currentIndex === tocItem.index ? Theme.accentText : Theme.textSecondary
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 30
                            elide: Text.ElideRight
                            text: tocItem.modelData.title
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: root.currentIndex === tocItem.index ? Font.DemiBold : Font.Normal
                            color: root.currentIndex === tocItem.index ? Theme.accentText : Theme.textPrimary
                        }
                    }

                    MouseArea {
                        id: tocMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.scrollTo(tocItem.index)
                    }
                }
            }
        }
    }

    // ---- Bölümler ----
    Flickable {
        id: flick
        objectName: "guideFlick"
        anchors.left: toc.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        contentWidth: width
        contentHeight: contentCol.implicitHeight + 80
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        onContentYChanged: root.syncCurrent()
        ScrollBar.vertical: ScrollBar { active: true }

        NumberAnimation {
            id: scrollAnimation
            target: flick
            property: "contentY"
            duration: Theme.animBase
            easing.type: Easing.OutCubic
        }

        Column {
            id: contentCol
            x: Math.max(32, (flick.width - root.contentWidth) / 2)
            width: root.contentWidth
            topPadding: 32
            spacing: 40

            // Sayfa başlığı
            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "Kullanım Kılavuzu"
                    font.family: Theme.fontHeading
                    font.pixelSize: Theme.font2Xl
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Uygulamayı baştan sona anlatan kısa bir rehber. Soldaki listeden istediğin bölüme geçebilirsin."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    color: Theme.textSecondary
                }
            }

            Repeater {
                id: sectionRepeater
                model: root.sections

                delegate: Column {
                    id: section
                    required property var modelData
                    required property int index
                    objectName: "guideSection"
                    width: contentCol.width
                    spacing: 14

                    Row {
                        spacing: 12
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 36
                            height: 36
                            radius: Theme.radiusSm
                            color: Theme.accentSubtle
                            border.width: 1
                            border.color: Theme.accent
                            AppIcon {
                                anchors.centerIn: parent
                                name: section.modelData.icon
                                size: 15
                                color: Theme.accent
                            }
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: (section.index + 1) + ". " + section.modelData.title
                            font.family: Theme.fontHeading
                            font.pixelSize: Theme.fontXl
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        lineHeight: 1.3
                        text: section.modelData.intro
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        color: Theme.textPrimary
                    }

                    Column {
                        width: parent.width
                        spacing: 10

                        Repeater {
                            model: section.modelData.steps

                            delegate: Row {
                                id: step
                                required property string modelData
                                required property int index
                                objectName: "guideStep"
                                width: parent.width
                                spacing: 12

                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: 12
                                    color: Theme.accentSubtle
                                    Text {
                                        anchors.centerIn: parent
                                        text: step.index + 1
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.accentText
                                    }
                                }
                                Text {
                                    width: parent.width - 36
                                    wrapMode: Text.Wrap
                                    lineHeight: 1.3
                                    text: step.modelData
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }

                    // Ekran görüntüsü (1280x800 = 8:5)
                    Column {
                        visible: section.modelData.image !== ""
                        width: parent.width
                        spacing: 8

                        Rectangle {
                            width: parent.width
                            height: width * 0.625
                            radius: Theme.radiusMd
                            color: Theme.bgElevated
                            border.width: 1
                            border.color: Theme.borderStrong
                            clip: true

                            Image {
                                objectName: "guideImage"
                                anchors.fill: parent
                                anchors.margins: 1
                                source: section.modelData.image !== "" ? Qt.resolvedUrl("../../assets/guide/" + section.modelData.image) : ""
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                smooth: true
                                mipmap: true
                            }
                        }
                        Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            text: section.modelData.caption
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.italic: true
                            color: Theme.textMuted
                        }
                    }

                    // İpucu
                    Rectangle {
                        visible: section.modelData.tip !== ""
                        objectName: "guideTip"
                        width: parent.width
                        height: tipText.implicitHeight + 24
                        radius: Theme.radiusSm
                        color: Theme.accentSubtle
                        border.width: 1
                        border.color: Theme.accent

                        Row {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10
                            AppIcon {
                                anchors.top: parent.top
                                anchors.topMargin: 2
                                name: "fa5s.lightbulb"
                                size: 13
                                color: Theme.accentText
                            }
                            Text {
                                id: tipText
                                width: parent.width - 28
                                wrapMode: Text.Wrap
                                text: section.modelData.tip
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.accentText
                            }
                        }
                    }
                }
            }
        }
    }
}
