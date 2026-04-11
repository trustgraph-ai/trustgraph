# MCP Tool Bearer Token Authentication Specification

> **⚠️ MUHIMU: INATUMIWA TU KWA MASHARTI MOJA**
>
> Maelezo haya yanaelezea **mfumo msingi wa uthibitishaji wa kiwango cha huduma** kwa zana za MCP. Haikuwa **suluhisho kamili** la uthibitishaji na **haifai** kwa:
> - Mazingira ya watumiaji wengi
> - Matumizi mengi ya wateja
> - Uthibitishaji uliounganishwa
> - Usambazaji wa muktadha wa mtumiaji
> - Ruhusa kwa kila mtumiaji
>
> Kipengele hiki hutoa **simu moja ya tuli kwa kila zana ya MCP**, ambayo inashirikiwa na watumiaji wote na vipindi vyote. Ikiwa unahitaji uthibitishaji kwa kila mtumiaji au kwa kila mteja, hii si suluhisho sahihi.

## Maelezo
**Jina la Kipengele**: Usaidizi wa Uthibitishaji wa Simu ya Bearer ya Zana ya MCP
**Mwandishi**: Claude Code Assistant
**Tarehe**: 2025-11-11
**Hali**: Katika Maendeleo

### Muhtasari

Ruhusu usanidi wa zana za MCP kubainisha simu za hiari za bearer kwa uthibitishaji na seva za MCP zilizolindwa. Hii inaruhusu TrustGraph kuita zana za MCP zilizohifadhiwa kwenye seva ambazo zinahitaji uthibitishaji, bila kubadilisha wakala au interfaces za kutumia zana.

**MUHIMU**: Hii ni mfumo msingi wa uthibitishaji ulioundwa kwa hali za uthibitishaji wa huduma hadi huduma kwa mteja mmoja. Haifai kwa:
Mazingira ya watumiaji wengi ambapo watumiaji tofauti wanahitaji anwani tofauti
Matumizi mengi ya wateja yanayohitaji kutengwa kwa kila mteja
Hali za uthibitishaji zilizounganishwa
Uthibitishaji au ruhusa za kiwango cha mtumiaji
Usimamizi wa anwani ya kipekee au urekebishaji wa simu

Kipengele hiki hutoa simu ya tuli, ya kimfumo kwa usanidi wa kila zana ya MCP, ambayo inashirikiwa na watumiaji wote na matumizi ya zana hiyo.

### Tatizo

Kwa sasa, zana za MCP zinaweza kuunganisha tu kwa seva za MCP zinazopatikana kwa umma. Matumizi mengi ya uzalishaji ya MCP yanahitaji uthibitishaji kupitia simu za bearer kwa usalama. Bila usaidizi wa uthibitishaji:
Zana za MCP haziwezi kuunganisha kwa seva za MCP zilizolindwa
Watumiaji lazima iweze kufungua seva za MCP kwa umma au kutumia viboreshaji vya kurudi nyuma
Hakuna njia iliyoanzishwa ya kupitisha anwani kwa miunganisho ya MCP
Mazoea bora ya usalama hayawezi kutekelezwa kwenye mwisho wa MCP

### Lengo

[ ] Ruhusu usanidi wa zana za MCP kubainisha parameter ya `auth-token` ya hiari
[ ] Sasisha huduma ya zana ya MCP ili itumie simu za bearer wakati inapo na seva za MCP
[ ] Sasisha zana za CLI ili kusaidia kuweka/kuonyesha anwani
[ ] Dumishe utangamano wa nyuma na usanidi usio na uthibitishaji wa MCP
[ ] Andika masuala ya usalama ya uhifadhi wa simu

### Lengo Lisilofikiwa
Urekebishaji wa simu ya kipekee au mtiririko wa OAuth (simu za tuli tu)
Usifungishaji wa simu zilizohifadhiwa (usalama wa mfumo wa usanidi uko nje ya wigo)
Njia zingine za uthibitishaji (uthibitishaji wa Msingi, ufunguo wa API, n.k.)
Uthibitishaji au ukaguzi wa kumalizika wa simu
**Uthibitishaji wa kila mtumiaji**: Kipengele hiki hakisaidii anwani maalum za mtumiaji
**Kutengwa kwa mteja mwingi**: Kipengele hiki hakutoa usimamizi wa simu kwa kila mteja
**Uthibitishaji uliounganishwa**: Kipengele hiki hakujumuisha na watoa utambulisho (SSO, OAuth, SAML, n.k.)
**Uthibitishaji unaohusiana na muktadha**: Simu hazipitishwe kulingana na muktadha wa mtumiaji au kikao

