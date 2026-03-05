// 行为树可视化脚本
document.addEventListener('DOMContentLoaded', function() {
    // 初始化节点位置
    const nodeContainers = document.querySelectorAll('.node-container');
    let yPosition = 50;
    
    nodeContainers.forEach((container, index) => {
        container.style.position = 'absolute';
        container.style.left = '50%';
        container.style.top = yPosition + 'px';
        container.style.transform = 'translateX(-50%)';
        
        // 为不同层级的节点设置不同的初始位置
        if (index % 3 === 0) {
            yPosition += 150;
        } else {
            yPosition += 100;
        }
    });
    
    // 拖拽功能
    let draggedElement = null;
    let offsetX = 0;
    let offsetY = 0;
    
    document.addEventListener('mousedown', function(e) {
        if (e.target.closest('.node')) {
            const node = e.target.closest('.node');
            const container = node.closest('.node-container');
            
            draggedElement = container;
            const rect = container.getBoundingClientRect();
            const treeRect = document.querySelector('.tree').getBoundingClientRect();
            
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            
            node.classList.add('dragging');
        }
    });
    
    document.addEventListener('mousemove', function(e) {
        if (draggedElement) {
            const treeRect = document.querySelector('.tree').getBoundingClientRect();
            const x = e.clientX - treeRect.left - offsetX;
            const y = e.clientY - treeRect.top - offsetY;
            
            // 确保节点不会被拖出可视区域
            const maxX = treeRect.width - draggedElement.offsetWidth;
            const maxY = treeRect.height - draggedElement.offsetHeight;
            
            const clampedX = Math.max(0, Math.min(maxX, x));
            const clampedY = Math.max(0, Math.min(maxY, y));
            
            draggedElement.style.left = clampedX + 'px';
            draggedElement.style.top = clampedY + 'px';
            draggedElement.style.transform = 'none';
            
            // 更新连线
            updateConnections();
        }
    });
    
    document.addEventListener('mouseup', function() {
        if (draggedElement) {
            const node = draggedElement.querySelector('.node');
            node.classList.remove('dragging');
            draggedElement = null;
        }
    });
    
    // 更新连线
    function updateConnections() {
        // 这里可以实现更复杂的连线逻辑
        // 目前保持静态连线，后续可以添加动态连线
    }
});
