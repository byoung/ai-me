function setupScrollHandler() {
    // Set up observer once page loads
    setTimeout(() => {
        const chatbot = document.querySelector('#main-chatbot');
        
        if (!chatbot) {
            return;
        }
        
        let lastScrollTime = 0;
        const SCROLL_DELAY = 100; // Minimum ms between scroll attempts
        
        // Create observer to watch for pending bubble
        const observer = new MutationObserver((mutations) => {
            const now = Date.now();
            
            // Only process if enough time has passed since last scroll
            if (now - lastScrollTime < SCROLL_DELAY) {
                return;
            }
            
            // Look for pending bubble
            const pending = document.querySelector('.message.bot.pending.bubble');
            
            if (pending) {
                lastScrollTime = now;
                pending.scrollIntoView({ 
                    behavior: 'instant', 
                    block: 'nearest'
                });
            }
        });
        
        // Start observing with subtree to catch nested messages
        observer.observe(chatbot, {
            childList: true,
            subtree: true
        });
    }, 1000);
}

setupScrollHandler();
