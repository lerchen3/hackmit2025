// Main JavaScript for Assignment System
console.log('main.js loaded successfully');

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                const fileType = file.type;
                
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.className = 'mt-2 text-muted small';
                fileInfo.innerHTML = `
                    <i class="fas fa-file me-1"></i>
                    ${fileName} (${fileSize} MB)
                `;
                
                // Remove previous file info
                const existingInfo = input.parentNode.querySelector('.file-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                fileInfo.className += ' file-info';
                input.parentNode.appendChild(fileInfo);
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});

// Graph visualization functions
function initializeGraph(containerId, graphData, layoutType = 'dag') {
    console.log('initializeGraph function called');
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Debug: Log the received data
    console.log('Received graph data:', graphData);
    
    // Validate graph data
    if (!graphData) {
        console.error('No graph data received');
        container.innerHTML = '<div class="text-center text-red-600">No graph data received</div>';
        return;
    }
    
    if (!graphData.graph) {
        console.error('Missing graph property:', graphData);
        container.innerHTML = '<div class="text-center text-red-600">Missing graph property in data</div>';
        return;
    }
    
    if (!Array.isArray(graphData.graph)) {
        console.error('Graph property is not an array:', graphData.graph);
        container.innerHTML = '<div class="text-center text-red-600">Graph property is not an array</div>';
        return;
    }
    
    // Check if graph has required structure
    if (graphData.graph.length === 0) {
        console.error('Empty graph data');
        container.innerHTML = '<div class="text-center text-red-600">Empty graph data provided</div>';
        return;
    }

    // Clear container and create SVG
    container.innerHTML = '';
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', 500)
        .attr('viewBox', '0 0 800 500');

    // Define arrow markers for directed edges
    const defs = svg.append('defs');
    
    // Arrow marker pointing right
    const marker = defs.append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 0 10 10')
        .attr('refX', 10)
        .attr('refY', 5)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto');
    
    marker.append('polygon')
        .attr('points', '0,0 10,5 0,10')
        .attr('fill', '#999');
    

    // Convert graph edges to proper format for D3
    const edges = graphData.graph.map(edge => ({
        source: edge[0],
        target: edge[1]
    }));

    // Generate nodes from the graph structure using 0-indexed integers
    const nodeIds = [...new Set([...graphData.graph.map(e => e[0]), ...graphData.graph.map(e => e[1])])].sort((a, b) => a - b);
    
    // Create a hierarchical layout for better symmetry
    const createHierarchicalLayout = (nodeIds, edges) => {
        const levels = new Map();
        const visited = new Set();
        
        // Find start node (id 0)
        const startNode = nodeIds.find(id => id === 0);
        if (startNode !== undefined) {
            levels.set(0, [startNode]);
            visited.add(startNode);
        }
        
        // Build levels using BFS
        let currentLevel = 0;
        while (levels.has(currentLevel)) {
            const currentNodes = levels.get(currentLevel);
            const nextLevel = [];
            
            for (const nodeId of currentNodes) {
                const outgoingEdges = edges.filter(e => e.source === nodeId);
                for (const edge of outgoingEdges) {
                    if (!visited.has(edge.target)) {
                        nextLevel.push(edge.target);
                        visited.add(edge.target);
                    }
                }
            }
            
            if (nextLevel.length > 0) {
                levels.set(currentLevel + 1, nextLevel);
                currentLevel++;
            } else {
                break;
            }
        }
        
        return levels;
    };
    
    let levels, maxLevel, nodeLevels;
    
    if (layoutType === 'tree') {
        console.log('Creating tree layout...');
        // For tree layout, create a proper depth-ordered structure
        levels = new Map();
        levels.set(0, [0]); // Root at level 0 (top)
        
        // Group nodes by their distance from root using BFS
        nodeLevels = new Map();
        nodeLevels.set(0, 0); // Root is at level 0 (top)
        
        // BFS to assign levels - process level by level to ensure proper depth ordering
        let currentLevel = 0;
        let currentLevelNodes = [0];
        const visited = new Set([0]);
        
        while (currentLevelNodes.length > 0) {
            const nextLevelNodes = [];
            
            // Process all nodes at current level
            for (const currentNode of currentLevelNodes) {
                // Find children of current node
                const children = edges
                    .filter(edge => edge.source === currentNode)
                    .map(edge => edge.target)
                    .filter(child => !visited.has(child));
                
                // Add children to next level
                children.forEach(child => {
                    if (!visited.has(child)) {
                        const nextLevel = currentLevel + 1;
                        nodeLevels.set(child, nextLevel);
                        
                        if (!levels.has(nextLevel)) {
                            levels.set(nextLevel, []);
                        }
                        levels.get(nextLevel).push(child);
                        nextLevelNodes.push(child);
                        visited.add(child);
                    }
                });
            }
            
            // Move to next level
            currentLevelNodes = nextLevelNodes;
            currentLevel++;
        }
        
        // Add any unvisited nodes to the last level
        const unvisitedNodes = nodeIds.filter(id => !visited.has(id));
        if (unvisitedNodes.length > 0) {
            const lastLevel = Math.max(...levels.keys()) + 1;
            levels.set(lastLevel, unvisitedNodes);
            unvisitedNodes.forEach(node => {
                nodeLevels.set(node, lastLevel);
            });
        }
        
        maxLevel = Math.max(...levels.keys());
        console.log('Tree layout levels (depth-ordered):', levels);
        console.log('Max level:', maxLevel);
    } else {
        console.log('Creating DAG layout...');
        // For DAG layout, use the existing hierarchical layout
        levels = createHierarchicalLayout(nodeIds, edges);
        maxLevel = Math.max(...levels.keys());
        nodeLevels = new Map(); // Initialize empty for DAG layout
        console.log('DAG layout levels:', levels);
        console.log('Max level:', maxLevel);
    }
    
    console.log('Creating nodes...');
    const nodes = nodeIds.map((id) => {
        // Find which level this node belongs to - use nodeLevels map for accuracy
        let level = 0;
        if (layoutType === 'tree' && nodeLevels.has(id)) {
            level = nodeLevels.get(id);
        } else {
            // Fallback: search through levels map
            for (const [levelNum, levelNodes] of levels.entries()) {
                if (levelNodes.includes(id)) {
                    level = levelNum;
                    break;
                }
            }
        }
        
        // Calculate position within level for symmetry
        const levelNodes = levels.get(level) || [];
        const nodeIndex = levelNodes.indexOf(id);
        const totalInLevel = levelNodes.length;
        
        // Calculate symmetric positioning
        const levelWidth = 600; // Total width for all levels
        const levelHeight = 400; // Total height for vertical spacing
        const centerX = 400; // Center of the SVG
        const centerY = 250;
        
        // Determine node type based on layout type
        let nodeType;
        if (id === 0) {
            nodeType = 'start'; // Start node is always special
        } else if (layoutType === 'dag' && id === nodeIds[1]) {
            nodeType = 'end'; // Last node is end node for DAG layout
        } else {
            nodeType = 'process'; // All other nodes are process nodes
        }
        
        // Special positioning for start and end nodes
        let x, y;
        if (layoutType === 'tree') {
            // Tree layout: depth-ordered positioning from top to bottom
            if (nodeType === 'start') {
                // Root node at the very top
                x = centerX;
                y = 30;
            } else {
                // All other nodes positioned by depth level
                const totalHeight = 450; // Total available height
                const levelSpacing = totalHeight / Math.max(1, maxLevel + 1); // Even spacing between levels
                
                // Position horizontally within level for symmetry
                x = centerX + (nodeIndex - totalInLevel/2) * 180; // Spread horizontally within level
                
                // Position vertically based on depth (level 0 = top, higher levels = lower)
                y = 30 + (level * levelSpacing);
            }
        } else {
            // DAG layout: original left-to-right positioning
            if (nodeType === 'start') {
                // Start node always on the left
                x = 100;
                y = centerY;
            } else if (nodeType === 'end') {
                // End node always on the right
                x = 700;
                y = centerY;
            } else {
                // Process nodes positioned within their level
                // Horizontal positioning based on level (closer to start = more left)
                const levelSpacing = 600 / Math.max(1, maxLevel + 1); // Total width divided by levels
                x = 100 + (level * levelSpacing); // Start at 100, move right by level
                
                // Vertical positioning within level for symmetry
                if (totalInLevel === 1) {
                    y = centerY; // Center single nodes
                } else {
                    const verticalSpacing = levelHeight / (totalInLevel + 1);
                    y = centerY - (levelHeight / 2) + (nodeIndex + 1) * verticalSpacing;
                }
            }
        }
        
        const node = {
            id: id,
            label: (graphData.step_summaries && graphData.step_summaries[id]) || 
                 (graphData.step_summary && graphData.step_summary[id]) ? 
                 (graphData.step_summaries && graphData.step_summaries[id] ? graphData.step_summaries[id] : graphData.step_summary[id]) : 
                 `Step ${id}`,
            type: nodeType,
            is_correct: graphData.step_is_correct && graphData.step_is_correct[id] !== undefined ? graphData.step_is_correct[id] : true,
            x: x,
            y: y,
            level: level
        };
        
        // Fix start and end nodes in place
        if (nodeType === 'start' || nodeType === 'end') {
            node.fx = x; // Fixed x position
            node.fy = y; // Fixed y position
        }
        
        return node;
    });

    console.log('Nodes created:', nodes.length);
    console.log('Sample node:', nodes[0]);

    // Create simulation with improved symmetry
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(120).strength(0.5))
        .force('charge', d3.forceManyBody().strength(-400))
        .force('center', d3.forceCenter(400, 250))
        .force('collision', d3.forceCollide().radius(50).strength(1.0))
        .force('x', d3.forceX().x(d => {
            // Use the calculated hierarchical position
            return d.x;
        }).strength(d => {
            // No force for fixed nodes, stronger force for process nodes to maintain level positioning
            if (d.fx !== undefined) {
                return 0; // No force applied to fixed nodes
            }
            return 0.8; // Stronger force to maintain level-based horizontal positioning
        }))
        .force('y', d3.forceY(d => d.y).strength(d => {
            // No force for fixed nodes, stronger force for process nodes to maintain level positioning
            if (d.fy !== undefined) {
                return 0; // No force applied to fixed nodes
            }
            return 0.8; // Stronger force to maintain vertical positioning within levels
        }))
        .force('radial', d3.forceRadial(d => {
            // Add subtle radial force for better symmetry
            const centerX = 400;
            const centerY = 250;
            const distance = Math.sqrt((d.x - centerX) ** 2 + (d.y - centerY) ** 2);
            return Math.min(distance * 0.1, 50); // Gentle radial force
        }, 400, 250).strength(d => {
            // No radial force for fixed nodes
            if (d.fx !== undefined && d.fy !== undefined) {
                return 0;
            }
            return 0.1;
        }));

    // Configure simulation for better settling and symmetry
    simulation.alphaDecay(0.02); // Slower decay for more settling time
    simulation.velocityDecay(0.4); // Add some friction for stability

    // Create links
    const link = svg.append('g')
        .selectAll('line')
        .data(edges)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 2)
        .attr('marker-end', 'url(#arrowhead)');
    

    // Create nodes
    const node = svg.append('g')
        .selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .filter(function(event, d) {
                // Only allow dragging of non-fixed nodes
                return d.fx === undefined || d.fy === undefined;
            })
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Calculate node usage proportions
    const nodeUsageCounts = {};
    const totalSubmissions = graphData.submissions ? graphData.submissions.length : 0;
    
    // Count how many submissions use each node
    if (graphData.submissions) {
        graphData.submissions.forEach(submission => {
            if (submission.submission_nodes) {
                let me = submission.submission_nodes;
                //remove duplicates of me
                me = [...new Set(me)];
                me.forEach(nodeId => {
                    nodeUsageCounts[nodeId] = (nodeUsageCounts[nodeId] || 0) + 1;
                });
            }
        });
    }
    
    // Function to get solid color based on usage proportion
    function getUsageColor(usageProportion) {
        if (usageProportion === 0) return '#ffffff'; // White for 0% usage
        if (usageProportion === 1) return '#000000'; // Black for 100% usage
        
        // Calculate grey intensity based on usage proportion
        // Lighter grey (closer to white) for lower usage
        // Darker grey (closer to black) for higher usage
        const intensity = Math.floor(usageProportion * 128) + 127; // Range from 127 to 255
        const greyValue = 255 - intensity; // Invert so higher usage = darker
        return `rgb(${greyValue}, ${greyValue}, ${greyValue})`;
    }
    
    // Add circles to nodes
    node.append('circle')
        .attr('r', 20)
        .attr('fill', d => {
            // Start and end nodes are always white
            if (d.type === 'start' || d.type === 'end') {
                return '#ffffff';
            }
            // Process nodes use usage-based coloring
            const usageCount = nodeUsageCounts[d.id] || 0;
            const usageProportion = totalSubmissions > 0 ? usageCount / totalSubmissions : 0;
            return getUsageColor(usageProportion);
        })
        .attr('stroke', '#000000')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('click', function(event, d) {
            // Only handle click if we're not dragging
            if (d.isDragging) return;
            
            // Handle node click to select students using this step
            selectStudentsUsingStep(d.id);
        });

    // Add X mark for incorrect nodes
    node.filter(d => d.type === 'process' && !d.is_correct)
        .append('text')
        .attr('x', 0)
        .attr('y', 0)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Arial, sans-serif')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#ff0000')
        .text('✕');

    // Add start icon (play symbol) for start nodes
    node.filter(d => d.type === 'start')
        .append('text')
        .attr('x', 0)
        .attr('y', 0)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Arial, sans-serif')
        .attr('font-size', '14px')
        .attr('font-weight', 'bold')
        .attr('fill', '#000000')
        .text('▶');

    // Add end icon (flag) for end nodes
    node.filter(d => d.type === 'end')
        .append('text')
        .attr('x', 0)
        .attr('y', 0)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Arial, sans-serif')
        .attr('font-size', '14px')
        .attr('font-weight', 'bold')
        .attr('fill', '#000000')
        .text('🏁');

    // Add invisible larger circle for easier hovering on process nodes
    node.filter(d => d.type === 'process')
        .append('circle')
        .attr('r', 35)
        .attr('cx', 0)
        .attr('cy', 0)
        .attr('fill', 'rgba(0,0,0,0)')
        .attr('stroke', 'none')
        .attr('opacity', 0)
        .style('cursor', 'pointer')
        .style('pointer-events', 'all')
        .on('click', function(event, d) {
            // Only handle click if we're not dragging
            if (d.isDragging) return;
            
            // Handle node click to select students using this step
            event.stopPropagation();
            selectStudentsUsingStep(d.id);
        })
        .on('mouseover', function(event, d) {
            // Clear any existing timeout
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
            
            // Show tooltip after a small delay to prevent flickering
            this.tooltipTimeout = setTimeout(() => {
                const tooltipGroup = d3.select(this.parentNode).select('.tooltip-group');
                
                // Create HTML tooltip for LaTeX support
                const nodeData = d3.select(this.parentNode).datum();
                const tooltipId = `tooltip-${nodeData.id}`;
                
                // Remove existing HTML tooltip if it exists
                d3.select(`#${tooltipId}`).remove();
                
                // Create HTML tooltip
                const htmlTooltip = d3.select('body')
                    .append('div')
                    .attr('id', tooltipId)
                    .attr('class', 'graph-tooltip')
                    .style('position', 'absolute')
                    .style('background', '#333')
                    .style('color', 'white')
                    .style('padding', '8px 12px')
                    .style('border-radius', '8px')
                    .style('font-size', '11px')
                    .style('font-weight', '500')
                    .style('max-width', '300px')
                    .style('z-index', '1000')
                    .style('pointer-events', 'none')
                    .style('opacity', '0')
                    .style('transition', 'opacity 0.2s')
                    .html(`<div class="latex-content">${nodeData.label}</div>`);
                
                // Position the tooltip
                const nodeRect = this.parentNode.getBoundingClientRect();
                const tooltipRect = htmlTooltip.node().getBoundingClientRect();
                const x = nodeRect.left + (nodeRect.width / 2) - (tooltipRect.width / 2);
                const y = nodeRect.top - tooltipRect.height - 10;
                
                htmlTooltip
                    .style('left', `${x}px`)
                    .style('top', `${y}px`)
                    .transition()
                    .duration(200)
                    .style('opacity', '1');
                
                // Render LaTeX in the tooltip
                if (window.MathJax) {
                    window.MathJax.typesetPromise([htmlTooltip.node()]).catch(function (err) {
                        console.log('MathJax tooltip rendering error:', err);
                    });
                }
                
                // Slightly enlarge the visible circle
                d3.select(this.parentNode).select('circle')
                    .transition()
                    .duration(200)
                    .attr('r', 25);
            }, 100); // 100ms delay
        })
        .on('mouseout', function(event, d) {
            // Clear timeout if mouse leaves before tooltip shows
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
            
            // Remove HTML tooltip
            const nodeData = d3.select(this.parentNode).datum();
            const tooltipId = `tooltip-${nodeData.id}`;
            d3.select(`#${tooltipId}`).remove();
            
            // Return circle to normal size
            d3.select(this.parentNode).select('circle')
                .transition()
                .duration(200)
                .attr('r', 20);
        });

    // Add hover functionality for start and end nodes to show tooltips
    node.filter(d => d.type === 'start' || d.type === 'end')
        .on('mouseover', function(event, d) {
            // Clear any existing timeout
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
            
            // Show tooltip after a small delay to prevent flickering
            this.tooltipTimeout = setTimeout(() => {
                // Create HTML tooltip for LaTeX support
                const nodeData = d3.select(this).datum();
                const tooltipId = `tooltip-${nodeData.id}`;
                
                // Remove existing HTML tooltip if it exists
                d3.select(`#${tooltipId}`).remove();
                
                // Create HTML tooltip
                const htmlTooltip = d3.select('body')
                    .append('div')
                    .attr('id', tooltipId)
                    .attr('class', 'graph-tooltip')
                    .style('position', 'absolute')
                    .style('background', '#333')
                    .style('color', 'white')
                    .style('padding', '8px 12px')
                    .style('border-radius', '8px')
                    .style('font-size', '11px')
                    .style('font-weight', '500')
                    .style('max-width', '300px')
                    .style('z-index', '1000')
                    .style('pointer-events', 'none')
                    .style('opacity', '0')
                    .style('transition', 'opacity 0.2s')
                    .html(`<div class="latex-content">${nodeData.label}</div>`);
                
                // Position the tooltip
                const nodeRect = this.getBoundingClientRect();
                const tooltipRect = htmlTooltip.node().getBoundingClientRect();
                const x = nodeRect.left + (nodeRect.width / 2) - (tooltipRect.width / 2);
                const y = nodeRect.top - tooltipRect.height - 10;
                
                htmlTooltip
                    .style('left', `${x}px`)
                    .style('top', `${y}px`)
                    .transition()
                    .duration(200)
                    .style('opacity', '1');
                
                // Render LaTeX in the tooltip
                if (window.MathJax) {
                    window.MathJax.typesetPromise([htmlTooltip.node()]).catch(function (err) {
                        console.log('MathJax tooltip rendering error:', err);
                    });
                }
                
                // Slightly enlarge the visible circle
                d3.select(this).select('circle')
                    .transition()
                    .duration(200)
                    .attr('r', 25);
            }, 100); // 100ms delay
        })
        .on('mouseout', function(event, d) {
            // Clear timeout if mouse leaves before tooltip shows
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
            
            // Remove HTML tooltip
            const nodeData = d3.select(this).datum();
            const tooltipId = `tooltip-${nodeData.id}`;
            d3.select(`#${tooltipId}`).remove();
            
            // Return circle to normal size
            d3.select(this).select('circle')
                .transition()
                .duration(200)
                .attr('r', 20);
        });

    // Add labels to nodes (only for process nodes, start/end nodes will use tooltips)
    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em')
        .attr('fill', 'white')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('opacity', 0) // Hide all text labels by default
        .text(d => d.label);
    

    // Create tooltip groups for all nodes (process, start, and end)
    const tooltipGroups = node
        .append('g')
        .attr('class', 'tooltip-group')
        .attr('opacity', 0)
        .attr('transform', 'translate(0, -45)'); // Position above the node with more space

    // Add tooltip background
    tooltipGroups.append('rect')
        .attr('class', 'tooltip-bg')
        .attr('rx', 8)
        .attr('ry', 8)
        .attr('fill', '#333')
        .attr('stroke', '#666')
        .attr('stroke-width', 1)
        .attr('x', -50) // Temporary positioning
        .attr('y', -15)
        .attr('width', 100)
        .attr('height', 30);

    // Add tooltip text container (will be replaced with HTML for LaTeX support)
    tooltipGroups.append('text')
        .attr('class', 'tooltip-text')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em')
        .attr('fill', 'white')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .attr('x', 0)
        .attr('y', 0)
        .text(d => d.label);

    // Update positions on simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
    });

    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start and end nodes
        }
        
        d.fx = d.x;
        d.fy = d.y;
        
        // Mark that we're dragging to prevent click events
        d.isDragging = false;
    }

    function dragged(event, d) {
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start and end nodes
        }
        
        // Mark that we're dragging
        d.isDragging = true;
        
        // Process nodes can move more freely but within reasonable bounds
        d.fx = Math.max(50, Math.min(750, event.x));
        d.fy = Math.max(100, Math.min(400, event.y));
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start and end nodes
        }
        
        // Allow process nodes to settle naturally
        d.fx = null;
        d.fy = null;
        
        // Reset dragging flag after a short delay to allow click events
        setTimeout(() => {
            d.isDragging = false;
        }, 100);
    }

    // Highlight student paths
    function highlightStudentPath(submissionUid) {
        // Reset all nodes and links first
        node.select('circle').attr('stroke', '#000000').attr('stroke-width', 2)
        .attr('fill', d => {
            // Start and end nodes are always white
            if (d.type === 'start' || d.type === 'end') {
                return '#ffffff';
            }
            // Process nodes use usage-based fill colors
            const usageCount = nodeUsageCounts[d.id] || 0;
            const usageProportion = totalSubmissions > 0 ? usageCount / totalSubmissions : 0;
            return getUsageColor(usageProportion);
        });
        link.attr('stroke', '#999').attr('stroke-opacity', 0.6).attr('stroke-width', 2).attr('marker-end', 'url(#arrowhead)');
        
        // Preserve X marks for incorrect nodes during reset
        node.filter(d => d.type === 'process' && !d.is_correct)
            .select('text')
            .attr('fill', '#ff0000');
        
        // Hide all tooltips
        node
            .select('.tooltip-group')
            .transition()
            .duration(200)
            .attr('opacity', 0);
        
        // Remove all HTML tooltips
        d3.selectAll('.graph-tooltip').remove();
        
        // If no submission UID provided, just reset and return
        if (!submissionUid) {
            return;
        }
        
        // Find the submission
        const submission = graphData.submissions.find(sub => sub.submission_uid === submissionUid);
        if (!submission) {
            return;
        }
        
        const path = submission.submission_nodes;
        
        // Highlight path nodes
        const highlightedNodes = node.filter(d => path.includes(d.id));
        highlightedNodes.select('circle')
            .attr('stroke', '#ffc107')
            .attr('stroke-width', 4)
            .attr('fill', d => {
                // Start and end nodes are always white
                if (d.type === 'start' || d.type === 'end') {
                    return '#ffffff';
                }
                // Process nodes use usage-based color
                const usageCount = nodeUsageCounts[d.id] || 0;
                const usageProportion = totalSubmissions > 0 ? usageCount / totalSubmissions : 0;
                return getUsageColor(usageProportion);
            });
        
        // Preserve X marks for incorrect nodes during highlighting
        highlightedNodes.filter(d => d.type === 'process' && !d.is_correct)
            .select('text')
            .attr('fill', '#ff0000');
        
        // Don't show tooltips when highlighting - only show on hover
        
        // Highlight path links
        link.filter(d => {
            const sourceIndex = path.indexOf(d.source);
            const targetIndex = path.indexOf(d.target);
            return sourceIndex !== -1 && targetIndex !== -1 && targetIndex === sourceIndex + 1;
        })
        .attr('stroke', '#ffc107')
        .attr('stroke-opacity', 1)
        .attr('stroke-width', 4)
        .attr('marker-end', 'url(#arrowhead)');
    }

    // Function to select students using a specific step
    function selectStudentsUsingStep(stepId) {
        // Find all students that use this step
        const studentsUsingStep = graphData.submissions.filter(submission => 
            submission.submission_nodes.includes(stepId)
        ).map(submission => submission.submission_uid);
        
        // Update all checkboxes
        const checkboxes = document.querySelectorAll('#student-list input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            // Extract username_solutionId from checkbox value (first two parts)
            const checkboxUid = checkbox.value.split('_').slice(0, 2).join('_');
            const isUsingStep = studentsUsingStep.includes(checkboxUid);
            checkbox.checked = isUsingStep;
        });
        
        // Update highlighting based on new selection
        updateHighlighting();
    }
    
    // Make selectStudentsUsingStep available globally
    window.selectStudentsUsingStep = selectStudentsUsingStep;

    console.log('Graph initialization completed successfully');
    
    // Return highlight function for external use
    return highlightStudentPath;
}

