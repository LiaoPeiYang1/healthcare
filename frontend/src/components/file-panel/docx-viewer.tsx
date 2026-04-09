import DOMPurify from 'dompurify'

export default function DocxViewer({ htmlContent }: { htmlContent: string }) {
  const clean = DOMPurify.sanitize(htmlContent, {
    ALLOWED_TAGS: ['p', 'span', 'table', 'tr', 'td', 'th', 'ul', 'ol', 'li', 'strong', 'em', 'br', 'h1', 'h2', 'h3', 'h4'],
    ALLOWED_ATTR: ['style', 'class'],
  })

  return <div className="docx-preview" dangerouslySetInnerHTML={{ __html: clean }} />
}
