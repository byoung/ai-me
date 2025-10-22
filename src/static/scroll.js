function setupScrollHandler() {
    // Set up observer once page loads
    setTimeout(() => {
        const chatbot = document.querySelector('#main-chatbot');
        
        if (!chatbot) {
            return;
        }
        
        // Create observer to watch for pending bubble
        const observer = new MutationObserver((mutations) => {
            // Look for pending bubble
            const pending = document.querySelector('.message.bot.pending.bubble');
            
            if (pending) {
                // Scroll to the pending message using instant scroll to avoid layout thrashing
                pending.scrollIntoView({ 
                    behavior: 'instant', 
                    block: 'nearest'
                });
            }
        });
        
        // Start observing
        observer.observe(chatbot, {
            childList: true,
            subtree: true
        });
    }, 1000);
}

setupScrollHandler();
