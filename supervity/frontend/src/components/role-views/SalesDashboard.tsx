'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useRole, ROLE_META } from '@/context/RoleContext'
import type { AppRole } from '@/context/RoleContext'

interface DashboardStats {
  total_leads: number
  active_opportunities: number
  pipeline_value: number
  win_rate: number
  active_sdrs: number
  total_activities: number
  pending_exceptions: number
  active_policies: number
}

interface Policy {
  id: string
  name: string
  natural_language: string
  is_active: boolean
  priority: number
}

interface Lead {
  id: string
  first_name: string | null
  last_name: string | null
  email: string | null
  account_name: string | null
  lead_stage: string | null
  owner_name: string | null
}

interface AccountDetail {
  id: string
  name: string | null
  industry: string | null
  number_of_employees: number | null
  type: string | null
  website: string | null
  billing_country: string | null
  strategic: boolean | null
}

interface VisitorActivity {
  id: number
  visitor_id: string | null
  type: string | null
  created_at: string | null
  url: string | null
  duration_seconds: number | null
  campaign: string | null
  source: string | null
  company_domain: string | null
  channel: string | null
}

interface SentEmail {
  id: number
  subject: string
  body: string
  sent_at: string
  sent_by: string
}

interface ContactContext {
  id: number
  type: string
  content: string
  generated_by: string
  priority: number
  created_at: string
}

interface Learning {
  id: number
  category: string
  insight: string
  source: string
  confidence: number
  sample_text: string | null
  reviewed: boolean
}

