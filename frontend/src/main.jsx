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

// ─── SVG ICONS ──────────────────────────────────────────────────────────────────

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
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="19" cy="12" r="1.5" />
        <circle cx="5" cy="12" r="1.5" />
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
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </>
    ),
    close: (
      <path d="M18 6L6 18M6 6l12 12" />
    ),
    upload: (
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M17 8l-5-5-5 5 M12 3v12" />
    ),
    columns: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
        <line x1="12" y1="4" x2="12" y2="20" />
      </>
    ),
    camera: (
      <>
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
        <circle cx="12" cy="13" r="4" />
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
    check: (
      <polyline points="20 6 9 17 4 12" />
    ),
    waveform: (
      <>
        <path d="M3 10v4" />
        <path d="M7 6v12" />
        <path d="M11 3v18" />
        <path d="M15 8v8" />
        <path d="M19 11v2" />
      </>
    )
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {icons[name] || null}
    </svg>
  )
}

// ─── MAIN APP COMPONENT ─────────────────────────────────────────────────────────

export default function App() {
  const [isDark, setIsDark] = useState(false)
  const [mainMode, setMainMode] = useState('chat') // 'chat' | 'split'

  // Real Database Documents
  const [documents, setDocuments] = useState([])
  const [selectedDocId, setSelectedDocId] = useState(null)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  // Real Extraction Data
  const [extractionData, setExtractionData] = useState(null)
  const [loadingExtraction, setLoadingExtraction] = useState(false)

  // PDF Viewer States
  const [numPages, setNumPages] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageScale, setPageScale] = useState(1.0)
  const [showOcrBoxes, setShowOcrBoxes] = useState(true)
  const [pdfPageSizes, setPdfPageSizes] = useState({})

  // Markdown States
  const [mdViewMode, setMdViewMode] = useState('rendered')
  const [copiedMd, setCopiedMd] = useState(false)

  // Real Chat State (NO MOCK MESSAGES)
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [recentQueries, setRecentQueries] = useState([])
  const chatBottomRef = useRef(null)
  const fileInputRef = useRef(null)

  // Real Authenticated User
  const [currentUser, setCurrentUser] = useState('admin')

  // Auto Theme
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
      document.documentElement.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.removeAttribute('data-theme')
    }
  }, [isDark])

  // Authentication & Session
  const checkAuth = async () => {
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        setCurrentUser(data.username || data.user || 'admin')
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
        fetchDocuments()
      }
    } catch (err) {
      console.error(err)
    }
  }

  // Fetch Real Documents
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
    return documents.find(d => String(d.id) === String(selectedDocId)) || documents[0] || null
  }, [documents, selectedDocId])

  // Fetch Extraction Data for Active Document
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

  // Real Upload Handler
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
    if (!window.confirm('Bạn có chắc muốn xóa tài liệu này khỏi hệ thống?')) return
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
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files) {
      handleFileUpload(e.dataTransfer.files)
    }
  }

  // Real RAG Query Handler (Using User's Hybrid Search & LLM)
  const handleSendChat = async (presetText) => {
    const query = (presetText || chatInput).trim()
    if (!query || chatLoading) return

    const newMsg = { role: 'user', text: query }
    setChatMessages(prev => [...prev, newMsg])
    setRecentQueries(prev => [query, ...prev.filter(q => q !== query)].slice(0, 5))
    if (!presetText) setChatInput('')
    setChatLoading(true)

    try {
      const bodyPayload = {
        query: query,
        top_k: 10
      }
      if (currentDoc) {
        bodyPayload.document_id = currentDoc.id
      }

      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload)
      })

      if (res.ok) {
        const data = await res.json()
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            text: data.answer || 'Không tìm thấy câu trả lời phù hợp trong tài liệu.',
            sources: data.sources || [],
            retrieved_chunks: data.retrieved_chunks || []
          }
        ])
      } else {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            text: 'Không thể xử lý truy vấn RAG lúc này. Vui lòng thử lại.'
          }
        ])
      }
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Lỗi kết nối API: ${err.message}`
        }
      ])
    } finally {
      setChatLoading(false)
      setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }
  }

  const extractedObj = extractionData?.extraction || {}
  const chunks = extractedObj.chunks || []
  const fullMarkdown = extractedObj.normalized_markdown || extractedObj.raw_markdown || ''

  return (
    <div className="min-h-screen w-screen p-2 sm:p-4 md:p-6 lg:p-8 flex items-center justify-center overflow-hidden">
      {/* ═══ 3D BUBBLE TABLET CONTAINER ═══ */}
      <div className="w-full max-w-[1520px] h-[95vh] bubble-tablet-frame flex overflow-hidden p-3 md:p-4 gap-3 md:gap-4 relative">

        {/* ─── 1. LEFT SLIM FLOATING PILL DOCK ─── */}
        <aside className="w-14 shrink-0 floating-vertical-dock flex flex-col justify-between items-center py-4 px-1.5 shadow-sm">
          {/* Top Arrow Back */}
          <button
            onClick={() => setMainMode('chat')}
            className="circle-btn w-9 h-9"
            title="Trang chủ"
          >
            <Icon name="arrowLeft" className="w-4 h-4" />
          </button>

          {/* Center Navigation Icons */}
          <div className="flex flex-col items-center gap-3 w-full py-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="circle-btn w-9 h-9"
              title="Tải lên tệp PDF"
            >
              <Icon name="plus" className="w-4 h-4" />
            </button>

            {/* Active Blue Chat Pill */}
            <button
              onClick={() => setMainMode('chat')}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition shadow-md ${
                mainMode === 'chat'
                  ? 'bg-blue-600 text-white shadow-blue-500/35'
                  : 'bg-white/70 dark:bg-white/10 text-[var(--text-secondary)]'
              }`}
              title="Hỏi đáp AI"
            >
              <Icon name="message" className="w-4 h-4" />
            </button>

            <button
              onClick={() => setMainMode('split')}
              className={`w-9 h-9 rounded-full flex items-center justify-center transition ${
                mainMode === 'split'
                  ? 'bg-blue-600 text-white'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
              title="Đối chiếu PDF & Markdown"
            >
              <Icon name="folder" className="w-4 h-4" />
            </button>
          </div>

          {/* Bottom Icons: Theme Toggle, Refresh, User Avatar */}
          <div className="flex flex-col items-center gap-3 w-full">
            <button
              onClick={() => setIsDark(!isDark)}
              className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] transition"
              title={isDark ? 'Chế độ Sáng' : 'Chế độ Tối'}
            >
              <Icon name={isDark ? 'sun' : 'moon'} className="w-4 h-4" />
            </button>

            <button
              onClick={fetchDocuments}
              className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] transition"
              title="Làm mới danh sách"
            >
              <Icon name="settings" className="w-4 h-4" />
            </button>

            {/* User Avatar Badge (No broken image links) */}
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-500 to-purple-500 p-0.5 shadow-xs flex items-center justify-center text-white font-bold text-xs shrink-0">
              <div className="w-full h-full rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center text-[var(--text-primary)] font-bold text-[11px]">
                {currentUser.slice(0, 2).toUpperCase()}
              </div>
            </div>
          </div>
        </aside>

        {/* ─── 2. MIDDLE / LEFT COLUMN: REAL DOCUMENTS ─── */}
        <section className="w-80 md:w-[350px] shrink-0 flex flex-col justify-between overflow-hidden px-1 py-1">
          <div className="flex-1 overflow-y-auto pr-1 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between px-1">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                  Chat Results
                </h2>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  {documents.length} tài liệu trong cơ sở tri thức
                </p>
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="circle-btn w-8 h-8"
                title="Tải lên tệp mới"
              >
                <Icon name="plus" className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* ─── REAL HERO DOCUMENT CARD (ACTIVE DOCUMENT) ─── */}
            {currentDoc ? (
              <div>
                <div className="text-xs font-semibold text-[var(--text-muted)] mb-2 px-1">
                  Đang chọn (Active)
                </div>

                <div
                  onClick={() => setSelectedDocId(currentDoc.id)}
                  className="hero-doc-card p-3.5 cursor-pointer relative group ring-2 ring-blue-500/30"
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="circle-btn-dark w-8 h-8 shrink-0">
                        <Icon name="fileText" className="w-4 h-4" />
                      </div>
                      <div className="min-w-0 max-w-[190px]">
                        <h4 className="text-xs font-bold text-[var(--text-primary)] truncate" title={getDocName(currentDoc)}>
                          {getDocName(currentDoc)}
                        </h4>
                        <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                          {formatFileSize(currentDoc.size_bytes)} • {currentDoc.status}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setMainMode('split')
                      }}
                      className="circle-btn w-8 h-8 shrink-0"
                      title="Mở xem đối chiếu PDF & Markdown"
                    >
                      <Icon name="arrowUpRight" className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Center Visual Area: Real Document Preview (React-PDF thumbnail) */}
                  <div className="hero-preview-box p-3 min-h-[175px] relative overflow-hidden flex items-center justify-between">
                    {/* Left: Real Page 1 Rendered Thumbnail */}
                    <div className="w-44 h-36 rounded-2xl overflow-hidden shadow-xs flex items-center justify-center relative bg-white dark:bg-zinc-900 border border-black/5 dark:border-white/10">
                      <Document
                        file={`/api/documents/${currentDoc.id}/file`}
                        loading={
                          <div className="text-[10px] text-[var(--text-muted)] flex flex-col items-center gap-1">
                            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                            Đang nạp trang 1...
                          </div>
                        }
                        error={
                          <div className="text-[10px] text-[var(--text-muted)] p-2 text-center">
                            <Icon name="fileText" className="w-8 h-8 text-blue-500 mx-auto mb-1" />
                            <span>{getDocName(currentDoc).slice(0, 20)}</span>
                          </div>
                        }
                      >
                        <Page
                          pageNumber={1}
                          width={170}
                          renderTextLayer={false}
                          renderAnnotationLayer={false}
                        />
                      </Document>
                    </div>

                    {/* Right Stacked Page Indicators */}
                    <div className="flex flex-col items-center gap-2 pr-1">
                      <div className="w-9 h-9 rounded-full bg-white/90 dark:bg-zinc-800 shadow-xs border border-white/80 dark:border-white/10 flex items-center justify-center font-bold text-[10px] text-blue-600 dark:text-blue-400">
                        P1
                      </div>
                      <div className="w-9 h-9 rounded-full bg-white/90 dark:bg-zinc-800 shadow-xs border border-white/80 dark:border-white/10 flex items-center justify-center font-bold text-[10px] text-[var(--text-secondary)]">
                        P2
                      </div>
                      <div className="w-9 h-9 rounded-full bg-white/80 dark:bg-white/10 backdrop-blur-md border border-white/90 dark:border-white/15 flex items-center justify-center font-bold text-[10px] text-[var(--text-muted)] shadow-xs">
                        {extractedObj.metadata?.page_count ? `+${Math.max(1, extractedObj.metadata.page_count - 2)}` : '+...'}
                      </div>
                    </div>
                  </div>

                  {/* Bottom Info Pill Inside Card */}
                  <div className="frosted-sub-pill p-2.5 px-3 flex items-center gap-2.5 mt-3">
                    <div className="w-5 h-5 rounded-full bg-[#18181b] text-white flex items-center justify-center shrink-0">
                      <Icon name="check" className="w-2.5 h-2.5 text-emerald-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-bold text-[var(--text-primary)] block truncate">
                        {currentDoc.status === 'processed' ? 'Đã lập chỉ mục pgvector' : 'Đang xử lý tài liệu'}
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)] block truncate">
                        {chunks.length > 0 ? `${chunks.length} chunks • Hybrid Search RRF` : 'Đang đồng bộ vector chunks...'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Empty State when no document */
              <div
                onClick={() => fileInputRef.current?.click()}
                className="hero-doc-card p-6 text-center cursor-pointer flex flex-col items-center justify-center gap-2 border border-dashed border-black/10 dark:border-white/10"
              >
                <div className="w-12 h-12 rounded-full bg-blue-600/10 text-blue-600 flex items-center justify-center">
                  <Icon name="upload" className="w-5 h-5" />
                </div>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">
                  Chưa có tài liệu nào
                </h4>
                <p className="text-[11px] text-[var(--text-muted)]">
                  Bấm vào đây hoặc kéo thả file PDF vào để bắt đầu.
                </p>
              </div>
            )}

            {/* ─── REAL RECENT QUERIES (IF USER HAS ASKED QUESTIONS) ─── */}
            {recentQueries.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-[var(--text-muted)] mb-2 px-1">
                  Truy vấn gần đây
                </div>
                <div className="space-y-1.5">
                  {recentQueries.map((q, qIdx) => (
                    <div
                      key={qIdx}
                      onClick={() => handleSendChat(q)}
                      className="frosted-sub-pill p-2 px-3 flex items-center justify-between cursor-pointer hover:border-blue-400 transition"
                    >
                      <span className="text-[11px] font-medium text-[var(--text-primary)] truncate max-w-[240px]">
                        {q}
                      </span>
                      <Icon name="arrowUpRight" className="w-3 h-3 text-[var(--text-muted)]" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ─── REMAINING REAL DOCUMENTS LIST ─── */}
            {documents.length > 1 && (
              <div>
                <div className="text-xs font-semibold text-[var(--text-muted)] mb-2 px-1">
                  Tài liệu khác ({documents.length - 1})
                </div>
                <div className="space-y-2">
                  {documents.filter(d => d.id !== currentDoc?.id).map(doc => (
                    <div
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id)}
                      className="frosted-sub-pill p-3 flex items-center justify-between cursor-pointer hover:border-blue-400 transition"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-xl bg-red-500/10 text-red-500 flex items-center justify-center font-bold text-[10px] shrink-0">
                          PDF
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-bold text-[var(--text-primary)] block truncate" title={getDocName(doc)}>
                            {getDocName(doc)}
                          </span>
                          <span className="text-[10px] text-[var(--text-muted)]">
                            {formatFileSize(doc.size_bytes)} • {doc.status}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={e => handleDeleteDoc(e, doc.id)}
                        className="opacity-40 hover:opacity-100 p-1 text-rose-500 transition"
                        title="Xóa tệp"
                      >
                        <Icon name="trash" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Hidden File Input & Upload Dropzone */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.csv,.txt"
            className="hidden"
            onChange={e => handleFileUpload(e.target.files)}
          />

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`mt-2 p-2.5 rounded-2xl border border-dashed text-center cursor-pointer transition ${
              isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-black/10 dark:border-white/10 hover:bg-white/40'
            }`}
          >
            <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
              {uploading ? 'Đang tải lên và xử lý...' : '+ Kéo thả hoặc chọn thêm file PDF'}
            </span>
          </div>
        </section>

        {/* ─── 3. RIGHT MAIN PANEL: REAL RAG CHAT & DUAL-PANE WORKSPACE ─── */}
        <main className="flex-1 bubble-tablet-frame bg-white/70 dark:bg-white/5 flex flex-col overflow-hidden relative">

          {/* Top Panel Header */}
          <header className="h-14 px-5 border-b border-black/5 dark:border-white/10 flex items-center justify-between shrink-0">
            <button className="circle-btn w-8 h-8">
              <Icon name="sparkle" className="w-4 h-4 text-blue-600" />
            </button>

            <h2 className="text-base font-bold tracking-tight text-[var(--text-primary)] truncate max-w-md">
              {mainMode === 'chat' ? (currentDoc ? getDocName(currentDoc) : 'Hỏi Đáp Tri Thức AI') : 'Đối Chiếu Song Song'}
            </h2>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 p-1 rounded-full bg-white/60 dark:bg-white/10 border border-white/80 dark:border-white/10 shadow-2xs">
                <button
                  onClick={() => setMainMode('split')}
                  className={`circle-btn w-7 h-7 ${mainMode === 'split' ? 'bg-blue-600 text-white' : ''}`}
                  title="Đối chiếu đôi PDF & Markdown"
                >
                  <Icon name="columns" className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setMainMode('chat')}
                  className={`circle-btn w-7 h-7 ${mainMode === 'chat' ? 'bg-blue-600 text-white' : ''}`}
                  title="Chế độ Chat"
                >
                  <Icon name="edit" className="w-3.5 h-3.5" />
                </button>
              </div>

              {chatMessages.length > 0 && (
                <button
                  onClick={() => setChatMessages([])}
                  className="circle-btn w-8 h-8 text-rose-500"
                  title="Xóa đoạn chat này"
                >
                  <Icon name="close" className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </header>

          {/* ═══ VIEW 1: REAL CHAT VIEW (NO MOCK DATA) ═══ */}
          {mainMode === 'chat' ? (
            <div className="flex-1 flex flex-col justify-between overflow-hidden relative p-4 md:p-6">
              <div className="flex-1 overflow-y-auto pr-2 space-y-6 max-w-2xl mx-auto w-full">

                {/* Real Greeting Row */}
                <div className="flex items-center gap-3 pt-2">
                  <div className="w-11 h-11 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-500 to-purple-500 p-0.5 shadow-xs flex items-center justify-center text-white font-bold text-xs shrink-0">
                    <div className="w-full h-full rounded-full bg-white dark:bg-zinc-800 flex items-center justify-center text-[var(--text-primary)] font-bold">
                      {currentUser.slice(0, 2).toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <span className="text-xs text-[var(--text-muted)] font-medium">Xin chào, {currentUser}!</span>
                    <h3 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
                      Tôi có thể giúp gì cho bạn về tài liệu này?
                    </h3>
                  </div>
                </div>

                {/* Empty Chat State: Real Document Overview & Real Suggested Questions */}
                {chatMessages.length === 0 && (
                  <div className="space-y-4 pt-2">
                    {currentDoc ? (
                      <>
                        {/* Real Document Information Chip */}
                        <div className="flex justify-end pr-2">
                          <div className="p-3 rounded-2xl bg-white/80 dark:bg-white/10 border border-white/90 dark:border-white/15 shadow-xs flex items-center gap-3">
                            <div className="w-8 h-9 rounded bg-red-500/10 text-red-600 font-bold text-[10px] flex items-center justify-center border border-red-500/20">
                              PDF
                            </div>
                            <div>
                              <span className="text-xs font-bold text-[var(--text-primary)] block truncate max-w-[260px]">
                                {getDocName(currentDoc)}
                              </span>
                              <span className="text-[10px] text-[var(--text-muted)]">
                                {formatFileSize(currentDoc.size_bytes)} • {chunks.length} chunks vector
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Real Suggested Questions for Active Document */}
                        <div className="space-y-2 pt-2">
                          <span className="text-[11px] font-semibold text-[var(--text-muted)] block px-1">
                            Gợi ý câu hỏi cho tài liệu này:
                          </span>
                          <div className="grid grid-cols-1 gap-2">
                            <button
                              onClick={() => handleSendChat(`Tóm tắt các nội dung và quy định chính trong tài liệu ${getDocName(currentDoc)}`)}
                              className="user-chat-bubble p-3 text-left hover:border-blue-400 hover:shadow-sm transition flex items-center justify-between text-xs"
                            >
                              <span>📋 Tóm tắt các nội dung và quy định chính trong tài liệu</span>
                              <Icon name="arrowUpRight" className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                            </button>

                            <button
                              onClick={() => handleSendChat(`Các mốc thời gian, người phụ trách và trách nhiệm được nêu trong tài liệu`)}
                              className="user-chat-bubble p-3 text-left hover:border-blue-400 hover:shadow-sm transition flex items-center justify-between text-xs"
                            >
                              <span>⏱️ Các mốc thời gian, người phụ trách và trách nhiệm được quy định</span>
                              <Icon name="arrowUpRight" className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                            </button>

                            <button
                              onClick={() => handleSendChat(`Điều kiện áp dụng và các trường hợp ngoại lệ trong tài liệu này là gì?`)}
                              className="user-chat-bubble p-3 text-left hover:border-blue-400 hover:shadow-sm transition flex items-center justify-between text-xs"
                            >
                              <span>⚖️ Điều kiện áp dụng và các trường hợp ngoại lệ cần lưu ý</span>
                              <Icon name="arrowUpRight" className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                            </button>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-10 rounded-2xl border border-dashed border-black/10 dark:border-white/10 bg-white/30 dark:bg-white/5 p-4">
                        <p className="text-xs text-[var(--text-muted)]">
                          Chưa có tài liệu nào được chọn. Hãy tải lên tệp PDF để bắt đầu hỏi đáp AI.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Real Chat Conversation Feed */}
                {chatMessages.map((msg, idx) => {
                  const isUser = msg.role === 'user'
                  return (
                    <div key={idx} className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      {!isUser && (
                        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-1 shadow-xs">
                          AI
                        </div>
                      )}
                      <div className={isUser ? 'user-chat-bubble p-4 max-w-lg font-medium' : 'assistant-chat-card p-5 flex-1'}>
                        <p className="text-xs md:text-sm whitespace-pre-wrap leading-relaxed">
                          {msg.text}
                        </p>

                        {/* Real Source Citations */}
                        {!isUser && msg.sources && msg.sources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-black/5 dark:border-white/10 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                              Trích dẫn chính xác ({msg.sources.length}):
                            </span>
                            {msg.sources.map((s, sIdx) => (
                              <div
                                key={sIdx}
                                onClick={() => {
                                  setCurrentPage(s.page || 1)
                                  setMainMode('split')
                                }}
                                className="p-2 rounded-xl bg-white/70 dark:bg-white/10 hover:border-blue-400 border border-black/5 cursor-pointer text-xs flex items-center justify-between"
                              >
                                <span className="font-semibold text-blue-600 dark:text-blue-400">
                                  {s.file_name} (Trang {s.page || 1})
                                </span>
                                {s.similarity_score && (
                                  <span className="text-[10px] text-emerald-600 font-mono">
                                    {(s.similarity_score * 100).toFixed(1)}% match
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
                <div ref={chatBottomRef} />
              </div>

              {/* ─── REAL QUICK ACTION CARDS (4 ACTIONS CONNECTED TO REAL API) ─── */}
              <div className="max-w-2xl mx-auto w-full pt-4 space-y-3">
                <div className="grid grid-cols-4 gap-2.5">
                  {/* 1. Tóm tắt tài liệu */}
                  <div
                    onClick={() => {
                      if (currentDoc) {
                        handleSendChat(`Tóm tắt các nội dung trọng tâm của tài liệu ${getDocName(currentDoc)}`)
                      }
                    }}
                    className="quick-tool-card p-3 flex flex-col items-center text-center cursor-pointer group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-600 flex items-center justify-center font-bold text-xs mb-2">
                      <Icon name="fileText" className="w-4 h-4" />
                    </div>
                    <span className="text-[11px] font-bold text-[var(--text-primary)]">
                      Tóm tắt tệp
                    </span>
                  </div>

                  {/* 2. Đối chiếu PDF & MD */}
                  <div
                    onClick={() => setMainMode('split')}
                    className="quick-tool-card p-3 flex flex-col items-center text-center cursor-pointer group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-600 flex items-center justify-center font-bold text-xs mb-2">
                      <Icon name="columns" className="w-4 h-4" />
                    </div>
                    <span className="text-[11px] font-bold text-[var(--text-primary)]">
                      Đối chiếu đôi
                    </span>
                  </div>

                  {/* 3. Khung BBox */}
                  <div
                    onClick={() => {
                      setMainMode('split')
                      setShowOcrBoxes(true)
                    }}
                    className="quick-tool-card p-3 flex flex-col items-center text-center cursor-pointer group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center font-bold text-xs mb-2">
                      <Icon name="sparkle" className="w-4 h-4" />
                    </div>
                    <span className="text-[11px] font-bold text-[var(--text-primary)]">
                      Khung BBox
                    </span>
                  </div>

                  {/* 4. Trích xuất .md */}
                  <div
                    onClick={() => {
                      setMainMode('split')
                      setMdViewMode('rendered')
                    }}
                    className="quick-tool-card p-3 flex flex-col items-center text-center cursor-pointer group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center font-bold text-xs mb-2">
                      <Icon name="waveform" className="w-4 h-4" />
                    </div>
                    <span className="text-[11px] font-bold text-[var(--text-primary)]">
                      Văn bản .md
                    </span>
                  </div>
                </div>

                {/* ─── REAL INPUT BAR (PILL CONTAINER WITH SEND) ─── */}
                <div className="bubble-input-bar p-1.5 pl-5 pr-2 flex items-center justify-between">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') handleSendChat()
                    }}
                    placeholder={currentDoc ? `Hỏi đáp về "${getDocName(currentDoc)}"...` : "Nhập câu hỏi tri thức..."}
                    className="flex-1 bg-transparent border-none outline-none text-xs md:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)]"
                  />
                  <button
                    onClick={() => handleSendChat()}
                    disabled={chatLoading || !chatInput.trim()}
                    className="circle-btn-dark w-9 h-9 disabled:opacity-40"
                    title="Gửi câu hỏi"
                  >
                    {chatLoading ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Icon name="arrowUp" className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* ═══ VIEW 2: REAL DUAL-PANE SPLIT COMPARISON (PDF & MARKDOWN) ═══ */
            <div className="flex-1 flex overflow-hidden p-4 gap-4">
              {/* Left Sub-pane: PDF Reader */}
              <div className="flex-1 bubble-tablet-frame bg-white/60 dark:bg-black/20 flex flex-col overflow-hidden p-3">
                <div className="flex items-center justify-between pb-3 border-b border-black/5 dark:border-white/10 mb-3">
                  <span className="text-xs font-bold text-[var(--text-primary)] truncate max-w-[200px]">
                    {currentDoc ? getDocName(currentDoc) : 'Tệp PDF'} • Trang {currentPage} / {numPages || 1}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="circle-btn w-7 h-7 disabled:opacity-40"
                    >
                      <Icon name="chevronLeft" className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(numPages || 1, p + 1))}
                      disabled={currentPage >= (numPages || 1)}
                      className="circle-btn w-7 h-7 disabled:opacity-40"
                    >
                      <Icon name="chevronRight" className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setShowOcrBoxes(!showOcrBoxes)}
                      className={`circle-btn w-7 h-7 ${showOcrBoxes ? 'bg-blue-600 text-white' : ''}`}
                      title="Bật/tắt BBox"
                    >
                      <Icon name="sparkle" className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-auto flex items-center justify-center bg-zinc-100 dark:bg-zinc-900 rounded-2xl p-4">
                  {currentDoc ? (
                    <Document
                      file={`/api/documents/${currentDoc.id}/file`}
                      onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                      className="shadow-md rounded-lg overflow-hidden"
                    >
                      <Page
                        pageNumber={currentPage}
                        scale={pageScale}
                        onLoadSuccess={(page) => {
                          setPdfPageSizes(prev => ({
                            ...prev,
                            [currentPage]: { width: page.width, height: page.height }
                          }))
                        }}
                      />
                    </Document>
                  ) : (
                    <p className="text-xs text-[var(--text-muted)]">Chưa chọn tệp PDF</p>
                  )}
                </div>
              </div>

              {/* Right Sub-pane: Markdown View */}
              <div className="flex-1 bubble-tablet-frame bg-white/60 dark:bg-black/20 flex flex-col overflow-hidden p-3">
                <div className="flex items-center justify-between pb-3 border-b border-black/5 dark:border-white/10 mb-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setMdViewMode('rendered')}
                      className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                        mdViewMode === 'rendered' ? 'bg-blue-600 text-white shadow-xs' : 'text-[var(--text-muted)]'
                      }`}
                    >
                      Đã định dạng .md
                    </button>
                    <button
                      onClick={() => setMdViewMode('raw')}
                      className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                        mdViewMode === 'raw' ? 'bg-blue-600 text-white shadow-xs' : 'text-[var(--text-muted)]'
                      }`}
                    >
                      Mã nguồn .md
                    </button>
                  </div>

                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(fullMarkdown)
                      setCopiedMd(true)
                      setTimeout(() => setCopiedMd(false), 2000)
                    }}
                    className="circle-btn w-7 h-7"
                    title="Sao chép Markdown"
                  >
                    <Icon name="copy" className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 rounded-2xl bg-white/80 dark:bg-zinc-900/80 border border-black/5 text-xs">
                  {fullMarkdown ? (
                    mdViewMode === 'rendered' ? (
                      <div
                        className="prose prose-xs dark:prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: marked.parse(fullMarkdown) }}
                      />
                    ) : (
                      <pre className="font-mono text-[11px] whitespace-pre-wrap">{fullMarkdown}</pre>
                    )
                  ) : (
                    <p className="text-[var(--text-muted)] text-center py-12">
                      {loadingExtraction ? 'Đang trích xuất văn bản từ tài liệu...' : 'Chưa có nội dung trích xuất.'}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

const rootEl = document.getElementById('root')
if (rootEl) {
  createRoot(rootEl).render(<App />)
}
