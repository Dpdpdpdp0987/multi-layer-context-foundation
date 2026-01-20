"""
Relationship Mapper - Identifies and extracts relationships between entities.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from loguru import logger

try:
    import spacy
    from spacy.tokens import Doc, Token
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from mlcf.graph.entity_extractor import Entity


@dataclass
class Relationship:
    """Extracted relationship."""
    source: Entity
    target: Entity
    relationship_type: str
    confidence: float = 1.0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "type": self.relationship_type,
            "confidence": self.confidence,
            "properties": self.properties
        }


class RelationshipMapper:
    """
    Relationship extraction using dependency parsing.
    
    Extracts relationships between entities based on:
    - Dependency trees
    - Pattern matching
    - Co-occurrence
    """
    
    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        min_confidence: float = 0.5,
        use_patterns: bool = True
    ):
        """
        Initialize relationship mapper.
        
        Args:
            model_name: Spacy model name
            min_confidence: Minimum confidence threshold
            use_patterns: Use pattern-based extraction
        """
        if not SPACY_AVAILABLE:
            raise ImportError(
                "spacy required. Install with: pip install spacy"
            )
        
        self.model_name = model_name
        self.min_confidence = min_confidence
        self.use_patterns = use_patterns
        
        # Load spacy model
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"RelationshipMapper initialized with model: {model_name}")
        except OSError:
            logger.error(f"Model '{model_name}' not found")
            raise
        
        # Relationship patterns
        self._init_patterns()
    
    def _init_patterns(self):
        """
        Initialize relationship extraction patterns.
        """
        # Verb-based patterns
        self.verb_patterns = {
            "work": "WORKS_FOR",
            "employ": "EMPLOYS",
            "manage": "MANAGES",
            "lead": "LEADS",
            "own": "OWNS",
            "create": "CREATED",
            "develop": "DEVELOPED",
            "build": "BUILT",
            "found": "FOUNDED",
            "located": "LOCATED_IN",
            "born": "BORN_IN",
            "live": "LIVES_IN",
            "study": "STUDIED_AT",
            "collaborate": "COLLABORATES_WITH",
            "partner": "PARTNERS_WITH",
            "acquire": "ACQUIRED",
            "invest": "INVESTS_IN",
            "use": "USES",
            "prefer": "PREFERS",
            "like": "LIKES",
        }
        
        # Preposition-based patterns
        self.prep_patterns = {
            "of": "BELONGS_TO",
            "in": "LOCATED_IN",
            "at": "AT",
            "with": "ASSOCIATED_WITH",
            "for": "FOR",
            "by": "CREATED_BY",
            "from": "FROM",
            "to": "TO",
        }
    
    def extract(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Relationship]:
        """
        Extract relationships from text.
        
        Args:
            text: Input text
            entities: Extracted entities
            
        Returns:
            List of relationships
        """
        if not text or not entities:
            return []
        
        # Process text
        doc = self.nlp(text)
        
        # Extract relationships
        relationships = []
        
        # Dependency-based extraction
        relationships.extend(
            self._extract_dependency_based(doc, entities)
        )
        
        # Pattern-based extraction
        if self.use_patterns:
            relationships.extend(
                self._extract_pattern_based(doc, entities)
            )
        
        # Co-occurrence based
        relationships.extend(
            self._extract_cooccurrence(doc, entities)
        )
        
        # Filter by confidence
        relationships = [
            r for r in relationships
            if r.confidence >= self.min_confidence
        ]
        
        # Deduplicate
        relationships = self._deduplicate(relationships)
        
        logger.debug(f"Extracted {len(relationships)} relationships")
        return relationships
    
    def _extract_dependency_based(
        self,
        doc: Doc,
        entities: List[Entity]
    ) -> List[Relationship]:
        """
        Extract relationships using dependency parsing.
        
        Args:
            doc: Spacy Doc
            entities: Extracted entities
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Map entities to their tokens
        entity_map = {}
        for entity in entities:
            for token in doc:
                if token.idx >= entity.start and token.idx < entity.end:
                    entity_map[token.i] = entity
        
        # Find relationships through verbs
        for token in doc:
            if token.pos_ == "VERB":
                # Find subject and object
                subject = None
                obj = None
                
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        if child.i in entity_map:
                            subject = entity_map[child.i]
                    elif child.dep_ in ["dobj", "pobj", "attr"]:
                        if child.i in entity_map:
                            obj = entity_map[child.i]
                
                # Create relationship if both found
                if subject and obj and subject != obj:
                    rel_type = self.verb_patterns.get(
                        token.lemma_.lower(),
                        "RELATED_TO"
                    )
                    
                    relationships.append(Relationship(
                        source=subject,
                        target=obj,
                        relationship_type=rel_type,
                        confidence=0.7,
                        properties={"verb": token.text, "lemma": token.lemma_}
                    ))
        
        return relationships
    
    def _extract_pattern_based(
        self,
        doc: Doc,
        entities: List[Entity]
    ) -> List[Relationship]:
        """
        Extract relationships using patterns.
        
        Args:
            doc: Spacy Doc
            entities: Extracted entities
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Simple pattern: Entity1 [verb/prep] Entity2
        for i, ent1 in enumerate(entities):
            for ent2 in entities[i+1:]:
                # Check if entities are in same sentence
                if abs(ent1.start - ent2.start) > 100:  # Skip if too far apart
                    continue
                
                # Find tokens between entities
                start_idx = min(ent1.end, ent2.end)
                end_idx = max(ent1.start, ent2.start)
                
                between_text = doc.text[start_idx:end_idx].lower()
                
                # Check for relationship indicators
                for word, rel_type in self.verb_patterns.items():
                    if word in between_text:
                        relationships.append(Relationship(
                            source=ent1 if ent1.start < ent2.start else ent2,
                            target=ent2 if ent1.start < ent2.start else ent1,
                            relationship_type=rel_type,
                            confidence=0.6,
                            properties={"pattern": word}
                        ))
                        break
        
        return relationships
    
    def _extract_cooccurrence(
        self,
        doc: Doc,
        entities: List[Entity]
    ) -> List[Relationship]:
        """
        Extract relationships based on co-occurrence.
        
        Args:
            doc: Spacy Doc
            entities: Extracted entities
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Group entities by sentence
        sentence_entities = {}
        
        for sent_idx, sent in enumerate(doc.sents):
            sent_ents = []
            for entity in entities:
                if entity.start >= sent.start_char and entity.end <= sent.end_char:
                    sent_ents.append(entity)
            
            if len(sent_ents) >= 2:
                sentence_entities[sent_idx] = sent_ents
        
        # Create co-occurrence relationships
        for sent_idx, sent_ents in sentence_entities.items():
            for i, ent1 in enumerate(sent_ents):
                for ent2 in sent_ents[i+1:]:
                    if ent1 != ent2:
                        relationships.append(Relationship(
                            source=ent1,
                            target=ent2,
                            relationship_type="CO_OCCURS_WITH",
                            confidence=0.4,
                            properties={"sentence_idx": sent_idx}
                        ))
        
        return relationships
    
    def _deduplicate(
        self,
        relationships: List[Relationship]
    ) -> List[Relationship]:
        """
        Remove duplicate relationships.
        
        Args:
            relationships: List of relationships
            
        Returns:
            Deduplicated relationships
        """
        seen = set()
        unique = []
        
        for rel in relationships:
            # Create unique key
            key = (
                rel.source.text.lower(),
                rel.target.text.lower(),
                rel.relationship_type
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(rel)
            else:
                # Keep relationship with higher confidence
                for i, existing in enumerate(unique):
                    existing_key = (
                        existing.source.text.lower(),
                        existing.target.text.lower(),
                        existing.relationship_type
                    )
                    
                    if existing_key == key and rel.confidence > existing.confidence:
                        unique[i] = rel
                        break
        
        return unique
    
    def __repr__(self) -> str:
        """String representation."""
        return f"RelationshipMapper(model={self.model_name})"