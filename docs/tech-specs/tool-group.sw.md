# Mfumo wa Kikundi cha Zana za TrustGraph
## Maelezo ya Kiufundi v1.0

### Muhtasari

Maelezo haya yanafafanua mfumo wa kuunganisha zana kwa wakala wa TrustGraph ambao huruhusu udhibiti wa kina kuhusu zana zipi zinazopatikana kwa ombi fulani. Mfumo huu huleta uchujaji wa zana unaotegemea kikundi kupitia usanidi na maelezo ya ombi, na hivyo kuwezesha mipaka bora ya usalama, usimamizi wa rasilimali, na ugawaji wa kazi wa uwezo wa wakala.

### 1. Muhtasari

#### 1.1 Tatizo

Kwa sasa, wakala wa TrustGraph wana uwezo wa kutumia zana zote zilizosanidiwa, bila kujali muktadha wa ombi au mahitaji ya usalama. Hii huleta changamoto kadhaa:

**Hatari ya Usalama**: Zana nyeti (k.m., uhariri wa data) zinapatikana hata kwa maswali ya kusoma tu.
**Uharibifu wa Rasilimali**: Zana ngumu huzingirwa hata wakati maswali rahisi hayahitaji.
**Uchanganyifu wa Kazi**: Wakala wanaweza kuchagua zana zisizofaa wakati mbadala rahisi zipo.
**Tenganisho la Wafanyabiashara Wengi**: Makundi tofauti ya watumiaji yanahitaji ufikiaji wa seti tofauti za zana.

#### 1.2 Muhtasari wa Suluhisho

Mfumo wa kikundi cha zana huleta:

1. **Uainishaji wa Kikundi**: Zana huwekwa alama na uanachama wa kikundi wakati wa usanidi.
2. **Uchujaji wa Kwenye Ombi**: Ombi la Wakala (AgentRequest) linaonyesha ambayo makundi ya zana yanaruhusiwa.
3. **Utendaji wa Wakati Halisi**: Wakala wana uwezo wa kutumia zana zinazolingana na makundi yaliyoomba.
4. **Uunganishaji Wenye Ugumu**: Zana zinaweza kuwa katika makundi mengi kwa hali ngumu.

### 2. Mabadiliko ya Muundo

#### 2.1 Ongezeko la Muundo wa Usanidi wa Zana

Usanidi wa zana uliopo umeongezwa na sehemu `group`:

**Kabla:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**Baada ya:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**Maelezo ya Kundi:**
`group`: Array(String) - Orodha ya vikundi ambavyo zana hii inahusishwa nayo.
**Hiari:** Zana ambazo hazina uwanja wa kundi huenda katika kundi "linaloepuka".
**Uanachama wa mengi:** Zana zinaweza kuhusishwa na vikundi vingi.
**Huwezi kubadilishwa (Case-sensitive):** Majina ya vikundi ni mechi kamili ya herufi.

#### 2.1.2 Kuboresha Mabadiliko ya Hali ya Zana

Zana zinaweza, kwa hiari, kutaja mabadiliko ya hali na upatikanaji unaotegemea hali:

```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"],
  "state": "analysis",
  "available_in_states": ["undefined", "research"]
}
```

**Maelezo ya Kikoa:**
`state`: String - **Hiari** - Hali ya kuhamia baada ya utekelezaji wa zana.
`available_in_states`: Array(String) - **Hiari** - Hali ambazo zana hii inapatikana.
**Tabia ya kawaida**: Zana ambazo hazina `available_in_states` zinapatikana katika hali zote.
**Mabadiliko ya hali**: Hutokea tu baada ya utekelezaji wa zana.

#### 2.2 Uboreshaji wa Mfumo wa AgentRequest

Mfumo wa `AgentRequest` katika `trustgraph-base/trustgraph/schema/services/agent.py` umeboreshwa:

**AgentRequest ya Sasa:**
`question`: String - Uliza wa mtumiaji.
`plan`: String - Mpango wa utekelezaji (unaweza kuondolewa).
`state`: String - Hali ya wakala.
`history`: Array(AgentStep) - Historia ya utekelezaji.