## Asili na Mfumo

### Hali ya Sasa
Usanidi wa zana za MCP huhifadhiwa katika kikundi cha usanidi cha `mcp` na muundo huu:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

Huduma ya zana ya MCP inaunganisha na seva kwa kutumia `streamablehttp_client(url)` bila vichwa vya uthibitishaji.

### Marekebisho

**Marekebisho ya Sasa ya Mfumo:**
1. **Hakuna usaidizi wa uthibitishaji**: Haiwezi kuunganisha na seva za MCP zilizolindwa.
2. **Ufafanuzi wa usalama**: Seva za MCP lazima ziwe zinapatikana kwa umma au zitumie usalama wa kiwango cha mtandao pekee.
3. **Matatizo ya matumizi katika mazingira ya uzalishaji**: Haiwezi kufuata mbinu bora za usalama kwa vidokezo vya API.

**Marekebisho ya Suluhisho Hili:**
1. **Kwa watumiaji mmoja tu**: Ishara moja ya tuli kwa kila zana ya MCP, inayoshirikiwa na watumiaji wote.
2. **Hakuna anwani za mtumiaji binafsi**: Haiwezi kuthibitisha kama watumiaji tofauti au kupitisha muktadha wa mtumiaji.
3. **Hakuna usaidizi wa watumiaji wengi**: Haiwezi kutenganisha anwani kwa kila mhakiki au shirika.
4. **Ishara za tuli tu**: Hakuna usaidizi kwa sasisho, mzunguko, au utunzaji wa kumalizika kwa ishara.
5. **Uthibitishaji wa huduma**: Inathibitisha huduma ya TrustGraph, sio watumiaji binafsi.
6. **Muktadha wa usalama unaoshirikiwa**: Matumizi yote ya zana ya MCP hutumia anwani sawa.

### Ufaa wa Matumizi

**✅ Matumizi Yanayofaa:**
Uwekaji wa TrustGraph kwa watumiaji mmoja.
Uthibitishaji kutoka kwa huduma hadi huduma (TrustGraph → Seva ya MCP).
Mazingira ya maendeleo na majaribio.
Zana za ndani za MCP zinazopatikana na mfumo wa TrustGraph.
Matukio ambamo watumiaji wote wana kiwango sawa cha ufikiaji wa zana ya MCP.
Anwani za huduma za tuli, za muda mrefu.

**❌ Matumizi Yasiyofaa:**
Mifumo ya watumiaji wengi inayohitaji uthibitishaji wa kila mtumiaji.
Uwekaji wa SaaS wa watumiaji wengi wenye mahitaji ya kutenganisha kila mhakiki.
Matukio ya uthibitishaji uliounganishwa (SSO, OAuth, SAML).
Mifumo inayohitaji kupitisha muktadha wa mtumiaji kwa seva za MCP.
Mazingira yanayohitaji sasisho za ishara za nguvu au ishara za muda mfupi.
Programu ambamo watumiaji tofauti wanahitaji viwango tofauti vya ruhusa.
Mahitaji ya utiifu kwa njia za ukaguzi za kiwango cha mtumiaji.

**Mfano wa Matumizi Yanayofaa:**
Uwekaji wa TrustGraph wa shirika moja ambamo wafanyakazi wote hutumia zana sawa ya ndani ya MCP (k.m., utafutaji wa hifadhi ya kampuni). Seva ya MCP inahitaji uthibitishaji ili kuzuia ufikiaji wa nje, lakini watumiaji wote wa ndani wana kiwango sawa cha ufikiaji.

