'use client'

import { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'

export default function WorkbenchLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  
  const isUsers = pathname.includes('/users')
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
          Workbench
        </h1>
        <p className='mt-2 text-lg text-muted-foreground'>
          Access your AI tools, handle exceptions, and communicate with users.
        </p>
      </motion.div>
      
      {/* Navigation */}
      <div className="flex space-x-4 border-b pb-2">
        <Link 
          href="/workbench" 
          className={`pb-2 px-1 border-b-2 font-medium text-sm ${!isUsers ? 'border-brand-primary text-brand-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
        >
          Exceptions Inbox
        </Link>
        <Link 
          href="/workbench/users" 
          className={`pb-2 px-1 border-b-2 font-medium text-sm ${isUsers ? 'border-brand-primary text-brand-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
        >
          User Communications
        </Link>
      </div>

      <div>
        {children}
      </div>
    </div>
  )
}
