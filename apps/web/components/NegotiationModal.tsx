"use client"

import { useState, useRef, useEffect } from 'react'
import { Zap, Scale, Smile, CheckCircle, DollarSign, X, MessageSquare, ExternalLink } from 'lucide-react'

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

interface NegotiationModalProps {
  listing: {
    id: string
    title: string
    price: number
    url: string
    market_avg?: number
  }
  bounds: NegotiationBounds
  onClose: () => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  type?: 'suggestion' | 'sent' | 'received' | 'info'
}

const OPENING_TEMPLATES = [
  { label: "Friendly Interest", template: "Hey! Is this still available? Really interested in the {item}." },
  { label: "Direct Offer", template: "Hi! Would you consider ${offer} for the {item}?" },
  { label: "Question First", template: "Hey, what condition is this in? Any issues I should know about?" },
  { label: "Bundle Ask", template: "Hi! Interested in the {item}. Would you do ${offer} if I pick up today?" },
  { label: "Casual", template: "Hey is this available? Been looking for one of these" },
]

const STRATEGY_OPTIONS = [
  { value: 'shrewd', label: 'Shrewd', desc: 'Aggressive - start at 50%', initial: 0.50 },
  { value: 'moderate', label: 'Moderate', desc: 'Balanced - start at 70%', initial: 0.70 },
  { value: 'lenient', label: 'Lenient', desc: 'Easy-going - start at 85%', initial: 0.85 },
  { value: 'accept', label: 'Accept', desc: 'Just buy it at listed price', initial: 1.0 },
]

