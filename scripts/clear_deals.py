#!/usr/bin/env python3
"""Clear deals and listings from database to repopulate with fresh eBay data."""

import asyncio
import asyncpg
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

async def clear_deals():
    database_url = os.getenv('DATABASE_URL', 'postgresql://dealscout:localdev@localhost:5432/dealscout')
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Clear deals first (foreign key constraint)
        result1 = await conn.execute('DELETE FROM deals')
        print(f'Cleared deals table: {result1}')
        
        # Clear listings
        result2 = await conn.execute('DELETE FROM listings')
        print(f'Cleared listings table: {result2}')
        
        # Clear search history
        result3 = await conn.execute('DELETE FROM search_history')
        print(f'Cleared search_history table: {result3}')
        
        await conn.close()
        print('Database cleared successfully!')
        
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(clear_deals())
