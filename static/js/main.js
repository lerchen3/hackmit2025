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

    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', 500)
        .attr('viewBox', '0 0 800 500');

    // Create simulation
    const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.edges).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(400, 250));

    // Create links
    const link = svg.append('g')
        .selectAll('line')
        .data(graphData.edges)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 2);

    // Create nodes
    const node = svg.append('g')
        .selectAll('g')
        .data(graphData.nodes)
        .enter().append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Add circles to nodes
    node.append('circle')
        .attr('r', 20)
        .attr('fill', d => {
            switch(d.type) {
                case 'start': return '#28a745';
                case 'end': return '#dc3545';
                case 'process': return '#007bff';
                default: return '#6c757d';
            }
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);

    // Add labels to nodes
    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em')
        .attr('fill', 'white')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
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

    // Highlight student paths
    function highlightStudentPath(studentName) {
        if (graphData.student_paths[studentName]) {
            const path = graphData.student_paths[studentName];
            
            // Reset all nodes and links
            node.select('circle').attr('stroke', '#fff').attr('stroke-width', 2);
            link.attr('stroke', '#999').attr('stroke-opacity', 0.6);
            
            // Highlight path nodes
            node.filter(d => path.includes(d.id))
                .select('circle')
                .attr('stroke', '#ffc107')
                .attr('stroke-width', 4);
            
            // Highlight path links
            link.filter(d => {
                const sourceIndex = path.indexOf(d.source.id);
                const targetIndex = path.indexOf(d.target.id);
                return sourceIndex !== -1 && targetIndex !== -1 && targetIndex === sourceIndex + 1;
            })
            .attr('stroke', '#ffc107')
            .attr('stroke-opacity', 1)
            .attr('stroke-width', 4);
        }
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
