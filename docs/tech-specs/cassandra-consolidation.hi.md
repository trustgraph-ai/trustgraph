# तकनीकी विनिर्देश: कैसेंड्रा कॉन्फ़िगरेशन समेकन

**स्थिति:** मसौदा
**लेखक:** सहायक
**तिथि:** 2024-09-03

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ कोडबेस में कैसेंड्रा कनेक्शन मापदंडों के लिए असंगत नामकरण और कॉन्फ़िगरेशन पैटर्न को संबोधित करता है। वर्तमान में, दो अलग-अलग पैरामीटर नामकरण योजनाएं मौजूद हैं (`cassandra_*` बनाम `graph_*`), जिससे भ्रम और रखरखाव जटिलता होती है।

## समस्या विवरण

कोडबेस वर्तमान में कैसेंड्रा कॉन्फ़िगरेशन मापदंडों के दो अलग-अलग सेट का उपयोग करता है:

1. **ज्ञान/कॉन्फ़िग/लाइब्रेरी मॉड्यूल** निम्नलिखित का उपयोग करते हैं:
   `cassandra_host` (होस्ट की सूची)
   `cassandra_user`
   `cassandra_password`

2. **ग्राफ/भंडारण मॉड्यूल** निम्नलिखित का उपयोग करते हैं:
   `graph_host` (एकल होस्ट, कभी-कभी सूची में परिवर्तित)
   `graph_username`
   `graph_password`

3. **असंगत कमांड-लाइन एक्सपोजर**:
   कुछ प्रोसेसर (जैसे, `kg-store`) कैसेंड्रा सेटिंग्स को कमांड-लाइन तर्कों के रूप में उजागर नहीं करते हैं
   अन्य प्रोसेसर उन्हें अलग-अलग नामों और प्रारूपों के साथ उजागर करते हैं
   सहायता पाठ पर्यावरण चर डिफ़ॉल्ट को प्रतिबिंबित नहीं करता है

दोनों पैरामीटर सेट एक ही कैसेंड्रा क्लस्टर से जुड़ते हैं, लेकिन अलग-अलग नामकरण सम्मेलनों के साथ, जिससे:
उपयोगकर्ताओं के लिए कॉन्फ़िगरेशन भ्रम
रखरखाव का बढ़ता बोझ
असंगत प्रलेखन
गलत कॉन्फ़िगरेशन की संभावना
कुछ प्रोसेसर में कमांड-लाइन के माध्यम से सेटिंग्स को ओवरराइड करने में असमर्थता

## प्रस्तावित समाधान

### 1. पैरामीटर नामों का मानकीकरण

सभी मॉड्यूल सुसंगत `cassandra_*` पैरामीटर नामों का उपयोग करेंगे:
`cassandra_host` - होस्ट की सूची (आंतरिक रूप से सूची के रूप में संग्रहीत)
`cassandra_username` - प्रमाणीकरण के लिए उपयोगकर्ता नाम
`cassandra_password` - प्रमाणीकरण के लिए पासवर्ड

### 2. कमांड-लाइन तर्क

सभी प्रोसेसर को कैसेंड्रा कॉन्फ़िगरेशन को कमांड-लाइन तर्कों के माध्यम से उजागर करना होगा:
`--cassandra-host` - होस्ट की अल्पविराम-विभाजित सूची
`--cassandra-username` - प्रमाणीकरण के लिए उपयोगकर्ता नाम
`--cassandra-password` - प्रमाणीकरण के लिए पासवर्ड

### 3. पर्यावरण चर बैकअप

यदि कमांड-लाइन पैरामीटर स्पष्ट रूप से प्रदान नहीं किए जाते हैं, तो सिस्टम पर्यावरण चर की जांच करेगा:
`CASSANDRA_HOST` - होस्ट की अल्पविराम-विभाजित सूची
`CASSANDRA_USERNAME` - प्रमाणीकरण के लिए उपयोगकर्ता नाम
`CASSANDRA_PASSWORD` - प्रमाणीकरण के लिए पासवर्ड

### 4. डिफ़ॉल्ट मान

यदि न तो कमांड-लाइन पैरामीटर और न ही पर्यावरण चर निर्दिष्ट हैं:
`cassandra_host` डिफ़ॉल्ट रूप से `["cassandra"]` है
`cassandra_username` डिफ़ॉल्ट रूप से `None` है (कोई प्रमाणीकरण नहीं)
`cassandra_password` डिफ़ॉल्ट रूप से `None` है (कोई प्रमाणीकरण नहीं)

