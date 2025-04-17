// animation.js (amélioré)
document.addEventListener("DOMContentLoaded", function () {
    // Animation des éléments au scroll
    const animatedElements = document.querySelectorAll(".animated-on-scroll");
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const animation = entry.target.dataset.animate || "fadeInUp";
                entry.target.classList.add("animated", animation);
                // Optional: Only animate once
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.2,
        rootMargin: "0px 0px -50px 0px"
    });
    
    animatedElements.forEach(el => observer.observe(el));
    
    // Animation des cartes au survol
    const cards = document.querySelectorAll('.card:not(.no-hover)');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('card-hover');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('card-hover');
        });
    });
    
    // Animation des boutons
    const buttons = document.querySelectorAll('.btn-primary, .btn-outline-primary');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.classList.add('animated', 'pulse');
        });
        
        button.addEventListener('mouseleave', function() {
            this.classList.remove('animated', 'pulse');
        });
    });
    
    // Effet de typage pour les titres spécifiques
    const typingElements = document.querySelectorAll('.typing-effect');
    typingElements.forEach(element => {
        const text = element.textContent;
        element.textContent = '';
        
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 100);
            }
        };
        
        typeWriter();
    });
    
    // Animation de chargement des images
    const images = document.querySelectorAll('.animate-image');
    images.forEach(img => {
        img.style.opacity = '0';
        img.style.transform = 'scale(0.95)';
        
        img.onload = function() {
            setTimeout(() => {
                img.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                img.style.opacity = '1';
                img.style.transform = 'scale(1)';
            }, 100);
        };
        
        if (img.complete) {
            img.onload();
        }
    });
});

// Fonction pour créer un effet de vague au clic
function createRipple(event) {
    const button = event.currentTarget;
    
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    
    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.offsetLeft - diameter / 2}px`;
    circle.style.top = `${event.clientY - button.offsetTop - diameter / 2}px`;
    circle.classList.add('ripple');
    
    const ripple = button.querySelector('.ripple');
    if (ripple) {
        ripple.remove();
    }
    
    button.appendChild(circle);
}

// Appliquer l'effet ripple aux boutons
const buttons = document.querySelectorAll('.btn');
buttons.forEach(button => {
    button.addEventListener('click', createRipple);
});