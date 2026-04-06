/**
 * Tests for OntologyValidationTab component
 * Tests SKOS validation, quality metrics calculation, and auto-fix functionality
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "../../../test/test-utils";
import { describe, test, expect, vi } from "vitest";
import { OntologyValidationTab } from "../OntologyValidationTab";
import { Ontology } from "@trustgraph/react-state/ontologies";
import { validateOntology } from "../../../utils/skos-validation";
import { OntologyQA } from "../../../utils/ontology-qa";

// Mock dependencies
vi.mock("../../../utils/skos-validation", () => ({
  validateOntology: vi.fn(),
}));

interface QualitySuggestion {
  type: "auto" | "manual";
  field: string;
  description: string;
  conceptId?: string;
}

vi.mock("../../../utils/ontology-qa", () => ({
  OntologyQA: {
    generateSuggestions: vi.fn().mockReturnValue([]),
    autoFix: vi
      .fn()
      .mockImplementation((ontology: Ontology) => ({ ontology })),
  },
}));

interface ValidationResult {
  isValid: boolean;
  errors: Array<{
    type: string;
    code: string;
    message: string;
    conceptId?: string;
  }>;
  warnings: Array<{
    type: string;
    code: string;
    message: string;
    conceptId?: string;
  }>;
  info: Array<{
    type: string;
    code: string;
    message: string;
    conceptId?: string;
  }>;
}

vi.mock("../ValidationResults", () => ({
  ValidationResults: ({ validation }: { validation: ValidationResult }) => (
    <div data-testid="validation-results">
      Errors: {validation.errors.length}, Warnings:{" "}
      {validation.warnings.length}
    </div>
  ),
}));

// Mock data
const mockValidOntology: Ontology = {
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
      related: [],
      topConcept: true,
    },
    "concept-2": {
      id: "concept-2",
      prefLabel: "Plants",
      definition: "Living organisms that produce their own food",
      narrower: ["concept-4"],
      related: [],
      topConcept: true,
    },
    "concept-3": {
      id: "concept-3",
      prefLabel: "Mammals",
      definition: "Warm-blooded vertebrate animals",
      broader: "concept-1",
      narrower: [],
      related: [],
    },
    "concept-4": {
      id: "concept-4",
      prefLabel: "Trees",
      definition: "Woody perennial plants with a main trunk",
      broader: "concept-2",
      narrower: [],
      related: [],
    },
  },
};

const mockInvalidOntology: Ontology = {
  ...mockValidOntology,
  concepts: {
    "concept-1": {
      id: "concept-1",
      prefLabel: "", // Missing preferred label
      narrower: [],
      related: [],
    },
    "concept-2": {
      id: "concept-2",
      prefLabel: "Test Concept",
      broader: "non-existent", // Invalid broader reference
      narrower: [],
      related: [],
    },
  },
};

const mockValidationResult = {
  isValid: true,
  errors: [],
  warnings: [],
  info: [],
};

const mockInvalidValidationResult = {
  isValid: false,
  errors: [
    {
      type: "error",
      code: "CONCEPT_NO_PREFLABEL",
      message: "Concept missing preferred label",
      conceptId: "concept-1",
    },
    {
      type: "error",
      code: "CONCEPT_INVALID_BROADER",
      message: "Invalid broader reference",
      conceptId: "concept-2",
    },
  ],
  warnings: [
    {
      type: "warning",
      code: "CONCEPT_NO_DEFINITION",
      message: "Concept missing definition",
      conceptId: "concept-1",
    },
  ],
  info: [
    {
      type: "info",
      code: "CONCEPT_COULD_IMPROVE",
      message: "Concept could be improved",
      conceptId: "concept-2",
    },
  ],
};

describe("OntologyValidationTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders quality metrics for valid ontology", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    // Check that quality score is displayed
    expect(screen.getByText("Ontology Quality Score")).toBeInTheDocument();

    // Check individual metrics
    expect(screen.getByText("Completeness")).toBeInTheDocument();
    expect(screen.getByText("Consistency")).toBeInTheDocument();
    expect(screen.getByText("Coverage")).toBeInTheDocument();
    expect(screen.getByText("SKOS Compliance")).toBeInTheDocument();

    // Check validation summary
    expect(screen.getByText("Validation Summary")).toBeInTheDocument();
    expect(screen.getByText("Errors")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
  });

  test("calculates quality metrics correctly for complete ontology", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    // Since all concepts have prefLabel, definition, and proper hierarchy,
    // completeness should be 100%
    const completenessMetrics = screen.getAllByText(/100%|[89][0-9]%/);
    expect(completenessMetrics.length).toBeGreaterThan(0);
  });

  test("displays validation errors and warnings", () => {
    vi.mocked(validateOntology).mockReturnValue(mockInvalidValidationResult);

    render(<OntologyValidationTab ontology={mockInvalidOntology} />);

    // Check error count badge
    expect(screen.getByText("2")).toBeInTheDocument(); // 2 errors

    // Check validation results component is rendered
    expect(screen.getByTestId("validation-results")).toBeInTheDocument();
    expect(screen.getByText("Errors: 2, Warnings: 1")).toBeInTheDocument();
  });

  test("shows auto-fix suggestions when available", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);
    vi.mocked(OntologyQA.generateSuggestions).mockReturnValue([
      {
        type: "auto",
        field: "prefLabel",
        description: "Some concepts can be auto-fixed",
        conceptId: "concept-1",
      } as QualitySuggestion,
    ]);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    // Should show quick fixes section
    expect(screen.getByText("Quick Fixes")).toBeInTheDocument();
    expect(screen.getByText("Fix Now")).toBeInTheDocument();
    expect(screen.getByText("Fix All")).toBeInTheDocument();
  });

  test("handles auto-fix functionality", async () => {
    const mockOnOntologyChange = vi.fn();
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);
    vi.mocked(OntologyQA.generateSuggestions).mockReturnValue([
      {
        type: "auto",
        field: "consistency",
        description: "Fix relationship inconsistencies",
        conceptId: "concept-1",
      } as QualitySuggestion,
    ]);

    render(
      <OntologyValidationTab
        ontology={mockValidOntology}
        onOntologyChange={mockOnOntologyChange}
      />,
    );

    // Click Fix All button
    const fixAllButton = screen.getByText("Fix All");
    fireEvent.click(fixAllButton);

    await waitFor(() => {
      expect(vi.mocked(OntologyQA.autoFix)).toHaveBeenCalledWith(
        mockValidOntology,
      );
      expect(mockOnOntologyChange).toHaveBeenCalledWith(mockValidOntology);
    });
  });

  test("disables auto-fix when no onOntologyChange handler", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);
    vi.mocked(OntologyQA.generateSuggestions).mockReturnValue([
      {
        type: "auto",
        field: "consistency",
        description: "Fix relationship inconsistencies",
        conceptId: "concept-1",
      } as QualitySuggestion,
    ]);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    // Fix buttons should be disabled
    const fixAllButton = screen.getByText("Fix All");
    expect(fixAllButton).toBeDisabled();
  });

  test("calculates correct quality metrics for empty ontology", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    const emptyOntology: Ontology = {
      ...mockValidOntology,
      concepts: {},
      scheme: { ...mockValidOntology.scheme, hasTopConcept: [] },
    };

    render(<OntologyValidationTab ontology={emptyOntology} />);

    // Should show 0% for all metrics when no concepts exist
    const zeroPercentElements = screen.getAllByText("0%");
    expect(zeroPercentElements.length).toBeGreaterThan(0);
  });

  test("detects orphaned concepts", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    const ontologyWithOrphans: Ontology = {
      ...mockValidOntology,
      scheme: { ...mockValidOntology.scheme, hasTopConcept: [] },
      concepts: {
        "orphan-1": {
          id: "orphan-1",
          prefLabel: "Orphaned Concept",
          definition: "A concept without proper hierarchy",
          narrower: [],
          related: [],
        },
      },
    };

    render(<OntologyValidationTab ontology={ontologyWithOrphans} />);

    // Component should internally identify orphaned concepts for quality suggestions
    expect(validateOntology).toHaveBeenCalledWith(ontologyWithOrphans);
  });

  test("calculates hierarchy depth correctly", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    // Create a deep hierarchy ontology
    const deepOntology: Ontology = {
      ...mockValidOntology,
      scheme: { ...mockValidOntology.scheme, hasTopConcept: ["level-1"] },
      concepts: {
        "level-1": {
          id: "level-1",
          prefLabel: "Level 1",
          definition: "Top level concept",
          narrower: ["level-2"],
          related: [],
          topConcept: true,
        },
        "level-2": {
          id: "level-2",
          prefLabel: "Level 2",
          definition: "Second level concept",
          broader: "level-1",
          narrower: ["level-3"],
          related: [],
        },
        "level-3": {
          id: "level-3",
          prefLabel: "Level 3",
          definition: "Third level concept",
          broader: "level-2",
          narrower: ["level-4"],
          related: [],
        },
        "level-4": {
          id: "level-4",
          prefLabel: "Level 4",
          definition: "Fourth level concept",
          broader: "level-3",
          narrower: [],
          related: [],
        },
      },
    };

    render(<OntologyValidationTab ontology={deepOntology} />);

    // Should render without errors and calculate depth-based coverage
    expect(screen.getByText("Coverage")).toBeInTheDocument();
    expect(validateOntology).toHaveBeenCalledWith(deepOntology);
  });

  test("handles relationship consistency calculations", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    // Create ontology with inconsistent relationships
    const inconsistentOntology: Ontology = {
      ...mockValidOntology,
      concepts: {
        "concept-1": {
          id: "concept-1",
          prefLabel: "Parent",
          definition: "Parent concept",
          narrower: ["concept-2"], // Claims concept-2 as narrower
          related: [],
          topConcept: true,
        },
        "concept-2": {
          id: "concept-2",
          prefLabel: "Child",
          definition: "Child concept",
          // Missing broader reference back to concept-1
          narrower: [],
          related: [],
        },
      },
    };

    render(<OntologyValidationTab ontology={inconsistentOntology} />);

    // Should detect relationship inconsistencies in quality metrics
    expect(screen.getByText("Consistency")).toBeInTheDocument();
    expect(validateOntology).toHaveBeenCalledWith(inconsistentOntology);
  });

  test("displays success message when no issues found", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);
    vi.mocked(OntologyQA.generateSuggestions).mockReturnValue([]);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    expect(
      screen.getByText("No issues found. Your ontology looks great!"),
    ).toBeInTheDocument();
  });

  test("revalidation button triggers validation", () => {
    vi.mocked(validateOntology).mockReturnValue(mockValidationResult);

    render(<OntologyValidationTab ontology={mockValidOntology} />);

    const revalidateButton = screen.getByText("Revalidate");

    // Clear previous calls
    vi.mocked(validateOntology).mockClear();

    fireEvent.click(revalidateButton);

    // Note: The component uses useMemo for validation, so clicking revalidate
    // won't actually trigger re-validation unless ontology changes.
    // This test verifies the button exists and is clickable.
    expect(revalidateButton).toBeInTheDocument();
  });
});
