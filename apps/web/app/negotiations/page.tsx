"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Clock, Check, X, Lightbulb, Home } from "lucide-react"
import { api, type Negotiation } from "@/lib/api"
import { formatPrice, formatDate } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export default function NegotiationsPage() {
  const [negotiations, setNegotiations] = useState<Negotiation[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string | undefined>(undefined)
  const [selectedNeg, setSelectedNeg] = useState<Negotiation | null>(null)

  useEffect(() => {
    loadNegotiations()
  }, [filter])

  async function loadNegotiations() {
    setLoading(true)
    try {
      const data = await api.getNegotiations(filter)
      setNegotiations(data)
    } catch (error) {
      console.error('Failed to load negotiations:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSendOffer(negId: number, offer: number, message: string) {
    try {
      await api.sendOffer(negId, offer, message)
      await loadNegotiations()
      setSelectedNeg(null)
    } catch (error) {
      console.error('Failed to send offer:', error)
      alert('Failed to send offer')
    }
  }

  async function handleRecordResponse(negId: number, sellerMessage: string, sellerCounter?: number) {
    try {
      const updated = await api.recordResponse(negId, sellerMessage, sellerCounter)
      await loadNegotiations()
      setSelectedNeg(updated)
    } catch (error) {
      console.error('Failed to record response:', error)
      alert('Failed to record response')
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Negotiations</h1>
          <p className="text-muted-foreground">AI-powered lowball offers</p>
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
          onClick={() => setFilter('awaiting')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'awaiting' ? 'bg-yellow-500 text-white hover:bg-yellow-600' : ''
          }`}
        >
          <Clock className="h-4 w-4 mr-1" /> Awaiting
        </Button>
        <Button
          onClick={() => setFilter('accepted')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'accepted' ? 'bg-green-500 text-white hover:bg-green-600' : ''
          }`}
        >
          <Check className="h-4 w-4 mr-1" /> Accepted
        </Button>
        <Button
          onClick={() => setFilter('rejected')}
          variant="secondary"
          className={`shadow-md hover:shadow-lg transition-shadow ${
            filter === 'rejected' ? 'bg-red-500 text-white hover:bg-red-600' : ''
          }`}
        >
          <X className="h-4 w-4 mr-1" /> Rejected
        </Button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
        </div>
      )}

      {/* Negotiations List */}
      {!loading && (
        <div className="space-y-3">
          {negotiations.map((neg) => (
            <div
              key={neg.id}
              onClick={() => setSelectedNeg(neg)}
              className="rounded-lg border bg-card p-4 hover:bg-accent transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">Negotiation #{neg.id}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      neg.state === 'accepted' ? 'bg-green-500/20 text-green-500' :
                      neg.state === 'awaiting' ? 'bg-yellow-500/20 text-yellow-500' :
                      neg.state === 'rejected' ? 'bg-red-500/20 text-red-500' :
                      neg.state === 'countering' ? 'bg-blue-500/20 text-blue-500' :
                      'bg-gray-500/20 text-gray-500'
                    }`}>
                      {neg.state}
                    </span>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Round {neg.round_number} • {formatDate(neg.updated_at)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">Asking: {formatPrice(neg.asking_price)}</div>
                  <div className="font-semibold">Your offer: {formatPrice(neg.current_offer)}</div>
                  <div className="text-sm text-muted-foreground">Budget: {formatPrice(neg.max_budget)}</div>
                </div>
              </div>

              {/* Message Preview */}
              {neg.messages.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <div className="text-sm text-muted-foreground">
                    Last message: {neg.messages[neg.messages.length - 1].content.slice(0, 100)}...
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && negotiations.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No negotiations yet. Start one from the Deals page.
        </div>
      )}

      {/* Detail Modal */}
      {selectedNeg && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={() => setSelectedNeg(null)}>
          <div className="bg-card rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Negotiation #{selectedNeg.id}</h2>
              <button onClick={() => setSelectedNeg(null)} className="text-muted-foreground hover:text-foreground p-1">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div>
                <div className="text-sm text-muted-foreground">Asking Price</div>
                <div className="font-semibold">{formatPrice(selectedNeg.asking_price)}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Current Offer</div>
                <div className="font-semibold">{formatPrice(selectedNeg.current_offer)}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Max Budget</div>
                <div className="font-semibold">{formatPrice(selectedNeg.max_budget)}</div>
              </div>
            </div>

            {/* Messages */}
            <div className="space-y-3 mb-6">
              <h3 className="font-semibold">Message History</h3>
              {selectedNeg.messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-primary/10 ml-8'
                      : 'bg-secondary mr-8'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold">
                      {msg.role === 'user' ? 'You' : 'Seller'}
                    </span>
                    {msg.amount && (
                      <span className="text-sm font-semibold">{formatPrice(msg.amount)}</span>
                    )}
                  </div>
                  <p className="text-sm">{msg.content}</p>
                </div>
              ))}
            </div>

            {/* Suggested Action */}
            {selectedNeg.suggested_message && (
              <div className="bg-accent p-4 rounded-lg mb-4">
                <div className="font-semibold mb-2 flex items-center gap-2"><Lightbulb className="h-4 w-4" /> Suggested Message:</div>
                <p className="text-sm mb-2">{selectedNeg.suggested_message}</p>
                {selectedNeg.suggested_offer && (
                  <div className="text-sm text-muted-foreground">
                    Suggested offer: {formatPrice(selectedNeg.suggested_offer)}
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            {selectedNeg.state === 'composing' && selectedNeg.suggested_offer && selectedNeg.suggested_message && (
              <button
                onClick={() => handleSendOffer(selectedNeg.id, selectedNeg.suggested_offer!, selectedNeg.suggested_message!)}
                className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Send Offer
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
