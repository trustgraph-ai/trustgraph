/**
 * Ontology Quality Assurance Utilities
 *
 * This module provides tools for automatically fixing common ontology issues
 * and enhancing ontology quality.
 */

import { Ontology } from "@trustgraph/react-state";
import { validateOntology, ValidationError } from "./skos-validation";

export interface QAFix {
  type: "auto" | "manual";
  description: string;
  conceptId?: string;
  field?: string;
  oldValue?: unknown;
  newValue?: unknown;
}

export interface QAResult {
  ontology: Ontology;
  fixes: QAFix[];
  remainingIssues: ValidationError[];
}

export class OntologyQA {
  /**
   * Auto-fix common ontology issues
   */
  static autoFix(ontology: Ontology): QAResult {
    let updatedOntology = { ...ontology };
    const fixes: QAFix[] = [];

    // Fix missing scheme URI
    if (!updatedOntology.scheme.uri && updatedOntology.metadata.namespace) {
      const newUri = `${updatedOntology.metadata.namespace}${updatedOntology.metadata.name.replace(/\s+/g, "-").toLowerCase()}`;
      updatedOntology = {
        ...updatedOntology,
        scheme: {
          ...updatedOntology.scheme,
          uri: newUri,
        },
      };
      fixes.push({
        type: "auto",
        description: "Generated missing scheme URI",
        field: "scheme.uri",
        newValue: newUri,
      });
    }

    // Fix missing scheme prefLabel
    if (!updatedOntology.scheme.prefLabel && updatedOntology.metadata.name) {
      updatedOntology = {
        ...updatedOntology,
        scheme: {
          ...updatedOntology.scheme,
          prefLabel: updatedOntology.metadata.name,
        },
      };
      fixes.push({
        type: "auto",
        description: "Set scheme prefLabel from ontology name",
        field: "scheme.prefLabel",
        newValue: updatedOntology.metadata.name,
      });
    }

    // Fix relationship inconsistencies
    const relationshipFixes =
      this.fixRelationshipInconsistencies(updatedOntology);
    updatedOntology = relationshipFixes.ontology;
    fixes.push(...relationshipFixes.fixes);

    // Remove duplicate relationships
    const duplicateFixes = this.removeDuplicateRelationships(updatedOntology);
    updatedOntology = duplicateFixes.ontology;
    fixes.push(...duplicateFixes.fixes);

    // Fix orphaned concepts by connecting them to existing hierarchy
    const orphanFixes = this.fixOrphanedConcepts(updatedOntology);
    updatedOntology = orphanFixes.ontology;
    fixes.push(...orphanFixes.fixes);

    // Clean up empty relationships
    const cleanupFixes = this.cleanupEmptyRelationships(updatedOntology);
    updatedOntology = cleanupFixes.ontology;
    fixes.push(...cleanupFixes.fixes);

    // Validate the fixed ontology
    const validation = validateOntology(updatedOntology);

    return {
      ontology: updatedOntology,
      fixes,
      remainingIssues: [...validation.errors, ...validation.warnings],
    };
  }

  /**
   * Fix relationship inconsistencies (ensure broader/narrower relationships are reciprocated)
   */
  private static fixRelationshipInconsistencies(ontology: Ontology): {
    ontology: Ontology;
    fixes: QAFix[];
  } {
    const updatedConcepts = { ...ontology.concepts };
    const fixes: QAFix[] = [];

    Object.values(updatedConcepts).forEach((concept) => {
      // Ensure broader relationships are reciprocated
      if (concept.broader && updatedConcepts[concept.broader]) {
        const broaderConcept = updatedConcepts[concept.broader];
        if (!broaderConcept.narrower?.includes(concept.id)) {
          updatedConcepts[concept.broader] = {
            ...broaderConcept,
            narrower: [...(broaderConcept.narrower || []), concept.id],
          };
          fixes.push({
            type: "auto",
            description: `Added ${concept.prefLabel} as narrower concept to ${broaderConcept.prefLabel}`,
            conceptId: concept.broader,
            field: "narrower",
          });
        }
      }

      // Ensure narrower relationships are reciprocated
      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          const narrowerConcept = updatedConcepts[narrowerId];
          if (narrowerConcept && narrowerConcept.broader !== concept.id) {
            updatedConcepts[narrowerId] = {
              ...narrowerConcept,
              broader: concept.id,
            };
            fixes.push({
              type: "auto",
              description: `Set ${concept.prefLabel} as broader concept for ${narrowerConcept.prefLabel}`,
              conceptId: narrowerId,
              field: "broader",
            });
          }
        });
      }

