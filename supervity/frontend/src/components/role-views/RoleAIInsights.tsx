'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { ROLE_META, type AppRole } from '@/context/RoleContext'

interface Insight {
  id: string
  title: string
  description: string
  severity: 'critical' | 'warning' | 'info'
  type: string
  owner_name?: string
  owner_role?: string
  owner_id?: string
  suggested_action?: string
  consequence?: string
  confidence: number
  action_type?: string
  data?: Record<string, unknown>
  created_at: string
}

interface Forecast {
  win_rate: number
  open_pipeline: number
  predicted_revenue: number
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

function severityVariant(severity: string) {
  switch (severity) {
    case 'critical': return 'destructive'
    case 'warning': return 'secondary'
    default: return 'outline'
  }
}

export function RoleAIInsights({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const [insights, setInsights] = useState<Insight[]>([])
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null)
  const [draftEmail, setDraftEmail] = useState<{ subject: string; body: string } | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [i, f] = await Promise.all([
        apiClient.get<Insight[]>('/api/insights'),
        apiClient.get<Forecast>('/api/insights/forecast'),
      ])
      setInsights(i)
      setForecast(f)
    } catch (err) {
      console.error('Insights load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const analyze = async () => {
    setAnalyzing(true)
    try {
      await apiClient.post('/api/insights/generate')
      await load()
    } catch (err) {
      console.error('Analyze failed:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const draftReminder = async (insight: Insight) => {
    setSelectedInsight(insight)
    setDrafting(true)
    setDraftEmail(null)
    try {
      const userName = insight.owner_name || 'Team'
      const userEmail = `${userName.toLowerCase().replace(/\s+/g, '.')}@supervity.ai`
      const res = await apiClient.post<{ subject: string; body: string }>('/api/ai/draft-reminder', {
        owner_name: userName,
        owner_email: userEmail,
        insight_title: insight.title,
        insight_description: insight.description,
        suggested_action: insight.suggested_action || 'Review and act within 24 hours.',
        consequence: insight.consequence || 'The opportunity may stall without action.',
      })
      setDraftEmail({ subject: res.subject, body: res.body })
    } catch (err) {
      console.error('Reminder draft failed:', err)
      setDraftEmail({
        subject: `Follow-up required: ${insight.title}`,
        body: `Hi ${insight.owner_name || 'Team'},\n\nThis is a reminder to follow up on: ${insight.title}.\n\n${insight.description}\n\nSuggested action: ${insight.suggested_action || 'Review and act within 24 hours.'}\n\nRisk: ${insight.consequence || 'The opportunity may stall without action.'}\n\nBest,\nAutoPilot AI`,
      })
    } finally {
      setDrafting(false)
    }
  }

  const sendReminder = async () => {
    if (!draftEmail || !selectedInsight) return
    setSending(true)
    try {
      await apiClient.post('/api/workbench/send-email', {
        to: `${selectedInsight.owner_name?.toLowerCase().replace(/\s+/g, '.')}@supervity.ai`,
        subject: draftEmail.subject,
        body: draftEmail.body,
      })
      setSent(`Reminder sent to ${selectedInsight.owner_name || 'owner'}.`)
    } catch {
      setSent('Email send not wired to a real provider in this environment.')
    } finally {
      setSending(false)
      setTimeout(() => setSent(null), 4000)
    }
  }

  return (
    <motion.div className='space-y-6' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>AI Insights</h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            Follow-up reminders, potential customers, and risk if no action is taken.
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <Badge className={cn('rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide', meta.color)}>
            {meta.label}
          </Badge>
          <Button onClick={analyze} disabled={analyzing}>
            {analyzing ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.sparkles className='mr-2 h-4 w-4' />}
            Run Analysis
          </Button>
        </div>
      </motion.div>

      {sent && (
        <div className='rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700'>
          {sent}
        </div>
      )}

      {/* Forecast */}
      {forecast && (
        <motion.div variants={itemVariants} className='grid gap-4 sm:grid-cols-3'>
          <Card className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <p className='text-micro uppercase text-brand-muted'>Win Rate</p>
              <p className='font-display text-2xl font-bold text-brand-navy'>{Math.round(forecast.win_rate * 100)}%</p>
            </CardContent>
          </Card>
          <Card className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <p className='text-micro uppercase text-brand-muted'>Open Pipeline</p>
              <p className='font-display text-2xl font-bold text-brand-navy'>${Math.round(forecast.open_pipeline).toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <p className='text-micro uppercase text-brand-muted'>Predicted Revenue</p>
              <p className='font-display text-2xl font-bold text-brand-navy'>${Math.round(forecast.predicted_revenue).toLocaleString()}</p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Insights */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.lightbulb className='h-5 w-5 text-brand-cornflower' />
              Actionable Insights
            </CardTitle>
            <CardDescription>Insights tagged with an owner, suggested action, and consequence.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : insights.length === 0 ? (
              <p className='text-center text-muted-foreground'>No insights yet. Run an analysis to generate some.</p>
            ) : (
              <div className='space-y-4'>
                {insights.map((i) => (
                  <div
                    key={i.id}
                    className={cn(
                      'rounded-xl border p-4',
                      i.severity === 'critical' ? 'border-red-200 bg-red-50/30' : 'border-border/50'
                    )}
                  >
                    <div className='flex flex-wrap items-center justify-between gap-2'>
                      <div className='flex items-center gap-2'>
                        <Badge variant={severityVariant(i.severity)}>{i.severity}</Badge>
                        <span className='font-semibold text-brand-navy'>{i.title}</span>
                      </div>
                      <Button size='sm' variant='outline' onClick={() => draftReminder(i)}>
                        <Icons.mail className='mr-1.5 h-4 w-4' />
                        Draft Reminder
                      </Button>
                    </div>
                    <p className='mt-2 text-sm text-muted-foreground'>{i.description}</p>
                    <div className='mt-3 grid gap-3 sm:grid-cols-2'>
                      <div className='rounded-lg bg-muted/30 p-3 text-sm'>
                        <p className='text-xs font-semibold uppercase text-muted-foreground'>Suggested Action</p>
                        <p className='mt-1 text-foreground'>{i.suggested_action || 'No action specified.'}</p>
                      </div>
                      <div className='rounded-lg bg-muted/30 p-3 text-sm'>
                        <p className='text-xs font-semibold uppercase text-muted-foreground'>Risk of Inaction</p>
                        <p className='mt-1 text-foreground'>{i.consequence || 'No consequence specified.'}</p>
                      </div>
                    </div>
                    {i.owner_name && (
                      <p className='mt-2 text-xs text-muted-foreground'>
                        Owner: <strong>{i.owner_name}</strong> {i.owner_role && `— ${i.owner_role}`}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Reminder Email Dialog */}
      <Dialog open={!!selectedInsight} onOpenChange={(open) => !open && setSelectedInsight(null)}>
        <DialogContent className='sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>Follow-up Reminder Email</DialogTitle>
            <DialogDescription>Review and send this follow-up to {selectedInsight?.owner_name || 'the owner'}.</DialogDescription>
          </DialogHeader>
          {drafting ? (
            <div className='flex justify-center p-8'>
              <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
            </div>
          ) : (
            <div className='space-y-4'>
              <div className='space-y-2'>
                <label className='text-sm font-medium'>Subject</label>
                <input
                  type='text'
                  className='h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftEmail?.subject || ''}
                  onChange={(e) => setDraftEmail((prev) => prev ? { ...prev, subject: e.target.value } : null)}
                />
              </div>
              <div className='space-y-2'>
                <label className='text-sm font-medium'>Body</label>
                <textarea
                  className='min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftEmail?.body || ''}
                  onChange={(e) => setDraftEmail((prev) => prev ? { ...prev, body: e.target.value } : null)}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant='outline' onClick={() => setSelectedInsight(null)}>Cancel</Button>
            <Button onClick={sendReminder} disabled={drafting || sending || !draftEmail}>
              {sending ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.send className='mr-2 h-4 w-4' />}
              {sending ? 'Sending...' : 'Send Reminder'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
