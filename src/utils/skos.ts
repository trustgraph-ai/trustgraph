/**
 * SKOS (Simple Knowledge Organization System) Parser and Serializer
 *
 * This module handles conversion between our internal ontology format
 * and standard SKOS RDF/XML and Turtle formats for interoperability.
 */

import {
  Ontology,
  OntologyConcept,
  OntologyScheme,
} from "@trustgraph/react-state";

// SKOS namespace constants
export const SKOS_NAMESPACES = {
  rdf: "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  skos: "http://www.w3.org/2004/02/skos/core#",
  dc: "http://purl.org/dc/terms/",
  dcterms: "http://purl.org/dc/terms/",
} as const;

// SKOS RDF/XML serialization
export class SKOSSerializer {
  private baseURI: string;

  constructor(baseURI?: string) {
    this.baseURI = baseURI || "http://example.org/ontology/";
  }

  /**
   * Convert internal ontology format to SKOS RDF/XML
   */
  toRDF(ontology: Ontology): string {
    const concepts = Object.values(ontology.concepts);
    const scheme = ontology.scheme;

    const rdf = [];

    // RDF/XML header with namespaces
    rdf.push('<?xml version="1.0" encoding="UTF-8"?>');
    rdf.push("<rdf:RDF");
    rdf.push(`  xmlns:rdf="${SKOS_NAMESPACES.rdf}"`);
    rdf.push(`  xmlns:skos="${SKOS_NAMESPACES.skos}"`);
    rdf.push(`  xmlns:dc="${SKOS_NAMESPACES.dc}"`);
    rdf.push(`  xmlns:dcterms="${SKOS_NAMESPACES.dcterms}">`);
    rdf.push("");

    // Concept Scheme
    rdf.push(`  <skos:ConceptScheme rdf:about="${scheme.uri}">`);
    rdf.push(
      `    <skos:prefLabel xml:lang="en">${this.escapeXML(scheme.prefLabel)}</skos:prefLabel>`,
    );
    if (ontology.metadata.description) {
      rdf.push(
        `    <dc:description xml:lang="en">${this.escapeXML(ontology.metadata.description)}</dc:description>`,
      );
    }
    rdf.push(
      `    <dcterms:created>${ontology.metadata.created}</dcterms:created>`,
    );
    rdf.push(
      `    <dcterms:modified>${ontology.metadata.modified}</dcterms:modified>`,
    );
    rdf.push(
      `    <dc:creator>${this.escapeXML(ontology.metadata.creator)}</dc:creator>`,
    );

    // Top concepts
    scheme.hasTopConcept.forEach((conceptId) => {
      rdf.push(
        `    <skos:hasTopConcept rdf:resource="${this.getConceptURI(conceptId)}" />`,
      );
    });

    rdf.push("  </skos:ConceptScheme>");
    rdf.push("");

    // Concepts
    concepts.forEach((concept) => {
      rdf.push(
        `  <skos:Concept rdf:about="${this.getConceptURI(concept.id)}">`,
      );
      rdf.push(`    <skos:inScheme rdf:resource="${scheme.uri}" />`);
      rdf.push(
        `    <skos:prefLabel xml:lang="en">${this.escapeXML(concept.prefLabel)}</skos:prefLabel>`,
      );

      // Alternative labels
      if (concept.altLabel) {
        concept.altLabel.forEach((altLabel) => {
          rdf.push(
            `    <skos:altLabel xml:lang="en">${this.escapeXML(altLabel)}</skos:altLabel>`,
          );
        });
      }

      // Definition
      if (concept.definition) {
        rdf.push(
          `    <skos:definition xml:lang="en">${this.escapeXML(concept.definition)}</skos:definition>`,
        );
      }

      // Scope note
      if (concept.scopeNote) {
        rdf.push(
          `    <skos:scopeNote xml:lang="en">${this.escapeXML(concept.scopeNote)}</skos:scopeNote>`,
        );
      }

      // Examples
      if (concept.example) {
        concept.example.forEach((example) => {
          rdf.push(
            `    <skos:example xml:lang="en">${this.escapeXML(example)}</skos:example>`,
          );
        });
      }

      // Notation
      if (concept.notation) {
        rdf.push(
          `    <skos:notation>${this.escapeXML(concept.notation)}</skos:notation>`,
        );
      }

      // Broader concept
      if (concept.broader) {
        rdf.push(
          `    <skos:broader rdf:resource="${this.getConceptURI(concept.broader)}" />`,
        );
      }

      // Narrower concepts
      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          rdf.push(
            `    <skos:narrower rdf:resource="${this.getConceptURI(narrowerId)}" />`,
          );
        });
      }

