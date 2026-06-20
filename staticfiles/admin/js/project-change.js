// ============================================================================
// ITesho - Project Change Page JavaScript
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Add tooltips to form rows
    const rows = document.querySelectorAll('.form-row');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s ease';
        });
    });
    
    // Add confirmation for delete action
    const deleteLink = document.querySelector('.deletelink');
    if (deleteLink) {
        deleteLink.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    }
    
    // Add character counter for textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        if (maxLength) {
            const counter = document.createElement('small');
            counter.className = 'char-counter';
            counter.style.cssText = 'display: block; text-align: right; font-size: 10px; color: #64748b; margin-top: 4px;';
            counter.innerText = `0 / ${maxLength} characters`;
            textarea.parentNode.appendChild(counter);
            
            textarea.addEventListener('input', function() {
                counter.innerText = `${this.value.length} / ${maxLength} characters`;
            });
        }
    });
});
