"""
Convert RF Syllabus Text to Structured Markdown

This script converts the RF syllabus pages text file into a hierarchical
Markdown structure suitable for the RF mindmap project.
"""

import re
from pathlib import Path


def parse_syllabus_text(text_content):
    """Parse the syllabus text and extract structured content."""
    
    # Split by page markers
    pages = text_content.split('--- PAGE')
    
    # Initialize structure
    structure = {
        'title': 'Radio (RF) and Microwave Engineering (136 study hours)',
        'sections': []
    }
    
    # Find the theoretical topics index (page 11)
    topics_section = None
    labs_section = None
    
    for page in pages:
        if 'Index of Theoretical Topics Taught in the Course' in page:
            topics_section = page
        elif 'Index of Practical Laboratories Taught in the Course' in page:
            labs_section = page
    
    return structure, topics_section, labs_section


def extract_topics_from_index(topics_text):
    """Extract topic information from the theoretical topics index."""
    topics = []
    
    # Pattern to match topic lines like: "1, Introduction and Foundations..., 5"
    # More flexible pattern to handle various formats
    lines = topics_text.split('\n')
    
    for line in lines:
        # Skip header and empty lines
        if not line.strip() or 'Topic No.' in line or 'Total Theory' in line:
            continue
        
        # Try to match topic format: number, title, hours
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) >= 3:
            try:
                topic_num = parts[0].strip()
                topic_title = ','.join(parts[1:-1]).strip()  # Handle titles with commas
                hours = parts[-1].strip()
                
                if topic_num.isdigit():
                    topics.append({
                        'number': int(topic_num),
                        'title': topic_title,
                        'hours': hours
                    })
            except (ValueError, IndexError):
                continue
    
    return topics


def extract_labs_from_index(labs_text):
    """Extract lab information from the practical laboratories index."""
    labs = []
    
    lines = labs_text.split('\n')
    
    for line in lines:
        # Skip header and empty lines
        if not line.strip() or 'Lab No.' in line:
            continue
        
        # Try to match lab format: number, title, hours, topics
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) >= 3:
            try:
                lab_num = parts[0].strip()
                lab_title = parts[1].strip()
                hours = parts[2].strip()
                topics = ','.join(parts[3:]).strip() if len(parts) > 3 else ''
                
                if lab_num.isdigit():
                    labs.append({
                        'number': int(lab_num),
                        'title': lab_title,
                        'hours': hours,
                        'topics': topics
                    })
            except (ValueError, IndexError):
                continue
    
    return labs


def extract_detailed_topics(text_content):
    """Extract detailed topic content from pages 13+."""
    detailed_topics = {}
    
    # Split by pages
    pages = text_content.split('--- PAGE')
    
    current_topic = None
    current_subtopic = None
    current_content = []
    
    for page in pages:
        lines = page.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Match main topic headers like "Topic 1 -" or "1.1 Introduction"
            topic_match = re.match(r'^Topic\s+(\d+)\s*[-–]\s*(.+?)(?:\s*\(.*?\))?$', line)
            if topic_match:
                # Save previous topic if exists
                if current_topic:
                    if current_topic not in detailed_topics:
                        detailed_topics[current_topic] = {}
                    if current_subtopic:
                        detailed_topics[current_topic][current_subtopic] = current_content
                
                current_topic = int(topic_match.group(1))
                current_subtopic = None
                current_content = []
                continue
            
            # Match subtopic headers like "1.1 Introduction to..." or "2.1 Introduction to..."
            subtopic_match = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
            if subtopic_match and current_topic:
                # Save previous subtopic if exists
                if current_subtopic:
                    if current_topic not in detailed_topics:
                        detailed_topics[current_topic] = {}
                    detailed_topics[current_topic][current_subtopic] = current_content
                
                current_subtopic = f"{subtopic_match.group(1)}.{subtopic_match.group(2)} {subtopic_match.group(3)}"
                current_content = []
                continue
            
            # Collect content lines (bullets, sub-bullets)
            if line and current_topic and current_subtopic:
                # Check if it's a bullet point
                if line.startswith('*') or line.startswith('-') or line.startswith('•'):
                    current_content.append(line)
                elif re.match(r'^\s+[*-•]', line):
                    current_content.append(line)
    
    # Save last topic
    if current_topic and current_subtopic:
        if current_topic not in detailed_topics:
            detailed_topics[current_topic] = {}
        detailed_topics[current_topic][current_subtopic] = current_content
    
    return detailed_topics


def generate_markdown(structure, topics, labs, detailed_topics, source_file):
    """Generate the final Markdown output."""
    
    md_lines = []
    
    # Header
    md_lines.append(f"# {structure['title']}\n")
    md_lines.append("*Structured course syllabus extracted from Interlligent RF Training Center*\n")
    md_lines.append("---\n")
    
    # Theoretical Topics Section
    md_lines.append("## 📚 Theoretical Topics (100 hours)\n")
    
    for topic in topics:
        topic_num = topic['number']
        topic_title = topic['title']
        hours = topic['hours']
        
        md_lines.append(f"### Topic {topic_num} - {topic_title} ({hours} theoretical study hours)\n")
        
        # Add detailed subtopics if available
        if topic_num in detailed_topics:
            for subtopic_title, content_lines in detailed_topics[topic_num].items():
                md_lines.append(f"#### {subtopic_title}\n")
                
                for content_line in content_lines:
                    md_lines.append(f"{content_line}\n")
                
                md_lines.append("")  # Empty line after subtopic
        
        md_lines.append("")  # Empty line after topic
    
    # Practical Laboratories Section
    md_lines.append("---\n")
    md_lines.append("## 🔬 Practical Laboratories (36 hours)\n")
    
    for lab in labs:
        lab_num = lab['number']
        lab_title = lab['title']
        hours = lab['hours']
        topics_covered = lab['topics']
        
        md_lines.append(f"### Lab {lab_num} - {lab_title} ({hours} hours)\n")
        
        if topics_covered:
            md_lines.append(f"**Topics Covered:** {topics_covered}\n")
        
        md_lines.append("")  # Empty line after lab
    
    # Footer
    md_lines.append("---\n")
    md_lines.append(f"*Generated from: {source_file}*\n")
    
    return '\n'.join(md_lines)


def main():
    """Main conversion function."""
    
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data'
    
    input_file = data_dir / 'RF silvus pages.txt'
    output_file = data_dir / 'RF_syllabus_full.md'
    
    print(f"Reading input file: {input_file}")
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        return
    
    print("Parsing syllabus content...")
    
    # Parse the content
    structure, topics_section, labs_section = parse_syllabus_text(text_content)
    
    # Extract topics and labs from indices
    topics = []
    labs = []
    
    if topics_section:
        topics = extract_topics_from_index(topics_section)
        print(f"Extracted {len(topics)} topics")
    
    if labs_section:
        labs = extract_labs_from_index(labs_section)
        print(f"Extracted {len(labs)} labs")
    
    # Extract detailed topic content
    detailed_topics = extract_detailed_topics(text_content)
    print(f"Extracted detailed content for {len(detailed_topics)} topics")
    
    # Generate Markdown
    print("Generating Markdown output...")
    markdown_content = generate_markdown(
        structure, 
        topics, 
        labs, 
        detailed_topics,
        input_file.name
    )
    
    # Write output
    print(f"Writing output file: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"✅ Conversion complete! Output saved to: {output_file}")
    print(f"   - {len(topics)} theoretical topics")
    print(f"   - {len(labs)} practical labs")
    print(f"   - Total lines: {len(markdown_content.splitlines())}")


if __name__ == '__main__':
    main()
