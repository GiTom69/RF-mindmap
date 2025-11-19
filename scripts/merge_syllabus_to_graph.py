"""
Merge RF Syllabus into d3_graph_data.json

This script converts the RF_syllabus_full.md into nodes and links,
then merges them into the existing d3_graph_data.json file.
It also adds new metadata fields to all existing nodes.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
import uuid


class SyllabusToGraphConverter:
    """Convert RF syllabus markdown to graph nodes and links."""
    
    def __init__(self, syllabus_path: Path):
        self.syllabus_path = syllabus_path
        self.nodes = []
        self.links = []
        
    def parse_syllabus(self) -> Tuple[List[Dict], List[Dict]]:
        """Parse the syllabus markdown file and extract nodes and links."""
        
        with open(self.syllabus_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create root node
        root_node = {
            "id": "syllabus-root",
            "name": "Radio (RF) and Microwave Engineering Course",
            "description": "Complete 136-hour professional RF engineering training course from Interlligent RF Training Center, covering theoretical topics (100 hours) and practical laboratories (36 hours).",
            "source": "rf_syllabus_interlligent",
            "category": "course",
            "hours": 136,
            "topic_number": None,
            "subtopic_number": None,
            "professional_foundation": None,
            "urls": []
        }
        self.nodes.append(root_node)
        
        # Create theoretical section node
        theoretical_node = {
            "id": "syllabus-theoretical",
            "name": "Theoretical Topics",
            "description": "100 hours of theoretical study covering 16 major topics in RF and microwave engineering.",
            "source": "rf_syllabus_interlligent",
            "category": "theoretical_section",
            "hours": 100,
            "topic_number": None,
            "subtopic_number": None,
            "professional_foundation": None,
            "urls": []
        }
        self.nodes.append(theoretical_node)
        self.links.append({
            "source": "syllabus-root",
            "target": "syllabus-theoretical",
            "type": "sub topic"
        })
        
        # Parse theoretical topics
        self._parse_theoretical_topics(content)
        
        # Create labs section node
        labs_node = {
            "id": "syllabus-labs",
            "name": "Practical Laboratories",
            "description": "36 hours of hands-on laboratory work across 9 lab sessions covering practical RF measurements and design.",
            "source": "rf_syllabus_interlligent",
            "category": "laboratory_section",
            "hours": 36,
            "topic_number": None,
            "subtopic_number": None,
            "professional_foundation": None,
            "urls": []
        }
        self.nodes.append(labs_node)
        self.links.append({
            "source": "syllabus-root",
            "target": "syllabus-labs",
            "type": "sub topic"
        })
        
        # Parse labs
        self._parse_labs(content)
        
        return self.nodes, self.links
    
    def _parse_theoretical_topics(self, content: str):
        """Parse theoretical topics section."""
        
        # Extract theoretical section
        theoretical_match = re.search(r'## 📚 Theoretical Topics.*?(?=---|\Z)', content, re.DOTALL)
        if not theoretical_match:
            return
        
        theoretical_section = theoretical_match.group(0)
        
        # Find all main topics (### Topic X -)
        topic_pattern = r'### Topic (\d+) - (.+?)\((\d+) theoretical study hours\)'
        topic_matches = list(re.finditer(topic_pattern, theoretical_section))
        
        for i, topic_match in enumerate(topic_matches):
            topic_num = int(topic_match.group(1))
            topic_title = topic_match.group(2).strip()
            hours = topic_match.group(3)
            
            # Find the end of this topic (start of next topic or end of section)
            start_pos = topic_match.end()
            if i + 1 < len(topic_matches):
                end_pos = topic_matches[i + 1].start()
            else:
                end_pos = len(theoretical_section)
            
            topic_content = theoretical_section[start_pos:end_pos]
            
            # Create main topic node
            topic_id = f"syllabus-{topic_num}"
            topic_node = {
                "id": topic_id,
                "name": topic_title,
                "description": f"Topic {topic_num}: {topic_title} ({hours} study hours)",
                "source": "rf_syllabus_interlligent",
                "category": "theoretical",
                "hours": int(hours),
                "topic_number": topic_num,
                "subtopic_number": None,
                "professional_foundation": None,
                "urls": []
            }
            self.nodes.append(topic_node)
            
            # Link to theoretical section
            self.links.append({
                "source": "syllabus-theoretical",
                "target": topic_id,
                "type": "sub topic"
            })
            
            # Parse subtopics
            self._parse_subtopics(topic_content, topic_num, topic_id)
    
    def _parse_subtopics(self, topic_content: str, topic_num: int, parent_id: str):
        """Parse subtopics within a topic."""
        
        # Find all subtopics (#### X.Y Title)
        subtopic_pattern = r'#### (\d+)\.(\d+) (.+?)$'
        subtopic_matches = list(re.finditer(subtopic_pattern, topic_content, re.MULTILINE))
        
        for i, subtopic_match in enumerate(subtopic_matches):
            main_num = int(subtopic_match.group(1))
            sub_num = int(subtopic_match.group(2))
            subtopic_title = subtopic_match.group(3).strip()
            
            # Find the end of this subtopic
            start_pos = subtopic_match.end()
            if i + 1 < len(subtopic_matches):
                end_pos = subtopic_matches[i + 1].start()
            else:
                # Find next section marker or end
                next_section = re.search(r'\n### ', topic_content[start_pos:])
                if next_section:
                    end_pos = start_pos + next_section.start()
                else:
                    end_pos = len(topic_content)
            
            subtopic_content = topic_content[start_pos:end_pos].strip()
            
            # Extract bullet points and convert to description
            description = self._extract_bullet_description(subtopic_content, subtopic_title)
            
            # Check for professional foundation formulas
            prof_foundation = self._extract_professional_foundation(subtopic_content)
            
            # Create subtopic node
            subtopic_id = f"syllabus-{main_num}.{sub_num}"
            subtopic_node = {
                "id": subtopic_id,
                "name": subtopic_title,
                "description": description,
                "source": "rf_syllabus_interlligent",
                "category": "theoretical",
                "hours": None,
                "topic_number": main_num,
                "subtopic_number": f"{main_num}.{sub_num}",
                "professional_foundation": prof_foundation,
                "urls": []
            }
            self.nodes.append(subtopic_node)
            
            # Link to parent topic
            self.links.append({
                "source": parent_id,
                "target": subtopic_id,
                "type": "sub topic"
            })
    
    def _extract_bullet_description(self, content: str, title: str) -> str:
        """Convert bullet points to flowing paragraph description."""
        
        lines = content.split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                # Remove bullet marker
                bullet_text = line[2:].strip()
                bullets.append(bullet_text)
        
        if bullets:
            # Join bullets into paragraph
            description = ' '.join(bullets)
            # Limit length
            if len(description) > 2000:
                description = description[:1997] + "..."
            return description
        else:
            return f"{title}: Detailed study of this topic."
    
    def _extract_professional_foundation(self, content: str) -> str:
        """Extract professional foundation formula references."""
        
        # Look for patterns like "Professional Foundation No. X"
        match = re.search(r'"Professional Foundation(?:\s+Formula)?\s+No\.\s*(\d+)"[:\s]+([^.]+\.)', content)
        if match:
            num = match.group(1)
            desc = match.group(2).strip()
            return f"No. {num}: {desc}"
        return None
    
    def _parse_labs(self, content: str):
        """Parse laboratory section."""
        
        # Extract labs section
        labs_match = re.search(r'## 🔬 Practical Laboratories.*?(?=---|\Z)', content, re.DOTALL)
        if not labs_match:
            return
        
        labs_section = labs_match.group(0)
        
        # Find all labs (### Lab X -)
        lab_pattern = r'### Lab (\d+) - (.+?)\((\d+) hours?\)'
        lab_matches = list(re.finditer(lab_pattern, labs_section))
        
        for i, lab_match in enumerate(lab_matches):
            lab_num = int(lab_match.group(1))
            lab_title = lab_match.group(2).strip()
            hours = lab_match.group(3)
            
            # Find the end of this lab
            start_pos = lab_match.end()
            if i + 1 < len(lab_matches):
                end_pos = lab_matches[i + 1].start()
            else:
                end_pos = len(labs_section)
            
            lab_content = labs_section[start_pos:end_pos]
            
            # Extract topics covered
            topics_match = re.search(r'\*\*Topics Covered:\*\*\s*(.+?)(?:\n|$)', lab_content)
            topics_covered = topics_match.group(1).strip() if topics_match else ""
            
            # Create description
            description = f"Lab {lab_num}: {lab_title}. {topics_covered}" if topics_covered else f"Lab {lab_num}: {lab_title}"
            
            # Create lab node
            lab_id = f"syllabus-lab-{lab_num}"
            lab_node = {
                "id": lab_id,
                "name": lab_title,
                "description": description,
                "source": "rf_syllabus_interlligent",
                "category": "laboratory",
                "hours": int(hours),
                "topic_number": None,
                "subtopic_number": None,
                "professional_foundation": None,
                "urls": []
            }
            self.nodes.append(lab_node)
            
            # Link to labs section
            self.links.append({
                "source": "syllabus-labs",
                "target": lab_id,
                "type": "sub topic"
            })


def add_metadata_to_existing_nodes(nodes: List[Dict]) -> List[Dict]:
    """Add new metadata fields to all existing nodes."""
    
    for node in nodes:
        # Only add fields if they don't exist
        if 'source' not in node:
            node['source'] = 'original_dataset'
        if 'category' not in node:
            node['category'] = 'concept'
        if 'hours' not in node:
            node['hours'] = None
        if 'topic_number' not in node:
            node['topic_number'] = None
        if 'subtopic_number' not in node:
            node['subtopic_number'] = None
        if 'professional_foundation' not in node:
            node['professional_foundation'] = None
    
    return nodes


def merge_graphs(existing_graph: Dict, new_nodes: List[Dict], new_links: List[Dict]) -> Dict:
    """Merge new syllabus nodes and links into existing graph."""
    
    print(f"\n{'='*60}")
    print("MERGING SYLLABUS INTO GRAPH")
    print(f"{'='*60}")
    
    # Add metadata to existing nodes
    print(f"\nAdding metadata fields to {len(existing_graph['nodes'])} existing nodes...")
    existing_graph['nodes'] = add_metadata_to_existing_nodes(existing_graph['nodes'])
    
    # Get existing node IDs to check for duplicates
    existing_ids = {node['id'] for node in existing_graph['nodes']}
    
    # Add new nodes (skip duplicates)
    added_nodes = 0
    for node in new_nodes:
        if node['id'] not in existing_ids:
            existing_graph['nodes'].append(node)
            added_nodes += 1
        else:
            print(f"Warning: Skipping duplicate node ID: {node['id']}")
    
    print(f"Added {added_nodes} new syllabus nodes")
    
    # Add new links
    existing_graph['links'].extend(new_links)
    print(f"Added {len(new_links)} new syllabus links")
    
    print(f"\nFinal graph statistics:")
    print(f"  Total nodes: {len(existing_graph['nodes'])}")
    print(f"  Total links: {len(existing_graph['links'])}")
    
    return existing_graph


def main():
    """Main execution function."""
    
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data'
    
    syllabus_file = data_dir / 'RF_syllabus_full.md'
    graph_file = data_dir / 'd3_graph_data.json'
    output_file = data_dir / 'd3_graph_data_with_syllabus.json'
    
    print("="*60)
    print("RF SYLLABUS TO GRAPH MERGER")
    print("="*60)
    
    # Check input files exist
    if not syllabus_file.exists():
        print(f"Error: Syllabus file not found: {syllabus_file}")
        return
    
    if not graph_file.exists():
        print(f"Error: Graph file not found: {graph_file}")
        return
    
    # Load existing graph
    print(f"\nLoading existing graph from: {graph_file}")
    with open(graph_file, 'r', encoding='utf-8') as f:
        existing_graph = json.load(f)
    
    print(f"  Loaded {len(existing_graph['nodes'])} nodes")
    print(f"  Loaded {len(existing_graph['links'])} links")
    
    # Parse syllabus
    print(f"\nParsing syllabus from: {syllabus_file}")
    converter = SyllabusToGraphConverter(syllabus_file)
    syllabus_nodes, syllabus_links = converter.parse_syllabus()
    
    print(f"  Extracted {len(syllabus_nodes)} syllabus nodes")
    print(f"  Generated {len(syllabus_links)} syllabus links")
    
    # Show node breakdown
    categories = {}
    for node in syllabus_nodes:
        cat = node.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\nSyllabus node breakdown by category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    
    # Merge graphs
    merged_graph = merge_graphs(existing_graph, syllabus_nodes, syllabus_links)
    
    # Save merged graph
    print(f"\nSaving merged graph to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_graph, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ SUCCESS!")
    print(f"\nMerged graph saved to: {output_file}")
    print(f"\nTo use the new graph, replace d3_graph_data.json with this file:")
    print(f"  copy \"{output_file}\" \"{graph_file}\"")


if __name__ == '__main__':
    main()
