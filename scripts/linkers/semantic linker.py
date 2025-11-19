"""
Semantic Similarity-Based Link Generator for Knowledge Graph

This script analyzes node pairs using:
1. All-Pairs Cosine Similarity (sentence embeddings)
2. Keyword/Phrase Co-occurrence Filter
3. Dynamic/Adaptive Thresholding (user-configurable)
4. High-Level Topic Clustering (optional)
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
import numpy as np
from collections import defaultdict
import re
import uuid

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

# Gemini AI for topic naming
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    import os
    GEMINI_AVAILABLE = True
    load_dotenv()
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai or python-dotenv not installed.")
    print("Install with: pip install google-generativeai python-dotenv")

# Configure paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_with_syllabus.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_with_semantic_links.json"


class SemanticLinkGenerator:
    """Generate semantic links between nodes based on similarity."""
    
    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased"):
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
        # For semantic links, we treat them as bidirectional, so we store both directions
        for link in data.get('links', []):
            self.existing_links.add((link['source'], link['target']))
            # For semantic links, also block the reverse direction to prevent duplicate bidirectional links
            if link.get('type') == 'semantically_similar' or link.get('is_bidirectional', False):
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
    
    def _are_hierarchically_related(self, id1: str, id2: str) -> bool:
        """
        Check if two nodes are in a hierarchical relationship.
        
        Args:
            id1: First node ID
            id2: Second node ID
            
        Returns:
            True if nodes are parent-child or siblings
        """
        parts1 = str(id1).split('.')
        parts2 = str(id2).split('.')
        
        # One is parent of the other
        if parts1 == parts2[:len(parts1)] or parts2 == parts1[:len(parts2)]:
            return True
        
        # Share common parent (siblings)
        if len(parts1) > 1 and len(parts2) > 1:
            return parts1[:-1] == parts2[:-1]
        
        return False
    
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
                         use_keyword_filter: bool = True,
                         filter_hierarchical: bool = True,
                         max_per_node: int = None) -> List[Tuple[int, float]]:
        """
        Get top-K most similar nodes for a given node.
        
        Args:
            node_idx: Index of the source node
            k: Number of top similar nodes to return
            min_similarity: Minimum similarity threshold
            use_keyword_filter: Apply keyword co-occurrence filter
            filter_hierarchical: Exclude hierarchically related nodes
            max_per_node: Maximum semantic links per node (None = unlimited)
            
        Returns:
            List of (node_index, similarity_score) tuples
        """
        similarities = self.similarity_matrix[node_idx]
        source_node = self.nodes[node_idx]
        
        # Apply filters
        valid_indices = []
        for idx in range(len(similarities)):
            if idx == node_idx or similarities[idx] < min_similarity:
                continue
            
            target_node = self.nodes[idx]
            
            # Filter hierarchically related nodes
            if filter_hierarchical and self._are_hierarchically_related(source_node['id'], target_node['id']):
                continue
            
            # Apply keyword filter if requested
            if use_keyword_filter:
                if not self.keyword_cooccurrence_filter(source_node, target_node):
                    continue
            
            valid_indices.append(idx)
        
        if not valid_indices:
            return []
        
        # Get similarities for valid indices
        valid_sims = [(idx, similarities[idx]) for idx in valid_indices]
        
        # Sort by similarity and take top K
        valid_sims.sort(key=lambda x: x[1], reverse=True)
        
        # Apply max_per_node limit if specified
        if max_per_node is not None:
            return valid_sims[:min(k, max_per_node)]
        
        return valid_sims[:k]
    
    def generate_links(self, k: int = 5, min_similarity: float = 0.5,
                      use_keyword_filter: bool = True,
                      filter_hierarchical: bool = True,
                      max_semantic_per_node: int = 3) -> List[Dict]:
        """
        Generate semantic links using dynamic thresholding with hierarchical awareness.
        Semantic links are bidirectional by nature - only one link is created per node pair.
        
        Args:
            k: Number of top similar nodes to consider per node
            min_similarity: Minimum similarity threshold
            use_keyword_filter: Apply keyword co-occurrence filter
            filter_hierarchical: Exclude hierarchically related nodes
            max_semantic_per_node: Maximum semantic links per node (prevents over-connection)
            
        Returns:
            List of new link dictionaries
        """
        print("\n" + "="*60)
        print("GENERATING SEMANTIC LINKS WITH HIERARCHICAL FILTERING")
        print("="*60)
        print(f"Parameters:")
        print(f"  Top-K per node: {k}")
        print(f"  Min similarity: {min_similarity}")
        print(f"  Keyword filter: {use_keyword_filter}")
        print(f"  Filter hierarchical: {filter_hierarchical}")
        print(f"  Max semantic per node: {max_semantic_per_node}")
        
        new_links = []
        links_by_source = defaultdict(int)
        semantic_count = defaultdict(int)
        
        for i, node in enumerate(self.nodes):
            # Skip if node already has too many semantic links
            if semantic_count[node['id']] >= max_semantic_per_node:
                continue
            
            top_similar = self.get_top_k_similar(i, k, min_similarity, use_keyword_filter, 
                                                 filter_hierarchical, max_semantic_per_node)
            
            for j, similarity in top_similar:
                source_id = node['id']
                target_id = self.nodes[j]['id']
                
                # Check if link already exists (in either direction, since semantic links are bidirectional)
                if (source_id, target_id) in self.existing_links or (target_id, source_id) in self.existing_links:
                    continue
                
                # Check target node's semantic link count
                if semantic_count[target_id] >= max_semantic_per_node:
                    continue
                
                # Create new bidirectional link
                new_links.append({
                    'source': source_id,
                    'target': target_id,
                    'type': 'semantically_similar',
                    'similarity_score': float(similarity),
                    'is_bidirectional': True,
                    'urls': []
                })
                
                # Mark both directions as existing to prevent duplicate creation
                self.existing_links.add((source_id, target_id))
                self.existing_links.add((target_id, source_id))
                
                links_by_source[source_id] += 1
                semantic_count[source_id] += 1
                semantic_count[target_id] += 1
                
                # Stop if this node has reached its limit
                if semantic_count[source_id] >= max_semantic_per_node:
                    break
        
        print(f"\nGenerated {len(new_links):,} new bidirectional semantic links")
        print(f"Average links per node: {len(new_links) / len(self.nodes):.2f}")
        
        # Show distribution
        link_counts = list(links_by_source.values())
        if link_counts:
            print(f"Min links from a node: {min(link_counts)}")
            print(f"Max links from a node: {max(link_counts)}")
            print(f"Median links from a node: {np.median(link_counts):.1f}")
        
        return new_links
    
    def cluster_nodes(self, similarity_threshold: float = 0.7, 
                     min_cluster_size: int = 3) -> List[List[int]]:
        """
        Find tightly related clusters of nodes using agglomerative clustering.
        
        Args:
            similarity_threshold: Minimum similarity to be in same cluster
            min_cluster_size: Minimum nodes required to form a cluster
            
        Returns:
            List of clusters, where each cluster is a list of node indices
        """
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import squareform
        
        print("\n" + "="*60)
        print("CLUSTERING ANALYSIS")
        print("="*60)
        print(f"Parameters:")
        print(f"  Similarity threshold: {similarity_threshold}")
        print(f"  Min cluster size: {min_cluster_size}")
        
        # Convert similarity to distance
        distance_matrix = 1 - self.similarity_matrix
        
        # Convert to condensed distance matrix for linkage
        condensed_dist = squareform(distance_matrix, checks=False)
        
        # Perform hierarchical clustering
        print("Performing hierarchical clustering...")
        linkage_matrix = linkage(condensed_dist, method='average')
        
        # Cut tree at distance threshold
        distance_threshold = 1 - similarity_threshold
        cluster_labels = fcluster(linkage_matrix, distance_threshold, criterion='distance')
        
        # Group nodes by cluster
        clusters_dict = defaultdict(list)
        for node_idx, cluster_id in enumerate(cluster_labels):
            clusters_dict[cluster_id].append(node_idx)
        
        # Filter by minimum size
        clusters = [cluster for cluster in clusters_dict.values() 
                   if len(cluster) >= min_cluster_size]
        
        print(f"\nFound {len(clusters)} clusters with {min_cluster_size}+ nodes")
        
        # Show cluster size distribution
        cluster_sizes = [len(c) for c in clusters]
        if cluster_sizes:
            print(f"Cluster sizes:")
            print(f"  Min: {min(cluster_sizes)} nodes")
            print(f"  Max: {max(cluster_sizes)} nodes")
            print(f"  Mean: {np.mean(cluster_sizes):.1f} nodes")
            print(f"  Median: {np.median(cluster_sizes):.0f} nodes")
            
            # Show size distribution
            size_bins = [(3, 5), (6, 10), (11, 20), (21, 50), (51, 100), (100, 1000)]
            print("\nCluster size distribution:")
            for low, high in size_bins:
                count = sum(1 for s in cluster_sizes if low <= s <= high)
                if count > 0:
                    print(f"  {low}-{high} nodes: {count} clusters")
        
        return clusters
    
    def generate_cluster_name(self, cluster_indices: List[int], max_words: int = 3) -> str:
        """
        Generate a descriptive name for a cluster based on common keywords.
        
        Args:
            cluster_indices: List of node indices in the cluster
            max_words: Maximum words in the generated name
            
        Returns:
            Cluster name string
        """
        # Collect all keywords from cluster nodes
        all_keywords = []
        for idx in cluster_indices:
            node = self.nodes[idx]
            text = f"{node['name']} {node.get('description', '')}"
            keywords = self.extract_keywords(text, min_length=3)
            all_keywords.extend(keywords)
        
        # Count keyword frequency
        from collections import Counter
        keyword_freq = Counter(all_keywords)
        
        # Get most common keywords
        most_common = keyword_freq.most_common(max_words)
        
        if not most_common:
            return "Unnamed Cluster"
        
        # Create name from top keywords
        top_keywords = [word for word, _ in most_common]
        
        # Capitalize first letter of each word
        cluster_name = " ".join(word.capitalize() for word in top_keywords)
        
        return cluster_name
    
    def generate_ai_topic_names(self, high_level_topics: List[Dict], 
                               model_name: str = 'gemini-flash-latest') -> List[Dict]:
        """
        Use Gemini AI to generate better topic names based on subtopic content.
        
        Args:
            high_level_topics: List of high-level topics
            model_name: Gemini model to use
            
        Returns:
            Updated list of high-level topics with AI-generated names (or original list if error)
        """
        if not high_level_topics:
            print("\nWarning: No topics provided for AI naming")
            return high_level_topics
        
        if not GEMINI_AVAILABLE:
            print("\nError: Gemini AI not available. Install with:")
            print("pip install google-generativeai python-dotenv")
            return high_level_topics
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("\nError: GEMINI_API_KEY not found in .env file")
            return high_level_topics
        
        print("\n" + "="*60)
        print("GENERATING AI-POWERED TOPIC NAMES")
        print("="*60)
        
        # Rate limit configuration (requests per minute)
        rate_limits = {
            'gemini-2.5-pro': 2,
            'gemini-2.5-flash': 10,
            'gemini-2.5-flash-preview': 10,
            'gemini-2.5-flash-lite': 15,
            'gemini-2.5-flash-lite-preview': 15,
            'gemini-2.0-flash': 15,
            'gemini-2.0-flash-exp': 15,
            'gemini-2.0-flash-lite': 30,
        }
        
        # Get RPM for selected model (default to 10 if not found)
        rpm_limit = rate_limits.get(model_name.lower(), 10)
        delay_between_requests = 60.0 / rpm_limit  # seconds between requests
        
        print(f"Using model: {model_name}")
        print(f"Rate limit: {rpm_limit} requests/minute")
        print(f"Delay between requests: {delay_between_requests:.2f} seconds")
        
        # Calculate batch size based on topics (process more topics per request for efficiency)
        # We'll batch multiple topics into one request to minimize API calls
        topics_per_request = min(10, max(3, len(high_level_topics) // 5))
        
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            total_requests = (len(high_level_topics) + topics_per_request - 1) // topics_per_request
            print(f"\nProcessing {len(high_level_topics)} topics in {total_requests} API requests...")
            print(f"Estimated time: {total_requests * delay_between_requests:.1f} seconds")
            
            import time
            start_time = time.time()
            request_count = 0
            
            # Process topics in batches
            for i in range(0, len(high_level_topics), topics_per_request):
                batch = high_level_topics[i:i+topics_per_request]
                
                # Rate limiting: ensure we don't exceed RPM
                if request_count > 0:
                    elapsed = time.time() - start_time
                    expected_time = request_count * delay_between_requests
                    if elapsed < expected_time:
                        sleep_time = expected_time - elapsed
                        print(f"  Rate limiting: waiting {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                
                # Prepare batch prompt
                prompt_parts = [
                    "You are an expert at analyzing technical concepts and creating concise, descriptive topic names.",
                    "For each cluster of related concepts below, generate a SHORT (1-4 words) topic name that best describes the theme.",
                    "The name should be specific, technical, and capture the essence of what these concepts have in common.",
                    "Return ONLY the topic names, one per line, in the same order as provided.\n"
                ]
                
                for j, topic in enumerate(batch, 1):
                    # Get node names and descriptions for this topic
                    node_texts = []
                    for node_id in topic['sub_topics'][:15]:  # Limit to first 15 nodes
                        node = next((n for n in self.nodes if n['id'] == node_id), None)
                        if node:
                            node_text = f"{node['name']}"
                            if node.get('description'):
                                desc = node['description'][:100]  # Limit description length
                                node_text += f" ({desc})"
                            node_texts.append(node_text)
                    
                    prompt_parts.append(f"\nCluster {j} ({len(topic['sub_topics'])} concepts):")
                    prompt_parts.append(", ".join(node_texts[:10]))
                    if len(node_texts) > 10:
                        prompt_parts.append(f"... and {len(node_texts)-10} more")
                
                prompt = "\n".join(prompt_parts)
                
                # Call Gemini API
                try:
                    response = model.generate_content(prompt)
                    request_count += 1
                    generated_names = response.text.strip().split('\n')
                    
                    # Update topic names
                    for j, topic in enumerate(batch):
                        if j < len(generated_names):
                            old_name = topic['name']
                            new_name = generated_names[j].strip()
                            # Remove numbering if present (e.g., "1. Name" -> "Name")
                            new_name = re.sub(r'^\d+\.\s*', '', new_name)
                            # Remove quotes if present
                            new_name = new_name.strip('"\'')
                            # Remove any markdown formatting
                            new_name = re.sub(r'\*\*', '', new_name)
                            
                            if new_name and len(new_name) > 2:
                                topic['name'] = new_name
                                print(f"✓ '{old_name}' → '{new_name}'")
                            else:
                                print(f"⚠ Keeping original: '{old_name}'")
                        
                except Exception as e:
                    print(f"⚠ Error generating names for batch {i//topics_per_request + 1}: {e}")
                    continue
            
            total_time = time.time() - start_time
            print(f"\n✓ Completed AI topic naming in {total_time:.1f} seconds")
            print(f"  Made {request_count} API requests (avg {total_time/request_count:.2f}s per request)")
            
        except Exception as e:
            print(f"\nError with Gemini AI: {e}")
            print("Keeping original keyword-based names")
        
        return high_level_topics 


    def merge_small_clusters_with_high_level_topics(self, clusters: List[List[int]], high_level_topics: List[Dict]) -> List[Dict]:
        """
        For small clusters (<10 nodes), find the most similar large cluster.
        If the small cluster has high average similarity to a large cluster topic,
        merge all small cluster nodes into that topic.
        
        Args:
            clusters: List of clusters (each cluster is list of node indices)
            high_level_topics: Initial high-level topics
            
        Returns:
            Updated list of high-level topic dictionaries
        """
        print("\n" + "="*60)
        print("MERGING SMALL CLUSTERS WITH DOMINANT TOPICS")
        print("="*60)
        
        # Create a mapping from cluster indices to topic indices
        cluster_to_topic = {}
        for topic_idx, topic in enumerate(high_level_topics):
            # Find which cluster this topic came from
            topic_node_ids = set(topic['sub_topics'])
            for cluster_idx, cluster_indices in enumerate(clusters):
                cluster_node_ids = set(self.nodes[idx]['id'] for idx in cluster_indices)
                # If this topic contains all nodes from this cluster, they match
                if topic_node_ids == cluster_node_ids:
                    cluster_to_topic[cluster_idx] = topic_idx
                    break
        
        merged_count = 0
        nodes_added = 0
        topics_to_remove = set()
        
        for small_cluster_idx, small_cluster_indices in enumerate(clusters):
            cluster_size = len(small_cluster_indices)
            
            # Only process small clusters
            if cluster_size >= 10:
                continue
            
            # Find the most similar large cluster
            best_large_cluster_idx = None
            best_avg_similarity = 0
            overlap_count = 0
            
            for large_cluster_idx, large_cluster_indices in enumerate(clusters):
                # Skip if it's the same cluster or also small
                if large_cluster_idx == small_cluster_idx or len(large_cluster_indices) < 10:
                    continue
                
                # Calculate average similarity between small and large cluster
                similarities = []
                for small_idx in small_cluster_indices:
                    for large_idx in large_cluster_indices:
                        similarities.append(self.similarity_matrix[small_idx, large_idx])
                
                avg_sim = np.mean(similarities) if similarities else 0
                
                # Also count how many nodes from small cluster are already in large cluster
                small_node_ids = set(self.nodes[idx]['id'] for idx in small_cluster_indices)
                large_node_ids = set(self.nodes[idx]['id'] for idx in large_cluster_indices)
                current_overlap = len(small_node_ids & large_node_ids)
                
                # Update best if this is better
                if avg_sim > best_avg_similarity or (avg_sim == best_avg_similarity and current_overlap > overlap_count):
                    best_avg_similarity = avg_sim
                    best_large_cluster_idx = large_cluster_idx
                    overlap_count = current_overlap
            
            # Check if we found a good match (high similarity threshold)
            if best_large_cluster_idx is not None and best_avg_similarity >= 0.5:
                # Get the topic for the large cluster
                if best_large_cluster_idx in cluster_to_topic:
                    target_topic_idx = cluster_to_topic[best_large_cluster_idx]
                    target_topic = high_level_topics[target_topic_idx]
                    
                    # Get all nodes from small cluster
                    small_cluster_node_ids = [self.nodes[idx]['id'] for idx in small_cluster_indices]
                    
                    # Find nodes not already in the target topic
                    existing_nodes = set(target_topic['sub_topics'])
                    new_nodes = [nid for nid in small_cluster_node_ids if nid not in existing_nodes]
                    
                    if new_nodes:
                        target_topic['sub_topics'].extend(new_nodes)
                        merged_count += 1
                        nodes_added += len(new_nodes)
                        
                        # Mark small cluster's topic for removal if it exists
                        if small_cluster_idx in cluster_to_topic:
                            topics_to_remove.add(cluster_to_topic[small_cluster_idx])
                        
                        small_node_names = [self.nodes[idx]['name'] for idx in small_cluster_indices[:3]]
                        preview = ", ".join(small_node_names)
                        if len(small_cluster_indices) > 3:
                            preview += "..."
                        
                        print(f"Merged small cluster ({cluster_size} nodes: {preview})")
                        print(f"  → into '{target_topic['name']}' (avg similarity: {best_avg_similarity:.3f})")
                        print(f"  Added {len(new_nodes)} new nodes to topic")
        
        # Remove topics that were merged into others
        if topics_to_remove:
            high_level_topics = [topic for idx, topic in enumerate(high_level_topics) 
                                if idx not in topics_to_remove]
            print(f"\nRemoved {len(topics_to_remove)} small topic(s) that were merged")
        
        if merged_count > 0:
            print(f"\nTotal: Merged {merged_count} small clusters, added {nodes_added} nodes to topics")
        else:
            print("\nNo small clusters met the merging criteria (similarity >= 0.5 with large cluster)")
        
        return high_level_topics
    
    def create_high_level_topics(self, clusters: List[List[int]], 
                                apply_merging: bool = True) -> Tuple[List[Dict], List[List[int]]]:
        """
        Create high-level topic structures from clusters.
        
        Args:
            clusters: List of clusters (each cluster is list of node indices)
            apply_merging: Whether to apply small cluster merging after creation
            
        Returns:
            Tuple of (high-level topics list, original clusters list)
        """
        print("\n" + "="*60)
        print("GENERATING HIGH-LEVEL TOPICS")
        print("="*60)
        
        high_level_topics = []
        
        for i, cluster_indices in enumerate(clusters, 1):
            # Generate cluster name
            cluster_name = self.generate_cluster_name(cluster_indices)
            
            # Get node IDs
            sub_topic_ids = [self.nodes[idx]['id'] for idx in cluster_indices]
            
            # Create topic structure
            topic = {
                'id': str(uuid.uuid4()),
                'name': cluster_name,
                'sub_topics': sub_topic_ids
            }
            
            high_level_topics.append(topic)
            
            # Show preview
            if i <= 10:  # Show first 10 clusters
                node_names = [self.nodes[idx]['name'] for idx in cluster_indices[:5]]
                preview = ", ".join(node_names)
                if len(cluster_indices) > 5:
                    preview += f", ... ({len(cluster_indices)-5} more)"
                print(f"\n{i}. {cluster_name} ({len(cluster_indices)} nodes)")
                print(f"   {preview}")
        
        if len(clusters) > 10:
            print(f"\n... and {len(clusters)-10} more clusters")
        
        print(f"\nCreated {len(high_level_topics)} initial high-level topics")
        
        # Store clusters for later merging
        return high_level_topics, clusters
    
    def save_with_new_links(self, data: Dict, new_links: List[Dict], output_file: Path,
                           high_level_topics: List[Dict] = None):
        """Save graph data with new semantic links and optional high-level topics."""
        data['links'].extend(new_links)
        
        # Add high-level topics if provided
        if high_level_topics:
            data['high_level_topics'] = high_level_topics
            print(f"\nAdded {len(high_level_topics)} high-level topics")
        
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
        generator = SemanticLinkGenerator(model_name='all-mpnet-base-v2')
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
        filter_hier = input("Filter hierarchically related nodes? (y/n, default: y): ").lower()
        filter_hierarchical = filter_hier != 'n'
        max_sem = int(input("Max semantic links per node (e.g., 3, prevents over-connection): ") or "3")
        
        # Generate links
        new_links = generator.generate_links(k, min_sim, use_keyword_filter, filter_hierarchical, max_sem)
        
        # Optional: Generate high-level topics from clusters
        high_level_topics = None
        cluster_prompt = input("\nGenerate high-level topic clusters? (y/n, default: n): ").lower()
        
        if cluster_prompt == 'y':
            # Check if scipy is available
            try:
                import scipy
                
                print("\n" + "="*60)
                print("CLUSTERING CONFIGURATION")
                print("="*60)
                print("Clusters group tightly related nodes into high-level topics.")
                
                cluster_sim = float(input("\nCluster similarity threshold (e.g., 0.7): ") or "0.7")
                min_size = int(input("Minimum cluster size (e.g., 3): ") or "3")
                
                # Perform clustering
                clusters = generator.cluster_nodes(cluster_sim, min_size)
                
                if clusters:
                    # Generate high-level topics (without merging yet)
                    high_level_topics, original_clusters = generator.create_high_level_topics(clusters)
                    
                    # Safety check
                    if not high_level_topics:
                        print("\nError: Failed to create high-level topics")
                        high_level_topics = None
                    else:
                        # Optional: Use AI to generate better topic names
                        ai_naming = input("\nUse AI (Gemini) to generate topic names? (y/n, default: n): ").lower()
                        if ai_naming == 'y':
                            high_level_topics = generator.generate_ai_topic_names(high_level_topics)
                            
                            # Check if AI naming returned valid topics
                            if not high_level_topics:
                                print("\nWarning: AI naming failed, reverting to keyword-based names")
                                high_level_topics, original_clusters = generator.create_high_level_topics(clusters)
                        
                        # Now apply merging after all topics are created
                        if high_level_topics:
                            print("\n" + "="*60)
                            print("POST-PROCESSING: MERGING SMALL CLUSTERS")
                            print("="*60)
                            
                            merge_prompt = input("\nApply small cluster merging? (y/n, default: y): ").lower()
                            if merge_prompt != 'n':
                                high_level_topics = generator.merge_small_clusters_with_high_level_topics(
                                    original_clusters, high_level_topics
                                )
                        
                        # Ask for confirmation
                        if high_level_topics:
                            total_nodes_in_topics = sum(len(topic['sub_topics']) for topic in high_level_topics)
                            print(f"\nFinal Summary:")
                            print(f"  {len(high_level_topics)} high-level topics")
                            print(f"  {total_nodes_in_topics} total node assignments")
                            print(f"  {len(generator.nodes)} total nodes in graph")
                        else:
                            print("\nError: No valid topics created")
                            high_level_topics = None
                else:
                    print("\nNo clusters found with the specified parameters.")
                    high_level_topics = None
                    
            except ImportError:
                print("\nError: scipy is required for clustering.")
                print("Install with: pip install scipy")
                high_level_topics = None
        
        # Confirm save
        save_msg = f"\nSave {len(new_links)} new links"
        if high_level_topics:
            save_msg += f" and {len(high_level_topics)} high-level topics"
        save_msg += " to file? (y/n): "
        
        save = input(save_msg).lower()
        if save == 'y':
            generator.save_with_new_links(data, new_links, OUTPUT_FILE, high_level_topics)
            print("\n✓ Complete!")
        else:
            print("\nData not saved. Adjust parameters and run again.")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()