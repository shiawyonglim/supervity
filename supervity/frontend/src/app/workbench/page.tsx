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

export default function WorkbenchPage() {
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedException, setSelectedException] = useState<Exception | null>(null)
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [isResolving, setIsResolving] = useState(false)

  const fetchExceptions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await apiClient.get<Exception[]>('/api/exceptions')
      setExceptions(data)
    } catch (err) {
      console.error('Failed to load exceptions:', err)
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

  return (
    <motion.div
      className='space-y-8'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      {/* Exception Inbox */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.alertCircle className='h-5 w-5 text-red-500' />
              Exception Inbox
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

                {/* AI Assistant Section (Placeholder) */}
                <div className="bg-brand-cornflower/10 rounded-lg p-4 border border-brand-cornflower/30">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-brand-navy">
                    <Icons.sparkles className="w-4 h-4 text-brand-cornflower" />
                    AI Assistant
                  </h4>
                  <p className="text-sm text-slate-700 mb-3">
                    The AI Orchestrator flagged this item for review. 
                    {selectedException.ai_recommendation ? ` Recommendation: ${selectedException.ai_recommendation}` : ' Need help deciding?'}
                  </p>
                  <Button variant="outline" size="sm" className="bg-white">Ask AI for context</Button>
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
              <Button variant='outline' size='sm'>
                <Icons.plus className='mr-2 h-4 w-4' />
                New Task
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.fileText className='mr-2 h-4 w-4' />
                Generate Report
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.mail className='mr-2 h-4 w-4' />
                Send Notification
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.download className='mr-2 h-4 w-4' />
                Export Data
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
