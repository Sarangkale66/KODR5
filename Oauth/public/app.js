// Client-side script for OAuth Demo

document.addEventListener('DOMContentLoaded', () => {
  // Check for error in query string on login page
  const urlParams = new URLSearchParams(window.location.search);
  const error = urlParams.get('error');
  const errorEl = document.getElementById('error-message');

  if (error && errorEl) {
    errorEl.style.display = 'block';
    errorEl.textContent = `Authentication Failed: ${error}. Please check your credentials in .env.`;
  }

  // If on dashboard page, fetch user data from /api/current-user
  const profileContainer = document.getElementById('avatar');
  if (profileContainer) {
    fetch('/api/current-user')
      .then((res) => {
        if (!res.ok) {
          window.location.href = '/';
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (!data || !data.authenticated) {
          window.location.href = '/';
          return;
        }

        const user = data.user;
        document.getElementById('avatar').src = user.avatar || 'https://via.placeholder.com/150';
        document.getElementById('user-name').textContent = user.name || 'User';
        document.getElementById('user-email').textContent = user.email || 'No email provided';
        document.getElementById('provider-name').textContent = (user.provider || 'OAuth').toUpperCase();

        const jsonBox = document.getElementById('json-preview');
        if (jsonBox) {
          jsonBox.textContent = JSON.stringify(user, null, 2);
        }
      })
      .catch((err) => {
        console.error('Error fetching user info:', err);
        window.location.href = '/';
      });
  }
});
