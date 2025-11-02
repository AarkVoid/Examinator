// Main JavaScript file
document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-delete') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Dynamic form handling for question types
    const questionTypeSelect = document.getElementById('id_question_type');
    if (questionTypeSelect) {
        questionTypeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            // Add logic for showing/hiding form fields based on question type
            console.log('Question type changed to:', selectedType);
        });
    }
    
    // Subject-Chapter cascade
    const subjectSelect = document.getElementById('id_subject');
    const chapterSelect = document.getElementById('id_chapter');
    
    if (subjectSelect && chapterSelect) {
        subjectSelect.addEventListener('change', function() {
            const subjectId = this.value;
            
            if (subjectId) {
                fetch(`/quiz/ajax/get-chapters/?subject_id=${subjectId}`)
                    .then(response => response.json())
                    .then(data => {
                        chapterSelect.innerHTML = '<option value="">---------</option>';
                        data.chapters.forEach(chapter => {
                            chapterSelect.innerHTML += `<option value="${chapter.id}">${chapter.name}</option>`;
                        });
                    })
                    .catch(error => {
                        console.error('Error fetching chapters:', error);
                    });
            } else {
                chapterSelect.innerHTML = '<option value="">---------</option>';
            }
        });
    }
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });
    
    // Search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Implement search logic here
                console.log('Searching for:', this.value);
            }, 300);
        });
    }
    
});

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function confirmAction(message = 'Are you sure?') {
    return confirm(message);
}