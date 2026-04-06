import { Ontology } from "@trustgraph/react-state";

export interface ExportOptions {
  format: "owl" | "rdf" | "turtle";
  includeComments?: boolean;
  includeNamespaces?: boolean;
}

export class OntologyExporter {
  static export(ontology: Ontology, options: ExportOptions): string {
    switch (options.format) {
      case "owl":
        return this.exportToOWL(ontology, options);
      case "rdf":
        return this.exportToRDF(ontology, options);
      case "turtle":
        return this.exportToTurtle(ontology, options);
      default:
        throw new Error(`Unsupported export format: ${options.format}`);
    }
  }

  private static exportToOWL(
    ontology: Ontology,
    options: ExportOptions,
  ): string {
    const lines: string[] = [];

    // XML Declaration and Ontology header
    lines.push('<?xml version="1.0"?>');
    lines.push('<rdf:RDF xmlns="' + ontology.metadata.namespace + '"');
    lines.push('     xml:base="' + ontology.metadata.namespace + '"');
    lines.push('     xmlns:owl="http://www.w3.org/2002/07/owl#"');
    lines.push('     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"');
    lines.push('     xmlns:xml="http://www.w3.org/XML/1998/namespace"');
    lines.push('     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"');
    lines.push('     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">');
    lines.push(
      '    <owl:Ontology rdf:about="' + ontology.metadata.namespace + '">',
    );

    if (ontology.metadata.name) {
      lines.push(
        '        <rdfs:label xml:lang="en">' +
          this.escapeXML(ontology.metadata.name) +
          "</rdfs:label>",
      );
    }

    if (ontology.metadata.description && options.includeComments !== false) {
      lines.push(
        '        <rdfs:comment xml:lang="en">' +
          this.escapeXML(ontology.metadata.description) +
          "</rdfs:comment>",
      );
    }

    if (ontology.metadata.version) {
      lines.push(
        "        <owl:versionInfo>" +
          this.escapeXML(ontology.metadata.version) +
          "</owl:versionInfo>",
      );
    }

    lines.push("    </owl:Ontology>");
    lines.push("");

    // Export Classes
    Object.entries(ontology.classes).forEach(([_classId, owlClass]) => {
      lines.push("    <!-- " + owlClass.uri + " -->");
      lines.push('    <owl:Class rdf:about="' + owlClass.uri + '">');

      // rdfs:label
      if (owlClass["rdfs:label"] && owlClass["rdfs:label"].length > 0) {
        owlClass["rdfs:label"].forEach((label) => {
          const langAttr = label.lang ? ` xml:lang="${label.lang}"` : "";
          lines.push(
            "        <rdfs:label" +
              langAttr +
              ">" +
              this.escapeXML(label.value) +
              "</rdfs:label>",
          );
        });
      }

      // rdfs:comment
      if (owlClass["rdfs:comment"] && options.includeComments !== false) {
        lines.push(
          '        <rdfs:comment xml:lang="en">' +
            this.escapeXML(owlClass["rdfs:comment"]) +
            "</rdfs:comment>",
        );
      }

      // rdfs:subClassOf
      if (owlClass["rdfs:subClassOf"]) {
        const parentClass = ontology.classes[owlClass["rdfs:subClassOf"]];
        if (parentClass) {
          lines.push(
            '        <rdfs:subClassOf rdf:resource="' +
              parentClass.uri +
              '"/>',
          );
        }
      }

      lines.push("    </owl:Class>");
      lines.push("");
    });

    // Export Object Properties
    Object.entries(ontology.objectProperties).forEach(
      ([_propId, property]) => {
        lines.push("    <!-- " + property.uri + " -->");
        lines.push(
          '    <owl:ObjectProperty rdf:about="' + property.uri + '">',
        );

        // rdfs:label
        if (property["rdfs:label"] && property["rdfs:label"].length > 0) {
          property["rdfs:label"].forEach((label) => {
            const langAttr = label.lang ? ` xml:lang="${label.lang}"` : "";
            lines.push(
              "        <rdfs:label" +
                langAttr +
                ">" +
                this.escapeXML(label.value) +
                "</rdfs:label>",
            );
          });
        }

        // rdfs:comment
        if (property["rdfs:comment"] && options.includeComments !== false) {
          lines.push(
            '        <rdfs:comment xml:lang="en">' +
              this.escapeXML(property["rdfs:comment"]) +
              "</rdfs:comment>",
          );
        }

        // rdfs:domain
        if (property["rdfs:domain"]) {
          const domainClass = ontology.classes[property["rdfs:domain"]];
          if (domainClass) {
            lines.push(
              '        <rdfs:domain rdf:resource="' + domainClass.uri + '"/>',
            );
          }
        }

        // rdfs:range
        if (property["rdfs:range"]) {
          const rangeClass = ontology.classes[property["rdfs:range"]];
          if (rangeClass) {
            lines.push(
              '        <rdfs:range rdf:resource="' + rangeClass.uri + '"/>',
            );
          }
        }

        // owl:inverseOf
        if (property["owl:inverseOf"]) {
          const inverseProperty =
            ontology.objectProperties[property["owl:inverseOf"]];
          if (inverseProperty) {
            lines.push(
              '        <owl:inverseOf rdf:resource="' +
                inverseProperty.uri +
                '"/>',
            );
          }
        }

        // rdfs:subPropertyOf
        if (property["rdfs:subPropertyOf"]) {
          const parentProperty =
            ontology.objectProperties[property["rdfs:subPropertyOf"]];
          if (parentProperty) {
            lines.push(
              '        <rdfs:subPropertyOf rdf:resource="' +
                parentProperty.uri +
                '"/>',
            );
          }
        }

        // owl:functionalProperty
        if (property["owl:functionalProperty"]) {
          lines.push(
            '        <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#FunctionalProperty"/>',
          );
        }

        // owl:inverseFunctionalProperty
        if (property["owl:inverseFunctionalProperty"]) {
          lines.push(
            '        <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#InverseFunctionalProperty"/>',
          );
        }

        // Cardinality constraints (as comments for documentation)
        if (property["owl:minCardinality"] !== undefined) {
          lines.push(
            "        <!-- Minimum cardinality: " +
              property["owl:minCardinality"] +
              " -->",
          );
        }
        if (property["owl:maxCardinality"] !== undefined) {
          lines.push(
            "        <!-- Maximum cardinality: " +
              property["owl:maxCardinality"] +
              " -->",
          );
        }
        if (property["owl:cardinality"] !== undefined) {
          lines.push(
            "        <!-- Exact cardinality: " +
              property["owl:cardinality"] +
              " -->",
          );
        }

        lines.push("    </owl:ObjectProperty>");
        lines.push("");
      },
    );

    // Export Datatype Properties
    Object.entries(ontology.datatypeProperties).forEach(
      ([_propId, property]) => {
        lines.push("    <!-- " + property.uri + " -->");
        lines.push(
          '    <owl:DatatypeProperty rdf:about="' + property.uri + '">',
        );

        // rdfs:label
        if (property["rdfs:label"] && property["rdfs:label"].length > 0) {
          property["rdfs:label"].forEach((label) => {
            const langAttr = label.lang ? ` xml:lang="${label.lang}"` : "";
            lines.push(
              "        <rdfs:label" +
                langAttr +
                ">" +
                this.escapeXML(label.value) +
                "</rdfs:label>",
            );
          });
        }

        // rdfs:comment
        if (property["rdfs:comment"] && options.includeComments !== false) {
          lines.push(
            '        <rdfs:comment xml:lang="en">' +
              this.escapeXML(property["rdfs:comment"]) +
              "</rdfs:comment>",
          );
        }

        // rdfs:domain
        if (property["rdfs:domain"]) {
          const domainClass = ontology.classes[property["rdfs:domain"]];
          if (domainClass) {
            lines.push(
              '        <rdfs:domain rdf:resource="' + domainClass.uri + '"/>',
            );
          }
        }

        // rdfs:range (datatype)
        if (property["rdfs:range"]) {
          lines.push(
            '        <rdfs:range rdf:resource="' +
              property["rdfs:range"] +
              '"/>',
          );
        }

        // rdfs:subPropertyOf
        if (property["rdfs:subPropertyOf"]) {
          const parentProperty =
            ontology.datatypeProperties[property["rdfs:subPropertyOf"]];
          if (parentProperty) {
            lines.push(
              '        <rdfs:subPropertyOf rdf:resource="' +
                parentProperty.uri +
                '"/>',
            );
          }
        }

        // owl:functionalProperty
        if (property["owl:functionalProperty"]) {
          lines.push(
            '        <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#FunctionalProperty"/>',
          );
        }

        // Cardinality constraints would typically be expressed as restrictions on classes
        // For now, we include them as annotations for documentation purposes
        if (property["owl:minCardinality"] !== undefined) {
          lines.push(
            "        <!-- Minimum cardinality: " +
              property["owl:minCardinality"] +
              " -->",
          );
        }
        if (property["owl:maxCardinality"] !== undefined) {
          lines.push(
            "        <!-- Maximum cardinality: " +
              property["owl:maxCardinality"] +
              " -->",
          );
        }
        if (property["owl:cardinality"] !== undefined) {
          lines.push(
            "        <!-- Exact cardinality: " +
              property["owl:cardinality"] +
              " -->",
          );
        }

        lines.push("    </owl:DatatypeProperty>");
        lines.push("");
      },
    );

    lines.push("</rdf:RDF>");

    return lines.join("\n");
  }

