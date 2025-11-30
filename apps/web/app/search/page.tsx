"use client"

import { useState } from "react"
import Link from "next/link"
import { api, type SearchResult, type Listing, type Deal } from "@/lib/api"
import { formatPrice } from "@/lib/utils"

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [minPrice, setMinPrice] = useState("")
  const [maxPrice, setMaxPrice] = useState("")
  const [location, setLocation] = useState("")
  const [result, setResult] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDeal, setSelectedDeal] = useState<any | null>(null)
  const [dealLoading, setDealLoading] = useState(false)
  const [dealError, setDealError] = useState<string | null>(null)

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

  async function handleViewDeal(listing: Listing) {
    setDealLoading(true)
    setDealError(null)
    setSelectedDeal({ loading: true, listing })
    try {
      const result = await api.viewDeal(listing.url)
      setSelectedDeal({ ...result, listing })
    } catch (err) {
      console.error('Failed to analyze deal:', err)
      setDealError(err instanceof Error ? err.message : 'Failed to analyze deal')
      setSelectedDeal(null)
    } finally {
      setDealLoading(false)
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

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
            <h3 className="text-lg font-semibold mb-2">Searching Marketplace...</h3>
            <p className="text-sm text-muted-foreground">
              Generating query variations, scraping listings, and scoring deals
            </p>
          </div>
          
          {/* Loading Skeleton */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="rounded-lg border bg-card p-4 animate-pulse">
                <div className="aspect-video bg-muted rounded-md mb-3"></div>
                <div className="h-4 bg-muted rounded mb-2"></div>
                <div className="h-4 bg-muted rounded w-2/3 mb-2"></div>
                <div className="h-8 bg-muted rounded w-1/3 mb-3"></div>
                <div className="flex gap-2">
                  <div className="flex-1 h-9 bg-muted rounded"></div>
                  <div className="flex-1 h-9 bg-muted rounded"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && result && (
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
              <div key={listing.id} className="rounded-lg border bg-card overflow-hidden hover:bg-accent transition-colors flex flex-col">
                {listing.image_url && (
                  <div className="aspect-video bg-muted overflow-hidden">
                    <img 
                      src={listing.image_url} 
                      alt={listing.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <div className="p-4 flex flex-col flex-1">
                  <h3 className="font-semibold line-clamp-2 mb-2 text-sm">{listing.title}</h3>
                  <div className="text-2xl font-bold mb-1">{listing.price}</div>
                  {listing.location && (
                    <p className="text-xs text-muted-foreground mb-3">{listing.location}</p>
                  )}
                  {listing.description && (
                    <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{listing.description}</p>
                  )}
                  <div className="flex gap-2 mt-auto">
                    <a
                      href={listing.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 px-3 py-2 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center"
                    >
                      View on Facebook
                    </a>
                    <button
                      onClick={() => handleViewDeal(listing)}
                      className="flex-1 px-3 py-2 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-center font-semibold"
                    >
                      View Deal
                    </button>
                  </div>
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

      {/* Deal Error */}
      {dealError && (
        <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {dealError}
          <button onClick={() => setDealError(null)} className="ml-2">×</button>
        </div>
      )}

      {/* Deal Modal */}
      {selectedDeal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-card border-b p-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">
                {selectedDeal.loading ? 'Analyzing Deal...' : selectedDeal.listing?.title || selectedDeal.analysis?.title}
              </h2>
              <button
                onClick={() => setSelectedDeal(null)}
                className="text-muted-foreground hover:text-foreground text-2xl"
              >
                ×
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Loading State */}
              {selectedDeal.loading && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                  <p className="text-muted-foreground">Fetching eBay market data...</p>
                </div>
              )}

              {/* Analysis Results */}
              {!selectedDeal.loading && selectedDeal.analysis && (
                <>
                  {/* Image */}
                  {selectedDeal.listing?.image_url && (
                    <div className="rounded-lg overflow-hidden bg-muted">
                      <img 
                        src={selectedDeal.listing.image_url} 
                        alt={selectedDeal.listing.title}
                        className="w-full h-auto max-h-96 object-cover"
                      />
                    </div>
                  )}

                  {/* Rating Badge */}
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 text-sm font-bold rounded ${
                      selectedDeal.analysis.rating === 'HOT' ? 'bg-red-500 text-white' :
                      selectedDeal.analysis.rating === 'GOOD' ? 'bg-green-500 text-white' :
                      selectedDeal.analysis.rating === 'FAIR' ? 'bg-yellow-500 text-white' :
                      'bg-gray-500 text-white'
                    }`}>
                      {selectedDeal.analysis.rating}
                    </span>
                    <span className="text-muted-foreground">Score: {selectedDeal.analysis.score?.toFixed(1)}/100</span>
                    <span className="text-muted-foreground">Confidence: {selectedDeal.analysis.confidence}</span>
                  </div>

                  {/* Pricing from eBay */}
                  <div className="rounded-lg border bg-background p-4">
                    <h3 className="font-semibold mb-3">💰 eBay Market Analysis</h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Listed Price</span>
                        <span className="font-semibold text-base">{selectedDeal.listing?.price || `$${selectedDeal.analysis?.listing?.price}`}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">eBay Avg Price</span>
                        <span className="font-semibold text-base">${selectedDeal.analysis.ebay_avg_price?.toFixed(0)}</span>
                      </div>
                      <div className="flex items-center justify-between pt-3 border-t">
                        <span className="text-muted-foreground">Est. Profit</span>
                        <span className={`font-semibold text-base ${selectedDeal.analysis.profit_estimate > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {selectedDeal.analysis.profit_estimate > 0 ? '+' : ''}${selectedDeal.analysis.profit_estimate?.toFixed(0)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">ROI</span>
                        <span className={`font-semibold text-base ${selectedDeal.analysis.roi_percent > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {selectedDeal.analysis.roi_percent?.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Analysis Reason */}
                  <div className="rounded-lg border bg-background p-4">
                    <h3 className="font-semibold mb-2">📊 Analysis</h3>
                    <p className="text-sm text-muted-foreground">{selectedDeal.analysis.reason}</p>
                  </div>

                  {/* Negotiation Strategy */}
                  {selectedDeal.negotiation_strategy && (
                    <div className="rounded-lg border bg-blue-500/10 p-4">
                      <h3 className="font-semibold mb-3">🎯 Negotiation Strategy</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span>Initial Offer</span>
                          <span className="font-semibold">${selectedDeal.negotiation_strategy.initial_offer?.toFixed(0)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Target Price</span>
                          <span className="font-semibold">${selectedDeal.negotiation_strategy.target_price?.toFixed(0)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Walk Away Above</span>
                          <span className="font-semibold">${selectedDeal.negotiation_strategy.walk_away_price?.toFixed(0)}</span>
                        </div>
                        {selectedDeal.negotiation_strategy.talking_points?.length > 0 && (
                          <div className="pt-2 border-t mt-2">
                            <p className="font-medium mb-1">Talking Points:</p>
                            <ul className="list-disc list-inside text-muted-foreground">
                              {selectedDeal.negotiation_strategy.talking_points.map((point: string, i: number) => (
                                <li key={i}>{point}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Action Items */}
                  {selectedDeal.action_items?.length > 0 && (
                    <div className="rounded-lg border bg-background p-4">
                      <h3 className="font-semibold mb-3">📋 Next Steps</h3>
                      <div className="space-y-2">
                        {selectedDeal.action_items.map((item: string, i: number) => (
                          <div key={i} className="text-sm p-2 bg-muted rounded">{item}</div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <a
                      href={selectedDeal.listing?.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center font-semibold text-sm"
                    >
                      View on Facebook
                    </a>
                    <button
                      onClick={() => setSelectedDeal(null)}
                      className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 font-semibold text-sm"
                    >
                      Close
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
