document.addEventListener("DOMContentLoaded", () => {
    const controlsContainer = document.getElementById('controls-container');
    const initialControlsHTML = controlsContainer.innerHTML;
    const saveButton = document.getElementById('save-csv-button');
    
    let currentGraphData = null;

    Promise.all([
        d3.csv("data/topics.csv"),
        d3.csv("data/links.csv"),
        d3.csv("data/urls.csv")
    ]).then(([topics, links, urls]) => {
        const validTopics = topics.filter(t => t.Index && t.Index.trim() !== '');
        const validLinks = links.filter(l => l['Source Index'] && l['Target Index']);
        currentGraphData = createD3Graph(validTopics, validLinks, urls);
        renderD3MindMap(currentGraphData);
    }).catch(error => {
        console.error("Error loading or parsing data:", error);
    });

    saveButton.addEventListener('click', () => {
        if (currentGraphData) {
            saveUrlsToCsv(currentGraphData);
        } else {
            alert("No data available to save.");
        }
    });

    function createD3Graph(topics, links, urlsData) {
        // ... (This function is unchanged from the previous step)
        const urlMap = new Map();
        urlsData.forEach(entry => {
            if (!urlMap.has(entry.Identifier)) { urlMap.set(entry.Identifier, []); }
            urlMap.get(entry.Identifier).push(entry.URL);
        });
        const nodes = topics.map(topic => ({ id: topic.Index, title: topic.Topic, description: topic['Description / Key Concepts'], urls: urlMap.get(topic.Index) || [] }));
        const dependencyLinks = links.map(link => { const linkId = getLinkId(link['Source Index'], link['Target Index'], link['Relation Type']); return { source: link['Source Index'], target: link['Target Index'], relation: link['Relation Type'], type: 'dependency', urls: urlMap.get(linkId) || [] }; });
        const hierarchicalLinks = [];
        const nodeIdSet = new Set(nodes.map(n => n.id));
        nodes.forEach(node => {
            const parts = node.id.toString().split('.');
            if (parts.length > 1) {
                const parentId = parts.slice(0, -1).join('.');
                if (nodeIdSet.has(parentId)) { const linkId = getLinkId(parentId, node.id, 'parent-child'); hierarchicalLinks.push({ source: parentId, target: node.id, relation: 'parent-child', type: 'hierarchical', urls: urlMap.get(linkId) || [] }); }
            }
        });
        const allLinks = [...dependencyLinks, ...hierarchicalLinks];
        return { nodes, links: allLinks };
    }

    function getLinkId(sourceId, targetId, relation) {
        const sId = typeof sourceId === 'object' ? sourceId.id : sourceId;
        const tId = typeof targetId === 'object' ? targetId.id : targetId;
        return `${sId}|${tId}|${relation}`;
    }

    function saveUrlsToCsv(graph) {
        // ... (This function is unchanged from the previous step)
        let csvContent = "Identifier,URL\n";
        graph.nodes.forEach(node => { if (node.urls && node.urls.length > 0) { node.urls.forEach(url => { csvContent += `${node.id},"${url}"\n`; }); } });
        graph.links.forEach(link => { if (link.urls && link.urls.length > 0) { const linkId = getLinkId(link.source, link.target, link.relation); link.urls.forEach(url => { csvContent += `${linkId},"${url}"\n`; }); } });
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const downloadLink = document.createElement("a");
        const url = URL.createObjectURL(blob);
        downloadLink.setAttribute("href", url); downloadLink.setAttribute("download", "urls.csv"); downloadLink.style.visibility = 'hidden'; document.body.appendChild(downloadLink); downloadLink.click(); document.body.removeChild(downloadLink);
    }

    // --- NEW: YouTube Helper Functions ---
    function getYoutubeVideoId(url) {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
        const match = url.match(regExp);
        return (match && match[2].length === 11) ? match[2] : null;
    }

    function getYoutubeThumbnailUrl(videoId) {
        // 'mqdefault' is a good balance of quality and size
        return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
    }

    // --- MODIFIED: URL Management UI now builds thumbnail previews ---
    function showUrlManager(element, type) {
        controlsContainer.innerHTML = '';
        const title = type === 'Node' ? element.title : `${element.source.title} → ${element.target.title}`;
        
        const h3 = document.createElement('h3');
        h3.textContent = `Resources for ${title}`;
        controlsContainer.appendChild(h3);

        const urlList = document.createElement('ul');
        if (element.urls && element.urls.length > 0) {
            element.urls.forEach((url) => {
                const li = document.createElement('li');
                const videoId = getYoutubeVideoId(url);

                if (videoId) {
                    // It's a YouTube video, build a preview
                    li.className = 'url-entry youtube-preview';
                    
                    const linkElement = document.createElement('a');
                    linkElement.href = url;
                    linkElement.target = "_blank";
                    
                    const thumbnail = document.createElement('img');
                    thumbnail.src = getYoutubeThumbnailUrl(videoId);
                    linkElement.appendChild(thumbnail);
                    
                    const urlTextDiv = document.createElement('div');
                    urlTextDiv.className = 'url-text';
                    urlTextDiv.textContent = url;
                    linkElement.appendChild(urlTextDiv);

                    li.appendChild(linkElement);
                } else {
                    // It's a regular link
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
            noUrlsMessage.textContent = 'No URLs have been added to this item yet.';
            noUrlsMessage.style.fontSize = '14px';
            noUrlsMessage.style.color = '#666';
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
    
    // --- (The following functions are unchanged) ---
    function getNodeStyle(nodeId) { const level = nodeId.toString().split('.').length; switch (level) { case 1: return { radius: 20, stroke: 'black', strokeWidth: 2 }; case 2: return { radius: 15, stroke: 'none', strokeWidth: 0 }; default: return { radius: 10, stroke: 'none', strokeWidth: 0 }; } }
    function renderD3MindMap(graph) { const container = document.getElementById('mind-map-container'); const width = container.clientWidth; const height = container.clientHeight; const svg = d3.select("#mind-map-container").append("svg").attr("width", width).attr("height", height).call(d3.zoom().on("zoom", (event) => g.attr("transform", event.transform))).on("click", resetControlsPanel); const g = svg.append("g"); const simulation = d3.forceSimulation(graph.nodes).force("link", d3.forceLink(graph.links).id(d => d.id).distance(120)).force("charge", d3.forceManyBody().strength(-400)).force("center", d3.forceCenter(width / 2, height / 2)); const link = g.append("g").attr("class", "links").selectAll("line").data(graph.links).join("line").attr("class", d => `link ${d.type}`).attr("stroke-width", 2).on("click", (event, d) => { event.stopPropagation(); showUrlManager(d, 'Link'); }); const node = g.append("g").attr("class", "nodes").selectAll("g").data(graph.nodes).join("g").attr("class", "node").call(drag(simulation)).on("click", (event, d) => { event.stopPropagation(); showUrlManager(d, 'Node'); }); node.append("circle").attr("r", d => getNodeStyle(d.id).radius).attr("fill", "steelblue").attr("stroke", d => getNodeStyle(d.id).stroke).attr("stroke-width", d => getNodeStyle(d.id).strokeWidth); node.append("text").text(d => d.title).attr("x", d => getNodeStyle(d.id).radius + 5).attr("y", 3); node.append("title").text(d => d.description); simulation.on("tick", () => { link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y); node.attr("transform", d => `translate(${d.x},${d.y})`); }); }
    function drag(simulation) { function dragstarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; } function dragged(event, d) { d.fx = event.x; d.fy = event.y; } function dragended(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; } return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended); }
    function resetControlsPanel() { controlsContainer.innerHTML = initialControlsHTML; document.getElementById('save-csv-button').addEventListener('click', () => { if (currentGraphData) saveUrlsToCsv(currentGraphData); else alert("No data available to save."); }); }
});