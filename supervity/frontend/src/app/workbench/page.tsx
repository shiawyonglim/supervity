'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '@/components/ui/sheet'
import { Label } from '@/components/ui/label'
import { useRouter } from 'next/navigation'

interface Exception {
  id: number
  type: string
  severity: string
  title: string
  description: string
  prospect_id?: string
  account_name?: string
  context?: any
  ai_recommendation?: string
  ai_confidence?: number
  status: string
  created_at: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

export default function WorkbenchPage() {
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedException, setSelectedException] = useState<Exception | null>(null)
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [isResolving, setIsResolving] = useState(false)
  
  const [aiContext, setAiContext] = useState<string | null>(null)
  const [isAskingAi, setIsAskingAi] = useState(false)

  // Quick Actions state
  const [quickActionLoading, setQuickActionLoading] = useState<string | null>(null)
  const [quickActionResult, setQuickActionResult] = useState<{title: string, message: string} | null>(null)

  // AI Assistant chat state
  const [chatMessages, setChatMessages] = useState<{role: 'user' | 'ai', content: string}[]>([
    { role: 'ai', content: 'Hello! I am AutoPilot AI. Ask me about your leads, exceptions, policies, or revenue forecast.' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)

  // Automation Builder state
  const [ruleName, setRuleName] = useState('')
  const [ruleCondition, setRuleCondition] = useState('Lead Stage')
  const [ruleOperator, setRuleOperator] = useState('equals')
  const [ruleValue, setRuleValue] = useState('Open')
  const [ruleAction, setRuleAction] = useState('assign to SDR')
  const [ruleActionValue, setRuleActionValue] = useState('')
  const [ruleSaving, setRuleSaving] = useState(false)

  // Prospects state for drafting email
  const [prospects, setProspects] = useState<any[]>([])
  const [draftingEmailFor, setDraftingEmailFor] = useState<any | null>(null)
  const [emailDraft, setEmailDraft] = useState('')
  const [isDrafting, setIsDrafting] = useState(false)

  const router = useRouter()

  const fetchExceptions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await apiClient.get<Exception[]>('/api/exceptions')
      setExceptions(data)
      const dataPack = await apiClient.get<any>('/api/data/contact')
      if (dataPack && dataPack.data) setProspects(dataPack.data)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchExceptions()
  }, [fetchExceptions])

  const handleResolve = async (id: number, action: string, notes: string = 'Resolved via Workbench') => {
    setIsResolving(true)
    try {
      await apiClient.post(`/api/exceptions/${id}/resolve`, {
        resolution_action: action,
        resolved_by: 'Admin',
        resolution_notes: notes
      })
      setExceptions(prev => prev.filter(e => e.id !== id))
      setSelectedException(null)
      setResolutionNotes('')
    } catch (err) {
      console.error('Failed to resolve exception:', err)
    } finally {
      setIsResolving(false)
    }
  }

  const handleDraftEmail = async (prospect: any) => {
    setDraftingEmailFor(prospect)
    setIsDrafting(true)
    setEmailDraft('')
    try {
      const res = await apiClient.post<any>('/api/workbench/draft-email', {
        user_id: prospect.Id,
        user_name: prospect.FirstName + ' ' + prospect.LastName,
        user_email: prospect.Email
      })
      setEmailDraft(res.draft)
    } catch (err) {
      console.error('Draft error', err)
      setEmailDraft('Failed to generate draft.')
    } finally {
      setIsDrafting(false)
    }
  }

  const handleSaveRule = async () => {
    if (!ruleName.trim()) return
    const natural_language = `If ${ruleCondition} ${ruleOperator} "${ruleValue}" then ${ruleAction}${ruleActionValue ? ` "${ruleActionValue}"` : ''}.`
    setRuleSaving(true)
    try {
      await apiClient.post('/api/policies', {
        name: ruleName,
        description: `Workbench automation rule: ${natural_language}`,
        policy_type: 'natural_language',
        natural_language,
        entity_name: 'contact',
        priority: 5,
        is_active: true,
      })
      alert('Automation rule saved as an AI Policy!')
      setRuleName('')
      setRuleValue('')
      setRuleActionValue('')
    } catch (err) {
      console.error('Failed to save rule:', err)
      alert('Failed to save automation rule.')
    } finally {
      setRuleSaving(false)
    }
  }

