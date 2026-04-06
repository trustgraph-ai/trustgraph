import {
  Ontology,
  OWLClass,
  OWLObjectProperty,
  OWLDatatypeProperty,
  OntologyMetadata,
} from "@trustgraph/react-state";
import { Parser, Store, DataFactory } from "n3";

const { namedNode } = DataFactory;

// Common RDF/OWL namespace URIs
const RDF = {
  type: namedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
};
const RDFS = {
  label: namedNode("http://www.w3.org/2000/01/rdf-schema#label"),
  comment: namedNode("http://www.w3.org/2000/01/rdf-schema#comment"),
  domain: namedNode("http://www.w3.org/2000/01/rdf-schema#domain"),
  range: namedNode("http://www.w3.org/2000/01/rdf-schema#range"),
  subClassOf: namedNode("http://www.w3.org/2000/01/rdf-schema#subClassOf"),
};
const OWL = {
  Ontology: namedNode("http://www.w3.org/2002/07/owl#Ontology"),
  Class: namedNode("http://www.w3.org/2002/07/owl#Class"),
  ObjectProperty: namedNode("http://www.w3.org/2002/07/owl#ObjectProperty"),
  DatatypeProperty: namedNode(
    "http://www.w3.org/2002/07/owl#DatatypeProperty",
  ),
  versionInfo: namedNode("http://www.w3.org/2002/07/owl#versionInfo"),
};
const DCTERMS = {
  title: namedNode("http://purl.org/dc/terms/title"),
  created: namedNode("http://purl.org/dc/terms/created"),
};

export type ImportFormat = "owl" | "rdf" | "turtle";

export interface ImportOptions {
  format: ImportFormat;
  overwriteExisting?: boolean;
  mergeWithExisting?: boolean;
}

export class OntologyImporter {
  static async import(
    content: string,
    options: ImportOptions,
  ): Promise<Ontology> {
    switch (options.format) {
      case "owl":
        return this.parseOWL(content);
      case "rdf":
        return this.parseRDF(content);
      case "turtle":
        return this.parseTurtle(content);
      default:
        throw new Error(`Unsupported import format: ${options.format}`);
    }
  }

  static detectFormat(content: string): ImportFormat | null {
    // Trim and get first meaningful line
    const trimmed = content.trim();

    // Check for OWL/XML
    if (
      trimmed.startsWith("<?xml") ||
      trimmed.includes("<rdf:RDF") ||
      trimmed.includes("<owl:Ontology")
    ) {
      // Distinguish between OWL and RDF
      if (trimmed.includes("<owl:Ontology") || trimmed.includes("owl:Class")) {
        return "owl";
      }
      return "rdf";
    }

    // Check for Turtle
    if (
      trimmed.includes("@prefix") ||
      trimmed.includes("@base") ||
      trimmed.includes("a owl:") ||
      trimmed.includes("a rdfs:")
    ) {
      return "turtle";
    }

    return null;
  }

  private static parseOWL(content: string): Ontology {
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, "text/xml");

    // Check for parse errors
    const parseError = doc.querySelector("parsererror");
    if (parseError) {
      throw new Error("Invalid XML/OWL format: " + parseError.textContent);
    }

    // Extract ontology metadata
    const ontologyElement = doc.querySelector("Ontology");
    const metadata = this.extractMetadata(doc, ontologyElement);

    // Extract classes
    const classes: Record<string, OWLClass> = {};
    const classElements = doc.querySelectorAll("Class");

    classElements.forEach((classEl) => {
      const uri =
        classEl.getAttribute("rdf:about") ||
        classEl.getAttribute("rdf:ID") ||
        "";
      if (!uri) return;

      const classId = this.extractId(uri, metadata.namespace);
      const labels = this.extractLabels(classEl);
      const comment = this.extractComment(classEl);
      const subClassOf = this.extractSubClassOf(classEl, metadata.namespace);

      classes[classId] = {
        uri,
        type: "owl:Class",
        "rdfs:label": labels.length > 0 ? labels : undefined,
        "rdfs:comment": comment || undefined,
        "rdfs:subClassOf": subClassOf || undefined,
      };
    });

