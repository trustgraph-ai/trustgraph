---
layout: default
title: "Vipimo vya Zusisi vya Amri ya Utekelezaji (CLI)"
parent: "Swahili (Beta)"
---

# Vipimo vya Zusisi vya Amri ya Utekelezaji (CLI)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Haya yanaeleza uwezo wa ziada wa usanidi wa amri ya utekelezaji (CLI) kwa TrustGraph, ambayo inaruhusu watumiaji kusimamia vipengele vya usanidi kila kimoja kupitia amri mahususi za CLI. Uunganisho huu unaunga mkono matumizi manne makuu:

1. **Orodha ya Vipengele vya Usanidi**: Kuonyesha funguo za usanidi za aina fulani.
2. **Pata Kipengele cha Usanidi**: Kuchukua maadili maalum ya usanidi.
3. **Weka Kipengele cha Usanidi**: Kuweka au kusasisha vipengele vya usanidi.
4. **Futa Kipengele cha Usanidi**: Kuondoa vipengele vya usanidi.

## Malengo

- **Usimamizi Mahususi**: Kuwezesha usimamizi wa vipengele vya usanidi kila kimoja badala ya shughuli za jumla.
- **Orodha Kulingana na Aina**: Kuruhusu watumiaji kuchunguza vipengele vya usanidi kwa aina.
- **Shughuli za Kipengele Kimoja**: Kutoa amri za kupata/kuweka/kufuta vipengele vya usanidi kila kimoja.
- **Uunganisho wa API**: Kutumia API ya Usanidi iliyopo kwa shughuli zote.
- **Mifumo ya Utekelezaji ya Umoja**: Kufuata misingi na mifumo iliyopo ya CLI ya TrustGraph.
- **Usimamizi wa Makosa**: Kutoa ujumbe wazi wa makosa kwa shughuli zisizo halali.
- **Pato la JSON**: Kusaidia pato lililopangwa kwa matumizi ya programu.
- **Wasifu**: Kuweka msaada kamili na mifano ya matumizi.

## Licha

Hivi sasa, TrustGraph hutoa usimamizi wa usanidi kupitia API ya Usanidi na amri moja ya CLI, `tg-show-config`, ambayo inaonyesha usanidi wote. Ingawa hii inafaa kwa kuona usanidi, haitoi uwezo wa usimamizi wa kina.

Hali ya sasa ya kikwazo ni pamoja na:
- Hakuna njia ya kuorodisha vipengele vya usanidi kwa aina kutoka kwa CLI.
- Hakuna amri ya CLI ya kuchukua maadili maalum ya usanidi.
- Hakuna amri ya CLI ya kuweka vipengele vya usanidi kila kimoja.
- Hakuna amri ya CLI ya kufuta vipengele maalum vya usanidi.

Haya yanaashiria pengo hili kwa kuongeza amri nne mpya za CLI ambazo hutoa usimamizi wa kina wa usanidi. Kwa kufichua shughuli za API ya Usanidi kupitia amri za CLI, TrustGraph inaweza:
- Kuwezesha usimamizi wa usanidi kwa njia ya programu.
- Kuruhusu kuchunguza muundo wa usanidi kwa aina.
- Kusaidia sasisho maalumu ya usanidi.
- Kutoa udhibiti wa kina wa usanidi.

## Muundo wa Kiufundi

### Usanifu

Utekelezaji wa ziada wa usanidi wa CLI unahitaji vipengele hivi vya kiufundi:

1. **tg-list-config-items**
   - Huorodhesha funguo za usanidi kwa aina iliyoelezwa.
   - Huita njia ya API `Config.list(type)`.
   - Huonyesha orodha ya funguo za usanidi.
   
   Moduli: `trustgraph.cli.list_config_items`

2. **tg-get-config-item**
   - Inachukua kipengele(s) maalum(s) cha usanidi.
   - Huita njia ya API `Config.get(keys)`.
   - Inaonyesha maadili ya usanidi katika umbizo la JSON.

   Moduli: `trustgraph.cli.get_config_item`

3. **tg-put-config-item**
   - Inaweka au kusasisha kipengele cha usanidi.
   - Huita njia ya API `Config.put(values)`.
   - Inakubali vigezo vya aina, funguo, na thamani.

   Moduli: `trustgraph.cli.put_config_item`

4. **tg-delete-config-item**
   - Inaondoa kipengele cha usanidi.
   - Huita njia ya API `Config.delete(keys)`.
   - Inakubali vigezo vya aina na funguo.

   Moduli: `trustgraph.cli.delete_config_item`