      // Related concepts
      if (concept.related) {
        concept.related.forEach((relatedId) => {
          rdf.push(
            `    <skos:related rdf:resource="${this.getConceptURI(relatedId)}" />`,
          );
        });
      }

      // Top concept marker
      if (concept.topConcept) {
        rdf.push(`    <skos:topConceptOf rdf:resource="${scheme.uri}" />`);
      }

      rdf.push("  </skos:Concept>");
      rdf.push("");
    });

    rdf.push("</rdf:RDF>");
    return rdf.join("\n");
  }

  /**
   * Convert internal ontology format to SKOS Turtle
   */
  toTurtle(ontology: Ontology): string {
    const concepts = Object.values(ontology.concepts);
    const scheme = ontology.scheme;

    const ttl = [];

    // Prefixes
    ttl.push("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .");
    ttl.push("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .");
    ttl.push("@prefix dc: <http://purl.org/dc/terms/> .");
    ttl.push("@prefix dcterms: <http://purl.org/dc/terms/> .");
    ttl.push("");

    // Concept Scheme
    ttl.push(`<${scheme.uri}>`);
    ttl.push("  a skos:ConceptScheme ;");
    ttl.push(`  skos:prefLabel "${this.escapeTurtle(scheme.prefLabel)}"@en ;`);
    if (ontology.metadata.description) {
      ttl.push(
        `  dc:description "${this.escapeTurtle(ontology.metadata.description)}"@en ;`,
      );
    }
    ttl.push(`  dcterms:created "${ontology.metadata.created}" ;`);
    ttl.push(`  dcterms:modified "${ontology.metadata.modified}" ;`);
    ttl.push(
      `  dc:creator "${this.escapeTurtle(ontology.metadata.creator)}" ;`,
    );

    // Top concepts
    if (scheme.hasTopConcept.length > 0) {
      const topConcepts = scheme.hasTopConcept
        .map((id) => `<${this.getConceptURI(id)}>`)
        .join(", ");
      ttl.push(`  skos:hasTopConcept ${topConcepts} ;`);
    }

    // Remove trailing semicolon and add period
    const lastLine = ttl[ttl.length - 1];
    ttl[ttl.length - 1] = lastLine.replace(/;$/, " .");
    ttl.push("");

    // Concepts
    concepts.forEach((concept) => {
      ttl.push(`<${this.getConceptURI(concept.id)}>`);
      ttl.push("  a skos:Concept ;");
      ttl.push(`  skos:inScheme <${scheme.uri}> ;`);
      ttl.push(
        `  skos:prefLabel "${this.escapeTurtle(concept.prefLabel)}"@en ;`,
      );

      // Alternative labels
      if (concept.altLabel && concept.altLabel.length > 0) {
        concept.altLabel.forEach((altLabel) => {
          ttl.push(`  skos:altLabel "${this.escapeTurtle(altLabel)}"@en ;`);
        });
      }

      // Definition
      if (concept.definition) {
        ttl.push(
          `  skos:definition "${this.escapeTurtle(concept.definition)}"@en ;`,
        );
      }

      // Scope note
      if (concept.scopeNote) {
        ttl.push(
          `  skos:scopeNote "${this.escapeTurtle(concept.scopeNote)}"@en ;`,
        );
      }

      // Examples
      if (concept.example && concept.example.length > 0) {
        concept.example.forEach((example) => {
          ttl.push(`  skos:example "${this.escapeTurtle(example)}"@en ;`);
        });
      }

      // Notation
      if (concept.notation) {
        ttl.push(`  skos:notation "${this.escapeTurtle(concept.notation)}" ;`);
      }

      // Broader concept
      if (concept.broader) {
        ttl.push(`  skos:broader <${this.getConceptURI(concept.broader)}> ;`);
      }

      // Narrower concepts
      if (concept.narrower && concept.narrower.length > 0) {
        const narrowerConcepts = concept.narrower
          .map((id) => `<${this.getConceptURI(id)}>`)
          .join(", ");
        ttl.push(`  skos:narrower ${narrowerConcepts} ;`);
      }

      // Related concepts
      if (concept.related && concept.related.length > 0) {
        const relatedConcepts = concept.related
          .map((id) => `<${this.getConceptURI(id)}>`)
          .join(", ");
        ttl.push(`  skos:related ${relatedConcepts} ;`);
      }

      // Top concept marker
      if (concept.topConcept) {
        ttl.push(`  skos:topConceptOf <${scheme.uri}> ;`);
      }

      // Remove trailing semicolon and add period
      const lastLine = ttl[ttl.length - 1];
      ttl[ttl.length - 1] = lastLine.replace(/;$/, " .");
      ttl.push("");
    });

    return ttl.join("\n");
  }

  private getConceptURI(conceptId: string): string {
    return this.baseURI + conceptId;
  }

  private escapeXML(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  private escapeTurtle(text: string): string {
    return text
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\n/g, "\\n")
      .replace(/\r/g, "\\r")
      .replace(/\t/g, "\\t");
  }
}

