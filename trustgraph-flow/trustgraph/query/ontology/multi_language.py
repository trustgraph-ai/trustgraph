"""
Multi-language support for OntoRAG.
Provides language detection, translation, and multilingual query processing.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    RUSSIAN = "ru"
    DUTCH = "nl"


@dataclass
class LanguageDetectionResult:
    """Language detection result."""
    language: Language
    confidence: float
    detected_text: str
    alternative_languages: List[Tuple[Language, float]] = None


@dataclass
class TranslationResult:
    """Translation result."""
    original_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    confidence: float


class LanguageDetector:
    """Detects language of input text."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize language detector.

        Args:
            config: Detector configuration
        """
        self.config = config or {}
        self.default_language = Language(self.config.get('default_language', 'en'))
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)

        # Try to import language detection libraries
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """Initialize language detection backend."""
        try:
            # Try langdetect first
            import langdetect
            self.detector = 'langdetect'
            logger.info("Using langdetect for language detection")
        except ImportError:
            try:
                # Try textblob as fallback
                from textblob import TextBlob
                self.detector = 'textblob'
                logger.info("Using TextBlob for language detection")
            except ImportError:
                logger.warning("No language detection library available, using rule-based detection")
                self.detector = 'rule_based'

    def detect_language(self, text: str) -> LanguageDetectionResult:
        """Detect language of input text.

        Args:
            text: Text to analyze

        Returns:
            Language detection result
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                language=self.default_language,
                confidence=0.0,
                detected_text=text
            )

        try:
            if self.detector == 'langdetect':
                return self._detect_with_langdetect(text)
            elif self.detector == 'textblob':
                return self._detect_with_textblob(text)
            else:
                return self._detect_with_rules(text)

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return LanguageDetectionResult(
                language=self.default_language,
                confidence=0.0,
                detected_text=text
            )

    def _detect_with_langdetect(self, text: str) -> LanguageDetectionResult:
        """Detect language using langdetect library."""
        import langdetect
        from langdetect.lang_detect_exception import LangDetectException

        try:
            # Get detailed detection results
            probabilities = langdetect.detect_langs(text)

            if not probabilities:
                return LanguageDetectionResult(
                    language=self.default_language,
                    confidence=0.0,
                    detected_text=text
                )

            best_match = probabilities[0]
            detected_lang_code = best_match.lang
            confidence = best_match.prob

            # Map to our Language enum
            try:
                detected_language = Language(detected_lang_code)
            except ValueError:
                # Map common variations
                lang_mapping = {
                    'ca': Language.SPANISH,  # Catalan -> Spanish
                    'eu': Language.SPANISH,  # Basque -> Spanish
                    'gl': Language.SPANISH,  # Galician -> Spanish
                    'zh-cn': Language.CHINESE,
                    'zh-tw': Language.CHINESE,
                }
                detected_language = lang_mapping.get(detected_lang_code, self.default_language)

            # Get alternatives
            alternatives = []
            for lang_prob in probabilities[1:3]:  # Top 3 alternatives
                try:
                    alt_lang = Language(lang_prob.lang)
                    alternatives.append((alt_lang, lang_prob.prob))
                except ValueError:
                    continue

            return LanguageDetectionResult(
                language=detected_language,
                confidence=confidence,
                detected_text=text,
                alternative_languages=alternatives
            )

        except LangDetectException:
            return LanguageDetectionResult(
                language=self.default_language,
                confidence=0.0,
                detected_text=text
            )

    def _detect_with_textblob(self, text: str) -> LanguageDetectionResult:
        """Detect language using TextBlob."""
        from textblob import TextBlob

        try:
            blob = TextBlob(text)
            detected_lang_code = blob.detect_language()

            try:
                detected_language = Language(detected_lang_code)
            except ValueError:
                detected_language = self.default_language

            # TextBlob doesn't provide confidence, so estimate based on text length
            confidence = min(0.8, len(text) / 100.0) if len(text) > 10 else 0.5

            return LanguageDetectionResult(
                language=detected_language,
                confidence=confidence,
                detected_text=text
            )

        except Exception:
            return LanguageDetectionResult(
                language=self.default_language,
                confidence=0.0,
                detected_text=text
            )

    def _detect_with_rules(self, text: str) -> LanguageDetectionResult:
        """Rule-based language detection fallback."""
        text_lower = text.lower()

        # Simple keyword-based detection
        language_keywords = {
            Language.SPANISH: ['qué', 'cuál', 'cuándo', 'dónde', 'cómo', 'por qué', 'cuántos'],
            Language.FRENCH: ['que', 'quel', 'quand', 'où', 'comment', 'pourquoi', 'combien'],
            Language.GERMAN: ['was', 'welche', 'wann', 'wo', 'wie', 'warum', 'wieviele'],
            Language.ITALIAN: ['che', 'quale', 'quando', 'dove', 'come', 'perché', 'quanti'],
            Language.PORTUGUESE: ['que', 'qual', 'quando', 'onde', 'como', 'por que', 'quantos'],
            Language.DUTCH: ['wat', 'welke', 'wanneer', 'waar', 'hoe', 'waarom', 'hoeveel']
        }

        best_match = self.default_language
        best_score = 0

        for language, keywords in language_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > best_score:
                best_score = score
                best_match = language

        confidence = min(0.8, best_score / 3.0) if best_score > 0 else 0.1

        return LanguageDetectionResult(
            language=best_match,
            confidence=confidence,
            detected_text=text
        )


