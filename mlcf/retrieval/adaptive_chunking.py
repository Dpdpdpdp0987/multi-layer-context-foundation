"""
Adaptive Chunk Overlap System - Intelligent document chunking with context preservation.
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import re
from loguru import logger


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    chunk_id: str
    content: str
    start_pos: int
    end_pos: int
    overlap_before: int
    overlap_after: int
    metadata: Dict[str, Any]
    
    def __len__(self) -> int:
        """Return chunk length."""
        return len(self.content)


class AdaptiveChunker:
    """
    Adaptive chunking with intelligent overlap management.
    
    Adjusts chunk size and overlap based on content structure,
    preserving semantic boundaries like sentences and paragraphs.
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1024,
        base_overlap: int = 50,
        adaptive_overlap: bool = True,
        preserve_sentences: bool = True
    ):
        """
        Initialize adaptive chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            min_chunk_size: Minimum allowed chunk size
            max_chunk_size: Maximum allowed chunk size
            base_overlap: Base overlap size between chunks
            adaptive_overlap: Enable adaptive overlap calculation
            preserve_sentences: Try to preserve sentence boundaries
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.base_overlap = base_overlap
        self.adaptive_overlap = adaptive_overlap
        self.preserve_sentences = preserve_sentences
        
        # Sentence boundary detection pattern
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
        
        # Paragraph boundary detection
        self.paragraph_pattern = re.compile(r'\n\s*\n')
        
        logger.info(
            f"AdaptiveChunker initialized: chunk_size={chunk_size}, "
            f"overlap={base_overlap}, adaptive={adaptive_overlap}"
        )
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Chunk text with adaptive overlap.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunks
        """
        if not text:
            return []
        
        metadata = metadata or {}
        chunks = []
        
        # Detect structural boundaries
        sentence_positions = self._find_sentence_boundaries(text)
        paragraph_positions = self._find_paragraph_boundaries(text)
        
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Calculate chunk end position
            target_end = current_pos + self.chunk_size
            
            # Find optimal chunk boundary
            chunk_end = self._find_optimal_boundary(
                text=text,
                target_pos=target_end,
                sentence_positions=sentence_positions,
                paragraph_positions=paragraph_positions,
                max_pos=min(target_end + 200, len(text))  # Allow some flexibility
            )
            
            # Ensure minimum chunk size
            if chunk_end - current_pos < self.min_chunk_size and chunk_end < len(text):
                chunk_end = min(current_pos + self.min_chunk_size, len(text))
            
            # Ensure maximum chunk size
            if chunk_end - current_pos > self.max_chunk_size:
                chunk_end = current_pos + self.max_chunk_size
            
            # Calculate adaptive overlap for next chunk
            if self.adaptive_overlap:
                overlap = self._calculate_adaptive_overlap(
                    text=text,
                    chunk_start=current_pos,
                    chunk_end=chunk_end,
                    sentence_positions=sentence_positions
                )
            else:
                overlap = self.base_overlap
            
            # Extract chunk content
            chunk_content = text[current_pos:chunk_end]
            
            # Create chunk
            chunk = Chunk(
                chunk_id=f"chunk_{chunk_index}",
                content=chunk_content,
                start_pos=current_pos,
                end_pos=chunk_end,
                overlap_before=overlap if chunk_index > 0 else 0,
                overlap_after=overlap if chunk_end < len(text) else 0,
                metadata={
                    **metadata,
                    "chunk_index": chunk_index,
                    "total_length": len(text)
                }
            )
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            current_pos = chunk_end - overlap
            
            # Ensure we make progress
            if current_pos >= chunk_end:
                current_pos = chunk_end
            
            chunk_index += 1
            
            # Safety check for infinite loops
            if chunk_index > 10000:
                logger.warning("Chunking exceeded maximum iterations")
                break
        
        logger.debug(
            f"Created {len(chunks)} chunks from {len(text)} characters, "
            f"avg size: {sum(len(c) for c in chunks) / len(chunks):.0f}"
        )
        
        return chunks
    
    def _find_sentence_boundaries(self, text: str) -> List[int]:
        """
        Find sentence boundary positions in text.
        
        Args:
            text: Input text
            
        Returns:
            List of boundary positions
        """
        boundaries = [0]
        
        for match in self.sentence_pattern.finditer(text):
            boundaries.append(match.end())
        
        boundaries.append(len(text))
        
        return boundaries
    
    def _find_paragraph_boundaries(self, text: str) -> List[int]:
        """
        Find paragraph boundary positions in text.
        
        Args:
            text: Input text
            
        Returns:
            List of boundary positions
        """
        boundaries = [0]
        
        for match in self.paragraph_pattern.finditer(text):
            boundaries.append(match.end())
        
        boundaries.append(len(text))
        
        return boundaries
    
    def _find_optimal_boundary(
        self,
        text: str,
        target_pos: int,
        sentence_positions: List[int],
        paragraph_positions: List[int],
        max_pos: int
    ) -> int:
        """
        Find optimal chunk boundary near target position.
        
        Prioritizes paragraph > sentence > word boundaries.
        
        Args:
            text: Input text
            target_pos: Target boundary position
            sentence_positions: Sentence boundary positions
            paragraph_positions: Paragraph boundary positions
            max_pos: Maximum allowed position
            
        Returns:
            Optimal boundary position
        """
        # Clamp target position
        target_pos = min(target_pos, len(text))
        max_pos = min(max_pos, len(text))
        
        # Find nearest paragraph boundary
        nearest_para = self._find_nearest(
            target_pos,
            paragraph_positions,
            max_distance=100
        )
        
        if nearest_para and abs(nearest_para - target_pos) <= 100:
            return min(nearest_para, max_pos)
        
        # Find nearest sentence boundary
        if self.preserve_sentences:
            nearest_sent = self._find_nearest(
                target_pos,
                sentence_positions,
                max_distance=150
            )
            
            if nearest_sent:
                return min(nearest_sent, max_pos)
        
        # Find word boundary (fallback)
        boundary = self._find_word_boundary(text, target_pos, max_pos)
        
        return boundary
    
    def _find_nearest(
        self,
        target: int,
        positions: List[int],
        max_distance: int
    ) -> Optional[int]:
        """
        Find nearest position to target within max_distance.
        
        Args:
            target: Target position
            positions: Available positions
            max_distance: Maximum allowed distance
            
        Returns:
            Nearest position or None
        """
        if not positions:
            return None
        
        # Binary search for closest position
        left, right = 0, len(positions) - 1
        closest = None
        min_distance = float('inf')
        
        while left <= right:
            mid = (left + right) // 2
            pos = positions[mid]
            distance = abs(pos - target)
            
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest = pos
            
            if pos < target:
                left = mid + 1
            else:
                right = mid - 1
        
        return closest
    
    def _find_word_boundary(
        self,
        text: str,
        target_pos: int,
        max_pos: int
    ) -> int:
        """
        Find word boundary near target position.
        
        Args:
            text: Input text
            target_pos: Target position
            max_pos: Maximum position
            
        Returns:
            Word boundary position
        """
        # Search forward for whitespace
        pos = min(target_pos, max_pos - 1)
        
        while pos < max_pos and not text[pos].isspace():
            pos += 1
        
        # If we hit max_pos without finding space, use target
        if pos >= max_pos:
            pos = target_pos
        
        return min(pos, max_pos)
    
    def _calculate_adaptive_overlap(
        self,
        text: str,
        chunk_start: int,
        chunk_end: int,
        sentence_positions: List[int]
    ) -> int:
        """
        Calculate adaptive overlap size based on content.
        
        Args:
            text: Input text
            chunk_start: Chunk start position
            chunk_end: Chunk end position
            sentence_positions: Sentence boundary positions
            
        Returns:
            Overlap size
        """
        # Count sentences in chunk
        sentences_in_chunk = sum(
            1 for pos in sentence_positions
            if chunk_start <= pos <= chunk_end
        )
        
        # More sentences = larger overlap for better context
        if sentences_in_chunk <= 2:
            overlap = self.base_overlap // 2
        elif sentences_in_chunk <= 5:
            overlap = self.base_overlap
        else:
            overlap = int(self.base_overlap * 1.5)
        
        # Ensure overlap is within bounds
        chunk_size = chunk_end - chunk_start
        max_overlap = min(chunk_size // 3, 200)  # Max 1/3 of chunk or 200 chars
        
        return min(overlap, max_overlap)
    
    def merge_chunks(
        self,
        chunks: List[Chunk],
        max_merged_size: Optional[int] = None
    ) -> List[Chunk]:
        """
        Merge small adjacent chunks.
        
        Args:
            chunks: List of chunks to merge
            max_merged_size: Maximum size for merged chunks
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return []
        
        max_merged_size = max_merged_size or self.max_chunk_size
        merged = []
        current_merge = None
        
        for chunk in chunks:
            if current_merge is None:
                current_merge = chunk
            elif (len(current_merge) + len(chunk) <= max_merged_size and
                  len(current_merge) < self.chunk_size):
                # Merge chunks
                merged_content = current_merge.content + chunk.content
                current_merge = Chunk(
                    chunk_id=f"{current_merge.chunk_id}_merged",
                    content=merged_content,
                    start_pos=current_merge.start_pos,
                    end_pos=chunk.end_pos,
                    overlap_before=current_merge.overlap_before,
                    overlap_after=chunk.overlap_after,
                    metadata={**current_merge.metadata, "merged": True}
                )
            else:
                merged.append(current_merge)
                current_merge = chunk
        
        if current_merge:
            merged.append(current_merge)
        
        logger.debug(f"Merged {len(chunks)} chunks into {len(merged)} chunks")
        
        return merged