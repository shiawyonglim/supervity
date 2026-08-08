'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import type { AppRole } from '@/context/RoleContext'
import { ROLE_META } from '@/context/RoleContext'

type Tab = 'buying-groups' | 'consent' | 'quality'

interface ConsentRecord {
  consent_id: number
  contact_id: string
  contact_name: string
  contact_email: string
  basis: string
  region: string
  status: string
  channel: string
  source: string
  captured_at: string
  expires_at: string
}

interface QualityIssue {
  issue: string
  count: number
  severity: string
  examples: Array<{ id: string; table: string }>
}

interface QualityReport {
  chronological: QualityIssue[]
  relational: QualityIssue[]
  state_logic: QualityIssue[]
  format: QualityIssue[]
}

interface BuyingGroup {
  group_id: string
  account_name: string
  account_industry: string
  is_proposed: boolean
  contacts: Array<{
    contact_id: string
    name: string
    title: string
    email: string
    role: string
    is_primary: boolean
  }>
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'buying-groups', label: 'Buying Groups', icon: Icons.users },
  { id: 'consent', label: 'Consent Registry', icon: Icons.checkCircle },
  { id: 'quality', label: 'Data Quality', icon: Icons.shield },
]

export function SalesDataManager({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const [activeTab, setActiveTab] = useState<Tab>('buying-groups')
  const [loading, setLoading] = useState(true)
  const [buyingGroups, setBuyingGroups] = useState<BuyingGroup[]>([])
  const [consent, setConsent] = useState<ConsentRecord[]>([])
  const [quality, setQuality] = useState<QualityReport | null>(null)
  const [fixing, setFixing] = useState(false)
  const [advising, setAdvising] = useState(false)
  const [advice, setAdvice] = useState<{ issue: string; explanation: string; steps: string[] } | null>(null)

  const load = useCallback(async (tab: Tab) => {
    setLoading(true)
    try {
      if (tab === 'buying-groups') {
        const res = await apiClient.get<{ buying_groups: BuyingGroup[] }>('/api/data-manager/buying-groups')
        setBuyingGroups(res.buying_groups || [])
      } else if (tab === 'consent') {
        const res = await apiClient.get<{ consent_records: ConsentRecord[] }>('/api/data-manager/consent')
        setConsent(res.consent_records || [])
      } else if (tab === 'quality') {
        const res = await apiClient.get<QualityReport>('/api/data-manager/quality')
        setQuality(res)
      }
    } catch (err) {
      console.error('Sales data manager load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(activeTab)
  }, [activeTab, load])

  const runFix = async () => {
    setFixing(true)
    try {
      await apiClient.post('/api/data-manager/quality/fix', {})
      await load('quality')
    } catch (err) {
      console.error('Fix failed:', err)
    } finally {
      setFixing(false)
    }
  }

  const askAIAdvice = async (issue: string) => {
    setAdvising(true)
    try {
      const res = await apiClient.post<{ advice: { issue: string; explanation: string; steps: string[] } }>('/api/data-manager/quality/advise', { category: 'quality', issue })
      setAdvice(res.advice || { issue, explanation: 'No advice available.', steps: [] })
    } catch (err) {
      console.error('Advice failed:', err)
      setAdvice({ issue, explanation: 'Could not load AI advice.', steps: [] })
    } finally {
      setAdvising(false)
    }
  }

  const totalIssues = quality
    ? Object.values(quality).flat().reduce((sum, issue) => sum + issue.count, 0)
    : 0

  return (
    <motion.div className='space-y-6' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
            {meta.label} Data Manager
          </h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            Buying groups, consent registry, and data quality.
          </p>
        </div>
        <Badge className={cn('rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide', meta.color)}>
          {meta.label}
        </Badge>
      </motion.div>

      <motion.div variants={itemVariants} className='flex gap-2 border-b pb-1'>
        {tabs.map((tab) => {
          const Icon = tab.icon
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors',
                active
                  ? 'border-b-2 border-brand-primary text-brand-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className='h-4 w-4' strokeWidth={1.5} />
              {tab.label}
            </button>
          )
        })}
      </motion.div>

      <AnimatePresence mode='wait'>
        <motion.div
          key={activeTab}
          variants={itemVariants}
          initial='hidden'
          animate='visible'
          exit='hidden'
        >
          {activeTab === 'buying-groups' && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Icons.users className='h-5 w-5 text-brand-cornflower' />
                  Buying Groups
                </CardTitle>
                <CardDescription>Existing and proposed buying groups for your accounts.</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className='flex justify-center p-8'>
                    <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
                  </div>
                ) : buyingGroups.length === 0 ? (
                  <p className='text-center text-muted-foreground'>No buying groups found.</p>
                ) : (
                  <div className='space-y-4'>
                    {buyingGroups.map((g) => (
                      <div key={g.group_id} className='rounded-xl border p-4'>
                        <div className='flex flex-wrap items-center gap-2'>
                          <span className='font-semibold text-brand-navy'>{g.account_name}</span>
                          <span className='text-xs text-muted-foreground'>{g.account_industry}</span>
                          {g.is_proposed && <Badge variant='secondary' className='text-[10px]'>Proposed</Badge>}
                        </div>
                        <div className='mt-3 flex flex-wrap gap-2'>
                          {g.contacts.map((c) => (
                            <div
                              key={c.contact_id}
                              className={cn(
                                'rounded-lg border px-3 py-2 text-xs',
                                c.is_primary ? 'border-brand-cornflower bg-brand-cornflower/5' : 'bg-muted/30'
                              )}
                            >
                              <p className='font-medium text-foreground'>{c.name}</p>
                              <p className='text-muted-foreground'>{c.title} · {c.role}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'consent' && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Icons.checkCircle className='h-5 w-5 text-brand-cornflower' />
                  Consent Registry
                </CardTitle>
                <CardDescription>Review consent status by region and contact.</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className='flex justify-center p-8'>
                    <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
                  </div>
                ) : consent.length === 0 ? (
                  <p className='text-center text-muted-foreground'>No consent records found.</p>
                ) : (
                  <div className='overflow-x-auto'>
                    <table className='w-full text-sm'>
                      <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                        <tr>
                          <th className='py-3 px-4 font-medium'>Contact</th>
                          <th className='py-3 px-4 font-medium'>Region</th>
                          <th className='py-3 px-4 font-medium'>Basis</th>
                          <th className='py-3 px-4 font-medium'>Status</th>
                          <th className='py-3 px-4 font-medium'>Channel</th>
                          <th className='py-3 px-4 font-medium'>Expires</th>
                        </tr>
                      </thead>
                      <tbody>
                        {consent.map((c) => (
                          <tr key={c.consent_id} className='border-b last:border-0 hover:bg-slate-50'>
                            <td className='py-3 px-4'>
                              <p className='font-medium text-foreground'>{c.contact_name}</p>
                              <p className='text-xs text-muted-foreground'>{c.contact_email}</p>
                            </td>
                            <td className='py-3 px-4'>{c.region}</td>
                            <td className='py-3 px-4'>{c.basis}</td>
                            <td className='py-3 px-4'>
                              <Badge variant={c.status === 'active' ? 'default' : 'destructive'}>{c.status}</Badge>
                            </td>
                            <td className='py-3 px-4'>{c.channel}</td>
                            <td className='py-3 px-4'>{new Date(c.expires_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'quality' && (
            <Card>
              <CardHeader className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
                <div>
                  <CardTitle className='flex items-center gap-2'>
                    <Icons.shield className='h-5 w-5 text-brand-cornflower' />
                    Data Quality
                  </CardTitle>
                  <CardDescription>Issues found across the CRM data. Total: {totalIssues} rows.</CardDescription>
                </div>
                <div className='flex items-center gap-2'>
                  <Button variant='outline' size='sm' onClick={() => load('quality')} disabled={loading}>
                    <Icons.refresh className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
                    Rescan
                  </Button>
                  <Button size='sm' onClick={runFix} disabled={fixing}>
                    {fixing ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.sparkles className='mr-2 h-4 w-4' />}
                    Auto-Fix
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className='flex justify-center p-8'>
                    <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
                  </div>
                ) : !quality || totalIssues === 0 ? (
                  <p className='text-center text-muted-foreground'>No data quality issues found.</p>
                ) : (
                  <div className='space-y-6'>
                    {(Object.entries(quality) as [string, QualityIssue[]][]).map(([category, issues]) =>
                      issues.length > 0 ? (
                        <div key={category}>
                          <h3 className='mb-2 text-xs font-bold uppercase tracking-wider text-brand-navy'>
                            {category.replace('_', ' ')}
                          </h3>
                          <div className='space-y-3'>
                            {issues.map((issue, idx) => (
                              <div
                                key={idx}
                                className={cn(
                                  'rounded-xl border p-4',
                                  issue.severity === 'high' ? 'border-red-200 bg-red-50/30' : 'border-border/50'
                                )}
                              >
                                <div className='flex flex-wrap items-center justify-between gap-2'>
                                  <div className='flex items-center gap-2'>
                                    <Badge variant={issue.severity === 'high' ? 'destructive' : 'outline'} className='text-[10px] uppercase'>
                                      {issue.severity}
                                    </Badge>
                                    <span className='font-medium text-foreground'>{issue.issue}</span>
                                  </div>
                                  <div className='flex items-center gap-2'>
                                    <span className='text-xs text-muted-foreground'>{issue.count} rows</span>
                                    <Button variant='ghost' size='sm' onClick={() => askAIAdvice(issue.issue)} disabled={advising}>
                                      <Icons.sparkles className='mr-1.5 h-4 w-4 text-brand-purple' />
                                      Ask AI
                                    </Button>
                                  </div>
                                </div>
                                {issue.examples.length > 0 && (
                                  <div className='mt-2 text-xs text-muted-foreground'>
                                    Examples: {issue.examples.slice(0, 3).map((e: { id: string; table: string }) => `${e.table}/${e.id}`).join(', ')}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null
                    )}
                    {advice && (
                      <div className='rounded-xl border border-brand-cornflower/30 bg-brand-cornflower/5 p-4'>
                        <p className='text-sm font-semibold text-brand-navy'>{advice.issue}</p>
                        <p className='mt-1 text-sm text-muted-foreground'>{advice.explanation}</p>
                        {advice.steps.length > 0 && (
                          <ol className='mt-2 list-decimal pl-4 text-sm text-muted-foreground'>
                            {advice.steps.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ol>
                        )}
                        <Button variant='ghost' size='sm' className='mt-2' onClick={() => setAdvice(null)}>
                          Close
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  )
}