console.log('initializeGraph function defined, type:', typeof initializeGraph);

// Ensure initializeGraph is available on window immediately
window.initializeGraph = initializeGraph;
console.log('initializeGraph assigned to window, type:', typeof window.initializeGraph);

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// AJAX helper functions
function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaultOptions, ...options };
    
    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Request failed:', error);
            throw error;
        });
}

// LaTeX preview functionality
function updateLatexPreview(sourceId, previewId) {
    const sourceElement = document.getElementById(sourceId);
    const previewElement = document.getElementById(previewId);
    
    if (sourceElement && previewElement) {
        const content = sourceElement.value;
        previewElement.textContent = content;
        
        // Re-render LaTeX in the preview element
        if (window.MathJax) {
            window.MathJax.typesetPromise([previewElement]).catch(function (err) {
                console.log('MathJax preview rendering error:', err);
            });
        }
    }
}

// Initialize LaTeX previews when page loads
function initializeLatexPreviews() {
    // Initialize previews for existing content
    const solutionText = document.getElementById('solution_text');
    const finalAnswer = document.getElementById('final_answer');
    
    if (solutionText) {
        updateLatexPreview('solution_text', 'solution_preview');
    }
    
    if (finalAnswer) {
        updateLatexPreview('final_answer', 'final_answer_preview');
    }
}

