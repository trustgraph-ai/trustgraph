# Vipimo vya Majadiliano ya Zana ya MCP

## Muhtasari
**Jina la Kipengele:** Usaidizi wa Majadiliano ya Zana ya MCP
**Mwandishi:** Claude Code Assistant
**Tarehe:** 2025-08-21
**Hali:** Imekamilika

### Muhtasari

Kuruhusu wakala wa ReACT kuita zana za MCP (Model Context Protocol) kwa
majadiliano yaliyobainishwa vizuri kwa kuongeza usaidizi wa majadiliano katika
usanidi wa zana za MCP, kama vile zana za kiolezo za matangazo
zinavyofanya sasa.

### Tatizo

Kwa sasa, zana za MCP katika mfumo wa wakala wa ReACT haziwezi kuainisha
majadiliano yake yanayotarajiwa. Njia ya `McpToolImpl.get_arguments()` hurudisha
orodha tupu, na kuwafanya LLMs (Large Language Models) nadhani muundo sahihi
wa vigezo kulingana na majina na maelezo ya zana pekee. Hii husababisha:
Utendaji usio wa kuaminika wa zana kutokana na nadharia ya vigezo
Uzoefu mbaya wa mtumiaji wakati zana zinashindwa kutokana na majadiliano yasiyo sahihi
Hakuna uthibitishaji wa vigezo vya zana kabla ya utekelezaji
Ukosefu wa maandishi ya vigezo katika matangazo ya wakala

### Lengo

[ ] Kuruhusu usanidi wa zana za MCP kuainisha majadiliano yanayotarajiwa (jina, aina, maelezo)
[ ] Kusasisha meneja wa wakala ili kuonyesha majadiliano ya zana za MCP kwa LLMs kupitia matangazo
[ ] Kuhifadhi utangamano na usanidi wa zana za MCP zilizopo
[ ] Kusaidia uthibitishaji wa majadiliano kama vile zana za kiolezo za matangazo

### Mambo ambayo Hayatarajiwi
Kugundua majadiliano kwa njia ya moja kwa moja kutoka kwa seva za MCP (ongezeko la baadaye)
Uthibitishaji wa aina ya majadiliano zaidi ya muundo wa msingi
Mifumo ngumu ya majadiliano (vitu vilivyojumuishwa, safu)

## Asili na Mfumo