  private static exportToRDF(
    ontology: Ontology,
    options: ExportOptions,
  ): string {
    // For now, RDF export is the same as OWL since OWL is built on RDF
    return this.exportToOWL(ontology, options);
  }

  private static exportToTurtle(
    ontology: Ontology,
    options: ExportOptions,
  ): string {
    const lines: string[] = [];

    // Prefixes
    lines.push("@prefix : <" + ontology.metadata.namespace + "> .");
    lines.push("@prefix owl: <http://www.w3.org/2002/07/owl#> .");
    lines.push("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .");
    lines.push("@prefix xml: <http://www.w3.org/XML/1998/namespace> .");
    lines.push("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .");
    lines.push("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .");
    lines.push("@base <" + ontology.metadata.namespace + "> .");
    lines.push("");

    // Ontology declaration
    lines.push("<" + ontology.metadata.namespace + "> rdf:type owl:Ontology");
    if (ontology.metadata.name) {
      lines.push(
        '    ; rdfs:label "' +
          this.escapeTurtle(ontology.metadata.name) +
          '"@en',
      );
    }
    if (ontology.metadata.description && options.includeComments !== false) {
      lines.push(
        '    ; rdfs:comment "' +
          this.escapeTurtle(ontology.metadata.description) +
          '"@en',
      );
    }
    if (ontology.metadata.version) {
      lines.push(
        '    ; owl:versionInfo "' +
          this.escapeTurtle(ontology.metadata.version) +
          '"',
      );
    }
    lines.push("    .");
    lines.push("");

    // Export Classes
    Object.entries(ontology.classes).forEach(([classId, owlClass]) => {
      lines.push("###  " + owlClass.uri);
      lines.push(":" + classId + " rdf:type owl:Class");

      // rdfs:label
      if (owlClass["rdfs:label"] && owlClass["rdfs:label"].length > 0) {
        owlClass["rdfs:label"].forEach((label) => {
          const langTag = label.lang ? `@${label.lang}` : "";
          lines.push(
            '    ; rdfs:label "' +
              this.escapeTurtle(label.value) +
              '"' +
              langTag,
          );
        });
      }

      // rdfs:comment
      if (owlClass["rdfs:comment"] && options.includeComments !== false) {
        lines.push(
          '    ; rdfs:comment "' +
            this.escapeTurtle(owlClass["rdfs:comment"]) +
            '"@en',
        );
      }

      // rdfs:subClassOf
      if (owlClass["rdfs:subClassOf"]) {
        lines.push("    ; rdfs:subClassOf :" + owlClass["rdfs:subClassOf"]);
      }

      lines.push("    .");
      lines.push("");
    });

    // Export Object Properties
    Object.entries(ontology.objectProperties).forEach(([propId, property]) => {
      lines.push("###  " + property.uri);
      lines.push(":" + propId + " rdf:type owl:ObjectProperty");

      // rdfs:label
      if (property["rdfs:label"] && property["rdfs:label"].length > 0) {
        property["rdfs:label"].forEach((label) => {
          const langTag = label.lang ? `@${label.lang}` : "";
          lines.push(
            '    ; rdfs:label "' +
              this.escapeTurtle(label.value) +
              '"' +
              langTag,
          );
        });
      }

      // rdfs:comment
      if (property["rdfs:comment"] && options.includeComments !== false) {
        lines.push(
          '    ; rdfs:comment "' +
            this.escapeTurtle(property["rdfs:comment"]) +
            '"@en',
        );
      }

      // rdfs:domain
      if (property["rdfs:domain"]) {
        lines.push("    ; rdfs:domain :" + property["rdfs:domain"]);
      }

      // rdfs:range
      if (property["rdfs:range"]) {
        lines.push("    ; rdfs:range :" + property["rdfs:range"]);
      }

      lines.push("    .");
      lines.push("");
    });

    // Export Datatype Properties
    Object.entries(ontology.datatypeProperties).forEach(
      ([propId, property]) => {
        lines.push("###  " + property.uri);
        lines.push(":" + propId + " rdf:type owl:DatatypeProperty");

        // rdfs:label
        if (property["rdfs:label"] && property["rdfs:label"].length > 0) {
          property["rdfs:label"].forEach((label) => {
            const langTag = label.lang ? `@${label.lang}` : "";
            lines.push(
              '    ; rdfs:label "' +
                this.escapeTurtle(label.value) +
                '"' +
                langTag,
            );
          });
        }

        // rdfs:comment
        if (property["rdfs:comment"] && options.includeComments !== false) {
          lines.push(
            '    ; rdfs:comment "' +
              this.escapeTurtle(property["rdfs:comment"]) +
              '"@en',
          );
        }

        // rdfs:domain
        if (property["rdfs:domain"]) {
          lines.push("    ; rdfs:domain :" + property["rdfs:domain"]);
        }

        // rdfs:range (datatype)
        if (property["rdfs:range"]) {
          if (property["rdfs:range"].startsWith("xsd:")) {
            lines.push("    ; rdfs:range " + property["rdfs:range"]);
          } else {
            lines.push("    ; rdfs:range <" + property["rdfs:range"] + ">");
          }
        }

        lines.push("    .");
        lines.push("");
      },
    );

    return lines.join("\n");
  }

  private static escapeXML(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  private static escapeTurtle(text: string): string {
    return text
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\n/g, "\\n")
      .replace(/\r/g, "\\r")
      .replace(/\t/g, "\\t");
  }

  static downloadFile(
    content: string,
    filename: string,
    mimeType: string,
  ): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  static getFileExtension(format: ExportOptions["format"]): string {
    switch (format) {
      case "owl":
        return ".owl";
      case "rdf":
        return ".rdf";
      case "turtle":
        return ".ttl";
      default:
        return ".txt";
    }
  }

  static getMimeType(format: ExportOptions["format"]): string {
    switch (format) {
      case "owl":
      case "rdf":
        return "application/rdf+xml";
      case "turtle":
        return "text/turtle";
      default:
        return "text/plain";
    }
  }
}