    // Extract object properties
    const objectProperties: Record<string, OWLObjectProperty> = {};
    const objectPropElements = doc.querySelectorAll("ObjectProperty");

    objectPropElements.forEach((propEl) => {
      const uri =
        propEl.getAttribute("rdf:about") ||
        propEl.getAttribute("rdf:ID") ||
        "";
      if (!uri) return;

      const propId = this.extractId(uri, metadata.namespace);
      const labels = this.extractLabels(propEl);
      const comment = this.extractComment(propEl);
      const domain = this.extractDomain(propEl, metadata.namespace);
      const range = this.extractRange(propEl, metadata.namespace);

      objectProperties[propId] = {
        uri,
        type: "owl:ObjectProperty",
        "rdfs:label": labels.length > 0 ? labels : undefined,
        "rdfs:comment": comment || undefined,
        "rdfs:domain": domain || undefined,
        "rdfs:range": range || undefined,
      };
    });

    // Extract datatype properties
    const datatypeProperties: Record<string, OWLDatatypeProperty> = {};
    const datatypePropElements = doc.querySelectorAll("DatatypeProperty");

    datatypePropElements.forEach((propEl) => {
      const uri =
        propEl.getAttribute("rdf:about") ||
        propEl.getAttribute("rdf:ID") ||
        "";
      if (!uri) return;

      const propId = this.extractId(uri, metadata.namespace);
      const labels = this.extractLabels(propEl);
      const comment = this.extractComment(propEl);
      const domain = this.extractDomain(propEl, metadata.namespace);
      const range =
        propEl.querySelector("range")?.getAttribute("rdf:resource") ||
        "xsd:string";

      datatypeProperties[propId] = {
        uri,
        type: "owl:DatatypeProperty",
        "rdfs:label": labels.length > 0 ? labels : undefined,
        "rdfs:comment": comment || undefined,
        "rdfs:domain": domain || undefined,
        "rdfs:range": range.includes("xsd:") ? range : "xsd:string",
      };
    });