**AgentRequest Iliyoboreshwa:**
`question`: String - Uliza wa mtumiaji.
`state`: String - Hali ya utekelezaji wa wakala (sasa inatumika kikamilifu kwa kuchuja zana).
`history`: Array(AgentStep) - Historia ya utekelezaji.
`group`: Array(String) - **MPYA** - Vikundi vya zana ambavyo vinaruhusiwa kwa ombi hili.

**Mabadiliko ya Mfumo:**
**Imeondolewa**: Uwanja wa `plan` hauhitajiki tena na unaweza kuondolewa (hapo awali ulikuwa umekusudiwa kwa vipimo vya zana).
**Imeongezwa**: Uwanja wa `group` kwa vipimo vya kikundi cha zana.
**Imeboreshwa**: Uwanja wa `state` sasa unadhibiti upatikanaji wa zana wakati wa utekelezaji.

**Tabia za Uwanja:**

**Kikundi cha Uwanja:**
**Hiari**: Ikiwa haijaainishwa, huanguka kwenye ["default"].
**Uunganishaji**: Zana zinazofanana na angalau kikundi kilichoainishwa ndizo zinazopatikana.
**Safisha ya tupu**: Hakuna zana zinazopatikana (wakala anaweza kutumia tu utafakari wa ndani).
**Kikundi cha "Wildcard"**: Kikundi maalum "*" kinatoa ufikiaji kwa zana zote.

**Uwanja wa Hali:**
**Hiari**: Ikiwa haijaainishwa, huanguka kwenye "haijulikani".
**Uchujaji wa msingi wa hali**: Zana zinazopatikana katika hali ya sasa ndizo zinazoweza kutumika.
**Hali ya kawaida**: Hali ya "haijulikani" inaruhusu zana zote (kulingana na uchujaji wa kikundi).
**Mabadiliko ya hali**: Zana zinaweza kubadilisha hali baada ya utekelezaji wa mafanikio.

### 3. Mifano ya Kikundi Maalum

Mashirika yanaweza kuainisha vikundi maalum ya kikoa:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. Maelezo ya Utendaji

#### 4.1 Kupakia na Kuchuja Vifaa

**Awamu ya Usanidi:**
1. Vifaa vyote hupakuliwa kutoka usanidi pamoja na uamlisho wao wa kundi.
2. Vifaa visivyokuwa na uamlisho wa kundi wanakabidhiwa kwenye kundi la "default".
3. Uanachama wa kundi huthibitishwa na kuhifadhiwa kwenye rejista ya vifaa.

**Awamu ya Usimamizi wa Ombi:**
1. Ombi la Wakala (AgentRequest) linafika pamoja na maelezo ya kundi (group) ambayo ni ya hiari.
2. Wakala huchuja vifaa vinavyopatikana kulingana na msalaba wa makundi.
3. Vifaa vinavyolingana pekee hupitishwa kwa muktadha wa utekelezaji wa wakala.
4. Wakala hutumia seti ya vifaa vilivyochujwa katika mchakato wote wa ombi.

#### 4.2 Mantiki ya Kuchuja Vifaa

**Kuchuja kwa Pamoja kwa Kundi na Hali:**

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  tool_states = tool.available_in_states || ["*"]  // Available in all states
  
For each request:
  requested_groups = request.group || ["default"]
  current_state = request.state || "undefined"
  
Tool is available if:
  // Group filtering
  (intersection(tool_groups, requested_groups) is not empty OR "*" in requested_groups)
  AND
  // State filtering  
  (current_state in tool_states OR "*" in tool_states)