// SKOS Parser for importing
export class SKOSParser {
  /**
   * Parse SKOS RDF/XML and convert to internal ontology format
   */
  async parseRDF(rdfXML: string, ontologyId: string): Promise<Ontology> {
    // For a complete implementation, we'd use a proper RDF parser like rdflib.js
    // For now, we'll implement a simplified parser using DOM parsing

    const parser = new DOMParser();
    const doc = parser.parseFromString(rdfXML, "text/xml");

    // Check for parsing errors
    if (doc.documentElement.nodeName === "parsererror") {
      throw new Error("Invalid XML format");
    }

    const concepts: Record<string, OntologyConcept> = {};
    let scheme: OntologyScheme | null = null;
    const metadata = {
      name: "",
      description: "",
      version: "1.0",
      created: new Date().toISOString(),
      modified: new Date().toISOString(),
      creator: "Imported",
      namespace: "",
    };

    // Parse ConceptScheme
    const conceptSchemes = doc.getElementsByTagNameNS(
      SKOS_NAMESPACES.skos,
      "ConceptScheme",
    );
    if (conceptSchemes.length > 0) {
      const schemeElement = conceptSchemes[0];
      const uri =
        schemeElement.getAttribute("rdf:about") ||
        schemeElement.getAttributeNS(SKOS_NAMESPACES.rdf, "about") ||
        "";
      const prefLabel =
        this.getTextContent(schemeElement, "skos:prefLabel") ||
        "Imported Ontology";
      const description =
        this.getTextContent(schemeElement, "dc:description") ||
        this.getTextContent(schemeElement, "dcterms:description") ||
        "";

      metadata.name = prefLabel;
      metadata.description = description;
      metadata.namespace = uri;

      const created = this.getTextContent(schemeElement, "dcterms:created");
      const modified = this.getTextContent(schemeElement, "dcterms:modified");
      const creator = this.getTextContent(schemeElement, "dc:creator");

      if (created) metadata.created = created;
      if (modified) metadata.modified = modified;
      if (creator) metadata.creator = creator;

      // Get top concepts
      const topConceptElements = schemeElement.getElementsByTagNameNS(
        SKOS_NAMESPACES.skos,
        "hasTopConcept",
      );
      const hasTopConcept = Array.from(topConceptElements).map((el) => {
        const resource =
          el.getAttribute("rdf:resource") ||
          el.getAttributeNS(SKOS_NAMESPACES.rdf, "resource") ||
          "";
        return this.extractConceptId(resource);
      });

      scheme = {
        uri,
        prefLabel,
        hasTopConcept,
      };
    }

    // Parse Concepts
    const conceptElements = doc.getElementsByTagNameNS(
      SKOS_NAMESPACES.skos,
      "Concept",
    );
    Array.from(conceptElements).forEach((conceptElement) => {
      const conceptURI =
        conceptElement.getAttribute("rdf:about") ||
        conceptElement.getAttributeNS(SKOS_NAMESPACES.rdf, "about") ||
        "";
      const conceptId = this.extractConceptId(conceptURI);

      const prefLabel =
        this.getTextContent(conceptElement, "skos:prefLabel") || conceptId;
      const definition = this.getTextContent(
        conceptElement,
        "skos:definition",
      );
      const scopeNote = this.getTextContent(conceptElement, "skos:scopeNote");
      const notation = this.getTextContent(conceptElement, "skos:notation");

      // Get alternative labels
      const altLabels = this.getAllTextContent(
        conceptElement,
        "skos:altLabel",
      );

      // Get examples
      const examples = this.getAllTextContent(conceptElement, "skos:example");

      // Get broader concept
      const broaderElements = conceptElement.getElementsByTagNameNS(
        SKOS_NAMESPACES.skos,
        "broader",
      );
      const broader =
        broaderElements.length > 0
          ? this.extractConceptId(
              broaderElements[0].getAttribute("rdf:resource") ||
                broaderElements[0].getAttributeNS(
                  SKOS_NAMESPACES.rdf,
                  "resource",
                ) ||
                "",
            )
          : null;

      // Get narrower concepts
      const narrowerElements = conceptElement.getElementsByTagNameNS(
        SKOS_NAMESPACES.skos,
        "narrower",
      );
      const narrower = Array.from(narrowerElements).map((el) => {
        const resource =
          el.getAttribute("rdf:resource") ||
          el.getAttributeNS(SKOS_NAMESPACES.rdf, "resource") ||
          "";
        return this.extractConceptId(resource);
      });

      // Get related concepts
      const relatedElements = conceptElement.getElementsByTagNameNS(
        SKOS_NAMESPACES.skos,
        "related",
      );
      const related = Array.from(relatedElements).map((el) => {
        const resource =
          el.getAttribute("rdf:resource") ||
          el.getAttributeNS(SKOS_NAMESPACES.rdf, "resource") ||
          "";
        return this.extractConceptId(resource);
      });

      // Check if it's a top concept
      const topConceptOfElements = conceptElement.getElementsByTagNameNS(
        SKOS_NAMESPACES.skos,
        "topConceptOf",
      );
      const topConcept = topConceptOfElements.length > 0;

      const concept: OntologyConcept = {
        id: conceptId,
        prefLabel,
        broader: broader || null,
        narrower,
        related,
        topConcept,
      };

      if (altLabels.length > 0) concept.altLabel = altLabels;
      if (definition) concept.definition = definition;
      if (scopeNote) concept.scopeNote = scopeNote;
      if (examples.length > 0) concept.example = examples;
      if (notation) concept.notation = notation;

      concepts[conceptId] = concept;
    });

    // If no scheme was found, create a default one
    if (!scheme) {
      scheme = {
        uri: metadata.namespace || `http://example.org/ontology/${ontologyId}`,
        prefLabel: metadata.name || "Imported Ontology",
        hasTopConcept: Object.values(concepts)
          .filter((c) => c.topConcept)
          .map((c) => c.id),
      };
    }

    return {
      metadata,
      concepts,
      scheme,
    };
  }