**Mfano wa Matumizi Yasiyofaa:**
Jukwaa la SaaS la TrustGraph la watumiaji wengi ambamo Mhakiki A na Mhakiki B kila mmoja anahitaji kufikia seva zao zilizotenganishwa za MCP na anwani tofauti. Kipengele hiki hakitumii usimamizi wa anwani wa kila mhakiki.

### Vipengele Vinavyohusiana
**trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: Huduma ya utekelezaji wa zana ya MCP.
**trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: Zana ya CLI ya kuunda/kusasisha mipangilio ya MCP.
**trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: Zana ya CLI ya kuonyesha mipangilio ya MCP.
**SDK ya Python ya MCP**: `streamablehttp_client` kutoka `mcp.client.streamable_http`

## Mahitaji

### Mahitaji ya Kifaa

1. **Ishara ya Uthibitishaji ya Mipangilio ya MCP**: Mipangilio ya zana ya MCP INAWEZA kuwa na `auth-token`.
2. **Matumizi ya Ishara ya Bearer**: Huduma ya zana ya MCP INAWEZA kutuma `Authorization: Bearer {token}` wakati ishara ya uthibitishaji imewekwa.
3. **Usaidizi wa CLI**: `tg-set-mcp-tool` INAWEZA kukubali parameter ya `--auth-token`.
4. **Uonyesho wa Ishara**: `tg-show-mcp-tools` INAWEZA kuonyesha wakati ishara ya uthibitishaji imewekwa (imeficha kwa usalama).
5. **Ulinganishaji na Mifumo ya Zamani**: Mipangilio ya zana ya MCP iliyopo bila uthibitishaji INAWEZA kuendelea kufanya kazi.

### Mahitaji Yasiyo ya Kifaa
1. **Ulinganishaji na Mifumo ya Zamani**: Hakuna mabadiliko yoyote yanayoweza kusababisha migogoro kwa mipangilio ya zana ya MCP iliyopo.
2. **Utendaji**: Hakuna athari kubwa ya utendaji kwenye utekelezaji wa zana ya MCP.
3. **Usalama**: Anwani zinaohifadhiwa katika mipangilio (angalia masuala ya usalama).

### Hadithi za Mtumiaji

1. Kama **mhandisi wa DevOps**, ningependa kusanidi anwani za bearer kwa zana za MCP ili niweze kulinda vidokezo vya seva za MCP.
2. Kama **mtumiaji wa CLI**, ningependa kuweka anwani za uthibitishaji wakati ninaunda zana za MCP ili niweze kuunganisha na seva zilizolindwa.
3. Kama **mhasibu wa mfumo**, ningependa kuona zana gani za MCP zilizosanidiwa na uthibitishaji ili niweze kukagua mipangilio ya usalama.

## Muundo

### Muundo wa Juu
Panua mipangilio ya zana ya MCP na huduma ili kusaidia uthibitishaji wa ishara ya bearer:
1. Ongeza `auth-token` kwenye schema ya mipangilio ya zana ya MCP.
2. Badilisha huduma ya zana ya MCP ili kusoma ishara ya uthibitishaji na kuipitisha kwa mteja wa HTTP.
3. Sasisha zana za CLI ili kusaidia kuweka na kuonyesha anwani za uthibitishaji.
4. Andika masuala ya usalama na mbinu bora.

### Schema ya Mipangilio

**Schema ya Sasa**:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**Mfumo Mpya** (na ishara ya uthibitisho ya hiari):
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Maelezo ya Kila Kila Nyanja:**
`remote-name` (hiari): Jina linalotumika na seva ya MCP (linalotumika kiotomatiki kama funguo ya usanidi)
`url` (lazima): URL ya mwisho wa seva ya MCP
`auth-token` (hiari): Alama ya "Bearer" kwa uthibitishaji

### Mtiririko wa Data

1. **Hifadhi ya Usanidi:** Mtumiaji huanzisha `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`
2. **Upakiaji wa Usanidi:** Huduma ya zana ya MCP hupokea sasisho la usanidi kupitia mjumuko wa `on_mcp_config()`
3. **Uanzishaji wa Zana:** Wakati zana inaanzishwa:
   Huduma husoma `auth-token` kutoka usanidi (ikiwa ipo)
   Huunda kamusi ya vichwa: `{"Authorization": "Bearer {token}"}`
   Hutuma vichwa kwa `streamablehttp_client(url, headers=headers)`
   Seva ya MCP huangalia alama na kutoa ombi