### 5. सहायता पाठ आवश्यकताएँ

`--help` आउटपुट को:
जब सेट किया गया हो तो पर्यावरण चर मानों को डिफ़ॉल्ट के रूप में दिखाना चाहिए
पासवर्ड मानों को कभी भी प्रदर्शित नहीं करना चाहिए (इसके बजाय `****` या `<set>` दिखाएं)
सहायता पाठ में समाधान क्रम को स्पष्ट रूप से इंगित करना चाहिए

उदाहरण सहायता आउटपुट:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## कार्यान्वयन विवरण

### पैरामीटर समाधान का क्रम

प्रत्येक कैसेंड्रा पैरामीटर के लिए, समाधान का क्रम इस प्रकार होगा:
1. कमांड-लाइन तर्क मान
2. पर्यावरण चर (`CASSANDRA_*`)
3. डिफ़ॉल्ट मान

### होस्ट पैरामीटर हैंडलिंग

`cassandra_host` पैरामीटर:
कमांड-लाइन अल्पविराम-विभाजित स्ट्रिंग स्वीकार करता है: `--cassandra-host "host1,host2,host3"`
पर्यावरण चर अल्पविराम-विभाजित स्ट्रिंग स्वीकार करता है: `CASSANDRA_HOST="host1,host2,host3"`
आंतरिक रूप से हमेशा सूची के रूप में संग्रहीत किया जाता है: `["host1", "host2", "host3"]`
एकल होस्ट: `"localhost"` → `["localhost"]` में परिवर्तित
पहले से ही एक सूची: `["host1", "host2"]` → जैसा है उपयोग किया जाता है

### प्रमाणीकरण तर्क

प्रमाणीकरण का उपयोग तब किया जाएगा जब `cassandra_username` और `cassandra_password` दोनों प्रदान किए जाते हैं:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## संशोधित करने योग्य फ़ाइलें

### `graph_*` पैरामीटर का उपयोग करने वाले मॉड्यूल (जिन्हें बदला जाना है):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### `cassandra_*` पैरामीटर का उपयोग करने वाले मॉड्यूल (जिन्हें पर्यावरण बैकअप के साथ अपडेट किया जाना है):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### अपडेट करने योग्य परीक्षण फ़ाइलें:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## कार्यान्वयन रणनीति

### चरण 1: सामान्य कॉन्फ़िगरेशन हेल्पर बनाएं
सभी प्रोसेसरों में कैसेंड्रा कॉन्फ़िगरेशन को मानकीकृत करने के लिए उपयोगिता फ़ंक्शन बनाएं:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### चरण 2: `graph_*` पैरामीटर का उपयोग करके मॉड्यूल को अपडेट करें
1. पैरामीटर नामों को `graph_*` से `cassandra_*` में बदलें
2. कस्टम `add_args()` विधियों को मानकीकृत `add_cassandra_args()` से बदलें
3. सामान्य कॉन्फ़िगरेशन सहायक फ़ंक्शन का उपयोग करें
4. दस्तावेज़ स्ट्रिंग को अपडेट करें

उदाहरण परिवर्तन:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### चरण 3: `cassandra_*` पैरामीटर का उपयोग करके मॉड्यूल को अपडेट करें
1. उन स्थानों पर कमांड-लाइन तर्क समर्थन जोड़ें जहां यह गायब है (उदाहरण के लिए, `kg-store`)
2. मौजूदा तर्क परिभाषाओं को `add_cassandra_args()` से बदलें
3. सुसंगत समाधान के लिए `resolve_cassandra_config()` का उपयोग करें
4. सुसंगत होस्ट सूची प्रबंधन सुनिश्चित करें

### चरण 4: परीक्षण और दस्तावेज़ को अपडेट करें
1. सभी परीक्षण फ़ाइलों को नए पैरामीटर नामों का उपयोग करने के लिए अपडेट करें
2. CLI दस्तावेज़ को अपडेट करें
3. API दस्तावेज़ को अपडेट करें
4. पर्यावरण चर दस्तावेज़ जोड़ें

## पिछली अनुकूलता

