"""
Semantic Similarity-Based Link Generator for Knowledge Graph

This script analyzes node pairs using:
1. All-Pairs Cosine Similarity (sentence embeddings)
2. Keyword/Phrase Co-occurrence Filter
3. Dynamic/Adaptive Thresholding (user-configurable)
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
import numpy as np
from collections import defaultdict
import re

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

# Configure paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_with_semantic_links.json"


class SemanticLinkGenerator:
    """Generate semantic links between nodes based on similarity."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the link generator.
        
        Args:
            model_name: Name of the sentence transformer model
                       Options: 'all-MiniLM-L6-v2' (fast, general)
                               'all-mpnet-base-v2' (better quality)
                               'allenai/scibert_scivocab_uncased' (scientific text)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")
        
        print(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.nodes = []
        self.embeddings = None
        self.similarity_matrix = None
        self.existing_links = set()
        
    def load_data(self, filepath: Path) -> Dict:
        """Load the graph data from JSON file."""
        print(f"Loading data from: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.nodes = data['nodes']
        
        # Store existing links to avoid duplicates
        for link in data.get('links', []):
            self.existing_links.add((link['source'], link['target']))
            # Add reverse direction for undirected semantics
            self.existing_links.add((link['target'], link['source']))
        
        print(f"Loaded {len(self.nodes)} nodes and {len(data.get('links', []))} existing links")
        return data
    
    def extract_keywords(self, text: str, min_length: int = 3) -> Set[str]:
        """
        Extract keywords from text (simple word tokenization).
        
        Args:
            text: Input text
            min_length: Minimum word length to consider
            
        Returns:
            Set of lowercase keywords
        """
        # Remove special characters and split
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        # Filter by length and common stop words
        stop_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was', 'has'}
        return {w for w in words if len(w) >= min_length and w not in stop_words}
    
    def keyword_cooccurrence_filter(self, node_a: Dict, node_b: Dict) -> bool:
        """
        Check if nodes share significant keywords.
        
        Args:
            node_a: First node
            node_b: Second node
            
        Returns:
            True if nodes share keywords
        """
        # Combine name and description for each node
        text_a = f"{node_a['name']} {node_a.get('description', '')}"
        text_b = f"{node_b['name']} {node_b.get('description', '')}"
        
        keywords_a = self.extract_keywords(text_a)
        keywords_b = self.extract_keywords(text_b)
        
        # Check for overlap
        overlap = keywords_a & keywords_b
        return len(overlap) > 0
    
    def compute_embeddings(self):
        """Compute embeddings for all nodes."""
        print("Computing embeddings for all nodes...")
        
        # Create text representations
        texts = []
        for node in self.nodes:
            # Combine name and description
            text = f"{node['name']}. {node.get('description', '')}"
            texts.append(text)
        
        # Compute embeddings
        self.embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=32)
        print(f"Computed embeddings with shape: {self.embeddings.shape}")
    
    def compute_similarity_matrix(self):
        """Compute all-pairs cosine similarity."""
        print("Computing all-pairs cosine similarity matrix...")
        
        if self.embeddings is None:
            raise ValueError("Embeddings not computed. Call compute_embeddings() first.")
        
        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        normalized_embeddings = self.embeddings / norms
        
        # Compute similarity matrix (all pairs)
        self.similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
        
        # Set diagonal to -1 to avoid self-links
        np.fill_diagonal(self.similarity_matrix, -1)
        
        print(f"Similarity matrix shape: {self.similarity_matrix.shape}")
    
    def analyze_similarity_distribution(self):
        """Analyze and display similarity score distribution."""
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not computed.")
        
        # Get upper triangle (avoid duplicates)
        triu_indices = np.triu_indices_from(self.similarity_matrix, k=1)
        similarities = self.similarity_matrix[triu_indices]
        
        print("\n" + "="*60)
        print("SIMILARITY DISTRIBUTION ANALYSIS")
        print("="*60)
        print(f"Total node pairs: {len(similarities):,}")
        print(f"Min similarity: {similarities.min():.4f}")
        print(f"Max similarity: {similarities.max():.4f}")
        print(f"Mean similarity: {similarities.mean():.4f}")
        print(f"Median similarity: {np.median(similarities):.4f}")
        print(f"Std deviation: {similarities.std():.4f}")
        
        # Percentiles
        percentiles = [90, 95, 99, 99.5, 99.9]
        print("\nPercentiles:")
        for p in percentiles:
            value = np.percentile(similarities, p)
            count = np.sum(similarities >= value)
            print(f"  {p}th percentile: {value:.4f} ({count:,} pairs above this)")
        
        # Distribution by bins
        print("\nDistribution by similarity range:")
        bins = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        for low, high in bins:
            count = np.sum((similarities >= low) & (similarities < high))
            pct = 100 * count / len(similarities)
            print(f"  [{low:.1f}, {high:.1f}): {count:,} pairs ({pct:.2f}%)")
    
    def analyze_keyword_cooccurrence(self, sample_size: int = 1000):
        """Analyze keyword co-occurrence statistics."""
        print("\n" + "="*60)
        print("KEYWORD CO-OCCURRENCE ANALYSIS")
        print("="*60)
        
        # Sample random pairs for efficiency
        n = len(self.nodes)
        if sample_size > n * (n - 1) / 2:
            sample_size = n * (n - 1) // 2
        
        print(f"Analyzing {sample_size:,} random node pairs...")
        
        cooccur_count = 0
        sampled = 0
        
        # Random sampling
        import random
        random.seed(42)
        pairs = [(i, j) for i in range(n) for j in range(i+1, n)]
        sampled_pairs = random.sample(pairs, min(sample_size, len(pairs)))
        
        for i, j in sampled_pairs:
            if self.keyword_cooccurrence_filter(self.nodes[i], self.nodes[j]):
                cooccur_count += 1
            sampled += 1
        
        pct = 100 * cooccur_count / sampled
        print(f"Pairs with keyword overlap: {cooccur_count:,} / {sampled:,} ({pct:.2f}%)")
        print(f"Estimated total pairs with overlap: {int(pct * n * (n-1) / 200):,}")
    
    def get_top_k_similar(self, node_idx: int, k: int, 
                         min_similarity: float = 0.0,
                         use_keyword_filter: bool = True) -> List[Tuple[int, float]]:
        """
        Get top-K most similar nodes for a given node.
        
        Args:
            node_idx: Index of the source node
            k: Number of top similar nodes to return
            min_similarity: Minimum similarity threshold
            use_keyword_filter: Apply keyword co-occurrence filter
            
        Returns:
            List of (node_index, similarity_score) tuples
        """
        similarities = self.similarity_matrix[node_idx]
        
        # Apply keyword filter if requested
        if use_keyword_filter:
            valid_indices = []
            for idx in range(len(similarities)):
                if idx != node_idx and similarities[idx] >= min_similarity:
                    if self.keyword_cooccurrence_filter(self.nodes[node_idx], self.nodes[idx]):
                        valid_indices.append(idx)
            
            if not valid_indices:
                return []
            
            # Get similarities for valid indices
            valid_sims = [(idx, similarities[idx]) for idx in valid_indices]
        else:
            # All indices except self
            valid_sims = [(idx, sim) for idx, sim in enumerate(similarities) 
                         if idx != node_idx and sim >= min_similarity]
        
        # Sort by similarity and take top K
        valid_sims.sort(key=lambda x: x[1], reverse=True)
        return valid_sims[:k]
    
    def generate_links(self, k: int = 5, min_similarity: float = 0.5,
                      use_keyword_filter: bool = True) -> List[Dict]:
        """
        Generate semantic links using dynamic thresholding.
        
        Args:
            k: Number of top similar nodes to link per node
            min_similarity: Minimum similarity threshold
            use_keyword_filter: Apply keyword co-occurrence filter
            
        Returns:
            List of new link dictionaries
        """
        print("\n" + "="*60)
        print("GENERATING SEMANTIC LINKS")
        print("="*60)
        print(f"Parameters:")
        print(f"  Top-K per node: {k}")
        print(f"  Min similarity: {min_similarity}")
        print(f"  Keyword filter: {use_keyword_filter}")
        
        new_links = []
        links_by_source = defaultdict(int)
        
        for i, node in enumerate(self.nodes):
            top_similar = self.get_top_k_similar(i, k, min_similarity, use_keyword_filter)
            
            for j, similarity in top_similar:
                source_id = node['id']
                target_id = self.nodes[j]['id']
                
                # Check if link already exists
                if (source_id, target_id) in self.existing_links:
                    continue
                
                # Create new link
                new_links.append({
                    'source': source_id,
                    'target': target_id,
                    'type': 'semantically_similar',
                    'similarity_score': float(similarity),
                    'urls': []
                })
                
                links_by_source[source_id] += 1
        
        print(f"\nGenerated {len(new_links):,} new semantic links")
        print(f"Average links per node: {len(new_links) / len(self.nodes):.2f}")
        
        # Show distribution
        link_counts = list(links_by_source.values())
        if link_counts:
            print(f"Min links from a node: {min(link_counts)}")
            print(f"Max links from a node: {max(link_counts)}")
            print(f"Median links from a node: {np.median(link_counts):.1f}")
        
        return new_links
    
    def save_with_new_links(self, data: Dict, new_links: List[Dict], output_file: Path):
        """Save graph data with new semantic links."""
        data['links'].extend(new_links)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved graph with {len(data['links'])} total links to: {output_file}")


def main():
    """Main execution function."""
    print("="*60)
    print("SEMANTIC SIMILARITY LINK GENERATOR")
    print("="*60)
    
    # Check if input file exists
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        return
    
    # Initialize generator
    try:
        # Choose model - options:
        # 'all-MiniLM-L6-v2' - fast, good for general text
        # 'all-mpnet-base-v2' - slower but better quality
        # 'allenai/scibert_scivocab_uncased' - for scientific text
        generator = SemanticLinkGenerator(model_name='all-MiniLM-L6-v2')
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    # Load data
    data = generator.load_data(INPUT_FILE)
    
    # Compute embeddings and similarity
    generator.compute_embeddings()
    generator.compute_similarity_matrix()
    
    # Analyze similarity distribution
    generator.analyze_similarity_distribution()
    
    # Analyze keyword co-occurrence
    generator.analyze_keyword_cooccurrence(sample_size=1000)
    
    # Interactive parameter selection
    print("\n" + "="*60)
    print("DYNAMIC THRESHOLDING CONFIGURATION")
    print("="*60)
    print("\nBased on the analysis above, configure your linking strategy:")
    
    try:
        k = int(input("\nTop-K similar nodes per node (e.g., 5): ") or "5")
        min_sim = float(input("Minimum similarity threshold (e.g., 0.5): ") or "0.5")
        use_filter = input("Use keyword co-occurrence filter? (y/n, default: y): ").lower()
        use_keyword_filter = use_filter != 'n'
        
        # Generate links
        new_links = generator.generate_links(k, min_sim, use_keyword_filter)
        
        # Confirm save
        save = input(f"\nSave {len(new_links)} new links to file? (y/n): ").lower()
        if save == 'y':
            generator.save_with_new_links(data, new_links, OUTPUT_FILE)
            print("\n✓ Complete!")
        else:
            print("\nLinks not saved. Adjust parameters and run again.")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()