### Hali ya Sasa
Zana za MCP zimepangwa katika mfumo wa wakala wa ReACT na metadata ndogo:
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance"
}
```

Njia `McpToolImpl.get_arguments()` hurudia `[]`, kwa hivyo, mifumo ya lugha kubwa (LLMs) hayapokei mwongozo wowote kuhusu hoja katika maagizo yao.

### Mapungufu

1. **Hakuna uainishaji wa hoja**: Vifaa vya MCP haviwezi kufafanua
   vigezo.

2. **Utabiri wa vigezo vya LLM**: Wawakilishi lazima watabiri vigezo kutoka kwa majina/maelezo ya zana.
   
3. **Habari ya maagizo inayokosekana**: Maagizo ya wakala yanaonyesha maelezo yoyote kuhusu hoja kwa vifaa vya MCP.

   4. **Hakuna uthibitisho**: Vigezo visivyofaa hugunduliwa wakati wa utekelezaji wa zana ya MCP.

### Vipengele Vinavyohusiana
   **trustgraph-flow/agent/react/service.py**: Kupakia usanidi wa zana na uundaji wa AgentManager.
**trustgraph-flow/agent/react/tools.py**: Utendaji wa McpToolImpl.
**trustgraph-flow/agent/react/agent_manager.py**: Uundaji wa maagizo pamoja na hoja za zana.
**trustgraph-cli**: Vifaa vya CLI kwa usimamizi wa zana za MCP.
**Workbench**: Kiolesura cha nje cha usanidi wa zana za wakala.

## Mahitaji

### Mahitaji ya Kifamilia
## Mahitaji

### Mahitaji ya Kazi

1. **Vigezo vya Usanidi wa Zana ya MCP**: Usanidi wa zana za MCP LAZIMA uunga mkono safu ya hiari ya `arguments` yenye nyanja za jina, aina, na maelezo.
2. **Uonyeshaji wa Vigezo**: `McpToolImpl.get_arguments()` INAHITAJIKA kurudisha vigezo vilivyosanidiwa badala ya orodha tupu.
3. **Uunganisho wa Maagizo**: Maagizo ya wakala LAZIMA yajumuise maelezo ya vigezo vya zana ya MCP wakati vigezo vinapotajwa.
4. **Ulinganifu na Mifumo ya Zamani**: Usanidi wa zana za MCP uliopo bila vigezo LAZIMA uendelee kufanya kazi.
5. **Usaidizi wa CLI**: CLI ya `tg-invoke-mcp-tool` iliyopo inasaidia vigezo (tayari imetekelezwa).

### Mahitaji Yasiyo ya Kazi
1. **Ulinganifu na Mifumo ya Zamani**: Hakuna mabadiliko yoyote yanayoweza kusababisha migogoro kwa usanidi wa zana za MCP uliopo.
2. **Utendaji**: Hakuna athari kubwa ya utendaji kwenye uzalishaji wa maagizo ya wakala.
3. **Ulinganifu**: Usimamizi wa vigezo LAZIMA uangane na mifumo ya zana za kiolezo katika kiolezo cha maagizo.

### Hadithi za Mtumiaji

1. Kama **msanidi programu wa wakala**, ninataka kuainisha vigezo vya zana ya MCP katika usanidi ili kwamba mifumo ya LLM iweze kutumia zana na vigezo sahihi.
2. Kama **mtumiaji wa benchi ya kazi**, ninataka kusanidi vigezo vya zana ya MCP katika UI ili kwamba wakala watumie zana vizuri.
3. Kama **mfumo wa LLM katika wakala wa ReACT**, ninataka kuona maelezo ya vigezo vya zana katika maagizo ili kwamba niweze kutoa vigezo sahihi.

## Muundo

### Muundo wa Juu
Panua usanidi wa zana ya MCP ili uangane na muundo wa kiolezo cha maagizo kwa:
1. Kuongeza safu ya hiari ya `arguments` kwa usanidi wa zana za MCP.
2. Kubadilisha `McpToolImpl` ili kukubali na kurudisha vigezo vilivyosanidiwa.
3. Kusasisha upakaji wa usanidi ili kushughulikia vigezo vya zana ya MCP.
4. Kuhakikisha kwamba maagizo ya wakala yajumuise taarifa ya vigezo vya zana ya MCP.

### Mfumo wa Usanidi
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "Bank account identifier"
    },
    {
      "name": "date",
      "type": "string",
      "description": "Date for balance query (optional, format: YYYY-MM-DD)"
    }
  ]
}
```

### Mtiririko wa Data
1. **Uipakaji wa Usanidi**: Usanidi wa zana ya MCP pamoja na hoja huipakwa na `on_tools_config()`
2. **Uundaji wa Zana**: Hoja huzingatiwa na kupitishwa kwa `McpToolImpl` kupitia kwa konstrukta
3. **Uundaji wa Maagizo**: `agent_manager.py` huita `tool.arguments` ili kujumuishwa katika maagizo ya LLM
4. **Utendaji wa Zana**: LLM hutoa vigezo ambavyo hupitishwa kwa huduma ya MCP bila kubadilishwa

### Mabadiliko ya API
Hakuna mabadiliko ya API ya nje - hii ni usanidi na usimamizi wa hoja wa ndani tu.

### Maelezo ya Vipengele

#### Kipengele 1: service.py (Uipakaji wa Usanidi wa Zana)
**Madhumuni**: Kuchanganua usanidi wa zana za MCP na kuunda mifano ya zana
**Mabadiliko Yanayohitajika**: Ongeza uchanganuzi wa hoja kwa zana za MCP (kama vile zana za maagizo)
**Utendaji Mpya**: Toa safu ya `arguments` kutoka usanidi wa zana ya MCP na uunde vitu vya `Argument`

#### Kipengele 2: tools.py (McpToolImpl)
**Madhumuni**: Kifungashio cha utekelezaji wa zana ya MCP
**Mabadiliko Yanayohitajika**: Kukubali hoja katika konstrukta na kurejesha hoja hizo kutoka `get_arguments()`
**Utendaji Mpya**: Kuhifadhi na kuonyesha hoja zilizosanidiwa badala ya kurejesha orodha tupu

