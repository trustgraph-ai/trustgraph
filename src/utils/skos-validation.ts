/**
 * SKOS Validation Utilities
 *
 * This module provides validation functions to ensure ontologies
 * comply with SKOS standards and best practices.
 */

import { Ontology } from "@trustgraph/react-state";

export interface ValidationError {
  type: "error" | "warning" | "info";
  code: string;
  message: string;
  conceptId?: string;
  details?: Record<string, unknown>;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
  info: ValidationError[];
}

export class SKOSValidator {
  /**
   * Comprehensive SKOS validation
   */
  validate(ontology: Ontology): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];
    const info: ValidationError[] = [];

    // Validate scheme
    this.validateScheme(ontology, errors, warnings, info);

    // Validate concepts
    this.validateConcepts(ontology, errors, warnings, info);

    // Validate relationships
    this.validateRelationships(ontology, errors, warnings, info);

    // Validate hierarchy
    this.validateHierarchy(ontology, errors, warnings, info);

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      info,
    };
  }

  private validateScheme(
    ontology: Ontology,
    errors: ValidationError[],
    warnings: ValidationError[],
  ) {
    const { scheme, metadata } = ontology;

    // Required scheme properties
    if (!scheme.uri) {
      errors.push({
        type: "error",
        code: "SCHEME_NO_URI",
        message: "Concept scheme must have a URI",
      });
    }

    if (!scheme.prefLabel) {
      errors.push({
        type: "error",
        code: "SCHEME_NO_PREFLABEL",
        message: "Concept scheme must have a preferred label",
      });
    }

    // URI format validation
    if (scheme.uri && !this.isValidURI(scheme.uri)) {
      warnings.push({
        type: "warning",
        code: "SCHEME_INVALID_URI",
        message: `Scheme URI "${scheme.uri}" may not be a valid URI format`,
      });
    }

    // Top concepts validation
    if (scheme.hasTopConcept.length === 0) {
      warnings.push({
        type: "warning",
        code: "SCHEME_NO_TOP_CONCEPTS",
        message: "Concept scheme has no top concepts defined",
      });
    }

    // Validate that all hasTopConcept references exist
    scheme.hasTopConcept.forEach((conceptId) => {
      if (!ontology.concepts[conceptId]) {
        errors.push({
          type: "error",
          code: "SCHEME_INVALID_TOP_CONCEPT",
          message: `Scheme references non-existent top concept: ${conceptId}`,
          conceptId,
        });
      }
    });

    // Metadata validation
    if (!metadata.name) {
      warnings.push({
        type: "warning",
        code: "METADATA_NO_NAME",
        message: "Ontology should have a name",
      });
    }
  }

  private validateConcepts(
    ontology: Ontology,
    errors: ValidationError[],
    warnings: ValidationError[],
    info: ValidationError[],
  ) {
    const concepts = ontology.concepts;

    Object.values(concepts).forEach((concept) => {
      // Required properties
      if (!concept.prefLabel || concept.prefLabel.trim().length === 0) {
        errors.push({
          type: "error",
          code: "CONCEPT_NO_PREFLABEL",
          message: `Concept ${concept.id} must have a preferred label`,
          conceptId: concept.id,
        });
      }

      // Recommended properties
      if (!concept.definition) {
        warnings.push({
          type: "warning",
          code: "CONCEPT_NO_DEFINITION",
          message: `Concept "${concept.prefLabel}" (${concept.id}) should have a definition`,
          conceptId: concept.id,
        });
      }

      // Alternative labels should not duplicate preferred label
      if (concept.altLabel) {
        concept.altLabel.forEach((altLabel) => {
          if (altLabel === concept.prefLabel) {
            warnings.push({
              type: "warning",
              code: "CONCEPT_DUPLICATE_LABEL",
              message: `Concept "${concept.prefLabel}" has duplicate label in altLabel`,
              conceptId: concept.id,
            });
          }
        });

        // Check for duplicate alternative labels
        const uniqueAltLabels = new Set(concept.altLabel);
        if (uniqueAltLabels.size !== concept.altLabel.length) {
          warnings.push({
            type: "warning",
            code: "CONCEPT_DUPLICATE_ALTLABEL",
            message: `Concept "${concept.prefLabel}" has duplicate alternative labels`,
            conceptId: concept.id,
          });
        }
      }

      // Notation format (if present)
      if (concept.notation && !/^[A-Za-z0-9._-]+$/.test(concept.notation)) {
        info.push({
          type: "info",
          code: "CONCEPT_NOTATION_FORMAT",
          message: `Concept "${concept.prefLabel}" notation "${concept.notation}" uses non-standard characters`,
          conceptId: concept.id,
        });
      }
    });
  }

  private validateRelationships(
    ontology: Ontology,
    errors: ValidationError[],
    warnings: ValidationError[],
  ) {
    const concepts = ontology.concepts;

    Object.values(concepts).forEach((concept) => {
      // Validate broader concept exists
      if (concept.broader && !concepts[concept.broader]) {
        errors.push({
          type: "error",
          code: "CONCEPT_INVALID_BROADER",
          message: `Concept "${concept.prefLabel}" references non-existent broader concept: ${concept.broader}`,
          conceptId: concept.id,
        });
      }

      // Validate narrower concepts exist
      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          if (!concepts[narrowerId]) {
            errors.push({
              type: "error",
              code: "CONCEPT_INVALID_NARROWER",
              message: `Concept "${concept.prefLabel}" references non-existent narrower concept: ${narrowerId}`,
              conceptId: concept.id,
            });
          }
        });
      }

      // Validate related concepts exist
      if (concept.related) {
        concept.related.forEach((relatedId) => {
          if (!concepts[relatedId]) {
            errors.push({
              type: "error",
              code: "CONCEPT_INVALID_RELATED",
              message: `Concept "${concept.prefLabel}" references non-existent related concept: ${relatedId}`,
              conceptId: concept.id,
            });
          }
        });
      }

      // Check for self-references
      if (concept.broader === concept.id) {
        errors.push({
          type: "error",
          code: "CONCEPT_SELF_BROADER",
          message: `Concept "${concept.prefLabel}" cannot be broader than itself`,
          conceptId: concept.id,
        });
      }

      if (concept.narrower?.includes(concept.id)) {
        errors.push({
          type: "error",
          code: "CONCEPT_SELF_NARROWER",
          message: `Concept "${concept.prefLabel}" cannot be narrower than itself`,
          conceptId: concept.id,
        });
      }

      if (concept.related?.includes(concept.id)) {
        errors.push({
          type: "error",
          code: "CONCEPT_SELF_RELATED",
          message: `Concept "${concept.prefLabel}" cannot be related to itself`,
          conceptId: concept.id,
        });
      }

      // Check for broader/narrower consistency
      if (concept.broader && concepts[concept.broader]) {
        const broaderConcept = concepts[concept.broader];
        if (!broaderConcept.narrower?.includes(concept.id)) {
          warnings.push({
            type: "warning",
            code: "RELATIONSHIP_INCONSISTENT_BROADER",
            message: `Concept "${concept.prefLabel}" claims "${broaderConcept.prefLabel}" as broader, but broader concept doesn't list it as narrower`,
            conceptId: concept.id,
          });
        }
      }

      // Check for narrower/broader consistency
      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          const narrowerConcept = concepts[narrowerId];
          if (narrowerConcept && narrowerConcept.broader !== concept.id) {
            warnings.push({
              type: "warning",
              code: "RELATIONSHIP_INCONSISTENT_NARROWER",
              message: `Concept "${concept.prefLabel}" claims "${narrowerConcept.prefLabel}" as narrower, but narrower concept doesn't list it as broader`,
              conceptId: concept.id,
            });
          }
        });
      }

      // Check for related relationship symmetry
      if (concept.related) {
        concept.related.forEach((relatedId) => {
          const relatedConcept = concepts[relatedId];
          if (
            relatedConcept &&
            !relatedConcept.related?.includes(concept.id)
          ) {
            warnings.push({
              type: "warning",
              code: "RELATIONSHIP_ASYMMETRIC_RELATED",
              message: `Concept "${concept.prefLabel}" is related to "${relatedConcept.prefLabel}", but the relationship is not symmetric`,
              conceptId: concept.id,
            });
          }
        });
      }
    });
  }

  private validateHierarchy(
    ontology: Ontology,
    errors: ValidationError[],
    warnings: ValidationError[],
    info: ValidationError[],
  ) {
    const concepts = ontology.concepts;

    // Check for circular references in broader/narrower relationships
    Object.values(concepts).forEach((concept) => {
      if (concept.broader) {
        const visited = new Set<string>();
        let current = concept.id;

        while (current && concepts[current]?.broader) {
          if (visited.has(current)) {
            errors.push({
              type: "error",
              code: "HIERARCHY_CIRCULAR_REFERENCE",
              message: `Circular reference detected in hierarchy starting from concept "${concept.prefLabel}"`,
              conceptId: concept.id,
              details: { path: Array.from(visited) },
            });
            break;
          }
          visited.add(current);
          current = concepts[current].broader!;
        }
      }
    });

    // Check for orphaned concepts (no broader and not a top concept)
    const topConceptIds = new Set(ontology.scheme.hasTopConcept);
    const explicitTopConcepts = new Set(
      Object.values(concepts)
        .filter((c) => c.topConcept)
        .map((c) => c.id),
    );

    Object.values(concepts).forEach((concept) => {
      const hasNoBroader = !concept.broader;
      const isNotTopConcept =
        !topConceptIds.has(concept.id) && !explicitTopConcepts.has(concept.id);

      if (hasNoBroader && isNotTopConcept) {
        warnings.push({
          type: "warning",
          code: "HIERARCHY_ORPHANED_CONCEPT",
          message: `Concept "${concept.prefLabel}" has no broader concept and is not marked as a top concept`,
          conceptId: concept.id,
        });
      }
    });

    // Check for disconnected subhierarchies
    const connectedConcepts = this.findConnectedConcepts(ontology);
    const allConceptIds = new Set(Object.keys(concepts));
    const disconnected = new Set(
      [...allConceptIds].filter((id) => !connectedConcepts.has(id)),
    );

    if (disconnected.size > 0) {
      info.push({
        type: "info",
        code: "HIERARCHY_DISCONNECTED_CONCEPTS",
        message: `Found ${disconnected.size} concepts that are not connected to the main hierarchy`,
        details: { conceptIds: Array.from(disconnected) },
      });
    }
  }

  private findConnectedConcepts(ontology: Ontology): Set<string> {
    const connected = new Set<string>();
    const concepts = ontology.concepts;
    const topConcepts = ontology.scheme.hasTopConcept;

    // Start from top concepts and traverse down
    const toVisit = [...topConcepts];

    while (toVisit.length > 0) {
      const conceptId = toVisit.pop()!;
      if (connected.has(conceptId) || !concepts[conceptId]) continue;

      connected.add(conceptId);

      // Add narrower concepts to visit
      if (concepts[conceptId].narrower) {
        toVisit.push(...concepts[conceptId].narrower!);
      }

      // Also add related concepts
      if (concepts[conceptId].related) {
        toVisit.push(...concepts[conceptId].related!);
      }
    }

    return connected;
  }

  private isValidURI(uri: string): boolean {
    try {
      new URL(uri);
      return true;
    } catch {
      return false;
    }
  }
}

// Convenience functions
export const skosValidator = new SKOSValidator();

export function validateOntology(ontology: Ontology): ValidationResult {
  return skosValidator.validate(ontology);
}

// Format detection utilities
export function detectSKOSFormat(
  content: string,
): "rdf" | "turtle" | "unknown" {
  const trimmed = content.trim();

  // Check for XML declaration or RDF root element
  if (
    trimmed.startsWith("<?xml") ||
    trimmed.includes("<rdf:RDF") ||
    trimmed.includes("<RDF")
  ) {
    return "rdf";
  }

  // Check for Turtle prefixes
  if (
    trimmed.includes("@prefix") ||
    trimmed.includes("@base") ||
    /^\s*<[^>]+>\s+a\s+/.test(trimmed)
  ) {
    return "turtle";
  }

  return "unknown";
}

export function isSKOSContent(content: string): boolean {
  const lowercased = content.toLowerCase();
  return (
    lowercased.includes("skos:") ||
    lowercased.includes("skos/core") ||
    lowercased.includes("conceptscheme") ||
    lowercased.includes("concept") ||
    lowercased.includes("preflabel")
  );
}