class TextTranslator:
    """Translates text between languages."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize text translator.

        Args:
            config: Translator configuration
        """
        self.config = config or {}
        self.translator = None
        self._init_translator()

    def _init_translator(self):
        """Initialize translation backend."""
        try:
            # Try Google Translate first
            from googletrans import Translator
            self.translator = Translator()
            self.backend = 'googletrans'
            logger.info("Using Google Translate for translation")
        except ImportError:
            try:
                # Try TextBlob as fallback
                from textblob import TextBlob
                self.backend = 'textblob'
                logger.info("Using TextBlob for translation")
            except ImportError:
                logger.warning("No translation library available")
                self.backend = None

    def translate(self,
                 text: str,
                 target_language: Language,
                 source_language: Optional[Language] = None) -> TranslationResult:
        """Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language
            source_language: Source language (auto-detect if None)

        Returns:
            Translation result
        """
        if not text or not text.strip():
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_language or Language.ENGLISH,
                target_language=target_language,
                confidence=0.0
            )

        try:
            if self.backend == 'googletrans':
                return self._translate_with_googletrans(text, target_language, source_language)
            elif self.backend == 'textblob':
                return self._translate_with_textblob(text, target_language, source_language)
            else:
                # No translation available
                return TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=source_language or Language.ENGLISH,
                    target_language=target_language,
                    confidence=0.0
                )

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_language or Language.ENGLISH,
                target_language=target_language,
                confidence=0.0
            )

    def _translate_with_googletrans(self,
                                   text: str,
                                   target_language: Language,
                                   source_language: Optional[Language]) -> TranslationResult:
        """Translate using Google Translate."""
        try:
            src_code = source_language.value if source_language else 'auto'
            dest_code = target_language.value

            result = self.translator.translate(text, src=src_code, dest=dest_code)

            detected_source = Language(result.src) if result.src != 'auto' else Language.ENGLISH
            confidence = 0.9  # Google Translate is generally reliable

            return TranslationResult(
                original_text=text,
                translated_text=result.text,
                source_language=detected_source,
                target_language=target_language,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Google Translate error: {e}")
            raise

    def _translate_with_textblob(self,
                                text: str,
                                target_language: Language,
                                source_language: Optional[Language]) -> TranslationResult:
        """Translate using TextBlob."""
        from textblob import TextBlob

        try:
            blob = TextBlob(text)

            if not source_language:
                # Auto-detect source language
                detected_lang = blob.detect_language()
                try:
                    source_language = Language(detected_lang)
                except ValueError:
                    source_language = Language.ENGLISH

            translated_blob = blob.translate(to=target_language.value)
            translated_text = str(translated_blob)

            # TextBlob confidence estimation
            confidence = 0.7 if len(text) > 10 else 0.5

            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"TextBlob translation error: {e}")
            raise


