"""
SHACL-based policy evaluator.  Builds a small evaluation context graph
from the request, then runs SHACL shapes (policy rules) against it.

Supports the following SHACL target types:
  - sh:targetNode       — exact IRI match
  - sh:targetClass      — rdf:type membership
  - sh:targetSubjectsOf — subject has a given property
  - sh:targetObjectsOf  — subject is object of a given property
  - sh:SPARQLTarget     — full SPARQL SELECT for complex matching

Rules use sh:SPARQLRule (sh:construct) to produce results with
tg-exec-pol vocabulary terms for verdict, disclosure, etc.
"""

import logging
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD

logger = logging.getLogger(__name__)

SH = Namespace("http://www.w3.org/ns/shacl#")
TG_EXEC = Namespace("https://trustgraph.ai/ontology/exec/")
TG_EXEC_POL = Namespace("https://trustgraph.ai/ontology/exec-pol/")
TG_UC = Namespace("https://trustgraph.ai/ns/user-context/")

EVAL_NS = "urn:tg:eval:"
SUBJECT_IRI = URIRef(EVAL_NS + "subject")
CONTEXT_IRI = URIRef(EVAL_NS + "context")
STEP_IRI = URIRef(EVAL_NS + "step")

ARTIFACT_TYPE_MAP = {
    "TabularArtifact": TG_EXEC.TabularArtifact,
    "TextBlobArtifact": TG_EXEC.TextBlobArtifact,
    "SubgraphArtifact": TG_EXEC.SubgraphArtifact,
    "ExternalReferenceArtifact": TG_EXEC.ExternalReferenceArtifact,
    "CompositeArtifact": TG_EXEC.CompositeArtifact,
    "ReportArtifact": TG_EXEC.ReportArtifact,
}

EVAL_TYPE_MAP = {
    "plan-preflight": TG_EXEC_POL.PlanPreflight,
    "step-ingress": TG_EXEC_POL.StepIngress,
    "step-egress": TG_EXEC_POL.StepEgress,
    "artifact-egress": TG_EXEC_POL.ArtifactEgress,
}

VERDICT_MAP = {
    str(TG_EXEC_POL.Allow): "ALLOW",
    str(TG_EXEC_POL.Filter): "FILTER",
    str(TG_EXEC_POL.RequireApproval): "REQUIRE_APPROVAL",
    str(TG_EXEC_POL.Deny): "DENY",
}

DISCLOSURE_MAP = {
    str(TG_EXEC_POL.Silent): "SILENT",
    str(TG_EXEC_POL.Opaque): "OPAQUE",
    str(TG_EXEC_POL.Transparent): "TRANSPARENT",
}

REDACTION_METHOD_MAP = {
    str(TG_EXEC_POL.Strip): "strip",
    str(TG_EXEC_POL.Mask): "mask",
    str(TG_EXEC_POL.Generalise): "generalise",
    str(TG_EXEC_POL.SyntheticReplace): "synthetic-replace",
}

DEFAULT_PREFIXES = f"""
PREFIX sh: <{SH}>
PREFIX rdf: <{RDF}>
PREFIX rdfs: <{RDFS}>
PREFIX xsd: <{XSD}>
PREFIX tg-exec: <{TG_EXEC}>
PREFIX tg-exec-pol: <{TG_EXEC_POL}>
PREFIX tg-uc: <{TG_UC}>
PREFIX eval: <{EVAL_NS}>
"""


class PolicyRule:

    def __init__(self, rule_id, order, targets, rules, prefixes=""):
        self.rule_id = rule_id
        self.order = order
        self.targets = targets
        self.rules = rules
        self.prefixes = prefixes


def parse_rules(rules_turtle):

    g = Graph()
    g.parse(data=rules_turtle, format="turtle")

    shapes = list(g.subjects(RDF.type, SH.NodeShape))

    rules = []
    for shape_iri in shapes:
        rule_id = str(shape_iri)

        order_val = g.value(shape_iri, SH.order)
        order = int(order_val) if order_val else 0

        prefix_decls = _extract_prefixes(g, shape_iri)

        targets = _extract_targets(g, shape_iri)
        shape_rules = _extract_rules(g, shape_iri)

        rules.append(PolicyRule(
            rule_id=rule_id,
            order=order,
            targets=targets,
            rules=shape_rules,
            prefixes=prefix_decls,
        ))

    rules.sort(key=lambda r: r.order)
    return rules