  const runQuickAction = async (name: string, endpoint: string, method: 'get' | 'post' = 'post') => {
    setQuickActionLoading(name)
    setQuickActionResult(null)
    try {
      const res = method === 'get'
        ? await apiClient.get<any>(endpoint)
        : await apiClient.post<any>(endpoint, {})
      let message = ''
      if (res.forecast) {
        message = res.forecast
      } else if (res.results) {
        const r = res.results
        message = `Merged ${r.merged ?? 0} record(s) and routed ${r.exceptions ?? 0} to Workbench.`
      } else if (res.count !== undefined) {
        message = `${res.count} item(s) found.`
      } else if (res.win_rate !== undefined) {
        message = `Win rate: ${Math.round(res.win_rate * 100)}%, Open pipeline: $${Number(res.open_pipeline || 0).toLocaleString()}, Predicted revenue: $${Number(res.predicted_revenue || 0).toLocaleString()}.`
      } else if (res.insights) {
        message = `${res.insights.length} insight(s) generated.`
      } else if (res.patterns_found !== undefined) {
        message = `${res.patterns_found} pattern(s) found, ${res.insights_created} policy suggestion(s) created.`
      } else if (res.collisions) {
        message = `${res.collisions.length} engagement collision(s) detected.`
      } else {
        message = JSON.stringify(res).slice(0, 250)
      }
      setQuickActionResult({ title: name, message })
    } catch (err) {
      console.error(`Quick action ${name} failed:`, err)
      setQuickActionResult({ title: name, message: 'Action failed. Check console for details.' })
    } finally {
      setQuickActionLoading(null)
    }
  }

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsChatLoading(true)
    try {
      const res = await apiClient.post<any>('/api/ai/chat', {
        message: userMessage,
        history: chatMessages.map(m => ({ role: m.role, content: m.content })),
        context: { page: '/workbench' }
      })
      setChatMessages(prev => [...prev, { role: 'ai', content: res.response || 'No response from AI.' }])
    } catch (err) {
      console.error('AI chat error:', err)
      setChatMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I encountered an error. Please try again.' }])
    } finally {
      setIsChatLoading(false)
    }
  }

  return (
    <motion.div
      className='space-y-8'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-display-3 font-bold tracking-tight text-brand-navy font-display">Workbench</h1>
          <p className="mt-2 text-lg text-muted-foreground font-sans">Human-in-the-loop exception handling and user management.</p>
        </div>
      </div>

      <Tabs defaultValue="inbox" className="space-y-6">
        <TabsList className="bg-white/50 border backdrop-blur-sm">
          <TabsTrigger value="inbox" className="data-[state=active]:bg-brand-navy data-[state=active]:text-white">Exception Inbox</TabsTrigger>
          <TabsTrigger value="prospects" className="data-[state=active]:bg-brand-navy data-[state=active]:text-white">Prospects / Users</TabsTrigger>
          <TabsTrigger value="assistant" className="data-[state=active]:bg-brand-navy data-[state=active]:text-white">AI Assistant</TabsTrigger>
          <TabsTrigger value="automation" className="data-[state=active]:bg-brand-navy data-[state=active]:text-white">Automation Builder</TabsTrigger>
        </TabsList>

        <TabsContent value="inbox" className="space-y-6">
          {/* Exception Inbox */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Icons.alertCircle className='h-5 w-5 text-red-500' />
                  Needs Review
                </CardTitle>
                <CardDescription>
                  Review and resolve automated tasks that require human intervention
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex justify-center p-8"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
                ) : exceptions.length === 0 ? (
                  <div className="text-center p-8 text-muted-foreground">
                    <Icons.checkCircle className="h-12 w-12 mx-auto mb-4 text-emerald-500 opacity-50" />
                    <p>No pending exceptions to resolve. Great job!</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {exceptions.map(exc => (
                      <div 
                        key={exc.id} 
                        className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center p-4 border rounded-xl bg-white shadow-sm cursor-pointer hover:bg-slate-50 transition-colors"
                        onClick={() => {
                          setSelectedException(exc)
                          setResolutionNotes('')
                          setAiContext(null)
                        }}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold">{exc.title}</h4>
                            <Badge variant={exc.severity === 'critical' ? 'destructive' : 'secondary'}>
                              {exc.severity}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{exc.description}</p>
                          {exc.ai_recommendation && (
                            <p className="text-sm text-brand-navy font-medium mt-2">
                              <Icons.sparkles className="inline w-3 h-3 mr-1" />
                              AI Suggestion: {exc.ai_recommendation} ({exc.ai_confidence}% confidence)
                            </p>
                          )}
                        </div>
                        <div className="flex gap-2 shrink-0">
                          <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); handleResolve(exc.id, 'rejected') }}>
                            Reject
                          </Button>
                          <Button variant="default" size="sm" onClick={(e) => { e.stopPropagation(); handleResolve(exc.id, 'approved') }}>
                            Approve
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="prospects" className="space-y-6">
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Icons.users className="h-5 w-5 text-brand-cornflower" />
                  Prospect Directory
                </CardTitle>
                <CardDescription>Select a user to draft an email</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  {prospects.slice(0, 10).map((p: any) => (
                    <div key={p.Id} className="p-4 border rounded-lg bg-white flex justify-between items-center">
                      <div>
                        <p className="font-semibold text-sm">{p.FirstName} {p.LastName}</p>
                        <p className="text-xs text-muted-foreground">{p.Email} • {p.Title}</p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => handleDraftEmail(p)}>Draft Email</Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="assistant" className="space-y-6">
          <motion.div variants={itemVariants}>
            <Card className="h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Icons.bot className="h-5 w-5 text-brand-cornflower" />
                  AI Assistant
                </CardTitle>
                <CardDescription>Ask AutoPilot AI about your sales data, exceptions, forecasts, and policies.</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col min-h-0">
                <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                  {chatMessages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${msg.role === 'user' ? 'bg-brand-navy text-white' : 'bg-slate-100 text-slate-800'}`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {isChatLoading && (
                    <div className="flex justify-start">
                      <div className="bg-slate-100 rounded-lg px-4 py-2 text-sm flex items-center gap-2">
                        <Icons.loader className="w-4 h-4 animate-spin" />
                        Thinking...
                      </div>
                    </div>
                  )}
                </div>
                <form onSubmit={handleChatSubmit} className="mt-4 flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                  <Button type="submit" disabled={isChatLoading || !chatInput.trim()}>
                    {isChatLoading ? <Icons.loader className="w-4 h-4 animate-spin" /> : <Icons.send className="w-4 h-4" />}
                    Send
                  </Button>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="automation" className="space-y-6">
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Icons.zap className="h-5 w-5 text-amber-500" />
                  Automation Builder
                </CardTitle>
                <CardDescription>Create a simple rule and save it as an AI Policy. It will be evaluated by the policy engine.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm font-medium">Rule name</Label>
                  <input
                    type="text"
                    value={ruleName}
                    onChange={(e) => setRuleName(e.target.value)}
                    placeholder="e.g. Auto-assign SQL leads to senior SDR"
                    className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Field</Label>
                    <select value={ruleCondition} onChange={(e) => setRuleCondition(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm">
                      <option>Lead Stage</option>
                      <option>Email Domain</option>
                      <option>Country</option>
                      <option>Title</option>
                      <option>Account Name</option>
                    </select>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Operator</Label>
                    <select value={ruleOperator} onChange={(e) => setRuleOperator(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm">
                      <option value="equals">equals</option>
                      <option value="contains">contains</option>
                      <option value="is not">is not</option>
                    </select>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Value</Label>
                    <input
                      type="text"
                      value={ruleValue}
                      onChange={(e) => setRuleValue(e.target.value)}
                      placeholder="Open"
                      className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Then do this</Label>
                    <select value={ruleAction} onChange={(e) => setRuleAction(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm">
                      <option value="assign to SDR">assign to SDR</option>
                      <option value="send to Workbench">send to Workbench</option>
                      <option value="mark as">mark as</option>
                      <option value="skip">skip</option>
                    </select>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Action value (optional)</Label>
                    <input
                      type="text"
                      value={ruleActionValue}
                      onChange={(e) => setRuleActionValue(e.target.value)}
                      placeholder="owner_id or status"
                      className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </div>
                </div>
                <Button onClick={handleSaveRule} disabled={ruleSaving || !ruleName.trim()}>
                  {ruleSaving ? <Icons.loader className="w-4 h-4 mr-2 animate-spin" /> : <Icons.plus className="w-4 h-4 mr-2" />}
                  Save Automation Rule
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>

      {/* Draft Email Sheet */}
      <Sheet open={!!draftingEmailFor} onOpenChange={(open) => !open && setDraftingEmailFor(null)}>
        <SheetContent className="sm:max-w-xl overflow-y-auto">
          {draftingEmailFor && (
            <>
              <SheetHeader className="mb-6">
                <SheetTitle>Draft Email for {draftingEmailFor.FirstName}</SheetTitle>
                <SheetDescription>{draftingEmailFor.Email}</SheetDescription>
              </SheetHeader>
              <div className="space-y-4">
                {isDrafting ? (
                  <div className="flex flex-col items-center justify-center p-8">
                    <Icons.loader className="w-8 h-8 animate-spin text-brand-cornflower mb-4" />
                    <p className="text-sm text-muted-foreground">AI is drafting the email...</p>
                  </div>
                ) : (
                  <>
                    <Label>Email Content</Label>
                    <textarea 
                      className="flex min-h-[300px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={emailDraft}
                      onChange={(e) => setEmailDraft(e.target.value)}
                    />
                    <Button className="w-full">Send Email</Button>
                  </>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Exception Detail Sheet */}
      <Sheet open={!!selectedException} onOpenChange={(open) => !open && setSelectedException(null)}>
        <SheetContent className="sm:max-w-xl overflow-y-auto">
          {selectedException && (
            <>
              <SheetHeader className="mb-6">
                <div className="flex items-center gap-2">
                  <Badge variant={selectedException.severity === 'critical' ? 'destructive' : 'secondary'}>
                    {selectedException.severity}
                  </Badge>
                  <span className="text-sm text-muted-foreground uppercase tracking-wider">{selectedException.type}</span>
                </div>
                <SheetTitle className="text-2xl mt-2">{selectedException.title}</SheetTitle>
                <SheetDescription className="text-base text-foreground mt-2">
                  {selectedException.description}
                </SheetDescription>
              </SheetHeader>

              <div className="space-y-6">
                {/* Context Data payload */}
                <div>
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    <Icons.layers className="w-4 h-4 text-brand-primary" />
                    Data Context payload
                  </h4>
                  <div className="bg-slate-900 rounded-md p-4 overflow-x-auto">
                    <pre className="text-xs text-slate-50 font-mono">
                      {JSON.stringify(selectedException.context, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* AI Assistant Section */}
                <div className="bg-brand-cornflower/10 rounded-lg p-4 border border-brand-cornflower/30">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-brand-navy">
                    <Icons.sparkles className="w-4 h-4 text-brand-cornflower" />
                    AI Assistant
                  </h4>
                  <p className="text-sm text-slate-700 mb-3">
                    The AI Orchestrator flagged this item for review. 
                    {selectedException.ai_recommendation ? ` Recommendation: ${selectedException.ai_recommendation}` : ' Need help deciding?'}
                  </p>
                  
                  {aiContext && (
                    <div className="mb-3 p-3 bg-white rounded-md text-sm text-slate-800 border border-slate-200">
                      <strong>AI Context:</strong> {aiContext}
                    </div>
                  )}

                  <div className="flex gap-2 flex-wrap">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="bg-white"
                      onClick={async () => {
                        setIsAskingAi(true)
                        try {
                          const res = await apiClient.post<any>('/api/workbench/ask-ai', { exception_id: selectedException.id })
                          setAiContext(res.ai_context)
                        } catch (e) {
                          console.error(e)
                          setAiContext("Failed to get AI context.")
                        } finally {
                          setIsAskingAi(false)
                        }
                      }}
                      disabled={isAskingAi}
                    >
                      {isAskingAi ? <Icons.loader className="w-4 h-4 mr-2 animate-spin" /> : <Icons.helpCircle className="w-4 h-4 mr-2" />}
                      Ask AI for context
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="bg-white border-brand-cornflower text-brand-navy hover:bg-brand-cornflower/10"
                      onClick={() => {
                        // Navigate to policies page to build automation
                        router.push(`/ai/policies?tab=create-with-ai&context=Auto-resolve exception type ${selectedException.type}`)
                      }}
                    >
                      <Icons.zap className="w-4 h-4 mr-2" />
                      Automate this
                    </Button>
                  </div>
                </div>

                {/* Resolution Form */}
                <div className="space-y-3">
                  <Label htmlFor="notes">Resolution Notes</Label>
                  <textarea 
                    id="notes"
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="Why did you approve/reject this?"
                    value={resolutionNotes}
                    onChange={e => setResolutionNotes(e.target.value)}
                  />
                </div>
              </div>

              <SheetFooter className="mt-8 flex gap-3 sm:justify-start">
                <Button 
                  variant="outline" 
                  className="w-full sm:w-auto"
                  onClick={() => handleResolve(selectedException.id, 'rejected', resolutionNotes || 'Rejected manually')}
                  disabled={isResolving}
                >
                  Reject
                </Button>
                <Button 
                  className="w-full sm:w-auto"
                  onClick={() => handleResolve(selectedException.id, 'approved', resolutionNotes || 'Approved manually')}
                  disabled={isResolving}
                >
                  {isResolving && <Icons.loader className="mr-2 h-4 w-4 animate-spin" />}
                  Approve Exception
                </Button>
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.zap className='h-5 w-5 text-brand-cornflower' />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Frequently used actions for faster access
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className='flex flex-wrap gap-3'>
              <Button
                variant='outline'
                size='sm'
                onClick={() => runQuickAction('Generate AI Insights', '/api/insights/generate')}
                disabled={quickActionLoading === 'Generate AI Insights'}
              >
                {quickActionLoading === 'Generate AI Insights' ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.sparkles className='mr-2 h-4 w-4' />}
                Generate AI Insights
              </Button>
              <Button
                variant='outline'
                size='sm'
                onClick={() => runQuickAction('Run Self-Learn', '/api/insights/self-learn')}
                disabled={quickActionLoading === 'Run Self-Learn'}
              >
                {quickActionLoading === 'Run Self-Learn' ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.brain className='mr-2 h-4 w-4' />}
                Run Self-Learn
              </Button>
              <Button
                variant='outline'
                size='sm'
                onClick={() => runQuickAction('Run Deduplication', '/api/data-manager/dedup/run')}
                disabled={quickActionLoading === 'Run Deduplication'}
              >
                {quickActionLoading === 'Run Deduplication' ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.layers className='mr-2 h-4 w-4' />}
                Run Deduplication
              </Button>
              <Button
                variant='outline'
                size='sm'
                onClick={() => runQuickAction('Check Collisions', '/api/data-manager/collisions', 'get')}
                disabled={quickActionLoading === 'Check Collisions'}
              >
                {quickActionLoading === 'Check Collisions' ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.shield className='mr-2 h-4 w-4' />}
                Check Collisions
              </Button>
              <Button
                variant='outline'
                size='sm'
                onClick={() => runQuickAction('Revenue Forecast', '/api/insights/forecast', 'get')}
                disabled={quickActionLoading === 'Revenue Forecast'}
              >
                {quickActionLoading === 'Revenue Forecast' ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.trendingUp className='mr-2 h-4 w-4' />}
                Revenue Forecast
              </Button>
            </div>
            {quickActionResult && (
              <div className='mt-4 p-3 bg-slate-50 rounded-md border text-sm'>
                <strong>{quickActionResult.title}</strong>
                <p className='text-muted-foreground'>{quickActionResult.message}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}