class MultiLanguageQueryProcessor:
    """Processes queries in multiple languages."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize multi-language query processor.

        Args:
            config: Processor configuration
        """
        self.config = config or {}
        self.language_detector = LanguageDetector(config.get('language_detection', {}))
        self.translator = TextTranslator(config.get('translation', {}))
        self.supported_languages = [Language(lang) for lang in config.get('supported_languages', ['en'])]
        self.primary_language = Language(config.get('primary_language', 'en'))

    async def process_multilingual_query(self, question: str) -> Dict[str, Any]:
        """Process a query in any supported language.

        Args:
            question: Question in any language

        Returns:
            Processing result with language information
        """
        # Step 1: Detect language
        detection_result = self.language_detector.detect_language(question)
        detected_language = detection_result.language

        logger.info(f"Detected language: {detected_language.value} "
                   f"(confidence: {detection_result.confidence:.2f})")

        # Step 2: Translate to primary language if needed
        translated_question = question
        translation_result = None

        if detected_language != self.primary_language:
            if detection_result.confidence >= self.language_detector.confidence_threshold:
                translation_result = self.translator.translate(
                    question, self.primary_language, detected_language
                )
                translated_question = translation_result.translated_text
                logger.info(f"Translated question: {translated_question}")
            else:
                logger.warning(f"Low confidence language detection, processing in {self.primary_language.value}")

        # Step 3: Return processing information
        return {
            'original_question': question,
            'translated_question': translated_question,
            'detected_language': detected_language,
            'detection_confidence': detection_result.confidence,
            'translation_result': translation_result,
            'processing_language': self.primary_language,
            'alternative_languages': detection_result.alternative_languages
        }

    async def translate_answer(self,
                             answer: str,
                             target_language: Language) -> TranslationResult:
        """Translate answer back to target language.

        Args:
            answer: Answer in primary language
            target_language: Target language for answer

        Returns:
            Translation result
        """
        if target_language == self.primary_language:
            # No translation needed
            return TranslationResult(
                original_text=answer,
                translated_text=answer,
                source_language=self.primary_language,
                target_language=target_language,
                confidence=1.0
            )

        return self.translator.translate(answer, target_language, self.primary_language)

    def get_language_specific_ontology_terms(self,
                                           ontology_subset: Dict[str, Any],
                                           language: Language) -> Dict[str, Any]:
        """Get language-specific terms from ontology.

        Args:
            ontology_subset: Ontology subset
            language: Target language

        Returns:
            Language-specific ontology terms
        """
        # Extract language-specific labels and descriptions
        lang_code = language.value
        result = {}

        # Process classes
        if 'classes' in ontology_subset:
            result['classes'] = {}
            for class_id, class_def in ontology_subset['classes'].items():
                lang_labels = []
                if 'labels' in class_def:
                    for label in class_def['labels']:
                        if isinstance(label, dict) and label.get('language') == lang_code:
                            lang_labels.append(label['value'])
                        elif isinstance(label, str):
                            lang_labels.append(label)

                result['classes'][class_id] = {
                    **class_def,
                    'language_labels': lang_labels
                }

        # Process properties
        for prop_type in ['object_properties', 'datatype_properties']:
            if prop_type in ontology_subset:
                result[prop_type] = {}
                for prop_id, prop_def in ontology_subset[prop_type].items():
                    lang_labels = []
                    if 'labels' in prop_def:
                        for label in prop_def['labels']:
                            if isinstance(label, dict) and label.get('language') == lang_code:
                                lang_labels.append(label['value'])
                            elif isinstance(label, str):
                                lang_labels.append(label)

                    result[prop_type][prop_id] = {
                        **prop_def,
                        'language_labels': lang_labels
                    }

        return result

    def is_language_supported(self, language: Language) -> bool:
        """Check if language is supported.

        Args:
            language: Language to check

        Returns:
            True if language is supported
        """
        return language in self.supported_languages

    def get_supported_languages(self) -> List[Language]:
        """Get list of supported languages.

        Returns:
            List of supported languages
        """
        return self.supported_languages.copy()

    def add_language_support(self, language: Language):
        """Add support for a new language.

        Args:
            language: Language to add support for
        """
        if language not in self.supported_languages:
            self.supported_languages.append(language)
            logger.info(f"Added support for language: {language.value}")

    def remove_language_support(self, language: Language):
        """Remove support for a language.

        Args:
            language: Language to remove support for
        """
        if language in self.supported_languages and language != self.primary_language:
            self.supported_languages.remove(language)
            logger.info(f"Removed support for language: {language.value}")
        else:
            logger.warning(f"Cannot remove primary language or unsupported language: {language.value}")


