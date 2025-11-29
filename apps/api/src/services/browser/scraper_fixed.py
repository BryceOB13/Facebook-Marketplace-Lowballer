"""
Facebook Marketplace scraper - FIXED VERSION with improved extraction.
"""

SINGLE_LISTING_EXTRACTION_SCRIPT = """
(function() {
    try {
        const bodyText = document.body.innerText;
        
        // ===== TITLE EXTRACTION =====
        let title = '';
        
        // Method 1: Meta tag (most reliable)
        const ogTitle = document.querySelector('meta[property="og:title"]');
        if (ogTitle) {
            title = ogTitle.getAttribute('content') || '';
        }
        
        // Method 2: Filter h1 elements (skip Facebook UI)
        if (!title) {
            const h1Elements = document.querySelectorAll('h1');
            for (const h1 of h1Elements) {
                const text = h1.innerText.trim();
                if (text && text !== 'Notifications' && text !== 'Marketplace' && 
                    text !== 'Menu' && text.length > 5 && text.length < 200) {
                    title = text;
                    break;
                }
            }
        }
        
        // Method 3: Large font spans
        if (!title) {
            const spans = document.querySelectorAll('span');
            for (const span of spans) {
                const text = span.innerText.trim();
                if (text.length > 10 && text.length < 200 && 
                    !text.includes('$') && !text.includes('Message') &&
                    !text.includes('Share') && !text.includes('Save')) {
                    const style = window.getComputedStyle(span);
                    const fontSize = parseFloat(style.fontSize);
                    if (fontSize > 20) {
                        title = text;
                        break;
                    }
                }
            }
        }
        
        // ===== PRICE EXTRACTION =====
        let priceText = '';
        let price = 0;
        
        // Method 1: Meta tag
        const ogPrice = document.querySelector('meta[property="product:price:amount"]');
        if (ogPrice) {
            price = parseFloat(ogPrice.getAttribute('content') || '0');
            priceText = '$' + price.toLocaleString();
        }
        
        // Method 2: Find all price-formatted spans, take the most prominent
        if (price === 0) {
            const allSpans = document.querySelectorAll('span');
            const priceSpans = [];
            
            for (const span of allSpans) {
                const text = span.innerText.trim();
                if (/^\$[\d,]+$/.test(text)) {
                    const numVal = parseFloat(text.replace(/[$,]/g, ''));
                    if (numVal > 0 && numVal < 1000000) {
                        const fontSize = parseFloat(window.getComputedStyle(span).fontSize);
                        priceSpans.push({ value: numVal, text: text, fontSize: fontSize });
                    }
                }
            }
            
            if (priceSpans.length > 0) {
                priceSpans.sort((a, b) => b.fontSize - a.fontSize);
                price = priceSpans[0].value;
                priceText = priceSpans[0].text;
            }
        }
        
        // ===== DESCRIPTION EXTRACTION =====
        let description = '';
        const allDivs = document.querySelectorAll('div');
        for (const div of allDivs) {
            const text = div.innerText.trim();
            if (text.length > 50 && text.length < 2000 && 
                !text.includes('Message') && !text.includes('Share')) {
                if (text.toLowerCase().includes('condition') || 
                    text.toLowerCase().includes('working') ||
                    text.toLowerCase().includes('used') ||
                    text.toLowerCase().includes('new') ||
                    text.toLowerCase().includes('original')) {
                    description = text;
                    break;
                }
            }
        }
        
        // ===== CONDITION EXTRACTION =====
        let condition = 'USED';
        if (bodyText.includes('Used - like new')) condition = 'Used - like new';
        else if (bodyText.includes('Used - good')) condition = 'Used - good';
        else if (bodyText.includes('Used - fair')) condition = 'Used - fair';
        else if (bodyText.includes('New')) condition = 'New';
        
        // ===== LOCATION EXTRACTION =====
        let location = '';
        const locationMatch = bodyText.match(/in ([A-Za-z\s]+, [A-Z]{2})/);
        if (locationMatch) {
            location = locationMatch[1];
        } else {
            const locMatch = bodyText.match(/([A-Za-z\s]+, [A-Z]{2})\s*Location is approximate/);
            if (locMatch) {
                location = locMatch[1];
            }
        }
        
        // ===== IMAGE EXTRACTION =====
        let image = '';
        const imgEl = document.querySelector('img[src*="scontent"]');
        if (imgEl) {
            image = imgEl.src;
        }
        
        return {
            title: title,
            price: priceText,
            price_value: price,
            description: description,
            condition: condition,
            location: location,
            seller_name: '',
            image_url: image,
            url: window.location.href
        };
    } catch (e) {
        return { error: e.toString() };
    }
})()
"""
