document.addEventListener("DOMContentLoaded", () => {
    // --- Global Element References & State ---
    const controlsContainer = document.getElementById('controls-container');
    const initialControlsHTML = controlsContainer.innerHTML;
    const saveButton = document.getElementById('save-csv-button');
    const notesSection = document.getElementById('notes-section');
    const notesToggle = document.getElementById('notes-toggle');
    const searchInput = document.getElementById('search-input');
    const suggestionsContainer = document.getElementById('search-suggestions');
    const loadingScreen = document.getElementById('loading-screen');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    // --- Loading Progress Helper ---
    function updateProgress(percent, text) {
        progressBar.style.width = percent + '%';
        progressText.textContent = text;
    }

    function hideLoadingScreen() {
        updateProgress(100, 'Complete!');
        setTimeout(() => {
            loadingScreen.classList.add('hidden');
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 500); // Wait for fade out
        }, 300);
    }

    // --- 10 Second Timeout Safety Mechanism ---
    let loadingTimeout = setTimeout(() => {
        console.warn('Loading screen timeout reached (10 seconds). Force hiding loading screen.');
        hideLoadingScreen();
    }, 10000);

    // Clear timeout when loading completes normally
    function clearLoadingTimeout() {
        if (loadingTimeout) {
            clearTimeout(loadingTimeout);
            loadingTimeout = null;
        }
    }
    
    let currentGraphData = null;
    let svg, zoom, width, height, g; // D3 variables for global access
    let simulation = null;
    let isSimulationRunning = false;
    let linkElements = null; // Store link selection for toggling

    // Link visibility state
    let linkVisibility = {
        'sub topic': true,
        'depends on': true,
        'extends': true,
        'semantically_similar': true,
        'other': true
    };

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
    updateProgress(10, 'Loading data...');
    
    d3.json("../data/d3_graph_data_hierarchical.json").then(graphData => {
        updateProgress(30, 'Data loaded, rendering graph...');
        currentGraphData = graphData;
        renderD3MindMap(currentGraphData);
        updateProgress(50, 'Initializing search...');
        initializeSearch();
        updateProgress(60, 'Settling layout...');
    }).catch(error => {
        console.error("Error loading or parsing data:", error);
        progressText.textContent = 'Error loading data';
        progressBar.style.backgroundColor = '#FF6B6B';
    });

    // --- Link Toggle Initialization ---
    function initializeLinkToggles() {
        const toggleSubTopic = document.getElementById('toggle-sub-topic');
        const toggleDependsOn = document.getElementById('toggle-depends-on');
        const toggleExtends = document.getElementById('toggle-extends');
        const toggleSemantic = document.getElementById('toggle-semantic');

        if (toggleSubTopic) {
            toggleSubTopic.checked = linkVisibility['sub topic'];
            toggleSubTopic.addEventListener('change', () => toggleLinkType('sub topic'));
        }
        if (toggleDependsOn) {
            toggleDependsOn.checked = linkVisibility['depends on'];
            toggleDependsOn.addEventListener('change', () => toggleLinkType('depends on'));
        }
        if (toggleExtends) {
            toggleExtends.checked = linkVisibility['extends'];
            toggleExtends.addEventListener('change', () => toggleLinkType('extends'));
        }
        if (toggleSemantic) {
            toggleSemantic.checked = linkVisibility['semantically_similar'];
            toggleSemantic.addEventListener('change', () => toggleLinkType('semantically_similar'));
        }
    }

    // --- Search Functionality (Optimized) ---
    let searchDebounceTimer;
    function initializeSearch() {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounceTimer);
            const query = searchInput.value;
            
            if (query.length > 1) {
                searchDebounceTimer = setTimeout(() => {
                    const results = fuzzySearch(query, currentGraphData.nodes);
                    displaySuggestions(results.slice(0, 10));
                }, 150); // Debounce search
            } else {
                clearSuggestions();
            }
        });

        document.addEventListener('click', (event) => {
            if (!document.getElementById('search-container').contains(event.target)) {
                clearSuggestions();
            }
        }, { passive: true });
    }
    
    function fuzzySearch(query, nodes) {
        const lowerCaseQuery = query.toLowerCase();
        const results = [];
        
        // Early exit optimization
        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];
            const lowerCaseTitle = node.name.toLowerCase();
            const score = calculateMatchScore(lowerCaseTitle, lowerCaseQuery);
            
            if (score > 0) {
                results.push({ node, score });
            }
        }
        
        return results.sort((a, b) => b.score - a.score);
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

    // Category color mapping
    function getCategoryColor(category) {
        const colorMap = {
            'Core concept in RF engineering': 'hsla(0, 100%, 71%, 1.00)',        // Bright red
            'Core concept in Electrical engineering': 'hsla(176, 56%, 56%, 1.00)', // Teal
            'Core concept in System design': 'hsla(228, 64%, 61%, 1.00)',          // Light teal
            'Useful term in RF engineering': '#FFB6B9',          // Light coral
            'Useful term in Electrical engineering': '#A8E6CF',  // Mint green
            'Useful term in System design': '#c7ceeaff',           // Lavender
            'Other (mechanical, chemical, unrelated)': '#B8B8B8' // Gray
        };
        return colorMap[category] || '#778899'; // Default: light slate gray
    }

    // Cached node styles
    const nodeStyleCache = new Map();
    function getNodeStyle(nodeId) {
        if (nodeStyleCache.has(nodeId)) {
            return nodeStyleCache.get(nodeId);
        }
        
        const level = nodeId.toString().split('.').length;
        let style;
        switch (level) {
            case 1: style = { radius: 20, stroke: 'black', strokeWidth: 2 }; break;
            case 2: style = { radius: 15, stroke: 'none', strokeWidth: 0 }; break;
            default: style = { radius: 10, stroke: 'none', strokeWidth: 0 }; break;
        }
        
        nodeStyleCache.set(nodeId, style);
        return style;
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
        const originalColor = getCategoryColor(targetNode.category);
        circle.transition().duration(300)
            .attr("fill", "#ffcc00")
            .attr("r", getNodeStyle(targetNode.id).radius + 5)
            .transition().duration(1000)
            .attr("fill", originalColor)
            .attr("r", getNodeStyle(targetNode.id).radius);
    }

    function renderD3MindMap(graph) {
        const container = document.getElementById('mind-map-container');
        width = container.clientWidth;
        height = container.clientHeight;

        zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));

        svg = d3.select("#mind-map-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .call(zoom)
            .on("click", (event) => {
                if (!document.getElementById('search-container').contains(event.target)) {
                    resetControlsPanel();
                }
            }, { passive: false });

        g = svg.append("g");

        // --- Setup data structures ---
        const nodeById = new Map(graph.nodes.map(d => [d.id, d]));
        const highLevelTopics = graph.high_level_topics || [];

        // Assign cluster property
        graph.nodes.forEach(n => {
            let foundCluster = null;
            for (let i = 0; i < highLevelTopics.length; i++) {
                if (highLevelTopics[i].sub_topics.includes(n.id)) {
                    foundCluster = highLevelTopics[i].id;
                    break;
                }
            }
            n.cluster = foundCluster || n.id;
        });

        const color = d3.scaleOrdinal(d3.schemeTableau10);

        // --- Link Hierarchy Configuration ---
        const linkHierarchy = {
            'sub topic': { strength: 0.8, distance: 100, width: 3, opacity: 1.0, color: '#333', dashArray: null },
            'depends on': { strength: 0.3, distance: 200, width: 2, opacity: 0.7, color: '#666', dashArray: '5,5' },
            'extends': { strength: 0.2, distance: 250, width: 1.5, opacity: 0.5, color: '#999', dashArray: '5,5' },
            'semantically_similar': { strength: 0.1, distance: 300, width: 1, opacity: 0.3, color: '#ccc', dashArray: '2,2' },
            'default': { strength: 0.2, distance: 200, width: 2, opacity: 0.6, color: '#888', dashArray: '5,5' }
        };

        // --- Cluster force (defined early for use in simulation) ---
        // Pre-compute sub-topic arrays for performance
        const clusterSubTopics = highLevelTopics.map(hl => ({
            parentNode: nodeById.get(hl.id),
            subs: hl.sub_topics.map(id => nodeById.get(id)).filter(Boolean)
        })).filter(c => c.parentNode);
        
        function clusteringForce() {
            const strength = 0.1;
            function force(alpha) {
                for (let i = 0; i < clusterSubTopics.length; i++) {
                    const cluster = clusterSubTopics[i];
                    const parentNode = cluster.parentNode;
                    const subs = cluster.subs;
                    
                    for (let j = 0; j < subs.length; j++) {
                        const sub = subs[j];
                        const dx = sub.x - parentNode.x;
                        const dy = sub.y - parentNode.y;
                        sub.vx -= dx * strength * alpha;
                        sub.vy -= dy * strength * alpha;
                    }
                }
            }
            return force;
        }

        // --- Optimized Simulation (Fast Initial Layout) ---
        simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.links)
                .id(d => d.id)
                .strength(link => {
                    const config = linkHierarchy[link.type] || linkHierarchy['default'];
                    return config.strength;
                })
                .distance(link => {
                    const config = linkHierarchy[link.type] || linkHierarchy['default'];
                    return config.distance;
                })
            )
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide().radius(d => getNodeStyle(d.id).radius + 60))
            .force("cluster", clusteringForce())
            .alphaDecay(0.05) // Faster initial convergence
            .velocityDecay(0.6) // More damping for quicker settling
            .alphaMin(0.001); // Stop earlier

        // --- Contour group (blobs) ---
        const contourGroup = g.append("g").attr("class", "contours");

        // --- Links (Optimized with Visual Hierarchy) ---
        linkElements = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(graph.links)
            .join("line")
            .attr("class", d => `link link-type-${d.type.replace(/\s+/g, '-')}`)
            .attr("stroke-width", d => {
                const config = linkHierarchy[d.type] || linkHierarchy['default'];
                return config.width;
            })
            .style("stroke-opacity", d => {
                const config = linkHierarchy[d.type] || linkHierarchy['default'];
                const visibility = linkVisibility[d.type] !== undefined ? linkVisibility[d.type] : linkVisibility['other'];
                return visibility ? config.opacity : 0;
            })
            .attr("stroke", d => {
                const config = linkHierarchy[d.type] || linkHierarchy['default'];
                return config.color;
            })
            .attr("stroke-dasharray", d => {
                const config = linkHierarchy[d.type] || linkHierarchy['default'];
                return config.dashArray;
            })
            .style("pointer-events", d => {
                const visibility = linkVisibility[d.type] !== undefined ? linkVisibility[d.type] : linkVisibility['other'];
                return visibility ? "auto" : "none";
            })
            .on("click", (event, d) => {
                event.stopPropagation();
                showUrlManager(d, 'Link');
            });
        
        console.log('linkElements created with', linkElements.size(), 'links');
        
        // Initialize link toggles now that linkElements exists
        initializeLinkToggles();

        // --- Nodes (Optimized with canvas-like rendering) ---
        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(graph.nodes)
            .join("g")
            .attr("class", d => `node node-id-${d.id.toString().replace(/\./g, '-')}`)
            .call(drag(simulation))
            .on("click", (event, d) => {
                event.stopPropagation();
                showUrlManager(d, 'Node');
            });

        node.append("circle")
            .attr("r", d => {
                const isHighLevel = highLevelTopics.find(h => h.id === d.id);
                return isHighLevel ? 50 : getNodeStyle(d.id).radius;
            })
            .attr("fill", d => getCategoryColor(d.category))
            .attr("stroke", d => getNodeStyle(d.id).stroke)
            .attr("stroke-width", d => getNodeStyle(d.id).strokeWidth);

        // Only show labels when zoomed in or for important nodes
        node.append("text")
            .text(d => d.name)
            .attr("x", d => getNodeStyle(d.id).radius + 5)
            .attr("y", 3)
            .style("opacity", d => {
                const level = d.id.toString().split('.').length;
                return level <= 2 ? 1 : 0; // Hide minor node labels initially
            });

        node.append("title").text(d => d.description);

        // --- Labels for clusters ---
        const clusterLabels = contourGroup.selectAll("text")
            .data(highLevelTopics)
            .join("text")
            .attr("class", "cluster-label")
            .attr("text-anchor", "middle")
            .attr("dy", ".35em")
            .attr("font-size", "16px")
            .attr("font-weight", "600")
            .attr("fill", "#222")
            .attr("pointer-events", "none")
            .text(d => d.name);

        // --- Optimized Simulation Tick with Throttling ---
        let tickCount = 0;
        let rafId = null;
        let skipContours = true; // Defer contours initially
        const targetTicks = 100; // Estimate for progress tracking
        
        simulation.on("tick", () => {
            tickCount++;
            
            // Update loading progress during simulation (60-95%)
            if (tickCount % 5 === 0 && tickCount <= targetTicks) {
                const simProgress = Math.min(95, 60 + (tickCount / targetTicks) * 35);
                updateProgress(simProgress, `Settling layout... (${tickCount}/${targetTicks})`);
            }
            
            // Update on every tick, but throttle expensive operations
            // IMPORTANT: Only update position attributes, preserve stroke-opacity for toggles
            linkElements
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${d.x},${d.y})`);

            // Skip contours for first 30 ticks (fast initial render)
            if (tickCount < 30) return;
            
            // Enable contours after initial layout
            if (skipContours && tickCount >= 30) {
                skipContours = false;
                updateProgress(70, 'Rendering clusters...');
            }
            
            // Only render contours every 10 ticks and use RAF (less frequent)
            if (!skipContours && tickCount % 10 === 0) {
                if (rafId) cancelAnimationFrame(rafId);
                rafId = requestAnimationFrame(() => renderContours());
            }
        });

        // Stop simulation after it settles to save CPU
        simulation.on("end", () => {
            isSimulationRunning = false;
            renderContours(); // Final render
            clearLoadingTimeout(); // Clear timeout before hiding
            hideLoadingScreen();
        });

        isSimulationRunning = true;

        // --- Optimized Contour Rendering ---
        let contourRenderTimeout;
        function renderContours() {
            // Debounce rapid calls
            clearTimeout(contourRenderTimeout);
            contourRenderTimeout = setTimeout(() => {
                const contours = [];

                highLevelTopics.forEach(hl => {
                    const members = hl.sub_topics.map(id => nodeById.get(id)).filter(Boolean);
                    const parentNode = nodeById.get(hl.id);
                    if (parentNode) members.push(parentNode);
                    if (members.length === 0) return;

                    // Reduced grid resolution for performance
                    const xs = members.map(d => d.x);
                    const ys = members.map(d => d.y);
                    const xMin = d3.min(xs) - 100, xMax = d3.max(xs) + 100;
                    const yMin = d3.min(ys) - 100, yMax = d3.max(ys) + 100;
                    const step = 25; // Further increased for faster rendering

                    const grid = [];
                    for (let y = yMin; y <= yMax; y += step) {
                        for (let x = xMin; x <= xMax; x += step) {
                            let density = 0;
                            // Optimized density calculation
                            for (let i = 0; i < members.length; i++) {
                                const n = members[i];
                                const dx = n.x - x;
                                const dy = n.y - y;
                                const distSq = dx * dx + dy * dy;
                                density += Math.exp(-distSq / 8000);
                            }
                            grid.push(density);
                        }
                    }

                    const nx = Math.floor((xMax - xMin) / step) + 1;
                    const ny = Math.floor((yMax - yMin) / step) + 1;

                    const contourGen = d3.contours()
                        .size([nx, ny])
                        .thresholds([0.4]);

                    const c = contourGen(grid)[0];
                    if (c && c.coordinates.length) {
                        contours.push({
                            id: hl.id,
                            color: color(hl.id),
                            coordinates: c.coordinates.map(ring =>
                                ring[0].map(([ix, iy]) => [
                                    xMin + ix * step,
                                    yMin + iy * step
                                ])
                            )
                        });
                    }
                });

                // Draw contours
                contourGroup.selectAll("path")
                    .data(contours, d => d.id)
                    .join("path")
                    .attr("d", d => d3.line()(d.coordinates[0]))
                    .attr("fill", d => d.color)
                    .attr("fill-opacity", 0.15)
                    .attr("stroke", d => d.color)
                    .attr("stroke-width", 2);

                // Update label positions
                clusterLabels
                    .attr("x", d => {
                        const hl = contours.find(c => c.id === d.id);
                        if (!hl || !hl.coordinates[0]) return 0;
                        const xs = hl.coordinates[0].map(p => p[0]);
                        return d3.mean(xs);
                    })
                    .attr("y", d => {
                        const hl = contours.find(c => c.id === d.id);
                        if (!hl || !hl.coordinates[0]) return 0;
                        const ys = hl.coordinates[0].map(p => p[1]);
                        return d3.mean(ys);
                    });
            }, 50); // Debounce by 50ms
        }

        // --- Optimized Drag behavior ---
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

        // Zoom-based label visibility
        zoom.on("zoom.labels", (event) => {
            const scale = event.transform.k;
            node.selectAll("text")
                .style("opacity", d => {
                    const level = d.id.toString().split('.').length;
                    if (level === 1) return 1;
                    if (level === 2) return scale > 0.5 ? 1 : 0;
                    return scale > 1 ? 1 : 0;
                });
        });
    }

    function resetControlsPanel() {
        controlsContainer.innerHTML = initialControlsHTML;
        document.getElementById('save-csv-button').addEventListener('click', () => {
            if (currentGraphData) saveUrlsToCsv(currentGraphData); else alert("No data available to save.");
        });
        // Re-initialize link toggles after resetting
        initializeLinkToggles();
        // Restore checkbox states
        updateCheckboxStates();
    }

    function updateCheckboxStates() {
        const toggleSubTopic = document.getElementById('toggle-sub-topic');
        const toggleDependsOn = document.getElementById('toggle-depends-on');
        const toggleExtends = document.getElementById('toggle-extends');
        const toggleSemantic = document.getElementById('toggle-semantic');

        if (toggleSubTopic) toggleSubTopic.checked = linkVisibility['sub topic'];
        if (toggleDependsOn) toggleDependsOn.checked = linkVisibility['depends on'];
        if (toggleExtends) toggleExtends.checked = linkVisibility['extends'];
        if (toggleSemantic) toggleSemantic.checked = linkVisibility['semantically_similar'];
    }

    function toggleLinkType(linkType) {
        linkVisibility[linkType] = !linkVisibility[linkType];
        console.log(`Toggling ${linkType} to ${linkVisibility[linkType]}`);
        
        // Use the same linkHierarchy config as during initial render
        const linkHierarchy = {
            'sub topic': { opacity: 1.0 },
            'depends on': { opacity: 0.7 },
            'extends': { opacity: 0.5 },
            'semantically_similar': { opacity: 0.3 },
            'default': { opacity: 0.6 }
        };
        
        // Re-select all links fresh from the DOM using the svg and g references
        const allLinks = g.selectAll(".link");
        console.log('Total link elements in DOM:', allLinks.size());
        
        // Update all links based on their current visibility state
        // Use .style() instead of .attr() to override CSS
        allLinks
            .style("stroke-opacity", function(d) {
                const visibility = linkVisibility[d.type] !== undefined ? linkVisibility[d.type] : linkVisibility['other'];
                const linkConfig = linkHierarchy[d.type] || linkHierarchy['default'];
                const targetOpacity = visibility ? linkConfig.opacity : 0;
                return targetOpacity;
            })
            .style("pointer-events", function(d) {
                const visibility = linkVisibility[d.type] !== undefined ? linkVisibility[d.type] : linkVisibility['other'];
                return visibility ? "auto" : "none";
            });
        
        // Count how many were updated
        const updatedCount = allLinks.filter(d => d.type === linkType).size();
        console.log(`Updated ${updatedCount} links of type "${linkType}" to visibility: ${linkVisibility[linkType]}`);
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
            const connectedLinks = currentGraphData.links.filter(link => 
                link.source.id === element.id || link.target.id === element.id
            );

            if (connectedLinks.length > 0) {
                connectedLinks.forEach(link => {
                    const isSource = link.source.id === element.id;
                    const otherNode = isSource ? link.target : link.source;
                    const li = document.createElement('li');
                    const button = document.createElement('button');
                    button.className = 'related-topic-button';
                    button.innerHTML = isSource ? 
                        `<span class="relation">[${link.type}] →</span> ${otherNode.name}` : 
                        `<span class="relation">← [${link.type}]</span> ${otherNode.name}`;
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