```

**Mantiki ya Mabadiliko ya Hali:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 Maeneo ya Uunganisho wa Mwakala

**Mwakala wa ReAct:**
Uchujaji wa zana hufanyika katika `agent_manager.py` wakati wa uundaji wa usajili wa zana.
Orodha ya zana zinazopatikana huchujwa na kikundi na hali kabla ya utayarishaji wa mpango.
Mabadiliko ya hali husasisha sehemu `AgentRequest.state` baada ya utekelezaji wa zana kwa mafanikio.
Iteration inayofuata hutumia hali iliyosasishwa kwa uchujaji wa zana.

**Mwakala Kulingana na Umoja wa Maoni:**
Uchujaji wa zana hufanyika katika `planner.py` wakati wa utayarishaji wa mpango.
Uthibitisho wa `ExecutionStep` huhakikisha kuwa zana zinazofaa tu za kikundi na hali hutumiwa.
Kidhibiti cha mtiririko huweka upatikanaji wa zana wakati wa utendakazi.
Mabadiliko ya hali yanadhibitiwa na Kidhibiti cha Mtiririko kati ya hatua.

### 5. Mifano ya Usanidi

#### 5.1 Usanidi wa Zana na Vikundi na Hali

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    state: "analysis"
    available_in_states: ["undefined", "research"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    available_in_states: ["analysis", "modification"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    state: "undefined"
    # No available_in_states = available in all states
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    state: "results"
    available_in_states: ["analysis"]
    mcp_tool_id: "analysis-server"
    
  reset-workflow:
    type: mcp-tool
    name: "Reset Workflow"
    description: "Reset to initial state"
    group: ["admin"]
    state: "undefined"
    available_in_states: ["analysis", "results"]
```

#### 5.2 Mifano ya Maombi na Mchakato wa Kazi wa Jimbo

**Maombi ya Uchunguzi wa Mwanzo:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*Vifaa vinavyopatikana: knowledge-query, text-completion*
*Baada ya knowledge-query: hali → "uchambuzi"*

**Awamu ya Uchambuzi:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*Vifaa vinavyopatikana: uchambuzi-wa-mazingo, sasisho-la-picha, upya-mchakato*
*Baada ya uchambuzi-wa-mazingo: hali → "matokeo"*

**Awamu ya Matokeo:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*Vifaa vinavyopatikana: reset-workflow pekee*
*Baada ya reset-workflow: hali → "haijulikani"*

**Mfano wa Mchakato - Mchakato Kamili:**
1. **Anza (haijulikani)**: Tumia utafutaji wa maarifa → mabadiliko hadi "uchambuzi"
2. **Hali ya uchambuzi**: Tumia uchambuzi tata → mabadiliko hadi "matokeo"
3. **Hali ya matokeo**: Tumia reset-workflow → mabadiliko kurudi "haijulikani"
4. **Kurudi kwenye mwanzo**: Vifaa vyote vya awali vinapatikana tena

### 6. Masuala ya Usalama

#### 6.1 Uunganisho wa Udhibiti wa Ufikiaji

**Uchujaji wa Kawaida ya Mawasiliano:**
Kawaida ya mawasiliano inaweza kutekeleza vizuizi vya kikundi kulingana na ruhusa za mtumiaji
Kuzuia ongezeko la madaraka kupitia ubadilishaji wa ombi
Rekodi ya ukaguzi inajumuisha vikundi vya vifaa vilivyoomba na vilivyokabidhiwa

**Mfano wa Mantiki ya Kawaida ya Mawasiliano:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 Ukaguzi na Ufuatiliaji

**Ukaguzi Ulioboreshwa:**
Kurekodi vikundi vya zana vilivyoomba na hali ya awali kwa kila ombi
Kufuatilia mabadiliko ya hali na matumizi ya zana kwa kila kundi
Kufuatilia majaribio ya kupata vikundi bila ruhusa na mabadiliko ya hali yasiyofaa
Kutoa arifa kuhusu mifumo isiyo ya kawaida ya matumizi ya kundi au mchakato wa hali unaotishiwa

### 7. Mkakati wa Uhamisho

#### 7.1 Ulinganifu na Mifumo ya Zamani

**Awamu ya 1: Mabadiliko ya Ongezeko**
Ongeza sehemu ya `group` ya hiari kwenye usanidi wa zana
Ongeza sehemu ya `group` ya hiari kwenye schema ya AgentRequest
Tabia ya chagu ya: Zana zote zilizopo zinahusishwa na kundi "linalingana"
Maombi yaliyopo bila sehemu ya kundi hutumia kundi "linalingana"

**Tabia Zilizopo Zinahifadhiwa:**
Zana ambazo hazina usanidi wa kundi zinaendelea kufanya kazi (kundi linalingana)
Zana ambazo hazina usanidi wa hali zinapatikana katika hali zote
Maombi ambayo hayajainisha kundi hupata zana zote (kundi linalingana)
Maombi ambayo hayajainisha hali hutumia hali "isiyojulikana" (zana zote zinapatikana)
Hakuna mabadiliko yanayoweza kusababisha hitilafu katika matumizi yaliyopo

