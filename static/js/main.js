// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Animation pour les éléments au chargement de la page
    animateElements();
    
    // Animation pour les boutons
    animateButtons();
    
    // Animation pour les cartes
    animateCards();
});

// Fonction pour animer les éléments au scroll
function animateElements() {
    // Détection du scroll pour déclencher les animations
    const animateOnScroll = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeIn');
                animateOnScroll.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    // Sélection des éléments à animer
    document.querySelectorAll('.card, .feature-icon, h2, h3, p.lead').forEach(element => {
        animateOnScroll.observe(element);
    });
}

// Fonction pour animer les boutons
function animateButtons() {
    // Animation au survol des boutons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.classList.add('animate__animated', 'animate__pulse');
        });
        
        button.addEventListener('mouseleave', function() {
            this.classList.remove('animate__animated', 'animate__pulse');
        });
    });
}

// Fonction pour animer les cartes
function animateCards() {
    // Animation au survol des cartes
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('no-hover-effect')) {
                this.style.transform = 'translateY(-10px)';
                this.style.boxShadow = '0 15px 30px rgba(0, 0, 0, 0.1)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('no-hover-effect')) {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.1)';
            }
        });
    });
}

// Fonction pour créer un effet de confetti quand un test est terminé
function showConfetti() {
    const confettiColors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'];
    const confettiCount = 200;
    const confettiContainer = document.createElement('div');
    confettiContainer.className = 'confetti-container';
    document.body.appendChild(confettiContainer);
    
    for (let i = 0; i < confettiCount; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.backgroundColor = confettiColors[Math.floor(Math.random() * confettiColors.length)];
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
        confetti.style.animationDelay = Math.random() * 2 + 's';
        confettiContainer.appendChild(confetti);
    }
    
    setTimeout(() => {
        confettiContainer.remove();
    }, 5000);
}

// Afficher le confetti sur la page des résultats
if (window.location.pathname.includes('results')) {
    setTimeout(showConfetti, 2000);
}

// Animation pour la progression du test
function updateProgressIndicator() {
    const questions = document.querySelectorAll('.question-container');
    const progress = Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100);
    document.getElementById('progress-bar').style.width = `${progress}%`;
}

// Navigation fluide entre les questions
document.querySelectorAll('.question-navigation button').forEach(button => {
    button.addEventListener('click', function() {
        const targetQuestion = document.getElementById(`question-${this.dataset.question}`);
        targetQuestion.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    });
});

// Affichage dynamique du feedback
document.querySelectorAll('.form-check-input').forEach(input => {
    input.addEventListener('change', function() {
        const feedback = this.closest('.question-container').querySelector('.answer-feedback');
        if (feedback) {
            feedback.classList.add('animate__animated', 'animate__fadeIn');
        }
    });
});