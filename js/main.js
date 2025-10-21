document.addEventListener("DOMContentLoaded", () => {
    // --- Data Loading ---
    Promise.all([
        d3.csv("data/topics.csv"),
        d3.csv("data/links.csv")
    ]).then(([topics, links]) => {
        const graph = createD3Graph(topics, links);
        renderD3MindMap(graph);
    }).catch(error => {
        console.error("Error loading or parsing data:", error);
    });

    // --- Data Transformation ---
    function createD3Graph(topics, links) {
        const nodes = topics.map(topic => ({
            id: topic.Index,
            title: topic.Topic,
            description: topic['Description / Key Concepts'],
            urls: [] // Initialize with an empty array for custom URLs
        }));

        const d3Links = links.map(link => ({
            source: link['Source Index'],
            target: link['Target Index'],
            relation: link['Relation Type'],
            urls: [] // Initialize for custom URLs
        }));

        return { nodes, links: d3Links };
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
            }));

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
            .attr("class", "link")
            .attr("stroke-width", 2)
            .on("click", (event, d) => {
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
                showUrlManager(d, 'Node');
            });

        node.append("circle")
            .attr("r", 10)
            .attr("fill", "steelblue");

        node.append("text")
            .text(d => d.title)
            .attr("x", 12)
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

    // --- Interactivity ---
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

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    // --- URL Management UI ---
    function showUrlManager(element, type) {
        const urlContainer = document.getElementById('url-manager');
        const title = type === 'Node' ? element.title : `${element.source.title} → ${element.target.title}`;

        urlContainer.innerHTML = `<h3>Resources for ${title}</h3>`;

        const urlList = document.createElement('ul');
        element.urls.forEach((url, index) => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = url;
            a.textContent = url;
            a.target = "_blank";
            li.appendChild(a);
            urlList.appendChild(li);
        });
        urlContainer.appendChild(urlList);

        const addUrlInput = document.createElement('input');
        addUrlInput.type = 'text';
        addUrlInput.id = 'add-url-input';
        addUrlInput.placeholder = 'Add a new URL';

        const addUrlButton = document.createElement('button');
        addUrlButton.id = 'add-url-button';
        addUrlButton.textContent = 'Add';

        addUrlButton.onclick = () => {
            if (addUrlInput.value) {
                try {
                    new URL(addUrlInput.value); // Validate URL
                    element.urls.push(addUrlInput.value);
                    showUrlManager(element, type); // Refresh the display
                } catch (_) {
                    alert("Please enter a valid URL.");
                }
            }
        };

        urlContainer.appendChild(addUrlInput);
        urlContainer.appendChild(addUrlButton);
    }
});