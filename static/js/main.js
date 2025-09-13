// Main JavaScript for Assignment System

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
function initializeGraph(containerId, graphData) {
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

    // Create SVG
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
        source: edge.from,
        target: edge.to
    }));

    // Generate nodes from the graph structure using 0-indexed integers
    const nodeIds = [...new Set([...graphData.graph.map(e => e.from), ...graphData.graph.map(e => e.to)])].sort((a, b) => a - b);
    
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
    
    const levels = createHierarchicalLayout(nodeIds, edges);
    const maxLevel = Math.max(...levels.keys());
    
    const nodes = nodeIds.map((id) => {
        // Find which level this node belongs to
        let level = 0;
        for (const [levelNum, levelNodes] of levels.entries()) {
            if (levelNodes.includes(id)) {
                level = levelNum;
                break;
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
        
        // Determine node type
        const nodeType = id === 0 ? 'start' : id === nodeIds[nodeIds.length - 1] ? 'end' : 'process';
        
        // Special positioning for start and end nodes
        let x, y;
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
        
        const node = {
            id: id,
            label: graphData.step_summary && graphData.step_summary[id] ? graphData.step_summary[id] : `Step ${id}`,
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

    // Add circles to nodes
    node.append('circle')
        .attr('r', 20)
        .attr('fill', d => {
            if (d.type === 'start') return '#ffffff';
            if (d.type === 'end') return '#ffffff';
            if (d.type === 'process') {
                return d.is_correct ? '#333333' : '#666666';
            }
            return '#999999';
        })
        .attr('stroke', d => (d.type === 'start' || d.type === 'end') ? '#000000' : '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer');

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
        .on('mouseover', function(event, d) {
            // Clear any existing timeout
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
            
            // Check if tooltip is already visible from highlighting
            const tooltipGroup = d3.select(this.parentNode).select('.tooltip-group');
            const isAlreadyVisible = tooltipGroup.attr('opacity') == 1;
            
            // If already visible from highlighting, don't do anything
            if (isAlreadyVisible) {
                return;
            }
            
            // Show tooltip after a small delay to prevent flickering
            this.tooltipTimeout = setTimeout(() => {
                // Double-check if tooltip is still not visible (in case highlighting changed)
                const currentOpacity = tooltipGroup.attr('opacity');
                if (currentOpacity == 1) {
                    return; // Already visible from highlighting
                }
                
                // Get text dimensions for proper sizing
                const tooltipText = tooltipGroup.select('.tooltip-text');
                const textNode = tooltipText.node();
                const bbox = textNode.getBBox();
                const padding = 8;
                
                // Update background size based on text
                tooltipGroup.select('.tooltip-bg')
                    .attr('x', -bbox.width/2 - padding)
                    .attr('y', -bbox.height/2 - padding)
                    .attr('width', bbox.width + (padding * 2))
                    .attr('height', bbox.height + (padding * 2));
                
                // Show the tooltip
                tooltipGroup
                    .transition()
                    .duration(200)
                    .attr('opacity', 1);
                
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
            
            // Check if tooltip is visible from highlighting - if so, don't hide it
            const tooltipGroup = d3.select(this.parentNode).select('.tooltip-group');
            const isFromHighlighting = tooltipGroup.classed('highlighted-tooltip');
            
            if (!isFromHighlighting) {
                // Hide tooltip bubble only if it's not from highlighting
                tooltipGroup
                    .transition()
                    .duration(200)
                    .attr('opacity', 0);
            }
            
            // Return circle to normal size
            d3.select(this.parentNode).select('circle')
                .transition()
                .duration(200)
                .attr('r', 20);
        });

    // Add labels to nodes (only visible for start/end nodes)
    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em')
        .attr('fill', d => (d.type === 'start' || d.type === 'end') ? '#000000' : 'white')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('opacity', d => d.type === 'start' || d.type === 'end' ? 1 : 0)
        .text(d => d.label);

    // Create tooltip groups for process nodes
    const tooltipGroups = node.filter(d => d.type === 'process')
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

    // Add tooltip text
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
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start/end nodes
        }
        
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start/end nodes
        }
        
        // Process nodes can move more freely but within reasonable bounds
        d.fx = Math.max(50, Math.min(750, event.x));
        d.fy = Math.max(100, Math.min(400, event.y));
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        
        // Don't allow dragging of fixed nodes
        if (d.fx !== undefined && d.fy !== undefined) {
            return; // Prevent dragging of start/end nodes
        }
        
        // Allow process nodes to settle naturally
        d.fx = null;
        d.fy = null;
    }

    // Highlight student paths
    function highlightStudentPath(submissionUid) {
        // Reset all nodes and links first
        node.select('circle').attr('stroke', '#fff').attr('stroke-width', 2);
        link.attr('stroke', '#999').attr('stroke-opacity', 0.6).attr('stroke-width', 2).attr('marker-end', 'url(#arrowhead)');
        
        // Hide all tooltips and clear highlighting class
        node.filter(d => d.type === 'process')
            .select('.tooltip-group')
            .classed('highlighted-tooltip', false)
            .transition()
            .duration(200)
            .attr('opacity', 0);
        
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
            .attr('stroke-width', 4);
        
        // Show tooltips for highlighted process nodes
        highlightedNodes.filter(d => d.type === 'process')
            .select('.tooltip-group')
            .each(function(d) {
                const tooltipGroup = d3.select(this);
                const tooltipText = tooltipGroup.select('.tooltip-text');
                const textNode = tooltipText.node();
                const bbox = textNode.getBBox();
                const padding = 8;
                
                // Update background size based on text
                tooltipGroup.select('.tooltip-bg')
                    .attr('x', -bbox.width/2 - padding)
                    .attr('y', -bbox.height/2 - padding)
                    .attr('width', bbox.width + (padding * 2))
                    .attr('height', bbox.height + (padding * 2));
                
                // Show the tooltip and mark it as from highlighting
                tooltipGroup
                    .classed('highlighted-tooltip', true)
                    .transition()
                    .duration(200)
                    .attr('opacity', 1);
            });
        
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

    // Return highlight function for external use
    return highlightStudentPath;
}

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

// Export functions for global use
window.initializeGraph = initializeGraph;
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;
window.makeRequest = makeRequest;
