"""
Convert JSON graph data to Obsidian-flavored Markdown files

This script takes the d3_graph_data.json file and creates individual
Markdown files for each node, with proper Obsidian wikilinks [[]] syntax
for relationships and hierarchies.

Output structure:
- Each node becomes a separate .md file
- File names are sanitized versions of node names
- Wikilinks connect related nodes
- Tags are added based on node depth and type
- Frontmatter includes metadata (YAML)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# Configure paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data.json"
OUTPUT_DIR = PROJECT_ROOT / "obsidian_vault"


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Convert node name to valid filename.
    
    Args:
        name: Original node name
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename without extension
    """
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    # Replace multiple spaces/underscores with single underscore
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('_.')
    
    return filename


def get_node_depth(node: Dict) -> int:
    """
    Calculate node depth. Returns 1 for all nodes since we don't have
    a hierarchical structure in the UUID-based system.
    
    Args:
        node: Node dictionary
        
    Returns:
        Depth level (default to 1)
    """
    # Could be extended to use other metadata if available
    return 1


def get_parent_id(node: Dict, node_map: Dict = None) -> str:
    """
    Get parent node ID. In UUID-based system, there's no inherent hierarchy.
    Returns empty string.
    
    Args:
        node: Node dictionary
        node_map: Optional mapping of node IDs to nodes
        
    Returns:
        Parent node ID, or empty string if no parent
    """
    # Could be extended to use 'parent' field if available in node data
    return ""


def get_node_tags(node: Dict) -> List[str]:
    """
    Generate tags for a node based on its properties.
    
    Args:
        node: Node dictionary
        
    Returns:
        List of tag strings
    """
    tags = []
    
    # Add general tag
    tags.append("concept")
    
    # Add RF domain tag
    tags.append("rf-engineering")
    
    # Check if node name suggests it's a fundamental concept
    name = node.get('name', '').lower()
    if any(word in name for word in ['fundamental', 'basic', 'introduction', 'overview']):
        tags.append("fundamental")
    
    return tags


