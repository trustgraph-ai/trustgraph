import React, { useMemo } from "react";
import {
  VStack,
  HStack,
  Text,
  Box,
  Badge,
  Button,
  Alert,
  Progress,
  Card,
  Separator,
} from "@chakra-ui/react";
import {
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  TrendingUp,
  Target,
  Zap,
} from "lucide-react";
import { validateOntology } from "../../utils/skos-validation";
import { Ontology } from "@trustgraph/react-state";
import { ValidationResults } from "./ValidationResults";
import { OntologyQA } from "../../utils/ontology-qa";

interface OntologyValidationTabProps {
  ontology: Ontology;
  onOntologyChange?: (ontology: Ontology) => void;
}

interface ValidationIssue {
  type: "error" | "warning" | "info";
  code: string;
  message: string;
  conceptId?: string;
  autoFixable?: boolean;
  suggestion?: string;
}

interface QualityMetrics {
  completeness: number;
  consistency: number;
  coverage: number;
  compliance: number;
  overall: number;
}

export const OntologyValidationTab: React.FC<OntologyValidationTabProps> = ({
  ontology,
  onOntologyChange,
}) => {
  // Run validation
  const validation = useMemo(() => validateOntology(ontology), [ontology]);

  // Calculate quality metrics
  const qualityMetrics = useMemo((): QualityMetrics => {
    const concepts = Object.values(ontology.concepts);
    const totalConcepts = concepts.length;

    if (totalConcepts === 0) {
      return {
        completeness: 0,
        consistency: 0,
        coverage: 0,
        compliance: 0,
        overall: 0,
      };
    }

    // Completeness: How many concepts have all recommended fields
    const completeConceptsCount = concepts.filter(
      (c) =>
        c.prefLabel &&
        c.definition &&
        (c.broader || ontology.scheme.hasTopConcept.includes(c.id)),
    ).length;
    const completeness = (completeConceptsCount / totalConcepts) * 100;

    // Consistency: Relationship consistency
    let consistentRelationships = 0;
    let totalRelationships = 0;

    concepts.forEach((concept) => {
      if (concept.broader && ontology.concepts[concept.broader]) {
        totalRelationships++;
        const broaderConcept = ontology.concepts[concept.broader];
        if (broaderConcept.narrower?.includes(concept.id)) {
          consistentRelationships++;
        }
      }

      if (concept.narrower) {
        concept.narrower.forEach((narrowerId) => {
          if (ontology.concepts[narrowerId]) {
            totalRelationships++;
            const narrowerConcept = ontology.concepts[narrowerId];
            if (narrowerConcept.broader === concept.id) {
              consistentRelationships++;
            }
          }
        });
      }

      if (concept.related) {
        concept.related.forEach((relatedId) => {
          if (ontology.concepts[relatedId]) {
            totalRelationships++;
            const relatedConcept = ontology.concepts[relatedId];
            if (relatedConcept.related?.includes(concept.id)) {
              consistentRelationships++;
            }
          }
        });
      }
    });

    const consistency =
      totalRelationships > 0
        ? (consistentRelationships / totalRelationships) * 100
        : 100;

    // Coverage: How well the ontology covers its domain (based on hierarchy depth and breadth)
    const topConceptsCount = ontology.scheme.hasTopConcept.length;
    const maxDepth = calculateMaxDepth(ontology);
    const avgBranchingFactor =
      totalConcepts > 1 ? totalConcepts / Math.max(topConceptsCount, 1) : 0;

    // Ideal coverage considers both depth (3-6 levels) and branching (2-8 children per concept)
    const depthScore = Math.min(maxDepth / 4, 1) * 100; // Ideal depth ~4
    const branchingScore = Math.min(avgBranchingFactor / 5, 1) * 100; // Ideal branching ~5
    const coverage = (depthScore + branchingScore) / 2;

    // Compliance: SKOS compliance (inverse of validation errors)
    const errorWeight = validation.errors.length * 10;
    const warningWeight = validation.warnings.length * 5;
    const totalIssueWeight = errorWeight + warningWeight;
    const compliance = Math.max(0, 100 - totalIssueWeight);

    // Overall quality score
    const overall = (completeness + consistency + coverage + compliance) / 4;

    return { completeness, consistency, coverage, compliance, overall };
  }, [ontology, validation]);

  // Generate quality suggestions using OntologyQA
  const qualitySuggestions = useMemo((): ValidationIssue[] => {
    const qaSuggestions = OntologyQA.generateSuggestions(ontology);
    const concepts = Object.values(ontology.concepts);

    // Convert QA suggestions to validation issues
    const suggestions: ValidationIssue[] = qaSuggestions.map((qa) => ({
      type: qa.type === "manual" ? "info" : "warning",
      code: qa.field ? `QA_${qa.field.toUpperCase()}` : "QA_IMPROVEMENT",
      message: qa.description,
      conceptId: qa.conceptId,
      suggestion: qa.description,
      autoFixable: qa.type === "auto",
    }));

    // Add auto-fixable consistency suggestions
    if (qualityMetrics.consistency < 90) {
      suggestions.push({
        type: "warning",
        code: "QA_RELATIONSHIP_INCONSISTENCIES",
        message: "Some relationships are not properly reciprocated",
        suggestion:
          "Review broader/narrower and related relationships for consistency",
        autoFixable: true,
      });
    }

    // Add auto-fixable orphaned concepts suggestion for small ontologies
    const orphanedConcepts = concepts.filter(
      (c) => !c.broader && !ontology.scheme.hasTopConcept.includes(c.id),
    ).length;

    if (
      orphanedConcepts > 0 &&
      orphanedConcepts <= 3 &&
      concepts.length <= 20
    ) {
      suggestions.push({
        type: "warning",
        code: "QA_ORPHANED_CONCEPTS_FIXABLE",
        message: `${orphanedConcepts} concept${orphanedConcepts !== 1 ? "s" : ""} can be promoted to top concepts`,
        suggestion:
          "Automatically promote orphaned concepts to top-level concepts",
        autoFixable: true,
      });
    }

    return suggestions;
  }, [ontology, qualityMetrics]);

  const allIssues = [
    ...validation.errors.map((e) => ({ ...e, autoFixable: false })),
    ...validation.warnings.map((w) => ({ ...w, autoFixable: false })),
    ...validation.info.map((i) => ({ ...i, autoFixable: false })),
    ...qualitySuggestions,
  ];

  const handleAutoFix = (issue: ValidationIssue) => {
    if (!onOntologyChange || !issue.autoFixable) return;

    const qaResult = OntologyQA.autoFix(ontology);
    onOntologyChange(qaResult.ontology);
  };

  const handleFixAll = () => {
    if (!onOntologyChange) return;

    const qaResult = OntologyQA.autoFix(ontology);
    onOntologyChange(qaResult.ontology);
  };

  return (
    <VStack gap={6} align="stretch">
      {/* Quality Overview */}
      <Card.Root>
        <Card.Header>
          <HStack justify="space-between">
            <HStack>
              <Target size={20} />
              <Text fontSize="lg" fontWeight="bold">
                Ontology Quality Score
              </Text>
            </HStack>
            <Badge
              size="lg"
              colorPalette={
                qualityMetrics.overall >= 80
                  ? "green"
                  : qualityMetrics.overall >= 60
                    ? "orange"
                    : "red"
              }
            >
              {Math.round(qualityMetrics.overall)}%
            </Badge>
          </HStack>
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            {/* Overall Progress */}
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" fontWeight="medium">
                  Overall Quality
                </Text>
                <Text fontSize="sm" color="fg.muted">
                  {Math.round(qualityMetrics.overall)}%
                </Text>
              </HStack>
              <Progress.Root
                value={qualityMetrics.overall}
                colorPalette={
                  qualityMetrics.overall >= 80
                    ? "green"
                    : qualityMetrics.overall >= 60
                      ? "orange"
                      : "red"
                }
              >
                <Progress.Track>
                  <Progress.Range />
                </Progress.Track>
              </Progress.Root>
            </Box>

            {/* Individual Metrics */}
            <VStack gap={2} align="stretch">
              {[
                {
                  label: "Completeness",
                  value: qualityMetrics.completeness,
                  description: "Required and recommended fields",
                },
                {
                  label: "Consistency",
                  value: qualityMetrics.consistency,
                  description: "Relationship coherence",
                },
                {
                  label: "Coverage",
                  value: qualityMetrics.coverage,
                  description: "Hierarchy depth and breadth",
                },
                {
                  label: "SKOS Compliance",
                  value: qualityMetrics.compliance,
                  description: "Standards adherence",
                },
              ].map(({ label, value, description }) => (
                <HStack key={label} justify="space-between">
                  <VStack align="start" gap={0} flex={1}>
                    <Text fontSize="sm" fontWeight="medium">
                      {label}
                    </Text>
                    <Text fontSize="xs" color="fg.muted">
                      {description}
                    </Text>
                  </VStack>
                  <HStack>
                    <Progress.Root
                      value={value}
                      size="sm"
                      width="60px"
                      colorPalette={
                        value >= 80 ? "green" : value >= 60 ? "orange" : "red"
                      }
                    >
                      <Progress.Track>
                        <Progress.Range />
                      </Progress.Track>
                    </Progress.Root>
                    <Text
                      fontSize="xs"
                      color="fg.muted"
                      minW="35px"
                      textAlign="right"
                    >
                      {Math.round(value)}%
                    </Text>
                  </HStack>
                </HStack>
              ))}
            </VStack>
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Validation Summary */}
      <Card.Root>
        <Card.Header>
          <HStack justify="space-between">
            <HStack>
              <CheckCircle size={20} />
              <Text fontSize="lg" fontWeight="bold">
                Validation Summary
              </Text>
            </HStack>
            <HStack>
              {qualitySuggestions.some((s) => s.autoFixable) && (
                <Button
                  size="sm"
                  colorPalette="blue"
                  onClick={handleFixAll}
                  disabled={!onOntologyChange}
                >
                  <Zap size={14} />
                  Fix All
                </Button>
              )}
              <Button size="sm" variant="outline">
                <RefreshCw size={14} />
                Revalidate
              </Button>
            </HStack>
          </HStack>
        </Card.Header>
        <Card.Body>
          <HStack gap={6}>
            <VStack>
              <HStack>
                <XCircle size={16} color="red" />
                <Badge colorPalette="red" variant="solid">
                  {validation.errors.length}
                </Badge>
              </HStack>
              <Text fontSize="xs" color="fg.muted">
                Errors
              </Text>
            </VStack>
            <VStack>
              <HStack>
                <AlertTriangle size={16} color="orange" />
                <Badge colorPalette="orange" variant="solid">
                  {validation.warnings.length}
                </Badge>
              </HStack>
              <Text fontSize="xs" color="fg.muted">
                Warnings
              </Text>
            </VStack>
            <VStack>
              <HStack>
                <Info size={16} color="blue" />
                <Badge colorPalette="blue" variant="solid">
                  {validation.info.length}
                </Badge>
              </HStack>
              <Text fontSize="xs" color="fg.muted">
                Info
              </Text>
            </VStack>
            <VStack>
              <HStack>
                <TrendingUp size={16} color="purple" />
                <Badge colorPalette="purple" variant="solid">
                  {qualitySuggestions.length}
                </Badge>
              </HStack>
              <Text fontSize="xs" color="fg.muted">
                Suggestions
              </Text>
            </VStack>
          </HStack>
        </Card.Body>
      </Card.Root>

      <Separator />

      {/* Quick Actions */}
      {qualitySuggestions.some((s) => s.autoFixable) && (
        <Card.Root>
          <Card.Header>
            <HStack>
              <Zap size={20} />
              <Text fontSize="lg" fontWeight="bold">
                Quick Fixes
              </Text>
            </HStack>
          </Card.Header>
          <Card.Body>
            <VStack gap={3} align="stretch">
              {qualitySuggestions
                .filter((s) => s.autoFixable)
                .map((issue, index) => (
                  <Alert.Root key={index} status="info">
                    <Alert.Content>
                      <HStack justify="space-between" width="full">
                        <VStack align="start" gap={1} flex={1}>
                          <Text fontSize="sm" fontWeight="medium">
                            {issue.message}
                          </Text>
                          {issue.suggestion && (
                            <Text fontSize="xs" color="fg.muted">
                              {issue.suggestion}
                            </Text>
                          )}
                        </VStack>
                        <Button
                          size="sm"
                          colorPalette="blue"
                          variant="solid"
                          onClick={() => handleAutoFix(issue)}
                        >
                          Fix Now
                        </Button>
                      </HStack>
                    </Alert.Content>
                  </Alert.Root>
                ))}
            </VStack>
          </Card.Body>
        </Card.Root>
      )}

      {/* Detailed Issues */}
      <Card.Root>
        <Card.Header>
          <Text fontSize="lg" fontWeight="bold">
            Detailed Issues & Suggestions
          </Text>
        </Card.Header>
        <Card.Body>
          {allIssues.length > 0 ? (
            <ValidationResults
              validation={{
                isValid: validation.isValid,
                errors: allIssues.filter((i) => i.type === "error"),
                warnings: allIssues.filter((i) => i.type === "warning"),
                info: allIssues.filter((i) => i.type === "info"),
              }}
              maxErrors={10}
              maxWarnings={10}
              maxInfo={10}
            />
          ) : (
            <Alert.Root status="success">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>
                  No issues found. Your ontology looks great!
                </Alert.Description>
              </Alert.Content>
            </Alert.Root>
          )}
        </Card.Body>
      </Card.Root>
    </VStack>
  );
};

// Helper function to calculate maximum hierarchy depth
function calculateMaxDepth(ontology: Ontology): number {
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
