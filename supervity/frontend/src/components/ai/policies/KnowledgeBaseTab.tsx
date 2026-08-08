'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'

// ============================================================================
// Types
// ============================================================================

interface KnowledgeDocument {
  id: number
  title: string
  category: string
  content: string
  is_active: boolean
  source: string
  created_at: string
  updated_at: string
}

interface KnowledgeBaseText {
  text: string
  policy_count: number
  document_count: number
  generated_at: string
}

const EMPTY_FORM = { title: '', category: 'reference', content: '' }

// ============================================================================
// Component
// ============================================================================

export function KnowledgeBaseTab() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [preview, setPreview] = useState<KnowledgeBaseText | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showPreview, setShowPreview] = useState(false)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [isSaving, setIsSaving] = useState(false)

  const [isIngesting, setIsIngesting] = useState(false)
  const [ingestResult, setIngestResult] = useState<{ status: string; message?: string; documents?: { title: string }[] } | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [docs, kb] = await Promise.all([
        apiClient.get<KnowledgeDocument[]>('/api/knowledge-base/documents'),
        apiClient.get<KnowledgeBaseText>('/api/knowledge-base'),
      ])
      setDocuments(docs)
      setPreview(kb)
    } catch (err) {
      console.error('Failed to load knowledge base:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const startCreate = useCallback(() => {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setIsCreating(true)
  }, [])

  const startEdit = useCallback((doc: KnowledgeDocument) => {
    setForm({ title: doc.title, category: doc.category, content: doc.content })
    setEditingId(doc.id)
    setIsCreating(true)
  }, [])

  const cancelEdit = useCallback(() => {
    setIsCreating(false)
    setEditingId(null)
    setForm(EMPTY_FORM)
  }, [])

  const handleSave = useCallback(async () => {
    if (!form.title.trim() || !form.content.trim()) return
    setIsSaving(true)
    try {
      if (editingId) {
        await apiClient.put(`/api/knowledge-base/documents/${editingId}`, form)
      } else {
        await apiClient.post('/api/knowledge-base/documents', { ...form, is_active: true })
      }
      cancelEdit()
      await load()
    } catch (err) {
      console.error('Failed to save document:', err)
    } finally {
      setIsSaving(false)
    }
  }, [form, editingId, cancelEdit, load])

  const toggleDoc = useCallback(async (id: number) => {
    try {
      await apiClient.patch(`/api/knowledge-base/documents/${id}/toggle`)
      await load()
    } catch (err) {
      console.error('Failed to toggle document:', err)
    }
  }, [load])

  const deleteDoc = useCallback(async (id: number) => {
    try {
      await apiClient.delete(`/api/knowledge-base/documents/${id}`)
      await load()
    } catch (err) {
      console.error('Failed to delete document:', err)
    }
  }, [load])

  const handleIngest = useCallback(async () => {
    setIsIngesting(true)
    setIngestResult(null)
    try {
      const result = await apiClient.post<{ status: string; documents: { title: string }[] }>('/api/knowledge-base/ingest')
      setIngestResult(result)
      await load()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ingestion failed. Is GEMINI_API_KEY set?'
      setIngestResult({ status: 'error', message })
      console.error('Failed to ingest knowledge base:', err)
    } finally {
      setIsIngesting(false)
    }
  }, [load])

  return (
    <div className="space-y-6">
      {/* Explainer */}
      <Card className="relative overflow-hidden">
        <CardWatermark opacity={3} scale={1} />
        <CardContent className="relative z-10 p-5">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-brand-cornflower/10 shrink-0">
              <Icons.layers className="h-5 w-5 text-brand-cornflower" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-brand-navy">The Knowledge Base</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Every active <span className="font-medium">AI Policy</span> plus every active reference
                document below is assembled into one plain-text corpus and sent to the Orchestrator on
                every run. Edit a policy or a document here — no code, no redeploy — and the very next
                run uses the new text.
              </p>
              {preview && (
                <p className="text-xs text-muted-foreground mt-2">
                  Currently: <span className="font-medium text-brand-navy">{preview.policy_count} active policies</span>
                  {' · '}
                  <span className="font-medium text-brand-navy">{preview.document_count} active documents</span>
                </p>
              )}
            </div>
            <Button variant="outline" size="sm" className="ml-auto shrink-0" onClick={() => setShowPreview((v) => !v)}>
              {showPreview ? 'Hide' : 'Preview'} Assembled Text
            </Button>
          </div>

          <AnimatePresence>
            {showPreview && preview && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <pre className="mt-4 max-h-96 overflow-y-auto rounded-lg bg-gray-50 border border-gray-200 p-4 text-xs whitespace-pre-wrap text-gray-700">
                  {preview.text}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Create / Edit form */}
      {isCreating ? (
        <Card>
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-semibold text-brand-navy">
                {editingId ? 'Edit Document' : 'New Reference Document'}
              </h3>
              <Button variant="ghost" size="icon" onClick={cancelEdit}>
                <Icons.close className="h-4 w-4" />
              </Button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-1.5">Title</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g., Consent & Privacy Compliance"
                  className="w-full px-3 py-2 rounded-lg border border-input text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-input text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                >
                  <option value="reference">Reference</option>
                  <option value="operator_instruction">Operator Instruction</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Content (plain text)</label>
              <textarea
                value={form.content}
                onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                rows={8}
                placeholder="Write the reference material in plain English — the agent reads this verbatim."
                className="w-full px-3 py-2 rounded-lg border border-input resize-none text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
              />
            </div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" onClick={cancelEdit}>Cancel</Button>
              <Button
                variant="gradient"
                onClick={handleSave}
                disabled={isSaving || !form.title.trim() || !form.content.trim()}
              >
                {isSaving ? <Icons.loader className="mr-2 h-4 w-4 animate-spin" /> : <Icons.check className="mr-2 h-4 w-4" />}
                Save Document
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col sm:flex-row sm:items-center justify-end gap-3">
          <Button variant="outline" onClick={handleIngest} disabled={isIngesting}>
            {isIngesting ? (
              <Icons.loader className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Icons.sparkles className="mr-2 h-4 w-4" />
            )}
            Generate from Docs (AI)
          </Button>
          <Button variant="gradient" onClick={startCreate}>
            <Icons.plus className="mr-2 h-4 w-4" />
            Add Reference Document
          </Button>
        </div>
      )}

      {ingestResult && (
        <div className={cn(
          'rounded-lg border p-3 text-sm',
          ingestResult.status === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
            : 'bg-red-50 border-red-200 text-red-700'
        )}>
          {ingestResult.status === 'success'
            ? `AI generated ${ingestResult.documents?.length ?? 0} documents from docs/*.md and data config files.`
            : ingestResult.message || 'Ingestion failed.'}
        </div>
      )}

      {/* Document list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
        </div>
      ) : documents.length === 0 ? (
        <Card className="relative overflow-hidden">
          <CardWatermark opacity={3} scale={1} />
          <CardContent className="relative z-10 flex flex-col items-center justify-center py-16 text-center">
            <h3 className="font-display text-lg font-semibold text-brand-navy">No reference documents yet</h3>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Add domain knowledge — scoring rules, compliance rules, routing logic — for the agent to use.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {documents.map((doc) => (
            <Card key={doc.id} className={cn('transition-opacity', !doc.is_active && 'opacity-50')}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-medium text-brand-navy">{doc.title}</h4>
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-[11px] font-medium text-gray-600">
                        {doc.category.replace(/_/g, ' ')}
                      </span>
                      {doc.source === 'seed' && (
                        <span className="px-2 py-0.5 rounded-full bg-blue-50 text-[11px] font-medium text-blue-600">
                          default
                        </span>
                      )}
                      <span className={cn(
                        'px-2 py-0.5 rounded-full text-[11px] font-medium',
                        doc.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'
                      )}>
                        {doc.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground line-clamp-3 whitespace-pre-wrap">
                      {doc.content}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => toggleDoc(doc.id)} title={doc.is_active ? 'Deactivate' : 'Activate'}>
                      <Icons.check className={cn('h-4 w-4', doc.is_active ? 'text-emerald-600' : 'text-gray-400')} />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => startEdit(doc)} title="Edit">
                      <Icons.pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => deleteDoc(doc.id)} title="Delete">
                      <Icons.close className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