class ObsidianConverter:
    """Convert JSON graph data to Obsidian Markdown files."""
    
    def __init__(self, input_file: Path, output_dir: Path):
        """
        Initialize converter.
        
        Args:
            input_file: Path to input JSON file
            output_dir: Path to output directory for Markdown files
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.data = None
        self.nodes = []
        self.links = []
        self.node_map = {}  # id -> node
        self.filename_map = {}  # id -> filename
        self.links_by_source = defaultdict(list)  # source_id -> [links]
        self.links_by_target = defaultdict(list)  # target_id -> [links]
        self.children_map = defaultdict(list)  # parent_id -> [child_ids]
        
    def load_data(self):
        """Load JSON data from file."""
        print(f"Loading data from: {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.nodes = self.data.get('nodes', [])
        self.links = self.data.get('links', [])
        
        print(f"Loaded {len(self.nodes)} nodes and {len(self.links)} links")
        
    def prepare_mappings(self):
        """Create helpful mappings for quick lookups."""
        print("Preparing node and link mappings...")
        
        # Create node map and filename map
        filename_counts = defaultdict(int)
        
        for node in self.nodes:
            node_id = node['id']
            self.node_map[node_id] = node
            
            # Generate unique filename
            base_filename = sanitize_filename(node['name'])
            
            # Handle duplicates by appending ID
            if filename_counts[base_filename] > 0:
                filename = f"{base_filename}_{node_id}"
            else:
                filename = base_filename
            
            filename_counts[base_filename] += 1
            self.filename_map[node_id] = filename
            
            # Parent-child relationships will be determined from links
            # (no hierarchical structure in UUID-based system)
        
        # Create link mappings
        for link in self.links:
            source_id = link['source']
            target_id = link['target']
            
            self.links_by_source[source_id].append(link)
            self.links_by_target[target_id].append(link)
        
        print(f"Created mappings for {len(self.node_map)} nodes")
        print(f"Found {len(self.children_map)} nodes with children")
        
    def create_frontmatter(self, node: Dict) -> str:
        """
        Create YAML frontmatter for a node.
        
        Args:
            node: Node dictionary
            
        Returns:
            YAML frontmatter string
        """
        node_id = node['id']
        tags = get_node_tags(node)
        
        frontmatter = ["---"]
        frontmatter.append(f"id: {node_id}")
        frontmatter.append(f"title: {node['name']}")
        
        # Add tags
        if tags:
            frontmatter.append("tags:")
            for tag in tags:
                frontmatter.append(f"  - {tag}")
        
        frontmatter.append("---")
        frontmatter.append("")
        
        return "\n".join(frontmatter)
    
    def create_node_content(self, node: Dict) -> str:
        """
        Create Markdown content for a node.
        
        Args:
            node: Node dictionary
            
        Returns:
            Complete Markdown content
        """
        node_id = node['id']
        content_parts = []
        
        # Add frontmatter
        content_parts.append(self.create_frontmatter(node))
        
        # Add title
        content_parts.append(f"# {node['name']}\n")
        
        # Add description if available
        description = node.get('description', '').strip()
        if description:
            content_parts.append(f"{description}\n")
        
        # Add related concepts (from links)
        outgoing_links = self.links_by_source.get(node_id, [])
        incoming_links = self.links_by_target.get(node_id, [])
        
        # Group links by type
        links_by_type = defaultdict(list)
        
        for link in outgoing_links:
            target_id = link['target']
            if target_id in self.node_map:
                link_type = link.get('type', 'related')
                links_by_type[link_type].append((target_id, 'to'))
        
        for link in incoming_links:
            source_id = link['source']
            if source_id in self.node_map:
                link_type = link.get('type', 'related')
                links_by_type[link_type].append((source_id, 'from'))
        
        # Display relationships by type
        if links_by_type:
            content_parts.append("## Related Concepts\n")
            
            # Define friendly names for link types
            type_names = {
                'dependency': 'Dependencies',
                'semantically_similar': 'Semantically Similar',
                'related': 'Related To',
                'prerequisite': 'Prerequisites',
                'implements': 'Implements',
                'uses': 'Uses',
            }
            
            for link_type, related_nodes in sorted(links_by_type.items()):
                friendly_name = type_names.get(link_type, link_type.replace('_', ' ').title())
                content_parts.append(f"### {friendly_name}\n")
                
                # Remove duplicates and sort
                unique_nodes = list(set(related_nodes))
                unique_nodes.sort(key=lambda x: (x[1], self.node_map[x[0]]['name']))
                
                for related_id, direction in unique_nodes:
                    related = self.node_map[related_id]
                    related_link = f"[[{self.filename_map[related_id]}|{related['name']}]]"
                    
                    # Add direction indicator
                    if link_type in ['dependency', 'prerequisite']:
                        if direction == 'from':
                            content_parts.append(f"- {related_link} (required)")
                        else:
                            content_parts.append(f"- {related_link} (depends on this)")
                    else:
                        content_parts.append(f"- {related_link}")
                
                content_parts.append("")
        
        # Add resources section (URLs)
        node_urls = node.get('urls', [])
        link_urls = []
        
        # Collect URLs from related links
        for link in outgoing_links + incoming_links:
            link_urls.extend(link.get('urls', []))
        
        all_urls = node_urls + link_urls
        
        if all_urls:
            content_parts.append("## Resources\n")
            
            # Deduplicate URLs
            seen_urls = set()
            for url_data in all_urls:
                # Handle both string and object formats
                if isinstance(url_data, str):
                    url = url_data
                    title = url
                    description = ''
                else:
                    url = url_data.get('url', '')
                    title = url_data.get('title', url)
                    description = url_data.get('description', '')
                
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    
                    # Format based on URL type
                    if 'youtube.com' in url or 'youtu.be' in url:
                        content_parts.append(f"- 📺 [{title}]({url})")
                    elif any(domain in url for domain in ['.pdf', 'arxiv.org']):
                        content_parts.append(f"- 📄 [{title}]({url})")
                    else:
                        content_parts.append(f"- 🔗 [{title}]({url})")
                    
                    if description:
                        content_parts.append(f"  - {description}")
            
            content_parts.append("")
        
        # Add metadata section
        content_parts.append("---\n")
        content_parts.append(f"*Node ID: `{node_id}`*")
        
        return "\n".join(content_parts)
    
    def create_index_file(self) -> str:
        """
        Create an index/home file that lists all root nodes.
        
        Returns:
            Markdown content for index file
        """
        content_parts = []
        
        content_parts.append("---")
        content_parts.append("title: RF Engineering Knowledge Base")
        content_parts.append("tags:")
        content_parts.append("  - index")
        content_parts.append("  - home")
        content_parts.append("---")
        content_parts.append("")
        content_parts.append("# RF Engineering Knowledge Base\n")
        content_parts.append("Welcome to the RF Engineering knowledge vault. This is an interconnected collection of concepts, topics, and resources related to Radio Frequency engineering.\n")
        
        # Add statistics
        content_parts.append("## Overview\n")
        content_parts.append(f"- **Total Concepts**: {len(self.nodes)}")
        content_parts.append(f"- **Total Connections**: {len(self.links)}")
        
        # Find nodes with the most connections (hub nodes)
        connection_counts = defaultdict(int)
        for link in self.links:
            connection_counts[link['source']] += 1
            connection_counts[link['target']] += 1
        
        hub_nodes = sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        content_parts.append("")
        
        # List most connected nodes
        root_nodes = [self.node_map[node_id] for node_id, _ in hub_nodes if node_id in self.node_map]
        
        if root_nodes:
            content_parts.append("## Most Connected Concepts\n")
            content_parts.append("Start exploring from these highly connected concepts:\n")
            
            for i, node in enumerate(root_nodes[:15], 1):
                node_id = node['id']
                node_link = f"[[{self.filename_map[node_id]}|{node['name']}]]"
                description = node.get('description', '')[:150]
                
                connections = connection_counts[node_id]
                content_parts.append(f"{i}. {node_link} ({connections} connections)")
                if description:
                    content_parts.append(f"   {description}{'...' if len(node.get('description', '')) > 150 else ''}")
                content_parts.append("")
        
        # Add high-level topics if available
        if self.data.get('high_level_topics'):
            content_parts.append("## Thematic Clusters\n")
            content_parts.append("Concepts grouped by semantic similarity:\n")
            
            for topic in self.data['high_level_topics']:
                topic_name = topic['name']
                sub_topics = topic.get('sub_topics', [])
                
                content_parts.append(f"### {topic_name} ({len(sub_topics)} concepts)\n")
                
                # Show first few topics
                for node_id in sub_topics[:5]:
                    if node_id in self.node_map:
                        node = self.node_map[node_id]
                        node_link = f"[[{self.filename_map[node_id]}|{node['name']}]]"
                        content_parts.append(f"- {node_link}")
                
                if len(sub_topics) > 5:
                    content_parts.append(f"- *...and {len(sub_topics) - 5} more*\n")
                else:
                    content_parts.append("")
        
        content_parts.append("---\n")
        content_parts.append("*Use the graph view to explore connections between concepts.*")
        
        return "\n".join(content_parts)
    
    def write_files(self):
        """Write all Markdown files to output directory."""
        print(f"\nCreating output directory: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write individual node files
        print(f"Writing {len(self.nodes)} node files...")
        
        for i, node in enumerate(self.nodes, 1):
            node_id = node['id']
            filename = self.filename_map[node_id]
            filepath = self.output_dir / f"{filename}.md"
            
            content = self.create_node_content(node)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if i % 50 == 0:
                print(f"  Written {i}/{len(self.nodes)} files...")
        
        print(f"✓ Written {len(self.nodes)} node files")
        
        # Write index file
        print("Creating index file...")
        index_content = self.create_index_file()
        index_path = self.output_dir / "INDEX.md"
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"✓ Created index file: {index_path}")
    
    def create_obsidian_config(self):
        """Create basic Obsidian vault configuration."""
        obsidian_dir = self.output_dir / ".obsidian"
        obsidian_dir.mkdir(exist_ok=True)
        
        # Create basic config
        config = {
            "baseFontSize": 16,
            "theme": "moonstone",
            "showLineNumber": True,
            "foldHeading": True,
            "foldIndent": True,
            "showIndentGuide": True,
        }
        
        config_file = obsidian_dir / "app.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Create graph config for better visualization
        graph_config = {
            "search": "",
            "localJumps": 2,
            "localBacklinks": True,
            "localForelinks": True,
            "localInterlinkedNotes": True,
            "showTags": True,
            "showAttachments": False,
            "hideUnresolved": False,
            "showArrow": True,
            "textFadeMultiplier": 0,
            "nodeSizeMultiplier": 1,
            "lineSizeMultiplier": 1,
            "centerStrength": 0.3,
            "repelStrength": 10,
            "linkStrength": 1,
            "linkDistance": 250,
        }
        
        graph_file = obsidian_dir / "graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(graph_config, f, indent=2)
        
        print(f"✓ Created Obsidian configuration in {obsidian_dir}")
    
    def generate_statistics(self):
        """Generate and display conversion statistics."""
        print("\n" + "="*60)
        print("CONVERSION STATISTICS")
        print("="*60)
        
        # Connection distribution
        connection_counts = defaultdict(int)
        for link in self.links:
            connection_counts[link['source']] += 1
            connection_counts[link['target']] += 1
        
        connected_nodes = len([c for c in connection_counts.values() if c > 0])
        avg_connections = sum(connection_counts.values()) / len(connection_counts) if connection_counts else 0
        
        print(f"\nConnectivity:")
        print(f"  Nodes with connections: {connected_nodes}/{len(self.nodes)}")
        print(f"  Average connections per node: {avg_connections:.2f}")
        
        # Link types
        link_type_counts = defaultdict(int)
        for link in self.links:
            link_type = link.get('type', 'unknown')
            link_type_counts[link_type] += 1
        
        print("\nLinks by type:")
        for link_type, count in sorted(link_type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {link_type}: {count}")
        
        # Nodes with resources
        nodes_with_urls = sum(1 for n in self.nodes if n.get('urls'))
        print(f"\nNodes with resources: {nodes_with_urls}/{len(self.nodes)}")
        
        # File count
        total_files = len(self.nodes) + 1  # +1 for index
        print(f"\nTotal files created: {total_files}")
        print(f"Output directory: {self.output_dir}")
        
    def convert(self):
        """Execute the full conversion process."""
        print("="*60)
        print("JSON TO OBSIDIAN MARKDOWN CONVERTER")
        print("="*60)
        print()
        
        # Load and prepare
        self.load_data()
        self.prepare_mappings()
        
        # Convert and write
        self.write_files()
        
        # Create Obsidian config
        self.create_obsidian_config()
        
        # Show statistics
        self.generate_statistics()
        
        print("\n" + "="*60)
        print("✓ CONVERSION COMPLETE!")
        print("="*60)
        print(f"\nYou can now open '{self.output_dir}' as an Obsidian vault.")
        print("Start with the INDEX.md file to explore the knowledge base.")


def main():
    """Main execution function."""
    print("="*60)
    print("JSON TO OBSIDIAN MARKDOWN CONVERTER")
    print("="*60)
    print()
    
    # Check which files are available
    base_file = DATA_DIR / "d3_graph_data.json"
    semantic_file = DATA_DIR / "d3_graph_data_with_semantic_links.json"
    
    available_files = []
    
    if base_file.exists():
        available_files.append(("1", "Basic graph data (no links)", base_file))
    
    if semantic_file.exists():
        available_files.append(("2", "Graph data with semantic links", semantic_file))
    
    if not available_files:
        print(f"Error: No data files found in {DATA_DIR}")
        print(f"Looking for: d3_graph_data.json or d3_graph_data_with_semantic_links.json")
        return
    
    # Let user choose
    print("Available data files:")
    for num, desc, filepath in available_files:
        print(f"  {num}. {desc}")
        print(f"     {filepath}")
    
    print()
    
    if len(available_files) == 1:
        choice = "1"
        print(f"Only one file available, using: {available_files[0][1]}")
    else:
        choice = input("Select file to convert (1 or 2, default: 2): ").strip() or "2"
    
    # Find selected file
    input_file = None
    for num, desc, filepath in available_files:
        if num == choice:
            input_file = filepath
            break
    
    if not input_file:
        print(f"Invalid choice: {choice}")
        return
    
    print()
    
    try:
        converter = ObsidianConverter(input_file, OUTPUT_DIR)
        converter.convert()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"\nMake sure the input file exists at: {input_file}")
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
