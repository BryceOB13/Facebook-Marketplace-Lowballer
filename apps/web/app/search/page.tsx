"use client"

import { useState } from "react"
import Link from "next/link"
import { api, type SearchResult, type Listing } from "@/lib/api"
import { formatPrice } from "@/lib/utils"

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [minPrice, setMinPrice] = useState("")
  const [maxPrice, setMaxPrice] = useState("")
  const [location, setLocation] = useState("")
  const [result, setResult] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)

    try {
      const searchResult = await api.search({
        query: query.trim(),
        min_price: minPrice ? parseInt(minPrice) : undefined,
        max_price: maxPrice ? parseInt(maxPrice) : undefined,
        location: location.trim() || undefined
      })
      setResult(searchResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Search Marketplace</h1>
          <p className="text-muted-foreground">Find deals with AI-powered query expansion</p>
        </div>
        <Link href="/" className="text-sm text-primary hover:underline">
          ← Back to Dashboard
        </Link>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="rounded-lg border bg-card p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Search Query</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., 'macbook pro', 'ps5', 'iphone 14'"
            className="w-full px-4 py-2 rounded-md border bg-background"
            disabled={loading}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium mb-2">Min Price</label>
            <input
              type="number"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="$0"
              className="w-full px-4 py-2 rounded-md border bg-background"
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Max Price</label>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="$1000"
              className="w-full px-4 py-2 rounded-md border bg-background"
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="San Francisco, CA"
              className="w-full px-4 py-2 rounded-md border bg-background"
              disabled={loading}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
        >
          {loading ? 'Searching...' : 'Search Marketplace'}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500 bg-red-500/10 p-4 text-red-500">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Metadata */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div>
              Found {result.total_count} listings in {result.search_time_ms?.toFixed(0)}ms
              {result.cached && ' (cached)'}
            </div>
            {result.query_variations.length > 1 && (
              <div>
                Searched: {result.query_variations.join(', ')}
              </div>
            )}
          </div>

          {/* Listings Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {result.listings.map((listing) => (
              <div key={listing.id} className="rounded-lg border bg-card p-4 hover:bg-accent transition-colors">
                {listing.image_url && (
                  <div className="aspect-video bg-muted rounded-md mb-3 overflow-hidden">
                    <img 
                      src={listing.image_url} 
                      alt={listing.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <h3 className="font-semibold line-clamp-2 mb-2">{listing.title}</h3>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-2xl font-bold">{listing.price}</div>
                </div>
                {listing.location && (
                  <p className="text-sm text-muted-foreground mb-3">{listing.location}</p>
                )}
                <div className="flex gap-2">
                  <a
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 px-3 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center"
                  >
                    View on Facebook
                  </a>
                  <Link
                    href={`/deals/${listing.id}`}
                    className="flex-1 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-center"
                  >
                    Score Deal
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {result.listings.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No listings found. Try adjusting your search criteria.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