class LanguageSpecificTemplates:
    """Manages language-specific query and answer templates."""

    def __init__(self):
        """Initialize language-specific templates."""
        self.question_templates = {
            Language.ENGLISH: {
                'count': ['how many', 'count of', 'number of'],
                'boolean': ['is', 'are', 'does', 'can', 'will'],
                'retrieval': ['what', 'which', 'who', 'where'],
                'factual': ['tell me about', 'describe', 'explain']
            },
            Language.SPANISH: {
                'count': ['cuántos', 'cuántas', 'número de', 'cantidad de'],
                'boolean': ['es', 'son', 'está', 'están', 'puede', 'pueden'],
                'retrieval': ['qué', 'cuál', 'cuáles', 'quién', 'dónde'],
                'factual': ['dime sobre', 'describe', 'explica']
            },
            Language.FRENCH: {
                'count': ['combien', 'nombre de', 'quantité de'],
                'boolean': ['est', 'sont', 'peut', 'peuvent'],
                'retrieval': ['que', 'quel', 'quelle', 'qui', 'où'],
                'factual': ['dis-moi sur', 'décris', 'explique']
            },
            Language.GERMAN: {
                'count': ['wie viele', 'anzahl der', 'zahl der'],
                'boolean': ['ist', 'sind', 'kann', 'können'],
                'retrieval': ['was', 'welche', 'wer', 'wo'],
                'factual': ['erzähl mir über', 'beschreibe', 'erkläre']
            }
        }

        self.answer_templates = {
            Language.ENGLISH: {
                'count': 'There are {count} {entity}.',
                'boolean_true': 'Yes, {statement}.',
                'boolean_false': 'No, {statement}.',
                'not_found': 'No information found.',
                'error': 'Sorry, I encountered an error.'
            },
            Language.SPANISH: {
                'count': 'Hay {count} {entity}.',
                'boolean_true': 'Sí, {statement}.',
                'boolean_false': 'No, {statement}.',
                'not_found': 'No se encontró información.',
                'error': 'Lo siento, encontré un error.'
            },
            Language.FRENCH: {
                'count': 'Il y a {count} {entity}.',
                'boolean_true': 'Oui, {statement}.',
                'boolean_false': 'Non, {statement}.',
                'not_found': 'Aucune information trouvée.',
                'error': 'Désolé, j\'ai rencontré une erreur.'
            },
            Language.GERMAN: {
                'count': 'Es gibt {count} {entity}.',
                'boolean_true': 'Ja, {statement}.',
                'boolean_false': 'Nein, {statement}.',
                'not_found': 'Keine Informationen gefunden.',
                'error': 'Entschuldigung, ich bin auf einen Fehler gestoßen.'
            }
        }

    def get_question_patterns(self, language: Language) -> Dict[str, List[str]]:
        """Get question patterns for a language.

        Args:
            language: Target language

        Returns:
            Dictionary of question patterns
        """
        return self.question_templates.get(language, self.question_templates[Language.ENGLISH])

    def get_answer_template(self, language: Language, template_type: str) -> str:
        """Get answer template for a language and type.

        Args:
            language: Target language
            template_type: Template type

        Returns:
            Answer template string
        """
        templates = self.answer_templates.get(language, self.answer_templates[Language.ENGLISH])
        return templates.get(template_type, templates.get('error', 'Error'))

    def format_answer(self,
                     language: Language,
                     template_type: str,
                     **kwargs) -> str:
        """Format answer using language-specific template.

        Args:
            language: Target language
            template_type: Template type
            **kwargs: Template variables

        Returns:
            Formatted answer
        """
        template = self.get_answer_template(language, template_type)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return self.get_answer_template(language, 'error')