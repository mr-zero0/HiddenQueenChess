document.getElementById('signupForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });

    const result = await response.json();
    if (result.success) {
        alert('Signup successful! You can now log in.');
        window.location.href = 'login.html'; // Redirect to login
    } else {
        alert('Signup failed: ' + result.message);
    }
});

document.getElementById('homeButton').addEventListener('click', function() {
    window.location.href = '../Home/home.html';
});
