document.addEventListener("DOMContentLoaded", () => {
    // --- Global Element References & State ---
    const controlsContainer = document.getElementById('controls-container');
    const initialControlsHTML = controlsContainer.innerHTML;
    const saveButton = document.getElementById('save-csv-button');
    const notesSection = document.getElementById('notes-section');
    const notesToggle = document.getElementById('notes-toggle');
    const searchInput = document.getElementById('search-input');
    const suggestionsContainer = document.getElementById('search-suggestions');
    
    let currentGraphData = null;
    let svg, zoom, width, height; // D3 variables for global access

    // --- Initial Event Listeners ---
    notesToggle.addEventListener('click', () => {
        notesSection.classList.toggle('notes-visible');
    });

    saveButton.addEventListener('click', () => {
        if (currentGraphData) {
            saveUrlsToCsv(currentGraphData);
        } else {
            alert("No data available to save.");
        }
    });

    // --- Data Loading & Initialization ---
    // MODIFIED: Load only the single, complete JSON data file.
    d3.json("d3_graph_data.json").then(graphData => {
        // The data is already in the correct format with URLs embedded.
        currentGraphData = graphData; 
        renderD3MindMap(currentGraphData);
        initializeSearch();
    }).catch(error => {
        console.error("Error loading or parsing data:", error);
    });

    // --- Search Functionality ---
    function initializeSearch() {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value;
            if (query.length > 1) {
                const results = fuzzySearch(query, currentGraphData.nodes);
                displaySuggestions(results.slice(0, 10));
            } else {
                clearSuggestions();
            }
        });

        document.addEventListener('click', (event) => {
            if (!document.getElementById('search-container').contains(event.target)) {
                clearSuggestions();
            }
        });
    }
    
    function fuzzySearch(query, nodes) {
        const lowerCaseQuery = query.toLowerCase();
        return nodes.map(node => {
            const lowerCaseTitle = node.name.toLowerCase();
            const score = calculateMatchScore(lowerCaseTitle, lowerCaseQuery);
            return { node, score };
        })
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score);
    }

    function calculateMatchScore(text, query) {
        let score = 0;
        let queryIndex = 0;
        let textIndex = 0;
        
        while (queryIndex < query.length && textIndex < text.length) {
            if (text[textIndex] === query[queryIndex]) {
                score += 1;
                if (queryIndex > 0 && text[textIndex - 1] === query[queryIndex - 1]) {
                    score += 2;
                }
                queryIndex++;
            }
            textIndex++;
        }
        
        if (queryIndex !== query.length) return 0;
        return score / text.length;
    }

    function displaySuggestions(results) {
        clearSuggestions();
        results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = result.node.name;
            item.addEventListener('click', () => {
                focusOnNode(result.node);
                showUrlManager(result.node, 'Node');
                searchInput.value = '';
                clearSuggestions();
            });
            suggestionsContainer.appendChild(item);
        });
    }

    function clearSuggestions() {
        suggestionsContainer.innerHTML = '';
    }

    // REMOVED: The mergeUrlsIntoGraph function is no longer needed.

    // --- Helper Functions ---
    function getLinkId(sourceId, targetId, type) {
        const sId = typeof sourceId === 'object' ? sourceId.id : sourceId;
        const tId = typeof targetId === 'object' ? targetId.id : targetId;
        return `${sId}|${tId}|${type}`;
    }
    
    function saveUrlsToCsv(graph) {
        let csvContent = "Identifier,URL\n";
        const escapeCsv = (str) => `"${(str || '').replace(/"/g, '""')}"`;

        graph.nodes.forEach(node => {
            if (node.urls && node.urls.length > 0) {
                node.urls.forEach(url => {
                    csvContent += `${node.id},${escapeCsv(url)}\n`;
                });
            }
        });
        graph.links.forEach(link => {
            if (link.urls && link.urls.length > 0) {
                const linkId = getLinkId(link.source, link.target, link.type);
                 link.urls.forEach(url => {
                    csvContent += `${linkId},${escapeCsv(url)}\n`;
                });
            }
        });
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const downloadLink = document.createElement("a");
        const url = URL.createObjectURL(blob);
        downloadLink.setAttribute("href", url);
        downloadLink.setAttribute("download", "urls.csv");
        downloadLink.style.visibility = 'hidden';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }

    function getYoutubeVideoId(url) {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
        const match = url.match(regExp);
        return (match && match[2].length === 11) ? match[2] : null;
    }

    function getYoutubeThumbnailUrl(videoId) {
        return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
    }

    async function fetchYoutubeMetadata(videoUrl) {
        const response = await fetch(`https://noembed.com/embed?url=${encodeURIComponent(videoUrl)}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch metadata for ${videoUrl}`);
        }
        return await response.json();
    }

    function getNodeStyle(nodeId) {
        const level = nodeId.toString().split('.').length;
        switch (level) {
            case 1: return { radius: 20, stroke: 'black', strokeWidth: 2 };
            case 2: return { radius: 15, stroke: 'none', strokeWidth: 0 };
            default: return { radius: 10, stroke: 'none', strokeWidth: 0 };
        }
    }

    // --- D3 & UI Interaction ---
    function focusOnNode(targetNode) {
        if (!targetNode.x || !targetNode.y) {
            console.warn("focusOnNode called on a node without coordinates.", targetNode);
            return;
        }
        const safeId = targetNode.id.toString().replace(/\./g, '-');
        const nodeElement = d3.select(`.node-id-${safeId}`);
        if (nodeElement.empty()) return;

        const scale = 1.5;
        const transform = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(scale)
            .translate(-targetNode.x, -targetNode.y);

        svg.transition().duration(750).call(zoom.transform, transform);

        const circle = nodeElement.select('circle');
        circle.transition().duration(300)
            .attr("fill", "#ffcc00")
            .attr("r", getNodeStyle(targetNode.id).radius + 5)
            .transition().duration(1000)
            .attr("fill", "steelblue")
            .attr("r", getNodeStyle(targetNode.id).radius);
    }

    function renderD3MindMap(graph) {
        const container = document.getElementById('mind-map-container');
        width = container.clientWidth;
        height = container.clientHeight;

        zoom = d3.zoom().on("zoom", (event) => g.attr("transform", event.transform));

        svg = d3.select("#mind-map-container").append("svg")
            .attr("width", width)
            .attr("height", height)
            .call(zoom)
            .on("click", (event) => {
                if (!document.getElementById('search-container').contains(event.target)) {
                    resetControlsPanel();
                }
            });
        
        const g = svg.append("g");
        
        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.links).id(d => d.id).distance(200))
            .force("charge", d3.forceManyBody().strength(-800))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide().radius(d => getNodeStyle(d.id).radius + 60));

        const link = g.append("g").attr("class", "links").selectAll("line").data(graph.links)
            .join("line")
            .attr("class", "link")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", d => (d.type === 'sub topic' ? null : "5,5"))
            .on("click", (event, d) => { event.stopPropagation(); showUrlManager(d, 'Link'); });

        const node = g.append("g").attr("class", "nodes").selectAll("g").data(graph.nodes)
            .join("g").attr("class", d => `node node-id-${d.id.toString().replace(/\./g, '-')}`)
            .call(drag(simulation))
            .on("click", (event, d) => { event.stopPropagation(); showUrlManager(d, 'Node'); });

        node.append("circle")
            .attr("r", d => getNodeStyle(d.id).radius)
            .attr("fill", "steelblue")
            .attr("stroke", d => getNodeStyle(d.id).stroke)
            .attr("stroke-width", d => getNodeStyle(d.id).strokeWidth);

        node.append("text").text(d => d.name).attr("x", d => getNodeStyle(d.id).radius + 5).attr("y", 3);
        node.append("title").text(d => d.description);

        simulation.on("tick", () => {
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    }

    function drag(simulation) {
        function dragstarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
        function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
        function dragended(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }
        return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
    }

    function resetControlsPanel() {
        controlsContainer.innerHTML = initialControlsHTML;
        document.getElementById('save-csv-button').addEventListener('click', () => {
            if (currentGraphData) saveUrlsToCsv(currentGraphData); else alert("No data available to save.");
        });
    }

    function showUrlManager(element, type) {
        controlsContainer.innerHTML = '';
        
        let title;
        if (type === 'Node') {
            title = element.name;
        } else {
            title = `${element.source.name} <span style="color: #a0e0ff; font-weight: normal;">[${element.type}]</span> ${element.target.name}`;
        }
        
        const h3 = document.createElement('h3');
        h3.innerHTML = `Details for ${title}`;
        controlsContainer.appendChild(h3);

        if (type === 'Node' && element.description) {
            const descriptionP = document.createElement('p');
            descriptionP.className = 'node-description';
            descriptionP.textContent = element.description;
            controlsContainer.appendChild(descriptionP);
        }

        if (type === 'Node') {
            const relatedSectionTitle = document.createElement('h4');
            relatedSectionTitle.textContent = 'Related Topics';
            relatedSectionTitle.style.borderBottom = '1px solid #666';
            relatedSectionTitle.style.paddingBottom = '5px';
            controlsContainer.appendChild(relatedSectionTitle);

            const relatedList = document.createElement('ul');
            relatedList.className = 'related-topics-list';
            const connectedLinks = currentGraphData.links.filter(link => link.source.id === element.id || link.target.id === element.id);

            if (connectedLinks.length > 0) {
                connectedLinks.forEach(link => {
                    const isSource = link.source.id === element.id;
                    const otherNode = isSource ? link.target : link.source;
                    const li = document.createElement('li');
                    const button = document.createElement('button');
                    button.className = 'related-topic-button';
                    button.innerHTML = isSource ? `<span class="relation">[${link.type}] →</span> ${otherNode.name}` : `<span class="relation">← [${link.type}]</span> ${otherNode.name}`;
                    button.onclick = () => {
                        focusOnNode(otherNode);
                        showUrlManager(otherNode, 'Node');
                    };
                    li.appendChild(button);
                    relatedList.appendChild(li);
                });
            } else {
                const noRelationsMessage = document.createElement('p');
                noRelationsMessage.textContent = 'No direct relationships found.';
                noRelationsMessage.style.fontSize = '14px';
                noRelationsMessage.style.color = '#aaa';
                relatedList.appendChild(noRelationsMessage);
            }
            controlsContainer.appendChild(relatedList);
        }
        
        const urlSectionTitle = document.createElement('h4');
        urlSectionTitle.textContent = 'Associated Resources';
        urlSectionTitle.style.marginTop = '20px';
        urlSectionTitle.style.borderBottom = '1px solid #666';
        urlSectionTitle.style.paddingBottom = '5px';
        controlsContainer.appendChild(urlSectionTitle);

        const urlList = document.createElement('ul');
        if (element.urls && element.urls.length > 0) {
            element.urls.forEach((url) => {
                const li = document.createElement('li');
                const videoId = getYoutubeVideoId(url);
                if (videoId) {
                    li.className = 'url-entry youtube-preview';
                    const linkElement = document.createElement('a');
                    linkElement.href = url;
                    linkElement.target = "_blank";
                    
                    const thumbnail = document.createElement('img');
                    thumbnail.src = getYoutubeThumbnailUrl(videoId);
                    linkElement.appendChild(thumbnail);
                    
                    const titleDiv = document.createElement('div');
                    titleDiv.className = 'youtube-title';
                    titleDiv.textContent = 'Loading title...';
                    titleDiv.style.opacity = '0';
                    linkElement.appendChild(titleDiv);
                    
                    li.appendChild(linkElement);

                    fetchYoutubeMetadata(url)
                        .then(data => {
                            if (data && data.title) {
                                titleDiv.textContent = data.title;
                                titleDiv.style.opacity = '1';
                            } else {
                                titleDiv.textContent = 'Title not available';
                            }
                        })
                        .catch(error => {
                            console.error(error);
                            titleDiv.style.display = 'none';
                        });
                } else {
                    li.className = 'url-entry';
                    const linkElement = document.createElement('a');
                    linkElement.href = url;
                    linkElement.target = "_blank";
                    const urlTextDiv = document.createElement('div');
                    urlTextDiv.className = 'url-text';
                    urlTextDiv.textContent = url;
                    linkElement.appendChild(urlTextDiv);
                    li.appendChild(linkElement);
                }
                urlList.appendChild(li);
            });
        } else {
            const noUrlsMessage = document.createElement('p');
            noUrlsMessage.textContent = 'No resources have been added to this item yet.';
            noUrlsMessage.style.fontSize = '14px';
            noUrlsMessage.style.color = '#aaa';
            urlList.appendChild(noUrlsMessage);
        }
        controlsContainer.appendChild(urlList);

        const addUrlInput = document.createElement('input');
        addUrlInput.type = 'text'; addUrlInput.id = 'add-url-input'; addUrlInput.placeholder = 'Add a new URL';
        controlsContainer.appendChild(addUrlInput);
        const addUrlButton = document.createElement('button');
        addUrlButton.id = 'add-url-button'; addUrlButton.textContent = 'Add';
        controlsContainer.appendChild(addUrlButton);

        addUrlButton.onclick = () => {
            if (addUrlInput.value) {
                try {
                    new URL(addUrlInput.value);
                    if (!element.urls) element.urls = [];
                    element.urls.push(addUrlInput.value);
                    showUrlManager(element, type);
                } catch (_) {
                    alert("Please enter a valid URL.");
                }
            }
        };
    }
});