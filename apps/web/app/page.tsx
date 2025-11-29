"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { api, type Deal, type Negotiation } from "@/lib/api"
import { formatPrice, formatDate } from "@/lib/utils"

export default function DashboardPage() {
  const [hotDeals, setHotDeals] = useState<Deal[]>([])
  const [negotiations, setNegotiations] = useState<Negotiation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [dealsData, negsData] = await Promise.all([
        api.getHotDeals(),
        api.getNegotiations()
      ])
      setHotDeals(dealsData.deals.slice(0, 5))
      setNegotiations(negsData.slice(0, 5))
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold">Deal Scout</h1>
          <p className="text-muted-foreground">Facebook Marketplace automation</p>
        </div>
        <nav className="flex gap-4">
          <Link href="/search" className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
            Search
          </Link>
          <Link href="/deals" className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
            Deals
          </Link>
          <Link href="/negotiations" className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
            Negotiations
          </Link>
        </nav>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border bg-card p-6">
          <div className="text-2xl font-bold">{hotDeals.length}</div>
          <p className="text-sm text-muted-foreground">Hot Deals</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <div className="text-2xl font-bold">{negotiations.filter(n => n.state === 'awaiting').length}</div>
          <p className="text-sm text-muted-foreground">Active Negotiations</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <div className="text-2xl font-bold">
            {formatPrice(hotDeals.reduce((sum, d) => sum + (d.profit_estimate || 0), 0))}
          </div>
          <p className="text-sm text-muted-foreground">Est. Profit</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <div className="text-2xl font-bold">{negotiations.filter(n => n.state === 'accepted').length}</div>
          <p className="text-sm text-muted-foreground">Deals Closed</p>
        </div>
      </div>

      {/* Hot Deals */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">🔥 Hot Deals</h2>
          <Link href="/deals" className="text-sm text-primary hover:underline">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border bg-card p-4 animate-pulse">
                <div className="h-4 bg-muted rounded mb-2 w-3/4"></div>
                <div className="h-3 bg-muted rounded mb-4 w-1/2"></div>
                <div className="h-8 bg-muted rounded w-1/3"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {hotDeals.map((deal) => (
            <div key={deal.id} className="rounded-lg border bg-card p-4 hover:bg-accent transition-colors">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h3 className="font-semibold line-clamp-2">{deal.title}</h3>
                  <p className="text-sm text-muted-foreground">{deal.location}</p>
                </div>
                <span className={`px-2 py-1 text-xs font-bold rounded ${
                  deal.deal_rating === 'HOT' ? 'bg-red-500 text-white' :
                  deal.deal_rating === 'GOOD' ? 'bg-green-500 text-white' :
                  'bg-gray-500 text-white'
                }`}>
                  {deal.deal_rating}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{deal.price}</div>
                  {deal.profit_estimate && (
                    <div className="text-sm text-green-500">+{formatPrice(deal.profit_estimate)} profit</div>
                  )}
                </div>
              </div>
              {deal.why_standout && (
                <p className="text-xs text-muted-foreground mt-2">{deal.why_standout}</p>
              )}
            </div>
          ))}
          </div>
        )}
      </div>

      {/* Recent Negotiations */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">💬 Recent Negotiations</h2>
          <Link href="/negotiations" className="text-sm text-primary hover:underline">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border bg-card p-4 animate-pulse">
                <div className="h-4 bg-muted rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-muted rounded w-1/4"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {negotiations.map((neg) => (
            <div key={neg.id} className="rounded-lg border bg-card p-4 flex items-center justify-between hover:bg-accent transition-colors">
              <div>
                <div className="font-semibold">Listing #{neg.listing_id.slice(0, 8)}</div>
                <div className="text-sm text-muted-foreground">
                  Round {neg.round_number} • {formatDate(neg.updated_at)}
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold">{formatPrice(neg.current_offer)}</div>
                <span className={`text-xs px-2 py-1 rounded ${
                  neg.state === 'accepted' ? 'bg-green-500/20 text-green-500' :
                  neg.state === 'awaiting' ? 'bg-yellow-500/20 text-yellow-500' :
                  neg.state === 'rejected' ? 'bg-red-500/20 text-red-500' :
                  'bg-gray-500/20 text-gray-500'
                }`}>
                  {neg.state}
                </span>
              </div>
            </div>
          ))}
          </div>
        )}
      </div>
    </div>
  )
}
