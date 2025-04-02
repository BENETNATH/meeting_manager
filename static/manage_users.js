document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.delete-user-btn');
    const table = document.querySelector('table');
    const message = table.dataset.confirmMessage;

    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            if (confirm(message)) {
                const form = this.closest('form');
                form.submit();
            }
        });
    });
});
