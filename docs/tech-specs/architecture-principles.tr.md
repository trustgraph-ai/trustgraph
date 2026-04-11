# Bilgi Grafiği Mimarisi Temelleri

## Temel 1: Özne-Yüklem-Nesne (ÖYY) Grafik Modeli
**Karar**: Çekirdek bilgi gösterim modeli olarak SPO/RDF'yi benimse

**Gerekçe**:
- Mevcut grafik teknolojileriyle maksimum esneklik ve uyumluluk sağlar
- Diğer grafik sorgu dillerine (örneğin, SPO → Cypher, ancak tersi değil) sorunsuz çeviri sağlar
- "Birçok" sonraki yeteneği "açığa çıkaran" bir temel oluşturur
- Hem düğüm-düğüm ilişkilerini (ÖYY) hem de düğüm-literal ilişkilerini (RDF) destekler

**Uygulama**:
- Temel veri yapısı: `node → edge → {node | literal}`
- RDF standartlarıyla uyumluluğu korurken, gelişmiş SPO işlemlerini destekler

## Temel 2: LLM-Yerel Bilgi Grafiği Entegrasyonu
**Karar**: Bilgi grafiği yapısını ve işlemlerini LLM etkileşimi için optimize et

**Gerekçe**:
- Birincil kullanım durumu, LLM'lerin bilgi grafikleriyle etkileşimini içerir
- Grafik teknolojisi seçimleri, diğer hususlara kıyasla LLM uyumluluğuna öncelik vermelidir
- Yapılandırılmış bilgiyi kullanan doğal dil işleme iş akışlarını sağlar

**Uygulama**:
- LLM'lerin etkili bir şekilde akıl yürütebileceği grafik şemalarını tasarla
- Yaygın LLM etkileşim kalıpları için optimize et

## Temel 3: Gömme Tabanlı Grafik Navigasyonu
**Karar**: Doğal dil sorgularını, gömmeler aracılığıyla doğrudan grafik düğümlerine eşleyin

**Gerekçe**:
- NLP sorgusundan grafik navigasyonuna en basit yolu sağlar
- Karmaşık ara sorgu oluşturma adımlarından kaçının
- Grafik yapısı içinde verimli semantik arama yetenekleri sağlar

**Uygulama**:
- `NLP Query → Graph Embeddings → Graph Nodes`
- Tüm grafik varlıkları için gömme gösterimlerini koru
- Sorgu çözümlemesi için doğrudan semantik benzerlik eşleştirmesini destekle

## Temel 4: Dağıtılmış Varlık Çözümlemesi ve Belirleyici Tanımlayıcılar
**Karar**: Paralel bilgi çıkarma işlemini, deterministik varlık tanımlamasıyla (80% kuralı) destekle

**Gerekçe**:
- **İdeal**: Tam durum görünürlüğü sağlayan tek işlem çıkarma, mükemmel varlık çözümlemesine olanak tanır
- **Gerçeklik**: Ölçeklenebilirlik gereksinimleri, paralel işleme yetenekleri gerektirir
- **Uzlaşma**: Dağıtılmış işlemler arasında deterministik varlık tanımlaması için tasarla

**Uygulama**:
- Farklı bilgi çıkarıcılar arasında tutarlı, benzersiz tanımlayıcılar oluşturmak için mekanizmalar geliştir
- Farklı işlemlerde bahsedilen aynı varlık, aynı tanımlayıcıya çözümlenmelidir
- Yaklaşık olarak %20'lik bir oranın, alternatif işleme modelleri gerektirebilecek uç durumlara karşılık geldiğinin farkında olun
- Karmaşık varlık çözümleme senaryoları için yedek mekanizmalar tasarla

## Temel 5: Yayın-Abonelik ile Olay Odaklı Mimari
**Karar**: Sistem koordinasyonu için bir yayın-abone mesajlaşma sistemi uygula

**Gerekçe**:
- Bilgi çıkarma, depolama ve sorgu bileşenleri arasında gevşek bir bağlama olanak tanır
- Sistem genelinde gerçek zamanlı güncellemeleri ve bildirimleri destekler
- Ölçeklenebilir, dağıtılmış iş akışlarını kolaylaştırır

**Uygulama**:
- Sistem bileşenleri arasındaki mesaj odaklı koordinasyon
- Bilgi güncellemeleri, çıkarma tamamlama ve sorgu sonuçları için olay akışları

## Temel 6: Geri Çağrılabilir Ajan İletişimi
**Karar**: Ajan tabanlı işleme için geri çağrılabilir yayın-abone işlemlerini destekle

**Gerekçe**:
- Ajanların birbirini tetikleyebildiği ve yanıtlayabildiği gelişmiş ajan iş akışlarına olanak tanır
- Karmaşık, çok aşamalı bilgi işleme boru hatlarını destekler
- Yinelemeli ve yinelemeli işleme kalıplarına izin verir

**Uygulama**:
- Yayın-abone sistemi, geri çağrılabilir çağrıları güvenli bir şekilde işlemelidir
- Sonsuz döngüleri önleyen ajan koordinasyon mekanizmaları
- Ajan iş akışı orkestrasyonu desteği

## Temel 7: Sütun Veri Depolama Entegrasyonu
**Karar**: Sorgu uyumluluğunun, sütunlu depolama sistemleriyle sağlanması.

**Gerekçe**:
- Büyük bilgi veri kümeleri üzerinde verimli analitik sorgulara olanak tanır.
- İş zekası ve raporlama kullanım senaryolarını destekler.
- Grafik tabanlı bilgi gösterimini geleneksel analitik iş akışlarıyla birleştirir.

**Uygulama**:
- Sorgu çevirme katmanı: Grafik sorguları → Sütunlu sorgular.
- Hem grafik işlemlerini hem de analitik iş yüklerini destekleyen hibrit depolama stratejisi.
- Her iki paradigma için de sorgu performansını koruyun.

---

## Mimari İlkeler Özeti

1. **Öncelikli Olarak Esneklik**: SPO/RDF modeli, maksimum uyarlanabilirlik sağlar.
2. **LLM Optimizasyonu**: Tüm tasarım kararları, LLM etkileşim gereksinimlerini dikkate alır.
3. **Anlamsal Verimlilik**: Optimum sorgu performansı için doğrudan gömülü-düğüm eşlemesi.
4. **Pratik Ölçeklenebilirlik**: Mükemmel doğruluğu, pratik dağıtılmış işleme ile dengeleyin.
5. **Olay Odaklı Koordinasyon**: Yayın-abone, gevşek bağlama ve ölçeklenebilirliğe olanak tanır.
6. **Ajan Dostu**: Karmaşık, çoklu ajan iş akışlarını destekler.
7. **Analitik Uyumluluk**: Kapsamlı sorgulama için grafik ve sütunlu paradigmaları birleştirir.

Bu temeller, teorik titizliği pratik ölçeklenebilirlik gereksinimleriyle dengeleyen, LLM entegrasyonu ve dağıtılmış işleme için optimize edilmiş bir bilgi grafiği mimarisi oluşturur.

