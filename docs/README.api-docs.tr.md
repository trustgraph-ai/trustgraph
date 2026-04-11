
# Otomatik olarak dokümantasyon oluşturma

## REST ve WebSocket API Dokümantasyonu

`specs/build-docs.sh` - REST ve websocket dokümantasyonunu OpenAPI ve AsyncAPI özelliklerinden oluşturur.
  
## Python API Dokümantasyonu


Python API dokümantasyonu, `trustgraph.api` paketini inceleyen özel bir Python betiği kullanılarak, dokümantasyon dizelerinden (docstrings) oluşturulur.

### Ön Koşullar

trustgraph paketi içe aktarılabilir olmalıdır. Geliştirme ortamında çalışıyorsanız:

```bash
cd trustgraph-base
pip install -e .
```

### Belgeler Oluşturma

"docs" dizininden:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

Bu, eksiksiz API dokümantasyonunu içeren tek bir Markdown dosyası oluşturur ve şunları gösterir:
Kurulum ve hızlı başlangıç kılavuzu
Her sınıf/tip için içe aktarma ifadeleri
Örneklerle birlikte tam dokümanlar
Kategoriye göre düzenlenmiş içindekiler tablosu

### Dokümantasyon Stili

Tüm dokümanlar, Google stili biçimini izler:
Kısa, tek satırlık özet
Ayrıntılı açıklama
Parametre açıklamalarıyla birlikte "Args" bölümü
"Returns" bölümü
"Raises" bölümü (uygulanabilir olduğunda)
Doğru sözdizimi vurgulamasıyla birlikte örnek kod blokları

Oluşturulan dokümantasyon, kullanıcıların `trustgraph.api`'dan içe aktardığı şekilde, tam olarak kamu API'sini gösterir ve dahili modül yapısını ortaya çıkarmaz.