### 8. Ufuatiliaji na Uonevu

#### 8.1 Vipimo Vipya

**Matumizi ya Kundi la Zana:**
`agent_tool_group_requests_total` - Idadi ya maombi kwa kila kundi
`agent_tool_group_availability` - Kiwango cha zana zinazopatikana kwa kila kundi
`agent_filtered_tools_count` - Jadili ya idadi ya zana baada ya kuchujwa kwa kundi na hali

**Vipimo vya Mchakato wa Hali:**
`agent_state_transitions_total` - Idadi ya mabadiliko ya hali kwa kila zana
`agent_workflow_duration_seconds` - Jadili ya muda uliotumika katika kila hali
`agent_state_availability` - Kiwango cha zana zinazopatikana kwa kila hali

**Vipimo vya Usalama:**
`agent_group_access_denied_total` - Idadi ya upataji usioidhinishwa wa kundi
`agent_invalid_state_transition_total` - Idadi ya mabadiliko ya hali yasiyofaa
`agent_privilege_escalation_attempts_total` - Idadi ya maombi yanayoshukiwa

#### 8.2 Uboreshaji wa Kurekodi

**Kurekodi ya Maombi:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "initial_state": "undefined",
  "state_transitions": [
    {"tool": "knowledge-query", "from": "undefined", "to": "analysis", "timestamp": "2024-01-01T10:00:01Z"}
  ],
  "available_tools": ["knowledge-query", "text-completion"],
  "filtered_by_group": ["graph-update", "admin-tool"],
  "filtered_by_state": [],
  "execution_time": "1.2s"
}
```

### 9. Mbinu ya Majaribio

#### 9.1 Majaribio ya Kitengo

**Mantiki ya Kuchuja Zana:**
Majaribio ya hesabu za makutano ya vikundi
Majaribio ya mantiki ya kuchuja kulingana na hali
Thibitisha utoaji wa kikundi na hali chagu
Majaribio ya tabia ya kikundi cha "wildcard"
Thibitisha usimamizi wa kikundi tupu
Majaribio ya hali ya kuchuja iliyounganisha kikundi+hali

**Uthibitisho wa Usanidi:**
Majaribio ya kupakia zana pamoja na usanidi mbalimbali wa kikundi na hali
Thibitisha uthibitisho wa schema kwa vipimo visivyo sahihi vya kikundi na hali
Majaribio ya utangamano wa nyuma na usanidi uliopo
Thibitisha ufafanuzi na mizunguko ya mabadiliko ya hali

#### 9.2 Majaribio ya Uunganisho

**Tabia ya Wakala:**
Thibitisha kwamba wakala huona tu zana zilizochujwa kwa kikundi+hali
Majaribio ya utekelezaji wa ombi kwa mchanganyiko mbalimbali wa vikundi
Majaribio ya mabadiliko ya hali wakati wa utekelezaji wa wakala
Thibitisha usimamizi wa makosa wakati hakuna zana zinazopatikana
Majaribio ya maendeleo ya mtiririko wa kazi kupitia hali nyingi

**Majaribio ya Usalama:**
Majaribio ya kuzuia kupanda kwa madaraka
Thibitisha usahihi wa njia ya ukaguzi
Majaribio ya ujumuishaji wa lango pamoja na ruhusa za mtumiaji

#### 9.3 Hali za Jumla

**Matumizi ya Mfumo Mwingi Pamoja na Mitiririko ya Kazi ya Hali:**
```
Scenario: Different users with different tool access and workflow states
Given: User A has "read-only" permissions, state "undefined"
  And: User B has "write" permissions, state "analysis"
When: Both request knowledge operations
Then: User A gets read-only tools available in "undefined" state
  And: User B gets write tools available in "analysis" state
  And: State transitions are tracked per user session
  And: All usage and transitions are properly audited
```

**Maendeleo ya Hatua ya Mchakato:**
```
Scenario: Complete workflow execution
Given: Request with groups ["knowledge", "compute"] and state "undefined"
When: Agent executes knowledge-query tool (transitions to "analysis")
  And: Agent executes complex-analysis tool (transitions to "results")
  And: Agent executes reset-workflow tool (transitions to "undefined")
