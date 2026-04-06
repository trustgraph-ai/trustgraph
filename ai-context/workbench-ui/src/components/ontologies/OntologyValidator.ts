import { Ontology } from "@trustgraph/react-state";

export interface ValidationIssue {
  type: "error" | "warning" | "info";
  category: "classes" | "properties" | "metadata" | "structure";
  itemId?: string;
  itemType?: "class" | "objectProperty" | "datatypeProperty";
  message: string;
  suggestion?: string;
}

export interface ValidationResult {
  isValid: boolean;
  issues: ValidationIssue[];
  summary: {
    errors: number;
    warnings: number;
    info: number;
  };
}

export class OntologyValidator {
  static validate(ontology: Ontology): ValidationResult {
    const issues: ValidationIssue[] = [];

    // Validate metadata
    issues.push(...this.validateMetadata(ontology));

    // Validate classes
    issues.push(...this.validateClasses(ontology));

    // Validate properties
    issues.push(...this.validateProperties(ontology));

    // Validate structure and relationships
    issues.push(...this.validateStructure(ontology));

    const summary = {
      errors: issues.filter((i) => i.type === "error").length,
      warnings: issues.filter((i) => i.type === "warning").length,
      info: issues.filter((i) => i.type === "info").length,
    };

    return {
      isValid: summary.errors === 0,
      issues,
      summary,
    };
  }

  private static validateMetadata(ontology: Ontology): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Check required metadata
    if (!ontology.metadata.name?.trim()) {
      issues.push({
        type: "error",
        category: "metadata",
        message: "Ontology name is required",
        suggestion: "Add a descriptive name for your ontology",
      });
    }

    if (!ontology.metadata.description?.trim()) {
      issues.push({
        type: "warning",
        category: "metadata",
        message: "Ontology description is missing",
        suggestion:
          "Add a description to help others understand the purpose of this ontology",
      });
    }

    // Check namespace URI format
    if (!ontology.metadata.namespace) {
      issues.push({
        type: "error",
        category: "metadata",
        message: "Namespace URI is required",
        suggestion:
          "Set a valid namespace URI (e.g., http://example.org/myontology#)",
      });
    } else if (!this.isValidURI(ontology.metadata.namespace)) {
      issues.push({
        type: "error",
        category: "metadata",
        message: "Invalid namespace URI format",
        suggestion: "Use a valid URI format starting with http:// or https://",
      });
    }

