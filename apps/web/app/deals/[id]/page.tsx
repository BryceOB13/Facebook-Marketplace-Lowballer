"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { DollarSign, BarChart3, Target } from "lucide-react"
import { api, type Deal, type ViewDealResult } from "@/lib/api"
import { formatPrice } from "@/lib/utils"

export default function DealDetailPage({ params }: { params: { id: string } }) {
  const [deal, setDeal] = useState<Deal | null>(null)
  const [analysis, setAnalysis] = useState<ViewDealResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDeal()
  }, [params.id])

  async function loadDeal() {
    try {
      const dealData = await api.getDeal(params.id)
      setDeal(dealData)
      // Auto-analyze with eBay data
      if (dealData.url) {
        setAnalyzing(true)
        try {
          const analysisData = await api.viewDeal(dealData.url)
          setAnalysis(analysisData)
        } catch (err) {
          console.error('Failed to analyze deal:', err)
        } finally {
          setAnalyzing(false)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deal')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
          <p className="text-muted-foreground">Loading deal...</p>
        </div>
      </div>
    )
  }

  if (error || !deal) {
    return (
      <div className="container mx-auto p-6">
        <div className="rounded-lg border border-red-500 bg-red-500/10 p-4 text-red-500 mb-4">
          {error || 'Deal not found'}
        </div>
        <Link href="/search" className="text-primary hover:underline">
          ← Back to Search
        </Link>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{deal.title}</h1>
          <p className="text-muted-foreground">{deal.location}</p>
        </div>
        <Link href="/search" className="text-sm text-primary hover:underline">
          ← Back to Search
        </Link>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Image */}
        <div className="md:col-span-1">
          {deal.image_url && (
            <div className="rounded-lg overflow-hidden bg-muted">
              <img 
                src={deal.image_url} 
                alt={deal.title}
                className="w-full h-auto"
              />
            </div>
          )}
        </div>

        {/* Deal Info */}
        <div className="md:col-span-2 space-y-6">
          {/* Analyzing State */}
          {analyzing && (
            <div className="rounded-lg border bg-card p-6 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-2"></div>
              <p className="text-muted-foreground">Fetching eBay market data...</p>
            </div>
          )}

          {/* eBay Analysis Results */}
          {analysis && (
            <>
              {/* Rating Badge */}
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 text-sm font-bold rounded ${
                  analysis.analysis.rating === 'HOT' ? 'bg-red-500 text-white' :
                  analysis.analysis.rating === 'GOOD' ? 'bg-green-500 text-white' :
                  analysis.analysis.rating === 'FAIR' ? 'bg-yellow-500 text-white' :
                  'bg-gray-500 text-white'
                }`}>
                  {analysis.analysis.rating}
                </span>
                <span className="text-muted-foreground">Score: {analysis.analysis.score?.toFixed(1)}/100</span>
                <span className="text-muted-foreground">Confidence: {analysis.analysis.confidence}</span>
              </div>

              {/* eBay Market Analysis */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><DollarSign className="h-5 w-5" /> eBay Market Analysis</h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Listed Price</span>
                    <span className="text-2xl font-bold">{deal.price}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">eBay Avg Price</span>
                    <span className="text-xl">${analysis.analysis.ebay_avg_price?.toFixed(0)}</span>
                  </div>
                  <div className="flex items-center justify-between pt-3 border-t">
                    <span className="text-muted-foreground">Est. Profit</span>
                    <span className={`text-xl font-semibold ${analysis.analysis.profit_estimate > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {analysis.analysis.profit_estimate > 0 ? '+' : ''}${analysis.analysis.profit_estimate?.toFixed(0)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">ROI</span>
                    <span className={`text-xl font-semibold ${analysis.analysis.roi_percent > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {analysis.analysis.roi_percent?.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Analysis Reason */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-2 flex items-center gap-2"><BarChart3 className="h-5 w-5" /> Analysis</h2>
                <p className="text-muted-foreground">{analysis.analysis.reason}</p>
              </div>

              {/* Negotiation Strategy */}
              {analysis.negotiation_strategy && (
                <div className="rounded-lg border bg-blue-500/10 p-6">
                  <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Target className="h-5 w-5" /> Negotiation Strategy</h2>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span>Initial Offer</span>
                      <span className="font-semibold">${analysis.negotiation_strategy.initial_offer?.toFixed(0)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Target Price</span>
                      <span className="font-semibold">${analysis.negotiation_strategy.target_price?.toFixed(0)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Walk Away Above</span>
                      <span className="font-semibold">${analysis.negotiation_strategy.walk_away_price?.toFixed(0)}</span>
                    </div>
                    {analysis.negotiation_strategy.talking_points?.length > 0 && (
                      <div className="pt-3 border-t">
                        <p className="font-medium mb-2">Talking Points:</p>
                        <ul className="list-disc list-inside text-muted-foreground space-y-1">
                          {analysis.negotiation_strategy.talking_points.map((point: string, i: number) => (
                            <li key={i}>{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action Items */}
              {analysis.action_items?.length > 0 && (
                <div className="rounded-lg border bg-card p-6">
                  <h2 className="text-lg font-semibold mb-4">📋 Next Steps</h2>
                  <div className="space-y-2">
                    {analysis.action_items.map((item: string, i: number) => (
                      <div key={i} className="p-2 bg-muted rounded">{item}</div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Fallback: Basic deal info if no analysis */}
          {!analysis && !analyzing && (
            <>
              {/* Price Section */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">Pricing</h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Listed Price</span>
                    <span className="text-2xl font-bold">{deal.price}</span>
                  </div>
                  {deal.ebay_avg_price && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Market Value (eBay)</span>
                      <span className="text-xl">{formatPrice(deal.ebay_avg_price)}</span>
                    </div>
                  )}
                  {deal.profit_estimate && (
                    <div className="flex items-center justify-between pt-3 border-t">
                      <span className="text-muted-foreground">Est. Profit</span>
                      <span className="text-xl font-semibold text-green-500">
                        +{formatPrice(deal.profit_estimate)}
                      </span>
                    </div>
                  )}
                  {deal.roi_percent && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">ROI</span>
                      <span className="text-xl font-semibold text-green-500">
                        {deal.roi_percent.toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Deal Rating */}
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">Deal Rating</h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Rating</span>
                    <span className={`px-3 py-1 text-sm font-bold rounded ${
                      deal.deal_rating === 'HOT' ? 'bg-red-500 text-white' :
                      deal.deal_rating === 'GOOD' ? 'bg-green-500 text-white' :
                      deal.deal_rating === 'FAIR' ? 'bg-yellow-500 text-white' :
                      'bg-gray-500 text-white'
                    }`}>
                      {deal.deal_rating}
                    </span>
                  </div>
                  {deal.match_score && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Match Score</span>
                      <span className="text-lg font-semibold">
                        {Math.max(0, Math.min((deal.match_score * 100), 100)).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {deal.category && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Category</span>
                      <span className="text-lg">{deal.category}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Why Standout */}
              {deal.why_standout && (
                <div className="rounded-lg border bg-card p-6">
                  <h2 className="text-lg font-semibold mb-2">Why It Stands Out</h2>
                  <p className="text-muted-foreground">{deal.why_standout}</p>
                </div>
              )}
            </>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <a
              href={deal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 px-6 py-3 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 text-center font-semibold"
            >
              View on Facebook
            </a>
            <Link
              href={`/negotiations?listing_id=${deal.id}`}
              className="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-center font-semibold"
            >
              Start Negotiation
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
