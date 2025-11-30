"""
Facebook Marketplace scraper - FIXED VERSION with improved extraction.
"""

SINGLE_LISTING_EXTRACTION_SCRIPT = r"""
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
        
        // ===== PRICE EXTRACTION =====
        let priceText = '';
        let price = 0;
        let originalPrice = 0;
        
        // Method 1: Meta tag
        const ogPrice = document.querySelector('meta[property="product:price:amount"]');
        if (ogPrice) {
            price = parseFloat(ogPrice.getAttribute('content') || '0');
            priceText = '$' + price.toLocaleString();
        }
        
        // Method 2: Find the FIRST price on the page
        // Facebook shows current price first, then strikethrough original price
        if (price === 0) {
            const allPrices = bodyText.match(/\$[\d,]+/g) || [];
            if (allPrices.length > 0) {
                const firstPrice = parseFloat(allPrices[0].replace(/[$,]/g, ''));
                
                if (allPrices.length > 1) {
                    const secondPrice = parseFloat(allPrices[1].replace(/[$,]/g, ''));
                    if (secondPrice > firstPrice && secondPrice < firstPrice * 3) {
                        price = firstPrice;
                        originalPrice = secondPrice;
                    } else {
                        price = firstPrice;
                    }
                } else {
                    price = firstPrice;
                }
                priceText = '$' + price.toLocaleString();
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
