.pragma library

// Kullanım Kılavuzu içeriği (GuideView.qml). Son kullanıcı için yazıldı: teknik terim yok, "sen" dili, kısa adımlar.
// Görseller assets/guide/ altındadır ve `scripts/guide_screenshots.py` ile üretilir; arayüz değişince yeniden üretilir.
// Her bölüm: id, title, icon (qtawesome adı), intro, steps (numaralı adımlar), image (dosya adı ya da ""), caption,
// tip (ipucu kutusu ya da "").

var sections = [
    {
        id: "baslarken",
        title: "Uygulama ne işe yarar?",
        icon: "fa5s.bookmark",
        intro: "Kaynak Yönetim, okuduğun makaleleri, web sayfalarını ve PDF'leri tek yerde toplar. PDF okurken önemli yerleri "
               + "renklerle işaretlersin; işaretlediğin her şey kendiliğinden bir araya gelir. İstersen Obsidian'daki notlarına da gönderirsin.",
        steps: [
            "Oku: kaynağını ekle ve uygulamanın içinde aç.",
            "İşaretle: önemli cümleleri seç, anlamına uygun rengi ver.",
            "Derle: Bilgi Havuzu'nda tüm işaretlerini gör, ara, makaleleri yan yana karşılaştır."
        ],
        image: "",
        caption: "",
        tip: "Her şey kendi bilgisayarında durur. İnternet yalnızca Makale Market'te ve makale bilgisi getirirken kullanılır."
    },
    {
        id: "kaynak-ekleme",
        title: "Kaynak ekleme ve düzenleme",
        icon: "fa5s.plus-circle",
        intro: "Bağlantı Vitrini, tüm kaynaklarının durduğu ana sayfadır. Her kaynak bir kart olarak görünür.",
        steps: [
            "Sağ üstteki \"Yeni Ekle\" düğmesine bas. Bir web adresi yapıştırabilir ya da \"Bilgisayardan PDF Yükle\" ile dosya seçebilirsin.",
            "PDF'i doğrudan pencerenin üzerine sürükleyip bırakmak da yeterli.",
            "Karta tıklayınca sağda ayrıntıları açılır. Buradan durumunu (Gelen Kutusu, Planlandı, Devam Ediyor, Tamamlandı) değiştirebilir, \"Düzenle\" ile kategori ve etiketlerini güncelleyebilirsin.",
            "Sol taraftaki \"Durumlar\" listesi kaynaklarını duruma göre süzer; kalp simgesi favorilerini gösterir."
        ],
        image: "kutuphane.png",
        caption: "Bağlantı Vitrini: her kaynak bir kart. Üstteki kutudan arama yapılır.",
        tip: "Aynı PDF dosyası bilgisayarında yalnızca bir kez saklanır."
    },
    {
        id: "pdf-okuma",
        title: "PDF okuma ve renkle işaretleme",
        icon: "fa5s.highlighter",
        intro: "PDF kartına tıkladığında dosya uygulamanın içinde açılır. Kaldığın yeri hatırlar; bir sonraki açışında oradan devam edersin.",
        steps: [
            "Okurken önemli bir cümleyi fareyle seç. Seçimin yanında renkli noktalar belirir.",
            "Cümlenin anlamına uygun rengi seç. Sarı: Önemli. Yeşil: Bulgu / Sonuç. Turkuaz: Yöntem. Mor: Tanım / Kavram. Pembe: Eleştiri / Soru.",
            "Sol paneldeki \"Notlarım\" sekmesi o PDF'teki tüm işaretlerini listeler. Birine tıklayınca sayfada o yere gidersin.",
            "Üstteki büyüteç simgesi (ya da Ctrl+F) PDF'in içinde kelime arar."
        ],
        image: "okuyucu.png",
        caption: "PDF okuyucu: işaretli cümleler renkli görünür, solda \"Notlarım\" paneli.",
        tip: "Aynı cümleyi başka bir renkle tekrar işaretlersen yeni kayıt oluşmaz, rengi değişir."
    },
    {
        id: "not-kelime",
        title: "Not, etiket ve kelime ekleme",
        icon: "fa5s.sticky-note",
        intro: "İşaretlerin yanına kendi düşüncelerini de ekleyebilirsin.",
        steps: [
            "Üstteki \"Not Ekle\" düğmesine bas, sonra sayfada istediğin yere tıkla ve notunu yaz.",
            "Bir işaretin altına yorum ve #etiket yazabilirsin. Etiketler Bilgi Havuzu'nda süzgeç olarak çıkar.",
            "Yabancı dildeki bir kelimeyi seçip \"Kelime Havuzuna Ekle\" simgesine basarsan Türkçe anlamını yazıp kaydedebilirsin. Kelimelerin Bilgi Havuzu'ndaki \"Kelimeler\" sekmesinde toplanır."
        ],
        image: "",
        caption: "",
        tip: ""
    },
    {
        id: "bilgi-havuzu",
        title: "Bilgi Havuzu: işaretlerin tek yerde",
        icon: "fa5s.quote-right",
        intro: "Bilgi Havuzu, hangi kaynaktan olursa olsun yaptığın tüm işaretleri ve kelimeleri bir arada gösterir.",
        steps: [
            "Üstteki renk düğmeleriyle yalnızca belirli anlamdaki işaretleri göster (örneğin yalnızca \"Yöntem\").",
            "Altındaki #etiket düğmeleri, kendi etiketlerinle süzmeni sağlar. Aynı düğmeye tekrar basınca süzgeç kalkar.",
            "İşaretin altındaki kaynak adına tıklayınca o kaynak açılır. Çöp kutusu simgesiyle işareti silebilir, kutucuklarla birden çok işareti seçip toplu silebilirsin.",
            "Sağ üstteki \"Tümünü Dışa Aktar\" düğmesi, tüm işaretlerini tek bir not dosyası olarak kaydeder."
        ],
        image: "bilgi-havuzu.png",
        caption: "Bilgi Havuzu > Alıntılar: renk ve etiketle süzülen işaretlerin listesi.",
        tip: ""
    },
    {
        id: "icerikte-arama",
        title: "PDF'lerin içinde arama",
        icon: "fa5s.search",
        intro: "Bilgi Havuzu'ndaki \"Metinde Ara\" sekmesi, tüm PDF'lerinin içindeki yazıyı arar. Hangi makalede ne geçtiğini hatırlamasan da bulursun.",
        steps: [
            "\"Metinde Ara\" sekmesini aç ve yukarıdaki kutuya aramak istediğin kelimeyi yaz.",
            "Sonuçlar makaleye göre gruplanır; bulunan kelime kalın görünür. Büyük/küçük harf ve Türkçe karakterler fark etmez: \"ogrenme\" yazsan da \"öğrenme\" bulunur.",
            "Tırnak içinde yazarsan yan yana geçen kelimeler aranır: \"derin öğrenme\".",
            "Bir sonuca tıklayınca PDF tam o satırda açılır ve aranan kelime işaretlenir.",
            "Bir makaleden çok sonuç varsa \"tümünü göster\" bağlantısı hepsini açar."
        ],
        image: "metinde-ara.png",
        caption: "Metinde Ara: sonuçlar makaleye göre gruplu, aranan kelime kalın.",
        tip: "Yeni eklediğin bir PDF'in aramaya hazırlanması birkaç saniye sürebilir; üstte ilerlemeyi görürsün. Yazısı seçilemeyen (taranmış) PDF'lerin içinde arama yapılamaz; bunlar sağ üstteki \"PDF aranamıyor\" bağlantısında listelenir."
    },
    {
        id: "matris",
        title: "Matris: makaleleri karşılaştır",
        icon: "fa5s.table",
        intro: "Matris sekmesi, her makaleyi bir satırda, her anlam rengini bir sütunda gösterir. Böylece \"tüm makalelerin yöntemleri\" gibi soruları tek bakışta yanıtlarsın.",
        steps: [
            "Üstteki renk düğmelerine basarak yalnızca istediğin sütunları göster.",
            "#etiket düğmeleri ve üstteki arama kutusu (makale adı yazarak) satırları daraltır.",
            "Bir hücrede en çok üç alıntı görünür; fazlası için \"alıntı daha\" bağlantısına bas.",
            "Bir alıntıya tıklayınca makale o cümlede açılır.",
            "\"Panoya kopyala\" ya da \"Markdown'a aktar\" ile ekrandaki tabloyu not olarak alabilirsin."
        ],
        image: "matris.png",
        caption: "Matris: satırlar makale, sütunlar anlam rengi.",
        tip: "Obsidian'a henüz gönderilmemiş makalelerde \"(öneri)\" yazan kısa bir ad görürsün; Obsidian'a ilk gönderimde bu ad kesinleşir."
    },
    {
        id: "obsidian",
        title: "Obsidian ile bağlama",
        icon: "fa5s.gem",
        intro: "Obsidian kullanıyorsan işaretlerin her PDF için ayrı bir not olarak Obsidian klasörüne yazılabilir. Kullanmıyorsan bu bölümü atlayabilirsin.",
        steps: [
            "Ayarlar > Obsidian sekmesinde \"Klasör Seç\" düğmesine bas ve Obsidian'da açtığın klasörü seç.",
            "\"Şimdi Eşitle\"ye bas. Klasörde \"Papers\" adlı bir klasör oluşur; her PDF için bir not dosyası, ayrıca Kütüphane Dizini, Kelime Defteri ve Literatür Matrisi notları yazılır.",
            "Bundan sonra yeni işaretlerin birkaç saniye içinde notlara kendiliğinden eklenir.",
            "\"Bağlantıları Etkinleştir\" dersen Obsidian'daki \"s. 3\" gibi sayfa bağlantılarına tıklayınca uygulama açılır ve PDF tam o işarette durur."
        ],
        image: "ayarlar-obsidian.png",
        caption: "Ayarlar > Obsidian: klasörü seç, \"Şimdi Eşitle\"ye bas.",
        tip: "Uygulama notlarda yalnızca kendi işaretli bölümünü günceller. Notlara kendi yazdıkların silinmez. İstediğin zaman \"Eşitlemeyi Kapat\" diyebilirsin; mevcut notlara dokunulmaz."
    },
    {
        id: "matris-ayarlari",
        title: "Matris ayarları",
        icon: "fa5s.sliders-h",
        intro: "Ayarlar > Matris sekmesinde matrisin görünümünü kendine göre düzenlersin.",
        steps: [
            "Sütunların sırasını yukarı/aşağı okları ile değiştir. Bilgi Havuzu'ndaki matris, dışa aktarılan dosya ve Obsidian notu aynı sırayı kullanır.",
            "\"Obsidian'da yaz\" kutusunu kaldırdığın sütun Obsidian'daki matris notunda görünmez.",
            "Obsidian notunda hücre başına kaç alıntı yazılacağını seç. Fazlası \"... ve N alıntı daha\" satırıyla belirtilir.",
            "\"Varsayılana dön\" her şeyi ilk haline getirir."
        ],
        image: "ayarlar-matris.png",
        caption: "Ayarlar > Matris: sıra, Obsidian'da yazılacak sütunlar ve hücre sınırı.",
        tip: ""
    },
    {
        id: "gorunum",
        title: "Renk ve yazı tipi seçimi",
        icon: "fa5s.palette",
        intro: "Uygulamanın renklerini ve yazı tiplerini beğenine göre değiştirebilirsin. Ayarlar > Görünüm sekmesinde seçtiğin hemen uygulanır ve bir sonraki açılışta da hatırlanır.",
        steps: [
            "\"Mod\" bölümünden Açık ya da Koyu görünümü seç. Sol alttaki düğme de aynı işi yapar.",
            "\"Renk teması\" bölümünde altı hazır tema var: Akademik Mavi, Klasik Akademik, Modern Akademik, Kütüphane, Bilimsel / Teknik ve Prestijli Üniversite. Karta tıklaman yeterli.",
            "\"Yazı tipi\" bölümünde başlık, arayüz ve alıntı yazılarının nasıl görüneceğini her çiftin örneğinden görüp seçebilirsin.",
            "Her temada yazılar, uzun süre okumada yormayacak ve rahat seçilecek şekilde ayarlanır. \"Varsayılana dön\" ilk haline getirir."
        ],
        image: "ayarlar-gorunum.png",
        caption: "Ayarlar > Görünüm: mod, renk teması ve yazı tipi çifti.",
        tip: "Bir yazı tipi bilgisayarında kurulu değilse, kartın altında yazan benzer bir yazı tipi kullanılır."
    },
    {
        id: "makale-market",
        title: "Makale Market: yeni makale bul",
        icon: "fa5s.compass",
        intro: "Makale Market, internette bilimsel makale aramanı sağlar. Bulduklarını tek tıkla kütüphanene kaydedersin.",
        steps: [
            "Üstteki kutuya bir konu yaz ve \"Ara\"ya bas. İstersen yıl, tür, dil ve \"Sadece açık erişim\" ile daralt.",
            "Sonuçları \"En Güncel\", \"En Popüler\" ya da \"En Çok Atıf Alan\" olarak sırala.",
            "Beğendiğin makalenin \"Kaydet\" düğmesine bas; makale vitrinine eklenir. Birden çok seçip \"Seçilenleri Kaydet\" de diyebilirsin.",
            "\"Aramayı kaydet\" dersen o arama üstte bir düğme olarak durur ve yeni çıkan makale sayısını gösterir."
        ],
        image: "makale-market.png",
        caption: "Makale Market: konu yaz, sonuçları süz, beğendiğini kaydet.",
        tip: "Bu bölüm internet bağlantısı gerektirir."
    },
    {
        id: "kunye",
        title: "Makale bilgisini otomatik doldurma",
        icon: "fa5s.id-card",
        intro: "Bir PDF'in üzerinde makale numarası (DOI) varsa uygulama yazar, yıl ve dergi bilgisini internetten kendisi getirebilir.",
        steps: [
            "Bu özellik varsayılan olarak açıktır. Ayarlar > Künye sekmesinden kapatabilirsin.",
            "Açıkken yeni bir PDF eklediğinde bilgiler kendiliğinden dolar; kaynak adı, yazarlar ve yıl atıf yazarken kullanılır.",
            "Zaten dolu olan hiçbir bilgi değiştirilmez."
        ],
        image: "ayarlar-kunye.png",
        caption: "Ayarlar > Künye: otomatik doldurmayı aç ya da kapat.",
        tip: "Açıkken internete yalnızca PDF'ten okunan makale numarası gönderilir, başka hiçbir şey gönderilmez."
    },
    {
        id: "sss",
        title: "Sık sorulanlar",
        icon: "fa5s.question-circle",
        intro: "Karşılaşabileceğin yaygın durumlar:",
        steps: [
            "PDF'te yazıyı seçemiyorum. PDF taranmış bir görüntü olabilir. Böyle PDF'lerde seçim, işaretleme ve içinde arama çalışmaz; yine de sayfaya not ekleyebilirsin.",
            "Aradığım kelimeyi bulamıyorum. PDF'in aramaya hazırlandığından emin ol (Metinde Ara'nın üstünde ilerleme çıkar) ve kelimenin doğru yazıldığına bak.",
            "Verilerim nerede duruyor? Hepsi senin bilgisayarında, uygulamanın kendi klasöründe. Obsidian klasörün senin kendi dosyalarındır.",
            "Obsidian'daki notumu uygulama silebilir mi? Hayır. Uygulama yalnızca kendi işaretli bölümünü günceller.",
            "Kısayollar: Esc tuşu açık pencereyi ya da ayrıntı panelini kapatır; PDF okurken Ctrl+F kelime arama çubuğunu açar."
        ],
        image: "",
        caption: "",
        tip: ""
    }
];
