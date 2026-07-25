import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import {
  ArrowUp,
  CheckCircle2,
  FileText,
  LoaderCircle,
  Search,
  Upload,
} from 'lucide-react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

type DocumentRecord = {
  id: string
  filename: string
  status: string
}

type Citation = {
  index: number
  chunk_id: string
  document_id: string
  filename: string
  content: string
  score: number
}

type AnswerResponse = {
  question: string
  answer: string
  citations: Citation[]
}

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [document, setDocument] = useState<DocumentRecord | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AnswerResponse | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnswering, setIsAnswering] = useState(false)
  const [error, setError] = useState('')

  const processFile = async (file: File) => {
    setError('')
    setAnswer(null)
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const uploadResponse = await fetch(`${API_BASE_URL}/documents`, {
        method: 'POST',
        body: formData,
      })

      if (!uploadResponse.ok) {
        const payload = await uploadResponse.json().catch(() => null)
        throw new Error(payload?.detail ?? '文档上传失败')
      }

      const uploaded: DocumentRecord = await uploadResponse.json()
      setDocument(uploaded)

      const processResponse = await fetch(
        `${API_BASE_URL}/documents/${uploaded.id}/process`,
        { method: 'POST' },
      )

      if (!processResponse.ok) {
        const payload = await processResponse.json().catch(() => null)
        throw new Error(payload?.detail ?? '文档处理失败')
      }

      setDocument(await processResponse.json())
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '操作失败')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) void processFile(file)
  }

  const handleQuestion = async (event: FormEvent) => {
    event.preventDefault()
    const normalizedQuestion = question.trim()
    if (normalizedQuestion.length < 2 || isAnswering) return

    setError('')
    setIsAnswering(true)

    try {
      const response = await fetch(`${API_BASE_URL}/rag/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: normalizedQuestion, limit: 5 }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.detail ?? '生成回答失败')
      }

      setAnswer(await response.json())
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '操作失败')
    } finally {
      setIsAnswering(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><Search size={19} /></div>
        <div>
          <h1>Deep Research</h1>
          <p>Local evidence workspace</p>
        </div>
        <span className="service-status"><i /> 本地模型在线</span>
      </header>

      <section className="workspace">
        <aside className="library-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">KNOWLEDGE BASE</span>
              <h2>研究资料</h2>
            </div>
            <button
              className="icon-button"
              type="button"
              title="上传文档"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              <Upload size={18} />
            </button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileChange}
            hidden
          />

          <button
            className="upload-zone"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? <LoaderCircle className="spin" /> : <Upload />}
            <strong>{isUploading ? '正在构建索引' : '添加研究资料'}</strong>
            <span>PDF、TXT 或 Markdown，最大 10 MB</span>
          </button>

          <div className="document-list">
            {document ? (
              <div className="document-row">
                <span className="file-icon"><FileText size={18} /></span>
                <div>
                  <strong>{document.filename}</strong>
                  <span>{document.status === 'ready' ? '已完成向量索引' : document.status}</span>
                </div>
                {document.status === 'ready' && <CheckCircle2 className="ready-icon" size={17} />}
              </div>
            ) : (
              <p className="empty-library">上传资料后即可基于内容提问</p>
            )}
          </div>
        </aside>

        <section className="research-panel">
          <div className="research-header">
            <span className="eyebrow">RESEARCH SESSION</span>
            <h2>基于证据展开研究</h2>
            <p>答案仅根据本地知识库生成，并保留可核验的原文引用。</p>
          </div>

          <div className="conversation">
            {!answer && !isAnswering && (
              <div className="empty-state">
                <Search size={28} />
                <h3>从一个具体问题开始</h3>
                <p>系统将检索最相关的资料片段，再由本地模型组织答案。</p>
              </div>
            )}

            {isAnswering && (
              <div className="thinking-state">
                <LoaderCircle className="spin" />
                <div><strong>正在分析证据</strong><span>检索资料并生成可引用回答...</span></div>
              </div>
            )}

            {answer && !isAnswering && (
              <article className="answer-block">
                <span className="answer-label">ANSWER</span>
                <h3>{answer.question}</h3>
                <p className="answer-copy">{answer.answer}</p>

                {answer.citations.length > 0 && (
                  <div className="citations">
                    <h4>引用来源</h4>
                    {answer.citations.map((citation) => (
                      <details key={citation.chunk_id} className="citation-item">
                        <summary>
                          <span>[{citation.index}]</span>
                          <strong>{citation.filename}</strong>
                          <small>{Math.round(citation.score * 100)}% 相关</small>
                        </summary>
                        <p>{citation.content}</p>
                      </details>
                    ))}
                  </div>
                )}
              </article>
            )}
          </div>

          {error && <div className="error-message">{error}</div>}

          <form className="question-form" onSubmit={handleQuestion}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="针对已上传资料提出问题..."
              rows={2}
            />
            <button
              className="send-button"
              type="submit"
              title="发送问题"
              disabled={question.trim().length < 2 || isAnswering}
            >
              {isAnswering ? <LoaderCircle className="spin" size={19} /> : <ArrowUp size={19} />}
            </button>
          </form>
        </section>
      </section>
    </main>
  )
}

export default App
