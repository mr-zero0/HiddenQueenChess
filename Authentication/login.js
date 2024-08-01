document.getElementById('loginForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });

    const result = await response.json();
    if (result.success) {
        localStorage.setItem('isLoggedIn', 'true');
        window.location.href = '../GUI/Chess.html'; // Redirect to GUI
    } else {
        alert('Login failed: ' + result.message);
    }
});

document.getElementById('homeButton').addEventListener('click', function() {
    window.location.href = '../Home/home.html';
});
