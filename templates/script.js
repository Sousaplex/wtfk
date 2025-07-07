// Search functionality
function searchContent() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const sections = document.querySelectorAll('.section');
    
    sections.forEach(section => {
        const text = section.textContent.toLowerCase();
        if (query === '' || text.includes(query)) {
            section.style.display = 'block';
            if (query !== '') {
                highlightText(section, query);
            } else {
                removeHighlights(section);
            }
        } else {
            section.style.display = 'none';
        }
    });
}

function highlightText(element, query) {
    removeHighlights(element);
    const regex = new RegExp(`(${query})`, 'gi');
    element.innerHTML = element.innerHTML.replace(regex, '<span class="highlight">$1</span>');
}

function removeHighlights(element) {
    element.innerHTML = element.innerHTML.replace(/<span class="highlight">(.*?)<\/span>/gi, '$1');
}

// Smooth scrolling for links
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});

// TOC generation
document.addEventListener('DOMContentLoaded', function() {
    const headings = document.querySelectorAll('.main-content h1, .main-content h2, .main-content h3');
    const tocContent = document.getElementById('toc-content');
    if (tocContent) {
        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.paddingLeft = '0';
        
        headings.forEach((heading, index) => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            const id = heading.id || 'heading-' + index;
            
            if (!heading.id) {
                heading.id = id;
            }
            
            a.href = '#' + id;
            a.textContent = heading.textContent.replace(/¶/g, '').trim();
            
            li.appendChild(a);
            ul.appendChild(li);
        });
        
        tocContent.appendChild(ul);
    }
});