    return {
      metadata,
      classes,
      objectProperties,
      datatypeProperties,
    };
  }

  private static parseRDF(content: string): Ontology {
    // RDF/XML is similar to OWL/XML but with different namespace usage
    // For now, we'll use the same parser with slight modifications
    return this.parseOWL(content);
  }

  private static parseTurtle(content: string): Ontology {
    // Parse Turtle using N3.js
    const parser = new Parser();
    const quads = parser.parse(content); // Synchronous parsing
    const store = new Store(quads);

    // Extract namespace prefixes from content using regex
    const prefixes: Record<string, string> = {};
    const prefixRegex = /@prefix\s+(\w*):?\s+<([^>]+)>/g;
    let match;
    while ((match = prefixRegex.exec(content)) !== null) {
      const prefix = match[1] || ""; // Empty string for default prefix
      const uri = match[2];
      prefixes[prefix] = uri;
    }

    const metadata: OntologyMetadata = {
      name: "Imported Ontology",
      description: "",
      version: "1.0",
      created: new Date().toISOString(),
      modified: new Date().toISOString(),
      creator: "",
      namespace: "",
      namespaces: prefixes,
    };

    const classes: Record<string, OWLClass> = {};
    const objectProperties: Record<string, OWLObjectProperty> = {};
    const datatypeProperties: Record<string, OWLDatatypeProperty> = {};

    // Helper function to extract local name from URI
    const extractLocalName = (uri: string, namespace: string): string => {
      if (uri.startsWith(namespace)) {
        return uri.slice(namespace.length);
      }
      // Try to extract after # or /
      const hashIndex = uri.lastIndexOf("#");
      const slashIndex = uri.lastIndexOf("/");
      const index = Math.max(hashIndex, slashIndex);
      return index >= 0 ? uri.slice(index + 1) : uri;
    };

    // Extract ontology URI and metadata
    const ontologyQuads = store.getQuads(null, RDF.type, OWL.Ontology, null);
    if (ontologyQuads.length > 0) {
      const ontologySubject = ontologyQuads[0].subject;
      // Store the ontology's own URI in the namespace field
      metadata.namespace = ontologySubject.value;

      // Extract title
      const titleQuads = [
        ...store.getQuads(ontologySubject, DCTERMS.title, null, null),
        ...store.getQuads(ontologySubject, RDFS.label, null, null),
      ];
      if (
        titleQuads.length > 0 &&
        titleQuads[0].object.termType === "Literal"
      ) {
        metadata.name = titleQuads[0].object.value;
      }

      // Extract description
      const commentQuads = store.getQuads(
        ontologySubject,
        RDFS.comment,
        null,
        null,
      );
      if (
        commentQuads.length > 0 &&
        commentQuads[0].object.termType === "Literal"
      ) {
        metadata.description = commentQuads[0].object.value;
      }

      // Extract version
      const versionQuads = store.getQuads(
        ontologySubject,
        OWL.versionInfo,
        null,
        null,
      );
      if (
        versionQuads.length > 0 &&
        versionQuads[0].object.termType === "Literal"
      ) {
        metadata.version = versionQuads[0].object.value;
      }

      // Extract created date
      const createdQuads = store.getQuads(
        ontologySubject,
        DCTERMS.created,
        null,
        null,
      );
      if (
        createdQuads.length > 0 &&
        createdQuads[0].object.termType === "Literal"
      ) {
        metadata.created = createdQuads[0].object.value;
      }
    }

    // Determine the base namespace for classes in this ontology
    // Usually classes share a common prefix with the ontology URI
    const ontologyBaseNS = metadata.namespace;

    // Extract classes
    const classQuads = store.getQuads(null, RDF.type, OWL.Class, null);
    for (const quad of classQuads) {
      const classURI = quad.subject.value;

      // Only include classes from this ontology's namespace
      // Classes whose URI starts with the ontology's base namespace are considered internal
      if (!ontologyBaseNS || !classURI.startsWith(ontologyBaseNS)) {
        continue;
      }

      const classId = extractLocalName(classURI, ontologyBaseNS);

      classes[classId] = {
        uri: classURI,
        type: "owl:Class",
      };

      // Extract labels
      const labelQuads = store.getQuads(quad.subject, RDFS.label, null, null);
      const labels: Array<{ value: string; lang?: string }> = [];
      for (const labelQuad of labelQuads) {
        if (labelQuad.object.termType === "Literal") {
          labels.push({
            value: labelQuad.object.value,
            lang: labelQuad.object.language || "en",
          });
        }
      }
      if (labels.length > 0) {
        classes[classId]["rdfs:label"] = labels;
      }

      // Extract comment
      const commentQuads = store.getQuads(
        quad.subject,
        RDFS.comment,
        null,
        null,
      );
      if (
        commentQuads.length > 0 &&
        commentQuads[0].object.termType === "Literal"
      ) {
        classes[classId]["rdfs:comment"] = commentQuads[0].object.value;
      }

      // Extract subClassOf (only internal references)
      const subClassQuads = store.getQuads(
        quad.subject,
        RDFS.subClassOf,
        null,
        null,
      );
      if (
        subClassQuads.length > 0 &&
        subClassQuads[0].object.termType === "NamedNode"
      ) {
        const parentURI = subClassQuads[0].object.value;
        if (parentURI.startsWith(ontologyBaseNS)) {
          classes[classId]["rdfs:subClassOf"] = extractLocalName(
            parentURI,
            ontologyBaseNS,
          );
        }
      }
    }

    // Extract object properties
    const objPropQuads = store.getQuads(
      null,
      RDF.type,
      OWL.ObjectProperty,
      null,
    );
    for (const quad of objPropQuads) {
      const propURI = quad.subject.value;

      // Only include properties from this ontology's namespace
      if (!ontologyBaseNS || !propURI.startsWith(ontologyBaseNS)) {
        continue;
      }

      const propId = extractLocalName(propURI, ontologyBaseNS);

      objectProperties[propId] = {
        uri: propURI,
        type: "owl:ObjectProperty",
      };

      // Extract labels
      const labelQuads = store.getQuads(quad.subject, RDFS.label, null, null);
      const labels: Array<{ value: string; lang?: string }> = [];
      for (const labelQuad of labelQuads) {
        if (labelQuad.object.termType === "Literal") {
          labels.push({
            value: labelQuad.object.value,
            lang: labelQuad.object.language || "en",
          });
        }
      }
      if (labels.length > 0) {
        objectProperties[propId]["rdfs:label"] = labels;
      }

      // Extract comment
      const commentQuads = store.getQuads(
        quad.subject,
        RDFS.comment,
        null,
        null,
      );
      if (
        commentQuads.length > 0 &&
        commentQuads[0].object.termType === "Literal"
      ) {
        objectProperties[propId]["rdfs:comment"] =
          commentQuads[0].object.value;
      }

      // Extract domain (only internal references)
      const domainQuads = store.getQuads(
        quad.subject,
        RDFS.domain,
        null,
        null,
      );
      if (
        domainQuads.length > 0 &&
        domainQuads[0].object.termType === "NamedNode"
      ) {
        const domainURI = domainQuads[0].object.value;
        if (domainURI.startsWith(ontologyBaseNS)) {
          objectProperties[propId]["rdfs:domain"] = extractLocalName(
            domainURI,
            ontologyBaseNS,
          );
        }
      }

      // Extract range (only internal references)
      const rangeQuads = store.getQuads(quad.subject, RDFS.range, null, null);
      if (
        rangeQuads.length > 0 &&
        rangeQuads[0].object.termType === "NamedNode"
      ) {
        const rangeURI = rangeQuads[0].object.value;
        if (rangeURI.startsWith(ontologyBaseNS)) {
          objectProperties[propId]["rdfs:range"] = extractLocalName(
            rangeURI,
            ontologyBaseNS,
          );
        }
      }
    }

    // Extract datatype properties
    const dtPropQuads = store.getQuads(
      null,
      RDF.type,
      OWL.DatatypeProperty,
      null,
    );
    for (const quad of dtPropQuads) {
      const propURI = quad.subject.value;

      // Only include properties from this ontology's namespace
      if (!ontologyBaseNS || !propURI.startsWith(ontologyBaseNS)) {
        continue;
      }

      const propId = extractLocalName(propURI, ontologyBaseNS);

      datatypeProperties[propId] = {
        uri: propURI,
        type: "owl:DatatypeProperty",
        "rdfs:range": "xsd:string",
      };

      // Extract labels
      const labelQuads = store.getQuads(quad.subject, RDFS.label, null, null);
      const labels: Array<{ value: string; lang?: string }> = [];
      for (const labelQuad of labelQuads) {
        if (labelQuad.object.termType === "Literal") {
          labels.push({
            value: labelQuad.object.value,
            lang: labelQuad.object.language || "en",
          });
        }
      }
      if (labels.length > 0) {
        datatypeProperties[propId]["rdfs:label"] = labels;
      }

      // Extract comment
      const commentQuads = store.getQuads(
        quad.subject,
        RDFS.comment,
        null,
        null,
      );
      if (
        commentQuads.length > 0 &&
        commentQuads[0].object.termType === "Literal"
      ) {
        datatypeProperties[propId]["rdfs:comment"] =
          commentQuads[0].object.value;
      }

      // Extract domain (only internal references)
      const domainQuads = store.getQuads(
        quad.subject,
        RDFS.domain,
        null,
        null,
      );
      if (
        domainQuads.length > 0 &&
        domainQuads[0].object.termType === "NamedNode"
      ) {
        const domainURI = domainQuads[0].object.value;
        if (domainURI.startsWith(ontologyBaseNS)) {
          datatypeProperties[propId]["rdfs:domain"] = extractLocalName(
            domainURI,
            ontologyBaseNS,
          );
        }
      }

      // Extract range (XSD datatypes)
      const rangeQuads = store.getQuads(quad.subject, RDFS.range, null, null);
      if (
        rangeQuads.length > 0 &&
        rangeQuads[0].object.termType === "NamedNode"
      ) {
        const rangeURI = rangeQuads[0].object.value;
        // Keep XSD datatypes as-is
        if (rangeURI.startsWith("http://www.w3.org/2001/XMLSchema#")) {
          datatypeProperties[propId]["rdfs:range"] =
            "xsd:" +
            extractLocalName(rangeURI, "http://www.w3.org/2001/XMLSchema#");
        }
      }
    }

    return {
      metadata,
      classes,
      objectProperties,
      datatypeProperties,
    };
  }

  private static extractMetadata(
    doc: Document,
    ontologyElement: Element | null,
  ): OntologyMetadata {
    const namespace =
      ontologyElement?.getAttribute("rdf:about") ||
      doc.documentElement.getAttribute("xml:base") ||
      "http://example.org/ontology#";

    const title =
      doc.querySelector("Ontology > title")?.textContent ||
      doc.querySelector("Ontology > label")?.textContent ||
      "Imported Ontology";

    const description =
      doc.querySelector("Ontology > comment")?.textContent ||
      doc.querySelector("Ontology > description")?.textContent ||
      "";

    const creator =
      doc.querySelector("Ontology > creator")?.textContent ||
      doc.querySelector("Ontology > contributor")?.textContent ||
      "";

    const version =
      doc.querySelector("Ontology > versionInfo")?.textContent || "1.0";

    return {
      name: title,
      description,
      version,
      created: new Date().toISOString(),
      modified: new Date().toISOString(),
      creator,
      namespace:
        namespace.endsWith("#") || namespace.endsWith("/")
          ? namespace
          : namespace + "#",
    };
  }

  private static extractId(uri: string, namespace: string): string {
    if (uri.startsWith(namespace)) {
      return uri.substring(namespace.length);
    }
    // Extract ID from the URI (last part after # or /)
    const match = uri.match(/[#/]([^#/]+)$/);
    return match ? match[1] : uri;
  }

  private static extractLabels(
    element: Element,
  ): Array<{ value: string; lang?: string }> {
    const labels: Array<{ value: string; lang?: string }> = [];
    const labelElements = element.querySelectorAll("label");

    labelElements.forEach((label) => {
      const value = label.textContent;
      const lang = label.getAttribute("xml:lang") || "en";
      if (value) {
        labels.push({ value, lang });
      }
    });

    return labels;
  }

  private static extractComment(element: Element): string | null {
    return element.querySelector("comment")?.textContent || null;
  }

  private static extractSubClassOf(
    element: Element,
    namespace: string,
  ): string | null {
    const subClassElement = element.querySelector("subClassOf");
    if (!subClassElement) return null;

    const resource = subClassElement.getAttribute("rdf:resource");
    if (!resource) return null;

    return this.extractId(resource, namespace);
  }

  private static extractDomain(
    element: Element,
    namespace: string,
  ): string | null {
    const domainElement = element.querySelector("domain");
    if (!domainElement) return null;

    const resource = domainElement.getAttribute("rdf:resource");
    if (!resource) return null;

    return this.extractId(resource, namespace);
  }

  private static extractRange(
    element: Element,
    namespace: string,
  ): string | null {
    const rangeElement = element.querySelector("range");
    if (!rangeElement) return null;

    const resource = rangeElement.getAttribute("rdf:resource");
    if (!resource) return null;

    return this.extractId(resource, namespace);
  }
}
