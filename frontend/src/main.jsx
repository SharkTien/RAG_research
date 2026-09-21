import React, { useEffect, useRef, useState, useMemo } from 'react'
import { createRoot } from 'react-dom/client'
import { marked } from 'marked'
import './styles.css'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

// ─── UTILITIES & HELPERS ────────────────────────────────────────────────────────

const formatFileSize = (bytes) => {
  if (!bytes && bytes !== 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getDocName = (doc) => {
  if (!doc) return ''
  if (typeof doc === 'string') return doc
  return doc.filename || doc.original_filename || ''
}

const getFileExtension = (filename = '') => {
  const parts = String(filename || '').split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
}

const getFileTypeMeta = (ext = '') => {
  const e = String(ext || '').toLowerCase()
  if (e === 'pdf') {
    return {
      label: 'PDF',
      iconColor: 'text-rose-500 dark:text-rose-400',
      bgLight: 'bg-rose-500/10 dark:bg-rose-500/20',
      borderColor: 'border-rose-500/20 dark:border-rose-500/30',
      badgeColor: 'bg-rose-500/10 text-rose-600 dark:text-rose-300 border-rose-500/20',
    }
  }
  if (['doc', 'docx'].includes(e)) {
    return {
      label: 'DOCX',
      iconColor: 'text-blue-500 dark:text-blue-400',
      bgLight: 'bg-blue-500/10 dark:bg-blue-500/20',
      borderColor: 'border-blue-500/20 dark:border-blue-500/30',
      badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-300 border-blue-500/20',
    }
  }
  if (['xls', 'xlsx', 'csv'].includes(e)) {
    return {
      label: e.toUpperCase(),
      iconColor: 'text-emerald-500 dark:text-emerald-400',
      bgLight: 'bg-emerald-500/10 dark:bg-emerald-500/20',
      borderColor: 'border-emerald-500/20 dark:border-emerald-500/30',
      badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300 border-emerald-500/20',
    }
  }
  if (['ppt', 'pptx'].includes(e)) {
    return {
      label: 'PPTX',
      iconColor: 'text-amber-500 dark:text-amber-400',
      bgLight: 'bg-amber-500/10 dark:bg-amber-500/20',
      borderColor: 'border-amber-500/20 dark:border-amber-500/30',
      badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-300 border-amber-500/20',
    }
  }
  return {
    label: e.toUpperCase() || 'FILE',
    iconColor: 'text-indigo-500 dark:text-indigo-400',
    bgLight: 'bg-indigo-500/10 dark:bg-indigo-500/20',
    borderColor: 'border-indigo-500/20 dark:border-indigo-500/30',
    badgeColor: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border-indigo-500/20',
  }
}

// ─── ICONS (Clean, modern SVG icons) ──────────────────────────────────────────

function Icon({ name, className = 'w-4 h-4', ...props }) {
  const icons = {
    sparkle: (
      <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z" />
    ),
    message: (
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    ),
    plus: (
      <path d="M12 5v14M5 12h14" />
    ),
    star: (
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    ),
    calendar: (
      <>
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </>
    ),
    folder: (
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    ),
    arrowUp: (
      <path d="M12 19V5M5 12l7-7 7 7" />
    ),
    arrowUpRight: (
      <path d="M7 17L17 7M7 7h10v10" />
    ),
    arrowLeft: (
      <path d="M19 12H5M12 19l-7-7 7-7" />
    ),
    chevronLeft: (
      <polyline points="15 18 9 12 15 6" />
    ),
    chevronRight: (
      <polyline points="9 18 15 12 9 6" />
    ),
    copy: (
      <>
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </>
    ),
    download: (
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3" />
    ),
    trash: (
      <>
        <polyline points="3 6 5 6 21 6" />
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </>
    ),
    edit: (
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7 M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    ),
    more: (
      <>
        <circle cx="12" cy="12" r="1" />
        <circle cx="19" cy="12" r="1" />
        <circle cx="5" cy="12" r="1" />
      </>
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </>
    ),
    moon: (
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    ),
    close: (
      <>
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </>
    ),
    fileText: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </>
    ),
    columns: (
      <>
        <path d="M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h6" />
        <path d="M14 3h6a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1h-6" />
      </>
    ),
    check: (
      <polyline points="20 6 9 17 4 12" />
    ),
    upload: (
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M17 8l-5-5-5 5 M12 3v12" />
    ),
    zoomIn: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </>
    ),
    zoomOut: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </>
    ),
    pdfIcon: (
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#f87171" stroke="#ef4444" />
    ),
    docIcon: (
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#60a5fa" stroke="#3b82f6" />
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </>
    ),
    refresh: (
      <>
        <polyline points="23 4 23 10 17 10" />
        <polyline points="1 20 1 14 7 14" />
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
      </>
    )
  }

  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {icons[name] || null}
    </svg>
  )
}

marked.setOptions({
  gfm: true,
  breaks: true,
})

// ─── CSRF INTERCEPTOR ─────────────────────────────────────────────────────────

const originalFetch = window.fetch
window.fetch = async function () {
  let [resource, config] = arguments
  if (!config) config = {}
  config.credentials = 'same-origin'
  if (!config.cache) config.cache = 'no-store'
  const csrfToken = localStorage.getItem('csrf_token')
  if (csrfToken && config.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method.toUpperCase())) {
    config.headers = {
      ...config.headers,
      'x-csrf-token': csrfToken
    }
  }
  return originalFetch(resource, config)
}