### Mabadiliko ya API
Hakuna mabadiliko ya API ya nje - mabadiliko ya muundo wa usanidi tu.

### Maelezo ya Vipengele

#### Kipengele 1: service.py (Huduma ya Zana ya MCP)
**Faili:** `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**Lengo:** Kuendesha zana za MCP kwenye seva za mbali

**Mabadiliko Yanayohitajika** (katika njia ya `invoke_tool()`):
1. Angalia `auth-token` katika usanidi wa `self.mcp_services[name]`
2. Jenga kamusi ya vichwa na kichwa cha "Authorization" ikiwa alama ipo
3. Tuma vichwa kwa `streamablehttp_client(url, headers=headers)`

**Msimbo Sasa** (mistari 42-89):
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**Msimbo Uliorekebishwa**:
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### Sehemu ya 2: set_mcp_tool.py (Zana ya Usanidi wa CLI)
**Faili**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**Madhumuni**: Kuunda/kusasisha usanidi wa zana ya MCP

**Mabadiliko Yanayohitajika**:
1. Ongeza sajili ya `--auth-token` ya hiari kwa argparse
2. Jumuisha `auth-token` katika JSON ya usanidi wakati inatolewa

**Sajili za Sasa**:
`--id` (lazima): Kitambulisho cha zana ya MCP
`--remote-name` (ya hiari): Jina la zana ya MCP ya mbali
`--tool-url` (lazima): Ncha ya URL ya zana ya MCP
`-u, --api-url` (ya hiari): URL ya API ya TrustGraph

**Sajili Mpya**:
`--auth-token` (ya hiari): Alama ya "Bearer" kwa uthibitishaji

**Ujenzi wa Usanidi Uliobadilishwa**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### Sehemu ya 3: show_mcp_tools.py (Chombo cha Kuonyesha Kwenye Kamba)
**Faili**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**Madhumuni**: Kuonyesha usanidi wa chombo cha MCP

**Mabadiliko Yanayohitajika**:
1. Ongeza safu ya "Auth" kwenye meza ya pato
2. Onyesha "Ndiyo" au "Hapana" kulingana na uwepo wa ishara ya uthibitishaji (auth-token)
3. Usionyeshe thamani halisi ya ishara (usalama)

**Pato Lililopo Sasa**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**Pato Jipya**:
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### Sehemu ya 4: Nyaraka
**Faili**: `docs/cli/tg-set-mcp-tool.md`

**Mabadiliko Yanayohitajika**:
1. Andika nyaraka kwa parameter mpya ya `--auth-token`
2. Toa mfano wa matumizi na uthibitishaji
3. Andika masuala ya usalama

## Mpango wa Utendaji

### Awamu ya 1: Unda Vipimo vya Kisaikolojia
[x] Andika vipimo vya kisaikolojia vya kina ambavyo vinadokeza mabadiliko yote

### Awamu ya 2: Sasisha Huduma ya Zana ya MCP
[ ] Badilisha `invoke_tool()` katika `service.py` ili kusoma `auth-token` kutoka kwa usanidi
[ ] Jenga kamusi ya vichwa na uipitisha kwa `streamablehttp_client`
[ ] Jaribu na seva ya MCP iliyo na uthibitishaji

### Awamu ya 3: Sasisha Zana za CLI
[ ] Ongeza hoja ya `--auth-token` kwa `set_mcp_tool.py`
[ ] Jumuisha `auth-token` katika usanidi wa JSON
[ ] Ongeza safu ya "Auth" kwenye pato la `show_mcp_tools.py`
[ ] Jaribu mabadiliko ya zana ya CLI

### Awamu ya 4: Sasisha Nyaraka
[ ] Andika `--auth-token` katika `tg-set-mcp-tool.md`
[ ] Ongeza sehemu ya masuala ya usalama
[ ] Toa mfano wa matumizi

### Awamu ya 5: Majaribio
[ ] Jaribu zana ya MCP na `auth-token` inaunganisha kwa ufanisi
[ ] Jaribu utangamano wa nyuma (zana bila `auth-token` zinaendelea kufanya kazi)
[ ] Jaribu zana za CLI hupokea na kuhifadhi `auth-token` kwa usahihi
[ ] Jaribu amri ya "Onyesha" inaonyesha hali ya uthibitishaji kwa usahihi

### Muhtasari wa Mabadiliko ya Msimbo
| Faili | Aina ya Mabadiliko | Mistari | Maelezo |
|------|------------|-------|-------------|
| `service.py` | Imebadilishwa | ~52-66 | Ongeza usomaji wa `auth-token` na ujenzi wa vichwa |
| `set_mcp_tool.py` | Imebadilishwa | ~30-60 | Ongeza hoja ya `--auth-token` na uhifadhi wa usanidi |
| `show_mcp_tools.py` | Imebadilishwa | ~40-70 | Ongeza safu ya Uthibitishaji kwenye onyesho |
| `tg-set-mcp-tool.md` | Imebadilishwa | Mbalimbali | Andika parameter mpya |

## Mkakati wa Majaribio

### Majaribio ya Kitengo
**Usomaji wa Tokeni ya Uthibitishaji**: Jaribu `invoke_tool()` husoma `auth-token` kwa usahihi kutoka kwa usanidi
**Ujenzi wa Vichwa**: Jaribu vichwa vya Ruhusa vinajengwa kwa usahihi na mbele ya `Bearer`
**Utangamano wa Nyuma**: Jaribu zana bila `auth-token` zinafanya kazi bila mabadiliko
**Uchanganuzi wa Hoja ya CLI**: Jaribu hoja ya `--auth-token` inachanganzwa kwa usahihi

### Majaribio ya Uunganisho
**Uunganisho Ulio na Uthibitishaji**: Jaribu huduma ya zana ya MCP inaunganisha na seva iliyo na uthibitishaji
**Kila kitu**: Jaribu CLI → uhifadhi wa usanidi → utekelezaji wa huduma na `auth token`
**Tokeni Haihitajiki**: Jaribu uunganisho na seva isiyo na uthibitishaji unaendelea kufanya kazi

### Majaribio ya Kawaida
**Seva Halisi ya MCP**: Jaribu na seva halisi ya MCP inayohitaji uthibitishaji wa `bearer token`
**Mwendo wa CLI**: Jaribu mwendo kamili: weka zana na uthibitishaji → fanya kazi ya zana → thibitisha mafanikio
**Kuficha Kuonyesha**: Thibitisha hali ya uthibitishaji inaonyeshwa lakini thamani ya tokeni haijaonyeshwa

## Uhamishaji na Utoaji

### Mkakati wa Uhamishaji
Hakuna uhamishaji unaohitajika - hii ni utendakazi wa ziada:
Usanidi wa zana ya MCP iliyopo bila `auth-token` inaendelea kufanya kazi bila mabadiliko
Usanidi mpya unaweza kujumuisha sehemu ya `auth-token`
Zana za CLI hupokea lakini hazihitaji parameter ya `--auth-token`

### Mpango wa Utoaji
1. **Awamu ya 1**: Toa mabadiliko ya msingi ya huduma kwa maendeleo/maandalizi
2. **Awamu ya 2**: Toa sasisho za zana za CLI
3. **Awamu ya 3**: Sasisha nyaraka
4. **Awamu ya 4**: Utoaji wa uzalishaji na ufuatiliaji

### Mpango wa Kurudisha Nyuma
Mabadiliko ya msingi yana utangamano wa nyuma - zana zilizopo hazipatiwa madhara
Ikiwa matatizo yanajitokeza, utunzaji wa `auth-token` unaweza kuzimwa kwa kuondoa mantiki ya ujenzi wa vichwa
Mabadiliko ya zana za CLI ni huru na yanaweza kurejeshwa kando

## Masuala ya Usalama

### ⚠️ Kikomo Muhimu: Uthibitishaji wa Mfumo Mmoja Tu

**Mfumo huu wa uthibitishaji haufai kwa mazingira ya watumiaji wengi au ya wateja wengi.**

**Anwani zilizoshirikiwa**: Watumiaji wote na matumizi yote huongea tokeni moja kwa kila zana ya MCP
**Hakuna muktadha wa mtumiaji**: Seva ya MCP haiwezi kutofautisha kati ya watumiaji tofauti wa TrustGraph
**Hakuna kutengwa kwa mteja**: Wateja wote huongea anwani sawa kwa kila zana ya MCP
**Kizuia cha ukaguzi**: Seva ya MCP inaonyesha maombi yote kutoka kwa anwani sawa
**Nguvu za idhini**: Haiwezi kutekeleza viwango tofauti vya idhini kwa watumiaji tofauti

**Usitumie kipengele hiki ikiwa:**
Umechanganya mashirika mengi
Unahitaji uthibitishaji wa mtu binafsi
Unahitaji uthibitishaji wa muda
Unahitaji uthibitishaji wa mteja mmoja


**Suluhisho mbadala kwa matukio ya watumiaji wengi/watu wengi:**
Tengeneza usambazaji wa muktadha wa mtumiaji kupitia vichwa maalum
Weka mifumo tofauti ya TrustGraph kwa kila mtoa huduma
Tumia utengano wa kiwango cha mtandao (VPCs, huduma za mtandao)
Tengeneza safu ya wakala inayoshughulikia uthibitishaji wa kila mtumiaji

### Uhifadhi wa Tokeni
**Hatari**: Tokeni za uthibitishaji zimehifadhiwa kwa maandishi wazi katika mfumo wa usanidi

**Hatua za kuzuia**:
Andika kwamba tokeni zimehifadhiwa bila usimbaji
Pendekeza kutumia tokeni za muda mfupi inapowezekana
Pendekeza udhibiti sahihi wa ufikiaji kwenye hifadhi ya usanidi
Fikiria uboreshaji wa baadaye kwa uhifadhi uliosimbwa wa tokeni

### Uonyeshaji wa Tokeni
**Hatari**: Tokeni zinaweza kuonyeshwa katika arifa au pato la CLI

**Hatua za kuzuia**:
Usiandike maadili ya tokeni (andika tu "uthibitishaji umeanzishwa: ndiyo/hapana")
Amri ya CLI ya kuonyesha inaonyesha hali iliyofichwa tu, sio tokeni halisi
Usijumuishe tokeni katika ujumbe wa hitilafu

### Usalama wa Mtandao
**Hatari**: Tokeni zinafutwa kupitia miunganisho isiyo salama

**Hatua za kuzuia**:
Andika pendekezo la kutumia URL za HTTPS kwa seva za MCP
Onya watumiaji kuhusu hatari ya usambazaji wa maandishi wazi na HTTP

### Ufikiaji wa Usanidi
**Hatari**: Ufikiaji usioidhinishwa kwa mfumo wa usanidi unaoonyesha tokeni

**Hatua za kuzuia**:
Andika umuhimu wa kuhakikisha ufikiaji wa mfumo wa usanidi
Pendekeza kanuni ya madaraka madogo kwa ufikiaji wa usanidi
Fikiria uandikaji wa matukio kwa mabadiliko ya usanidi (uboresho wa baadaye)

### Mazingira ya Watumiaji Wengi
**Hatari**: Katika matukio ya watumiaji wengi, watumiaji wote wanashiriki anwani sawa za MCP

**Kuelewa Hatari**:
Mtumiaji A na Mtumiaji B hutumia tokeni sawa wakati wa kufikia zana ya MCP
Seva ya MCP haiwezi kutofautisha kati ya watumiaji tofauti wa TrustGraph
Hakuna njia ya kutekeleza ruhusa au mipaka ya kiwango cha mtumiaji
Arifa kwenye seva ya MCP zinaonyesha maombi yote kutoka kwa anwani sawa
Ikiwa kikao cha mtumiaji mmoja kimebanwa, mshambuliaji ana ufikiaji sawa wa MCP kama watumiaji wote

**HII SI hitilafu - ni kikomo cha msingi cha muundo huu.**

## Athari ya Utendaji
**Mzigo mdogo**: Ujenzi wa kichwa unaongeza muda mdogo wa usindikaji
**Athari ya mtandao**: Kichwa cha ziada cha HTTP huongeza ~50-200 baiti kwa ombi
**Matumizi ya kumbukumbu**: Kuongezeka kwa kiasi kidogo kwa kuhifadhi mnyororo wa tokeni katika usanidi

## Nyaraka

### Nyaraka za Mtumiaji
[ ] Sasisha `tg-set-mcp-tool.md` na parameter ya `--auth-token`
[ ] Ongeza sehemu ya mambo ya usalama
[ ] Toa mfano wa matumizi na tokeni ya mfuata
[ ] Andika madhumuni ya uhifadhi wa tokeni

### Nyaraka za Msanidi Programu
[ ] Ongeza maelezo ya ndani kwa usimamizi wa tokeni ya uthibitishaji katika `service.py`
[ ] Andika mantiki ya ujenzi wa kichwa
[ ] Sasisha nyaraka za schema ya usanidi ya zana ya MCP

## Maswali ya Funguo
1. **Usimbaji wa tokeni**: Je, tunapaswa kutekeleza uhifadhi uliosimbwa wa tokeni katika mfumo wa usanidi?
2. **Urekebishaji wa tokeni**: Usaidizi wa siku zijazo kwa mtiririko wa OAuth wa urekebishaji au mzunguko wa tokeni?
3. **Njia mbadala za uthibitishaji**: Je, tunapaswa kusaidia uthibitishaji wa Msingi, ufunguo wa API, au mbinu zingine?

## Mbadala Zilizozingatiwa

1. **Vigezo vya mazingira kwa tokeni**: Hifadhi tokeni katika vigezo vya mazingira badala ya usanidi
   **Ilikataliwa**: Inachanganya usakinishaji na usimamizi wa usanidi

2. **Hifadhi ya siri tofauti**: Tumia mfumo maalum wa usimamizi wa siri
   **Imeahirishwa**: Nje ya upeo wa utekelezaji wa awali, fikiria uboreshaji wa siku zijazo

3. **Njia nyingi za uthibitishaji**: Kusaidia Msingi, ufunguo wa API, OAuth, n.k.
   **Ilikataliwa**: Tokeni za mfuata hufunika matumizi mengi, endeleza utekelezaji wa awali rahisi

4. **Uhifadhi uliosimbwa wa tokeni**: Simba tokeni katika mfumo wa usanidi
   **Imeahirishwa**: Usalama wa mfumo wa usanidi ni suala pana, chelewesha hadi kazi ya baadaye

5. **Tokeni za kila utendaji**: Ruhusu tokeni kupitishwa wakati wa utendaji
   **Ilikataliwa**: Inakiuka utengano wa masuala, wakala haupaswi kushughulikia anwani

## Marejeleo
[Maelezo ya Protokali ya MCP](https://github.com/modelcontextprotocol/spec)
[Uthibitishaji wa Mfuata wa HTTP (RFC 6750)](https://tools.ietf.org/html/rfc6750)
[Huduma ya Zana ya MCP ya Sasa](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
[Maelezo ya Majadilisho ya Zana ya MCP](./mcp-tool-arguments.md)

## Toa Maelezo

### Matumizi ya Kifaa

**Kuanzisha zana ya MCP pamoja na uthibitishaji:**
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Kuonyesha zana za MCP**:
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### Mfano wa Usanidi

**Imehifadhiwa katika mfumo wa usanidi:**
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### Mbinu Bora za Usalama

1. **Tumia HTTPS**: Daima tumia anwani za mtandao (URLs) za HTTPS kwa seva za MCP zenye uthibitishaji.
2. **Alama za muda mfupi**: Tumia alama (tokens) zenye muda wa kumalizika unapowezekana.
3. **Haki ndogo zaidi**: Toa alama ruhusa ndogo zaidi zinazohitajika.
4. **Kidhibiti cha ufikiaji**: Punguza ufikiaji kwenye mfumo wa usanidi.
5. **Kubadilisha alama**: Badilisha alama mara kwa mara.
6. **Uandikaji wa matukio**: Fuatilia mabadiliko ya usanidi ili kutambua matukio ya usalama.