  /**
   * Parse SKOS Turtle and convert to internal ontology format
   */
  async parseTurtle(): Promise<Ontology> {
    // For a complete implementation, we'd use a proper Turtle parser
    // This is a placeholder for the Turtle parsing functionality
    throw new Error(
      "Turtle parsing not yet implemented. Please use RDF/XML format.",
    );
  }

  private getTextContent(element: Element, selector: string): string | null {
    const [prefix, localName] = selector.split(":");

    // Get namespace URI based on prefix
    let namespaceURI = "";
    switch (prefix) {
      case "skos":
        namespaceURI = SKOS_NAMESPACES.skos;
        break;
      case "dc":
        namespaceURI = SKOS_NAMESPACES.dc;
        break;
      case "dcterms":
        namespaceURI = SKOS_NAMESPACES.dcterms;
        break;
      default:
        namespaceURI = "";
    }

    // Try to find element using namespace
    let el: Element | null = null;
    if (namespaceURI) {
      const elements = element.getElementsByTagNameNS(namespaceURI, localName);
      el = elements.length > 0 ? elements[0] : null;
    }

    // Fallback to querySelector with localName
    if (!el) {
      el = element.querySelector(`*[localName="${localName}"]`);
    }

    return el?.textContent?.trim() || null;
  }

  private getAllTextContent(element: Element, selector: string): string[] {
    const [prefix, localName] = selector.split(":");

    // Get namespace URI based on prefix
    let namespaceURI = "";
    switch (prefix) {
      case "skos":
        namespaceURI = SKOS_NAMESPACES.skos;
        break;
      case "dc":
        namespaceURI = SKOS_NAMESPACES.dc;
        break;
      case "dcterms":
        namespaceURI = SKOS_NAMESPACES.dcterms;
        break;
      default:
        namespaceURI = "";
    }

    // Try to find elements using namespace
    let elements: HTMLCollectionOf<Element> | NodeListOf<Element>;
    if (namespaceURI) {
      elements = element.getElementsByTagNameNS(namespaceURI, localName);
    } else {
      elements = element.querySelectorAll(`*[localName="${localName}"]`);
    }

    return Array.from(elements)
      .map((el) => el.textContent?.trim() || "")
      .filter((text) => text.length > 0);
  }

  private extractConceptId(uri: string): string {
    // Extract the concept ID from the URI (everything after the last # or /)
    const match = uri.match(/[#/]([^#/]+)$/);
    return match ? match[1] : uri;
  }
}

// Convenience functions
export const skosSerializer = new SKOSSerializer();
export const skosParser = new SKOSParser();

// Export functions
export function serializeToSKOS(
  ontology: Ontology,
  format: "rdf" | "turtle" = "rdf",
): string {
  if (format === "turtle") {
    return skosSerializer.toTurtle(ontology);
  }
  return skosSerializer.toRDF(ontology);
}

export async function parseFromSKOS(
  content: string,
  ontologyId: string,
  format: "rdf" | "turtle" = "rdf",
): Promise<Ontology> {
  if (format === "turtle") {
    return skosParser.parseTurtle(content, ontologyId);
  }
  return skosParser.parseRDF(content, ontologyId);
}
