// Handle user search functionality
document.addEventListener('DOMContentLoaded', function() {
    const userSearch = document.getElementById('user_search');
    if (userSearch) {
        userSearch.addEventListener('input', function() {
            const query = this.value.trim();
            const resultsContainer = document.getElementById('user_search_results');
            
            if (query.length < 2) {
                resultsContainer.classList.add('d-none');
                return;
            }
            
            fetch(`/api/search_users?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    resultsContainer.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(user => {
                            const userElement = document.createElement('button');
                            userElement.type = 'button';
                            userElement.className = 'list-group-item list-group-item-action';
                            userElement.textContent = `${user.username} (${user.email})`;
                            userElement.onclick = function() {
                                document.getElementById('user_id').value = user.id;
                                userSearch.value = `${user.username} (${user.email})`;
                                resultsContainer.classList.add('d-none');
                            };
                            resultsContainer.appendChild(userElement);
                        });
                        resultsContainer.classList.remove('d-none');
                    } else {
                        resultsContainer.innerHTML = `
                            <div class="list-group-item">
                                No se encontraron usuarios
                            </div>`;
                        resultsContainer.classList.remove('d-none');
                    }
                })
                .catch(error => {
                    console.error('Error searching users:', error);
                    resultsContainer.innerHTML = `
                        <div class="list-group-item text-danger">
                            Error al buscar usuarios
                        </div>`;
                    resultsContainer.classList.remove('d-none');
                });
        });
    }

    // Handle loan form submission
    document.querySelectorAll('.loan-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            // Disable button and show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                Procesando...
            `;
            
            // Get CSRF token from meta tag
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            // Add CSRF token to form data
            formData.append('csrf_token', csrfToken);
            
            // Send form data
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    const successAlert = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                    
                    // Insert alert before the form
                    this.insertAdjacentHTML('beforebegin', successAlert);
                    
                    // Reset form and close modal after 1.5 seconds
                    setTimeout(() => {
                        this.reset();
                        const modal = bootstrap.Modal.getInstance(this.closest('.modal'));
                        if (modal) modal.hide();
                        
                        // Reload the page to update the book availability
                        window.location.reload();
                    }, 1500);
                } else {
                    // Show error message
                    const errorAlert = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            ${data.message || 'Error al procesar el préstamo'}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                    
                    // Insert alert before the form
                    this.insertAdjacentHTML('beforebegin', errorAlert);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const errorMessage = error.message || 'Ocurrió un error al procesar la solicitud';
                
                // Show error message
                const errorAlert = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        ${errorMessage}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;
                
                // Insert alert before the form
                this.insertAdjacentHTML('beforebegin', errorAlert);
            })
            .finally(() => {
                // Re-enable button and restore original text
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            });
        });
    });

    // --- Load movement history in modal ---
    document.querySelectorAll('[id^="historyBookModal"]').forEach(modalEl => {
        modalEl.addEventListener('show.bs.modal', function(event) {
            const bookId = this.id.replace('historyBookModal', '');
            const container = document.getElementById(`movements-${bookId}`);
            const loadingDiv = container.querySelector('.loading-movements');
            const contentDiv = container.querySelector('.movements-content');
            const errorDiv = container.querySelector('.error-movements');
            
            // Show loading, hide content and error
            loadingDiv.classList.remove('d-none');
            contentDiv.classList.add('d-none');
            errorDiv.classList.add('d-none');
            
            // Fetch movement history
            fetch(`/api/books/${bookId}/movements`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Error al cargar el historial');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.length === 0) {
                        contentDiv.innerHTML = `
                            <div class="alert alert-info mb-0">
                                No hay movimientos registrados para este libro.
                            </div>`;
                    } else {
                        // Build movements table
                        let html = `
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>Fecha</th>
                                            <th>Tipo</th>
                                            <th>Usuario</th>
                                            <th>Detalles</th>
                                        </tr>
                                    </thead>
                                    <tbody>`;
                        
                        data.forEach(movement => {
                            const date = new Date(movement.created_at).toLocaleString();
                            const typeClass = movement.type === 'loan' ? 'text-success' : 'text-danger';
                            const typeText = movement.type === 'loan' ? 'Préstamo' : 'Devolución';
                            
                            html += `
                                <tr>
                                    <td>${date}</td>
                                    <td><span class="badge ${typeClass}">${typeText}</span></td>
                                    <td>${movement.user_name || 'Sistema'}</td>
                                    <td>${movement.details || '-'}</td>
                                </tr>`;
                        });
                        
                        html += `
                                    </tbody>
                                </table>
                            </div>`;
                        
                        contentDiv.innerHTML = html;
                    }
                    
                    // Show content, hide loading
                    contentDiv.classList.remove('d-none');
                    loadingDiv.classList.add('d-none');
                })
                .catch(error => {
                    console.error('Error loading movement history:', error);
                    
                    // Show error, hide loading
                    errorDiv.textContent = 'Error al cargar el historial de movimientos';
                    errorDiv.classList.remove('d-none');
                    loadingDiv.classList.add('d-none');
                });
        });
    });
});

// Date validation for loan forms
document.addEventListener('DOMContentLoaded', function() {
    // Set minimum date to today for loan date inputs
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('.loan-date-input').forEach(input => {
        input.min = today;
        input.value = today;
        
        // When loan date changes, update due date min value
        input.addEventListener('change', function() {
            const dueDateInput = this.closest('.modal').querySelector('.due-date-input');
            dueDateInput.min = this.value;
            
            // If current due date is before the new loan date, update it
            if (dueDateInput.value < this.value) {
                const dueDate = new Date(this.value);
                dueDate.setDate(dueDate.getDate() + 14); // Default to 14 days
                dueDateInput.value = dueDate.toISOString().split('T')[0];
            }
        });
    });
    
    // Set default due date to 14 days from today
    document.querySelectorAll('.due-date-input').forEach(input => {
        if (!input.value) {
            const dueDate = new Date();
            dueDate.setDate(dueDate.getDate() + 14);
            input.value = dueDate.toISOString().split('T')[0];
        }
        input.min = today;
    });
});
