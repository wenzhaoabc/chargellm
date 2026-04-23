import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'

type Props = {
  text: string
}

export function MarkdownView({ text }: Props) {
  return (
    <div className="markdown-view">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {text}
      </ReactMarkdown>
    </div>
  )
}
