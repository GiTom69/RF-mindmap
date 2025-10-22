# copilot-instructions.md

This file provides guidance for AI code assistants like GitHub Copilot to ensure consistency in style, conventions, and overall approach for this project.

## Purpose & Scope

This project is an interactive, web-based mind map visualizer. Its primary purpose is to render structured data from CSV files into a dynamic, explorable graph. The user interacts with the graph to view relationships, descriptions, and associated resources (URLs).

**Key Coding Domains:**
- **Data Visualization:** The core of the project is rendering and manipulating a graph using D3.js.
- **Front-End Web Development:** The application is built with vanilla JavaScript, HTML, and CSS. No front-end frameworks are used.
- **UI/UX Design:** Focus on creating an intuitive user interface for graph exploration, including interactive panels, buttons, and visual feedback.
- **Data Processing:** The application parses and links data from multiple CSV files.

The initial data set provided by the user relates to **RF Communications concepts**, but the tool itself is a general-purpose visualizer.

## Coding Style & Conventions

**Languages & Libraries:**
- **JavaScript:** Use modern vanilla JavaScript (ES6+), including `const`/`let`, arrow functions, and Promises (`Promise.all`).
- **D3.js:** This is the primary and only major library. Use D3 version 7 conventions.
- **HTML5 & CSS3:** All markup and styling are contained within a single `index.html` file. CSS is placed in a `<style>` block in the `<head>`.

**File & Code Structure:**
- The project is structured in a simple hierarchy:
  - `index.html`: The main entry point, containing all HTML and CSS.
  - `js/main.js`: Contains all JavaScript application logic.
  - `data/`: A directory containing all data sources (`topics.csv`, `links.csv`, `urls.csv`).
- All JavaScript code in `main.js` must be wrapped within a `document.addEventListener("DOMContentLoaded", () => { ... });` block.
- Use clear, commented section headers to structure the code, for example: `// --- Data Loading ---` or `// --- D3 & UI Interaction ---`.
- Create well-named, single-purpose functions (e.g., `createD3Graph`, `focusOnNode`, `showUrlManager`).

**Naming Conventions:**
- **JavaScript:** Use `camelCase` for variables and functions (`currentGraphData`, `getNodeStyle`).
- **CSS / HTML:** Use `kebab-case` for all IDs and class names (`mind-map-container`, `related-topic-button`).
- **D3 Selections:** Use descriptive, simple variable names for D3 selections (`svg`, `node`, `link`).

**Comments:**
- Prefer section headers over frequent inline comments.
- Inline comments should only be used to explain non-obvious logic or "magic numbers".

## AI Guidance

**Response Format:**
- When adding a new feature, provide the complete, updated code for any modified files (`index.html` or `main.js`). This is the user's preferred interaction style.
- Briefly explain what was changed and why, especially when introducing new functions or complex logic.
- When generating code, prioritize **readability, clarity, and modularity**. The user often builds on previous features, so clean, understandable code is more important than micro-optimizations.

**Context & Ambiguity:**
- If a request is ambiguous, make a reasonable assumption based on the existing UI and functionality, but state the assumption clearly in your explanation.
- The user builds features incrementally. Suggestions should respect and integrate with the existing code structure, not replace it entirely unless requested.

**Examples & Explanations:**
- Generate code that is immediately usable within the project.
- Explanations should be technical and concise. Avoid lengthy conversational introductions or summaries.

## Project-Specific Notes

This project revolves around a few key concepts and UI components. AI suggestions should be aware of them:

- **Core Data Entities:**
  - **Nodes:** From `topics.csv`. Each has an `id`, `title`, and `description`. Their visual style (size, outline) is based on the depth of their `id` (e.g., `1` vs. `1.1` vs. `1.1.1`).
  - **Links:** From `links.csv` ("dependency") and generated automatically ("hierarchical"). Each connects a `source` and a `target`.
  - **URLs:** From `urls.csv`. These are attached to nodes and links and can include special previews for YouTube videos.

- **Key UI Components:**
  - **The SVG Canvas** (`#mind-map-container`): The main D3.js drawing area.
  - **The Details Panel (`#controls-container`):** A panel on the right that contextually displays information about the selected node or link. This includes descriptions, related topics, and associated resources (URLs).
  - **The Notes Panel (`#notes-section`):** A collapsible "hamburger" menu in the bottom-left that contains a legend for relationship types.

- **Key Features to be Aware of:**
  - **"Jump-to-Node" (`focusOnNode` function):** An important navigation feature that animates the view to center on a selected node and highlights it.
  - **Data Persistence:** The workflow is file-based. URLs are loaded from `data/urls.csv` and saved by generating a new `urls.csv` for the user to download and replace the old one. Do not suggest server-side or automatic file-writing solutions.
  - **Hierarchical Linking:** In addition to links from `links.csv`, the application automatically generates "sub topic" links between parent and child nodes (e.g., from node `1.1` to `1.1.1`).

## Tone & Behavior for AI Assistants

- **Tone:** Be a helpful but precise technical assistant. The user is knowledgeable and wants direct, functional solutions.
- **Markdown:** Use Markdown extensively for formatting, especially for file paths, code blocks, and lists.
- **Output Style:** When providing code, always wrap it in the correct language-tagged Markdown block (e.g., ` ```javascript `).

### Example Prompts

Here are a few examples that reflect the user's interaction style:

**User → AI:** "add a search bar to the controls panel that finds nodes by their title and highlights them."

**User → AI:** "change the hierarchical links to have an arrowhead at the end to show direction."

**User → AI:** "when a node is highlighted by the `focusOnNode` function, also highlight its direct links."