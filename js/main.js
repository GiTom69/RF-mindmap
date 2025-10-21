document.addEventListener("DOMContentLoaded", () => {
    const controlsContainer = document.getElementById('controls-container');
    const initialControlsHTML = controlsContainer.innerHTML;

    // --- Data Loading ---
    Promise.all([
        d3.csv("data/topics.csv"),
        d3.csv("data/links.csv")
    ]).then(([topics, links]) => {
        const validTopics = topics.filter(t => t.Index && t.Index.trim() !== '');
        const validLinks = links.filter(l => l['Source Index'] && l['Target Index']);

        const graph = createD3Graph(validTopics, validLinks);
        renderD3MindMap(graph);
    }).catch(error => {
        console.error("Error loading or parsing data:", error);
    });

    // --- MODIFIED: Data Transformation ---
    function createD3Graph(topics, links) {
        const nodes = topics.map(topic => ({
            id: topic.Index,
            title: topic.Topic,
            description: topic['Description / Key Concepts'],
            urls: []
        }));

        // Process explicit links from links.csv
        const dependencyLinks = links.map(link => ({
            source: link['Source Index'],
            target: link['Target Index'],
            relation: link['Relation Type'],
            type: 'dependency', // Assign a type for styling
            urls: []
        }));
        
        // --- NEW: Generate hierarchical links automatically ---
        const hierarchicalLinks = [];
        const nodeIdSet = new Set(nodes.map(n => n.id));

        nodes.forEach(node => {
            const parts = node.id.toString().split('.');
            if (parts.length > 1) {
                // Find the parent ID by removing the last part (e.g., "1.1.1" -> "1.1")
                const parentId = parts.slice(0, -1).join('.');
                // If the parent node actually exists, create a link
                if (nodeIdSet.has(parentId)) {
                    hierarchicalLinks.push({
                        source: parentId,
                        target: node.id,
                        relation: 'parent-child',
                        type: 'hierarchical' // Assign a type for styling
                    });
                }
            }
        });

        // Combine both types of links
        const allLinks = [...dependencyLinks, ...hierarchicalLinks];

        return { nodes, links: allLinks };
    }

    // --- NEW: Function to determine node style based on index depth ---
    function getNodeStyle(nodeId) {
        const level = nodeId.toString().split('.').length;
        switch (level) {
            case 1:
                return { radius: 20, stroke: 'black', strokeWidth: 2 };
            case 2:
                return { radius: 15, stroke: 'none', strokeWidth: 0 };
            default:
                return { radius: 10, stroke: 'none', strokeWidth: 0 };
        }
    }

    // --- D3.js Rendering ---
    function renderD3MindMap(graph) {
        const container = document.getElementById('mind-map-container');
        const width = container.clientWidth;
        const height = container.clientHeight;

        const svg = d3.select("#mind-map-container").append("svg")
            .attr("width", width)
            .attr("height", height)
            .call(d3.zoom().on("zoom", (event) => {
                g.attr("transform", event.transform);
            }))
            .on("click", resetControlsPanel);

        const g = svg.append("g");

        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.links).id(d => d.id).distance(120))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2));

        const link = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(graph.links)
            .join("line")
            // --- MODIFIED: Apply class based on link type ---
            .attr("class", d => `link ${d.type}`)
            .attr("stroke-width", 2)
            .on("click", (event, d) => {
                event.stopPropagation();
                showUrlManager(d, 'Link');
            });

        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(graph.nodes)
            .join("g")
            .attr("class", "node")
            .call(drag(simulation))
            .on("click", (event, d) => {
                event.stopPropagation();
                showUrlManager(d, 'Node');
            });
        
        node.append("circle")
            .attr("r", d => getNodeStyle(d.id).radius)
            .attr("fill", "steelblue")
            .attr("stroke", d => getNodeStyle(d.id).stroke)
            .attr("stroke-width", d => getNodeStyle(d.id).strokeWidth);

        node.append("text")
            .text(d => d.title)
            .attr("x", d => getNodeStyle(d.id).radius + 5)
            .attr("y", 3);

        node.append("title")
            .text(d => d.description);

        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("transform", d => `translate(${d.x},${d.y})`);
        });
    }

    // --- Interactivity (Unchanged) ---
    function drag(simulation) {
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
    }

    function resetControlsPanel() {
        controlsContainer.innerHTML = initialControlsHTML;
    }

    function showUrlManager(element, type) {
        controlsContainer.innerHTML = '';
        const title = type === 'Node' ? element.title : `${element.source.title} → ${element.target.title}`;
        const h3 = document.createElement('h3');
        h3.textContent = `Resources for ${title}`;
        controlsContainer.appendChild(h3);
        const urlList = document.createElement('ul');
        if (element.urls) { // Check if urls array exists
            element.urls.forEach((url) => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = url;
                a.textContent = url;
                a.target = "_blank";
                li.appendChild(a);
                urlList.appendChild(li);
            });
        }
        controlsContainer.appendChild(urlList);
        const addUrlInput = document.createElement('input');
        addUrlInput.type = 'text';
        addUrlInput.id = 'add-url-input';
        addUrlInput.placeholder = 'Add a new URL';
        controlsContainer.appendChild(addUrlInput);
        const addUrlButton = document.createElement('button');
        addUrlButton.id = 'add-url-button';
        addUrlButton.textContent = 'Add';
        controlsContainer.appendChild(addUrlButton);
        addUrlButton.onclick = () => {
            if (addUrlInput.value) {
                try {
                    new URL(addUrlInput.value);
                    if (!element.urls) element.urls = []; // Initialize if it doesn't exist
                    element.urls.push(addUrlInput.value);
                    showUrlManager(element, type);
                } catch (_) {
                    alert("Please enter a valid URL.");
                }
            }
        };
    }
});