#### Kipengele 3: Workbench (Hifadhi Nje)
**Madhumuni**: Kiolesura cha usanidi wa zana za wakala
**Mabadiliko Yanayohitajika**: Ongeza kiolesura cha maelezo ya hoja kwa zana za MCP
**Utendaji Mpya**: Kuruhusu watumiaji kuongeza/kuhariri/kuondoa hoja kwa zana za MCP

#### Kipengele 4: Zana za CLI
**Madhumuni**: Usimamizi wa zana za mstari wa amri
**Mabadiliko Yanayohitajika**: Kusaidia maelezo ya hoja katika amri za uundaji/kusasisha zana za MCP
**Utendaji Mpya**: Kukubali parameter ya hoja katika amri za usanidi wa zana

## Mpango wa Utendaji

### Awamu ya 1: Marekebisho ya Msingi ya Mfumo wa Wakala
[ ] Sasisha konstrukta ya `McpToolImpl` ili kukubali parameter ya `arguments`
[ ] Badilisha `McpToolImpl.get_arguments()` ili irudishe hoja zilizohifadhiwa
[ ] Badilisha usanifuaji wa `service.py` wa zana ya MCP ili kushughulikia hoja
[ ] Ongeza vipimo vya kitengo kwa usimamizi wa hoja za zana ya MCP
[ ] Hakikisha maagizo ya wakala yanajumuisha hoja za zana ya MCP

### Awamu ya 2: Usaidizi wa Zana za Nje
[ ] Sasisha zana za CLI ili kusaidia vipimo vya hoja za zana ya MCP
[ ] Andika maelezo ya muundo wa usanifuaji wa hoja kwa watumiaji
[ ] Sasisha kiolesura cha Kazi (Workbench) ili kusaidia usanifuaji wa hoja za zana ya MCP
[ ] Ongeza mifano na maandishi

### Muhtasari wa Marekebisho ya Msimbo
| Faili | Aina ya Marekebisho | Maelezo |
|------|------------|-------------|
| `tools.py` | Imebadilishwa | Sasisha McpToolImpl ili kukubali na kuhifadhi hoja |
| `service.py` | Imebadilishwa | Pata hoja kutoka usanifuaji wa zana ya MCP (mstari wa 108-113) |
| `test_react_processor.py` | Imebadilishwa | Ongeza vipimo kwa hoja za zana ya MCP |
| Zana za CLI | Imebadilishwa | Saidia vipimo vya hoja katika amri |
| Workbench | Imebadilishwa | Ongeza kiolesura kwa usanifuaji wa hoja za zana ya MCP |

## Mkakati wa Upimaji

### Vipimo vya Kitengo
**Uchanganuzi wa Hoja za Zana ya MCP**: Hakikisha `service.py` inachanganua hoja vizuri kutoka usanifuaji wa zana ya MCP
**Hoja za McpToolImpl**: Hakikisha `get_arguments()` inarudisha hoja zilizosanifishwa badala ya orodha tupu
**Ulinganishi wa Awali**: Hakikisha zana za MCP bila hoja zinaendelea kufanya kazi (kurudisha orodha tupu)
**Uundaji wa Maagizo ya Wakala**: Hakikisha maagizo ya wakala yanajumuisha maelezo ya hoja za zana ya MCP

### Vipimo vya Uunganisho
**Uteuzi wa Zana Kamili**: Mfumo wa majaribio unaweza kuendesha zana kwa kutumia hoja za zana za MCP.
**Uipakaji wa Mipangilio**: Jaribu mchakato kamili wa kupakua mipangilio kwa kutumia hoja za zana za MCP.
**Kati ya Vipengele**: Hakikisha hoja zinapitishwa vizuri kutoka kwenye mipangilio hadi katika uundaji wa zana na uundaji wa maagizo.

### Majaribio ya Kawaida
**Tabia ya Mfumo**: Angalia kwa uangalifu kama mfumo unapokea na kutumia taarifa za hoja katika mzunguko wa ReACT.
**Uunganisho wa CLI**: Jaribu kama `tg-invoke-mcp-tool` inafanya kazi na zana za MCP ambazo zimepangwa na hoja.
**Uunganisho wa Workbench**: Jaribu kama UI inasaidia upangaji wa hoja za zana za MCP.

## Uhamisho na Uanzishaji

