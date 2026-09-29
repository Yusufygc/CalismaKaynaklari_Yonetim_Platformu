import QtQuick
import "../theme"

Item {
    id: root

    property string name: ""
    property int size: 18
    property color color: Theme.textPrimary

    implicitWidth: size
    implicitHeight: size

    // Rengi hex koduna çevir (# işaretini kaldırarak sağlayıcıya gönder)
    function colorToHexNoHash(c) {
        var str = c.toString()
        if (str.startsWith("#")) {
            return str.substring(1)
        }
        return "ffffff"
    }

    Image {
        id: iconImg
        anchors.fill: parent
        sourceSize.width: root.size * 2
        sourceSize.height: root.size * 2
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        cache: true
        source: root.name ? "image://icon/" + root.name + "/" + root.colorToHexNoHash(root.color) : ""
    }
}