    return issues;
  }

  private static validateClasses(ontology: Ontology): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    Object.entries(ontology.classes).forEach(([classId, owlClass]) => {
      // Check for missing labels
      if (
        !owlClass["rdfs:label"] ||
        owlClass["rdfs:label"].length === 0 ||
        !owlClass["rdfs:label"][0]?.value?.trim()
      ) {
        issues.push({
          type: "warning",
          category: "classes",
          itemId: classId,
          itemType: "class",
          message: `Class "${classId}" has no label`,
          suggestion:
            "Add a human-readable label to make the class easier to understand",
        });
      }

      // Check for missing comments
      if (!owlClass["rdfs:comment"]?.trim()) {
        issues.push({
          type: "info",
          category: "classes",
          itemId: classId,
          itemType: "class",
          message: `Class "${classId}" has no description`,
          suggestion: "Add a comment to explain what this class represents",
        });
      }

      // Check for invalid subclass references
      const subClassOf = owlClass["rdfs:subClassOf"];
      if (subClassOf && !ontology.classes[subClassOf]) {
        // Check if this is an external class reference (from standard vocabularies)
        const isExternalRef = this.isExternalClassReference(
          subClassOf,
          owlClass.uri,
        );
        if (!isExternalRef) {
          issues.push({
            type: "error",
            category: "classes",
            itemId: classId,
            itemType: "class",
            message: `Class "${classId}" references non-existent parent class "${subClassOf}"`,
            suggestion:
              "Remove the invalid parent reference or create the missing class",
          });
        }
      }

      // Check URI format
      if (!this.isValidURI(owlClass.uri)) {
        issues.push({
          type: "error",
          category: "classes",
          itemId: classId,
          itemType: "class",
          message: `Class "${classId}" has invalid URI format`,
          suggestion: "Ensure the URI follows a valid format",
        });
      }
    });

    // Check for circular dependencies
    const circularDeps = this.findCircularDependencies(ontology);
    circularDeps.forEach((cycle) => {
      issues.push({
        type: "error",
        category: "structure",
        message: `Circular dependency detected in class hierarchy: ${cycle.join(" → ")}`,
        suggestion:
          "Remove one of the subclass relationships to break the cycle",
      });
    });

    return issues;
  }

  private static validateProperties(ontology: Ontology): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Validate object properties
    Object.entries(ontology.objectProperties).forEach(([propId, property]) => {
      issues.push(
        ...this.validateProperty(propId, property, "objectProperty", ontology),
      );
    });

    // Validate datatype properties
    Object.entries(ontology.datatypeProperties).forEach(
      ([propId, property]) => {
        issues.push(
          ...this.validateProperty(
            propId,
            property,
            "datatypeProperty",
            ontology,
          ),
        );
      },
    );

    return issues;
  }

  private static validateProperty(
    propId: string,
    property: unknown,
    propType: "objectProperty" | "datatypeProperty",
    ontology: Ontology,
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Check for missing labels
    if (
      !property["rdfs:label"] ||
      property["rdfs:label"].length === 0 ||
      !property["rdfs:label"][0]?.value?.trim()
    ) {
      issues.push({
        type: "warning",
        category: "properties",
        itemId: propId,
        itemType: propType,
        message: `${propType === "objectProperty" ? "Object" : "Datatype"} property "${propId}" has no label`,
        suggestion:
          "Add a human-readable label to make the property easier to understand",
      });
    }

    // Check for missing comments
    if (!property["rdfs:comment"]?.trim()) {
      issues.push({
        type: "info",
        category: "properties",
        itemId: propId,
        itemType: propType,
        message: `${propType === "objectProperty" ? "Object" : "Datatype"} property "${propId}" has no description`,
        suggestion: "Add a comment to explain what this property represents",
      });
    }

    // Check domain references
    const domain = property["rdfs:domain"];
    if (domain && !ontology.classes[domain]) {
      const isExternalRef = this.isExternalClassReference(
        domain,
        property.uri,
      );
      if (!isExternalRef) {
        issues.push({
          type: "error",
          category: "properties",
          itemId: propId,
          itemType: propType,
          message: `Property "${propId}" references non-existent domain class "${domain}"`,
          suggestion:
            "Remove the invalid domain reference or create the missing class",
        });
      }
    }

    // Check range references for object properties
    if (propType === "objectProperty") {
      const range = property["rdfs:range"];
      if (range && !ontology.classes[range]) {
        const isExternalRef = this.isExternalClassReference(
          range,
          property.uri,
        );
        if (!isExternalRef) {
          issues.push({
            type: "error",
            category: "properties",
            itemId: propId,
            itemType: propType,
            message: `Object property "${propId}" references non-existent range class "${range}"`,
            suggestion:
              "Remove the invalid range reference or create the missing class",
          });
        }
      }
    }

    // Check URI format
    if (!this.isValidURI(property.uri)) {
      issues.push({
        type: "error",
        category: "properties",
        itemId: propId,
        itemType: propType,
        message: `Property "${propId}" has invalid URI format`,
        suggestion: "Ensure the URI follows a valid format",
      });
    }

    return issues;
  }

  private static validateStructure(ontology: Ontology): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Check for empty ontology
    const hasClasses = Object.keys(ontology.classes).length > 0;
    const hasProperties =
      Object.keys(ontology.objectProperties).length > 0 ||
      Object.keys(ontology.datatypeProperties).length > 0;

    if (!hasClasses && !hasProperties) {
      issues.push({
        type: "info",
        category: "structure",
        message: "Ontology is empty",
        suggestion:
          "Add some classes and properties to define your domain model",
      });
    } else if (!hasClasses) {
      issues.push({
        type: "warning",
        category: "structure",
        message: "Ontology has no classes",
        suggestion: "Add classes to define the main concepts in your domain",
      });
    } else if (!hasProperties) {
      issues.push({
        type: "info",
        category: "structure",
        message: "Ontology has no properties",
        suggestion: "Add properties to define relationships between classes",
      });
    }

    // Check for orphaned classes (no relationships)
    if (hasClasses && hasProperties) {
      const referencedClasses = new Set<string>();

      // Collect classes referenced in subclass relationships
      Object.values(ontology.classes).forEach((cls) => {
        if (cls["rdfs:subClassOf"]) {
          referencedClasses.add(cls["rdfs:subClassOf"]);
        }
      });

      // Collect classes referenced in property domains/ranges
      [
        ...Object.values(ontology.objectProperties),
        ...Object.values(ontology.datatypeProperties),
      ].forEach((prop) => {
        if (prop["rdfs:domain"]) referencedClasses.add(prop["rdfs:domain"]);
        if (prop["rdfs:range"]) referencedClasses.add(prop["rdfs:range"]);
      });

      const orphanedClasses = Object.keys(ontology.classes).filter(
        (classId) =>
          !referencedClasses.has(classId) &&
          !ontology.classes[classId]["rdfs:subClassOf"] &&
          !this.hasPropertiesWithDomainOrRange(classId, ontology),
      );

      orphanedClasses.forEach((classId) => {
        issues.push({
          type: "info",
          category: "structure",
          itemId: classId,
          itemType: "class",
          message: `Class "${classId}" is not connected to other classes`,
          suggestion:
            "Consider adding subclass relationships or properties that use this class",
        });
      });
    }

    return issues;
  }

  private static findCircularDependencies(ontology: Ontology): string[][] {
    const cycles: string[][] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const dfs = (classId: string, path: string[]): boolean => {
      if (recursionStack.has(classId)) {
        // Found a cycle - extract it from the path
        const cycleStart = path.indexOf(classId);
        cycles.push([...path.slice(cycleStart), classId]);
        return true;
      }

      if (visited.has(classId)) {
        return false;
      }

      visited.add(classId);
      recursionStack.add(classId);

      const owlClass = ontology.classes[classId];
      const parent = owlClass?.["rdfs:subClassOf"];

      if (parent && ontology.classes[parent]) {
        if (dfs(parent, [...path, classId])) {
          return true;
        }
      }

      recursionStack.delete(classId);
      return false;
    };

    Object.keys(ontology.classes).forEach((classId) => {
      if (!visited.has(classId)) {
        dfs(classId, []);
      }
    });

    return cycles;
  }

  private static hasPropertiesWithDomainOrRange(
    classId: string,
    ontology: Ontology,
  ): boolean {
    const allProperties = [
      ...Object.values(ontology.objectProperties),
      ...Object.values(ontology.datatypeProperties),
    ];
    return allProperties.some(
      (prop) =>
        prop["rdfs:domain"] === classId || prop["rdfs:range"] === classId,
    );
  }

  private static isValidURI(uri: string): boolean {
    try {
      new URL(uri);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Check if a class reference appears to be from an external vocabulary
   * Common patterns:
   * - Well-known class names from standard vocabularies (Seq, Bag, Alt, Thing, etc.)
   * - Different namespace from the referencing class
   */
  private static isExternalClassReference(
    className: string,
    referencingUri: string,
  ): boolean {
    // Common external class names from standard vocabularies
    const standardClasses = [
      "Seq",
      "Bag",
      "Alt",
      "List",
      "Statement",
      "Property",
      "Thing",
      "Class",
      "Ontology",
      "Collection",
      "Container",
    ];

    if (standardClasses.includes(className)) {
      return true;
    }

    // If the class name looks like it's from a different namespace
    // (doesn't match the pattern of the referencing URI)
    // This is a heuristic - in a full implementation, we'd track namespace prefixes
    if (referencingUri && className) {
      try {
        new URL(referencingUri);
        return false;
      } catch {
        return false;
      }
    }

    return false;
  }
}
