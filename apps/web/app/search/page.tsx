"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { DollarSign, BarChart3, Target, MessageSquare, ClipboardList, X, Home, Search, MapPin, ChevronDown, SlidersHorizontal } from "lucide-react"
import { api, type SearchResult, type Listing, type Deal } from "@/lib/api"
import { formatPrice } from "@/lib/utils"
import { searchCities } from "@/lib/cities"
import { NegotiationModal } from "@/components/NegotiationModal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface NegotiationBounds {
  strategy_name: string
  strategy_tier: string
  initial_offer: number
  target_price: number
  walk_away_price: number
  max_increase_per_round_pct: number
  tone_guidance: string
  opening_approach: string
}

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
  const [negotiationId, setNegotiationId] = useState<string | null>(null)
  const [negotiationBounds, setNegotiationBounds] = useState<NegotiationBounds | null>(null)
  const [negotiationListing, setNegotiationListing] = useState<any | null>(null)
  const [citySuggestions, setCitySuggestions] = useState<string[]>([])
  const [showCitySuggestions, setShowCitySuggestions] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [searchVariationIndex, setSearchVariationIndex] = useState(0)
  const locationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (locationRef.current && !locationRef.current.contains(event.target as Node)) {
        setShowCitySuggestions(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  function handleLocationChange(value: string) {
    setLocation(value)
    const suggestions = searchCities(value)
    setCitySuggestions(suggestions)
    setShowCitySuggestions(suggestions.length > 0)
  }

  function selectCity(city: string) {
    setLocation(city)
    setShowCitySuggestions(false)
  }

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
      setSearchVariationIndex(0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleLoadMore() {
    if (!result || loadingMore) return
    
    setLoadingMore(true)
    
    // Generate variation queries based on original query
    const variations = [
      query + " used",
      query + " like new",
      query + " cheap",
      query.split(' ').reverse().join(' '),
      query + " deal",
      query + " sale",
    ]
    
    const nextIndex = (searchVariationIndex + 1) % variations.length
    const variationQuery = variations[nextIndex]
    
    try {
      const moreResults = await api.search({
        query: variationQuery,
        min_price: minPrice ? parseInt(minPrice) : undefined,
        max_price: maxPrice ? parseInt(maxPrice) : undefined,
        location: location.trim() || undefined
      })
      
      // Merge new listings, avoiding duplicates by ID
      const existingIds = new Set(result.listings.map(l => l.id))
      const newListings = moreResults.listings.filter(l => !existingIds.has(l.id))
      
      setResult({
        ...result,
        listings: [...result.listings, ...newListings],
        total_count: result.total_count + newListings.length
      })
      setSearchVariationIndex(nextIndex)
    } catch (err) {
      console.error('Failed to load more:', err)
    } finally {
      setLoadingMore(false)
    }
  }

  async function handleViewDeal(listing: Listing) {
    setDealLoading(true)
    setDealError(null)
    setSelectedDeal({ loading: true, listing })
    try {
      // Pass the known price as fallback for the backend
      const result = await api.viewDeal(listing.url, listing.price_value)
      setSelectedDeal({ ...result, listing })
    } catch (err) {
      console.error('Failed to analyze deal:', err)
      setDealError(err instanceof Error ? err.message : 'Failed to analyze deal')
      setSelectedDeal(null)
    } finally {
      setDealLoading(false)
    }
  }

  async function handleStartNegotiation(dealData: any) {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    try {
      // Get negotiation bounds only - no auto-start
      const boundsRes = await fetch(`${apiBase}/api/negotiate/bounds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asking_price: dealData.listing?.price_value || dealData.analysis?.listing?.price || 0,
          market_avg: dealData.analysis?.ebay_avg_price || 0,
          deal_rating: dealData.analysis?.rating || 'FAIR',
          listing_age_days: null
        })
      })
      const bounds = await boundsRes.json()
      
      // Set up negotiation modal with bounds (no auto-start)
      setNegotiationBounds(bounds)
      setNegotiationListing({
        id: dealData.listing?.id,
        title: dealData.listing?.title,
        price: dealData.listing?.price_value,
        url: dealData.listing?.url,
        market_avg: dealData.analysis?.ebay_avg_price || 0
      })
      setSelectedDeal(null) // Close the deal modal
      
    } catch (err) {
      console.error('Failed to start negotiation:', err)
      alert('Failed to start negotiation. Please try again.')
    }
  }

  function closeNegotiation() {
    setNegotiationId(null)
    setNegotiationBounds(null)
    setNegotiationListing(null)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Search Marketplace</h1>
          <p className="text-muted-foreground">Find deals with AI-powered query expansion</p>
        </div>
        <Button variant="ghost" asChild>
          <Link href="/">
            <Home className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>
        </Button>
      </div>

      {/* Main Search */}
      <Card className="shadow-xl border-2">
        <CardContent className="p-6">
          <form onSubmit={handleSearch} className="space-y-4">
            {/* Prominent Search Bar */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                id="query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you looking for? e.g., 'macbook pro', 'ps5', 'iphone 14'"
                disabled={loading}
                className="h-14 pl-12 text-lg rounded-xl shadow-inner"
              />
            </div>

            {/* Collapsible Filters */}
            <Collapsible open={filtersOpen} onOpenChange={setFiltersOpen}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" type="button" className="w-full justify-between text-muted-foreground hover:text-foreground">
                  <span className="flex items-center gap-2">
                    <SlidersHorizontal className="h-4 w-4" />
                    Advanced Filters
                    {(minPrice || maxPrice || location) && (
                      <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                        {[minPrice && `$${minPrice}`, maxPrice && `$${maxPrice}`, location].filter(Boolean).join(' • ')}
                      </span>
                    )}
                  </span>
                  <ChevronDown className={`h-4 w-4 transition-transform ${filtersOpen ? 'rotate-180' : ''}`} />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-4 space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-4 md:col-span-1">
                    <div className="flex items-center justify-between">
                      <Label>Price Range</Label>
                      <span className="text-sm text-muted-foreground">
                        ${minPrice || 0} - ${maxPrice || 2000}
                      </span>
                    </div>
                    <Slider
                      defaultValue={[0, 2000]}
                      value={[parseInt(minPrice) || 0, parseInt(maxPrice) || 2000]}
                      onValueChange={([min, max]) => {
                        setMinPrice(min.toString())
                        setMaxPrice(max.toString())
                      }}
                      max={5000}
                      step={50}
                      disabled={loading}
                      className="py-2"
                    />
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <Label htmlFor="minPrice" className="text-xs text-muted-foreground">Min</Label>
                        <Input
                          id="minPrice"
                          type="number"
                          value={minPrice}
                          onChange={(e) => setMinPrice(e.target.value)}
                          placeholder="$0"
                          disabled={loading}
                          className="h-8 text-sm"
                        />
                      </div>
                      <div className="flex-1">
                        <Label htmlFor="maxPrice" className="text-xs text-muted-foreground">Max</Label>
                        <Input
                          id="maxPrice"
                          type="number"
                          value={maxPrice}
                          onChange={(e) => setMaxPrice(e.target.value)}
                          placeholder="$2000"
                          disabled={loading}
                          className="h-8 text-sm"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2 relative" ref={locationRef}>
                    <Label htmlFor="location">Location</Label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="location"
                        type="text"
                        value={location}
                        onChange={(e) => handleLocationChange(e.target.value)}
                        onFocus={() => citySuggestions.length > 0 && setShowCitySuggestions(true)}
                        placeholder="Start typing a city..."
                        disabled={loading}
                        className="pl-9"
                      />
                    </div>
                    {showCitySuggestions && citySuggestions.length > 0 && (
                      <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-auto">
                        {citySuggestions.map((city) => (
                          <button
                            key={city}
                            type="button"
                            onClick={() => selectCity(city)}
                            className="w-full px-3 py-2 text-left text-sm hover:bg-accent flex items-center gap-2"
                          >
                            <MapPin className="h-3 w-3 text-muted-foreground" />
                            {city}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>

            <Button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full shadow-md hover:shadow-lg transition-shadow"
              size="lg"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search Marketplace
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

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
        <div className="space-y-6">
          {/* Listings Grid - 4 columns */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {result.listings.map((listing) => (
              <Card key={listing.id} className="overflow-hidden hover:shadow-xl transition-shadow flex flex-col">
                {listing.image_url && (
                  <div className="aspect-square bg-muted overflow-hidden">
                    <img 
                      src={listing.image_url} 
                      alt={listing.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <CardContent className="p-4 flex flex-col flex-1">
                  <h3 className="font-semibold line-clamp-2 mb-2 text-sm">{listing.title}</h3>
                  <div className="text-2xl font-bold mb-1">{listing.price}</div>
                  {listing.location && (
                    <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {listing.location}
                    </p>
                  )}
                  {listing.description && (
                    <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{listing.description}</p>
                  )}
                  <div className="flex gap-2 mt-auto">
                    <Button variant="secondary" size="sm" asChild className="flex-1">
                      <a href={listing.url} target="_blank" rel="noopener noreferrer">
                        View on FB
                      </a>
                    </Button>
                    <Button size="sm" onClick={() => handleViewDeal(listing)} className="flex-1">
                      View Deal
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {result.listings.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No listings found. Try adjusting your search criteria.
            </div>
          )}

          {/* Load More Button */}
          {result.listings.length > 0 && (
            <div className="flex justify-center pt-4">
              <Button
                variant="outline"
                size="lg"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-8"
              >
                {loadingMore ? (
                  <>
                    <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Finding more...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Find Similar Listings
                  </>
                )}
              </Button>
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

      {/* Deal Modal - Full Screen */}
      {selectedDeal && (
        <div className="fixed inset-0 w-screen h-screen bg-background z-[90]" style={{ margin: 0 }}>
          <div className="h-full w-full flex flex-col">
            <div className="shrink-0 bg-card border-b p-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">
                {selectedDeal.loading ? 'Analyzing Deal...' : selectedDeal.listing?.title || selectedDeal.analysis?.title}
              </h2>
              <Button variant="ghost" size="icon" onClick={() => setSelectedDeal(null)}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto space-y-6">
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
                  {/* Image - Full width */}
                  {selectedDeal.listing?.image_url && (
                    <div className="rounded-lg overflow-hidden bg-muted">
                      <img 
                        src={selectedDeal.listing.image_url} 
                        alt={selectedDeal.listing.title}
                        className="w-full h-auto object-contain max-h-[60vh]"
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
                    <h3 className="font-semibold mb-3 flex items-center gap-2"><DollarSign className="h-4 w-4" /> eBay Market Analysis</h3>
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
                    <h3 className="font-semibold mb-2 flex items-center gap-2"><BarChart3 className="h-4 w-4" /> Analysis</h3>
                    <p className="text-sm text-muted-foreground">{selectedDeal.analysis.reason}</p>
                  </div>

                  {/* Negotiation Strategy */}
                  {selectedDeal.negotiation_strategy && (
                    <div className="rounded-lg border bg-blue-500/10 p-4">
                      <h3 className="font-semibold mb-3 flex items-center gap-2"><Target className="h-4 w-4" /> Negotiation Strategy</h3>
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
                      onClick={() => handleStartNegotiation(selectedDeal)}
                      className="flex-1 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 font-semibold text-sm"
                    >
                      <MessageSquare className="h-4 w-4 inline mr-1" /> Start Negotiation
                    </button>
                  </div>
                </>
              )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Negotiation Modal */}
      {negotiationBounds && negotiationListing && (
        <NegotiationModal
          listing={negotiationListing}
          bounds={negotiationBounds}
          onClose={closeNegotiation}
        />
      )}
    </div>
  )
}
