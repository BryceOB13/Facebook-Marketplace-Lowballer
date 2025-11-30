"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { api, type Deal } from "@/lib/api"
import { formatPrice } from "@/lib/utils"

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string | undefined>(undefined)

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

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Scored Deals</h1>
          <p className="text-muted-foreground">AI-evaluated marketplace opportunities</p>
        </div>
        <Link href="/" className="text-sm text-primary hover:underline">
          ← Back to Dashboard
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter(undefined)}
          className={`px-4 py-2 rounded-md ${
            filter === undefined
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('HOT')}
          className={`px-4 py-2 rounded-md ${
            filter === 'HOT'
              ? 'bg-red-500 text-white'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
          }`}
        >
          🔥 HOT
        </button>
        <button
          onClick={() => setFilter('GOOD')}
          className={`px-4 py-2 rounded-md ${
            filter === 'GOOD'
              ? 'bg-green-500 text-white'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
          }`}
        >
          ✓ GOOD
        </button>
        <button
          onClick={() => setFilter('FAIR')}
          className={`px-4 py-2 rounded-md ${
            filter === 'FAIR'
              ? 'bg-yellow-500 text-white'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
          }`}
        >
          ~ FAIR
        </button>
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
            <div key={deal.id} className="rounded-lg border bg-card p-4 hover:bg-accent transition-colors">
              {deal.image_url && (
                <div className="aspect-video bg-muted rounded-md mb-3 overflow-hidden">
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

              <div className="flex gap-2">
                <a
                  href={deal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center"
                >
                  View
                </a>
                <Link
                  href={`/negotiations/new?listing_id=${deal.id}`}
                  className="flex-1 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-center"
                >
                  Negotiate
                </Link>
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
    </div>
  )
}
