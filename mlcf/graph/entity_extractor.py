"""
Entity Extractor - Extracts entities from text using NLP.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import re
from loguru import logger

try:
    import spacy
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    logger.warning(
        "spacy not installed. "
        "Install with: pip install spacy && python -m spacy download en_core_web_sm"
    )
    SPACY_AVAILABLE = False


@dataclass
class Entity:
    """Extracted entity."""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = 1.0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "properties": self.properties
        }


class EntityExtractor:
    """
    Entity extraction using NLP.
    
    Extracts named entities from text including:
    - PERSON: People, including fictional
    - ORGANIZATION: Companies, agencies, institutions
    - GPE: Geopolitical entities (countries, cities)
    - PRODUCT: Objects, vehicles, foods, etc.
    - EVENT: Named events
    - WORK_OF_ART: Titles of books, songs, etc.
    - LAW: Named documents made into laws
    - LANGUAGE: Any named language
    - DATE: Absolute or relative dates
    - TIME: Times smaller than a day
    - MONEY: Monetary values
    - QUANTITY: Measurements
    """
    
    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.5
    ):
        """
        Initialize entity extractor.
        
        Args:
            model_name: Spacy model name
            entity_types: Entity types to extract (None = all)
            min_confidence: Minimum confidence threshold
        """
        if not SPACY_AVAILABLE:
            raise ImportError(
                "spacy required. Install with: pip install spacy && "
                "python -m spacy download en_core_web_sm"
            )
        
        self.model_name = model_name
        self.entity_types = entity_types
        self.min_confidence = min_confidence
        
        # Load spacy model
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"EntityExtractor initialized with model: {model_name}")
        except OSError:
            logger.error(
                f"Model '{model_name}' not found. "
                f"Download with: python -m spacy download {model_name}"
            )
            raise
        
        # Entity type mapping (spacy -> graph)
        self.type_mapping = {
            "PERSON": "Person",
            "ORG": "Organization",
            "GPE": "Location",
            "LOC": "Location",
            "PRODUCT": "Product",
            "EVENT": "Event",
            "WORK_OF_ART": "WorkOfArt",
            "LAW": "Law",
            "LANGUAGE": "Language",
            "DATE": "Date",
            "TIME": "Time",
            "MONEY": "Money",
            "QUANTITY": "Quantity",
            "NORP": "Group",  # Nationalities, religious groups
            "FAC": "Facility",  # Buildings, airports, etc.
        }
    
    def extract(
        self,
        text: str,
        merge_overlapping: bool = True
    ) -> List[Entity]:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            merge_overlapping: Merge overlapping entities
            
        Returns:
            List of extracted entities
        """
        if not text or not text.strip():
            return []
        
        # Process text
        doc = self.nlp(text)
        
        # Extract entities
        entities = []
        
        for ent in doc.ents:
            # Filter by type if specified
            if self.entity_types and ent.label_ not in self.entity_types:
                continue
            
            # Map entity type
            entity_type = self.type_mapping.get(ent.label_, "Entity")
            
            # Create entity
            entity = Entity(
                text=ent.text,
                entity_type=entity_type,
                start=ent.start_char,
                end=ent.end_char,
                confidence=1.0,  # Spacy doesn't provide confidence
                properties={
                    "label": ent.label_,
                    "lemma": ent.lemma_
                }
            )
            
            entities.append(entity)
        
        # Add custom patterns (e.g., email, URL)
        entities.extend(self._extract_patterns(text))
        
        # Merge overlapping if requested
        if merge_overlapping:
            entities = self._merge_overlapping(entities)
        
        # Filter by confidence
        entities = [
            e for e in entities
            if e.confidence >= self.min_confidence
        ]
        
        logger.debug(f"Extracted {len(entities)} entities from text")
        return entities
    
    def extract_batch(
        self,
        texts: List[str]
    ) -> List[List[Entity]]:
        """
        Extract entities from multiple texts.
        
        Args:
            texts: List of texts
            
        Returns:
            List of entity lists
        """
        # Process in batch for efficiency
        docs = list(self.nlp.pipe(texts))
        
        results = []
        for doc in docs:
            # Extract entities from each doc
            entities = []
            for ent in doc.ents:
                if self.entity_types and ent.label_ not in self.entity_types:
                    continue
                
                entity_type = self.type_mapping.get(ent.label_, "Entity")
                
                entity = Entity(
                    text=ent.text,
                    entity_type=entity_type,
                    start=ent.start_char,
                    end=ent.end_char,
                    properties={"label": ent.label_}
                )
                
                entities.append(entity)
            
            results.append(entities)
        
        return results
    
    def _extract_patterns(self, text: str) -> List[Entity]:
        """
        Extract entities using regex patterns.
        
        Args:
            text: Input text
            
        Returns:
            List of pattern-based entities
        """
        entities = []
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type="Email",
                start=match.start(),
                end=match.end(),
                confidence=0.9,
                properties={"pattern": "email"}
            ))
        
        # URL pattern
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        for match in re.finditer(url_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type="URL",
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                properties={"pattern": "url"}
            ))
        
        # Phone number pattern (simple)
        phone_pattern = r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b'
        for match in re.finditer(phone_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type="Phone",
                start=match.start(),
                end=match.end(),
                confidence=0.8,
                properties={"pattern": "phone"}
            ))
        
        return entities
    
    def _merge_overlapping(self, entities: List[Entity]) -> List[Entity]:
        """
        Merge overlapping entities.
        
        Args:
            entities: List of entities
            
        Returns:
            Merged entities
        """
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: (e.start, -e.end))
        
        merged = [sorted_entities[0]]
        
        for entity in sorted_entities[1:]:
            last = merged[-1]
            
            # Check for overlap
            if entity.start < last.end:
                # Keep entity with higher confidence
                if entity.confidence > last.confidence:
                    merged[-1] = entity
            else:
                merged.append(entity)
        
        return merged
    
    def extract_with_context(
        self,
        text: str,
        context_window: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Extract entities with surrounding context.
        
        Args:
            text: Input text
            context_window: Characters before/after entity
            
        Returns:
            Entities with context
        """
        entities = self.extract(text)
        
        results = []
        for entity in entities:
            # Get context
            context_start = max(0, entity.start - context_window)
            context_end = min(len(text), entity.end + context_window)
            
            context = text[context_start:context_end]
            
            results.append({
                **entity.to_dict(),
                "context": context,
                "context_start": context_start,
                "context_end": context_end
            })
        
        return results
    
    def get_entity_types(self) -> List[str]:
        """
        Get list of supported entity types.
        
        Returns:
            List of entity type labels
        """
        return list(self.type_mapping.keys())
    
    def __repr__(self) -> str:
        """String representation."""
        return f"EntityExtractor(model={self.model_name}, types={len(self.entity_types or [])})"