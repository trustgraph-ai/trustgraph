"""
Question analyzer for ontology-sensitive query system.
Decomposes user questions into semantic components.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of questions that can be asked."""
    FACTUAL = "factual"          # What is X?
    RETRIEVAL = "retrieval"      # Find all X
    AGGREGATION = "aggregation"  # How many X?
    COMPARISON = "comparison"     # Is X better than Y?
    RELATIONSHIP = "relationship" # How is X related to Y?
    BOOLEAN = "boolean"          # Yes/no questions
    PROCESS = "process"          # How to do X?
    TEMPORAL = "temporal"        # When did X happen?
    SPATIAL = "spatial"          # Where is X?


@dataclass
class QuestionComponents:
    """Components extracted from a question."""
    original_question: str
    question_type: QuestionType
    entities: List[str]
    relationships: List[str]
    constraints: List[str]
    aggregations: List[str]
    expected_answer_type: str
    keywords: List[str]


class QuestionAnalyzer:
    """Analyzes natural language questions to extract semantic components."""

    def __init__(self):
        """Initialize question analyzer."""
        # Question word patterns
        self.question_patterns = {
            QuestionType.FACTUAL: [
                r'^what\s+(?:is|are)',
                r'^who\s+(?:is|are)',
                r'^which\s+',
            ],
            QuestionType.RETRIEVAL: [
                r'^find\s+',
                r'^list\s+',
                r'^show\s+',
                r'^get\s+',
                r'^retrieve\s+',
            ],
            QuestionType.AGGREGATION: [
                r'^how\s+many',
                r'^count\s+',
                r'^what\s+(?:is|are)\s+the\s+(?:number|total|sum)',
            ],
            QuestionType.COMPARISON: [
                r'(?:better|worse|more|less|greater|smaller)\s+than',
                r'compare\s+',
                r'difference\s+between',
            ],
            QuestionType.RELATIONSHIP: [
                r'^how\s+(?:is|are).*related',
                r'relationship\s+between',
                r'connection\s+between',
            ],
            QuestionType.BOOLEAN: [
                r'^(?:is|are|was|were|do|does|did|can|could|will|would|should)',
                r'^has\s+',
                r'^have\s+',
            ],
            QuestionType.PROCESS: [
                r'^how\s+(?:to|do)',
                r'^explain\s+how',
            ],
            QuestionType.TEMPORAL: [
                r'^when\s+',
                r'what\s+time',
                r'what\s+date',
            ],
            QuestionType.SPATIAL: [
                r'^where\s+',
                r'location\s+of',
            ],
        }

        # Aggregation keywords
        self.aggregation_keywords = [
            'count', 'sum', 'total', 'average', 'mean', 'median',
            'maximum', 'minimum', 'max', 'min', 'number of'
        ]

        # Constraint patterns
        self.constraint_patterns = [
            r'(?:with|having|where)\s+(.+?)(?:\s+and|\s+or|$)',
            r'(?:greater|less|more|fewer)\s+than\s+(\d+)',
            r'(?:between|from)\s+(.+?)\s+(?:and|to)\s+(.+)',
            r'(?:before|after|since|until)\s+(.+)',
        ]

    def analyze(self, question: str) -> QuestionComponents:
        """Analyze a question to extract components.

        Args:
            question: Natural language question

        Returns:
            QuestionComponents with extracted information
        """
        # Normalize question
        question_lower = question.lower().strip()

        # Determine question type
        question_type = self._identify_question_type(question_lower)

        # Extract entities
        entities = self._extract_entities(question)

        # Extract relationships
        relationships = self._extract_relationships(question_lower)

        # Extract constraints
        constraints = self._extract_constraints(question_lower)

        # Extract aggregations
        aggregations = self._extract_aggregations(question_lower)

        # Determine expected answer type
        answer_type = self._determine_answer_type(question_type, aggregations)

        # Extract keywords
        keywords = self._extract_keywords(question_lower)

        return QuestionComponents(
            original_question=question,
            question_type=question_type,
            entities=entities,
            relationships=relationships,
            constraints=constraints,
            aggregations=aggregations,
            expected_answer_type=answer_type,
            keywords=keywords
        )

    def _identify_question_type(self, question: str) -> QuestionType:
        """Identify the type of question.

        Args:
            question: Lowercase question text

        Returns:
            QuestionType enum value
        """
        for q_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question):
                    return q_type

        # Default to factual
        return QuestionType.FACTUAL

    def _extract_entities(self, question: str) -> List[str]:
        """Extract potential entities from question.

        Args:
            question: Original question text

        Returns:
            List of entity strings
        """
        entities = []

        # Extract capitalized words/phrases (potential proper nouns)
        # Pattern for consecutive capitalized words
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(pattern, question)
        entities.extend(matches)

        # Extract quoted strings
        quoted = re.findall(r'"([^"]+)"', question)
        entities.extend(quoted)
        quoted = re.findall(r"'([^']+)'", question)
        entities.extend(quoted)

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities

    def _extract_relationships(self, question: str) -> List[str]:
        """Extract relationship indicators from question.

        Args:
            question: Lowercase question text

        Returns:
            List of relationship strings
        """
        relationships = []

        # Common relationship patterns
        rel_patterns = [
            r'(\w+)\s+(?:of|by|from|to|with|for)\s+',
            r'has\s+(\w+)',
            r'belongs?\s+to',
            r'(?:created|written|authored|owned)\s+by',
            r'related\s+to',
            r'connected\s+to',
            r'associated\s+with',
        ]

        for pattern in rel_patterns:
            matches = re.findall(pattern, question)
            relationships.extend(matches)

        # Clean up
        relationships = [r for r in relationships if len(r) > 2]
        return list(set(relationships))

    def _extract_constraints(self, question: str) -> List[str]:
        """Extract constraints from question.

        Args:
            question: Lowercase question text

        Returns:
            List of constraint strings
        """
        constraints = []

        for pattern in self.constraint_patterns:
            matches = re.findall(pattern, question)
            if matches:
                if isinstance(matches[0], tuple):
                    constraints.extend(list(matches[0]))
                else:
                    constraints.extend(matches)

        # Clean up
        constraints = [c.strip() for c in constraints if c and len(c.strip()) > 0]
        return constraints

    def _extract_aggregations(self, question: str) -> List[str]:
        """Extract aggregation operations from question.

        Args:
            question: Lowercase question text

        Returns:
            List of aggregation operations
        """
        aggregations = []

        for keyword in self.aggregation_keywords:
            if keyword in question:
                aggregations.append(keyword)

        return aggregations

    def _determine_answer_type(self, question_type: QuestionType,
                              aggregations: List[str]) -> str:
        """Determine expected answer type.

        Args:
            question_type: Type of question
            aggregations: Aggregation operations found

        Returns:
            Expected answer type string
        """
        if aggregations:
            if any(a in ['count', 'number of', 'total'] for a in aggregations):
                return 'number'
            elif any(a in ['average', 'mean', 'median'] for a in aggregations):
                return 'number'
            elif any(a in ['sum'] for a in aggregations):
                return 'number'

        if question_type == QuestionType.BOOLEAN:
            return 'boolean'
        elif question_type == QuestionType.TEMPORAL:
            return 'datetime'
        elif question_type == QuestionType.SPATIAL:
            return 'location'
        elif question_type == QuestionType.RETRIEVAL:
            return 'list'
        elif question_type == QuestionType.COMPARISON:
            return 'comparison'
        else:
            return 'text'

    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords from question.

        Args:
            question: Lowercase question text

        Returns:
            List of keywords
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'shall', 'what', 'which', 'who',
            'when', 'where', 'why', 'how'
        }

        # Extract words
        words = re.findall(r'\b\w+\b', question)

        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords

    def get_question_segments(self, question: str) -> List[str]:
        """Split question into segments for embedding.

        Args:
            question: Question text

        Returns:
            List of question segments
        """
        segments = []

        # Add full question
        segments.append(question)

        # Split by clauses
        clauses = re.split(r'[,;]', question)
        segments.extend([c.strip() for c in clauses if len(c.strip()) > 3])

        # Extract key phrases
        components = self.analyze(question)
        segments.extend(components.entities)
        segments.extend(components.keywords)

        # Remove duplicates
        return list(dict.fromkeys(segments))