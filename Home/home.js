document.addEventListener('DOMContentLoaded', () => {
    console.log('Homepage loaded');

    const playChessButton = document.getElementById('playChessButton');
    const playNowButton = document.getElementById('playNowButton');

    const redirectToLogin = () => {
        alert('Please log in first.');
        window.location.href = '../Authentication/login.html';
    };

    const checkLoginAndRedirect = () => {
        if (localStorage.getItem('isLoggedIn') === 'true') {
            window.location.href = '../GUI/Chess.html';
        } else {
            redirectToLogin();
        }
    };

    if (playChessButton) {
        playChessButton.addEventListener('click', checkLoginAndRedirect);
    }

    if (playNowButton) {
        playNowButton.addEventListener('click', checkLoginAndRedirect);
    }
});
document.addEventListener('DOMContentLoaded', () => {
    const playLinks = document.querySelectorAll('a[href="../GUI/Chess.html"], a.btn-primary');

    playLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
            if (!isLoggedIn) {
                event.preventDefault();
                alert('You must be logged in to play. Please log in or sign up.');
                window.location.href = '../Authentication/login.html';
            }
        });
    });
});
document.addEventListener('DOMContentLoaded', () => {
    const playLinks = document.querySelectorAll('a[href="../GUI/Chess.html"], a.btn-primary');

    playLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
            if (!isLoggedIn) {
                event.preventDefault();
                alert('You must be logged in to play. Please log in or sign up.');
                window.location.href = '../Authentication/login.html';
            }
        });
    });
});

