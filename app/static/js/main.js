/**
 * LifeFlow Main JavaScript.
 * Handles client-side form interactions, alert dismissals, and dynamic role toggle.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flash alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });

  // Dynamic role toggle on Registration page
  const roleSelect = document.getElementById('role-select');
  const donorFields = document.getElementById('donor-specific-fields');
  const requesterFields = document.getElementById('requester-specific-fields');

  if (roleSelect && donorFields && requesterFields) {
    function toggleRoleFields() {
      const selected = roleSelect.value;
      if (selected === 'donor') {
        donorFields.style.display = 'block';
        requesterFields.style.display = 'none';
      } else if (selected === 'requester') {
        donorFields.style.display = 'none';
        requesterFields.style.display = 'block';
      } else {
        donorFields.style.display = 'none';
        requesterFields.style.display = 'none';
      }
    }

    roleSelect.addEventListener('change', toggleRoleFields);
    toggleRoleFields();
  }
});