// ─── MAIN APP COMPONENT ────────────────────────────────────────────────────────

export default function App() {
  // Theme state: dark / light
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  })

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.setAttribute('data-theme', 'light')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))
  }

  // Active Main Mode: 'chat' | 'split'
  const [mainMode, setMainMode] = useState('chat')

  // Real Document state (no mock data!)
  const [documents, setDocuments] = useState([])
  const [selectedDocId, setSelectedDocId] = useState(null)
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [docSearch, setDocSearch] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  // Extraction data for selected document
  const [extractionData, setExtractionData] = useState(null)
  const [loadingExtraction, setLoadingExtraction] = useState(false)

  // PDF Viewer states (for Split view)
  const [numPages, setNumPages] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageScale, setPageScale] = useState(1.0)
  const [showOcrBoxes, setShowOcrBoxes] = useState(true)
  const [hoveredBox, setHoveredBox] = useState(null)
  const [pdfPageSizes, setPdfPageSizes] = useState({})

  // Markdown View states
  const [mdViewMode, setMdViewMode] = useState('rendered') // 'rendered' | 'raw'
  const [mdScope, setMdScope] = useState('all') // 'all' | 'page'
  const [copiedMd, setCopiedMd] = useState(false)

  // Real Chat conversation
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatBottomRef = useRef(null)
  const fileInputRef = useRef(null)

  // Current user
  const [currentUser, setCurrentUser] = useState('admin')

  // ─── AUTH & FETCH ───────────────────────────────────────────────────────────

  const checkAuth = async () => {
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        setCurrentUser(data.user || data.username || 'admin')
        if (data.csrf_token) localStorage.setItem('csrf_token', data.csrf_token)
      } else {
        autoLogin()
      }
    } catch {
      autoLogin()
    }
  }

  const autoLogin = async () => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'admin', password: 'matkhausieudai123' })
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentUser(data.username || 'admin')
        if (data.csrf_token) localStorage.setItem('csrf_token', data.csrf_token)
        fetchDocuments()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchDocuments = async () => {
    try {
      setLoadingDocs(true)
      const res = await fetch('/api/documents?page=1&size=50')
      if (res.ok) {
        const data = await res.json()
        const docs = data.items || data.documents || []
        setDocuments(docs)
        if (docs.length > 0 && !selectedDocId) {
          setSelectedDocId(docs[0].id)
        } else if (docs.length === 0) {
          setSelectedDocId(null)
        }
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingDocs(false)
    }
  }

  useEffect(() => {
    checkAuth()
    fetchDocuments()
    const interval = setInterval(fetchDocuments, 4000)
    return () => clearInterval(interval)
  }, [])

  const currentDoc = useMemo(() => {
    return documents.find(d => String(d.id) === String(selectedDocId)) || null
  }, [documents, selectedDocId])

  useEffect(() => {
    if (!selectedDocId) {
      setExtractionData(null)
      return
    }
    setLoadingExtraction(true)
    fetch(`/api/documents/${selectedDocId}/extraction`)
      .then(r => r.json())
      .then(d => {
        setExtractionData(d)
        setLoadingExtraction(false)
      })
      .catch(() => setLoadingExtraction(false))
  }, [selectedDocId])

  // ─── UPLOAD & DELETE ────────────────────────────────────────────────────────

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadError('')
    const formData = new FormData()
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i])
    }
    try {
      const res = await fetch('/api/documents', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Lỗi khi tải lên tệp')
      const data = await res.json()
      await fetchDocuments()
      if (data.uploaded && data.uploaded.length > 0) {
        setSelectedDocId(data.uploaded[0].id)
      }
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDoc = async (e, docId) => {
    e.stopPropagation()
    if (!window.confirm('Bạn có chắc muốn xóa tài liệu này khỏi cơ sở tri thức?')) return
    try {
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' })
      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.id !== docId))
        if (selectedDocId === docId) setSelectedDocId(null)
      }
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files)
    }
  }

  const filteredDocuments = useMemo(() => {
    if (!docSearch.trim()) return documents
    const q = docSearch.toLowerCase()
    return documents.filter(d => getDocName(d).toLowerCase().includes(q))
  }, [documents, docSearch])

  // ─── MARKDOWN COMPILER ───────────────────────────────────────────────────────

  const extractedObj = extractionData?.extracted_data || {}
  const normalizedElements = extractedObj.normalized_elements || []
  const ocrBoxes = extractedObj.ocr_bboxes || []
  const chunks = extractedObj.chunks || []

  const markdownText = useMemo(() => {
    if (!extractionData?.extracted_data) return ''
    const docName = getDocName(currentDoc)
    if (mdScope === 'page') {
      const pageElements = normalizedElements.filter(el => (el.page || 1) === currentPage)
      if (pageElements.length > 0) {
        return `# Trang ${currentPage} — ${docName}\n\n` + pageElements.map(el => el.text).filter(Boolean).join('\n\n')
      }
      const pageChunks = chunks.filter(c => (c.metadata?.page || 1) === currentPage)
      if (pageChunks.length > 0) {
        return `# Trang ${currentPage} — ${docName}\n\n` + pageChunks.map(c => c.text).join('\n\n')
      }
      return `# Trang ${currentPage} — ${docName}\n\n*Không có dữ liệu trích xuất cho trang này.*`
    }
    if (extractedObj.text) return extractedObj.text
    if (normalizedElements.length > 0) return normalizedElements.map(el => el.text).filter(Boolean).join('\n\n')
    return chunks.map((c, i) => `### Đoạn ${i + 1} (Trang ${c.metadata?.page || 1})\n\n${c.text}`).join('\n\n---\n\n')
  }, [extractionData, currentDoc, mdScope, currentPage, normalizedElements, chunks, extractedObj])

  const renderedHtml = useMemo(() => {
    if (!markdownText) return ''
    try {
      return marked.parse(markdownText)
    } catch {
      return markdownText
    }
  }, [markdownText])

  const copyMarkdown = () => {
    navigator.clipboard.writeText(markdownText)
    setCopiedMd(true)
    setTimeout(() => setCopiedMd(false), 2000)
  }

  const downloadMarkdown = () => {
    const filename = `${(getDocName(currentDoc) || 'tai_lieu').replace(/\.[^/.]+$/, '')}_trich_xuat.md`
    const blob = new Blob([markdownText], { type: 'text/markdown;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  // ─── CHAT QUERY ─────────────────────────────────────────────────────────────

  const handleSendMessage = async (e) => {
    e?.preventDefault()
    const q = chatInput.trim()
    if (!q || chatLoading) return
    const newMsgs = [...chatMessages, { role: 'user', text: q }]
    setChatMessages(newMsgs)
    setChatInput('')
    setChatLoading(true)

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, top_k: 5, document_id: selectedDocId || null })
      })
      if (!res.ok) throw new Error('Lỗi truy vấn AI')
      const data = await res.json()
      setChatMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: data.answer || 'Không tìm thấy thông tin phù hợp trong tài liệu.',
          sources: data.sources || []
        }
      ])
    } catch (err) {
      setChatMessages([
        ...newMsgs,
        { role: 'assistant', text: `Lỗi: ${err.message}`, sources: [] }
      ])
    } finally {
      setChatLoading(false)
      setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }
  }

  const pdfPreviewUrl = useMemo(() => {
    if (!currentDoc?.id) return ''
    const ext = getFileExtension(getDocName(currentDoc))
    if (ext === 'pdf' || currentDoc.content_type === 'application/pdf') {
      return `/api/documents/${currentDoc.id}/content`
    }
    return `/api/documents/${currentDoc.id}/preview`
  }, [currentDoc])

  // ─── RENDER BUBBLE TABLET INTERFACE ─────────────────────────────────────────

  return (
    <div className="flex h-screen w-screen p-3 md:p-5 gap-3 md:gap-5 overflow-hidden select-none text-[var(--text-primary)]">
      {/* ─── 1. THIN FLOATING PILL DOCK (FAR LEFT) ─── */}
      <aside className="w-14 shrink-0 flex flex-col items-center justify-between py-5 glass-dock z-20">
        {/* Top: Toggle Mode arrow circle */}
        <button
          onClick={() => setMainMode(mainMode === 'chat' ? 'split' : 'chat')}
          className="w-10 h-10 rounded-full bg-white/80 dark:bg-white/10 hover:scale-105 active:scale-95 transition flex items-center justify-center text-[var(--text-secondary)] shadow-sm border border-white/60 dark:border-white/10"
          title="Chuyển chế độ xem"
        >
          <Icon name="arrowLeft" className="w-4 h-4" />
        </button>

        {/* Center: Navigation Bubble Pill */}
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-10 h-10 rounded-full bg-white/80 dark:bg-white/10 hover:scale-105 active:scale-95 transition flex items-center justify-center text-[var(--text-secondary)] shadow-xs border border-white/60 dark:border-white/10"
            title="Tải tệp mới"
          >
            <Icon name="plus" className="w-4 h-4" />
          </button>

          {/* Active Chat Bubble - Blue glow */}
          <button
            onClick={() => setMainMode('chat')}
            className={`w-10 h-10 rounded-full transition flex items-center justify-center shadow-md ${
              mainMode === 'chat'
                ? 'bg-blue-600 text-white shadow-blue-500/30 scale-105'
                : 'bg-white/80 dark:bg-white/10 text-[var(--text-secondary)] hover:scale-105 border border-white/60 dark:border-white/10'
            }`}
            title="Hỏi đáp AI"
          >
            <Icon name="message" className="w-4 h-4" />
          </button>

          {/* Split Screen Dual-Pane Button */}
          <button
            onClick={() => setMainMode('split')}
            className={`w-10 h-10 rounded-full transition flex items-center justify-center shadow-xs ${
              mainMode === 'split'
                ? 'bg-blue-600 text-white shadow-blue-500/30 scale-105'
                : 'bg-white/80 dark:bg-white/10 text-[var(--text-secondary)] hover:scale-105 border border-white/60 dark:border-white/10'
            }`}
            title="Đối chiếu song song (PDF & MD)"
          >
            <Icon name="columns" className="w-4 h-4" />
          </button>

          <button
            onClick={fetchDocuments}
            className="w-10 h-10 rounded-full bg-white/80 dark:bg-white/10 hover:scale-105 active:scale-95 transition flex items-center justify-center text-[var(--text-secondary)] shadow-xs border border-white/60 dark:border-white/10"
            title="Làm mới danh sách"
          >
            <Icon name="calendar" className="w-4 h-4" />
          </button>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-10 h-10 rounded-full bg-white/80 dark:bg-white/10 hover:scale-105 active:scale-95 transition flex items-center justify-center text-[var(--text-secondary)] shadow-xs border border-white/60 dark:border-white/10"
            title="Kho tài liệu"
          >
            <Icon name="folder" className="w-4 h-4" />
          </button>
        </div>

        {/* Bottom: Theme toggle, avatar */}
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={toggleTheme}
            className="w-10 h-10 rounded-full bg-white/80 dark:bg-white/10 hover:scale-105 active:scale-95 transition flex items-center justify-center text-[var(--text-secondary)] shadow-xs border border-white/60 dark:border-white/10"
            title={theme === 'dark' ? 'Giao diện Sáng' : 'Giao diện Tối'}
          >
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="w-4 h-4" />
          </button>

          <div
            className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 via-purple-400 to-pink-500 p-0.5 shadow-sm cursor-pointer hover:scale-105 transition"
            title={`Người dùng: ${currentUser}`}
          >
            <div className="w-full h-full rounded-full bg-white dark:bg-zinc-900 flex items-center justify-center font-bold text-xs text-[var(--text-primary)]">
              {currentUser.slice(0, 2).toUpperCase()}
            </div>
          </div>
        </div>
      </aside>

      {/* ─── 2. LEFT PANEL: REAL DOCUMENTS & MEDIA UPLOAD ─── */}
      <section className="w-80 md:w-96 shrink-0 flex flex-col justify-between py-1 overflow-hidden">
        {/* Section Header */}
        <div className="px-2 mb-2 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
              Kho Tài Liệu
            </h1>
            <p className="text-xs text-[var(--text-muted)] mt-0.5 font-medium">
              Cơ sở tri thức Mini RAG • {documents.length} tài liệu
            </p>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={fetchDocuments}
              className="w-8 h-8 rounded-full bg-white/80 dark:bg-white/10 border border-white/70 dark:border-white/10 flex items-center justify-center text-[var(--text-secondary)] hover:scale-105 active:scale-95 transition shadow-xs"
              title="Làm mới danh sách"
            >
              <Icon name="refresh" className={`w-3.5 h-3.5 ${loadingDocs ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:scale-105 active:scale-95 transition shadow-xs"
              title="Tải lên tài liệu"
            >
              <Icon name="plus" className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search bar */}
        <div className="px-1 mb-2.5">
          <div className="relative">
            <Icon name="search" className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              value={docSearch}
              onChange={e => setDocSearch(e.target.value)}
              placeholder="Tìm kiếm tài liệu..."
              className="w-full pl-8.5 pr-8 py-1.5 text-xs rounded-xl bg-white/70 dark:bg-white/5 border border-black/5 dark:border-white/10 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
            />
            {docSearch && (
              <button
                onClick={() => setDocSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <Icon name="close" className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.csv,.txt"
          className="hidden"
          onChange={e => handleFileUpload(e.target.files)}
        />

        {/* Scrollable list of Document Cards */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
          {documents.length === 0 ? (
            /* Empty State when no document uploaded */
            <div
              onClick={() => fileInputRef.current?.click()}
              className="rounded-2xl p-6 text-center cursor-pointer flex flex-col items-center justify-center gap-3 border border-dashed border-black/10 dark:border-white/15 bg-white/40 dark:bg-white/[0.03] hover:border-blue-400 transition group"
            >
              <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shadow-xs group-hover:scale-110 transition">
                <Icon name="upload" className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">
                  Chưa có tài liệu nào
                </h4>
                <p className="text-[11px] text-[var(--text-muted)] mt-1 max-w-[200px] leading-relaxed">
                  Bấm vào đây hoặc kéo thả file PDF, Word để nạp tri thức cho AI.
                </p>
              </div>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="py-8 text-center text-xs text-[var(--text-muted)]">
              Không tìm thấy tài liệu phù hợp với "{docSearch}"
            </div>
          ) : (
            filteredDocuments.map((doc) => {
              const isSelected = String(doc.id) === String(selectedDocId)
              const name = getDocName(doc)
              const ext = getFileExtension(name)
              const typeMeta = getFileTypeMeta(ext)
              const isProcessing = doc.status === 'processing' || doc.status === 'queued'
              const isProcessed = doc.status === 'processed'
              const isFailed = doc.status === 'failed'

              return (
                <div
                  key={doc.id}
                  onClick={() => setSelectedDocId(doc.id)}
                  className={`doc-item-card p-3.5 cursor-pointer relative transition ${
                    isSelected ? 'is-selected' : ''
                  }`}
                >
                  {/* Top: File Icon, Name, Size, Actions */}
                  <div className="flex items-start gap-2.5">
                    <div className={`w-9 h-9 rounded-xl ${typeMeta.bgLight} ${typeMeta.borderColor} border flex items-center justify-center shrink-0`}>
                      <Icon name="fileText" className={`w-4 h-4 ${typeMeta.iconColor}`} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <h4 className="text-xs font-bold text-[var(--text-primary)] truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition" title={name}>
                          {name}
                        </h4>
                        <button
                          onClick={e => handleDeleteDoc(e, doc.id)}
                          className="opacity-50 hover:opacity-100 hover:text-rose-500 hover:bg-rose-500/10 p-1 rounded-md transition shrink-0"
                          title="Xóa tài liệu"
                        >
                          <Icon name="trash" className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-[var(--text-muted)] font-mono">
                        <span className={`px-1 py-0.2 rounded border text-[9px] font-bold ${typeMeta.badgeColor}`}>
                          {typeMeta.label}
                        </span>
                        <span>•</span>
                        <span>{formatFileSize(doc.size_bytes)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Status indicator row */}
                  <div className="mt-2.5 pt-2 border-t border-black/5 dark:border-white/5">
                    {isProcessing ? (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-medium">
                            <span className="relative flex h-2 w-2">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                            </span>
                            {doc.status === 'processing' ? 'Đang trích xuất vector...' : 'Đang trong hàng đợi...'}
                          </span>
                          <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-700 dark:text-amber-300 font-semibold border border-amber-500/20">
                            Processing
                          </span>
                        </div>
                        {/* Animated progress bar */}
                        <div className="w-full bg-amber-500/15 dark:bg-amber-500/20 rounded-full h-1 overflow-hidden">
                          <div className="bg-gradient-to-r from-amber-400 to-orange-500 h-1 rounded-full animate-pulse w-3/4" />
                        </div>
                      </div>
                    ) : isFailed ? (
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1">
                          Lỗi xử lý tài liệu
                        </span>
                        <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-700 dark:text-rose-300 font-semibold border border-rose-500/20">
                          Failed
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                          <Icon name="check" className="w-3 h-3 text-emerald-500" />
                          Đã nạp kiến thức pgvector
                        </span>
                        <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-500/20">
                          Vectorized
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Bottom selection indicator */}
                  <div className="mt-2 flex items-center justify-between text-[10px]">
                    <div className="flex items-center gap-1.5 font-medium">
                      <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                      <span className={isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-[var(--text-muted)]'}>
                        {isSelected ? 'Đang chọn' : 'Bấm để chọn'}
                      </span>
                    </div>
                    {isSelected && (
                      <span className="text-blue-600 dark:text-blue-400 flex items-center gap-0.5 font-medium">
                        Đối chiếu <Icon name="arrowUpRight" className="w-2.5 h-2.5" />
                      </span>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Upload error banner if any */}
        {uploadError && (
          <div className="p-2.5 text-xs text-rose-600 bg-rose-500/10 rounded-xl border border-rose-500/20 my-2">
            {uploadError}
          </div>
        )}

        {/* Media Upload Dropzone (Styled like UI.png) */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-2.5 p-3.5 rounded-2xl border-2 border-dashed transition cursor-pointer flex flex-col items-center justify-center gap-1.5 text-center group ${
            isDragging
              ? 'border-blue-500 bg-blue-500/10 scale-[1.01]'
              : 'border-black/10 dark:border-white/15 bg-white/50 dark:bg-white/[0.03] hover:border-blue-400 dark:hover:border-blue-400/60 hover:bg-white/80 dark:hover:bg-white/[0.06]'
          }`}
        >
          <div className="w-9 h-9 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center group-hover:scale-110 transition shadow-xs">
            {uploading ? (
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
            ) : (
              <Icon name="upload" className="w-4 h-4" />
            )}
          </div>
          <div>
            <div className="text-xs font-bold text-[var(--text-primary)]">
              {uploading ? 'Đang tải lên và xử lý...' : (
                <>Kéo thả tài liệu vào đây hoặc <span className="text-blue-600 dark:text-blue-400 underline decoration-dotted">chọn tệp</span></>
              )}
            </div>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
              Hỗ trợ PDF, DOCX, XLSX, TXT (tối đa 500MB)
            </p>
          </div>
        </div>
      </section>

      {/* ─── 3. RIGHT MAIN PANEL: FROSTED GLASS PANEL ─── */}
      <main className="flex-1 glass-panel flex flex-col overflow-hidden relative">
        {/* Panel Header */}
        <header className="h-16 px-6 border-b border-black/5 dark:border-white/10 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-white/80 dark:bg-white/10 flex items-center justify-center text-[var(--text-primary)] shadow-2xs border border-white/80 dark:border-white/10">
              <Icon name="sparkle" className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
                {mainMode === 'chat' ? 'Hỏi Đáp Tri Thức AI' : 'Đối Chiếu Song Song'}
              </h2>
              <span className="text-[11px] text-[var(--text-muted)] font-medium">
                {currentDoc ? getDocName(currentDoc) : 'Chưa chọn tài liệu'}
              </span>
            </div>
          </div>

          {/* Mode Pill Switcher */}
          <div className="flex items-center p-1 rounded-full bg-black/5 dark:bg-white/10 border border-white/60 dark:border-white/10 text-xs font-semibold">
            <button
              onClick={() => setMainMode('chat')}
              className={`px-4 py-1.5 rounded-full transition ${
                mainMode === 'chat'
                  ? 'bg-white dark:bg-zinc-800 text-[var(--text-primary)] shadow-xs'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              Hỏi đáp AI
            </button>
            <button
              onClick={() => setMainMode('split')}
              className={`px-4 py-1.5 rounded-full transition ${
                mainMode === 'split'
                  ? 'bg-white dark:bg-zinc-800 text-[var(--text-primary)] shadow-xs'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              Đối chiếu PDF & MD
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setMainMode(mainMode === 'chat' ? 'split' : 'chat')}
              className="w-9 h-9 rounded-full bg-white/80 dark:bg-white/10 hover:bg-white transition flex items-center justify-center text-[var(--text-secondary)] shadow-2xs border border-white/60 dark:border-white/10"
              title="Chuyển chế độ"
            >
              <Icon name="columns" className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* ═══ VIEW 1: CHAT VIEW (TRANSLUCENT GRADIENT CARDS) ═══ */}
        {mainMode === 'chat' ? (
          <div className="flex-1 flex flex-col justify-between overflow-hidden relative p-6">
            <div className="flex-1 overflow-y-auto pr-2 space-y-6 max-w-3xl mx-auto w-full">
              {/* Real Welcome Header */}
              <div className="flex items-center gap-3 pt-2">
                <div className="w-12 h-12 rounded-full overflow-hidden bg-gradient-to-tr from-blue-400 via-indigo-500 to-purple-500 p-0.5 shadow-sm">
                  <div className="w-full h-full rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center font-bold text-sm text-[var(--text-primary)]">
                    AI
                  </div>
                </div>
                <div>
                  <span className="text-xs text-[var(--text-muted)] font-medium">Xin chào, {currentUser}!</span>
                  <h3 className="text-lg font-bold text-[var(--text-primary)]">
                    Tôi có thể giúp gì cho bạn hôm nay?
                  </h3>
                </div>
              </div>

              {/* Floating Document Badge Stack (Only when real doc is selected) */}
              {currentDoc ? (
                <div className="flex items-center justify-end my-2">
                  <div className="flex items-center gap-3 bg-white/75 dark:bg-white/10 p-3 rounded-[24px] border border-white/80 dark:border-white/10 shadow-xs backdrop-blur-md">
                    <div className="w-9 h-11 rounded-lg bg-white dark:bg-zinc-800 shadow-sm border border-red-200 flex flex-col items-center justify-center p-1 -rotate-3">
                      <Icon name="pdfIcon" className="w-5 h-5 text-red-500" />
                      <span className="text-[8px] font-bold text-red-500 mt-0.5">PDF</span>
                    </div>
                    <div className="pr-2 max-w-[220px]">
                      <span className="text-xs font-bold text-[var(--text-primary)] block truncate">
                        {getDocName(currentDoc)}
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)] font-mono">
                        {extractedObj.metadata?.page_count || 1} trang • {chunks.length} chunks đã nạp
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 px-4 rounded-[28px] border border-dashed border-black/10 dark:border-white/10 bg-white/30 dark:bg-white/5 backdrop-blur-xs max-w-lg mx-auto">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    Chưa có tài liệu nào được chọn
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Hãy bấm nút "Tải thêm tài liệu kiến thức" bên trái để tải lên tệp PDF/DOCX cần hỏi đáp.
                  </p>
                </div>
              )}

              {/* Message List */}
              {chatMessages.map((msg, idx) => {
                const isUser = msg.role === 'user'

                return (
                  <div
                    key={idx}
                    className={`flex gap-3 text-sm leading-relaxed ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isUser && (
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold text-xs flex items-center justify-center shrink-0 mt-1 shadow-xs">
                        AI
                      </div>
                    )}

                    <div
                      className={`max-w-xl p-5 rounded-[26px] shadow-xs ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-md font-medium'
                          : 'bg-white/80 dark:bg-white/10 text-[var(--text-primary)] rounded-tl-md border border-white/70 dark:border-white/10 backdrop-blur-md'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>

                      {/* Source citations */}
                      {!isUser && msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-black/5 dark:border-white/10 space-y-2">
                          <span className="text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider block">
                            Nguồn trích dẫn ({msg.sources.length}):
                          </span>
                          <div className="space-y-1.5">
                            {msg.sources.map((src, sIdx) => (
                              <div
                                key={sIdx}
                                onClick={() => {
                                  setCurrentPage(src.page || 1)
                                  setMainMode('split')
                                }}
                                className="p-2.5 rounded-[16px] bg-white/90 dark:bg-black/30 border border-white/80 dark:border-white/10 hover:border-blue-400 cursor-pointer transition shadow-2xs text-xs"
                              >
                                <div className="flex items-center justify-between font-mono text-[11px] mb-1">
                                  <span className="font-bold text-blue-600 dark:text-blue-400">
                                    {src.file_name} (Trang {src.page || '1'})
                                  </span>
                                  {src.similarity_score && (
                                    <span className="text-emerald-600 dark:text-emerald-400 text-[10px]">
                                      {(src.similarity_score * 100).toFixed(1)}% match
                                    </span>
                                  )}
                                </div>
                                <p className="text-[var(--text-muted)] text-[11px] line-clamp-2 italic font-mono">
                                  "{src.content_snippet}"
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}

              {chatLoading && (
                <div className="flex gap-3 text-sm justify-start">
                  <div className="w-8 h-8 rounded-full bg-indigo-500 text-white font-bold text-xs flex items-center justify-center shrink-0">
                    AI
                  </div>
                  <div className="p-4 rounded-[22px] bg-white/80 dark:bg-white/10 border border-white/70 dark:border-white/10 text-[var(--text-muted)] font-mono text-xs animate-pulse">
                    Đang tìm kiếm vector và tổng hợp câu trả lời từ tài liệu...
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Bottom Actions: Quick Tool Cards + Pill Input Bar with Gradient Fades */}
            <div className="mt-4 max-w-3xl mx-auto w-full space-y-3">
              <div className="grid grid-cols-4 gap-2.5">
                <div
                  onClick={() => setMainMode('split')}
                  className="glass-tool-card p-2.5 cursor-pointer flex flex-col items-center justify-center text-center gap-1 group"
                >
                  <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center group-hover:scale-110 transition shadow-2xs">
                    <Icon name="pdfIcon" className="w-4 h-4" />
                  </div>
                  <span className="text-[11px] font-bold text-[var(--text-primary)]">Xem tệp PDF</span>
                </div>

                <div
                  onClick={() => {
                    setMainMode('split')
                    setMdViewMode('rendered')
                  }}
                  className="glass-tool-card p-2.5 cursor-pointer flex flex-col items-center justify-center text-center gap-1 group"
                >
                  <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center group-hover:scale-110 transition shadow-2xs">
                    <Icon name="fileText" className="w-4 h-4" />
                  </div>
                  <span className="text-[11px] font-bold text-[var(--text-primary)]">Trích xuất .md</span>
                </div>

                <div
                  onClick={() => {
                    setMainMode('split')
                    setShowOcrBoxes(true)
                  }}
                  className="glass-tool-card p-2.5 cursor-pointer flex flex-col items-center justify-center text-center gap-1 group"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center group-hover:scale-110 transition shadow-2xs">
                    <Icon name="sparkle" className="w-4 h-4" />
                  </div>
                  <span className="text-[11px] font-bold text-[var(--text-primary)]">Khung BBox</span>
                </div>

                <div
                  onClick={() => setMainMode('split')}
                  className="glass-tool-card p-2.5 cursor-pointer flex flex-col items-center justify-center text-center gap-1 group"
                >
                  <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 flex items-center justify-center group-hover:scale-110 transition shadow-2xs">
                    <Icon name="columns" className="w-4 h-4" />
                  </div>
                  <span className="text-[11px] font-bold text-[var(--text-primary)]">Đối chiếu đôi</span>
                </div>
              </div>

              {/* Frosted Pill Input Bar with Upward Arrow Send Button */}
              <form onSubmit={handleSendMessage} className="relative flex items-center">
                <input
                  type="text"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  placeholder="Hỏi bất kỳ điều gì về tài liệu..."
                  className="w-full h-14 pl-6 pr-16 rounded-full glass-pill-input text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:ring-2 focus:ring-blue-500/20 font-medium"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || chatLoading}
                  className="absolute right-2.5 w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center hover:scale-105 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition shadow-sm"
                >
                  <Icon name="arrowUp" className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        ) : (
          /* ═══ VIEW 2: ĐỐI CHIẾU SONG SONG (SPLIT SCREEN) ═══ */
          <div className="flex-1 flex overflow-hidden p-4 gap-4">
            {/* PANE TRÁI: XEM TRƯỚC FILE (PDF & BBOX) */}
            <div className="flex-1 glass-subcard flex flex-col overflow-hidden bg-white/70 dark:bg-black/30">
              <div className="h-12 px-4 border-b border-black/5 dark:border-white/10 flex items-center justify-between shrink-0 text-xs">
                <div className="flex items-center gap-1.5 font-mono">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}
                    className="w-7 h-7 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center disabled:opacity-30 transition shadow-2xs"
                  >
                    <Icon name="chevronLeft" className="w-3.5 h-3.5" />
                  </button>
                  <span className="font-bold px-1.5 text-[var(--text-primary)]">
                    {currentPage} / {numPages || 1}
                  </span>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(numPages || 1, p + 1))}
                    disabled={currentPage >= (numPages || 1)}
                    className="w-7 h-7 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center disabled:opacity-30 transition shadow-2xs"
                  >
                    <Icon name="chevronRight" className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPageScale(s => Math.max(0.6, s - 0.1))}
                    className="w-7 h-7 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center shadow-2xs"
                    title="Thu nhỏ"
                  >
                    <Icon name="zoomOut" className="w-3 h-3" />
                  </button>
                  <span className="font-mono text-[11px] text-[var(--text-secondary)]">
                    {Math.round(pageScale * 100)}%
                  </span>
                  <button
                    onClick={() => setPageScale(s => Math.min(2.0, s + 0.1))}
                    className="w-7 h-7 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center shadow-2xs"
                    title="Phóng to"
                  >
                    <Icon name="zoomIn" className="w-3 h-3" />
                  </button>

                  <div className="h-4 w-px bg-black/10 dark:bg-white/10 mx-1" />

                  <button
                    onClick={() => setShowOcrBoxes(!showOcrBoxes)}
                    className={`px-3 py-1 rounded-full text-[11px] font-semibold transition ${
                      showOcrBoxes ? 'bg-blue-600 text-white' : 'bg-white dark:bg-zinc-800 text-[var(--text-muted)]'
                    }`}
                  >
                    OCR Box
                  </button>
                </div>
              </div>

              {/* PDF Content */}
              <div className="flex-1 overflow-auto p-4 flex flex-col items-center relative">
                {!currentDoc ? (
                  <div className="py-20 text-xs text-[var(--text-muted)]">Chưa chọn tài liệu</div>
                ) : (
                  <Document
                    file={pdfPreviewUrl}
                    onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                    loading={<div className="py-20 text-xs text-[var(--text-muted)] font-mono">Đang nạp PDF...</div>}
                  >
                    {(() => {
                      const renderWidth = 520 * pageScale
                      const pageSize = pdfPageSizes[currentPage]
                      const scale = pageSize ? renderWidth / pageSize.width : 1
                      const pageOcr = ocrBoxes.filter(i => (i.page_no || 1) === currentPage)

                      return (
                        <div className="relative rounded-[16px] overflow-hidden shadow-sm border border-black/5 dark:border-white/10 bg-white">
                          <Page
                            pageNumber={currentPage}
                            width={renderWidth}
                            renderTextLayer={false}
                            renderAnnotationLayer={false}
                            onLoadSuccess={pdfPage => {
                              const vp = pdfPage.getViewport({ scale: 1 })
                              setPdfPageSizes(old => ({ ...old, [currentPage]: { width: vp.width, height: vp.height } }))
                            }}
                          />

                          {pageSize && showOcrBoxes && (
                            <div className="absolute inset-0 pointer-events-none">
                              {pageOcr.map((box, i) => (
                                <div
                                  key={i}
                                  onMouseEnter={e => setHoveredBox({ text: box.text, page: currentPage, x: e.clientX, y: e.clientY })}
                                  onMouseLeave={() => setHoveredBox(null)}
                                  style={{
                                    position: 'absolute',
                                    left: box.bbox.left * scale,
                                    bottom: box.bbox.bottom * scale,
                                    width: Math.max(8, (box.bbox.right - box.bbox.left) * scale),
                                    height: Math.max(8, (box.bbox.top - box.bbox.bottom) * scale),
                                    border: '1.5px solid rgba(59, 130, 246, 0.75)',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    cursor: 'pointer',
                                    pointerEvents: 'auto',
                                    borderRadius: '2px',
                                  }}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </Document>
                )}

                {hoveredBox && (
                  <div
                    className="fixed z-50 bg-white/95 dark:bg-zinc-900/95 text-[var(--text-primary)] text-xs p-3 rounded-2xl border border-white/80 dark:border-white/10 shadow-lg max-w-xs pointer-events-none font-mono"
                    style={{ left: Math.min(window.innerWidth - 260, hoveredBox.x + 12), top: hoveredBox.y + 12 }}
                  >
                    <div className="text-[10px] text-blue-500 font-bold mb-1">OCR TRANG {hoveredBox.page}</div>
                    <div className="line-clamp-3">{hoveredBox.text}</div>
                  </div>
                )}
              </div>
            </div>

            {/* PANE PHẢI: THÔNG TIN TRÍCH XUẤT DẠNG .MD */}
            <div className="flex-1 glass-subcard flex flex-col overflow-hidden bg-white/70 dark:bg-black/30">
              <div className="h-12 px-4 border-b border-black/5 dark:border-white/10 flex items-center justify-between shrink-0 text-xs">
                <div className="flex items-center gap-2">
                  <div className="flex p-0.5 rounded-full bg-black/5 dark:bg-white/10 text-[11px] font-semibold">
                    <button
                      onClick={() => setMdViewMode('rendered')}
                      className={`px-3 py-1 rounded-full transition ${
                        mdViewMode === 'rendered' ? 'bg-white dark:bg-zinc-800 text-[var(--text-primary)] shadow-xs' : 'text-[var(--text-muted)]'
                      }`}
                    >
                      Markdown
                    </button>
                    <button
                      onClick={() => setMdViewMode('raw')}
                      className={`px-3 py-1 rounded-full transition ${
                        mdViewMode === 'raw' ? 'bg-white dark:bg-zinc-800 text-[var(--text-primary)] shadow-xs' : 'text-[var(--text-muted)]'
                      }`}
                    >
                      Mã .md thô
                    </button>
                  </div>

                  <button
                    onClick={() => setMdScope(mdScope === 'all' ? 'page' : 'all')}
                    className="px-2.5 py-1 rounded-full bg-black/5 dark:bg-white/10 text-[11px] font-semibold text-[var(--text-secondary)]"
                  >
                    {mdScope === 'all' ? 'Toàn bộ file' : `Trang ${currentPage}`}
                  </button>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={copyMarkdown}
                    className="w-8 h-8 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center text-[var(--text-secondary)] transition shadow-2xs"
                    title="Sao chép Markdown"
                  >
                    <Icon name={copiedMd ? 'check' : 'copy'} className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={downloadMarkdown}
                    className="w-8 h-8 rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center text-[var(--text-secondary)] transition shadow-2xs"
                    title="Tải tệp .md"
                  >
                    <Icon name="download" className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Markdown Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {loadingExtraction ? (
                  <div className="text-center py-20 text-xs text-[var(--text-muted)] font-mono">
                    Đang đồng bộ dữ liệu trích xuất...
                  </div>
                ) : !markdownText ? (
                  <div className="text-center py-20 text-xs text-[var(--text-muted)]">
                    Chưa có văn bản trích xuất cho tài liệu này.
                  </div>
                ) : mdViewMode === 'rendered' ? (
                  <div className="markdown-body max-w-2xl mx-auto" dangerouslySetInnerHTML={{ __html: renderedHtml }} />
                ) : (
                  <pre className="text-xs font-mono p-4 rounded-2xl bg-white/60 dark:bg-black/40 text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
                    {markdownText}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Floating Right Action Rail */}
        <aside className="absolute right-5 top-20 flex flex-col gap-2.5 z-10">
          <button
            onClick={() => setMainMode(mainMode === 'chat' ? 'split' : 'chat')}
            className="w-9 h-9 rounded-full bg-white/80 dark:bg-white/10 border border-white/80 dark:border-white/10 flex items-center justify-center text-[var(--text-secondary)] hover:scale-105 active:scale-95 transition shadow-xs"
            title="Đổi khung làm việc"
          >
            <Icon name="edit" className="w-4 h-4" />
          </button>
          <button
            onClick={copyMarkdown}
            className="w-9 h-9 rounded-full bg-white/80 dark:bg-white/10 border border-white/80 dark:border-white/10 flex items-center justify-center text-[var(--text-secondary)] hover:scale-105 active:scale-95 transition shadow-xs"
            title="Sao chép nội dung"
          >
            <Icon name="copy" className="w-4 h-4" />
          </button>
        </aside>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