Then: Each step has correctly filtered available tools
  And: State transitions are logged with timestamps
  And: Final state allows initial workflow to repeat
```

### 10. Mambo Muhimu ya Utendaji

#### 10.1 Athari ya Kuanzisha Zana

**Uteuzi wa Vipimo:**
Meta data ya kikundi na hali huwekwa mara moja wakati wa kuanzishwa
Uwezekano mdogo wa matumizi ya kumbukumbu kwa kila zana (nafasi za ziada)
Hakuna athari kwenye muda wa kuanzisha zana

**Uchakataji wa Maombi:**
Kuchujwa kwa pamoja kwa kikundi + hali hufanyika mara moja kwa kila ombi
Ufumbuzi wa O(n) ambapo n = idadi ya zana zilizosanidiwa
Mabadiliko ya hali huongeza uwezekano mdogo (utambulisho wa herufi)
Athari ndogo kwa idadi ya kawaida ya zana (< 100)

#### 10.2 Mikakati ya Ubora

**Kikundi cha Zana Zilizopangwa Mapema:**
Hifadhi vikundi vya zana kwa kila mchanganyiko wa kikundi + hali
Epuka kuchujwa mara kwa mara kwa mifumo ya kawaida ya kikundi/hali
Usawa kati ya kumbukumbu na hesabu kwa mchanganyiko unaotumika mara kwa mara

**Kupakua kwa Kila Matumizi:**
Pakua matumizi ya zana tu wakati inahitajika
Punguza muda wa kuanzishwa kwa matumizi ambayo yana zana nyingi
Usajili wa zana kwa njia ya moja kwa moja kulingana na mahitaji ya kikundi

### 11. Maboresho ya Baadaye

#### 11.1 Uteuzi wa Kikundi wa Kila Muda

**Uteuzi wa Kikundi Kulingana na Mazingira:**
Weka zana katika vikundi kulingana na mazingira ya ombi
Upatikanaji wa kikundi kulingana na wakati (sawa za biashara tu)
Marekebisho ya kikundi kulingana na mzigo (zana ghali wakati wa matumizi kidogo)

#### 11.2 Hierarkia za Kikundi

**Muundo Ulioingilishwa wa Kikundi:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 Mapendekezo ya Zana

**Mapendekezo Kulingana na Kikundi:**
Pendekeza vikundi bora vya zana kwa aina za ombi.
Jifunze kutoka kwa mitindo ya matumizi ili kuboresha mapendekezo.
Toa vikundi vya dharura wakati zana zinazopendekezwa hazipatikani.

### 12. Maswali ya Kufungua

1. **Uthibitisho wa Kikundi**: Je, majina ya vikundi yasiyo halali katika maombi yanapaswa kusababisha hitilafu kubwa au onyo?

2. **Udagano wa Kikundi**: Je, mfumo unapaswa kutoa API ili kuorodhesha vikundi vinavyopatikana na zana zao?

3. **Vikundi vya Njia Moja Moja**: Je, vikundi vinapaswa kupangwa wakati wa utendaji au wakati wa kuanzishwa tu?

4. **Urithi wa Kikundi**: Je, zana zinapaswa kurithi vikundi kutoka kwa makundi yao ya wazazi au matoleo?

5. **Ufuatiliaji wa Utendaji**: Ni vipimo vipi vya ziada vinavyohitajika kufuatilia matumizi ya zana kulingana na vikundi kwa ufanisi?

### 13. Hitimisho

Mfumo wa vikundi vya zana hutoa:

**Usalama**: Udhibiti wa kina wa ufikiaji wa uwezo wa wakala.
**Utendaji**: Kupunguza mzigo wa kupakua na kuchagua zana.
**Unyumbufu**: Uainishaji wa zana wa mwelekeo mwingi.
**Ulinganifu**: Ujumuishaji laini na miundo ya wakala iliyopo.

Mfumo huu huruhusu usakinishaji wa TrustGraph kusimamia ufikiaji wa zana vizuri zaidi, kuboresha mipaka ya usalama, na kuongeza matumizi ya rasilimali huku ikiendelea kuwa na ulinganifu kamili na usanidi na maombi iliyopo.
