/**
 * Tests for SKOS parser and serializer functionality
 */

import { describe, test, expect } from "vitest";
import {
  SKOSSerializer,
  SKOSParser,
  serializeToSKOS,
  parseFromSKOS,
} from "../skos";
import { validateOntology } from "../skos-validation";
import { Ontology } from "@trustgraph/react-state";

// Sample ontology for testing
const sampleOntology: Ontology = {
  metadata: {
    name: "Test Ontology",
    description: "A sample ontology for testing",
    version: "1.0",
    created: "2024-01-01T00:00:00Z",
    modified: "2024-01-02T00:00:00Z",
    creator: "Test User",
    namespace: "http://example.org/test/",
  },
  scheme: {
    uri: "http://example.org/test/scheme",
    prefLabel: "Test Ontology",
    hasTopConcept: ["concept-1", "concept-2"],
  },
  concepts: {
    "concept-1": {
      id: "concept-1",
      prefLabel: "Animals",
      definition: "Living organisms that feed on organic matter",
      narrower: ["concept-3"],
      topConcept: true,
    },
    "concept-2": {
      id: "concept-2",
      prefLabel: "Plants",
      definition:
        "Living organisms that typically produce their own food through photosynthesis",
      narrower: ["concept-4"],
      topConcept: true,
    },
    "concept-3": {
      id: "concept-3",
      prefLabel: "Mammals",
      definition: "Warm-blooded vertebrate animals",
      broader: "concept-1",
      altLabel: ["Mammalia"],
      example: ["Dog", "Cat", "Human"],
      narrower: [],
      related: [],
    },
    "concept-4": {
      id: "concept-4",
      prefLabel: "Trees",
      definition: "Woody perennial plants with a main trunk",
      broader: "concept-2",
      scopeNote: "Includes both deciduous and evergreen trees",
      notation: "T001",
      narrower: [],
      related: [],
    },
  },
};

describe("SKOS Serializer", () => {
  test("should serialize ontology to RDF/XML", () => {
    const serializer = new SKOSSerializer("http://example.org/test/");
    const rdf = serializer.toRDF(sampleOntology);

    // Check basic structure
    expect(rdf).toContain('<?xml version="1.0" encoding="UTF-8"?>');
    expect(rdf).toContain("<rdf:RDF");
    expect(rdf).toContain('xmlns:skos="http://www.w3.org/2004/02/skos/core#"');

    // Check scheme
    expect(rdf).toContain(
      '<skos:ConceptScheme rdf:about="http://example.org/test/scheme">',
    );
    expect(rdf).toContain(
      '<skos:prefLabel xml:lang="en">Test Ontology</skos:prefLabel>',
    );
    expect(rdf).toContain(
      '<skos:hasTopConcept rdf:resource="http://example.org/test/concept-1"',
    );

    // Check concepts
    expect(rdf).toContain(
      '<skos:Concept rdf:about="http://example.org/test/concept-1">',
    );
    expect(rdf).toContain(
      '<skos:prefLabel xml:lang="en">Animals</skos:prefLabel>',
    );
    expect(rdf).toContain(
      '<skos:definition xml:lang="en">Living organisms that feed on organic matter</skos:definition>',
    );
    expect(rdf).toContain(
      '<skos:narrower rdf:resource="http://example.org/test/concept-3"',
    );

    // Check concept with alternative labels and examples
    expect(rdf).toContain(
      '<skos:altLabel xml:lang="en">Mammalia</skos:altLabel>',
    );
    expect(rdf).toContain('<skos:example xml:lang="en">Dog</skos:example>');
    expect(rdf).toContain("<skos:notation>T001</skos:notation>");
    expect(rdf).toContain(
      '<skos:scopeNote xml:lang="en">Includes both deciduous and evergreen trees</skos:scopeNote>',
    );
  });

  test("should serialize ontology to Turtle", () => {
    const serializer = new SKOSSerializer("http://example.org/test/");
    const turtle = serializer.toTurtle(sampleOntology);

    // Check prefixes
    expect(turtle).toContain(
      "@prefix skos: <http://www.w3.org/2004/02/skos/core#>",
    );
    expect(turtle).toContain("@prefix dc: <http://purl.org/dc/terms/>");

    // Check scheme
    expect(turtle).toContain("<http://example.org/test/scheme>");
    expect(turtle).toContain("a skos:ConceptScheme");
    expect(turtle).toContain('skos:prefLabel "Test Ontology"@en');

    // Check concepts
    expect(turtle).toContain("<http://example.org/test/concept-1>");
    expect(turtle).toContain('skos:prefLabel "Animals"@en');
    expect(turtle).toContain(
      'skos:definition "Living organisms that feed on organic matter"@en',
    );
  });

  test("should handle XML escaping correctly", () => {
    const ontologyWithSpecialChars: Ontology = {
      ...sampleOntology,
      concepts: {
        "concept-1": {
          id: "concept-1",
          prefLabel: "Test & Example <tag>",
          definition: "Definition with \"quotes\" and 'apostrophes'",
          narrower: [],
          related: [],
        },
      },
    };

    const serializer = new SKOSSerializer();
    const rdf = serializer.toRDF(ontologyWithSpecialChars);

    expect(rdf).toContain("Test &amp; Example &lt;tag&gt;");
    expect(rdf).toContain(
      "Definition with &quot;quotes&quot; and &apos;apostrophes&apos;",
    );
  });
});