export function NegotiationModal({ listing, bounds, onClose }: NegotiationModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [customOffer, setCustomOffer] = useState(bounds.initial_offer)
  const [isSending, setIsSending] = useState(false)
  const [showTemplates, setShowTemplates] = useState(true)
  const [strategy, setStrategy] = useState(bounds.strategy_tier)
  const [currentBounds, setCurrentBounds] = useState(bounds)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleStrategyChange = async (newStrategy: string) => {
    setStrategy(newStrategy)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiBase}/api/negotiate/bounds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asking_price: listing.price,
          market_avg: listing.market_avg || listing.price * 1.3,
          deal_rating: 'FAIR',
          user_strategy: newStrategy
        })
      })
      if (res.ok) {
        const newBounds = await res.json()
        setCurrentBounds(newBounds)
        setCustomOffer(newBounds.initial_offer)
        addMessage('system', `Strategy changed to ${newBounds.strategy_name}. New initial offer: $${newBounds.initial_offer}`, 'info')
      }
    } catch {
      console.error('Failed to update strategy')
    }
  }

  useEffect(() => {
    setMessages([{
      id: '1',
      role: 'system',
      content: `Ready to negotiate for "${listing.title}". Choose an opening message or write your own.`,
      timestamp: new Date(),
      type: 'info'
    }])
  }, [listing.title])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = (role: ChatMessage['role'], content: string, type?: ChatMessage['type']) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role, content, timestamp: new Date(), type }])
  }

  const applyTemplate = (template: string) => {
    const filled = template
      .replace('{item}', listing.title.split(' ').slice(0, 4).join(' '))
      .replace('{offer}', customOffer.toString())
    setInputValue(filled)
    setShowTemplates(false)
    inputRef.current?.focus()
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return
    const messageToSend = inputValue.trim()
    setInputValue('')
    setIsSending(true)
    addMessage('user', messageToSend, 'suggestion')
    
    const offerMatch = messageToSend.match(/\$(\d+)/)
    const offerAmount = offerMatch ? parseInt(offerMatch[1]) : null
    
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBase}/api/negotiate/send-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ listing_url: listing.url, message: messageToSend, offer_amount: offerAmount })
      })
      
      if (response.ok) {
        addMessage('assistant', 'Message typed into Facebook. Click Send when ready.', 'info')
        if (offerAmount) addMessage('system', `Offer: $${offerAmount} | Walk-away: $${bounds.walk_away_price}`, 'info')
      } else {
        addMessage('assistant', 'Failed. Make sure Chrome is open to the listing.', 'info')
      }
    } catch {
      addMessage('assistant', 'Connection error. Is the API running?', 'info')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage() }
  }

  const suggestCounter = () => {
    const nextOffer = Math.min(customOffer + (listing.price * 0.05), bounds.walk_away_price)
    setInputValue(`How about $${Math.round(nextOffer)}? That's the best I can do.`)
    setCustomOffer(Math.round(nextOffer))
    inputRef.current?.focus()
  }

  const suggestWalkAway = () => {
    setInputValue("Thanks for your time, but that's more than I can do. Good luck!")
    inputRef.current?.focus()
  }

  return (
    <div className="fixed inset-0 w-screen h-screen bg-background z-[100]" style={{ margin: 0 }}>
      <div className="h-full w-full flex flex-col">
        <div className="border-b border-border p-4 flex items-center justify-between shrink-0 bg-card">
          <div>
            <h2 className="text-lg font-bold text-foreground">Negotiation Assistant</h2>
            <p className="text-sm text-muted-foreground truncate max-w-lg">{listing.title}</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-2 hover:bg-muted rounded-md">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="bg-primary/10 p-3 border-b border-border shrink-0">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <select 
                value={strategy}
                onChange={(e) => handleStrategyChange(e.target.value)}
                className="font-medium text-foreground bg-transparent border border-border rounded px-2 py-1 text-sm cursor-pointer"
              >
                {STRATEGY_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <span className="text-muted-foreground">Listed: ${listing.price}</span>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span style={{ color: 'var(--color-tertiary)' }}>Start: ${currentBounds.initial_offer}</span>
              <span style={{ color: 'var(--color-accent)' }}>Target: ${currentBounds.target_price}</span>
              <span className="text-destructive">Max: ${currentBounds.walk_away_price}</span>
            </div>
          </div>
        </div>

        <div className="p-3 border-b border-border bg-muted shrink-0">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-foreground">Your Offer:</label>
            <input type="range" min={currentBounds.initial_offer * 0.8} max={currentBounds.walk_away_price} value={customOffer}
              onChange={(e) => setCustomOffer(parseInt(e.target.value))} className="flex-1 accent-primary" />
            <input type="number" value={customOffer} onChange={(e) => setCustomOffer(parseInt(e.target.value) || currentBounds.initial_offer)}
              className="w-20 px-2 py-1 border border-border rounded text-center text-sm bg-input text-foreground" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 bg-background">
          <div className="max-w-3xl mx-auto space-y-3">
          {showTemplates && (
            <div className="bg-card rounded-lg p-4 border border-border">
              <h3 className="text-sm font-medium mb-3 text-foreground">Choose an opening message:</h3>
              <div className="space-y-2">
                {OPENING_TEMPLATES.map((t, i) => (
                  <button key={i} onClick={() => applyTemplate(t.template)}
                    className="w-full text-left p-3 rounded-lg border border-border hover:bg-primary/10 text-sm">
                    <span className="font-medium text-primary">{t.label}</span>
                    <p className="text-muted-foreground mt-1">
                      {t.template.replace('{item}', listing.title.split(' ').slice(0, 3).join(' ')).replace('{offer}', customOffer.toString())}
                    </p>
                  </button>
                ))}
              </div>
              <button onClick={() => setShowTemplates(false)} className="mt-3 text-sm text-muted-foreground hover:text-foreground">
                Or write your own ↓
              </button>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user' ? 'bg-primary text-primary-foreground' 
                : msg.role === 'system' ? 'bg-muted text-muted-foreground text-sm'
                : 'bg-card text-card-foreground border border-border'
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                <span className="text-xs opacity-70 mt-1 block">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-border p-2 flex gap-2 shrink-0 bg-muted">
          <button onClick={suggestCounter} className="px-3 py-1.5 text-xs bg-accent/20 text-accent-foreground rounded-full hover:bg-accent/30 flex items-center gap-1">
            <DollarSign className="h-3 w-3" />
            Counter
          </button>
          <button onClick={suggestWalkAway} className="px-3 py-1.5 text-xs bg-destructive/20 text-destructive rounded-full hover:bg-destructive/30 flex items-center gap-1">
            <X className="h-3 w-3" />
            Walk Away
          </button>
          <button onClick={() => setShowTemplates(true)} className="px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded-full flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            Templates
          </button>
          <a href={listing.url} target="_blank" rel="noopener noreferrer"
            className="px-3 py-1.5 text-xs bg-primary/20 text-primary rounded-full ml-auto flex items-center gap-1">
            <ExternalLink className="h-3 w-3" />
            Open FB
          </a>
        </div>

        <div className="border-t border-border p-3 shrink-0 bg-card">
          <div className="flex gap-2">
            <textarea ref={inputRef} value={inputValue} onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown} placeholder="Type your message... (Enter to send)"
              className="flex-1 px-3 py-2 border border-border rounded-lg resize-none text-sm bg-input text-foreground placeholder:text-muted-foreground"
              rows={2} disabled={isSending} />
            <button onClick={handleSendMessage} disabled={!inputValue.trim() || isSending}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 font-medium text-sm">
              {isSending ? '...' : 'Type in FB'}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Types into Facebook Messenger. You click Send.</p>
        </div>
      </div>
    </div>
  )
}
