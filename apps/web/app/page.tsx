"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Flame, MessageCircle, X, TrendingUp, Handshake, CheckCircle, Search, LayoutGrid } from "lucide-react"
import { api, type Deal, type Negotiation } from "@/lib/api"
import { formatPrice, formatDate } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export default function DashboardPage() {
  const [hotDeals, setHotDeals] = useState<Deal[]>([])
  const [negotiations, setNegotiations] = useState<Negotiation[]>([])
  const [loading, setLoading] = useState(true)
  const [dismissedDeals, setDismissedDeals] = useState<Set<string>>(new Set())

  function dismissDeal(dealId: string) {
    setDismissedDeals(prev => new Set([...prev, dealId]))
  }

  const visibleDeals = hotDeals.filter(deal => !dismissedDeals.has(deal.id))

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
        <nav className="flex gap-2">
          <Button asChild>
            <Link href="/search">
              <Search className="h-4 w-4 mr-2" />
              Search
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/deals">
              <LayoutGrid className="h-4 w-4 mr-2" />
              Deals
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/negotiations">
              <Handshake className="h-4 w-4 mr-2" />
              Negotiations
            </Link>
          </Button>
        </nav>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="group relative rounded-xl border bg-gradient-to-br from-card to-card/80 p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Hot Deals</p>
              <div className="text-3xl font-bold tracking-tight">{visibleDeals.length}</div>
            </div>
            <div className="p-3 rounded-full bg-red-500/10 text-red-500">
              <Flame className="h-6 w-6" />
            </div>
          </div>
          <div className="relative mt-3 pt-3 border-t border-border/50">
            <span className="text-xs text-muted-foreground">Ready to negotiate</span>
          </div>
        </div>

        <div className="group relative rounded-xl border bg-gradient-to-br from-card to-card/80 p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Active Negotiations</p>
              <div className="text-3xl font-bold tracking-tight">{negotiations.filter(n => n.state === 'awaiting').length}</div>
            </div>
            <div className="p-3 rounded-full bg-yellow-500/10 text-yellow-500">
              <Handshake className="h-6 w-6" />
            </div>
          </div>
          <div className="relative mt-3 pt-3 border-t border-border/50">
            <span className="text-xs text-muted-foreground">Awaiting response</span>
          </div>
        </div>

        <div className="group relative rounded-xl border bg-gradient-to-br from-card to-card/80 p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Est. Profit</p>
              <div className="text-3xl font-bold tracking-tight text-green-500">
                {formatPrice(visibleDeals.reduce((sum, d) => sum + (d.profit_estimate || 0), 0))}
              </div>
            </div>
            <div className="p-3 rounded-full bg-green-500/10 text-green-500">
              <TrendingUp className="h-6 w-6" />
            </div>
          </div>
          <div className="relative mt-3 pt-3 border-t border-border/50">
            <span className="text-xs text-muted-foreground">From visible deals</span>
          </div>
        </div>

        <div className="group relative rounded-xl border bg-gradient-to-br from-card to-card/80 p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Deals Closed</p>
              <div className="text-3xl font-bold tracking-tight">{negotiations.filter(n => n.state === 'accepted').length}</div>
            </div>
            <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
              <CheckCircle className="h-6 w-6" />
            </div>
          </div>
          <div className="relative mt-3 pt-3 border-t border-border/50">
            <span className="text-xs text-muted-foreground">Successfully negotiated</span>
          </div>
        </div>
      </div>

      {/* Hot Deals */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold flex items-center gap-2"><Flame className="h-6 w-6 text-red-500" /> Hot Deals</h2>
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
            {visibleDeals.map((deal) => (
            <div key={deal.id} className="rounded-lg border bg-card overflow-hidden hover:bg-accent transition-colors relative group">
              <button
                onClick={() => dismissDeal(deal.id)}
                className="absolute top-2 right-2 z-10 p-1 rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                title="Dismiss deal"
              >
                <X className="h-4 w-4" />
              </button>
              {deal.image_url && (
                <img 
                  src={deal.image_url} 
                  alt={deal.title}
                  className="w-full h-auto object-contain bg-muted"
                />
              )}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold line-clamp-2">{deal.title}</h3>
                    <p className="text-sm text-muted-foreground">{deal.location}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-bold rounded ml-2 ${
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
                  <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{deal.why_standout}</p>
                )}
              </div>
            </div>
          ))}
          </div>
        )}
      </div>

      {/* Recent Negotiations */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold flex items-center gap-2"><MessageCircle className="h-6 w-6 text-blue-500" /> Recent Negotiations</h2>
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