describe("SKOS Parser", () => {
  test("should parse simple RDF/XML", async () => {
    const rdfXML = `<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF 
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:skos="http://www.w3.org/2004/02/skos/core#"
      xmlns:dc="http://purl.org/dc/terms/">
      
      <skos:ConceptScheme rdf:about="http://example.org/test-scheme">
        <skos:prefLabel xml:lang="en">Test Scheme</skos:prefLabel>
        <dc:description xml:lang="en">A test concept scheme</dc:description>
        <skos:hasTopConcept rdf:resource="http://example.org/concept1" />
      </skos:ConceptScheme>
      
      <skos:Concept rdf:about="http://example.org/concept1">
        <skos:inScheme rdf:resource="http://example.org/test-scheme" />
        <skos:prefLabel xml:lang="en">Test Concept</skos:prefLabel>
        <skos:definition xml:lang="en">A test concept definition</skos:definition>
        <skos:altLabel xml:lang="en">Alternative Label</skos:altLabel>
        <skos:topConceptOf rdf:resource="http://example.org/test-scheme" />
      </skos:Concept>
      
    </rdf:RDF>`;

    const parser = new SKOSParser();
    const ontology = await parser.parseRDF(rdfXML, "test-ontology");

    // Check metadata
    expect(ontology.metadata.name).toBe("Test Scheme");
    expect(ontology.metadata.description).toBe("A test concept scheme");

    // Check scheme
    expect(ontology.scheme.uri).toBe("http://example.org/test-scheme");
    expect(ontology.scheme.prefLabel).toBe("Test Scheme");
    expect(ontology.scheme.hasTopConcept).toContain("concept1");

    // Check concepts
    expect(ontology.concepts["concept1"]).toBeDefined();
    expect(ontology.concepts["concept1"].prefLabel).toBe("Test Concept");
    expect(ontology.concepts["concept1"].definition).toBe(
      "A test concept definition",
    );
    expect(ontology.concepts["concept1"].altLabel).toContain(
      "Alternative Label",
    );
    expect(ontology.concepts["concept1"].topConcept).toBe(true);
  });

  test("should handle parsing errors gracefully", async () => {
    const invalidXML = "<invalid>xml</content>";

    const parser = new SKOSParser();
    await expect(parser.parseRDF(invalidXML, "test")).rejects.toThrow(
      "Invalid XML format",
    );
  });
});

describe("SKOS Validation", () => {
  test("should validate correct ontology", () => {
    const result = validateOntology(sampleOntology);

    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test("should detect missing preferred labels", () => {
    const invalidOntology: Ontology = {
      ...sampleOntology,
      concepts: {
        "concept-1": {
          id: "concept-1",
          prefLabel: "", // Empty label
          narrower: [],
          related: [],
        },
      },
    };

    const result = validateOntology(invalidOntology);

    expect(result.isValid).toBe(false);
    expect(result.errors.some((e) => e.code === "CONCEPT_NO_PREFLABEL")).toBe(
      true,
    );
  });

  test("should detect circular references", () => {
    const circularOntology: Ontology = {
      ...sampleOntology,
      concepts: {
        "concept-1": {
          id: "concept-1",
          prefLabel: "A",
          broader: "concept-2",
          narrower: [],
          related: [],
        },
        "concept-2": {
          id: "concept-2",
          prefLabel: "B",
          broader: "concept-1", // Circular reference
          narrower: [],
          related: [],
        },
      },
    };

    const result = validateOntology(circularOntology);

    expect(result.isValid).toBe(false);
    expect(
      result.errors.some((e) => e.code === "HIERARCHY_CIRCULAR_REFERENCE"),
    ).toBe(true);
  });

  test("should detect invalid concept references", () => {
    const invalidRefOntology: Ontology = {
      ...sampleOntology,
      concepts: {
        "concept-1": {
          id: "concept-1",
          prefLabel: "Test",
          broader: "non-existent-concept", // Invalid reference
          narrower: [],
          related: [],
        },
      },
    };

    const result = validateOntology(invalidRefOntology);

    expect(result.isValid).toBe(false);
    expect(
      result.errors.some((e) => e.code === "CONCEPT_INVALID_BROADER"),
    ).toBe(true);
  });
});

describe("Convenience Functions", () => {
  test("should serialize to SKOS RDF by default", () => {
    const result = serializeToSKOS(sampleOntology);

    expect(result).toContain('<?xml version="1.0" encoding="UTF-8"?>');
    expect(result).toContain("<rdf:RDF");
  });

  test("should serialize to SKOS Turtle when specified", () => {
    const result = serializeToSKOS(sampleOntology, "turtle");

    expect(result).toContain("@prefix skos:");
    expect(result).toContain("a skos:ConceptScheme");
  });

  test("should parse from SKOS RDF by default", async () => {
    const rdfXML = `<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF 
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:skos="http://www.w3.org/2004/02/skos/core#">
      
      <skos:ConceptScheme rdf:about="http://example.org/scheme">
        <skos:prefLabel xml:lang="en">Test</skos:prefLabel>
      </skos:ConceptScheme>
      
    </rdf:RDF>`;

    const result = await parseFromSKOS(rdfXML, "test");

    expect(result.scheme.prefLabel).toBe("Test");
  });
});