### Mifano ya Data

#### ConfigKey na ConfigValue

Amri hizi hutumia miundo ya data iliyopo kutoka `trustgraph.api.types`:

```python
@dataclasses.dataclass
class ConfigKey:
    type : string
    key : string

@dataclasses.dataclass
class ConfigValue:
    type : string
    key : string
    value : string
```

Mbinu hii inaruhusu:
- Usimamizi wa data thabiti katika CLI na API.
- Shughuli za usanidi salama za aina.
- Umbizo la pembejeo/patou lililopangwa.
- Uunganisho na API ya Usanidi iliyopo.

### Maelezo ya Amri ya CLI

#### tg-list-config-items
```bash
tg-list-config-items --type <config-type> [--format text|json] [--api-url <url>]
```
- **Lengo**: Kuorodisha funguo zote za usanidi kwa aina iliyopewa.
- **Wito wa API**: `Config.list(type)`
- **Pato**:
  - `text` (cha kawaida): Funguo za usanidi zilizotenganishwa na mistari mipya.
  - `json`: Safu ya JSON ya funguo za usanidi.

#### tg-get-config-item
```bash
tg-get-config-item --type <type> --key <key> [--format text|json] [--api-url <url>]
```
- **Lengo**: Kuchukua kipengele maalum cha usanidi.
- **Wito wa API**: `Config.get(keys)`
- **Pato**:
  - `text` (cha kawaida): Thamani ya usanidi.
  - `json`: Thamani ya usanidi katika umbizo la JSON.

#### tg-put-config-item
```bash
tg-put-config-item --type <type> --key <key> --value <value>
```
- **Lengo**: Kuweka thamani ya usanidi.
- **Wito wa API**: `Config.put(values)`
- **Ingizo**:
  - `type`: Aina ya usanidi.
  - `key`: Funguo ya usanidi.
  - `value`: Thamani ya usanidi.

#### tg-delete-config-item
```bash
tg-delete-config-item --type <type> --key <key>
```
- **Lengo**: Kuondoa kipengele cha usanidi.
- **Wito wa API**: `Config.delete(keys)`
- **Ingizo**:
  - `type`: Aina ya usanidi.
  - `key`: Funguo ya usanidi.

## Mifano ya Matumizi

#### Kuorodisha vipengele vya usanidi
```bash
# Kuorodisha funguo za prompt (umbizo la maandishi)
tg-list-config-items --type prompt
template-1
template-2
system-prompt

# Kuorodisha funguo za prompt (umbizo la JSON)
tg-list-config-items --type prompt --format json
["template-1", "template-2", "system-prompt"]
```

#### Kupata kipengele cha usanidi
```bash
# Kupata thamani ya prompt (umbizo la maandishi)
tg-get-config-item --type prompt --key template-1
You are a helpful assistant. Please respond to: {query}

# Kupata thamani ya prompt (umbizo la JSON)
tg-get-config-item --type prompt --key template-1 --format json
"You are a helpful assistant. Please respond to: {query}"
```

#### Kuweka kipengele cha usanidi
```bash
# Kuweka kutoka kwa mstari wa amri
tg-put-config-item --type prompt --key new-template --value "Custom prompt: {input}"

# Kuweka kutoka kwa faili kupitia bomba
cat ./prompt-template.txt | tg-put-config-item --type prompt --key complex-template --stdin

# Kuweka kutoka kwa faili kupitia urejeshaji
tg-put-config-item --type prompt --key complex-template --stdin < ./prompt-template.txt

# Kuweka kutoka kwa pato la amri
echo "Generated template: {query}" | tg-put-config-item --type prompt --key auto-template --stdin
```

#### Kufuta kipengele cha usanidi
```bash
tg-delete-config-item --type prompt --key old-template
```

## Masuala Yaliyoshindikana

- Je, amri zinapaswa kusaidia shughuli za kundi (funguo nyingi) pamoja na vipengele vya kimoja?
- Umbizo gani la pato unapaswa kutumika kwa uthibitisho wa mafanikio?
- Jinsi aina za usanidi zinavyoweza kuelekezwa/kuchunguzwa na watumiaji?

## Marejeleo

- API ya Usanidi iliyopo: `trustgraph/api/config.py`
- Mfumo wa CLI: `trustgraph-cli/trustgraph/cli/show_config.py`
- Data: `trustgraph/api/types.py`
