"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Flame, Check, DollarSign, BarChart3, Target, MessageSquare, X, Home, Minus } from "lucide-react"
import { api, type Deal, type ViewDealResult } from "@/lib/api"
import { formatPrice } from "@/lib/utils"
import { NegotiationModal } from "@/components/NegotiationModal"
import { Button } from "@/components/ui/button"

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

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string | undefined>(undefined)
  const [selectedDeal, setSelectedDeal] = useState<any | null>(null)
  const [dealLoading, setDealLoading] = useState(false)
  const [negotiationId, setNegotiationId] = useState<string | null>(null)
  const [negotiationBounds, setNegotiationBounds] = useState<NegotiationBounds | null>(null)
  const [negotiationListing, setNegotiationListing] = useState<any | null>(null)

  useEffect(() => {
    loadDeals()
  }, [filter])

  async function loadDeals() {
    setLoading(true)
    try {
      const data = await api.getDeals(filter)
      setDeals(data)
    } catch (error) {
      console.error('Failed to load deals:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleViewDeal(deal: Deal) {
    setDealLoading(true)
    setSelectedDeal({ loading: true, deal })
    try {
      const result = await api.viewDeal(deal.url, deal.price_value)
      setSelectedDeal({ ...result, deal })
    } catch (err) {
      console.error('Failed to analyze deal:', err)
      setSelectedDeal(null)
    } finally {
      setDealLoading(false)
    }
  }

  async function handleNegotiateFromCard(deal: Deal) {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    try {
      // Get negotiation bounds using existing deal data
      const boundsRes = await fetch(`${apiBase}/api/negotiate/bounds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asking_price: deal.price_value,
          market_avg: deal.ebay_avg_price || deal.price_value * 1.3,
          deal_rating: deal.deal_rating || 'FAIR',
          listing_age_days: null
        })
      })
      const bounds = await boundsRes.json()
      
      // Open negotiation modal directly
      setNegotiationBounds(bounds)
      setNegotiationListing({
        id: deal.id,
        title: deal.title,
        price: deal.price_value,
        url: deal.url,
        market_avg: deal.ebay_avg_price || 0
      })
      
    } catch (err) {
      console.error('Failed to start negotiation:', err)
      alert('Failed to start negotiation. Please try again.')
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
          asking_price: dealData.deal?.price_value || dealData.listing?.price,
          market_avg: dealData.analysis?.ebay_avg_price || 0,
          deal_rating: dealData.analysis?.rating || 'FAIR',
          listing_age_days: null
        })
      })
      const bounds = await boundsRes.json()
      
      // Set up negotiation modal with bounds (no auto-start)
      setNegotiationBounds(bounds)
      setNegotiationListing({
        id: dealData.deal?.id,
        title: dealData.deal?.title || dealData.listing?.title,
        price: dealData.deal?.price_value || dealData.listing?.price,
        url: dealData.deal?.url,
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
          <h1 className="text-3xl font-bold">Scored Deals</h1>
          <p className="text-muted-foreground">AI-evaluated marketplace opportunities</p>
        </div>
        <Button variant="ghost" asChild>
          <Link href="/">
            <Home className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <Button
          onClick={() => setFilter(undefined)}
          variant={filter === undefined ? "default" : "secondary"}
          className="shadow-md hover:shadow-lg transition-shadow"
        >
          All
        </Button>
        <Button
          onClick={() => setFilter('HOT')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'HOT' ? 'bg-red-500 text-white hover:bg-red-600' : ''
          }`}
        >
          <Flame className="h-4 w-4 mr-1" /> HOT
        </Button>
        <Button
          onClick={() => setFilter('GOOD')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'GOOD' ? 'bg-green-500 text-white hover:bg-green-600' : ''
          }`}
        >
          <Check className="h-4 w-4 mr-1" /> GOOD
        </Button>
        <Button
          onClick={() => setFilter('FAIR')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'FAIR' ? 'bg-yellow-500 text-white hover:bg-yellow-600' : ''
          }`}
        >
          <Minus className="h-4 w-4 mr-1" /> FAIR
        </Button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
        </div>
      )}

      {/* Deals Grid */}
      {!loading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {deals.map((deal) => (
            <div 
              key={deal.id} 
              className="rounded-lg border bg-card p-4 hover:bg-accent transition-colors cursor-pointer"
              onClick={() => handleViewDeal(deal)}
            >
              {deal.image_url && (
                <div className="aspect-square bg-muted rounded-md mb-3 overflow-hidden">
                  <img 
                    src={deal.image_url} 
                    alt={deal.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold line-clamp-2 flex-1">{deal.title}</h3>
                <span className={`px-2 py-1 text-xs font-bold rounded ml-2 ${
                  deal.deal_rating === 'HOT' ? 'bg-red-500 text-white' :
                  deal.deal_rating === 'GOOD' ? 'bg-green-500 text-white' :
                  deal.deal_rating === 'FAIR' ? 'bg-yellow-500 text-white' :
                  'bg-gray-500 text-white'
                }`}>
                  {deal.deal_rating}
                </span>
              </div>

              <div className="space-y-2 mb-3">
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">{deal.price}</span>
                  {deal.ebay_avg_price && (
                    <span className="text-sm text-muted-foreground">
                      Avg: {formatPrice(deal.ebay_avg_price)}
                    </span>
                  )}
                </div>

                {deal.profit_estimate !== undefined && deal.profit_estimate !== null && (
                  <div className="flex items-center justify-between text-sm">
                    <span className={`font-semibold ${deal.profit_estimate >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {deal.profit_estimate >= 0 ? '+' : ''}{formatPrice(deal.profit_estimate)} profit
                    </span>
                    {deal.roi_percent !== undefined && deal.roi_percent !== null && (
                      <span className={`${deal.roi_percent >= 0 ? 'text-muted-foreground' : 'text-red-500'}`}>
                        {deal.roi_percent.toFixed(0)}% ROI
                      </span>
                    )}
                  </div>
                )}

                {deal.location && (
                  <p className="text-sm text-muted-foreground">{deal.location}</p>
                )}

                {deal.why_standout && (
                  <p className="text-xs text-muted-foreground border-t pt-2">
                    {deal.why_standout}
                  </p>
                )}
              </div>

              <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                <a
                  href={deal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center"
                >
                  View on FB
                </a>
                <button
                  onClick={() => handleNegotiateFromCard(deal)}
                  className="flex-1 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-center"
                >
                  Negotiate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && deals.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No deals found. Try running a search first.
        </div>
      )}

      {/* Deal Analysis Modal */}
      {selectedDeal && (
        <div className="fixed top-0 left-0 right-0 bottom-0 w-screen h-screen bg-black/60 flex items-center justify-center z-[90] p-4" style={{ margin: 0 }} onClick={() => setSelectedDeal(null)}>
          <div className="bg-card rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-border" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-card border-b p-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">
                {selectedDeal.loading ? 'Analyzing Deal...' : selectedDeal.deal?.title}
              </h2>
              <button onClick={() => setSelectedDeal(null)} className="text-muted-foreground hover:text-foreground p-1"><X className="h-5 w-5" /></button>
            </div>

            <div className="p-6 space-y-6">
              {selectedDeal.loading && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                  <p className="text-muted-foreground">Fetching eBay market data...</p>
                </div>
              )}

              {!selectedDeal.loading && selectedDeal.analysis && (
                <>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 text-sm font-bold rounded ${
                      selectedDeal.analysis.rating === 'HOT' ? 'bg-red-500 text-white' :
                      selectedDeal.analysis.rating === 'GOOD' ? 'bg-green-500 text-white' :
                      selectedDeal.analysis.rating === 'FAIR' ? 'bg-yellow-500 text-white' :
                      'bg-gray-500 text-white'
                    }`}>{selectedDeal.analysis.rating}</span>
                    <span className="text-muted-foreground">Score: {selectedDeal.analysis.score?.toFixed(1)}/100</span>
                  </div>

                  <div className="rounded-lg border bg-background p-4">
                    <h3 className="font-semibold mb-3 flex items-center gap-2"><DollarSign className="h-4 w-4" /> eBay Market Analysis</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Listed Price</span>
                        <span className="font-semibold">{selectedDeal.deal?.price}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">eBay Avg Price</span>
                        <span className="font-semibold">${selectedDeal.analysis.ebay_avg_price?.toFixed(0)}</span>
                      </div>
                      <div className="flex justify-between pt-2 border-t">
                        <span className="text-muted-foreground">Est. Profit</span>
                        <span className={`font-semibold ${selectedDeal.analysis.profit_estimate > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {selectedDeal.analysis.profit_estimate > 0 ? '+' : ''}${selectedDeal.analysis.profit_estimate?.toFixed(0)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">ROI</span>
                        <span className={`font-semibold ${selectedDeal.analysis.roi_percent > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {selectedDeal.analysis.roi_percent?.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border bg-background p-4">
                    <h3 className="font-semibold mb-2 flex items-center gap-2"><BarChart3 className="h-4 w-4" /> Analysis</h3>
                    <p className="text-sm text-muted-foreground">{selectedDeal.analysis.reason}</p>
                  </div>

                  {selectedDeal.negotiation_strategy && (
                    <div className="rounded-lg border bg-blue-500/10 p-4">
                      <h3 className="font-semibold mb-3 flex items-center gap-2"><Target className="h-4 w-4" /> Negotiation Strategy</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between"><span>Initial Offer</span><span className="font-semibold">${selectedDeal.negotiation_strategy.initial_offer?.toFixed(0)}</span></div>
                        <div className="flex justify-between"><span>Target Price</span><span className="font-semibold">${selectedDeal.negotiation_strategy.target_price?.toFixed(0)}</span></div>
                        <div className="flex justify-between"><span>Walk Away Above</span><span className="font-semibold">${selectedDeal.negotiation_strategy.walk_away_price?.toFixed(0)}</span></div>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <a href={selectedDeal.deal?.url} target="_blank" rel="noopener noreferrer" className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center font-semibold text-sm">View on Facebook</a>
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