def _extract_prefixes(g, shape_iri):

    lines = []
    for prefix_node in g.objects(shape_iri, SH.prefixes):
        for decl in g.objects(prefix_node, SH.declare):
            pfx = g.value(decl, SH.prefix)
            ns = g.value(decl, SH.namespace)
            if pfx is not None and ns is not None:
                lines.append(f"PREFIX {pfx}: <{ns}>")
    return "\n".join(lines)


def _extract_targets(g, shape_iri):

    targets = []

    for node in g.objects(shape_iri, SH.targetNode):
        targets.append(("targetNode", str(node)))

    for cls in g.objects(shape_iri, SH.targetClass):
        targets.append(("targetClass", str(cls)))

    for prop in g.objects(shape_iri, SH.targetSubjectsOf):
        targets.append(("targetSubjectsOf", str(prop)))

    for prop in g.objects(shape_iri, SH.targetObjectsOf):
        targets.append(("targetObjectsOf", str(prop)))

    for target_node in g.objects(shape_iri, SH.target):
        target_type = g.value(target_node, RDF.type)
        if target_type == SH.SPARQLTarget:
            select = g.value(target_node, SH.select)
            if select:
                targets.append(("SPARQLTarget", str(select)))

    return targets


def _extract_rules(g, shape_iri):

    rules = []
    for rule_node in g.objects(shape_iri, SH.rule):
        rule_type = g.value(rule_node, RDF.type)
        if rule_type == SH.SPARQLRule:
            construct = g.value(rule_node, SH.construct)
            if construct:
                rules.append(("SPARQLRule", str(construct)))

    return rules


def build_eval_graph(evaluation_type, subject, principal):

    g = Graph()

    g.bind("tg-exec", TG_EXEC)
    g.bind("tg-exec-pol", TG_EXEC_POL)
    g.bind("tg-uc", TG_UC)
    g.bind("sh", SH)
    g.bind("eval", URIRef(EVAL_NS))

    eval_type_iri = EVAL_TYPE_MAP.get(evaluation_type)
    if eval_type_iri:
        g.add((SUBJECT_IRI, TG_EXEC_POL.evaluationType, eval_type_iri))

    subject_type = subject.get("type", "")
    type_iri = ARTIFACT_TYPE_MAP.get(subject_type)
    if type_iri:
        g.add((SUBJECT_IRI, RDF.type, type_iri))

    if subject_type == "ExecutionPlan":
        g.add((SUBJECT_IRI, RDF.type, TG_EXEC.ExecutionPlan))
    elif subject_type == "Step":
        g.add((SUBJECT_IRI, RDF.type, TG_EXEC.Step))

    capability = subject.get("capability")
    if capability:
        cap_iri = URIRef(f"urn:tg:cap:{capability}")
        g.add((SUBJECT_IRI, TG_EXEC.invokesCapability, cap_iri))
        g.add((cap_iri, TG_EXEC.capabilityId, Literal(capability)))

    for key, value in subject.items():
        if key in ("type", "capability"):
            continue
        pred = TG_EXEC[key]
        if isinstance(value, str):
            g.add((SUBJECT_IRI, pred, Literal(value)))
        elif isinstance(value, bool):
            g.add((SUBJECT_IRI, pred, Literal(value, datatype=XSD.boolean)))
        elif isinstance(value, (int, float)):
            g.add((SUBJECT_IRI, pred, Literal(value)))
        elif isinstance(value, list):
            for item in value:
                g.add((SUBJECT_IRI, pred, Literal(str(item))))

    g.add((CONTEXT_IRI, RDF.type, TG_UC.UserContext))

    user = principal.get("user", "")
    if user:
        g.add((CONTEXT_IRI, TG_UC.user, URIRef(user)
               if user.startswith("urn:") else Literal(user)))

    for role in principal.get("roles", []):
        g.add((CONTEXT_IRI, TG_UC.role, Literal(role)))

    workspace = principal.get("workspace", "")
    if workspace:
        g.add((CONTEXT_IRI, TG_UC.workspace, Literal(workspace)))

    for key, value in principal.items():
        if key in ("user", "roles", "workspace"):
            continue
        if isinstance(value, str):
            g.add((CONTEXT_IRI, TG_UC[key], Literal(value)))
        elif isinstance(value, list):
            for item in value:
                g.add((CONTEXT_IRI, TG_UC[key], Literal(str(item))))

    return g


