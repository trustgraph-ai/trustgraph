"""
Verification service.  Validates that a step's output artifact
conforms to the expected type and structural contract.  Tier 1
(deterministic structural checks) only — no LLM calls.
"""

import logging

from ... schema import VerificationRequest, VerificationResponse, Violation
from ... base import VerificationService

logger = logging.getLogger(__name__)

default_ident = "verification"

KNOWN_TYPES = {
    "TabularArtifact",
    "TextBlobArtifact",
    "SubgraphArtifact",
    "ExternalReferenceArtifact",
    "CompositeArtifact",
    "ReportArtifact",
    "QuerySpecArtifact",
}


class Processor(VerificationService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.validators = {
            "TabularArtifact": self.validate_tabular,
            "TextBlobArtifact": self.validate_text_blob,
            "SubgraphArtifact": self.validate_subgraph,
            "ExternalReferenceArtifact": self.validate_external_ref,
            "CompositeArtifact": self.validate_composite,
            "ReportArtifact": self.validate_report,
            "QuerySpecArtifact": self.validate_query_spec,
        }

    async def verify(self, workspace, request, flow):

        violations = []

        if not request.expected_type:
            violations.append(Violation(
                field="expected-type",
                message="No expected type specified",
                severity="error",
            ))
            return self.build_response(request, violations)

        if request.expected_type not in KNOWN_TYPES:
            violations.append(Violation(
                field="expected-type",
                message=f"Unknown artifact type: {request.expected_type}",
                severity="error",
            ))
            return self.build_response(request, violations)

        if not request.artifact:
            violations.append(Violation(
                field="artifact",
                message="No artifact payload provided",
                severity="error",
            ))
            return self.build_response(request, violations)

        validator = self.validators.get(request.expected_type)
        if validator:
            validator(request.artifact, violations)

        return self.build_response(request, violations)

    def build_response(self, request, violations):

        errors = [v for v in violations if v.severity == "error"]

        return VerificationResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            valid=len(errors) == 0,
            tier=1,
            violations=violations,
        )

    def validate_tabular(self, artifact, violations):

        columns = artifact.get("columns")
        if columns is None:
            violations.append(Violation(
                field="columns",
                message="TabularArtifact missing 'columns'",
                severity="error",
            ))
        elif not isinstance(columns, list):
            violations.append(Violation(
                field="columns",
                message="'columns' must be a list",
                severity="error",
            ))
        else:
            for i, col in enumerate(columns):
                if not isinstance(col, dict):
                    violations.append(Violation(
                        field=f"columns[{i}]",
                        message="Column entry must be an object",
                        severity="error",
                    ))
                    continue
                if "name" not in col:
                    violations.append(Violation(
                        field=f"columns[{i}].name",
                        message="Column missing 'name'",
                        severity="error",
                    ))

        rows = artifact.get("rows")
        if rows is None:
            violations.append(Violation(
                field="rows",
                message="TabularArtifact missing 'rows'",
                severity="error",
            ))
        elif not isinstance(rows, list):
            violations.append(Violation(
                field="rows",
                message="'rows' must be a list",
                severity="error",
            ))

        if (isinstance(columns, list) and isinstance(rows, list)
                and len(columns) > 0 and len(rows) > 0):
            col_names = {c["name"] for c in columns if isinstance(c, dict) and "name" in c}
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    violations.append(Violation(
                        field=f"rows[{i}]",
                        message="Row must be an object",
                        severity="error",
                    ))
                    continue
                extra = set(row.keys()) - col_names
                if extra:
                    violations.append(Violation(
                        field=f"rows[{i}]",
                        message=f"Row has undeclared columns: {sorted(extra)}",
                        severity="warning",
                    ))

    def validate_text_blob(self, artifact, violations):

        text = artifact.get("text")
        if text is None:
            violations.append(Violation(
                field="text",
                message="TextBlobArtifact missing 'text'",
                severity="error",
            ))
        elif not isinstance(text, str):
            violations.append(Violation(
                field="text",
                message="'text' must be a string",
                severity="error",
            ))
        elif len(text) == 0:
            violations.append(Violation(
                field="text",
                message="'text' is empty",
                severity="warning",
            ))

    def validate_subgraph(self, artifact, violations):

        triples = artifact.get("triples")
        if triples is None:
            violations.append(Violation(
                field="triples",
                message="SubgraphArtifact missing 'triples'",
                severity="error",
            ))
        elif not isinstance(triples, list):
            violations.append(Violation(
                field="triples",
                message="'triples' must be a list",
                severity="error",
            ))
        else:
            for i, t in enumerate(triples):
                if not isinstance(t, dict):
                    violations.append(Violation(
                        field=f"triples[{i}]",
                        message="Triple must be an object",
                        severity="error",
                    ))
                    continue
                for field in ("s", "p", "o"):
                    if field not in t:
                        violations.append(Violation(
                            field=f"triples[{i}].{field}",
                            message=f"Triple missing '{field}'",
                            severity="error",
                        ))

    def validate_external_ref(self, artifact, violations):

        uri = artifact.get("uri")
        if uri is None:
            violations.append(Violation(
                field="uri",
                message="ExternalReferenceArtifact missing 'uri'",
                severity="error",
            ))
        elif not isinstance(uri, str):
            violations.append(Violation(
                field="uri",
                message="'uri' must be a string",
                severity="error",
            ))
        elif len(uri) == 0:
            violations.append(Violation(
                field="uri",
                message="'uri' is empty",
                severity="error",
            ))

    def validate_composite(self, artifact, violations):

        components = artifact.get("components")
        if components is None:
            violations.append(Violation(
                field="components",
                message="CompositeArtifact missing 'components'",
                severity="error",
            ))
        elif not isinstance(components, list):
            violations.append(Violation(
                field="components",
                message="'components' must be a list",
                severity="error",
            ))
        elif len(components) == 0:
            violations.append(Violation(
                field="components",
                message="CompositeArtifact has no components",
                severity="warning",
            ))
        else:
            for i, comp in enumerate(components):
                if not isinstance(comp, dict):
                    violations.append(Violation(
                        field=f"components[{i}]",
                        message="Component must be an object",
                        severity="error",
                    ))
                    continue
                if "role" not in comp:
                    violations.append(Violation(
                        field=f"components[{i}].role",
                        message="Component missing 'role'",
                        severity="error",
                    ))
                if "artifact" not in comp:
                    violations.append(Violation(
                        field=f"components[{i}].artifact",
                        message="Component missing 'artifact'",
                        severity="error",
                    ))

    def validate_report(self, artifact, violations):

        fmt = artifact.get("format")
        if fmt is None:
            violations.append(Violation(
                field="format",
                message="ReportArtifact missing 'format'",
                severity="error",
            ))
        elif fmt not in ("markdown", "html", "pdf"):
            violations.append(Violation(
                field="format",
                message=f"Unknown report format: {fmt}",
                severity="warning",
            ))

        narrative = artifact.get("narrative")
        if narrative is None:
            violations.append(Violation(
                field="narrative",
                message="ReportArtifact missing 'narrative'",
                severity="error",
            ))
        elif not isinstance(narrative, str):
            violations.append(Violation(
                field="narrative",
                message="'narrative' must be a string",
                severity="error",
            ))
        elif len(narrative) == 0:
            violations.append(Violation(
                field="narrative",
                message="'narrative' is empty",
                severity="warning",
            ))

    def validate_query_spec(self, artifact, violations):

        version = artifact.get("version")
        if version != "1":
            violations.append(Violation(
                field="version",
                message=f"Expected version '1', got '{version}'",
                severity="error",
            ))

        qtype = artifact.get("type")
        if qtype == "select":
            self.validate_query_spec_select(artifact, violations)
        elif qtype == "join":
            self.validate_query_spec_join(artifact, violations)
        else:
            violations.append(Violation(
                field="type",
                message=f"Unknown query type: {qtype}",
                severity="error",
            ))

    def validate_query_spec_select(self, artifact, violations):

        table = artifact.get("table")
        if not table or not isinstance(table, str):
            violations.append(Violation(
                field="table",
                message="QuerySpecArtifact missing 'table'",
                severity="error",
            ))

        columns = artifact.get("columns")
        if not columns or not isinstance(columns, list):
            violations.append(Violation(
                field="columns",
                message="QuerySpecArtifact missing 'columns'",
                severity="error",
            ))
        elif len(columns) == 0:
            violations.append(Violation(
                field="columns",
                message="'columns' must not be empty",
                severity="error",
            ))

    def validate_query_spec_join(self, artifact, violations):

        for sub_key in ("left", "right"):
            sub = artifact.get(sub_key)
            if not sub or not isinstance(sub, dict):
                violations.append(Violation(
                    field=sub_key,
                    message=f"Join spec missing '{sub_key}'",
                    severity="error",
                ))
            else:
                self.validate_query_spec(sub, violations)

        on = artifact.get("on")
        if not on or not isinstance(on, list):
            violations.append(Violation(
                field="on",
                message="Join spec missing 'on' clauses",
                severity="error",
            ))
        else:
            for i, clause in enumerate(on):
                if not isinstance(clause, dict):
                    violations.append(Violation(
                        field=f"on[{i}]",
                        message="'on' clause must be an object",
                        severity="error",
                    ))
                    continue
                for col in ("left_column", "right_column"):
                    if col not in clause:
                        violations.append(Violation(
                            field=f"on[{i}].{col}",
                            message=f"'on' clause missing '{col}'",
                            severity="error",
                        ))

    @staticmethod
    def add_args(parser):
        VerificationService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