संक्रमण के दौरान पिछली अनुकूलता बनाए रखने के लिए:

1. `graph_*` पैरामीटर के लिए **अवरोधन चेतावनी**
2. **पैरामीटर उपनाम** - शुरू में पुराने और नए दोनों नामों को स्वीकार करें
3. कई रिलीज़ में **चरणबद्ध कार्यान्वयन**
4. माइग्रेशन गाइड के साथ **दस्तावेज़ अपडेट**

पिछली अनुकूलता कोड का उदाहरण:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## परीक्षण रणनीति

1. **यूनिट परीक्षण** कॉन्फ़िगरेशन रिज़ॉल्यूशन लॉजिक के लिए
2. विभिन्न कॉन्फ़िगरेशन संयोजनों के साथ **एकीकरण परीक्षण**
3. **पर्यावरण चर परीक्षण**
4. **पिछड़ा संगतता परीक्षण** अप्रचलित मापदंडों के साथ
5. **डॉकर कंपोज़ परीक्षण** पर्यावरण चर के साथ

## दस्तावेज़ अपडेट

1. सभी CLI कमांड दस्तावेज़ों को अपडेट करें
2. API दस्तावेज़ों को अपडेट करें
3. माइग्रेशन गाइड बनाएं
4. डॉकर कंपोज़ उदाहरणों को अपडेट करें
5. कॉन्फ़िगरेशन संदर्भ दस्तावेज़ को अपडेट करें

## जोखिम और निवारण

| जोखिम | प्रभाव | निवारण |
|------|--------|------------|
| उपयोगकर्ताओं के लिए ब्रेकिंग परिवर्तन | उच्च | पिछड़े संगतता अवधि लागू करें |
| संक्रमण के दौरान कॉन्फ़िगरेशन भ्रम | मध्यम | स्पष्ट दस्तावेज़ और अवमूल्यन चेतावनियाँ |
| परीक्षण विफलताएँ | मध्यम | व्यापक परीक्षण अपडेट |
| डॉकर परिनियोजन मुद्दे | उच्च | सभी डॉकर कंपोज़ उदाहरणों को अपडेट करें |

## सफलता मानदंड

[ ] सभी मॉड्यूल सुसंगत `cassandra_*` पैरामीटर नामों का उपयोग करते हैं
[ ] सभी प्रोसेसर कमांड-लाइन तर्कों के माध्यम से कैसेंड्रा सेटिंग्स को उजागर करते हैं
[ ] कमांड-लाइन सहायता पाठ पर्यावरण चर डिफ़ॉल्ट दिखाता है
[ ] पासवर्ड मान कभी भी सहायता पाठ में प्रदर्शित नहीं होते हैं
[ ] पर्यावरण चर बैकअप सही ढंग से काम करता है
[ ] `cassandra_host` को आंतरिक रूप से लगातार एक सूची के रूप में संभाला जाता है
[ ] कम से कम 2 रिलीज़ के लिए पिछड़े संगतता बनाए रखी जाती है
[ ] सभी परीक्षण नए कॉन्फ़िगरेशन सिस्टम के साथ पास होते हैं
[ ] दस्तावेज़ पूरी तरह से अपडेट किया गया है
[ ] डॉकर कंपोज़ उदाहरण पर्यावरण चर के साथ काम करते हैं

## समयरेखा

**सप्ताह 1:** सामान्य कॉन्फ़िगरेशन हेल्पर लागू करें और `graph_*` मॉड्यूल को अपडेट करें
**सप्ताह 2:** मौजूदा `cassandra_*` मॉड्यूल में पर्यावरण चर समर्थन जोड़ें
**सप्ताह 3:** परीक्षण और दस्तावेज़ अपडेट करें
**सप्ताह 4:** एकीकरण परीक्षण और बग फिक्स

## भविष्य के विचार

अन्य डेटाबेस कॉन्फ़िगरेशन (जैसे, Elasticsearch) के लिए इस पैटर्न को विस्तारित करने पर विचार करें
कॉन्फ़िगरेशन सत्यापन और बेहतर त्रुटि संदेश लागू करें
कैसेंड्रा कनेक्शन पूलिंग कॉन्फ़िगरेशन के लिए समर्थन जोड़ें
कॉन्फ़िगरेशन फ़ाइल समर्थन (.env फ़ाइलें) जोड़ने पर विचार करें