def check_target(eval_graph, target_type, target_value, prefixes=""):

    if target_type == "targetNode":
        return SUBJECT_IRI == URIRef(target_value)

    elif target_type == "targetClass":
        target_cls = URIRef(target_value)
        return (SUBJECT_IRI, RDF.type, target_cls) in eval_graph

    elif target_type == "targetSubjectsOf":
        target_prop = URIRef(target_value)
        return any(eval_graph.objects(SUBJECT_IRI, target_prop))

    elif target_type == "targetObjectsOf":
        target_prop = URIRef(target_value)
        return any(eval_graph.subjects(target_prop, SUBJECT_IRI))

    elif target_type == "SPARQLTarget":
        query = DEFAULT_PREFIXES
        if prefixes:
            query += "\n" + prefixes
        query += "\n" + target_value
        try:
            results = eval_graph.query(
                query,
                initBindings={"this": SUBJECT_IRI},
            )
            return len(list(results)) > 0
        except Exception as e:
            logger.error(f"SPARQL target query failed: {e}")
            return False

    return False


def execute_rule(eval_graph, rule_type, rule_value, prefixes=""):

    if rule_type != "SPARQLRule":
        return Graph()

    query = DEFAULT_PREFIXES
    if prefixes:
        query += "\n" + prefixes
    query += "\n" + rule_value

    try:
        result_graph = eval_graph.query(
            query,
            initBindings={"this": SUBJECT_IRI},
        ).graph
        return result_graph if result_graph else Graph()
    except Exception as e:
        logger.error(f"SPARQL rule execution failed: {e}")
        return Graph()


def extract_attestation(result_graph):

    verdict = "ALLOW"
    disclosure = "SILENT"
    boundary_failure = False
    message = ""
    redaction_fields = []

    for result_node in result_graph.subjects(RDF.type, SH.ValidationResult):

        v = result_graph.value(result_node, TG_EXEC_POL.verdict)
        if v:
            verdict = VERDICT_MAP.get(str(v), str(v))

        d = result_graph.value(result_node, TG_EXEC_POL.disclosure)
        if d:
            disclosure = DISCLOSURE_MAP.get(str(d), str(d))

        bf = result_graph.value(result_node, TG_EXEC_POL.boundaryFailure)
        if bf is not None:
            boundary_failure = bf.toPython() if hasattr(bf, 'toPython') else bool(bf)

        msg = result_graph.value(result_node, SH.resultMessage)
        if msg:
            message = str(msg)

        field = result_graph.value(result_node, TG_EXEC_POL.affectedField)
        method = result_graph.value(result_node, TG_EXEC_POL.redactionMethod)
        if field:
            redaction_fields.append({
                "field": str(field),
                "method": REDACTION_METHOD_MAP.get(str(method), str(method)) if method else "strip",
            })

    return {
        "verdict": verdict,
        "disclosure": disclosure,
        "boundary_failure": boundary_failure,
        "message": message,
        "redaction_fields": redaction_fields,
    }


def evaluate_rules(rules, evaluation_type, subject, principal):

    eval_graph = build_eval_graph(evaluation_type, subject, principal)

    for rule in rules:

        target_matched = False
        for target_type, target_value in rule.targets:
            if check_target(eval_graph, target_type, target_value,
                            rule.prefixes):
                target_matched = True
                break

        if not target_matched:
            continue

        combined_results = Graph()
        for rule_type, rule_value in rule.rules:
            result_graph = execute_rule(
                eval_graph, rule_type, rule_value, rule.prefixes,
            )
            combined_results += result_graph

        if len(combined_results) > 0:
            attestation = extract_attestation(combined_results)
            attestation["matched_rule"] = rule.rule_id
            return attestation

    return {
        "verdict": "ALLOW",
        "disclosure": "SILENT",
        "boundary_failure": False,
        "message": "",
        "redaction_fields": [],
        "matched_rule": None,
    }
