# RF Mind Map Visualizer

An **interactive web-based visualization tool** for exploring structured knowledge in **RF communications** and related engineering domains.
It renders a **mind map** from CSV datasets describing topics, their relationships, and associated multimedia resources (e.g., YouTube links).

---

## 🚀 Features

* **Dynamic Mind Map Visualization**
  Built with [D3.js](https://d3js.org/), the app displays interconnected RF topics as an explorable graph.

* **Contextual Details Panel**
  Clicking a topic or relationship opens a side panel showing:

  * Descriptions and key concepts
  * Related topics and their relation types
  * Linked YouTube resources with thumbnails

* **Data-Driven Structure**
  Topics, links, and URLs are loaded directly from CSV files located in the `data/` directory.

* **Offline & Client-Side**
  Entirely browser-based — no backend required.
  Data editing (e.g., adding URLs) is done by re-generating and downloading updated CSVs.

---

## 📂 Project Structure

```
.github/
  copilot-instructions.md      # AI assistant code conventions

data/
  topics.csv                   # List of topics and subtopics
  links.csv                    # Relationships between topics
  urls.csv                     # URLs associated with topics
  yt-playlists.url             # YouTube playlists to crawl

scripts/
  calculate_tokens.py          # Token estimator for Gemini AI context
  check_models.py              # Lists Gemini models supporting content generation
  check_limits.py              # Prints available models’ context limits
  enrich_urls.py               # Matches topics to YouTube videos using Gemini AI

src/
  index.html                   # Main application HTML (with inline CSS)
  main.js                      # D3.js logic and UI interaction code

.env.example                   # Example environment file (YouTube + Gemini API keys)
.gitignore                     # Git ignore rules
requirements.txt               # Python dependencies
todo.txt                       # Developer task notes
```

---

## 🧠 How It Works

1. **Data Preparation**

   * `topics.csv`: hierarchical list of RF topics
   * `links.csv`: defines cross-topic relations (e.g., *depends on*, *extends*)
   * `urls.csv`: connects topics/links to videos or web resources

2. **Visualization**

   * Open `src/index.html` in a browser
   * The app loads data from `/data/`
   * Interactive D3.js graph is generated dynamically

3. **URL Enrichment (Optional)**

   * `scripts/enrich_urls.py` uses **Gemini AI** + **YouTube Data API**
   * It reads YouTube playlists and matches videos to topics automatically
   * Generates/updates `urls.csv` with best-matching resources

---

## ⚙️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<yourusername>/rf-mindmap.git
cd rf-mindmap
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file (based on `.env.example`) and add:

```
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run Scripts (Optional)

* **Check Model Limits**

  ```bash
  python scripts/check_limits.py
  ```
* **Estimate Token Usage**

  ```bash
  python scripts/calculate_tokens.py
  ```
* **Enrich URLs Automatically**

  ```bash
  python scripts/enrich_urls.py
  ```

---

## 🌐 Using the Visualizer

1. Open `src/index.html` in your browser.
2. Explore the mind map — click on nodes or links to view details.
3. Modify data files in `/data/` to expand or update the graph.
4. Use the “Save & Download urls.csv” button to export updated data.

---

## 🧩 Data File Formats

| File               | Description                             |
| ------------------ | --------------------------------------- |
| `topics.csv`       | Topic index, title, and description     |
| `links.csv`        | Relationships between topics            |
| `urls.csv`         | URLs mapped to topics or links          |
| `yt-playlists.url` | List of playlists for enrichment script |

---

## 🛠️ Technologies

* **Frontend:** D3.js (v7), HTML5, CSS3
* **Backend Scripts:** Python 3.x
* **APIs:** YouTube Data API, Google Gemini AI
* **Data Format:** CSV

---

## 🧑‍💻 Development Notes

See `.github/copilot-instructions.md` for code conventions and AI assistant guidance.
This ensures generated code remains clean, modular, and compatible with the project’s structure.

---

## 📜 License

This project is released under the **No License**.
Feel free to use, modify, and adapt it for educational or visualization purposes.

this project was made using Google AI studio 