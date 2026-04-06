import type { DomainKey, OntologyDomain } from "../types";
import { SectionLabel, Card, Badge, LoadingState } from "../components";
import { useGraphData, useOntologySchema } from "../state";
import { getLocalName } from "../utils";
import { text, surface, border } from "../theme";

export function OntologyView() {
  const { ontology, isLoading: graphLoading } = useGraphData();
  const { schema, isLoading: schemaLoading } = useOntologySchema();

  const isLoading = graphLoading || schemaLoading;

  if (isLoading || !ontology || !schema) {
    return <LoadingState message="Loading ontology..." />;
  }

  // Count total instances
  const totalInstances = Object.values(ontology).reduce((sum, d) => sum + d.subclasses.length, 0);

  return (
    <div style={{ flex: 1, padding: "28px", overflowY: "auto", height: "calc(100vh - 110px)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <SectionLabel marginBottom={24}>ONTOLOGY SCHEMA</SectionLabel>

        {/* Ontology class cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 32 }}>
          {(Object.entries(ontology) as [DomainKey, OntologyDomain][]).map(([key, data]) => {
            // Find datatype properties for this domain from schema
            const domainProps = schema.datatypeProperties
              .filter(p => p.domain && getLocalName(p.domain) === data.label)
              .map(p => p.label);

            return (
              <Card key={key} borderColor={data.color + "22"}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <span style={{ fontSize: 24 }}>{data.icon}</span>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 18, color: data.color }}>{data.label}</div>
                    <div style={{ fontSize: 11, color: text.faint, fontFamily: "'IBM Plex Mono', monospace" }}>owl:Class</div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: text.subtle, lineHeight: 1.5, marginBottom: 14 }}>{data.description}</div>
                <SectionLabel marginBottom={8}>PROPERTIES ({domainProps.length})</SectionLabel>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {domainProps.map((p) => (
                    <Badge key={p} color={data.color} size="small">{p}</Badge>
                  ))}
                </div>
                <SectionLabel marginTop={14} marginBottom={8}>INSTANCES ({data.subclasses.length})</SectionLabel>
                {data.subclasses.map((sc) => (
                  <div key={sc.id} style={{
                    padding: "6px 10px", marginBottom: 3, borderRadius: 4,
                    background: surface.card, fontSize: 11, color: text.muted,
                    display: "flex", justifyContent: "space-between",
                  }}>
                    <span>{sc.label}</span>
                    <span style={{ color: text.disabled, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10 }}>{sc.id}</span>
                  </div>
                ))}
              </Card>
            );
          })}
        </div>

        {/* Relationship predicates (Object Properties) */}
        <Card borderColor={border.default}>
          <SectionLabel marginBottom={16}>RELATIONSHIP PREDICATES ({schema.objectProperties.length})</SectionLabel>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            {schema.objectProperties.map((prop) => {
              const fromDomain = prop.domain ? getLocalName(prop.domain).toLowerCase() as DomainKey : null;
              const toDomain = prop.range ? getLocalName(prop.range).toLowerCase() as DomainKey : null;

              return (
                <Card key={prop.uri} padding="10px 12px" borderRadius={6}>
                  <div style={{ fontSize: 12, color: text.secondary, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>
                    {prop.label}
                  </div>
                  <div style={{ fontSize: 10, color: text.disabled }}>
                    {fromDomain && ontology[fromDomain] && (
                      <span style={{ color: ontology[fromDomain].color }}>{ontology[fromDomain].label}</span>
                    )}
                    {fromDomain && toDomain && " → "}
                    {toDomain && ontology[toDomain] && (
                      <span style={{ color: ontology[toDomain].color }}>{ontology[toDomain].label}</span>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </Card>

        {/* Triple count summary */}
        <div style={{
          marginTop: 20, padding: "16px 24px", borderRadius: 10,
          background: "linear-gradient(135deg, rgba(110,231,183,0.04) 0%, rgba(147,197,253,0.04) 50%, rgba(249,168,212,0.04) 100%)",
          border: `1px solid ${border.default}`,
          display: "flex", justifyContent: "space-around",
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {[
            { label: "Classes", value: schema.classes.length },
            { label: "Instances", value: totalInstances },
            { label: "Object Props", value: schema.objectProperties.length },
            { label: "Data Props", value: schema.datatypeProperties.length },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>{s.value}</div>
              <div style={{ fontSize: 10, color: text.faint, letterSpacing: "0.05em" }}>{s.label.toUpperCase()}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