// Export functions for global use
// window.initializeGraph = initializeGraph; // Already assigned above
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;
window.makeRequest = makeRequest;
window.updateLatexPreview = updateLatexPreview;
window.initializeLatexPreviews = initializeLatexPreviews;

// Show graph function
function showGraph() {
    const container = document.getElementById('graph-container');
    if (!container) {
        console.error('Graph container not found');
        return;
    }
    
    // Show loading state
    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-96">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <p class="mt-4 text-gray-600">Loading graph...</p>
        </div>
    `;
    
    // Get assignment ID from the current page URL
    const assignmentId = window.location.pathname.split('/').pop();
    if (!assignmentId || isNaN(assignmentId)) {
        console.error('Could not determine assignment ID');
        container.innerHTML = '<div class="text-center text-red-600">Could not determine assignment ID</div>';
        return;
    }
    
    // Fetch graph data
    fetch(`/api/solution-graph/${assignmentId}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Access denied. Only teachers can view solution graphs.');
                } else if (response.status === 404) {
                    throw new Error('Graph data not found.');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            return response.json();
        })
        .then(data => {
            container.innerHTML = '';
            
            // Store graph data globally for multi-student highlighting
            window.graphData = data;
            
            // Initialize the graph with DAG layout
            if (typeof initializeGraph === 'function') {
                window.highlightFunction = initializeGraph('graph-container', data, 'dag');
            } else {
                console.error('initializeGraph function not available');
                container.innerHTML = '<div class="text-center text-red-600">Graph visualization function not loaded</div>';
            }
        })
        .catch(error => {
            console.error('Error loading graph:', error);
            container.innerHTML = 
                '<div class="bg-red-50 border border-red-200 rounded-md p-4"><div class="flex"><div class="flex-shrink-0"><i class="fas fa-exclamation-circle text-red-400"></i></div><div class="ml-3"><p class="text-sm text-red-700">' + error.message + '</p></div></div></div>';
        });
}

// Export showGraph function
window.showGraph = showGraph;

// Upload solutions CSV helper (teacher)
function uploadSolutionsCsv(file, assignmentId, selectedStudentIds = []) {
    if (!file || !assignmentId) {
        console.error('CSV file and assignmentId are required');
        return Promise.reject(new Error('CSV file and assignmentId are required'));
    }
    const formData = new FormData();
    formData.append('solutions_csv', file);
    if (selectedStudentIds && selectedStudentIds.length > 0) {
        formData.append('student_ids', JSON.stringify(selectedStudentIds));
    }
    return fetch(`/teacher/assignment/${assignmentId}/submit-solutions`, {
        method: 'POST',
        body: formData
    }).then(res => {
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
        return res.text();
    });
}

window.uploadSolutionsCsv = uploadSolutionsCsv;
