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
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Label } from '@/components/ui/label'

interface Contact {
  id: string
  first_name: string
  last_name: string
  email: string
  title: string
  account_name: string
  lead_stage: string
  owner_name: string
}

interface Email {
  id: number
  subject: string
  body: string
  sent_at: string
  sent_by: string
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

export default function WorkbenchUsersPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)
  const [emails, setEmails] = useState<Email[]>([])
  const [isLoadingEmails, setIsLoadingEmails] = useState(false)
  
  const [isDrafting, setIsDrafting] = useState(false)
  const [draftSubject, setDraftSubject] = useState('')
  const [draftBody, setDraftBody] = useState('')

  const fetchContacts = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await apiClient.get<Contact[]>('/api/contacts?limit=20')
      setContacts(data)
    } catch (err) {
      console.error('Failed to load contacts:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchContacts()
  }, [fetchContacts])

  const handleSelectContact = async (contact: Contact) => {
    setSelectedContact(contact)
    setIsLoadingEmails(true)
    setIsDrafting(false)
    setDraftSubject('')
    setDraftBody('')
    try {
      const data = await apiClient.get<Email[]>(`/api/contacts/${contact.id}/emails`)
      setEmails(data)
    } catch (err) {
      console.error('Failed to load emails:', err)
    } finally {
      setIsLoadingEmails(false)
    }
  }

  const handleDraftEmail = async () => {
    if (!selectedContact) return
    setIsDrafting(true)
    setDraftSubject('Drafting...')
    setDraftBody('AI is analyzing context and writing your email...')
    try {
      const res = await apiClient.post<{subject: string, body: string}>(`/api/contacts/${selectedContact.id}/draft`, {
        prompt_context: "Focus on their recent activity and be concise."
      })
      setDraftSubject(res.subject)
      setDraftBody(res.body)
    } catch (err) {
      console.error('Failed to draft email:', err)
      setDraftSubject('Error')
      setDraftBody('Failed to draft email.')
    } finally {
      setIsDrafting(false)
    }
  }

  const handleSendEmail = () => {
    // Mock sending email
    const newEmail: Email = {
      id: Date.now(),
      subject: draftSubject,
      body: draftBody,
      sent_at: new Date().toISOString(),
      sent_by: 'You (Sent via Workbench)'
    }
    setEmails([newEmail, ...emails])
    setDraftSubject('')
    setDraftBody('')
  }

  return (
    <motion.div
      className='space-y-8'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.users className='h-5 w-5 text-brand-primary' />
              Users & Communications
            </CardTitle>
            <CardDescription>
              View contacts, review their email history, and draft new communications with AI.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center p-8"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
            ) : contacts.length === 0 ? (
              <div className="text-center p-8 text-muted-foreground">
                <p>No contacts found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground uppercase bg-slate-50 border-b">
                    <tr>
                      <th className="px-4 py-3 font-medium">Name</th>
                      <th className="px-4 py-3 font-medium">Email</th>
                      <th className="px-4 py-3 font-medium">Company</th>
                      <th className="px-4 py-3 font-medium">Stage</th>
                      <th className="px-4 py-3 font-medium">Owner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contacts.map(c => (
                      <tr 
                        key={c.id} 
                        className="border-b hover:bg-slate-50 cursor-pointer transition-colors"
                        onClick={() => handleSelectContact(c)}
                      >
                        <td className="px-4 py-3 font-medium text-brand-navy">
                          {c.first_name} {c.last_name}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{c.email}</td>
                        <td className="px-4 py-3">{c.account_name || '-'}</td>
                        <td className="px-4 py-3">
                          <Badge variant="outline">{c.lead_stage || 'Unknown'}</Badge>
                        </td>
                        <td className="px-4 py-3">{c.owner_name || 'Unassigned'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Communications Sheet */}
      <Sheet open={!!selectedContact} onOpenChange={(open) => !open && setSelectedContact(null)}>
        <SheetContent className="sm:max-w-2xl overflow-y-auto">
          {selectedContact && (
            <>
              <SheetHeader className="mb-6 border-b pb-4">
                <SheetTitle className="text-2xl">{selectedContact.first_name} {selectedContact.last_name}</SheetTitle>
                <SheetDescription>
                  {selectedContact.title} at {selectedContact.account_name} &bull; {selectedContact.email}
                </SheetDescription>
              </SheetHeader>

              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Icons.mail className="w-5 h-5 text-brand-primary" />
                    Communication History
                  </h3>
                  <Button onClick={handleDraftEmail} disabled={isDrafting}>
                    <Icons.sparkles className="w-4 h-4 mr-2" />
                    Draft Email via AI
                  </Button>
                </div>

                {(draftSubject || draftBody) && (
                  <Card className="border-brand-primary/50 shadow-md">
                    <CardHeader className="bg-brand-primary/5 pb-4">
                      <CardTitle className="text-sm font-medium flex items-center gap-2 text-brand-primary">
                        <Icons.edit className="w-4 h-4" />
                        AI Draft
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                      <div className="space-y-2">
                        <Label>Subject</Label>
                        <input 
                          type="text" 
                          className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background"
                          value={draftSubject}
                          onChange={e => setDraftSubject(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Body</Label>
                        <textarea 
                          className="flex min-h-[150px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background"
                          value={draftBody}
                          onChange={e => setDraftBody(e.target.value)}
                        />
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => {setDraftSubject(''); setDraftBody('')}}>Discard</Button>
                        <Button onClick={handleSendEmail} disabled={isDrafting}>Send Email</Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {isLoadingEmails ? (
                  <div className="flex justify-center p-4"><Icons.loader className="h-6 w-6 animate-spin text-muted-foreground" /></div>
                ) : emails.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">No past emails found.</p>
                ) : (
                  <div className="space-y-4">
                    {emails.map(email => (
                      <div key={email.id} className="border rounded-lg p-4 bg-slate-50 space-y-2">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Subject</span>
                            <h4 className="font-medium">{email.subject}</h4>
                          </div>
                          <div className="text-right">
                            <span className="text-xs text-muted-foreground block">{new Date(email.sent_at).toLocaleString()}</span>
                            <span className="text-xs font-medium text-brand-navy">From: {email.sent_by}</span>
                          </div>
                        </div>
                        <div className="bg-white p-3 rounded border text-sm whitespace-pre-wrap text-slate-700">
                          {email.body}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </motion.div>
  )
}