      // Ensure related relationships are symmetric
      if (concept.related) {
        concept.related.forEach((relatedId) => {
          const relatedConcept = updatedConcepts[relatedId];
          if (
            relatedConcept &&
            !relatedConcept.related?.includes(concept.id)
          ) {
            updatedConcepts[relatedId] = {
              ...relatedConcept,
              related: [...(relatedConcept.related || []), concept.id],
            };
            fixes.push({
              type: "auto",
              description: `Made ${concept.prefLabel} and ${relatedConcept.prefLabel} mutually related`,
              conceptId: relatedId,
              field: "related",
            });
          }
        });
      }
    });

    return {
      ontology: {
        ...ontology,
        concepts: updatedConcepts,
      },
      fixes,
    };
  }

  /**
   * Remove duplicate relationships within concepts
   */
  private static removeDuplicateRelationships(ontology: Ontology): {
    ontology: Ontology;
    fixes: QAFix[];
  } {
    const updatedConcepts = { ...ontology.concepts };
    const fixes: QAFix[] = [];

    Object.values(updatedConcepts).forEach((concept) => {
      let hasChanges = false;

      // Remove duplicate narrower relationships
      if (concept.narrower && concept.narrower.length > 0) {
        const uniqueNarrower = [...new Set(concept.narrower)];
        if (uniqueNarrower.length !== concept.narrower.length) {
          updatedConcepts[concept.id] = {
            ...concept,
            narrower: uniqueNarrower,
          };
          hasChanges = true;
        }
      }

      // Remove duplicate related relationships
      if (concept.related && concept.related.length > 0) {
        const uniqueRelated = [...new Set(concept.related)];
        if (uniqueRelated.length !== concept.related.length) {
          updatedConcepts[concept.id] = {
            ...updatedConcepts[concept.id],
            related: uniqueRelated,
          };
          hasChanges = true;
        }
      }

      // Remove duplicate alternative labels
      if (concept.altLabel && concept.altLabel.length > 0) {
        const uniqueAltLabels = [...new Set(concept.altLabel)];
        if (uniqueAltLabels.length !== concept.altLabel.length) {
          updatedConcepts[concept.id] = {
            ...updatedConcepts[concept.id],
            altLabel: uniqueAltLabels,
          };
          hasChanges = true;
        }
      }

      if (hasChanges) {
        fixes.push({
          type: "auto",
          description: `Removed duplicate relationships and labels from ${concept.prefLabel}`,
          conceptId: concept.id,
        });
      }
    });

    return {
      ontology: {
        ...ontology,
        concepts: updatedConcepts,
      },
      fixes,
    };
  }

  /**
   * Fix orphaned concepts by suggesting connections or promoting to top concepts
   */
  private static fixOrphanedConcepts(ontology: Ontology): {
    ontology: Ontology;
    fixes: QAFix[];
  } {
    const updatedOntology = { ...ontology };
    const fixes: QAFix[] = [];
    const concepts = Object.values(ontology.concepts);
    const topConceptIds = new Set(ontology.scheme.hasTopConcept);

    // Find orphaned concepts (no broader and not a top concept)
    const orphanedConcepts = concepts.filter(
      (concept) => !concept.broader && !topConceptIds.has(concept.id),
    );

    if (orphanedConcepts.length > 0) {
      // If there are few orphaned concepts and the ontology is small, promote them to top concepts
      if (orphanedConcepts.length <= 3 && concepts.length <= 20) {
        updatedOntology.scheme = {
          ...updatedOntology.scheme,
          hasTopConcept: [
            ...updatedOntology.scheme.hasTopConcept,
            ...orphanedConcepts.map((c) => c.id),
          ],
        };

        orphanedConcepts.forEach((concept) => {
          fixes.push({
            type: "auto",
            description: `Promoted "${concept.prefLabel}" to top concept`,
            conceptId: concept.id,
          });
        });
      } else {
        // For larger ontologies, suggest manual review
        orphanedConcepts.forEach((concept) => {
          fixes.push({
            type: "manual",
            description: `Orphaned concept "${concept.prefLabel}" needs to be connected to the hierarchy or marked as a top concept`,
            conceptId: concept.id,
          });
        });
      }
    }

    return {
      ontology: updatedOntology,
      fixes,
    };
  }

  /**
   * Clean up empty or invalid relationships
   */
  private static cleanupEmptyRelationships(ontology: Ontology): {
    ontology: Ontology;
    fixes: QAFix[];
  } {
    const updatedConcepts = { ...ontology.concepts };
    const fixes: QAFix[] = [];

    Object.values(updatedConcepts).forEach((concept) => {
      let hasChanges = false;

      // Remove invalid narrower relationships (pointing to non-existent concepts)
      if (concept.narrower && concept.narrower.length > 0) {
        const validNarrower = concept.narrower.filter(
          (id) => updatedConcepts[id],
        );
        if (validNarrower.length !== concept.narrower.length) {
          updatedConcepts[concept.id] = {
            ...concept,
            narrower: validNarrower.length > 0 ? validNarrower : undefined,
          };
          hasChanges = true;
        }
      }

      // Remove invalid related relationships
      if (concept.related && concept.related.length > 0) {
        const validRelated = concept.related.filter(
          (id) => updatedConcepts[id],
        );
        if (validRelated.length !== concept.related.length) {
          updatedConcepts[concept.id] = {
            ...updatedConcepts[concept.id],
            related: validRelated.length > 0 ? validRelated : undefined,
          };
          hasChanges = true;
        }
      }

      // Remove invalid broader relationship
      if (concept.broader && !updatedConcepts[concept.broader]) {
        updatedConcepts[concept.id] = {
          ...updatedConcepts[concept.id],
          broader: undefined,
        };
        hasChanges = true;
      }

      if (hasChanges) {
        fixes.push({
          type: "auto",
          description: `Cleaned up invalid relationships for ${concept.prefLabel}`,
          conceptId: concept.id,
        });
      }
    });

    // Clean up invalid top concepts
    const validTopConcepts = ontology.scheme.hasTopConcept.filter(
      (id) => updatedConcepts[id],
    );
    if (validTopConcepts.length !== ontology.scheme.hasTopConcept.length) {
      const updatedScheme = {
        ...ontology.scheme,
        hasTopConcept: validTopConcepts,
      };

      fixes.push({
        type: "auto",
        description: "Removed invalid top concept references",
        field: "scheme.hasTopConcept",
      });

      return {
        ontology: {
          ...ontology,
          concepts: updatedConcepts,
          scheme: updatedScheme,
        },
        fixes,
      };
    }

    return {
      ontology: {
        ...ontology,
        concepts: updatedConcepts,
      },
      fixes,
    };
  }

  /**
   * Generate quality improvement suggestions
   */
  static generateSuggestions(ontology: Ontology): QAFix[] {
    const suggestions: QAFix[] = [];
    const concepts = Object.values(ontology.concepts);

    // Suggest adding definitions for concepts without them
    concepts
      .filter((c) => !c.definition)
      .forEach((concept) => {
        suggestions.push({
          type: "manual",
          description: `Add definition for "${concept.prefLabel}" to improve clarity`,
          conceptId: concept.id,
          field: "definition",
        });
      });

    // Suggest adding alternative labels for better searchability
    concepts
      .filter((c) => !c.altLabel || c.altLabel.length === 0)
      .forEach((concept) => {
        suggestions.push({
          type: "manual",
          description: `Consider adding alternative labels for "${concept.prefLabel}" to improve searchability`,
          conceptId: concept.id,
          field: "altLabel",
        });
      });

    // Suggest notation for concepts in larger ontologies
    if (concepts.length > 20) {
      concepts
        .filter((c) => !c.notation)
        .forEach((concept) => {
          suggestions.push({
            type: "manual",
            description: `Consider adding notation/code for "${concept.prefLabel}" to aid in referencing`,
            conceptId: concept.id,
            field: "notation",
          });
        });
    }

    // Suggest improving hierarchy depth if too shallow
    const maxDepth = this.calculateMaxDepth(ontology);
    if (maxDepth < 3 && concepts.length > 10) {
      suggestions.push({
        type: "manual",
        description: `Ontology hierarchy is shallow (max depth: ${maxDepth}). Consider adding more specific subconcepts.`,
      });
    }

    return suggestions;
  }

  /**
   * Calculate maximum hierarchy depth
   */
  private static calculateMaxDepth(ontology: Ontology): number {
    const concepts = ontology.concepts;
    const topConcepts = ontology.scheme.hasTopConcept;

    if (topConcepts.length === 0) return 0;

    let maxDepth = 1;

    const calculateDepth = (conceptId: string, currentDepth: number): void => {
      const concept = concepts[conceptId];
      if (!concept) return;

      maxDepth = Math.max(maxDepth, currentDepth);

      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          calculateDepth(narrowerId, currentDepth + 1);
        });
      }
    };

    topConcepts.forEach((topConceptId) => {
      calculateDepth(topConceptId, 1);
    });

    return maxDepth;
  }
}