### Mkakati wa Uhamisho
Hakuna uhamishaji unaohitajika - hii ni kipengele cha ziada:
Mipangilio ya zana za MCP iliyopo ambayo haina `arguments` inaendelea kufanya kazi bila mabadiliko.
`McpToolImpl.get_arguments()` inarudisha orodha tupu kwa zana za zamani.
Mipangilio mipya inaweza kujumuisha `arguments`.

### Mpango wa Uanzishaji
1. **Awamu ya 1**: Anzisha mabadiliko ya msingi ya mfumo kwenye eneo la maendeleo/maandalizi.
2. **Awamu ya 2**: Anzisha sasisho za zana za CLI na nyaraka.
3. **Awamu ya 3**: Anzisha sasisho za UI za Workbench kwa upangaji wa hoja.
4. **Awamu ya 4**: Uanzishaji wa uzalishaji na ufuatiliaji.

### Mpango wa Kurudisha Nyuma
Mabadiliko ya msingi yanaambatana na matoleo ya awali - hakuna haja ya kurudisha nyuma kwa utendaji.
Ikiwa matatizo yanajitokeza, zima uchanganuzi wa hoja kwa kurejesha mantiki ya kupakua mipangilio ya zana za MCP.
Mabadiliko ya Workbench na CLI yanaweza kurejeshwa kando.

## Masuala ya Usalama
**Hakuna eneo jipya la shambulio**: Hoja zinachanganzwa kutoka kwa vyanzo vya mipangilio iliyopo bila pembejeo mpya.
**Uthibitisho wa vigezo**: Hoja huhamishwa kwa zana za MCP bila mabadiliko - uthibitisho unaendelea katika kiwango cha zana za MCP.
**Uadilifu wa mipangilio**: Maelezo ya hoja ni sehemu ya upangaji wa zana - mfumo sawa wa usalama unafanya kazi.

## Athari za Utendaji
**Uongezeko mdogo**: Uchanganuzi wa hoja hufanyika tu wakati wa kupakua mipangilio, sio kwa kila ombi.
**Kukua kwa saizi ya maagizo**: Maagizo ya mfumo yatajumuisha maelezo ya hoja za zana za MCP, na hivyo kuongeza matumizi ya tokeni.
**Matumizi ya kumbukumbu**: Kuongezeka kwa kiasi kidogo kwa kuhifadhi maelezo ya hoja katika vitu vya zana.

## Nyaraka

### Nyaraka za Mtumiaji
[ ] Sasisha mwongozo wa upangaji wa zana za MCP na mifano ya hoja.
[ ] Ongeza maelezo ya hoja kwenye maandishi ya usaidizi wa zana za CLI.
[ ] Unda mifano ya muundo wa kawaida wa hoja za zana za MCP.

### Nyaraka za Mpelelezi
[ ] Sasisha nyaraka za darasa la `McpToolImpl`.
[ ] Ongeza maelezo ya ndani kwa mantiki ya uchanganuzi wa hoja.
[ ] Andika maelezo ya mtiririko wa hoja katika muundo wa mfumo.

## Maswali Yaliyofunguliwa
1. **Uthibitisho wa hoja**: Je, tunapaswa kuthibitisha aina/aina za hoja zaidi ya ukaguzi wa muundo wa msingi?
2. **Utafiti wa kiotomatiki**: Uboreshaji wa baadaye wa kuuliza seva za MCP kwa schema za zana kiotomatiki?

## Mbadala Zilizozingatiwa
1. **Utafiti wa kiotomatiki wa schema ya MCP**: Kuuliza seva za MCP kwa schema za hoja za zana wakati wa utendaji - ilikataliwa kwa sababu ya utata na wasiwasi wa kuegemea.
2. **Usajili wa kando wa hoja**: Kuhifadhi hoja za zana za MCP katika sehemu tofauti ya upangaji - ilikataliwa kwa utangamano na mbinu ya kiolezo ya maagizo.
3. **Uthibitisho wa aina**: Uthibitisho kamili wa schema ya JSON kwa hoja - imeahirishwa kama uboreshaji wa baadaye ili kuendeleza utekelezaji wa awali.

## Marejeleo
[Maelezo ya Itifaki ya MCP](https://github.com/modelcontextprotocol/spec)
[Utekelezaji wa Zana ya Kiolezo ya Maagizo](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
[Utekelezaji wa Sasa wa Zana ya MCP](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)

## Toa Maelezo
[Maelezo yoyote ya ziada, michoro, au mifano]