interface ContactDetail {
  id: string
  first_name: string | null
  last_name: string | null
  email: string | null
  phone: string | null
  title: string | null
  account_name: string | null
  lead_source: string | null
  lead_stage: string | null
  owner_name: string | null
  owner_id: string | null
  has_opted_out_of_email: boolean
  do_not_call: boolean
  consent_basis: string | null
  region: string | null
  confidence: number | null
  created_date: string | null
  last_activity_date: string | null
  account: AccountDetail | null
  recent_activities: VisitorActivity[]
  emails: SentEmail[]
  intent_score: number
  intent_signals: string[]
  privacy_status: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

const ALLOWED_STAGES: Record<AppRole, string[]> = {
  sdr: ['Open'],
  sales_agent: ['MQL', 'Opportunity'],
  manager: ['SQL'],
  admin: ['Open', 'MQL', 'Opportunity', 'SQL'],
  cro: ['Open', 'MQL', 'Opportunity', 'SQL', 'Customer'],
}

export function SalesDashboard({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const { activeUserId } = useRole()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [leads, setLeads] = useState<Lead[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [detailLead, setDetailLead] = useState<Lead | null>(null)
  const [detail, setDetail] = useState<ContactDetail | null>(null)
  const [contexts, setContexts] = useState<ContactContext[]>([])
  const [learnings, setLearnings] = useState<Learning[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [draftSubject, setDraftSubject] = useState('')
  const [draftBody, setDraftBody] = useState('')
  const [isDrafting, setIsDrafting] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendNotice, setSendNotice] = useState<string | null>(null)
  const [stageValue, setStageValue] = useState('')
  const [stageSaving, setStageSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const qs = activeUserId ? `?viewer_role=${role}&viewer_id=${activeUserId}` : ''
      const limitQs = activeUserId ? `&limit=20` : `?limit=20`
      const [s, l, p] = await Promise.all([
        apiClient.get<DashboardStats>(`/api/dashboard/stats${qs}`),
        apiClient.get<Lead[]>(`/api/contacts${qs}${limitQs}`),
        apiClient.get<Policy[]>('/api/policies?limit=20'),
      ])
      setStats(s)
      setLeads(l)
      setPolicies(p.filter((pol: Policy) => pol.is_active).slice(0, 5))
    } catch (err) {
      console.error('Sales dashboard load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [role, activeUserId])

  useEffect(() => {
    load()
  }, [load])

  const handleView = async (lead: Lead) => {
    setDetailLead(lead)
    setDetail(null)
    setContexts([])
    setLearnings([])
    setStageValue(lead.lead_stage || 'Open')
    setDetailLoading(true)
    try {
      const [d, ctxRes, learnRes] = await Promise.all([
        apiClient.get<ContactDetail>(`/api/contacts/${lead.id}`),
        apiClient.get<{ contexts: ContactContext[] }>(`/api/contacts/${lead.id}/context`),
        apiClient.get<{ learnings: Learning[] }>(`/api/contacts/${lead.id}/learnings`),
      ])
      setDetail(d)
      setContexts(ctxRes.contexts)
      setLearnings(learnRes.learnings)
      // If no learnings yet, generate them in the background
      if (learnRes.learnings.length === 0) {
        apiClient.post<{ learnings: Learning[] }>(`/api/contacts/${lead.id}/learn`)
          .then((res) => setLearnings(res.learnings))
          .catch((err) => console.error('Background learning failed:', err))
      }
    } catch (err) {
      console.error('Failed to load contact detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleDraft = async (lead: Lead | ContactDetail) => {
    setDetail(null)
    setDetailLead(null)
    setSelectedLead({
      id: lead.id,
      first_name: lead.first_name,
      last_name: lead.last_name,
      email: lead.email,
      account_name: (lead as ContactDetail).account?.name || lead.account_name,
      lead_stage: lead.lead_stage,
      owner_name: lead.owner_name,
    })
    setDraftSubject('')
    setDraftBody('')
    setIsDrafting(true)
    try {
      const payload: Record<string, unknown> = {
        role: meta.label,
        lead_stage: lead.lead_stage,
      }
      if ('intent_score' in lead) {
        payload.intent_score = lead.intent_score
        payload.intent_signals = lead.intent_signals
      }
      const res = await apiClient.post<{ subject: string; body: string }>(`/api/contacts/${lead.id}/draft`, payload)
      setDraftSubject(res.subject)
      setDraftBody(res.body)
    } catch (err) {
      console.error('Draft failed:', err)
      setDraftBody('Failed to draft email.')
    } finally {
      setIsDrafting(false)
    }
  }

  const handleSend = async () => {
    setIsSending(true)
    try {
      const res = await apiClient.post<{ status: string; to: string; smtp_success: boolean }>(`/api/contacts/${selectedLead?.id}/send-email`, {
        subject: draftSubject,
        body: draftBody,
      })
      const notice = `Email ${res.status} to ${res.to || `${selectedLead?.first_name || ''} ${selectedLead?.last_name || ''}`.trim()}${res.smtp_success ? '' : ' (SMTP not configured — queued)'}`
      setSendNotice(notice)
      setSelectedLead(null)
    } catch (err) {
      console.error('Send failed:', err)
      setSendNotice('Failed to send email.')
    } finally {
      setIsSending(false)
      setTimeout(() => setSendNotice(null), 4000)
    }
  }

  const handleStageChange = async () => {
    if (!detail || !detailLead) return
    setStageSaving(true)
    try {
      await apiClient.put(`/api/contacts/${detail.id}/stage`, { lead_stage: stageValue })
      setDetail({ ...detail, lead_stage: stageValue })
      setLeads((prev) => prev.map((l) => (l.id === detail.id ? { ...l, lead_stage: stageValue } : l)))
    } catch (err) {
      console.error('Stage change failed:', err)
    } finally {
      setStageSaving(false)
    }
  }

  const visibleLeads = useMemo(() => {
    const allowed = ALLOWED_STAGES[role]
    return leads.filter((l) => allowed.includes(l.lead_stage || ''))
  }, [leads, role])

  const togglePolicy = async (id: string, current: boolean) => {
    try {
      await apiClient.patch(`/api/policies/${id}/toggle`)
      setPolicies((prev) => prev.map((p) => (p.id === id ? { ...p, is_active: !current } : p)))
    } catch (err) {
      console.error('Toggle policy failed:', err)
    }
  }

  const kpiCards = [
    { title: 'Total Leads', value: stats?.total_leads ?? 0, icon: Icons.users, color: 'bg-blue-500' },
    { title: 'Active Policies', value: stats?.active_policies ?? 0, icon: Icons.brain, color: 'bg-purple-500' },
    { title: 'Open Pipeline', value: `$${Math.round(stats?.pipeline_value ?? 0).toLocaleString()}`, icon: Icons.trendingUp, color: 'bg-emerald-500', isText: true },
    { title: 'Active Opps', value: stats?.active_opportunities ?? 0, icon: Icons.activity, color: 'bg-amber-500' },
  ]

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex items-center justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
            {meta.label} Dashboard
          </h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            {role === 'sdr' && 'Qualify new leads, review visitor activity, and move them to MQL.'}
            {role === 'sales_agent' && 'Convert MQLs into opportunities and pitch Supervity.'}
            {role === 'manager' && 'Close SQLs and coach the team on high-intent deals.'}
            {role === 'cro' && 'Oversee pipeline, revenue, and AI policy performance across all roles.'}
            {role === 'admin' && 'KPIs, new leads, and active policies for your role.'}
          </p>
        </div>
        <Badge
          className={cn(
            'rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide',
            meta.color
          )}
        >
          {meta.label}
        </Badge>
      </motion.div>

      {sendNotice && (
        <div className='rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700'>
          {sendNotice}
        </div>
      )}

      {/* KPI Cards */}
      <motion.div variants={itemVariants} className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
        {kpiCards.map((card) => (
          <Card key={card.title} className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <div className='flex items-start justify-between'>
                <div className='space-y-2'>
                  <p className='text-micro uppercase text-brand-muted'>{card.title}</p>
                  <p className='font-display text-2xl font-bold text-brand-navy'>
                    {card.isText ? card.value : (card.value as number).toLocaleString()}
                  </p>
                </div>
                <div className={cn('rounded-xl p-2.5 text-white shadow-lg', card.color)}>
                  <card.icon className='h-5 w-5' strokeWidth={1.5} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </motion.div>

      {/* Active AI Policies showcase */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.brain className='h-5 w-5 text-brand-primary' />
              AI Policies in Action
            </CardTitle>
            <CardDescription>These active policies are currently routing, scoring, and communicating with leads.</CardDescription>
          </CardHeader>
          <CardContent>
            {policies.length === 0 ? (
              <p className='text-sm text-muted-foreground'>No active AI policies.</p>
            ) : (
              <div className='flex flex-wrap gap-2'>
                {policies.map((p) => (
                  <Badge key={p.id} variant='outline' className='px-2.5 py-1 text-xs'>
                    {p.name}
                  </Badge>
                ))}
                <Badge className='bg-brand-cornflower/20 px-2.5 py-1 text-xs text-brand-navy'>
                  {visibleLeads.length} leads matched this view
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* New Leads */}
      <motion.div variants={itemVariants}>
        <Card className='overflow-hidden'>
          <CardHeader className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
            <div>
              <CardTitle className='flex items-center gap-2'>
                <Icons.users className='h-5 w-5 text-brand-primary' />
                Total New Leads
              </CardTitle>
              <CardDescription>Draft and send emails directly from the dashboard.</CardDescription>
            </div>
            <Button variant='outline' size='sm' onClick={load} disabled={loading}>
              {loading ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.refresh className='mr-2 h-4 w-4' />}
              Refresh
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : visibleLeads.length === 0 ? (
              <p className='text-center text-muted-foreground'>No leads found for {meta.label} stage view.</p>
            ) : (
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                    <tr>
                      <th className='py-3 px-4 font-medium'>Name</th>
                      <th className='py-3 px-4 font-medium'>Email</th>
                      <th className='py-3 px-4 font-medium'>Company</th>
                      <th className='py-3 px-4 font-medium'>Stage</th>
                      <th className='py-3 px-4 font-medium'>Owner</th>
                      <th className='py-3 px-4 font-medium text-right'>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleLeads.map((lead) => (
                      <tr key={lead.id} className='border-b last:border-0 hover:bg-slate-50'>
                        <td className='py-3 px-4 font-medium text-brand-navy'>
                          {lead.first_name} {lead.last_name}
                        </td>
                        <td className='py-3 px-4 text-muted-foreground'>{lead.email}</td>
                        <td className='py-3 px-4'>{lead.account_name || '-'}</td>
                        <td className='py-3 px-4'>
                          <Badge variant='outline'>{lead.lead_stage || 'Unknown'}</Badge>
                        </td>
                        <td className='py-3 px-4'>{lead.owner_name || 'Unassigned'}</td>
                        <td className='py-3 px-4 text-right'>
                          <Button size='sm' onClick={() => handleView(lead)}>
                            <Icons.eye className='mr-2 h-4 w-4' />
                            View
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Active Policies */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.brain className='h-5 w-5 text-brand-purple' />
              Active Policies
            </CardTitle>
            <CardDescription>Toggle policies on or off for this role.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className='space-y-3'>
              {policies.map((pol) => (
                <div
                  key={pol.id}
                  className={cn(
                    'flex items-center justify-between rounded-xl border p-4 transition-colors',
                    pol.is_active ? 'border-brand-cornflower/30 bg-brand-cornflower/5' : 'border-border/50 bg-muted/20'
                  )}
                >
                  <div className='min-w-0'>
                    <p className='font-medium text-foreground'>{pol.name}</p>
                    <p className='truncate text-xs text-muted-foreground'>{pol.natural_language}</p>
                  </div>
                  <Button
                    variant={pol.is_active ? 'default' : 'outline'}
                    size='sm'
                    onClick={() => togglePolicy(pol.id, pol.is_active)}
                  >
                    {pol.is_active ? (
                      <>
                        <Icons.checkCircle className='mr-1.5 h-4 w-4' /> On
                      </>
                    ) : (
                      'Off'
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Lead Detail Dialog */}
      <Dialog open={!!detailLead} onOpenChange={(open) => { if (!open) { setDetailLead(null); setDetail(null) } }}>
        <DialogContent className='sm:max-w-4xl max-h-[90vh] overflow-y-auto'>
          <DialogHeader>
            <DialogTitle className='flex items-center gap-2'>
              {detailLead?.first_name} {detailLead?.last_name}
              {detail && (
                <Badge variant='outline' className={cn(
                  'ml-2',
                  detail.intent_score >= 70 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    detail.intent_score >= 40 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      'bg-slate-50 text-slate-600'
                )}>
                  Intent {detail.intent_score}/100
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              {detail ? `${detail.lead_stage || 'Unknown'} lead • ${detail.owner_name || 'Unassigned'} • ${detail.account?.name || detail.account_name || '-'}` : 'Loading lead details...'}
            </DialogDescription>
          </DialogHeader>

          {detailLoading || !detail ? (
            <div className='flex justify-center p-8'>
              <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
            </div>
          ) : (
            <div className='space-y-6'>
              {/* Intent score bar */}
              <div className='rounded-xl border bg-slate-50 p-4'>
                <div className='mb-2 flex items-center justify-between'>
                  <span className='text-sm font-medium text-brand-navy'>Intent Score</span>
                  <span className='text-sm font-bold text-brand-navy'>{detail.intent_score}/100</span>
                </div>
                <div className='h-2 w-full rounded-full bg-slate-200'>
                  <div
                    className={cn(
                      'h-2 rounded-full',
                      detail.intent_score >= 70 ? 'bg-emerald-500' :
                        detail.intent_score >= 40 ? 'bg-amber-500' : 'bg-slate-400'
                    )}
                    style={{ width: `${Math.max(0, Math.min(100, detail.intent_score))}%` }}
                  />
                </div>
                {detail.intent_signals.length > 0 && (
                  <div className='mt-3 flex flex-wrap gap-2'>
                    {detail.intent_signals.map((s) => (
                      <Badge key={s} variant='secondary' className='text-[10px]'>{s}</Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Contact + Account grid */}
              <div className='grid gap-4 md:grid-cols-2'>
                <Card>
                  <CardHeader>
                    <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>Contact</CardTitle>
                  </CardHeader>
                  <CardContent className='space-y-2 text-sm'>
                    <p><span className='text-muted-foreground'>Email:</span> {detail.email || '-'}</p>
                    <p><span className='text-muted-foreground'>Phone:</span> {detail.phone || '-'}</p>
                    <p><span className='text-muted-foreground'>Title:</span> {detail.title || '-'}</p>
                    <p><span className='text-muted-foreground'>Region:</span> {detail.region || '-'}</p>
                    <p><span className='text-muted-foreground'>Lead source:</span> {detail.lead_source || '-'}</p>
                    <p><span className='text-muted-foreground'>Created:</span> {detail.created_date ? new Date(detail.created_date).toLocaleDateString() : '-'}</p>
                    <p><span className='text-muted-foreground'>Last activity:</span> {detail.last_activity_date ? new Date(detail.last_activity_date).toLocaleDateString() : '-'}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>
                      {detail.account?.name || detail.account_name || 'Company'}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className='space-y-2 text-sm'>
                    {detail.account ? (
                      <>
                        <p><span className='text-muted-foreground'>Industry:</span> {detail.account.industry || '-'}</p>
                        <p><span className='text-muted-foreground'>Employees:</span> {detail.account.number_of_employees?.toLocaleString() || '-'}</p>
                        <p><span className='text-muted-foreground'>Type:</span> {detail.account.type || '-'}</p>
                        <p><span className='text-muted-foreground'>Website:</span> {detail.account.website || '-'}</p>
                        <p><span className='text-muted-foreground'>Billing country:</span> {detail.account.billing_country || '-'}</p>
                        <p><span className='text-muted-foreground'>Strategic account:</span> {detail.account.strategic ? 'Yes' : 'No'}</p>
                      </>
                    ) : (
                      <p className='text-muted-foreground'>No account details available.</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Privacy */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>Privacy & Consent</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='flex flex-wrap items-center gap-2'>
                    <Badge
                      className={cn(
                        detail.privacy_status === 'Can contact' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                      )}
                    >
                      {detail.privacy_status}
                    </Badge>
                    {detail.consent_basis && (
                      <Badge variant='outline' className='text-[10px]'>Consent: {detail.consent_basis}</Badge>
                    )}
                    {detail.do_not_call && (
                      <Badge variant='outline' className='text-[10px] text-red-600'>Do Not Call</Badge>
                    )}
                    {detail.has_opted_out_of_email && (
                      <Badge variant='outline' className='text-[10px] text-red-600'>Email Opt-Out</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Visitor Activity */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>Recent Visitor Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  {detail.recent_activities.length === 0 ? (
                    <p className='text-sm text-muted-foreground'>No recent activity.</p>
                  ) : (
                    <div className='space-y-3'>
                      {detail.recent_activities.map((a) => (
                        <div key={a.id} className='flex items-start justify-between gap-4 rounded-lg border p-3 text-sm'>
                          <div>
                            <p className='font-medium text-brand-navy'>
                              {a.type || 'Activity'} {a.url ? `on ${a.url}` : ''}
                            </p>
                            <p className='text-xs text-muted-foreground'>
                              {a.campaign ? `Campaign: ${a.campaign}` : ''}
                              {a.campaign && a.source ? ' · ' : ''}
                              {a.source ? `Source: ${a.source}` : ''}
                              {a.channel ? ` · Channel: ${a.channel}` : ''}
                            </p>
                          </div>
                          <div className='text-right text-xs text-muted-foreground'>
                            <p>{a.created_at ? new Date(a.created_at).toLocaleString() : '-'}</p>
                            {a.duration_seconds ? <p>{Math.round(a.duration_seconds / 60)}m {a.duration_seconds % 60}s</p> : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Email History */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>Recent Email History</CardTitle>
                </CardHeader>
                <CardContent>
                  {detail.emails.length === 0 ? (
                    <p className='text-sm text-muted-foreground'>No emails yet.</p>
                  ) : (
                    <div className='space-y-3'>
                      {detail.emails.map((e) => (
                        <div key={e.id} className='rounded-lg border p-3 text-sm'>
                          <p className='font-medium text-brand-navy'>{e.subject}</p>
                          <p className='text-xs text-muted-foreground'>Sent {new Date(e.sent_at).toLocaleString()} by {e.sent_by}</p>
                          <p className='mt-1 whitespace-pre-wrap text-xs text-muted-foreground'>{e.body}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Lead Stage */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>Lead Stage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='flex items-center gap-3'>
                    <select
                      className='h-10 rounded-md border border-input bg-background px-3 py-2 text-sm'
                      value={stageValue}
                      onChange={(e) => setStageValue(e.target.value)}
                    >
                      <option value='Open'>Open</option>
                      <option value='MQL'>MQL</option>
                      <option value='SQL'>SQL</option>
                      <option value='Opportunity'>Opportunity</option>
                      <option value='Customer'>Customer</option>
                    </select>
                    <Button onClick={handleStageChange} disabled={stageSaving || stageValue === (detail.lead_stage || 'Open')}>
                      {stageSaving ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : null}
                      Update Stage
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* AI Context */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>AI Context</CardTitle>
                </CardHeader>
                <CardContent>
                  {contexts.length === 0 ? (
                    <p className='text-sm text-muted-foreground'>No context generated yet.</p>
                  ) : (
                    <div className='space-y-3'>
                      {contexts.map((c) => (
                        <div key={c.id} className='rounded-lg border bg-slate-50 p-3 text-sm'>
                          <p className='whitespace-pre-wrap text-brand-navy'>{c.content}</p>
                          <p className='mt-1 text-[10px] text-muted-foreground'>Generated by {c.generated_by} · {new Date(c.created_at).toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* AI Learnings */}
              <Card>
                <CardHeader>
                  <CardTitle className='text-sm font-semibold uppercase tracking-wide text-muted-foreground'>AI Learnings</CardTitle>
                </CardHeader>
                <CardContent>
                  {learnings.length === 0 ? (
                    <p className='text-sm text-muted-foreground'>No learnings generated yet. Run a manual analysis from AI Manager.</p>
                  ) : (
                    <div className='space-y-3'>
                      {learnings.map((l) => (
                        <div key={l.id} className='rounded-lg border p-3 text-sm'>
                          <div className='mb-1 flex items-center gap-2'>
                            <Badge variant='secondary' className='text-[10px]'>{l.category}</Badge>
                            <span className='text-[10px] text-muted-foreground'>{l.confidence}% confidence</span>
                          </div>
                          <p className='font-medium text-brand-navy'>{l.insight}</p>
                          {l.sample_text && <p className='mt-1 text-xs text-muted-foreground'>&ldquo;{l.sample_text.length > 120 ? `${l.sample_text.slice(0, 120)}...` : l.sample_text}&rdquo;</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <DialogFooter>
                <Button variant='outline' onClick={() => { setDetailLead(null); setDetail(null) }}>Close</Button>
                <Button onClick={() => handleDraft(detail)} disabled={detail.has_opted_out_of_email}>
                  <Icons.mail className='mr-2 h-4 w-4' />
                  Draft Email
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Draft / Send Dialog */}
      <Dialog open={!!selectedLead} onOpenChange={(open) => !open && setSelectedLead(null)}>
        <DialogContent className='sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>Draft Email to {selectedLead?.first_name} {selectedLead?.last_name}</DialogTitle>
            <DialogDescription>Review and send this AI-drafted email.</DialogDescription>
          </DialogHeader>

          {isDrafting ? (
            <div className='flex justify-center p-8'>
              <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
            </div>
          ) : (
            <div className='space-y-4'>
              <div className='space-y-2'>
                <Label>Subject</Label>
                <input
                  type='text'
                  className='flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                />
              </div>
              <div className='space-y-2'>
                <Label>Body</Label>
                <textarea
                  className='min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant='outline' onClick={() => setSelectedLead(null)}>Cancel</Button>
            <Button onClick={handleSend} disabled={isDrafting || isSending || !draftBody}>
              {isSending ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.send className='mr-2 h-4 w-4' />}
              {isSending ? 'Sending...' : 'Send Email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
